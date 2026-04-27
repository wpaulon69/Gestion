import asyncio
import json
import requests
import urllib3
import os
from datetime import datetime, timedelta
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
UMBRAL_GRABACION_MINS = 10 # Tiempo incrementado para evaluar la grabación

# Mapeo de carpetas en el NAS para las cámaras
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

def get_zabbix_token():
    """Autenticación simple en Zabbix"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {"user": ZAB_USER, "password": ZAB_PASS},
            "id": 1
        }
        resp = requests.post(ZABBIX_URL, json=payload, timeout=5).json()
        return resp.get("result")
    except:
        return None

def verificar_grabacion_nas(nombre_carpeta):
    """Verifica recursivamente si hay archivos recientes en la estructura de Hikvision"""
    ruta_camara = os.path.join(NAS_BASE, nombre_carpeta)
    latest_time = 0
    existe_carpeta = os.path.exists(ruta_camara)
    
    if existe_carpeta:
        try:
            for root, dirs, files in os.walk(ruta_camara):
                for file in files:
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    if mtime > latest_time:
                        latest_time = mtime
        except:
            pass

    grabando = False
    ultima_mod = "Nunca"
    if latest_time > 0:
        dt_mtime = datetime.fromtimestamp(latest_time)
        ultima_mod = dt_mtime.strftime("%Y-%m-%d %H:%M:%S")
        if (datetime.now() - dt_mtime) < timedelta(minutes=UMBRAL_GRABACION_MINS):
            grabando = True

    return {
        "grabando": grabando,
        "ultima_modificacion": ultima_mod,
        "existe_carpeta": existe_carpeta,
        "carpeta_en_nas": nombre_carpeta
    }

async def get_omada_data():
    """Obtiene datos de Switches desde Omada"""
    switches_data = []
    try:
        async with OmadaClient(OMADA_IP, OMADA_USER, OMADA_PASS, verify=False) as client:
            await client.login()
            site_id = None
            async for site in client.get_sites():
                if site.name == SITE_NAME:
                    site_id = site.id
                    break
            
            if site_id:
                devices = await client.get_devices(site_id)
                for dev in devices:
                    if dev.type == "Switch":
                        switches_data.append({
                            "nombre": dev.name,
                            "modelo": dev.model,
                            "ip": dev.ip,
                            "clientes": dev.client_num,
                            "cpu": f"{dev.cpu_util}%",
                            "status": "OK" if dev.status == 1 else "DOWN"
                        })
    except:
        pass
    return switches_data

async def main():
    print(f"[{datetime.now()}] 🚀 Iniciando Auditoría Consolidada...")
    
    token = get_zabbix_token()
    if not token:
        print("❌ Error crítico: No se pudo conectar a Zabbix")
        return

    # 1. Obtener Hosts por Grupos desde Zabbix
    def get_hosts_by_group_name(group_name):
        try:
            # Obtener ID del grupo
            p_group = {"jsonrpc":"2.0","method":"hostgroup.get","params":{"filter":{"name":[group_name]}},"auth":token,"id":2}
            groups = requests.post(ZABBIX_URL, json=p_group).json().get("result", [])
            if not groups: return []
            
            gid = groups[0]["groupid"]
            # Obtener hosts
            p_hosts = {
                "jsonrpc":"2.0","method":"host.get",
                "params":{"groupids":gid, "selectInterfaces":["ip"], "output":["name","status"]},
                "auth":token,"id":3
            }
            return requests.post(ZABBIX_URL, json=p_hosts).json().get("result", [])
        except:
            return []

    # Consultas a Zabbix
    cams_h = get_hosts_by_group_name("Camaras") # Grupo sin acento como pediste
    wifi_h = get_hosts_by_group_name("Routers WIFI")
    huawei_h = get_hosts_by_group_name("Huawei CAPS")
    relojes_h = get_hosts_by_group_name("Relojes")

    # 2. Procesar Cámaras (Zabbix + NAS)
    lista_camaras = []
    for h in cams_h:
        nombre = h['name']
        carpeta = MAPEO_NAS_CAMARAS.get(nombre, nombre)
        info_nas = verificar_grabacion_nas(carpeta)
        
        lista_camaras.append({
            "camara": nombre,
            "ip": h['interfaces'][0]['ip'] if h.get('interfaces') else "S/D",
            "estado_conexion": "Online" if h['status'] == "0" else "Offline",
            "estado_grabacion": info_nas
        })

    # 3. Obtener Switches (Omada)
    switches = await get_omada_data()

    # 4. Alertas de Zabbix
    p_probs = {"jsonrpc":"2.0","method":"problem.get","params":{"recent":True,"limit":15},"auth":token,"id":4}
    probs_res = requests.post(ZABBIX_URL, json=p_probs).json().get("result", [])
    alertas = {
        "alertas_activas": len(probs_res),
        "detalle": [{"evento": p['name'], "severidad": p['severity']} for p in probs_res]
    }

    # 5. Consolidación Final
    reporte = {
        "metadatos": {
            "fecha_auditoria": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
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

    with open("config_red_total.json", "w", encoding='utf-8') as f:
        json.dump(reporte, f, indent=4, ensure_ascii=False)
    
    print(f"[{datetime.now()}] ✅ Auditoría finalizada. config_red_total.json generado.")

if __name__ == "__main__":
    asyncio.run(main())