"""Arma tex/hito2.tex (secciones 4 a 7 del informe) a partir de los .sql y de
exp/resultados.json, para que los números del informe sean los medidos."""
import json, os, re, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..")
sys.path.insert(0, os.path.join(RAIZ, "exp"))
from consultas import CONSULTAS, PLANES, INDICES_FINALES, REGION  # noqa: E402

R = json.load(open(os.path.join(RAIZ, "exp", "resultados.json")))
NS = sorted(R, key=int)
ETQ = {"1000": "1k", "10000": "10k", "100000": "100k", "1000000": "1M"}
QS = list(CONSULTAS)
M = "1000000"


def esc(s):
    return (s.replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("%", r"\%")
             .replace("&", r"\&").replace("#", r"\#").replace(">=", r"$\geq$"))


def tt(s):
    return r"\texttt{" + esc(s) + "}"


def ms(x):
    if x >= 100:
        return f"{x:,.0f}".replace(",", r"\,")
    if x >= 10:
        return f"{x:.1f}"
    return f"{x:.2f}"


def t(n, q, cfg):
    return R[n]["consultas"][q][cfg]["mediana_ms"]


def acel(n, q, cfg):
    return t(n, q, "sin") / t(n, q, cfg)


def sql_bloque(ruta, desde=None, hasta=None):
    txt = open(os.path.join(RAIZ, "sql", ruta)).read()
    if desde:
        i = txt.index(desde)
        j = txt.index(hasta, i) + len(hasta) if hasta else len(txt)
        txt = txt[i:j]
    return txt.strip("\n")


def listing(codigo, titulo, label=None):
    extra = f",label={label}" if label else ""
    return ("\\begin{lstlisting}[language=SQL,caption={" + titulo + "}" + extra + "]\n" + codigo + "\n\\end{lstlisting}\n")


def sql_psql(s):
    return s.replace("%(donante)s", ":'donante'").replace("%(crom)s", ":'crom'") \
            .replace("%(ini)s", ":ini").replace("%(fin)s", ":fin")


c = R[M]["conteos"]
act = R[M]["actualizaciones"]
tam = act["tam_indices"]
mv = {n: R[n]["c3_vista_materializada"] for n in NS}

out = []
w = out.append

# =====================================================================
w(r"""%% =====================================================================
%% GenVar-PE · Hito 2 · Secciones 4 a 7
%% Generado por tex/construir_tex.py a partir de sql/*.sql y exp/resultados.json
%% =====================================================================

\section{Implementación de la base de datos}

La base de datos se implementó en PostgreSQL 16~\cite{postgres} dentro del esquema \texttt{genvar}. Todo el código está
en la carpeta \texttt{sql/} del repositorio del proyecto y se ejecuta en este orden:

\begin{table}[H]
\centering\small
\begin{tabular}{@{}ll@{}}
\toprule
Archivo & Contenido \\
\midrule
\texttt{01\_esquema.sql} & Creación de tablas, llaves y restricciones (4.1) \\
\texttt{02\_vistas.sql} & Vistas de usuario (4.4) \\
\texttt{03\_procedimientos.sql} & Procedimientos almacenados y funciones (4.5) \\
\texttt{04\_triggers.sql} & Triggers (4.6) \\
\texttt{05\_roles.sql} & Roles y permisos por tipo de usuario \\
\texttt{06\_generar\_datos.sql} & Simulación de datos para los cuatro escenarios (4.3) \\
\texttt{07\_consultas.sql} & Las consultas C1--C8 (5.1.2) \\
\texttt{08\_indices.sql} & Planes de índices evaluados e índices finales (5.3) \\
\texttt{09\_pruebas.sql} & Pruebas de triggers y procedimientos (4.6) \\
\bottomrule
\end{tabular}
\caption{Scripts de la implementación.}
\end{table}

\subsection{Creación de tablas}\label{sec:creacion}

Las tablas siguen al pie de la letra el modelo relacional y el diccionario de datos de la Sección~3.
Cada regla semántica que se puede expresar dentro de una sola tabla se implementó como restricción
declarativa (\texttt{PRIMARY KEY}, \texttt{UNIQUE}, \texttt{FOREIGN KEY}, \texttt{NOT NULL} y \texttt{CHECK});
las que necesitan mirar otra tabla se implementaron con triggers (Sección~4.6). Las decisiones más
importantes son:

\begin{itemize}
  \item \textbf{RS19 con una llave foránea compuesta.} \texttt{genotipo(id\_muestra, id\_corrida)} referencia a
        \texttt{muestra\_corrida}, no a \texttt{muestra} y \texttt{corrida} por separado. Así es imposible guardar
        un genotipo de una muestra en una corrida en la que no fue secuenciada, sin escribir un trigger.
  \item \textbf{Especialización Is-A (RS3) con una tabla por clase.} \texttt{muestra\_germinal} y
        \texttt{muestra\_tumoral} tienen como llave primaria y foránea a \texttt{id\_muestra}. Que sea disjunta y
        total no lo puede garantizar un \texttt{CHECK}, por eso lo hacen los triggers T4 y T5.
  \item \textbf{Entidad débil \texttt{exon}.} Su llave es \texttt{(id\_gen, numero\_exon)} y se borra en cascada con su gen.
  \item \textbf{Llave natural de la variante (RS13).} Se usa la llave sustituta \texttt{id\_variante BIGSERIAL} para que
        \texttt{genotipo} sea liviana, y la llave natural \texttt{(id\_cromosoma, posicion, alelo\_ref, alelo\_alt)}
        queda como \texttt{UNIQUE}.
  \item \textbf{Atributo derivado.} \texttt{tipo\_variante} (RS15) no se guarda; se calcula en la vista \texttt{v\_variante}
        para no romper la FNBC.
  \item \textbf{Borrado en cascada (RS23).} \texttt{muestra}, \texttt{muestra\_corrida} y \texttt{genotipo} usan
        \texttt{ON DELETE CASCADE} hacia su padre.
  \item \textbf{Corrección al diccionario.} Al implementar se detectó que \texttt{secuenciador.tecnologia} no cabía en
        \texttt{VARCHAR(12)}, porque el valor \texttt{'LECTURA\_CORTA'} tiene 13 caracteres. Se cambió a \texttt{VARCHAR(14)}
        y el diccionario de datos de la Sección~3 ya refleja el cambio.
\end{itemize}

Además se agregaron tres tablas que el Hito~1 necesitaba pero no había modelado como tablas:
\texttt{informe} (fecha del último informe de cada donante, usada por la consulta C8),
\texttt{anotacion\_historial} (reclasificaciones de ClinVar, la llena el trigger T8) y
\texttt{bitacora} (auditoría de cargas y revocaciones). El Listado~\ref{lst:genotipo} muestra la tabla de hechos.
""")

w(listing(sql_bloque("01_esquema.sql", "CREATE TABLE muestra_corrida (", ");\n\n-- ---------- Tablas agregadas"
                     ).replace("\n\n-- ---------- Tablas agregadas", ""),
          r"Tablas \texttt{muestra\_corrida} y \texttt{genotipo} (extracto de \texttt{01\_esquema.sql})", "lst:genotipo"))

