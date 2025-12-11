import os
import zipfile
from flask import Flask, redirect, render_template_string, jsonify, request, session, send_file
import threading
import time
import logging
from functools import wraps
import glob
import shutil
import re
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    _HAVE_GDRIVE = True
except Exception:
    _HAVE_GDRIVE = False

# Import the automation runner
try:
    from posweb_principal import run_automation
except Exception as e:
    run_automation = None
    logging.exception("No se pudo importar run_automation desde posweb_principal: %s", e)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '3103487201022947165sG')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'POSWEB':
            logging.info("Acceso no autorizado, redirigiendo a http://192.168.21.56:5000")
            return redirect('http://192.168.21.56:5000')
        return f(*args, **kwargs)
    return decorated_function

# Simple in-memory state
automation_thread = None
automation_lock = threading.Lock()
automation_status = {
    "running": False,
    "last_started": None,
    "message": "Idle",
    "last_parche": None,
}

# Base dir
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Default Google Drive folder ID
DEFAULT_GDRIVE_FOLDER_URL = '1K9CgElDHIq9QtoMFoAZAdQr0ed5-wy0a'

def get_latest_parche_name():
    pattern = os.path.join(BASE_DIR, 'Parche_*')
    paths = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    if not paths:
        return None
    paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return os.path.basename(paths[0])

