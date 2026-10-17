"""Pruebas de la ventana. Se omiten si no hay tkinter o no hay pantalla disponible."""
import time

import matplotlib

matplotlib.use("Agg")

import pytest   # noqa: E402

tk = pytest.importorskip("tkinter")

from almacen.gui import tareas        # noqa: E402
from almacen.servicio import ACTUAL, Servicio   # noqa: E402


@pytest.fixture
def raiz():
  try:
    r = tk.Tk()
  except tk.TclError:
    pytest.skip("no hay pantalla disponible")
  r.withdraw()
  yield r
  r.destroy()


def esperar(raiz, condicion, limite=20):
  t0 = time.time()
  while not condicion() and time.time() - t0 < limite:
    raiz.update()
    time.sleep(0.01)
  raiz.update()
  assert condicion(), "la tarea no terminó a tiempo"


def test_tareas_exito_y_progreso(raiz):
  avances, salida = [], []
  tareas.ejecutar(raiz, lambda avance: (avance(1, 2), avance(2, 2), 42)[-1],
                  salida.append, progreso=lambda i, n: avances.append((i, n)))
  esperar(raiz, lambda: salida)
  assert salida == [42] and avances == [(1, 2), (2, 2)]


def test_tareas_error(raiz):
  errores = []
  tareas.ejecutar(raiz, lambda avance: 1 / 0, lambda r: None, error=errores.append)
  esperar(raiz, lambda: errores)
  assert isinstance(errores[0], ZeroDivisionError)


@pytest.fixture
def app(carpeta_datos):
  from almacen.gui.app import Aplicacion
  servicio = Servicio.desde_csv(carpeta_datos, por_zona=2, umbral=2, capacidad=2)
  try:
    a = Aplicacion(servicio)
  except tk.TclError:
    pytest.skip("no hay pantalla disponible")
  a.withdraw()
  a.update()
  yield a
  a.destroy()


def test_las_cuatro_pestanas(app):
  assert list(app.pestanas) == ["datos", "ubicacion", "ruteo", "comparacion"]


def test_ruteo_calcula_y_muestra_resultado(app):
  r = app.pestanas["ruteo"]
  r.obtener_pedido()
  assert r.pedido and r.order_id in app.servicio.pedidos
  r.calcular()
  esperar(app, lambda: r.resultado is not None)
  assert r.lbl_dist.cget("text").startswith("Distancia total:") and "—" not in r.lbl_dist.cget("text")
  assert r.resultado.layout == ACTUAL


def test_ruteo_por_numero_de_pedido_invalido(app, monkeypatch):
  from tkinter import messagebox
  avisos = []
  monkeypatch.setattr(messagebox, "showwarning", lambda *a, **k: avisos.append(a))
  r = app.pestanas["ruteo"]
  r.modo.set("numero")
  r.entrada_id.insert(0, "999999")
  r.obtener_pedido()
  assert avisos and not r.pedido


def test_comparacion_ejecuta_y_llena_tablas(app):
  c = app.pestanas["comparacion"]
  c.n_pedidos.set(6)
  c.ejecutar()
  esperar(app, lambda: c.resultado is not None, 40)
  assert len(c.tabla.arbol.get_children()) == 4
  assert "Aporte de la afinidad" in c.lbl_afinidad.cget("text")


def test_ubicacion_reejecuta_ufds(app, monkeypatch):
  from tkinter import messagebox
  monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)
  u = app.pestanas["ubicacion"]
  u.capacidad.set(2)
  u.ejecutar()
  esperar(app, lambda: u.boton.instate(["!disabled"]))
  assert len(u.tabla.arbol.get_children()) == app.servicio.estadisticas["pasillos_usados"]
