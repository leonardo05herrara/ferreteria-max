@echo off
cd /d "%~dp0"
net session >nul 2>&1
if errorlevel 1 (
  echo.
  echo Click derecho en este archivo y elige: Ejecutar como administrador
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cambiar-clave-mysql.ps1"
if errorlevel 1 (
  echo.
  echo No se pudo cambiar. Deja esa ventana abierta y avisa.
  pause
  exit /b 1
)

echo.
echo Listo. Contraseña nueva de root: FerreteriaMax2026
echo Ya quedo guardada en config.json
echo Ahora cierra otras ventanas de Python y abre abrir-tienda.bat
echo.
pause
