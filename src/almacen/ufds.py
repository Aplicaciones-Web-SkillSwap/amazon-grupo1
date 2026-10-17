"""UFDS (Union-Find) con Quick-Union ponderado, como en clase.

parent[i] >= 0 es el padre de i; en una raíz guarda el tamaño del conjunto en negativo
(parent[r] = -tamaño). La unión cuelga la raíz menor de la mayor, así que find cuesta
O(log n).
"""


class UFDS:
  def __init__(self, n):
    self.parent = [-1] * n

  def find(self, x):
    while self.parent[x] >= 0:
      x = self.parent[x]
    return x

  def tam(self, x):
    """Tamaño del conjunto de x, en O(1) una vez hallada la raíz."""
    return -self.parent[self.find(x)]

  def mismo_conjunto(self, a, b):
    return self.find(a) == self.find(b)

  def union(self, a, b, limite=None):
    """Une los conjuntos de a y b. Devuelve True si los unió.

    Si `limite` no es None, no los une cuando el conjunto resultante superaría `limite`."""
    ra, rb = self.find(a), self.find(b)
    if ra == rb:
      return False
    if limite is not None and -self.parent[ra] - self.parent[rb] > limite:
      return False
    if self.parent[ra] > self.parent[rb]:        # ra es el menor (menos negativo)
      ra, rb = rb, ra
    self.parent[ra] += self.parent[rb]
    self.parent[rb] = ra
    return True

  def conjuntos(self):
    """Lista de conjuntos (listas de índices), cada uno en orden creciente."""
    grupos = {}
    for x in range(len(self.parent)):
      grupos.setdefault(self.find(x), []).append(x)
    return list(grupos.values())
