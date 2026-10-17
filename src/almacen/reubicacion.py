"""Layout optimizado: agrupa productos afines con UFDS y los asigna a pasillos.

1. agrupar: recorre las aristas de G1 de mayor a menor afinidad (como Kruskal) y une los
   grupos de sus extremos mientras el grupo resultante no pase de `capacidad` productos.
2. empaquetar: acomoda los grupos en pasillos de `capacidad` ubicaciones (first-fit),
   empezando por los grupos con mayor frecuencia media de pedido, de modo que los
   productos más pedidos queden juntos en los primeros pasillos.
3. reubicar: los pasillos más pedidos quedan más cerca del depot y, dentro de cada
   pasillo, los productos más pedidos quedan más cerca del frente.
"""
from collections import Counter

from almacen import config
from almacen.ufds import UFDS


def agrupar(g1, capacidad=config.CAPACIDAD_PASILLO):
  """Grupos de productos (listas de etiquetas) de a lo más `capacidad` elementos.

  Incluye los productos aislados como grupos de uno. Orden determinista."""
  aristas = [(peso, u, v) for u, ady in enumerate(g1.G) for v, peso in ady if u < v]
  aristas.sort(key=lambda a: (-a[0], a[1], a[2]))
  uf = UFDS(g1.num_nodos())
  for _, u, v in aristas:
    uf.union(u, v, limite=capacidad)
  grupos = [[g1.etiqueta(i) for i in c] for c in uf.conjuntos()]
  return sorted(grupos, key=lambda c: (-len(c), c[0]))


def empaquetar(grupos, freq, n_pasillos, capacidad=config.CAPACIDAD_PASILLO):
  """Reparte los grupos en pasillos (listas de productos) con first-fit.

  Los grupos se procesan de mayor a menor frecuencia media; freq[producto] es el número
  de líneas de pedido del producto."""
  def media(grupo):
    return sum(freq[p] for p in grupo) / len(grupo)

  pasillos, libre = [], []
  for grupo in sorted(grupos, key=lambda c: (-media(c), c[0])):
    for k, espacio in enumerate(libre):
      if len(grupo) <= espacio:
        pasillos[k].extend(grupo)
        libre[k] -= len(grupo)
        break
    else:
      pasillos.append(list(grupo))
      libre.append(capacidad - len(grupo))
  if len(pasillos) > n_pasillos:
    raise ValueError(f"Se necesitan {len(pasillos)} pasillos y solo hay {n_pasillos}")
  return pasillos


def reubicar(g1, info, n_pasillos, capacidad=config.CAPACIDAD_PASILLO):
  """Devuelve los pasillos del layout optimizado: [(zona, id, [product_id]), ...].

  info es datos.info_productos(nodos). La zona de cada pasillo es la más común entre
  sus productos (solo sirve para colorear). Los ids de pasillo empiezan en 1."""
  freq = {p: info[p]["freq"] for p in g1.Vertices}
  pasillos = empaquetar(agrupar(g1, capacidad), freq, n_pasillos, capacidad)
  pasillos.sort(key=lambda prods: (-sum(freq[p] for p in prods), min(prods)))
  resultado = []
  for k, prods in enumerate(pasillos, start=1):
    prods = sorted(prods, key=lambda p: (-freq[p], p))
    zona = Counter(info[p]["zona"] for p in prods).most_common(1)[0][0]
    resultado.append((zona, k, prods))
  return resultado
