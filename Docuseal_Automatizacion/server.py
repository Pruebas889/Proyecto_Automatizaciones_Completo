from functools import wraps
import os
from flask import Flask, logging, redirect, send_from_directory, session
import subprocess

from flask import render_template
app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos de expiración de sesión

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'DocusealOP':
            logging.info("Acceso no autorizado, redirigiendo a http://192.168.21.36:5000")
            return redirect('http://192.168.21.36:5000')
        return f(*args, **kwargs)
    return decorated_function


# Registrar la ruta principal correctamente
@app.route('/')
def index():
    # Links de hojas de cálculo por rol
    sheet_links = {
        'DocusealOP': 'https://docs.google.com/spreadsheets/d/1W4YUEPY0JL6Vk9g8XTdXpA9S5ja9eQ0RI0yHyb1pLEM/edit?gid=1308134760#gid=1308134760',
        'Docuseal1OP': 'https://docs.google.com/spreadsheets/d/1c2U7Pz7azlzah04zYtOvn_UTsBSYlEqRU1Sf2kE48Tc/edit?gid=0#gid=0',
        'Docuseal2OP': 'https://docs.google.com/spreadsheets/d/ID_DE_DOCUSEAL2',
        # Agrega más roles y links si es necesario
    }
    role = session.get('role', '')
    sheet_link = sheet_links.get(role, None)
    return render_template('docuseal.html', sheet_link=sheet_link)

# Ruta para servir imágenes estáticas
@app.route('/images/<path:filename>')
def images(filename):
    return send_from_directory('images', filename)

@app.route('/start')
def start_automation():
    try:
        # Obtener credenciales y rol de la sesión
        email = session.get('username')
        password = session.get('temp_password')
        role = session.get('role')

        if not email or not password or not role:
            return 'Error: Credenciales o rol no disponibles en la sesión.', 400

        # Determinar el script según el rol
        if role == 'DocusealOP':
            script_name = 'docuseal.py'
        elif role == 'Docuseal1OP':
            script_name = 'docuseal1.py'
        elif role == 'Docuseal2OP':
            script_name = 'docuseal2.py'
        else:
            return f'Error: Rol no reconocido ({role})', 400

        script_path = os.path.join('Docuseal_Automatizacion', script_name)
        subprocess.Popen(['python', script_path, email, password])

        return f'Automatización {script_name} iniciada correctamente. Puedes verificar el progreso en la consola.'
    except Exception as e:
        return f'Error al iniciar la automatización: {str(e)}'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)