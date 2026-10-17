"""Ventana principal: carga el servicio en segundo plano y arma las cuatro pestañas."""
import tkinter as tk
from tkinter import messagebox, ttk

from almacen import config
from almacen.gui import tareas
from almacen.gui.pestana_comparacion import PestanaComparacion
from almacen.gui.pestana_datos import PestanaDatos
from almacen.gui.pestana_ruteo import PestanaRuteo
from almacen.gui.pestana_ubicacion import PestanaUbicacion
from almacen.servicio import Servicio

TITULO = "Gestión de almacenes inteligentes – Complejidad Algorítmica"


def _estilos(root):
  estilo = ttk.Style(root)
  if "clam" in estilo.theme_names():
    estilo.theme_use("clam")
  base = ("Segoe UI", 10)
  root.option_add("*Font", base)
  estilo.configure("TNotebook.Tab", padding=(16, 6), font=("Segoe UI", 10, "bold"))
  estilo.configure("Titulo.TLabel", font=("Segoe UI", 10, "bold"), foreground="#37474f")
  estilo.configure("Valor.TLabel", font=("Segoe UI", 10, "bold"))
  estilo.configure("Nota.TLabel", foreground="#607d8b", font=("Segoe UI", 9))
  estilo.configure("Resultado.TLabel", font=("Segoe UI", 11, "bold"))
  estilo.configure("Accion.TButton", font=("Segoe UI", 10, "bold"))
  estilo.configure("Treeview", rowheight=22)


class Aplicacion(tk.Tk):
  def __init__(self, servicio=None):
    super().__init__()
    self.title(TITULO)
    self.geometry("1320x820")
    self.minsize(1100, 700)
    _estilos(self)
    self.servicio = servicio
    self.pestanas = {}

    pie = ttk.Frame(self, padding=(10, 4))
    pie.pack(side="bottom", fill="x")
    self._estado = ttk.Label(pie, text="", style="Nota.TLabel")
    self._estado.pack(side="left")
    self._progreso = ttk.Progressbar(pie, mode="indeterminate", length=160)

    self.protocol("WM_DELETE_WINDOW", self.destroy)
    if servicio is not None:
      self._construir()
    else:
      self._carga = ttk.Label(self, text="Cargando el dataset y construyendo los grafos…\n"
                              "(unos segundos)", justify="center", font=("Segoe UI", 12))
      self._carga.place(relx=0.5, rely=0.45, anchor="center")
      self.ocupado(True, "Cargando…")
      tareas.ejecutar(self, lambda avance: Servicio.desde_csv(), self._servicio_listo,
                      self._fallo_carga)

  # ------------------------------------------------------------ carga
  def _servicio_listo(self, servicio):
    self.servicio = servicio
    self._carga.destroy()
    self.ocupado(False)
    self._construir()

  def _fallo_carga(self, error):
    self.ocupado(False)
    messagebox.showerror(
        "No se pudo cargar el dataset",
        f"{error}\n\nVerifique que la carpeta dataset/ tenga departments.csv, products.csv "
        f"y order_products__train.csv de Instacart.\nRuta buscada: {config.RUTA_DATOS}")
    self.destroy()

  def _construir(self):
    cuaderno = ttk.Notebook(self)
    cuaderno.pack(fill="both", expand=True, padx=8, pady=(8, 0))
    for clave, titulo, clase in [("datos", "1. Datos y grafos", PestanaDatos),
                                 ("ubicacion", "2. Ubicación", PestanaUbicacion),
                                 ("ruteo", "3. Ruteo", PestanaRuteo),
                                 ("comparacion", "4. Comparación", PestanaComparacion)]:
      pestana = clase(cuaderno, self)
      cuaderno.add(pestana, text=titulo)
      self.pestanas[clave] = pestana
    cuaderno.select(self.pestanas["ruteo"])
    self.estado("Listo")

  # ------------------------------------------------------------ utilidades para las pestañas
  def estado(self, texto):
    self._estado.configure(text=texto)

  def ocupado(self, si, texto=""):
    if si:
      self._progreso.pack(side="right")
      self._progreso.start(12)
      self.estado(texto)
    else:
      self._progreso.stop()
      self._progreso.pack_forget()
      self.estado("Listo")

  def layout_cambiado(self):
    """UFDS volvió a ejecutarse: las pestañas que dibujan el layout optimizado se actualizan."""
    if "ruteo" in self.pestanas:
      self.pestanas["ruteo"].refrescar()


def main():
  try:                                   # nitidez en pantallas de alta densidad (Windows)
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
  except Exception:
    pass
  Aplicacion().mainloop()
