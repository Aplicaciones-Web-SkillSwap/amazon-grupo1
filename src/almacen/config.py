"""Constantes del proyecto (las mismas del script del hito 1, más los umbrales de ruteo)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RUTA_DATOS = RAIZ / "dataset"       # carpeta con los CSV de Instacart
RUTA_SALIDA = RAIZ / "salida"       # carpeta donde se guardan imágenes y archivos generados

PRODUCTOS_POR_ZONA = 500            # nodos por integrante
UMBRAL_AFINIDAD = 20                # mín. de pedidos juntos para crear arista en G1
TOP_K_DIBUJO = 3                    # aristas más fuertes por nodo en la imagen
DIST_UBICACION = 1.0                # metros entre ubicaciones contiguas
DIST_PASILLO = 3.0                  # metros entre pasillos paralelos
CAPACIDAD_PASILLO = 16              # tope de productos por pasillo en el layout optimizado (UFDS)
SEMILLA = 42                        # semilla fija para el muestreo de pedidos

UMBRAL_FUERZA_BRUTA = 10            # hasta este tamaño de pedido se usa fuerza bruta + backtracking
UMBRAL_DP = 15                      # PROVISIONAL: umbral T de Held-Karp, se calibra en la capa 6

ZONAS = {
    "A": ["produce", "meat seafood", "deli", "bakery"],
    "B": ["dairy eggs", "frozen", "breakfast", "babies", "household", "personal care"],
    "C": ["snacks", "beverages", "pantry", "canned goods", "dry goods pasta",
          "international", "alcohol", "bulk", "other", "missing"],
}
# Departamento de Instacart que el hito 1 dejó fuera de las zonas (0.32% de las líneas).
DEPARTAMENTOS_SIN_ZONA = ["pets"]

NOMBRE_ZONA = {"A": "Frescos", "B": "Refrigerados, congelados y hogar",
               "C": "Abarrotes y bebidas"}
COLOR_ZONA = {"A": "#2e7d32", "B": "#1565c0", "C": "#ef6c00"}
