"""Versión web del aplicativo, con Streamlit:  streamlit run app_web.py

TÉCNICA: ninguna se calcula aquí. Cada pestaña llama a servicio.Servicio, que orquesta los
módulos de grafos (BFS, Floyd-Warshall), UFDS y ruteo (fuerza bruta, backtracking, programación
dinámica y voraz). Cada pestaña indica qué técnica está usando.
"""
import copy
import os
import random
from types import SimpleNamespace

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from matplotlib.figure import Figure

from almacen import config, experimento, reubicacion
from almacen.gui import dibujo
from almacen.servicio import ACTUAL, OPTIMIZADO, Servicio
from almacen.web import animacion, graficos, mapas, textos

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
  st.markdown("### En un almacén, caminar menos es ganar tiempo")
  st.markdown(
      "Armar un pedido obliga a recorrer pasillos para juntar sus productos. Esta página muestra "
      "cómo **ordenar los productos según lo que se compra junto** hace que ese recorrido sea "
      "más corto, y calcula la **ruta más corta** para cada pedido.")
  tarjetas = [c for c in textos.TARJETAS_INICIO]
  cols = st.columns(len(tarjetas), gap="medium")
  for col, (numero, titulo, texto, pestana) in zip(cols, tarjetas):
    with col.container(border=True, height=235):
      st.markdown(f"##### {numero}. {titulo}")
      st.write(texto)
      st.caption(f"Pestaña: **{pestana}**")
  r = s.resumen()
  st.markdown("#### El caso en números")
  c = st.columns(4)
  c[0].metric("Pedidos reales", miles(r["pedidos"]))
  c[1].metric("Productos", miles(r["productos"]))
  c[2].metric("Pares que se compran juntos", miles(r["aristas_g1"]))
  c[3].metric("Pasillos del almacén", f"{r['pasillos']}",
              help=f"Cada pasillo mide {r['largo_pasillo_m']:.0f} m de largo.")
  with st.expander("Técnicas de complejidad algorítmica que usa el proyecto"):
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


def ms_texto(segundos):
  """Tiempo legible: las técnicas rápidas (voraz) tardan microsegundos, no '0 ms'."""
  ms = segundos * 1000
  return f"{ms * 1000:,.0f} µs" if ms < 0.1 else f"{ms:,.1f} ms"


def tabla_visita(s, productos, layout, orden=None):
  filas = []
  for k, p in enumerate(orden or productos, start=1):
    filas.append({"Visita": k if orden else None, "Producto": s.info[p]["nombre"],
                  "Zona": s.info[p]["zona"], "Pasillo": s.pasillo_de(p, layout)})
  return pd.DataFrame(filas)