INDEX_HTML = """
<!doctype html>
<html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>POSWeb - Control</title>
        <style>
            :root{
                --bg: #ffffff;
                --accent: #0b934d;
                --accent-2: #0f7f43;
                --muted: #6b7280;
                --card: #f6fff9;
                --shadow: rgba(11,147,77,0.12);
                --radius: 10px;
            }
            *{box-sizing: border-box}
            body{
                font-family: Inter, -apple-system, 'Segoe UI', Roboto, Arial;
                margin:0; padding:0; background: linear-gradient(180deg, #f8fff8 0%, #ffffff 100%);
                color:#05261a;
                min-height:100vh; display:flex; align-items:center; justify-content:center;
            }
            .container{
                width: min(920px, 95%);
                background: var(--card);
                border-radius: var(--radius);
                box-shadow: 0 8px 24px var(--shadow);
                padding: 28px;
                display:flex;
                gap:24px;
                align-items:flex-start;
            }
            .right{
                width:865px;
            }
            h1{margin:0 0 8px 0; font-size:1.35rem; color:var(--accent-2)}
            p.lead{
            margin:0 0 18px 0; 
            color:var(--muted)
            text-align: justify;
            
            
            }
            label{font-size:0.85rem; color:var(--muted); display:block; margin-bottom:6px}
            input[type="text"]{
                width:100%; padding:10px 12px; border-radius:8px; border:1px solid #e6f4ea; background:#fff; font-size:0.95rem;
                box-shadow: inset 0 1px 0 rgba(0,0,0,0.02);
            }
            .controls{gap:12px; margin-top:12px; align-items:center}
            button{
                background: linear-gradient(180deg,var(--accent), var(--accent-2));
                color:white; border:none; padding:10px 16px; border-radius:8px; cursor:pointer; font-weight:600;
                box-shadow: 0 8px 18px rgba(11,147,77,0.14);
            }
            button:active{transform: translateY(1px)}
            .status-card{
                background: white; border-radius:10px; padding:14px; border:1px solid #eef7ef; box-shadow:0 6px 14px rgba(5,38,26,0.03);
            }
            .status-item{font-size:0.95rem; color:#072a1a; margin-bottom:8px}
            .status-value{font-weight:700; color:var(--accent-2)}
            .muted{color:var(--muted); font-size:0.85rem}
            @media (max-width:800px){
                .container{flex-direction:column}
                .right{width:100%}
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="left">
                <h1>POSWeb</h1>
                <p class="lead">Servidor puente para controlar la automatización POSWeb.</p>
                <div>
                    <label for="versionInput">Parche / Versión</label>
                    <input id="versionInput" type="text" placeholder="Ej: 1.0.1" />
                    <div style="margin-top:12px">
                        <label>Seleccionar procesos a ejecutar</label>
                        <div id="processList" style="max-height:220px; overflow:auto; padding:8px; border-radius:8px; background:#fff; border:1px solid #eef7ef; margin-top:8px"></div>
                        <div class="muted" style="margin-top:6px">Dejar en blanco para ejecutar todos.</div>
                    </div>
                    <div class="controls">
                        <button id="startBtn">Iniciar automatización</button>
                        <button id="stopBtn" style="background:#ffffff;color:var(--accent-2);border:1px solid #e6f4ea;padding:8px 12px">Detener</button>
                        <div class="muted" style="margin-top:6px">Inicia el proceso en segundo plano</div>
                    </div>
                </div>
            </div>
            <div class="right">
                <div class="status-card">
                    <div class="status-item">Estado: <span id="status-running" class="status-value">-</span></div>
                    <div class="status-item">Último inicio: <span id="status-started" class="status-value">-</span></div>
                    <div class="status-item">Mensaje: <div id="status-message" class="muted">-</div></div>
                    <div style="margin-top:12px">
                        <label>Carpetas de Parche</label>
                        <div id="parcheList" style="max-height:260px; overflow:auto; padding:8px; border-radius:8px; background:#fff; border:1px solid #eef7ef; margin-top:8px"></div>
                        <div class="muted" style="margin-top:6px">Puedes descargar la carpeta como zip o copiarla a tu carpeta de drive configurada.</div>
                        <!-- Área de acciones rápidas para el último parche generado -->
                        <div style="margin-top:12px">
                            <label>Último parche generado</label>
                            <div class="muted" style="margin-top:6px">Cuando termine una ejecución, aquí aparecerán acciones rápidas para el parche recién creado.</div>
                            <div style="margin-top:8px; display:flex; gap:8px; align-items:center">
                                <div style="flex:1">Parche: <span id="last-parche-name" class="status-value">-</span></div>
                                <div id="lastParcheActions" style="display:none; gap:8px">
                                    <button id="downloadLastParche">Descargar último parche</button>
                                    <button id="sendLastParche" style="background:#fff;color:var(--accent-2);border:1px solid #e6f4ea">Enviar a Drive</button>
                                    <button id="copyLastParcheLocal" style="background:#fff;color:var(--accent-2);border:1px solid #e6f4ea">Copiar a carpeta local</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script>
            const DEFAULT_GDRIVE_URL = '{{ default_gdrive_url }}';
            async function loadProcessList(){
                try{
                    const res = await fetch('/processes');
                    const data = await res.json();
                    const container = document.getElementById('processList');
                    container.innerHTML = '';
                    data.forEach((name, idx) => {
                        const id = 'p_' + idx;
                        const div = document.createElement('div');
                        div.innerHTML = `<label style="display:flex; gap:8px; align-items:center"><input type="checkbox" id="${id}" value="${name}" /> <span style="font-size:0.95rem">${name}</span></label>`;
                        container.appendChild(div);
                    });
                }catch(e){ console.error('No se pudieron cargar los procesos', e) }
            }
            async function updateStatus(){
                const res = await fetch('/status');
                const data = await res.json();
                document.getElementById('status-running').innerText = data.running ? 'En ejecución' : 'Inactivo';
                document.getElementById('status-started').innerText = data.last_started || '-';
                document.getElementById('status-message').innerText = data.message || '-';
            }
            document.getElementById('startBtn').addEventListener('click', async () => {
                const version = document.getElementById('versionInput').value || null;
                const checkboxes = document.querySelectorAll('#processList input[type=checkbox]');
                const selected = [];
                checkboxes.forEach(ch => { if(ch.checked) selected.push(ch.value) });
                const payload = { version };
                if(selected.length) payload['selected_steps'] = selected;
                const res = await fetch('/start', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
                const data = await res.json();
                alert(data.message);
                updateStatus();
            });
            loadProcessList();
            document.getElementById('stopBtn').addEventListener('click', async () => {
                const res = await fetch('/stop', { method: 'POST' });
                const data = await res.json();
                alert(data.message);
                updateStatus();
            });
            updateStatus();
            setInterval(updateStatus, 3000);
            async function loadParcheList(){
                try{
                    const res = await fetch('/parches');
                    const data = await res.json();
                    const container = document.getElementById('parcheList');
                    container.innerHTML = '';
                    data.forEach(name => {
                        const div = document.createElement('div');
                        div.style.display = 'flex';
                        div.style.justifyContent = 'space-between';
                        div.style.alignItems = 'center';
                        div.style.padding = '6px 4px';
                        div.innerHTML = `<div style="flex:1">${name}</div><div style="display:flex;gap:8px"><button data-name="${name}" class="downloadParche">Descargar</button><button data-name="${name}" class="copyParche" style="background:#fff;color:var(--accent-2);border:1px solid #e6f4ea">Copiar a Drive</button></div>`;
                        container.appendChild(div);
                    });
                    document.querySelectorAll('.downloadParche').forEach(btn => btn.addEventListener('click', async (e) => {
                        const name = e.currentTarget.dataset.name;
                        window.location = `/view_parche?name=${encodeURIComponent(name)}`;
                    }));
                    document.querySelectorAll('.copyParche').forEach(btn => btn.addEventListener('click', async (e) => {
                        const name = e.currentTarget.dataset.name;
                        const dest = prompt('Ingrese la carpeta destino completa donde desea copiar el parche (por ejemplo: D:\\MiDrive\\Parches). Dejar vacío para usar la carpeta por defecto del servidor:', '');
                        if(dest === null) return;
                        const res = await fetch('/copy_parche', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, dest }) });
                        const data = await res.json();
                        alert(data.message);
                    }));
                }catch(e){ console.error('No se pudieron cargar los parches', e) }
            }
            loadParcheList();
            // Mostrar acciones para el último parche cuando exista
            document.getElementById('downloadLastParche').addEventListener('click', () => {
                const name = document.getElementById('last-parche-name').innerText;
                if(!name || name === '-') return alert('No hay parche disponible');
                window.location = `/download_parche?name=${encodeURIComponent(name)}`;
            });
            document.getElementById('sendLastParche').addEventListener('click', async () => {
                const name = document.getElementById('last-parche-name').innerText;
                if(!name || name === '-') return alert('No hay parche disponible');
                const dest = prompt('Ingrese URL de Google Drive (carpeta) o deje vacío para usar la carpeta por defecto:', DEFAULT_GDRIVE_URL);
                if(dest === null) return;
                const res = await fetch('/copy_parche', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, dest }) });
                const data = await res.json();
                alert(data.message);
            });
            document.getElementById('copyLastParcheLocal').addEventListener('click', async () => {
                const name = document.getElementById('last-parche-name').innerText;
                if(!name || name === '-') return alert('No hay parche disponible');
                const dest = prompt('Ingrese la ruta local destino (por ejemplo: D:\\MiDrive\\Parches). Dejar vacío para usar DRIVE_ROOT si está configurado:', '');
                if(dest === null) return;
                const res = await fetch('/copy_parche', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, dest }) });
                const data = await res.json();
                alert(data.message);
            });
            setInterval(loadParcheList, 5000);
            // Actualiza la interfaz cuando cambie el estado (muestra acciones para last_parche)
            const _lastStatus = { running: null };
            const origUpdateStatus = updateStatus;
            async function updateStatusWithActions(){
                const res = await fetch('/status');
                const data = await res.json();
                document.getElementById('status-running').innerText = data.running ? 'En ejecución' : 'Inactivo';
                document.getElementById('status-started').innerText = data.last_started || '-';
                document.getElementById('status-message').innerText = data.message || '-';
                // last parche handling
                const last = data.last_parche || null;
                document.getElementById('last-parche-name').innerText = last || '-';
                const actions = document.getElementById('lastParcheActions');
                if(last){ actions.style.display = 'inline-flex'; } else { actions.style.display = 'none'; }
                // detect transition from running -> not running to optionally auto-show UI
                if(_lastStatus.running === true && data.running === false){
                    // automation just finished
                    if(last){
                        // reload parche list to ensure new parche is visible
                        loadParcheList();
                        // focus the actions area (visual cue)
                        actions.scrollIntoView({behavior:'smooth', block:'center'});
                    }
                }
                _lastStatus.running = data.running;
            }
            // replace the periodic status updater with the enhanced one
            updateStatusWithActions();
            setInterval(updateStatusWithActions, 3000);
        </script>
    </body>
</html>
"""

