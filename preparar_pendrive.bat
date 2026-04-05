@echo off
title GlassTrack Pro - Preparar Pendrive
color 0A
echo.
echo  =====================================================
echo    PREPARAR PENDRIVE - GlassTrack Pro
echo    Ejecutar en TU PC antes de llevar al cliente
echo  =====================================================
echo.
echo  Este script descarga todo lo necesario para que
echo  el sistema funcione SIN internet en la PC del cliente.
echo.
pause

set CARPETA=%~dp0
set PAQUETES_DIR=%CARPETA%_paquetes_offline

:: ── Crear carpeta de paquetes offline ────────────────────────────────────────
echo.
echo  [1/3] Creando carpeta de paquetes offline...
if not exist "%PAQUETES_DIR%" mkdir "%PAQUETES_DIR%"

:: ── Descargar todos los paquetes como .whl ───────────────────────────────────
echo.
echo  [2/3] Descargando paquetes para instalacion offline...
echo  (Necesita internet — solo se hace UNA VEZ en tu PC)
echo.
pip download streamlit pandas plotly openpyxl pyzbar Pillow streamlit-autorefresh cryptography ^
    --dest "%PAQUETES_DIR%" --quiet
if errorlevel 1 (
    echo  ERROR al descargar paquetes. Verifica tu internet.
    pause
    exit /b
)
echo  OK - Paquetes descargados en: _paquetes_offline\

:: ── Verificar tamaño ─────────────────────────────────────────────────────────
echo.
echo  [3/3] Verificando contenido...
dir "%PAQUETES_DIR%" | find "archivos"
echo.
echo  =====================================================
echo    LISTO - Podes copiar todo al pendrive
echo  =====================================================
echo.
echo  Copiá la carpeta completa  planilla--main  al pendrive.
echo  Incluye la subcarpeta  _paquetes_offline  con todo
echo  lo necesario para instalar sin internet.
echo.
echo  En la PC del cliente ejecutar:  instalar.bat
echo.
pause
