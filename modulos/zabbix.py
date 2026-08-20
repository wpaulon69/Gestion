import requests

def obtener_version_zabbix(config):
    """Obtiene la versión de Zabbix Server desde la API."""
    zabbix_config = config.get("zabbix")
    if not zabbix_config:
        return {"error": "Configuración de Zabbix no encontrada"}
    
    url = zabbix_config["url"]
    
    # apiinfo.version no requiere autenticación
    payload = {
        "jsonrpc": "2.0",
        "method": "apiinfo.version",
        "params": {},
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5).json()
        version = response.get("result")
        return {"version": version} if version else {"error": "No se encontró versión"}
    except Exception as e:
        return {"error": str(e)}

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
    """Obtiene hosts filtrando por el nombre del grupo (solo habilitados)."""
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

        # 2. Obtener hosts (solo habilitados: status=0)
        payload_hosts = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "groupids": group_id,
                "selectInterfaces": ["ip"],
                "output": ["name", "status"],
                "filter": {"status": "0"}
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

def obtener_estado_mpls(token, config, host_name="MPLS"):
    """Obtiene estado completo del enlace MPLS: ping, latencia, packet loss y trends horarios."""
    try:
        # 1. Obtener host MPLS
        payload = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "output": ["hostid", "host", "name"],
                "filter": {"host": [host_name]},
                "selectInterfaces": ["ip"],
                "selectItems": ["itemid", "name", "key_", "lastvalue", "units"],
                "selectTriggers": ["triggerid", "description", "priority", "value"]
            },
            "auth": token,
            "id": 1
        }
        res = requests.post(config["zabbix"]["url"], json=payload, timeout=10).json()
        hosts = res.get("result", [])
        if not hosts:
            return {"estado": "No encontrado", "ip": "N/A"}

        h = hosts[0]
        ip = h["interfaces"][0]["ip"] if h.get("interfaces") else "N/A"
        items = {it["key_"]: it for it in h.get("items", [])}

        # 2. Valores actuales
        ping_ok = items.get("icmpping", {}).get("lastvalue", "0") == "1"
        latencia_ms = round(float(items.get("icmppingsec", {}).get("lastvalue", 0)) * 1000, 2)
        loss_pct = float(items.get("icmppingloss", {}).get("lastvalue", 0))

        # 3. Triggers activos
        triggers_activos = [t for t in h.get("triggers", []) if t.get("value") == "1"]

        # 4. Trends de latencia (últimas 24 horas)
        from datetime import datetime
        now = int(datetime.now().timestamp())
        ayer = now - 86400

        itemid_latency = items.get("icmppingsec", {}).get("itemid")
        itemid_loss = items.get("icmppingloss", {}).get("itemid")

        trends_latencia = []
        trends_loss = []

        if itemid_latency:
            payload_t = {
                "jsonrpc": "2.0",
                "method": "trend.get",
                "params": {
                    "itemids": [itemid_latency],
                    "time_from": ayer,
                    "time_till": now,
                    "output": ["clock", "value_avg", "value_min", "value_max"],
                    "sortfield": "clock"
                },
                "auth": token,
                "id": 2
            }
            r = requests.post(config["zabbix"]["url"], json=payload_t, timeout=10).json()
            for t in r.get("result", []):
                trends_latencia.append({
                    "hora": datetime.fromtimestamp(int(t["clock"])).strftime("%H:%M"),
                    "avg": round(float(t["value_avg"]) * 1000, 2),
                    "min": round(float(t["value_min"]) * 1000, 2),
                    "max": round(float(t["value_max"]) * 1000, 2)
                })

        if itemid_loss:
            payload_t["params"]["itemids"] = [itemid_loss]
            r = requests.post(config["zabbix"]["url"], json=payload_t, timeout=10).json()
            for t in r.get("result", []):
                trends_loss.append({
                    "hora": datetime.fromtimestamp(int(t["clock"])).strftime("%H:%M"),
                    "avg": float(t["value_avg"]),
                    "max": float(t["value_max"])
                })

        # 5. Calcular estado resumido
        if not ping_ok:
            estado = "CAIDO"
        elif loss_pct > 20:
            estado = "CRITICO"
        elif loss_pct > 5 or latencia_ms > 20:
            estado = "ALERTA"
        else:
            estado = "OK"

        return {
            "estado": estado,
            "ip": ip,
            "ping": ping_ok,
            "latencia_ms": latencia_ms,
            "loss_pct": loss_pct,
            "triggers_activos": len(triggers_activos),
            "triggers_detalle": [{"descripcion": t["description"], "prioridad": t["priority"]} for t in triggers_activos],
            "trends_latencia": trends_latencia,
            "trends_loss": trends_loss
        }

    except Exception as e:
        print(f"❌ Error consultando MPLS: {e}")
        return {"estado": "Error", "ip": "N/A", "ping": False, "latencia_ms": 0, "loss_pct": 100,
                "triggers_activos": 0, "triggers_detalle": [], "trends_latencia": [], "trends_loss": []}


def obtener_ocupacion_nas(token, config):
    """Obtiene la ocupación de discos de todos los hosts con 'Space utilization'."""
    payload = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "search": {"name": "Space utilization"},
            "output": ["name", "lastvalue"],
            "selectHosts": ["host", "name"],
            "limit": 200
        },
        "auth": token,
        "id": 1
    }
    try:
        res = requests.post(config["zabbix"]["url"], json=payload, timeout=10).json().get("result", [])
        volumenes = []
        for item in res:
            # Capturar el nombre del punto de montaje del item name (formato: "MountPoint: Space utilization")
            full_path = item['name'].split(': ')[0]
            
            # Filtro: ignorar particiones de sistema, snaps, subvols, etc.
            black_list = ['/var/snap', 'subvol-', 'loop', 'squashfs', '/dev/', '/run']
            if any(x in full_path for x in black_list):
                continue

            # Filtro NAS: excluir subcarpetas de cámaras y items obsoletos
            # full_path viene como "/mnt/datastore/camaras-6tb/camConsultorioExt" etc.
            nas_exclude = [
                '/mnt/datastore/camaras-6tb/cam',  # subcarpetas por cámara
                'OMV-Backups',
                'rotan',
            ]
            if any(x in full_path for x in nas_exclude):
                continue

            # Excluir host OMV-Backups completo (ya no existe)
            hosts = item.get('hosts', [])
            host_name = hosts[0]['name'] if hosts else 'Desconocido'
            if host_name == 'OMV-Backups':
                continue
            
            # Ignorar paths técnicos UUID (ya tenemos los /export equivalentes)
            if full_path.startswith('/srv/dev-disk-by-uuid'):
                continue
            
            # Nombre del host Zabbix
            hosts = item.get('hosts', [])
            host_name = hosts[0]['name'] if hosts else 'Desconocido'
            
            # Limpiar nombre para el dashboard
            nombre = full_path.replace('/export/', '').replace('/mnt/datastore/', 'DS-')
            if nombre == "/": nombre = "Sistema (Root)"
            
            volumenes.append({
                "nombre": nombre,
                "porcentaje": round(float(item['lastvalue']), 2),
                "host": host_name
            })
        
        # Ordenar por host + nombre para consistencia
        volumenes.sort(key=lambda x: (x['host'], x['nombre']))
        return volumenes

    except:
        return []

