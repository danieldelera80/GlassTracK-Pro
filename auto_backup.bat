@echo off
title GlassTrack Pro - Backup de Produccion
color 0B
cd /d "%~dp0"

echo.
echo  =====================================================
echo    BACKUP AUTOMATICO - GlassTrack Pro (Nube Neon)
echo  =====================================================
echo.
echo  MANTEN ESTA VENTANA MINIMIZADA EN LA COMPUTADORA.
echo  El sistema descargara la base de datos cada 6 horas.
echo.

:BUCLE
python backup_nube.py

echo.
echo Esperando 6 horas para la proxima extraccion...
REM 21600 segundos = 6 horas
timeout /t 21600 >nul
goto BUCLE
