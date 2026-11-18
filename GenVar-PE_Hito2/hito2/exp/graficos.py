"""Genera las figuras de la Sección 5.6 a partir de resultados.json."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

AQUI = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(AQUI, "..", "fig")
os.makedirs(FIG, exist_ok=True)
R = json.load(open(os.path.join(AQUI, "resultados.json")))
NS = sorted(R, key=int)
X = [int(n) for n in NS]
ETQ = {1000: "1k", 10000: "10k", 100000: "100k", 1000000: "1M"}

TINTA, TINTA2, GRILLA = "#0b0b0b", "#52514e", "#e4e3df"
SERIES = {"sin": ("Sin índices", "#2a78d6", "o"),
          "A":   ("Plan A",      "#eb6834", "s"),
          "B":   ("Plan B",      "#1baf7a", "^"),
          "MV":  ("Vista materializada", "#eda100", "D")}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": TINTA2,
                     "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
                     "axes.spines.top": False, "axes.spines.right": False})
fmt_ms = FuncFormatter(lambda v, _: f"{v:g}")


def ejes(ax, titulo):
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(X); ax.set_xticklabels([ETQ[x] for x in X])
    ax.minorticks_off()
    ax.yaxis.set_major_formatter(fmt_ms)
    ax.grid(True, which="major", color=GRILLA, linewidth=0.8); ax.set_axisbelow(True)
    ax.set_title(titulo, loc="left", color=TINTA, fontsize=10, fontweight="bold")
    ax.set_xlabel("filas en GENOTIPO"); ax.set_ylabel("tiempo de ejecución (ms, mediana)")


def linea(ax, k, ys, etiqueta_final=True):
    nombre, color, m = SERIES[k]
    ax.plot(X, ys, color=color, linewidth=2, marker=m, markersize=6,
            markeredgecolor="white", markeredgewidth=1.2, label=nombre, zorder=3)


for q in R[NS[0]]["consultas"]:
    fig, ax = plt.subplots(figsize=(5.6, 3.6), dpi=200)
    for k in ("sin", "A", "B"):
        linea(ax, k, [R[n]["consultas"][q][k]["mediana_ms"] for n in NS])
    if q == "C3":
        linea(ax, "MV", [R[n]["c3_vista_materializada"]["mediana_ms"] for n in NS])
    ejes(ax, f"{q}: tiempo por escala")
    ax.legend(frameon=False, loc="upper left", labelcolor=TINTA)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, f"{q}.png")); plt.close(fig)

# Aceleración en 1M (sin / con) por consulta y plan
fig, ax = plt.subplots(figsize=(5.6, 3.0), dpi=200)
qs = list(R[NS[-1]]["consultas"])
w = 0.36
for i, k in enumerate(("A", "B")):
    vals = [R[NS[-1]]["consultas"][q]["sin"]["mediana_ms"] / R[NS[-1]]["consultas"][q][k]["mediana_ms"] for q in qs]
    xs = [j + (i - 0.5) * (w + 0.03) for j in range(len(qs))]
    ax.bar(xs, vals, width=w, color=SERIES[k][1], label=SERIES[k][0], zorder=3)
    for x_, v in zip(xs, vals):
        ax.text(x_, v + 0.05, f"{v:.1f}×", ha="center", va="bottom", fontsize=7.5, color=TINTA)
ax.axhline(1, color=TINTA2, linewidth=1, linestyle="--", zorder=2)
ax.set_xticks(range(len(qs))); ax.set_xticklabels(qs)
ax.set_ylabel("aceleración (sin ÷ con)\n1 = igual que sin índices")
ax.grid(True, axis="y", color=GRILLA); ax.set_axisbelow(True)
ax.set_title("Aceleración de cada plan con 1M filas", loc="left", color=TINTA, fontsize=10, fontweight="bold")
ax.legend(frameon=False, loc="upper left", labelcolor=TINTA)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "aceleracion_1M.png")); plt.close(fig)

# Costo de las actualizaciones: sin índices vs con los índices finales
fig, axs = plt.subplots(1, 2, figsize=(6.4, 3.2), dpi=200)
for ax, (op, tit) in zip(axs, (("insert_5000_genotipos", "INSERT de 5 000 genotipos"),
                               ("update_1000_anotaciones", "UPDATE de 1 000 anotaciones"))):
    for i, (k, nom, col) in enumerate((("sin", "Sin índices", "#2a78d6"),
                                       ("con", "Con índices finales", "#eb6834"))):
        vals = [R[n]["actualizaciones"][k][op]["mediana_ms"] for n in NS]
        xs = [j + (i - 0.5) * 0.39 for j in range(len(NS))]
        ax.bar(xs, vals, width=0.36, color=col, label=nom, zorder=3)
    ax.set_xticks(range(len(NS))); ax.set_xticklabels([ETQ[x] for x in X])
    ax.set_xlabel("filas en GENOTIPO"); ax.set_ylabel("ms (mediana)")
    ax.grid(True, axis="y", color=GRILLA); ax.set_axisbelow(True)
    ax.set_title(tit, loc="left", color=TINTA, fontsize=9.5, fontweight="bold")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, loc="upper center", ncol=2, labelcolor=TINTA, fontsize=8.5)
fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(os.path.join(FIG, "actualizaciones.png")); plt.close(fig)
print("figuras en", os.path.abspath(FIG))
