"""«Así piensa el algoritmo»: animaciones paso a paso de las decisiones del ruteo
(versión web, Plotly).

  figura_voraz         en cada paso mide la distancia a los productos que faltan y va al
                       más cercano.
  figura_fuerza_bruta  arma una ruta completa tras otra, sin descartar ninguna.
  figura_backtracking  arma rutas producto por producto y abandona las que ya van peor
                       que la mejor conocida (poda).
  figura_estados_dp    cuántos casos pequeños resuelve la programación dinámica.

Las decisiones no se calculan aquí: vienen de Servicio.explicar_ruteo, que ejecuta los
mismos algoritmos del proyecto anotando lo que hacen.
"""
import plotly.graph_objects as go

from almacen import config
from almacen.web.animacion import COLOR_PASILLO, COLOR_RUTA, _pasillos_xy, _rango

VERDE = "#2e7d32"
GRIS = "#607d8b"
MS_POR_PASO = 1500


def _nombre(s, etiqueta, n=30):
  return "el depot" if etiqueta == "depot" else s.info[etiqueta]["nombre"][:n]


def _recorrido(dist, lo, puntos):
  """Coordenadas del camino real (por los pasillos) que une `puntos` en ese orden."""
  ruta = [puntos[0]]
  for a, b in zip(puntos, puntos[1:]):
    ruta.extend(dist.camino(a, b)[1:])
  return [lo.pos[e][0] for e in ruta], [lo.pos[e][1] for e in ruta]


def _plano(s, layout, productos):
  """Figura con lo que no cambia: pasillos, productos (atenuados), depot y el pedido."""
  lo = s.layouts[layout]
  fig = go.Figure()
  px, py = _pasillos_xy(lo)
  fig.add_trace(go.Scatter(x=px, y=py, mode="lines", line=dict(color=COLOR_PASILLO, width=1.5),
                           hoverinfo="skip", showlegend=False))
  for zona in "ABC":
    prods = [p for p in lo.pasillo if s.info[p]["zona"] == zona]
    fig.add_trace(go.Scatter(
        x=[lo.pos[p][0] for p in prods], y=[lo.pos[p][1] for p in prods], mode="markers",
        marker=dict(size=4, color=config.COLOR_ZONA[zona], opacity=0.3), hoverinfo="skip",
        showlegend=False))
  dx, dy = lo.pos["depot"]
  fig.add_trace(go.Scatter(x=[dx], y=[dy], mode="markers+text", text=["Depot"],
                           textposition="bottom center", hoverinfo="skip", showlegend=False,
                           marker=dict(symbol="square", size=11, color="#263238")))
  fig.add_trace(go.Scatter(
      x=[lo.pos[p][0] for p in productos], y=[lo.pos[p][1] for p in productos], mode="markers",
      marker=dict(size=13, color="rgba(0,0,0,0)", line=dict(color="#111", width=1.6)),
      hovertext=[s.info[p]["nombre"] for p in productos], hoverinfo="text", showlegend=False))
  return fig, lo


def _mensaje(lo, texto):
  return go.Scatter(x=[-4], y=[lo.y_fondo + 9], mode="text", text=[f"<b>{texto}</b>"],
                    textposition="middle right", textfont=dict(size=14, color="#263238"),
                    hoverinfo="skip", showlegend=False)


def _numerados(lo, visitados, color=COLOR_RUTA):
  return go.Scatter(x=[lo.pos[p][0] for p in visitados], y=[lo.pos[p][1] for p in visitados],
                    mode="markers+text", text=[str(k) for k in range(1, len(visitados) + 1)],
                    textfont=dict(color="white", size=10), hoverinfo="skip", showlegend=False,
                    marker=dict(size=17, color=color, line=dict(color="white", width=1)))


def _linea(x, y, color, ancho=3, opacidad=1.0):
  return go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=ancho),
                    opacity=opacidad, hoverinfo="skip", showlegend=False)


def _contador(lo, texto):
  """Segundo renglón de texto, bajo el mensaje principal."""
  return go.Scatter(x=[-4], y=[lo.y_fondo + 3.5], mode="text", text=[texto],
                    textposition="middle right", textfont=dict(size=12, color="#455a64"),
                    hoverinfo="skip", showlegend=False)