# ---------------------------------------------------------------------
filas_tablas = ["genotipo", "variante", "variante_gen", "exon", "anotacion_clinica", "gen", "condicion",
                "muestra_corrida", "muestra", "muestra_germinal", "muestra_tumoral", "donante", "informe",
                "corrida", "secuenciador", "laboratorio", "cromosoma"]
tabla_conteos = "\n".join(
    f"\\texttt{{{esc(tb)}}} & " + " & ".join(f"{R[n]['conteos'][tb]:,}".replace(",", r"\,") for n in NS) + r" \\"
    for tb in filas_tablas)
tiempos_carga = " & ".join(f"{R[n]['t_carga_s']:.1f}" for n in NS)
tam_dump = {"1000": "0.1", "10000": "0.3", "100000": "2.0", "1000000": "22.2"}
dumps = " & ".join(tam_dump[n] for n in NS)

w(r"""
\subsection{Carga de datos}\label{sec:carga}

La carga sigue el orden de las dependencias entre llaves foráneas: primero el catálogo de referencia
(\texttt{cromosoma}, \texttt{gen}, \texttt{exon}, \texttt{variante}, \texttt{variante\_gen}, \texttt{condicion},
\texttt{anotacion\_clinica}), luego los laboratorios y secuenciadores, los donantes y sus muestras, las corridas
con sus muestras y, al final, los genotipos.

\paragraph{Carga de genotipos desde un VCF.} En operación, los genotipos llegan por corrida en archivos VCF ya
normalizados. El bioinformático los copia a la tabla de paso \texttt{stg\_genotipo} con \texttt{COPY} (la forma
más rápida de cargar en PostgreSQL) y llama al procedimiento \texttt{sp\_cargar\_genotipos} (Sección 4.5), que
inserta en el catálogo solo las variantes nuevas, inserta los genotipos y deja constancia en la bitácora:

\begin{lstlisting}[language=bash]
psql -d genvar -c "\copy genvar.stg_genotipo FROM 'RUN-2026-0142.tsv' WITH (FORMAT csv, DELIMITER E'\t', HEADER)"
psql -d genvar -c "CALL genvar.sp_cargar_genotipos('RUN-2026-0142')"
\end{lstlisting}

\paragraph{Los cuatro escenarios.} Para la experimentación se generaron cuatro bases con 1\,000, 10\,000,
100\,000 y 1\,000\,000 de filas en la tabla de hechos \texttt{genotipo}, escalando proporcionalmente las demás
(Tabla~\ref{tab:conteos}). Cada escenario se guardó en un dump de PostgreSQL (\texttt{dumps/genvar\_N.dump},
formato \texttt{-Fc}) que se restaura con:

\begin{lstlisting}[language=bash]
createdb genvar
pg_restore -d genvar dumps/genvar_1000000.dump
\end{lstlisting}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}lrrrr@{}}
\toprule
Tabla & 1k & 10k & 100k & 1M \\
\midrule
""" + tabla_conteos + r"""
\midrule
Tiempo de generación (s) & """ + tiempos_carga + r""" \\
Tamaño del dump (MB) & """ + dumps + r""" \\
\bottomrule
\end{tabular}
\caption{Filas por tabla en cada escenario.}
\label{tab:conteos}
\end{table}
""")

w(r"""
\subsection{Simulación de datos faltantes}\label{sec:simulacion}

Los datos de los donantes, sus muestras y sus genotipos son datos clínicos protegidos: no existen datos
públicos reales del CGA y, aunque existieran, no podrían usarse en un proyecto académico. Por eso se
simularon todos los datos con el script \texttt{06\_generar\_datos.sql}, escrito en SQL puro, que recibe el
tamaño \texttt{N} como parámetro (\texttt{psql -v N=1000000 -f 06\_generar\_datos.sql}). Del mundo real se tomaron
las longitudes de los 25 cromosomas del ensamblado GRCh38; los genes, variantes y anotaciones se simularon
imitando la forma de Ensembl, gnomAD y ClinVar\footnote{Si se dispone de los archivos de Ensembl, ClinVar o gnomAD,
se pueden cargar en lugar del catálogo simulado con el mismo procedimiento de carga de la Sección 4.2.}. Las
reglas de la simulación son:

\begin{itemize}
  \item \textbf{Reproducible:} el script empieza con \texttt{setseed(0.2026)}, así cada escenario sale igual cada vez.
  \item \textbf{Genes y exones:} los genes se reparten entre cromosomas en proporción a su longitud y siempre
        terminan dentro de él (RS11); cada gen tiene de 1 a 15 exones dentro de sus coordenadas (RS12).
  \item \textbf{Variantes:} 70\,\% caen dentro de un gen; 85\,\% son SNV, 8\,\% deleciones, 6\,\% inserciones y 1\,\% MNV;
        70\,\% tienen identificador rs; la frecuencia poblacional sigue una distribución sesgada hacia valores
        bajos (\texttt{power(random(), 4) * 0.5}) y 10\,\% queda desconocida (RS17).
  \item \textbf{Consecuencias e impacto:} 3\,\% \texttt{stop\_gained}, 25\,\% \texttt{missense\_variant}, 20\,\% sinónimas,
        etc., con el impacto que corresponde a cada consecuencia.
  \item \textbf{Anotaciones clínicas:} la probabilidad de ser patogénica depende del impacto (las de impacto ALTO
        suelen ser patogénicas; las de impacto BAJO, benignas); 15\,\% de las variantes anotadas tienen una
        segunda anotación (RS21).
  \item \textbf{Donantes y muestras:} 97\,\% firmó el consentimiento; solo ellos tienen muestras (RS4). Cada donante
        tiene una muestra germinal (95\,\%) y/o tumoral (30\,\%).
  \item \textbf{Corridas:} las muestras se agrupan de a 12 por orden de colecta y la corrida empieza de 3 a 20 días
        después de la última colecta del grupo (RS9). Alrededor del 10\,\% de las muestras se vuelve a secuenciar
        en una corrida posterior; en esa re-secuenciación 3\,\% de los genotipos sale distinto (para la consulta C6).
  \item \textbf{Genotipos:} cada muestra elige sus variantes con sesgo (\texttt{power(random(), 2.5)}): pocas
        variantes comunes aparecen en muchos donantes y la mayoría son raras, como en un exoma real. 25\,\% son
        homocigotas (\texttt{1/1}), la profundidad depende de la cobertura de la corrida y 5\,\% no pasa los filtros.
  \item \textbf{Historia:} parte de los donantes secuenciados tiene uno o más informes con fecha entre 2024 y 2025,
        y 3\,\% de las VUS se reclasifica a (probablemente) patogénica en 2025--2026; el trigger T8 guarda cada cambio (alimenta la consulta C8).
\end{itemize}

\paragraph{Una lección de la simulación.} En la primera versión, la variante de cada genotipo se elegía dentro de
un \texttt{LATERAL} que no dependía de la muestra. PostgreSQL guardó en caché (nodo \texttt{Memoize}) el resultado
de esa subconsulta y todas las muestras recibieron las mismas variantes: con 1M de genotipos solo había 990
variantes distintas. Al mover \texttt{random()} a la lista del \texttt{SELECT} se obtuvieron
""" + f"{223488:,}".replace(",", r"\,") + r""" variantes distintas. La primera ronda de mediciones se descartó por completo.
""")

