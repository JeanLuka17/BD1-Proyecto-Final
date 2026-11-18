"""Genera sql/07_consultas.sql y sql/08_indices.sql desde consultas.py."""
import os
from consultas import CONSULTAS, PLANES, INDICES_FINALES, REGION

SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")

def psql(sql):
    return (sql.replace("%(donante)s", ":'donante'").replace("%(crom)s", ":'crom'")
               .replace("%(ini)s", ":ini").replace("%(fin)s", ":fin"))

EXTRA = """
-- =====================================================================
-- Consultas adicionales del Hito 1 (no entran al experimento)
-- =====================================================================

-- C4. Control de calidad del último trimestre por laboratorio y secuenciador
SELECT l.nombre AS laboratorio, s.id_secuenciador,
       count(DISTINCT c.id_corrida)                                   AS corridas,
       round(avg(mc.cobertura_media), 1)                              AS cobertura_promedio,
       round(100.0 * avg((mc.cobertura_media < 30 OR mc.pct_q30 < 80)::int), 1)
                                                                      AS pct_muestras_deficientes
FROM laboratorio l
JOIN secuenciador s     ON s.id_laboratorio  = l.id_laboratorio
JOIN corrida c          ON c.id_secuenciador = s.id_secuenciador
JOIN muestra_corrida mc ON mc.id_corrida     = c.id_corrida
WHERE c.fecha_inicio >= :'hoy'::date - interval '3 months'
GROUP BY l.nombre, s.id_secuenciador
ORDER BY pct_muestras_deficientes DESC;

-- C7. Búsqueda puntual por identificador rs o por símbolo de gen
SELECT v.id_variante, v.rsid, v.id_cromosoma, v.posicion, v.alelo_ref, v.alelo_alt,
       v.tipo_variante, ge.simbolo, vg.consecuencia, a.significancia, a.estado_revision
FROM v_variante v
LEFT JOIN variante_gen vg     ON vg.id_variante = v.id_variante
LEFT JOIN gen ge              ON ge.id_gen      = vg.id_gen
LEFT JOIN anotacion_clinica a ON a.id_variante  = v.id_variante
WHERE v.rsid = :'rs' OR ge.simbolo = :'simbolo';

-- C8. Reevaluación: donantes con variantes reclasificadas de VUS a (probablemente)
--     patogénica DESPUÉS de su último informe
SELECT DISTINCT m.id_donante, v.rsid, a.id_anotacion, h.significancia_nueva,
       h.fecha_cambio, ult.ultimo_informe
FROM anotacion_historial h
JOIN anotacion_clinica a ON a.id_anotacion = h.id_anotacion
JOIN variante v          ON v.id_variante  = a.id_variante
JOIN genotipo g          ON g.id_variante  = a.id_variante
JOIN muestra m           ON m.id_muestra   = g.id_muestra
JOIN (SELECT id_donante, max(fecha_informe) AS ultimo_informe
      FROM informe GROUP BY id_donante) ult ON ult.id_donante = m.id_donante
WHERE h.significancia_anterior = 'VUS'
  AND h.significancia_nueva IN ('PATOGENICA','PROBABLEMENTE_PATOGENICA')
  AND h.fecha_cambio > ult.ultimo_informe
ORDER BY m.id_donante, h.fecha_cambio;
"""

with open(os.path.join(SQL, "07_consultas.sql"), "w") as f:
    f.write("-- =====================================================================\n"
            "-- GenVar-PE · Hito 2 · 5.1.2 Implementación de las consultas en SQL\n"
            "-- Uso: psql -d genvar -v donante=CGA-D000001 -f 07_consultas.sql\n"
            "-- =====================================================================\n"
            "SET search_path TO genvar;\n"
            "\\if :{?donante} \\else \\set donante 'CGA-D000001' \\endif\n"
            f"\\set crom '{REGION['crom']}'\n\\set ini {REGION['ini']}\n\\set fin {REGION['fin']}\n"
            "\\set hoy '2026-10-01'\n\\set rs 'rs1000010'\n\\set simbolo 'GV00010'\n\\timing on\n")
    for q, info in CONSULTAS.items():
        f.write(f"\n-- {q}. {info['titulo']}\n-- {info['descripcion']}\n{psql(info['sql'])};\n")
    f.write(EXTRA)

with open(os.path.join(SQL, "08_indices.sql"), "w") as f:
    f.write("-- =====================================================================\n"
            "-- GenVar-PE · Hito 2 · 5.3 Planes de índices evaluados y los índices finales\n"
            "-- =====================================================================\n"
            "SET search_path TO genvar;\n\n-- Planes evaluados en el experimento (se crean y se borran uno a la vez):\n")
    for q, planes in PLANES.items():
        for k, (desc, ddls) in planes.items():
            f.write(f"--   {q} plan {k}: {desc}\n")
            for d in ddls:
                f.write(f"--     {d};\n")
    f.write("\n-- Índices finales que quedan en la base de datos:\n")
    for d in INDICES_FINALES:
        f.write(d + ";\n")
    f.write("ANALYZE;\n")
print("ok")
