import asyncio
import json
import requests
import urllib3
import os
from datetime import datetime
from tplink_omada_client import OmadaClient

# Deshabilitar advertencias de seguridad
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CREDENCIALES ---
OMADA_IP, OMADA_USER, OMADA_PASS = '10.175.7.3', 'Sectorial', 'Nokia.3189'
SITE_NAME = 'SamcoEsperanza'

OPN_IP = "10.175.6.203"
OPN_KEY = "v4f9BWOZmEIOHFskhnAfXES6tBASBnloD6htMa98cWNADvyvbiuxAe3CREVvpO7FU1oheTAuSsGPKBX4"
OPN_SEC = "z8kfgfRhtCJYU4FXn993+ruklqnVpkehYYNa4g5EnWqM1+oiG3naafDHHDA8KnDqt+luwj23PdFz1m+W"

ZABBIX_URL = "http://10.175.6.12/zabbix/api_jsonrpc.php" 
ZAB_USER = "APIGrafana"
ZAB_PASS = "gestion1234"

NAS_BASE = r"\\10.175.6.10"

# --- CONFIGURACIÓN DE NOMBRES DE GRUPOS (DINÁMICO) ---
# Usamos nombres exactos de Zabbix para evitar errores de IDs movidos
NOMBRES_GRUPOS = {
    "CAMARAS": "Cámaras",
    "ROUTERS_WIFI": "Routers WiFi",
    "HUAWEI_CAPS": "Huawei CAPS",
    "RELOJES": "Relojes"
}

# Mapeo necesario solo para saber en qué carpeta del NAS buscar cada cámara
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

# --- FUNCIONES DE APOYO ZABBIX ---
def get_zabbix_token():
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {"username": ZAB_USER, "password": ZAB_PASS},
        "id": 1
    }
    try:
        return requests.post(ZABBIX_URL, json=payload).json().get("result")
    except:
        return None

def get_group_id_by_name(token, name):
    payload = {
        "jsonrpc": "2.0",
        "method": "hostgroup.get",
        "params": {
            "filter": {"name": [name]}
        },
        "auth": token,
        "id": 1
    }
    result = requests.post(ZABBIX_URL, json=payload).json().get("result", [])
    return result[0]['groupid'] if result else None

def get_zabbix_hosts_by_group_id(token, group_id):
    if not group_id: return []
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "groupids": group_id,
            "selectInterfaces": ["ip"],
            "output": ["name", "status"]
        },
        "auth": token,
        "id": 1
    }
    return requests.post(ZABBIX_URL, json=payload).json().get("result", [])

# --- LOGICA DE ESCANEO PROFUNDO (NAS) ---
def get_last_mod_time(folder_name):
    root_path = os.path.join(NAS_BASE, folder_name)
    latest_time = 0
    try:
        if not os.path.exists(root_path): return 0
        for root, dirs, files in os.walk(root_path):
            if "datadir" in root.lower():
                for f in files:
                    if f.endswith(('.mp4', '.dav')):
                        file_path = os.path.join(root, f)
                        mtime = os.path.getmtime(file_path)
                        if mtime > latest_time:
                            latest_time = mtime
    except: pass
    return latest_time

# --- AUDITORIA RED (OMADA) ---
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
                "mac": d.raw_data.get('mac'),
                "ip": d.raw_data.get('ip', 'N/A'),
                "clientes": int(d.raw_data.get('clientNum', 0)),
                "cpu": f"{d.raw_data.get('cpuUtil', 0)}%",
                "mem": f"{d.raw_data.get('memUtil', 0)}%",
                "status": "OK" if d.status == 14 else "DOWN"
            } for d in devices]
    except: return []

