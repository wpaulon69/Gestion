# Documentación Técnica: Dashboard de Infraestructura IT - SAMCo Esperanza

Este proyecto proporciona un sistema de monitoreo centralizado para la infraestructura IT del SAMCo Esperanza, integrando datos de Zabbix, Omada, Proxmox (VE/BS) y almacenamiento NAS en una interfaz web moderna y en tiempo real.

## 🏗️ Arquitectura del Sistema

El sistema sigue una arquitectura de monitoreo por sondeo (polling) y visualización desacoplada:

1.  **Backend (Python 3):**
    *   **`auditar.py`**: El motor del sistema. Realiza peticiones asíncronas a todos los servicios (Zabbix, Omada, Proxmox) y consolida la información en un archivo JSON único (`output/reporte_completo.json`).
    *   **`servidor.py`**: Un micro-servidor Flask que expone una API para:
        *   Servir el reporte consolidado.
        *   Disparar nuevas auditorías bajo demanda.
        *   Actuar de bridge para abrir carpetas de red (SMB/UNC) desde el navegador.
2.  **Frontend (HTML5/Tailwind/JS):**
    *   **`dashboard.html`**: Una Single Page Application (SPA) que consume el JSON y renderiza la interfaz. Utiliza Tailwind CSS para el diseño y Chart.js para visualización.

## 📂 Estructura de Módulos (`modulos/`)

Cada servicio externo tiene su propio módulo lógico para facilitar el mantenimiento:

*   **`zabbix`**: Conexión con el servidor Zabbix para obtener:
    *   Alertas activas (Triggers).
    *   Estado de PING de hosts (Cámaras, Relojes).
    *   Tráfico de interfaces WAN.
    *   Espacio en disco del NAS.
*   **`omada`**: Integración con el Controlador TP-Link Omada. Obtiene el estado de los switches, consumo de hardware y realiza la segmentación de clientes por IP (Red 10.x vs 170.x/192.x).
*   **`proxmox`**: Consulta la API de PVE y PBS para monitorear Nodos, VMs, Contenedores y el estado de éxito/error de las tareas de backup.
*   **`nas_camaras`**: Verifica la existencia de grabaciones en el NAS cruzando datos con el estado de red de las cámaras.

## ⚙️ Configuración (`config.json`)

Toda la lógica de conexión (IPs, Tokens, Credenciales) se centraliza en `config.json`. **No se deben hardcodear credenciales en los módulos.**

## 🚀 Mantenimiento y Ejecución

1.  **Servidor:** Mantener `python servidor.py` ejecutándose (preferentemente como servicio de Windows o tarea programada).
2.  **Auditoría:** Se puede automatizar con un CRON/Tarea Programada ejecutando `python auditar.py` cada 5-10 minutos, o dispararla manualmente desde el Dashboard.
3.  **Seguridad:** El acceso a las carpetas del NAS requiere que el usuario tenga permisos de red NTFS/SMB sobre las rutas UNC (`\\10.175.6.10\...`).

---
*Documentación generada automáticamente por Antigravity AI - Abril 2026*
