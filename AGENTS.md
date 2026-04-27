# AGENTS.md - SAMCo Gestion

## Project Overview
Python sistema de auditoría técnica unificada para SAMCo Esperanza (hospital). Recopila datos de Zabbix, Omada, OPNsense, Proxmox VE/PBS, y NAS.

## Quick Start
```powershell
# Via batch (produces reporte + sync a Google Drive)
.\ejecutar.bat

# Directo
python auditar.py
```

## Environment
- Windows + Python virtual env: `gestion_env\Scripts\python.exe`
- Entry point: `auditar.py`
- Config: `config.json` (credenciales sensibles - no commitear)

## Commands
| Command | Purpose |
|--------|---------|
| `python auditar.py` | Ejecutar auditoría completa |
| `.\ejecutar.bat` | Auditoría + sync a GDrive via rclone |

## Architecture
```
auditar.py       # Main async entry - orquesta todo
├── modulos/zabbix.py      # Monitoreo (cámaras, WiFi, alertas)
├── modulos/omada.py        # Red WiFi (EAPs)
├── modulos/opnsense.py    # Firewall
├── modulos/pve.py        # Proxmox VE
├── modulos/pbs.py         # Proxmox Backup Server
└── modulos/nas_camaras.py # Grabaciones NAS
```

## Output
- Reporte: `output/reporte_completo.json`
- Dashboard: `dashboard.html`

## Module Patterns
- `modulos/*.py`: Cada uno экспорта funciones según su sistema
- `config.json`: Centraliza IPs, credenciales, grupos Zabbix
- Async en `auditar.py`: `await` para Omada (REST), `asyncio.gather` para paralelismo

## Important Constraints
- No lint/typecheck configurado
- Dependiente de conectividad a sistemas internos (IPs en config.json)
- Credenciales en config.json son reales - no commitear
- Requiere Python 3.11+