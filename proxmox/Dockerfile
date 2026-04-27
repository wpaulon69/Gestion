# Dockerfile para auditoría SAMCo - Contenedor LXC Proxmox
# Construir: docker build -t samco-auditar .
# Ejecutar: docker run -d -p 8081:8081 --name samco-auditar samco-auditar

FROM python:3.11-slim

LABEL maintainer="informatica@samco.com.ar"
LABEL description="Sistema de auditoría técnica SAMCo Esperanza"

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    cifs-utils smbclient curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no root
RUN useradd -m -u 1000 auditar

WORKDIR /app

# Copiar scripts
COPY auditar.py modulos/ config.json proxmox/*.py ./
COPY dashboard.html ./
COPY proxmox/dashboard_server.py ./

# Copiar mount script
COPY proxmox/mounts.sh /usr/local/bin/mount-nas.sh
RUN chmod +x /usr/local/bin/mount-nas.sh

# Crear directorio de output
RUN mkdir -p output /mnt/nas

# Exponer puerto dashboard
EXPOSE 8080

# Puerto para healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/ || exit 1

# Por defecto corre el servidor
CMD ["python3", "dashboard_server.py"]