"""Ruteo de un pedido: ciclo más corto que sale del depot, pasa por todos los productos
del pedido y vuelve al depot (TSP sobre la matriz de distancias del pedido).

Todas las funciones reciben la matriz `m` del pedido: m[0] es el depot y m[1..n] son los
n productos. Devuelven (costo, orden) con `orden` = índices 1..n en el orden de visita
(sin repetir el depot).

  voraz         vecino más cercano          O(n^2)         no siempre óptimo
  fuerza_bruta  todas las permutaciones     O(n! * n)      óptimo
  backtracking  permutaciones con poda      O(n!) peor caso, óptimo
  held_karp     programación dinámica       O(n^2 * 2^n)   óptimo

TÉCNICA: VORAZ (voraz), FUERZA BRUTA (fuerza_bruta), BACKTRACKING (backtracking) y PROGRAMACIÓN DINÁMICA (held_karp, held_karp_opt, dividir_en_vueltas). resolver elige según el tamaño del pedido; Servicio.rutear lo invoca (pestaña Ruteo).
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


def voraz_pasos(m):
  """La misma ruta que `voraz`, pero contando cada decisión, para poder mostrarla paso a
  paso. Devuelve una lista de (actual, [(candidato, distancia), ...], elegido) con los
  candidatos ordenados del más cercano al más lejano."""
  n = len(m) - 1
  pendientes = set(range(1, n + 1))
  pasos, actual = [], 0
  while pendientes:
    candidatos = sorted(pendientes, key=lambda j: (m[actual][j], j))
    elegido = candidatos[0]
    pasos.append((actual, [(j, float(m[actual][j])) for j in candidatos], elegido))
    pendientes.remove(elegido)
    actual = elegido
  return pasos


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


def fuerza_bruta_traza(m, muestra=40):
  """La misma fuerza bruta, anotando su trabajo para poder explicarlo. Devuelve
  (costo, orden, traza) con traza = {"total": permutaciones revisadas (n!), "eventos":
  [(número, costo, orden, mejor_hasta_entonces, es_mejora), ...]}. Para no guardar n!
  rutas, los eventos son las primeras `muestra` permutaciones y, después, solo las que
  mejoran a la mejor conocida."""
  n = len(m) - 1
  mejor, mejor_orden = inf, []
  traza = {"total": 0, "eventos": []}
  if n == 0:
    return 0.0, [], traza
  for k, perm in enumerate(permutations(range(1, n + 1)), start=1):
    c = costo_ciclo(m, perm)
    es_mejora = c < mejor
    if es_mejora or k <= muestra:
      traza["eventos"].append((k, float(c), list(perm), float(min(mejor, c)), es_mejora))
    if es_mejora:
      mejor, mejor_orden = c, list(perm)
  traza["total"] = k
  return mejor, mejor_orden, traza


def backtracking_traza(m, muestra=30):
  """El mismo backtracking, anotando su trabajo para poder explicarlo. Devuelve
  (costo, orden, traza) con traza = {"inicio": (costo, orden) de la ruta voraz de partida,
  "mejoras": [(costo, orden), ...] cada vez que encontró un ciclo más corto,
  "completas": ciclos completos que llegó a evaluar, "podas": ramas abandonadas,
  "eventos": [(número, tipo, ruta, costo, mejor_conocida), ...]}.

  Un evento es un intento que terminó: tipo "poda" (ruta parcial abandonada, con su costo
  parcial), "completa" (ciclo completo que no mejora) o "mejora" (ciclo completo más
  corto). Se guardan los primeros `muestra` intentos y, después, solo las mejoras."""
  n = len(m) - 1
  if n == 0:
    return 0.0, [], {"inicio": (0.0, []), "mejoras": [], "completas": 0, "podas": 0,
                     "eventos": []}
  mejor, mejor_orden = voraz(m)
  traza = {"inicio": (float(mejor), list(mejor_orden)), "mejoras": [], "completas": 0,
           "podas": 0, "eventos": []}
  visitado = [False] * (n + 1)
  camino = []

  def anotar(tipo, costo):
    numero = traza["podas"] + traza["completas"]
    if tipo == "mejora" or numero <= muestra:
      traza["eventos"].append((numero, tipo, camino.copy(), float(costo), float(mejor)))

  def explorar(actual, costo):
    nonlocal mejor, mejor_orden
    if costo >= mejor:                       # poda
      traza["podas"] += 1
      anotar("poda", costo)
      return
    if len(camino) == n:
      traza["completas"] += 1
      total = costo + m[actual][0]
      if total < mejor:
        anotar("mejora", total)
        mejor, mejor_orden = total, camino.copy()
        traza["mejoras"].append((float(total), camino.copy()))
      else:
        anotar("completa", total)
      return
    for j in range(1, n + 1):
      if not visitado[j]:
        visitado[j] = True
        camino.append(j)
        explorar(j, costo + m[actual][j])
        camino.pop()
        visitado[j] = False

  explorar(0, 0.0)
  return mejor, mejor_orden, traza


def estados_held_karp(n):
  """Cuántos subproblemas resuelve Held-Karp por tamaño de grupo: para cada grupo de k
  productos guarda la mejor forma de recorrerlo terminando en cada uno de sus k productos,
  es decir C(n, k) * k estados. En total n * 2^(n-1), frente a n! rutas de la fuerza bruta."""
  from math import comb
  return [(k, comb(n, k) * k) for k in range(1, n + 1)]


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
# Vueltas del carrito (capacidad en kg)
# ---------------------------------------------------------------------------------------
def dividir_en_vueltas(m, orden, pesos, capacidad, max_unidades=None, cantidades=None):
  """Parte la ruta `orden` en vueltas que entren en el carrito, con la menor distancia.

  El carrito sale del depot, recoge los productos de una vuelta y regresa al depot a
  descargar antes de empezar la siguiente. Como el orden de visita ya viene dado (es la
  ruta óptima que calculó la técnica de ruteo), cada vuelta es un tramo seguido de ese
  orden y solo hay que decidir dónde cortar.

  El carrito se limita de dos formas, que se pueden usar juntas o por separado:
  `capacidad` son los kg que aguanta y `max_unidades` cuántas UNIDADES le caben (no
  productos distintos: 3 unidades de un mismo producto ocupan 3; None = sin tope). Para limitar solo por unidades, basta pasar capacidad = float("inf").

  `cantidades` dice cuántas unidades se recogen de cada índice (None = una de cada uno).
  Si de un producto se piden más unidades de las que caben, se reparten entre vueltas y
  su ubicación se visita en cada una de ellas.

  `pesos` se indexa igual que `m`: pesos[i] son los kg de UNA unidad del producto i
  (pesos[0], el depot, no se usa). Devuelve (costo_total, vueltas) con vueltas = lista de
  listas de índices, repetidos tantas veces como unidades se lleven en esa vuelta.

  Programación dinámica, O(n^2):
      mejor[i] = min sobre k de  mejor[k-1] + costo(depot -> orden[k-1..i-1] -> depot)
  tomando solo los tramos que entran en el carrito. Para cada i se recorre el inicio
  del tramo hacia atrás acumulando el peso y el tramo interno, así cada par (k, i) cuesta
  O(1) y el total es O(n^2).

  El resultado es el mejor corte *de ese orden*, que es lo que pide el enunciado; no
  rehace la ruta, así que no es necesariamente el óptimo del problema con capacidad."""
  # una entrada por unidad a recoger, en el orden de visita
  if cantidades is None:
    unidades = list(orden)
  else:
    unidades = []
    for i in orden:
      unidades.extend([i] * int(cantidades.get(i, 1)))
  n = len(unidades)
  if n == 0:
    return 0.0, []

  if max_unidades is not None and max_unidades < 1:
    raise ValueError("El carrito tiene que llevar al menos una unidad por vuelta")
  exceso = [i for i in unidades if pesos[i] > capacidad]
  if exceso:
    raise ValueError(
        f"El producto {exceso[0]} pesa {pesos[exceso[0]]:.2f} kg y el carrito aguanta "
        f"{capacidad:.2f} kg: el pedido no se puede recoger")

  mejor = [0.0] + [inf] * n
  corte = [0] * (n + 1)
  for i in range(1, n + 1):
    peso = interno = 0.0
    for k in range(i, 0, -1):                 # la vuelta cubre orden[k-1 .. i-1]
      if max_unidades is not None and i - k + 1 > max_unidades:
        break
      peso += pesos[unidades[k - 1]]
      if peso > capacidad:
        break
      if k < i:
        # si las dos unidades son del mismo producto, m[a][a] = 0 y no suma nada
        interno += m[unidades[k - 1]][unidades[k]]
      costo = m[0][unidades[k - 1]] + interno + m[unidades[i - 1]][0]
      if mejor[k - 1] + costo < mejor[i]:
        mejor[i] = mejor[k - 1] + costo
        corte[i] = k - 1

  vueltas, i = [], n
  while i > 0:
    j = corte[i]
    vueltas.append(list(unidades[j:i]))
    i = j
  vueltas.reverse()
  return mejor[n], vueltas


def peso_total(orden, pesos):
  """Kilos que suman los productos de una vuelta o de un pedido."""
  return sum(pesos[i] for i in orden)

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
