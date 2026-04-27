#!/usr/bin/env python3
"""
Adapta config.json para entorno Linux.
Convierte rutas Windows (\\\\10.175.6.10\\recurso) a rutas de mount (/mnt/nas/recurso)
"""
import json
import os
import sys

def get_linux_config(config_path="config.json", mount_base="/mnt/nas"):
    """
    Carga config.json y adapta las rutas NAS para Linux.
    """
    with open(config_path, "r", encoding='utf-8') as f:
        config = json.load(f)
    
    # Adaptar ruta NAS: \\10.175.6.10\recurso -> /mnt/nas/recurso
    original_path = config["nas"]["base_path"]
    
    # Extraer nombre del recurso de la ruta Windows
    # \\10.175.6.10\recurso -> recurso
    windows_prefix = original_path.replace("/", "\\").split("\\")[-1]
    linux_path = f"{mount_base}"
    
    config["nas"]["base_path"] = linux_path
    config["nas"]["_original_windows"] = original_path
    
    return config

def get_linux_config_cli():
    """CLI para obtener config adaptada."""
    import argparse
    parser = argparse.ArgumentParser(description="Adapta config para Linux")
    parser.add_argument("--json", action="store_true", help="Output como JSON")
    args = parser.parse_args()
    
    config = get_linux_config()
    
    if args.json:
        print(json.dumps(config, indent=2))
    else:
        print(f"NAS base path (Linux): {config['nas']['base_path']}")
        print(f"NAS base path (Windows): {config['nas']['_original_windows']}")

if __name__ == "__main__":
    get_linux_config_cli()