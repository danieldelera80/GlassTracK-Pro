@echo off
title GlassTrack Pro - Instalador
color 0B
echo.
echo  =====================================================
echo    INSTALADOR - GlassTrack Pro v1.0
echo    Sistema de Control de Produccion Industrial
echo  =====================================================
echo.

set CARPETA=%~dp0
set PAQUETES_DIR=%CARPETA%_paquetes_offline

:: ── PASO 1: Verificar Python ──────────────────────────────────────────────────
echo  [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Python no esta instalado en esta PC.
    echo.

    :: Buscar instalador de Python en el pendrive
    if exist "%CARPETA%_python_installer\python-installer.exe" (
        echo  Instalando Python desde el pendrive...
        echo  Seguir los pasos en pantalla.
        echo  IMPORTANTE: tildar "Add Python to PATH" antes de instalar.
        echo.
        start /wait "%CARPETA%_python_installer\python-installer.exe"
        echo.
        echo  Reiniciando verificacion...
        python --version >nul 2>&1
        if errorlevel 1 (
            echo  ERROR: Python no se instalo correctamente.
            echo  Instala Python manualmente desde python.org
            pause
            exit /b
        )
    ) else (
        echo  No se encontro instalador de Python en el pendrive.
        echo.
        echo  Opciones:
        echo  1. Instalar Python desde: https://www.python.org/downloads/
        echo     (tildar "Add Python to PATH")
        echo  2. Pedir al tecnico que lo instale.
        echo.
        pause
        exit /b
    )
)
python --version
echo  OK - Python listo.
echo.

:: ── PASO 2: Instalar librerias ────────────────────────────────────────────────
echo  [2/4] Instalando librerias del sistema...
echo.

if exist "%PAQUETES_DIR%" (
    echo  Instalando desde pendrive - sin necesidad de internet...
    pip install --no-index --find-links="%PAQUETES_DIR%" ^
        streamlit pandas plotly openpyxl pyzbar Pillow streamlit-autorefresh cryptography ^
        --quiet
) else (
    echo  Instalando desde internet...
    pip install streamlit pandas plotly openpyxl pyzbar Pillow streamlit-autorefresh cryptography ^
        --quiet
)

if errorlevel 1 (
    echo  ERROR al instalar librerias.
    echo  Si no hay internet, ejecuta primero preparar_pendrive.bat en tu PC.
    pause
    exit /b
)
echo  OK - Librerias instaladas.
echo.

:: ── PASO 3: Generar certificado SSL ──────────────────────────────────────────
echo  [3/4] Configurando acceso seguro desde celular (HTTPS)...
cd /d "%CARPETA%"
python generar_certificado.py
echo.

:: ── PASO 4: Configurar arranque automatico ────────────────────────────────────
echo  [4/4] Configurando arranque automatico con Windows...
set BAT="%CARPETA%iniciar_https.bat"
schtasks /create /tn "GlassTrack Pro" /tr %BAT% /sc onlogon /rl highest /f >nul 2>&1
if errorlevel 1 (
    echo  AVISO: No se pudo configurar arranque automatico.
    echo  Ejecuta este instalador click derecho "Ejecutar como Administrador".
) else (
    echo  OK - El sistema arrancara automaticamente al encender la PC.
)
echo.

echo  =====================================================
echo    INSTALACION COMPLETADA EXITOSAMENTE
echo  =====================================================
echo.
echo  El sistema ya esta listo para usar.
echo.
echo  Para iniciar ahora mismo:
echo  → Doble click en  iniciar_https.bat
echo.
echo  La proxima vez que enciendan la PC
echo  el sistema arranca automaticamente.
echo.
echo  Soporte tecnico:
echo  Daniel De Lera - WhatsApp: +54 9 3624210356
echo.
pause
