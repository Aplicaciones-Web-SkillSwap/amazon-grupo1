"""Grafo ponderado con lista de adyacencia.

Sigue la clase Graph vista en clase (04_02_Lista_Adyacencia_CA): los atributos Vertices,
label2v y G, y los métodos node/nodes/edge/edges. La diferencia es que cada arista
guarda su peso: G[u] = [(v, peso), ...], igual que el show(weighted=True) del notebook
de ordenamiento topológico.

Archivo de texto (.la), una línea por nodo, como 06vesturario.txt pero con pesos:
    # dirigido=0
    etiqueta: vecino/peso vecino/peso ...
"""


class Grafo:
  def __init__(self, dirigido=False):
    self.dirigido = dirigido
    self.Vertices = []        # etiqueta de cada nodo, por índice
    self.label2v = dict()     # etiqueta -> índice
    self.G = []               # G[u] = [(v, peso), ...] con índices

  # ---------- construcción (mismos nombres que en clase) ----------
  def node(self, label):
    if label in self.label2v:
      raise ValueError(f"El nodo {label!r} ya existe")
    self.label2v[label] = len(self.Vertices)
    self.Vertices.append(label)
    self.G.append([])
    return self.label2v[label]

  def nodes(self, labels):
    for label in labels:
      self.node(label)

  def edge(self, u, v, peso=1):
    """Agrega la arista u-v (u->v si es dirigido). No verifica duplicados."""
    iu = self.label2v[u]
    iv = self.label2v[v]
    self.G[iu].append((iv, peso))
    if not self.dirigido and iu != iv:
      self.G[iv].append((iu, peso))

  def edges(self, u, vs, peso=1):
    for v in vs:
      self.edge(u, v, peso)

  # ---------- consultas ----------
  def num_nodos(self):
    return len(self.Vertices)

  def num_aristas(self):
    total = sum(len(ady) for ady in self.G)
    if self.dirigido:
      return total
    lazos = sum(1 for u, ady in enumerate(self.G) for v, _ in ady if v == u)
    return (total - lazos) // 2 + lazos

  def densidad(self):
    n = self.num_nodos()
    if n < 2:
      return 0.0
    m = self.num_aristas()
    return m / (n * (n - 1)) if self.dirigido else 2 * m / (n * (n - 1))

  def grado_promedio(self):
    n = self.num_nodos()
    if n == 0:
      return 0.0
    m = self.num_aristas()
    return m / n if self.dirigido else 2 * m / n

  def num_aislados(self):
    return sum(1 for ady in self.G if not ady)

  def indice(self, label):
    return self.label2v[label]

  def etiqueta(self, indice):
    return self.Vertices[indice]

  def grado(self, label):
    return len(self.G[self.label2v[label]])

  def vecinos(self, label):
    return [self.Vertices[v] for v, _ in self.G[self.label2v[label]]]

  def peso(self, u, v):
    """Peso de la arista u-v, o None si no existe."""
    iv = self.label2v[v]
    for w, p in self.G[self.label2v[u]]:
      if w == iv:
        return p
    return None

  # ---------- archivo de texto ----------
  def guardar(self, ruta):
    for label in self.Vertices:
      if any(c in str(label) for c in ": /\n"):
        raise ValueError(f"Etiqueta no guardable: {label!r}")
    with open(ruta, "w", encoding="utf-8") as f:
      f.write(f"# dirigido={int(self.dirigido)}\n")
      for u, label in enumerate(self.Vertices):
        vecinos = " ".join(f"{self.Vertices[v]}/{p}" for v, p in self.G[u])
        f.write(f"{label}: {vecinos}\n")

  @staticmethod
  def cargar(ruta):
    """Lee un archivo .la. Las etiquetas numéricas se restauran como int."""
    with open(ruta, encoding="utf-8") as f:
      lineas = [linea.rstrip("\n") for linea in f]
    dirigido = False
    filas = []
    for linea in lineas:
      if linea.startswith("#"):
        dirigido = linea.replace(" ", "") == "#dirigido=1"
      elif linea.strip():
        etiqueta, resto = linea.split(":", 1)
        filas.append((_a_etiqueta(etiqueta.strip()), resto.split()))
    g = Grafo(dirigido)
    g.nodes([etiqueta for etiqueta, _ in filas])
    for etiqueta, vecinos in filas:
      u = g.label2v[etiqueta]
      for token in vecinos:
        v, p = token.split("/")
        g.G[u].append((g.label2v[_a_etiqueta(v)], _a_numero(p)))
    return g


def _a_etiqueta(texto):
  try:
    if str(int(texto)) == texto:
      return int(texto)
  except ValueError:
    pass
  return texto


def _a_numero(texto):
  try:
    return int(texto)
  except ValueError:
    return float(texto)
