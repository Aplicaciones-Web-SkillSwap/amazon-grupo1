"""Pruebas de la animación del recorrido (versión web, Plotly)."""
import pytest

pytest.importorskip("plotly")
from almacen import config   # noqa: E402
from almacen.layout import construir_layout   # noqa: E402
from almacen.web import animacion   # noqa: E402


@pytest.fixture
def lo():
  pasillos = [("A", 0, [1, 2, 3]), ("B", 1, [4, 5, 6])]
  return construir_layout(pasillos)


def test_trayecto_acumula_la_distancia_del_camino(lo):
  camino = ["depot", "F0", 1, "F0", "depot"]
  puntos, acum = animacion._trayecto(lo, camino)
  assert acum[0] == 0
  assert acum == sorted(acum)
  assert acum[-1] == pytest.approx(2 * (config.DIST_PASILLO + lo.pos[1][1]))


def test_llegadas_siguen_el_orden_de_visita(lo):
  camino = ["depot", "F0", 1, 2, "F0", "F1", 4, "F1", "depot"]
  _, acum = animacion._trayecto(lo, camino)
  llegadas = animacion._llegadas(camino, [1, 4], acum)
  assert llegadas == [acum[2], acum[6]]


def test_hasta_interpola_dentro_de_un_tramo(lo):
  camino = ["depot", "F0"]
  puntos, acum = animacion._trayecto(lo, camino)
  xs, ys = animacion._hasta(puntos, acum, acum[-1] / 2)
  assert xs[-1] == pytest.approx((puntos[0][0] + puntos[1][0]) / 2)
  xs, ys = animacion._hasta(puntos, acum, 1e9)
  assert (xs[-1], ys[-1]) == puntos[-1]
