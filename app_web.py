"""Abre la versión web:  streamlit run app_web.py   (desde la raíz del repositorio)."""
import hashlib
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC))


def huella_del_codigo():
  huella = hashlib.md5()
  for archivo in sorted((SRC / "almacen").rglob("*.py")):
    huella.update(archivo.read_bytes())
  return huella.hexdigest()


# Streamlit vuelve a ejecutar este archivo en cada interacción, pero los módulos importados
# quedan en memoria. Si un redespliegue trae código nuevo sin reiniciar el proceso (pasa en
# Streamlit Community Cloud), se seguiría ejecutando la versión vieja del paquete. Por eso,
# si el código cambió desde la última ejecución, se descartan esos módulos y se cargan de nuevo.
huella = huella_del_codigo()
if getattr(sys, "_almacen_huella", huella) != huella:
  for nombre in [m for m in sys.modules if m == "almacen" or m.startswith("almacen.")]:
    del sys.modules[nombre]
sys._almacen_huella = huella

from almacen.web.app import main   # noqa: E402

main()
