"""Une el LaTeX del Hito 1 con las secciones 4 a 7 del Hito 2 en un solo main.tex."""
import os
AQUI = os.path.dirname(os.path.abspath(__file__))
h1 = open(os.path.join(AQUI, "hito1_original.tex")).read()
h2 = open(os.path.join(AQUI, "..", "tex", "hito2.tex")).read()
anexos = open(os.path.join(AQUI, "..", "tex", "anexos.tex")).read()

PREAMBULO = r"""\usepackage[hidelinks]{hyperref}
\usepackage{listings}
\lstset{basicstyle=\ttfamily\footnotesize, breaklines=true, frame=single, columns=fullflexible,
  keywordstyle=\color{blue!60!black}\bfseries, commentstyle=\color{gray}, stringstyle=\color{teal!70!black},
  showstringspaces=false, upquote=true, captionpos=t,
  literate={á}{{\'a}}1 {é}{{\'e}}1 {í}{{\'i}}1 {ó}{{\'o}}1 {ú}{{\'u}}1 {ñ}{{\~n}}1
           {Á}{{\'A}}1 {É}{{\'E}}1 {Í}{{\'I}}1 {Ó}{{\'O}}1 {Ú}{{\'U}}1 {Ñ}{{\~N}}1 {·}{{$\cdot$}}1}
\renewcommand{\lstlistingname}{Listado}"""

cambios = [
    (r"\usepackage[hidelinks]{hyperref}", PREAMBULO),
    (r"{\LARGE\bfseries Proyecto Final -- Hito 1\par}", r"{\LARGE\bfseries Proyecto Final -- Hitos 1 y 2\par}"),
    (r"La implementación física en PostgreSQL, la carga masiva y la experimentación con índices corresponden al Hito~2.",
     r"La implementación física en PostgreSQL, la carga de datos y la experimentación con índices corresponden al Hito~2 y se presentan en las Secciones~\ref{sec:implementacion} y~\ref{sec:optimizacion}."),
    (r"\footnote{Organización ficticia creada para efectos del proyecto. Los datos de referencia sí provienen de fuentes públicas reales (ver Sección~\ref{sec:referencias}).}",
     r"\footnote{Organización ficticia creada para efectos del proyecto. La estructura de los datos sigue la de fuentes públicas reales (ver Sección~\ref{sec:referencias}).}"),
    (r"Para la experimentación del Hito~2 se generarán cuatro \emph{dumps}", r"Para la experimentación del Hito~2 se generaron cuatro \emph{dumps}"),
    (r"lo cual queda fuera del alcance del proyecto y se discutirá en la pregunta extra del Hito~2.",
     r"lo cual queda fuera del alcance del proyecto y se discute en la Sección~\ref{sec:extra}."),
    (r"De este conjunto se elegirán las 5 consultas intermedias no triviales para la experimentación con índices del Hito~2.",
     r"De este conjunto se eligieron las 5 consultas intermedias no triviales para la experimentación con índices del Hito~2 (Sección~\ref{sec:consultas})."),
    (r"Implementar el esquema en PostgreSQL, cargar datos reales y sintéticos, y crear",
     r"Implementar el esquema en PostgreSQL, cargar los datos y crear"),
    (r"Fuentes de datos reales que se usarán para poblar la base de datos:",
     r"Fuentes públicas que definen la estructura y los formatos del catálogo de referencia:"),
    (r"""Los donantes, muestras, laboratorios, secuenciadores, corridas y métricas de calidad se generarán sintéticamente con Python (\tb{Faker}, \tb{numpy}), respetando distribuciones plausibles, pues no existen datos públicos de ese tipo por razones de privacidad. Los genotipos de 1000 Genomas se reasignarán a donantes sintéticos y se completarán con genotipos simulados para alcanzar los volúmenes requeridos.""",
     r"""Los donantes, muestras, laboratorios, secuenciadores, corridas, métricas de calidad y genotipos no existen como datos públicos por razones de privacidad. En la implementación se simularon todos los datos con un script SQL reproducible que imita la forma de estas fuentes y respeta distribuciones plausibles; del mundo real se tomaron las longitudes de los cromosomas de GRCh38 (Sección~\ref{sec:simulacion})."""),
    (r"En el Hito~2 se implementará como columna generada o dentro de una vista.",
     r"Se implementó dentro de la vista \tb{v\_variante} (Sección~\ref{sec:vistas})."),
    (r"involucra otra tabla y se validará con un \emph{trigger} (Hito~2).",
     r"involucra otra tabla y se valida con el \emph{trigger} T1 (Sección~\ref{sec:triggers})."),
    (r"que el exón esté dentro del gen se valida con \emph{trigger}.",
     r"que el exón esté dentro del gen se valida con el \emph{trigger} T2."),
    (r"RS4 (consentimiento) y la cobertura total/disjunta de la jerarquía se implementarán con \emph{triggers}.",
     r"RS4 (consentimiento) y la cobertura total/disjunta de la jerarquía se implementaron con los \emph{triggers} T3, T4 y T5 (Sección~\ref{sec:triggers})."),
    (r"no se puede expresar solo con llaves; se garantizará con \emph{triggers} en el Hito~2.",
     r"no se puede expresar solo con llaves; se garantiza con los \emph{triggers} T4 y T5 (Sección~\ref{sec:triggers})."),
    (r"no es expresable con llaves foráneas; se controlará con un \emph{trigger} diferido o al cerrar la corrida.",
     r"no es expresable con llaves foráneas; se controla al cerrar la corrida con el \emph{trigger} T7."),
    (r"Los tipos indicados son los que se usarán en PostgreSQL.",
     r"Los tipos indicados son los que se usaron en PostgreSQL (Sección~\ref{sec:creacion})."),
    (r"tecnologia & VARCHAR(12) & NN, CHECK & LECTURA\_CORTA o LECTURA\_LARGA. \\",
     r"tecnologia & VARCHAR(14) & NN, CHECK & LECTURA\_CORTA o LECTURA\_LARGA. \\"),
]
for a, b in cambios:
    assert h1.count(a) == 1, a[:80]
    h1 = h1.replace(a, b)

h2 = h2.replace(r"\section{Implementación de la base de datos}", r"\section{Implementación de la base de datos}\label{sec:implementacion}", 1)
h2 = h2.replace(r"\section{Optimización y experimentación}", r"\section{Optimización y experimentación}\label{sec:optimizacion}", 1)
assert r"\label{sec:implementacion}" in h2 and r"\label{sec:optimizacion}" in h2

corte = h1.index("%=====================================================================\n\\begin{thebibliography}")
fin_bib = h1.index("\\end{thebibliography}") + len("\\end{thebibliography}")
cuerpo, bib = h1[:corte], h1[corte:fin_bib]
main = (cuerpo
        + "%=====================================================================\n% HITO 2\n"
        + h2 + "\n" + bib + "\n\n" + anexos + "\n\\end{document}\n")
open(os.path.join(AQUI, "main.tex"), "w").write(main)
print("main.tex:", len(main.splitlines()), "líneas")
