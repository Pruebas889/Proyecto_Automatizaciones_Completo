@echo off
rem Este archivo inicia el servidor de Python y abre la interfaz en el navegador.
echo Iniciando el servidor de automatizacion...
echo Por favor, espera a que el navegador se abra automaticamente.
start chrome http://127.0.0.1:5000
python server.py
pause
