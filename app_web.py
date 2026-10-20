"""Abre la versión web:  streamlit run app_web.py   (desde la raíz del repositorio)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from almacen.web.app import main   # noqa: E402

main()
