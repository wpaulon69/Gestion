import requests
import os
import json
from datetime import datetime

# --- CONFIGURACIÓN DE ACCESO ---
ZABBIX_URL = "http://10.175.6.12/zabbix/api_jsonrpc.php"
ZAB_USER = "APIGrafana"
ZAB_PASS = "gestion1234"

# Nueva ruta raíz basada en el comando ls
NAS_PATH = r"\\10.175.6.10\export" 

# --- DOCUMENTACIÓN Y MAPEO DE CÁMARAS ---
# Clave: Nombre exacto en Zabbix | Valor: Nombre de la carpeta en /export/
MAPEO_CARPETAS = {
    "Camara Estacionamiento": "camEstacionamiento",
    "Camara Odontologia RX": "camOdontoRX",
    "Camara Taller": "camTaller",
    "Camara Hall Central": "camHallCentral",
    "Camara Porton Principal": "camPortonPral",
    "Camara Consultorios Externos": "camConsultorioExt",
    "Camara Laboratorio": "camLaboratorio",
    "Camara SUM": "camSUM"
}

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
    except:
        return None

def get_cameras_from_zabbix(token):
    """Obtiene los hosts del grupo 'Camaras' en Zabbix."""
    group_payload = {
        "jsonrpc": "2.0",
        "method": "hostgroup.get",
        "params": {"output": ["groupid"], "filter": {"name": ["Camaras"]}},
        "auth": token, "id": 2
    }
    
    group_res = requests.post(ZABBIX_URL, json=group_payload).json()
    group_ids = [g['groupid'] for g in group_res.get("result", [])]

    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid", "name"],
            "selectInterfaces": ["ip"],
            "groupids": group_ids if group_ids else None
        },
        "auth": token, "id": 3
    }
    
    response = requests.post(ZABBIX_URL, json=payload).json()
    return response.get("result", [])

def check_recording_status(cam_name):
    """Verifica el estado de escritura en la carpeta del NAS."""
    # Buscamos en el mapeo, si no está, probamos con el nombre de Zabbix
    nombre_carpeta = MAPEO_CARPETAS.get(cam_name, cam_name)
    cam_folder = os.path.join(NAS_PATH, nombre_carpeta)
    
    status = {
        "carpeta_en_nas": nombre_carpeta,
        "existe_carpeta": os.path.exists(cam_folder),
        "ultima_modificacion": None,
        "grabando": False
    }

    if status["existe_carpeta"]:
        try:
            mtime = os.path.getmtime(cam_folder)
            last_change = datetime.fromtimestamp(mtime)
            status["ultima_modificacion"] = last_change.strftime("%Y-%m-%d %H:%M:%S")
            
            # Se considera que graba si hubo cambios en los últimos 5 minutos
            diff = (datetime.now() - last_change).total_seconds()
            if diff < 300:
                status["grabando"] = True
        except Exception as e:
            status["error"] = f"Error de acceso: {str(e)}"
            
    return status

def main():
    print(f"[{datetime.now()}] 🎥 Iniciando auditoría de cámaras en {NAS_PATH}")
    token = get_zabbix_token()
    if not token:
        print("❌ Error: No se pudo autenticar con Zabbix.")
        return

    cameras = get_cameras_from_zabbix(token)
    if not cameras:
        print("⚠️ No se encontraron cámaras en el grupo 'Camaras'.")
        return

    reporte_camaras = []

    for cam in cameras:
        name = cam['name']
        ip = cam['interfaces'][0]['ip'] if cam['interfaces'] else "N/A"
        
        info = check_recording_status(name)
        
        # Log por consola rápido
        check_mark = "✅" if info['grabando'] else "❌"
        print(f"{check_mark} {name.ljust(25)} -> Folder: {info['carpeta_en_nas']}")
        
        reporte_camaras.append({
            "camara": name,
            "ip": ip,
            "estado_grabacion": info,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    with open("estado_grabaciones.json", "w") as f:
        json.dump(reporte_camaras, f, indent=4)
    
    print(f"\n✅ Proceso completado. Reporte guardado en 'estado_grabaciones.json'")

if __name__ == "__main__":
    main()