import requests
import os
import json
from datetime import datetime

# --- CONFIGURACIÓN DE ACCESO ---
ZABBIX_URL = "http://10.175.6.12/zabbix/api_jsonrpc.php"
ZAB_USER = "APIGrafana"
ZAB_PASS = "gestion1234"

# La raíz es la IP del NAS directamente (recurso compartido)
NAS_BASE = r"\\10.175.6.10" 

# --- MAPEO DEFINITIVO (Zabbix -> Nombre de Recurso Compartido) ---
# Clave: 'name' tal cual figura en Zabbix
# Valor: Nombre de la carpeta compartida en el NAS
MAPEO_CARPETAS = {
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
    """Autenticación con la API de Zabbix para obtener token de sesión."""
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {"username": ZAB_USER, "password": ZAB_PASS},
        "id": 1
    }
    try:
        response = requests.post(ZABBIX_URL, json=payload, timeout=5).json()
        return response.get("result")
    except Exception as e:
        print(f"Error conectando a Zabbix: {e}")
        return None

def get_cameras_from_zabbix(token):
    """Obtiene los hosts que pertenecen al grupo 'Camaras' (ID 22)."""
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid", "name"],
            "selectInterfaces": ["ip"],
            "groupids": "22" 
        },
        "auth": token,
        "id": 2
    }
    try:
        response = requests.post(ZABBIX_URL, json=payload).json()
        return response.get("result", [])
    except Exception as e:
        print(f"Error obteniendo cámaras: {e}")
        return []

def get_hikvision_latest_file(root_path):
    """
    Escanea las subcarpetas datadirX y encuentra el archivo 
    individual más reciente (el que se está sobreescribiendo ahora).
    """
    latest_time = 0
    latest_file_path = None

    try:
        if not os.path.exists(root_path):
            return None, 0
            
        # Hikvision usa estructuras datadir0, datadir1, etc.
        for entry in os.scandir(root_path):
            if entry.is_dir() and "datadir" in entry.name.lower():
                # Escaneamos archivos dentro de cada datadir (ej: datadir0/hiv00001.mp4)
                try:
                    for f in os.scandir(entry.path):
                        if f.is_file():
                            # Obtenemos fecha de modificación del archivo individual
                            mtime = f.stat().st_mtime
                            if mtime > latest_time:
                                latest_time = mtime
                                latest_file_path = f.path
                except Exception:
                    continue
    except Exception as e:
        print(f"Error escaneando subdirectorios en {root_path}: {e}")
    
    return latest_file_path, latest_time

def check_recording_status(cam_name):
    """Verifica si el recurso compartido tiene actividad de escritura real."""
    recurso = MAPEO_CARPETAS.get(cam_name)
    ruta_completa = os.path.join(NAS_BASE, recurso) if recurso else None
    
    status = {
        "carpeta_en_nas": recurso or cam_name,
        "existe_carpeta": False,
        "archivo_actual": "N/A",
        "ultima_modificacion": None,
        "grabando": False
    }

    try:
        if ruta_completa and os.path.exists(ruta_completa):
            status["existe_carpeta"] = True
            
            # Buscamos el archivo más reciente dentro de los datadir
            archivo_path, mtime = get_hikvision_latest_file(ruta_completa)
            
            if mtime > 0:
                dt_mtime = datetime.fromtimestamp(mtime)
                status["archivo_actual"] = os.path.basename(archivo_path)
                status["ultima_modificacion"] = dt_mtime.strftime("%Y-%m-%d %H:%M:%S")
                
                # Consideramos grabando si hubo cambios en los últimos 15 minutos (900 seg)
                diff_segundos = (datetime.now() - dt_mtime).total_seconds()
                if diff_segundos < 900:
                    status["grabando"] = True
    except Exception as e:
        status["error"] = str(e)
            
    return status

def main():
    print(f"[{datetime.now()}] 🎥 Iniciando auditoría profunda Hikvision...")
    
    token = get_zabbix_token()
    if not token:
        print("Abortando: No hay token de Zabbix.")
        return

    cameras = get_cameras_from_zabbix(token)
    if not cameras:
        print("No se encontraron cámaras en Zabbix.")
        return

    reporte_final = []

    for cam in cameras:
        name = cam['name']
        ip = cam['interfaces'][0]['ip'] if cam['interfaces'] else "0.0.0.0"
        
        # Realizar el chequeo profundo de archivos
        storage_info = check_recording_status(name)
        
        # Log visual rápido en consola para depuración
        status_icon = "✅" if storage_info['grabando'] else "❌"
        if not storage_info['existe_carpeta']: status_icon = "⚠️"
        
        print(f"{status_icon} {name.ljust(30)} | Archivo: {str(storage_info['archivo_actual']).ljust(15)} | Modif: {storage_info['ultima_modificacion']}")
        
        reporte_final.append({
            "camara": name,
            "ip": ip,
            "estado_grabacion": storage_info,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    # Guardar reporte JSON para el Dashboard
    output_file = "estado_grabaciones.json"
    with open(output_file, "w") as f:
        json.dump(reporte_final, f, indent=4)
    
    print(f"\nAuditado: {len(reporte_final)} cámaras. Reporte generado en '{output_file}'.")

if __name__ == "__main__":
    main()