def _animar(fig, lo, cuadros, ms=MS_POR_PASO, alto=420):
  """Convierte la lista de cuadros (cada uno, la lista de trazas dinámicas) en una
  animación con botones y barra de pasos."""
  base = len(fig.data)
  for traza in cuadros[0]:
    fig.add_trace(traza)
  dinamicas = list(range(base, len(fig.data)))
  fig.frames = [go.Frame(data=c, traces=dinamicas, name=str(i)) for i, c in enumerate(cuadros)]
  quieto = dict(mode="immediate", frame=dict(duration=0, redraw=False),
                transition=dict(duration=0))
  xr, yr = _rango(lo)
  fig.update_xaxes(range=xr, title_text="metros (a lo ancho)", title_font_size=11, tickfont_size=10)
  fig.update_yaxes(range=yr, title_text="metros (al fondo)", title_font_size=11, tickfont_size=10)
  y_ctrl = -62 / alto
  fig.update_layout(
      height=alto + 110, margin=dict(l=50, r=20, t=20, b=100), plot_bgcolor="white",
      paper_bgcolor="rgba(0,0,0,0)",
      updatemenus=[dict(type="buttons", direction="left", x=0, xanchor="left", y=y_ctrl,
                        yanchor="top", showactive=False, pad=dict(t=8, r=8), buttons=[
          dict(label="Reproducir", method="animate",
               args=[None, dict(mode="immediate", fromcurrent=True, transition=dict(duration=0),
                                frame=dict(duration=ms, redraw=False))]),
          dict(label="Pausar", method="animate", args=[[None], quieto]),
          dict(label="Reiniciar", method="animate", args=[["0"], quieto])])],
      sliders=[dict(steps=[dict(method="animate", label="", args=[[str(i)], quieto])
                           for i in range(len(cuadros))],
                    x=0.34, len=0.66, xanchor="left", y=y_ctrl, yanchor="top",
                    pad=dict(t=0, b=0), ticklen=0, minorticklen=0,
                    currentvalue=dict(visible=False), font=dict(color="rgba(0,0,0,0)"))])
  return fig


# ------------------------------------------------------------------ voraz
def figura_voraz(s, layout, productos, pasos, ms=MS_POR_PASO):
  """Dos cuadros por decisión: primero las distancias a todos los productos que faltan y
  luego el elegido (el más cercano). `pasos` viene de ruteo.voraz_pasos."""
  fig, lo = _plano(s, layout, productos)
  dist = s.distancias[layout]
  puntos = ["depot"] + list(productos)             # índice de la matriz -> etiqueta
  visitados, cuadros = [], []

  def cuadro(actual, candidatos, elegido, texto):
    xa, ya = lo.pos[actual]
    lx, ly = [], []
    for p, _ in candidatos:
      lx += [xa, lo.pos[p][0], None]
      ly += [ya, lo.pos[p][1], None]
    ex, ey = ([xa, lo.pos[elegido][0]], [ya, lo.pos[elegido][1]]) if elegido else ([], [])
    tx, ty = _recorrido(dist, lo, ["depot"] + visitados)
    return [
        go.Scatter(x=tx, y=ty, mode="lines", line=dict(color=COLOR_RUTA, width=3),
                   hoverinfo="skip", showlegend=False),
        go.Scatter(x=lx, y=ly, mode="lines", line=dict(color="#78909c", width=1.2, dash="dot"),
                   hoverinfo="skip", showlegend=False),
        go.Scatter(x=ex, y=ey, mode="lines", line=dict(color=VERDE, width=4),
                   hoverinfo="skip", showlegend=False),
        go.Scatter(x=[lo.pos[p][0] for p, _ in candidatos],
                   y=[lo.pos[p][1] + 3.5 for p, _ in candidatos], mode="text",
                   text=[f"<b>{d:,.0f} m</b>" if p == elegido else f"{d:,.0f} m"
                         for p, d in candidatos],
                   textposition="top center", hoverinfo="skip", showlegend=False,
                   textfont=dict(size=12, color=[VERDE if p == elegido else "#37474f"
                                                 for p, _ in candidatos])),
        _numerados(lo, visitados),
        go.Scatter(x=[xa], y=[ya], mode="markers", hoverinfo="skip", showlegend=False,
                   marker=dict(size=16, color="#ffd54f", line=dict(color="#263238", width=2.5))),
        _mensaje(lo, texto),
    ]

  for k, (actual, candidatos, elegido) in enumerate(pasos, start=1):
    a, e = puntos[actual], puntos[elegido]
    cands = [(puntos[j], d) for j, d in candidatos]
    faltan = "al único producto que falta" if len(cands) == 1 else \
        f"a los {len(cands)} productos que faltan"
    cuadros.append(cuadro(a, cands, None,
                          f"Paso {k}: está en {_nombre(s, a)}. Mide la distancia {faltan}."))
    cuadros.append(cuadro(a, cands, e,
                          f"Paso {k}: va a {_nombre(s, e)}, el más cercano "
                          f"({cands[0][1]:,.0f} m caminando)."))
    visitados.append(e)
  ciclo = ["depot"] + visitados + ["depot"]
  total = float(sum(dist.entre(a, b) for a, b in zip(ciclo, ciclo[1:])))
  fin = cuadro("depot", [], None, f"Ya recogió todo y vuelve al depot. Total: {total:,.0f} m.")
  tx, ty = _recorrido(dist, lo, ciclo)
  fin[0] = go.Scatter(x=tx, y=ty, mode="lines", line=dict(color=COLOR_RUTA, width=3),
                      hoverinfo="skip", showlegend=False)
  cuadros.append(fin)
  return _animar(fig, lo, cuadros, ms), total


