#!/usr/bin/env python3
"""
Actualiza la planilla 'Mapa Switchs' en Google Drive añadiendo la hoja 'Servidores'.
Ejecutar en máquina con navegador (para OAuth interactivo).
"""

import json
import os
import csv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuración
CLIENT_SECRET_PATH = '/home/sectorial/google_client_secret.json'
TOKEN_PATH = '/home/sectorial/.config/gdrive/token.json'
FOLDER_ID = '1bRC7Ax5RBCzgcWVqoc9fEFNR1Ur2fhv6'  # Carpeta "Ing-Hermes"
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

# Datos de la hoja Servidores (desde mapa_switchs_servidores.csv)
SERVIDORES_DATA = [
    ["Puerto", "Dispositivo", "IP", "Tipo", "LAG", "Observaciones", "Perfil"],
    [1, "hpdl360 (Proxmox)", "10.175.6.20", "Hypervisor", "LAG-SRV-HPDL360", "NIC 1 - bond0 LACP - desde Pepe P11", "Trunk_a_principal"],
    [2, "hpdl360 (Proxmox)", "10.175.6.20", "Hypervisor", "LAG-SRV-HPDL360", "NIC 2 - bond0 LACP - desde Pepe P11", "Trunk_a_principal"],
    [3, "dellr610 (Proxmox)", "10.175.6.4", "Hypervisor", "LAG-SRV-DELLR610", "NIC 1 - bond0 LACP - desde Rack-Medio P5", "Trunk_a_principal"],
    [4, "dellr610 (Proxmox)", "10.175.6.4", "Hypervisor", "LAG-SRV-DELLR610", "NIC 2 - bond0 LACP - desde Rack-Medio P5", "Trunk_a_principal"],
    [5, "IBM x3400 PBS", "10.175.6.2", "Backup Server", "LAG-SRV-PBS", "NIC 1 - YA CONECTADO - LACP", "Trunk_a_principal"],
    [6, "IBM x3400 PBS", "10.175.6.2", "Backup Server", "LAG-SRV-PBS", "NIC 2 - YA CONECTADO - LACP", "Trunk_a_principal"],
    [7, "dellr610-2 (Proxmox)", "10.175.6.14", "Hypervisor", "LAG-SRV-DELLR610-2", "NIC 1 - bond0 LACP - desde Rack-Medio P7", "Trunk_a_principal"],
    [8, "dellr610-2 (Proxmox)", "10.175.6.14", "Hypervisor", "LAG-SRV-DELLR610-2", "NIC 2 - bond0 LACP - desde Rack-Medio P7", "Trunk_a_principal"],
    [9, "msi-i5 (Proxmox)", "10.175.6.6", "Hypervisor", "LAG-SRV-MSI", "NIC 1 - bond0 LACP (enp1s0)", "Trunk_a_principal"],
    [10, "msi-i5 (Proxmox)", "10.175.6.6", "Hypervisor", "LAG-SRV-MSI", "NIC 2 - bond0 LACP (enp3s0)", "Trunk_a_principal"],
    [11, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [12, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [13, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [14, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [15, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [16, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [17, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [18, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [19, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [20, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [21, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [22, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [23, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    [24, "LIBRE", "", "", "", "Para futuro Proxmox / NAS / Backup", ""],
    ["25 (SFP+)", "Principal (Uplink 10G)", "10.175.6.236", "Switch Core", "Trunk 10G", "Fibra 10G - Profile Trunk_a_principal", "Trunk_a_principal"],
    ["26 (SFP+)", "LIBRE", "", "", "", "Para uplink 10G redundante / Storage 10G", ""],
    ["27 (SFP+)", "LIBRE", "", "", "", "Para uplink 10G redundante / Storage 10G", ""],
    ["28 (SFP+)", "LIBRE", "", "", "", "Para uplink 10G redundante / Storage 10G", ""],
]


def get_credentials():
    """Obtiene credenciales OAuth válidas."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'r') as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            with open(CLIENT_SECRET_PATH, 'r') as f:
                client_config = json.load(f)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
    
    return creds


def find_mapa_switchs_spreadsheet(drive_service):
    """Busca la planilla 'Mapa Switchs' en la carpeta Ing-Hermes."""
    results = drive_service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false and name contains 'Mapa' and mimeType='application/vnd.google-apps.spreadsheet'",
        spaces='drive', fields='files(id,name)').execute()
    
    files = results.get('files', [])
    if not files:
        raise Exception("No se encontró la planilla 'Mapa Switchs' en la carpeta Ing-Hermes")
    
    # Tomar la primera coincidencia
    return files[0]['id'], files[0]['name']


def add_servidores_sheet(sheets_service, spreadsheet_id):
    """Añade o actualiza la hoja 'Servidores'."""
    # Verificar si ya existe
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = spreadsheet.get('sheets', [])
    
    servidores_sheet = None
    for s in sheets:
        if s['properties']['title'] == 'Servidores':
            servidores_sheet = s['properties']['sheetId']
            break
    
    if servidores_sheet is not None:
        print(f"Hoja 'Servidores' ya existe (sheetId: {servidores_sheet}), actualizando...")
        sheet_id = servidores_sheet
        
        # Limpiar contenido existente
        sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range='Servidores'
        ).execute()
    else:
        print("Creando nueva hoja 'Servidores'...")
        # Añadir nueva hoja
        request = {
            'addSheet': {
                'properties': {
                    'title': 'Servidores',
                    'gridProperties': {
                        'rowCount': 100,
                        'columnCount': 10
                    }
                }
            }
        }
        response = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [request]}
        ).execute()
        sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        print(f"Hoja creada con sheetId: {sheet_id}")
    
    # Escribir datos
    body = {
        'values': SERVIDORES_DATA
    }
    result = sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Servidores!A1',
        valueInputOption='RAW',
        body=body
    ).execute()
    
    print(f"✅ Hoja 'Servidores' actualizada: {result.get('updatedCells')} celdas")
    
    # Formatear encabezados (negrita, fondo)
    format_request = {
        'requests': [{
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {'bold': True},
                        'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9}
                    }
                },
                'fields': 'userEnteredFormat(textFormat,backgroundColor)'
            }
        }]
    }
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=format_request
    ).execute()
    
    # Ajustar ancho de columnas
    resize_request = {
        'requests': [{
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 7
                },
                'properties': {'pixelSize': 200},
                'fields': 'pixelSize'
            }
        }]
    }
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=resize_request
    ).execute()
    
    print("✅ Formato aplicado")


def main():
    print("🔐 Autenticando con Google...")
    creds = get_credentials()
    
    print("📋 Conectando a Google Drive y Sheets...")
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    print("🔍 Buscando planilla 'Mapa Switchs'...")
    spreadsheet_id, spreadsheet_name = find_mapa_switchs_spreadsheet(drive_service)
    print(f"✅ Encontrada: {spreadsheet_id} ({spreadsheet_name})")
    
    print("📝 Actualizando hoja 'Servidores'...")
    add_servidores_sheet(sheets_service, spreadsheet_id)
    
    print("\n✅ ¡Completado! La planilla 'Mapa Switchs' ahora tiene la hoja 'Servidores'.")


if __name__ == '__main__':
    main()