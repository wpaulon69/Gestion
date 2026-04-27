import http.server
import socketserver
import subprocess
import os
import json
from datetime import datetime

PORT = 8081
AUDIT_SCRIPT = r".\gestion_env\Scripts\python.exe auditar.py"

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/open-folder'):
            try:
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                folder_path = query.get('path', [None])[0]
                
                if folder_path:
                    print(f"[{datetime.now()}] [BACKEND] Solicitada apertura de carpeta: {folder_path}")
                    # En Windows, os.startfile abre el explorador o aplicación por defecto
                    os.startfile(folder_path)
                    
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
        else:
            # Comportamiento normal para archivos estáticos
            super().do_GET()

    def do_POST(self):

        if self.path == '/api/run-audit':
            try:
                print(f"[{datetime.now()}] [BACKEND] Iniciando auditoría solicitada desde el Dashboard...")
                
                # Ejecutar el script de auditoría
                # shell=True es necesario para expandir rutas en Windows si usamos comandos complejos
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
        else:
            self.send_response(404)
            self.end_headers()

    def end_headers(self):
        # Permite CORS para desarrollo local si fuera necesario
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

if __name__ == "__main__":
    # Cambiamos al directorio del script para que las rutas relativas funcionen
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"--- SERVIDOR DASHBOARD INICIADO ---")
        print(f"URL: http://localhost:{PORT}/dashboard.html")
        print(f"Presiona Ctrl+C para detener.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")
