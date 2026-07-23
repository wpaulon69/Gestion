import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
from modulos import zabbix, omada, opnsense, pve, pbs, nas_camaras, ocs

def cargar_configuracion():
    with open("config.json", "r", encoding='utf-8') as f:
        return json.load(f)


def verificar_gateway(config, ip_gateway="192.168.0.1"):
    """Verifica conectividad y latencia al gateway de internet (192.168.0.1)."""
    resultado = {
        "ip": ip_gateway,
        "alcanzable": False,
        "latencia_ms": None,
        "velocidad_mbps": None,
        "estado": "CAIDO"
    }
    
    # 1. Ping simple (3 paquetes)
    try:
        ping_cmd = ["ping", "-c", "3", "-W", "2", ip_gateway]
        proc = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            resultado["alcanzable"] = True
            # Extraer latencia promedio del output del ping
            for line in proc.stdout.split('\n'):
                if 'rtt min/avg/max' in line or 'min/avg/max/mdev' in line:
                    partes = line.split('=')[1].strip().split('/')
                    if len(partes) >= 2:
                        resultado["latencia_ms"] = round(float(partes[1]), 2)
                    break
    except Exception as e:
        resultado["error_ping"] = str(e)
    
    # 2. Speed test simple (descarga de 10MB desde un servidor rápido)
    if resultado["alcanzable"]:
        try:
            # Usar speedtest-cli si está disponible, si no hacer test simple
            speed_cmd = ["speedtest-cli", "--simple", "--secure", "--timeout", "30"]
            proc = subprocess.run(speed_cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0:
                for line in proc.stdout.split('\n'):
                    if line.startswith('Download:'):
                        partes = line.split()
                        if len(partes) >= 2:
                            resultado["velocidad_mbps"] = float(partes[1])
        except FileNotFoundError:
            # speedtest-cli no instalado, hacer test simple con curl/wget
            try:
                # Test simple: descargar 10MB de un CDN rápido
                start = time.time()
                test_url = "http://speed.hetzner.de/10MB.bin"
                proc = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{speed_download}", "--max-time", "30", test_url],
                    capture_output=True, text=True, timeout=35
                )
                if proc.returncode == 0 and proc.stdout:
                    speed_bps = float(proc.stdout.strip())
                    resultado["velocidad_mbps"] = round(speed_bps / 1_000_000, 2)
            except Exception:
                pass
        except Exception:
            pass
    
    # 3. Determinar estado
    if not resultado["alcanzable"]:
        resultado["estado"] = "CAIDO"
    elif resultado["latencia_ms"] and resultado["latencia_ms"] > 50:
        resultado["estado"] = "ALTO_LATENCIA"
    elif resultado["velocidad_mbps"] and resultado["velocidad_mbps"] < 10:
        resultado["estado"] = "LENTO"
    else:
        resultado["estado"] = "OK"
    
    return resultado

