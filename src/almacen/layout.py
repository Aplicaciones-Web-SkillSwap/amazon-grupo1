"""Layout del almacén (G2): almacén rectangular con pasillos verticales paralelos.

Hay un pasillo transversal al frente (y = 0) y otro al fondo. Cada pasillo vertical
tiene un cruce al frente (F{i}) y uno al fondo (R{i}); los productos se ubican a ambos
lados de la estantería (dos ubicaciones por metro). El depot, donde empieza y termina
cada recorrido, está en la esquina frontal izquierda.

Etiquetas de nodo: "depot", "F{i}", "R{i}" y el product_id (int) para cada ubicación.

TÉCNICA: GRAFOS - construcción de G2 (plano del almacén). Lo recorren bfs.py y distancias.py.
"""
from dataclasses import dataclass

from almacen import config
from almacen.grafo import Grafo


@dataclass
class Layout:
  grafo: Grafo
  pos: dict           # etiqueta -> (x, y) en metros
  tipo: dict          # etiqueta -> "depot" | "cruce" | "ubicacion"
  zona: dict          # etiqueta -> zona (None para el depot)
  pasillo: dict       # product_id -> índice del pasillo (0, 1, ...)
  n_pasillos: int
  y_fondo: float      # largo del pasillo: y del pasillo transversal del fondo


def largo_del_almacen(pasillos):
  """y del fondo para un conjunto de pasillos: (filas del pasillo más largo + 1) metros."""
  largo_max = max((len(p) + 1) // 2 for _, _, p in pasillos)
  return (largo_max + 1) * config.DIST_UBICACION


def construir_layout(pasillos, y_fondo=None):
  """Construye G2 a partir de la lista de pasillos [(zona, id, [product_id]), ...].

  y_fondo fija el largo de los pasillos; si es None se calcula con el pasillo más largo.
  Pasarlo explícito permite comparar dos distribuciones sobre el mismo almacén físico.
  """
  if y_fondo is None:
    y_fondo = largo_del_almacen(pasillos)
  d_ub, d_pas = config.DIST_UBICACION, config.DIST_PASILLO

  g = Grafo()
  pos, tipo, zonas, pasillo_de = {}, {}, {}, {}

  def agregar(etiqueta, t, xy, z):
    g.node(etiqueta)
    pos[etiqueta], tipo[etiqueta], zonas[etiqueta] = xy, t, z

  agregar("depot", "depot", (-d_pas, 0.0), None)
  frente_prev, fondo_prev, x_prev = "depot", None, -d_pas

  for i, (zona, _, prods) in enumerate(pasillos):
    x = i * d_pas
    frente, fondo = f"F{i}", f"R{i}"
    agregar(frente, "cruce", (x, 0.0), zona)
    agregar(fondo, "cruce", (x, y_fondo), zona)
    g.edge(frente_prev, frente, x - x_prev)          # pasillo transversal frontal
    if fondo_prev is not None:
      g.edge(fondo_prev, fondo, d_pas)               # pasillo transversal del fondo

    anterior, y_anterior = frente, 0.0
    for j, pid in enumerate(prods):
      y = (j // 2 + 1) * d_ub
      if y > y_fondo:
        raise ValueError(f"El pasillo {i} ({len(prods)} productos) no cabe en y_fondo={y_fondo}")
      agregar(pid, "ubicacion", (x, y), zona)
      pasillo_de[pid] = i
      if y != y_anterior:                            # nuevo punto a lo largo del pasillo
        g.edge(anterior, pid, y - y_anterior)
        anterior, y_anterior = pid, y
      else:                                          # mismo metro, lado opuesto
        g.edge(anterior, pid, 0.0)
    g.edge(anterior, fondo, y_fondo - y_anterior)

    frente_prev, fondo_prev, x_prev = frente, fondo, x

  return Layout(g, pos, tipo, zonas, pasillo_de, len(pasillos), y_fondo)
