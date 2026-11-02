"""Gráficos interactivos (Plotly) de la pestaña Comparación: pensados para entenderse de
un vistazo, con el valor escrito sobre cada barra y el detalle al pasar el mouse."""
import plotly.graph_objects as go

from almacen.gui.dibujo import COLOR_LAYOUT, nombre_layout

ACTUAL, OPTIMIZADO = "actual", "optimizado"


def _corto(nombre):
  return nombre_layout(nombre).split(" (")[0]


def _base(fig, alto, titulo):
  fig.update_layout(title=dict(text=titulo, font_size=15, x=0), height=alto,
                    margin=dict(l=10, r=20, t=55, b=45), plot_bgcolor="white",
                    paper_bgcolor="rgba(0,0,0,0)", font_size=12)
  return fig


def barras_layouts(resumen):
  """Distancia media por pedido en cada layout (el mejor, abajo)."""
  f = resumen.sort_values("media_m", ascending=False)
  nombres = [_corto(n) for n in f["layout"]]
  textos = [f"{m:,.0f} m" if n == ACTUAL else f"{m:,.0f} m  (−{r:.1f} %)"
            for n, m, r in zip(f["layout"], f["media_m"], f["reduccion_pct"])]
  fig = go.Figure(go.Bar(
      x=f["media_m"], y=nombres, orientation="h", text=textos, textposition="outside",
      marker_color=[COLOR_LAYOUT.get(n, "#90a4ae") for n in f["layout"]],
      hovertemplate="%{y}: %{x:,.0f} m por pedido<extra></extra>"))
  fig.update_xaxes(range=[0, f["media_m"].max() * 1.35], title_text="metros recorridos por pedido (promedio)",
                   showgrid=True, gridcolor="#eceff1")
  fig.update_yaxes(automargin=True)
  return _base(fig, 120 + 55 * len(f), "¿Cuántos metros se camina por pedido?")


def dispersion_pedidos(df):
  """Cada punto es un pedido: distancia con el layout actual (x) y con el optimizado (y).
  Los puntos por debajo de la diagonal son pedidos que mejoraron."""
  p = df.pivot_table(index=["order_id", "n"], columns="layout", values="costo").reset_index()
  x, y = p[ACTUAL], p[OPTIMIZADO]
  tope = float(max(x.max(), y.max())) * 1.05
  fig = go.Figure()
  for nombre, mask, color in (("Mejoran", y < x - 1e-6, "#2e7d32"),
                              ("Igual", (y - x).abs() <= 1e-6, "#9e9e9e"),
                              ("Empeoran", y > x + 1e-6, "#c62828")):
    q = p[mask]
    fig.add_trace(go.Scatter(
        x=q[ACTUAL], y=q[OPTIMIZADO], mode="markers", name=f"{nombre} ({len(q)})",
        marker=dict(size=6, color=color, opacity=0.55),
        customdata=q[["order_id", "n"]].to_numpy(),
        hovertemplate=("Pedido %{customdata[0]} (%{customdata[1]} productos)<br>"
                       "Actual: %{x:,.0f} m<br>Optimizado: %{y:,.0f} m<extra></extra>")))
  fig.add_trace(go.Scatter(x=[0, tope], y=[0, tope], mode="lines", hoverinfo="skip",
                           line=dict(color="#455a64", dash="dash", width=1), showlegend=False))
  fig.update_xaxes(range=[0, tope], title_text="metros con el layout actual", gridcolor="#eceff1")
  fig.update_yaxes(range=[0, tope], title_text="metros con el layout optimizado",
                   gridcolor="#eceff1")
  fig.update_layout(legend=dict(orientation="h", x=0, y=-0.22))
  return _base(fig, 430, "Cada punto es un pedido (debajo de la línea: mejoró)")


def barras_tamano(tamano):
  """Distancia media según cuántos productos tiene el pedido."""
  capas = [c for c in tamano.columns if c != "pedidos"]
  fig = go.Figure()
  etiquetas = [f"{r} productos<br>({int(n)} pedidos)" for r, n in zip(tamano.index, tamano["pedidos"])]
  for nombre in capas:
    fig.add_trace(go.Bar(x=etiquetas, y=tamano[nombre], name=_corto(nombre),
                         marker_color=COLOR_LAYOUT.get(nombre, "#90a4ae"),
                         hovertemplate=f"{_corto(nombre)}: " + "%{y:,.0f} m<extra></extra>"))
  fig.update_layout(barmode="group", legend=dict(orientation="h", x=0, y=-0.28))
  fig.update_yaxes(title_text="metros por pedido (promedio)", gridcolor="#eceff1")
  return _base(fig, 400, "Los pedidos grandes son los que más se benefician")


