"""Distancias entre ubicaciones del almacén.

Un producto solo se puede dejar por los dos extremos de su pasillo, así que la distancia
entre dos productos de pasillos distintos es
    min sobre (salida de a, entrada de b) de  d(a, salida) + D(salida, entrada) + d(entrada, b)
donde D sale de Floyd-Warshall sobre el grafo reducido (depot + cruces F{i}/R{i}, con una
arista F{i}-R{i} por pasillo de largo y_fondo). Dentro de un mismo pasillo la distancia es
|Δy|. Así se evitan los 1,697 nodos de G2 y Floyd-Warshall corre sobre solo 197.
"""
from almacen.floyd import INF, floyd_warshall, reconstruir
from almacen.grafo import Grafo


def grafo_reducido(layout):
  """Grafo con el depot y los cruces de G2, más una arista F{i}-R{i} por pasillo."""
  g = layout.grafo
  red = Grafo()
  for etiqueta in g.Vertices:
    if layout.tipo[etiqueta] != "ubicacion":
      red.node(etiqueta)
  for u, ady in enumerate(g.G):
    a = g.etiqueta(u)
    if layout.tipo[a] == "ubicacion":
      continue
    for v, peso in ady:
      b = g.etiqueta(v)
      if layout.tipo[b] != "ubicacion" and u < v:
        red.edge(a, b, peso)
  for i in range(layout.n_pasillos):
    red.edge(f"F{i}", f"R{i}", layout.y_fondo)
  return red


class Distancias:
  def __init__(self, layout):
    self.layout = layout
    self.red = grafo_reducido(layout)
    self.dist, self.sig = floyd_warshall(self.red)

  def _salidas(self, punto):
    """[(nodo del grafo reducido, costo para llegar a él)] desde un punto del almacén."""
    if punto == "depot":
      return [("depot", 0.0)]
    i = self.layout.pasillo[punto]
    y = self.layout.pos[punto][1]
    return [(f"F{i}", y), (f"R{i}", self.layout.y_fondo - y)]

  def _mejor(self, a, b):
    """(distancia, salida de a, entrada de b) con el menor costo entre pasillos distintos."""
    mejor = (INF, None, None)
    for u, cu in self._salidas(a):
      iu = self.red.indice(u)
      for v, cv in self._salidas(b):
        total = cu + self.dist[iu][self.red.indice(v)] + cv
        if total < mejor[0]:
          mejor = (total, u, v)
    return mejor

  def _mismo_pasillo(self, a, b):
    lo = self.layout
    return (a != "depot" and b != "depot" and lo.pasillo[a] == lo.pasillo[b])

  def entre(self, a, b):
    """Distancia mínima en metros entre dos puntos ("depot" o product_id)."""
    if a == b:
      return 0.0
    if self._mismo_pasillo(a, b):
      return abs(self.layout.pos[a][1] - self.layout.pos[b][1])
    return self._mejor(a, b)[0]

  def matriz(self, puntos):
    """Matriz simétrica de distancias entre los puntos dados, en el mismo orden."""
    n = len(puntos)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
      for j in range(i + 1, n):
        m[i][j] = m[j][i] = self.entre(puntos[i], puntos[j])
    return m

  def camino(self, a, b):
    """Puntos de paso (etiquetas) de un recorrido mínimo a -> b, para dibujarlo."""
    if a == b:
      return [a]
    if self._mismo_pasillo(a, b):
      return [a, b]
    _, u, v = self._mejor(a, b)
    medio = [self.red.etiqueta(k)
             for k in reconstruir(self.sig, self.red.indice(u), self.red.indice(v))]
    ruta = [a] + medio + [b]
    return [p for k, p in enumerate(ruta) if k == 0 or p != ruta[k - 1]]
