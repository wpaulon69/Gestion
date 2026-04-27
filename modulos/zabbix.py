import requests

def autenticar(config):
    """Autenticación en Zabbix para obtener token de sesión."""
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "username": config["zabbix"]["user"], 
            "password": config["zabbix"]["password"]
        },
        "id": 1
    }
    try:
        response = requests.post(config["zabbix"]["url"], json=payload, timeout=5).json()
        return response.get("result")
    except Exception as e:
        print(f"❌ Error conectando a Zabbix: {e}")
        return None

def obtener_hosts_por_grupo(token, config, nombre_grupo):
    """Obtiene hosts filtrando por el nombre del grupo."""
    # 1. Obtener ID del grupo
    payload_group = {
        "jsonrpc": "2.0",
        "method": "hostgroup.get",
        "params": {"filter": {"name": [nombre_grupo]}},
        "auth": token,
        "id": 1
    }
    try:
        group_res = requests.post(config["zabbix"]["url"], json=payload_group).json().get("result", [])
        if not group_res: 
            return []
        
        group_id = group_res[0]['groupid']

        # 2. Obtener hosts
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
        return requests.post(config["zabbix"]["url"], json=payload_hosts).json().get("result", [])
    except Exception as e:
        print(f"❌ Error al obtener hosts de {nombre_grupo}: {e}")
        return []

def obtener_alertas(token, config, limite=15):
    """Obtiene problemas activos de Zabbix incluyendo el host."""
    payload = {
        "jsonrpc": "2.0",
        "method": "problem.get",
        "params": {
            "recent": True,
            "selectAcknowledges": "extend",
            "selectTags": "extend",
            "limit": limite
        },
        "auth": token,
        "id": 1
    }
    try:
        # Para obtener el nombre del host necesitamos consultar los triggers relacionados
        response = requests.post(config["zabbix"]["url"], json=payload).json()
        probs = response.get("result", [])
        
        # Obtenemos detalles de los triggers para saber a qué host pertenecen
        trigger_ids = [p['objectid'] for p in probs]
        payload_triggers = {
            "jsonrpc": "2.0",
            "method": "trigger.get",
            "params": {
                "triggerids": trigger_ids,
                "selectHosts": ["name"],
                "output": ["description"]
            },
            "auth": token,
            "id": 2
        }
        triggers_res = requests.post(config["zabbix"]["url"], json=payload_triggers).json().get("result", [])
        trigger_map = {t['triggerid']: t['hosts'][0]['name'] for t in triggers_res if t.get('hosts')}

        detalle = []
        for p in probs:
            host_name = trigger_map.get(p['objectid'], "N/A")
            detalle.append({
                "host": host_name,
                "evento": p['name'], 
                "severidad": p['severity']
            })

        return {
            "alertas_activas": len(probs),
            "detalle": detalle
        }
    except Exception as e:
        print(f"Error alertas: {e}")
        return {"alertas_activas": 0, "detalle": []}

def obtener_valores_ping(token, config, host_ids):
    """Consulta el valor mas reciente de icmpping para una lista de hosts."""
    if not host_ids: return {}
    payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "hostids": host_ids,
            "filter": {"key_": ["icmpping"]},
            "output": ["hostid", "lastvalue"]
        },
        "auth": token,
        "id": 1
    }
    try:
        response = requests.post(config["zabbix"]["url"], json=payload).json()
        items = response.get("result", [])
        return {item['hostid']: item['lastvalue'] for item in items}
    except Exception as e:
        print(f"Error cargando pings: {e}")
        return {}

def obtener_trafico_wan(token, config, ip_opnsense="10.175.6.203"):
    """Obtiene el tráfico entrante/saliente de la interfaz WAN."""
    payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "filter": {"ip": [ip_opnsense]},
            "search": {"name": ["network traffic on re0"]},
            "searchByAny": True,
            "output": ["name", "lastvalue", "units"]
        },
        "auth": token,
        "id": 1
    }
    try:
        res = requests.post(config["zabbix"]["url"], json=payload).json().get("result", [])
        stats = {"rx": 0, "tx": 0}
        for item in res:
            val = float(item['lastvalue'])
            if "Incoming" in item['name']: stats["rx"] = val
            if "Outgoing" in item['name']: stats["tx"] = val
        return stats
    except:
        return {"rx": 0, "tx": 0}

def obtener_ocupacion_nas(token, config, ip_nas="10.175.6.10"):
    """Obtiene la ocupación de los discos del NAS."""
    payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "filter": {"ip": [ip_nas]},
            "search": {"name": ["Space utilization"]},
            "output": ["name", "lastvalue"]
        },
        "auth": token,
        "id": 1
    }
    try:
        res = requests.post(config["zabbix"]["url"], json=payload).json().get("result", [])
        volumenes = []
        for item in res:
            # Capturar el nombre del punto de montaje del item name (formato: "MountPoint: Space utilization")
            full_path = item['name'].split(': ')[0]
            
            # Filtro: Solo nos interesan los volúmenes compartidos (/export) o montajes de datos (/mnt)
            # Ignoramos particiones de sistema, snaps de ubuntu y subvols de proxmox
            black_list = ['/var/snap', 'subvol-', 'loop', 'squashfs', '/dev/', '/run']
            if any(x in full_path for x in black_list):
                continue
            
            # Si el path es muy largo o técnico, y no es /export, lo ignoramos (opcional, ajustamos según imagen)
            if full_path.startswith('/srv/dev-disk-by-uuid'):
                continue # Ya tenemos los de /export que apuntan aquí

            # Limpiar nombre para el dashboard
            nombre = full_path.replace('/export/', '').replace('/mnt/datastore/', 'DS-')
            if nombre == "/": nombre = "Sistema (Root)"
            
            volumenes.append({
                "nombre": nombre,
                "porcentaje": round(float(item['lastvalue']), 2)
            })
        
        # Ordenar por nombre para consistencia
        volumenes.sort(key=lambda x: x['nombre'])
        return volumenes

    except:
        return []

