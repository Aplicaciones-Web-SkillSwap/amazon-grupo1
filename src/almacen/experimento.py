"""Experimento: compara distribuciones del almacén sobre una muestra de pedidos reales.

Los pedidos se toman solo del conjunto de prueba (los que no se usaron para armar G1 ni las
frecuencias). Cada pedido se rutea en cada layout con la técnica exacta (DP) si su tamaño llega al
umbral T, y con el voraz si no. Así la comparación entre layouts no depende de la
heurística salvo en los pedidos más grandes.

TÉCNICA: Rutea una muestra de pedidos reales con ruteo.py en cada layout de Servicio y compara las distancias (pestaña Comparación).
"""
import time

import numpy as np
import pandas as pd

from almacen import config


class Cancelado(Exception):
  """El usuario canceló el experimento."""



def correr(servicio, n_pedidos, semilla=config.SEMILLA, layouts=None, umbral_dp=None,
           progreso=None, cancelar=None):
  """Una fila por (pedido, layout): order_id, n, layout, costo, tecnica, tiempo_s,
  costo_voraz, tiempo_voraz_s.

  progreso(i, total) se llama tras cada pedido; si cancelar() devuelve True se lanza
  Cancelado."""
  import random
  umbral_dp = config.UMBRAL_DP if umbral_dp is None else umbral_dp
  layouts = layouts or list(servicio.layouts)
  ids = sorted(servicio.pedidos_prueba)
  muestra = random.Random(semilla).sample(ids, min(n_pedidos, len(ids)))
  filas = []
  for i, oid in enumerate(muestra, start=1):
    if cancelar is not None and cancelar():
      raise Cancelado()
    productos = servicio.pedidos_prueba[oid]
    n = len(productos)
    tecnica = "dp" if n <= umbral_dp else "voraz"
    for nombre in layouts:
      r = servicio.rutear(productos, nombre, tecnica)
      v = r if tecnica == "voraz" else servicio.rutear(productos, nombre, "voraz")
      filas.append({"order_id": oid, "n": n, "layout": nombre, "costo": r.costo,
                    "tecnica": tecnica, "tiempo_s": r.tiempo_s,
                    "costo_voraz": v.costo, "tiempo_voraz_s": v.tiempo_s})
    if progreso is not None:
      progreso(i, len(muestra))
  return pd.DataFrame(filas)


def _ic_reduccion(base, otro, repeticiones=1000, semilla=config.SEMILLA):
  """Reducción de la distancia total (en %) e intervalo de confianza bootstrap de 95 %."""
  rng = np.random.default_rng(semilla)
  base, otro = np.asarray(base, float), np.asarray(otro, float)
  idx = rng.integers(0, len(base), size=(repeticiones, len(base)))
  r = 100 * (1 - otro[idx].sum(axis=1) / base[idx].sum(axis=1))
  return 100 * (1 - otro.sum() / base.sum()), np.percentile(r, 2.5), np.percentile(r, 97.5)


def por_layout(df, base="actual"):
  """Resumen por layout: distancia media y reducción frente al layout base."""
  costos = df.pivot(index="order_id", columns="layout", values="costo")
  filas = []
  for nombre in costos.columns:
    c = costos[nombre]
    fila = {"layout": nombre, "pedidos": len(c), "media_m": c.mean(),
            "mediana_m": c.median(), "p90_m": c.quantile(0.9)}
    if nombre != base:
      red, lo, hi = _ic_reduccion(costos[base], c)
      fila.update(reduccion_pct=red, ic95_bajo=lo, ic95_alto=hi,
                  mejor_pct=100 * (c < costos[base]).mean(),
                  peor_pct=100 * (c > costos[base]).mean())
    filas.append(fila)
  return pd.DataFrame(filas)


def por_tamano(df, umbral_dp=None):
  """Distancia media por rango de tamaño de pedido y layout."""
  t = config.UMBRAL_DP if umbral_dp is None else umbral_dp
  limites = [0, 5, 10, 15, t, max(t, df["n"].max()) + 1]
  etiquetas = ["1-5", "6-10", "11-15", f"16-{t}", f">{t}"]
  rangos = pd.cut(df["n"], bins=limites, labels=etiquetas, right=True)
  tabla = df.assign(rango=rangos).pivot_table(
      index="rango", columns="layout", values="costo", aggfunc="mean", observed=False)
  tabla.insert(0, "pedidos", df[df["layout"] == df["layout"].iloc[0]]
               .assign(rango=rangos).groupby("rango", observed=False).size())
  return tabla


def brecha_voraz(df):
  """Cuánto más largo es el voraz que el óptimo (solo pedidos resueltos con DP)."""
  exactos = df[df["tecnica"] == "dp"].copy()
  exactos["brecha_pct"] = 100 * (exactos["costo_voraz"] - exactos["costo"]) / exactos["costo"]
  filas = []
  for nombre, g in exactos.groupby("layout"):
    filas.append({"layout": nombre, "pedidos": len(g), "brecha_media_pct": g["brecha_pct"].mean(),
                  "brecha_max_pct": g["brecha_pct"].max(),
                  "voraz_optimo_pct": 100 * (g["brecha_pct"] < 1e-9).mean()})
  return pd.DataFrame(filas)


def comparar_pareado(df, a, b):
  """Reducción (%) de la distancia total del layout `a` frente a `b`, pedido por pedido,
  con su intervalo bootstrap de 95 %. Si el intervalo contiene 0, no hay diferencia clara."""
  costos = df.pivot(index="order_id", columns="layout", values="costo")
  red, lo, hi = _ic_reduccion(costos[b], costos[a])
  return {"a": a, "b": b, "pedidos": len(costos), "reduccion_pct": red,
          "ic95_bajo": lo, "ic95_alto": hi, "significativo": not (lo <= 0 <= hi)}


def _rangos(df, umbral_dp=None):
  t = config.UMBRAL_DP if umbral_dp is None else umbral_dp
  limites = [0, 5, 10, 15, t, max(t, df["n"].max()) + 1]
  etiquetas = ["1-5", "6-10", "11-15", f"16-{t}", f">{t}"]
  return pd.cut(df["n"], bins=limites, labels=etiquetas, right=True)


def tiempos_por_tamano(df, umbral_dp=None):
  """Tiempo medio de ruteo (ms) por rango de tamaño: DP (pedidos resueltos con DP) y voraz."""
  rango = _rangos(df, umbral_dp)
  d = df.assign(rango=rango)
  dp = d[d["tecnica"] == "dp"].groupby("rango", observed=False)["tiempo_s"].mean() * 1000
  voraz = d.groupby("rango", observed=False)["tiempo_voraz_s"].mean() * 1000
  return pd.DataFrame({"dp_ms": dp, "voraz_ms": voraz})
