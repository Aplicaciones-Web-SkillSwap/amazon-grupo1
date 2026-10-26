"""Grafo de afinidad G1: nodos = productos, arista = pedidos en los que coinciden.

TÉCNICA: GRAFOS - construcción de G1 (no dirigido, peso = pedidos en común). Alimenta a reubicacion.py.
"""
from collections import Counter
from itertools import combinations

from almacen import config
from almacen.grafo import Grafo


def contar_coocurrencias(pedidos):
  """Counter {(u, v): n pedidos en que u y v coinciden}, con u < v."""
  conteo = Counter()
  for productos in pedidos.values():
    for u, v in combinations(sorted(productos), 2):
      conteo[(u, v)] += 1
  return conteo


def construir_desde_conteo(nodos, conteo, umbral=config.UMBRAL_AFINIDAD):
  """G1 no dirigido y ponderado a partir de un conteo de coocurrencias ya calculado.
  Solo se crean las aristas con peso >= umbral."""
  g = Grafo()
  g.nodes([int(p) for p in nodos["product_id"]])
  for (u, v), peso in conteo.items():
    if peso >= umbral:
      g.edge(u, v, peso)
  return g


def construir_afinidad(nodos, pedidos, umbral=config.UMBRAL_AFINIDAD):
  """G1 no dirigido y ponderado. Solo se crean las aristas con peso >= umbral."""
  return construir_desde_conteo(nodos, contar_coocurrencias(pedidos), umbral)
