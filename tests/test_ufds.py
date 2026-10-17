import random

from almacen.ufds import UFDS


def test_estado_inicial():
  uf = UFDS(4)
  assert uf.parent == [-1, -1, -1, -1]
  assert all(uf.tam(i) == 1 for i in range(4))


def test_union_y_find():
  uf = UFDS(6)
  assert uf.union(0, 1) and uf.union(1, 2)
  assert uf.mismo_conjunto(0, 2) and not uf.mismo_conjunto(0, 3)
  assert uf.tam(2) == 3
  assert not uf.union(0, 2)                   # ya estaban juntos
  assert uf.parent[uf.find(0)] == -3          # la raíz guarda el tamaño en negativo


def test_union_por_tamano_cuelga_el_menor():
  uf = UFDS(5)
  uf.union(0, 1)
  uf.union(0, 2)                              # {0,1,2} con raíz r
  raiz = uf.find(0)
  uf.union(3, 0)                              # el singleton 3 debe colgar de la raíz grande
  assert uf.find(3) == raiz and uf.parent[3] == raiz


def test_limite_de_capacidad():
  uf = UFDS(5)
  assert uf.union(0, 1, limite=3) and uf.union(1, 2, limite=3)
  assert not uf.union(2, 3, limite=3)         # quedaría de 4
  assert uf.tam(3) == 1 and not uf.mismo_conjunto(0, 3)
  assert uf.union(3, 4, limite=3)


def test_conjuntos_es_una_particion():
  rnd = random.Random(1)
  uf = UFDS(40)
  for _ in range(30):
    uf.union(rnd.randrange(40), rnd.randrange(40))
  grupos = uf.conjuntos()
  assert sorted(x for g in grupos for x in g) == list(range(40))
  assert all(len(g) == uf.tam(g[0]) for g in grupos)
