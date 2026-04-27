#!/bin/bash
# Script de setup para ejecutar DENTRO de la VM Proxmox (Debian 12)
# Ejecutar como root dentro de la VM

set -e

NAS_IP="10.175.6.10"
NAS_PASS="XXXX"  # <-- CAMBIAR ESTA PASSWORD
APP_DIR="/opt/auditar"

echo "[INFO] Setup SAMCo Auditoría VM..."

# ============ INSTALAR DEPENDENCIAS ============
echo "[1/6] Actualizar e instalar paquetes..."
apt-get update
apt-get upgrade -y
apt-get install -y python3 python3-venv git cifs-utils curl rsync net-tools

# ============ CONFIGURAR RED ============
echo "[2/6] Verificar red..."
hostname -I

# ============ COPIAR APP ============
echo "[3/6] Copiar aplicación..."
mkdir -p $APP_DIR
echo "[INFO] Desde Proxmox host copiar:"
echo "      scp -r /path/to/gestion/* root@10.175.6.200:$APP_DIR/"

# ============ CONFIGURAR CIFS ============
echo "[4/6] Configurar mounts CIFS..."

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
    mount -t cifs //${NAS_IP}/$cam /mnt/nas/$cam -o credentials=/etc/samba/creds.nas,uid=1000,gid=1000 2>/dev/null || echo "[WARN] $cam no montada"
done

# Verificar mounts
ls -la /mnt/nas/

# ============ PREPARAR PYTHON ============
echo "[5/6] Configurar Python..."
cd $APP_DIR

python3 -m venv gestion_env
source gestion_env/bin/activate

pip install requests tplink-omada-client

# ============ INICIAR SERVICIO ============
echo "[6/6] Configurar servicio systemd..."

cat > /etc/systemd/system/auditar.service <<EOF
[Unit]
Description=SAMCo Auditoria Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/gestion_env/bin/python $APP_DIR/proxmox/dashboard_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable auditar
systemctl start auditar

# Verificar
systemctl status auditar --no-pager

echo ""
echo "========================================"
echo "[OK] Setup completado!"
echo "========================================"
echo ""
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Comandos:"
echo "  systemctl status auditar    # Estado"
echo "  systemctl restart auditar   # Reiniciar"
echo "  journalctl -u auditar -f   # Ver logs"