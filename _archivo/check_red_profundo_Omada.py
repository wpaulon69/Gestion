import asyncio
import json
import requests
import urllib3
from datetime import datetime
from tplink_omada_client import OmadaClient

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
OMADA_IP, OMADA_USER, OMADA_PASS = '10.175.7.3', 'Sectorial', 'Nokia.3189'
SITE_NAME = 'SamcoEsperanza'

async def get_omada_deep_analysis():
    try:
        url = f"https://{OMADA_IP}:8043"
        async with OmadaClient(url, OMADA_USER, OMADA_PASS, verify_ssl=False) as client:
            await client.login()
            sites = await client.get_sites()
            target_site = next((s for s in sites if s.name == SITE_NAME), None)
            site_client = await client.get_site_client(target_site)
            
            # 1. Obtener todos los dispositivos (Switches/APs)
            devices = await site_client.get_devices()
            
            analisis_profundo = []
            
            for dev in devices:
                d = dev.raw_data
                device_id = d.get('id')
                
                # 2. Extraer configuración detallada de puertos (si es un switch)
                puertos_info = []
                if d.get('type') in [1, 'switch']:
                    # Intentamos obtener el estado de los puertos
                    ports = d.get('portStats', [])
                    for p in ports:
                        puertos_info.append({
                            "puerto": p.get('port'),
                            "nombre_puerto": p.get('name'),
                            "estado": "UP" if p.get('status') == 1 else "DOWN",
                            "velocidad": f"{p.get('speed')} Mbps",
                            "poe": p.get('poeActive', False),
                            "rx": f"{round(p.get('rxRate', 0) / 1024, 2)} MBs",
                            "tx": f"{round(p.get('txRate', 0) / 1024, 2)} MBs"
                        })

                # 3. Consolidar ficha técnica del equipo
                analisis_profundo.append({
                    "info_basica": {
                        "nombre": d.get('name'),
                        "modelo": d.get('model'),
                        "mac": d.get('mac'),
                        "ip": d.get('ip'),
                        "version_firmware": d.get('firmwareVersion'),
                        "necesita_upgrade": d.get('needUpgrade', False)
                    },
                    "rendimiento": {
                        "uptime": d.get('uptime'),
                        "clientes_actuales": d.get('clientNum', 0),
                        "uso_cpu": f"{d.get('cpuUtil', 0)}%",
                        "uso_memoria": f"{d.get('memUtil', 0)}%"
                    },
                    "configuracion_puertos": puertos_info,
                    "alertas_dispositivo": d.get('statusCategory', 0) # 1=Normal, otros=Error/Adopción
                })
                
            return analisis_profundo
    except Exception as e:
        return {"error": str(e)}

async def main():
    print(f"[{datetime.now()}] Iniciando escaneo profundo de Omada...")
    data = await get_omada_deep_analysis()
    
    with open("auditoria_red_omada.json", "w") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Auditoría completada. Datos guardados en 'auditoria_red_omada.json'")

if __name__ == "__main__":
    asyncio.run(main())