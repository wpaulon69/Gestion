import requests
import urllib3

# Deshabilitar advertencias de certificados no válidos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_version_opnsense(config):
    """Obtiene la versión de OPNsense desde la API."""
    url = f"https://{config['opnsense']['ip']}/api/core/firmware/status"
    try:
        response = requests.get(
            url,
            auth=(config['opnsense']['api_key'], config['opnsense']['api_secret']),
            verify=False,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            # OPNsense devuelve version en product.CORE_VERSION o product.product_version
            product = data.get('product', {})
            version = product.get('CORE_VERSION') or product.get('product_version') or product.get('version') or 'desconocida'
            return {"version": version}
        return {"version": "error HTTP " + str(response.status_code)}
    except Exception as e:
        return {"version": "error: " + str(e)}

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
            # Verificar que la respuesta sea JSON antes de parsear
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    data = response.json()
                except ValueError:
                    return {"error": "Respuesta no es JSON válido"}
            else:
                # Si no es JSON, intentar interpretar como texto o devolver error
                return {"error": f"Respuesta inesperada (content-type: {content_type}): {response.text[:200]}"}

            # La API de OPNsense devuelve un objeto con 'rows' que contiene las interfaces
            interfaces_limpias = []
            if 'rows' in data:
                for info in data['rows']:
                    if info.get('enabled'):
                        interfaces_limpias.append({
                            "id": info.get('device', 'unknown'),
                            "nombre": info.get('description', info.get('device', 'unknown')),
                            "status": info.get('status', 'unknown'),
                            "ip": info.get('addr4', 'N/A'),
                            "mac": info.get('macaddr', 'N/A')
                        })
            else:
                # Formato alternativo: intentar el formato antiguo por compatibilidad
                for key, info in data.items():
                    if isinstance(info, dict) and info.get('enabled'):
                        interfaces_limpias.append({
                            "id": key,
                            "nombre": info.get('description', key),
                            "status": info.get('status', 'unknown'),
                            "ip": info.get('addr4', 'N/A'),
                            "mac": info.get('macaddr', 'N/A')
                        })
            return {"interfaces": interfaces_limpias}
        else:
            return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}