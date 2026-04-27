import asyncio
import aiohttp
from tplink_omada_client import OmadaClient

# --- CONFIGURACIÓN ---
IP_CONTROLADOR = '10.175.7.3' 
USER = 'Sectorial'
PASS = 'Nokia.3189'
SITE_NAME = 'SamcoEsperanza'

async def run():
    url = f"https://{IP_CONTROLADOR}:8043"
    async with OmadaClient(url, USER, PASS, verify_ssl=False) as client:
        try:
            await client.login()
            sites = await client.get_sites()
            target_site = next((s for s in sites if s.name == SITE_NAME), None)
            
            site_client = await client.get_site_client(target_site)
            devices = await site_client.get_devices()

            print(f"\nESTADO REAL DE RED - {SITE_NAME}")
            print("=" * 115)
            print(f"{'DISPOSITIVO':<35} | {'ESTADO':<12} | {'CLIENTES':<10} | {'UPTIME':<20} | {'CPU/MEM'}")
            print("-" * 115)

            for dev in devices:
                d = dev.raw_data
                nombre = d.get('name', 'S/N')
                
                # Usamos los nombres exactos que vimos en el diagnóstico
                clientes = d.get('clientNum', 0)
                uptime_txt = d.get('uptime', '0h')
                cpu = d.get('cpuUtil', 0)
                mem = d.get('memUtil', 0)
                
                status_raw = d.get('status', 0)
                if status_raw == 14:
                    estado = "✅ CONECTADO"
                elif status_raw == 22:
                    estado = "⏳ ADOPTANDO"
                else:
                    estado = f"❌ DOWN ({status_raw})"

                # Formateamos la salida
                rendimiento = f"C:{cpu}% M:{mem}%"
                print(f"{nombre:<35} | {estado:<12} | {clientes:<10} | {uptime_txt:<20} | {rendimiento}")
            
            print("=" * 115)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())