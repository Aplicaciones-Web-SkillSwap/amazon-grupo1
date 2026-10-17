import random

import pytest

from almacen.distancias import Distancias, grafo_reducido
from almacen.layout import construir_layout
from oraculo import dijkstra

PASILLOS = [("A", 1, [10, 11, 12]), ("B", 2, [20]), ("C", 3, [30, 31])]


@pytest.fixture(scope="module")
def pequeno():
  lo = construir_layout(PASILLOS)
  return lo, Distancias(lo)


def test_grafo_reducido(pequeno):
  lo, _ = pequeno
  red = grafo_reducido(lo)
  assert red.num_nodos() == 1 + 2 * 3                  # depot + F/R por pasillo
  assert red.num_aristas() == 1 + 2 + 2 + 3            # depot-F0, F's, R's, F-R por pasillo
  assert red.peso("F1", "R1") == lo.y_fondo
  assert red.peso("depot", "F0") == 3.0


def test_distancias_a_mano(pequeno):
  _, d = pequeno
  assert d.entre("depot", 10) == 4.0                   # 3 + 1
  assert d.entre("depot", 12) == 5.0                   # por el frente: 3 + 2
  assert d.entre(10, 12) == 1.0                        # mismo pasillo
  assert d.entre(10, 11) == 0.0                        # mismo metro, lado opuesto
  assert d.entre(10, 20) == 5.0                        # 1 + 3 + 1
  assert d.entre(12, 20) == 6.0                        # frente 2+3+1 = fondo 1+3+2
  assert d.entre(12, 30) == 9.0
  assert d.entre(20, 30) == 5.0
  assert d.entre("depot", 30) == 10.0
  assert d.entre(20, 20) == 0.0 and d.entre("depot", "depot") == 0.0


def test_matriz_simetrica_con_diagonal_cero(pequeno):
  _, d = pequeno
  puntos = ["depot", 10, 12, 20, 30, 31]
  m = d.matriz(puntos)
  for i in range(len(puntos)):
    assert m[i][i] == 0.0
    for j in range(len(puntos)):
      assert m[i][j] == m[j][i]
  assert m[0][1] == 4.0 and m[1][3] == 5.0


def sumar_tramos(lo, ruta):
  """Largo de un recorrido que solo avanza en vertical u horizontal."""
  total = 0.0
  for a, b in zip(ruta, ruta[1:]):
    (xa, ya), (xb, yb) = lo.pos[a], lo.pos[b]
    assert xa == xb or ya == yb                        # nunca en diagonal
    total += abs(xa - xb) + abs(ya - yb)
  return total


def test_camino_mide_lo_mismo_que_la_distancia(pequeno):
  lo, d = pequeno
  puntos = ["depot", 10, 11, 12, 20, 30, 31]
  for a in puntos:
    for b in puntos:
      ruta = d.camino(a, b)
      assert ruta[0] == a and ruta[-1] == b
      assert sumar_tramos(lo, ruta) == pytest.approx(d.entre(a, b))


def almacen_aleatorio(semilla, n_pasillos=8):
  rnd = random.Random(semilla)
  pasillos, pid = [], 1
  for i in range(n_pasillos):
    largo = rnd.randint(1, 14)
    pasillos.append(("A", i, list(range(pid, pid + largo))))
    pid += largo
  return pasillos


@pytest.mark.parametrize("semilla", [1, 2, 3])
def test_coincide_con_dijkstra_sobre_g2_completo(semilla):
  """Valida el atajo de grafo reducido contra Dijkstra sobre todas las ubicaciones."""
  lo = construir_layout(almacen_aleatorio(semilla))
  d = Distancias(lo)
  puntos = ["depot"] + [e for e in lo.grafo.Vertices if lo.tipo[e] == "ubicacion"]
  for a in puntos:
    ref = dijkstra(lo.grafo, a)
    for b in puntos:
      assert d.entre(a, b) == pytest.approx(ref[lo.grafo.indice(b)])
