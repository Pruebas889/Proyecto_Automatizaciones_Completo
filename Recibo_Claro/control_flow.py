import threading
import subprocess
import os

# Bandera para controlar la detención del proceso
stop_automation_flag = threading.Event()

def start_automation(username, password, download_dir, anio, mes):
    """Inicia el script de automatización en un proceso separado."""
    stop_automation_flag.clear()  # Reset the flag on start
    print("Iniciando la automatización en un nuevo proceso...")
    
    # Prepara el comando para ejecutar el script, pasando los argumentos necesarios
    command = ["python", "-u", "automatizacion_descarga.py", username, password, download_dir, str(anio), str(mes)]
    
    # Configuración del proceso
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    return process

def stop_automation():
    """Establece la bandera para detener la automatización."""
    stop_automation_flag.set()
    print("Señal de detención enviada. La automatización se detendrá pronto.")