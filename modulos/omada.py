import asyncio
from tplink_omada_client import OmadaClient

async def obtener_datos_red(config):
    """
    Obtiene auditoría completa de switches de Omada.
    Combina datos básicos y de rendimiento.
    """
    switches_info = []
    try:
        url = f"https://{config['omada']['ip']}:{config['omada']['port']}"
        async with OmadaClient(url, config['omada']['user'], config['omada']['password'], verify_ssl=False) as client:
            await client.login()
            sites = await client.get_sites()
            target_site = next((s for s in sites if s.name == config['omada']['site']), None)
            
            if not target_site:
                return []
                
            site_client = await client.get_site_client(target_site)
            devices = await site_client.get_devices()
            
            # Segmentación de clientes
            resumen_clientes = {"pc": 0, "wifi": 0, "total": 0}
            try:
                # get_connected_clients es un generador asíncrono
                async for c in site_client.get_connected_clients():
                    resumen_clientes["total"] += 1
                    ip = getattr(c, 'ip', '0.0.0.0') or '0.0.0.0'
                    if ip.startswith("10."):
                        resumen_clientes["pc"] += 1
                    elif ip.startswith("170.") or ip.startswith("192."):
                        resumen_clientes["wifi"] += 1
            except Exception as e:
                print(f"⚠️ Aviso: Error al segmentar clientes: {e}")

            for dev in devices:
                d = dev.raw_data
                switches_info.append({
                    "nombre": d.get('name', 'S/N'),
                    "modelo": d.get('model'),
                    "mac": d.get('mac'),
                    "ip": d.get('ip', 'N/A'),
                    "clientes": int(d.get('clientNum', 0)),
                    "cpu": f"{d.get('cpuUtil', 0)}%",
                    "mem": f"{d.get('memUtil', 0)}%",
                    "uptime": d.get('uptime', '0h'),
                    "firmware": d.get('firmwareVersion', 'N/A'),
                    "upgrade_disponible": d.get('needUpgrade', False),
                    "status": "OK" if dev.status == 14 else ("ADOPTANDO" if dev.status == 22 else f"DOWN ({dev.status})"),
                    "resumen_clientes": resumen_clientes # Adjuntamos el resumen al primer dispositivo o globalmente
                })
        return switches_info

    except Exception as e:
        print(f"❌ Error conectando a Omada: {e}")
        return []
