"""Dibujos con matplotlib: mapa del almacén, ruta, grafo de afinidad y gráficos del
experimento. Solo usa Figure/Axes, así que funciona con cualquier backend (y sin tkinter)."""
import math

import networkx as nx
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch

from almacen import config

COLOR_RUTA = "#c62828"
COLOR_PASILLO = "#cfd8dc"
COLOR_RESALTE = "#fff176"

NOMBRE_LAYOUT = {
    "actual": "Actual (catálogo)",
    "optimizado": "Optimizado (UFDS + frecuencia)",
    "solo_frecuencia": "Solo frecuencia (control)",
    "aleatorio": "Aleatorio (control)",
}
COLOR_LAYOUT = {"actual": "#607d8b", "optimizado": "#6a1b9a",
                "solo_frecuencia": "#26a69a", "aleatorio": "#bdbdbd"}


def nombre_layout(clave):
  return NOMBRE_LAYOUT.get(clave, clave)


def leyenda_zonas():
  return [Patch(color=config.COLOR_ZONA[z], label=f"{z}: {config.NOMBRE_ZONA[z]}") for z in "ABC"]


# ------------------------------------------------------------------ almacén
def dibujar_almacen(ax, lo, info, orden=None, camino=None, marcar=None, resaltar=None,
                    titulo=""):
  """Plano del almacén (vista desde arriba, frente abajo, depot a la izquierda).

  orden: productos en el orden de visita (se numeran); camino: etiquetas de paso del
  recorrido; marcar: productos del pedido a señalar con un aro; resaltar: índice de
  pasillo a sombrear."""
  ax.clear()
  paso, y = config.DIST_PASILLO, lo.y_fondo
  x_max = (lo.n_pasillos - 1) * paso

  if resaltar is not None and 0 <= resaltar < lo.n_pasillos:
    ax.axvspan(resaltar * paso - 1.4, resaltar * paso + 1.4, color=COLOR_RESALTE, alpha=0.9,
               zorder=0)
  ax.plot([-paso, x_max], [0, 0], color=COLOR_PASILLO, lw=2.2, zorder=1)
  ax.plot([0, x_max], [y, y], color=COLOR_PASILLO, lw=2.2, zorder=1)
  for i in range(lo.n_pasillos):
    ax.plot([i * paso, i * paso], [0, y], color=COLOR_PASILLO, lw=1.4, zorder=1)

  for zona in "ABC":
    pts = [lo.pos[p] for p in lo.pasillo if info[p]["zona"] == zona]
    if pts:
      xs, ys = zip(*pts)
      ax.scatter(xs, ys, s=7, color=config.COLOR_ZONA[zona], zorder=3, linewidths=0)

  dx, dy = lo.pos["depot"]
  ax.scatter([dx], [dy], marker="s", s=70, color="#263238", zorder=6)
  ax.annotate("Depot", (dx, dy), xytext=(0, -13), textcoords="offset points", ha="center",
              fontsize=7, color="#263238")

  if marcar:
    xs, ys = zip(*[lo.pos[p] for p in marcar if p in lo.pos])
    ax.scatter(xs, ys, s=70, facecolors="none", edgecolors="#111111", linewidths=1.2, zorder=5)

  if camino:
    xs, ys = zip(*[lo.pos[e] for e in camino])
    ax.plot(xs, ys, color=COLOR_RUTA, lw=1.8, zorder=4, solid_joinstyle="round")
  if orden:
    for k, p in enumerate(orden, start=1):
      px, py = lo.pos[p]
      ax.scatter([px], [py], s=120, color=COLOR_RUTA, edgecolors="white", linewidths=0.8,
                 zorder=7)
      ax.text(px, py, str(k), color="white", fontsize=6.5, ha="center", va="center",
              fontweight="bold", zorder=8)

  ax.set_xlim(-8, x_max + 6)
  ax.set_ylim(-6, y + 14)
  ax.set_aspect("auto")
  ax.set_xlabel("metros (a lo ancho)", fontsize=8)
  ax.set_ylabel("metros (hacia el fondo)", fontsize=8)
  ax.tick_params(labelsize=7)
  ax.set_title(titulo, fontsize=9, loc="left")
  ax.legend(handles=leyenda_zonas(), loc="upper right", ncol=3, fontsize=7, frameon=True,
            borderaxespad=0.3)


def vista_completa(ax, lo):
  x_max = (lo.n_pasillos - 1) * config.DIST_PASILLO
  ax.set_xlim(-8, x_max + 6)
  ax.set_ylim(-6, lo.y_fondo + 14)


def vista_a_la_ruta(ax, lo, camino, margen=10.0):
  """Acerca la vista al recuadro que contiene el recorrido."""
  if not camino:
    return vista_completa(ax, lo)
  xs, ys = zip(*[lo.pos[e] for e in camino])
  ax.set_xlim(min(xs) - margen, max(xs) + margen)
  ax.set_ylim(min(ys) - margen, max(ys) + margen)