# ---------------------------------------------------------------------
w(r"""
\subsection{Views}\label{sec:vistas}

Las vistas cumplen dos funciones: ocultar la complejidad de los joins a cada tipo de usuario de la
Sección~1.5.3 y limitar lo que cada uno puede ver (los permisos se dan sobre la vista y no sobre las tablas).

\begin{table}[H]
\centering\small
\begin{tabular}{@{}p{3.6cm}p{2.4cm}p{8.4cm}@{}}
\toprule
Vista & Usuario & Qué muestra \\
\midrule
\texttt{v\_variante} & todos & Variantes con su atributo derivado \texttt{tipo\_variante} (SNV, INSERCION, DELECION, MNV). \\
\texttt{v\_reporte\_clinico} & genetista & Variantes reportables de cada donante: filtro PASS, profundidad $\geq 20$ y anotación (probablemente) patogénica, con gen, consecuencia y condición. \\
\texttt{v\_frecuencia\_cohorte} & investigador & Solo agregados por variante (número de donantes y frecuencia en la cohorte); nunca una fila de un donante. \\
\texttt{v\_qc\_muestra\_corrida} & técnico, bioinformático & Métricas de calidad por muestra y corrida, con su laboratorio y una marca de calidad deficiente. \\
\texttt{v\_trazabilidad} & auditor & De qué muestra, donante, corrida, secuenciador y laboratorio viene cada genotipo. \\
\bottomrule
\end{tabular}
\caption{Vistas de usuario.}
\end{table}
""")
w(listing(sql_bloque("02_vistas.sql", "CREATE OR REPLACE VIEW v_variante", "FROM variante v;"),
          r"Vista con el atributo derivado"))
w(r"""
\paragraph{Roles.} El script \texttt{05\_roles.sql} crea un rol por tipo de usuario (\texttt{tecnico\_lab},
\texttt{bioinformatico}, \texttt{genetista}, \texttt{investigador}, \texttt{auditor}) y les da solo los permisos que
necesitan. Por ejemplo, el investigador solo puede leer \texttt{v\_frecuencia\_cohorte}, \texttt{v\_variante},
\texttt{gen} y \texttt{condicion}; no tiene acceso a \texttt{genotipo} ni a \texttt{donante}.
""")

# ---------------------------------------------------------------------
w(r"""
\subsection{Procedimientos}\label{sec:procs}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}p{4.6cm}p{9.8cm}@{}}
\toprule
Procedimiento / función & Qué hace \\
\midrule
\texttt{sp\_registrar\_muestra} & Inserta la muestra y su subclase (germinal o tumoral) en la misma transacción, así nunca queda una muestra sin tipo (RS3). \\
\texttt{sp\_cargar\_genotipos} & Carga los genotipos de una corrida desde \texttt{stg\_genotipo}: inserta solo las variantes nuevas (\texttt{ON CONFLICT DO NOTHING}, RS13), inserta los genotipos (la FK compuesta impone RS19), vacía la tabla de paso y escribe en la bitácora. \\
\texttt{sp\_reclasificar\_anotacion} & Cambia la significancia de una anotación (recarga mensual de ClinVar); el trigger T8 guarda el historial. \\
\texttt{sp\_revocar\_consentimiento} & Marca al donante sin consentimiento; el trigger T9 borra en cascada sus datos (RS23). \\
\texttt{fn\_reporte\_clinico(donante)} & Función que devuelve el reporte clínico de un donante (la consulta C1 encapsulada para el genetista). \\
\bottomrule
\end{tabular}
\caption{Procedimientos almacenados y funciones.}
\end{table}
""")
w(listing(sql_bloque("03_procedimientos.sql", "CREATE OR REPLACE PROCEDURE sp_cargar_genotipos", "END $$;"),
          r"Procedimiento de carga de genotipos de una corrida"))

# ---------------------------------------------------------------------
w(r"""
\subsection{Triggers}\label{sec:triggers}

Los triggers implementan las reglas semánticas que un \texttt{CHECK} no puede expresar porque necesitan
consultar otra tabla, y automatizan cambios de estado.

\begin{table}[H]
\centering\small
\begin{tabular}{@{}p{0.6cm}p{4.4cm}p{3.0cm}p{6.4cm}@{}}
\toprule
 & Trigger & Evento & Qué hace \\
\midrule
T1 & \texttt{trg\_gen\_dentro\_cromosoma} & BEFORE INSERT/UPDATE en \texttt{gen} & RS11: el gen termina dentro de su cromosoma. \\
T2 & \texttt{trg\_exon\_dentro\_gen} & BEFORE INSERT/UPDATE en \texttt{exon} & RS12: el exón está dentro de su gen. \\
T3 & \texttt{trg\_muestra\_consentimiento} & BEFORE INSERT en \texttt{muestra} & RS4: el donante debe tener consentimiento. \\
T4 & \texttt{trg\_germinal\_disjunta}, \texttt{trg\_tumoral\_disjunta} & BEFORE INSERT en cada subclase & RS3 (disjunta): una muestra no puede ser de los dos tipos. \\
T5 & \texttt{trg\_muestra\_cobertura\_total} & CONSTRAINT TRIGGER diferido, AFTER INSERT en \texttt{muestra} & RS3 (total): al hacer COMMIT toda muestra debe tener subclase. \\
T6 & \texttt{trg\_muestra\_corrida\_fechas} & BEFORE INSERT/UPDATE en \texttt{muestra\_corrida} & RS9: la colecta no es posterior al inicio de la corrida. Además pasa la muestra de RECIBIDA a EN\_PROCESO. \\
T7 & \texttt{trg\_cerrar\_corrida} & BEFORE UPDATE OF estado en \texttt{corrida} & Una corrida sin muestras no se puede completar; al completarse pone \texttt{fecha\_fin} y pasa sus muestras a SECUENCIADA. \\
T8 & \texttt{trg\_anotacion\_historial} & AFTER UPDATE OF significancia & Guarda cada reclasificación en \texttt{anotacion\_historial}. \\
T9 & \texttt{trg\_donante\_revoca} & AFTER UPDATE OF consentimiento & RS23: borra en cascada las muestras del donante y lo registra en la bitácora. \\
\bottomrule
\end{tabular}
\caption{Triggers implementados.}
\end{table}

T5 merece una explicación: la muestra y su subclase se insertan con dos sentencias, así que entre una y otra
la muestra existe sin tipo. Un trigger normal fallaría en la primera sentencia; por eso es un
\texttt{CONSTRAINT TRIGGER ... DEFERRABLE INITIALLY DEFERRED}, que se revisa recién al hacer \texttt{COMMIT}.
""")
w(listing(sql_bloque("04_triggers.sql", "CREATE OR REPLACE FUNCTION fn_muestra_cobertura_total",
                     "FOR EACH ROW EXECUTE FUNCTION fn_muestra_cobertura_total();"),
          r"T5: cobertura total de la especialización, revisada al COMMIT"))

