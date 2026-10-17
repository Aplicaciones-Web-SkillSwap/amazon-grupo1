"""Compara el layout actual con el optimizado (y dos controles) sobre pedidos reales.

Uso (desde la raíz del repo, con el venv activo):
    python scripts/experimento.py [--pedidos 1000] [--semilla 42]

Controles: "solo_frecuencia" (sin afinidad) y "aleatorio" (16 productos por pasillo al azar).
Escribe los resultados en salida/.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd                                    # noqa: E402

from almacen import config, experimento, reubicacion   # noqa: E402
from almacen.servicio import Servicio                  # noqa: E402


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--pedidos", type=int, default=1000)
  ap.add_argument("--semilla", type=int, default=config.SEMILLA)
  args = ap.parse_args()

  print("Cargando datos y construyendo layouts...", flush=True)
  s = Servicio.desde_csv()
  s.agregar_layout("solo_frecuencia", reubicacion.por_frecuencia(s.info))
  s.agregar_layout("aleatorio", reubicacion.aleatorio(s.info, semilla=args.semilla))
  print(f"Rutando {args.pedidos} pedidos en {len(s.layouts)} layouts (T = {config.UMBRAL_DP})...",
        flush=True)
  df = experimento.correr(s, args.pedidos, args.semilla)

  pd.set_option("display.width", 200)
  resumen = experimento.por_layout(df)
  tamano = experimento.por_tamano(df)
  brecha = experimento.brecha_voraz(df)
  print("\n== Distancia por pedido y layout (metros) ==")
  print(resumen.round(2).to_string(index=False))
  print("\n== Distancia media por tamaño de pedido ==")
  print(tamano.round(1).to_string())
  print("\n== Brecha del voraz frente al óptimo (pedidos resueltos con DP) ==")
  print(brecha.round(2).to_string(index=False))

  par = experimento.comparar_pareado(df, "optimizado", "solo_frecuencia")
  print("\n== Aporte de la afinidad: optimizado frente a solo_frecuencia (pareado) ==")
  print(f"reducción {par['reduccion_pct']:.2f} %  IC95 [{par['ic95_bajo']:.2f}, "
        f"{par['ic95_alto']:.2f}]  -> "
        f"{'diferencia clara' if par['significativo'] else 'sin diferencia clara'}")

  config.RUTA_SALIDA.mkdir(exist_ok=True)
  df.to_csv(config.RUTA_SALIDA / "experimento_pedidos.csv", index=False)
  resumen.to_csv(config.RUTA_SALIDA / "experimento_layouts.csv", index=False)
  tamano.to_csv(config.RUTA_SALIDA / "experimento_tamano.csv")
  brecha.to_csv(config.RUTA_SALIDA / "experimento_brecha_voraz.csv", index=False)
  print(f"\nResultados guardados en {config.RUTA_SALIDA}")


if __name__ == "__main__":
  main()
