# coding: utf-8
import os
import sys
import logging
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import io
from PyPDF2 import PdfReader, PdfWriter
import tempfile
import shutil

# Importar funciones de recibos_energia
from recibos_energia import extraer_paginas_pdf, extraer_datos_factura, generar_excel_facturas

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# 🔥 IDS DE CARPETAS GOOGLE DRIVE
CARPETA_ENTRADA_ID = "1eveBX7jxaV1O8aawhldyTWeMVzBqutZQ"  # Donde buscar PDFs
CARPETA_SEPARADOS_ID = "1NXNT-9tsn_6bDLJIIgwGNjIPJmyEidqL"  # Donde guardar PDFs separados
CARPETA_EXCEL_ID = "1z4__4EDoV_CT0z-aHupEYgrTa7W_FatA"  # Donde guardar Excel final

# 🔥 CREDENCIALES GOOGLE
CREDENTIALS_FILE = 'credenciales_google.json'  # Descargar desde Google Cloud Console
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# ==================== AUTENTICACIÓN GOOGLE DRIVE ====================

def autenticar_google_drive():
    """Autentica con Google Drive"""
    creds = None
    token_file = 'token.pickle'
    
    if os.path.exists(token_file):
        from pickle import load
        with open(token_file, 'rb') as token:
            creds = load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        from pickle import dump
        with open(token_file, 'wb') as token:
            dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)

# ==================== FUNCIONES GOOGLE DRIVE ====================

def buscar_archivos_en_carpeta(service, carpeta_id, nombre_archivo=None):
    """Busca archivos en una carpeta de Google Drive"""
    try:
        query = f"'{carpeta_id}' in parents and trashed=false"
        
        if nombre_archivo:
            query += f" and name contains '{nombre_archivo}'"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, size)',
            pageSize=100
        ).execute()
        
        return results.get('files', [])
    
    except Exception as e:
        logging.error(f"❌ Error buscando archivos: {e}")
        return []

def descargar_archivo(service, file_id, ruta_destino):
    """Descarga un archivo de Google Drive"""
    try:
        request = service.files().get_media(fileId=file_id)
        with open(ruta_destino, 'wb') as f:
            downloader = request.execute()
            f.write(downloader)
        logging.info(f"✅ Descargado: {ruta_destino}")
        return True
    except Exception as e:
        logging.error(f"❌ Error descargando archivo: {e}")
        return False

def subir_archivo(service, ruta_archivo, carpeta_id, nombre_archivo=None):
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
        
        logging.info(f"✅ Subido: {nombre_archivo} (ID: {file['id']})")
        return file['id']
    
    except Exception as e:
        logging.error(f"❌ Error subiendo archivo: {e}")
        return None

def listar_subcarpetas(service, carpeta_id):
    """Lista las subcarpetas de una carpeta"""
    try:
        query = f"'{carpeta_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=100
        ).execute()
        
        return results.get('files', [])
    
    except Exception as e:
        logging.error(f"❌ Error listando subcarpetas: {e}")
        return []

# ==================== FUNCIONES DE PROCESAMIENTO ====================

