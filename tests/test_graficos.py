"""Pruebas de los mapas y gráficos interactivos de la versión web (Plotly)."""
import pytest

pytest.importorskip("plotly")
from almacen.gui import dibujo   # noqa: E402
from almacen.servicio import ACTUAL, OPTIMIZADO, Servicio   # noqa: E402
from almacen.web import graficos, mapas, pasos   # noqa: E402


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


def test_paso_a_paso_de_cada_tecnica(servicio):
  productos = [1, 2, 4, 6]
  explicar = lambda tecnica: servicio.explicar_ruteo(productos, ACTUAL, tecnica)
  fig, total = pasos.figura_voraz(servicio, ACTUAL, productos, explicar("voraz"))
  assert len(fig.frames) == 2 * len(productos) + 1       # dos cuadros por decisión y el regreso
  assert total == pytest.approx(servicio.rutear(productos, ACTUAL, "voraz").costo)
  traza = explicar("fuerza_bruta")
  fig = pasos.figura_fuerza_bruta(servicio, ACTUAL, productos, traza)
  assert len(fig.frames) == len(traza["eventos"]) + 1
  traza = explicar("backtracking")
  fig = pasos.figura_backtracking(servicio, ACTUAL, productos, traza)
  assert len(fig.frames) >= len(traza["eventos"]) + 2
  assert len(pasos.figura_estados_dp(explicar("dp")).data[0].x) == len(productos)


def test_la_ruta_animada_marca_cada_tramo(servicio):
  from almacen.web import animacion
  r = servicio.rutear([1, 2, 4, 6], ACTUAL, "dp")
  fig = animacion.figura_ruta(servicio, [("x", ACTUAL, r)], metros_tramos=True)
  tramos = next(t for t in fig.data if t.hovertext and str(t.hovertext[0]).startswith("Tramo 1"))
  assert len(tramos.x) == 5
  metros = [float(x.split()[0].replace(",", "")) for x in tramos.text]
  assert sum(metros) == pytest.approx(r.costo, abs=3)
