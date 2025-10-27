import json
from flask import Flask, jsonify, send_from_directory, request, session, redirect, Response
from functools import wraps
import subprocess
import os
import time
import logging
import threading

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800

# Decorador login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('username') != 'colpensiones':
            return redirect('http://192.168.21.36:5000')
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
log_stdout_fh = None
log_stderr_fh = None
TABLA_GUARDADA_FILE = os.path.join(os.path.dirname(__file__), "tabla_guardada.json")
ULTIMO_PROGRESO_FILE = os.path.join(os.path.dirname(__file__), "ultimo_progreso.json")

# Note: realtime log capture removed. Logs still go to server.log via logging handlers.

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
    global running_process, log_stdout_fh, log_stderr_fh
    if running_process and running_process.poll() is None:
        return jsonify({'status': 'error', 'error': 'Ya está corriendo.'}), 409
    
    try:
        script_path = os.path.abspath('Automatizacion_Colpenciones/Colpensiones.py')
        # Asegura carpeta para logs de subprocesos
        logs_dir = os.path.join(os.path.dirname(__file__), '..', 'subserver_logs')
        os.makedirs(logs_dir, exist_ok=True)
        stdout_path = os.path.join(logs_dir, 'Colpensiones_stdout.log')
        stderr_path = os.path.join(logs_dir, 'Colpensiones_stderr.log')
    # Abrir archivos para redirigir stdout/stderr y evitar bloqueo por pipes
        log_stdout_fh = open(stdout_path, 'a', encoding='utf-8')
        log_stderr_fh = open(stderr_path, 'a', encoding='utf-8')
        running_process = subprocess.Popen(
            ['python', script_path],
            stdout=log_stdout_fh,
            stderr=log_stderr_fh,
            text=True,
            bufsize=1
        )
        logging.info(f"Automatización iniciada. PID: {running_process.pid}")
        return jsonify({'status': 'success', 'message': f'Iniciada con PID {running_process.pid}.'})
    except Exception as e:
        logging.error(f"Error iniciando: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/stop-automation', methods=['POST'])
@login_required
def stop_automation():
    global running_process, log_stdout_fh, log_stderr_fh
    if running_process and running_process.poll() is None:
        try:
            pid = running_process.pid
            running_process.terminate()
            running_process.wait(timeout=10)
            logging.info(f"Detenida PID {pid} correctamente.")
            # cerrar file handles de logs si existen
            try:
                if log_stdout_fh:
                    log_stdout_fh.close()
            except Exception:
                pass
            try:
                if log_stderr_fh:
                    log_stderr_fh.close()
            except Exception:
                pass
            log_stdout_fh = None
            log_stderr_fh = None
            return jsonify({'status': 'success', 'message': f'Detenida PID {pid}.'})
        except subprocess.TimeoutExpired:
            running_process.kill()
            running_process.wait()
            logging.info(f"Detenida forzosamente PID {running_process.pid}.")
            # cerrar file handles de logs si existen
            try:
                if log_stdout_fh:
                    log_stdout_fh.close()
            except Exception:
                pass
            try:
                if log_stderr_fh:
                    log_stderr_fh.close()
            except Exception:
                pass
            log_stdout_fh = None
            log_stderr_fh = None
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


@app.route('/progress-data', methods=['GET'])
@login_required
def progress_data():
    """Return progress metrics based on tabla_guardada.json and ultimo_progreso.json.
    Response: { total: int, processed: int, percent: int }
    """
    try:
        total = 0
        processed = 0
        tabla = []

        # Load table if exists
        if os.path.exists(TABLA_GUARDADA_FILE):
            try:
                with open(TABLA_GUARDADA_FILE, 'r', encoding='utf-8') as f:
                    tabla = json.load(f) or []
                    total = len(tabla)
            except Exception as e:
                logging.error(f"Error leyendo tabla guardada: {e}")

        # Load ultimo progreso and try to compute processed count
        if os.path.exists(ULTIMO_PROGRESO_FILE):
            try:
                with open(ULTIMO_PROGRESO_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
                    ultimo_sticker = data.get('ultimo_sticker')
                    if ultimo_sticker is not None and total > 0:
                        # try to find the index of the last sticker in the table
                        for idx, row in enumerate(tabla):
                            try:
                                # table row expected format: [ciclo, no_sticker, ...]
                                if str(row[1]) == str(ultimo_sticker):
                                    processed = idx + 1
                                    break
                            except Exception:
                                continue
            except Exception as e:
                logging.error(f"Error leyendo ultimo progreso: {e}")

        percent = int(processed * 100 / total) if total > 0 else 0
        return jsonify({'total': total, 'processed': processed, 'percent': percent})
    except Exception as e:
        logging.error(f"Error generando progress-data: {e}")
        return jsonify({'error': str(e)}), 500

# Realtime logs endpoint removed. Use server.log file for logs.

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)