def dividir_pdf_local(ruta_pdf, carpeta_salida, limite_paginas=2):
    """Divide un PDF en archivos individuales si tiene más de X páginas.
    Cada archivo se nombra con el número de cliente y nombre de cada página."""
    try:
        lector = PdfReader(ruta_pdf)
        total_paginas = len(lector.pages)
        
        logging.info(f"📄 PDF tiene {total_paginas} páginas")
        
        if total_paginas <= limite_paginas:
            logging.info(f"✅ PDF no requiere división ({total_paginas} <= {limite_paginas})")
            return [ruta_pdf]  # Retornar el archivo original
        
        logging.info(f"📂 Dividiendo PDF en {total_paginas} archivos...")
        
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
        
        archivos_creados = []
        
        # 🔥 NUEVO: Importar funciones necesarias
        from recibos_energia import extraer_datos_factura, extraer_paginas_pdf
        import re
        
        # Extraer datos de TODAS las páginas primero
        paginas = extraer_paginas_pdf(ruta_pdf)
        logging.info(f"   📖 Extrayendo datos de {len(paginas)} páginas para nombrar archivos...")
        
        for num_pagina in range(total_paginas):
            escritor = PdfWriter()
            escritor.add_page(lector.pages[num_pagina])
            
            # 🔥 NUEVO: Extraer datos de ESTA página específica
            cliente_nombre = None
            numero_pagina_real = num_pagina + 1
            
            if num_pagina < len(paginas):
                try:
                    texto_pagina = paginas[num_pagina]['texto']
                    
                    # 🔥 NUEVO: Extraer cliente y nombre de forma DIRECTA sin pasar por extraer_datos_factura
                    match_numero = re.search(r'(\d{7}-\d)(?:\s*[\d\w])', texto_pagina)  # ⬅️ CAMBIO AQUÍ: [\d\w] en lugar de [A-Z]
                    
                    if match_numero:
                        numero_cliente = match_numero.group(1).strip()
                        logging.info(f"   ✅ Página {numero_pagina_real}: Número de cliente encontrado: {numero_cliente}")
                        
                        # Buscar nombre del cliente
                        # 🔥 NUEVO: Captura MÁS agresiva del nombre completo
                        patron = rf'{re.escape(numero_cliente)}\s*\n?\s*([\d\w].*?)(?:\n(?:CL|KR|AC|DG|AV|AVENIDA|CALLE|CARRERA|AK|PZ|TV|VT|RA|AP|MNZ|ZN|BRR|SM|LT|MZ)\s+|\n\n|$)'
                        match_nombre = re.search(patron, texto_pagina, re.DOTALL)
                        
                        if match_nombre:
                            nombre_cliente = match_nombre.group(1).strip()

                            # 🔥 LIMPIEZA CRÍTICA - Remover saltos de línea e caracteres inválidos
                            nombre_cliente = nombre_cliente.replace('\n', ' ')
                            nombre_cliente = nombre_cliente.replace('\r', ' ')
                            nombre_cliente = re.sub(r'[\n\r\t]', '', nombre_cliente)  # ⬅️ NUEVA LÍNEA
                            nombre_cliente = re.sub(r'\s+', ' ', nombre_cliente)
                            
                            # 🔥 NUEVO: Limpiar el nombre - PERMITIR puntos, guiones, &
                            nombre_cliente_limpio = re.sub(r'[^\w\s\.\-&]', '', nombre_cliente)
                            nombre_cliente_limpio = nombre_cliente_limpio.replace(' ', '_').upper()
                            
                            # 🔥 EXTRAER DATOS COMPLETOS
                            from recibos_energia import extraer_datos_factura

                            datos = extraer_datos_factura(texto_pagina)

                            # 🔥 MES (ENE26, FEB26, etc)
                            mes = ""
                            if datos and datos.get("Fecha_Inicial"):
                                match_fecha = re.search(r'\d{2}\s+([A-Z]{3})\s*/(\d{4})', datos["Fecha_Inicial"])
                                if match_fecha:
                                    mes = f"{match_fecha.group(1)}{match_fecha.group(2)[-2:]}"

                            # 🔥 GRUPO (GA / GB)
                            grupo = ""
                            if datos and datos.get("Cuenta_Padre"):
                                if datos["Cuenta_Padre"] == "3968375":
                                    grupo = "GA"
                                elif datos["Cuenta_Padre"] == "8150280":
                                    grupo = "GB"

                            # 🔥 NOMBRE FINAL
                            cliente_nombre = f"{numero_cliente} {nombre_cliente_limpio} {mes} {grupo}"
                            logging.info(f"      📝 Nombre: {nombre_cliente_limpio}")
                        else:
                            # Si no encontró nombre, usa solo el número
                            cliente_nombre = numero_cliente
                            logging.info(f"      ⚠️ No se encontró nombre, usando solo número")
                    else:
                        logging.info(f"   ℹ️ Página {numero_pagina_real}: Sin número de cliente")
                
                except Exception as e:
                    logging.warning(f"   ⚠️ Página {numero_pagina_real}: Error extrayendo - {str(e)}")
            
            # Si no se pudo extraer, usa número de página genérico
            if not cliente_nombre:
                cliente_nombre = f"pagina_{numero_pagina_real:04d}"
                logging.info(f"   ℹ️ Página {numero_pagina_real}: Usando nombre genérico")
            
            # Crear nombre del archivo (sin duplicar .pdf)
            if not cliente_nombre.endswith('.pdf'):
                nombre_archivo = f"{cliente_nombre}.pdf"
            else:
                nombre_archivo = cliente_nombre

            # 🔥 CRÍTICO: Limpiar caracteres inválidos para nombres de archivo Windows
            nombre_archivo = re.sub(r'[\n\r\t:\"/<>|?*\\]', '', nombre_archivo)
            
            # 🔥 NUEVO: Remover caracteres inválidos para nombres de archivo Windows
            nombre_archivo = re.sub(r'[\n\r\t:\"/<>|?*\\]', '', nombre_archivo)  # ⬅️ UNA SOLA LÍNEA
            
            ruta_completa = os.path.join(carpeta_salida, nombre_archivo)
            
            with open(ruta_completa, "wb") as archivo_salida:
                escritor.write(archivo_salida)
            
            archivos_creados.append(ruta_completa)
            
            if (num_pagina + 1) % 10 == 0:
                logging.info(f"   📖 Procesadas {num_pagina + 1}/{total_paginas} páginas")
        
        logging.info(f"✅ PDF dividido en {len(archivos_creados)} archivos con nombres personalizados")
        return archivos_creados
    
    except Exception as e:
        logging.error(f"❌ Error dividiendo PDF: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return []

def procesar_pdfs_locales(lista_pdfs):
    """Procesa una lista de PDFs locales"""
    todas_las_facturas = []
    
    for pdf_path in lista_pdfs:
        logging.info(f"\n📄 Procesando: {os.path.basename(pdf_path)}")
        
        paginas = extraer_paginas_pdf(pdf_path)
        
        if not paginas:
            logging.warning(f"⚠️ No se pudo extraer páginas")
            continue
        
        for pagina_info in paginas:
            num_pagina = pagina_info['numero']
            texto_pagina = pagina_info['texto']
            
            datos = extraer_datos_factura(texto_pagina, pdf_path=pdf_path, numero_pagina=num_pagina)
            
            if datos and datos.get("Numero_Cliente"):
                todas_las_facturas.append(datos)
                logging.info(f"   ✅ Factura extraída: {datos.get('Numero_Cliente')}")
            else:
                logging.info(f"   ⏭️ Página {num_pagina}: Sin factura válida")
    
    return todas_las_facturas

# ==================== FLUJO PRINCIPAL ====================

def procesar_carpeta_google_drive():
    """Flujo principal: descarga -> procesa -> sube"""
    
    logging.info("="*70)
    logging.info("🚀 INICIANDO INTEGRADOR GOOGLE DRIVE")
    logging.info("="*70)
    
    # Autenticar
    try:
        service = autenticar_google_drive()
        logging.info("✅ Autenticado con Google Drive")
    except Exception as e:
        logging.error(f"❌ Error de autenticación: {e}")
        return
    
    # Crear carpetas temporales
    tmpdir_main = tempfile.mkdtemp(prefix='google_drive_')
    tmpdir_separados = os.path.join(tmpdir_main, 'separados')
    
    try:
        # PASO 1: Listar subcarpetas de entrada
        logging.info(f"\n📂 Buscando subcarpetas en carpeta de entrada...")
        subcarpetas = listar_subcarpetas(service, CARPETA_ENTRADA_ID)
        
        if not subcarpetas:
            logging.warning(f"⚠️ No se encontraron subcarpetas")
            return
        
        logging.info(f"✅ Encontradas {len(subcarpetas)} subcarpeta(s)")
        
        todas_las_facturas_finales = []
        
        # PASO 2: Procesar cada subcarpeta
        for subcarpeta in subcarpetas:
            subfolder_id = subcarpeta['id']
            subfolder_name = subcarpeta['name']
            
            logging.info(f"\n{'='*70}")
            logging.info(f"📂 PROCESANDO SUBCARPETA: {subfolder_name}")
            logging.info(f"{'='*70}")
            
            # Buscar PDFs en la subcarpeta
            pdfs_encontrados = buscar_archivos_en_carpeta(service, subfolder_id, '.pdf')
            
            if not pdfs_encontrados:
                logging.warning(f"⚠️ No hay PDFs en {subfolder_name}")
                continue
            
            logging.info(f"✅ Encontrados {len(pdfs_encontrados)} PDF(s)")
            
            # PASO 3: Descargar y procesar cada PDF
            for pdf_info in pdfs_encontrados:
                pdf_id = pdf_info['id']
                pdf_nombre = pdf_info['name']
                
                logging.info(f"\n📥 Descargando: {pdf_nombre}")
                
                ruta_pdf_temp = os.path.join(tmpdir_main, pdf_nombre)
                
                if not descargar_archivo(service, pdf_id, ruta_pdf_temp):
                    continue
                
                # PASO 4: Verificar si necesita dividirse
                logging.info(f"\n🔍 Verificando tamaño del PDF...")
                
                pdfs_a_procesar = dividir_pdf_local(ruta_pdf_temp, tmpdir_separados, limite_paginas=2)
                
                # PASO 5: Si se dividió, subir los separados
                if len(pdfs_a_procesar) > 1:
                    logging.info(f"\n📤 Subiendo {len(pdfs_a_procesar)} PDFs separados...")
                    
                    for pdf_separado in pdfs_a_procesar:
                        nombre_separado = os.path.basename(pdf_separado)
                        subir_archivo(service, pdf_separado, CARPETA_SEPARADOS_ID, nombre_separado)
                
                # PASO 6: Procesar PDFs
                logging.info(f"\n🔄 Procesando {len(pdfs_a_procesar)} PDF(s)...")
                
                facturas = procesar_pdfs_locales(pdfs_a_procesar)
                todas_las_facturas_finales.extend(facturas)
                
                logging.info(f"✅ Procesadas {len(facturas)} facturas")
        
        # PASO 7: Generar Excel final
        if todas_las_facturas_finales:
            logging.info(f"\n{'='*70}")
            logging.info(f"📊 GENERANDO EXCEL FINAL...")
            logging.info(f"{'='*70}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_filename = f"facturas_procesadas_{timestamp}.xlsx"
            excel_path = os.path.join(tmpdir_main, excel_filename)
            
            if generar_excel_facturas(todas_las_facturas_finales, excel_path):
                # Subir Excel a Google Drive
                logging.info(f"\n📤 Subiendo Excel a Google Drive...")
                subir_archivo(service, excel_path, CARPETA_EXCEL_ID, excel_filename)
                
                logging.info(f"\n{'='*70}")
                logging.info(f"✅ ¡COMPLETADO EXITOSAMENTE!")
                logging.info(f"{'='*70}")
                logging.info(f"📊 Total facturas procesadas: {len(todas_las_facturas_finales)}")
                logging.info(f"📁 Excel subido a Google Drive: {excel_filename}")
            else:
                logging.error(f"❌ Error generando Excel")
        else:
            logging.warning(f"⚠️ No hay facturas para exportar")
    
    except Exception as e:
        logging.error(f"❌ Error en flujo principal: {e}")
        import traceback
        logging.error(traceback.format_exc())
    
    finally:
        # Limpiar archivos temporales
        try:
            if os.path.isdir(tmpdir_main):
                shutil.rmtree(tmpdir_main)
                logging.info(f"🧹 Archivos temporales eliminados")
        except Exception as e:
            logging.warning(f"⚠️ No se pudieron limpiar temporales: {e}")

if __name__ == "__main__":
    procesar_carpeta_google_drive()