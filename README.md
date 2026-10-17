# Almacenes inteligentes (Amazon) - Complejidad Algorítmica 1ACC0184 (2026-20)

Optimización de la ubicación de productos y de las rutas de picking de un almacén,
modelado con grafos. Dataset: Instacart (Kaggle). Grupo 2.

## Preparar el entorno (PowerShell, desde la raíz del repo)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # si falla: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
```

Colocar los CSV de Instacart en `dataset/` (`products.csv`, `departments.csv`, `order_products__train.csv`).

## Pruebas

```powershell
python -m pytest
```

## Script del hito 1

```powershell
python scripts/grafos_hito1.py    # ejecutar desde la raíz del repo
```
