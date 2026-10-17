"""Widgets reutilizables: lienzo de matplotlib con barra de zoom y tabla con scroll."""
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class Lienzo(ttk.Frame):
  """Figura de matplotlib dentro de tkinter, con la barra de zoom/desplazamiento."""

  def __init__(self, padre, figsize=(8, 5)):
    super().__init__(padre)
    self.fig = Figure(figsize=figsize, dpi=100, constrained_layout=True)
    self.canvas = FigureCanvasTkAgg(self.fig, master=self)
    barra = ttk.Frame(self)
    barra.pack(side="bottom", fill="x")
    self.barra = NavigationToolbar2Tk(self.canvas, barra)
    self.barra.update()
    self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

  def redibujar(self):
    self.canvas.draw_idle()


class Tabla(ttk.Frame):
  """Treeview con barra de desplazamiento. columnas: [(id, titulo, ancho, alineacion)]."""

  def __init__(self, padre, columnas, alto=8, seleccion=False):
    super().__init__(padre)
    self.arbol = ttk.Treeview(self, columns=[c[0] for c in columnas], show="headings",
                              height=alto, selectmode="browse" if seleccion else "none")
    for ident, titulo, ancho, ancla in columnas:
      self.arbol.heading(ident, text=titulo)
      self.arbol.column(ident, width=ancho, anchor=ancla, stretch=True)
    scroll = ttk.Scrollbar(self, orient="vertical", command=self.arbol.yview)
    self.arbol.configure(yscrollcommand=scroll.set)
    self.arbol.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

  def llenar(self, filas):
    self.arbol.delete(*self.arbol.get_children())
    for fila in filas:
      self.arbol.insert("", "end", values=fila)

  def al_seleccionar(self, callback):
    def _evento(_):
      sel = self.arbol.selection()
      if sel:
        callback(self.arbol.index(sel[0]), self.arbol.item(sel[0], "values"))
    self.arbol.bind("<<TreeviewSelect>>", _evento)


def formato_miles(n):
  return f"{n:,}"
