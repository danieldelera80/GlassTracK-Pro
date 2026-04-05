@echo off
title GlassTrack Pro - Backup de datos
color 0A
cd /d "%~dp0"

echo.
echo  =====================================================
echo    BACKUP DE DATOS - GlassTrack Pro
echo  =====================================================
echo.

if not exist "produccion.db" (
    echo  No hay base de datos para respaldar.
    pause
    exit /b
)

if not exist "_backups" mkdir "_backups"

for /f "tokens=1-3 delims=/" %%a in ("%date%") do set FECHA=%%c%%b%%a
for /f "tokens=1-2 delims=:" %%a in ("%time%") do set HORA=%%a%%b
set HORA=%HORA: =0%
set NOMBRE=produccion_%FECHA%_%HORA%.db

copy "produccion.db" "_backups\%NOMBRE%" >nul

echo  Backup guardado exitosamente:
echo.
echo    _backups\%NOMBRE%
echo.
echo  Para restaurar: copiar ese archivo y renombrarlo
echo  a  produccion.db  en esta carpeta.
echo.
echo  Backups disponibles:
dir "_backups\*.db" /b 2>nul
echo.
pause
