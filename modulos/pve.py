import requests
import urllib3

# Deshabilitar advertencias de certificados no válidos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def obtener_version_pve(config):
    """Obtiene la versión de Proxmox VE desde la API."""
    pve_config = config.get("pve")
    if not pve_config:
        return {"error": "Configuración de PVE no encontrada"}
    
    base_url = f"https://{pve_config['ip']}:{pve_config.get('port', 8006)}"
    headers = {
        "Authorization": f"PVEAPIToken={pve_config['token_id']}={pve_config['token_secret']}"
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


def obtener_datos_pve(config):
    """Consulta la API de Proxmox VE para obtener el estado del hardware y las máquinas virtuales."""
    
    pve_config = config.get("pve")
    if not pve_config:
        return {"error": "Configuración de PVE no encontrada."}

    base_url = f"https://{pve_config['ip']}:{pve_config.get('port', 8006)}"
    
    # Header de autorización específico para Proxomx VE
    headers = {
        "Authorization": f"PVEAPIToken={pve_config['token_id']}={pve_config['token_secret']}"
    }
    
    resultado = {
        "nodos": [],
        "vms": [],
        "resumen_recursos": {}
    }

    try:
        # 1. Obtener lista de nodos
        url_nodos = f"{base_url}/api2/json/nodes"
        res_nodos = requests.get(url_nodos, headers=headers, verify=False, timeout=30)
        
        if res_nodos.status_code == 200:
            nodos_data = res_nodos.json().get("data", [])
            for n in nodos_data:
                node_name = n["node"]
                
                # 2. Obtener estado detallado del nodo (para discos y RAM)
                url_st = f"{base_url}/api2/json/nodes/{node_name}/status"
                res_st = requests.get(url_st, headers=headers, verify=False, timeout=30)
                
                if res_st.status_code == 200:
                    st = res_st.json().get("data", {})
                    
                    # Extraer info de root disk (está en rootfs)
                    rootfs = st.get("rootfs", {})
                    total_root = rootfs.get("total", 0)
                    used_root = rootfs.get("used", 0)
                    free_root = rootfs.get("free", 0)
                    pct_root = 0
                    if total_root > 0:
                        pct_root = round((used_root / total_root) * 100, 2)
                    
                    node_info = {
                        "nombre": node_name,
                        "cpu_uso": round(st.get("cpu", 0) * 100, 2),
                        "ram_total_gb": round(st.get("memory", {}).get("total", 0) / (1024**3), 2),
                        "ram_usada_gb": round(st.get("memory", {}).get("used", 0) / (1024**3), 2),
                        "ram_pct": round((st.get("memory", {}).get("used", 0) / st.get("memory", {}).get("total", 1)) * 100, 2),
                        "uptime": st.get("uptime", 0),
                        "disco_root_pct": pct_root,
                        "status": n.get("status", "unknown")
                    }
                    resultado["nodos"].append(node_info)
                    
                    # 3. Obtener VMs del nodo
                    url_vms = f"{base_url}/api2/json/nodes/{node_name}/qemu"
                    res_vms = requests.get(url_vms, headers=headers, verify=False, timeout=30)
                    
                    if res_vms.status_code == 200:
                        vms_data = res_vms.json().get("data", [])
                        for v in vms_data:
                            # Filtramos las VMs con nombre relevante o todas
                            resultado["vms"].append({
                                "vmid": v.get("vmid"),
                                "nombre": v.get("name"),
                                "estado": v.get("status"), # running, stopped
                                "cpu": round(v.get("cpu", 0) * 100, 2),
                                "ram_gb": round(v.get("maxmem", 0) / (1024**3), 2),
                                "uptime": v.get("uptime", 0),
                                "nodo": node_name
                            })
                    
                    # 4. Obtener Contenedores (LXC) del nodo
                    url_lxc = f"{base_url}/api2/json/nodes/{node_name}/lxc"
                    res_lxc = requests.get(url_lxc, headers=headers, verify=False, timeout=30)
                    if res_lxc.status_code == 200:
                        for l in res_lxc.json().get("data", []):
                            resultado["vms"].append({
                                "vmid": l.get("vmid"),
                                "nombre": l.get("name"),
                                "estado": l.get("status"),
                                "cpu": round(l.get("cpu", 0) * 100, 2),
                                "ram_gb": round(l.get("maxmem", 0) / (1024**3), 2),
                                "uptime": l.get("uptime", 0),
                                "nodo": node_name,
                                "tipo": "lxc"
                            })
                    
                    else:
                        resultado["error"] = f"Error al consultar nodos PVE: HTTP {res_nodos.status_code}"
            
    except Exception as e:
        resultado["error"] = f"Excepción en PVE: {str(e)}"

    return resultado
