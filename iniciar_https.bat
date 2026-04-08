@echo off
title GlassTrack Pro - Control de Produccion
color 0B

:: ── Ir a la carpeta del sistema ───────────────────────────────────────────────
cd /d "%~dp0"

:: ── Verificar certificado SSL ─────────────────────────────────────────────────
if not exist ".streamlit\cert.pem" (
    echo.
    echo  Generando certificado SSL por primera vez...
    pip install cryptography --quiet
    python generar_certificado.py
    echo.
)

:: ── Obtener IP local ──────────────────────────────────────────────────────────
echo.
echo  =====================================================
echo    GlassTrack Pro v1.0
echo    Sistema de Control de Produccion
echo  =====================================================
echo.
echo  Buscando IP de red local...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R "IPv4"') do (
    set RAW=%%a
    goto :found
)
:found
set IP=%RAW: =%

:: ── Configurar Streamlit para red local ───────────────────────────────────────
:: Asegurar que el archivo config.toml existe con la configuración correcta
if not exist ".streamlit\config.toml" (
    echo  Creando configuracion de red...
    mkdir ".streamlit" 2>nul
    echo [server] > ".streamlit\config.toml"
    echo address = "0.0.0.0" >> ".streamlit\config.toml"
    echo port = 8501 >> ".streamlit\config.toml"
    echo. >> ".streamlit\config.toml"
    echo [browser] >> ".streamlit\config.toml"
    echo gatherUsageStats = false >> ".streamlit\config.toml"
)

:: ── Verificar que la configuración tenga la IP correcta ───────────────────────
:: Streamlit con HTTPS necesita la IP explícita
echo.
echo  =====================================================
echo   SISTEMA ACTIVO
echo  =====================================================
echo.
echo   ACCESOS DISPONIBLES:
echo.
echo   En esta PC (localhost):
echo     https://localhost:8501
echo     https://127.0.0.1:8501
echo.
echo   Desde cualquier celular o PC en la misma RED:
echo     https://%IP%:8501
echo.
echo   ⚠️  IMPORTANTE:
echo   - La primera vez el navegador muestra advertencia.
echo   - Tocar "Avanzado" y luego "Continuar de todos modos"
echo   - En CELULARES: Usar Chrome o Firefox
echo   - En PC: Usar Chrome o Edge
echo.
echo  =====================================================
echo.
echo   NO CERRAR ESTA VENTANA
echo   (Es el servidor del sistema)
echo.
echo  =====================================================
echo.

:: ── Agregar regla al firewall automáticamente (como administrador) ────────────
netsh advfirewall firewall add rule name="GlassTrack Pro" dir=in action=allow protocol=tcp localport=8501 >nul 2>&1

:: ── Iniciar Streamlit con configuración explícita ─────────────────────────────
streamlit run main.py --server.address 0.0.0.0 --server.port 8501 --server.sslCertFile .streamlit/cert.pem --server.sslKeyFile .streamlit/key.pem

pause