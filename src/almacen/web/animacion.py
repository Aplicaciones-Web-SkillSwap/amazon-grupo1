"""Animación del recorrido de picking con Plotly (solo la versión web).

Dibuja el plano del almacén y, al pulsar Reproducir, el operario sale del depot y la ruta se va
trazando tramo a tramo; los productos del pedido se numeran al recogerse y un contador
muestra los metros. Con dos paneles es una "carrera": los dos recorridos avanzan a la
misma velocidad (metros por cuadro), así que el más corto llega primero a la meta.

No toca los algoritmos: solo recibe el `Resultado` que ya calculó el servicio. La
animación corre en el navegador (cuadros de Plotly), sin volver a ejecutar Streamlit.
"""
import math
from bisect import bisect_right

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from almacen import config

COLOR_RUTA = "#e53935"
COLOR_PASILLO = "#cfd8dc"
CUADROS = 110          # cuadros de la animación del recorrido más largo
EXTRA_FINAL = 8        # cuadros quietos al terminar, para que se vea la meta
MS_POR_CUADRO = 55


def _trayecto(lo, camino):
  """Puntos (x, y) del camino y los metros acumulados hasta cada uno."""
  puntos = [lo.pos[e] for e in camino]
  acum = [0.0]
  for (x0, y0), (x1, y1) in zip(puntos, puntos[1:]):
    acum.append(acum[-1] + math.hypot(x1 - x0, y1 - y0))
  return puntos, acum


def _llegadas(camino, orden, acum):
  """Metros recorridos al llegar a cada producto del pedido, en el orden de visita."""
  salida, k = [], 0
  for i, etiqueta in enumerate(camino):
    if k < len(orden) and etiqueta == orden[k]:
      salida.append(acum[i])
      k += 1
  salida += [acum[-1]] * (len(orden) - len(salida))
  return salida


def _hasta(puntos, acum, d):
  """Parte del camino recorrida a los `d` metros: (xs, ys) y la posición actual."""
  i = bisect_right(acum, d)          # puntos[:i] ya se pasaron
  xs = [p[0] for p in puntos[:i]]
  ys = [p[1] for p in puntos[:i]]
  if i < len(puntos) and i > 0:
    tramo = acum[i] - acum[i - 1]
    t = (d - acum[i - 1]) / tramo if tramo > 0 else 0.0
    xs.append(xs[-1] + t * (puntos[i][0] - xs[-1]))
    ys.append(ys[-1] + t * (puntos[i][1] - ys[-1]))
  return xs, ys


def _pasillos_xy(lo):
  """Todas las líneas de pasillo como una sola traza (None separa los tramos)."""
  paso, y = config.DIST_PASILLO, lo.y_fondo
  x_max = (lo.n_pasillos - 1) * paso
  xs, ys = [-paso, x_max, None, 0, x_max, None], [0, 0, None, y, y, None]
  for i in range(lo.n_pasillos):
    xs += [i * paso, i * paso, None]
    ys += [0, y, None]
  return xs, ys


def _rango(lo, camino=None, margen=10.0):
  x_max = (lo.n_pasillos - 1) * config.DIST_PASILLO
  if camino:
    xs, ys = zip(*[lo.pos[e] for e in camino])
    return [min(xs) - margen, max(xs) + margen], [min(ys) - margen, max(ys) + margen]
  return [-8, x_max + 6], [-6, lo.y_fondo + 14]


