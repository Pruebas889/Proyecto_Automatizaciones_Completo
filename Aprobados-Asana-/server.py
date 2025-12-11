
# coding: utf-8
from functools import wraps
from flask import Flask, redirect, render_template, request, jsonify, session
import os
import logging
import subprocess
import sys
from pathlib import Path
# Nota: `aprobado.py` se ejecuta como subprocess; no importamos run_automatizacion aquí.


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos de expiración de sesión

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'aprobados':
            logging.info("Acceso no autorizado, redirigiendo a http://192.168.20.8:5000")
            return redirect('http://192.168.20.8:5000')
        return f(*args, **kwargs)
    return decorated_function



# Configuración de los logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("automatizacion.log", encoding='utf-8')
    ]
)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/run', methods=['POST'])
def run():
    sprint_number = request.form.get('sprint_number', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()

    if not sprint_number.isdigit():
        logging.error("El número de sprint debe ser un número válido.")
        return jsonify({'error': 'El número de sprint debe ser un número válido.'}), 400
    if not start_date or not end_date:
        logging.error("Las fechas de inicio y fin son requeridas.")
        return jsonify({'error': 'Las fechas de inicio y fin son requeridas.'}), 400

    sprint_number = int(sprint_number)
    logging.info(f"Iniciando automatización para Sprint {sprint_number}, {start_date} al {end_date}")

    # Leer URLs enviadas desde la interfaz (campo 'urls_text' con una URL por línea)
    urls_text = request.form.get('urls_text', '').strip()
    urls_list = []
    if urls_text:
        urls_list = [u.strip() for u in urls_text.splitlines() if u.strip()]

    # Leer correo único enviado desde la interfaz (campo 'email')
    email = request.form.get('email', '').strip()

    # Validación: requerir al menos 1 URL y un correo válido
    if not urls_list:
        msg = 'Se requiere al menos una URL para procesar.'
        logging.error(msg)
        return jsonify({'error': msg}), 400
    if not email or '@' not in email:
        msg = 'Se requiere un correo válido para asignar a todas las URLs.'
        logging.error(msg)
        return jsonify({'error': msg}), 400

    # Ejecutar `aprobado.py` como un subprocess y pasar las URLs con --urls
    try:
        aprobado_path = Path(__file__).with_name('aprobado.py')
        if not aprobado_path.exists():
            logging.error(f"No se encontró {aprobado_path}; asegúrese de que `aprobado.py` esté en el mismo directorio.")
            return jsonify({'error': f"No se encontró {aprobado_path}."}), 500

        cmd = [sys.executable, str(aprobado_path)]
        # pasar URLs
        urls_arg = ','.join(urls_list)
        cmd.extend(['--urls', urls_arg])
        # pasar único correo para todas las URLs
        cmd.extend(['--email', email])

        # Pasar variables como environment variables para que `aprobado.py` pueda leerlas si es necesario
        env = os.environ.copy()
        env.update({
            'SPRINT_NUMBER': str(sprint_number),
            'START_DATE': start_date,
            'END_DATE': end_date,
        })

        logging.info(f"Ejecutando comando: {cmd}")
        # Ajustar timeout según sea necesario (segundos)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
        except subprocess.TimeoutExpired as te:
            logging.error(f"Timeout al ejecutar `aprobado.py`: {te}")
            return jsonify({'status': 'error', 'message': 'Timeout al ejecutar la automatización.'}), 504

        stdout = proc.stdout or ''
        stderr = proc.stderr or ''
        rc = proc.returncode

        logging.info(f"`aprobado.py` finalizó con código {rc}")
        if rc == 0:
            # Devolver líneas más recientes del stdout para evitar payload demasiado grande
            out_lines = stdout.splitlines()
            return jsonify({'status': 'success', 'message': 'Automatización ejecutada con éxito.', 'results': {'stdout': out_lines, 'stderr': stderr, 'returncode': rc}})
        else:
            logging.error(f"Error en `aprobado.py`. rc={rc} stderr={stderr}")
            return jsonify({'status': 'error', 'message': 'Error en la automatización. Revisa stderr.', 'details': {'stdout': stdout, 'stderr': stderr, 'returncode': rc}}), 500
    except Exception as e:
        logging.error(f"Error al ejecutar `aprobado.py`: {e}")
        return jsonify({'status': 'error', 'message': f"Error al ejecutar la automatización: {str(e)}"}), 500

if __name__ == '__main__':
    logging.info("Iniciando el servidor de la interfaz web para Asana... 🚀")
    app.run(host='0.0.0.0', port=5009, debug=True)
