"""Pestaña 3 – Ruteo: elegir un pedido, la técnica y el layout; ver la ruta resaltada."""
import tkinter as tk
from tkinter import messagebox, ttk

from almacen.gui import dibujo, tareas
from almacen.gui.widgets import Lienzo, Tabla, formato_miles
from almacen.servicio import ACTUAL, OPTIMIZADO

TECNICAS = {
    "Automática (según el tamaño del pedido)": "auto",
    "Fuerza bruta": "fuerza_bruta",
    "Backtracking": "backtracking",
    "Programación dinámica (Held-Karp optimizado)": "dp",
    "Voraz (vecino más cercano)": "voraz",
}
NOMBRE_TECNICA = {
    "exacta_verificada": "Backtracking + Programación dinámica (verificadas)",
    "dp": "Programación dinámica (Held-Karp optimizado)",
    "backtracking": "Backtracking", "fuerza_bruta": "Fuerza bruta",
    "voraz": "Voraz (vecino más cercano)", "dp_base": "Held-Karp base",
}
LAYOUTS = {"Actual": ACTUAL, "Optimizado (UFDS)": OPTIMIZADO}


class PestanaRuteo(ttk.Frame):
  def __init__(self, padre, app):
    super().__init__(padre, padding=8)
    self.app = app
    self.servicio = app.servicio
    self.pedido = []
    self.resultado = None
    self.order_id = None

    izq = ttk.Frame(self, width=370)
    izq.pack(side="left", fill="y", padx=(0, 10))
    izq.pack_propagate(False)
    self._controles(izq)

    der = ttk.Frame(self)
    der.pack(side="left", fill="both", expand=True)
    arriba = ttk.Frame(der)
    arriba.pack(fill="x")
    ttk.Label(arriba, text="Layout del almacén y ruta resaltada",
              style="Titulo.TLabel").pack(side="left")
    ttk.Button(arriba, text="Ver almacén completo", command=self._vista_completa).pack(
        side="right")
    ttk.Button(arriba, text="Acercar a la ruta", command=self._vista_ruta).pack(
        side="right", padx=6)
    self.lienzo = Lienzo(der, figsize=(8, 5))
    self.lienzo.pack(fill="both", expand=True)
    self.ax = self.lienzo.fig.add_subplot(111)

    abajo = ttk.Frame(der)
    abajo.pack(fill="x", pady=(6, 0))
    self.lbl_dist = ttk.Label(abajo, text="Distancia total: — m", style="Resultado.TLabel")
    self.lbl_dist.pack(side="left")
    self.lbl_tiempo = ttk.Label(abajo, text="Tiempo de ejecución: — ms", style="Resultado.TLabel")
    self.lbl_tiempo.pack(side="left", padx=24)
    self.lbl_tecnica = ttk.Label(abajo, text="", style="Nota.TLabel")
    self.lbl_tecnica.pack(side="left")
    self._dibujar()

  # ------------------------------------------------------------ controles
  def _controles(self, izq):
    ttk.Label(izq, text="Pedido", style="Titulo.TLabel").pack(anchor="w")
    self.modo = tk.StringVar(value="aleatorio")
    fila = ttk.Frame(izq)
    fila.pack(fill="x", pady=2)
    ttk.Radiobutton(fila, text="Aleatorio", variable=self.modo, value="aleatorio").pack(
        side="left")
    ttk.Label(fila, text="  de").pack(side="left")
    self.tamano = ttk.Spinbox(fila, from_=1, to=50, width=4)
    self.tamano.pack(side="left", padx=3)
    ttk.Label(fila, text="productos", style="Nota.TLabel").pack(side="left")
    fila2 = ttk.Frame(izq)
    fila2.pack(fill="x", pady=2)
    ttk.Radiobutton(fila2, text="Por número de pedido", variable=self.modo,
                    value="numero").pack(side="left")
    self.entrada_id = ttk.Entry(fila2, width=10)
    self.entrada_id.pack(side="left", padx=6)
    ttk.Label(izq, text="Deje el tamaño vacío para un pedido de cualquier tamaño.",
              style="Nota.TLabel").pack(anchor="w")
    ttk.Button(izq, text="Obtener pedido", command=self.obtener_pedido).pack(fill="x", pady=4)
    self.lbl_pedido = ttk.Label(izq, text="Aún no hay un pedido.", style="Nota.TLabel")
    self.lbl_pedido.pack(anchor="w")

    self.tabla = Tabla(izq, [("n", "#", 32, "center"), ("producto", "Producto", 190, "w"),
                             ("zona", "Zona", 38, "center"), ("pasillo", "Pas.", 42, "center")],
                       alto=12)
    self.tabla.pack(fill="both", expand=True, pady=(4, 8))

    ttk.Label(izq, text="Técnica", style="Titulo.TLabel").pack(anchor="w")
    self.tecnica = ttk.Combobox(izq, values=list(TECNICAS), state="readonly")
    self.tecnica.current(0)
    self.tecnica.pack(fill="x", pady=(0, 6))
    ttk.Label(izq, text="Layout", style="Titulo.TLabel").pack(anchor="w")
    self.layout = ttk.Combobox(izq, values=list(LAYOUTS), state="readonly")
    self.layout.current(0)
    self.layout.pack(fill="x", pady=(0, 8))
    self.layout.bind("<<ComboboxSelected>>", lambda _: self._cambio_layout())

    self.botones = [
        ttk.Button(izq, text="Calcular ruta", style="Accion.TButton", command=self.calcular),
        ttk.Button(izq, text="Comparar técnicas", command=self.comparar_tecnicas),
        ttk.Button(izq, text="Comparar layouts", command=self.comparar_layouts),
    ]
    for b in self.botones:
      b.pack(fill="x", pady=2)

  def _layout_elegido(self):
    return LAYOUTS[self.layout.get()]

  # ------------------------------------------------------------ pedido
  def obtener_pedido(self):
    try:
      if self.modo.get() == "aleatorio":
        txt = self.tamano.get().strip()
        tamano = int(txt) if txt else None
        self.order_id, self.pedido = self.servicio.pedido_aleatorio(tamano)
      else:
        try:
          oid = int(self.entrada_id.get())
        except ValueError:
          raise ValueError("Escriba un número de pedido (order_id).")
        if oid not in self.servicio.pedidos:
          raise ValueError(f"El pedido {oid} no está entre los {formato_miles(len(self.servicio.pedidos))} "
                           "pedidos filtrados.")
        self.order_id, self.pedido = oid, list(self.servicio.pedidos[oid])
    except ValueError as e:
      messagebox.showwarning("Pedido no válido", str(e))
      return
    self.resultado = None
    self.lbl_pedido.configure(
        text=f"Pedido {self.order_id}: {len(self.pedido)} productos distintos")
    self._tabla_pedido()
    self._limpiar_resultado()
    self._dibujar()

  def _tabla_pedido(self, orden=None):
    s, lay = self.servicio, self._layout_elegido()
    productos = orden or self.pedido
    filas = []
    for k, p in enumerate(productos, start=1):
      filas.append((k if orden else "", s.info[p]["nombre"], s.info[p]["zona"],
                    s.pasillo_de(p, lay)))
    self.tabla.llenar(filas)

  def _limpiar_resultado(self):
    self.lbl_dist.configure(text="Distancia total: — m")
    self.lbl_tiempo.configure(text="Tiempo de ejecución: — ms")
    self.lbl_tecnica.configure(text="")

  def _cambio_layout(self):
    self.resultado = None
    self._limpiar_resultado()
    if self.pedido:
      self._tabla_pedido()
    self._dibujar()

  def refrescar(self):
    """Se llama cuando UFDS vuelve a ejecutarse y el layout optimizado cambia."""
    self._cambio_layout()

  # ------------------------------------------------------------ acciones
  def _necesita_pedido(self):
    if not self.pedido:
      messagebox.showinfo("Falta el pedido", "Primero obtenga un pedido.")
      return False
    return True

  def _bloquear(self, texto):
    for b in self.botones:
      b.state(["disabled"])
    self.app.ocupado(True, texto)

  def _liberar(self):
    for b in self.botones:
      b.state(["!disabled"])
    self.app.ocupado(False)

  def _fallo(self, error):
    self._liberar()
    messagebox.showwarning("No se pudo calcular", str(error))

  def calcular(self):
    if not self._necesita_pedido():
      return
    tecnica, lay = TECNICAS[self.tecnica.get()], self._layout_elegido()
    self._bloquear("Calculando la ruta…")
    tareas.ejecutar(self.winfo_toplevel(),
                    lambda avance: self.servicio.rutear(self.pedido, lay, tecnica),
                    self._mostrar, self._fallo)

  def _mostrar(self, r):
    self._liberar()
    self.resultado = r
    self.lbl_dist.configure(text=f"Distancia total: {r.costo:,.0f} m")
    ms = r.tiempo_s * 1000
    self.lbl_tiempo.configure(text=f"Tiempo de ejecución: {ms:,.1f} ms")
    self.lbl_tecnica.configure(text=NOMBRE_TECNICA.get(r.tecnica, r.tecnica))
    self._tabla_pedido(r.orden)
    self._dibujar()

  def comparar_tecnicas(self):
    if not self._necesita_pedido():
      return
    lay = self._layout_elegido()
    self._bloquear("Ejecutando las tres técnicas…")
    tareas.ejecutar(self.winfo_toplevel(),
                    lambda avance: self.servicio.comparar_tecnicas(self.pedido, lay),
                    self._dialogo_tecnicas, self._fallo)

  def _dialogo_tecnicas(self, resultados):
    self._liberar()
    validos = [r.costo for r in resultados.values() if r is not None]
    mejor = min(validos)
    filas = []
    for nombre, r in resultados.items():
      if r is None:
        filas.append((NOMBRE_TECNICA[nombre], "no viable", "—", "—"))
      else:
        dif = 100 * (r.costo - mejor) / mejor if mejor else 0.0
        filas.append((NOMBRE_TECNICA[nombre], f"{r.costo:,.0f}", f"{r.tiempo_s * 1000:,.1f}",
                      "óptima" if dif < 1e-9 else f"+{dif:.1f} %"))
    self._dialogo(f"Técnicas sobre el pedido {self.order_id} ({len(self.pedido)} productos)",
                  [("t", "Técnica", 290, "w"), ("d", "Distancia (m)", 100, "e"),
                   ("ms", "Tiempo (ms)", 90, "e"), ("dif", "Frente a la mejor", 110, "e")], filas)

  def comparar_layouts(self):
    if not self._necesita_pedido():
      return
    tecnica = TECNICAS[self.tecnica.get()]
    self._bloquear("Ruteando en ambos layouts…")
    tareas.ejecutar(self.winfo_toplevel(),
                    lambda avance: self.servicio.comparar_layouts(self.pedido, tecnica),
                    self._dialogo_layouts, self._fallo)

  def _dialogo_layouts(self, resultados):
    self._liberar()
    base = resultados[ACTUAL].costo
    filas = []
    for clave, r in resultados.items():
      red = "—" if clave == ACTUAL else (f"{100 * (base - r.costo) / base:+.1f} %" if base else "—")
      filas.append((dibujo.nombre_layout(clave), f"{r.costo:,.0f}", f"{r.tiempo_s * 1000:,.1f}", red))
    self._dialogo(f"Layouts sobre el pedido {self.order_id} ({len(self.pedido)} productos)",
                  [("l", "Layout", 240, "w"), ("d", "Distancia (m)", 100, "e"),
                   ("ms", "Tiempo (ms)", 90, "e"), ("red", "Reducción", 100, "e")], filas)

  def _dialogo(self, titulo, columnas, filas):
    ventana = tk.Toplevel(self)
    ventana.title(titulo)
    ventana.transient(self.winfo_toplevel())
    marco = ttk.Frame(ventana, padding=12)
    marco.pack(fill="both", expand=True)
    ttk.Label(marco, text=titulo, style="Titulo.TLabel").pack(anchor="w", pady=(0, 6))
    tabla = Tabla(marco, columnas, alto=len(filas))
    tabla.pack(fill="both", expand=True)
    tabla.llenar(filas)
    ttk.Button(marco, text="Cerrar", command=ventana.destroy).pack(anchor="e", pady=(8, 0))

  # ------------------------------------------------------------ mapa
  def _dibujar(self):
    lo = self.servicio.layouts[self._layout_elegido()]
    r = self.resultado
    titulo = dibujo.nombre_layout(self._layout_elegido())
    dibujo.dibujar_almacen(self.ax, lo, self.servicio.info,
                           orden=r.orden if r else None, camino=r.camino if r else None,
                           marcar=self.pedido or None, titulo=f"Layout {titulo.lower()}")
    self.lienzo.redibujar()

  def _vista_completa(self):
    dibujo.vista_completa(self.ax, self.servicio.layouts[self._layout_elegido()])
    self.lienzo.redibujar()

  def _vista_ruta(self):
    lo = self.servicio.layouts[self._layout_elegido()]
    dibujo.vista_a_la_ruta(self.ax, lo, self.resultado.camino if self.resultado else None)
    self.lienzo.redibujar()
