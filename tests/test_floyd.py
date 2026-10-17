import random

from almacen.floyd import INF, floyd_warshall, reconstruir
from almacen.grafo import Grafo
from oraculo import dijkstra


def test_atajo_a_traves_de_un_nodo():
  g = Grafo()
  g.nodes(["a", "b", "c"])
  g.edge("a", "b", 1)
  g.edge("b", "c", 2)
  g.edge("a", "c", 10)
  dist, sig = floyd_warshall(g)
  assert dist[0][2] == 3 and dist[2][0] == 3
  assert [g.etiqueta(k) for k in reconstruir(sig, 0, 2)] == ["a", "b", "c"]
  assert dist[1][1] == 0 and reconstruir(sig, 1, 1) == [1]


def test_no_alcanzable():
  g = Grafo()
  g.nodes(["a", "b", "c"])
  g.edge("a", "b", 1)
  dist, sig = floyd_warshall(g)
  assert dist[0][2] == INF
  assert reconstruir(sig, 0, 2) == []


def test_dirigido_es_asimetrico():
  g = Grafo(dirigido=True)
  g.nodes([0, 1, 2])
  g.edge(0, 1, 1)
  g.edge(1, 2, 1)
  g.edge(2, 0, 5)
  dist, _ = floyd_warshall(g)
  assert dist[0][2] == 2 and dist[2][1] == 6 and dist[1][0] == 6


def test_aristas_de_peso_cero():
  g = Grafo()
  g.nodes(["a", "b", "c"])
  g.edge("a", "b", 0.0)
  g.edge("b", "c", 1.5)
  dist, _ = floyd_warshall(g)
  assert dist[0][2] == 1.5


def test_coincide_con_dijkstra_en_grafos_aleatorios():
  rnd = random.Random(7)
  for _ in range(5):
    n = 25
    g = Grafo()
    g.nodes(range(n))
    usadas = set()
    while len(usadas) < 45:                       # sin aristas repetidas
      u, v = sorted(rnd.sample(range(n), 2))
      if (u, v) not in usadas:
        usadas.add((u, v))
        g.edge(u, v, rnd.randint(1, 9))
    dist, sig = floyd_warshall(g)
    for s in range(n):
      ref = dijkstra(g, s)
      for t in range(n):
        assert dist[s][t] == ref.get(t, INF)
        if dist[s][t] < INF:
          ruta = reconstruir(sig, s, t)
          assert ruta[0] == s and ruta[-1] == t
          assert sum(g.peso(ruta[k], ruta[k + 1]) for k in range(len(ruta) - 1)) == dist[s][t]
