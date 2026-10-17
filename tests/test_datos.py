import pandas as pd

from almacen import datos


def test_cargar_datos_asigna_zonas(carpeta_datos):
  d = datos.cargar_datos(carpeta_datos)
  assert len(d) == 19
  assert d.loc[d.product_id == 1, "zona"].eq("A").all()
  assert d.loc[d.product_id == 4, "zona"].eq("B").all()
  assert d.loc[d.product_id == 6, "zona"].eq("C").all()
  assert d.loc[d.product_id == 8, "zona"].isna().all()   # pets queda sin zona


def test_seleccionar_nodos_top_por_zona(carpeta_datos):
  nodos = datos.seleccionar_nodos(datos.cargar_datos(carpeta_datos), por_zona=2)
  assert set(nodos["product_id"]) == {1, 2, 4, 5, 6, 7}
  assert 8 not in set(nodos["product_id"])               # pets nunca se selecciona
  assert 3 not in set(nodos["product_id"])               # 3er más pedido de la zona A
  freq = dict(zip(nodos["product_id"], nodos["freq"]))
  assert freq[1] == 5 and freq[2] == 4 and freq[4] == 3


def test_info_productos(carpeta_datos):
  nodos = datos.seleccionar_nodos(datos.cargar_datos(carpeta_datos), por_zona=2)
  info = datos.info_productos(nodos)
  assert info[1] == {"nombre": "Banana", "zona": "A", "departamento": "produce",
                     "pasillo": 1, "freq": 5}
  assert info[6]["zona"] == "C"


def test_pedidos_filtrados(carpeta_datos):
  d = datos.cargar_datos(carpeta_datos)
  nodos = datos.seleccionar_nodos(d, por_zona=2)
  assert datos.pedidos_filtrados(d, nodos) == {
      1: [1, 2, 4], 2: [1, 2, 4, 6], 3: [1, 2], 4: [1, 4], 5: [5, 6, 7], 6: [1, 2]}


def test_pasillos_desde_catalogo(carpeta_datos):
  nodos = datos.seleccionar_nodos(datos.cargar_datos(carpeta_datos), por_zona=2)
  assert datos.pasillos_desde_catalogo(nodos) == [
      ("A", 1, [1, 2]), ("B", 3, [4, 5]), ("C", 4, [6, 7])]
