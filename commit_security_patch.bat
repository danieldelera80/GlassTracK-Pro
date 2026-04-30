@echo off
REM ════════════════════════════════════════════════════════════════════════════
REM  commit_security_patch.bat
REM  Commit de los cambios de seguridad: admin bypass + license resilience
REM  Generado por Claude — auditoria GlassTrack Pro
REM ════════════════════════════════════════════════════════════════════════════

cd /d "%~dp0"

echo.
echo === Estado previo del repo ===
git status --short
echo.

echo === Stageando archivos modificados ===
git add config.py pages/01_Monitor.py
if errorlevel 1 (
    echo [ERROR] git add fallo. Abortando.
    pause
    exit /b 1
)

echo.
echo === Commit ===
git commit -m "security: patch admin bypass and license resilience"
if errorlevel 1 (
    echo [ERROR] git commit fallo (puede no haber cambios staged).
    pause
    exit /b 1
)

echo.
echo === Push a GitHub ===
git push
if errorlevel 1 (
    echo [ERROR] git push fallo. Verifica credenciales o conexion.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  LISTO. Cambios pusheados a GitHub.
echo ============================================================
pause
