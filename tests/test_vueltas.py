"""Vueltas del carrito (ruteo.dividir_en_vueltas) y stock del almacén."""
import random
from itertools import combinations

import pytest

from almacen import config, datos, ruteo
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
# tope de unidades
# --------------------------------------------------------------------------------------
def test_sin_tope_de_unidades_es_igual_que_antes():
  m = matriz_aleatoria(7, random.Random(31))
  orden = [1, 2, 3, 4, 5, 6, 7]
  pesos = [0.0] + [1.0] * 7
  assert (ruteo.dividir_en_vueltas(m, orden, pesos, 3)
          == ruteo.dividir_en_vueltas(m, orden, pesos, 3, max_unidades=None))


def test_ninguna_vuelta_pasa_el_tope_de_unidades():
  rnd = random.Random(37)
  for _ in range(40):
    n = rnd.randint(1, 12)
    m = matriz_aleatoria(n, rnd)
    orden = list(range(1, n + 1))
    rnd.shuffle(orden)
    pesos = [0.0] + [1.0] * n
    tope = rnd.randint(1, 5)
    _, vueltas = ruteo.dividir_en_vueltas(m, orden, pesos, float("inf"), tope)
    assert all(len(v) <= tope for v in vueltas)
    assert [i for v in vueltas for i in v] == orden


def test_tope_de_una_unidad_obliga_a_una_vuelta_por_producto():
  m = matriz_aleatoria(5, random.Random(41))
  orden = [1, 2, 3, 4, 5]
  pesos = [0.0] + [1.0] * 5
  costo, vueltas = ruteo.dividir_en_vueltas(m, orden, pesos, float("inf"), 1)
  assert vueltas == [[1], [2], [3], [4], [5]]
  assert costo == pytest.approx(sum(m[0][i] + m[i][0] for i in orden))


def test_los_dos_topes_a_la_vez_se_respetan():
  rnd = random.Random(43)
  for _ in range(30):
    n = rnd.randint(1, 10)
    m = matriz_aleatoria(n, rnd)
    orden = list(range(1, n + 1))
    rnd.shuffle(orden)
    pesos = [0.0] + [round(rnd.uniform(0.5, 2.0), 2) for _ in range(n)]
    capacidad = max(pesos[1:]) + rnd.uniform(0, 3)
    tope = rnd.randint(1, 4)
    costo, vueltas = ruteo.dividir_en_vueltas(m, orden, pesos, capacidad, tope)
    for v in vueltas:
      assert len(v) <= tope
      assert ruteo.peso_total(v, pesos) <= capacidad + 1e-9
    assert costo == pytest.approx(sum(ruteo.costo_ciclo(m, v) for v in vueltas))


def test_tope_de_unidades_coincide_con_la_fuerza_bruta():
  rnd = random.Random(47)
  for _ in range(40):
    n = rnd.randint(1, 8)
    m = matriz_aleatoria(n, rnd)
    orden = list(range(1, n + 1))
    rnd.shuffle(orden)
    pesos = [0.0] + [1.0] * n                  # peso 1 por producto: capacidad = unidades
    tope = rnd.randint(1, 4)
    costo, _ = ruteo.dividir_en_vueltas(m, orden, pesos, float("inf"), tope)
    assert costo == pytest.approx(cortes_por_fuerza_bruta(m, orden, pesos, tope))


def test_tope_de_unidades_invalido_da_error():
  m = matriz_aleatoria(2, random.Random(53))
  with pytest.raises(ValueError, match="al menos un producto"):
    ruteo.dividir_en_vueltas(m, [1, 2], [0.0, 1.0, 1.0], float("inf"), 0)


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


def test_servicio_limita_por_unidades(servicio):
  r = servicio.rutear([1, 2, 4], ACTUAL, capacidad_kg=float("inf"), max_unidades=2)
  assert r.max_unidades == 2
  assert len(r.vueltas) == 2                           # 3 productos de a 2 por vuelta
  assert all(v["unidades"] <= 2 for v in r.vueltas)
  assert sum(v["unidades"] for v in r.vueltas) == 3
  assert [p for v in r.vueltas for p in v["productos"]] == r.orden


def test_servicio_con_los_dos_topes(servicio):
  r = servicio.rutear([1, 2, 4], ACTUAL, capacidad_kg=CARRITO_CHICO, max_unidades=1)
  assert len(r.vueltas) == 3
  assert all(v["unidades"] == 1 for v in r.vueltas)


def test_los_tramos_indican_su_vuelta(servicio):
  r = servicio.rutear([1, 2, 4], ACTUAL, capacidad_kg=CARRITO_CHICO)
  tramos = servicio.tramos(r)
  assert {t["vuelta"] for t in tramos} == set(range(1, len(r.vueltas) + 1))
  assert tramos[-1]["acumulado"] == pytest.approx(r.costo_total)


# --------------------------------------------------------------------------------------
# stock del almacén
# --------------------------------------------------------------------------------------
def test_stock_es_proporcional_a_la_demanda(servicio):
  stock = servicio.stock()
  mas, menos = 1, 5                           # 1 es el más pedido del mini dataset
  assert stock[mas] >= stock[menos]
  assert stock[mas] == config.STOCK_PRODUCTO_TOP


