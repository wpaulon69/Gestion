@echo off
title SAMCo Esperanza - Control de Cámaras y Grabación
color 0B

:: --- CONFIGURACIÓN DE ENTORNO ---
set LOCAL_PATH=Z:\Documentos Informatica\gestion
set PYTHON_ENV=%LOCAL_PATH%\gestion_env\Scripts\python.exe
set SCRIPT_NAME=check_camaras.py
set NAS_IP=10.175.6.10

:: Cambiar al directorio de trabajo
cd /d "%LOCAL_PATH%"

echo ======================================================
echo       SAMCo Esperanza - Sistema de Auditoría
echo ======================================================
echo [%date% %time%] --- INICIANDO CONTROL DE CÁMARAS ---
echo.

:: 1. Verificar conexión con el NAS (IP de export)
echo [%time%] Verificando conexión con el NAS (%NAS_IP%)...
ping -n 1 %NAS_IP% >nul
if %errorlevel% neq 0 (
    color 0C
    echo [%time%] ERROR: No se puede alcanzar el NAS %NAS_IP%.
    echo Verifique si el servidor de almacenamiento está encendido.
    pause
    exit
)
echo [OK] Conexión establecida.

:: 2. Ejecutar el script de Python
echo [%time%] Ejecutando auditoría de grabación...
echo ------------------------------------------------------
"%PYTHON_ENV%" %SCRIPT_NAME%
echo ------------------------------------------------------

if %errorlevel% equ 0 (
    echo.
    echo [OK] Reporte 'estado_grabaciones.json' generado correctamente.
    
    :: 3. Subir a Google Drive (Misma lógica que subir_reporte.bat)
    echo [%time%] Sincronizando reporte con Google Drive...
    rclone\rclone copy "estado_grabaciones.json" gdrive:Gestion -v
    
    if %errorlevel% equ 0 (
        echo [%time%] --- PROCESO COMPLETADO EXITOSAMENTE ---
    ) else (
        echo [%time%] ADVERTENCIA: No se pudo subir a Drive. Revise rclone.
    )
) else (
    color 0C
    echo.
    echo [%time%] ERROR: Falló la ejecución del script de Python.
)

echo.
echo La ventana se cerrará en 10 segundos...
timeout /t 10