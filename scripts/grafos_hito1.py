"""
TB1 - Complejidad Algorítmica (1ACC0184) - Grupo 2
Construcción y visualización de los grafos del almacén (Hito 1)
  G1: grafo de afinidad de productos (co-compra)
  G2: grafo del layout del almacén (ubicaciones + pasillos + depot)
"""
import os
from collections import Counter
from itertools import combinations

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ---------------- Configuración ----------------
RUTA_DATOS = "dataset"          # carpeta con los CSV de Instacart
RUTA_SALIDA = "salida"          # carpeta donde se guardan las imágenes
PRODUCTOS_POR_ZONA = 500        # nodos por integrante
UMBRAL_AFINIDAD = 20            # mín. de pedidos juntos para crear arista
TOP_K_DIBUJO = 3                # aristas más fuertes por nodo en la imagen
DIST_UBICACION = 1.0            # metros entre ubicaciones contiguas
DIST_PASILLO = 3.0              # metros entre pasillos paralelos

ZONAS = {
    "A": ["produce", "meat seafood", "deli", "bakery"],
    "B": ["dairy eggs", "frozen", "breakfast", "babies", "household", "personal care"],
    "C": ["snacks", "beverages", "pantry", "canned goods", "dry goods pasta",
          "international", "alcohol", "bulk", "other", "missing"],
}
NOMBRE_ZONA = {"A": "Frescos", "B": "Refrigerados, congelados y hogar",
               "C": "Abarrotes y bebidas"}
COLOR_ZONA = {"A": "#2e7d32", "B": "#1565c0", "C": "#ef6c00"}


# ---------------- 1. Carga y selección de nodos ----------------
def cargar_datos():
    productos = pd.read_csv(os.path.join(RUTA_DATOS, "products.csv"))
    departamentos = pd.read_csv(os.path.join(RUTA_DATOS, "departments.csv"))
    pedidos = pd.read_csv(os.path.join(RUTA_DATOS, "order_products__train.csv"))

    zona_de_dep = {dep: z for z, deps in ZONAS.items() for dep in deps}
    datos = (pedidos.merge(productos, on="product_id")
                    .merge(departamentos, on="department_id"))
    datos["zona"] = datos["department"].map(zona_de_dep)
    return datos


def seleccionar_nodos(datos):
    """Top N productos más pedidos de cada zona."""
    frecuencia = datos.groupby(["zona", "product_id"]).size().rename("freq").reset_index()
    seleccion = (frecuencia.sort_values("freq", ascending=False)
                           .groupby("zona").head(PRODUCTOS_POR_ZONA))
    info = (datos[["product_id", "product_name", "aisle_id", "department", "zona"]]
            .drop_duplicates("product_id").set_index("product_id"))
    return seleccion.join(info, on="product_id", rsuffix="_")


# ---------------- 2. G1: grafo de afinidad ----------------
def construir_afinidad(datos, nodos):
    ids = set(nodos["product_id"])
    filtrado = datos[datos["product_id"].isin(ids)]

    conteo = Counter()
    for _, grupo in filtrado.groupby("order_id")["product_id"]:
        for u, v in combinations(sorted(grupo), 2):
            conteo[(u, v)] += 1

    G1 = nx.Graph()
    for _, fila in nodos.iterrows():
        G1.add_node(fila.product_id, nombre=fila.product_name, zona=fila.zona,
                    departamento=fila.department, freq=fila.freq)
    for (u, v), peso in conteo.items():
        if peso >= UMBRAL_AFINIDAD:
            G1.add_edge(u, v, weight=peso)
    return G1


def reducir_para_dibujo(G, k=TOP_K_DIBUJO):
    """Conserva solo las k aristas más pesadas de cada nodo (solo para la imagen)."""
    H = nx.Graph()
    H.add_nodes_from(G.nodes(data=True))
    for n in G.nodes:
        mejores = sorted(G[n].items(), key=lambda e: e[1]["weight"], reverse=True)[:k]
        for vecino, attr in mejores:
            H.add_edge(n, vecino, **attr)
    return H


