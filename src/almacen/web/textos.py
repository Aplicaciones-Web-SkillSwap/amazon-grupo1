"""Textos y nombres que usa la versión web (sin dependencias de Streamlit ni de tkinter)."""
from almacen import config
from almacen.servicio import ACTUAL, OPTIMIZADO

# Lo que se muestra al elegir -> clave que entiende Servicio.rutear
TECNICAS = {
    "Automática (según el tamaño del pedido)": "auto",
    "Fuerza bruta": "fuerza_bruta",
    "Backtracking": "backtracking",
    "Programación dinámica (Held-Karp optimizado)": "dp",
    "Voraz (vecino más cercano)": "voraz",
}
# Lo que ejecutó realmente Servicio.rutear -> texto para el usuario
NOMBRE_TECNICA = {
    "exacta_verificada": "Backtracking + Programación dinámica (verificadas entre sí)",
    "dp": "Programación dinámica (Held-Karp optimizado)",
    "backtracking": "Backtracking", "fuerza_bruta": "Fuerza bruta",
    "voraz": "Voraz (vecino más cercano)", "dp_base": "Held-Karp base",
}
AYUDA_TECNICA = {
    "auto": (f"Hasta {config.UMBRAL_FUERZA_BRUTA} productos corre backtracking y programación "
             f"dinámica y comprueba que den lo mismo; hasta {config.UMBRAL_DP} usa programación "
             "dinámica; más allá usa el voraz, que es rápido pero no siempre óptimo."),
    "fuerza_bruta": "Prueba todos los órdenes. Exacta, pero solo viable hasta 9 productos.",
    "backtracking": "Prueba órdenes y abandona los que ya son más largos que el mejor. Hasta 11 productos.",
    "dp": "Guarda las mejores rutas parciales de cada subconjunto. Exacta, hasta 22 productos.",
    "voraz": "Va siempre al producto más cercano. Instantánea, pero puede dar una ruta más larga.",
}
LAYOUTS = {"Actual (catálogo de Instacart)": ACTUAL, "Optimizado (UFDS)": OPTIMIZADO}

PASOS_INICIO = (
    "**1. Ruteo.** Ya hay un pedido de ejemplo cargado: pulse *Calcular ruta* y vea el recorrido "
    "numerado sobre el plano del almacén.",
    "**2. Pruebe otras opciones.** Cambie la técnica, el layout o el pedido, y use *Comparar "
    "técnicas* o *Comparar layouts* para ver las diferencias.",
    "**3. Ubicación y Comparación.** Vea cómo UFDS reubica los productos y cuánta distancia se "
    "ahorra en una muestra de pedidos de prueba (no usados para construir el layout).",
)

TECNICAS_DEL_PROYECTO = [
    ("Lista de adyacencia ponderada", "Grafos G₁ y G₂", "Datos y grafos"),
    ("BFS", "Comprobar que todo el almacén es alcanzable desde el depot", "Datos y grafos"),
    ("Floyd-Warshall", "Distancias entre cruces de pasillo y entre productos", "Ruteo, Ubicación"),
    ("UFDS", "Agrupar productos afines con un tope de 16 por pasillo", "Ubicación"),
    ("Voraz", "Empaquetar grupos en pasillos y ruta del vecino más cercano", "Ubicación, Ruteo"),
    ("Fuerza bruta y backtracking", "Ruta exacta de pedidos chicos", "Ruteo"),
    ("Programación dinámica", "Ruta exacta (Held-Karp, base y optimizada)", "Ruteo, Comparación"),
]
