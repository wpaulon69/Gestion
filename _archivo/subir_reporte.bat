@echo off
set LOCAL_PATH=Z:\Documentos Informatica\gestion
set PYTHON_ENV=%LOCAL_PATH%\gestion_env\Scripts\python.exe

cd /d "%LOCAL_PATH%"
echo [%date% %time%] --- INICIANDO REPORTE UNIFICADO ---

:: Ejecutar el script
"%PYTHON_ENV%" check_red.py

:: Subir a Drive
echo [%date% %time%] Subiendo a Google Drive...
rclone\rclone copy "estado_sistema.json" gdrive:Gestion -v
rclone\rclone copy "config_red_total.json" gdrive:Gestion -v

echo [%date% %time%] --- PROCESO COMPLETADO ---
timeout /t 10

