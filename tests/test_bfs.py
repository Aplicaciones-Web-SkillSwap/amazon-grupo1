from almacen import bfs
from almacen.grafo import Grafo


def grafo_ejemplo():
  # a-b-c-d en línea, a-e atajo largo a d (a-e-f-d), g solo, h-i aparte
  g = Grafo()
  g.nodes(list("abcdefghi"))
  for u, v in [("a", "b"), ("b", "c"), ("c", "d"), ("a", "e"), ("e", "f"), ("f", "d"), ("h", "i")]:
    g.edge(u, v)
  return g


def test_bfs_visita_solo_la_componente():
  g = grafo_ejemplo()
  visited, path = bfs.bfs(g, "a")
  assert [g.etiqueta(i) for i, v in enumerate(visited) if v] == list("abcdef")
  assert path[g.indice("a")] == -1
  assert path[g.indice("b")] == g.indice("a")


def test_camino_con_menos_aristas():
  g = grafo_ejemplo()
  _, path = bfs.bfs(g, "a")
  assert bfs.camino(g, path, "a", "d") in (list("abcd"), list("aefd"))
  assert len(bfs.camino(g, path, "a", "d")) == 4
  assert bfs.camino(g, path, "a", "a") == ["a"]
  assert bfs.camino(g, path, "a", "h") == []


def test_saltos():
  g = grafo_ejemplo()
  d = bfs.saltos(g, "a")
  assert d[g.indice("d")] == 3 and d[g.indice("f")] == 2
  assert d[g.indice("g")] == -1 and d[g.indice("a")] == 0


def test_componentes():
  grupos = bfs.componentes(grafo_ejemplo())
  assert [len(x) for x in grupos] == [6, 2, 1]
  assert sorted(grupos[0]) == list("abcdef")


def test_bfs_en_grafo_dirigido():
  g = Grafo(dirigido=True)
  g.nodes([1, 2, 3])
  g.edge(1, 2)
  g.edge(3, 1)
  visited, _ = bfs.bfs(g, 1)
  assert visited == [True, True, False]
