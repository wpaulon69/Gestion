#!/usr/bin/env python3
"""
Sync dashboard.html y reporte_completo.json a GitHub repo wpaulon69/gestion
"""
import json
import subprocess
import sys
from pathlib import Path

# Cargar config
with open('config.json') as f:
    config = json.load(f)

gh_user = config['github']['user']
gh_token = config['github']['token']
repo = 'gestion'
repo_url = f"https://{gh_token}@github.com/{gh_user}/{repo}.git"

files_to_sync = [
    'dashboard.html',
    'output/reporte_completo.json'
]

def run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"ERROR: {cmd}")
        print(result.stderr)
    return result

def main():
    # Verificar archivos
    for f in files_to_sync:
        if not Path(f).exists():
            print(f"Falta archivo: {f}")
            return 1

    # Clone o pull
    if not Path('.git').exists():
        print(f"Clonando repo...")
        r = run(f"git clone {repo_url} .")
        if r.returncode != 0:
            return 1
    else:
        print("Actualizando repo...")
        r = run("git pull origin clean_start")
        if r.returncode != 0:
            return 1

    # Configurar git
    run('git config user.name "hermes-bot"')
    run('git config user.email "hermes@samco.local"')

    # 1. Agregar archivos (dashboard + assets estáticos)
    run("git add dashboard.html static/")
    if r.returncode != 0:
        return 1

    # Commit y push
    r = run('git commit -m "Update dashboard y reporte desde SAMCo"')
    if r.returncode != 0:
        # Puede que no haya cambios
        if "nothing to commit" in r.stdout:
            print("Sin cambios para commitear")
            return 0
        return 1

    r = run('git push origin clean_start')
    if r.returncode != 0:
        return 1

    print("✅ Sync a GitHub completado")
    return 0

if __name__ == '__main__':
    sys.exit(main())