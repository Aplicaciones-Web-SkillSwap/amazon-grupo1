import pytest

from almacen import experimento
from almacen.servicio import ACTUAL, OPTIMIZADO, Servicio


@pytest.fixture
def servicio(carpeta_datos):
  # capacidad 2 para que los pasillos optimizados quepan en el almacén de juguete
  return Servicio.desde_csv(carpeta_datos, por_zona=2, umbral=2, capacidad=2)


def largo_manhattan(lo, ruta):
  total = 0.0
  for a, b in zip(ruta, ruta[1:]):
    (xa, ya), (xb, yb) = lo.pos[a], lo.pos[b]
    assert xa == xb or ya == yb
    total += abs(xa - xb) + abs(ya - yb)
  return total


def test_construccion(servicio):
  r = servicio.resumen()
  assert r["productos"] == 6 and r["pedidos"] == 6 and r["pasillos"] == 3
  assert set(servicio.layouts) == {ACTUAL, OPTIMIZADO}
  assert servicio.layouts[ACTUAL].y_fondo == servicio.layouts[OPTIMIZADO].y_fondo


def test_descripcion(servicio):
  d = servicio.descripcion(1)
  assert d["nombre"] == "Banana" and d["zona"] == "A"
  assert d["pasillo_actual"] == 1


def test_rutear_devuelve_ciclo_valido(servicio):
  for nombre in (ACTUAL, OPTIMIZADO):
    r = servicio.rutear([1, 2, 4, 6], nombre, "dp")
    assert sorted(r.orden) == [1, 2, 4, 6]
    assert r.camino[0] == "depot" and r.camino[-1] == "depot"
    assert largo_manhattan(servicio.layouts[nombre], r.camino) == pytest.approx(r.costo)
    assert r.tiempo_s >= 0 and r.layout == nombre


def test_tecnicas_exactas_coinciden_y_voraz_no_mejora(servicio):
  c = servicio.comparar_tecnicas([1, 2, 4, 5, 6, 7])
  assert c["backtracking"].costo == pytest.approx(c["dp"].costo)
  assert c["voraz"].costo >= c["dp"].costo - 1e-9


def test_auto_elige_segun_el_tamano(servicio):
  assert servicio.rutear([1, 2, 4], tecnica="auto").tecnica == "exacta_verificada"


def test_pedido_duplicado_se_deduplica(servicio):
  assert sorted(servicio.rutear([1, 1, 2]).orden) == [1, 2]


def test_errores_claros(servicio):
  with pytest.raises(ValueError, match="vacío"):
    servicio.rutear([])
  with pytest.raises(ValueError, match="no están"):
    servicio.rutear([1, 999])
  with pytest.raises(ValueError, match="desconocida"):
    servicio.rutear([1, 2], tecnica="magia")


def test_comparar_tecnicas_marca_las_no_viables(servicio, monkeypatch):
  from almacen import servicio as mod
  monkeypatch.setitem(mod.TECNICAS, "backtracking", (mod.TECNICAS["backtracking"][0], 2))
  assert servicio.comparar_tecnicas([1, 2, 4])["backtracking"] is None
  with pytest.raises(ValueError, match="no es viable"):
    servicio.rutear([1, 2, 4], tecnica="backtracking")


def test_comparar_layouts(servicio):
  r = servicio.comparar_layouts([1, 2, 4], "dp")
  assert set(r) == {ACTUAL, OPTIMIZADO}


def test_pedido_aleatorio(servicio):
  oid, prods = servicio.pedido_aleatorio(semilla=1)
  assert oid in servicio.pedidos and prods == servicio.pedidos[oid]
  assert len(servicio.pedido_aleatorio(tamano=2, semilla=1)[1]) == 2
  with pytest.raises(ValueError):
    servicio.pedido_aleatorio(tamano=40)


def test_experimento_en_juguete(servicio):
  df = experimento.correr(servicio, 6, semilla=1, umbral_dp=19)
  assert len(df) == 12 and set(df["layout"]) == {ACTUAL, OPTIMIZADO}
  assert (df["costo_voraz"] >= df["costo"] - 1e-9).all()
  resumen = experimento.por_layout(df)
  assert set(resumen["layout"]) == {ACTUAL, OPTIMIZADO}
  par = experimento.comparar_pareado(df, OPTIMIZADO, ACTUAL)
  assert par["ic95_bajo"] <= par["reduccion_pct"] <= par["ic95_alto"]


def test_reoptimizar_y_controles(servicio):
  est = servicio.reoptimizar(2)
  assert est["capacidad"] == 2 and est["pasillos_usados"] == 3 and est["mayor_grupo"] <= 2
  assert est["grupos"] == est["grupos_de_varios"] + est["aislados"]
  servicio.agregar_controles()
  assert {"solo_frecuencia", "aleatorio"} <= set(servicio.layouts)
  with pytest.raises(ValueError):                    # 6 productos no caben en 3 pasillos de 1
    servicio.reoptimizar(1)


def test_alcance_bfs_y_floyd(servicio):
  alcanzados, total = servicio.alcance_bfs()
  assert alcanzados == total
  r = servicio.resumen()
  assert r["nodos_floyd"] == 7 and r["tiempo_floyd_s"] >= 0


def test_experimento_con_progreso_y_cancelacion(servicio):
  avances = []
  df = experimento.correr(servicio, 4, semilla=1, progreso=lambda i, n: avances.append((i, n)))
  assert avances[-1] == (4, 4) and {"tiempo_s", "tiempo_voraz_s"} <= set(df.columns)
  assert set(experimento.tiempos_por_tamano(df).columns) == {"dp_ms", "voraz_ms"}
  with pytest.raises(experimento.Cancelado):
    experimento.correr(servicio, 4, cancelar=lambda: True)
