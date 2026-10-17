import matplotlib

matplotlib.use("Agg")

import pytest                                   # noqa: E402
from matplotlib.figure import Figure             # noqa: E402

from almacen import experimento                  # noqa: E402
from almacen.gui import dibujo                   # noqa: E402
from almacen.servicio import ACTUAL, OPTIMIZADO, Servicio   # noqa: E402


@pytest.fixture
def servicio(carpeta_datos):
  return Servicio.desde_csv(carpeta_datos, por_zona=2, umbral=2, capacidad=2)


def test_dibujar_almacen_con_ruta(servicio):
  r = servicio.rutear([1, 2, 4, 6], ACTUAL, "dp")
  ax = Figure().subplots()
  lo = servicio.layouts[ACTUAL]
  dibujo.dibujar_almacen(ax, lo, servicio.info, orden=r.orden, camino=r.camino,
                         marcar=r.productos, resaltar=1, titulo="Prueba")
  assert ax.get_title(loc="left") == "Prueba"
  assert len(ax.texts) >= len(r.orden)           # un número por parada
  dibujo.vista_a_la_ruta(ax, lo, r.camino)
  dibujo.vista_completa(ax, lo)
  dibujo.vista_a_la_ruta(ax, lo, None)


def test_dibujar_almacen_sin_ruta(servicio):
  ax = Figure().subplots()
  dibujo.dibujar_almacen(ax, servicio.layouts[OPTIMIZADO], servicio.info)


@pytest.mark.parametrize("zona", [None, "A", "B"])
def test_g1(servicio, zona):
  calculo = dibujo.calcular_posiciones_g1(servicio.g1, servicio.info, zona)
  assert set(calculo["pos"]) == set(calculo["nodos"])
  assert all(u in calculo["pos"] and v in calculo["pos"] for u, v in calculo["aristas"])
  dibujo.dibujar_g1(Figure().subplots(), calculo, servicio.g1, servicio.info, "G1")


def test_graficos_del_experimento(servicio):
  servicio.agregar_controles()
  df = experimento.correr(servicio, 6, semilla=1, umbral_dp=19)
  fig = Figure()
  a, b, c = fig.subplots(1, 3)
  dibujo.grafico_distancia_por_layout(a, experimento.por_layout(df))
  dibujo.grafico_distancia_por_tamano(b, experimento.por_tamano(df, 19))
  dibujo.grafico_tiempos(c, experimento.tiempos_por_tamano(df, 19))
  assert len(a.patches) == len(set(df["layout"]))
