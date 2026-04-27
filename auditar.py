import asyncio
import json
import os
from datetime import datetime
from modulos import zabbix, omada, opnsense, nas_camaras, pbs, pve

def cargar_configuracion():
    with open("config.json", "r", encoding='utf-8') as f:
        return json.load(f)

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
    # Obtenemos todos los IDs de hosts para consultar sus pings en una sola llamada
    todas_entidades = cams_h + wifi_h + huawei_h + relojes_h
    host_ids = [h['hostid'] for h in todas_entidades]
    pings = zabbix.obtener_valores_ping(token, config, host_ids)

    print(f"[INFO] Verificando grabacion en NAS para {len(cams_h)} camaras...")
    lista_camaras = []
    for h in cams_h:
        nombre = h['name']
        hid = h['hostid']
        estado_nas = nas_camaras.verificar_grabacion_hikvision(config, nombre)
        
        # Prioridad 1: Valor de ping real (1=Online, 0=Offline)
        val_ping = pings.get(hid, "1") # Default 1 si no hay item
        if val_ping == "0":
            real_status = "Offline"
        else:
            real_status = "Online" if h['status'] == "0" else "Offline"

        lista_camaras.append({
            "camara": nombre,
            "ip": h['interfaces'][0]['ip'] if h.get('interfaces') else "0.0.0.0",
            "estado": real_status,
            "estado_grabacion": estado_nas
        })

    # 4. Auditoria de Red (Omada y OPNsense)
    print("[INFO] Consultando infraestructura de red (Omada y OPNsense)...")
    switches_task = omada.obtener_datos_red(config)
    opnsense_data = opnsense.obtener_estado_interfaces(config)
    pbs_data = pbs.obtener_datos_pbs(config)
    pve_data = pve.obtener_datos_pve(config)
    
    # 5. Datos Extra desde Zabbix (Tráfico y NAS)
    print("[INFO] Obteniendo tráfico WAN y salud de NAS desde Zabbix...")
    trafico_wan = zabbix.obtener_trafico_wan(token, config)
    nas_health = zabbix.obtener_ocupacion_nas(token, config)
    
    switches = await switches_task
    
    # Extraer resumen de clientes si hay datos disponibles
    resumen_clientes = {"pc": 0, "wifi": 0, "total": 0}
    if switches and len(switches) > 0 and "resumen_clientes" in switches[0]:
        resumen_clientes = switches[0]["resumen_clientes"]

    # 5. Consolidacion Final
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
        "trafico_wan": trafico_wan,
        "nas_health": nas_health,
        "resumen_clientes": resumen_clientes,
        "dispositivos_wifi": [
            *[{"nombre": h['name'], "ip": h['interfaces'][0]['ip'], "tipo": "Router WiFi", "estado": "Offline" if pings.get(h['hostid']) == "0" or h['status']!="0" else "Online"} for h in wifi_h],
            *[{"nombre": h['name'], "ip": h['interfaces'][0]['ip'], "tipo": "Huawei CAPS", "estado": "Offline" if pings.get(h['hostid']) == "0" or h['status']!="0" else "Online"} for h in huawei_h]
        ],
        "relojes_personal": [
            {"nombre": h['name'], "ip": h['interfaces'][0]['ip'] if h.get('interfaces') else "S/D", "estado": "Offline" if pings.get(h['hostid']) == "0" or h['status']!="0" else "Online"} for h in relojes_h
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
    print(f"   -> Camaras: {len(lista_camaras)}")
    print(f"   -> Switches: {len(switches)}")
    print(f"   -> PVE Nodos: {len(pve_data.get('nodos', []))} | VMs: {len(pve_data.get('vms', []))}")
    print(f"   -> Tráfico WAN (Rx/Tx): {round(trafico_wan['rx']/1000000, 2)} / {round(trafico_wan['tx']/1000000, 2)} Mbps")
    print(f"   -> Clientes Red: PC/Trabajo: {resumen_clientes['pc']} | WiFi: {resumen_clientes['wifi']}")
    print(f"   -> Alertas Zabbix: {alertas['alertas_activas']}")

if __name__ == "__main__":
    asyncio.run(main())
