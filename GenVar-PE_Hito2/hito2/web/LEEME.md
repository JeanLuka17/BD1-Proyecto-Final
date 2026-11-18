# GenVar-PE · MVP web

Aplicación web (Flask + PostgreSQL) para el punto extra del Hito 2.

## Qué hace
- **Inicio:** cantidad de filas de las tablas principales y los últimos eventos de la bitácora.
- **Consultas C1–C8:** formulario con los parámetros de cada consulta, resultado en tabla, tiempo de ejecución, el SQL y, opcionalmente, el plan (`EXPLAIN ANALYZE`). C1, C2, C3, C5 y C6 usan exactamente el mismo SQL del experimento (`exp/consultas.py`).
- **Donante:** buscador arriba; muestra sus muestras y su reporte clínico (`fn_reporte_clinico`).
- **Registrar y actualizar:** registrar donantes y muestras (`sp_registrar_muestra`), reclasificar anotaciones (`sp_reclasificar_anotacion`, trigger T8) y revocar consentimientos (`sp_revocar_consentimiento`, trigger T9). Si una operación viola una regla (por ejemplo, muestra de un donante sin consentimiento), se muestra el error que lanza el trigger.
- **Índices y tiempos:** borrar los índices, medir las 5 consultas, crear los índices finales y volver a medir; muestra la comparación en barras y tabla. Sirve para grabar el video del experimento.
- **Roles:** arriba a la derecha se elige "actuar como" genetista, investigador, etc. (`SET ROLE`), para mostrar que cada rol solo ve lo que le corresponde.

## Cómo correrla
1. Tener la base `genvar` cargada (por ejemplo `pg_restore -O -x -d genvar dumps/genvar_1000000.dump`) con los scripts `sql/01` a `05` aplicados.
2. Instalar dependencias y ejecutar (desde la carpeta `web/`, que debe estar junto a `exp/`):
```bash
pip install -r requirements.txt
python app.py
```
3. Abrir http://localhost:5000

Si PostgreSQL pide usuario y contraseña, usar la variable `GENVAR_DSN`:
```bash
# Linux / Mac
GENVAR_DSN="dbname=genvar user=postgres password=TU_CLAVE host=localhost" python app.py
# Windows (PowerShell)
$env:GENVAR_DSN="dbname=genvar user=postgres password=TU_CLAVE host=localhost"; python app.py
```
Para usar "actuar como", el usuario de la conexión debe ser superusuario (como `postgres`) o miembro de esos roles.
