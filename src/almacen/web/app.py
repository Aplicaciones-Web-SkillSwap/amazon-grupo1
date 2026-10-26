"""Versión web del aplicativo, con Streamlit:  streamlit run app_web.py

TÉCNICA: ninguna se calcula aquí. Cada pestaña llama a servicio.Servicio, que orquesta los
módulos de grafos (BFS, Floyd-Warshall), UFDS y ruteo (fuerza bruta, backtracking, programación
dinámica y voraz). Cada pestaña indica qué técnica está usando.
"""
import copy
import os
import random

import pandas as pd
import streamlit as st
from matplotlib.figure import Figure

from almacen import config, experimento
from almacen.gui import dibujo
from almacen.servicio import ACTUAL, OPTIMIZADO, Servicio
from almacen.web import textos

OPCIONES_GRAFO = {
    "G₁ completo (afinidad)": ("g1", None),
    "G₁ zona A – Frescos": ("g1", "A"),
    "G₁ zona B – Refrigerados, congelados y hogar": ("g1", "B"),
    "G₁ zona C – Abarrotes y bebidas": ("g1", "C"),
    "G₂ almacén actual": ("g2", ACTUAL),
    "G₂ almacén optimizado": ("g2", OPTIMIZADO),
}


# ------------------------------------------------------------------ servicio
def ruta_datos():
  return os.environ.get("ALMACEN_DATOS", str(config.RUTA_DATOS))


@st.cache_resource(show_spinner="Cargando el dataset y construyendo los grafos (unos segundos)…")
def servicio_base():
  """Una sola vez por proceso: lo comparten todas las sesiones, solo para lectura."""
  return Servicio.desde_csv(ruta_datos())


def servicio_propio():
  """Copia de esta sesión, para las acciones que modifican layouts (UFDS con otra K,
  layouts de control). Así un usuario no cambia lo que ven los demás."""
  if "svc" not in st.session_state:
    st.session_state["svc"] = copy.deepcopy(servicio_base())
  return st.session_state["svc"]


def servicio_actual():
  return st.session_state.get("svc") or servicio_base()


@st.cache_resource(show_spinner="Calculando la posición de los nodos de G₁…")
def posiciones_g1(zona):
  s = servicio_base()
  return dibujo.calcular_posiciones_g1(s.g1, s.info, zona)


def miles(x):
  return f"{x:,.0f}"


def figura(ancho=9, alto=5, filas=1):
  fig = Figure(figsize=(ancho, alto), layout="constrained")
  return fig, (fig.subplots(filas, 1, sharex=True) if filas > 1 else fig.subplots())


# ------------------------------------------------------------------ inicio
def pestana_inicio(s):
  st.markdown("### Cómo usar esta página")
  for paso in textos.PASOS_INICIO:
    st.markdown(paso)
  r = s.resumen()
  st.markdown("### El caso en números")
  c = st.columns(4)
  c[0].metric("Pedidos reales", miles(r["pedidos"]))
  c[1].metric("Productos (nodos de G₁)", miles(r["productos"]))
  c[2].metric("Aristas de afinidad", miles(r["aristas_g1"]))
  c[3].metric("Pasillos × largo", f"{r['pasillos']} × {r['largo_pasillo_m']:.0f} m")
  st.markdown("### Técnicas que usa el proyecto")
  st.dataframe(pd.DataFrame(textos.TECNICAS_DEL_PROYECTO,
                            columns=["Técnica", "Para qué se usa", "Dónde verla"]),
               hide_index=True, width="stretch")
  st.caption("Dataset: Instacart Market Basket Analysis (Kaggle). Complejidad Algorítmica "
             "1ACC0184, UPC 2026-20.")


# ------------------------------------------------------------------ ruteo
def pedido_inicial(s):
  try:
    return s.pedido_aleatorio(8, semilla=1)
  except ValueError:
    return s.pedido_aleatorio(None, semilla=1)