def carrera(s, clave, panes):
  """Dos recorridos animados a la vez, a la misma velocidad: llega antes el más corto."""
  fig = animacion.figura_ruta(s, panes)
  st.plotly_chart(fig, width="stretch", key=clave, config={"displaylogo": False})
  st.caption("Los dos carritos avanzan a la misma velocidad (metros por segundo): el que "
             "tiene la ruta más corta llega primero a la meta. Pulse **Reproducir**.")


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
    comparar_t = c1.button("Carrera de técnicas", width="stretch")
    comparar_l = c2.button("Carrera de layouts", width="stretch")

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
      m[1].metric("Tiempo del algoritmo", ms_texto(r.tiempo_s))
      m[2].markdown(f"<span style='font-size:0.85rem;color:#6b6b6b'>Técnica ejecutada</span><br>"
                    f"<span style='font-size:1.05rem;font-weight:600'>"
                    f"{textos.NOMBRE_TECNICA.get(r.tecnica, r.tecnica)}</span>",
                    unsafe_allow_html=True)
    else:
      st.info("Pulse **Calcular ruta** y luego **Reproducir** para ver el recorrido.")
    acercar = st.checkbox("Acercar a la ruta", value=False, disabled=r is None)
    previo = SimpleNamespace(productos=productos, orden=[], camino=["depot"], costo=0.0)
    titulo = f"Pedido {oid} · {dibujo.nombre_layout(layout)}"
    fig = animacion.figura_ruta(s, [(titulo, layout, r or previo)], acercar=acercar)
    st.plotly_chart(fig, width="stretch", key="mapa_ruta", config={"displaylogo": False})
    st.caption("Los aros negros son los productos del pedido. Con **Reproducir** el carrito "
               "sale del depot, la ruta se va trazando y cada producto se numera al recogerlo; "
               "la barra permite ir y volver, y al pasar el mouse sobre un punto aparece su "
               "nombre.")
    st.dataframe(tabla_visita(s, productos, layout, r.orden if r else None),
                 hide_index=True, width="stretch")

  g = st.session_state.get("cmp_t")
  if g and g[0] == clave[:3]:
    st.markdown("#### Carrera de técnicas sobre este pedido")
    voraz, exacta = g[1]["voraz"], g[1]["dp"] or g[1]["backtracking"]
    if voraz and exacta:
      carrera(s, "carrera_t", [("Voraz (vecino más cercano)", layout, voraz),
                               ("Programación dinámica", layout, exacta)])
      if voraz.costo - exacta.costo < 1e-6:
        st.success("Empate: en este pedido la voraz encontró una ruta tan corta como la de la "
                   "programación dinámica (pasa seguido en pedidos chicos; pruebe uno más grande).")
      else:
        st.success(f"Gana la programación dinámica: recorre {voraz.costo - exacta.costo:,.0f} m "
                   f"menos ({100 * (voraz.costo - exacta.costo) / voraz.costo:.1f} %) que la voraz.")
    else:
      st.info("Este pedido es muy grande para la programación dinámica; la tabla muestra "
              "lo que sí se pudo ejecutar.")
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
                      "Tiempo (ms)": round(x.tiempo_s * 1000, 3),
                      "Frente a la mejor": "óptima" if dif < 1e-9 else f"+{dif:.1f} %"})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
  g = st.session_state.get("cmp_l")
  if g and g[0] == (clave[0], clave[1], tecnica):
    st.markdown("#### Carrera de layouts sobre este pedido")
    base = g[1][ACTUAL].costo
    carrera(s, "carrera_l", [(f"{dibujo.nombre_layout(n)}", n, g[1][n]) for n in g[1]])
    ahorro = base - g[1][OPTIMIZADO].costo
    if ahorro > 1e-6:
      st.success(f"Gana el layout optimizado: {ahorro:,.0f} m menos ({100 * ahorro / base:.1f} %) "
                 "que el actual para este pedido.")
    elif ahorro < -1e-6:
      st.info(f"En este pedido el layout actual es {-ahorro:,.0f} m más corto; en promedio, "
              "el optimizado gana (pestaña Comparación).")
    else:
      st.success("Empate: los dos layouts recorren la misma distancia en este pedido.")
    filas = []
    for nombre, x in g[1].items():
      filas.append({"Layout": dibujo.nombre_layout(nombre), "Distancia (m)": round(x.costo),
                    "Tiempo (ms)": round(x.tiempo_s * 1000, 3),
                    "Reducción": "—" if nombre == ACTUAL or not base
                    else f"{100 * (base - x.costo) / base:+.1f} %"})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")


# ------------------------------------------------------------------ ubicación
@st.cache_data(show_spinner=False)
def pasillos_con_k(_s, k):
  """Cuántos pasillos usaría UFDS con capacidad k (solo agrupa y acomoda; no recalcula
  distancias, así que es instantáneo)."""
  try:
    return len(reubicacion.reubicar(_s.g1_construccion, _s.info_construccion,
                                    _s.layouts[ACTUAL].n_pasillos, k))
  except ValueError:
    return None


@st.cache_data(show_spinner=False)
def grupos_de_afinidad(_s, k):
  return [g for g in reubicacion.agrupar(_s.g1_construccion, k) if len(g) > 1]


def nombre_corto(s, p, n=24):
  return s.info[p]["nombre"][:n]


