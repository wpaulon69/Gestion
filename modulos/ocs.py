import requests
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def obtener_datos_ocs(config):
    """Consulta la API REST de OCS Inventory para obtener inventario del parque informatico."""

    ocs_config = config.get("ocs")
    if not ocs_config:
        return {"error": "Configuracion de OCS no encontrada en config.json"}

    base_url = ocs_config.get("url", "").rstrip("/")
    user = ocs_config.get("user", "")
    password = ocs_config.get("password", "")
    verify_ssl = ocs_config.get("verify_ssl", False)
    timeout = ocs_config.get("timeout", 15)

    resultado = {
        "total_equipos": 0,
        "equipos_activos": 0,
        "equipos_inactivos": 0,
        "antiguedad_promedio_anios": 0,
        "por_os": {},
        "por_tipo": {},
        "por_ubicacion": {},
        "alertas_disco": [],
        "alertas_ram": [],
        "alertas_antiguedad": [],
        "alertas_antivirus": [],
        "alertas_updates": [],
        "equipos_detalle": [],
        "error": None
    }

    session = requests.Session()
    session.verify = verify_ssl
    session.timeout = timeout

    try:
        # 1. Autenticacion - obtener cookie de sesion
        auth_url = base_url + "/v1/login"
        auth_payload = {"username": user, "password": password}
        r_auth = session.post(auth_url, json=auth_payload, timeout=timeout)

        if r_auth.status_code == 401 or r_auth.status_code == 403:
            resultado["error"] = "Autenticacion OCS fallida (HTTP " + str(r_auth.status_code) + ")"
            return resultado

        # Si la API usa token en headers en vez de cookie
        if r_auth.status_code == 200:
            auth_data = r_auth.json()
            token = auth_data.get("token") or auth_data.get("access_token") or auth_data.get("apikey")
            if token:
                session.headers.update({"Authorization": "Bearer " + token})

        # 2. Obtener lista de computadoras
        computers_url = base_url + "/v1/computers"
        r_comp = session.get(computers_url, timeout=timeout)

        if r_comp.status_code == 404:
            # Probar endpoint alternativo (OCS 2.x usa /ocsapi/v1/computers)
            computers_url = base_url + "/computers"
            r_comp = session.get(computers_url, timeout=timeout)

        if r_comp.status_code != 200:
            resultado["error"] = "Error al obtener equipos (HTTP " + str(r_comp.status_code) + ")"
            return resultado

        equipos = r_comp.json()
        if isinstance(equipos, dict):
            equipos = equipos.get("data", equipos.get("results", equipos.get("computers", [])))
        if not isinstance(equipos, list):
            equipos = []

        ahora = datetime.now()
        hace_30_dias = ahora - timedelta(days=30)
        hace_60_dias = ahora - timedelta(days=60)
        hace_5_anios = ahora - timedelta(days=1825)

        total_edad = 0
        equipos_con_edad = 0

        for eq in equipos:
            detalle = _procesar_equipo(eq, ahora, hace_30_dias, hace_60_dias, hace_5_anios)

            # Contadores
            resultado["total_equipos"] += 1
            if detalle.get("activo"):
                resultado["equipos_activos"] += 1
            else:
                resultado["equipos_inactivos"] += 1

            # Por OS
            os_name = detalle.get("os", "Desconocido")
            resultado["por_os"][os_name] = resultado["por_os"].get(os_name, 0) + 1

            # Por tipo
            tipo = detalle.get("tipo", "Desconocido")
            resultado["por_tipo"][tipo] = resultado["por_tipo"].get(tipo, 0) + 1

            # Por ubicacion
            ubicacion = detalle.get("ubicacion", "Sin ubicacion")
            resultado["por_ubicacion"][ubicacion] = resultado["por_ubicacion"].get(ubicacion, 0) + 1

            # Antiguedad
            if detalle.get("fecha_compra"):
                total_edad += detalle["anios_antiguedad"]
                equipos_con_edad += 1

            # Alertas
            if detalle.get("alerta_disco"):
                resultado["alertas_disco"].append(detalle)
            if detalle.get("alerta_ram"):
                resultado["alertas_ram"].append(detalle)
            if detalle.get("alerta_antiguedad"):
                resultado["alertas_antiguedad"].append(detalle)
            if detalle.get("alerta_antivirus"):
                resultado["alertas_antivirus"].append(detalle)
            if detalle.get("alerta_updates"):
                resultado["alertas_updates"].append(detalle)

            resultado["equipos_detalle"].append(detalle)

        # Antiguedad promedio
        if equipos_con_edad > 0:
            resultado["antiguedad_promedio_anios"] = round(total_edad / equipos_con_edad, 1)

    except requests.exceptions.ConnectionError:
        resultado["error"] = "Sin conexion al servidor OCS (" + base_url + ")"
    except requests.exceptions.Timeout:
        resultado["error"] = "Timeout conectando a OCS (" + str(timeout) + "s)"
    except Exception as e:
        resultado["error"] = "Error OCS: " + str(e)
    finally:
        session.close()

    return resultado