def elegir_pedido(s):
  """Controles para elegir el pedido; guarda (order_id, productos) en la sesión."""
  modo = st.radio("¿Cómo quiere elegirlo?",
                  ["Aleatorio", "Por número de pedido", "Armar uno propio"], key="modo_pedido")
  try:
    if modo == "Aleatorio":
      cualquiera = st.checkbox("De cualquier tamaño")
      tamano = st.slider("Productos del pedido", 1, 25, 8, disabled=cualquiera)
      if st.button("Obtener otro pedido"):
        st.session_state["pedido"] = s.pedido_aleatorio(
            None if cualquiera else tamano, semilla=random.randrange(10 ** 9))
    elif modo == "Por número de pedido":
      actual = st.session_state["pedido"][0]
      oid = st.number_input("Número de pedido (order_id)", min_value=0, step=1,
                            value=actual if isinstance(actual, int) else 0)
      if st.button("Usar este pedido"):
        if int(oid) not in s.pedidos:
          st.warning(f"El pedido {int(oid)} no está entre los {miles(len(s.pedidos))} pedidos "
                     "filtrados.")
        else:
          st.session_state["pedido"] = (int(oid), list(s.pedidos[int(oid)]))
    else:
      elegidos = st.multiselect("Productos (escriba para buscar)", sorted(s.info),
                                format_func=lambda p: s.info[p]["nombre"])
      if st.button("Usar mi selección"):
        if not elegidos:
          st.warning("Elija al menos un producto.")
        else:
          st.session_state["pedido"] = ("propio", list(elegidos))
  except ValueError as e:
    st.warning(str(e))
  oid, productos = st.session_state["pedido"]
  st.caption(f"Pedido {oid}: {len(productos)} productos distintos")
  return oid, productos


def tabla_visita(s, productos, layout, orden=None):
  filas = []
  for k, p in enumerate(orden or productos, start=1):
    filas.append({"Visita": k if orden else None, "Producto": s.info[p]["nombre"],
                  "Zona": s.info[p]["zona"], "Pasillo": s.pasillo_de(p, layout)})
  return pd.DataFrame(filas)


