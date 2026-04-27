# Contexto - SAMCo Auditoría Proxmox

## Estado Actual
- Contenedor LXC en 10.175.6.19 (Debian 12)
- Dashboard funcionando en puerto 80
- Servicio systemd configurado (auditar.service)

## Pendiente
- Botón Sincronizar no actualiza datos (possible problema de fecha/hora del JSON vs sistema)

## Última acción realizada
- Se cambió puerto de 8080 a 80 en dashboard_server.py y dashboard.html
- Se verificó que el puerto quedó correcto (localhost:80 en 3 lugares)
- Sincronizar responde "Completado" pero no actualiza datos visuales
- Posible causa: timestamp del JSON vs fecha del sistema

## Para continuar mañana
1. Verificar hora del sistema:
   ```
   date
   cat output/reporte_completo.json | grep fecha
   ```
2. Forzar refresh borrando JSON:
   ```
   rm output/reporte_completo.json
   curl -X POST http://localhost:80/api/run-audit
   ```
3. O cargar JSON manualmente desde el navegador

## Archivos en /opt/auditar/
- auditar.py, config.json, dashboard.html (modificado puerto a 80)
- modulos/*.py
- proxmox/dashboard_server.py, config_linux.py
- gestion_env/ (venv)

## Logs
```
journalctl -u auditar.service -n 20 --no-pager
```