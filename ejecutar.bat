@echo off
title SAMCo Esperanza - Auditoria Unificada
set LOCAL_PATH=Z:\Documentos Informatica\gestion
set PYTHON_ENV=%LOCAL_PATH%\gestion_env\Scripts\python.exe

:: Cambiar al directorio de trabajo
cd /d "%LOCAL_PATH%"

echo ======================================================
echo       SAMCo Esperanza - Sistema de Auditoria
echo ======================================================
echo [%date% %time%] --- INICIANDO REPORTE UNIFICADO ---
echo.

:: 1. Ejecutar el script centralizado
"%PYTHON_ENV%" auditar.py

if %errorlevel% equ 0 (
    echo.
    echo [OK] Auditoria completada exitosamente.
    
    :: 2. Sincronizar con Google Drive
    echo [%time%] Sincronizando con Google Drive via rclone...
    echo ------------------------------------------------------
    rclone\rclone --config "rclone\rclone.conf" copy "output\reporte_completo.json" gdrive:Gestion -v
    
    if %errorlevel% equ 0 (
        echo.
        echo [%time%] --- PROCESO FINALIZADO EXITOSAMENTE ---
    ) else (
        echo.
        echo [%time%] ADVERTENCIA: Fallo la subida a Drive. Verifique rclone.
    )
) else (
    color 0C
    echo.
    echo [%time%] ERROR: El script de auditoria fallo.
)

echo.
echo La ventana se cerrara en 10 segundos...
timeout /t 10
