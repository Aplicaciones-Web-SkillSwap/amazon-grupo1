from almacen import benchmark


def test_medir_devuelve_segundos_positivos():
  assert benchmark.medir(lambda m: sum(range(1000)), None, repeticiones=3) >= 0


def test_calibrar_umbral():
  tiempos = {8: 0.01, 9: 0.05, 10: 0.2, 11: 0.8, 12: 3.0, 13: 0.5}
  assert benchmark.calibrar_umbral(tiempos, 1.0) == 11     # se detiene en el primero que excede
  assert benchmark.calibrar_umbral(tiempos, 0.001) == 0
  assert benchmark.calibrar_umbral(tiempos, 100) == 13
