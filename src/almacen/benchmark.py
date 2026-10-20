"""Medición de tiempos de las técnicas de ruteo y calibración del umbral T.

TÉCNICA: Medición de tiempos de las técnicas de ruteo (no es una técnica del curso).
"""
import statistics
import time


def medir(funcion, matriz, repeticiones=1):
  """Segundos que tarda funcion(matriz): mediana de `repeticiones` ejecuciones."""
  tiempos = []
  for _ in range(repeticiones):
    t0 = time.perf_counter()
    funcion(matriz)
    tiempos.append(time.perf_counter() - t0)
  return statistics.median(tiempos)


def calibrar_umbral(tiempo_por_n, limite_s):
  """Mayor n tal que todos los tamaños hasta n tardan a lo más `limite_s` segundos.

  tiempo_por_n: dict n -> segundos (mediana o peor caso medido)."""
  umbral = 0
  for n in sorted(tiempo_por_n):
    if tiempo_por_n[n] > limite_s:
      break
    umbral = n
  return umbral
