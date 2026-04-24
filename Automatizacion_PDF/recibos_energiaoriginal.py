# coding: utf-8
import pdfplumber
import os
import re
import sys
import glob
import logging
import time
from datetime import datetime
import PyPDF2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# Configuración
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1wY2UIuHzVEmTIQfvdnK_zBertwP1J72Zt3Y5PwlGJVM'
SHEET_NAME = 'Facturas'
CREDENTIALS_FILE = 'prueba-de-gmail-486215-a27c8163c331.json'
PDF_DIR = r"C:\Users\cmarroquin\Music\PDF python\paginas_separadas"

# PARÁMETROS DE LOTE
FACTURAS_POR_LOTE = 15  # Procesa 15 facturas por lote
PAUSA_ENTRE_LOTES = 30  # Pausa de 30 segundos entre lotes

HEADERS = [
    'Empresa',
    'Numero_Cliente',
    'Nombre_Cliente',
    'Cuenta_Padre',
    # 'Documento_Equivalente',
    'Direccion',
    'Periodo_Facturacion',
    'Fecha_Pago_Oportuno',
    'Fecha_Suspension',
    'Total_Energia',
    'Total_Aseo',
    # 'Total_a_Pagar',
    'Consumo_Cantidad',
    'Consumo_Unidad',
    'Costo_Unitario',
    'Estado_Pago',
    'NIT_Empresa',
    'NIT_Aseo',
    'Prestador_Aseo',
    'Aseo_Servicio_No_Residencial',  # ← NUEVO
    'Aseo_Contribucion_No_Residen',  # ← NUEVO
    'Aseo_Ajuste_Decena',  # ← NUEVO
    'Aseo_Reliquidacion',  # ← NUEVO
    'Aseo_Menor_Valor'  # ← NUEVO
]

# Archivo de log de seguimiento
LOG_FILE = 'procesamiento_facturas.log'
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(file_handler)

def authenticate_google_sheets():
    """Autentica con Service Account"""
    try:
        creds = Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=SCOPES
        )
        logging.info("✅ Autenticación exitosa con Service Account")
        return creds
    except FileNotFoundError:
        logging.error(f"❌ No se encontró el archivo {CREDENTIALS_FILE}")
        raise
    except Exception as e:
        logging.error(f"❌ Error al autenticar: {e}")
        raise

