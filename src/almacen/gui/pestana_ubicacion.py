"""Pestaña 2 – Ubicación: ejecuta UFDS y compara el layout actual con el optimizado."""
from tkinter import messagebox, ttk

from almacen import config
from almacen.gui import dibujo, tareas
from almacen.gui.widgets import Lienzo, Tabla, formato_miles
from almacen.servicio import ACTUAL, OPTIMIZADO


class PestanaUbicacion(ttk.Frame):
  def __init__(self, padre, app):
    super().__init__(padre, padding=8)
    self.app = app
    self.servicio = app.servicio
    self.resaltar = None

    barra = ttk.Frame(self)
    barra.pack(fill="x")
    ttk.Label(barra, text="Capacidad por pasillo (K):").pack(side="left")
    self.capacidad = ttk.Spinbox(barra, from_=config.CAPACIDAD_PASILLO, to=60, width=5)
    self.capacidad.set(self.servicio.capacidad)
    self.capacidad.pack(side="left", padx=6)
    self.boton = ttk.Button(barra, text="Ejecutar UFDS", command=self.ejecutar)
    self.boton.pack(side="left")
    self.resumen = ttk.Label(barra, style="Nota.TLabel", justify="left")
    self.resumen.pack(side="left", padx=16)

    cuerpo = ttk.Frame(self)
    cuerpo.pack(fill="both", expand=True, pady=(8, 0))
    izq = ttk.Frame(cuerpo, width=480)
    izq.pack(side="left", fill="y", padx=(0, 10))
    izq.pack_propagate(False)
    ttk.Label(izq, text="Pasillos del layout optimizado", style="Titulo.TLabel").pack(anchor="w")
    self.tabla = Tabla(izq, [("pasillo", "Pasillo", 55, "center"),
                             ("productos", "Prod.", 50, "center"),
                             ("lineas", "Líneas", 80, "e"),
                             ("ejemplos", "Productos más pedidos", 260, "w")],
                       alto=26, seleccion=True)
    self.tabla.pack(fill="both", expand=True, pady=(4, 0))
    self.tabla.al_seleccionar(self._seleccion)

    self.lienzo = Lienzo(cuerpo, figsize=(8, 6))
    self.lienzo.pack(side="left", fill="both", expand=True)
    self._refrescar()

  def ejecutar(self):
    try:
      k = int(self.capacidad.get())
    except ValueError:
      messagebox.showwarning("Capacidad no válida", "Ingrese un número entero.")
      return
    self.boton.state(["disabled"])
    self.app.ocupado(True, "Ejecutando UFDS y reconstruyendo distancias…")
    tareas.ejecutar(self.winfo_toplevel(), lambda avance: self.servicio.reoptimizar(k),
                    self._listo, self._fallo)

  def _listo(self, _):
    self.boton.state(["!disabled"])
    self.app.ocupado(False)
    self.resaltar = None
    self._refrescar()
    self.app.layout_cambiado()

  def _fallo(self, error):
    self.boton.state(["!disabled"])
    self.app.ocupado(False)
    messagebox.showerror("No se pudo reubicar", str(error))

  def _refrescar(self):
    s, e = self.servicio, self.servicio.estadisticas
    self.resumen.configure(text=(
        f"{formato_miles(e['grupos_de_varios'])} grupos de afinidad "
        f"({formato_miles(e['productos_en_grupos'])} productos, el mayor de {e['mayor_grupo']}) "
        f"+ {formato_miles(e['aislados'])} productos sin grupo\n"
        f"Se usan {e['pasillos_usados']} de {s.layouts[ACTUAL].n_pasillos} pasillos "
        f"con K = {e['capacidad']}"))
    filas = []
    for _, k, prods in s.pasillos[OPTIMIZADO]:
      nombres = ", ".join(s.info[p]["nombre"][:22] for p in prods[:2])
      filas.append((k, len(prods), formato_miles(sum(s.info[p]["freq"] for p in prods)), nombres))
    self.tabla.llenar(filas)
    self._dibujar()

  def _seleccion(self, indice, _valores):
    self.resaltar = indice
    self._dibujar()

  def _dibujar(self):
    s = self.servicio
    fig = self.lienzo.fig
    fig.clear()
    ax1, ax2 = fig.subplots(2, 1, sharex=True)
    dibujo.dibujar_almacen(ax1, s.layouts[ACTUAL], s.info,
                           titulo="Layout actual (pasillos y departamentos de Instacart)")
    dibujo.dibujar_almacen(ax2, s.layouts[OPTIMIZADO], s.info, resaltar=self.resaltar,
                           titulo=f"Layout optimizado (UFDS, K = {s.capacidad})")
    self.lienzo.redibujar()
