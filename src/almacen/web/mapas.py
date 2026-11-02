"""Mapas interactivos del almacén con Plotly (versión web): hover con el nombre de cada
producto, zoom y resaltado de un producto, un grupo de productos o un pasillo."""
import plotly.graph_objects as go

from almacen import config
from almacen.web.animacion import _pasillos_xy, _rango, COLOR_PASILLO

COLOR_RESALTE = "#ffd54f"


def mapa_almacen(s, nombre, titulo, resaltar=None, pasillo=None, alto=300):
  """Plano del layout `nombre`. resaltar: productos a destacar (el resto se atenúa);
  pasillo: índice de pasillo a sombrear."""
  lo = s.layouts[nombre]
  fig = go.Figure()
  px, py = _pasillos_xy(lo)
  fig.add_trace(go.Scatter(x=px, y=py, mode="lines", line=dict(color=COLOR_PASILLO, width=1.5),
                           hoverinfo="skip", showlegend=False))
  atenuar = bool(resaltar)
  for zona in "ABC":
    prods = [p for p in lo.pasillo if s.info[p]["zona"] == zona]
    fig.add_trace(go.Scatter(
        x=[lo.pos[p][0] for p in prods], y=[lo.pos[p][1] for p in prods], mode="markers",
        marker=dict(size=4.5, color=config.COLOR_ZONA[zona], opacity=0.25 if atenuar else 1),
        name=f"{zona}: {config.NOMBRE_ZONA[zona]}",
        hovertext=[f"{s.info[p]['nombre']}<br>Pasillo {s.pasillos[nombre][lo.pasillo[p]][1]}"
                   for p in prods], hoverinfo="text"))
  if resaltar:
    prods = [p for p in resaltar if p in lo.pos]
    fig.add_trace(go.Scatter(
        x=[lo.pos[p][0] for p in prods], y=[lo.pos[p][1] for p in prods], mode="markers",
        marker=dict(size=12, color=COLOR_RESALTE, line=dict(color="#111", width=1.6)),
        hovertext=[f"{s.info[p]['nombre']}<br>Pasillo {s.pasillos[nombre][lo.pasillo[p]][1]}"
                   for p in prods], hoverinfo="text", showlegend=False))
  if pasillo is not None and 0 <= pasillo < lo.n_pasillos:
    x = pasillo * config.DIST_PASILLO
    fig.add_shape(type="rect", x0=x - 1.4, x1=x + 1.4, y0=-4, y1=lo.y_fondo + 4,
                  fillcolor=COLOR_RESALTE, opacity=0.55, line_width=0, layer="below")
  dx, dy = lo.pos["depot"]
  fig.add_trace(go.Scatter(x=[dx], y=[dy], mode="markers+text", text=["Depot"],
                           textposition="bottom center", hoverinfo="skip", showlegend=False,
                           marker=dict(symbol="square", size=10, color="#263238")))
  xr, yr = _rango(lo)
  ids = [e[1] for e in s.pasillos[nombre]]
  paso = config.DIST_PASILLO
  fig.update_xaxes(range=xr, title_text="número de pasillo", title_font_size=11, tickfont_size=9,
                   tickmode="array", tickangle=-90,
                   tickvals=[i * paso for i in range(0, lo.n_pasillos, 2)],
                   ticktext=[str(ids[i]) for i in range(0, lo.n_pasillos, 2)])
  fig.update_yaxes(range=yr, title_text="metros (al fondo)", title_font_size=11, tickfont_size=10)
  fig.update_layout(title=dict(text=titulo, font_size=14, x=0), height=alto,
                    margin=dict(l=50, r=20, t=50, b=60), plot_bgcolor="white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom"))
  return fig