# ------------------------------------------------------------------ fuerza bruta
def figura_fuerza_bruta(s, layout, productos, traza, ms=400):
  """Una ruta completa por cuadro: en gris la que está probando (verde si es la nueva
  mejor) y, debajo, la mejor encontrada hasta ese momento. `traza` viene de
  ruteo.fuerza_bruta_traza."""
  fig, lo = _plano(s, layout, productos)
  dist = s.distancias[layout]
  total = traza["total"]

  def ruta(orden):
    visita = [productos[i - 1] for i in orden]
    return visita, _recorrido(dist, lo, ["depot"] + visita + ["depot"])

  cuadros, mejor_orden, anterior = [], None, 0
  for numero, costo, orden, mejor, es_mejora in traza["eventos"]:
    visita, (tx, ty) = ruta(orden)
    bx, by = ruta(mejor_orden)[1] if mejor_orden else ([], [])
    salto = f" (saltó {numero - anterior - 1:,} rutas que no mejoraban)" \
        if numero - anterior > 1 else ""
    if es_mejora:
      texto = f"Ruta {numero:,} de {total:,}: mide {costo:,.0f} m, es la mejor hasta ahora."
      mejor_orden = orden
    else:
      texto = f"Ruta {numero:,} de {total:,}: mide {costo:,.0f} m, no mejora."
    cuadros.append([_linea(bx, by, VERDE, 6, 0.35),
                    _linea(tx, ty, VERDE if es_mejora else GRIS),
                    _numerados(lo, visita, VERDE if es_mejora else GRIS),
                    _mensaje(lo, texto),
                    _contador(lo, f"Mejor hasta ahora: {mejor:,.0f} m{salto}")])
    anterior = numero
  visita, (tx, ty) = ruta(mejor_orden)
  costo = min(e[1] for e in traza["eventos"])
  cuadros.append([_linea([], [], VERDE, 6, 0.35), _linea(tx, ty, VERDE, 4),
                  _numerados(lo, visita, VERDE),
                  _mensaje(lo, f"Revisó las {total:,} rutas posibles, una por una."),
                  _contador(lo, f"La más corta mide {costo:,.0f} m")])
  return _animar(fig, lo, cuadros, ms)


# ------------------------------------------------------------------ backtracking
DETALLADOS = 4       # primeros intentos que se muestran armándose producto por producto


