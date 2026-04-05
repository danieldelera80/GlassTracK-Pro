@echo off
title GlassTrack Pro - Actualizador
color 0B
cd /d "%~dp0"

echo.
echo  =====================================================
echo    GlassTrack Pro - Actualizacion del sistema
echo    Support IT - Daniel De Lera
echo  =====================================================
echo.

:: ── PASO 1: Backup de la base de datos ANTES de todo ─────────────────────────
echo  [1/4] Haciendo backup de los datos...

if not exist "produccion.db" (
    echo  No hay base de datos todavia. Continuando...
) else (
    :: Crear carpeta de backups si no existe
    if not exist "_backups" mkdir "_backups"

    :: Nombre del backup con fecha y hora
    for /f "tokens=1-3 delims=/" %%a in ("%date%") do set FECHA=%%c%%b%%a
    for /f "tokens=1-2 delims=:" %%a in ("%time%") do set HORA=%%a%%b
    set HORA=%HORA: =0%
    set NOMBRE_BACKUP=produccion_%FECHA%_%HORA%.db

    copy "produccion.db" "_backups\%NOMBRE_BACKUP%" >nul
    echo  OK - Backup guardado: _backups\%NOMBRE_BACKUP%
)
echo.

:: ── PASO 2: Verificar que Git esta instalado ──────────────────────────────────
echo  [2/4] Verificando Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Git no esta instalado.
    echo  Instalar desde: https://git-scm.com/download/win
    echo.
    pause
    exit /b
)
echo  OK - Git encontrado.
echo.

:: ── PASO 3: Descargar la ultima version del codigo ────────────────────────────
echo  [3/4] Descargando actualizacion...
echo  (Necesita internet)
echo.
git pull origin main
if errorlevel 1 (
    echo.
    echo  ERROR al descargar la actualizacion.
    echo  Verificar conexion a internet.
    echo.
    echo  Los datos NO fueron modificados.
    echo  El sistema sigue funcionando normalmente.
    pause
    exit /b
)
echo.
echo  OK - Codigo actualizado.
echo.

:: ── PASO 4: Reiniciar el sistema ──────────────────────────────────────────────
echo  [4/4] Reiniciando el sistema...

:: Cerrar cualquier instancia de streamlit corriendo
taskkill /f /im "streamlit.exe" >nul 2>&1
taskkill /f /im "python.exe"    >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
echo  =====================================================
echo    ACTUALIZACION COMPLETADA
echo  =====================================================
echo.
echo  Datos protegidos:
echo    produccion.db  →  intacta, sin cambios
echo    _backups\      →  copia de seguridad guardada
echo.
echo  Iniciando el sistema actualizado...
echo.
timeout /t 3 /nobreak >nul

:: Reiniciar
call iniciar_https.bat
