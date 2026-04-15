@echo off
setlocal

:: ============================================================
::  GlassTrack Pro - Backup con pg_dump
::  Support IT - Daniel De Lera
:: ============================================================

set DB_URL=postgresql://neondb_owner:npg_QX5KbazNRUO6@ep-odd-frost-acbh50ok-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require^&channel_binding=require
set BACKUP_DIR=D:\Users\ryrco\Desktop\copia de mjjm funcionando neo\backups
FOR /F "tokens=1-3 delims=/" %%a IN ("%date%") DO SET FECHA=%%a-%%b-%%c
set ARCHIVO=glasstrak_backup_%FECHA%.sql

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo.
echo ================================
echo  GlassTrack Pro - Backup Neon
echo ================================
echo Iniciando backup...
echo.

IF NOT EXIST "backups" MKDIR "backups"
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" "%DB_URL%" -f "%BACKUP_DIR%\%ARCHIVO%"

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
