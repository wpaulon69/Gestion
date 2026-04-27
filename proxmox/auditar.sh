#!/bin/bash
# Ejecuta la auditoría - wrapper para contenedor Proxmox
# Uso: ./auditar.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/../gestion_env"

# Activar venv si existe
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

# Ejecutar auditoría
python3 "$SCRIPT_DIR/../auditar.py"

# Código de salida
exit $?