def pestana_ruteo(s):
  st.caption("Técnicas en esta pestaña: Floyd-Warshall (distancias) y fuerza bruta, backtracking, "
             "programación dinámica o voraz (orden de visita).")
  izq, der = st.columns([1, 2], gap="large")
  with izq:
    st.markdown("#### 1. Pedido")
    oid, productos = elegir_pedido(s)
    st.markdown("#### 2. Técnica")
    tecnica = textos.TECNICAS[st.selectbox("Técnica", list(textos.TECNICAS),
                                           label_visibility="collapsed")]
    st.caption(textos.AYUDA_TECNICA[tecnica])
    st.markdown("#### 3. Layout")
    layout = textos.LAYOUTS[st.radio("Layout", list(textos.LAYOUTS),
                                     label_visibility="collapsed")]
    calcular = st.button("Calcular ruta", type="primary", width="stretch")
    c1, c2 = st.columns(2)
    comparar_t = c1.button("Comparar técnicas", width="stretch")
    comparar_l = c2.button("Comparar layouts", width="stretch")

  clave = (str(oid), tuple(productos), layout, tecnica)
  if calcular:
    try:
      with st.spinner("Calculando la ruta…"):
        st.session_state["res"] = (clave, s.rutear(productos, layout, tecnica))
    except ValueError as e:
      st.warning(str(e))
  if comparar_t:
    try:
      with st.spinner("Ejecutando las tres técnicas…"):
        st.session_state["cmp_t"] = (clave[:3], s.comparar_tecnicas(productos, layout))
    except ValueError as e:
      st.warning(str(e))
  if comparar_l:
    try:
      with st.spinner("Ruteando en ambos layouts…"):
        st.session_state["cmp_l"] = ((clave[0], clave[1], tecnica),
                                     s.comparar_layouts(productos, tecnica))
    except ValueError as e:
      st.warning(str(e))

  guardado = st.session_state.get("res")
  r = guardado[1] if guardado and guardado[0] == clave else None
  with der:
    if r:
      m = st.columns(3)
      m[0].metric("Distancia total", f"{r.costo:,.0f} m")
      m[1].metric("Tiempo del algoritmo", f"{r.tiempo_s * 1000:,.1f} ms")
      m[2].metric("Técnica ejecutada", textos.NOMBRE_TECNICA.get(r.tecnica, r.tecnica))
    else:
      st.info("Pulse **Calcular ruta** para ver el recorrido de este pedido.")
    acercar = st.checkbox("Acercar a la ruta", value=False, disabled=r is None)
    fig, ax = figura(9, 5)
    lo = s.layouts[layout]
    dibujo.dibujar_almacen(ax, lo, s.info, orden=r.orden if r else None,
                           camino=r.camino if r else None, marcar=productos,
                           titulo=dibujo.nombre_layout(layout))
    if r and acercar:
      dibujo.vista_a_la_ruta(ax, lo, r.camino)
    st.pyplot(fig)
    st.caption("Los aros marcan los productos del pedido; con la ruta calculada se numeran en "
               "el orden de visita (el ciclo sale del depot y vuelve a él).")
    st.dataframe(tabla_visita(s, productos, layout, r.orden if r else None),
                 hide_index=True, width="stretch")

  g = st.session_state.get("cmp_t")
  if g and g[0] == clave[:3]:
    st.markdown("#### Comparación de técnicas sobre este pedido")
    validos = [x.costo for x in g[1].values() if x is not None]
    mejor = min(validos)
    filas = []
    for nombre, x in g[1].items():
      if x is None:
        filas.append({"Técnica": textos.NOMBRE_TECNICA[nombre], "Distancia (m)": None,
                      "Tiempo (ms)": None, "Frente a la mejor": "no viable"})
      else:
        dif = 100 * (x.costo - mejor) / mejor if mejor else 0.0
        filas.append({"Técnica": textos.NOMBRE_TECNICA[nombre], "Distancia (m)": round(x.costo),
                      "Tiempo (ms)": round(x.tiempo_s * 1000, 1),
                      "Frente a la mejor": "óptima" if dif < 1e-9 else f"+{dif:.1f} %"})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
  g = st.session_state.get("cmp_l")
  if g and g[0] == (clave[0], clave[1], tecnica):
    st.markdown("#### Comparación de layouts sobre este pedido")
    base = g[1][ACTUAL].costo
    filas = []
    for nombre, x in g[1].items():
      filas.append({"Layout": dibujo.nombre_layout(nombre), "Distancia (m)": round(x.costo),
                    "Tiempo (ms)": round(x.tiempo_s * 1000, 1),
                    "Reducción": "—" if nombre == ACTUAL or not base
                    else f"{100 * (base - x.costo) / base:+.1f} %"})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")


# ------------------------------------------------------------------ ubicación
def pestana_ubicacion(s):
  st.caption("Técnicas en esta pestaña: UFDS (agrupar productos afines, estilo Kruskal sobre G₁) "
             "y voraz (first-fit para acomodar los grupos en pasillos).")
  c = st.columns([1, 1, 3])
  k = c[0].number_input("Capacidad por pasillo (K)", min_value=config.CAPACIDAD_PASILLO,
                        max_value=60, value=int(s.capacidad), step=1,
                        help="Mínimo 16: 98 pasillos × 15 no alcanzan para 1,500 productos.")
  c[1].markdown("&nbsp;")
  if c[1].button("Ejecutar UFDS", type="primary"):
    propio = servicio_propio()
    try:
      with st.spinner("Ejecutando UFDS y reconstruyendo distancias…"):
        propio.reoptimizar(int(k))
      st.rerun()
    except ValueError as e:
      st.error(f"No se pudo reubicar: {e}")
  e = s.estadisticas
  c[2].markdown(
      f"**{miles(e['grupos_de_varios'])}** grupos de afinidad "
      f"({miles(e['productos_en_grupos'])} productos, el mayor de {e['mayor_grupo']}) + "
      f"**{miles(e['aislados'])}** productos sin grupo. Se usan **{e['pasillos_usados']}** de "
      f"{s.layouts[ACTUAL].n_pasillos} pasillos con K = {e['capacidad']}.")

  filas = []
  for _, kk, prods in s.pasillos[OPTIMIZADO]:
    filas.append({"Pasillo": kk, "Productos": len(prods),
                  "Líneas de pedido": sum(s.info[p]["freq"] for p in prods),
                  "Más pedidos": ", ".join(s.info[p]["nombre"][:22] for p in prods[:2])})
  tabla = pd.DataFrame(filas)
  izq, der = st.columns([2, 3], gap="large")
  with izq:
    st.markdown("#### Pasillos del layout optimizado")
    pasillo = st.selectbox("Resaltar un pasillo en el plano", ["Ninguno"] + list(tabla["Pasillo"]))
    st.dataframe(tabla, hide_index=True, width="stretch", height=520)
  with der:
    resaltar = None if pasillo == "Ninguno" else int(tabla.index[tabla["Pasillo"] == pasillo][0])
    fig, (ax1, ax2) = figura(9, 8, filas=2)
    dibujo.dibujar_almacen(ax1, s.layouts[ACTUAL], s.info,
                           titulo="Layout actual (pasillos y departamentos de Instacart)")
    dibujo.dibujar_almacen(ax2, s.layouts[OPTIMIZADO], s.info, resaltar=resaltar,
                           titulo=f"Layout optimizado (UFDS, K = {s.capacidad})")
    st.pyplot(fig)


