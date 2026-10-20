"""Ruteo de un pedido: ciclo más corto que sale del depot, pasa por todos los productos
del pedido y vuelve al depot (TSP sobre la matriz de distancias del pedido).

Todas las funciones reciben la matriz `m` del pedido: m[0] es el depot y m[1..n] son los
n productos. Devuelven (costo, orden) con `orden` = índices 1..n en el orden de visita
(sin repetir el depot).

  voraz         vecino más cercano          O(n^2)         no siempre óptimo
  fuerza_bruta  todas las permutaciones     O(n! * n)      óptimo
  backtracking  permutaciones con poda      O(n!) peor caso, óptimo
  held_karp     programación dinámica       O(n^2 * 2^n)   óptimo

TÉCNICA: VORAZ (voraz), FUERZA BRUTA (fuerza_bruta), BACKTRACKING (backtracking) y PROGRAMACIÓN DINÁMICA (held_karp, held_karp_opt). resolver elige según el tamaño del pedido; Servicio.rutear lo invoca (pestaña Ruteo).
"""
from itertools import permutations
from math import inf

import numpy as np


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


# ---------------------------------------------------------------------------------------
# Held-Karp optimizado
# ---------------------------------------------------------------------------------------
MAX_N_DP = 22        # con n = 22 la tabla ocupa ~0.7 GB; por encima no es viable en memoria


def held_karp_opt(m, poda=False):
  """Held-Karp con cuatro mejoras sobre la versión base.

  1. Submatriz del pedido: recibe solo la matriz del pedido (depot + n productos), que
     arma Distancias.matriz a partir de Floyd-Warshall; cada distancia es un acceso O(1).
  2. Estructura plana: la tabla dp es un solo arreglo NumPy de forma (2^n, n).
  3. Vectorización: se llenan los estados por capas (cantidad de productos visitados) y,
     para cada último producto k, todas las máscaras de la capa se calculan de una vez.
  4. Poda por cota superior (poda=True): la ruta del voraz acota el óptimo. Un estado se
     descarta si su costo más una cota inferior de lo que falta (entrar una vez a cada
     producto pendiente y al depot por su arista más barata) supera esa cota.
     Está apagada por defecto: en pedidos reales el voraz queda a 0-3 % del óptimo, pero
     esa cota inferior es solo ~40 % del óptimo, así que casi no descarta estados y la
     poda solo agrega costo (ver scripts/benchmark_ruteo.py).

  La complejidad sigue siendo O(n^2 * 2^n) en tiempo y O(n * 2^n) en memoria.
  Devuelve (costo, orden) igual que held_karp."""
  n = len(m) - 1
  if n == 0:
    return 0.0, []
  if n > MAX_N_DP:
    raise ValueError(f"Pedido de {n} productos: supera el máximo de {MAX_N_DP} para la DP")

  C = np.asarray(m, dtype=float)
  D = C[1:, 1:]                       # D[j, k]: del producto j al k
  inicio, fin = C[0, 1:], C[1:, 0]    # depot -> producto, producto -> depot
  total = 1 << n

  dp = np.full((total, n), np.inf)
  for j in range(n):
    dp[1 << j, j] = inicio[j]

  # cantidad de productos de cada máscara y las máscaras de cada capa
  cuenta = np.zeros(total, dtype=np.int8)
  for u in range(n):
    cuenta[1 << u: 1 << (u + 1)] = cuenta[: 1 << u] + 1
  capas = [np.flatnonzero(cuenta == s) for s in range(n + 1)]

  if poda:
    cota, eps = voraz(m)[0], 1e-9
    entrada = np.array([min(C[w][u + 1] for w in range(n + 1) if w != u + 1)
                        for u in range(n)])
    visitado = np.zeros(total)
    for u in range(n):
      visitado[1 << u: 1 << (u + 1)] = visitado[: 1 << u] + entrada[u]
    falta = entrada.sum() - visitado + fin.min()    # cota inferior de lo que resta
    ms = capas[1]
    dp[ms] = np.where(dp[ms] + falta[ms, None] > cota + eps, np.inf, dp[ms])
    vivo = np.zeros(total, dtype=bool)
    vivo[ms] = np.isfinite(dp[ms]).any(axis=1)

  for s in range(2, n + 1):
    ms = capas[s]
    for k in range(n):
      bit = 1 << k
      sel = ms[(ms & bit) != 0]
      prev = sel ^ bit
      if poda:
        ok = vivo[prev]
        sel, prev = sel[ok], prev[ok]
      if sel.size == 0:
        continue
      costo = (dp[prev] + D[:, k]).min(axis=1)
      if poda:
        costo[costo + falta[sel] > cota + eps] = np.inf
      dp[sel, k] = costo
    if poda:
      vivo[ms] = np.isfinite(dp[ms]).any(axis=1)

  completo = total - 1
  cierre = dp[completo] + fin
  j = int(np.argmin(cierre))
  mejor = float(cierre[j])
  orden, mask = [j + 1], completo
  while cuenta[mask] > 1:
    prev = mask ^ (1 << j)
    j_ant = int(np.argmin(dp[prev] + D[:, j]))
    orden.append(j_ant + 1)
    mask, j = prev, j_ant
  orden.reverse()
  return mejor, orden


# ---------------------------------------------------------------------------------------
# Selección de la técnica según el tamaño del pedido
# ---------------------------------------------------------------------------------------
def elegir_tecnica(n, umbral_fb=None, umbral_dp=None):
  """"exacta_verificada" (n <= umbral_fb), "dp" (hasta umbral_dp) o "voraz"."""
  from almacen import config
  umbral_fb = config.UMBRAL_FUERZA_BRUTA if umbral_fb is None else umbral_fb
  umbral_dp = config.UMBRAL_DP if umbral_dp is None else umbral_dp
  if n <= umbral_fb:
    return "exacta_verificada"
  if n <= umbral_dp:
    return "dp"
  return "voraz"


def resolver(m, umbral_fb=None, umbral_dp=None):
  """Resuelve un pedido con la técnica que corresponde a su tamaño.

  Devuelve (costo, orden, tecnica). Para pedidos chicos corre backtracking y Held-Karp
  optimizado y comprueba que den el mismo costo."""
  n = len(m) - 1
  tecnica = elegir_tecnica(n, umbral_fb, umbral_dp)
  if tecnica == "voraz":
    costo, orden = voraz(m)
  elif tecnica == "dp":
    costo, orden = held_karp_opt(m)
  else:
    costo, orden = held_karp_opt(m)
    costo_bt, _ = backtracking(m)
    if abs(costo - costo_bt) > 1e-6:
      raise AssertionError(f"Backtracking ({costo_bt}) y DP ({costo}) no coinciden")
  return costo, orden, tecnica
