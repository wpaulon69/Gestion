import http.server
import socketserver
import subprocess
import os
import json
import sys
from datetime import datetime

PORT = 8081
AUDIT_SCRIPT = "./venv/bin/python auditar.py"

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/open-folder'):
            try:
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                folder_path = query.get('path', [None])[0]
                
                if folder_path:
                    print(f"[{datetime.now()}] [BACKEND] Solicitada apertura de carpeta: {folder_path}")
                    import platform
                    import shutil
                    if platform.system() == 'Windows':
                        os.startfile(folder_path)
                    else:
                        opener = shutil.which('xdg-open') or shutil.which('nautilus') or shutil.which('thunar') or shutil.which('pcmanfm')
                        if opener:
                            subprocess.Popen([opener, folder_path])
                        else:
                            print(f"[{datetime.now()}] [BACKEND] No se encontró gestor de archivos para abrir: {folder_path}")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode())
                else:
                    self.send_response(400)
                    self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif self.path.startswith('/api/buscar-puerto-ip'):
            try:
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                ip_list = query.get('ip')
                if not ip_list or not ip_list[0]:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'IP parameter is required'}).encode())
                    return
                
                target_ip = ip_list[0]
                
                # Run the omada_port_lookup script
                process = subprocess.run(
                    ['/home/sectorial/gestion/venv/bin/python', '/home/sectorial/gestion/omada_port_lookup.py', target_ip],
                    capture_output=True,
                    text=True,
                    cwd='/home/sectorial/gestion'
                )
                
                if process.returncode != 0:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': f'Script failed: {process.stderr}'}).encode())
                    return
                
                # The script outputs JSON to stdout
                try:
                    result = json.loads(process.stdout)
                except json.JSONDecodeError:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid JSON output from script'}).encode())
                    return
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            # Comportamiento normal para archivos estáticos
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/run-audit':
            try:
                print(f"[{datetime.now()}] [BACKEND] Iniciando auditoría solicitada desde el Dashboard...")
                
                # Ejecutar el script de auditoría
                process = subprocess.run(AUDIT_SCRIPT, shell=True, capture_output=True, text=True)
                
                if process.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        "status": "success", 
                        "message": "Auditoría completada exitosamente.",
                        "output": process.stdout
                    }
                    self.wfile.write(json.dumps(response).encode())
                    print(f"[{datetime.now()}] [BACKEND] Auditoría terminada con éxito.")
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        "status": "error", 
                        "message": "Error al ejecutar el script de auditoría.",
                        "error": process.stderr
                    }
                    self.wfile.write(json.dumps(response).encode())
                    print(f"[{datetime.now()}] [BACKEND] ERROR en la auditoría: {process.stderr}")
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif self.path == '/api/pregunta':
            # Endpoint para el asistente IA
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(post_data) if post_data else {}
                
                pregunta = data.get('pregunta', '')
                
                if not pregunta:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'La pregunta es requerida'}).encode())
                    return
                
                print(f"[{datetime.now()}] [BACKEND] Pregunta recibida: {pregunta[:100]}...")
                
                # Importar y ejecutar el módulo de IA
                sys.path.insert(0, '/home/sectorial/gestion')
                from ia_asistente import responder_pregunta
                
                resultado = responder_pregunta(pregunta)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resultado, ensure_ascii=False).encode())
                
                print(f"[{datetime.now()}] [BACKEND] Respuesta generada exitosamente")
                
            except Exception as e:
                print(f"[{datetime.now()}] [BACKEND] ERROR en pregunta IA: {e}")
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        elif self.path.startswith('/api/buscar-puerto-ip'):
            try:
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                ip_list = query.get('ip')
                if not ip_list or not ip_list[0]:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'IP parameter is required'}).encode())
                    return
                
                target_ip = ip_list[0]
                
                # Run the omada_port_lookup script
                process = subprocess.run(
                    ['/home/sectorial/gestion/venv/bin/python', '/home/sectorial/gestion/omada_port_lookup.py', target_ip],
                    capture_output=True,
                    text=True,
                    cwd='/home/sectorial/gestion'
                )
                
                if process.returncode != 0:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': f'Script failed: {process.stderr}'}).encode())
                    return
                
                # The script outputs JSON to stdout
                try:
                    result = json.loads(process.stdout)
                except json.JSONDecodeError:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid JSON output from script'}).encode())
                    return
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
