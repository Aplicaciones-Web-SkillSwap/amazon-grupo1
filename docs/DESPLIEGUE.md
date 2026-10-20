# Despliegue de la versión web en una máquina virtual

La versión web (`app_web.py`, Streamlit) se publica en una VM Linux de **AWS (EC2)** o de **Azure**.
Los pasos son los mismos; solo cambia cómo se crea la VM y cómo se abre el puerto.

**Tamaño recomendado:** 2 vCPU y 4 GB de RAM (EC2 `t3.medium`, Azure `B2s`). La app usa unos 0.5 GB
por proceso al cargar el dataset; con 2 GB (`t3.small`) también corre, pero con poco margen.
**Sistema:** Ubuntu Server 22.04 o 24.04 LTS.

## 1. Crear la VM

**AWS:** EC2 → *Launch instance* → Ubuntu Server 24.04 → tipo `t3.medium` → crear un *key pair*
(se descarga un `.pem`) → en *Network settings* permita **SSH (22)** y agregue una regla **TCP 8501**
desde *Anywhere* (`0.0.0.0/0`).

**Azure:** *Virtual machines* → Crear → Ubuntu Server 24.04 → tamaño `B2s` → autenticación con clave SSH
(se descarga un `.pem`) → en *Networking* agregue una regla de entrada para el puerto **8501** (TCP).

Anote la **IP pública** de la VM.

## 2. Conectarse

En PowerShell (cambie la ruta de la clave, el usuario y la IP; en AWS el usuario es `ubuntu`,
en Azure el que eligió al crear la VM):

```powershell
ssh -i C:\ruta\clave.pem ubuntu@IP_PUBLICA
```

## 3. Traer el código (dentro de la VM)

```bash
sudo apt-get update && sudo apt-get install -y git unzip
git clone https://github.com/Aplicaciones-Web-SkillSwap/amazon-grupo1.git
cd amazon-grupo1
```

## 4. Subir el dataset (desde su PC)

El dataset no está en git. En otra ventana de PowerShell, dentro de la carpeta del proyecto:

```powershell
ssh -i C:\ruta\clave.pem ubuntu@IP_PUBLICA "mkdir -p ~/amazon-grupo1/dataset"
scp -i C:\ruta\clave.pem dataset\departments.csv dataset\products.csv dataset\order_products__train.csv ubuntu@IP_PUBLICA:~/amazon-grupo1/dataset/
```

## 5. Instalar y arrancar (dentro de la VM)

```bash
bash deploy/instalar.sh
```

El script crea el entorno virtual, instala `requirements.txt` y registra el servicio `almacen`
(systemd), que arranca solo si la VM se reinicia. La primera carga tarda unos segundos.

## 6. Abrir la página

`http://IP_PUBLICA:8501`

## Operación

| Qué | Comando |
|---|---|
| Ver si está corriendo | `sudo systemctl status almacen` |
| Ver el registro | `journalctl -u almacen -f` |
| Reiniciar | `sudo systemctl restart almacen` |
| Actualizar el código | `cd ~/amazon-grupo1 && git pull && sudo systemctl restart almacen` |

## Problemas frecuentes

- **La página no abre:** casi siempre es el puerto 8501 sin abrir en el *security group* (AWS) o en el
  NSG (Azure), o falta `http://` en la dirección.
- **El script dice que falta el dataset:** repita el paso 4.
- **Quedó sin memoria:** use un tamaño de 4 GB.
- **Costos:** apague (*Stop*) la VM cuando no la use; las IP públicas de AWS cambian al reiniciar
  salvo que se asigne una *Elastic IP*.

## Probar en local antes de subirla

```powershell
pip install -r requirements.txt
streamlit run app_web.py
```