# ------------------------------------------------------------------ comparación
def pestana_comparacion(s):
  st.caption("Técnicas en esta pestaña: programación dinámica (pedidos de hasta "
             f"{config.UMBRAL_DP} productos) y voraz (el resto), sobre una muestra de pedidos reales. "
             "Solo se usan pedidos de prueba (30 %): no intervinieron en armar G1 ni las frecuencias.")
  with st.form("experimento"):
    c = st.columns(3)
    n = c[0].slider("Pedidos a evaluar", 20, 1000, 200, step=20)
    semilla = c[1].number_input("Semilla", value=config.SEMILLA, step=1)
    controles = c[2].checkbox("Incluir layouts de control (solo frecuencia, aleatorio)", value=True)
    lanzar = st.form_submit_button("Ejecutar experimento", type="primary")
  st.caption("Con 200 pedidos tarda unos segundos; con 1,000 puede tardar un par de minutos.")

  if lanzar:
    propio = servicio_propio()
    barra = st.progress(0.0, text="Preparando layouts…")
    if controles:
      propio.agregar_controles()
    layouts = ([ACTUAL, OPTIMIZADO, "solo_frecuencia", "aleatorio"] if controles
               else [ACTUAL, OPTIMIZADO])
    df = experimento.correr(
        propio, int(n), int(semilla), layouts,
        progreso=lambda i, t: barra.progress(i / t, text=f"{i} de {t} pedidos"))
    barra.empty()
    res = {"df": df, "layouts": experimento.por_layout(df),
           "tamano": experimento.por_tamano(df), "brecha": experimento.brecha_voraz(df),
           "tiempos": experimento.tiempos_por_tamano(df)}
    if controles:
      res["pareado"] = experimento.comparar_pareado(df, OPTIMIZADO, "solo_frecuencia")
    st.session_state["exp"] = res

  res = st.session_state.get("exp")
  if not res:
    st.info("Pulse **Ejecutar experimento** para comparar los layouts.")
    return
  st.markdown("#### Distancia por pedido y layout")
  filas = []
  for _, f in res["layouts"].iterrows():
    base = f["layout"] == ACTUAL
    filas.append({"Layout": dibujo.nombre_layout(f["layout"]), "Media (m)": round(f["media_m"]),
                  "Reducción": "—" if base else f"−{f['reduccion_pct']:.1f} %",
                  "IC 95 %": "—" if base else f"{f['ic95_bajo']:.1f} a {f['ic95_alto']:.1f}",
                  "% de pedidos mejores": "—" if base else f"{f['mejor_pct']:.0f} %"})
  st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
  par = res.get("pareado")
  if par:
    st.markdown(
        f"Aporte de la afinidad (optimizado frente a solo frecuencia, pedido por pedido): "
        f"**{par['reduccion_pct']:.2f} %** menos distancia, IC 95 % "
        f"[{par['ic95_bajo']:.2f}, {par['ic95_alto']:.2f}] — "
        f"{'diferencia clara' if par['significativo'] else 'sin diferencia clara'}.")
  st.markdown("#### Brecha del voraz frente al óptimo (pedidos resueltos con DP)")
  st.dataframe(pd.DataFrame([
      {"Layout": dibujo.nombre_layout(f["layout"]), "Pedidos": int(f["pedidos"]),
       "Brecha media": f"{f['brecha_media_pct']:.2f} %", "Máxima": f"{f['brecha_max_pct']:.1f} %",
       "Voraz óptimo": f"{f['voraz_optimo_pct']:.0f} %"} for _, f in res["brecha"].iterrows()]),
      hide_index=True, width="stretch")
  fig = Figure(figsize=(10, 7), layout="constrained")
  grid = fig.add_gridspec(2, 2)
  dibujo.grafico_distancia_por_layout(fig.add_subplot(grid[0, 0]), res["layouts"])
  dibujo.grafico_distancia_por_tamano(fig.add_subplot(grid[0, 1]), res["tamano"])
  dibujo.grafico_tiempos(fig.add_subplot(grid[1, :]), res["tiempos"])
  st.pyplot(fig)
  st.download_button("Descargar el detalle por pedido (CSV)",
                     res["df"].to_csv(index=False).encode("utf-8"),
                     file_name="experimento_pedidos.csv", mime="text/csv")


