"""GenVar-PE · Hito 2 · Experimento de optimización (Sección 5).

Para cada escenario (1k, 10k, 100k y 1M filas en GENOTIPO):
  1. genera los datos con sql/06_generar_datos.sql y guarda el dump (pg_dump -Fc);
  2. ejecuta cada consulta sin índices, con el plan A y con el plan B
     (1 ejecución de calentamiento + REPS mediciones, se reporta la mediana
     del "Execution Time" de EXPLAIN ANALYZE);
  3. mide el costo de las actualizaciones (INSERT de genotipos y UPDATE de
     anotaciones) sin índices y con los índices finales.
Uso:  python3 experimento.py [--escalas 1000 10000 100000 1000000] [--reps 7]
"""
import argparse, json, os, statistics, subprocess, time
import psycopg2
from consultas import CONSULTAS, PLANES, INDICES_FINALES, REGION, MV_C3, C3_SOBRE_MV

AQUI = os.path.dirname(os.path.abspath(__file__))
SQL = os.path.join(AQUI, "..", "sql")
DUMPS = os.path.join(AQUI, "..", "dumps")
DB = os.environ.get("GENVAR_DB", "genvar")


def conectar():
    c = psycopg2.connect(dbname=DB)
    c.autocommit = True
    cur = c.cursor()
    cur.execute("SET search_path TO genvar")
    return c, cur


def borrar_indices(cur):
    cur.execute("""SELECT indexname FROM pg_indexes
                   WHERE schemaname = 'genvar' AND indexname LIKE 'ix\\_%'""")
    for (ix,) in cur.fetchall():
        cur.execute(f"DROP INDEX genvar.{ix}")


def nodos(plan, acc):
    """Junta los nodos de acceso del plan (Seq Scan sobre X, Index Scan con Y...)."""
    t = plan["Node Type"]
    if "Scan" in t and "Relation Name" in plan:
        acc.add(f"{t} {plan['Relation Name']}" + (f" ({plan['Index Name']})" if "Index Name" in plan else ""))
    for p in plan.get("Plans", []):
        nodos(p, acc)
    return acc


def medir(cur, sql, params, reps):
    cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params)  # calentamiento
    tiempos, plan = [], None
    for _ in range(reps):
        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params)
        r = cur.fetchone()[0][0]
        tiempos.append(r["Execution Time"])
        plan = r["Plan"]
    cur.execute(sql, params)
    filas = cur.rowcount
    return dict(mediana_ms=statistics.median(tiempos), min_ms=min(tiempos), max_ms=max(tiempos),
                tiempos_ms=tiempos, filas=filas, nodos=sorted(nodos(plan, set())))


