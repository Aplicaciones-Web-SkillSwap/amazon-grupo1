"""Carga y selección de datos de Instacart (pandas).

Mismo procedimiento del script del hito 1: se cruzan pedidos, productos y departamentos,
se asigna cada departamento a una zona (A, B, C) y se eligen los productos más pedidos
de cada zona. Los departamentos que no están en ZONAS (pets) quedan fuera.
"""
from pathlib import Path

import pandas as pd

from almacen import config


def cargar_datos(ruta=config.RUTA_DATOS):
  """Una fila por línea de pedido, con producto, departamento y zona (NaN si no tiene)."""
  ruta = Path(ruta)
  productos = pd.read_csv(ruta / "products.csv")
  departamentos = pd.read_csv(ruta / "departments.csv")
  pedidos = pd.read_csv(ruta / "order_products__train.csv")

  zona_de_dep = {dep: z for z, deps in config.ZONAS.items() for dep in deps}
  datos = (pedidos.merge(productos, on="product_id")
                  .merge(departamentos, on="department_id"))
  datos["zona"] = datos["department"].map(zona_de_dep)
  return datos


def seleccionar_nodos(datos, por_zona=config.PRODUCTOS_POR_ZONA):
  """Los `por_zona` productos más pedidos de cada zona."""
  frecuencia = datos.groupby(["zona", "product_id"]).size().rename("freq").reset_index()
  seleccion = (frecuencia.sort_values("freq", ascending=False)
                         .groupby("zona").head(por_zona))
  info = (datos[["product_id", "product_name", "aisle_id", "department", "zona"]]
          .drop_duplicates("product_id").set_index("product_id"))
  return seleccion.join(info, on="product_id", rsuffix="_")


def info_productos(nodos):
  """Diccionario product_id -> datos del producto seleccionado."""
  info = {}
  for fila in nodos.itertuples():
    info[int(fila.product_id)] = {
        "nombre": fila.product_name,
        "zona": fila.zona,
        "departamento": fila.department,
        "pasillo": int(fila.aisle_id),
        "freq": int(fila.freq),
    }
  return info


def pedidos_filtrados(datos, nodos):
  """Diccionario order_id -> lista ordenada de productos del pedido que están en `nodos`."""
  ids = set(nodos["product_id"])
  filtrado = datos[datos["product_id"].isin(ids)]
  return {int(oid): sorted(int(p) for p in grupo)
          for oid, grupo in filtrado.groupby("order_id")["product_id"]}


def pasillos_desde_catalogo(nodos):
  """Lista de pasillos (zona, aisle_id, [product_id]) según el catálogo de Instacart.

  Es la distribución actual del almacén: cada producto en el pasillo de su catálogo.
  """
  pasillos = []
  for zona in config.ZONAS:
    sub = nodos[nodos["zona"] == zona].sort_values(["aisle_id", "product_id"])
    for aisle_id, grupo in sub.groupby("aisle_id"):
      pasillos.append((zona, int(aisle_id), [int(p) for p in grupo["product_id"]]))
  return pasillos
