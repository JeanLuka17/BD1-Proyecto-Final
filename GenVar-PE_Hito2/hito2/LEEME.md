# GenVar-PE · Hito 2

Implementación en PostgreSQL y experimento de índices (secciones 4 a 7 del informe).

## Contenido
- `sql/01_esquema.sql` a `05_roles.sql`: tablas, vistas, procedimientos, triggers y roles.
- `sql/06_generar_datos.sql`: simulación de datos (`psql -d genvar -v N=1000000 -f sql/06_generar_datos.sql`).
- `sql/07_consultas.sql`: consultas C1 a C8. `sql/08_indices.sql`: planes evaluados e índices finales.
- `sql/09_pruebas.sql`: 12 pruebas de triggers y procedimientos (salida en `exp/salida_pruebas.txt`).
- `dumps/`: los 4 escenarios (1k, 10k, 100k, 1M genotipos). Restaurar: `createdb genvar && pg_restore -O -x -d genvar dumps/genvar_1000000.dump`.
- `exp/`: `consultas.py` (fuente única de consultas y planes), `experimento.py`, `graficos.py`, `resultados.json`.
- `fig/`: gráficos de la Sección 5.6.
- `web/`: MVP web (Flask) para el punto extra; ver `web/LEEME.md`.
- `tex/hito2.tex`: secciones 4 a 7 para pegar en el informe con `\input{hito2}` después de la Sección 3.
  `tex/main_hito2.tex` compila esas secciones solas (sirve para probar en Overleaf; ver el preámbulo que usa).
- `final/`: `hito1_original.tex` (LaTeX del Hito 1) y `unir.py`, que arma el informe completo (`informe_final/overleaf/main.tex`).

## Reproducir todo
```bash
createdb genvar
for f in 01_esquema 02_vistas 03_procedimientos 04_triggers 05_roles; do psql -d genvar -f sql/$f.sql; done
pip install psycopg2-binary matplotlib
python3 exp/experimento.py --reps 7      # ~6 min: 4 escenarios, dumps y resultados.json
python3 exp/graficos.py                  # fig/*.png
python3 tex/construir_tex.py             # rehace tex/hito2.tex con los números nuevos
python3 final/unir.py                    # vuelve a unir Hito 1 + Hito 2 en final/main.tex
psql -d genvar -f sql/08_indices.sql
psql -d genvar -f sql/09_pruebas.sql
```
Si corren el experimento en su propia PC, los tiempos cambian: actualicen la tabla de la Sección 5.4 (Plataforma de pruebas) con los datos de su máquina.

## Guion del video (Anexo 7.1)
1. `createdb genvar && pg_restore -O -x -d genvar dumps/genvar_1000000.dump`
2. En psql: `SET search_path TO genvar;` y `\timing on`. Mostrar `SELECT count(*) FROM genotipo;` (1 000 000).
3. Sin índices: mostrar `\di genvar.*` (solo PK/UNIQUE) y ejecutar `\i sql/07_consultas.sql` (o C1, C2, C3, C5 y C6 una por una). Mostrar un `EXPLAIN ANALYZE` de C6 con `Seq Scan`.
4. Crear los índices: `\i sql/08_indices.sql`.
5. Volver a ejecutar las mismas consultas y el `EXPLAIN ANALYZE` de C6 (ahora usa `ix_gen_mue_var`). Comparar los tiempos.
6. Subir el video y poner el enlace en la Sección 7.1 del informe.