w(r"""
\paragraph{Pruebas.} El script \texttt{09\_pruebas.sql} prueba cada trigger y procedimiento sobre el escenario de 1M
y al final borra los datos de prueba. Los casos que deben fallar se ejecutan dentro de un bloque que captura el
error y lo imprime. Todos los resultados fueron los esperados (la salida completa está en
\texttt{exp/salida\_pruebas.txt}):

\begin{table}[H]
\centering\small
\begin{tabular}{@{}p{0.5cm}p{6.6cm}p{7.3cm}@{}}
\toprule
 & Prueba & Resultado obtenido \\
\midrule
1 & Muestra de un donante sin consentimiento (T3) & Rechazada: \textit{El donante CGA-DTEST01 no tiene consentimiento informado} \\
2 & \texttt{sp\_registrar\_muestra} germinal válida & Muestra en estado RECIBIDA con fuente SANGRE \\
3 & La misma muestra también como tumoral (T4) & Rechazada: \textit{La muestra CGA-MTEST001 ya es germinal} \\
4 & Muestra sin subclase al confirmar (T5) & Rechazada: \textit{La muestra CGA-MTEST002 no es germinal ni tumoral} \\
5 & Colecta posterior al inicio de la corrida (T6) & Rechazada: \textit{se colectó (2026-09-01) después del inicio de la corrida RUN-TEST1 (2026-08-15)} \\
6 & Completar una corrida sin muestras (T7) & Rechazada: \textit{La corrida RUN-TEST1 no tiene muestras y no puede completarse} \\
7 & Muestra entra a corrida, carga con \texttt{sp\_cargar\_genotipos} y cierre de corrida (T6, T7) & Muestra pasa a EN\_PROCESO; bitácora: \textit{2 variantes nuevas, 2 genotipos}; corrida COMPLETADA con \texttt{fecha\_fin} y muestra SECUENCIADA \\
8 & Genotipo de una muestra en una corrida en la que no está (RS19) & Rechazado por la FK compuesta \texttt{genotipo\_id\_muestra\_id\_corrida\_fkey} \\
9 & \texttt{sp\_reclasificar\_anotacion} de una VUS (T8) & Historial: VUS $\rightarrow$ PATOGENICA con fecha 2026-09-30 \\
10 & \texttt{fn\_reporte\_clinico} del donante con más hallazgos & Devuelve sus variantes patogénicas con gen, consecuencia y condición \\
11 & \texttt{sp\_revocar\_consentimiento} (T9) & Muestras y genotipos del donante: 2 $\rightarrow$ 0; bitácora: \textit{1 muestras eliminadas en cascada} \\
12 & Vista \texttt{v\_variante} & SNV """ + "212\\,547, deleciones 20\\,035, inserciones 14\\,999, MNV 2\\,419" + r""" \\
\bottomrule
\end{tabular}
\caption{Pruebas de las reglas de negocio.}
\end{table}
""")

# =====================================================================
desc_rows = "\n".join(f"{q} & {esc(CONSULTAS[q]['titulo'])} & {esc(CONSULTAS[q]['descripcion'])} \\\\" for q in QS)
w(r"""
\section{Optimización y experimentación}

\subsection{Consultas}\label{sec:consultas}

De las ocho consultas de la Sección~1.5.4 se eligieron las cinco que combinan joins de varias tablas, agregación
y subconsultas, y que leen la tabla de hechos \texttt{genotipo}: C1, C2, C3, C5 y C6. Se mantiene la numeración
del Hito~1. Las otras tres (C4, C7 y C8) también están implementadas en \texttt{07\_consultas.sql}, pero no entran
al experimento: C4 y C7 son triviales en costo (C4 solo lee las tablas de corridas y C7 es una búsqueda por llave
única) y C8 lee principalmente la tabla pequeña de historial.

\subsubsection{Descripción de las consultas}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}p{0.7cm}p{3.2cm}p{10.5cm}@{}}
\toprule
 & Consulta & Descripción \\
\midrule
""" + desc_rows + r"""
\bottomrule
\end{tabular}
\caption{Consultas del experimento.}
\end{table}

\subsubsection{Implementación de las consultas en SQL}

Los parámetros se pasan como variables de \texttt{psql}. En el experimento, \texttt{:donante} es el donante con
más hallazgos de cada escenario y la región de C5 es el cromosoma """ + REGION["crom"] + r""", posiciones
""" + f"{REGION['ini']:,}".replace(",", r"\,") + " a " + f"{REGION['fin']:,}".replace(",", r"\,") + r""".
""")
for q in QS:
    w(listing(sql_psql(CONSULTAS[q]["sql"]) + ";", f"{q}. {esc(CONSULTAS[q]['titulo'])}"))

# ---------------------------------------------------------------------
w(r"""
\subsection{Metodología}

\begin{enumerate}
  \item Para cada escenario (1k, 10k, 100k y 1M) se generan los datos con \texttt{06\_generar\_datos.sql}, se guarda el
        dump y se ejecuta \texttt{VACUUM ANALYZE} para que el planificador tenga estadísticas al día.
  \item Se mide cada consulta en tres configuraciones: \textbf{sin índices}, con el \textbf{plan A} y con el
        \textbf{plan B}. ``Sin índices'' significa solo los índices que PostgreSQL crea por las \texttt{PRIMARY KEY}
        y \texttt{UNIQUE}: no se pueden quitar sin romper la integridad. Antes de cada configuración se borran
        todos los índices del experimento, se crean los del plan y se ejecuta \texttt{ANALYZE}.
  \item Cada medición es el \texttt{Execution Time} que informa \texttt{EXPLAIN (ANALYZE, BUFFERS)}: el tiempo
        dentro del servidor, sin la red ni el cliente. Se hace una ejecución de calentamiento (para que los datos
        estén en memoria) y luego 7 ejecuciones; se reporta la \textbf{mediana}, que no se ve afectada por una
        ejecución aislada lenta, junto con el mínimo y el máximo.
  \item Se verifica que las tres configuraciones devuelvan el mismo número de filas.
  \item Se guarda el plan de ejecución para saber qué índice usó realmente el planificador.
  \item Para el costo de las actualizaciones se mide un \texttt{INSERT} de hasta 5\,000 genotipos y un \texttt{UPDATE}
        de hasta 1\,000 anotaciones, sin índices y con los índices finales, dentro de una transacción que se
        deshace con \texttt{ROLLBACK} para no alterar los datos. El tiempo incluye el de los triggers.
\end{enumerate}

Todo el procedimiento está automatizado en \texttt{exp/experimento.py}, que escribe los resultados en
\texttt{exp/resultados.json}. Las consultas y los planes se definen en un solo archivo (\texttt{exp/consultas.py})
del que también se generan \texttt{07\_consultas.sql} y \texttt{08\_indices.sql}, para que el informe y el
experimento usen exactamente el mismo SQL.
""")

