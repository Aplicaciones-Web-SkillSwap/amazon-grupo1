"""Ruteo de un pedido: ciclo más corto que sale del depot, pasa por todos los productos
del pedido y vuelve al depot (TSP sobre la matriz de distancias del pedido).

Todas las funciones reciben la matriz `m` del pedido: m[0] es el depot y m[1..n] son los
n productos. Devuelven (costo, orden) con `orden` = índices 1..n en el orden de visita
(sin repetir el depot).

  voraz         vecino más cercano          O(n^2)         no siempre óptimo
  fuerza_bruta  todas las permutaciones     O(n! * n)      óptimo
  backtracking  permutaciones con poda      O(n!) peor caso, óptimo
  held_karp     programación dinámica       O(n^2 * 2^n)   óptimo
"""
from itertools import permutations
from math import inf


def costo_ciclo(m, orden):
  """Largo del ciclo depot -> orden -> depot."""
  if not orden:
    return 0.0
  total = m[0][orden[0]] + m[orden[-1]][0]
  for a, b in zip(orden, orden[1:]):
    total += m[a][b]
  return total


def voraz(m):
  """Vecino más cercano: desde el depot, ir siempre al producto pendiente más cercano."""
  n = len(m) - 1
  pendientes = set(range(1, n + 1))
  orden, actual = [], 0
  while pendientes:
    siguiente = min(pendientes, key=lambda j: (m[actual][j], j))
    orden.append(siguiente)
    pendientes.remove(siguiente)
    actual = siguiente
  return costo_ciclo(m, orden), orden


def fuerza_bruta(m):
  """Prueba todas las permutaciones de los productos y se queda con la mejor."""
  n = len(m) - 1
  mejor, mejor_orden = inf, []
  for perm in permutations(range(1, n + 1)):
    c = costo_ciclo(m, perm)
    if c < mejor:
      mejor, mejor_orden = c, list(perm)
  return (mejor, mejor_orden) if n else (0.0, [])


def backtracking(m):
  """Igual que fuerza bruta, pero abandona una rama apenas su costo parcial iguala o
  supera el mejor ciclo conocido (que arranca con el del algoritmo voraz)."""
  n = len(m) - 1
  if n == 0:
    return 0.0, []
  mejor, mejor_orden = voraz(m)
  visitado = [False] * (n + 1)
  camino = []

  def explorar(actual, costo):
    nonlocal mejor, mejor_orden
    if costo >= mejor:                       # poda
      return
    if len(camino) == n:
      total = costo + m[actual][0]
      if total < mejor:
        mejor, mejor_orden = total, camino.copy()
      return
    for j in range(1, n + 1):
      if not visitado[j]:
        visitado[j] = True
        camino.append(j)
        explorar(j, costo + m[actual][j])
        camino.pop()
        visitado[j] = False

  explorar(0, 0.0)
  return mejor, mejor_orden


def held_karp(m):
  """Programación dinámica sobre subconjuntos (Held-Karp).

  dp[mask][j] = costo mínimo de salir del depot, visitar exactamente los productos de
  `mask` (bit j-1 = producto j) y terminar en el producto j."""
  n = len(m) - 1
  if n == 0:
    return 0.0, []
  total = 1 << n
  dp = [[inf] * n for _ in range(total)]
  padre = [[-1] * n for _ in range(total)]
  for j in range(n):
    dp[1 << j][j] = m[0][j + 1]
  for mask in range(1, total):
    for j in range(n):
      actual = dp[mask][j]
      if not (mask >> j) & 1 or actual == inf:
        continue
      for k in range(n):
        if (mask >> k) & 1:
          continue
        nuevo = mask | (1 << k)
        costo = actual + m[j + 1][k + 1]
        if costo < dp[nuevo][k]:
          dp[nuevo][k] = costo
          padre[nuevo][k] = j

  completo = total - 1
  mejor, ultimo = min((dp[completo][j] + m[j + 1][0], j) for j in range(n))
  orden, mask, j = [], completo, ultimo
  while j != -1:
    orden.append(j + 1)
    anterior = padre[mask][j]
    mask ^= 1 << j
    j = anterior
  orden.reverse()
  return mejor, orden
