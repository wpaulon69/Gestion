#!/bin/bash
# Script de setup para ejecutar DENTRO del contenedor LXC
# Ejecutar como root dentro del CT

set -e

NAS_IP="10.175.6.10"
NAS_PASS="XXXX"  # <-- CAMBIAR ESTA PASSWORD
APP_DIR="/opt/auditar"

echo "[INFO] Setup SAMCo Auditoría..."

# ============ INSTALAR DEPENDENCIAS ============
echo "[1/5] Instalar paquetes..."
apt-get update
apt-get install -y python3 python3-venv git cifs-utils curl rsync

# ============ COPIAR APP ============
echo "[2/5] Copiar aplicación..."
mkdir -p $APP_DIR
echo "[INFO] Copiar archivos a $APP_DIR manualmente:"
echo "      scp -r /path/to/gestion/* root@10.175.6.200:$APP_DIR/"

# ============ CONFIGURAR CIFS ============
echo "[3/5] Configurar mounts CIFS..."

mkdir -p /mnt/nas /etc/samba

# Crear credenciales
cat > /etc/samba/creds.nas <<EOF
username=admin
password=$NAS_PASS
EOF
chmod 600 /etc/samba/creds.nas

# Montar shares
for cam in camHallCentral camEstacionamiento camPortonPral camConsultorioExt camOdontoRX camSUM camTaller camLaboratorio; do
    mkdir -p /mnt/nas/$cam
    mount -t cifs //${NAS_IP}/$cam /mnt/nas/$cam -o credentials=/etc/samba/creds.nas,uid=1000,gid=1000 2>/dev/null || echo "[WARN] $cam"
done

# Verificar
ls /mnt/nas/

# ============ PREPARAR PYTHON ============
echo "[4/5] Configurar Python..."
cd $APP_DIR

python3 -m venv gestion_env
source gestion_env/bin/activate

pip install requests tplink-omada-client

# ============ INICIAR SERVICIO ============
echo "[5/5] Iniciador servidor..."
nohup sh -c "source $APP_DIR/gestion_env/bin/activate && python3 $APP_DIR/proxmox/dashboard_server.py" > /var/log/auditar.log 2>&1 &

echo ""
echo "========================================"
echo "[OK] Setup completado!"
echo "========================================"
echo ""
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Para ejecutar auditoría manualmente:"
echo "  cd $APP_DIR"
echo "  source gestion_env/bin/activate"
echo "  python3 auditar.py"