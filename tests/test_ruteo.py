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


# ------------------------- Held-Karp optimizado y selección -------------------------
@pytest.mark.parametrize("poda", [True, False])
def test_held_karp_opt_a_mano(poda):
  costo, orden = ruteo.held_karp_opt(M4, poda=poda)
  assert costo == 13 and ruteo.costo_ciclo(M4, orden) == 13
  assert sorted(orden) == [1, 2, 3]


@pytest.mark.parametrize("poda", [True, False])
def test_held_karp_opt_casos_borde(poda):
  assert ruteo.held_karp_opt([[0]], poda=poda) == (0.0, [])
  assert ruteo.held_karp_opt([[0, 7], [7, 0]], poda=poda) == (14, [1])


@pytest.mark.parametrize("poda", [True, False])
@pytest.mark.parametrize("n", [2, 4, 6, 8, 10, 12])
def test_held_karp_opt_coincide_con_la_version_base(n, poda):
  for semilla in range(5):
    m = matriz_aleatoria(n, semilla)
    costo, orden = ruteo.held_karp_opt(m, poda=poda)
    assert costo == pytest.approx(ruteo.held_karp(m)[0])
    assert sorted(orden) == list(range(1, n + 1))
    assert ruteo.costo_ciclo(m, orden) == pytest.approx(costo)


def test_la_poda_no_cambia_el_optimo():
  for semilla in range(30):
    m = matriz_aleatoria(9, 100 + semilla)
    assert ruteo.held_karp_opt(m, poda=True)[0] == pytest.approx(
        ruteo.held_karp_opt(m, poda=False)[0])


def test_held_karp_opt_con_matriz_no_metrica():
  rnd = random.Random(5)
  for _ in range(10):
    n = 6
    m = [[0 if i == j else rnd.randint(1, 20) for j in range(n + 1)] for i in range(n + 1)]
    assert ruteo.held_karp_opt(m)[0] == pytest.approx(ruteo.held_karp(m)[0])


def test_held_karp_opt_rechaza_pedidos_demasiado_grandes():
  m = [[0] * 24 for _ in range(24)]
  with pytest.raises(ValueError):
    ruteo.held_karp_opt(m)


def test_elegir_tecnica():
  assert ruteo.elegir_tecnica(10, umbral_fb=10, umbral_dp=15) == "exacta_verificada"
  assert ruteo.elegir_tecnica(11, umbral_fb=10, umbral_dp=15) == "dp"
  assert ruteo.elegir_tecnica(15, umbral_fb=10, umbral_dp=15) == "dp"
  assert ruteo.elegir_tecnica(16, umbral_fb=10, umbral_dp=15) == "voraz"


def test_resolver_segun_el_tamano():
  m = matriz_aleatoria(6, 3)
  exacto = ruteo.held_karp(m)[0]
  costo, _, tecnica = ruteo.resolver(m, umbral_fb=6, umbral_dp=8)
  assert tecnica == "exacta_verificada" and costo == pytest.approx(exacto)
  costo, _, tecnica = ruteo.resolver(m, umbral_fb=4, umbral_dp=8)
  assert tecnica == "dp" and costo == pytest.approx(exacto)
  costo, orden, tecnica = ruteo.resolver(m, umbral_fb=2, umbral_dp=4)
  assert tecnica == "voraz" and costo == pytest.approx(ruteo.voraz(m)[0])
