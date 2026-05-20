import asyncio
import json
from tplink_omada_client import OmadaClient


def buscar_puerto_por_ip(config, target_ip):
    """Busca en Omada el switch y puerto donde está conectada una IP."""
    result = asyncio.run(_buscar(config, target_ip))
    return result


async def _buscar(config, target_ip):
    url = f"https://{config['omada']['ip']}:{config['omada']['port']}"
    try:
        async with OmadaClient(url, config['omada']['user'], config['omada']['password'], verify_ssl=False) as client:
            await client.login()
            sites = await client.get_sites()
            site = next((s for s in sites if s.name == config['omada']['site']), None)
            if not site:
                return {"error": f"Site '{config['omada']['site']}' no encontrado"}

            sc = await client.get_site_client(site)

            # Buscar la IP entre los clientes conectados
            async for c in sc.get_connected_clients():
                rd = c.raw_data if hasattr(c, 'raw_data') else {}
                client_ip = rd.get('ip', '') or rd.get('lastIp', '')
                if client_ip == target_ip:
                    return {
                        "switch_name": rd.get("switchName", "N/A"),
                        "switch_mac": rd.get("switchMac", "N/A"),
                        "switch_ip": rd.get("switchIp", rd.get("switchName", "N/A").split("-")[0] if "-" in rd.get("switchName", "") else "N/A"),
                        "switch_model": rd.get("switchModel", "N/A"),
                        "port_number": rd.get("port", "N/A"),
                        "standard_port": rd.get("standardPort", "N/A"),
                        "vlan": rd.get("vid", "N/A"),
                        "vlan_name": rd.get("networkName", "N/A"),
                        "client_mac": rd.get("mac", "N/A"),
                        "client_name": rd.get("name", "N/A"),
                        "client_hostname": rd.get("hostName", rd.get("systemName", "N/A")),
                        "ip": client_ip,
                        "status": "Online" if rd.get("active") else "Offline",
                        "connect_type": "WiFi" if rd.get("wireless") else "Cableado",
                        "uptime": rd.get("uptime", 0),
                        "traffic_down": rd.get("trafficDown", 0),
                        "traffic_up": rd.get("trafficUp", 0),
                    }

            return {"error": f"IP {target_ip} no encontrada entre los clientes Omada"}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import sys
    config = json.load(open('config.json'))
    ip = sys.argv[1] if len(sys.argv) > 1 else "10.175.6.100"
    result = buscar_puerto_por_ip(config, ip)
    print(json.dumps(result, indent=2))
