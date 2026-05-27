import requests
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _crear_session(config):
    ocs_config = config.get("ocs")
    base_url = ocs_config.get("url", "").rstrip("/")
    user = ocs_config.get("user", "")
    password = ocs_config.get("password", "")
    verify_ssl = ocs_config.get("verify_ssl", False)
    timeout = ocs_config.get("timeout", 15)

    session = requests.Session()
    session.verify = verify_ssl
    session.auth = (user, password)
    session.timeout = timeout

    return session, base_url, timeout


def _obtener_equipos(session, base_url, timeout, offset=0, limit=500):
    all_equipos = []
    current_offset = offset

    while True:
        url = base_url + "/v1/computers?offset=" + str(current_offset) + "&limit=" + str(limit)
        try:
            r = session.get(url, timeout=timeout)
        except Exception:
            break

        if r.status_code != 200:
            break

        data = r.json()
        if not isinstance(data, dict):
            break

        items = []
        for key, value in data.items():
            try:
                int(key)
                items.append(value)
            except (ValueError, TypeError):
                pass

        if not items:
            break

        all_equipos.extend(items)

        if len(items) < limit:
            break

        current_offset += limit

    return all_equipos


def _simplificar_os(os_name):
    if not os_name:
        return "Desconocido"
    os_lower = os_name.lower()
    if "windows 11" in os_lower:
        return "Windows 11"
    elif "windows 10" in os_lower:
        return "Windows 10"
    elif "windows server" in os_lower:
        return "Windows Server"
    elif "windows 7" in os_lower:
        return "Windows 7"
    elif "windows" in os_lower:
        return "Windows (otro)"
    elif "linux" in os_lower:
        if "ubuntu" in os_lower:
            return "Ubuntu Linux"
        elif "debian" in os_lower:
            return "Debian Linux"
        elif "centos" in os_lower:
            return "CentOS Linux"
        else:
            return "Linux (otro)"
    elif "mac" in os_lower or "darwin" in os_lower:
        return "macOS"
    elif "zorin" in os_lower:
        return "Zorin OS"
    else:
        return os_name[:30]


