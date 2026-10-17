import random

import pytest

from almacen import ruteo

TECNICAS = [ruteo.fuerza_bruta, ruteo.backtracking, ruteo.held_karp]

# Matriz a mano: el óptimo es 13 (0-2-1-3-0) y el vecino más cercano da 15 (0-1-2-3-0).
M4 = [[0, 1, 5, 3],
      [1, 0, 1, 4],
      [5, 1, 0, 10],
      [3, 4, 10, 0]]


def matriz_aleatoria(n, semilla):
  """Distancias Manhattan entre el depot y n puntos al azar (métrica simétrica)."""
  rnd = random.Random(semilla)
  pts = [(0, 0)] + [(rnd.randint(0, 30), rnd.randint(0, 30)) for _ in range(n)]
  return [[abs(a[0] - b[0]) + abs(a[1] - b[1]) for b in pts] for a in pts]


def test_costo_ciclo():
  assert ruteo.costo_ciclo(M4, [1, 2, 3]) == 15
  assert ruteo.costo_ciclo(M4, [2, 1, 3]) == 13
  assert ruteo.costo_ciclo(M4, []) == 0


def test_voraz_a_mano():
  assert ruteo.voraz(M4) == (15, [1, 2, 3])


@pytest.mark.parametrize("tecnica", TECNICAS)
def test_optimo_a_mano(tecnica):
  costo, orden = tecnica(M4)
  assert costo == 13
  assert ruteo.costo_ciclo(M4, orden) == 13
  assert sorted(orden) == [1, 2, 3]


@pytest.mark.parametrize("tecnica", TECNICAS + [ruteo.voraz])
def test_pedidos_de_cero_y_un_producto(tecnica):
  assert tecnica([[0]]) == (0.0, [])
  assert tecnica([[0, 7], [7, 0]]) == (14, [1])


@pytest.mark.parametrize("n", [2, 3, 5, 7])
def test_las_tecnicas_exactas_coinciden(n):
  for semilla in range(4):
    m = matriz_aleatoria(n, semilla)
    resultados = [t(m) for t in TECNICAS]
    optimo = resultados[0][0]
    for costo, orden in resultados:
      assert costo == pytest.approx(optimo)
      assert sorted(orden) == list(range(1, n + 1))
      assert ruteo.costo_ciclo(m, orden) == pytest.approx(costo)


@pytest.mark.parametrize("n", [8, 9])
def test_backtracking_y_held_karp_coinciden_en_pedidos_mayores(n):
  m = matriz_aleatoria(n, 11)
  assert ruteo.backtracking(m)[0] == pytest.approx(ruteo.held_karp(m)[0])


def test_voraz_nunca_mejora_al_optimo():
  for semilla in range(10):
    m = matriz_aleatoria(7, semilla)
    costo, orden = ruteo.voraz(m)
    assert costo >= ruteo.held_karp(m)[0] - 1e-9
    assert sorted(orden) == list(range(1, 8))
    assert ruteo.costo_ciclo(m, orden) == pytest.approx(costo)
