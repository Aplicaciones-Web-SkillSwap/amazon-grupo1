"""Reproduce las cifras del informe con el dataset real de Instacart (se omite si no está)."""
import pytest

from almacen import afinidad, config, datos, layout

CSV = config.RUTA_DATOS / "order_products__train.csv"
pytestmark = pytest.mark.skipif(not CSV.exists(), reason="falta dataset/ con los CSV de Instacart")


@pytest.fixture(scope="module")
def real():
  d = datos.cargar_datos()
  nodos = datos.seleccionar_nodos(d)
  pedidos = datos.pedidos_filtrados(d, nodos)
  return d, nodos, pedidos


def test_dataset_y_nodos(real):
  d, nodos, pedidos = real
  assert d["order_id"].nunique() == 131209
  assert d["product_id"].nunique() == 39123
  assert len(nodos) == 1500
  assert nodos["zona"].value_counts().to_dict() == {"A": 500, "B": 500, "C": 500}
  assert len(pedidos) == 123138


def test_tamano_de_pedidos(real):
  tam = [len(p) for p in real[2].values()]
  assert round(100 * sum(t <= 10 for t in tam) / len(tam), 1) == 80.4
  assert round(100 * sum(t <= 15 for t in tam) / len(tam), 1) == 92.6
  assert max(tam) == 50


def test_g1_como_en_el_informe(real):
  _, nodos, pedidos = real
  g1 = afinidad.construir_afinidad(nodos, pedidos)
  assert g1.num_nodos() == 1500
  assert g1.num_aristas() == 34388
  assert g1.num_aislados() == 4
  assert round(g1.densidad(), 4) == 0.0306
  assert round(g1.grado_promedio(), 1) == 45.9


def test_g2_como_en_el_informe(real):
  nodos = real[1]
  lo = layout.construir_layout(datos.pasillos_desde_catalogo(nodos))
  assert lo.grafo.num_nodos() == 1697
  assert lo.grafo.num_aristas() == 1793
  assert lo.n_pasillos == 98
  assert lo.y_fondo == 76.0
