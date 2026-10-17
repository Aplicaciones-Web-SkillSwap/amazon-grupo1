import pytest

from almacen import layout
from almacen.grafo import Grafo

PASILLOS = [("A", 1, [10, 11, 12]), ("B", 2, [20])]


def alcanzables(g, origen):
  visto = {g.indice(origen)}
  pila = [g.indice(origen)]
  while pila:
    u = pila.pop()
    for v, _ in g.G[u]:
      if v not in visto:
        visto.add(v)
        pila.append(v)
  return len(visto)


def test_largo_del_almacen():
  assert layout.largo_del_almacen(PASILLOS) == 3.0      # (2 filas + 1) * 1 m


def test_construir_layout_pequeno():
  lo = layout.construir_layout(PASILLOS)
  g = lo.grafo
  assert g.num_nodos() == 9                             # depot + 2*2 cruces + 4 productos
  assert g.num_aristas() == 9
  assert lo.n_pasillos == 2 and lo.y_fondo == 3.0
  assert lo.pos["depot"] == (-3.0, 0.0)
  assert lo.pos[10] == (0.0, 1.0) and lo.pos[11] == (0.0, 1.0) and lo.pos[12] == (0.0, 2.0)
  assert lo.pos["F1"] == (3.0, 0.0) and lo.pos["R1"] == (3.0, 3.0)
  assert lo.tipo["depot"] == "depot" and lo.tipo["F0"] == "cruce" and lo.tipo[20] == "ubicacion"
  assert lo.pasillo == {10: 0, 11: 0, 12: 0, 20: 1}
  assert lo.zona[20] == "B" and lo.zona["depot"] is None


def test_pesos_del_layout():
  g = layout.construir_layout(PASILLOS).grafo
  assert g.peso("depot", "F0") == 3.0
  assert g.peso("F0", 10) == 1.0
  assert g.peso(10, 11) == 0.0                          # mismo metro, lado opuesto
  assert g.peso(10, 12) == 1.0
  assert g.peso(12, "R0") == 1.0
  assert g.peso("F0", "F1") == 3.0
  assert g.peso("R0", "R1") == 3.0
  assert g.peso(20, "R1") == 2.0


def test_layout_es_conexo():
  g = layout.construir_layout(PASILLOS).grafo
  assert alcanzables(g, "depot") == g.num_nodos()


def test_y_fondo_explicito():
  lo = layout.construir_layout(PASILLOS, y_fondo=10.0)
  assert lo.y_fondo == 10.0
  assert lo.grafo.peso(12, "R0") == 8.0
  assert lo.pos["R0"] == (0.0, 10.0)


def test_el_layout_se_puede_guardar_y_cargar(tmp_path):
  g = layout.construir_layout(PASILLOS).grafo
  g.guardar(tmp_path / "g2.la")
  h = Grafo.cargar(tmp_path / "g2.la")
  assert h.G == g.G and h.Vertices == g.Vertices


def test_pasillo_que_no_cabe_en_y_fondo():
  with pytest.raises(ValueError):
    layout.construir_layout(PASILLOS, y_fondo=1.0)