def medir_actualizaciones(cur, reps):
    """INSERT de hasta 5 000 genotipos (20 muestras x 250 variantes) y UPDATE de 1 000 anotaciones, dentro de una
    transacción que se deshace (ROLLBACK) para no alterar los datos."""
    res = {}
    ins = """EXPLAIN (ANALYZE, FORMAT JSON)
             INSERT INTO genotipo
             SELECT mc.id_muestra, mc.id_corrida, v.id_variante, '0/1', 40, 50, 0.5, 'PASS'
             FROM (SELECT id_muestra, id_corrida FROM muestra_corrida ORDER BY id_muestra LIMIT 20) mc
             CROSS JOIN (SELECT id_variante FROM variante ORDER BY id_variante DESC LIMIT 250) v
             ON CONFLICT DO NOTHING"""
    upd = """EXPLAIN (ANALYZE, FORMAT JSON)
             UPDATE anotacion_clinica SET significancia = 'BENIGNA', fecha_evaluacion = DATE '2026-09-30'
             WHERE id_anotacion IN (SELECT id_anotacion FROM anotacion_clinica
                                    WHERE significancia <> 'BENIGNA' ORDER BY id_anotacion LIMIT 1000)"""
    for nombre, sql in (("insert_5000_genotipos", ins), ("update_1000_anotaciones", upd)):
        t = []
        for _ in range(reps):
            cur.execute("BEGIN")
            cur.execute(sql)
            r = cur.fetchone()[0][0]
            t.append(r["Execution Time"] + sum(tr.get("Time", 0) for tr in r.get("Triggers", [])))
            cur.execute("ROLLBACK")
        res[nombre] = dict(mediana_ms=statistics.median(t), tiempos_ms=t)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escalas", type=int, nargs="+", default=[1000, 10000, 100000, 1000000])
    ap.add_argument("--reps", type=int, default=7)
    ap.add_argument("--sin-generar", action="store_true", help="usar los datos ya cargados")
    a = ap.parse_args()
    os.makedirs(DUMPS, exist_ok=True)
    salida = os.path.join(AQUI, "resultados.json")
    todo = json.load(open(salida)) if os.path.exists(salida) else {}

    for n in a.escalas:
        print(f"\n===== Escenario N = {n:,} genotipos =====", flush=True)
        c, cur = conectar()
        borrar_indices(cur)
        if not a.sin_generar:
            t0 = time.time()
            subprocess.run(["psql", "-d", DB, "-q", "-v", f"N={n}", "-f",
                            os.path.join(SQL, "06_generar_datos.sql")], check=True,
                           stdout=subprocess.DEVNULL)
            t_carga = time.time() - t0
            dump = os.path.join(DUMPS, f"genvar_{n}.dump")
            subprocess.run(["pg_dump", "-d", DB, "-n", "genvar", "-Fc", "-f", dump], check=True)
            print(f"  datos generados en {t_carga:.1f} s; dump {os.path.getsize(dump)/1e6:.1f} MB")
        else:
            t_carga = None
        cur.execute("VACUUM ANALYZE")

        cur.execute("""SELECT relname, n_live_tup FROM pg_stat_user_tables
                       WHERE schemaname = 'genvar' ORDER BY relname""")
        conteos = {}
        for t, _ in cur.fetchall():
            cur.execute(f"SELECT count(*) FROM {t}")
            conteos[t] = cur.fetchone()[0]

        cur.execute("""SELECT m.id_donante FROM genotipo g JOIN muestra m USING (id_muestra)
                       JOIN anotacion_clinica a ON a.id_variante = g.id_variante
                       WHERE a.significancia IN ('PATOGENICA','PROBABLEMENTE_PATOGENICA')
                         AND g.filtro = 'PASS' AND g.profundidad >= 20
                       GROUP BY 1 ORDER BY count(*) DESC, 1 LIMIT 1""")
        fila = cur.fetchone()
        if fila is None:   # escenario chico sin hallazgos: el donante con más genotipos
            cur.execute("""SELECT m.id_donante FROM genotipo g JOIN muestra m USING (id_muestra)
                           GROUP BY 1 ORDER BY count(*) DESC, 1 LIMIT 1""")
            fila = cur.fetchone()
        donante = fila[0]
        params = dict(donante=donante, **REGION)

        esc = dict(n=n, t_carga_s=t_carga, conteos=conteos, parametros=params, consultas={})
        for q, info in CONSULTAS.items():
            esc["consultas"][q] = {}
            for cfg in ("sin", "A", "B"):
                borrar_indices(cur)
                t_idx = 0.0
                if cfg != "sin":
                    t0 = time.time()
                    for ddl in PLANES[q][cfg][1]:
                        cur.execute(ddl)
                    t_idx = (time.time() - t0) * 1000
                    cur.execute("ANALYZE")
                r = medir(cur, info["sql"], params, a.reps)
                r["t_crear_indices_ms"] = t_idx
                esc["consultas"][q][cfg] = r
                print(f"  {q} {cfg:>3}: {r['mediana_ms']:9.2f} ms  filas={r['filas']}", flush=True)
            filas = {esc["consultas"][q][k]["filas"] for k in ("sin", "A", "B")}
            assert len(filas) == 1, f"{q}: los planes devuelven distinto número de filas {filas}"

        # Alternativa para C3 (agregación de toda la tabla): vista materializada
        borrar_indices(cur)
        cur.execute("DROP MATERIALIZED VIEW IF EXISTS mv_frec_variante")
        t0 = time.time()
        cur.execute(MV_C3)
        t_mv = (time.time() - t0) * 1000
        cur.execute("ANALYZE mv_frec_variante")
        r = medir(cur, C3_SOBRE_MV, params, a.reps)
        t0 = time.time()
        cur.execute("REFRESH MATERIALIZED VIEW mv_frec_variante")
        r["t_refresh_ms"] = (time.time() - t0) * 1000
        r["t_crear_ms"] = t_mv
        esc["c3_vista_materializada"] = r
        print(f"  C3  MV: {r['mediana_ms']:9.2f} ms  filas={r['filas']}  (refresh {r['t_refresh_ms']:.0f} ms)")
        cur.execute("DROP MATERIALIZED VIEW mv_frec_variante")

        # Actualizaciones sin índices vs con los índices finales
        borrar_indices(cur)
        cur.execute("ANALYZE")
        act_sin = medir_actualizaciones(cur, a.reps)
        t0 = time.time()
        for ddl in INDICES_FINALES:
            cur.execute(ddl)
        t_fin = (time.time() - t0) * 1000
        cur.execute("ANALYZE")
        act_con = medir_actualizaciones(cur, a.reps)
        cur.execute("""SELECT indexrelname, pg_relation_size(indexrelid)
                       FROM pg_stat_user_indexes WHERE schemaname = 'genvar' AND indexrelname LIKE 'ix\\_%'""")
        tam = dict(cur.fetchall())
        cur.execute("SELECT pg_total_relation_size('genotipo'), pg_relation_size('genotipo')")
        tot, heap = cur.fetchone()
        esc["actualizaciones"] = dict(sin=act_sin, con=act_con, t_crear_finales_ms=t_fin,
                                      tam_indices=tam, genotipo_total=tot, genotipo_heap=heap)
        for k in act_sin:
            print(f"  {k}: sin {act_sin[k]['mediana_ms']:.1f} ms | con {act_con[k]['mediana_ms']:.1f} ms")
        todo[str(n)] = esc
        json.dump(todo, open(salida, "w"), indent=1, ensure_ascii=False)
        c.close()

    # deja la base con el escenario más grande y los índices finales
    print("\nResultados en", salida)


if __name__ == "__main__":
    main()
