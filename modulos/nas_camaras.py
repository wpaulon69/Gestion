import subprocess
from datetime import datetime

def verificar_grabacion_hikvision(config, nombre_camara):
    nas_config = config.get("nas", {})
    nas_ip = nas_config.get("base_path", "\\\\10.175.6.2").replace("\\\\", "")
    nas_user = nas_config.get("user", "camaras")
    nas_pass = nas_config.get("password", "camaras")
    recurso = nas_config.get("mapeo_camaras", {}).get(nombre_camara, nombre_camara)

    status = {
        "carpeta_en_nas": recurso,
        "existe_carpeta": False,
        "ruta_completa_nas": f"\\\\{nas_ip}\\{recurso}",
        "archivo_actual": "N/A",
        "ultima_modificacion": "N/A",
        "grabando": False
    }

    try:
        cmd = ["smbclient", "-U", nas_user, "--password", nas_pass,
              f"//{nas_ip}/{recurso}", "-c", "recurse; ls"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            status["existe_carpeta"] = True

            # Buscar archivos con fecha - parsear output de "recurse; ls"
            # Formato: lista directorios y luego archivos por directorio
            # \datadir3
            #   hiv00065.mp4  A  0  Tue Aug 18 12:33:41 2026
            ultimo_archivo = None
            ultimo_timestamp = 0
            directorio_actual = ""  # Trackear subdirectorio actual

            for line in result.stdout.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Detectar cambio de directorio: línea que empieza con \
                if line.startswith("\\"):
                    directorio_actual = line[1:]  # Quitar el \ inicial
                    continue

                # Buscar archivos .mp4 o .pic
                if ".mp4" in line or ".pic" in line:
                    parts = line.split()
                    if len(parts) >= 6:
                        # Formato: nombre N tamano Mes dia hora año
                        nombre = parts[0]
                        fecha_str = " ".join(parts[-5:])  # "Thu Mar 5 17:51:11 2026"

                        try:
                            fecha_val = datetime.strptime(fecha_str, "%a %b %d %H:%M:%S %Y")
                            if fecha_val.timestamp() > ultimo_timestamp:
                                ultimo_timestamp = fecha_val.timestamp()
                                # Construir ruta relativa: directorio_actual/nombre
                                if directorio_actual:
                                    ultimo_archivo = f"{directorio_actual}/{nombre}"
                                else:
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