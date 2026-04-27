import subprocess
from datetime import datetime

def verificar_grabacion_hikvision(config, nombre_camara):
    recurso = config["nas"]["mapeo_camaras"].get(nombre_camara, nombre_camara)
    nas_ip = "10.175.6.10"
    
    status = {
        "carpeta_en_nas": recurso,
        "existe_carpeta": False,
        "ruta_completa_nas": f"\\\\{nas_ip}\\{recurso}",
        "archivo_actual": "N/A",
        "ultima_modificacion": "N/A",
        "grabando": False
    }

    try:
        cmd = ["smbclient", "-U", "sectorial", "--password", "nokia3189",
              f"//{nas_ip}/{recurso}", "-c", "recurse; ls"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            status["existe_carpeta"] = True
            
            # Buscar archivos con fecha
            ultimo_archivo = None
            ultimo_timestamp = 0
            
            for line in result.stdout.split("\n"):
                line = line.strip()
                if ".mp4" in line or ".pic" in line:
                    parts = line.split()
                    if len(parts) >= 6:
                        # Formato: nombre N tamano Mes dia hora año
                        # ej: hiv00007.mp4 N 268435456 Thu Mar 5 17:51:11 2026
                        nombre = parts[0]
                        fecha_str = " ".join(parts[-5:])  # "Thu Mar 5 17:51:11 2026"
                        
                        try:
                            # Parsear fecha
                            fecha_val = datetime.strptime(fecha_str, "%a %b %d %H:%M:%S %Y")
                            if fecha_val.timestamp() > ultimo_timestamp:
                                ultimo_timestamp = fecha_val.timestamp()
                                ultimo_archivo = nombre
                        except:
                            pass
            
            if ultimo_archivo:
                status["archivo_actual"] = ultimo_archivo
                status["grabando"] = True
                ft = datetime.fromtimestamp(ultimo_timestamp)
                status["ultima_modificacion"] = ft.strftime("%Y-%m-%d %H:%M:%S")
                
    except Exception as e:
        status["error"] = str(e)
            
    return status