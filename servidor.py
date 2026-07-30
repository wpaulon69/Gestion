import http.server
import socketserver
import subprocess
import os
import json
import re
import socket
import time
import requests as req_lib
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from omada_port_lookup import buscar_puerto_por_ip
from modulos import ocs

PORT = 8081
AUDIT_SCRIPT = ['venv/bin/python', 'auditar.py']
REPORT_PATH = '/home/sectorial/gestion/output/reporte_completo.json'
CONFIG_PATH = '/home/sectorial/gestion/config.json'


class HermesHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='/home/sectorial/gestion', **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _run_audit(self):
        """Ejecuta auditar.py y devuelve el JSON del reporte generado."""
        print(f"[{datetime.now()}] [BACKEND] Iniciando auditoria solicitada desde el Dashboard...")
        process = subprocess.run(AUDIT_SCRIPT, capture_output=True, text=True, cwd='/home/sectorial/gestion')

        if process.returncode != 0:
            print(f"[{datetime.now()}] [BACKEND] Error en auditoria: {process.stderr}")
            raise Exception(f'Script failed: {process.stderr}')

        print(f"[{datetime.now()}] [BACKEND] Auditoria completada. Leyendo reporte...")
        with open(REPORT_PATH, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return result

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _load_config(self):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    def do_GET(self):
        if self.path == '/api/run-audit':
            try:
                result = self._run_audit()
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {'error': str(e)})

        elif self.path.startswith('/api/check-watch'):
            try:
                query = parse_qs(urlparse(self.path).query)
                ip_list = query.get('ip')
                if not ip_list or not ip_list[0]:
                    self._send_json(400, {'error': 'IP parameter is required'})
                    return

                target_ip = ip_list[0]
                result = {'ip': target_ip, 'status_code': None, 'is_watch': False, 'web_ok': False, 'message': 'SIN WEB'}

                try:
                    r = req_lib.get(f'http://{target_ip}', timeout=5, allow_redirects=True)
                    if r.status_code == 200:
                        result['web_ok'] = True
                        result['status_code'] = r.status_code
                        if 'csl' in r.text.lower() and 'login' in r.text.lower():
                            result['is_watch'] = True
                            result['message'] = 'Reloj detectado - web responde OK'
                        else:
                            result['is_watch'] = False
                            result['message'] = 'Responde pero no es reloj ZKTeco'
                    else:
                        result['message'] = f'HTTP {r.status_code}'
                        result['status_code'] = r.status_code

                except req_lib.exceptions.ConnectionError:
                    result['message'] = 'Sin conexion puerto 80'
                except req_lib.exceptions.Timeout:
                    result['message'] = 'Timeout (5s)'
                except Exception as e:
                    result['message'] = f'Error: {str(e)}'

                self._send_json(200, result)

            except Exception as e:
                self._send_json(500, {'error': str(e)})

        elif self.path.startswith('/api/buscar-puerto-ip'):
            try:
                query = parse_qs(urlparse(self.path).query)
                ip_list = query.get('ip')
                if not ip_list or not ip_list[0]:
                    self._send_json(400, {'error': 'IP parameter is required'})
                    return

                target_ip = ip_list[0]
                config = self._load_config()
                result = buscar_puerto_por_ip(config, target_ip)
                self._send_json(200, result)

            except Exception as e:
                self._send_json(500, {'error': str(e)})

        elif self.path.startswith('/api/ping-device'):
            try:
                query = parse_qs(urlparse(self.path).query)
                ip_list = query.get('ip')
                if not ip_list or not ip_list[0]:
                    self._send_json(400, {'error': 'IP parameter is required'})
                    return

                target_ip = ip_list[0]
                ip_pattern = r'^([0-9]{1,3}\.){3}[0-9]{1,3}$'
                if not re.match(ip_pattern, target_ip):
                    self._send_json(400, {'error': 'Invalid IP address'})
                    return

                ports_to_try = [22, 80, 443, 8443, 23]
                online = False
                best_rtt = None
                reachable_port = None

                for port in ports_to_try:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        t_start = time.time()
                        result = sock.connect_ex((target_ip, port))
                        t_end = time.time()
                        sock.close()
                        if result == 0:
                            online = True
                            rtt_ms = round((t_end - t_start) * 1000, 1)
                            if best_rtt is None or rtt_ms < best_rtt:
                                best_rtt = rtt_ms
                                reachable_port = port
                    except Exception:
                        continue

                avg_rtt = str(best_rtt) + 'ms' if best_rtt is not None else 'N/A'

                self._send_json(200, {
                    'ip': target_ip,
                    'online': online,
                    'loss': '0%' if online else '100%',
                    'avg_rtt': avg_rtt,
                    'port': reachable_port
                })

            except Exception as e:
                self._send_json(500, {'error': str(e)})

        elif self.path.startswith('/api/ocs-summary'):
            try:
                config = self._load_config()
                result = ocs.obtener_datos_ocs(config)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {'error': str(e)})

        elif self.path.startswith('/api/ocs-search'):
            try:
                query = parse_qs(urlparse(self.path).query)
                q = query.get('q', [''])[0]
                tipo = query.get('tipo', ['hostname'])[0]
                if not q:
                    self._send_json(400, {'error': 'q parameter is required'})
                    return
                config = self._load_config()
                result = ocs.buscar_equipos_ocs(config, q, tipo)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {'error': str(e)})

        elif self.path.startswith('/api/unified-search'):
            try:
                query = parse_qs(urlparse(self.path).query)
                q = query.get('q', [''])[0]
                if not q:
                    self._send_json(400, {'error': 'q parameter is required'})
                    return
                config = self._load_config()
                result = self._unified_search(config, q)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {'error': str(e)})

        elif self.path.startswith('/api/ocs-alerts'):
            try:
                config = self._load_config()
                data = ocs.obtener_datos_ocs(config)
                if data.get('error'):
                    self._send_json(500, data)
                    return
                alerts = {
                    'disco_lleno': data.get('alertas_disco', []),
                    'ram_baja': data.get('alertas_ram', []),
                    'antiguedad': data.get('alertas_antiguedad', []),
                    'sin_antivirus': data.get('alertas_antivirus', []),
                    'sin_updates': data.get('alertas_updates', [])
                }
                self._send_json(200, alerts)
            except Exception as e:
                self._send_json(500, {'error': str(e)})

        elif self.path == '/api/report':
            try:
                with open(REPORT_PATH, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                self._send_json(200, report_data)
            except FileNotFoundError:
                self._send_json(404, {'error': 'Report file not found'})
            except json.JSONDecodeError:
                self._send_json(500, {'error': 'Error decoding report JSON'})
            except Exception as e:
                self._send_json(500, {'error': str(e)})
        elif self.path.startswith('/api/ocs-device'):
            try:
                query = parse_qs(urlparse(self.path).query)
                hostname = query.get('hostname', [''])[0]
                ip_addr = query.get('ip', [''])[0]
                search_term = hostname or ip_addr
                if not search_term:
                    self._send_json(400, {'error': 'hostname or ip parameter is required'})
                    return
                config = self._load_config()
                tipo_busqueda = 'ip' if ip_addr else 'hostname'
                result = ocs.buscar_equipos_ocs(config, search_term, tipo_busqueda)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {'error': str(e)})

        else:
            # Servir archivos estaticos del dashboard
            super().do_GET()

    def _unified_search(self, config, query):
        """Búsqueda unificada: busca en OCS y enriquece con Omada si hay IP."""
        import asyncio
        import re
        ip_pattern = r'^([0-9]{1,3}\.){3}[0-9]{1,3}$'
        is_ip = bool(re.match(ip_pattern, query))
        
        # 2. Buscar en OCS
        # Si es IP, buscar por IP; si no, buscar por hostname
        tipo_busqueda = 'ip' if is_ip else 'hostname'
        ocs_result = ocs.buscar_equipos_ocs(config, query, tipo_busqueda)
        
        unified = {
            'query': query,
            'is_ip': is_ip,
            'ocs': ocs_result,
            'omada': None,
            'enriched': []
        }
        
        # 3. Si OCS encontró resultados, enriquecer cada uno con Omada
        if isinstance(ocs_result, list) and len(ocs_result) > 0:
            for device in ocs_result:
                device_ip = device.get('ip', '')
                enriched_device = dict(device)
                
                if device_ip and device_ip != '0.0.0.0':
                    # Buscar en Omada por la IP del dispositivo
                    try:
                        omada_result = asyncio.run(self._buscar_omada_async(config, device_ip))
                        enriched_device['omada'] = omada_result
                    except Exception as e:
                        enriched_device['omada'] = {'error': str(e)}
                else:
                    enriched_device['omada'] = {'error': 'Sin IP válida para buscar en Omada'}
                
                unified['enriched'].append(enriched_device)
        
        # 4. Si no hay resultados en OCS pero es una IP, buscar directamente en Omada
        elif is_ip:
            try:
                omada_result = asyncio.run(self._buscar_omada_async(config, query))
                unified['omada'] = omada_result
                if 'error' not in omada_result:
                    unified['enriched'].append({
                        'ip': query,
                        'source': 'omada_only',
                        'omada': omada_result
                    })
            except Exception as e:
                unified['omada'] = {'error': str(e)}
        
        return unified

    async def _buscar_omada_async(self, config, target_ip):
        """Wrapper async para buscar en Omada."""
        from omada_port_lookup import _buscar
        return await _buscar(config, target_ip)

    def do_POST(self):
        if self.path == '/api/run-audit':
            try:
                result = self._run_audit()
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {'error': str(e)})
        else:
            self._send_json(404, {'error': 'Not Found'})


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
    httpd = ThreadedHTTPServer(('0.0.0.0', PORT), HermesHandler)
    print(f"[{datetime.now()}] [BACKEND] Serving on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"[{datetime.now()}] [BACKEND] Shutting down server...")
        httpd.shutdown()
        print(f"[{datetime.now()}] [BACKEND] Server stopped.")

if __name__ == "__main__":
    run_server()
