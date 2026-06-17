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
import queue
from flask_cors import CORS

from google_drive_integrador import obtener_mes_real_pdf

def generar_nombre_carpeta():
    meses = {
        1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR",
        5: "MAY", 6: "JUN", 7: "JUL", 8: "AGO",
        9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"
    }

    ahora = datetime.now()

    mes = meses[ahora.month]
    dia = ahora.day
    anio = ahora.year
    hora = ahora.strftime("%H.%M")

    return f"{mes} {dia} {anio}_{hora}"


def crear_carpeta_drive(service, nombre_carpeta, carpeta_padre_id):
    try:
        file_metadata = {
            'name': nombre_carpeta,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [carpeta_padre_id]
        }

        carpeta = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        return carpeta.get('id')

    except Exception as e:
        print(f"❌ Error creando carpeta: {e}")
        return None

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
APP.secret_key = '3103487201022947165sG'
APP.config['PERMANENT_SESSION_LIFETIME'] = 18000

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
CREDENTIALS_FILE = r'C:\Users\jperdomolc\Pictures\Proyecto_Automatizaciones_Completo\Automatizacion_PDF\credenciales_google.json'
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
    BASE_DIR = r'C:\Users\jperdomolc\Pictures\Proyecto_Automatizaciones_Completo\Automatizacion_PDF'
    token_file = os.path.join(BASE_DIR, 'token.pickle')

    # Asegurar que la carpeta exista
    os.makedirs(BASE_DIR, exist_ok=True)
    
    try:
        # 🔥 FUERZA AUTENTICACIÓN NUEVA SI NO EXISTE TOKEN
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired:
                print("🔄 Token expirado...")

                try:
                    if creds.refresh_token:
                        creds.refresh(Request())
                        print("✅ Token refrescado")
                    else:
                        print("⚠️ El token no tiene refresh_token")
                        creds = None

                except Exception as e:
                    print(f"⚠️ Error refrescando token: {e}")
                    creds = None
            
            if not creds:
                print("🔐 Iniciando nueva autenticación...")
                if not os.path.exists(CREDENTIALS_FILE):
                    print(f"❌ ERROR: Archivo {CREDENTIALS_FILE} no encontrado!")
                    print("   Descárgalo de: https://console.cloud.google.com/apis/credentials")
                    return None
                
                try:
                    # 🔥 ESTE ABRE UNA VENTANA DEL NAVEGADOR
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_FILE, SCOPES)
                    creds = flow.run_local_server(
                        port=8080, 
                        open_browser=True,
                        authorization_prompt_message='Por favor autoriza en el navegador',
                        access_type='offline'
                    )
                    print("✅ Autenticación completada!")
                except Exception as e:
                    print(f"❌ Error en flujo OAuth: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
        
        # Guardar token
        with open(token_file, 'wb') as token:
            dump(creds, token)
            print(f"✅ Token guardado en {token_file}")
        
        print("✅ Construyendo servicio de Google Drive...")
        return build('drive', 'v3', credentials=creds)
    
    except Exception as e:
        print(f"❌ Error autenticando: {e}")
        import traceback
        traceback.print_exc()
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

        # 🔥 PASO PRE-CALCULO: Calcular EXACTAMENTE cuántas páginas válidas hay en CADA PDF
        detalles_pdf = []
        total_paginas_validas_totales = 0

        for ruta_pdf in archivos_guardados:
            try:
                lector = PdfReader(ruta_pdf)
                total_paginas = len(lector.pages)
                
                # Extraer SOLO páginas con contenido válido
                paginas_validas = extraer_paginas_pdf(ruta_pdf)
                num_paginas_validas = len(paginas_validas)
                
                detalles_pdf.append({
                    'ruta': ruta_pdf,
                    'nombre': os.path.basename(ruta_pdf),
                    'total_paginas': total_paginas,
                    'paginas_validas': num_paginas_validas
                })
                
                total_paginas_validas_totales += num_paginas_validas
                
            except Exception as e:
                log_mensaje('⚠️', f'Error pre-calculando {os.path.basename(ruta_pdf)}: {e}')

        # 🔥 CALCULAR OPERACIONES REALES
        # Cada página válida = 3 operaciones: crear + subir + analizar
        total_operaciones_reales = total_paginas_validas_totales * 3

        log_mensaje('📊', f'Pre-cálculo: {total_paginas_validas_totales} páginas válidas = {total_operaciones_reales} operaciones')
        log_mensaje('TOTAL_REAL', str(total_operaciones_reales))

        # 🔥 VARIABLE GLOBAL PARA RASTREAR PROGRESO
        progreso_actual = {'count': 0}

        # PASO 2: Procesar cada PDF
        for pdf_detail in detalles_pdf:
            ruta_pdf = pdf_detail['ruta']
            pdf_nombre = pdf_detail['nombre']
            paginas_validas_esperadas = pdf_detail['paginas_validas']
            
            log_mensaje('📄', f'Procesando: {pdf_nombre} ({paginas_validas_esperadas} páginas válidas)')
            
            # PASO 3: Dividir si es necesario
            if pdf_detail['total_paginas'] > 2:
                log_mensaje('✂️', f'Dividiendo {pdf_nombre}...')
                
                import re
                
                archivos_divididos = []
                paginas_validas = extraer_paginas_pdf(ruta_pdf)
                
                if not paginas_validas:
                    log_mensaje('⚠️', 'No se encontraron páginas con contenido válido')
                    continue
                
                log_mensaje('📖', f'Procesando {len(paginas_validas)} página(s) válida(s)')
                
                lector = PdfReader(ruta_pdf)
                
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
                                
                                mes = obtener_mes_real_pdf(ruta_pdf, num_pagina_real)
                                
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
                        cliente_nombre = f"pagina_{num_pagina_real:04d}"
                    
                    nombre = f"{cliente_nombre}.pdf"
                    nombre = re.sub(r'[\n\r\t:\"/<>|?*\\]', '', nombre)
                    
                    ruta_completa = os.path.join(carpeta_separados_local, nombre)
                    
                    with open(ruta_completa, "wb") as f:
                        escritor.write(f)
                    
                    archivos_divididos.append(ruta_completa)
                    
                    # 🔥 ENVIAR PROGRESO DESPUÉS DE CADA CREACIÓN
                    progreso_actual['count'] += 1
                    log_mensaje('PROGRESO', '1')
                
                log_mensaje('✅', f'Dividido en {len(archivos_divididos)} archivo(s)')
                
                # Subir PDFs divididos a Google Drive
                if service:
                    log_mensaje('📤', f'Subiendo {len(archivos_divididos)} PDFs a Google Drive...')
                    nombre_carpeta = generar_nombre_carpeta()
                    carpeta_destino_id = crear_carpeta_drive(service, nombre_carpeta, CARPETA_SEPARADOS_ID)
                    
                    if not carpeta_destino_id:
                        carpeta_destino_id = CARPETA_SEPARADOS_ID
                    
                    estado_actual['carpeta_proceso_id'] = carpeta_destino_id
                    
                    for archivo_div in archivos_divididos:
                        nombre_div = os.path.basename(archivo_div)
                        file_id = subir_archivo_a_drive(service, archivo_div, carpeta_destino_id, nombre_div)
                        
                        if file_id:
                            archivos_subidos_drive.append({
                                'id': file_id,
                                'nombre': nombre_div
                            })
                            # 🔥 ENVIAR PROGRESO DESPUÉS DE CADA SUBIDA
                            progreso_actual['count'] += 1
                            log_mensaje('PROGRESO', '1')
                
                pdfs_a_procesar = archivos_divididos
            else:
                log_mensaje('✅', f'No requiere división')

                # Crear Carpeta para archivos de una sola pagina igualmente
                nombre_carpeta = generar_nombre_carpeta() + "(1 pagina)"

                carpeta_destino_id = None

                if service:
                    carpeta_destino_id = crear_carpeta_drive(
                        service,
                        nombre_carpeta,
                        CARPETA_SEPARADOS_ID
                    )

                    if not carpeta_destino_id:
                        carpeta_destino_id = CARPETA_SEPARADOS_ID

                    estado_actual['carpeta_proceso_id'] = carpeta_destino_id

                # Subir el pdf a esa carpeta

                if service:
                    file_id = subir_archivo_a_drive(
                        service,
                        ruta_pdf,
                        carpeta_destino_id,
                        pdf_nombre
                    )

                    if file_id:
                        archivos_subidos_drive.append({
                            'id': file_id,
                            'nombre': pdf_nombre
                        })

                        progreso_actual['count'] += 1
                        log_mensaje('PROGRESO', '1')
                pdfs_a_procesar= [ruta_pdf]
                
                # Subir el original si no se divide
                if service:
                    file_id = subir_archivo_a_drive(service, ruta_pdf, CARPETA_SEPARADOS_ID, pdf_nombre)
                    if file_id:
                        archivos_subidos_drive.append({
                            'id': file_id,
                            'nombre': pdf_nombre
                        })
                        # 🔥 ENVIAR PROGRESO DESPUÉS DE SUBIR ORIGINAL
                        progreso_actual['count'] += 1
                        log_mensaje('PROGRESO', '1')
                
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
                    
                    # 🔥 ENVIAR PROGRESO DESPUÉS DE CADA PÁGINA ANALIZADA
                    progreso_actual['count'] += 1
                    log_mensaje('PROGRESO', '1')
        # PASO 5: Generar Excel
        # 🔥 ENVIAR SEÑAL DE FINALIZACIÓN ANTES DE GENERAR EXCEL
        log_mensaje('Total facturas procesadas', str(len(todas_las_facturas)))
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

@APP.route('/listar-carpetas-separados', methods=['GET'])
def listar_carpetas_separados():
    try:
        service = autenticar_google_drive()
        if not service:
            return jsonify({'success': False, 'error': 'No auth'}), 500

        query = f"'{CARPETA_SEPARADOS_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"

        results = service.files().list(
            q=query,
            fields='files(id, name)',
            pageSize=100
        ).execute()

        carpetas = results.get('files', [])

        print("CARPETAS ENCONTRADAS:", carpetas)  # 👈 DEBUG

        return jsonify({
            'success': True,
            'carpetas': carpetas
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@APP.route('/mover-carpetas-procesados', methods=['POST'])
def mover_carpetas_procesados():
    try:
        data = request.json
        carpetas_ids = data.get('carpetas', [])

        service = autenticar_google_drive()
        if not service:
            return jsonify({'success': False, 'error': 'No auth'}), 500

        for carpeta_id in carpetas_ids:
            file = service.files().get(fileId=carpeta_id, fields='parents').execute()
            padres = ",".join(file.get('parents', []))

            service.files().update(
                fileId=carpeta_id,
                addParents=CARPETA_PROCESADOS_ID,
                removeParents=padres,
                fields='id'
            ).execute()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



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
    """Busca PDF en Google Drive y lo prepara para procesar"""
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
        
        # 🔥 NUEVO: Crear carpeta de proceso en Google Drive
        log_mensaje('📁', 'Creando carpeta de proceso en Google Drive...')
        nombre_carpeta = generar_nombre_carpeta()
        carpeta_destino_id = crear_carpeta_drive(service, nombre_carpeta, CARPETA_SEPARADOS_ID)
        
        if not carpeta_destino_id:
            carpeta_destino_id = CARPETA_SEPARADOS_ID
        
        log_mensaje('✅', f'Carpeta creada: {nombre_carpeta}')
        
        # 🔥 NUEVO: Copiar el PDF original a la carpeta de proceso
        log_mensaje('📤', f'Subiendo PDF original a carpeta de proceso...')
        pdf_subido_id = subir_archivo_a_drive(service, ruta_pdf, carpeta_destino_id, pdf_nombre)
        
        if not pdf_subido_id:
            log_mensaje('⚠️', 'Error subiendo PDF a carpeta de proceso')
            pdf_subido_id = pdf_id
        
        # 🔥 Guardar estado
        estado_actual['pdf_encontrado'] = {
            'nombre': pdf_nombre,
            'ruta': ruta_pdf,
            'paginas': total_paginas,
            'id': pdf_id,
            'id_en_proceso': pdf_subido_id  # 🔥 ID del PDF en la carpeta de proceso
        }
        estado_actual['pdf_original_name'] = pdf_nombre
        estado_actual['pdf_original_id'] = pdf_id
        estado_actual['carpeta_proceso_id'] = carpeta_destino_id  # 🔥 Guardar carpeta de proceso
        
        log_mensaje('✅', f'PDF encontrado: {pdf_nombre}')
        log_mensaje('📄', f'Total de páginas: {total_paginas}')
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ PDF encontrado: {pdf_nombre}',
            'paginas': total_paginas,
            'requiere_division': total_paginas > 2,
            'carpeta_proceso': nombre_carpeta
        })
    
    except Exception as e:
        log_mensaje('❌', f'Error: {str(e)}')
        import traceback
        log_mensaje('❌', traceback.format_exc(), mostrar_en_web=False)
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
        
        log_mensaje('TOTAL', str(len(paginas_validas)))

        total_operaciones = len(paginas_validas) * 2
        log_mensaje('TOTAL_REAL', str(total_operaciones))
        
        total_operaciones = len(paginas_validas) * 2  # crear + subir
        log_mensaje('TOTAL_REAL', str(total_operaciones))
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
                        from google_drive_integrador import obtener_mes_real_pdf

                        mes = obtener_mes_real_pdf(ruta_pdf, num_pagina_real)
                        
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
            log_mensaje('PROGRESO', '1')

            log_mensaje('PROGRESO', '1')
        
        # 🔥 CREAR CARPETA UNA SOLA VEZ
        nombre_carpeta = generar_nombre_carpeta()
        carpeta_destino_id = crear_carpeta_drive(service, nombre_carpeta, CARPETA_SEPARADOS_ID)

        if not carpeta_destino_id:
            carpeta_destino_id = CARPETA_SEPARADOS_ID
        
        estado_actual['carpeta_proceso_id'] = carpeta_destino_id

        log_mensaje('📤', f'Subiendo {len(archivos_creados)} PDFs separados...')
        

        
        for archivo in archivos_creados:
            nombre = os.path.basename(archivo)
            subir_archivo_a_drive(service, archivo, carpeta_destino_id, nombre)

            log_mensaje('PROGRESO', '1')

            
        
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
    """Analiza los PDFs desde la carpeta de proceso"""
    global estado_actual

    if not estado_actual.get('pdf_encontrado'):
        return jsonify({'success': False, 'error': 'No hay PDF cargado'}), 400

    ruta_pdf = estado_actual['pdf_encontrado'].get('ruta')

    if not ruta_pdf or not os.path.exists(ruta_pdf):
        return jsonify({'success': False, 'error': 'PDF no existe en disco'}), 400
    
    try:
        log_mensaje('📊', 'Analizando PDFs...')
        
        service = estado_actual.get('service')
        if not service:
            service = autenticar_google_drive()
            estado_actual['service'] = service
        
        if not service:
            return jsonify({'success': False, 'error': 'Error de autenticación'}), 500
        
        # 🔥 AHORA SIEMPRE HAY carpeta_proceso_id
        carpeta_id = estado_actual.get('carpeta_proceso_id')
        
        if not carpeta_id:
            return jsonify({'success': False, 'error': 'No hay carpeta de proceso'}), 400
        
        pdfs_encontrados = buscar_archivos_en_carpeta(service, carpeta_id, '.pdf')
        
        if not pdfs_encontrados:
            return jsonify({'success': False, 'error': 'No hay PDFs para analizar'}), 404
        
        total_operaciones = len(pdfs_encontrados)
        log_mensaje('TOTAL_REAL', str(total_operaciones))
        
        FACTURAS_POR_LOTE = 15
        PAUSA_ENTRE_LOTES = 30
        
        facturas_analizadas = []
        pdfs_analizados = []
        facturas_en_lote = 0
        num_lote = 1
        
        for pdf_info in pdfs_encontrados:
            pdf_nombre = pdf_info['name']
            ruta_pdf_temp = os.path.join(TEMP_PDFS_DIR, pdf_nombre)
            
            # 🔥 Descargar desde carpeta de proceso en Drive
            if not descargar_archivo_desde_drive(service, pdf_info['id'], ruta_pdf_temp):
                log_mensaje('⚠️', f'Error descargando: {pdf_nombre}')
                continue
            
            log_mensaje('📄', f'Analizando: {pdf_nombre}')
            
            paginas = extraer_paginas_pdf(ruta_pdf_temp)
            if not paginas:
                log_mensaje('⚠️', f'PDF sin texto legible: {pdf_nombre}')
                continue
            
            for pagina_info in paginas:
                texto_pagina = pagina_info['texto']
                texto_upper = texto_pagina.upper()

                
                datos = extraer_datos_factura(
                    texto_pagina,
                    pdf_path=ruta_pdf_temp,
                    numero_pagina=pagina_info['numero']
                )
                
                if datos and datos.get("Numero_Cliente"):
                    facturas_analizadas.append(datos)
                    log_mensaje('PROGRESO', '1')
                    facturas_en_lote += 1
                    
                    if pdf_nombre not in pdfs_analizados:
                        pdfs_analizados.append(pdf_nombre)
                    
                    if facturas_en_lote >= FACTURAS_POR_LOTE:
                        log_mensaje('⏸️', f'Lote {num_lote}: {facturas_en_lote} facturas')
                        log_mensaje('⏳', f'Pausa de {PAUSA_ENTRE_LOTES}s...')
                        time.sleep(PAUSA_ENTRE_LOTES)
                        facturas_en_lote = 0
                        num_lote += 1
                        log_mensaje('✅', f'Reanudando - Lote {num_lote}')
        
        if not facturas_analizadas:
            return jsonify({
                'success': False,
                'error': 'No se encontraron facturas válidas'
            }), 400
        
        log_mensaje('✅', f'Facturas analizadas: {len(facturas_analizadas)}')
        estado_actual['facturas_analizadas'] = facturas_analizadas
        
        return jsonify({
            'success': True,
            'mensaje': f'✅ {len(facturas_analizadas)} facturas analizadas',
            'total_facturas': len(facturas_analizadas),
            'pdfs_analizados': pdfs_analizados
        })
    
    except Exception as e:
        log_mensaje('❌', f'Error: {str(e)}')
        import traceback
        log_mensaje('❌', traceback.format_exc(), mostrar_en_web=False)
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