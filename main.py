"""Abre el aplicativo:  python main.py   (desde la raíz del repositorio)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from almacen.gui.app import main   # noqa: E402

if __name__ == "__main__":
  main()
