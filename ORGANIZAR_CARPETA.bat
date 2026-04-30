@echo off
chcp 65001 >nul
echo ========================================
echo   ORGANIZANDO CARPETA GLASSTRACK PRO
echo ========================================
echo.
echo ⚠️  IMPORTANTE: NO se moveran .agent ni .claude
echo    (necesarias para Antigravity/Claude Code)
echo.

echo 📁 Moviendo carpetas de instalacion...
move "backups" "no se utiliza\backups" 2>nul && echo    ✓ backups || echo    ⚠ backups ya movida
move "_paquetes_offline" "no se utiliza\_paquetes_offline" 2>nul && echo    ✓ _paquetes_offline || echo    ⚠ _paquetes_offline ya movida
move "_python_installer" "no se utiliza\_python_installer" 2>nul && echo    ✓ _python_installer || echo    ⚠ _python_installer ya movida
move ".devcontainer" "no se utiliza\.devcontainer" 2>nul && echo    ✓ .devcontainer || echo    ⚠ .devcontainer ya movida

echo.
echo 📄 Moviendo scripts .bat innecesarios...
move "1_INSTALAR_SISTEMA.bat" "no se utiliza\" 2>nul && echo    ✓ 1_INSTALAR_SISTEMA.bat
move "2_ARRANCAR_SISTEMA.bat" "no se utiliza\" 2>nul && echo    ✓ 2_ARRANCAR_SISTEMA.bat
move "actualizar.bat" "no se utiliza\" 2>nul && echo    ✓ actualizar.bat
move "auto_backup.bat" "no se utiliza\" 2>nul && echo    ✓ auto_backup.bat
move "backup_datos.bat" "no se utiliza\" 2>nul && echo    ✓ backup_datos.bat
move "commit_security_patch.bat" "no se utiliza\" 2>nul && echo    ✓ commit_security_patch.bat
move "desinstalar_arranque.bat" "no se utiliza\" 2>nul && echo    ✓ desinstalar_arranque.bat
move "iniciar_https.bat" "no se utiliza\" 2>nul && echo    ✓ iniciar_https.bat
move "instalar.bat" "no se utiliza\" 2>nul && echo    ✓ instalar.bat
move "preparar_pendrive.bat" "no se utiliza\" 2>nul && echo    ✓ preparar_pendrive.bat
move "programar_backup_automatico.bat" "no se utiliza\" 2>nul && echo    ✓ programar_backup_automatico.bat
move "restaurar_backup.bat" "no se utiliza\" 2>nul && echo    ✓ restaurar_backup.bat
move "setup_ssl.bat" "no se utiliza\" 2>nul && echo    ✓ setup_ssl.bat

echo.
echo 📄 Moviendo archivos temporales...
move "config.py.bak.20260420" "no se utiliza\" 2>nul && echo    ✓ config.py.bak
move "config_dump.txt" "no se utiliza\" 2>nul && echo    ✓ config_dump.txt
move "diff.txt" "no se utiliza\" 2>nul && echo    ✓ diff.txt
move "cambios_multiseleccion.txt" "no se utiliza\" 2>nul && echo    ✓ cambios_multiseleccion.txt
move "produccion.db" "no se utiliza\" 2>nul && echo    ✓ produccion.db (SQLite viejo)

echo.
echo 📄 Moviendo scripts Python innecesarios...
move "backup_nube.py" "no se utiliza\" 2>nul && echo    ✓ backup_nube.py
move "generar_certificado.py" "no se utiliza\" 2>nul && echo    ✓ generar_certificado.py

echo.
echo 📄 Moviendo documentacion temporal...
move "LEER_MIGRACION.txt" "no se utiliza\" 2>nul && echo    ✓ LEER_MIGRACION.txt
move "MANUAL_ARQUITECTURA.md" "no se utiliza\" 2>nul && echo    ✓ MANUAL_ARQUITECTURA.md
move "README.md" "no se utiliza\" 2>nul && echo    ✓ README.md

echo.
echo 📄 Moviendo archivos Git...
move ".gitattributes" "no se utiliza\" 2>nul && echo    ✓ .gitattributes
move ".gitignore" "no se utiliza\" 2>nul && echo    ✓ .gitignore

echo.
echo 📄 Moviendo backups de pages...
move "pages\02_Formulario.py.backup" "no se utiliza\" 2>nul && echo    ✓ 02_Formulario.py.backup

echo.
echo ========================================
echo   ✅ ORGANIZACIÓN COMPLETADA
echo ========================================
echo.
echo 📂 Archivos movidos a: %CD%\no se utiliza
echo.
echo 📋 CARPETAS QUE QUEDAN (ESENCIALES + ANTIGRAVITY):
echo    ✓ .agent/ (Antigravity - skills y workflows)
echo    ✓ .claude/ (configuracion Claude Code)
echo    ✓ .git/ (repositorio)
echo    ✓ .streamlit/ (config Streamlit)
echo    ✓ main.py, config.py, styles.py
echo    ✓ pages/, components/
echo    ✓ requirements.txt, packages.txt
echo    ✓ logos, beep.wav
echo.
pause
