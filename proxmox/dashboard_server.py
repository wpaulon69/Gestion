#!/usr/bin/env python3
"""
Servidor HTTP simple para el dashboard.
Ejecuta la auditoría bajo demanda y sirve el HTML.
"""
import http.server
import json
import os
import socketserver
from datetime import datetime
from functools import partial

PORT = 8080
REPORT_FILE = "output/reporte_completo.json"
DASHBOARD_FILE = "dashboard.html"

class AuditarHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/" + DASHBOARD_FILE
        elif self.path == "/run" or self.path == "/api/run-audit":
            self.run_auditoria()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "timestamp": datetime.now().isoformat()}).encode())
            return
        elif self.path == "/data":
            self.send_json_report()
            return
        return super().do_GET()
    
    def do_POST(self):
        if self.path == "/api/run-audit":
            self.run_auditoria()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "timestamp": datetime.now().isoformat()}).encode())
            return
        return super().do_GET()
    
    def run_auditoria(self):
        """Ejecuta la auditoría."""
        import subprocess
        try:
            subprocess.run(["/opt/auditar/gestion_env/bin/python", "auditar.py"], check=True, capture_output=True, cwd="/opt/auditar")
        except Exception as e:
            print(f"Error: {e}")
    
    def send_json_report(self):
        """Envía el reporte JSON."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            with open(REPORT_FILE) as f:
                self.wfile.write(f.read().encode())
        except FileNotFoundError:
            self.wfile.write(b"{}")
    
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

def main():
    print(f"[INFO] Dashboard server en http://0.0.0.0:{PORT}")
    print(f"[INFO] Endpoints:")
    print(f"  - http://localhost:{PORT}/           Dashboard")
    print(f"  - http://localhost:{PORT}/run         Ejecutar auditoría")
    print(f"  - http://localhost:{PORT}/data         JSON directo")
    
    with socketserver.TCPServer(("", PORT), AuditarHandler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    main()