def _procesar_equipo(eq, ahora, hace_30_dias, hace_60_dias, hace_5_anios):
    """Extrae datos relevantes de un equipo individual de OCS.
    OCS API REST usa keys MAYUSCULAS en hardware dict."""

    detalle = {
        "hostname": "",
        "ip": "",
        "os": "Desconocido",
        "tipo": "Desconocido",
        "ubicacion": "Sin ubicacion",
        "ultimo_contacto": None,
        "activo": False,
        "cpu": "",
        "ram_gb": 0,
        "disco_uso_pct": 0,
        "disco_total_gb": 0,
        "disco_libre_gb": 0,
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

    hw = eq.get("hardware", {})

    # Hostname
    detalle["hostname"] = hw.get("NAME", hw.get("name", ""))

    # CPU
    detalle["cpu"] = hw.get("PROCESSORT", "")

    # OS
    os_name = hw.get("OSNAME", hw.get("osname", ""))
    if os_name:
        detalle["os"] = os_name
        os_lower = os_name.lower()
        if "windows" in os_lower:
            if "server" in os_lower:
                detalle["tipo"] = "Servidor"
            else:
                detalle["tipo"] = "PC/Notebook"
        elif "linux" in os_lower:
            detalle["tipo"] = "Servidor" if "server" in os_lower else "PC/Notebook"

    # IP
    detalle["ip"] = hw.get("IPADDR", hw.get("ipaddr", ""))
    if not detalle["ip"]:
        networks = eq.get("networks", [])
        if isinstance(networks, list):
            for net in networks:
                ip = net.get("IPADDRESS", net.get("ipaddress", net.get("IP", "")))
                if ip and ip != "0.0.0.0" and ip != "127.0.0.1" and not ip.startswith("169.254"):
                    detalle["ip"] = ip
                    break

    # Ubicacion - accountinfo TAG
    accountinfo = eq.get("accountinfo", [])
    if isinstance(accountinfo, list) and len(accountinfo) > 0:
        ai = accountinfo[0] if isinstance(accountinfo[0], dict) else {}
        tag = ai.get("TAG", ai.get("tag", ""))
        if tag:
            detalle["ubicacion"] = tag
    if detalle["ubicacion"] == "Sin ubicacion":
        detalle["ubicacion"] = hw.get("USERDOMAIN", hw.get("WORKGROUP", "Sin ubicacion"))

    # Ultimo contacto
    last_date_str = hw.get("LASTCOME", hw.get("LASTDATE", ""))
    if last_date_str:
        try:
            clean_date = str(last_date_str).replace("\\/", "-")[:19]
            last_date = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
            detalle["ultimo_contacto"] = clean_date
            detalle["activo"] = last_date > hace_30_dias
        except (ValueError, TypeError):
            detalle["ultimo_contacto"] = str(last_date_str)[:19]

    # RAM - hardware MEMORY en MB
    memory_mb = hw.get("MEMORY", 0)
    try:
        memory_mb = int(memory_mb)
    except (ValueError, TypeError):
        memory_mb = 0

    if memory_mb == 0:
        memories = eq.get("memories", [])
        if isinstance(memories, list):
            for mem in memories:
                cap = mem.get("CAPACITY", mem.get("capacity", 0))
                try:
                    val = int(cap)
                    if val > 0:
                        memory_mb += val
                except (ValueError, TypeError):
                    pass

    if memory_mb > 0:
        detalle["ram_gb"] = round(memory_mb / 1024, 1)

    # Disco - drives con TOTAL/FREE en MB
    drives = eq.get("drives", [])
    if isinstance(drives, list):
        max_uso = 0
        total_principal = 0
        libre_principal = 0
        for drv in drives:
            tipo_disco = str(drv.get("TYPE", drv.get("type", drv.get("FILESYSTEM", "")))).lower()
            if any(t in tipo_disco for t in ["cdrom", "dvd", "network", "nfs", "smb", "removable"]):
                continue
            total = drv.get("TOTAL", drv.get("total", 0))
            libre = drv.get("FREE", drv.get("free", 0))
            try:
                total_int = int(total)
                libre_int = int(libre)
                if total_int > 0:
                    uso_pct = round(((total_int - libre_int) / total_int) * 100, 1)
                    if uso_pct > max_uso:
                        max_uso = uso_pct
                    # Tomar el disco principal (el mas grande)
                    if total_int > total_principal:
                        total_principal = total_int
                        libre_principal = libre_int
            except (ValueError, TypeError):
                pass
        detalle["disco_uso_pct"] = max_uso
        if total_principal > 0:
            detalle["disco_total_gb"] = round(total_principal / 1024, 0)
            detalle["disco_libre_gb"] = round(libre_principal / 1024, 0)

    # Fecha de BIOS
    bios = eq.get("bios", [])
    if isinstance(bios, list) and len(bios) > 0:
        bios_dict = bios[0] if isinstance(bios[0], dict) else {}
        fecha_bios = bios_dict.get("BDATE", bios_dict.get("bdate", ""))
        if fecha_bios:
            try:
                clean = str(fecha_bios).replace("\\/", "-")[:10]
                fecha = datetime.strptime(clean, "%Y-%m-%d")
                detalle["fecha_compra"] = clean
                detalle["anios_antiguedad"] = round((ahora - fecha).days / 365.25, 1)
            except (ValueError, TypeError):
                pass

    # Antivirus
    if "antivirus" in eq:
        antivirus_data = eq["antivirus"]
        if isinstance(antivirus_data, list) and len(antivirus_data) > 0:
            av = antivirus_data[0] if isinstance(antivirus_data[0], dict) else {}
            detalle["antivirus"] = av.get("NAME", av.get("name", av.get("PRODUCT", "Detectado")))
        elif isinstance(antivirus_data, list) and len(antivirus_data) == 0:
            detalle["antivirus"] = None
        else:
            detalle["antivirus"] = "No reportado"
    else:
        detalle["antivirus"] = "No reportado"

    # === GENERAR ALERTAS ===
    if detalle["disco_uso_pct"] >= 90:
        detalle["alerta_disco"] = True
    if detalle["ram_gb"] > 0 and detalle["ram_gb"] < 4:
        detalle["alerta_ram"] = True
    if detalle["anios_antiguedad"] >= 5:
        detalle["alerta_antiguedad"] = True
    if detalle["antivirus"] is None:
        detalle["alerta_antivirus"] = True

    return detalle


def obtener_datos_ocs(config):
    """Consulta la API REST de OCS Inventory para obtener inventario del parque informatico."""

    ocs_config = config.get("ocs")
    if not ocs_config:
        return {"error": "Configuracion de OCS no encontrada en config.json"}

    resultado = {
        "total_equipos": 0,
        "equipos_activos": 0,
        "equipos_inactivos": 0,
        "equipos_sin_reportar": 0,
        "antiguedad_promedio_anios": 0,
        "por_os": {},
        "por_tipo": {},
        "por_ubicacion": {},
        "distribucion_os": {},
        "alertas_disco": [],
        "alertas_ram": [],
        "alertas_antiguedad": [],
        "alertas_antivirus": [],
        "alertas_updates": [],
        "equipos_detalle": [],
        "portal_url": "",
        "error": None
    }

    base_url_raw = ocs_config.get("url", "").rstrip("/")
    resultado["portal_url"] = base_url_raw.replace("/ocsapi", "/ocsreports")

    session, base_url, timeout = _crear_session(config)

    try:
        try:
            r_test = session.get(base_url + "/v1/computers?offset=0&limit=1", timeout=timeout)
            if r_test.status_code == 401:
                resultado["error"] = "Autenticacion OCS fallida (HTTP 401)"
                return resultado
            if r_test.status_code != 200:
                resultado["error"] = "Error API OCS (HTTP " + str(r_test.status_code) + ")"
                return resultado
        except requests.exceptions.ConnectionError:
            resultado["error"] = "Sin conexion al servidor OCS (" + base_url + ")"
            return resultado
        except requests.exceptions.Timeout:
            resultado["error"] = "Timeout conectando a OCS (" + str(timeout) + "s)"
            return resultado

        equipos = _obtener_equipos(session, base_url, timeout)

        ahora = datetime.now()
        hace_30_dias = ahora - timedelta(days=30)
        hace_60_dias = ahora - timedelta(days=60)
        hace_5_anios = ahora - timedelta(days=1825)

        total_edad = 0
        equipos_con_edad = 0

        for eq in equipos:
            detalle = _procesar_equipo(eq, ahora, hace_30_dias, hace_60_dias, hace_5_anios)

            resultado["total_equipos"] += 1
            if detalle.get("activo"):
                resultado["equipos_activos"] += 1
            else:
                resultado["equipos_inactivos"] += 1

            os_simple = _simplificar_os(detalle.get("os", "Desconocido"))
            resultado["por_os"][os_simple] = resultado["por_os"].get(os_simple, 0) + 1
            resultado["distribucion_os"][os_simple] = resultado["distribucion_os"].get(os_simple, 0) + 1

            tipo = detalle.get("tipo", "Desconocido")
            resultado["por_tipo"][tipo] = resultado["por_tipo"].get(tipo, 0) + 1

            ubicacion = detalle.get("ubicacion", "Sin ubicacion")
            resultado["por_ubicacion"][ubicacion] = resultado["por_ubicacion"].get(ubicacion, 0) + 1

            if detalle.get("anios_antiguedad") > 0:
                total_edad += detalle["anios_antiguedad"]
                equipos_con_edad += 1

            if detalle.get("alerta_disco"):
                resultado["alertas_disco"].append(detalle["hostname"] + " (" + str(detalle["disco_uso_pct"]) + "%)")
            if detalle.get("alerta_ram"):
                resultado["alertas_ram"].append(detalle["hostname"] + " (" + str(detalle["ram_gb"]) + "GB)")
            if detalle.get("alerta_antiguedad"):
                resultado["alertas_antiguedad"].append(detalle["hostname"] + " (" + str(detalle["anios_antiguedad"]) + " anios)")
            if detalle.get("alerta_antivirus"):
                resultado["alertas_antivirus"].append(detalle["hostname"])
            if detalle.get("alerta_updates"):
                resultado["alertas_updates"].append(detalle["hostname"])

            resultado["equipos_detalle"].append(detalle)

        resultado["equipos_sin_reportar"] = resultado["equipos_inactivos"]

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


def buscar_equipos_ocs(config, query, tipo_busqueda="hostname"):
    """Busca equipos en OCS Inventory por hostname, IP, software o usuario."""

    ocs_config = config.get("ocs")
    if not ocs_config:
        return {"error": "Configuracion de OCS no encontrada", "resultados": []}

    session, base_url, timeout = _crear_session(config)
    resultados = []

    try:
        equipos = _obtener_equipos(session, base_url, timeout, limit=1000)

        ahora = datetime.now()
        hace_30_dias = ahora - timedelta(days=30)
        hace_60_dias = ahora - timedelta(days=60)
        hace_5_anios = ahora - timedelta(days=1825)

        query_lower = query.lower()

        for eq in equipos:
            hw = eq.get("hardware", {})
            match = False

            if tipo_busqueda == "hostname":
                name = hw.get("NAME", hw.get("name", "")).lower()
                if query_lower in name:
                    match = True
            elif tipo_busqueda == "ip":
                ipaddr = hw.get("IPADDR", hw.get("ipaddr", "")).lower()
                if query_lower in ipaddr:
                    match = True
                if not match:
                    networks = eq.get("networks", [])
                    for net in networks:
                        ip = net.get("IPADDRESS", net.get("ipaddress", "")).lower()
                        if query_lower in ip:
                            match = True
                            break
            elif tipo_busqueda == "software":
                softwares = eq.get("software", [])
                if isinstance(softwares, list):
                    for sw in softwares:
                        sw_name = sw.get("NAME", sw.get("name", "")).lower()
                        if query_lower in sw_name:
                            match = True
                            break
            elif tipo_busqueda == "usuario":
                user = hw.get("USERID", hw.get("userid", "")).lower()
                if query_lower in user:
                    match = True

            if match:
                detalle = _procesar_equipo(eq, ahora, hace_30_dias, hace_60_dias, hace_5_anios)
                resultados.append({
                    "hostname": detalle["hostname"],
                    "name": detalle["hostname"],
                    "ip": detalle["ip"],
                    "os": detalle["os"],
                    "cpu": detalle["cpu"],
                    "ram_gb": detalle["ram_gb"],
                    "disco_uso_pct": detalle["disco_uso_pct"],
                    "disco_total_gb": detalle["disco_total_gb"],
                    "disco_libre_gb": detalle["disco_libre_gb"],
                    "ultimo_contacto": detalle["ultimo_contacto"] or "Nunca",
                    "last_contact": detalle["ultimo_contacto"] or "Nunca",
                    "activo": detalle["activo"],
                    "ubicacion": detalle["ubicacion"]
                })

            if len(resultados) >= 50:
                break

    except requests.exceptions.ConnectionError:
        return {"error": "Sin conexion a OCS", "resultados": []}
    except requests.exceptions.Timeout:
        return {"error": "Timeout en busqueda OCS", "resultados": []}
    except Exception as e:
        return {"error": "Error busqueda OCS: " + str(e), "resultados": []}
    finally:
        session.close()

    return resultados
