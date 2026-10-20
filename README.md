# Gestión de almacenes inteligentes (Amazon)

**Complejidad Algorítmica 1ACC0184 (2026-20) · UPC · Grupo 2**
Dataset: [Instacart Market Basket Analysis](https://www.kaggle.com/c/instacart-market-basket-analysis) (Kaggle).

El proyecto modela un almacén con grafos y resuelve dos problemas: **dónde ubicar los productos**
para que se pidan juntos desde lugares cercanos, y **en qué orden recorrer el almacén** para
armar un pedido (picking). Incluye un aplicativo de escritorio (tkinter), una versión web (Streamlit) desplegable en una máquina virtual y un experimento que
compara la distribución actual contra la optimizada sobre pedidos reales.

## Técnicas y dónde están

Cada módulo de `src/almacen/` lleva en su encabezado una línea `TÉCNICA:` que dice qué técnica
implementa y quién la invoca. Resumen:

| Técnica | Funciones | Para qué se usa | Se ejecuta cuando... |
|---|---|---|---|
| Lista de adyacencia ponderada | `grafo.Grafo` | Estructura de G₁ (afinidad) y G₂ (almacén) | Al cargar la app (`Servicio.desde_csv`) |
| Construcción de G₁ | `afinidad.construir_afinidad` | Productos unidos por pedidos en común | Al cargar la app; se dibuja en *Datos y grafos* |
| Construcción de G₂ | `layout.construir_layout` | Plano del almacén (pasillos, cruces, depot) | Al cargar y al reoptimizar; se dibuja en *Datos y grafos* y *Ubicación* |
| BFS | `bfs.bfs`, `bfs.camino`, `bfs.componentes` | Comprobar que todo G₂ es alcanzable desde el depot | `Servicio.alcance_bfs` → métricas de *Datos y grafos* |
| Floyd-Warshall | `floyd.floyd_warshall`, `distancias.Distancias` | Distancias mínimas entre cruces (197 nodos) y entre productos | Una vez por layout al cargar; alimenta todo el ruteo |
| UFDS (Quick-Union ponderado) | `ufds.UFDS`, `reubicacion.agrupar` | Unir productos afines con un tope de 16 por pasillo | Al cargar y con *Ejecutar UFDS* en *Ubicación* |
| Voraz | `reubicacion.empaquetar`, `ruteo.voraz` | Acomodar grupos en pasillos (first-fit) y ruta por vecino más cercano | *Ubicación*; técnica *Voraz* en *Ruteo* |
| Fuerza bruta | `ruteo.fuerza_bruta` | Ruta exacta de pedidos de hasta 9 productos | Técnica *Fuerza bruta* en *Ruteo* |
| Backtracking | `ruteo.backtracking` | Ruta exacta con poda (hasta 11 productos) | Técnica *Backtracking* en *Ruteo* |
| Programación dinámica (Held-Karp) | `ruteo.held_karp`, `ruteo.held_karp_opt` | Ruta exacta; versión base y versión optimizada con NumPy (hasta 22) | Técnica *DP* en *Ruteo*; usada por *Comparación* |
| Selección según tamaño del pedido | `ruteo.elegir_tecnica`, `ruteo.resolver` | n ≤ 10: backtracking + DP verificadas entre sí; hasta T = 19: DP optimizada; más: voraz | Técnica *Automática* en *Ruteo* |

La interfaz (tkinter o web) nunca calcula nada: solo llama a `servicio.Servicio`, que orquesta los módulos
anteriores. En la pantalla de *Ruteo* el resultado siempre indica qué técnica se ejecutó.

## Instalación

Requiere **Python 3.10 o superior** (en Windows, el instalador de python.org ya incluye tkinter).
Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # si falla: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
```

### Dataset

Descargue Instacart de Kaggle y copie estos tres archivos en la carpeta `dataset/`
(no se sube a git):

```
dataset/departments.csv
dataset/products.csv
dataset/order_products__train.csv
```

## Usar el aplicativo

```powershell
python main.py
```

Al abrir tarda unos 8 segundos en cargar el dataset y construir los grafos. Luego hay cuatro pestañas
que siguen el orden del proceso:

**1. Datos y grafos**: métricas del dataset (pedidos, aristas, densidad, BFS, Floyd-Warshall).
Elija un grafo en la lista y pulse *Dibujar*: G₁ completo o por zona, o G₂ (plano del almacén
actual u optimizado). Con la barra inferior puede acercar y mover el dibujo.

**2. Ubicación**: muestra el resultado de UFDS. A la izquierda, los pasillos del layout optimizado
(clic en uno para resaltarlo en el plano); a la derecha, el plano actual arriba y el optimizado abajo.
Cambie la capacidad *K* y pulse *Ejecutar UFDS* para recalcular (mínimo 16, porque 98 pasillos × 15 no
alcanzan para 1,500 productos).

**3. Ruteo**:
1. Elija el pedido: *Aleatorio* (opcionalmente de un tamaño dado) o *Por número de pedido*, y pulse *Obtener pedido*.
2. Elija la *técnica* (o *Automática*, que decide según el tamaño) y el *layout* (actual u optimizado).
3. Pulse *Calcular ruta*: se dibuja el recorrido numerado sobre el plano y se muestran la distancia
   total (ciclo depot → productos → depot) y el tiempo de ejecución del algoritmo.
4. *Comparar técnicas* corre backtracking, DP y voraz sobre el mismo pedido; *Comparar layouts* lo
   rutea en el actual y en el optimizado. *Acercar a la ruta* ajusta el zoom.

**4. Comparación**: ejecuta el experimento sobre una muestra de pedidos reales (300 por defecto). Muestra
la distancia por layout con intervalos de confianza, el aporte de la afinidad, la brecha del voraz y gráficos
de distancia y tiempo. Active *layouts de control* para medir cuánto aporta cada ingrediente de la
reubicación. *Guardar CSV* exporta el detalle por pedido.

## Versión web

Es la misma lógica (`servicio.py`) con una página Streamlit: pestañas *Inicio*, *Ruteo*, *Ubicación*,
*Comparación* y *Grafos*. Al abrirla ya hay un pedido de ejemplo cargado; basta pulsar *Calcular ruta*.

```powershell
pip install -r requirements.txt
streamlit run app_web.py
```

Se abre en http://localhost:8501. Cada pestaña indica qué técnicas usa. Para publicarla en una máquina
virtual de AWS o Azure vea [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).

## Scripts

```powershell
python scripts/experimento.py --pedidos 1500      # tablas del experimento, CSV en salida/
python scripts/benchmark_ruteo.py                 # tiempos por técnica y T sugerido, CSV en salida/
python scripts/grafos_hito1.py                    # figuras y métricas del hito 1
```

`benchmark_ruteo.py` imprime el umbral T que cumple el límite de 1 s por pedido en **su** equipo; si
difiere de `UMBRAL_DP` en `src/almacen/config.py`, actualice ese valor.

## Pruebas

```powershell
python -m pytest -q
```

131 pruebas. Las que usan el dataset real se omiten si no está en `dataset/`, y las de la ventana se
omiten si no hay pantalla. Las distancias del almacén se validan contra un Dijkstra independiente
sobre las 1,697 ubicaciones; las técnicas exactas se validan entre sí.

## Estructura

```
main.py                    abre el aplicativo de escritorio (tkinter)
app_web.py                 abre la versión web (streamlit run app_web.py)
deploy/  docs/             scripts y guía de despliegue en una VM
scripts/                   experimento, benchmark y script del hito 1
src/almacen/
  config.py                constantes (zonas, umbrales, capacidad, T)
  datos.py  afinidad.py    carga de Instacart, selección de 1,500 productos, grafo G₁
  grafo.py  layout.py      lista de adyacencia ponderada, grafo del almacén G₂
  bfs.py  floyd.py  distancias.py
  ufds.py  reubicacion.py
  ruteo.py  benchmark.py
  servicio.py              fachada que usa la interfaz
  experimento.py           comparación de layouts sobre pedidos reales
  gui/                     interfaz tkinter (sin lógica de algoritmos)
  web/                     interfaz web Streamlit (sin lógica de algoritmos)
tests/
```

## Decisiones de diseño

- **Selección de nodos:** los 500 productos más pedidos de cada zona (A, B, C). El departamento `pets`
  (0.32 % de las líneas) queda fuera, como en el hito 1. Los empates en el corte se resuelven por
  `product_id` para que el resultado sea idéntico en cualquier equipo.
- **Almacén:** 98 pasillos paralelos a 3 m, dos ubicaciones por metro, pasillos transversales al frente y al
  fondo, depot en la esquina frontal. El layout optimizado usa **el mismo almacén físico** (mismo largo de
  pasillo, 76 m) con un tope de 16 productos por pasillo.
- **UFDS:** une los productos de las aristas más fuertes de G₁ mientras el grupo no pase de 16. Los grupos
  se acomodan en pasillos empezando por los de mayor frecuencia media, y dentro del pasillo los más
  pedidos quedan al frente.
- **Pedidos:** se eliminan productos repetidos; un pedido es un ciclo que sale del depot y vuelve.
- **Poda en Held-Karp:** implementada pero apagada por defecto (ver resultados).

## Resultados (semilla 42, reproducibles con los scripts)

### Layouts: 1,500 pedidos reales, ruteo exacto con DP hasta 19 productos

| Layout | Distancia media | Reducción frente al actual (IC 95 %) | Pedidos con menor distancia |
|---|---|---|---|
| Actual (catálogo) | 547 m | – | – |
| Aleatorio, 16 por pasillo (control) | 509 m | 7.0 % (5.4 – 8.6) | 63 % |
| Solo frecuencia, sin afinidad (control) | 405 m | 26.0 % (24.5 – 27.6) | 79 % |
| **Optimizado (UFDS + frecuencia)** | **401 m** | **26.8 % (25.2 – 28.3)** | 79 % |

- La mayor parte de la mejora viene de poner lo más pedido al frente y compactar los productos
  (aleatorio ≈ 7 puntos por compactar; frecuencia ≈ 19 puntos más).
- La afinidad (UFDS) aporta un **1.07 % adicional** sobre solo frecuencia (IC 95 %: 0.42 – 1.71),
  pequeño pero estadísticamente claro. En pedidos de 1 a 5 productos no hay diferencia; aparece desde
  6 productos (454.8 m frente a 460.4 m, y 567.4 m frente a 589.0 m en pedidos de 16 a 19).
- Los pasillos del layout optimizado ocupan solo los primeros ~8 m, mientras el largo físico se
  mantiene en 76 m; parte de la ganancia es esa compactación.

### Técnicas de ruteo

| Productos | Held-Karp base | Held-Karp optimizado |
|---|---|---|
| 12 | 0.043 s | 0.003 s |
| 16 | 1.34 s | 0.047 s |
| 19 | – | 0.70 s |
| 20 | – | 1.58 s |
| 21 | – | 3.50 s |

Mediana de 5 pedidos reales por tamaño. Backtracking tarda de 1 a 4 s con 11 productos, por eso el corte
de fuerza bruta/backtracking es 10. El voraz queda, en promedio, a 0.25 % del óptimo en el layout
optimizado y es exacto en el 91 % de los pedidos, pero con 21 % de brecha en el peor caso. La
poda por cota superior **no reduce el tiempo** (+10 a 20 %): la cota inferior que usa es ~40 % del
óptimo y casi no descarta estados.

## Flujo de trabajo

Una rama por tema (`feature/<tema>`), un commit por capa con mensajes
[Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/) y PR a `main` con *Squash and merge*.