def check_and_create_headers(service, spreadsheet_id, sheet_name, headers):
    """Verifica si los encabezados existen"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:W1"
        ).execute()
        
        existing_headers = result.get('values', [[]])[0]
        
        if not existing_headers or len(existing_headers) == 0:
            logging.info("📝 Creando encabezados...")
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1:W1",
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
            logging.info("✅ Encabezados creados")
            return 2
        else:
            logging.info("✅ Encabezados ya existen")
            all_values = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}"
            ).execute()
            return len(all_values.get('values', [])) + 1
            
    except Exception as e:
        logging.error(f"❌ Error verificando encabezados: {e}")
        raise

def extraer_paginas_pdf(pdf_path):
    """Extrae texto de cada página del PDF por separado"""
    try:
        paginas = []
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            
            logging.info(f"📄 Total de páginas en PDF: {total_pages}")
            
            for num_pagina, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    paginas.append({
                        'numero': num_pagina,
                        'texto': page_text
                    })
        
        return paginas
    except Exception as e:
        logging.error(f"❌ Error al leer PDF {os.path.basename(pdf_path)}: {e}")
        return []


def extraer_direccion_por_coordenadas(pdf_path, numero_pagina, nombre_cliente):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[numero_pagina - 1]

            # 🔥 ZONA CLIENTE (AJUSTADA A TU PDF)
            bbox = (100, 120, 500, 260)
            # (x0, y0, x1, y1)

            texto = page.within_bbox(bbox).extract_text()

            if not texto:
                return None

            lineas = [l.strip() for l in texto.split('\n') if l.strip()]

            # quitar nombre
            direccion_lineas = []
            for l in lineas:
                if nombre_cliente and nombre_cliente in l:
                    continue
                direccion_lineas.append(l)

            if direccion_lineas:
                direccion = " ".join(direccion_lineas)
                direccion = re.sub(r'\s+', ' ', direccion).strip()
                return direccion

    except Exception as e:
        logging.warning(f"⚠️ Error coordenadas dirección: {e}")

    return None

def limpiar_numero(valor_str):
    """Limpia y convierte número del formato colombiano"""
    if not valor_str:
        return None
    valor_str = str(valor_str).strip()
    try:
        return float(valor_str.replace('.', '').replace(',', '.'))
    except ValueError:
        return None


def extraer_prestador_por_coordenadas(pdf_path, numero_pagina):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[numero_pagina - 1]

            # 🔥 ZONA SUPERIOR DONDE ESTÁ "ASEO / PRESTADOR"
            bbox = (0, 0, 600, 250)

            texto = page.within_bbox(bbox).extract_text()

            if not texto:
                return None

            texto = texto.replace('\n', ' ')
            texto = re.sub(r'\s+', ' ', texto)

            # 🔥 BUSCAR ENTRE PRESTADOR y NIT
            match = re.search(r'PRESTADOR:\s*(.*?)\s*NIT', texto, re.IGNORECASE)

            if match:
                prestador = match.group(1).strip()

                if len(prestador) > 3:
                    logging.info(f"   → Prestador (coord): {prestador}")
                    return prestador

    except Exception as e:
        logging.warning(f"⚠️ Error coordenadas prestador: {e}")

    return None


def extraer_direccion(texto_pagina, numero_cliente):
    """Extrae SOLO la dirección (CL, KR, AC, DG, AV, etc.) - Sin el nombre del cliente"""
    try:
        lineas = [l.strip() for l in texto_pagina.split('\n') if l.strip()]

        direccion_lineas = []
        capturar = False

        for i, linea in enumerate(lineas):
            # 🔥 Activar cuando encuentra el número cliente
            if numero_cliente in linea:
                capturar = True
                continue

            if capturar:
                # ✅ BUSCAR LÍNEA QUE EMPIECE CON DIRECCIÓN (CL, KR, AC, DG, AV, etc.)
                if re.match(r'^(CL|KR|AC|DG|AV|AVENIDA|CALLE|CARRERA|AK|PZ|TV|VT|RA|AP|MNZ|ZN|BRR|SM|LT|MZ)\s+', linea, re.IGNORECASE):
                    # 🎯 ENCONTRÓ LA DIRECCIÓN - CAPTURAR DESDE AQUÍ
                    direccion_lineas.append(linea)

                    # Capturar las siguientes líneas (máximo 4 líneas más)
                    for siguiente in lineas[i+1:i+5]:
                        # Detener si encuentra palabras clave de otra sección
                        if re.search(r'(ruta|transformador|nivel|red|circuito|tipo de servicio|estrato|barrio)', siguiente, re.IGNORECASE):
                            break
                        # Detener si la línea es un número o está vacía
                        if not siguiente or siguiente.isdigit():
                            break
                        direccion_lineas.append(siguiente)

                    break  # Ya capturamos la dirección, terminar

        if direccion_lineas:
            direccion = " ".join(direccion_lineas)
            # Limpieza final
            direccion = re.sub(r'\s+', ' ', direccion).strip()
            return direccion

    except Exception as e:
        logging.warning(f"Error extrayendo dirección: {e}")

    return None

    
def extraer_total_aseo(texto_pagina):
    """
    Extrae el TOTAL ASEO real desde facturas Enel.
    Busca la zona ASEO y toma el valor correcto (como en tu PDF).
    """
    if not texto_pagina:
        return 0.0

    # 🔧 LIMPIEZA (CLAVE)
    texto = texto_pagina.replace('\xa0', ' ')
    texto = re.sub(r'\s+', ' ', texto)

    # =========================
    # 1. UBICAR ZONA ASEO
    # =========================
    match_aseo = re.search(r'ASEO\s*-', texto, re.IGNORECASE)

    if not match_aseo:
        return 0.0

    # 🔥 CORTAR SOLO LA ZONA IMPORTANTE
    inicio = match_aseo.start()
    texto_aseo = texto[inicio:inicio + 800]  # límite para evitar ruido

    # =========================
    # 2. BUSCAR TODOS LOS VALORES $
    # =========================
    valores = re.findall(r'\$\s*[\d\.,]+', texto_aseo)

    if not valores:
        return 0.0

    # =========================
    # 3. TOMAR EL VALOR CORRECTO
    # =========================
    # En tu PDF: el TOTAL ASEO es el último valor "grande"
    for valor in reversed(valores):
        numero = valor.replace('$', '').replace('.', '').replace(',', '')

        if numero.isdigit():
            numero_int = int(numero)

            # filtro para evitar valores pequeños basura
            if numero_int > 100:
                logging.info(f"   → Total Aseo detectado correctamente: ${numero_int}")
                return float(numero_int)

    return 0.0


def extraer_nit_aseo(texto_pagina):
    """Extrae el NIT de la sección ASEO (robusto)"""
    try:
        texto = texto_pagina.replace('\xa0', ' ')

        # 🔥 1. Buscar zona ASEO
        match_aseo = re.search(r'ASEO', texto, re.IGNORECASE)
        if not match_aseo:
            return None

        # 🔥 2. Cortar zona cercana
        inicio = match_aseo.start()
        bloque = texto[inicio:inicio + 800]

        # 🔥 3. Buscar NIT en cualquier formato (SIN 'NIT:')
        match_nit = re.search(r'(\d{9,10}-\d)', bloque)
        if match_nit:
            nit = match_nit.group(1)
            logging.info(f"   → NIT ASEO detectado: {nit}")
            return nit

    except Exception as e:
        logging.warning(f"Error extrayendo NIT ASEO: {e}")

    return None


def extraer_prestador_aseo(texto_pagina):
    """Extrae el PRESTADOR buscando empresas conocidas o patrón genérico"""
    try:
        texto = texto_pagina.replace('\xa0', ' ')
        
        # 🔥 1. Encontrar sección ASEO
        match_aseo = re.search(r'ASEO', texto, re.IGNORECASE)
        if not match_aseo:
            return None
        
        # 🔥 2. Extraer bloque de 2000 caracteres desde ASEO
        inicio = match_aseo.start()
        bloque = texto[inicio:inicio + 2000]
        
        # 🔥 3. Buscar CUALQUIER línea que contenga SAS ESP, LTDA, S.A., COLOMBIA
        # sin importar dónde esté
        match = re.search(r'([A-Z][A-Z\s\.\-&0-9]+?(?:SAS\s+ESP|LTDA|S\.A\.?|COLOMBIA))', bloque)
        if match:
            prestador = match.group(1).strip()
            prestador = re.sub(r'\s+', ' ', prestador)
            
            # Limitar a máximo 60 caracteres (para evitar capturar texto basura)
            if 5 < len(prestador) < 60:
                logging.info(f"   → Prestador ASEO detectado: {prestador}")
                return prestador

    except Exception as e:
        logging.warning(f"Error extrayendo prestador ASEO: {e}")

    return None


def extraer_conceptos_aseo(texto_pagina):
    """Extrae CADA concepto de ASEO por separado - búsqueda flexible"""
    try:
        texto = texto_pagina.replace('\xa0', ' ')
        
        # 🔥 Buscar zona ASEO
        match_aseo = re.search(r'ASEO', texto, re.IGNORECASE)
        if not match_aseo:
            return {}
        
        # 🔥 Extraer bloque de 1500 caracteres desde ASEO
        inicio = match_aseo.start()
        bloque = texto[inicio:inicio + 1500]
        
        resultados = {
            "Aseo_Servicio_No_Residencial": None,
            "Aseo_Contribucion_No_Residen": None,
            "Aseo_Ajuste_Decena": None,
            "Aseo_Reliquidacion": None,
            "Aseo_Menor_Valor": None
        }
        
        # 🔥 Búsquedas más flexibles (sin espacios exactos)
        # 1. SERVICIO NO RESIDENCIAL
        match = re.search(r'SERVICIO\s+NO\s+RESIDENCIAL[^\$]*?\$\s*([\d\.,\-]+)', bloque, re.IGNORECASE)
        if match:
            resultados["Aseo_Servicio_No_Residencial"] = match.group(1).strip()
            logging.info(f"   → Aseo_Servicio_No_Residencial: ${match.group(1).strip()}")
        
        # 2. CONTRIBUCIÓN NO RESIDEN
        match = re.search(r'CONTRIBUCIÓN\s+NO\s+RESIDEN[^\$]*?\$\s*([\d\.,\-]+)', bloque, re.IGNORECASE)
        if match:
            resultados["Aseo_Contribucion_No_Residen"] = match.group(1).strip()
            logging.info(f"   → Aseo_Contribucion_No_Residen: ${match.group(1).strip()}")
        
        # 3. AJUSTE A LA DECENA
        match = re.search(r'AJUSTE\s+A\s+LA\s+DECENA[^\$]*?\$\s*([\d\.,\-]+)', bloque, re.IGNORECASE)
        if match:
            resultados["Aseo_Ajuste_Decena"] = match.group(1).strip()
            logging.info(f"   → Aseo_Ajuste_Decena: ${match.group(1).strip()}")
        
        # 4. RELIQUIDACIÓN
        match = re.search(r'RELIQUIDACIÓN[^\$]*?\$\s*([\d\.,\-]+)', bloque, re.IGNORECASE)
        if match:
            resultados["Aseo_Reliquidacion"] = match.group(1).strip()
            logging.info(f"   → Aseo_Reliquidacion: ${match.group(1).strip()}")
        
        # 5. MENOR VALOR A FACTURA
        match = re.search(r'MENOR\s+VALOR\s+A\s+FACTURA[^\$]*?\$\s*([\d\.,\-]+)', bloque, re.IGNORECASE)
        if match:
            resultados["Aseo_Menor_Valor"] = match.group(1).strip()
            logging.info(f"   → Aseo_Menor_Valor: ${match.group(1).strip()}")
        
        return resultados
        
    except Exception as e:
        logging.warning(f"Error extrayendo conceptos ASEO: {e}")
        return {}


def extraer_datos_factura(texto_pagina):
    """Extrae datos de una factura de UNA PÁGINA"""
    datos = {
        "Empresa": "ENEL",
        "Numero_Cliente": None,
        "Nombre_Cliente": None,
        "Cuenta_Padre": None,
        # "Documento_Equivalente": None,
        "Direccion": None,
        "Periodo_Facturacion": None,
        "Fecha_Pago_Oportuno": None,
        "Fecha_Suspension": None,
        "Total_Energia": None,
        "Total_Aseo": None,
        # "Total_a_Pagar": None,
        "Consumo_Cantidad": None,
        "Consumo_Unidad": "kWh",
        "Costo_Unitario": None,
        "Estado_Pago": None,
        "NIT_Empresa": None,
        "NIT_Aseo": None,
        "Prestador_Aseo": None,
        "Aseo_Servicio_No_Residencial": None,  # ← NUEVO
        "Aseo_Contribucion_No_Residen": None,  # ← NUEVO
        "Aseo_Ajuste_Decena": None,  # ← NUEVO
        "Aseo_Reliquidacion": None,  # ← NUEVO
        "Aseo_Menor_Valor": None  # ← NUEVO
    }
    
    # Validar que sea una factura ENEL válida
    if "Tipo de Lectura: Real" not in texto_pagina:
        return None
    
    # ========== NÚMERO DE CLIENTE ==========
    match = re.search(r'(\d{7}-\d)(?:\s*[A-Z])', texto_pagina)
    if match:
        datos["Numero_Cliente"] = match.group(1).strip()
    else:
        return None

    # ===== CUENTA PADRE =====
    match_padre = re.search(r'\n(\d{7})\s*\n', texto_pagina)
    if match_padre:
        datos["Cuenta_Padre"] = match_padre.group(1)

    # ===== DOCUMENTO EQUIVALENTE =====
    match_doc = re.search(r'\(415\)\d+\(8020\)\d+\(3900\)\d+', texto_pagina)
    if match_doc:
        datos["Documento_Equivalente"] = match_doc.group(0)
    
    # ========== NOMBRE CLIENTE ==========
    if datos["Numero_Cliente"]:
        # ===== DIRECCIÓN =====
        # ===== DIRECCIÓN (DEBAJO DEL NOMBRE) =====
        direccion = None

        if datos.get("Nombre_Cliente"):
            # buscar el nombre en el texto
            pos = texto_pagina.find(datos["Nombre_Cliente"])

            if pos != -1:
                texto_despues = texto_pagina[pos + len(datos["Nombre_Cliente"]):]

                # tomar solo unas líneas después
                lineas = texto_despues.split('\n')[1:6]

                lineas_limpias = []
                for l in lineas:
                    l = l.strip()

                    if not l:
                        continue

                    # detener si ya empieza otra sección
                    if re.search(r'(ruta|transformador|tipo de servicio|estrato)', l, re.IGNORECASE):
                        break

                    lineas_limpias.append(l)

                if lineas_limpias:
                    direccion = " ".join(lineas_limpias)

                    # limpieza mínima
                    direccion = re.sub(r'\s+', ' ', direccion).strip()

                    datos["Direccion"] = direccion
        patron = rf'{re.escape(datos["Numero_Cliente"])}\s*([A-Z][A-Z0-9\s\.\-&,/()]+?)(?=\n|KR|CL|AV|AC|DG|AK)'
        match = re.search(patron, texto_pagina)
        if match:
            nombre = match.group(1).strip()
            if 3 < len(nombre) < 100:
                datos["Nombre_Cliente"] = nombre
    
    # ========== PERÍODO DE FACTURACIÓN ==========
    match = re.search(
        r'(\d{1,2}\s+[A-Z]{3}/\d{4}\s+[AaBb]\s+\d{1,2}\s+[A-Z]{3}/\d{4})',
        texto_pagina
    )
    if match:
        datos["Periodo_Facturacion"] = match.group(1).strip()

    # ===== FECHAS =====
    fechas = re.findall(r'(\d{2}\s+[A-Z]{3}\s*/\d{4})', texto_pagina)
    if len(fechas) >= 2:
        datos["Fecha_Pago_Oportuno"] = fechas[0]
        datos["Fecha_Suspension"] = fechas[1]
    
    # ========== TOTAL ENERGÍA ==========
    match_energia = re.search(r"(?i)(?:Total Energía y Otros|SUBTOTAL VALOR CONSUMO)\s*[\$]*\s*([\d\.,]+)", texto_pagina)
    if match_energia:
        datos["Total_Energia"] = limpiar_numero(match_energia.group(1))
    else:
        match_energia_alt = re.search(r"(?i)TOTAL\s*CONCEPTO\s*ENERG[IÍ]A\s*[\$]*\s*([\d\.,]+)", texto_pagina)
        datos["Total_Energia"] = limpiar_numero(match_energia_alt.group(1)) if match_energia_alt else 0.0

    # ===== TOTAL ASEO =====
    datos["Total_Aseo"] = extraer_total_aseo(texto_pagina)

    # ===== TOTAL A PAGAR =====
    match_total_hoja = re.search(r"(?i)Total a Pagar\s*[\$]*\s*([\d\.,]+)", texto_pagina)
    if match_total_hoja:
        datos["Total_a_Pagar"] = limpiar_numero(match_total_hoja.group(1))
    else:
        valores = re.findall(r'\$\s*(\d{1,3}(?:\.\d{3})+)', texto_pagina)
        valores_limpios = [limpiar_numero(v) for v in valores if limpiar_numero(v)]
        datos["Total_a_Pagar"] = max(valores_limpios) if valores_limpios else 0.0
    
    # ========== CONSUMO (opcional) ==========
    match_consumo = re.search(r'CONSUMO ACTIVA SENCILLA\s+(\d{1,3}(?:\.\d{3})*)', texto_pagina, re.IGNORECASE)
    if match_consumo:
        datos["Consumo_Cantidad"] = limpiar_numero(match_consumo.group(1))
    
    # ========== NIT EMPRESA ==========
    match = re.search(r'NIT\.\s+(\d{3}\.\d{3}\.\d{3}-\d)', texto_pagina)
    if match:
        datos["NIT_Empresa"] = match.group(1).strip()
    else:
        match = re.search(r'NIT[.:\s]+(\d{9,10}-\d)', texto_pagina)
        if match:
            datos["NIT_Empresa"] = match.group(1).strip()


    # ========== NIT ASEO ==========
    datos["NIT_Aseo"] = extraer_nit_aseo(texto_pagina)


    datos["Prestador_Aseo"] = extraer_prestador_aseo(texto_pagina)

    datos["Prestador_Aseo"] = extraer_prestador_aseo(texto_pagina)

    # ========== CONCEPTOS ASEO (CADA UNO EN SU COLUMNA) ==========
    conceptos = extraer_conceptos_aseo(texto_pagina)
    datos.update(conceptos)  # Actualizar el diccionario con todos los conceptos
    
    # ========== ESTADO DE PAGO ==========

    
    # ========== ESTADO DE PAGO ==========
    if datos.get("Total_a_Pagar") == 0 or datos.get("Total_a_Pagar") is None or "$0" in texto_pagina or "SALDO CRÉDITO" in texto_pagina:
        datos["Estado_Pago"] = "Sin Deuda"
    elif "PAGADO" in texto_pagina.upper():
        datos["Estado_Pago"] = "Pagado"
    else:
        datos["Estado_Pago"] = "Pendiente"
    
    # ========== COSTO UNITARIO ==========
    if datos.get("Total_a_Pagar") and datos.get("Total_a_Pagar") > 0 and datos.get("Consumo_Cantidad"):
        try:
            total = datos["Total_a_Pagar"]
            consumo = datos["Consumo_Cantidad"]
            if consumo > 0:
                datos["Costo_Unitario"] = round(total / consumo, 2)
        except (ValueError, TypeError):
            pass
    
    return datos

def enviar_datos_a_sheets(service, spreadsheet_id, sheet_name, headers, datos):
    """Envía UN dato a Google Sheets"""
    try:
        next_row = check_and_create_headers(service, spreadsheet_id, sheet_name, headers)
        
        fila = [
            datos.get("Empresa", ""),
            datos.get("Numero_Cliente", ""),
            datos.get("Nombre_Cliente", ""),
            datos.get("Cuenta_Padre", ""),
            # datos.get("Documento_Equivalente", ""),
            datos.get("Direccion", ""),
            datos.get("Periodo_Facturacion", ""),
            datos.get("Fecha_Pago_Oportuno", ""),
            datos.get("Fecha_Suspension", ""),
            datos.get("Total_a_Pagar", ""),
            datos.get("Total_Aseo", ""),
            # datos.get("Total_a_Pagar", ""),
            datos.get("Consumo_Cantidad", ""),
            datos.get("Consumo_Unidad", ""),
            datos.get("Costo_Unitario", ""),
            datos.get("Estado_Pago", ""),
            datos.get("NIT_Empresa", ""),
            datos.get("NIT_Aseo", ""),
            datos.get("Prestador_Aseo",""),
            datos.get("Aseo_Servicio_No_Residencial", ""),
            datos.get("Aseo_Contribucion_No_Residen", ""),
            datos.get("Aseo_Ajuste_Decena", ""),
            datos.get("Aseo_Reliquidacion", ""),
            datos.get("Aseo_Menor_Valor", "")
        ]
        
        range_name = f"{sheet_name}!A{next_row}:W{next_row}"
        
        body = {'values': [fila]}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return True
        
    except HttpError as error:
        logging.error(f"❌ Error HTTP: {error}")
        return False
    except Exception as e:
        logging.error(f"❌ Error enviando datos: {e}")
        return False

def main():
    """Función principal"""
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))

    if not pdf_files:
        logging.warning(f"⚠️ No hay PDFs en: {PDF_DIR}")
        return

    logging.info(f"📊 Procesando {len(pdf_files)} archivo(s) PDF...")

    try:
        creds = authenticate_google_sheets()
        service = build('sheets', 'v4', credentials=creds)
    except Exception as e:
        logging.error(f"❌ Error de autenticación: {e}")
        return

    total_facturas = 0
    total_paginas = 0
    facturas_exitosas = 0
    facturas_fallidas = 0
    facturas_en_lote = 0
    num_lote = 1
    
    for pdf_file in pdf_files:
        logging.info(f"\n{'='*70}")
        logging.info(f"📄 PROCESANDO: {os.path.basename(pdf_file)}")
        logging.info(f"{'='*70}")
        
        paginas = extraer_paginas_pdf(pdf_file)
        
        if not paginas:
            logging.warning(f"⚠️ No se pudo extraer páginas")
            continue
        
        # Procesar CADA PÁGINA
        for pagina_info in paginas:
            num_pagina = pagina_info['numero']
            texto_pagina = pagina_info['texto']
            total_paginas += 1
            
            logging.info(f"\n📖 Página {num_pagina}/{len(paginas)}")
            
            datos = extraer_datos_factura(texto_pagina)


            # 🔥 NUEVO: corregir prestador con coordenadas
            if datos:
                prestador = extraer_prestador_por_coordenadas(pdf_file, num_pagina)
                if prestador:
                    datos["Prestador_Aseo"] = prestador

            # 🔥 NUEVO: corregir dirección (VERSIÓN BUENA)
            if datos and datos.get("Numero_Cliente"):
                direccion = extraer_direccion(texto_pagina, datos["Numero_Cliente"])
                if direccion:
                    datos["Direccion"] = direccion
            
            if datos and datos.get("Numero_Cliente"):
                total_facturas += 1
                facturas_en_lote += 1
                
                logging.info(f"   ✅ FACTURA PROCESADA ({facturas_en_lote}/{FACTURAS_POR_LOTE}):")
                logging.info(f"      🔹 Cliente: {datos.get('Numero_Cliente')} - {datos.get('Nombre_Cliente')}")
                logging.info(f"      🔹 Período: {datos.get('Periodo_Facturacion')}")
                logging.info(f"      🔹 Total Energía: ${datos.get('Total_Energia')}")
                logging.info(f"      🔹 Total Aseo: ${datos.get('Total_Aseo')}")
                logging.info(f"      🔹 Total a Pagar: ${datos.get('Total_a_Pagar')}")
                logging.info(f"      🔹 Consumo: {datos.get('Consumo_Cantidad')} {datos.get('Consumo_Unidad')}")
                logging.info(f"      🔹 Costo/Unidad: ${datos.get('Costo_Unitario')}")
                logging.info(f"      🔹 NIT: {datos.get('NIT_Empresa')}")
                
                # ENVIAR A SHEETS INMEDIATAMENTE
                if enviar_datos_a_sheets(service, SPREADSHEET_ID, SHEET_NAME, HEADERS, datos):
                    logging.info(f"      ✅ Subido a Google Sheets correctamente")
                    facturas_exitosas += 1
                else:
                    logging.error(f"      ❌ Error al subir a Google Sheets")
                    facturas_fallidas += 1
                
                # PAUSA DESPUÉS DE CADA LOTE
                if facturas_en_lote >= FACTURAS_POR_LOTE:
                    logging.info(f"\n{'='*70}")
                    logging.info(f"⏸️  PAUSA ENTRE LOTES")
                    logging.info(f"📊 LOTE {num_lote}: {facturas_en_lote} facturas procesadas")
                    logging.info(f"⏳ Esperando {PAUSA_ENTRE_LOTES} segundos...")
                    logging.info(f"{'='*70}")
                    
                    time.sleep(PAUSA_ENTRE_LOTES)
                    
                    # Reset contador
                    facturas_en_lote = 0
                    num_lote += 1
                    
                    logging.info(f"✅ Reanudando procesamiento - LOTE {num_lote}")
            else:
                if datos is None:
                    logging.info(f"   ⏭️ Página {num_pagina}: No es una factura ENEL válida (sin 'Tipo de Lectura: Real')")
                elif not datos.get("Numero_Cliente"):
                    logging.info(f"   ⏭️ Página {num_pagina}: No se encontró número de cliente válido")
                else:
                    logging.info(f"   ⏭️ Página {num_pagina}: Sin factura válida")
        
        logging.info(f"\n✅ Archivo completado: {len(paginas)} páginas procesadas")
    
    logging.info(f"\n{'='*70}")
    logging.info(f"✅ PROCESO FINALIZADO EXITOSAMENTE")
    logging.info(f"{'='*70}")
    logging.info(f"📊 RESUMEN GENERAL:")
    logging.info(f"   📄 Total de páginas procesadas: {total_paginas}")
    logging.info(f"   ✅ Total facturas extraídas: {total_facturas}")
    logging.info(f"   ✅ Facturas subidas exitosamente: {facturas_exitosas}")
    logging.info(f"   ❌ Facturas con error: {facturas_fallidas}")
    logging.info(f"   ⏭️ Páginas sin factura válida: {total_paginas - total_facturas}")
    logging.info(f"📤 Todas las facturas están en Google Sheets")
    logging.info(f"📝 Revisa '{LOG_FILE}' para más detalles del procesamiento")
    logging.info(f"{'='*70}\n")

if __name__ == "__main__":
    main()