# ---------------------------------------------------------------------
porque = {
"C1": ("El filtro es por donante y luego se busca la anotación de cada variante. Sin índices, PostgreSQL recorre "
       "completas \\texttt{muestra} y \\texttt{anotacion\\_clinica}. El plan A indexa las dos llaves foráneas que "
       "usan esos joins. El plan B cambia el índice de anotaciones por uno \\textbf{parcial} que solo guarda las "
       "anotaciones patogénicas, que son las únicas que pide la consulta, y por eso es más pequeño. "
       "No hace falta un índice para \\texttt{genotipo(id\\_muestra)}: la llave primaria "
       "\\texttt{(id\\_muestra, id\\_corrida, id\\_variante)} empieza por esa columna y ya sirve."),
"C2": ("La consulta busca, para cada genotipo, si su variante tiene una anotación patogénica. El plan A indexa "
       "\\texttt{genotipo(id\\_variante)} para entrar a la tabla de hechos por variante. El plan B combina el índice "
       "parcial de anotaciones patogénicas con un índice \\textbf{cubriente} "
       "\\texttt{genotipo(id\\_variante) INCLUDE (id\\_muestra)}, que tiene todas las columnas que la consulta lee de "
       "\\texttt{genotipo} y permite un \\textit{Index Only Scan} (no visita la tabla)."),
"C3": ("Agrupa \\textbf{toda} la tabla \\texttt{genotipo} por variante y donante, así que ningún índice puede "
       "evitar leer todas las filas. El plan A (B-tree simple en \\texttt{id\\_variante}) se incluye para comprobarlo. "
       "El plan B es un índice cubriente en \\texttt{(id\\_variante, id\\_muestra) INCLUDE (genotipo)}: entrega las filas "
       "ya ordenadas por las columnas del \\texttt{GROUP BY}, con lo que el agrupamiento se puede hacer sin ordenar ni "
       "construir una tabla hash, y sin leer la tabla. Como alternativa que no es un índice se midió una "
       "\\textbf{vista materializada} con el conteo por variante ya calculado."),
"C5": ("Filtra por un rango de posiciones de un cromosoma y luego busca los genotipos de esas variantes. El plan A "
       "es un B-tree compuesto \\texttt{variante(id\\_cromosoma, posicion)} (la igualdad primero y el rango después) "
       "más un B-tree en \\texttt{genotipo(id\\_variante)}. El plan B usa el mismo índice de región y cambia el de "
       "genotipo por un índice \\textbf{hash}, que solo sirve para igualdad, para comparar los dos tipos de índice."),
"C6": ("Une \\texttt{genotipo} consigo misma por \\texttt{(id\\_muestra, id\\_variante)} para comparar dos corridas de "
       "la misma muestra. El plan A es un índice compuesto en ese orden con \\texttt{INCLUDE (genotipo)}. El plan B es "
       "el mismo índice con las columnas en orden inverso, para medir si el orden de las columnas importa."),
}
w(r"""
\subsection{Planes de índices}

Para cada consulta se diseñaron dos planes de índices a partir de sus filtros y sus joins.
""")
for i, q in enumerate(QS, 1):
    filas = "\n".join(f"{k} & {esc(PLANES[q][k][0])} & " + r"\newline ".join(tt(d) for d in PLANES[q][k][1]) + r" \\"
                      for k in ("A", "B"))
    w(f"\\subsubsection{{Plan para {q}}}\n\n{porque[q]}\n\n" + r"""\begin{table}[H]
\centering\footnotesize
\begin{tabular}{@{}p{0.8cm}p{3.9cm}p{9.4cm}@{}}
\toprule
Plan & Idea & Índices \\
\midrule
""" + filas + r"""
\bottomrule
\end{tabular}
\caption{Planes de índices para """ + q + r""".}
\end{table}
""")

# ---------------------------------------------------------------------
w(r"""
\subsection{Plataforma de pruebas}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}ll@{}}
\toprule
Componente & Valor \\
\midrule
Procesador & Intel Xeon @ 2.10 GHz, 4 núcleos virtuales \\
Memoria RAM & 15 GB \\
Almacenamiento & Disco virtual (SSD de la nube) \\
Sistema operativo & Ubuntu 24.04 LTS (Linux, máquina virtual) \\
Motor & PostgreSQL 16.13, configuración por defecto \\
Parámetros relevantes & \texttt{shared\_buffers = 128MB}, \texttt{work\_mem = 4MB}, \\
 & \texttt{max\_parallel\_workers\_per\_gather = 2} \\
Cliente & Python 3.11 con \texttt{psycopg2}, en la misma máquina \\
\bottomrule
\end{tabular}
\caption{Plataforma de pruebas.}
\end{table}

Se dejó la configuración por defecto de PostgreSQL a propósito: con 1M de genotipos la base pesa unos
""" + f"{(act['genotipo_total'])/1e6:.0f}" + r""" MB con índices, más que \texttt{shared\_buffers}, de modo que una parte de las lecturas
viene de la caché del sistema operativo y no de la memoria de PostgreSQL, como pasaría en un servidor pequeño real.
""")

# ---------------------------------------------------------------------
def fila_tiempos(q, cfg):
    return " & ".join(ms(t(n, q, cfg)) for n in NS)


def rango(n, q, cfg):
    r = R[n]["consultas"][q][cfg]
    return f"{ms(r['min_ms'])}--{ms(r['max_ms'])}"


sin_rows = "\n".join(f"{q} & {fila_tiempos(q, 'sin')} & " + f"{R[M]['consultas'][q]['sin']['filas']:,}".replace(",", r"\,") + r" \\"
                     for q in QS)
con_rows = "\n".join(
    f"{q} & {k} & {fila_tiempos(q, k)} & {acel(M, q, k):.1f}$\\times$ \\\\" for q in QS for k in ("A", "B"))
con_rows = con_rows.replace(" & B & ", " & B & ")
w(r"""
\subsection{Medición de tiempos}

Todos los tiempos están en milisegundos y son la mediana de 7 ejecuciones.

\subsubsection{Sin índices}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}lrrrrr@{}}
\toprule
Consulta & 1k & 10k & 100k & 1M & Filas (1M) \\
\midrule
""" + sin_rows + r"""
\bottomrule
\end{tabular}
\caption{Tiempo de ejecución sin índices (ms).}
\label{tab:sin}
\end{table}

\subsubsection{Con índices}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}llrrrrr@{}}
\toprule
Consulta & Plan & 1k & 10k & 100k & 1M & Aceleración en 1M \\
\midrule
""" + con_rows + r"""
\bottomrule
\end{tabular}
\caption{Tiempo de ejecución con cada plan de índices (ms). Aceleración = tiempo sin índices / tiempo con el plan.}
\label{tab:con}
\end{table}

La variación entre ejecuciones fue pequeña. Por ejemplo, en 1M el rango (mínimo--máximo) de C6 fue
""" + rango(M, "C6", "sin") + r""" ms sin índices y """ + rango(M, "C6", "A") + r""" ms con el plan A, y el de C3 fue
""" + rango(M, "C3", "sin") + r""" ms sin índices. Los rangos completos están en \texttt{exp/resultados.json}.
""")

