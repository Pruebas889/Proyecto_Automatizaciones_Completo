@echo off
cd "C:\Users\dforero\Documents\Mensajeros\mensajeros.py"

:inicio
python mensajeros.py

echo Esperando 5 minutos antes de reiniciar...
timeout /t 300 >nul

echo Reiniciando script...
goto inicio