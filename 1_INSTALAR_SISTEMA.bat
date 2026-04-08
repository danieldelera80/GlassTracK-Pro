@echo off
color 0A
title Instalador Control de Produccion - Contacto S.A.
echo =========================================================
echo       Instalando Sistema de Control de Produccion
echo =========================================================
echo.

:: Verificar si Python esta instalado
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Por favor, instala Python 3.10 o superior (marca "Add Python to PATH" en el instalador).
    echo Descarga: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python detectado.
echo.
echo Creando entorno virtual aislado (venv)...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

echo [OK] Entorno virtual creado.
echo.
echo Activando entorno virtual...
call venv\Scripts\activate

echo.
echo Instalando dependencias necesarias (esto puede tardar unos minutos)...
pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema instalando las dependencias.
    echo Asegurate de tener conexion a internet.
    echo Nota: Si falla "pyzbar", quiza necesites instalar Visual C++ Redistributable.
    pause
    exit /b 1
)

echo.
echo =========================================================
echo       INSTALACION COMPLETADA CON EXITO
echo =========================================================
echo.
echo Para arrancar el sistema, haz doble clic en "2_ARRANCAR_SISTEMA.bat".
pause