def _run_wrapper_with_version(version=None):
    global automation_status
    try:
        automation_status['running'] = True
        automation_status['message'] = f'Starting (version={version})'
        automation_status['last_started'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if not run_automation:
            automation_status['message'] = 'run_automation not available (import error)'
            return
        try:
            run_automation(version=version, interactive=False)
        except TypeError:
            run_automation()
        automation_status['message'] = 'Completed'
        try:
            automation_status['last_parche'] = get_latest_parche_name()
        except Exception:
            automation_status['last_parche'] = None
    except Exception as e:
        logging.exception('Error running automation: %s', e)
        automation_status['message'] = f'Error: {e}'
    finally:
        automation_status['running'] = False

def _run_wrapper_with_version_with_steps(version=None, selected_steps=None):
    global automation_status
    try:
        automation_status['running'] = True
        automation_status['message'] = f'Starting (version={version})'
        automation_status['last_started'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if not run_automation:
            automation_status['message'] = 'run_automation not available (import error)'
            return
        try:
            run_automation(version=version, interactive=False, selected_steps=selected_steps)
        except TypeError:
            run_automation()
        automation_status['message'] = 'Completed'
        try:
            automation_status['last_parche'] = get_latest_parche_name()
        except Exception:
            automation_status['last_parche'] = None
    except Exception as e:
        logging.exception('Error running automation: %s', e)
        automation_status['message'] = f'Error: {e}'
    finally:
        automation_status['running'] = False

def is_gdrive_url(dest):
    if not dest or not isinstance(dest, str):
        return False
    return 'drive.google.com' in dest or re.match(r'^[a-zA-Z0-9_-]{10,}$', dest)

def extract_gdrive_folder_id(url):
    m = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{10,}$', url):
        return url
    return None

def upload_folder_to_gdrive(folder_path, folder_id):
    CLIENT_SECRETS_FILE = r"C:\\Users\\dforero\\Pictures\\Proyecto_Automatizaciones_Completo\\LoginPosWEB\\client_secret_777079944211-b8j5p3ij4t9s6estq9fjt16p9jeo8bdm.apps.googleusercontent.com.json"
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        creds = flow.run_local_server(port=0)  # Abre el navegador para iniciar sesión
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        
        folder_name = os.path.basename(folder_path)
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [folder_id]
        }
        logging.info(f'Creando carpeta en Google Drive: {folder_name} en folder_id: {folder_id}')
        created_folder = service.files().create(body=folder_metadata, fields='id').execute()
        created_folder_id = created_folder.get('id')
        logging.info(f'Carpeta creada con ID: {created_folder_id}')
        
        for root, dirs, files in os.walk(folder_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, folder_path)
                file_metadata = {
                    'name': rel_path.replace(os.sep, '/'),
                    'parents': [created_folder_id]
                }
                logging.info(f'Subiendo archivo: {file_path} a carpeta {created_folder_id}')
                media = MediaFileUpload(file_path, resumable=True)
                service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                logging.info(f'Archivo subido: {file_name}')
        
        return {'id': created_folder_id, 'name': folder_name}
    except Exception as e:
        logging.exception(f'Error al subir carpeta a Google Drive: {e}')
        raise

def list_parches_on_disk():
    pattern = os.path.join(BASE_DIR, 'Parche_*')
    paths = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    folders = [os.path.basename(p) for p in paths]
    return folders

def zip_parche_folder(name):
    folder_path = os.path.join(BASE_DIR, name)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise FileNotFoundError('Parche no encontrado')
    zip_name = os.path.join(BASE_DIR, f"{name}.zip")
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, folder_path)
                zf.write(abs_path, arcname=os.path.join(name, rel_path))
    return zip_name

