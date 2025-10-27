@echo off
setlocal enabledelayedexpansion

:: Configuración del entorno
set PYTHON_EXEC=python
set SCRIPT_PATH=server.py
set LOG_FILE=run_log.txt
set SLEEP_SECONDS=5

:: Crear o limpiar el archivo de log
echo [%DATE% %TIME%] Iniciando ejecución del script > %LOG_FILE%

:loop
echo [%DATE% %TIME%] Ejecutando %SCRIPT_PATH%... >> %LOG_FILE%
%PYTHON_EXEC% %SCRIPT_PATH%
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% NEQ 0 (
    echo [%DATE% %TIME%] Error: El script falló con código %EXIT_CODE%. Reintentando en %SLEEP_SECONDS% segundos... >> %LOG_FILE%
) else (
    echo [%DATE% %TIME%] El script finalizó correctamente. Terminando bucle. >> %LOG_FILE%
    goto :eof
)

timeout /t %SLEEP_SECONDS% /nobreak >nul
goto :loop

:eof
echo [%DATE% %TIME%] Proceso terminado. >> %LOG_FILE%
pause