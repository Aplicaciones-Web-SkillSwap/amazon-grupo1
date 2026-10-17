"""Dijkstra simple, independiente de Floyd-Warshall, para validar distancias en los tests."""
import heapq


def dijkstra(g, origen):
  """Distancias (por índice de nodo) desde la etiqueta `origen`."""
  dist = {g.indice(origen): 0.0}
  cola = [(0.0, g.indice(origen))]
  while cola:
    d, u = heapq.heappop(cola)
    if d > dist.get(u, float("inf")):
      continue
    for v, peso in g.G[u]:
      nd = d + peso
      if nd < dist.get(v, float("inf")):
        dist[v] = nd
        heapq.heappush(cola, (nd, v))
  return dist
