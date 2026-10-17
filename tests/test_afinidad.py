from almacen import afinidad, datos


def preparar(carpeta):
  d = datos.cargar_datos(carpeta)
  nodos = datos.seleccionar_nodos(d, por_zona=2)
  return nodos, datos.pedidos_filtrados(d, nodos)


def test_contar_coocurrencias(carpeta_datos):
  _, pedidos = preparar(carpeta_datos)
  conteo = afinidad.contar_coocurrencias(pedidos)
  assert conteo[(1, 2)] == 4
  assert conteo[(1, 4)] == 3
  assert conteo[(2, 4)] == 2
  assert conteo[(5, 7)] == 1


def test_construir_afinidad_con_umbral(carpeta_datos):
  nodos, pedidos = preparar(carpeta_datos)
  g1 = afinidad.construir_afinidad(nodos, pedidos, umbral=2)
  assert g1.num_nodos() == 6
  assert g1.num_aristas() == 3
  assert g1.peso(1, 2) == 4 and g1.peso(2, 1) == 4
  assert g1.peso(1, 4) == 3
  assert g1.peso(2, 4) == 2
  assert g1.num_aislados() == 3          # productos 5, 6 y 7


def test_umbral_mas_bajo_agrega_aristas(carpeta_datos):
  nodos, pedidos = preparar(carpeta_datos)
  assert afinidad.construir_afinidad(nodos, pedidos, umbral=1).num_aristas() == 9
