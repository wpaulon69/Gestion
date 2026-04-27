import asyncio
import json
import requests
import urllib3
from datetime import datetime
from tplink_omada_client import OmadaClient

# Deshabilitar advertencias de certificados (para OPNsense local)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN OMADA ---
OMADA_IP = '10.175.7.3'
OMADA_USER = 'Sectorial'
OMADA_PASS = 'Nokia.3189'
SITE_NAME = 'SamcoEsperanza'

# --- CONFIGURACIÓN OPNSENSE ---
OPN_IP = "10.175.6.203"
API_KEY = "v4f9BWOZmEIOHFskhnAfXES6tBASBnloD6htMa98cWNADvyvbiuxAe3CREVvpO7FU1oheTAuSsGPKBX4"
API_SECRET = "z8kfgfRhtCJYU4FXn993+ruklqnVpkehYYNa4g5EnWqM1+oiG3naafDHHDA8KnDqt+luwj23PdFz1m+W"

async def get_omada_data():
    try:
        url = f"https://{OMADA_IP}:8043"
        async with OmadaClient(url, OMADA_USER, OMADA_PASS, verify_ssl=False) as client:
            await client.login()
            sites = await client.get_sites()
            target_site = next((s for s in sites if s.name == SITE_NAME), None)
            site_client = await client.get_site_client(target_site)
            devices = await site_client.get_devices()
            
            return [{
                "nombre": d.raw_data.get('name', 'S/N'),
                "ip": d.raw_data.get('ip', 'N/A'),
                "clientes": int(d.raw_data.get('clientNum', 0)),
                "uptime": d.raw_data.get('uptime', '0h'),
                "cpu": f"{d.raw_data.get('cpuUtil', 0)}%",
                "status": "OK" if d.status == 14 else "DOWN"
            } for d in devices]
    except Exception as e:
        return {"error": f"Omada offline: {str(e)}"}

def get_opnsense_data():
    try:
        url = f"https://{OPN_IP}/api/interfaces/overview/interfacesInfo"
        response = requests.get(url, auth=(API_KEY, API_SECRET), verify=False, timeout=10)
        return response.json() if response.status_code == 200 else {"error": response.status_code}
    except Exception as e:
        return {"error": f"OPNsense offline: {str(e)}"}

async def main():
    print(f"[{datetime.now()}] Iniciando recolección unificada...")
    
    # Ejecutamos ambos en paralelo
    omada_info = await get_omada_data()
    opn_info = get_opnsense_data()

    reporte_final = {
        "metadatos": {
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "sitio": SITE_NAME
        },
        "infraestructura_omada": omada_info,
        "perimetro_opnsense": opn_info
    }

    with open("estado_sistema.json", "w") as f:
        json.dump(reporte_final, f, indent=4)
    
    print("✅ reporte_sistema.json generado con éxito.")

if __name__ == "__main__":
    asyncio.run(main())