def figura_backtracking(s, layout, productos, traza, ms=900):
  """Cada cuadro es un intento: la ruta se arma producto por producto y se pinta de rojo
  si se abandona (poda), de gris si se completa sin mejorar y de verde si es la nueva
  mejor. La mejor conocida queda de fondo. `traza` viene de ruteo.backtracking_traza."""
  fig, lo = _plano(s, layout, productos)
  dist = s.distancias[layout]

  def tramo(orden, cerrar):
    visita = [productos[i - 1] for i in orden]
    return visita, _recorrido(dist, lo, ["depot"] + visita + (["depot"] if cerrar else []))

  def parcial(orden):
    paradas = ["depot"] + [productos[i - 1] for i in orden]
    return sum(dist.entre(a, b) for a, b in zip(paradas, paradas[1:]))

  def cuadro(mejor_orden, orden, cerrar, color, texto, pie):
    bx, by = tramo(mejor_orden, True)[1]
    visita, (tx, ty) = tramo(orden, cerrar)
    return [_linea(bx, by, VERDE, 6, 0.35), _linea(tx, ty, color),
            _numerados(lo, visita, color), _mensaje(lo, texto), _contador(lo, pie)]

  mejor, mejor_orden = traza["inicio"]
  cuadros = [cuadro(mejor_orden, mejor_orden, True, VERDE,
                    f"Punto de partida: la ruta voraz, {mejor:,.0f} m.",
                    "Ahora prueba otros órdenes de visita para ver si hay una más corta.")]
  podas = completas = anterior = 0
  exacto = True
  for numero, tipo, orden, costo, conocida in traza["eventos"]:
    if numero - anterior > 1:                       # hubo intentos sin mejora no guardados
      exacto = False
    pie = lambda: (f"Intentos: {numero:,} · descartados a medias: {podas:,} · "
                   f"rutas completas: {completas:,} · mejor: {mejor:,.0f} m" if exacto
                   else f"Intentos: {numero:,} · mejor: {mejor:,.0f} m")
    if numero <= DETALLADOS:                        # se ve cómo arma la ruta
      for k in range(1, len(orden)):
        cuadros.append(cuadro(mejor_orden, orden[:k], False, GRIS,
                              f"Intento {numero:,}: va armando la ruta, lleva "
                              f"{parcial(orden[:k]):,.0f} m.", pie()))
    if tipo == "poda":
      podas += 1
      cuadros.append(cuadro(mejor_orden, orden, False, COLOR_RUTA,
                            f"Intento {numero:,}: descartado. Con {len(orden)} productos ya "
                            f"lleva {costo:,.0f} m y la mejor mide {conocida:,.0f} m.", pie()))
    elif tipo == "completa":
      completas += 1
      cuadros.append(cuadro(mejor_orden, orden, True, GRIS,
                            f"Intento {numero:,}: ruta completa de {costo:,.0f} m, no mejora "
                            f"a la de {conocida:,.0f} m.", pie()))
    else:
      completas += 1
      mejor, mejor_orden = costo, orden
      cuadros.append(cuadro(orden, orden, True, VERDE,
                            f"Intento {numero:,}: nueva mejor ruta, {costo:,.0f} m "
                            f"(la anterior medía {conocida:,.0f} m).", pie()))
    anterior = numero
  total = traza["podas"] + traza["completas"]
  cuadros.append(cuadro(mejor_orden, mejor_orden, True, VERDE,
                        f"Terminó: la ruta más corta mide {mejor:,.0f} m.",
                        f"Intentos: {total:,} · descartados a medias: {traza['podas']:,} · "
                        f"rutas completas: {traza['completas']:,}"))
  return _animar(fig, lo, cuadros, ms)


# ------------------------------------------------------------------ programación dinámica
def figura_estados_dp(estados):
  """Barras: cuántos casos resuelve Held-Karp para los grupos de 1, 2, ..., n productos."""
  fig = go.Figure(go.Bar(
      x=[f"{k}" for k, _ in estados], y=[e for _, e in estados], marker_color="#6a1b9a",
      text=[f"{e:,}" for _, e in estados], textposition="outside",
      hovertemplate="Grupos de %{x} productos: %{y:,} casos<extra></extra>"))
  fig.update_xaxes(title_text="productos en el grupo", title_font_size=11)
  fig.update_yaxes(title_text="casos resueltos", title_font_size=11, gridcolor="#eceff1",
                   range=[0, max(e for _, e in estados) * 1.18])
  fig.update_layout(title=dict(text="Casos que resuelve, del grupo más chico al pedido completo",
                               font_size=14, x=0),
                    height=300, margin=dict(l=50, r=20, t=50, b=45), plot_bgcolor="white",
                    paper_bgcolor="rgba(0,0,0,0)")
  return fig
