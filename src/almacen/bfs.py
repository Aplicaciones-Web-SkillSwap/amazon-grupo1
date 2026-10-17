"""Búsqueda en anchura (BFS) sobre Grafo, con el esquema visited/path visto en clase.

path[v] es el nodo desde el que se descubrió v (-1 para el origen y los no alcanzados).
Los índices son los de Grafo.Vertices; las funciones públicas reciben etiquetas.
"""
from collections import deque


def bfs(g, s):
  """BFS desde la etiqueta s. Devuelve (visited, path), listas indexadas por nodo."""
  origen = g.indice(s)
  visited = [False] * g.num_nodos()
  path = [-1] * g.num_nodos()
  visited[origen] = True
  cola = deque([origen])
  while cola:
    u = cola.popleft()
    for v, _ in g.G[u]:
      if not visited[v]:
        visited[v] = True
        path[v] = u
        cola.append(v)
  return visited, path


def camino(g, path, origen, destino):
  """Etiquetas del camino origen -> destino a partir de `path`, o [] si no es alcanzable.

  `path` debe venir de bfs(g, origen). Es un camino con el menor número de aristas."""
  o, v = g.indice(origen), g.indice(destino)
  ruta = [v]
  while v != o:
    if path[v] == -1:
      return []
    v = path[v]
    ruta.append(v)
  return [g.etiqueta(u) for u in reversed(ruta)]


def saltos(g, s):
  """Número mínimo de aristas desde s a cada nodo (-1 si no es alcanzable)."""
  origen = g.indice(s)
  dist = [-1] * g.num_nodos()
  dist[origen] = 0
  cola = deque([origen])
  while cola:
    u = cola.popleft()
    for v, _ in g.G[u]:
      if dist[v] == -1:
        dist[v] = dist[u] + 1
        cola.append(v)
  return dist


def componentes(g):
  """Componentes conexas (grafo no dirigido) como listas de etiquetas, de mayor a menor."""
  visto = [False] * g.num_nodos()
  grupos = []
  for u in range(g.num_nodos()):
    if visto[u]:
      continue
    visited, _ = bfs(g, g.etiqueta(u))
    grupo = [v for v in range(g.num_nodos()) if visited[v]]
    for v in grupo:
      visto[v] = True
    grupos.append([g.etiqueta(v) for v in grupo])
  return sorted(grupos, key=len, reverse=True)
