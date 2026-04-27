#!/bin/bash
# Deploy script para auditoría SAMCo en Proxmox LXC
# Ejecutar como root en el host Proxmox

set -e

# ============ CONFIGURACIÓN ============
VM_ID=200
NAME="samco-auditar"
HOST_IP="10.175.6.200"
NAS_IP="10.175.6.10"
ROOT_PASSWORD="Gestion2024!"
STORAGE="local-lvm"
TEMPLATE="local:vztmpl/debian-12-standard_12.2-1_amd64.tar.gz"

# ============ VERIFICACIONES ============
echo "[INFO] Verificando entorno..."

if ! command -v pct &> /dev/null; then
    echo "[ERROR] No es un host Proxmox"
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Ejecutar como root"
    exit 1
fi

# ============ CREAR CONTENEDOR ============
echo "[INFO] Verificando CT $VM_ID..."

if pct status $VM_ID &> /dev/null; then
    echo "[WARN] CT $VM_ID ya existe. Opciones:"
    echo "  [1] Eliminar y recrear"
    echo "  [2] Usar existente"
    read -p "Opción [1]: " opt
    if [ "$opt" == "2" ]; then
        echo "[INFO] Usando CT existente"
    else
        echo "[INFO] Eliminando CT..."
        pct stop $VM_ID 2>/dev/null || true
        pct destroy $VM_ID 2>/dev/null || true
        create_ct
    fi
else
    create_ct
fi

# ============ INSTALAR PAQUETES ============
echo "[INFO] Instalando paquetes..."
pct exec $VM_ID -- bash -c "apt-get update && apt-get install -y python3 python3-venv git cifs-utils curl"

# ============ SUBIR SCRIPTS ============
echo "[INFO] Subiendo scripts..."
pct exec $VM_ID -- mkdir -p /opt/auditar
pct exec $VM_ID -- bash -c "apt-get install -y rsync" 2>/dev/null || true

RSYNC_SRC="/opt/src/gestion"  # Ajustar path local
echo "[INFO] Copiando archivos..."
# Copiar repo al contenedor
pct push $VM_ID .. $RSYNC_SRC /opt/auditar

# ============ CONFIGURAR MOUNT CIFS ============
echo "[INFO] Configurando mounts CIFS..."
pct exec $VM_ID -- bash -c "
    mkdir -p /mnt/nas /etc/samba
    echo 'username=admin' > /etc/samba/creds.nas
    echo 'password=Gestion2024!' >> /etc/samba/creds.nas  # CAMBIAR
    chmod 600 /etc/samba/creds.nas
"

# Agregar al fstab
pct exec $VM_ID -- bash -c "
    cat >> /etc/fstab <<EOF
//${NAS_IP}/camHallCentral /mnt/nas/camHallCentral cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
//${NAS_IP}/camEstacionamiento /mnt/nas/camEstacionamiento cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
//${NAS_IP}/camPortonPral /mnt/nas/camPortonPral cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
//${NAS_IP}/camConsultorioExt /mnt/nas/camConsultorioExt cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
//${NAS_IP}/camOdontoRX /mnt/nas/camOdontoRX cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
//${NAS_IP}/camSUM /mnt/nas/camSUM cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
//${NAS_IP}/camTaller /mnt/nas/camTaller cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
//${NAS_IP}/camLaboratorio /mnt/nas/camLaboratorio cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
EOF
"

# ============ PREPARAR PYTHON ============
echo "[INFO] Configurando Python..."
pct exec $VM_ID -- bash -c "
    cd /opt/auditar
    python3 -m venv gestion_env
    source gestion_env/bin/activate
    pip install requests tplink-omada-client pyproxmox
"

# ============ INICIAR SERVICIO ============
echo "[INFO] Iniciando servidor..."
pct exec $VM_ID -- bash -c "
    cd /opt/auditar
    source gestion_env/bin/activate
    nohup python3 proxmox/dashboard_server.py > /var/log/auditar.log 2>&1 &
"

# ============ RESUMEN ============
echo ""
echo "========================================"
echo "[OK] Deploy completado!"
echo "========================================"
echo ""
echo "CT ID: $VM_ID"
echo "IP: $HOST_IP"
echo "Dashboard: http://$HOST_IP:8080"
echo ""
echo "Para acceder:"
echo "  pct enter $VM_ID"
echo "  cd /opt/auditar"
echo "  source gestion_env/bin/activate"
echo "  python3 auditar.py"
echo ""

create_ct() {
    echo "[INFO] Creando CT $VM_ID..."
    pct create $VM_ID $TEMPLATE \
        --hostname $NAME \
        --memory 1024 \
        --cores 1 \
        --storage $STORAGE \
        --password $ROOT_PASSWORD \
        --net0 name=eth0,ip=$HOST_IP/24,gw=10.175.6.1 \
        --features keyctl=1,nesting=1 \
        --unprivileged 0
    
    pct start $VM_ID
    sleep 10
    echo "[OK] CT creado"
}