def _procesar_equipo(eq, ahora, hace_30_dias, hace_60_dias, hace_5_anios):
    """Extrae datos relevantes de un equipo individual de OCS."""

    detalle = {
        "hostname": "",
        "ip": "",
        "os": "Desconocido",
        "tipo": "Desconocido",
        "ubicacion": "Sin ubicacion",
        "ultimo_contacto": None,
        "activo": False,
        "ram_gb": 0,
        "disco_uso_pct": 0,
        "fecha_compra": None,
        "anios_antiguedad": 0,
        "antivirus": None,
        "ultima_actualizacion": None,
        "alerta_disco": False,
        "alerta_ram": False,
        "alerta_antiguedad": False,
        "alerta_antivirus": False,
        "alerta_updates": False
    }

    # Hostname
    hardware = eq.get("hardware", eq)
    detalle["hostname"] = hardware.get("name", hardware.get("hostname", ""))
    detalle["tipo"] = hardware.get("type", hardware.get("osname", "Desconocido"))

    # Si el tipo viene del OS, inferir por nombre
    os_name = hardware.get("osname", hardware.get("os", ""))
    if os_name:
        detalle["os"] = os_name
        if "windows" in os_name.lower():
            if "server" in os_name.lower():
                detalle["tipo"] = "Servidor"
            elif "10" in os_name or "11" in os_name:
                detalle["tipo"] = "PC/Notebook"
            else:
                detalle["tipo"] = "PC/Notebook"
        elif "linux" in os_name.lower():
            detalle["tipo"] = "Servidor" if "ubuntu server" in os_name.lower() or "debian" in os_name.lower() else "PC/Notebook"

    # IP
    networks = eq.get("networks", [])
    if isinstance(networks, list) and len(networks) > 0:
        for net in networks:
            ip = net.get("ipaddress", net.get("ip", ""))
            if ip and ip != "0.0.0.0" and ip != "127.0.0.1" and not ip.startswith("169.254"):
                detalle["ip"] = ip
                break
    if not detalle["ip"]:
        detalle["ip"] = hardware.get("ipaddr", hardware.get("ip", ""))

    # Ubicacion
    detalle["ubicacion"] = hardware.get("location", hardware.get("userdomain", "Sin ubicacion"))

    # Ultimo contacto
    last_date_str = hardware.get("lastcome", hardware.get("last_seen", ""))
    if last_date_str:
        try:
            # OCS usa formato: 2024-01-15 10:30:00
            last_date = datetime.strptime(last_date_str[:19], "%Y-%m-%d %H:%M:%S")
            detalle["ultimo_contacto"] = last_date_str
            detalle["activo"] = last_date > hace_30_dias
        except (ValueError, TypeError):
            pass

    # RAM
    memories = eq.get("memories", [])
    if isinstance(memories, list):
        total_ram_mb = 0
        for mem in memories:
            cap = mem.get("capacity", mem.get("size", 0))
            try:
                total_ram_mb += int(cap)
            except (ValueError, TypeError):
                pass
        if total_ram_mb > 0:
            detalle["ram_gb"] = round(total_ram_mb / 1024, 1)

    # Disco
    drives = eq.get("drives", eq.get("storages", []))
    if isinstance(drives, list):
        max_uso = 0
        for drv in drives:
            tipo_disco = drv.get("type", drv.get("filesystem", ""))
            # Solo discos locales (ignorar CD-ROM, red, etc.)
            if any(t in tipo_disco.lower() for t in ["cdrom", "dvd", "network", "nfs", "smb"]):
                continue
            total = drv.get("total", drv.get("size", 0))
            libre = drv.get("free", drv.get("avail", 0))
            try:
                total_int = int(total)
                libre_int = int(libre)
                if total_int > 0:
                    uso_pct = round(((total_int - libre_int) / total_int) * 100, 1)
                    if uso_pct > max_uso:
                        max_uso = uso_pct
            except (ValueError, TypeError):
                pass
        detalle["disco_uso_pct"] = max_uso

    # Fecha de compra / BIOS
    bios = eq.get("bios", {})
    if isinstance(bios, dict):
        fecha_bios = bios.get("bdate", bios.get("release_date", ""))
        if fecha_bios:
            try:
                fecha = datetime.strptime(fecha_bios[:10], "%Y-%m-%d")
                detalle["fecha_compra"] = fecha_bios[:10]
                detalle["anios_antiguedad"] = round((ahora - fecha).days / 365.25, 1)
            except (ValueError, TypeError):
                pass

    # Antivirus
    antivirus = eq.get("antivirus", eq.get("security", []))
    if isinstance(antivirus, list):
        if len(antivirus) > 0:
            av = antivirus[0]
            detalle["antivirus"] = av.get("name", av.get("product", "Detectado"))
        else:
            detalle["antivirus"] = None

    # Ultima actualizacion Windows
    updates = eq.get("updates", eq.get("softwares", []))
    if isinstance(updates, list) and len(updates) > 0:
        ultima = updates[0]
        fecha_upd = ultima.get("install_date", ultima.get("date", ""))
        if fecha_upd:
            detalle["ultima_actualizacion"] = fecha_upd

    # === GENERAR ALERTAS ===
    if detalle["disco_uso_pct"] >= 90:
        detalle["alerta_disco"] = True
    if detalle["ram_gb"] > 0 and detalle["ram_gb"] < 4:
        detalle["alerta_ram"] = True
    if detalle["anios_antiguedad"] >= 5:
        detalle["alerta_antiguedad"] = True
    if detalle["antivirus"] is None:
        detalle["alerta_antivirus"] = True
    if detalle["activo"] and detalle["ultima_actualizacion"]:
        try:
            fecha_upd_dt = datetime.strptime(detalle["ultima_actualizacion"][:10], "%Y-%m-%d")
            if fecha_upd_dt < hace_60_dias:
                detalle["alerta_updates"] = True
        except (ValueError, TypeError):
            pass

    return detalle


