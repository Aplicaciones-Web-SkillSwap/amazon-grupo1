"""Floyd-Warshall: distancias mínimas entre todos los pares de nodos. O(V^3).

Se aplica al grafo reducido del almacén (depot + cruces de pasillo), no a las 1,697
ubicaciones: V^3 con V = 197 son ~7.6 millones de pasos, mientras que con 1,697
serían ~4.9 mil millones.
"""
INF = float("inf")


def floyd_warshall(g):
  """Devuelve (dist, sig) para un Grafo (dirigido o no).

  dist[i][j] es la distancia mínima de i a j (INF si no hay camino). sig[i][j] es el
  siguiente nodo después de i en un camino mínimo hacia j (-1 si no hay camino).
  """
  n = g.num_nodos()
  dist = [[INF] * n for _ in range(n)]
  sig = [[-1] * n for _ in range(n)]
  for u in range(n):
    dist[u][u] = 0.0
    sig[u][u] = u
    for v, peso in g.G[u]:
      if peso < dist[u][v]:
        dist[u][v] = peso
        sig[u][v] = v

  for k in range(n):
    dk = dist[k]
    for i in range(n):
      dik = dist[i][k]
      if dik == INF:
        continue
      di, si, sik = dist[i], sig[i], sig[i][k]
      for j in range(n):
        nueva = dik + dk[j]
        if nueva < di[j]:
          di[j] = nueva
          si[j] = sik
  return dist, sig


def reconstruir(sig, i, j):
  """Índices del camino mínimo i -> j usando la matriz `sig`, o [] si no hay camino."""
  if sig[i][j] == -1:
    return []
  ruta = [i]
  while i != j:
    i = sig[i][j]
    ruta.append(i)
  return ruta