# --- AUDITORIA PERIMETRO (OPNSENSE) ---
def get_opnsense_audit():
    try:
        url = f"https://{OPN_IP}/api/interfaces/overview/interfacesInfo"
        r = requests.get(url, auth=(OPN_KEY, OPN_SEC), verify=False, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {v.get('description', k): {
                "device": v.get('device'),
                "status": v.get('status'),
                "ipv4": v.get('ipv4', []),
                "mac": v.get('macaddr')
            } for k, v in data.items() if k.lower() in ['wan', 'lan', 'opt2']}
        return {"error": f"HTTP {r.status_code}"}
    except: return {"error": "Timeout/Conexión Rehusada"}

# --- MAIN ---
async def main():
    print(f"[{datetime.now()}] 🚀 Iniciando Auditoría Unificada por Nombres de Grupo...")
    
    token = get_zabbix_token()
    if not token:
        print("❌ Error: No se pudo autenticar en Zabbix.")
        return

    # 1. Resolver IDs de grupo dinámicamente para no "mearse"
    id_cams = get_group_id_by_name(token, NOMBRES_GRUPOS["CAMARAS"])
    id_wifi = get_group_id_by_name(token, NOMBRES_GRUPOS["ROUTERS_WIFI"])
    id_huawei = get_group_id_by_name(token, NOMBRES_GRUPOS["HUAWEI_CAPS"])
    id_relojes = get_group_id_by_name(token, NOMBRES_GRUPOS["RELOJES"])

    # 2. Obtener hosts
    cams_h = get_zabbix_hosts_by_group_id(token, id_cams)
    wifi_h = get_zabbix_hosts_by_group_id(token, id_wifi)
    huawei_h = get_zabbix_hosts_by_group_id(token, id_huawei)
    relojes_h = get_zabbix_hosts_by_group_id(token, id_relojes)

    # 3. Procesar Cámaras
    lista_camaras = []
    for h in cams_h:
        nombre = h['name']
        ip = h['interfaces'][0]['ip'] if h.get('interfaces') else "S/D"
        folder = MAPEO_NAS_CAMARAS.get(nombre, "desconocido")
        mtime = get_last_mod_time(folder)
        grabando = False
        last_mod = "Sin registros"
        if mtime > 0:
            dt = datetime.fromtimestamp(mtime)
            last_mod = dt.strftime("%Y-%m-%d %H:%M:%S")
            if (datetime.now() - dt).total_seconds() < 900: grabando = True
        
        lista_camaras.append({
            "camara": nombre, "ip": ip,
            "estado_grabacion": {"grabando": grabando, "ultima_modificacion": last_mod}
        })

    # 4. Omada y OPNsense
    switches = await get_omada_audit()
    perimetro = get_opnsense_audit()

    # 5. Alertas
    payload_probs = {"jsonrpc": "2.0", "method": "problem.get", "params": {"recent": True, "limit": 15}, "auth": token, "id": 1}
    probs = requests.post(ZABBIX_URL, json=payload_probs).json().get("result", [])

    # 6. Estructura Final
    reporte = {
        "metadatos": {
            "fecha_auditoria": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "responsable": "Soporte Técnico SAMCo"
        },
        "camaras": lista_camaras,
        "infraestructura_switches": switches,
        "configuracion_perimetro": perimetro,
        "dispositivos_wifi": [
            *[{"nombre": h['name'], "ip": h['interfaces'][0]['ip'], "tipo": "Router WiFi", "estado": "Online" if h['status']=="0" else "Offline"} for h in wifi_h],
            *[{"nombre": h['name'], "ip": h['interfaces'][0]['ip'], "tipo": "Huawei CAPS", "estado": "Online" if h['status']=="0" else "Offline"} for h in huawei_h]
        ],
        "relojes_personal": [
            {"nombre": h['name'], "ip": h['interfaces'][0]['ip'] if h.get('interfaces') else "S/D", "estado": "Online" if h['status']=="0" else "Offline"} for h in relojes_h
        ],
        "estado_alertas": {
            "alertas_activas": len(probs),
            "detalle": [{"evento": p['name'], "severidad": p['severity']} for p in probs]
        }
    }

    with open("config_red_total.json", "w") as f:
        json.dump(reporte, f, indent=4)
    
    print(f"[{datetime.now()}] ✅ Auditoría finalizada. Relojes detectados: {len(relojes_h)}")

if __name__ == "__main__":
    asyncio.run(main())