def copy_parche_to_drive(name, dest=None):
    src = os.path.join(BASE_DIR, name)
    if not os.path.exists(src) or not os.path.isdir(src):
        raise FileNotFoundError('Parche no encontrado')
    
    drive_root = os.environ.get('DRIVE_ROOT')
    if dest:
        dest_path = os.path.abspath(dest)
    else:
        if not drive_root:
            raise EnvironmentError('DRIVE_ROOT no está configurada y no se proporcionó dest')
        dest_path = os.path.abspath(os.path.join(drive_root, name))
    
    if os.name == 'nt':
        if len(os.path.splitdrive(dest_path)[1].strip('\\')) == 0:
            raise EnvironmentError('Destino no válido')
    else:
        if dest_path == '/' or dest_path == '':
            raise EnvironmentError('Destino no válido')
    
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)
    shutil.copytree(src, dest_path)
    return dest_path

@app.route('/')
@login_required
def index():
    default_url = os.environ.get('DRIVE_GDRIVE_FOLDER') or DEFAULT_GDRIVE_FOLDER_URL
    return render_template_string(INDEX_HTML, default_gdrive_url=default_url)

@app.route('/start', methods=['POST'])
@login_required
def start():
    global automation_thread
    with automation_lock:
        if automation_status['running']:
            return jsonify({'ok': False, 'message': 'La automatización ya está en ejecución.'}), 409
        try:
            payload = request.get_json(silent=True)
        except Exception:
            payload = None
        version = None
        if payload and isinstance(payload, dict):
            version = payload.get('version')
            selected_steps = payload.get('selected_steps')
        automation_status['running'] = True
        automation_status['message'] = 'Starting'
        automation_status['last_started'] = time.strftime('%Y-%m-%d %H:%M:%S')
        automation_thread = threading.Thread(target=lambda: _run_wrapper_with_version_with_steps(version, selected_steps), daemon=True)
        automation_thread.start()
        return jsonify({'ok': True, 'message': 'Automatización iniciada.'})

