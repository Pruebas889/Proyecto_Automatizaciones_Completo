# coding: utf-8
from functools import wraps
from flask import Flask, request, jsonify, render_template, Response, session, redirect
import estados
import socket
import threading
import time
import subprocess
import os
import logging
from collections import deque
from datetime import datetime


app = Flask(__name__)
app.secret_key = '3103487201022947165sG'
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos

# -------- Decorador para login protegido ----------
# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'reportes':
            logging.info("Acceso no autorizado, redirigiendo a http://192.168.20.8:5000")
            return redirect('http://192.168.20.8:5000')
        return f(*args, **kwargs)
    return decorated_function

# -------- Configuración de logs ----------
log_queue = deque(maxlen=200)
class QueueHandler(logging.Handler):
    def emit(self, record):
        log_queue.append(self.format(record))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[QueueHandler(), logging.StreamHandler()]
)


# Bandera para controlar la detención del proceso
stop_automation_flag = threading.Event()
automation_process = None
is_running = False
# -------- Lógica del servidor ----------

def start_automation(fecha):
    """Inicia el script de automatización en un proceso separado, pasando la fecha seleccionada."""
    stop_automation_flag.clear()  # Reset the flag on start
    print("Iniciando la automatización en un nuevo proceso...")
    # Ejecuta estados.py pasando la fecha como argumento
    command = ["python", "-u", "estados.py", fecha]
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


# -------- Lógica del servidor ----------
def read_logs_from_subprocess():
    global automation_process, is_running
    for line in iter(automation_process.stdout.readline, ''):
        if line.strip():
            logging.info(line.strip())
    automation_process.wait()
    is_running = False
    logging.info("Automatización finalizada.")
    # Mensaje claro que la UI detecta como finalización
    logging.info("Terminado")

@app.route('/')
@login_required
def home():
    # Determine local IP address for convenience
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return render_template('index.html', ip=local_ip, port=5008)

@app.route('/start', methods=['POST'])
@login_required
def start():
    global automation_process, is_running
    if is_running:
        return jsonify({'success': False, 'message': 'Ya se está ejecutando la automatización.'})
    is_running = True

    fecha = request.form.get('fecha')
    if not fecha:
        is_running = False
        return jsonify({'success': False, 'message': 'Debe seleccionar una fecha.'})
    try:
        automation_process = start_automation(fecha)
        threading.Thread(target=read_logs_from_subprocess, daemon=True).start()
        return jsonify({'success': True, 'message': 'Automatización iniciada.'})
    except Exception as e:
        is_running = False
        logging.error(f"Error al iniciar: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/stop', methods=['POST'])
@login_required
def stop():
    global automation_process, is_running
    stop_automation()
    if automation_process:
        automation_process.terminate()
    is_running = False
    return jsonify({'success': True, 'message': 'Automatización detenida.'})

@app.route('/stream_logs')
@login_required
def stream_logs():
    def generate():
        for log in list(log_queue):
            yield f"data: {log}\\n\\n"
        last = len(log_queue)
        while True:
            if len(log_queue) > last:
                yield f"data: {log_queue[last]}\\n\\n"
                last += 1
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')



if __name__ == '__main__':
    logging.info("Iniciando servidor de Estados... 🌐")
    app.run(host='0.0.0.0', port=5008, debug=True, use_reloader=False)
