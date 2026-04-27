import asyncio
import json
import os
from tplink_omada_client import OmadaClient

async def check_clients():
    try:
        if not os.path.exists("config.json"):
            print("config.json not found in CWD")
            return
            
        with open("config.json", "r", encoding='utf-8') as f:
            config = json.load(f)
            
        url = f"https://{config['omada']['ip']}:{config['omada']['port']}"
        async with OmadaClient(url, config['omada']['user'], config['omada']['password'], verify_ssl=False) as client:
            await client.login()
            sites = await client.get_sites()
            target_site = next((s for s in sites if s.name == config['omada']['site']), None)
            
            if not target_site:
                print("Site not found")
                return
                
            print(f"Checking site: {target_site.name}")
            site_client = await client.get_site_client(target_site)
            
            # Intentar obtener clientes
            try:
                # get_clients() es el método estándar en esta librería para ver clientes conectados
                clients = await site_client.get_clients()
                print(f"Total clients found: {len(clients)}")
                
                pc_count = 0
                wifi_count = 0
                other = 0
                
                for c in clients:
                    # La librería provee el objeto Client con atributo 'ip'
                    ip = getattr(c, 'ip', "0.0.0.0") or "0.0.0.0"
                    if ip.startswith("10."):
                        pc_count += 1
                    elif ip.startswith("170.") or ip.startswith("192."):
                        wifi_count += 1
                    else:
                        other += 1
                        
                print(f"RESULT_PC: {pc_count}")
                print(f"RESULT_WIFI: {wifi_count}")
                print(f"RESULT_OTHER: {other}")
                
            except Exception as e:
                print(f"Error getting clients: {e}")
                print("Methods in site_client:", [m for m in dir(site_client) if not m.startswith('_')])

    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    asyncio.run(check_clients())