async def main():
    print(f"[{datetime.now()}] [INICIO] Iniciando Auditoria Tecnica Unificada...")
    config = cargar_configuracion()

    # 1. Autenticacion en Zabbix
    token = zabbix.autenticar(config)
    if not token:
        print("[-] Error critico: No se pudo conectar a Zabbix")
        return

    # 2. Recoleccion de datos (Zabbix)
    print("[INFO] Obteniendo dispositivos desde Zabbix...")
    cams_h = zabbix.obtener_hosts_por_grupo(token, config, config["zabbix"]["grupos"]["camaras"])
    wifi_h = zabbix.obtener_hosts_por_grupo(token, config, config["zabbix"]["grupos"]["wifi"])
    huawei_h = zabbix.obtener_hosts_por_grupo(token, config, config["zabbix"]["grupos"]["huawei"])
    relojes_h = zabbix.obtener_hosts_por_grupo(token, config, config["zabbix"]["grupos"]["relojes"])
    alertas = zabbix.obtener_alertas(token, config)

    # 3. Procesamiento Inteligente de Estados (Ping Real + Alertas)
    todas_entidades = cams_h + wifi_h + huawei_h + relojes_h
    host_ids = [h['hostid'] for h in todas_entidades]
    pings = zabbix.obtener_valores_ping(token, config, host_ids)

    print(f"[INFO] Verificando grabacion en NAS para {len(cams_h)} camaras...")
    lista_camaras = []
    for h in cams_h:
        nombre = h['name']
        hid = h['hostid']
        estado_nas = nas_camaras.verificar_grabacion_hikvision(config, nombre)

        val_ping = pings.get(hid, "1")
        real_status = "Offline" if val_ping == "0" else "Online"

        lista_camaras.append({
            "camara": nombre,
            "ip": h['interfaces'][0]['ip'] if h.get('interfaces') else "0.0.0.0",
            "estado": real_status,
            "estado_grabacion": estado_nas
        })

    # 4. Auditoria de Red (Omada, OPNsense, PBS, PVE, OCS)
    print("[INFO] Consultando infraestructura de red (Omada y OPNsense)...")
    switches_task = omada.obtener_datos_red(config)
    opnsense_data = opnsense.obtener_estado_interfaces(config)
    pbs_data = pbs.obtener_datos_pbs(config)
    pve_data = pve.obtener_datos_pve(config)
    ocs_data = ocs.obtener_datos_ocs(config)

    # 5. Datos Extra desde Zabbix (Trafico, NAS y MPLS)
    print("[INFO] Obteniendo trafico WAN, salud de NAS y estado MPLS desde Zabbix...")
    trafico_wan = zabbix.obtener_trafico_wan(token, config)
    nas_health = zabbix.obtener_ocupacion_nas(token, config)
    estado_mpls = zabbix.obtener_estado_mpls(token, config)

    # 5b. Verificar gateway de internet (192.168.0.1)
    print("[INFO] Verificando gateway de internet (192.168.0.1)...")
    gateway_data = verificar_gateway(config, "192.168.0.1")

    switches = await switches_task

    # Extraer resumen de clientes si hay datos disponibles
    resumen_clientes = {"pc": 0, "wifi": 0, "total": 0}
    if switches and len(switches) > 0 and "resumen_clientes" in switches[0]:
        resumen_clientes = switches[0]["resumen_clientes"]

    # 6. Consolidacion Final
    reporte = {
        "metadatos": {
            "fecha_auditoria": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "responsable": config["responsable"],
            "sitio": config["sitio"]
        },
        "camaras": lista_camaras,
        "estado_alertas": alertas,
        "infraestructura_switches": switches,
        "opnsense": opnsense_data,
        "pbs": pbs_data,
        "pve": pve_data,
        "ocs": ocs_data,
        "trafico_wan": trafico_wan,
        "estado_mpls": estado_mpls,
        "gateway": gateway_data,
        "nas_health": nas_health,
        "resumen_clientes": resumen_clientes,
        "dispositivos_wifi": [
            *[{"nombre": h['name'], "ip": h['interfaces'][0]['ip'], "tipo": "Router WiFi", "estado": "Offline" if pings.get(h['hostid']) == "0" else "Online"} for h in wifi_h],
            *[{"nombre": h['name'], "ip": h['interfaces'][0]['ip'], "tipo": "Huawei CAPS", "estado": "Offline" if pings.get(h['hostid']) == "0" else "Online"} for h in huawei_h]
        ],
        "relojes_personal": [
            {"nombre": h['name'], "ip": h['interfaces'][0]['ip'] if h.get('interfaces') else "S/D", "estado": "Offline" if pings.get(h['hostid']) == "0" else "Online"} for h in relojes_h
        ]
    }

    # Asegurar que el directorio de salida existe
    output_dir = config["output"]["directorio"]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Guardado del reporte
    output_file = os.path.join(output_dir, config["output"]["archivo_reporte"])
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(reporte, f, indent=4, ensure_ascii=False)

    print(f"[{datetime.now()}] [OK] Auditoria finalizada. Reporte generado en '{output_file}'.")
    print(f" -> Camaras: {len(lista_camaras)}")
    print(f" -> Switches: {len(switches)}")
    print(f" -> PVE Nodos: {len(pve_data.get('nodos', []))} | VMs: {len(pve_data.get('vms', []))}")
    print(f" -> Trafico WAN (Rx/Tx): {round(trafico_wan['rx']/1000000, 2)} / {round(trafico_wan['tx']/1000000, 2)} Mbps")
    print(f" -> MPLS: {estado_mpls['estado']} | IP: {estado_mpls['ip']} | Latencia: {estado_mpls['latencia_ms']}ms | Loss: {estado_mpls['loss_pct']}%")
    print(f" -> Gateway: {gateway_data['estado']} | IP: {gateway_data['ip']} | Latencia: {gateway_data.get('latencia_ms', 'N/A')}ms | Speed: {gateway_data.get('velocidad_mbps', 'N/A')} Mbps")
    print(f" -> Clientes Red: PC/Trabajo: {resumen_clientes['pc']} | WiFi: {resumen_clientes['wifi']}")
    print(f" -> Alertas Zabbix: {alertas['alertas_activas']}")
    if not ocs_data.get('error'):
        print(f" -> OCS Inventory: {ocs_data.get('total_equipos', 0)} equipos | Activos: {ocs_data.get('equipos_activos', 0)} | Alertas: {len(ocs_data.get('alertas_disco', [])) + len(ocs_data.get('alertas_ram', [])) + len(ocs_data.get('alertas_antivirus', []))}")
    else:
        print(f" -> OCS Inventory: {ocs_data.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
