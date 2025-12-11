from datetime import datetime  # Agregar este import
from functools import wraps
import os
from flask import Flask, redirect, render_template, jsonify, send_from_directory, session, Response
import socket
import logging
import sys
import subprocess
import threading
import time
import json
from collections import deque

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos de expiración de sesión

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'larebaja':
            logging.info("Acceso no autorizado, redirigiendo a http://192.168.21.56:5000")
            return redirect('http://192.168.21.56:5000')
        return f(*args, **kwargs)
    return decorated_function

# Variable para controlar el estado de la automatización
running_process = None
log_queue = deque(maxlen=200)  # Cola para logs en memoria

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("server.log", encoding='utf-8')
    ]
)

# Obtener la IP del equipo
def obtener_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception as e:
        logging.error(f"Error obteniendo IP: {e}")
        return "127.0.0.1"  # Fallback a localhost

# Thread para capturar logs del subprocess
def read_logs_from_subprocess():
    global running_process
    if not running_process or running_process.stdout is None:
        logging.error("No se pudo leer logs del proceso.")
        return
    logging.info("Iniciando lectura de logs del subproceso...")
    for pipe in [running_process.stdout, running_process.stderr]:
        if pipe:
            for line in iter(pipe.readline, ''):
                decoded_line = line.strip()
                if decoded_line:
                    log_queue.append(decoded_line)  # Guardar en cola
    running_process.wait()
    log_queue.append("Automatización finalizada naturalmente")

# Ruta para servir imágenes desde la carpeta 'images'
@app.route('/images/<path:filename>')
@login_required
def images(filename):
    return send_from_directory('images', filename)

# Ruta para la página principal con el botón
@app.route('/')
@login_required
def index():
    return render_template('rebaja.html')

# Ruta para iniciar la automatización
@app.route('/start', methods=['POST'])
@login_required
def start_automation():
    global running_process
    if running_process and running_process.poll() is None:
        return jsonify({'status': 'error', 'error': 'Ya está corriendo.'}), 409
    
    try:
        # Ruta absoluta a loginlarebaja.py
        script_path = r"C:\Users\dforero\Pictures\Proyecto_Automatizaciones_Completo\LoginRebaja\loginlarebaja.py"
        # Verificar si el archivo existe
        if not os.path.exists(script_path):
            error_msg = f"No se encontró el archivo: {script_path}"
            logging.error(error_msg)
            return jsonify({'status': 'error', 'error': error_msg}), 500
            
        running_process = subprocess.Popen(
            [sys.executable, script_path],  # Usar sys.executable para el intérprete correcto
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',      # ← AGREGAR ESTA LÍNEA
            errors='replace',
            bufsize=1
        )
        logging.info(f"Automatización iniciada. PID: {running_process.pid}")
        threading.Thread(target=read_logs_from_subprocess, daemon=True).start()
        return jsonify({'status': 'success', 'message': f'Iniciada con PID {running_process.pid}. Chequea logs en la interfaz.'})
    except Exception as e:
        logging.error(f"Error iniciando: {e}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)}), 500

# Ruta para detener la automatización
@app.route('/stop', methods=['POST'])
@login_required
def stop_automation():
    global running_process
    if running_process and running_process.poll() is None:
        try:
            pid = running_process.pid
            running_process.terminate()  # Enviar SIGTERM
            running_process.wait(timeout=3)  # Esperar 3 segundos
            log_queue.append("Automatización detenida, navegador cerrado")
            with open("server.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} - Automatización detenida PID {pid}\n")
            running_process = None
            return jsonify({'status': 'success', 'message': f'Detenida PID {pid}'})
        except subprocess.TimeoutExpired:
            running_process.kill()  # Forzar con SIGKILL
            log_queue.append("Automatización detenida forzosamente, navegador cerrado")
            with open("server.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} - Automatización detenida forzosamente PID {pid}\n")
            running_process = None
            return jsonify({'status': 'success', 'message': f'Detenida forzosamente PID {pid}'})
        except Exception as e:
            log_queue.append(f"Error al detener: {str(e)}")
            with open("server.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} - Error al detener: {str(e)}\n")
            running_process = None
            return jsonify({'status': 'error', 'message': f'Error al detener: {str(e)}'})
    else:
        return jsonify({'status': 'error', 'message': 'No está corriendo.'}), 400

# Ruta para verificar el estado de la automatización
@app.route('/status', methods=['GET'])
@login_required
def get_status():
    global running_process
    is_running = running_process is not None and running_process.poll() is None
    return jsonify({'is_running': is_running})

# Ruta para streaming de logs
@app.route('/stream-logs', methods=['GET'])
@login_required
def stream_logs():
    def generate():
        last_log_index = len(log_queue)
        while True:
            if len(log_queue) > last_log_index:
                for i in range(last_log_index, len(log_queue)):
                    message = log_queue[i]
                    data = {'message': message, 'type': 'info' if 'iniciada' in message.lower() or 'detenida' in message.lower() else 'progress'}
                    yield f"data: {json.dumps(data)}\n\n"
                last_log_index = len(log_queue)
            if running_process and running_process.poll() is not None:
                yield f"data: {json.dumps({'message': 'Automatización finalizada', 'type': 'info'})}\n\n"
                break
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

if __name__ == "__main__":
    # Obtener IP y puerto
    ip = obtener_ip()
    port = 5004
    
    # Iniciar el servidor Flask
    logging.info(f"Servidor iniciado en http://192.168.21.56:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)