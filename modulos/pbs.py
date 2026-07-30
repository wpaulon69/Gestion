import requests
import urllib3
import time

# Deshabilitar advertencias de certificados no válidos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def obtener_version_pbs(config):
    """Obtiene la versión de Proxmox Backup Server desde la API."""
    pbs_config = config.get("pbs")
    if not pbs_config:
        return {"error": "Configuración de PBS no encontrada"}

    base_url = f"https://{pbs_config['ip']}:{pbs_config.get('port', 8007)}"
    headers = {
        "Authorization": f"PBSAPIToken {pbs_config['token_id']}:{pbs_config['token_secret']}"
    }

    try:
        url = f"{base_url}/api2/json/version"
        res = requests.get(url, headers=headers, verify=False, timeout=5)
        if res.status_code == 200:
            data = res.json().get("data", {})
            version = data.get("version") or data.get("release") or data.get("version_raw")
            return {"version": version} if version else {"error": "No se encontró versión"}
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
                
                if res_st.status_code == 200:
                    status_info = res_st.json().get("data", {})
                    # PBS retorna bytes
                    total_bytes = status_info.get("total", 0)
                    used_bytes = status_info.get("used", 0)
                    free_bytes = status_info.get("avail", 0)
                    
                    uso_porcentaje = 0
                    if total_bytes > 0:
                        uso_porcentaje = round((used_bytes / total_bytes) * 100, 1)

                    resultado["datastores"].append({
                        "nombre": ds["store"],
                        "total_gb": round(total_bytes / (1024**3), 2),
                        "usado_gb": round(used_bytes / (1024**3), 2),
                        "libre_gb": round(free_bytes / (1024**3), 2),
                        "uso_porcentaje": uso_porcentaje,
                        # Para status_info, hay error_count o cosas similares a veces, lo ignoramos de momento
                    })
        else:
            resultado["error_datastores"] = f"HTTP {res_ds.status_code}"

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
                # Si hay algo que no es OK y no es running, es fallo
                tiene_fallos = any(s != "OK" and s != "running" for s in estados)
                resultado["historial_backups"]["diarios_ultimos_7d"].append({
                    "fecha": fd,
                    "estado": "ERR" if tiene_fallos else "OK"
                })
                
            # Evaluar semanal (último fin de semana con actividad)
            fechas_semanales = sorted(list(semanales_agrupados.keys()), reverse=True)
            if fechas_semanales:
                fs = fechas_semanales[0]
                estados_sem = semanales_agrupados[fs]
                tiene_fallos = any(s != "OK" and s != "running" for s in estados_sem)
                resultado["historial_backups"]["semanal_ultimo"] = {
                    "fecha": fs,
                    "estado": "ERR" if tiene_fallos else "OK"
                }
                
        else:
            resultado["error_tareas"] = f"HTTP {res_tasks.status_code}"
        # Sin conversiones adicionales
    except Exception as e:
        resultado["error"] = str(e)

    return resultado
