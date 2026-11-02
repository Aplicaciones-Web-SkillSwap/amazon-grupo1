"""Pruebas de los mapas y gráficos interactivos de la versión web (Plotly)."""
import pytest

pytest.importorskip("plotly")
from almacen.gui import dibujo   # noqa: E402
from almacen.servicio import ACTUAL, OPTIMIZADO, Servicio   # noqa: E402
from almacen.web import graficos, mapas   # noqa: E402


@pytest.fixture
def servicio(carpeta_datos):
  return Servicio.desde_csv(carpeta_datos, por_zona=2, umbral=2, capacidad=2)


def test_mapa_resalta_productos_y_pasillo(servicio):
  fig = mapas.mapa_almacen(servicio, OPTIMIZADO, "x", resaltar=[1, 2], pasillo=0)
  assert any(len(t.x) == 2 for t in fig.data)        # la traza de resaltados
  assert len(fig.layout.shapes) == 1


def test_grafo_afinidad_devuelve_companeros_del_producto(servicio):
  calculo = dibujo.calcular_posiciones_g1(servicio.g1, servicio.info)
  producto = calculo["nodos"][0]
  fig, vecinos = graficos.grafo_afinidad(servicio, calculo, producto)
  assert all(p in servicio.info for p, _ in vecinos)
  assert [w for _, w in vecinos] == sorted((w for _, w in vecinos), reverse=True)
  _, sin = graficos.grafo_afinidad(servicio, calculo, None)
  assert sin == []


def test_dispersion_cuenta_todos_los_pedidos(servicio):
  from almacen import experimento
  df = experimento.correr(servicio, 6, layouts=[ACTUAL, OPTIMIZADO])
  fig = graficos.dispersion_pedidos(df)
  puntos = sum(len(t.x) for t in fig.data if t.mode == "markers")
  assert puntos == df["order_id"].nunique()
