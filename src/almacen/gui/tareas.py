"""Ejecuta trabajo pesado en un hilo para que la ventana no se congele.

El hilo solo calcula; los callbacks `exito`, `error` y `progreso` se llaman en el hilo de
tkinter (con root.after), que es el único que puede tocar los widgets."""
import queue
import threading


def ejecutar(root, trabajo, exito, error=None, progreso=None, intervalo_ms=50):
  """Corre trabajo(avance) en un hilo. `avance(i, n)` reporta progreso desde el hilo."""
  cola = queue.Queue()

  def hilo():
    try:
      resultado = trabajo(lambda i, n: cola.put(("progreso", (i, n))))
    except Exception as e:                       # se devuelve al hilo de la interfaz
      cola.put(("error", e))
    else:
      cola.put(("exito", resultado))

  def sondear():
    try:
      while True:
        tipo, dato = cola.get_nowait()
        if tipo == "progreso":
          if progreso is not None:
            progreso(*dato)
        elif tipo == "exito":
          exito(dato)
          return
        else:
          if error is not None:
            error(dato)
          else:
            raise dato
          return
    except queue.Empty:
      pass
    root.after(intervalo_ms, sondear)

  threading.Thread(target=hilo, daemon=True).start()
  root.after(intervalo_ms, sondear)
