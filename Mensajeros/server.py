from flask import Flask, render_template, jsonify, request, session, redirect
import socket
import threading
import mensajeros
import os
import sys
import subprocess
import logging
from functools import wraps
from typing import Optional

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos de expiración de sesión

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'mensajeros':
            logging.info("Acceso no autorizado, redirigiendo a http://192.168.21.36:5000")
            return redirect('http://192.168.21.36:5000')
        return f(*args, **kwargs)
    return decorated_function

# NOTE: removed a duplicate /api/status route that exposed internals. The
# /api/status route later in this file reports whether the automation child
# process is running and is the single canonical status endpoint.

# Endpoint to run a light-weight action (like leer_checkpoint)
@app.route('/api/checkpoint', methods=['GET','POST'])
def checkpoint():
    if request.method == 'GET':
        try:
            value = mensajeros.leer_checkpoint()
            return jsonify({'ok': True, 'checkpoint': value})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
    else:
        data = request.json or {}
        value = data.get('value')
        try:
            if value is None:
                return jsonify({'ok': False, 'error': 'value required'}), 400
            mensajeros.guardar_checkpoint(int(value))
            return jsonify({'ok': True, 'checkpoint': int(value)})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

automation_lock = threading.Lock()
# Manage an automation subprocess that runs mensajeros.py
automation_process: Optional[subprocess.Popen] = None
automation_log_file = None


@app.route('/api/start', methods=['POST'])
def start_automation():
    """Start mensajeros.py as a background process using the same Python executable."""
    global automation_process, automation_log_file
    with automation_lock:
        if automation_process and automation_process.poll() is None:
            return jsonify({'ok': False, 'error': 'Automation already running', 'pid': automation_process.pid}), 400

        script_path = os.path.join(os.path.dirname(__file__), 'mensajeros.py')
        if not os.path.exists(script_path):
            return jsonify({'ok': False, 'error': f"Script not found: {script_path}"}), 500

        # Before starting, ensure sheet3 has the activation flag set to 'En ejecución'
        try:
            client, credentials, sheet, sheet2, sheet3, SPREADSHEET_ID, SHEET_NAME2 = mensajeros.inicializar_sheets()
        except Exception as e:
            return jsonify({'ok': False, 'error': f'Could not initialize Google Sheets: {e}'}), 500

        try:
            # write activation value exactly as the automation expects
            sheet3.update_acell('B2', 'En ejecución')
        except Exception as e:
            return jsonify({'ok': False, 'error': f'Could not set activation cell B2 on sheet3: {e}'}), 500

        try:
            # Open a log file in append+binary mode so output is preserved
            log_path = os.path.join(os.path.dirname(__file__), 'automation.log')
            automation_log_file = open(log_path, 'ab')
            # Start the script with the same python interpreter
            automation_process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=automation_log_file,
                stderr=subprocess.STDOUT,
                cwd=os.path.dirname(__file__)
            )

            # Wait briefly to ensure the child didn't immediately exit due to an error
            wait_seconds = 2
            try:
                automation_process.wait(timeout=wait_seconds)
                # If wait returns, the process exited quickly — read tail of log and return error
                # Close the file handle to flush
                try:
                    automation_log_file.flush()
                except Exception:
                    pass
                # Read a small tail for diagnostic purposes
                tail = ''
                try:
                    with open(log_path, 'rb') as f:
                        f.seek(0, os.SEEK_END)
                        size = f.tell()
                        read_from = max(0, size - 1024)
                        f.seek(read_from)
                        tail = f.read().decode('utf-8', errors='replace')
                except Exception:
                    tail = '<could not read log>'

                exit_code = automation_process.returncode
                automation_process = None
                automation_log_file.close()
                automation_log_file = None
                return jsonify({'ok': False, 'error': f'Process exited early (code {exit_code})', 'log_tail': tail}), 500
            except subprocess.TimeoutExpired:
                # Child still running after wait_seconds — good
                return jsonify({'ok': True, 'message': 'Automation started', 'pid': automation_process.pid})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def stop_automation():
    """Stop the running mensajeros.py process if any."""
    global automation_process, automation_log_file
    with automation_lock:
        if not automation_process or automation_process.poll() is not None:
            return jsonify({'ok': False, 'error': 'No automation process running'}), 400
        try:
            automation_process.terminate()
            try:
                automation_process.wait(timeout=10)
            except Exception:
                automation_process.kill()
            pid = automation_process.pid
            automation_process = None
            if automation_log_file:
                try:
                    automation_log_file.close()
                except Exception:
                    pass
                automation_log_file = None
            # Try to restore the sheet activation flag to 'SI' so the automation can be re-enabled later
            try:
                client, credentials, sheet, sheet2, sheet3, SPREADSHEET_ID, SHEET_NAME2 = mensajeros.inicializar_sheets()
                try:
                    sheet3.update_acell('B2', 'SI')
                except Exception:
                    pass
            except Exception:
                pass

            return jsonify({'ok': True, 'message': 'Stopped', 'pid': pid})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/status')
def automation_status():
    """Return whether the automation subprocess is running and its PID."""
    global automation_process
    running = False
    pid = None
    if automation_process and automation_process.poll() is None:
        running = True
        pid = automation_process.pid
    return jsonify({'ok': True, 'running': running, 'pid': pid})

@app.route('/')
@login_required
def index():
    # Determine local IP address for convenience
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return render_template('index.html', ip=local_ip, port=5007)

if __name__ == '__main__':
    # Bind to 0.0.0.0 to be reachable via LAN IP
    app.run(host='0.0.0.0', port=5007)
