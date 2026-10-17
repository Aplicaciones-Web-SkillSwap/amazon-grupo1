import pytest

# Mini dataset con el mismo formato de Instacart.
#   zona A = produce (productos 1, 2, 3); zona B = dairy eggs (4, 5); zona C = snacks (6, 7)
#   producto 8 es de "pets", que no pertenece a ninguna zona
DEPARTAMENTOS = "department_id,department\n1,produce\n2,dairy eggs\n3,snacks\n4,pets\n"
PRODUCTOS = (
    "product_id,product_name,aisle_id,department_id\n"
    "1,Banana,1,1\n2,Apple,1,1\n3,Kale,2,1\n"
    "4,Milk,3,2\n5,Eggs,3,2\n"
    "6,Chips,4,3\n7,Nuts,4,3\n"
    "8,Dog food,5,4\n"
)
PEDIDOS = {1: [1, 2, 4], 2: [1, 2, 4, 6], 3: [1, 2], 4: [1, 4, 8], 5: [3, 5, 6, 7], 6: [1, 2, 3]}


@pytest.fixture
def carpeta_datos(tmp_path):
  (tmp_path / "departments.csv").write_text(DEPARTAMENTOS)
  (tmp_path / "products.csv").write_text(PRODUCTOS)
  lineas = ["order_id,product_id,add_to_cart_order,reordered"]
  for oid, prods in PEDIDOS.items():
    for k, p in enumerate(prods, start=1):
      lineas.append(f"{oid},{p},{k},0")
  (tmp_path / "order_products__train.csv").write_text("\n".join(lineas) + "\n")
  return tmp_path