def buscar_equipos_ocs(config, query, tipo_busqueda="hostname"):
    """Busca equipos en OCS Inventory por hostname, IP, software o usuario."""

    ocs_config = config.get("ocs")
    if not ocs_config:
        return {"error": "Configuracion de OCS no encontrada", "resultados": []}

    base_url = ocs_config.get("url", "").rstrip("/")
    user = ocs_config.get("user", "")
    password = ocs_config.get("password", "")
    verify_ssl = ocs_config.get("verify_ssl", False)
    timeout = ocs_config.get("timeout", 15)

    session = requests.Session()
    session.verify = verify_ssl
    session.timeout = timeout

    resultados = []

    try:
        # Autenticacion
        auth_url = base_url + "/v1/login"
        r_auth = session.post(auth_url, json={"username": user, "password": password}, timeout=timeout)
        if r_auth.status_code == 200:
            auth_data = r_auth.json()
            token = auth_data.get("token") or auth_data.get("access_token") or auth_data.get("apikey")
            if token:
                session.headers.update({"Authorization": "Bearer " + token})

        # Busqueda via API
        search_url = base_url + "/v1/computers"
        params = {}
        if tipo_busqueda == "hostname":
            params["name"] = query
        elif tipo_busqueda == "ip":
            params["ip"] = query
        elif tipo_busqueda == "software":
            search_url = base_url + "/v1/softwares"
            params["name"] = query
        elif tipo_busqueda == "usuario":
            params["user"] = query

        r_search = session.get(search_url, params=params, timeout=timeout)
        if r_search.status_code != 200:
            search_url_alt = base_url + "/computers"
            r_search = session.get(search_url_alt, params=params, timeout=timeout)

        if r_search.status_code == 200:
            data = r_search.json()
            if isinstance(data, dict):
                data = data.get("data", data.get("results", data.get("computers", [])))
            if isinstance(data, list):
                ahora = datetime.now()
                hace_30_dias = ahora - timedelta(days=30)
                hace_60_dias = ahora - timedelta(days=60)
                hace_5_anios = ahora - timedelta(days=1825)
                for eq in data[:50]:
                    resultados.append(_procesar_equipo(eq, ahora, hace_30_dias, hace_60_dias, hace_5_anios))

    except requests.exceptions.ConnectionError:
        return {"error": "Sin conexion a OCS", "resultados": []}
    except requests.exceptions.Timeout:
        return {"error": "Timeout en busqueda OCS", "resultados": []}
    except Exception as e:
        return {"error": "Error busqueda OCS: " + str(e), "resultados": []}
    finally:
        session.close()

    return {"resultados": resultados, "total": len(resultados)}
