@echo off
setlocal

:: ============================================================
::  GlassTrack Pro - Backup con pg_dump
::  Support IT - Daniel De Lera
:: ============================================================

set DB_URL=PONER_URL_NEON_AQUI
set BACKUP_DIR=D:\Users\ryrco\Desktop\copia de mjjm funcionando neo\backups
set FECHA=%date:~6,4%-%date:~3,2%-%date:~0,2%
set ARCHIVO=glasstrak_backup_%FECHA%.sql

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo.
echo ================================
echo  GlassTrack Pro - Backup Neon
echo ================================
echo Iniciando backup...
echo.

pg_dump "%DB_URL%" -f "%BACKUP_DIR%\%ARCHIVO%"

if %errorlevel% == 0 (
    echo.
    echo [OK] Backup completado exitosamente.
    echo      Archivo: %BACKUP_DIR%\%ARCHIVO%
) else (
    echo.
    echo [ERROR] Fallo el backup.
    echo         Verificar: conexion Neon, pg_dump instalado en PATH.
)

echo.
pause
