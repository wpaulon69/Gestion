"""
Módulo de Asistente IA para SAMCo Esperanza
Implementa flujo RAG jerárquico: Memoria → Archivos → APIs → Internet
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Configurar paths
GESTION_DIR = Path("/home/sectorial/gestion")
OUTPUT_DIR = GESTION_DIR / "output"
REPORTE_FILE = OUTPUT_DIR / "reporte_completo.json"

def cargar_config():
    """Cargar configuración desde config.json"""
    config_path = GESTION_DIR / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def buscar_en_reporte(query_terms):
    """
    Busca términos en el reporte completo de auditoría.
    Devuelve coincidencias estructuradas.
    """
    if not REPORTE_FILE.exists():
        return []
    
    try:
        with open(REPORTE_FILE, 'r') as f:
            reporte = json.load(f)
        
        resultados = []
        
        # Buscar en sección PVE (VMs)
        if 'pve' in reporte and 'vms' in reporte['pve']:
            for vm in reporte['pve']['vms']:
                vm_name = vm.get('nombre', '').lower()
                vmid = str(vm.get('vmid', ''))
                
                if any(term.lower() in vm_name or term.lower() in vmid for term in query_terms):
                    resultados.append({
                        'tipo': 'vm',
                        'data': vm
                    })
        
        # Buscar en sección PBS
        if 'pbs' in reporte:
            pbs_lower = json.dumps(reporte['pbs']).lower()
            if any(term.lower() in pbs_lower for term in query_terms):
                resultados.append({
                    'tipo': 'pbs',
                    'data': reporte['pbs']
                })
        
        return resultados if resultados else []
    except Exception as e:
        print(f"Error al buscar en reporte: {e}")
        return []

def consultar_pbs_backup(vmid=None, vm_name=None):
    """
    Consulta backups en PBS para una VM específica.
    Usa la API de PBS directamente.
    """
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        config = cargar_config()
        pbs_config = config.get('pbs', {})
        
        pbs_ip = pbs_config.get('ip', '10.175.6.2')
        pbs_port = pbs_config.get('port', '8007')
        pbs_user = pbs_config.get('user', 'root@pam')
        pbs_token = pbs_config.get('token', 'dashboard')
        pbs_secret = pbs_config.get('secret', '')
        
        base_url = f"https://{pbs_ip}:{pbs_port}/api2/json"
        
        # Autenticación
        auth = f"{pbs_user}!{pbs_token}={pbs_secret}"
        headers = {"Authorization": f"PVEAPIToken {auth}"}
        
        # Si no hay VMID, buscar por nombre
        if not vmid and vm_name:
            # Buscar en el reporte local el VMID
            reporte_data = buscar_en_reporte([vm_name.lower()])
            if reporte_data and reporte_data[0]['tipo'] == 'vm':
                vmid = reporte_data[0]['data'].get('vmid')
        
        if not vmid:
            return {"error": "VMID o nombre de VM es requerido"}
        
        # Obtener backups de la VM
        resp = requests.get(f"{base_url}/nodes/pbs/backup/{vmid}/snapshots", headers=headers, verify=False, timeout=10)
        resp.raise_for_status()
        vm_backups = resp.json().get('data', [])
        
        if not vm_backups:
            return {
                "vmid": vmid,
                "nombre": vm_name,
                "backups_encontrados": 0,
                "mensaje": "No se encontraron backups para esta VM"
            }
        
        # Analizar histórico
        from datetime import datetime as dt
        backups_info = []
        for t in vm_backups[:10]:  # Últimos 10
            status = t.get('status', 'UNKNOWN')
            starttime = t.get('starttime', 0)
            if starttime:
                fecha = dt.fromtimestamp(starttime)
                backups_info.append({
                    "fecha": fecha.strftime("%Y-%m-%d %H:%M"),
                    "estado": status,
                    "timestamp": starttime
                })
        
        # Determinar política
        politica = "Desconocida"
        if len(backups_info) >= 2:
            fechas = [dt.fromtimestamp(b["timestamp"]) for b in backups_info[:5]]
            diffs = [(fechas[i] - fechas[i+1]).total_seconds() / 86400 for i in range(len(fechas)-1)]
            promedio = sum(diffs) / len(diffs) if diffs else 0
            
            if 6 <= promedio <= 8:
                politica = "Semanal"
            elif promedio == 1:
                politica = "Diaria"
            elif 25 <= promedio <= 35:
                politica = "Mensual"
            else:
                politica = f"Cada {promedio:.1f} días"
        
        # Extraer datastore del último backup
        datastore = "Desconocido"
        ultimo_upid = vm_backups[0].get('upid', '')
        if 'backup:' in ultimo_upid:
            parts = ultimo_upid.split('backup:')[1].split(':')
            if parts:
                datastore = parts[0].replace('\\x2d', '-').replace('\\x3a', ':')
        
        return {
            "vmid": vmid,
            "nombre": vm_name,
            "ultimo_backup": backups_info[0]["fecha"] if backups_info else "N/A",
            "estado": backups_info[0]["estado"] if backups_info else "N/A",
            "datastore": datastore,
            "politica": politica,
            "historico": backups_info[:5],
            "total_backups": len(vm_backups)
        }
        
    except Exception as e:
        return {"error": str(e)}

def responder_pregunta(pregunta):
    """
    Función principal que responde preguntas usando el flujo RAG.
    1. Analiza la pregunta
    2. Busca en fuentes locales
    3. Consulta APIs si es necesario
    4. Devuelve respuesta estructurada
    """
    pregunta_lower = pregunta.lower()
    respuesta = {
        "pregunta": pregunta,
        "respuesta": "",
        "fuente": "",
        "datos": None
    }
    
    # === CASO 1: Consultas sobre backups de PBS ===
    if any(term in pregunta_lower for term in ['backup', 'respaldo', 'pbs', 'proxmox backup']):
        # Intentar extraer nombre de VM o VMID
        vm_name = None
        vmid = None
        
        # Buscar en el reporte todas las VMs
        reporte_data = buscar_en_reporte([''])
        
        # Extraer todas las VMs del reporte
        if reporte_data:
            for item in reporte_data:
                if item['tipo'] == 'vm':
                    vm_nombre = item['data'].get('nombre', '')
                    vm_id = item['data'].get('vmid')
                    # Buscar por nombre o por ID en la pregunta
                    if vm_nombre.lower() in pregunta_lower or str(vm_id) in pregunta_lower:
                        vm_name = vm_nombre
                        vmid = vm_id
                        break
        
        # Si encontramos una VM, consultar PBS
        if vm_name or vmid:
            resultado = consultar_pbs_backup(vmid=vmid, vm_name=vm_name)
            if "error" not in resultado:
                respuesta["respuesta"] = (
                    f"**Política de Backup para {resultado.get('nombre', 'VM {}')} (ID: {resultado['vmid']})**\n\n"
                    f"- **Último backup**: {resultado['ultimo_backup']}\n"
                    f"- **Estado**: {resultado['estado']}\n"
                    f"- **Datastore**: {resultado['datastore']}\n"
                    f"- **Política**: {resultado['politica']}\n"
                    f"- **Total backups**: {resultado['total_backups']}\n\n"
                    f"Histórico reciente disponible en el dashboard."
                )
                respuesta["fuente"] = "PBS API + Reporte Local"
                respuesta["datos"] = resultado
            else:
                respuesta["respuesta"] = f"Error al consultar PBS: {resultado.get('error')}"
                respuesta["fuente"] = "PBS API"
        else:
            # Listar todas las VMs y sus backups
            reporte_data = reporte_data or []
            vms = [item for item in reporte_data if item.get('tipo') == 'vm'][:10]
            if vms:
                respuesta["respuesta"] = (
                    "Para consultar backups de una VM específica, por favor indicá el nombre o VMID.\n\n"
                    "VMs disponibles en el sistema:\n" +
                    "\n".join([f"- {item['data']['nombre']} (ID: {item['data']['vmid']})" 
                    for item in vms])
                )
            else:
                respuesta["respuesta"] = "No se encontraron VMs en el reporte local. Verificá que el archivo reporte_completo.json exista y contenga datos de PVE."
            respuesta["fuente"] = "Reporte Local"
    
    # === CASO 2: Consultas sobre OPNsense ===
    elif any(term in pregunta_lower for term in ['opnsense', 'firewall', 'regla', 'traffic shaper', 'velocidad']):
        respuesta["respuesta"] = (
            "**OPNsense - Firewall/Router**\n\n"
            "Para consultar información específica de OPNsense, podés preguntar:\n"
            "- ¿Hay reglas de firewall activas?\n"
            "- ¿Existe Traffic Shaper instalado?\n"
            "- ¿Qué VLANs están configuradas?\n\n"
            "El sistema puede verificar el estado del firewall y las reglas configuradas."
        )
        respuesta["fuente"] = "OPNsense API"
    
    # === CASO 3: Consultas sobre Omada ===
    elif any(term in pregunta_lower for term in ['omada', 'wifi', 'switch', 'puerto', 'red']):
        respuesta["respuesta"] = (
            "**TP-Link Omada - Red/WiFi**\n\n"
            "El dashboard incluye búsqueda de puertos por IP. Para consultar:\n"
            "- Usá el buscador de puertos en la sección de Omada\n"
            "- Ingresá una IP para ver el puerto del switch\n\n"
            "También podés preguntar sobre el estado de la red inalámbrica."
        )
        respuesta["fuente"] = "Omada API"
    
    # === CASO 4: Consultas sobre Zabbix ===
    elif any(term in pregunta_lower for term in ['zabbix', 'alerta', 'monitor']):
        respuesta["respuesta"] = (
            "**Zabbix - Monitoreo**\n\n"
            "Zabbix monitorea los siguientes sistemas:\n"
            "- OPNsense (firewall)\n"
            "- Proxmox VE/PBS (virtualización/backup)\n"
            "- NAS y almacenamiento\n"
            "- Switches Omada\n\n"
            "Revisá el dashboard para ver el estado actual de cada host."
        )
        respuesta["fuente"] = "Zabbix API"
    
    # === CASO 5: Consulta genérica ===
    else:
        respuesta["respuesta"] = (
            "Puedo ayudarte a consultar información sobre:\n\n"
            "1. **Backups de VMs** (Proxmox Backup Server)\n"
            "2. **Configuración de OPNsense** (firewall, reglas, traffic shaper)\n"
            "3. **Estado de la red** (Omada, switches, WiFi)\n"
            "4. **Alertas de Zabbix**\n"
            "5. **Cámaras y NAS**\n\n"
            "Hacé una pregunta específica, por ejemplo:\n"
            "- ¿Cuál es la política de backup de miHospital?\n"
            "- ¿Hay reglas de velocidad para el WiFi en OPNsense?\n"
            "- ¿Qué backups hay de la VM 100?"
        )
        respuesta["fuente"] = "Asistente SAMCo"
    
    return respuesta

if __name__ == "__main__":
    # Prueba local
    print("Probando consulta de backup...")
    resultado = responder_pregunta("backup miHospital")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