# ---------------------------------------------------------------------
res_txt = {
"C1": f"Es la consulta más rápida en todos los escenarios porque filtra por un solo donante. Hasta 100k los tres casos "
      f"empatan. En 1M el plan A baja de {ms(t(M,'C1','sin'))} a {ms(t(M,'C1','A'))} ms y el plan B a "
      f"{ms(t(M,'C1','B'))} ms ({acel(M,'C1','B'):.1f}$\\times$): el índice parcial ocupa "
      f"{tam['ix_anot_patog']/1e6:.2f} MB frente a {tam['ix_anot_variante']/1e6:.2f} MB del índice completo, y como "
      f"solo contiene anotaciones patogénicas el filtro de significancia ya viene resuelto. Sin índices la consulta ya "
      f"era rápida gracias a que la llave primaria de \\texttt{{genotipo}} empieza por \\texttt{{id\\_muestra}}.",
"C2": f"Es el caso más interesante. En 10k y 100k los dos planes ayudan (en 100k: {ms(t('100000','C2','sin'))} ms sin "
      f"índices, {ms(t('100000','C2','A'))} con A y {ms(t('100000','C2','B'))} con B). Pero en 1M el plan A es "
      f"\\textbf{{más lento}} que no tener índices ({ms(t(M,'C2','A'))} frente a {ms(t(M,'C2','sin'))} ms). El plan "
      f"muestra por qué: el planificador entra a \\texttt{{genotipo}} por el índice una vez por cada variante "
      f"patogénica, y cada fila encontrada obliga a leer una página distinta de la tabla. Cerca del 5.8\\,\\% de los "
      f"genotipos tiene una variante patogénica (unas 58\\,000 filas en 1M); a ese volumen, leer la tabla completa en "
      f"orden y en paralelo cuesta menos que tantos accesos aleatorios. El plan B evita esas visitas a la tabla con un "
      f"\\textit{{Index Only Scan}} y queda empatado con la lectura completa ({ms(t(M,'C2','B'))} ms).",
"C3": f"Ningún índice cambia mucho el tiempo, como se esperaba: la consulta lee el millón de filas igual. Con el plan A "
      f"el planificador ni siquiera usa el índice (sigue haciendo \\textit{{Seq Scan}}). El plan B sí se usa y baja de "
      f"{ms(t(M,'C3','sin'))} a {ms(t(M,'C3','B'))} ms ({acel(M,'C3','B'):.1f}$\\times$) porque recorre el índice ya "
      f"ordenado y se ahorra el ordenamiento del \\texttt{{GROUP BY}}. La mejora real viene de la vista materializada: "
      f"la misma respuesta en {ms(mv[M]['mediana_ms'])} ms, {t(M,'C3','sin')/mv[M]['mediana_ms']:.0f} veces más rápido. "
      f"Su costo es que hay que refrescarla ({ms(mv[M]['t_refresh_ms'])} ms en 1M) y que entre refrescos sus datos "
      f"quedan desactualizados.",
"C5": f"El índice sobre \\texttt{{genotipo(id\\_variante)}} es el que importa: en 1M el tiempo baja de "
      f"{ms(t(M,'C5','sin'))} a {ms(t(M,'C5','A'))} ms ({acel(M,'C5','A'):.1f}$\\times$) y en 100k de "
      f"{ms(t('100000','C5','sin'))} a {ms(t('100000','C5','A'))} ms ({acel('100000','C5','A'):.1f}$\\times$). "
      f"El índice hash y el B-tree dan prácticamente el mismo tiempo, pero el B-tree además sirve para rangos y "
      f"ordenamiento, así que no hay razón para preferir el hash. El índice de región \\texttt{{ix\\_var\\_region}} "
      f"resultó \\textbf{{redundante}}: incluso sin él, el planificador ya usaba el índice del \\texttt{{UNIQUE}} "
      f"\\texttt{{(id\\_cromosoma, posicion, alelo\\_ref, alelo\\_alt)}} de la llave natural, que empieza por las "
      f"mismas dos columnas. Por eso no quedó entre los índices finales.",
"C6": f"Hasta 100k los índices no cambian nada, pero en 1M es la consulta que más gana: de {ms(t(M,'C6','sin'))} a "
      f"{ms(t(M,'C6','A'))} ms con el plan A ({acel(M,'C6','A'):.1f}$\\times$) y {ms(t(M,'C6','B'))} ms con el B. "
      f"Sin índices hay que construir una tabla hash con el millón de genotipos para el self-join; con el índice, cada "
      f"genotipo de una muestra re-secuenciada busca directamente su pareja. El orden de las columnas no importa aquí "
      f"porque el join usa las dos con igualdad. Una prueba adicional con "
      f"\\texttt{{INCLUDE (id\\_corrida, genotipo)}} permitió un \\textit{{Index Only Scan}} y bajó a unos 436 ms.",
}
w(r"""
\subsection{Resultados}

Las figuras usan escala logarítmica en los dos ejes: una recta de pendiente 1 significa que el tiempo crece en
proporción a los datos.
""")
for q in QS:
    w(r"""
\subsubsection*{""" + q + ". " + esc(CONSULTAS[q]["titulo"]) + r"""}

\begin{figure}[H]
\centering
\includegraphics[width=0.72\textwidth]{fig/""" + q + r""".png}
\caption{""" + q + r""": tiempo de ejecución por escenario.}
\end{figure}

""" + res_txt[q] + "\n")

w(r"""
\begin{figure}[H]
\centering
\includegraphics[width=0.72\textwidth]{fig/aceleracion_1M.png}
\caption{Aceleración de cada plan con 1M de genotipos. Una barra bajo 1 significa que el plan empeora la consulta.}
\end{figure}
""")

# actualizaciones
act_rows = []
for op, nom in (("insert_5000_genotipos", "INSERT de 5\\,000 genotipos"),
                ("update_1000_anotaciones", "UPDATE de 1\\,000 anotaciones")):
    for k, kn in (("sin", "sin índices"), ("con", "con índices finales")):
        act_rows.append(f"{nom} & {kn} & " + " & ".join(ms(R[n]['actualizaciones'][k][op]['mediana_ms']) for n in NS) + r" \\")
    sobre = (R[M]['actualizaciones']['con'][op]['mediana_ms'] / R[M]['actualizaciones']['sin'][op]['mediana_ms'] - 1) * 100
    act_rows.append(f"\\multicolumn{{2}}{{r}}{{\\textit{{sobrecosto en 1M}}}} & & & & {sobre:+.0f}\\,\\% \\\\")
    act_rows.append(r"\midrule")
act_rows = "\n".join(act_rows[:-1])

tam_rows = "\n".join(f"\\texttt{{{esc(k)}}} & {v/1e6:.2f} \\\\" for k, v in sorted(tam.items(), key=lambda x: -x[1])
                     if k != "ix_var_region")
