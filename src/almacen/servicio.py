"""Servicio del aplicativo: arma todo una vez (datos, G1, layouts, distancias) y ofrece lo
que necesita la interfaz: rutear un pedido con la técnica elegida, comparar técnicas y
comparar el layout actual con el optimizado. La GUI no llama a los algoritmos directamente.

Validación: los pedidos se separan en construcción (70 %) y prueba (30 %). G1 "de construcción"
y las frecuencias que arman el layout optimizado y los controles salen solo de la construcción;
el experimento rutea únicamente pedidos de prueba. G1 (`g1`) se arma con todos los pedidos y
solo sirve para describir y dibujar el grafo.

TÉCNICA: Orquesta todas las técnicas: ninguna se calcula en la interfaz, la GUI y la web solo llaman a esta clase.
"""
import random
import time
from collections import Counter
from dataclasses import dataclass, field

from almacen import afinidad, bfs, config, datos, layout, reubicacion, ruteo
from almacen.distancias import Distancias

ACTUAL, OPTIMIZADO = "actual", "optimizado"

# técnica -> (función, mayor n con el que se acepta). Los topes evitan tiempos de espera
# enormes; "dp" llega a MAX_N_DP por memoria.
TECNICAS = {
    "voraz": (ruteo.voraz, 10 ** 6),
    "fuerza_bruta": (ruteo.fuerza_bruta, 9),
    "backtracking": (ruteo.backtracking, 11),
    "dp": (ruteo.held_karp_opt, ruteo.MAX_N_DP),
    "dp_base": (ruteo.held_karp, 16),
}


@dataclass
class Resultado:
  productos: list           # product_id del pedido
  orden: list               # product_id en el orden de visita (sin el depot)
  costo: float              # metros del ciclo depot -> productos -> depot
  tecnica: str
  tiempo_s: float           # solo el tiempo del algoritmo de ruteo
  layout: str
  camino: list = field(default_factory=list)   # etiquetas de paso, de "depot" a "depot"