# ------------------------------------------------------------------ grafo G1
def calcular_posiciones_g1(g1, info, zona=None, top_k=config.TOP_K_DIBUJO):
  """Posiciones de los nodos de G1 (o de una zona) y las aristas que se dibujan: las
  `top_k` de mayor peso por nodo, como en el hito 1. Es lento (resorte): usar en un hilo."""
  nodos = [p for p in g1.Vertices if zona is None or info[p]["zona"] == zona]
  dentro = set(nodos)
  aristas = {}
  for u in nodos:
    vecinos = [(w, v) for v, w in g1.G[g1.indice(u)] if g1.etiqueta(v) in dentro]
    for w, v in sorted(vecinos, reverse=True)[:top_k]:
      v = g1.etiqueta(v)
      aristas[(min(u, v), max(u, v))] = w
  grafo = nx.Graph()
  grafo.add_nodes_from(nodos)
  grafo.add_weighted_edges_from((u, v, w) for (u, v), w in aristas.items())
  pos = nx.spring_layout(grafo, seed=config.SEMILLA, iterations=60, weight=None)
  return {"nodos": nodos, "aristas": aristas, "pos": pos, "zona": zona}


def dibujar_g1(ax, calculo, g1, info, titulo=""):
  ax.clear()
  pos, aristas = calculo["pos"], calculo["aristas"]
  if aristas:
    pesos = np.array(list(aristas.values()), dtype=float)
    seg = [(pos[u], pos[v]) for u, v in aristas]
    alfa = 0.12 + 0.5 * (pesos - pesos.min()) / max(pesos.max() - pesos.min(), 1)
    colores = [(0.3, 0.3, 0.3, a) for a in alfa]
    ax.add_collection(LineCollection(seg, colors=colores, linewidths=0.5, zorder=1))
  for zona in "ABC":
    nodos = [p for p in calculo["nodos"] if info[p]["zona"] == zona]
    if nodos:
      xs = [pos[p][0] for p in nodos]
      ys = [pos[p][1] for p in nodos]
      tam = [4 + 2.2 * math.sqrt(g1.grado(p)) for p in nodos]
      ax.scatter(xs, ys, s=tam, color=config.COLOR_ZONA[zona], zorder=2, linewidths=0)
  ax.autoscale_view()
  ax.set_xticks([])
  ax.set_yticks([])
  ax.set_title(titulo, fontsize=9, loc="left")
  ax.legend(handles=leyenda_zonas(), loc="lower right", fontsize=7, frameon=True)


# ------------------------------------------------------------------ experimento
def grafico_distancia_por_layout(ax, resumen):
  ax.clear()
  nombres = list(resumen["layout"])
  medias = list(resumen["media_m"])
  barras = ax.bar(range(len(nombres)), medias,
                  color=[COLOR_LAYOUT.get(n, "#90a4ae") for n in nombres])
  for b, m in zip(barras, medias):
    ax.text(b.get_x() + b.get_width() / 2, m, f"{m:.0f}", ha="center", va="bottom", fontsize=7)
  ax.set_xticks(range(len(nombres)))
  ax.set_xticklabels([nombre_layout(n).split(" (")[0] for n in nombres], fontsize=7)
  ax.set_ylabel("Distancia media por pedido (m)", fontsize=8)
  ax.set_title("Distancia media por layout", fontsize=9, loc="left")
  ax.tick_params(labelsize=7)


def grafico_distancia_por_tamano(ax, tamano):
  ax.clear()
  capas = [c for c in tamano.columns if c != "pedidos"]
  ancho = 0.8 / max(len(capas), 1)
  x = np.arange(len(tamano))
  for i, nombre in enumerate(capas):
    ax.bar(x + i * ancho - 0.4 + ancho / 2, tamano[nombre].fillna(0), ancho,
           color=COLOR_LAYOUT.get(nombre, "#90a4ae"), label=nombre_layout(nombre).split(" (")[0])
  ax.set_xticks(x)
  ax.set_xticklabels([f"{r}\n(n={int(n)})" for r, n in zip(tamano.index, tamano["pedidos"])],
                     fontsize=7)
  ax.set_ylabel("Distancia media (m)", fontsize=8)
  ax.set_xlabel("Productos por pedido", fontsize=8)
  ax.set_title("Distancia según el tamaño del pedido", fontsize=9, loc="left")
  ax.legend(fontsize=6.5, frameon=False)
  ax.tick_params(labelsize=7)


def grafico_tiempos(ax, tiempos):
  ax.clear()
  x = np.arange(len(tiempos))
  ancho = 0.38
  ax.bar(x - ancho / 2, tiempos["dp_ms"].fillna(0), ancho, color="#6a1b9a",
         label="Programación dinámica")
  ax.bar(x + ancho / 2, tiempos["voraz_ms"].fillna(0), ancho, color="#ffa726", label="Voraz")
  ax.set_yscale("symlog", linthresh=0.1)
  ax.set_xticks(x)
  ax.set_xticklabels(list(tiempos.index), fontsize=7)
  ax.set_ylabel("Tiempo medio (ms, escala log)", fontsize=8)
  ax.set_xlabel("Productos por pedido", fontsize=8)
  ax.set_title("Tiempo de ejecución por técnica", fontsize=9, loc="left")
  ax.legend(fontsize=7, frameon=False)
  ax.tick_params(labelsize=7)
