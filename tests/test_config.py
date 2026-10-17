from almacen import config


def test_zonas_disjuntas():
  deps = [d for lista in config.ZONAS.values() for d in lista]
  assert len(deps) == len(set(deps))


def test_departamentos_cubren_los_21_de_instacart():
  zonificados = sum(len(lista) for lista in config.ZONAS.values())
  assert zonificados + len(config.DEPARTAMENTOS_SIN_ZONA) == 21


def test_total_de_nodos():
  assert config.PRODUCTOS_POR_ZONA * len(config.ZONAS) == 1500


def test_colores_y_nombres_por_zona():
  assert set(config.COLOR_ZONA) == set(config.ZONAS) == set(config.NOMBRE_ZONA)
