import pytest

from almacen import reubicacion
from almacen.grafo import Grafo


def g1_ejemplo():
  g = Grafo()
  g.nodes([1, 2, 3, 4, 5, 6, 7])
  for u, v, w in [(1, 2, 10), (2, 3, 9), (3, 4, 8), (5, 6, 1)]:
    g.edge(u, v, w)
  return g                                    # el 7 queda aislado


def test_agrupar_respeta_la_capacidad():
  grupos = reubicacion.agrupar(g1_ejemplo(), capacidad=3)
  assert sorted(map(sorted, grupos)) == [[1, 2, 3], [4], [5, 6], [7]]
  assert all(len(x) <= 3 for x in grupos)


def test_agrupar_con_capacidad_grande_une_componentes():
  grupos = reubicacion.agrupar(g1_ejemplo(), capacidad=10)
  assert sorted(map(sorted, grupos)) == [[1, 2, 3, 4], [5, 6], [7]]


def test_agrupar_prioriza_la_arista_mas_pesada():
  g = Grafo()
  g.nodes([1, 2, 3])
  g.edge(1, 2, 5)
  g.edge(2, 3, 9)                             # con capacidad 2 gana la arista 2-3
  grupos = reubicacion.agrupar(g, capacidad=2)
  assert sorted(map(sorted, grupos)) == [[1], [2, 3]]


def test_empaquetar_first_fit():
  grupos = [[1, 2, 3], [4, 5], [6], [7]]
  freq = {i: 1 for i in range(1, 8)}
  pasillos = reubicacion.empaquetar(grupos, freq, n_pasillos=2, capacidad=4)
  assert sorted(map(sorted, pasillos)) == [[1, 2, 3, 6], [4, 5, 7]]


def test_empaquetar_sin_pasillos_suficientes():
  with pytest.raises(ValueError):
    reubicacion.empaquetar([[1, 2, 3], [4, 5, 6]], {i: 1 for i in range(1, 7)},
                           n_pasillos=1, capacidad=3)


def test_reubicar_ordena_por_frecuencia():
  g = g1_ejemplo()
  freq = {1: 5, 2: 9, 3: 1, 4: 2, 5: 50, 6: 40, 7: 3}
  info = {p: {"freq": f, "zona": "A" if p < 5 else "C"} for p, f in freq.items()}
  pasillos = reubicacion.reubicar(g, info, n_pasillos=3, capacidad=3)
  assert [k for _, k, _ in pasillos] == [1, 2, 3]
  assert pasillos[0][2] == [5, 6, 7]          # el más pedido: pasillo 1; el 7 rellena el hueco
  assert pasillos[0][0] == "C"
  assert pasillos[1][2] == [2, 1, 3]
  assert pasillos[2][2] == [4]
  assert sorted(p for _, _, ps in pasillos for p in ps) == [1, 2, 3, 4, 5, 6, 7]