# ------------------------------------------------------------------ grafos
def pestana_grafos(s):
  st.caption("Técnicas en esta pestaña: grafos con lista de adyacencia (G₁ y G₂), BFS y "
             "Floyd-Warshall.")
  r = s.resumen()
  alcanzados, total = s.alcance_bfs()
  c = st.columns(4)
  c[0].metric("Aristas de G₁", miles(r["aristas_g1"]))
  c[1].metric("Productos aislados", miles(r["aislados_g1"]))
  c[2].metric("BFS desde el depot", f"{miles(alcanzados)} de {miles(total)}")
  c[3].metric("Floyd-Warshall", f"{r['nodos_floyd']} nodos · {r['tiempo_floyd_s']:.2f} s")
  nombre = st.selectbox("Grafo a dibujar", list(OPCIONES_GRAFO))
  tipo, clave = OPCIONES_GRAFO[nombre]
  fig, ax = figura(9, 6)
  if tipo == "g1":
    calculo = posiciones_g1(clave)
    dibujo.dibujar_g1(ax, calculo, s.g1, s.info,
                      f"{nombre} · {miles(len(calculo['nodos']))} productos, "
                      f"{miles(len(calculo['aristas']))} aristas dibujadas")
  else:
    dibujo.dibujar_almacen(ax, s.layouts[clave], s.info, titulo=nombre)
  st.pyplot(fig)
  st.caption("G₁ se dibuja con las 3 aristas más fuertes de cada producto. En G₂ cada punto "
             "es una ubicación del almacén.")


# ------------------------------------------------------------------ main
def main():
  st.set_page_config(page_title="Almacenes inteligentes", layout="wide")
  st.title("Gestión de almacenes inteligentes")
  st.markdown("Ubique los productos de un almacén según lo que se pide junto y calcule la "
              "ruta más corta para armar cada pedido.")
  base = servicio_base()
  if "pedido" not in st.session_state:
    st.session_state["pedido"] = pedido_inicial(base)
  s = servicio_actual()
  if "svc" in st.session_state:
    st.sidebar.info("Está viendo su propia copia de la reubicación (K distinta o layouts de "
                    "control). Los demás usuarios no la ven.")
  # Mismo orden que la versión de escritorio (Datos y grafos, Ubicación, Ruteo, Comparación),
  # más una pestaña de inicio con la guía de uso.
  tabs = st.tabs(["Inicio", "Datos y grafos", "Ubicación", "Ruteo", "Comparación"])
  with tabs[0]:
    pestana_inicio(s)
  with tabs[1]:
    pestana_grafos(s)
  with tabs[2]:
    pestana_ubicacion(s)
  with tabs[3]:
    pestana_ruteo(s)
  with tabs[4]:
    pestana_comparacion(s)