def test_con_el_tope_por_defecto_no_hay_agotados(servicio):
  assert all(n >= 1 for n in servicio.stock().values())


def test_bajar_el_tope_agota_primero_los_menos_pedidos(servicio):
  bajo = servicio.stock(2)
  agotados = [p for p, n in bajo.items() if n < 1]
  assert agotados                              # con tope 2 alguno se queda sin stock
  freq = servicio.info
  assert max(freq[p]["freq"] for p in agotados) <= min(
      freq[p]["freq"] for p, n in bajo.items() if n >= 1)


def test_stock_negativo_da_error(servicio):
  with pytest.raises(ValueError, match="no puede ser negativo"):
    datos.calcular_stock(servicio.info, -1)


def test_rutear_omite_los_productos_sin_stock(servicio):
  completo = servicio.rutear([1, 2, 4], ACTUAL)
  assert completo.omitidos == []
  assert len(completo.productos) == 3

  bajo = servicio.rutear([1, 2, 4], ACTUAL, stock_tope=2)
  sin_stock = [p for p, n in servicio.stock(2).items() if n < 1]
  assert bajo.omitidos == [p for p in [1, 2, 4] if p in sin_stock]
  assert all(p not in bajo.productos for p in bajo.omitidos)
  assert len(bajo.productos) + len(bajo.omitidos) == 3


def test_rutear_sin_ningun_producto_con_stock_da_error_claro(servicio):
  sin_stock = [p for p, n in servicio.stock(2).items() if n < 1]
  with pytest.raises(ValueError, match="Ningún producto del pedido tiene stock"):
    servicio.rutear(sin_stock[:2], ACTUAL, stock_tope=2)


def test_el_stock_no_se_descuenta_entre_pedidos(servicio):
  antes = servicio.rutear([1, 2, 4], ACTUAL)
  servicio.rutear([1, 2, 4], ACTUAL)
  despues = servicio.rutear([1, 2, 4], ACTUAL)
  assert antes.costo == pytest.approx(despues.costo)
  assert servicio.stock() == servicio.stock()


# --------------------------------------------------------------------------------------
# cantidades por producto
# --------------------------------------------------------------------------------------
def test_unidades_pedidas_acepta_lista_y_diccionario(servicio):
  assert servicio.unidades_pedidas([1, 2, 1]) == {1: 1, 2: 1}
  assert servicio.unidades_pedidas({1: 3, 2: 1}) == {1: 3, 2: 1}


def test_el_peso_del_pedido_cuenta_las_unidades(servicio):
  uno = servicio.peso_pedido([1])
  assert servicio.peso_pedido({1: 4}) == pytest.approx(4 * uno)


def test_varias_unidades_no_alargan_la_ruta_si_caben(servicio):
  una = servicio.rutear([1, 2], ACTUAL)
  varias = servicio.rutear({1: 3, 2: 2}, ACTUAL)
  assert len(varias.vueltas) == 1
  assert varias.costo_total == pytest.approx(una.costo_total)   # una sola parada por producto
  assert varias.vueltas[0]["unidades"] == 5
  assert varias.cantidades == {1: 3, 2: 2}


def test_un_producto_se_parte_entre_vueltas_si_no_cabe():
  m = matriz_aleatoria(2, random.Random(61))
  pesos = [0.0, 1.0, 1.0]
  costo, vueltas = ruteo.dividir_en_vueltas(m, [1, 2], pesos, 2, cantidades={1: 3, 2: 1})
  assert sum(v.count(1) for v in vueltas) == 3          # las 3 unidades se recogen
  assert sum(v.count(2) for v in vueltas) == 1
  assert all(ruteo.peso_total(v, pesos) <= 2 + 1e-9 for v in vueltas)
  assert costo == pytest.approx(sum(ruteo.costo_ciclo(m, v) for v in vueltas))


def test_cantidades_coincide_con_la_fuerza_bruta():
  rnd = random.Random(67)
  for _ in range(30):
    n = rnd.randint(1, 4)
    m = matriz_aleatoria(n, rnd)
    orden = list(range(1, n + 1))
    cant = {i: rnd.randint(1, 3) for i in orden}
    pesos = [0.0] + [1.0] * n
    tope = rnd.randint(1, 4)
    expandido = [i for i in orden for _ in range(cant[i])]
    costo, _ = ruteo.dividir_en_vueltas(m, orden, pesos, tope, cantidades=cant)
    assert costo == pytest.approx(cortes_por_fuerza_bruta(m, expandido, pesos, tope))


def test_se_recoge_lo_que_haya_cuando_falta_stock(servicio):
  disponible = servicio.stock()[1]
  r = servicio.rutear({1: disponible + 5}, ACTUAL)
  assert r.cantidades == {1: disponible}
  assert r.faltantes == {1: 5}
  assert r.omitidos == []


def test_sin_cantidades_el_resultado_no_cambia(servicio):
  lista = servicio.rutear([1, 2, 4], ACTUAL)
  dicc = servicio.rutear({1: 1, 2: 1, 4: 1}, ACTUAL)
  assert lista.costo_total == pytest.approx(dicc.costo_total)
  assert lista.orden == dicc.orden
