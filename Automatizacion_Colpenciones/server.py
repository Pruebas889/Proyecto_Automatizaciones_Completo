import json
from flask import Flask, jsonify, send_from_directory, request, session, redirect, Response
from functools import wraps
import subprocess
import os
import time
import logging
import threading
from collections import deque

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800

# Decorador login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('username') != 'colpensiones':
            return redirect('http://192.168.20.8:5000')
        return f(*args, **kwargs)
    return decorated_function

# Logging simple
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log", encoding='utf-8')
    ]
)

running_process = None
log_queue = deque(maxlen=200)  # Cola para logs en memoria
TABLA_GUARDADA_FILE = os.path.join(os.path.dirname(__file__), "tabla_guardada.json")
ULTIMO_PROGRESO_FILE = os.path.join(os.path.dirname(__file__), "ultimo_progreso.json")

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

@app.route('/')
@login_required
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('username') == 'colpensiones':  # Sin password
        session['logged_in'] = True
        session['username'] = 'colpensiones'
        return redirect('/')
    return 'Login inválido', 401

@app.route('/run-automation', methods=['POST'])
@login_required
def run_automation():
    global running_process
    if running_process and running_process.poll() is None:
        return jsonify({'status': 'error', 'error': 'Ya está corriendo.'}), 409
    
    try:
        script_path = os.path.abspath('Automatizacion_Colpenciones/Colpensiones.py')
        running_process = subprocess.Popen(
            ['python', script_path],
            stdout=subprocess.PIPE,  # Captura stdout
            stderr=subprocess.PIPE,  # Captura stderr
            text=True,
            bufsize=1
        )
        logging.info(f"Automatización iniciada. PID: {running_process.pid}")
        threading.Thread(target=read_logs_from_subprocess, daemon=True).start()  # Inicia thread para logs
        return jsonify({'status': 'success', 'message': f'Iniciada con PID {running_process.pid}. Chequea logs en la interfaz.'})
    except Exception as e:
        logging.error(f"Error iniciando: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/stop-automation', methods=['POST'])
@login_required
def stop_automation():
    global running_process
    if running_process and running_process.poll() is None:
        try:
            pid = running_process.pid
            running_process.terminate()
            running_process.wait(timeout=10)
            logging.info(f"Detenida PID {pid} correctamente.")
            log_queue.append("Automatización detenida")
            return jsonify({'status': 'success', 'message': f'Detenida PID {pid}.'})
        except subprocess.TimeoutExpired:
            running_process.kill()
            running_process.wait()
            logging.info(f"Detenida forzosamente PID {running_process.pid}.")
            log_queue.append("Automatización detenida forzosamente")
            return jsonify({'status': 'success', 'message': 'Detenida forzosamente.'})
        except Exception as e:
            logging.error(f"Error deteniendo: {e}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'error': 'No está corriendo.'}), 400

@app.route('/clear-progress', methods=['POST'])
@login_required
def clear_progress():
    global running_process
    if running_process and running_process.poll() is None:
        return jsonify({'status': 'error', 'error': 'No se puede limpiar mientras corre la automatización.'}), 409

    files_to_clear = [TABLA_GUARDADA_FILE, ULTIMO_PROGRESO_FILE]
    cleared_files = []
    errors = []

    for file_path in files_to_clear:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                cleared_files.append(os.path.basename(file_path))
                logging.info(f"Archivo eliminado: {file_path}")
            except Exception as e:
                errors.append(f"No se pudo eliminar {os.path.basename(file_path)}: {str(e)}")
                logging.error(f"No se pudo eliminar {file_path}: {str(e)}")
        else:
            logging.info(f"Archivo no encontrado (ya limpio): {file_path}")

    if errors:
        return jsonify({'status': 'error', 'error': ' '.join(errors)}), 500
    if cleared_files:
        return jsonify({'status': 'success', 'message': f"Progreso limpiado: {', '.join(cleared_files)} eliminados."})
    else:
        return jsonify({'status': 'success', 'message': 'Progreso ya estaba limpio (no hay archivos).'})
    
@app.route('/status', methods=['GET'])
@login_required
def get_status():
    global running_process
    is_running = running_process is not None and running_process.poll() is None
    return jsonify({'is_running': is_running})

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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)