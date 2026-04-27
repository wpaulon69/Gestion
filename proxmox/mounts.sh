#!/bin/bash
# Monta los recursos CIFS del NAS para auditoría
# Ejecutar como root o con sudo

NAS_IP="10.175.6.10"
MOUNT_BASE="/mnt/nas"
CREDENTIALS="/etc/samba/creds.nas"

# Crear directorio base
mkdir -p "$MOUNT_BASE"

# Montar grabaciones de cámaras
for cam in camHallCentral camEstacionamiento camPortonPral camConsultorioExt camOdontoRX camSUM camTaller camLaboratorio; do
    mkdir -p "$MOUNT_BASE/$cam"
    mount -t cifs //${NAS_IP}/${cam} "$MOUNT_BASE/$cam" -o credentials=$CREDENTIALS,uid=100000,gid=100000,file_mode=0660,dir_mode=0770 2>/dev/null || echo "[WARN] $cam no disponible"
done

echo "[OK] Montajes CIFS completados"