class Servicio:
  def __init__(self, nodos, pedidos, g1, pasillos_actual, pasillos_optimizado,
               capacidad=config.CAPACIDAD_PASILLO, pedidos_prueba=None,
               g1_construccion=None, info_construccion=None):
    self.nodos = nodos
    self.info = datos.info_productos(nodos)
    self.pedidos = pedidos
    self.g1 = g1
    # Sin separación explícita, todo se construye y se prueba con los mismos pedidos.
    self.pedidos_prueba = pedidos if pedidos_prueba is None else pedidos_prueba
    self.g1_construccion = g1 if g1_construccion is None else g1_construccion
    self.info_construccion = self.info if info_construccion is None else info_construccion
    self.pasillos = {}
    self.layouts = {}
    self.distancias = {}
    self._base = None
    self.tiempos_floyd = {}           # layout -> segundos de Floyd-Warshall
    self.capacidad = capacidad
    self.agregar_layout(ACTUAL, pasillos_actual)
    self.agregar_layout(OPTIMIZADO, pasillos_optimizado)
    self.estadisticas = self._estadisticas_agrupacion(capacidad)

  @classmethod
  def desde_csv(cls, ruta=config.RUTA_DATOS, por_zona=config.PRODUCTOS_POR_ZONA,
                umbral=config.UMBRAL_AFINIDAD, capacidad=config.CAPACIDAD_PASILLO,
                fraccion_prueba=config.FRACCION_PRUEBA, semilla=config.SEMILLA):
    """Carga el dataset y construye el servicio. Tarda unos segundos.

    fraccion_prueba: parte de los pedidos que se reserva para evaluar (0 = sin separar)."""
    d = datos.cargar_datos(ruta)
    nodos = datos.seleccionar_nodos(d, por_zona)
    pedidos = datos.pedidos_filtrados(d, nodos)
    if fraccion_prueba:
      construccion, prueba = datos.dividir_pedidos(pedidos, fraccion_prueba, semilla)
    else:
      construccion, prueba = pedidos, pedidos
    conteo = afinidad.contar_coocurrencias(construccion)
    g1_construccion = afinidad.construir_desde_conteo(nodos, conteo, umbral)
    if construccion is prueba:
      g1 = g1_construccion
    else:
      conteo.update(afinidad.contar_coocurrencias(prueba))
      g1 = afinidad.construir_desde_conteo(nodos, conteo, umbral)
    del conteo
    frecuencias = Counter(p for productos in construccion.values() for p in productos)
    nodos_construccion = nodos.copy()
    nodos_construccion["freq"] = [frecuencias.get(int(p), 0) for p in nodos["product_id"]]
    info_construccion = datos.info_productos(nodos_construccion)
    actual = datos.pasillos_desde_catalogo(nodos)
    optimizado = reubicacion.reubicar(g1_construccion, info_construccion, len(actual), capacidad)
    return cls(nodos, pedidos, g1, actual, optimizado, capacidad, pedidos_prueba=prueba,
               g1_construccion=g1_construccion, info_construccion=info_construccion)

  # ---------- layouts ----------
  def agregar_layout(self, nombre, pasillos):
    """Registra un layout sobre el mismo almacén físico (mismo largo de pasillo que el
    primero registrado)."""
    y_fondo = None if self._base is None else self._base.y_fondo
    lo = layout.construir_layout(pasillos, y_fondo=y_fondo)
    if self._base is None:
      self._base = lo
    t0 = time.perf_counter()
    dist = Distancias(lo)
    self.tiempos_floyd[nombre] = time.perf_counter() - t0
    self.pasillos[nombre] = pasillos
    self.layouts[nombre] = lo
    self.distancias[nombre] = dist

  def agregar_controles(self):
    """Agrega los layouts de control (solo frecuencia y aleatorio) si no existen."""
    if "solo_frecuencia" not in self.layouts:
      self.agregar_layout("solo_frecuencia", reubicacion.por_frecuencia(self.info_construccion, self.capacidad))
    if "aleatorio" not in self.layouts:
      self.agregar_layout("aleatorio", reubicacion.aleatorio(self.info_construccion, self.capacidad))

  def reoptimizar(self, capacidad):
    """Vuelve a ejecutar UFDS con otra capacidad por pasillo y reemplaza el layout
    optimizado. Devuelve estadísticas de la agrupación. Lanza ValueError si no cabe."""
    pasillos = reubicacion.reubicar(self.g1_construccion, self.info_construccion,
                                    self.layouts[ACTUAL].n_pasillos, capacidad)
    self.agregar_layout(OPTIMIZADO, pasillos)
    self.capacidad = capacidad
    self.estadisticas = self._estadisticas_agrupacion(capacidad)
    return self.estadisticas

  def _estadisticas_agrupacion(self, capacidad):
    grupos = reubicacion.agrupar(self.g1_construccion, capacidad)
    tamanos = [len(g) for g in grupos]
    return {"capacidad": capacidad, "grupos": len(grupos),
            "grupos_de_varios": sum(t > 1 for t in tamanos),
            "productos_en_grupos": sum(t for t in tamanos if t > 1),
            "aislados": sum(t == 1 for t in tamanos), "mayor_grupo": max(tamanos),
            "pasillos_usados": len(self.pasillos[OPTIMIZADO])}

  def alcance_bfs(self, nombre=ACTUAL):
    """(nodos alcanzados desde el depot, nodos totales) del layout, con BFS."""
    lo = self.layouts[nombre]
    visited, _ = bfs.bfs(lo.grafo, "depot")
    return sum(visited), lo.grafo.num_nodos()

  def pasillo_de(self, producto, nombre=ACTUAL):
    """Id del pasillo en el que está el producto en ese layout."""
    lo = self.layouts[nombre]
    return self.pasillos[nombre][lo.pasillo[producto]][1]

  # ---------- consultas ----------
  def descripcion(self, producto):
    d = dict(self.info[producto])
    d["pasillo_actual"] = self.pasillo_de(producto, ACTUAL)
    d["pasillo_optimizado"] = self.pasillo_de(producto, OPTIMIZADO)
    return d

  def resumen(self):
    g1, g2 = self.g1, self.layouts[ACTUAL]
    return {
        "productos": g1.num_nodos(), "pedidos": len(self.pedidos),
        "pedidos_construccion": len(self.pedidos) - len(self.pedidos_prueba)
        if self.pedidos_prueba is not self.pedidos else len(self.pedidos),
        "pedidos_prueba": len(self.pedidos_prueba),
        "aristas_g1": g1.num_aristas(), "aislados_g1": g1.num_aislados(),
        "densidad_g1": g1.densidad(), "grado_promedio_g1": g1.grado_promedio(),
        "nodos_g2": g2.grafo.num_nodos(), "aristas_g2": g2.grafo.num_aristas(),
        "pasillos": g2.n_pasillos, "pasillos_optimizado": len(self.pasillos[OPTIMIZADO]),
        "largo_pasillo_m": g2.y_fondo,
        "nodos_floyd": self.distancias[ACTUAL].red.num_nodos(),
        "tiempo_floyd_s": self.tiempos_floyd[ACTUAL],
    }

  def pedido_aleatorio(self, tamano=None, semilla=None):
    """(order_id, productos) de un pedido real, opcionalmente de un tamaño dado."""
    rnd = random.Random(semilla)
    ids = sorted(self.pedidos)
    if tamano is not None:
      ids = [i for i in ids if len(self.pedidos[i]) == tamano]
      if not ids:
        raise ValueError(f"No hay pedidos de {tamano} productos")
    oid = rnd.choice(ids)
    return oid, list(self.pedidos[oid])

  # ---------- ruteo ----------
  def rutear(self, productos, layout=ACTUAL, tecnica="auto"):
    """Ruta de picking de un pedido. tecnica: "auto" o una clave de TECNICAS."""
    productos = list(dict.fromkeys(productos))
    if not productos:
      raise ValueError("El pedido está vacío")
    lo = self.layouts[layout]
    faltan = [p for p in productos if p not in lo.pasillo]
    if faltan:
      raise ValueError(f"Productos que no están en el almacén: {faltan}")
    n = len(productos)
    dist = self.distancias[layout]
    m = dist.matriz(["depot"] + productos)

    t0 = time.perf_counter()
    if tecnica == "auto":
      costo, orden, nombre = ruteo.resolver(m)
    else:
      if tecnica not in TECNICAS:
        raise ValueError(f"Técnica desconocida: {tecnica!r}")
      funcion, n_max = TECNICAS[tecnica]
      if n > n_max:
        raise ValueError(f"{tecnica} no es viable con {n} productos (máximo {n_max})")
      costo, orden = funcion(m)
      nombre = tecnica
    tiempo = time.perf_counter() - t0

    visita = [productos[i - 1] for i in orden]
    return Resultado(productos, visita, float(costo), nombre, tiempo, layout,
                     self._camino(dist, visita))

  @staticmethod
  def _camino(dist, visita):
    puntos = ["depot"] + visita + ["depot"]
    ruta = [puntos[0]]
    for a, b in zip(puntos, puntos[1:]):
      ruta.extend(dist.camino(a, b)[1:])
    return ruta

  def comparar_tecnicas(self, productos, layout=ACTUAL):
    """Corre backtracking, DP optimizada y voraz sobre el mismo pedido.

    Devuelve {tecnica: Resultado, o None si el pedido es demasiado grande para ella}."""
    n = len(dict.fromkeys(productos))
    salida = {}
    for nombre in ("backtracking", "dp", "voraz"):
      salida[nombre] = (self.rutear(productos, layout, nombre)
                        if n <= TECNICAS[nombre][1] else None)
    return salida

  def comparar_layouts(self, productos, tecnica="auto"):
    """El mismo pedido en el layout actual y en el optimizado."""
    return {nombre: self.rutear(productos, nombre, tecnica) for nombre in (ACTUAL, OPTIMIZADO)}
