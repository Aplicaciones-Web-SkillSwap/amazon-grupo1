"""Pruebas de la versión web con el simulador de Streamlit. Usan el dataset real
(carpeta dataset/), así que se omiten si falta Streamlit o los CSV."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest   # noqa: E402

from almacen import config   # noqa: E402
from almacen.web import textos   # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CSV = ("departments.csv", "products.csv", "order_products__train.csv")

pytestmark = pytest.mark.skipif(
    not all((config.RUTA_DATOS / f).exists() for f in CSV), reason="falta el dataset")


@pytest.fixture(scope="module")
def app():
  return AppTest.from_file(str(RAIZ / "app_web.py"), default_timeout=300).run()


def boton(at, etiqueta):
  return next(b for b in at.button if b.label == etiqueta)


def test_carga_sin_errores_y_con_pedido_de_ejemplo(app):
  assert not app.exception
  assert len(app.tabs) == 5
  assert app.session_state["pedido"][1]


def test_calcular_ruta_muestra_distancia_y_tecnica(app):
  boton(app, "Calcular ruta").click()
  app.run()
  assert not app.exception
  metricas = {m.label: m.value for m in app.metric}
  assert float(metricas["Distancia total"].split()[0].replace(",", "")) > 0
  assert metricas["Técnica ejecutada"] in textos.NOMBRE_TECNICA.values()


def test_comparar_tecnicas_y_layouts(app):
  boton(app, "Comparar técnicas").click()
  app.run()
  assert not app.exception
  boton(app, "Comparar layouts").click()
  app.run()
  assert not app.exception
  assert any("Comparación de layouts" in m.value for m in app.markdown)


def test_ufds_con_otra_capacidad(app):
  next(n for n in app.number_input if n.label.startswith("Capacidad")).set_value(20)
  boton(app, "Ejecutar UFDS").click()
  app.run()
  assert not app.exception
  assert any("K = 20" in m.value for m in app.markdown)


def test_experimento_y_grafos(app):
  next(s for s in app.slider if s.label == "Pedidos a evaluar").set_value(20)
  boton(app, "Ejecutar experimento").click()
  app.run()
  assert not app.exception
  assert "exp" in app.session_state
  next(s for s in app.selectbox if s.label == "Grafo a dibujar").select("G₂ almacén optimizado")
  app.run()
  assert not app.exception


def test_textos_coinciden_con_el_servicio():
  from almacen.servicio import TECNICAS
  claves = set(textos.TECNICAS.values()) - {"auto"}
  assert claves <= set(TECNICAS)
  assert claves <= set(textos.AYUDA_TECNICA)
