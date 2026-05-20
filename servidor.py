import http.server
import socketserver
import subprocess
import os
import json
import requests as req_lib
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from omada_port_lookup import buscar_puerto_por_ip

PORT = 8081
AUDIT_SCRIPT = ['venv/bin/python', 'auditar.py']
REPORT_PATH = '/home/sectorial/gestion/output/reporte_completo.json'

class HermesHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='/home/sectorial/gestion', **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

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
                    result['message'] = 'Sin conexión puerto 80'
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
                config = json.load(open('/home/sectorial/gestion/config.json'))
                result = buscar_puerto_por_ip(config, target_ip)
                self._send_json(200, result)

            except Exception as e:
                self._send_json(500, {'error': str(e)})
        
        else:
            # Servir archivos estáticos del dashboard
            super().do_GET()

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
