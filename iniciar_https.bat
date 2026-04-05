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

echo.
echo  =====================================================
echo   SISTEMA ACTIVO
echo  =====================================================
echo.
echo   Desde cualquier celular o PC en la misma WiFi:
echo.
echo     https://%IP%:8501
echo.
echo   La primera vez el navegador muestra advertencia.
echo   Tocar "Avanzado" y luego "Continuar de todos modos"
echo.
echo  =====================================================
echo.
echo   NO CERRAR ESTA VENTANA
echo   (Es el servidor del sistema)
echo.
echo  =====================================================
echo.

:: ── Iniciar Streamlit ─────────────────────────────────────────────────────────
streamlit run main.py

pause