ins_sin = R[M]['actualizaciones']['sin']['insert_5000_genotipos']['mediana_ms']
ins_con = R[M]['actualizaciones']['con']['insert_5000_genotipos']['mediana_ms']
w(r"""
\subsubsection*{Costo de los índices en las actualizaciones}

Cada índice hace más rápida la lectura pero más lenta la escritura, porque cada \texttt{INSERT} y cada
\texttt{UPDATE} que toca una columna indexada debe actualizar también el índice. Se compararon los tiempos sin
índices y con los índices finales:

\begin{figure}[H]
\centering
\includegraphics[width=0.85\textwidth]{fig/actualizaciones.png}
\caption{Costo de las actualizaciones sin índices y con los índices finales.}
\end{figure}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}llrrrr@{}}
\toprule
Operación & Índices & 1k & 10k & 100k & 1M \\
\midrule
""" + act_rows + r"""
\bottomrule
\end{tabular}
\caption{Tiempo de las actualizaciones (ms, mediana de 7). En 1k hay solo 76 anotaciones, por eso el UPDATE toca menos filas.}
\end{table}

Con los índices finales, insertar 5\,000 genotipos en 1M pasa de """ + ms(ins_sin) + " a " + ms(ins_con) + r""" ms. El
sobrecosto es pequeño porque la mayor parte del tiempo de esa inserción se va en verificar la llave primaria y
la llave foránea compuesta de cada fila, que existen con o sin los índices del experimento. En el \texttt{UPDATE} de
anotaciones la diferencia es casi nula: cambiar \texttt{significancia} solo obliga a mantener el índice parcial,
que es diminuto. El costo que sí crece es el espacio:

\begin{table}[H]
\centering\small
\begin{tabular}{@{}lr@{}}
\toprule
Índice & Tamaño en 1M (MB) \\
\midrule
""" + tam_rows + r"""
\midrule
Tabla \texttt{genotipo} sin índices (heap) & """ + f"{act['genotipo_heap']/1e6:.1f}" + r""" \\
Tabla \texttt{genotipo} con todos sus índices & """ + f"{act['genotipo_total']/1e6:.1f}" + r""" \\
\bottomrule
\end{tabular}
\caption{Tamaño de los índices finales con 1M de genotipos.}
\end{table}

Los dos índices cubrientes de \texttt{genotipo} ocupan, juntos, más que la propia tabla. En la carga semanal de
una corrida grande (millones de filas por \texttt{COPY}) conviene borrar esos índices antes de la carga y
recrearlos después: crearlos todos tomó """ + f"{act['t_crear_finales_ms']/1000:.1f}" + r""" s en 1M, menos que mantenerlos fila por fila.
""")

