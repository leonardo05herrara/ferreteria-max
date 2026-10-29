@echo off
cd /d "%~dp0"
python -m pip install pymysql -q
echo.
echo Ferreteria Max
echo Cerrando servidores viejos en el puerto 8766...
python -c "import servidor; servidor.liberar_puerto(servidor.PUERTO)"
echo Si MySQL pide contraseña, escribela cuando te la pida.
echo Luego abre: http://127.0.0.1:8766/cuenta.html
echo.
python crear_mysql.py
echo.
echo Abre en el navegador: http://127.0.0.1:8766/cuenta.html
python servidor.py
pause