def figura_ruta(s, panes, acercar=False, alto_panel=360):
  """Figura animada. panes: lista de (título, layout, Resultado) — uno para el recorrido
  de un pedido, dos para la carrera."""
  n = len(panes)
  fig = make_subplots(rows=n, cols=1, subplot_titles=[p[0] for p in panes],
                      vertical_spacing=0.16 if n > 1 else 0.05)
  datos = []             # por panel: puntos, acumulados, llegadas, orden, total
  dinamicas = []         # índices de las trazas que cambian en cada cuadro
  for j, (_, nombre, r) in enumerate(panes, start=1):
    lo = s.layouts[nombre]
    puntos, acum = _trayecto(lo, r.camino)
    datos.append((puntos, acum, _llegadas(r.camino, r.orden, acum), r))

    px, py = _pasillos_xy(lo)
    fig.add_trace(go.Scatter(x=px, y=py, mode="lines", line=dict(color=COLOR_PASILLO, width=1.5),
                             hoverinfo="skip", showlegend=False), row=j, col=1)
    for zona in "ABC":
      prods = [p for p in lo.pasillo if s.info[p]["zona"] == zona]
      fig.add_trace(go.Scatter(
          x=[lo.pos[p][0] for p in prods], y=[lo.pos[p][1] for p in prods], mode="markers",
          marker=dict(size=4, color=config.COLOR_ZONA[zona]), name=f"{zona}: {config.NOMBRE_ZONA[zona]}",
          legendgroup=zona, showlegend=(j == 1),
          hovertext=[f"{s.info[p]['nombre']}<br>Pasillo {lo.pasillo[p] + 1}" for p in prods],
          hoverinfo="text"), row=j, col=1)
    dx, dy = lo.pos["depot"]
    fig.add_trace(go.Scatter(x=[dx], y=[dy], mode="markers+text", text=["Depot"],
                             textposition="bottom center", hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="square", size=11, color="#263238")),
                  row=j, col=1)
    fig.add_trace(go.Scatter(
        x=[lo.pos[p][0] for p in r.productos], y=[lo.pos[p][1] for p in r.productos],
        mode="markers", marker=dict(size=13, color="rgba(0,0,0,0)", line=dict(color="#111", width=1.6)),
        hovertext=[s.info[p]["nombre"] for p in r.productos], hoverinfo="text",
        showlegend=False), row=j, col=1)

    for dato in _cuadro(datos[-1], lo, 0.0):          # trazas dinámicas, estado inicial
      fig.add_trace(dato, row=j, col=1)
      dinamicas.append(len(fig.data) - 1)

  total_max = max(d[1][-1] for d in datos)
  alto = alto_panel * n
  if total_max <= 0:                 # todavía no hay ruta: solo el plano y el pedido
    for j, (_, nombre, _r) in enumerate(panes, start=1):
      xr, yr = _rango(s.layouts[nombre])
      fig.update_xaxes(range=xr, title_text="metros (a lo ancho)", title_font_size=11,
                       tickfont_size=10, row=j, col=1)
      fig.update_yaxes(range=yr, title_text="metros (al fondo)", title_font_size=11,
                       tickfont_size=10, row=j, col=1)
    fig.update_layout(height=alto + 40, margin=dict(l=50, r=20, t=80, b=50),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
                      legend=dict(orientation="h", x=0, xanchor="left", y=1 + 45 / alto,
                                  yanchor="bottom"))
    return fig
  paso = max(total_max / CUADROS, 0.5)
  n_cuadros = int(math.ceil(total_max / paso)) + EXTRA_FINAL
  frames, pasos_slider = [], []
  for f in range(n_cuadros + 1):
    d = f * paso
    trazas = []
    for j, (_, nombre, _r) in enumerate(panes):
      trazas += _cuadro(datos[j], s.layouts[nombre], d)
    frames.append(go.Frame(data=trazas, traces=dinamicas, name=str(f)))
    pasos_slider.append(dict(method="animate", label="", args=[
        [str(f)], dict(mode="immediate", frame=dict(duration=0, redraw=False),
                       transition=dict(duration=0))]))
  fig.frames = frames

  for j, (_, nombre, r) in enumerate(panes, start=1):
    xr, yr = _rango(s.layouts[nombre], r.camino if (acercar and n == 1) else None)
    fig.update_xaxes(range=xr, title_text="metros (a lo ancho)", title_font_size=11,
                     tickfont_size=10, row=j, col=1)
    fig.update_yaxes(range=yr, title_text="metros (al fondo)", title_font_size=11,
                     tickfont_size=10, row=j, col=1)

  y_ctrl = -62 / alto
  anim = lambda cuadro_ms, **kw: dict(frame=dict(duration=cuadro_ms, redraw=False),
                                       transition=dict(duration=0), **kw)
  fig.update_layout(
      height=alto + 130, margin=dict(l=50, r=20, t=80, b=100),
      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
      legend=dict(orientation="h", x=0, xanchor="left", y=1 + 45 / alto, yanchor="bottom"),
      updatemenus=[dict(type="buttons", direction="left", x=0, xanchor="left", y=y_ctrl,
                        yanchor="top", showactive=False, pad=dict(t=8, r=8), buttons=[
          dict(label="Reproducir", method="animate",
               args=[None, anim(MS_POR_CUADRO, fromcurrent=True, mode="immediate")]),
          dict(label="Pausar", method="animate",
               args=[[None], anim(0, mode="immediate")]),
          dict(label="Reiniciar", method="animate",
               args=[["0"], anim(0, mode="immediate")])])],
      sliders=[dict(steps=pasos_slider, x=0.34, len=0.66, xanchor="left", y=y_ctrl,
                    yanchor="top", pad=dict(t=0, b=0), ticklen=0, minorticklen=0,
                    currentvalue=dict(visible=False), font=dict(color="rgba(0,0,0,0)"))])
  return fig


def _cuadro(dato, lo, d):
  """Las 4 trazas dinámicas de un panel a los `d` metros: trayecto, productos recogidos
  (numerados), operario y contador de metros."""
  puntos, acum, llegadas, r = dato
  total = acum[-1]
  xs, ys = _hasta(puntos, acum, d)
  recogidos = [k for k, a in enumerate(llegadas) if a <= d + 1e-9]
  fin = d >= total - 1e-9
  texto = f"Terminó: {total:,.0f} m" if fin else f"{min(d, total):,.0f} m"
  if total <= 0:
    texto = "Pulse «Calcular ruta»"
  y_tope = lo.y_fondo + 9
  return [
      go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=COLOR_RUTA, width=3),
                 hoverinfo="skip", showlegend=False),
      go.Scatter(x=[lo.pos[r.orden[k]][0] for k in recogidos],
                 y=[lo.pos[r.orden[k]][1] for k in recogidos], mode="markers+text",
                 text=[str(k + 1) for k in recogidos], textfont=dict(color="white", size=10),
                 marker=dict(size=17, color=COLOR_RUTA, line=dict(color="white", width=1)),
                 hoverinfo="skip", showlegend=False),
      go.Scatter(x=[xs[-1]], y=[ys[-1]], mode="markers",
                 marker=dict(size=16, color="#ffd54f", line=dict(color="#263238", width=2.5)),
                 hoverinfo="skip", showlegend=False),
      go.Scatter(x=[-4], y=[y_tope], mode="text", text=[f"<b>{texto}</b>"],
                 textposition="middle right", textfont=dict(size=15, color="#263238"),
                 hoverinfo="skip", showlegend=False),
  ]