@app.route('/status')
@login_required
def status():
    return jsonify(automation_status)

@app.route('/processes')
@login_required
def processes():
    try:
        import posweb_principal
        if hasattr(posweb_principal, 'available_processes'):
            names = posweb_principal.available_processes()
            return jsonify(names)
        else:
            return jsonify([])
    except Exception as e:
        logging.exception('Error fetching processes: %s', e)
        return jsonify([]), 500

@app.route('/stop', methods=['POST'])
@login_required
def stop():
    try:
        import posweb_principal
        if hasattr(posweb_principal, 'request_stop'):
            posweb_principal.request_stop()
            automation_status['message'] = 'Stop requested'
            return jsonify({'ok': True, 'message': 'Solicitud de parada enviada.'})
        else:
            return jsonify({'ok': False, 'message': 'El módulo no soporta parada.'}), 501
    except Exception as e:
        logging.exception('Error al solicitar parada: %s', e)
        return jsonify({'ok': False, 'message': f'Error: {e}'}), 500

@app.route('/parches')
@login_required
def parches():
    try:
        folders = list_parches_on_disk()
        return jsonify(folders)
    except Exception as e:
        logging.exception('Error listando parches: %s', e)
        return jsonify([]), 500

@app.route('/download_parche')
@login_required
def download_parche():
    name = request.args.get('name')
    if not name:
        return jsonify({'ok': False, 'message': 'Falta parametro name'}), 400
    accept = request.headers.get('Accept', '')
    if 'text/html' in accept:
        return redirect(f'/view_parche?name={name}')
    try:
        zip_path = zip_parche_folder(name)
        return send_file(zip_path, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'ok': False, 'message': 'Parche no encontrado'}), 404
    except Exception as e:
        logging.exception('Error creando zip: %s', e)
        return jsonify({'ok': False, 'message': str(e)}), 500

