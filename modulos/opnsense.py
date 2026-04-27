import requests
import urllib3

# Deshabilitar advertencias de certificados no válidos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_estado_interfaces(config):
    """Obtiene el resumen de interfaces desde la API de OPNsense."""
    url = f"https://{config['opnsense']['ip']}/api/interfaces/overview/interfacesInfo"
    try:
        response = requests.get(
            url, 
            auth=(config['opnsense']['api_key'], config['opnsense']['api_secret']), 
            verify=False, 
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            # Simplificamos la respuesta para el dashboard
            interfaces_limpias = []
            for key, info in data.items():
                if info.get('enabled'):
                    interfaces_limpias.append({
                        "id": key,
                        "nombre": info.get('description', key),
                        "status": info.get('status', 'unknown'),
                        "ip": info.get('addr4', 'N/A'),
                        "mac": info.get('macaddr', 'N/A')
                    })
            return {"interfaces": interfaces_limpias}
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}
