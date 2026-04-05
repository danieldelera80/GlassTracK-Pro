@echo off
title GlassTrack Pro - Desinstalar arranque automatico
echo.
echo  Eliminando tarea de arranque automatico...
schtasks /delete /tn "GlassTrack Pro" /f >nul 2>&1
if errorlevel 1 (
    echo  No habia tarea configurada.
) else (
    echo  OK - Arranque automatico eliminado.
)
echo.
pause
