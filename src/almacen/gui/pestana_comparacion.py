"""Pestaña 4 – Comparación: experimento sobre una muestra de pedidos reales."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from almacen import config, experimento
from almacen.gui import dibujo, tareas
from almacen.gui.widgets import Lienzo, Tabla
from almacen.servicio import ACTUAL, OPTIMIZADO


class PestanaComparacion(ttk.Frame):
  def __init__(self, padre, app):
    super().__init__(padre, padding=8)
    self.app = app
    self.servicio = app.servicio
    self.cancelar = False
    self.resultado = None

    barra = ttk.Frame(self)
    barra.pack(fill="x")
    ttk.Label(barra, text="Pedidos a evaluar:").pack(side="left")
    self.n_pedidos = ttk.Spinbox(barra, from_=20, to=5000, increment=50, width=6)
    self.n_pedidos.set(300)
    self.n_pedidos.pack(side="left", padx=(4, 12))
    ttk.Label(barra, text="Semilla:").pack(side="left")
    self.semilla = ttk.Entry(barra, width=6)
    self.semilla.insert(0, str(config.SEMILLA))
    self.semilla.pack(side="left", padx=(4, 12))
    self.controles = tk.BooleanVar(value=True)
    ttk.Checkbutton(barra, text="Incluir layouts de control (solo frecuencia, aleatorio)",
                    variable=self.controles).pack(side="left", padx=(0, 12))
    self.boton = ttk.Button(barra, text="Ejecutar experimento", style="Accion.TButton",
                            command=self.ejecutar)
    self.boton.pack(side="left")
    self.boton_cancelar = ttk.Button(barra, text="Cancelar", command=self._cancelar,
                                     state="disabled")
    self.boton_cancelar.pack(side="left", padx=6)
    self.boton_csv = ttk.Button(barra, text="Guardar CSV…", command=self.guardar,
                                state="disabled")
    self.boton_csv.pack(side="right")

    prog = ttk.Frame(self)
    prog.pack(fill="x", pady=(6, 0))
    self.barra = ttk.Progressbar(prog, maximum=100)
    self.barra.pack(side="left", fill="x", expand=True)
    self.lbl_prog = ttk.Label(prog, text="Listo para ejecutar", width=26, anchor="e")
    self.lbl_prog.pack(side="left", padx=(8, 0))

    cuerpo = ttk.Frame(self)
    cuerpo.pack(fill="both", expand=True, pady=(8, 0))
    izq = ttk.Frame(cuerpo, width=610)
    izq.pack(side="left", fill="y", padx=(0, 10))
    izq.pack_propagate(False)
    ttk.Label(izq, text="Distancia por pedido y layout", style="Titulo.TLabel").pack(anchor="w")
    self.tabla = Tabla(izq, [("layout", "Layout", 220, "w"), ("media", "Media (m)", 70, "e"),
                             ("red", "Reducción", 75, "e"), ("ic", "IC 95 %", 90, "e"),
                             ("mejor", "% mejor", 60, "e")], alto=5)
    self.tabla.pack(fill="x", pady=(4, 6))
    self.lbl_afinidad = ttk.Label(izq, style="Nota.TLabel", wraplength=590, justify="left")
    self.lbl_afinidad.pack(anchor="w", pady=(0, 8))
    ttk.Label(izq, text="Brecha del voraz frente al óptimo (pedidos resueltos con DP)",
              style="Titulo.TLabel").pack(anchor="w")
    self.tabla_brecha = Tabla(izq, [("layout", "Layout", 220, "w"), ("n", "Pedidos", 60, "e"),
                                    ("media", "Brecha media", 85, "e"),
                                    ("max", "Máxima", 65, "e"),
                                    ("opt", "Voraz óptimo", 85, "e")], alto=5)
    self.tabla_brecha.pack(fill="x", pady=(4, 6))
    ttk.Label(izq, wraplength=540, justify="left", style="Nota.TLabel", text=(
        f"Cada pedido se resuelve con programación dinámica exacta hasta {config.UMBRAL_DP} "
        "productos y con el voraz por encima de ese umbral. Los intervalos de confianza se "
        "obtienen por bootstrap sobre los pedidos.")).pack(anchor="w")

    self.lienzo = Lienzo(cuerpo, figsize=(8, 6))
    self.lienzo.pack(side="left", fill="both", expand=True)
    self._grafico_vacio()

  def _grafico_vacio(self):
    fig = self.lienzo.fig
    fig.clear()
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.5, 0.5, "Ejecute el experimento para ver los gráficos", ha="center",
            va="center", color="#78909c", fontsize=11)
    self.lienzo.redibujar()

  # ------------------------------------------------------------ ejecución
  def ejecutar(self):
    try:
      n = int(self.n_pedidos.get())
      semilla = int(self.semilla.get())
      if n < 1:
        raise ValueError
    except ValueError:
      messagebox.showwarning("Datos no válidos", "Pedidos y semilla deben ser números enteros.")
      return
    con_controles = self.controles.get()
    self.cancelar = False
    self.boton.state(["disabled"])
    self.boton_csv.state(["disabled"])
    self.boton_cancelar.state(["!disabled"])
    self.barra.configure(value=0)
    self.lbl_prog.configure(text="Preparando layouts…")

    def trabajo(avance):
      if con_controles:
        self.servicio.agregar_controles()
      layouts = ([ACTUAL, OPTIMIZADO, "solo_frecuencia", "aleatorio"] if con_controles
                 else [ACTUAL, OPTIMIZADO])
      df = experimento.correr(self.servicio, n, semilla, layouts, progreso=avance,
                              cancelar=lambda: self.cancelar)
      res = {"df": df, "layouts": experimento.por_layout(df),
             "tamano": experimento.por_tamano(df), "brecha": experimento.brecha_voraz(df),
             "tiempos": experimento.tiempos_por_tamano(df)}
      if con_controles:
        res["pareado"] = experimento.comparar_pareado(df, OPTIMIZADO, "solo_frecuencia")
      return res

    tareas.ejecutar(self.winfo_toplevel(), trabajo, self._listo, self._fallo, self._avance)

  def _cancelar(self):
    self.cancelar = True
    self.lbl_prog.configure(text="Cancelando…")

  def _avance(self, i, total):
    self.barra.configure(value=100 * i / total)
    self.lbl_prog.configure(text=f"{i} de {total} pedidos")

  def _terminar(self):
    self.boton.state(["!disabled"])
    self.boton_cancelar.state(["disabled"])

  def _fallo(self, error):
    self._terminar()
    if isinstance(error, experimento.Cancelado):
      self.lbl_prog.configure(text="Cancelado")
      return
    self.lbl_prog.configure(text="Error")
    messagebox.showerror("No se pudo ejecutar el experimento", str(error))

  def _listo(self, res):
    self._terminar()
    self.resultado = res
    self.boton_csv.state(["!disabled"])
    self.barra.configure(value=100)
    self.lbl_prog.configure(text=f"{len(res['df']['order_id'].unique())} pedidos evaluados")
    self._mostrar(res)

  # ------------------------------------------------------------ resultados
  def _mostrar(self, res):
    filas = []
    for _, f in res["layouts"].iterrows():
      if f["layout"] == ACTUAL:
        filas.append((dibujo.nombre_layout(f["layout"]), f"{f['media_m']:.0f}", "—", "—", "—"))
      else:
        filas.append((dibujo.nombre_layout(f["layout"]), f"{f['media_m']:.0f}",
                      f"−{f['reduccion_pct']:.1f} %",
                      f"{f['ic95_bajo']:.1f} a {f['ic95_alto']:.1f}", f"{f['mejor_pct']:.0f} %"))
    self.tabla.llenar(filas)

    par = res.get("pareado")
    if par:
      txt = (f"Aporte de la afinidad (optimizado frente a solo frecuencia, pedido por pedido): "
             f"{par['reduccion_pct']:.2f} % menos distancia, IC 95 % "
             f"[{par['ic95_bajo']:.2f}, {par['ic95_alto']:.2f}] — "
             f"{'diferencia clara' if par['significativo'] else 'sin diferencia clara'}.")
    else:
      txt = "Active los layouts de control para medir cuánto aporta la afinidad."
    self.lbl_afinidad.configure(text=txt)

    self.tabla_brecha.llenar([
        (dibujo.nombre_layout(f["layout"]), int(f["pedidos"]), f"{f['brecha_media_pct']:.2f} %",
         f"{f['brecha_max_pct']:.1f} %", f"{f['voraz_optimo_pct']:.0f} %")
        for _, f in res["brecha"].iterrows()])

    fig = self.lienzo.fig
    fig.clear()
    grid = fig.add_gridspec(2, 2)
    dibujo.grafico_distancia_por_layout(fig.add_subplot(grid[0, 0]), res["layouts"])
    dibujo.grafico_distancia_por_tamano(fig.add_subplot(grid[0, 1]), res["tamano"])
    dibujo.grafico_tiempos(fig.add_subplot(grid[1, :]), res["tiempos"])
    self.lienzo.redibujar()

  def guardar(self):
    if not self.resultado:
      return
    ruta = filedialog.asksaveasfilename(
        defaultextension=".csv", filetypes=[("CSV", "*.csv")],
        initialfile="experimento_pedidos.csv", title="Guardar resultados por pedido")
    if ruta:
      self.resultado["df"].to_csv(ruta, index=False)
      self.app.estado(f"Resultados guardados en {ruta}")
