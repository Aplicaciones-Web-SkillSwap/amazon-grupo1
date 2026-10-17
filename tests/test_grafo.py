import pytest

from almacen.grafo import Grafo


def triangulo(dirigido=False):
  g = Grafo(dirigido)
  g.nodes(["a", "b", "c"])
  g.edge("a", "b", 2)
  g.edge("b", "c", 3.5)
  g.edge("c", "a", 1)
  return g


def test_nodos_e_indices():
  g = Grafo()
  g.nodes(["x", "y"])
  assert g.num_nodos() == 2
  assert g.indice("y") == 1
  assert g.etiqueta(0) == "x"


def test_nodo_duplicado_falla():
  g = Grafo()
  g.node("a")
  with pytest.raises(ValueError):
    g.node("a")


def test_no_dirigido_es_simetrico():
  g = triangulo()
  assert g.peso("a", "b") == 2 and g.peso("b", "a") == 2
  assert g.num_aristas() == 3
  assert sorted(g.vecinos("a")) == ["b", "c"]
  assert g.grado("b") == 2


def test_dirigido_no_es_simetrico():
  g = triangulo(dirigido=True)
  assert g.peso("a", "b") == 2
  assert g.peso("b", "a") is None
  assert g.num_aristas() == 3
  assert g.vecinos("a") == ["b"]


def test_arista_inexistente():
  g = triangulo()
  g.node("d")
  assert g.peso("a", "d") is None
  assert g.grado("d") == 0


def test_lazo_no_dirigido_cuenta_una_vez():
  g = Grafo()
  g.node("a")
  g.edge("a", "a", 4)
  assert g.num_aristas() == 1
  assert g.grado("a") == 1


def test_edges_varias_aristas():
  g = Grafo()
  g.nodes([1, 2, 3, 4])
  g.edges(1, [2, 3, 4], peso=5)
  assert g.num_aristas() == 3
  assert g.peso(1, 4) == 5


def test_guardar_y_cargar(tmp_path):
  g = triangulo()
  g.node(10)          # nodo aislado y con etiqueta numérica
  g.node("depot")
  g.edge("depot", "a", 0.0)
  ruta = tmp_path / "g.la"
  g.guardar(ruta)
  h = Grafo.cargar(ruta)
  assert h.dirigido is False
  assert h.Vertices == g.Vertices
  assert h.G == g.G
  assert h.num_aristas() == g.num_aristas()
  assert h.peso("b", "c") == 3.5
  assert h.grado(10) == 0


def test_guardar_y_cargar_dirigido(tmp_path):
  g = triangulo(dirigido=True)
  ruta = tmp_path / "d.la"
  g.guardar(ruta)
  h = Grafo.cargar(ruta)
  assert h.dirigido is True
  assert h.G == g.G


def test_etiqueta_no_guardable(tmp_path):
  g = Grafo()
  g.node("con espacio")
  with pytest.raises(ValueError):
    g.guardar(tmp_path / "x.la")
