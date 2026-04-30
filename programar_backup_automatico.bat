@echo off
title GlassTrack Pro - Programar Backup Automatico
color 0A
cd /d "%~dp0"

echo.
echo  =====================================================
echo    PROGRAMAR BACKUP AUTOMATICO - GlassTrack Pro
echo    Lunes a Viernes - 17:45 hs
echo  =====================================================
echo.

:: Obtener ruta completa de Python
for /f "tokens=*" %%i in ('where python') do set PYTHON=%%i

if "%PYTHON%"=="" (
    :: Intentar con ruta local del sistema
    set PYTHON=C:\Users\ryrco\AppData\Local\Programs\Python\Python312\python.exe
)

set CARPETA=%~dp0
set SCRIPT=%CARPETA%backup_nube.py
set TAREA=GlassTrackPro_Backup_Diario

echo  Python encontrado en: %PYTHON%
echo  Script: %SCRIPT%
echo.

:: Eliminar tarea si ya existe (para actualizarla)
schtasks /delete /tn "%TAREA%" /f >nul 2>&1

:: Crear la tarea: Lun-Vie a las 17:45
schtasks /create ^
  /tn "%TAREA%" ^
  /tr "\"%PYTHON%\" \"%SCRIPT%\"" ^
  /sc WEEKLY ^
  /d MON,TUE,WED,THU,FRI ^
  /st 17:45 ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  =====================================================
    echo   Backup programado exitosamente!
    echo.
    echo   Horario: Lunes a Viernes a las 17:45 hs
    echo   Destino: %CARPETA%backups\
    echo   Formato: prod_YYYY-MM-DD_HH-MM.csv
    echo  =====================================================
    echo.
    echo  Para verificar: abri el Programador de tareas de
    echo  Windows y busca "%TAREA%"
    echo.
) else (
    echo.
    echo  ERROR al programar la tarea.
    echo  Intenta ejecutar este .bat como Administrador
    echo  (clic derecho - Ejecutar como administrador)
    echo.
)

pause
