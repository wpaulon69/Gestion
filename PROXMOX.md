# Despliegue en Proxmox (LXC)

## Opción 1: Contenedor LXC (Recomendado)

### Requisitos
- CT Debian 12 (1 vCPU, 1GB RAM, 4GB storage)
- Red: 10.175.6.x/24

### Preparación del contenedor

```bash
# Instalar dependencias
apt-get update && apt-get install -y python3 python3-venv cifs-utils git

# Clonar repo
cd /opt
git clone https://github.com/.../gestion.git
cd gestion

# Crear venv
python3 -m venv gestion_env
source gestion_env/bin/activate
pip install -r requirements.txt
```

### Montar CIFS del NAS

```bash
# Crear credenciales
echo "username=admin" > /etc/samba/creds.nas
echo "password=XXXX" >> /etc/samba/creds.nas
chmod 600 /etc/samba/creds.nas

# Montar grabaciones
./proxmox/mounts.sh

# Verificar
ls /mnt/nas/
```

### Ejecutar auditoría

```bash
source gestion_env/bin/activate
python3 auditar.py
# Output: output/reporte_completo.json
```

### Servir dashboard

```bash
# Ejecutar servidor
python3 proxmox/dashboard_server.py
# Acceder: http://10.175.6.x:8080
```

## Opción 2: Docker (Alternativo)

```bash
# Construir imagen
docker build -t samco-auditar -f proxmox/Dockerfile .

# Ejecutar con mount CIFS
docker run -d -p 8080:8080 \
  -v /mnt/nas:/mnt/nas \
  --name samco-auditar samco-auditar
```

## Montaje automático al iniciar

```ini
# /etc/fstab
//10.175.6.10/camHallCentral /mnt/nas/camHallCentral cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
//10.175.6.10/camEstacionamiento /mnt/nas/camEstacionamiento cifs credentials=/etc/samba/creds.nas,uid=1000,gid=1000 0 0
# ... (repetir para cada cámara)
```

## Troubleshooting

| Error | Solución |
|-------|---------|
| `Mount denied` | Verificar credenciales en `/etc/samba/creds.nas` |
| `No module named 'tplink_omada_client'` | `pip install tplink-omada-client` |
| `Connection refused` | Verificar que servicios Zielen en puerto correcto |