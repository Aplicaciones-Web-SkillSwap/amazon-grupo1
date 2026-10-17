"""Pestaña 1 – Datos y grafos: métricas del dataset y visualización de G1 y G2."""
from tkinter import messagebox, ttk

from almacen.gui import dibujo, tareas
from almacen.gui.widgets import Lienzo, formato_miles
from almacen.servicio import ACTUAL, OPTIMIZADO

OPCIONES = {
    "G₁ completo (afinidad)": ("g1", None),
    "G₁ zona A – Frescos": ("g1", "A"),
    "G₁ zona B – Refrigerados, congelados y hogar": ("g1", "B"),
    "G₁ zona C – Abarrotes y bebidas": ("g1", "C"),
    "G₂ almacén actual": ("g2", ACTUAL),
    "G₂ almacén optimizado": ("g2", OPTIMIZADO),
}


class PestanaDatos(ttk.Frame):
  def __init__(self, padre, app):
    super().__init__(padre, padding=8)
    self.app = app
    self.servicio = app.servicio
    self._cache = {}                              # (tipo, clave) -> posiciones de G1

    izq = ttk.Frame(self, width=330)
    izq.pack(side="left", fill="y", padx=(0, 10))
    izq.pack_propagate(False)
    self._metricas(izq)

    ttk.Label(izq, text="Visualización", style="Titulo.TLabel").pack(anchor="w", pady=(14, 4))
    self.opcion = ttk.Combobox(izq, values=list(OPCIONES), state="readonly", width=40)
    self.opcion.current(0)
    self.opcion.pack(fill="x")
    self.boton = ttk.Button(izq, text="Dibujar", command=self.dibujar)
    self.boton.pack(fill="x", pady=6)
    ttk.Label(izq, wraplength=300, style="Nota.TLabel", text=(
        "G₁ se dibuja con las 3 aristas más fuertes de cada producto. En G₂ cada punto es "
        "una ubicación; use la barra de abajo para acercar y mover el plano.")).pack(anchor="w")

    self.lienzo = Lienzo(self, figsize=(8, 6))
    self.lienzo.pack(side="left", fill="both", expand=True)
    self.dibujar()

  def _metricas(self, padre):
    s = self.servicio
    r = s.resumen()
    alcanzados, total = s.alcance_bfs()
    bloques = [
        ("Dataset", [
            ("Pedidos filtrados", formato_miles(r["pedidos"])),
            ("Productos (nodos de G₁)", formato_miles(r["productos"])),
        ]),
        ("Grafo de afinidad G₁", [
            ("Aristas", formato_miles(r["aristas_g1"])),
            ("Productos aislados", formato_miles(r["aislados_g1"])),
            ("Densidad", f"{r['densidad_g1']:.4f}"),
            ("Grado promedio", f"{r['grado_promedio_g1']:.1f}"),
        ]),
        ("Layout del almacén G₂", [
            ("Nodos / aristas", f"{formato_miles(r['nodos_g2'])} / {formato_miles(r['aristas_g2'])}"),
            ("Pasillos × largo", f"{r['pasillos']} × {r['largo_pasillo_m']:.0f} m"),
            ("BFS desde el depot", f"{formato_miles(alcanzados)} de {formato_miles(total)} nodos"),
            ("Floyd-Warshall", f"{r['nodos_floyd']} nodos, {r['tiempo_floyd_s']:.2f} s"),
        ]),
    ]
    for titulo, filas in bloques:
      ttk.Label(padre, text=titulo, style="Titulo.TLabel").pack(anchor="w", pady=(8, 2))
      marco = ttk.Frame(padre)
      marco.pack(fill="x")
      marco.columnconfigure(1, weight=1)
      for i, (nombre, valor) in enumerate(filas):
        ttk.Label(marco, text=nombre).grid(row=i, column=0, sticky="w", padx=(0, 8))
        ttk.Label(marco, text=valor, style="Valor.TLabel").grid(row=i, column=1, sticky="e")

  def dibujar(self):
    nombre = self.opcion.get()
    tipo, clave = OPCIONES[nombre]
    if tipo == "g2":
      self._dibujar_g2(nombre, clave)
      return
    if clave in self._cache:
      self._dibujar_g1(nombre, self._cache[clave])
      return
    self.boton.state(["disabled"])
    self.app.ocupado(True, "Calculando la posición de los nodos de G₁…")
    tareas.ejecutar(
        self.winfo_toplevel(),
        lambda avance: dibujo.calcular_posiciones_g1(self.servicio.g1, self.servicio.info, clave),
        lambda calculo: self._listo(nombre, clave, calculo),
        self._fallo)

  def _listo(self, nombre, clave, calculo):
    self._cache[clave] = calculo
    self.boton.state(["!disabled"])
    self.app.ocupado(False)
    self._dibujar_g1(nombre, calculo)

  def _fallo(self, error):
    self.boton.state(["!disabled"])
    self.app.ocupado(False)
    messagebox.showerror("No se pudo dibujar el grafo", str(error))

  def _dibujar_g1(self, nombre, calculo):
    self.lienzo.fig.clear()
    ax = self.lienzo.fig.add_subplot(111)
    n, m = len(calculo["nodos"]), len(calculo["aristas"])
    dibujo.dibujar_g1(ax, calculo, self.servicio.g1, self.servicio.info,
                      f"{nombre}  ·  {formato_miles(n)} productos, {formato_miles(m)} aristas dibujadas")
    self.lienzo.redibujar()

  def _dibujar_g2(self, nombre, clave):
    self.lienzo.fig.clear()
    ax = self.lienzo.fig.add_subplot(111)
    lo = self.servicio.layouts[clave]
    dibujo.dibujar_almacen(ax, lo, self.servicio.info, titulo=nombre)
    self.lienzo.redibujar()
