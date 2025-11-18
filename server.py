from flask import Flask, request, jsonify, redirect, url_for, session, render_template
import subprocess
import os
import time
from dotenv import load_dotenv
import mysql.connector
import bcrypt

# Configuración de la aplicación Flask
app = Flask(__name__, static_url_path='', static_folder='.')
load_dotenv()
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800

# Configuración de la conexión a MySQL
db_config = {
    'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'automatizaciones'),
    'connection_timeout': 5,
    'use_pure': True
}

# Puertos para los servidores
PORT_MAIN = 5000
PORT_CLARO = 5002
PORT_COLPENSIONES = 5001
PORT_ASANA = 5003  
PORT_REBAJA = 5004
PORT_DOCUSEAL = 5005
PORT_POSWEB = 5006
PORT_MENSAJEROS = 5007

def get_db_connection():
    print("Configuración de conexión:", db_config)
    try:
        print("Intentando conectar a MySQL...")
        conn = mysql.connector.connect(**db_config)
        print("Conexión exitosa a MySQL!")
        return conn
    except mysql.connector.Error as e:
        print(f"Error de conexión a MySQL: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None

# Ruta raíz: sirve el dashboard desde templates/dashboard.html
@app.route('/')
def dashboard():
    # Links de hojas de cálculo por rol
    sheet_links = {
        'DocusealOP': 'https://docs.google.com/spreadsheets/d/1W4YUEPY0JL6Vk9g8XTdXpA9S5ja9eQ0RI0yHyb1pLEM/edit?gid=1308134760#gid=1308134760',
        'Docuseal1OP': 'https://docs.google.com/spreadsheets/d/1c2U7Pz7azlzah04zYtOvn_UTsBSYlEqRU1Sf2kE48Tc/edit?gid=0#gid=0',
        'Docuseal2OP': 'https://docs.google.com/spreadsheets/d/ID_DE_DOCUSEAL2',
        # Agrega más roles y links si es necesario
    }
    role = session.get('role', '')
    sheet_link = sheet_links.get(role, None)
    return render_template('dashboard.html', logged_in=session.get('logged_in', False), username=session.get('username', ''), sheet_link=sheet_link)

# Rutas para login específico de cada automatización
@app.route('/login_claro')
def login_claro():
    if session.get('logged_in') and session.get('role') == 'claro':
        return redirect(f'http://192.168.21.37:{PORT_CLARO}')
    return app.send_static_file('index.html')

@app.route('/login_colpensiones')
def login_colpensiones():
    if session.get('logged_in') and session.get('role') == 'colpensiones':
        return redirect(f'http://192.168.21.37:{PORT_COLPENSIONES}')
    return app.send_static_file('index.html')

@app.route('/login_asana')
def login_asana():
    if session.get('logged_in') and session.get('role') == 'asana':
        return redirect(f'http://192.168.21.37:{PORT_ASANA}')
    return app.send_static_file('index.html')

@app.route('/login_posweb')
def login_posweb():
    if session.get('logged_in') and session.get('role') == 'POSWEB':
        return redirect(f'http://192.168.21.37:{PORT_POSWEB}')
    return app.send_static_file('index.html')

@app.route('/login_mensajeros')
def login_mensajeros():
    if session.get('logged_in') and session.get('role') == 'mensajeros':
        return redirect(f'http://192.168.21.37:{PORT_MENSAJEROS}')
    return app.send_static_file('index.html')


@app.route('/login_larebaja')
def login_larebaja():
    if session.get('logged_in') and session.get('role') == 'larebaja':
        return redirect(f'http://192.168.21.37:{PORT_REBAJA}')
    return app.send_static_file('index.html')


@app.route('/login_docuseal')
def login_docuseal():
    if session.get('logged_in') and session.get('role') == 'DocusealOP':
        return redirect(f'http://192.168.21.37:{PORT_DOCUSEAL}')
    return app.send_static_file('index.html')

# Ruta para procesar el login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    sistema = data.get('sistema')

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, password_hash, role FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Validar que el rol del usuario coincida con el sistema seleccionado
            # Para Docuseal, permitir DocusealOP, Docuseal1OP, Docuseal2OP
            if (
                (sistema == 'claro' and user['role'] == 'claro') or
                (sistema == 'colpensiones' and user['role'] == 'colpensiones') or
                (sistema == 'asana' and user['role'] == 'asana') or
                (sistema == 'POSWEB' and user['role'] == 'POSWEB') or
                (sistema == 'larebaja' and user['role'] == 'larebaja') or
                (sistema == 'mensajeros' and user['role'] == 'mensajeros') or
                (sistema == 'DocusealOP' and user['role'] in ['DocusealOP', 'Docuseal1OP', 'Docuseal2OP'])
            ):
                session['logged_in'] = True
                session['username'] = user['username']
                session['role'] = user['role']
                session.permanent = True


                if user['role'] == 'claro':
                    return jsonify({'success': True, 'redirect_url': f'http://192.168.21.37:{PORT_CLARO}'})
                elif user['role'] == 'colpensiones':
                    return jsonify({'success': True, 'redirect_url': f'http://192.168.21.37:{PORT_COLPENSIONES}'})
                elif user['role'] == 'asana':
                    return jsonify({'success': True, 'redirect_url': f'http://192.168.21.37:{PORT_ASANA}'})
                elif user['role'] == 'POSWEB':
                    return jsonify({'success': True, 'redirect_url': f'http://192.168.21.37:{PORT_POSWEB}'})
                elif user['role'] == 'larebaja':
                    return jsonify({'success': True, 'redirect_url': f'http://192.168.21.37:{PORT_REBAJA}'})
                elif user['role'] == 'mensajeros':
                    return jsonify({'success': True, 'redirect_url': f'http://192.168.21.37:{PORT_MENSAJEROS}'})
                elif user['role'] in ['DocusealOP', 'Docuseal1OP', 'Docuseal2OP']:
                    session['temp_password'] = password
                    return jsonify({'success': True, 'redirect_url': f'http://192.168.21.37:{PORT_DOCUSEAL}'})
                else:
                    return jsonify({'success': False, 'message': 'Rol no reconocido.'}), 403
            else:
                return jsonify({'success': False, 'message': 'No tienes permisos para acceder a este sistema con estas credenciales.'}), 403
        return jsonify({'success': False, 'message': 'Usuario o contraseña incorrectos.'}), 401
    except mysql.connector.Error as e:
        print(f"Error querying MySQL: {e}")
        return jsonify({'success': False, 'message': 'Error en la base de datos'}), 500

# Rutas para recuperar/actualizar contraseña
@app.route('/forgot_password', methods=['GET'])
def forgot_password_form():
    # Servir el formulario estático creado en la raíz
    return app.send_static_file('forgot_password.html')


@app.route('/forgot_password', methods=['POST'])
def forgot_password_submit():
    data = request.get_json() or {}
    username = data.get('username')
    new_password = data.get('password')
    sistema = data.get('sistema')
    old_password = data.get('old_password')

    if not username or not new_password or not old_password:
        return jsonify({'ok': False, 'error': 'username, old_password y password son requeridos'}), 400

    if not sistema:
        # Require the system context to avoid cross-system password changes
        return jsonify({'ok': False, 'error': 'Parámetro "sistema" requerido para operacion.'}), 400

    # Hash de la nueva contraseña
    try:
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        hashed_str = hashed.decode('utf-8')
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Error al hashear la contraseña: {e}'}), 500

    conn = get_db_connection()
    if not conn:
        return jsonify({'ok': False, 'error': 'No se pudo conectar a la base de datos'}), 500
    try:
        # First fetch the user's role to ensure it belongs to the same sistema
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT role, password_hash FROM users WHERE username = %s", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            cursor.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Usuario no encontrado'}), 404

        user_role = user_row.get('role')
        stored_hash = user_row.get('password_hash')

        # Verify provided old_password matches stored hash
        try:
            if not stored_hash or not bcrypt.checkpw(old_password.encode('utf-8'), stored_hash.encode('utf-8')):
                cursor.close()
                conn.close()
                return jsonify({'ok': False, 'error': 'La contraseña actual no coincide.'}), 403
        except Exception as e:
            cursor.close()
            conn.close()
            return jsonify({'ok': False, 'error': f'Error verificando la contraseña actual: {e}'}), 500

        # Map sistema -> allowed roles (Docuseal has multiple role variants)
        sistema_allowed = {
            'DocusealOP': ['DocusealOP', 'Docuseal1OP', 'Docuseal2OP'],
            # POSWEB is uppercase in your DB; keep exact match
            'POSWEB': ['POSWEB']
        }

        allowed_roles = sistema_allowed.get(sistema, [sistema])

        if user_role not in allowed_roles:
            cursor.close()
            conn.close()
            return jsonify({'ok': False, 'error': f'El usuario pertenece al rol "{user_role}" y no puede modificarse desde el sistema "{sistema}".'}), 403

        # Proceed to update
        cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (hashed_str, username))
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()

        if affected == 0:
            return jsonify({'ok': False, 'error': 'Usuario no encontrado al actualizar'}), 404
        return jsonify({'ok': True, 'message': 'Contraseña actualizada'}), 200
    except mysql.connector.Error as e:
        return jsonify({'ok': False, 'error': f'Error en la base de datos: {e}'}), 500

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('dashboard'))