def pestana_ubicacion(s):
  st.markdown("### Dónde va cada producto")
  st.markdown(
      "Cada pasillo guarda un máximo de **K** productos. Primero se **juntan en grupos los "
      "productos que la gente compra a la vez** (técnica UFDS sobre el grafo de afinidad G₁) y "
      "luego cada grupo se acomoda en un pasillo, empezando por los de mayor demanda (voraz, "
      "first-fit). Así un pedido pasa por menos pasillos y camina menos.")

  st.markdown("#### 1. Elija la capacidad de cada pasillo")
  izq, der = st.columns([1, 1], gap="large")
  with izq:
    k = st.slider("Capacidad por pasillo (K)", config.CAPACIDAD_PASILLO, 60, int(s.capacidad),
                  help="Cuántos productos caben en un pasillo. Con K chico los grupos son chicos y "
                       "se usan más pasillos; con K grande los grupos crecen y se usan menos "
                       "pasillos. El mínimo es 16: 98 pasillos de 15 no alcanzan para 1,500 "
                       "productos.")
    usados = pasillos_con_k(s, k)
    total = s.layouts[ACTUAL].n_pasillos
    st.caption(f"Con K = {k} se usarían {usados} de los {total} pasillos del almacén."
               if usados else f"Con K = {k} no caben los productos.")
    if st.button("Reubicar los productos con este K", type="primary", width="stretch"):
      propio = servicio_propio()
      try:
        with st.spinner("Agrupando productos y recalculando distancias (unos segundos)…"):
          propio.reoptimizar(int(k))
        st.rerun()
      except ValueError as e:
        st.error(f"No se pudo reubicar: {e}")
    e = s.estadisticas
    m = st.columns(3)
    m[0].metric("Grupos de afinidad", miles(e["grupos_de_varios"]),
                help=f"Grupos de 2 o más productos. Hay además {miles(e['aislados'])} productos "
                     "sin grupo (no tienen compañeros frecuentes).")
    m[1].metric("Productos agrupados", miles(e["productos_en_grupos"]))
    m[2].metric("Pasillos usados", f"{e['pasillos_usados']} de {total}")
    st.caption(f"Ahora mostrado: layout optimizado con K = {e['capacidad']}.")
  with der:
    ks = list(range(config.CAPACIDAD_PASILLO, 61, 4))
    ys = [pasillos_con_k(s, x) for x in ks]
    graf = go.Figure(go.Scatter(x=ks, y=ys, mode="lines+markers", line=dict(color="#6a1b9a"),
                                hovertemplate="K = %{x}: %{y} pasillos<extra></extra>"))
    graf.add_trace(go.Scatter(x=[k], y=[usados], mode="markers", hoverinfo="skip",
                              marker=dict(size=14, color="#e53935", line=dict(color="white",
                                                                              width=2))))
    graf.update_layout(title=dict(text="Pasillos usados según K", font_size=14, x=0),
                       height=250, showlegend=False, margin=dict(l=50, r=10, t=45, b=45),
                       plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    graf.update_xaxes(title_text="K (productos por pasillo)", title_font_size=11)
    graf.update_yaxes(title_text="pasillos usados", title_font_size=11)
    st.plotly_chart(graf, width="stretch", key="grafico_k", config={"displaylogo": False})

  st.markdown("#### 2. Explore el resultado")
  modo = st.radio("¿Qué quiere ver?", ["Un grupo de productos", "Un producto", "Un pasillo"],
                  horizontal=True, label_visibility="collapsed")
  resaltar, pasillo, mensaje, detalle = None, None, None, None
  if modo == "Un grupo de productos":
    grupos = grupos_de_afinidad(s, int(s.capacidad))[:20]
    if not grupos:
      st.info("No hay grupos de afinidad con esta configuración.")
    else:
      def etiqueta(i):
        top = sorted(grupos[i], key=lambda p: -s.info[p]["freq"])[:2]
        return (f"Grupo {i + 1}: {nombre_corto(s, top[0])}, {nombre_corto(s, top[1])}… "
                f"({len(grupos[i])} productos)")
      i = st.selectbox("Grupo (de los más grandes)", range(len(grupos)), format_func=etiqueta)
      resaltar = grupos[i]
      antes = len({s.layouts[ACTUAL].pasillo[p] for p in resaltar})
      ahora = len({s.layouts[OPTIMIZADO].pasillo[p] for p in resaltar})
      mensaje = (f"Estos {len(resaltar)} productos se piden juntos. En el almacén actual estaban "
                 f"repartidos en **{antes} pasillos**; en el optimizado quedan en **{ahora}**.")
      detalle = pd.DataFrame([{"Producto": s.info[p]["nombre"], "Zona": s.info[p]["zona"],
                               "Pasillo actual": s.pasillo_de(p, ACTUAL),
                               "Pasillo optimizado": s.pasillo_de(p, OPTIMIZADO)}
                              for p in resaltar])
  elif modo == "Un producto":
    p = st.selectbox("Producto (escriba para buscar)", sorted(s.info),
                     format_func=lambda x: s.info[x]["nombre"])
    resaltar = [p]
    mensaje = (f"**{s.info[p]['nombre']}** (zona {s.info[p]['zona']}, "
               f"{miles(s.info[p]['freq'])} líneas de pedido): estaba en el pasillo "
               f"**{s.pasillo_de(p, ACTUAL)}** y ahora está en el **{s.pasillo_de(p, OPTIMIZADO)}**.")
  else:
    opciones = list(range(len(s.pasillos[OPTIMIZADO])))
    pasillo = st.selectbox(
        "Pasillo del layout optimizado", opciones,
        format_func=lambda i: f"Pasillo {s.pasillos[OPTIMIZADO][i][1]} "
                              f"({len(s.pasillos[OPTIMIZADO][i][2])} productos)")
    zona, idp, prods = s.pasillos[OPTIMIZADO][pasillo]
    resaltar = None
    mensaje = f"El pasillo **{idp}** (zona {zona}) guarda {len(prods)} productos."
    detalle = pd.DataFrame([{"Producto": s.info[p]["nombre"], "Zona": s.info[p]["zona"],
                             "Líneas de pedido": s.info[p]["freq"]} for p in prods])
  if mensaje:
    st.info(mensaje)
  st.plotly_chart(mapas.mapa_almacen(s, ACTUAL, "Layout actual (pasillos de Instacart)", resaltar),
                  width="stretch", key="mapa_ubic_actual", config={"displaylogo": False})
  st.plotly_chart(mapas.mapa_almacen(s, OPTIMIZADO, f"Layout optimizado (UFDS, K = {s.capacidad})",
                                     resaltar, pasillo),
                  width="stretch", key="mapa_ubic_opt", config={"displaylogo": False})
  st.caption("Pase el mouse sobre un punto para ver el producto y su pasillo; con la rueda o "
             "arrastrando puede acercar el plano.")
  if detalle is not None:
    st.dataframe(detalle, hide_index=True, width="stretch")
  with st.expander("Ver la tabla de todos los pasillos del layout optimizado"):
    filas = [{"Pasillo": kk, "Productos": len(prods),
              "Líneas de pedido": sum(s.info[p]["freq"] for p in prods),
              "Más pedidos": ", ".join(s.info[p]["nombre"][:22] for p in prods[:2])}
             for _, kk, prods in s.pasillos[OPTIMIZADO]]
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch", height=400)


# ------------------------------------------------------------------ comparación
def pestana_comparacion(s):
  st.markdown("### ¿Cuánto camino se ahorra?")
  st.markdown(
      "Se toma una **muestra de pedidos reales** y se calcula la ruta de cada uno en el almacén "
      "actual y en el optimizado. Al final se comparan los metros recorridos.")
  with st.form("experimento"):
    n = st.slider("¿Cuántos pedidos quiere comparar?", 20, 1000, 200, step=20,
                  help="Con 200 pedidos tarda unos segundos; con 1,000 puede tardar un par de "
                       "minutos.")
    with st.expander("Opciones avanzadas"):
      semilla = st.number_input("Semilla (para repetir la misma muestra)", value=config.SEMILLA,
                                step=1)
      controles = st.checkbox("Incluir layouts de control (solo frecuencia y aleatorio)",
                              value=True)
    lanzar = st.form_submit_button("Comparar los almacenes", type="primary")
  st.caption("Solo se usan pedidos de prueba (30 % del total): no intervinieron en armar el "
             "grafo de afinidad ni las frecuencias del layout optimizado.")

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
    st.info("Elija la cantidad de pedidos y pulse **Comparar los almacenes**.")
    return
  filas = res["layouts"].set_index("layout")
  actual, opt = filas.loc[ACTUAL], filas.loc[OPTIMIZADO]
  m = st.columns(4)
  m[0].metric("Almacén actual", f"{actual['media_m']:,.0f} m", help="Distancia media por pedido.")
  m[1].metric("Almacén optimizado", f"{opt['media_m']:,.0f} m",
              delta=f"-{opt['reduccion_pct']:.1f} %", delta_color="inverse")
  m[2].metric("Se ahorra por pedido", f"{actual['media_m'] - opt['media_m']:,.0f} m")
  m[3].metric("Pedidos que mejoran", f"{opt['mejor_pct']:.0f} %",
              help="Porcentaje de pedidos que recorren menos metros con el layout optimizado.")

  st.plotly_chart(graficos.barras_layouts(res["layouts"]), width="stretch", key="g_layouts",
                  config={"displaylogo": False})
  par = res.get("pareado")
  if par:
    rango = f"entre {par['ic95_bajo']:.2f} % y {par['ic95_alto']:.2f} % (intervalo de confianza de 95 %)"
    if par["significativo"]:
      st.info("Ordenar los productos solo por popularidad ya acorta casi todo el camino. Agregar "
              f"la afinidad (que se compren juntos) mejora **{par['reduccion_pct']:.2f} %** más, "
              f"con un aporte {rango}.")
    else:
      st.info("Ordenar los productos solo por popularidad ya acorta casi todo el camino. Con esta "
              f"muestra, agregar la afinidad no marca una diferencia clara: el aporte está {rango}. "
              "Con más pedidos la estimación se afina.")
  izq, der = st.columns(2, gap="large")
  with izq:
    st.plotly_chart(graficos.dispersion_pedidos(res["df"]), width="stretch", key="g_dispersion",
                    config={"displaylogo": False})
  with der:
    st.plotly_chart(graficos.barras_tamano(res["tamano"]), width="stretch", key="g_tamano",
                    config={"displaylogo": False})
  st.caption("Pase el mouse sobre cualquier barra o punto para ver el detalle (en el gráfico de "
             "puntos, el número de pedido y cuántos productos tenía).")

  with st.expander("Detalle técnico: voraz frente a programación dinámica y tiempos"):
    st.markdown("**¿Qué tan buena es la ruta voraz?** Se compara con la ruta óptima en los "
                f"pedidos de hasta {config.UMBRAL_DP} productos (los que resuelve la programación "
                "dinámica).")
    st.dataframe(pd.DataFrame([
        {"Layout": dibujo.nombre_layout(f["layout"]), "Pedidos": int(f["pedidos"]),
         "Brecha media": f"{f['brecha_media_pct']:.2f} %", "Máxima": f"{f['brecha_max_pct']:.1f} %",
         "Ruta voraz igual a la óptima": f"{f['voraz_optimo_pct']:.0f} %"}
        for _, f in res["brecha"].iterrows()]), hide_index=True, width="stretch")
    st.plotly_chart(graficos.barras_tiempos(res["tiempos"]), width="stretch", key="g_tiempos",
                    config={"displaylogo": False})
    st.caption("Técnicas: programación dinámica (pedidos de hasta "
               f"{config.UMBRAL_DP} productos) y voraz (el resto).")
  st.download_button("Descargar el detalle por pedido (CSV)",
                     res["df"].to_csv(index=False).encode("utf-8"),
                     file_name="experimento_pedidos.csv", mime="text/csv")


# ------------------------------------------------------------------ grafos
def pestana_grafos(s):
  st.markdown("### Los dos mapas del problema")
  st.markdown(
      "**G₁ (afinidad):** une con una línea los productos que la gente compra en el mismo "
      "pedido. **G₂ (almacén):** es el plano real, con pasillos y ubicaciones. Con G₁ se decide "
      "dónde poner cada producto y con G₂ se calcula cuánto hay que caminar.")
  r = s.resumen()
  alcanzados, total = s.alcance_bfs()
  c = st.columns(4)
  c[0].metric("Productos", miles(r["productos"]))
  c[1].metric("Pares que se compran juntos", miles(r["aristas_g1"]),
              help="Aristas de G₁ (lista de adyacencia ponderada).")
  c[2].metric("Productos sin compañeros", miles(r["aislados_g1"]),
              help="Nodos aislados de G₁: casi nunca se piden junto a otro.")
  c[3].metric("Ubicaciones alcanzables", f"{miles(alcanzados)} de {miles(total)}",
              help="BFS desde el depot: comprueba que se puede llegar a todo el almacén.")

  st.markdown("#### G₁: qué productos se compran juntos")
  izq, der = st.columns([3, 2], gap="large")
  with izq:
    zona = st.radio("Zona del almacén", ["Todas", "A: Frescos", "B: Refrigerados, congelados y hogar",
                                         "C: Abarrotes y bebidas"], horizontal=True)
    clave = None if zona == "Todas" else zona[0]
  calculo = posiciones_g1(clave)
  with der:
    producto = st.selectbox("Busque un producto para ver con qué se compra", [None] + sorted(
        calculo["nodos"]), format_func=lambda p: "Ninguno" if p is None else s.info[p]["nombre"])
  fig, vecinos = graficos.grafo_afinidad(s, calculo, producto)
  st.plotly_chart(fig, width="stretch", key="grafo_g1", config={"displaylogo": False})
  if producto is None:
    st.caption("Cada punto es un producto (más grande = se compra con más productos) y su color "
               "indica la zona. Pase el mouse para ver su nombre, acerque con la rueda, o elija "
               "un producto arriba para resaltar sus compañeros de compra. Se dibujan las 3 "
               "conexiones más fuertes de cada producto.")
  else:
    st.markdown(f"**{s.info[producto]['nombre']}** se compra más seguido con:")
    st.dataframe(pd.DataFrame([{"Producto": s.info[p]["nombre"], "Zona": s.info[p]["zona"],
                                "Pedidos juntos": w} for p, w in vecinos]),
                 hide_index=True, width="stretch")

  st.markdown("#### G₂: el plano del almacén")
  opcion = st.radio("Almacén", ["Actual", "Optimizado"], horizontal=True)
  nombre = ACTUAL if opcion == "Actual" else OPTIMIZADO
  st.plotly_chart(mapas.mapa_almacen(s, nombre, f"Almacén {opcion.lower()}"), width="stretch",
                  key="mapa_g2", config={"displaylogo": False})
  st.caption("Vista desde arriba: cada columna es un pasillo, cada punto una ubicación con su "
             "producto, y el cuadrado negro es el depot, donde empieza y termina cada recorrido.")
  with st.expander("Detalle técnico"):
    st.markdown("Técnicas: grafos con lista de adyacencia (G₁ y G₂), BFS y Floyd-Warshall.")
    st.markdown(f"- **Floyd-Warshall:** {r['nodos_floyd']} nodos (cruces de pasillo y depot), "
                f"calculado en {r['tiempo_floyd_s']:.2f} s. Da la distancia mínima entre "
                "cualquier par de cruces.\n"
                f"- **G₂:** {miles(r['nodos_g2'])} nodos y {miles(r['aristas_g2'])} aristas.\n"
                f"- **G₁:** densidad {r['densidad_g1']:.4f} y grado promedio "
                f"{r['grado_promedio_g1']:.1f}.")


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
