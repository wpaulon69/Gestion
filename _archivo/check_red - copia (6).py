import asyncio
import json
import requests
import urllib3
import os
from datetime import datetime
from tplink_omada_client import OmadaClient

# Deshabilitar advertencias de seguridad para entornos locales
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN DE ACCESO ---
OMADA_IP, OMADA_USER, OMADA_PASS = '10.175.7.3', 'Sectorial', 'Nokia.3189'
SITE_NAME = 'SamcoEsperanza'

ZABBIX_URL = "http://10.175.6.12/zabbix/api_jsonrpc.php" 
ZAB_USER = "APIGrafana"
ZAB_PASS = "gestion1234"

NAS_BASE = r"\\10.175.6.10"

# Mapeo de carpetas en el NAS para las cámaras (Lógica verificada)
MAPEO_NAS_CAMARAS = {
    "Camara Hall Central": "camHallCentral",
    "Camara Estacionamiento Norte": "camEstacionamiento",
    "Camara Porton Entrada": "camPortonPral",
    "Camara Consultorios Externos": "camConsultorioExt",
    "Camara Odonto Rx": "camOdontoRX",
    "Camara SUM": "camSUM",
    "Camara Taller": "camTaller",
    "Camara Laboratorio": "camLaboratorio"
}

# --- FUNCIONES DE COMUNICACIÓN CON ZABBIX ---
def get_zabbix_token():
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {"username": ZAB_USER, "password": ZAB_PASS},
        "id": 1
    }
    try:
        response = requests.post(ZABBIX_URL, json=payload, timeout=5).json()
        return response.get("result")
    except Exception:
        return None

def get_hosts_by_group_name(token, group_name):
    """Obtiene hosts filtrando por el nombre del grupo directamente."""
    # 1. Obtener el ID del grupo (Se busca por nombre exacto)
    payload_group = {
        "jsonrpc": "2.0",
        "method": "hostgroup.get",
        "params": {"filter": {"name": [group_name]}},
        "auth": token,
        "id": 1
    }
    try:
        group_res = requests.post(ZABBIX_URL, json=payload_group).json().get("result", [])
        if not group_res: 
            print(f"⚠️ Advertencia: Grupo '{group_name}' no encontrado en Zabbix.")
            return []
        
        group_id = group_res[0]['groupid']

        # 2. Obtener los hosts de ese grupo
        payload_hosts = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "groupids": group_id,
                "selectInterfaces": ["ip"],
                "output": ["name", "status"]
            },
            "auth": token,
            "id": 2
        }
        return requests.post(ZABBIX_URL, json=payload_hosts).json().get("result", [])
    except Exception as e:
        print(f"❌ Error al obtener hosts de {group_name}: {e}")
        return []

# --- ESCANEO DE GRABACIÓN (Lógica optimizada para NAS) ---
def check_nas_recording(folder_name):
    """Verifica si hay archivos recientes en la carpeta datadir del NAS."""
    root_path = os.path.join(NAS_BASE, folder_name)
    latest_time = 0
    exists = False
    try:
        if os.path.exists(root_path):
            exists = True
            # Caminata por el árbol de directorios buscando 'datadir'
            for root, dirs, files in os.walk(root_path):
                if "datadir" in root.lower():
                    for f in files:
                        # Extensiones comunes de video de cámaras
                        if f.lower().endswith(('.mp4', '.dav', '.mov', '.mp2')):
                            mtime = os.path.getmtime(os.path.join(root, f))
                            if mtime > latest_time:
                                latest_time = mtime
    except Exception:
        pass
    
    grabbing = False
    if latest_time > 0:
        # Se considera grabando si hubo cambios en los últimos 20 minutos
        if (datetime.now().timestamp() - latest_time) < 1200:
            grabbing = True
            
    return {
        "grabando": grabbing,
        "ultima_modificacion": datetime.fromtimestamp(latest_time).strftime("%Y-%m-%d %H:%M:%S") if latest_time > 0 else "N/A",
        "existe_carpeta": exists,
        "carpeta_en_nas": folder_name
    }