# Iniciar los servidores al arrancar la aplicación
if __name__ == '__main__':
    claro_server_path = os.path.join("Recibo_Claro", "server.py")
    colpensiones_server_path = os.path.join("Automatizacion_Colpenciones", "server.py")
    asana_server_path = os.path.join("Asana-generaci-n-de-proyectos", "server.py")
    posweb_server_path = os.path.join("LoginPosWEB", "server.py")
    larebaja_server_path = os.path.join("LoginRebaja", "server.py")
    mensajeros_server_path = os.path.join("Mensajeros", "server.py")
    docuseal_server_path = os.path.join("Docuseal_Automatizacion", "server.py")
    
    if not os.path.exists(claro_server_path):
        print(f"Error: No se encontró {claro_server_path}")
    else:
        subprocess.Popen(["python", claro_server_path], cwd=os.getcwd())
        time.sleep(1)
    
    if not os.path.exists(colpensiones_server_path):
        print(f"Error: No se encontró {colpensiones_server_path}")
    else:
        subprocess.Popen(["python", colpensiones_server_path], cwd=os.getcwd())
        time.sleep(1)
    
    if not os.path.exists(asana_server_path):
        print(f"Error: No se encontró {asana_server_path}")
    else:
        subprocess.Popen(["python", asana_server_path], cwd=os.getcwd())
        time.sleep(1)

    if not os.path.exists(posweb_server_path):
            print(f"Error: No se encontró {posweb_server_path}")
    else:
        subprocess.Popen(["python", posweb_server_path], cwd=os.getcwd())

    if not os.path.exists(larebaja_server_path):
        print(f"Error: No se encontró {larebaja_server_path}")
    else:
        subprocess.Popen(["python", larebaja_server_path], cwd=os.getcwd())
        time.sleep(1)

    if not os.path.exists(mensajeros_server_path):
        print(f"Error: No se encontró {mensajeros_server_path}")
    else:
        subprocess.Popen(["python", mensajeros_server_path], cwd=os.getcwd())
        time.sleep(1)

    if not os.path.exists(docuseal_server_path):
        print(f"Error: No se encontró {docuseal_server_path}")
    else:
        subprocess.Popen(["python", docuseal_server_path], cwd=os.getcwd())
        time.sleep(1)

    print(f"Servidor principal iniciado en el puerto {PORT_MAIN}")
    print(f"Servidor de Claro iniciado en el puerto {PORT_CLARO}")
    print(f"Servidor de Colpensiones iniciado en el puerto {PORT_COLPENSIONES}")
    print(f"Servidor de Asana iniciado en el puerto {PORT_ASANA}")
    print(f"Servidor de PosWeb iniciado en el puerto {PORT_POSWEB}")
    print(f"Servidor de La Rebaja iniciado en el puerto {PORT_REBAJA}")
    print(f"Servidor de Mensajeros iniciado en el puerto {PORT_MENSAJEROS}")

    print(f"Servidor de DocusealOP iniciado en el puerto {PORT_DOCUSEAL}")

    app.run(host='0.0.0.0', port=PORT_MAIN, debug=True, use_reloader=False)