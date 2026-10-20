#!/usr/bin/env bash
# Instala y deja corriendo la versión web en una VM Ubuntu (AWS EC2 o Azure).
# Uso, desde la raíz del repositorio dentro de la VM:   bash deploy/instalar.sh
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

for f in departments.csv products.csv order_products__train.csv; do
  [ -f "$RAIZ/dataset/$f" ] || { echo "Falta dataset/$f (vea docs/DESPLIEGUE.md, paso 4)"; exit 1; }
done

sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip
python3 -m venv "$RAIZ/.venv"
"$RAIZ/.venv/bin/pip" install --upgrade pip
"$RAIZ/.venv/bin/pip" install -r "$RAIZ/requirements.txt"

sed -e "s#__RAIZ__#$RAIZ#g" -e "s#__USUARIO__#$(whoami)#g" "$RAIZ/deploy/almacen.service" \
  | sudo tee /etc/systemd/system/almacen.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now almacen
sudo systemctl restart almacen
echo "Listo. La página queda en el puerto 8501 (http://IP_PUBLICA:8501)."
echo "Estado: sudo systemctl status almacen   |   Registro: journalctl -u almacen -f"