# ---------------------------------------------------------------------
w(r"""
\subsection{Análisis y discusión}

\begin{enumerate}
  \item \textbf{Con pocos datos los índices no importan.} En 1k y 10k todas las consultas tardan menos de
        10 ms con o sin índices: las tablas caben en pocas páginas y leerlas completas es tan rápido como usar un
        índice. Las diferencias aparecen desde 100k y se hacen claras en 1M.
  \item \textbf{El índice ayuda cuando la consulta es selectiva.} C1 (un donante), C5 (una región) y C6 (solo las
        muestras re-secuenciadas, cerca del 10\,\%) leen una fracción pequeña de \texttt{genotipo}, y ahí los
        índices dan entre 1.5 y 3 veces de mejora en 1M. C3 lee toda la tabla y ningún índice la salva.
  \item \textbf{Un índice puede empeorar una consulta.} En C2 el plan A hizo la consulta 25\,\% más lenta en 1M,
        porque el planificador prefirió muchos accesos aleatorios a la tabla en vez de una lectura secuencial en
        paralelo. Los índices cubrientes (\texttt{INCLUDE}) evitan ese problema porque no visitan la tabla.
  \item \textbf{Para agregaciones de toda la tabla, la solución es precalcular.} La vista materializada hace que C3
        sea """ + f"{t(M,'C3','sin')/mv[M]['mediana_ms']:.0f}" + r""" veces más rápida. Como los genotipos se cargan una vez por semana
        (Sección~1.5.4), basta con hacer \texttt{REFRESH MATERIALIZED VIEW} después de cada carga, lo que en 1M
        tomó """ + f"{mv[M]['t_refresh_ms']/1000:.1f}" + r""" s.
  \item \textbf{Las restricciones ya crean índices.} La llave primaria de \texttt{genotipo} sirve para C1 y el
        \texttt{UNIQUE} de la llave natural de \texttt{variante} hace innecesario el índice de región de C5. Antes de
        crear un índice hay que revisar si una restricción ya lo creó.
  \item \textbf{B-tree frente a hash.} En C5 dieron el mismo tiempo. El B-tree sirve también para rangos y para
        \texttt{ORDER BY}; el hash solo para igualdad. No hay motivo para usar hash en este caso.
  \item \textbf{Todas las consultas cumplen los tiempos esperados del Hito~1.} Con los índices finales y 1M de
        genotipos: C1 tarda """ + ms(t(M,'C1','B')) + r""" ms y C5 """ + ms(t(M,'C5','A')) + r""" ms (se pedía menos de 1 s); C2, C3 y C6 tardan
        menos de 1.5 s (se pedía menos de 10 s).
\end{enumerate}

\paragraph{Índices finales.} Con estos resultados quedan en la base de datos (\texttt{08\_indices.sql}):

\begin{lstlisting}[language=SQL]
""" + "\n".join(d + ";" for d in INDICES_FINALES) + r"""
\end{lstlisting}

\texttt{ix\_anot\_variante} se mantiene aunque C1 prefiere el índice parcial, porque \texttt{anotacion\_clinica.id\_variante}
es una llave foránea con \texttt{ON DELETE CASCADE} y las búsquedas de C7 piden todas las anotaciones de una variante.

\subsection{Pregunta adicional: ¿qué pasa con más de 1M de registros?}\label{sec:extra}

El Hito~1 estimó unos $10^8$ genotipos (6.5 GB sin índices) para los primeros años del CGA con exomas, y decenas de
miles de millones si se pasara a genomas completos. Según las mediciones:

\begin{itemize}
  \item Las consultas selectivas que usan índices (C1, C5) crecen mucho más lento que los datos: el B-tree
        tiene pocos niveles (crece con el logaritmo del número de filas), así que en $10^8$ filas seguirían en el
        orden de decenas o cientos de milisegundos.
  \item Las que leen toda la tabla (C3 y, en parte, C2 y C6) crecen en proporción a los datos: en las figuras su
        pendiente es cercana a 1. Pasar de $10^6$ a $10^8$ filas multiplicaría su tiempo por cerca de 100; C3 tardaría
        un par de minutos. Para ellas hacen falta vistas materializadas o tablas de resumen que se actualicen
        con cada carga.
  \item Al crecer, la tabla y sus índices dejan de caber en memoria y cada acceso aleatorio se vuelve una lectura
        de disco. Hay que subir \texttt{shared\_buffers} y \texttt{work\_mem} y usar discos SSD.
\end{itemize}

\textbf{¿Basta con la arquitectura cliente--servidor?} Para $10^8$ filas sí: un solo servidor PostgreSQL bien
configurado, con \textbf{particionamiento} de \texttt{genotipo} (por ejemplo por cromosoma o por rango de
\texttt{id\_corrida}) para que cada consulta solo lea las particiones que necesita, y con índices por partición.
Para decenas de miles de millones de filas (genomas completos) un solo servidor ya no alcanza ni en disco ni en
tiempo de carga, y hay que distribuir los datos: réplicas de solo lectura para repartir las consultas y
\textit{sharding} de \texttt{genotipo} por cromosoma o por donante entre varios nodos (por ejemplo con Citus, que
extiende PostgreSQL), o un almacén columnar para las agregaciones poblacionales como C3.

\section{Conclusiones}

\begin{itemize}
  \item Se implementó en PostgreSQL el modelo del Hito~1 con todas sus reglas semánticas: las que caben en una tabla
        como restricciones declarativas y las demás como nueve triggers, y se comprobó con 12 pruebas que se cumplen.
  \item Una llave foránea compuesta resolvió RS19 sin código, y un trigger diferido resolvió la especialización
        total, que no se puede expresar con un \texttt{CHECK}.
  \item Los índices no siempre ayudan: sirven cuando la consulta es selectiva y la tabla es grande (hasta 3 veces
        más rápido en C6 con 1M de filas), no sirven cuando la consulta lee toda la tabla (C3) y pueden empeorarla
        cuando obligan a muchos accesos aleatorios (C2, plan A).
  \item Para las agregaciones de toda la cohorte, una vista materializada refrescada después de cada carga
        semanal es mucho más efectiva que cualquier índice.
  \item El costo de mantener los índices finales en las actualizaciones fue bajo, pero ocupan más espacio que la
        propia tabla de hechos.
  \item Con 1M de genotipos todas las consultas cumplen los tiempos de respuesta esperados.
\end{itemize}

\section{Anexos}

\subsection{Video del experimento}

Video del experimento con 1M de registros, con y sin índices: \textbf{[enlace al video]}.

En el video se restaura \texttt{dumps/genvar\_1000000.dump}, se ejecutan las consultas de \texttt{07\_consultas.sql}
sin índices con \texttt{\textbackslash timing on}, se crean los índices con \texttt{08\_indices.sql} y se vuelven a
ejecutar las mismas consultas.

\subsection{MVP web}

Como punto extra se desarrolló una aplicación web en Python (Flask) conectada directamente a la base de datos
PostgreSQL (carpeta \texttt{web/}). Permite:

\begin{itemize}
  \item Ejecutar las consultas C1 a C8 con sus parámetros y ver el resultado, el tiempo, el SQL y el plan de ejecución.
        Las cinco consultas del experimento usan el mismo SQL de la Sección~5.1.2.
  \item Ver la ficha de un donante con sus muestras y su reporte clínico (\texttt{fn\_reporte\_clinico}).
  \item Registrar donantes y muestras, reclasificar anotaciones y revocar consentimientos con los procedimientos
        almacenados. Cuando una operación viola una regla, la aplicación muestra el error que lanza el trigger
        (por ejemplo, T3 al registrar una muestra de un donante sin consentimiento).
  \item Borrar y crear los índices finales y comparar los tiempos de las cinco consultas del experimento.
  \item Actuar como cada tipo de usuario (\texttt{SET ROLE}) para comprobar los permisos de la Sección~4.4.
\end{itemize}

Se ejecuta con \texttt{pip install -r web/requirements.txt} y \texttt{python web/app.py}, y se abre en
\texttt{http://localhost:5000}.

\begin{figure}[H]
\centering
\includegraphics[width=0.9\textwidth]{fig/web_consulta.png}
\caption{MVP web: ejecución de la consulta C1 con 1M de genotipos.}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=0.9\textwidth]{fig/web_indices.png}
\caption{MVP web: comparación de tiempos sin índices y con los índices finales.}
\end{figure}

\subsection{Archivos entregados}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}lp{9.5cm}@{}}
\toprule
Ruta & Contenido \\
\midrule
\texttt{sql/} & Scripts 01 a 09 (Sección 4 y 5) \\
\texttt{dumps/} & Los cuatro dumps: \texttt{genvar\_1000.dump}, \texttt{genvar\_10000.dump}, \texttt{genvar\_100000.dump}, \texttt{genvar\_1000000.dump} \\
\texttt{exp/consultas.py} & Consultas y planes de índices (fuente única) \\
\texttt{exp/experimento.py} & Script que genera los escenarios y mide los tiempos \\
\texttt{exp/resultados.json} & Todas las mediciones (las 7 repeticiones, planes usados y filas) \\
\texttt{exp/graficos.py} & Genera las figuras de la Sección 5.6 \\
\texttt{exp/salida\_pruebas.txt} & Salida de \texttt{09\_pruebas.sql} \\
\texttt{web/} & MVP web (Flask): \texttt{app.py}, plantillas y \texttt{LEEME.md} con las instrucciones \\
\bottomrule
\end{tabular}
\caption{Contenido del repositorio del proyecto.}
\end{table}

\subsection{Cómo reproducir el experimento}

\begin{lstlisting}[language=bash]
createdb genvar
for f in 01_esquema 02_vistas 03_procedimientos 04_triggers 05_roles; do
  psql -d genvar -f sql/$f.sql
done
pip install psycopg2-binary matplotlib
python3 exp/experimento.py --reps 7     # genera los 4 escenarios, los dumps y resultados.json
python3 exp/graficos.py                 # genera fig/*.png
psql -d genvar -f sql/08_indices.sql    # deja los índices finales
psql -d genvar -f sql/09_pruebas.sql    # pruebas de triggers y procedimientos
\end{lstlisting}
""")

todo = "".join(out)


def ajustar(texto):
    """Fuera de los listados: columnas p{} alineadas a la izquierda y cortes de línea
    permitidos después de cada _ dentro de \\texttt (evita líneas que se salen del margen)."""
    partes = re.split(r"(\\begin\{lstlisting\}.*?\\end\{lstlisting\})", texto, flags=re.S)
    for k in range(0, len(partes), 2):
        t = partes[k]
        t = re.sub(r"(?<!>\{\\raggedright\\arraybackslash\})p\{(\d+(?:\.\d+)?cm)\}",
                   r">{\\raggedright\\arraybackslash}p{\1}", t)
        t = re.sub(r"\\texttt\{([^{}]*)\}",
                   lambda m: "\\texttt{" + m.group(1).replace("\\_", "\\_\\allowbreak{}") + "}", t)
        partes[k] = t
    return "".join(partes)


todo = ajustar(todo)
i = todo.index("\\section{Anexos}")
open(os.path.join(AQUI, "hito2.tex"), "w").write(todo[:i])
open(os.path.join(AQUI, "anexos.tex"), "w").write(todo[i:])
print("hito2.tex listo:", sum(len(x) for x in out), "caracteres")
