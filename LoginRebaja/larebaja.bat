@echo off
:inicio
:: Mantener ventana abierta
title Automatización La Rebaja - Logins
echo =======================================
echo  INICIANDO AUTOMATIZACION LA REBAJA
echo =======================================
:: Ir a la carpeta del script
cd /d "C:\Users\jperdomolc\Pictures\LoginRebaja"

:: Ejecutar el script

python loginlarebaja.py

echo.
echo =======================================
echo  AUTOMATIZACION FINALIZADA
echo =======================================
goto inicio