# ---------------- 3. G2: grafo del layout ----------------
def construir_layout(nodos):
    """
    Almacén rectangular: pasillos verticales paralelos, un pasillo transversal
    al frente (y=0) y otro al fondo. Cada producto ocupa una ubicación dentro
    de su pasillo (dos lados de estantería por cada metro).
    """
    G2 = nx.Graph()
    pasillos = []                      # (zona, aisle_id, lista de productos)
    for zona in ZONAS:
        sub = nodos[nodos["zona"] == zona].sort_values(["aisle_id", "product_id"])
        for aisle_id, grupo in sub.groupby("aisle_id"):
            pasillos.append((zona, aisle_id, list(grupo["product_id"])))

    largo_max = max((len(p) + 1) // 2 for _, _, p in pasillos)
    y_fondo = (largo_max + 1) * DIST_UBICACION

    G2.add_node("depot", tipo="depot", pos=(-DIST_PASILLO, 0.0), zona=None)
    frente_prev, fondo_prev, x_prev = "depot", None, -DIST_PASILLO

    for i, (zona, aisle_id, prods) in enumerate(pasillos):
        x = i * DIST_PASILLO
        frente, fondo = f"F{i}", f"R{i}"
        G2.add_node(frente, tipo="cruce", pos=(x, 0.0), zona=zona)
        G2.add_node(fondo, tipo="cruce", pos=(x, y_fondo), zona=zona)
        # pasillos transversales (frente y fondo)
        G2.add_edge(frente_prev, frente, weight=x - x_prev)
        if fondo_prev:
            G2.add_edge(fondo_prev, fondo, weight=DIST_PASILLO)

        anterior, y_anterior = frente, 0.0
        for j, pid in enumerate(prods):
            y = (j // 2 + 1) * DIST_UBICACION
            G2.add_node(pid, tipo="ubicacion", pos=(x, y), zona=zona, pasillo=aisle_id)
            if y != y_anterior:            # nuevo punto a lo largo del pasillo
                G2.add_edge(anterior, pid, weight=y - y_anterior)
                anterior, y_anterior = pid, y
            else:                          # mismo metro, lado opuesto
                G2.add_edge(anterior, pid, weight=0.0)
        G2.add_edge(anterior, fondo, weight=y_fondo - y_anterior)

        frente_prev, fondo_prev, x_prev = frente, fondo, x
    return G2, len(pasillos), y_fondo


# ---------------- 4. Visualización ----------------
def leyenda(zonas, extra=()):
    items = [(f"Zona {z}: {NOMBRE_ZONA[z]}", COLOR_ZONA[z]) for z in zonas] + list(extra)
    marcas = [Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=9)
              for _, c in items]
    plt.legend(marcas, [t for t, _ in items], loc="upper right")


def dibujar_afinidad(G, titulo, archivo):
    H = reducir_para_dibujo(G)
    pos = nx.spring_layout(H, k=0.15, iterations=60, seed=42)
    colores = [COLOR_ZONA[H.nodes[n]["zona"]] for n in H]
    tamanos = [10 + H.nodes[n]["freq"] / 60 for n in H]
    plt.figure(figsize=(12, 12))
    nx.draw_networkx_edges(H, pos, alpha=0.15, width=0.5)
    nx.draw_networkx_nodes(H, pos, node_color=colores, node_size=tamanos, alpha=0.85)
    plt.title(titulo, fontsize=14)
    leyenda(sorted({H.nodes[n]["zona"] for n in H}))
    plt.axis("off")
    plt.savefig(os.path.join(RUTA_SALIDA, archivo), dpi=200, bbox_inches="tight")
    plt.close()


def dibujar_layout(G, titulo, archivo):
    pos = nx.get_node_attributes(G, "pos")
    colores = []
    for n in G:
        t = G.nodes[n]["tipo"]
        colores.append("red" if t == "depot" else
                       "gray" if t == "cruce" else COLOR_ZONA[G.nodes[n]["zona"]])
    tamanos = [120 if G.nodes[n]["tipo"] == "depot" else 6 for n in G]
    fig, ax = plt.subplots(figsize=(16, 8))
    nx.draw_networkx_edges(G, pos, width=0.4, alpha=0.5, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=colores, node_size=tamanos, ax=ax)
    ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)
    ax.set_title(titulo, fontsize=14)
    ax.set_xlabel("metros"); ax.set_ylabel("metros")
    zonas = sorted({d["zona"] for _, d in G.nodes(data=True) if d["zona"]})
    extra = [("Cruce de pasillos", "gray")]
    if "depot" in G:
        extra.insert(0, ("Depot", "red"))
    leyenda(zonas, extra=extra)
    plt.savefig(os.path.join(RUTA_SALIDA, archivo), dpi=200, bbox_inches="tight")
    plt.close()


def resumen(G, nombre):
    print(f"{nombre}: nodos={G.number_of_nodes()}, aristas={G.number_of_edges()}, "
          f"densidad={nx.density(G):.4f}, grado_prom={2 * G.number_of_edges() / G.number_of_nodes():.1f}, "
          f"aislados={nx.number_of_isolates(G)}, componentes={nx.number_connected_components(G)}")


# ---------------- Main ----------------
if __name__ == "__main__":
    os.makedirs(RUTA_SALIDA, exist_ok=True)
    datos = cargar_datos()
    nodos = seleccionar_nodos(datos)

    G1 = construir_afinidad(datos, nodos)
    resumen(G1, "G1 completo")
    dibujar_afinidad(G1, "G1 - Grafo de afinidad (1,500 productos)", "G1_completo.png")
    for z in ZONAS:
        sub = G1.subgraph([n for n, d in G1.nodes(data=True) if d["zona"] == z])
        resumen(sub, f"G1 zona {z}")
        dibujar_afinidad(sub, f"G1 - Zona {z}: {NOMBRE_ZONA[z]}", f"G1_zona_{z}.png")

    G2, n_pasillos, largo = construir_layout(nodos)
    resumen(G2, "G2 completo")
    print(f"Pasillos: {n_pasillos}, largo del pasillo: {largo:.0f} m, "
          f"ancho del almacén: {(n_pasillos - 1) * DIST_PASILLO:.0f} m")
    dibujar_layout(G2, "G2 - Layout del almacén (zonas A, B y C)", "G2_completo.png")
    for z in ZONAS:
        nodos_z = [n for n, d in G2.nodes(data=True) if d["zona"] == z]
        sub2 = G2.subgraph(nodos_z)
        resumen(sub2, f"G2 zona {z}")
        dibujar_layout(sub2, f"G2 - Zona {z}: {NOMBRE_ZONA[z]}", f"G2_zona_{z}.png")