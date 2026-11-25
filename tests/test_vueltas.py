"""Vueltas del carrito: corte de la ruta por capacidad en kg (ruteo.dividir_en_vueltas)."""
import random
from itertools import combinations

import pytest

from almacen import ruteo
from almacen.servicio import ACTUAL, Servicio


@pytest.fixture
def servicio(carpeta_datos):
  # capacidad 2 para que los pasillos optimizados quepan en el almacén de juguete
  return Servicio.desde_csv(carpeta_datos, por_zona=2, umbral=2, capacidad=2, fraccion_prueba=0)


# El pedido [1, 2, 4] del mini dataset pesa 0.12 + 0.20 + 1.90 = 2.22 kg,
# así que un carrito de 2 kg obliga a dar dos vueltas.
CARRITO_CHICO = 2.0


def matriz_aleatoria(n, rnd):
  """Matriz de distancias euclidianas: el punto 0 es el depot."""
  pts = [(rnd.uniform(0, 60), rnd.uniform(0, 60)) for _ in range(n + 1)]
  return [[((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in pts] for a in pts]


def cortes_por_fuerza_bruta(m, orden, pesos, capacidad):
  """Prueba TODAS las formas de cortar `orden` en tramos seguidos y devuelve la menor
  distancia total. Solo para pedidos chicos: hay 2^(n-1) cortes posibles."""
  n = len(orden)
  mejor = float("inf")
  for k in range(n):                                   # cantidad de cortes interiores
    for puntos in combinations(range(1, n), k):
      limites = [0] + list(puntos) + [n]
      vueltas = [orden[a:b] for a, b in zip(limites, limites[1:])]
      if any(sum(pesos[i] for i in v) > capacidad for v in vueltas):
        continue
      mejor = min(mejor, sum(ruteo.costo_ciclo(m, v) for v in vueltas))
  return mejor


# --------------------------------------------------------------------------------------
# dividir_en_vueltas
# --------------------------------------------------------------------------------------
def test_pedido_liviano_queda_en_una_sola_vuelta():
  m = matriz_aleatoria(6, random.Random(1))
  orden = [1, 2, 3, 4, 5, 6]
  pesos = [0.0] + [1.0] * 6
  costo, vueltas = ruteo.dividir_en_vueltas(m, orden, pesos, capacidad=100)
  assert vueltas == [orden]
  assert costo == pytest.approx(ruteo.costo_ciclo(m, orden))


def test_vacio():
  assert ruteo.dividir_en_vueltas([[0.0]], [], [0.0], capacidad=10) == (0.0, [])


def test_ninguna_vuelta_pasa_la_capacidad():
  rnd = random.Random(7)
  for _ in range(40):
    n = rnd.randint(1, 12)
    m = matriz_aleatoria(n, rnd)
    orden = list(range(1, n + 1))
    rnd.shuffle(orden)
    pesos = [0.0] + [round(rnd.uniform(0.1, 3.0), 2) for _ in range(n)]
    capacidad = max(pesos[1:]) + rnd.uniform(0, 4)
    _, vueltas = ruteo.dividir_en_vueltas(m, orden, pesos, capacidad)
    for vuelta in vueltas:
      assert ruteo.peso_total(vuelta, pesos) <= capacidad + 1e-9


def test_las_vueltas_conservan_el_orden_y_los_productos():
  rnd = random.Random(11)
  n = 10
  m = matriz_aleatoria(n, rnd)
  orden = list(range(1, n + 1))
  rnd.shuffle(orden)
  pesos = [0.0] + [1.0] * n
  _, vueltas = ruteo.dividir_en_vueltas(m, orden, pesos, capacidad=3)
  assert [i for v in vueltas for i in v] == orden      # mismo orden, sin perder ni repetir


def test_la_suma_de_las_vueltas_es_la_distancia_total():
  rnd = random.Random(13)
  for _ in range(30):
    n = rnd.randint(1, 10)
    m = matriz_aleatoria(n, rnd)
    orden = list(range(1, n + 1))
    rnd.shuffle(orden)
    pesos = [0.0] + [round(rnd.uniform(0.5, 2.0), 2) for _ in range(n)]
    capacidad = max(pesos[1:]) + rnd.uniform(0, 3)
    costo, vueltas = ruteo.dividir_en_vueltas(m, orden, pesos, capacidad)
    assert costo == pytest.approx(sum(ruteo.costo_ciclo(m, v) for v in vueltas))


def test_coincide_con_la_fuerza_bruta_en_pedidos_chicos():
  rnd = random.Random(17)
  for _ in range(60):
    n = rnd.randint(1, 8)
    m = matriz_aleatoria(n, rnd)
    orden = list(range(1, n + 1))
    rnd.shuffle(orden)
    pesos = [0.0] + [round(rnd.uniform(0.5, 2.5), 2) for _ in range(n)]
    capacidad = max(pesos[1:]) + rnd.uniform(0, 3)
    costo, _ = ruteo.dividir_en_vueltas(m, orden, pesos, capacidad)
    assert costo == pytest.approx(cortes_por_fuerza_bruta(m, orden, pesos, capacidad))


def test_producto_mas_pesado_que_el_carrito_da_error_claro():
  m = matriz_aleatoria(2, random.Random(3))
  with pytest.raises(ValueError, match="no se puede recoger"):
    ruteo.dividir_en_vueltas(m, [1, 2], [0.0, 1.0, 9.0], capacidad=5)


def test_bajar_la_capacidad_nunca_acorta_la_ruta():
  rnd = random.Random(23)
  m = matriz_aleatoria(9, rnd)
  orden = list(range(1, 10))
  pesos = [0.0] + [1.0] * 9
  costos = [ruteo.dividir_en_vueltas(m, orden, pesos, k)[0] for k in range(9, 0, -1)]
  assert costos == sorted(costos)                      # a menor capacidad, más metros


# --------------------------------------------------------------------------------------
# integración con el servicio
# --------------------------------------------------------------------------------------
def test_servicio_devuelve_una_vuelta_con_la_capacidad_por_defecto(servicio):
  r = servicio.rutear([1, 2, 4], ACTUAL)
  assert len(r.vueltas) == 1
  assert r.costo_total == pytest.approx(r.costo)
  assert r.vueltas[0]["productos"] == r.orden
  assert r.vueltas[0]["kg"] == pytest.approx(servicio.peso_pedido([1, 2, 4]))


def test_servicio_parte_el_pedido_cuando_el_carrito_es_chico(servicio):
  r = servicio.rutear([1, 2, 4], ACTUAL, capacidad_kg=CARRITO_CHICO)
  assert len(r.vueltas) > 1
  assert all(v["kg"] <= CARRITO_CHICO + 1e-9 for v in r.vueltas)
  assert [p for v in r.vueltas for p in v["productos"]] == r.orden
  assert r.costo_total == pytest.approx(sum(v["metros"] for v in r.vueltas))
  assert r.costo_total >= r.costo


def test_el_camino_pasa_por_el_depot_entre_vueltas(servicio):
  r = servicio.rutear([1, 2, 4], ACTUAL, capacidad_kg=CARRITO_CHICO)
  assert r.camino[0] == "depot" and r.camino[-1] == "depot"
  assert r.camino.count("depot") == len(r.vueltas) + 1


def test_los_tramos_indican_su_vuelta(servicio):
  r = servicio.rutear([1, 2, 4], ACTUAL, capacidad_kg=CARRITO_CHICO)
  tramos = servicio.tramos(r)
  assert {t["vuelta"] for t in tramos} == set(range(1, len(r.vueltas) + 1))
  assert tramos[-1]["acumulado"] == pytest.approx(r.costo_total)
