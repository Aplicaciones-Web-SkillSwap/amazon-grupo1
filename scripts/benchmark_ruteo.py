"""Mide los tiempos de las técnicas de ruteo sobre pedidos reales y calibra el umbral T.

Uso (desde la raíz del repo, con el venv activo):
    python scripts/benchmark_ruteo.py [--limite 1.0] [--por-tamano 5] [--max-n 20]

Escribe salida/benchmark_ruteo.csv y muestra el T sugerido para config.UMBRAL_DP.
"""
import argparse
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from almacen import benchmark, config, datos, layout, ruteo   # noqa: E402
from almacen.distancias import Distancias                       # noqa: E402

TECNICAS = [
    # nombre, función, tamaño máximo con el que se mide
    ("voraz", ruteo.voraz, 99),
    ("backtracking", ruteo.backtracking, 11),
    ("held_karp_base", ruteo.held_karp, 16),
    ("held_karp_opt", lambda m: ruteo.held_karp_opt(m, poda=False), 99),
    ("held_karp_opt_poda", lambda m: ruteo.held_karp_opt(m, poda=True), 99),
]


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--limite", type=float, default=1.0, help="segundos máximos por pedido")
  ap.add_argument("--por-tamano", type=int, default=5, help="pedidos reales por tamaño")
  ap.add_argument("--min-n", type=int, default=4)
  ap.add_argument("--max-n", type=int, default=20)
  args = ap.parse_args()

  d = datos.cargar_datos()
  nodos = datos.seleccionar_nodos(d)
  pedidos = datos.pedidos_filtrados(d, nodos)
  dist = Distancias(layout.construir_layout(datos.pasillos_desde_catalogo(nodos)))

  por_tamano = {}
  for prods in pedidos.values():
    por_tamano.setdefault(len(prods), []).append(prods)
  rnd = random.Random(config.SEMILLA)

  config.RUTA_SALIDA.mkdir(exist_ok=True)
  filas, peor = [], {}
  print(f"{'n':>3} {'pedidos':>8} " + " ".join(f"{t[0][:14]:>15}" for t in TECNICAS))
  for n in range(args.min_n, args.max_n + 1):
    muestra = rnd.sample(por_tamano[n], min(args.por_tamano, len(por_tamano[n])))
    matrices = [dist.matriz(["depot"] + p) for p in muestra]
    celdas = []
    for nombre, f, n_max in TECNICAS:
      if n > n_max:
        celdas.append(f"{'-':>15}")
        continue
      tiempos = [benchmark.medir(f, m) for m in matrices]
      mediana, maximo = sorted(tiempos)[len(tiempos) // 2], max(tiempos)
      filas.append([n, nombre, len(matrices), f"{mediana:.5f}", f"{maximo:.5f}"])
      celdas.append(f"{mediana:>15.4f}")
      if nombre == "held_karp_opt":
        peor[n] = maximo
    print(f"{n:>3} {len(matrices):>8} " + " ".join(celdas), flush=True)

  ruta = config.RUTA_SALIDA / "benchmark_ruteo.csv"
  with open(ruta, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["n", "tecnica", "pedidos", "mediana_s", "maximo_s"])
    w.writerows(filas)
  t = benchmark.calibrar_umbral(peor, args.limite)
  print(f"\nSe guardó {ruta}")
  print(f"T sugerido (peor tiempo de held_karp_opt <= {args.limite} s): {t}")
  print(f"Valor actual de config.UMBRAL_DP: {config.UMBRAL_DP}")


if __name__ == "__main__":
  main()
