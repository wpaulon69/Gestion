import asyncio
import json
import os
from tplink_omada_client import OmadaClient

async def check_clients():
    try:
        with open("config.json", "r", encoding='utf-8') as f:
            config = json.load(f)
            
        url = f"https://{config['omada']['ip']}:{config['omada']['port']}"
        async with OmadaClient(url, config['omada']['user'], config['omada']['password'], verify_ssl=False) as client:
            await client.login()
            sites = await client.get_sites()
            target_site = next((s for s in sites if s.name == config['omada']['site']), None)
            site_client = await client.get_site_client(target_site)
            
            try:
                clients = await site_client.get_connected_clients()
                print(f"Total clients: {len(clients)}")
                
                stats = {"pc": 0, "wifi": 0, "other": 0}
                for c in clients:
                    ip = getattr(c, 'ip', '0.0.0.0') or '0.0.0.0'
                    if ip.startswith("10."): stats["pc"] += 1
                    elif ip.startswith("170.") or ip.startswith("192."): stats["wifi"] += 1
                    else: stats["other"] += 1
                
                print(f"STATS: {json.dumps(stats)}")
            except Exception as e:
                print(f"Error: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_clients())
