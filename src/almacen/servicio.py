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
  vueltas: list = field(default_factory=list)  # una por viaje del carrito: productos, kg y metros
  costo_total: float = 0.0                     # metros de todas las vueltas (= costo si es una sola)
  capacidad_kg: float = config.CAPACIDAD_CARRITO_KG
  max_unidades: int = config.CAPACIDAD_CARRITO_UNIDADES
  omitidos: list = field(default_factory=list)   # productos del pedido que no tenían stock
  stock_tope: int = config.STOCK_PRODUCTO_TOP


class Servicio:
  def __init__(self, nodos, pedidos, g1, pasillos_actual, pasillos_optimizado,
               capacidad=config.CAPACIDAD_PASILLO, pedidos_prueba=None,
               g1_construccion=None, info_construccion=None, pesos=None):
    self.nodos = nodos
    self.pesos = pesos
    self.info = datos.info_productos(nodos, pesos)
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
    pesos = datos.cargar_pesos(ruta)
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
    info_construccion = datos.info_productos(nodos_construccion, pesos)
    actual = datos.pasillos_desde_catalogo(nodos)
    optimizado = reubicacion.reubicar(g1_construccion, info_construccion, len(actual), capacidad)
    return cls(nodos, pedidos, g1, actual, optimizado, capacidad, pedidos_prueba=prueba,
               g1_construccion=g1_construccion, info_construccion=info_construccion,
               pesos=pesos)

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
  def stock(self, tope=None):
    """Unidades en almacén de cada producto (datos.calcular_stock)."""
    tope = config.STOCK_PRODUCTO_TOP if tope is None else int(tope)
    return datos.calcular_stock(self.info, tope)

  def peso_pedido(self, productos):
    """Kilos que suma un pedido."""
    return sum(self.info[p]["peso"] for p in dict.fromkeys(productos))

  def rutear(self, productos, layout=ACTUAL, tecnica="auto", capacidad_kg=None,
             max_unidades=None, stock_tope=None):
    """Ruta de picking de un pedido. tecnica: "auto" o una clave de TECNICAS.

    El carrito se limita por peso (`capacidad_kg`) y por cantidad de productos
    (`max_unidades`); se pueden usar juntos o por separado. Si el pedido no entra, la
    ruta se parte en varias vueltas que pasan por el depot a descargar
    (ruteo.dividir_en_vueltas). Para quitar un tope, pasar float("inf") o None.

    `stock_tope` son las unidades del producto más pedido; el stock del resto es
    proporcional a su demanda. Los productos del pedido que no tengan stock se omiten de
    la ruta y quedan en Resultado.omitidos."""
    productos = list(dict.fromkeys(productos))
    if not productos:
      raise ValueError("El pedido está vacío")
    lo = self.layouts[layout]
    faltan = [p for p in productos if p not in lo.pasillo]
    if faltan:
      raise ValueError(f"Productos que no están en el almacén: {faltan}")

    # el stock se mira después de comprobar que el producto existe, para no confundir
    # "no está en el almacén" con "está agotado"
    tope_stock = config.STOCK_PRODUCTO_TOP if stock_tope is None else int(stock_tope)
    disponible = self.stock(tope_stock)
    omitidos = [p for p in productos if disponible[p] < 1]
    productos = [p for p in productos if disponible[p] >= 1]
    if not productos:
      raise ValueError(
          f"Ningún producto del pedido tiene stock con un tope de {tope_stock} unidades")
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

    capacidad = config.CAPACIDAD_CARRITO_KG if capacidad_kg is None else float(capacidad_kg)
    tope_unidades = config.CAPACIDAD_CARRITO_UNIDADES if max_unidades is None else max_unidades
    tope_unidades = None if tope_unidades in (None, float("inf")) else int(tope_unidades)
    kilos = [0.0] + [self.info[p]["peso"] for p in productos]
    costo_total, cortes = ruteo.dividir_en_vueltas(m, orden, kilos, capacidad, tope_unidades)

    visita = [productos[i - 1] for i in orden]
    vueltas, camino = [], []
    for indices in cortes:
      prods = [productos[i - 1] for i in indices]
      paso = self._camino(dist, prods)
      vueltas.append({"productos": prods, "unidades": len(prods),
                      "kg": round(ruteo.peso_total(indices, kilos), 2),
                      "metros": float(ruteo.costo_ciclo(m, indices)),
                      "camino": paso})
      camino.extend(paso if not camino else paso[1:])
    return Resultado(productos, visita, float(costo), nombre, tiempo, layout,
                     camino, vueltas, float(costo_total), capacidad, tope_unidades,
                     omitidos, tope_stock)

  @staticmethod
  def _camino(dist, visita):
    puntos = ["depot"] + visita + ["depot"]
    ruta = [puntos[0]]
    for a, b in zip(puntos, puntos[1:]):
      ruta.extend(dist.camino(a, b)[1:])
    return ruta

  def explicar_ruteo(self, productos, layout=ACTUAL, tecnica="voraz"):
    """Lo que hace una técnica sobre un pedido, para mostrarlo paso a paso. Según `tecnica`
    devuelve: "voraz" -> ruteo.voraz_pasos; "fuerza_bruta" y "backtracking" -> la traza de
    ruteo.fuerza_bruta_traza / backtracking_traza; "dp" -> ruteo.estados_held_karp.
    Los índices 1..n se refieren a `productos` en el orden recibido (0 es el depot)."""
    productos = list(dict.fromkeys(productos))
    n = len(productos)
    if tecnica == "dp":
      return ruteo.estados_held_karp(n)
    if tecnica not in ("voraz", "fuerza_bruta", "backtracking"):
      raise ValueError(f"Técnica sin paso a paso: {tecnica!r}")
    if n > TECNICAS[tecnica][1]:
      raise ValueError(f"{tecnica} no es viable con {n} productos (máximo {TECNICAS[tecnica][1]})")
    m = [[float(x) for x in fila] for fila in self.distancias[layout].matriz(["depot"] + productos)]
    if tecnica == "voraz":
      return ruteo.voraz_pasos(m)
    if tecnica == "fuerza_bruta":
      return ruteo.fuerza_bruta_traza(m)[2]
    return ruteo.backtracking_traza(m)[2]

  def tramos(self, resultado):
    """La ruta de un Resultado, tramo por tramo: lista de dicts con la vuelta a la que
    pertenece, desde, hasta (etiquetas: "depot" o product_id), metros del tramo y metros
    acumulados."""
    dist = self.distancias[resultado.layout]
    filas, acumulado = [], 0.0
    for n_vuelta, vuelta in enumerate(resultado.vueltas, start=1):
      paradas = ["depot"] + list(vuelta["productos"]) + ["depot"]
      for a, b in zip(paradas, paradas[1:]):
        metros = float(dist.entre(a, b))
        acumulado += metros
        filas.append({"vuelta": n_vuelta, "desde": a, "hasta": b, "metros": metros,
                      "acumulado": acumulado})
    return filas

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
