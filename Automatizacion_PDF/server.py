# server.py (VERSIÓN ACTUALIZADA CON BOTÓN MOVER PROCESADOS)
import os
import sys
import tempfile
import shutil
import traceback
import time
from datetime import datetime
from pickle import load, dump

from flask import Flask, request, jsonify, send_from_directory, Response, session, redirect
from functools import wraps
import queue
from flask_cors import CORS

from recibos_energia import (
    extraer_paginas_pdf,
    extraer_datos_factura,
    generar_excel_facturas,
    HEADERS_BASE
)

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from PyPDF2 import PdfReader, PdfWriter
import io

# 🔥 COLA PARA MENSAJES EN TIEMPO REAL
mensajes_queue = queue.Queue()

def log_mensaje(tipo, texto, mostrar_en_web=True):
    """Envía un mensaje a la cola"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    mensaje = f"[{timestamp}] {tipo}: {texto}"
    print(mensaje)
    
    if mostrar_en_web:
        mensajes_queue.put(mensaje)

APP = Flask(__name__)
APP.secret_key = '3103487201022947165sG'  # MISMA del servidor principal
APP.config['PERMANENT_SESSION_LIFETIME'] = 1800

CORS(APP, supports_credentials=True, origins=[
    "http://192.168.20.8:5000",
    "http://localhost:5000",
    "http://192.168.20.8:5010",
    "http://localhost:5010"
])

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'pdf':
            return redirect('http://192.168.20.8:5000')
        return f(*args, **kwargs)
    return decorated_function

# 🔥 CARPETAS LOCALES
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'descargas')
TEMP_PDFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_pdfs')

if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)
if not os.path.exists(TEMP_PDFS_DIR):
    os.makedirs(TEMP_PDFS_DIR)

# 🔥 GOOGLE DRIVE CONFIG
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credenciales_google.json')
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file']
CARPETA_ENTRADA_ID = "1eveBX7jxaV1O8aawhldyTWeMVzBqutZQ"
CARPETA_SEPARADOS_ID = "1NXNT-9tsn_6bDLJIIgwGNjIPJmyEidqL"
CARPETA_EXCEL_ID = "1z4__4EDoV_CT0z-aHupEYgrTa7W_FatA"
CARPETA_PROCESADOS_ID = "1qLOSo4MlX0A-pev4BQaxhazxh4ZjC7-b"
CARPETA_FINALIZADOS_ID = "1xRFAm-Av5cAxxAcW0j-239mfjw-ACd4H"

# 🔥 ESTADO GLOBAL
estado_actual = {
    'pdf_encontrado': None,
    'pdf_dividido': False,
    'facturas_analizadas': [],
    'pdf_original_name': None,
    'pdfs_recortados': [],
    'service': None,
    'pdf_original_id': None
}

# ==================== AUTENTICACIÓN GOOGLE DRIVE ====================

def autenticar_google_drive():
    """Autentica con Google Drive"""
    creds = None
    token_file = 'token.pickle'
    
    try:
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=8080, open_browser=True)
            
            with open(token_file, 'wb') as token:
                dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    except Exception as e:
        print(f"⚠️ Error autenticando Google Drive: {e}")
        return None

def buscar_archivos_en_carpeta(service, carpeta_id, extension=None):
    """Busca archivos en una carpeta de Google Drive"""
    try:
        query = f"'{carpeta_id}' in parents and trashed=false"
        
        if extension:
            query += f" and name contains '{extension}'"
        
        todos_los_archivos = []
        page_token = None
        
        while True:
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, size)',
                pageSize=1000,
                pageToken=page_token
            ).execute()
            
            archivos = results.get('files', [])
            todos_los_archivos.extend(archivos)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        print(f"✅ Total archivos encontrados: {len(todos_los_archivos)}")
        return todos_los_archivos
    
    except Exception as e:
        print(f"❌ Error buscando archivos: {e}")
        return []

def descargar_archivo_desde_drive(service, file_id, ruta_destino):
    """Descarga un archivo de Google Drive"""
    try:
        request = service.files().get_media(fileId=file_id)
        with open(ruta_destino, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        print(f"✅ Descargado: {ruta_destino}")
        return True
    except Exception as e:
        print(f"❌ Error descargando archivo: {e}")
        return False

def subir_archivo_a_drive(service, ruta_archivo, carpeta_id, nombre_archivo=None):
    """Sube un archivo a Google Drive"""
    try:
        if nombre_archivo is None:
            nombre_archivo = os.path.basename(ruta_archivo)
        
        file_metadata = {
            'name': nombre_archivo,
            'parents': [carpeta_id]
        }
        
        media = MediaFileUpload(ruta_archivo, resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"✅ Subido: {nombre_archivo}")
        return file['id']
    
    except Exception as e:
        print(f"❌ Error subiendo archivo: {e}")
        return None

def mover_archivo_en_drive(service, file_id, nueva_carpeta_id):
    """Mueve un archivo a otra carpeta en Google Drive"""
    try:
        file = service.files().get(fileId=file_id, fields='parents').execute()
        parents = ",".join(file.get('parents', []))
        
        file = service.files().update(
            fileId=file_id,
            addParents=nueva_carpeta_id,
            removeParents=parents,
            fields='id'
        ).execute()
        
        return True
    except Exception as e:
        print(f"❌ Error moviendo archivo: {e}")
        return False

# ==================== PROCESAR LOTE LOCAL ====================

@APP.route('/procesar-lote', methods=['POST'])
def procesar_lote():
    """Procesa PDFs locales: divide, sube a Drive y genera Excel"""
    global estado_actual
    
    try:
        # Verificar que haya archivos
        if 'files' not in request.files or len(request.files.getlist('files')) == 0:
            return jsonify({'success': False, 'error': 'No hay archivos'}), 400
        
        archivos = request.files.getlist('files')
        log_mensaje('📥', f'Se subieron {len(archivos)} archivo(s)')
        
        # Crear carpeta temporal para este lote
        lote_dir = tempfile.mkdtemp(prefix='lote_')
        carpeta_separados_local = os.path.join(lote_dir, 'separados')
        
        if not os.path.exists(carpeta_separados_local):
            os.makedirs(carpeta_separados_local)
        
        todas_las_facturas = []
        archivos_subidos_drive = []
        
        # Autenticar para subir a Drive
        service = autenticar_google_drive()
        if service:
            log_mensaje('✅', 'Autenticado con Google Drive')
        else:
            log_mensaje('⚠️', 'Sin conexión a Google Drive (proceso local)')
        
        # PASO 1: Guardar archivos subidos
        archivos_guardados = []
        for archivo in archivos:
            ruta_archivo = os.path.join(lote_dir, archivo.filename)
            archivo.save(ruta_archivo)
            archivos_guardados.append(ruta_archivo)
            log_mensaje('✅', f'Guardado: {archivo.filename}')
        
        # PASO 2: Procesar cada PDF
        for ruta_pdf in archivos_guardados:
            pdf_nombre = os.path.basename(ruta_pdf)
            log_mensaje('📄', f'Procesando: {pdf_nombre}')
            
            # Verificar si necesita división
            lector = PdfReader(ruta_pdf)
            total_paginas = len(lector.pages)
            
            log_mensaje('📊', f'{pdf_nombre} tiene {total_paginas} página(s)')
            
            # PASO 3: Dividir si es necesario
            if total_paginas > 2:
                log_mensaje('✂️', f'Dividiendo {pdf_nombre}...')
                
                import re
                
                # 🔥 CORRECCIÓN: Definir la lista ANTES de usarla
                archivos_divididos = []  # ← ¡ESTA ES LA LÍNEA QUE FALTABA!
                
                # Extraer SOLO páginas con contenido válido
                paginas_validas = extraer_paginas_pdf(ruta_pdf)
                
                if not paginas_validas:
                    log_mensaje('⚠️', 'No se encontraron páginas con contenido válido')
                    continue
                
                log_mensaje('📖', f'Procesando {len(paginas_validas)} página(s) válida(s) de {total_paginas} totales')
                
                for pagina_info in paginas_validas:
                    num_pagina_real = pagina_info['numero']
                    texto_pagina = pagina_info['texto']
                    
                    page = lector.pages[num_pagina_real - 1]
                    
                    escritor = PdfWriter()
                    escritor.add_page(page)
                    
                    cliente_nombre = None
                    
                    try:
                        match_numero = re.search(r'(\d{7}-\d)(?:\s*[\d\w])', texto_pagina)
                        
                        if match_numero:
                            numero_cliente = match_numero.group(1).strip()
                            
                            patron = rf'{re.escape(numero_cliente)}\s*\n?\s*([\d\w].*?)(?:\n(?:CL|KR|AC|DG|AV|AVENIDA|CALLE|CARRERA|AK|PZ|TV|VT|RA|AP|MNZ|ZN|BRR|SM|LT|MZ)\s+|\n\n|$)'
                            match_nombre = re.search(patron, texto_pagina, re.DOTALL)
                            
                            if match_nombre:
                                nombre_cliente = match_nombre.group(1).strip()
                                nombre_cliente = re.sub(r'\s+', ' ', nombre_cliente)
                                
                                nombre_cliente_limpio = re.sub(r'[^\w\s\.\-&]', '', nombre_cliente)
                                nombre_cliente_limpio = nombre_cliente_limpio.replace(' ', '_').upper()
                                
                                datos = extraer_datos_factura(
                                    texto_pagina,
                                    pdf_path=ruta_pdf,
                                    numero_pagina=num_pagina_real
                                )
                                
                                # MES
                                mes = ""
                                if datos and datos.get("Fecha_Inicial"):
                                    match_fecha = re.search(r'\d{2}\s+([A-Z]{3})\s*/(\d{4})', datos["Fecha_Inicial"])
                                    if match_fecha:
                                        mes = f"{match_fecha.group(1)}{match_fecha.group(2)[-2:]}"
                                
                                # GRUPO
                                grupo = ""
                                if datos and datos.get("Cuenta_Padre"):
                                    if datos["Cuenta_Padre"] == "3968375":
                                        grupo = "GA"
                                    elif datos["Cuenta_Padre"] == "8150280":
                                        grupo = "GB"
                                
                                cliente_nombre = f"{numero_cliente} {nombre_cliente_limpio} {mes} {grupo}"
                            else:
                                cliente_nombre = numero_cliente
                    
                    except Exception as e:
                        log_mensaje('⚠️', f'Error página {num_pagina_real}: {str(e)}')
                    
                    if not cliente_nombre:
                        log_mensaje('⏭️', f'Página {num_pagina_real} ignorada (sin datos válidos)')
                        continue
                    
                    nombre = f"{cliente_nombre}.pdf"
                    nombre = re.sub(r'[\n\r\t:\"/<>|?*\\]', '', nombre)
                    
                    ruta_completa = os.path.join(carpeta_separados_local, nombre)
                    
                    with open(ruta_completa, "wb") as f:
                        escritor.write(f)
                    
                    archivos_divididos.append(ruta_completa)
                    log_mensaje('📄', f'Creado: {nombre}')
                
                log_mensaje('✅', f'Dividido en {len(archivos_divididos)} archivo(s)')
                
                # Subir PDFs divididos a Google Drive
                if service:
                    log_mensaje('📤', f'Subiendo {len(archivos_divididos)} PDFs a Google Drive...')
                    for archivo_div in archivos_divididos:
                        nombre_div = os.path.basename(archivo_div)
                        file_id = subir_archivo_a_drive(service, archivo_div, CARPETA_SEPARADOS_ID, nombre_div)
                        if file_id:
                            archivos_subidos_drive.append({
                                'id': file_id,
                                'nombre': nombre_div
                            })
                            log_mensaje('✅', f'Subido: {nombre_div}', mostrar_en_web=False)
                
                pdfs_a_procesar = archivos_divididos
            else:
                log_mensaje('✅', f'No requiere división')
                
                # Subir el original si no se divide
                if service:
                    file_id = subir_archivo_a_drive(service, ruta_pdf, CARPETA_SEPARADOS_ID, pdf_nombre)
                    if file_id:
                        archivos_subidos_drive.append({
                            'id': file_id,
                            'nombre': pdf_nombre
                        })
                
                pdfs_a_procesar = [ruta_pdf]
            
            # PASO 4: Analizar cada PDF
            for pdf_analizar in pdfs_a_procesar:
                paginas = extraer_paginas_pdf(pdf_analizar)
                
                for pagina_info in paginas:
                    texto_pagina = pagina_info['texto']
                    
                    datos = extraer_datos_factura(
                        texto_pagina,
                        pdf_path=pdf_analizar,
                        numero_pagina=pagina_info['numero']
                    )
                    
                    if datos and datos.get("Numero_Cliente"):
                        todas_las_facturas.append(datos)
                        log_mensaje('✅', f'Factura: {datos.get("Numero_Cliente")} - {datos.get("Nombre_Cliente")}')
        
        # PASO 5: Generar Excel
        log_mensaje('📊', 'Generando Excel...')
        
        if todas_las_facturas:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_filename = f"facturas_procesadas_{timestamp}.xlsx"
            excel_path = os.path.join(DOWNLOADS_DIR, excel_filename)
            
            if generar_excel_facturas(todas_las_facturas, excel_path):
                log_mensaje('✅', f'Excel generado: {excel_filename}')
                
                # Subir Excel a Google Drive
                excel_subido = False
                if service:
                    try:
                        subir_archivo_a_drive(service, excel_path, CARPETA_EXCEL_ID, excel_filename)
                        log_mensaje('✅', 'Excel subido a Google Drive')
                        excel_subido = True
                    except:
                        excel_subido = False
                
                # Guardar estado para "Mover a Procesados"
                estado_actual['pdfs_recortados'] = [f['nombre'] for f in archivos_subidos_drive]
                estado_actual['facturas_analizadas'] = todas_las_facturas
                estado_actual['service'] = service
                estado_actual['archivos_subidos_ids'] = archivos_subidos_drive
                
                # Limpiar carpeta temporal
                try:
                    shutil.rmtree(lote_dir)
                except:
                    pass
                
                log_mensaje('✅', f'Total facturas procesadas: {len(todas_las_facturas)}')
                
                return jsonify({
                    'success': True,
                    'mensaje': f'✅ Procesamiento completado',
                    'total_procesados': len(todas_las_facturas),
                    'excel_filename': excel_filename,
                    'google_drive_subido': excel_subido,
                    'pdfs_divididos': len(archivos_subidos_drive)
                })
            else:
                return jsonify({'success': False, 'error': 'Error generando Excel'}), 500
        else:
            log_mensaje('⚠️', 'No hay facturas para exportar')
            return jsonify({'success': False, 'error': 'No se encontraron facturas'}), 400
    
    except Exception as e:
        log_mensaje('❌', f'Error: {str(e)}')
        import traceback
        log_mensaje('❌', traceback.format_exc(), mostrar_en_web=False)
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== RUTAS FLASK ====================

@APP.route('/')
def index():
    base = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base, 'templates')
    return send_from_directory(templates_dir, 'index.html')

@APP.route('/stream-logs')
def stream_logs():
    """SSE endpoint para enviar logs en tiempo real"""
    def generar():
        while True:
            try:
                mensaje = mensajes_queue.get(timeout=1)
                yield f"data: {mensaje}\n\n"
            except queue.Empty:
                yield f": heartbeat\n\n"
    
    return Response(generar(), mimetype='text/event-stream')

@APP.route('/buscar-pdf-drive', methods=['POST'])
def buscar_pdf_drive():
    """Busca PDF en Google Drive"""
    global estado_actual
    
    try:
        log_mensaje('🔍', 'Buscando PDF en Google Drive...')
        
        service = autenticar_google_drive()
        if not service:
            return jsonify({'success': False, 'error': 'No se pudo autenticar'}), 500
        
        estado_actual['service'] = service
        
        pdfs = buscar_archivos_en_carpeta(service, CARPETA_ENTRADA_ID, '.pdf')
        
        if not pdfs:
            return jsonify({'success': False, 'error': 'No hay PDFs'}), 404
        
        pdf_info = pdfs[0]
        pdf_id = pdf_info['id']
        pdf_nombre = pdf_info['name']
        
        ruta_pdf = os.path.join(TEMP_PDFS_DIR, pdf_nombre)
        
        if not descargar_archivo_desde_drive(service, pdf_id, ruta_pdf):
            return jsonify({'success': False, 'error': 'Error descargando'}), 500
        
        lector = PdfReader(ruta_pdf)
        total_paginas = len(lector.pages)
        
        estado_actual['pdf_encontrado'] = {
            'nombre': pdf_nombre,
            'ruta': ruta_pdf,
            'paginas': total_paginas,
            'id': pdf_id
        }
        estado_actual['pdf_original_name'] = pdf_nombre
        estado_actual['pdf_original_id'] = pdf_id
        
        log_mensaje('✅', f'PDF encontrado: {pdf_nombre}')
        log_mensaje('📄', f'Total de páginas: {total_paginas}')
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ PDF encontrado: {pdf_nombre}',
            'paginas': total_paginas,
            'requiere_division': total_paginas > 2
        })
    
    except Exception as e:
        log_mensaje('❌', f'Error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@APP.route('/dividir-pdf', methods=['POST'])
def dividir_pdf():
    """Divide el PDF - SOLO páginas con contenido válido"""
    global estado_actual
    
    try:
        log_mensaje('✂️', 'Dividiendo PDF...')
        
        if not estado_actual['pdf_encontrado']:
            return jsonify({'success': False, 'error': 'No hay PDF'}), 400
        
        ruta_pdf = estado_actual['pdf_encontrado']['ruta']
        service = estado_actual['service']
        
        lector = PdfReader(ruta_pdf)
        total_paginas = len(lector.pages)
        
        if total_paginas <= 2:
            log_mensaje('✅', 'PDF no requiere división')
            return jsonify({
                'success': True,
                'mensaje': 'PDF no requiere división',
                'pdfs_recortados': []
            })
        
        carpeta_salida = os.path.join(TEMP_PDFS_DIR, 'recortados')
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
        
        archivos_creados = []
        
        import re
        
        # 🔥 NUEVO: Extraer SOLO páginas con contenido válido
        paginas_validas = extraer_paginas_pdf(ruta_pdf)  # Esto ya ignora páginas en blanco
        
        if not paginas_validas:
            log_mensaje('⚠️', 'No se encontraron páginas con contenido válido')
            return jsonify({'success': False, 'error': 'No hay páginas válidas'}), 400
        
        log_mensaje('📖', f'Procesando {len(paginas_validas)} página(s) válida(s) de {total_paginas} totales')
        
        # 🔥 NUEVO: Procesar SOLO las páginas que tienen contenido
        for pagina_info in paginas_validas:
            num_pagina_real = pagina_info['numero']
            texto_pagina = pagina_info['texto']
            
            # Obtener la página del PDF original (usando índice base 0)
            page = lector.pages[num_pagina_real - 1]
            
            escritor = PdfWriter()
            escritor.add_page(page)
            
            cliente_nombre = None
            
            try:
                match_numero = re.search(r'(\d{7}-\d)(?:\s*[\d\w])', texto_pagina)
                
                if match_numero:
                    numero_cliente = match_numero.group(1).strip()
                    log_mensaje('✅', f'Página {num_pagina_real}: {numero_cliente}')
                    
                    # Buscar nombre del cliente
                    patron = rf'{re.escape(numero_cliente)}\s*\n?\s*([\d\w].*?)(?:\n(?:CL|KR|AC|DG|AV|AVENIDA|CALLE|CARRERA|AK|PZ|TV|VT|RA|AP|MNZ|ZN|BRR|SM|LT|MZ)\s+|\n\n|$)'
                    match_nombre = re.search(patron, texto_pagina, re.DOTALL)
                    
                    if match_nombre:
                        nombre_cliente = match_nombre.group(1).strip()
                        nombre_cliente = nombre_cliente.replace('\n', ' ')
                        nombre_cliente = nombre_cliente.replace('\r', ' ')
                        nombre_cliente = re.sub(r'[\n\r\t]', '', nombre_cliente)
                        nombre_cliente = re.sub(r'\s+', ' ', nombre_cliente)
                        
                        nombre_cliente_limpio = re.sub(r'[^\w\s\.\-&]', '', nombre_cliente)
                        nombre_cliente_limpio = nombre_cliente_limpio.replace(' ', '_').upper()
                        nombre_cliente_limpio = nombre_cliente_limpio.strip('_')
                        
                        from recibos_energia import extraer_datos_factura
                        
                        datos = extraer_datos_factura(
                            texto_pagina,
                            pdf_path=ruta_pdf,
                            numero_pagina=num_pagina_real
                        )
                        
                        # MES
                        mes = ""
                        if datos and datos.get("Fecha_Inicial"):
                            match_fecha = re.search(r'\d{2}\s+([A-Z]{3})\s*/(\d{4})', datos["Fecha_Inicial"])
                            if match_fecha:
                                mes = f"{match_fecha.group(1)}{match_fecha.group(2)[-2:]}"
                        
                        # GRUPO
                        grupo = ""
                        if datos and datos.get("Cuenta_Padre"):
                            if datos["Cuenta_Padre"] == "3968375":
                                grupo = "GA"
                            elif datos["Cuenta_Padre"] == "8150280":
                                grupo = "GB"
                        
                        cliente_nombre = f"{numero_cliente} {nombre_cliente_limpio} {mes} {grupo}"
                    else:
                        cliente_nombre = numero_cliente
            
            except Exception as e:
                log_mensaje('⚠️', f'Página {num_pagina_real}: Error - {str(e)}')
            
            # Si no se pudo extraer, usar número de página genérico (pero esto no debería pasar porque ya filtramos)
            if not cliente_nombre:
                cliente_nombre = f"pagina_{num_pagina_real:04d}"
                log_mensaje('⚠️', f'Página {num_pagina_real}: Usando nombre genérico')
            
            # Crear nombre del archivo
            nombre = f"{cliente_nombre}.pdf"
            nombre = re.sub(r'[\n\r\t:\"/<>|?*\\]', '', nombre)
            ruta_completa = os.path.join(carpeta_salida, nombre)
            
            with open(ruta_completa, "wb") as f:
                escritor.write(f)
            
            archivos_creados.append(ruta_completa)
            log_mensaje('📄', f'Creado: {nombre}')
        
        log_mensaje('📤', f'Subiendo {len(archivos_creados)} PDFs separados...')
        
        for archivo in archivos_creados:
            nombre = os.path.basename(archivo)
            subir_archivo_a_drive(service, archivo, CARPETA_SEPARADOS_ID, nombre)
        
        log_mensaje('✅', f'PDFs separados subidos exitosamente')
        
        estado_actual['pdf_dividido'] = True
        estado_actual['pdfs_recortados'] = [os.path.basename(a) for a in archivos_creados]
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ PDF dividido en {len(archivos_creados)} archivos (ignoradas {total_paginas - len(archivos_creados)} páginas en blanco)',
            'pdfs_recortados': estado_actual['pdfs_recortados']
        })
    
    except Exception as e:
        log_mensaje('❌', f'Error dividiendo: {str(e)}')
        import traceback
        log_mensaje('❌', traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@APP.route('/analizar-pdfs-drive', methods=['POST'])
def analizar_pdfs_drive():
    """Analiza los PDFs"""
    global estado_actual
    
    try:
        log_mensaje('📊', 'Analizando PDFs...')
        
        service = estado_actual.get('service')
        if not service:
            service = autenticar_google_drive()
            estado_actual['service'] = service
        
        if not service:
            return jsonify({'success': False, 'error': 'Error de autenticación'}), 500
        
        if estado_actual.get('pdf_dividido'):
            pdfs_encontrados = buscar_archivos_en_carpeta(service, CARPETA_SEPARADOS_ID, '.pdf')
        else:
            pdfs_encontrados = []
            if estado_actual.get('pdf_encontrado'):
                pdfs_encontrados = [{
                    'id': '',
                    'name': os.path.basename(estado_actual['pdf_encontrado']['ruta'])
                }]
        
        if not pdfs_encontrados:
            return jsonify({'success': False, 'error': 'No hay PDFs para analizar'}), 404
        
        FACTURAS_POR_LOTE = 15
        PAUSA_ENTRE_LOTES = 30
        
        facturas_analizadas = []
        pdfs_analizados = []
        facturas_en_lote = 0
        num_lote = 1
        ultimo_log_factura = None
        
        for idx, pdf_info in enumerate(pdfs_encontrados, 1):
            pdf_nombre = pdf_info['name']
            ruta_pdf_temp = os.path.join(TEMP_PDFS_DIR, pdf_nombre)
            
            if not estado_actual.get('pdf_dividido'):
                ruta_pdf_temp = estado_actual['pdf_encontrado']['ruta']
            else:
                if pdf_info['id']:
                    descargar_archivo_desde_drive(service, pdf_info['id'], ruta_pdf_temp)
            
            paginas = extraer_paginas_pdf(ruta_pdf_temp)
            
            for pagina_info in paginas:
                texto_pagina = pagina_info['texto']
                datos = extraer_datos_factura(
                    texto_pagina,
                    pdf_path=ruta_pdf_temp,
                    numero_pagina=pagina_info['numero']
                )
                
                if datos and datos.get("Numero_Cliente"):
                    facturas_analizadas.append(datos)
                    facturas_en_lote += 1
                    
                    if pdf_nombre not in pdfs_analizados:
                        pdfs_analizados.append(pdf_nombre)
                    
                    ultimo_log_factura = datos.get('Numero_Cliente')
                    
                    # 🔥 PAUSA Y LOG CADA 15 FACTURAS
                    if facturas_en_lote >= FACTURAS_POR_LOTE:
                        log_mensaje('⏸️', f'Lote {num_lote}: {facturas_en_lote} facturas procesadas')
                        log_mensaje('⏳', f'Pausa de {PAUSA_ENTRE_LOTES} segundos...')
                        
                        time.sleep(PAUSA_ENTRE_LOTES)
                        
                        facturas_en_lote = 0
                        num_lote += 1
                        log_mensaje('✅', f'Reanudando - Lote {num_lote}')
        
        log_mensaje('✅', f'Total de facturas analizadas: {len(facturas_analizadas)}')
        
        estado_actual['facturas_analizadas'] = facturas_analizadas
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ Se analizaron {len(facturas_analizadas)} facturas',
            'total_facturas': len(facturas_analizadas),
            'pdfs_analizados': pdfs_analizados
        })
    
    except Exception as e:
        log_mensaje('❌', f'Error analizando: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@APP.route('/exportar-excel-drive', methods=['POST'])
def exportar_excel_drive():
    """Genera y exporta Excel"""
    global estado_actual
    
    try:
        log_mensaje('📊', 'Generando Excel...')
        
        if not estado_actual['facturas_analizadas']:
            return jsonify({'success': False, 'error': 'No hay facturas'}), 400
        
        service = estado_actual.get('service')
        if not service:
            service = autenticar_google_drive()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"facturas_procesadas_{timestamp}.xlsx"
        excel_path = os.path.join(DOWNLOADS_DIR, excel_filename)
        
        if not generar_excel_facturas(estado_actual['facturas_analizadas'], excel_path):
            return jsonify({'success': False, 'error': 'Error generando Excel'}), 500
        
        log_mensaje('✅', f'Excel generado: {excel_filename}')
        
        if service:
            log_mensaje('📤', 'Subiendo Excel a Google Drive...')
            subir_archivo_a_drive(service, excel_path, CARPETA_EXCEL_ID, excel_filename)
            log_mensaje('✅', 'Excel subido exitosamente')
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ Excel generado: {excel_filename}',
            'excel_filename': excel_filename,
            'total_facturas': len(estado_actual['facturas_analizadas']),
            'google_drive_subido': True
        })
    
    except Exception as e:
        log_mensaje('❌', f'Error exportando: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@APP.route('/mover-procesados', methods=['POST'])
def mover_procesados():
    """Mueve archivos procesados a sus carpetas correspondientes"""
    global estado_actual
    
    try:
        log_mensaje('🔄', 'Iniciando movimiento de archivos...')
        
        service = estado_actual.get('service')
        if not service:
            service = autenticar_google_drive()
            if not service:
                return jsonify({'success': False, 'error': 'No hay autenticación'}), 500
        
        archivos_movidos = 0
        
        # 1️⃣ Mover archivos subidos desde upload local
        if estado_actual.get('archivos_subidos_ids'):
            log_mensaje('📦', f'Moviendo {len(estado_actual["archivos_subidos_ids"])} archivos a PROCESADOS...')
            
            for archivo_info in estado_actual['archivos_subidos_ids']:
                file_id = archivo_info['id']
                nombre = archivo_info['nombre']
                
                if mover_archivo_en_drive(service, file_id, CARPETA_PROCESADOS_ID):
                    archivos_movidos += 1
                    log_mensaje('✅', f'Movido: {nombre}')
            
            log_mensaje('✅', f'Archivos de upload local movidos a PROCESADOS')
            
            # Limpiar lista
            estado_actual['archivos_subidos_ids'] = []
        
        # 2️⃣ Mover PDF original a FINALIZADOS (si viene de Google Drive)
        if estado_actual.get('pdf_original_id'):
            if mover_archivo_en_drive(service, estado_actual['pdf_original_id'], CARPETA_FINALIZADOS_ID):
                archivos_movidos += 1
                log_mensaje('✅', f"PDF original movido: {estado_actual['pdf_original_name']}")
        
        # 3️⃣ Mover PDFs recortados de Google Drive a PROCESADOS
        if estado_actual.get('pdf_dividido'):
            log_mensaje('📦', 'Moviendo archivos cortados de Google Drive...')
            
            pdfs_separados = buscar_archivos_en_carpeta(service, CARPETA_SEPARADOS_ID, '.pdf')
            
            for pdf_file in pdfs_separados:
                if mover_archivo_en_drive(service, pdf_file['id'], CARPETA_PROCESADOS_ID):
                    archivos_movidos += 1
                    log_mensaje('✅', f"Movido: {pdf_file['name']}", mostrar_en_web=False)
            
            log_mensaje('✅', f'Archivos de Google Drive movidos a PROCESADOS')
        
        log_mensaje('✅', f'Movimiento completado: {archivos_movidos} archivos')
        
        # Resetear estado para nuevo flujo
        estado_actual['pdf_dividido'] = False
        estado_actual['pdfs_recortados'] = []
        estado_actual['pdf_original_id'] = None
        estado_actual['archivos_subidos_ids'] = []
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ {archivos_movidos} archivos movidos exitosamente',
            'archivos_movidos': archivos_movidos
        })
    
    except Exception as e:
        log_mensaje('❌', f'Error moviendo archivos: {str(e)}')
        import traceback
        log_mensaje('❌', traceback.format_exc(), mostrar_en_web=False)
        return jsonify({'success': False, 'error': str(e)}), 500


        
@APP.route('/descargar-excel/<filename>')
def descargar_excel(filename):
    """Descarga Excel"""
    try:
        return send_from_directory(
            DOWNLOADS_DIR,
            filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404



if __name__ == '__main__':
    log_mensaje('🚀', 'Servidor iniciado en http://localhost:5010')
    APP.run(host='0.0.0.0', port=5010, debug=False)