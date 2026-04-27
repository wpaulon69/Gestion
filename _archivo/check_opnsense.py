import requests
import json
import urllib3

# Deshabilitar advertencias de certificados no válidos (común en redes locales)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURACIÓN
OPN_IP = "10.175.6.203" # IP de tu OPNsense según mis registros
API_KEY = "v4f9BWOZmEIOHFskhnAfXES6tBASBnloD6htMa98cWNADvyvbiuxAe3CREVvpO7FU1oheTAuSsGPKBX4"
API_SECRET = "z8kfgfRhtCJYU4FXn993+ruklqnVpkehYYNa4g5EnWqM1+oiG3naafDHHDA8KnDqt+luwj23PdFz1m+W"
OUTPUT_FILE = "estado_opnsense.json"

def obtener_estado_interfaces():
    url = f"https://{OPN_IP}/api/interfaces/overview/interfacesInfo"
    response = requests.get(url, auth=(API_KEY, API_SECRET), verify=False)
    
    if response.status_code == 200:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(response.json(), f, indent=4)
        print(f"Éxito: Datos guardados en {OUTPUT_FILE}")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    obtener_estado_interfaces()