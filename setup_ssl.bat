@echo off
title Generando certificado SSL...
echo.
echo  Instalando dependencia...
pip install cryptography -q
echo.
echo  Generando certificado SSL local...
echo.
python generar_certificado.py
echo.
pause
