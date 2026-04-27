import asyncio
import json
import requests
import urllib3
from datetime import datetime
from tplink_omada_client import OmadaClient

# Deshabilitar advertencias de seguridad
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
OMADA_IP, OMADA_USER, OMADA_PASS = '10.175.7.3', 'Sectorial', 'Nokia.3189'
SITE_NAME = 'SamcoEsperanza'

OPN_IP = "10.175.6.203"
OPN_KEY = "v4f9BWOZmEIOHFskhnAfXES6tBASBnloD6htMa98cWNADvyvbiuxAe3CREVvpO7FU1oheTAuSsGPKBX4"
OPN_SEC = "z8kfgfRhtCJYU4FXn993+ruklqnVpkehYYNa4g5EnWqM1+oiG3naafDHHDA8KnDqt+luwj23PdFz1m+W"

ZABBIX_URL = "http://10.175.6.12/zabbix/api_jsonrpc.php" 
ZAB_USER = "APIGrafana"
ZAB_PASS = "gestion1234"

async def get_omada_deep_data():
    """Extrae auditoría completa: Firmware, MACs, Modelos y Rendimiento"""
    try:
        url = f"https://{OMADA_IP}:8043"
        async with OmadaClient(url, OMADA_USER, OMADA_PASS, verify_ssl=False) as client:
            await client.login()
            sites = await client.get_sites()
            target_site = next((s for s in sites if s.name == SITE_NAME), None)
            site_client = await client.get_site_client(target_site)
            devices = await site_client.get_devices()
            
            # Mapeo de datos detallados según auditoria_red_omada.json
            return [{
                "nombre": d.raw_data.get('name', 'S/N'),
                "modelo": d.raw_data.get('model'),
                "mac": d.raw_data.get('mac'),
                "ip": d.raw_data.get('ip', 'N/A'),
                "firmware": d.raw_data.get('firmwareVersion'),
                "clientes": int(d.raw_data.get('clientNum', 0)),
                "uptime": d.raw_data.get('uptime', '0h'),
                "cpu": f"{d.raw_data.get('cpuUtil', 0)}%",
                "mem": f"{d.raw_data.get('memUtil', 0)}%",
                "status": "OK" if d.status == 14 else "DOWN",
                "upgrade_disponible": d.raw_data.get('needUpgrade', False)
            } for d in devices]
    except Exception as e:
        return {"error": f"Omada Error: {str(e)}"}

def get_opnsense_detailed_data():
    """Extrae configuración de interfaces y rutas según check_opnsense.py"""
    try:
        url = f"https://{OPN_IP}/api/interfaces/overview/interfacesInfo"
        r = requests.get(url, auth=(OPN_KEY, OPN_SEC), verify=False, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # Filtramos para quedarnos con lo esencial: WAN, LAN y VLAN 30
            interes = ['wan', 'lan', 'opt2']
            resumen = {}
            for k, v in data.items():
                if k.lower() in interes:
                    resumen[v.get('description', k)] = {
                        "interface": v.get('device'),
                        "status": v.get('status'),
                        "mac": v.get('macaddr'),
                        "ipv4": v.get('ipv4', []),
                        "routes": v.get('routes', []),
                        "mtu": v.get('mtu')
                    }
            return resumen
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": f"OPNsense Error: {str(e)}"}

def get_zabbix_status():
    """Consulta de incidentes activos para correlación"""
    try:
        payload = {"jsonrpc": "2.0", "method": "user.login", "params": {"username": ZAB_USER, "password": ZAB_PASS}, "id": 1}
        token = requests.post(ZABBIX_URL, json=payload, timeout=5).json().get("result")
        if not token: return {"error": "Zabbix Auth Failed"}

        payload_prob = {"jsonrpc": "2.0", "method": "problem.get", "params": {"recent": True, "limit": 10}, "auth": token, "id": 2}
        problems = requests.post(ZABBIX_URL, json=payload_prob).json().get("result", [])
        return {
            "alertas_activas": len(problems),
            "detalle": [{"evento": p['name'], "severidad": p['severity']} for p in problems]
        }
    except:
        return {"error": "Zabbix Offline"}

async def main():
    print(f"[{datetime.now()}] 🔍 Iniciando auditoría profunda de red...")
    
    # Recolección de datos
    omada_audit = await get_omada_deep_data()
    opn_audit = get_opnsense_detailed_data()
    zab_audit = get_zabbix_status()
    
    reporte_total = {
        "metadatos": {
            "fecha_auditoria": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "responsable": "Gestión de Red SAMCo"
        },
        "infraestructura_switches": omada_audit,
        "configuracion_perimetro": opn_audit,
        "estado_alertas": zab_audit
    }

    with open("config_red_total.json", "w") as f:
        json.dump(reporte_total, f, indent=4)
    
    print(f"[{datetime.now()}] ✅ Auditoría finalizada. Archivo 'config_red_total.json' actualizado.")

if __name__ == "__main__":
    asyncio.run(main())