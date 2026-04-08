@echo off
color 0B
title Iniciando Control de Produccion - Contacto S.A.

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual. 
    echo Por favor, ejecuta primero "1_INSTALAR_SISTEMA.bat".
    pause
    exit /b 1
)

echo =========================================================
echo       Iniciando Sistema de Produccion...
echo =========================================================
echo.
echo Activando entorno virtual...
call venv\Scripts\activate

echo.
echo Arrancando el servidor servidor local (Streamlit)...
echo Por favor, no cierres esta ventana negra mientras usas el sistema.
echo.
streamlit run main.py --server.port 8501 --server.address 0.0.0.0
