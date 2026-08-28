import requests
import urllib3
import time

# Deshabilitar advertencias de certificados no válidos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_version_pbs(config):
    """Obtiene la versión del Proxmox Backup Server."""
    pbs_config = config.get("pbs")
    if not pbs_config:
        return {"error": "Configuración de PBS no encontrada"}
    
    base_url = f"https://{pbs_config['ip']}:{pbs_config.get('port', 8007)}"
    headers = {
        "Authorization": f"PBSAPIToken {pbs_config['token_id']}:{pbs_config['token_secret']}"
    }
    
    try:
        # Endpoint /api2/json/version devuelve la versión
        url = f"{base_url}/api2/json/version"
        res = requests.get(url, headers=headers, verify=False, timeout=5)
        if res.status_code == 200:
            data = res.json().get("data", {})
            version = data.get("version", "unknown")
            return {"version": version}
        return {"error": f"HTTP {res.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def obtener_datos_pbs(config):
    """Consulta la API de Proxmox Backup Server para obtener el estado de los datastores y las tareas recientes."""
    
    pbs_config = config.get("pbs")
    if not pbs_config:
        return {"error": "Configuración de PBS no encontrada."}

    base_url = f"https://{pbs_config['ip']}:{pbs_config.get('port', 8007)}"
    
    # Header de autorización específico para Proxomx Backup Server
    headers = {
        "Authorization": f"PBSAPIToken {pbs_config['token_id']}:{pbs_config['token_secret']}"
    }
    
    resultado = {
        "datastores": [],
        "tareas_fallidas": [],
        "ultima_tarea_sincro": None
    }

    try:
        # 1. Consultar Datastores
        url_ds = f"{base_url}/api2/json/admin/datastore"
        res_ds = requests.get(url_ds, headers=headers, verify=False, timeout=5)
        
        if res_ds.status_code == 200:
            for ds in res_ds.json().get("data", []):
                
                # Obtener estado de cada datastore individual
                url_st = f"{base_url}/api2/json/admin/datastore/{ds['store']}/status"
                res_st = requests.get(url_st, headers=headers, verify=False, timeout=5)
                
                estado = "degraded" # Default si algo falla
                uso_porcentaje = None
                total_gb = None
                usado_gb = None
                libre_gb = None
                error_msg = None

                if res_st.status_code == 200:
                    status_info = res_st.json().get("data", {})
                    total_bytes = status_info.get("total")
                    used_bytes = status_info.get("used")
                    free_bytes = status_info.get("avail")
                    
                    if total_bytes is not None and used_bytes is not None:
                        uso_porcentaje = round((used_bytes / total_bytes) * 100, 2)
                        total_gb = round(total_bytes / (1024**3), 2)
                        usado_gb = round(used_bytes / (1024**3), 2)
                        libre_gb = round(free_bytes / (1024**3), 2)
                        estado = "ok" # Si hay info de uso y total, es OK
                    else:
                        error_msg = "Sin información de uso o total."
                else:
                    error_msg = f"HTTP {res_st.status_code} - No se pudo obtener estado (posible problema de montaje)"

                resultado["datastores"].append({
                    "nombre": ds["store"],
                    "estado": estado, # Siempre en minúsculas
                    "uso_porcentaje": uso_porcentaje,
                    "total_gb": total_gb,
                    "usado_gb": usado_gb,
                    "libre_gb": libre_gb,
                    "error": error_msg
                })
        else:
            resultado["error"] = f"HTTP {res_ds.status_code} al listar datastores"

        # Validar datastores esperados: solo advertimos cuáles faltan, no rompemos el PBS
        datastores_esperados = pbs_config.get("datastores_esperados", [])
        if datastores_esperados:
            datastores_encontrados = [ds["nombre"] for ds in resultado["datastores"]]
            faltantes = [ds for ds in datastores_esperados if ds not in datastores_encontrados]
            if faltantes:
                for ds_name in faltantes:
                    resultado["datastores"].append({
                        "nombre": ds_name,
                        "total_gb": None,
                        "usado_gb": None,
                        "libre_gb": None,
                        "uso_porcentaje": None,
                        "estado": "missing",
                        "error": "Datastore esperado pero no encontrado en PBS"
                    })

        # 2. Consultar Tareas (Tasks) enfocado a Backups
        url_tasks = f"{base_url}/api2/json/nodes/localhost/tasks"
        # Traemos 1000 tareas para tener buen historial de días
        res_tasks = requests.get(f"{url_tasks}?limit=1000", headers=headers, verify=False, timeout=5)
        
        resultado["historial_backups"] = {
            "diarios_ultimos_7d": [],
            "semanal_ultimo": None
        }

        if res_tasks.status_code == 200:
            import datetime
            tareas = res_tasks.json().get("data", [])
            
            diarios_agrupados = {}
            semanales_agrupados = {}
            
            for t in tareas:
                if t.get("worker_type") == "backup":
                    status = t.get("status", "running")
                    upid = t.get("upid", "")
                    # WD-1Tb es el datastore de semanales según infraestructura
                    # Copia-3Tb es diarios
                    is_semanal = "WD" in upid or "1Tb" in upid
                    
                    dt = datetime.datetime.fromtimestamp(t["starttime"])
                    # Usamos string de fecha
                    date_str = dt.strftime("%Y-%m-%d")
                    
                    target_dict = semanales_agrupados if is_semanal else diarios_agrupados
                    if date_str not in target_dict:
                        target_dict[date_str] = []
                    target_dict[date_str].append(status)
            
            # Evaluar diarios (últimos 7 días con actividad)
            fechas_diarios = sorted(list(diarios_agrupados.keys()), reverse=True)[:7]
            for fd in fechas_diarios:
                estados = diarios_agrupados[fd]
                # Si hay algo que no es ok y no es running, es fallo
                tiene_fallos = any(s.lower() != "ok" and s.lower() != "running" for s in estados)
                resultado["historial_backups"]["diarios_ultimos_7d"].append({
                    "fecha": fd,
                    "estado": "err" if tiene_fallos else "ok"
                })
                
            # Evaluar semanal (último fin de semana con actividad)
            fechas_semanales = sorted(list(semanales_agrupados.keys()), reverse=True)
            if fechas_semanales:
                fs = fechas_semanales[0]
                estados_sem = semanales_agrupados[fs]
                tiene_fallos = any(s.lower() != "ok" and s.lower() != "running" for s in estados_sem)
                resultado["historial_backups"]["semanal_ultimo"] = {
                    "fecha": fs,
                    "estado": "err" if tiene_fallos else "ok"
                }
                
        else:
            resultado["error_tareas"] = f"HTTP {res_tasks.status_code}"
        # Sin conversiones adicionales
    except Exception as e:
        resultado["error"] = str(e)

    return resultado
