
# coding: utf-8
from functools import wraps
from flask import Flask, redirect, render_template, request, jsonify, session
import os
import logging
from asana_generacion_proyectos import run_automatizacion

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos de expiración de sesión

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'asana':
            logging.info("Acceso no autorizado, redirigiendo a http://192.168.21.37:5000")
            return redirect('http://192.168.21.37:5000')
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

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
@login_required
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

    try:
        success, results = run_automatizacion(sprint_number, start_date, end_date)
        if success:
            logging.info(f"Automatización finalizada con éxito: {results}")
            # Return an object containing a message and the results list so the frontend
            # can consistently access result.message and result.results
            return jsonify({'message': 'Automatización ejecutada con éxito.', 'results': results})
        else:
            # results may be a list (empty) or contain error details; avoid .get() on list
            logging.error(f"Error en la automatización. Detalles: {results}")
            return jsonify({'error': 'Error en la automatización. Revisa los logs.'}), 500
    except Exception as e:
        logging.error(f"Error al ejecutar run_automatizacion: {str(e)}")
        return jsonify({'error': f"Error al ejecutar la automatización: {str(e)}"}), 500

if __name__ == '__main__':
    logging.info("Iniciando el servidor de la interfaz web para Asana... 🚀")
    app.run(host='0.0.0.0', port=5003, debug=True)