# --- AUDITORÍA DE INFRAESTRUCTURA (OMADA) ---
async def get_omada_audit():
    try:
        url = f"https://{OMADA_IP}:8043"
        async with OmadaClient(url, OMADA_USER, OMADA_PASS, verify_ssl=False) as client:
            await client.login()
            sites = await client.get_sites()
            target_site = next((s for s in sites if s.name == SITE_NAME), None)
            if not target_site: return []
            site_client = await client.get_site_client(target_site)
            devices = await site_client.get_devices()
            return [{
                "nombre": d.raw_data.get('name', 'S/N'),
                "modelo": d.raw_data.get('model'),
                "ip": d.raw_data.get('ip', 'N/A'),
                "clientes": int(d.raw_data.get('clientNum', 0)),
                "cpu": f"{d.raw_data.get('cpuUtil', 0)}%",
                "status": "OK" if d.status == 14 else "DOWN"
            } for d in devices]
    except Exception:
        return []

# --- PROCESO PRINCIPAL ---
async def main():
    print(f"[{datetime.now()}] 🚀 Iniciando Auditoría Técnica Unificada...")
    
    token = get_zabbix_token()
    if not token:
        print("❌ Error: Autenticación en Zabbix fallida.")
        return

    # 1. Obtención de Dispositivos desde Zabbix
    # Asegúrate de que estos nombres coincidan EXACTAMENTE con los grupos en Zabbix
    cams_h = get_hosts_by_group_name(token, "Camaras")
    wifi_h = get_hosts_by_group_name(token, "Router Wifi")
    huawei_h = get_hosts_by_group_name(token, "Huawei CAPS")
    relojes_h = get_hosts_by_group_name(token, "Relojes")

    # 2. Procesamiento de Cámaras y Grabación en NAS
    lista_camaras = []
    print(f"🔍 Procesando {len(cams_h)} cámaras encontradas...")
    
    for h in cams_h:
        # Buscamos la carpeta correspondiente en el mapeo
        folder = MAPEO_NAS_CAMARAS.get(h['name'], None)
        
        if folder:
            estado_nas = check_nas_recording(folder)
        else:
            # Si no hay mapeo, intentamos con el nombre del host simplificado o marcamos desconocido
            estado_nas = {
                "grabando": False,
                "ultima_modificacion": "N/A",
                "existe_carpeta": False,
                "carpeta_en_nas": "No mapeada"
            }
        
        lista_camaras.append({
            "camara": h['name'],
            "ip": h['interfaces'][0]['ip'] if h.get('interfaces') else "0.0.0.0",
            "estado_grabacion": estado_nas
        })

    # 3. Auditoría de Red (Switches y Alertas)
    switches = await get_omada_audit()
    
    # Obtener Alertas de Zabbix
    payload_probs = {
        "jsonrpc": "2.0", 
        "method": "problem.get", 
        "params": {"recent": True, "limit": 15}, 
        "auth": token, 
        "id": 1
    }
    probs_res = requests.post(ZABBIX_URL, json=payload_probs).json().get("result", [])
    alertas = {
        "alertas_activas": len(probs_res),
        "detalle": [{"evento": p['name'], "severidad": p['severity']} for p in probs_res]
    }

    # 4. Consolidación Final para el Dashboard
    reporte = {
        "metadatos": {
            "fecha_auditoria": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "responsable": "Departamento de Informática SAMCo"
        },
        "camaras": lista_camaras,
        "estado_alertas": alertas,
        "infraestructura_switches": switches,
        "dispositivos_wifi": [
            *[{"nombre": h['name'], "ip": h['interfaces'][0]['ip'], "tipo": "Router WiFi", "estado": "Online" if h['status']=="0" else "Offline"} for h in wifi_h],
            *[{"nombre": h['name'], "ip": h['interfaces'][0]['ip'], "tipo": "Huawei CAPS", "estado": "Online" if h['status']=="0" else "Offline"} for h in huawei_h]
        ],
        "relojes_personal": [
            {"nombre": h['name'], "ip": h['interfaces'][0]['ip'] if h.get('interfaces') else "S/D", "estado": "Online" if h['status']=="0" else "Offline"} for h in relojes_h
        ]
    }

    # Guardado del archivo config_red_total.json
    with open("config_red_total.json", "w") as f:
        json.dump(reporte, f, indent=4)
    
    print(f"[{datetime.now()}] ✅ Auditoría finalizada exitosamente.")
    print(f"   -> Cámaras: {len(lista_camaras)}")
    print(f"   -> Switches: {len(switches)}")
    print(f"   -> Alertas Zabbix: {alertas['alertas_activas']}")

if __name__ == "__main__":
    asyncio.run(main())