def barras_tiempos(tiempos):
  """Tiempo de cálculo de las dos técnicas según el tamaño del pedido (escala log)."""
  etiquetas = [f"{r} productos" for r in tiempos.index]
  fig = go.Figure()
  fig.add_trace(go.Bar(x=etiquetas, y=tiempos["dp_ms"], name="Programación dinámica",
                       marker_color="#6a1b9a", hovertemplate="%{y:,.2f} ms<extra></extra>"))
  fig.add_trace(go.Bar(x=etiquetas, y=tiempos["voraz_ms"], name="Voraz",
                       marker_color="#ffa726", hovertemplate="%{y:,.3f} ms<extra></extra>"))
  fig.update_layout(barmode="group", legend=dict(orientation="h", x=0, y=-0.28))
  fig.update_yaxes(type="log", title_text="milisegundos (escala log)", gridcolor="#eceff1")
  return _base(fig, 360, "Tiempo de cálculo por técnica")


def grafo_afinidad(s, calculo, producto=None, n_vecinos=10):
  """G₁ (o una zona) como red interactiva: cada punto es un producto y cada línea une dos
  productos que se compran juntos. Si se elige un producto, se resaltan sus compañeros
  más frecuentes. Devuelve (figura, lista de (vecino, veces juntos))."""
  from almacen import config
  pos, aristas, nodos = calculo["pos"], calculo["aristas"], calculo["nodos"]
  g1 = s.g1
  fig = go.Figure()
  ex, ey = [], []
  for u, v in aristas:
    ex += [pos[u][0], pos[v][0], None]
    ey += [pos[u][1], pos[v][1], None]
  fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(90,90,90,0.18)", width=0.6),
                           hoverinfo="skip", showlegend=False))
  elegido = producto is not None and producto in pos
  for zona in "ABC":
    zs = [p for p in nodos if s.info[p]["zona"] == zona]
    if zs:
      fig.add_trace(go.Scatter(
          x=[pos[p][0] for p in zs], y=[pos[p][1] for p in zs], mode="markers",
          name=f"{zona}: {config.NOMBRE_ZONA[zona]}",
          marker=dict(size=[3.5 + 1.1 * g1.grado(p) ** 0.5 for p in zs],
                      color=config.COLOR_ZONA[zona], opacity=0.25 if elegido else 0.75),
          hovertext=[f"{s.info[p]['nombre']}<br>Se compra junto con {g1.grado(p)} productos"
                     for p in zs], hoverinfo="text"))
  vecinos = []
  if elegido:
    i = g1.indice(producto)
    fuertes = sorted(((w, g1.etiqueta(v)) for v, w in g1.G[i]), reverse=True)[:n_vecinos]
    vecinos = [(p, w) for w, p in fuertes]
    cerca = [(p, w) for p, w in vecinos if p in pos]
    lx, ly = [], []
    for p, _ in cerca:
      lx += [pos[producto][0], pos[p][0], None]
      ly += [pos[producto][1], pos[p][1], None]
    fig.add_trace(go.Scatter(x=lx, y=ly, mode="lines", line=dict(color="#e53935", width=2),
                             hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=[pos[p][0] for p, _ in cerca], y=[pos[p][1] for p, _ in cerca], mode="markers",
        marker=dict(size=13, color="#ffd54f", line=dict(color="#111", width=1.5)),
        hovertext=[f"{s.info[p]['nombre']}<br>Comprados juntos en {w} pedidos" for p, w in cerca],
        hoverinfo="text", showlegend=False))
    fig.add_trace(go.Scatter(
        x=[pos[producto][0]], y=[pos[producto][1]], mode="markers",
        marker=dict(size=17, color="#e53935", line=dict(color="white", width=2)),
        hovertext=[s.info[producto]["nombre"]], hoverinfo="text", showlegend=False))
  import numpy as np
  xs = np.array([pos[p][0] for p in nodos])
  ys = np.array([pos[p][1] for p in nodos])
  x0, x1 = np.percentile(xs, [0.5, 99.5])
  y0, y1 = np.percentile(ys, [0.5, 99.5])
  mx, my = 0.15 * (x1 - x0), 0.15 * (y1 - y0)
  if elegido:                       # que el producto elegido siempre quede a la vista
    x0, x1 = min(x0, pos[producto][0] - mx), max(x1, pos[producto][0] + mx)
    y0, y1 = min(y0, pos[producto][1] - my), max(y1, pos[producto][1] + my)
  fig.update_xaxes(visible=False, range=[x0 - mx, x1 + mx])
  fig.update_yaxes(visible=False, range=[y0 - my, y1 + my])
  fig.update_layout(height=620, margin=dict(l=5, r=5, t=10, b=5), plot_bgcolor="white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom"))
  return fig, vecinos