@app.route('/view_parche')
@login_required
def view_parche():
    name = request.args.get('name')
    if not name:
        return 'Missing name', 400
    folder_path = os.path.join(BASE_DIR, name)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        logging.warning('view_parche: requested parche name %s resolved to path %s which does not exist', name, folder_path)
        available = list_parches_on_disk()
        if available:
            list_html = '\n'.join([f"<li>{p}</li>" for p in available])
            return f"<html><body><h3>Parche '{name}' no encontrado</h3><p>Parches disponibles:</p><ul>{list_html}</ul></body></html>", 404
        else:
            return f"<html><body><h3>Parche '{name}' no encontrado</h3><p>No se encontraron parches en el directorio.</p></body></html>", 404
    items = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, folder_path)
            items.append(rel.replace('\\', '/'))
    list_html = '\n'.join([f"<li><a href='/serve_parche_file?name={name}&file={f}' target='_blank'>{f}</a></li>" for f in items])
    page = f"""
    <html><body>
    <h2>Contenido de {name}</h2>
    <ul>{list_html}</ul>
    <div style='margin-top:12px'>
      <button onclick="window.location='/download_parche?name={name}'">Descargar ZIP</button>
      <button onclick="fetch('/copy_parche', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{'name':'{name}', 'dest':'{os.environ.get('DRIVE_GDRIVE_FOLDER') or DEFAULT_GDRIVE_FOLDER_URL}'}}) }}).then(r=>r.json()).then(j=>alert(j.message))">Enviar a Drive</button>
    </div>
    </body></html>
    """
    return page

@app.route('/serve_parche_file')
@login_required
def serve_parche_file():
    name = request.args.get('name')
    file = request.args.get('file')
    if not name or not file:
        return 'Missing params', 400
    folder_path = os.path.join(BASE_DIR, name)
    file_path = os.path.join(folder_path, file)
    if not os.path.exists(file_path):
        return 'File not found', 404
    return send_file(file_path, as_attachment=True)

@app.route('/copy_parche', methods=['POST'])
@login_required
def copy_parche():
    try:
        payload = request.get_json(silent=True) or {}
        name = payload.get('name')
        dest = payload.get('dest')
        logging.info(f'copy_parche llamado con payload: {payload}')
        if not name:
            logging.error('Falta el parámetro "name" en el payload')
            return jsonify({'ok': False, 'message': 'Falta name en body'}), 400
        
        folder_path = os.path.join(BASE_DIR, name)
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logging.error(f'Parche no encontrado: {folder_path}')
            return jsonify({'ok': False, 'message': 'Parche no encontrado'}), 404

        drive_folder_url = dest or os.environ.get('DRIVE_GDRIVE_FOLDER') or DEFAULT_GDRIVE_FOLDER_URL
        logging.info(f'Destino seleccionado: {drive_folder_url}')
        
        if is_gdrive_url(drive_folder_url):
            folder_id = extract_gdrive_folder_id(drive_folder_url)
            logging.info(f'ID de carpeta extraído: {folder_id}')
            if not folder_id:
                logging.error(f'No se pudo extraer el folder id de la URL: {drive_folder_url}')
                return jsonify({'ok': False, 'message': 'No se pudo extraer el folder id de la URL de Drive'}), 400
            
            try:
                logging.info(f'Subiendo carpeta {name} a Google Drive')
                created = upload_folder_to_gdrive(folder_path, folder_id)
                logging.info(f'Carpeta subida a Drive: {created}')
                return jsonify({
                    'ok': True,
                    'message': f'Carpeta subida a Google Drive (id: {created.get("id")})',
                    'drive_file': created
                }), 200
            except EnvironmentError as ee:
                logging.error(f'Error de entorno al subir a Drive: {ee}')
                return jsonify({'ok': False, 'message': str(ee)}), 500
            except Exception as e:
                logging.exception(f'Error subiendo a Drive: {e}')
                return jsonify({'ok': False, 'message': f'Error al subir a Drive: {str(e)}'}), 500
        
        dest_path = copy_parche_to_drive(name, dest=dest)
        logging.info(f'Parche copiado localmente a: {dest_path}')
        return jsonify({'ok': True, 'message': f'Parche copiado a {dest_path}'}), 200
    except EnvironmentError as ee:
        logging.error(f'Error de entorno: {ee}')
        return jsonify({'ok': False, 'message': str(ee)}), 400
    except FileNotFoundError:
        logging.error(f'Parche no encontrado: {name}')
        return jsonify({'ok': False, 'message': 'Parche no encontrado'}), 404
    except Exception as e:
        logging.exception(f'Error inesperado en copy_parche: {e}')
        return jsonify({'ok': False, 'message': f'Error inesperado: {str(e)}'}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename='app.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')
    app.run(host='0.0.0.0', port=5006)