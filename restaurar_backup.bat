@echo off
setlocal

:: ============================================================
::  GlassTrack Pro - Restaurar backup con psql
::  Support IT - Daniel De Lera
:: ============================================================

set DB_URL=postgresql://neondb_owner:npg_QX5KbazNRUO6@ep-odd-frost-acbh50ok-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require^&channel_binding=require
set BACKUP_DIR=D:\Users\ryrco\Desktop\copia de mjjm funcionando neo\backups
set PSQL="C:\Program Files\PostgreSQL\17\bin\psql.exe"

echo.
echo ================================
echo  GlassTrack Pro - Restaurar
echo ================================
echo.

:: Listar backups disponibles
echo Backups disponibles en %BACKUP_DIR%:
echo.
dir "%BACKUP_DIR%\*.sql" /b 2>nul
echo.

:: Pedir nombre del archivo
set /p ARCHIVO=Escribi el nombre del archivo a restaurar (ej: glasstrak_backup_2026-04-14.sql):

if not exist "%BACKUP_DIR%\%ARCHIVO%" (
    echo.
    echo [ERROR] El archivo no existe: %BACKUP_DIR%\%ARCHIVO%
    echo         Revisa el nombre e intentalo de nuevo.
    echo.
    pause
    exit /b
)

:: Confirmacion antes de restaurar
echo.
echo ATENCION: Esto va a restaurar los datos de:
echo   %BACKUP_DIR%\%ARCHIVO%
echo sobre la base de datos actual en Neon.
echo.
echo Los datos actuales seran reemplazados.
echo.
set /p CONFIRMAR=Escribi SI para continuar:

if /i not "%CONFIRMAR%"=="SI" (
    echo.
    echo Operacion cancelada.
    echo.
    pause
    exit /b
)

echo.
echo Restaurando backup...
echo.

%PSQL% "%DB_URL%" -f "%BACKUP_DIR%\%ARCHIVO%"

if %errorlevel% == 0 (
    echo.
    echo [OK] Restauracion completada exitosamente.
    echo      Archivo restaurado: %ARCHIVO%
) else (
    echo.
    echo [ERROR] Fallo la restauracion.
    echo         Verificar: conexion Neon, archivo SQL valido.
)

echo.
pause
