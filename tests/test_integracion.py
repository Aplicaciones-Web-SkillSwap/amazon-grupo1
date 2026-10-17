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


def test_g2_es_conexo_con_bfs(real):
  from almacen import bfs
  lo = layout.construir_layout(datos.pasillos_desde_catalogo(real[1]))
  visited, _ = bfs.bfs(lo.grafo, "depot")
  assert all(visited)


def test_g1_componentes(real):
  from almacen import bfs
  _, nodos, pedidos = real
  g1 = afinidad.construir_afinidad(nodos, pedidos)
  grupos = bfs.componentes(g1)
  assert len(grupos[0]) + sum(len(x) for x in grupos[1:]) == 1500
  assert [len(x) for x in grupos] == [1496, 1, 1, 1, 1]


def test_distancias_reales_contra_dijkstra(real):
  import random
  from almacen.distancias import Distancias
  from oraculo import dijkstra
  lo = layout.construir_layout(datos.pasillos_desde_catalogo(real[1]))
  d = Distancias(lo)
  assert d.red.num_nodos() == 197
  prods = [e for e in lo.grafo.Vertices if lo.tipo[e] == "ubicacion"]
  rnd = random.Random(0)
  for a in ["depot"] + rnd.sample(prods, 6):
    ref = dijkstra(lo.grafo, a)
    for b in prods:
      assert d.entre(a, b) == ref[lo.grafo.indice(b)]


def test_reubicacion_real(real):
  from almacen import reubicacion
  from almacen.distancias import Distancias
  _, nodos, pedidos = real
  info = datos.info_productos(nodos)
  g1 = afinidad.construir_afinidad(nodos, pedidos)
  base = layout.construir_layout(datos.pasillos_desde_catalogo(nodos))
  pasillos = reubicacion.reubicar(g1, info, n_pasillos=base.n_pasillos)
  colocados = [p for _, _, ps in pasillos for p in ps]
  assert sorted(colocados) == sorted(info)                      # cada producto, una vez
  assert all(len(ps) <= config.CAPACIDAD_PASILLO for _, _, ps in pasillos)
  assert len(pasillos) <= base.n_pasillos
  opt = layout.construir_layout(pasillos, y_fondo=base.y_fondo)
  assert opt.y_fondo == base.y_fondo == 76.0
  Distancias(opt).entre("depot", colocados[-1])                 # el layout es transitable


def test_ruteo_sobre_pedidos_reales(real):
  from almacen import ruteo
  from almacen.distancias import Distancias
  _, nodos, pedidos = real
  D = Distancias(layout.construir_layout(datos.pasillos_desde_catalogo(nodos)))
  chicos = [p for p in pedidos.values() if 6 <= len(p) <= 8][:15]
  assert len(chicos) == 15
  for prods in chicos:
    m = D.matriz(["depot"] + prods)
    exacto = ruteo.held_karp(m)[0]
    assert ruteo.backtracking(m)[0] == pytest.approx(exacto)
    assert ruteo.voraz(m)[0] >= exacto - 1e-9


@pytest.fixture(scope="module")
def servicio_real():
  from almacen.servicio import Servicio
  return Servicio.desde_csv()


def test_servicio_real(servicio_real):
  s = servicio_real
  r = s.resumen()
  assert r["productos"] == 1500 and r["pasillos"] == 98 and r["nodos_g2"] == 1697
  oid, prods = s.pedido_aleatorio(tamano=8, semilla=3)
  dos = s.comparar_layouts(prods, "dp")
  assert dos["actual"].camino[0] == "depot" and dos["optimizado"].costo > 0
  comp = s.comparar_tecnicas(prods)
  assert comp["backtracking"].costo == pytest.approx(comp["dp"].costo)


def test_experimento_real_pequeno(servicio_real):
  from almacen import experimento
  df = experimento.correr(servicio_real, 120, semilla=1)
  res = experimento.por_layout(df).set_index("layout")
  assert res.loc["optimizado", "media_m"] < res.loc["actual", "media_m"]
  assert res.loc["optimizado", "reduccion_pct"] > 15
