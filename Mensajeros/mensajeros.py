# cSpell:disable
'''
Proceso para consultar informacion de los mensajeros mediante el Simit
'''
# IMPORTACIÓN DE LIBRERÍAS
import os
import re
import sys
import time
import logging
import gspread
import requests
import traceback
import json
import pandas as pd
from io import StringIO
from typing import Optional
from datetime import datetime
from gspread.exceptions import SpreadsheetNotFound
from google.oauth2.service_account import Credentials
from webdriver_manager.chrome import ChromeDriverManager
from gspread_formatting import format_cell_range, CellFormat
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException
    )
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService

# Importaciones necesarias para enviar un correo
import smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage

# CONFIGURACIÓN GLOBAL de google sheets
def inicializar_sheets():
    CREDENTIALS_PATH = r"C:\Users\dforero\Pictures\Proyecto_Automatizaciones_Completo\Mensajeros\automatizaciones-471213-ba561bdefbc9.json"
    SPREADSHEET_ID = "1yVszdoqBzG10ZYXsuX9EXs0tuD_Ni9HBsW7DdK1OxN4"
    SHEET_NAME = "Cédula de Domiciliarios"
    SHEET_NAME2 = "Reporte Comparendos"
    SHEET_NAME3 = "Control"
    # Autenticación con Google Sheets credenciales de servicio.
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    sheet2 = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME2)
    sheet3 = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME3)
    return client,credentials,sheet,sheet2,sheet3,SPREADSHEET_ID,SHEET_NAME2

# _______ Configuracion del driver________
def iniciar_driver() -> Optional[webdriver.Chrome]:
    '''
    Inicia el driver de Selenium con varias opciones para evitar detección y errores.
    '''
    try:
        options = webdriver.ChromeOptions()

        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--profile-directory=Profile 1")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-save-password-bubble")

        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except WebDriverException as e:
        logging.error("Error al iniciar el driver: %s", e)
        return None

def send_error_email(subject: str, body: str, attachment_path: Optional[str] = None):
    # Configuracion para enviar correos
    SENDER_EMAIL = "david.forero.cop@gmail.com" # Usuario propietario de la contraseña de aplicaciones 
    SENDER_PASSWORD = 'zuxw oiut evev jdkf' # contraseñas de aplicaciones cambiarla siempre que cambien de usuario
    RECEIVER_EMAIL = "david.forero.cop@gmail.com" # Aqui se coloca a quien le enviaremos el correo
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465 # Puerto SMTP
    time.sleep(1)  # Espera 1 segundo para evitar problemas de conexión
    """
        Envía un correo electrónico con el asunto, cuerpo y opcionalmente un archivo adjunto.
    """
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"Error en Automatización - {subject}"

    msg.attach(MIMEText(body, 'plain'))

    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
            msg.attach(part)
        except Exception as e:
            logging.error(f"No se pudo adjuntar el archivo {attachment_path} al correo: {e}")

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        server.quit()
        logging.info(f"Correo de error enviado con asunto: {subject}")
        print(f"Correo de error enviado: {subject}")

    except TimeoutException as e:
        error_message = f"ERROR: No se pudo enviar el correo de error debido a un timeout: {e}"
        print(error_message)

        # Envía el correo
        send_error_email(
            subject = "Error al enviar correo de error",
            body = error_message,
            attachment_path = None  # No adjuntamos nada en este caso
        )
        
        raise  # Detiene el flujo completamente
    except Exception as e:
        logging.error(f"Fallo al enviar el correo de error: {e}")
        logging.exception("Detalle del error al enviar correo:") # Esto te dará el traceback completo
        print(f"Fallo al enviar el correo de error: {e}")


# ------------------ Checkpoint utilities ------------------
CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), 'checkpoint.txt')

def guardar_checkpoint(indice: int):
    """Guarda el índice (entero) del último registro procesado en un archivo local.

    Mantiene compatibilidad escribiendo un entero simple (histórico). Para metadatos
    más ricos usar guardar_checkpoint_meta.
    """
    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            f.write(str(int(indice)))
    except Exception as e:
        logging.error(f"Error al guardar checkpoint: {e}")
        raise


def guardar_checkpoint_meta(meta: dict):
    """Guarda un checkpoint enriquecido (JSON) con claves como:
    {"last_cedula_index": 30, "last_sheet2_row": 1234, "timestamp": "..."}
    """
    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error al guardar checkpoint meta: {e}")
        raise

def leer_checkpoint() -> int:
    """Lee el checkpoint y devuelve el índice desde el cual reanudar. Si no existe, devuelve 1."""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                contenido = f.read().strip()
                if not contenido:
                    return 1
                # Intentar parsear JSON de checkpoint meta
                try:
                    obj = json.loads(contenido)
                    if isinstance(obj, dict) and 'last_cedula_index' in obj:
                        return max(1, int(obj.get('last_cedula_index', 1)))
                except Exception:
                    pass
                # Fallback histórico: archivo con entero
                try:
                    return max(1, int(contenido))
                except Exception:
                    return 1
        return 1
    except Exception as e:
        logging.error(f"Error al leer checkpoint: {e}")
        return 1


def leer_checkpoint_meta() -> dict:
    """Lee el archivo de checkpoint y devuelve un diccionario con metadatos si está disponible.
    Devuelve {} si no hay información válida.
    """
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                contenido = f.read().strip()
                if not contenido:
                    return {}
                try:
                    obj = json.loads(contenido)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    # si no es JSON, devolver la forma histórica
                    try:
                        valor = int(contenido)
                        return {'last_cedula_index': valor}
                    except Exception:
                        return {}
        return {}
    except Exception as e:
        logging.error(f"Error al leer checkpoint meta: {e}")
        return {}


def normalize_checkpoint_meta_file():
    """
    Si el archivo de checkpoint contiene la clave 'timestamp', la elimina
    y reescribe el archivo con solo las claves relevantes (last_cedula_index, last_sheet2_row).
    Esto asegura que checkpoints antiguos con timestamp se normalicen a la nueva forma.
    """
    try:
        meta = leer_checkpoint_meta()
        if not meta:
            return
        if 'timestamp' in meta:
            try:
                # construir nuevo meta solo con las claves esperadas
                new_meta = {}
                if 'last_cedula_index' in meta:
                    new_meta['last_cedula_index'] = int(meta['last_cedula_index'])
                if 'last_sheet2_row' in meta:
                    new_meta['last_sheet2_row'] = int(meta['last_sheet2_row'])
                guardar_checkpoint_meta(new_meta)
                logging.info('Checkpoint meta normalizado (se eliminó timestamp).')
            except Exception as e:
                logging.warning(f'No se pudo normalizar checkpoint meta: {e}')
    except Exception as e:
        logging.debug(f'No se pudo ejecutar normalize_checkpoint_meta_file: {e}')

def borrar_checkpoint():
    """Vacía el archivo de checkpoint sin eliminarlo del sistema de archivos.

    Preferimos mantener el archivo presente (por permisos y por consistencia con
    otros procesos) pero borrando su contenido para indicar 'sin checkpoint'.
    """
    try:
        # Abrir en modo escritura truncará el archivo o lo creará si no existe
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        logging.info(f"Checkpoint vaciado correctamente: {CHECKPOINT_FILE}")
    except Exception as e:
        logging.warning(f"No se pudo vaciar el checkpoint: {e}")

# ------------------------------------------------------------

def screenshot(driver: webdriver.Chrome, screenshot_name: str, error_subject: str = "Error General Automatización"):
    """
    Toma una captura de pantalla y la guarda en una carpeta 'screenshots'.
    """
    screenshots_dir = "screenshots"
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        logging.info(f"Creado directorio para capturas de pantalla: {screenshots_dir}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # Formato de timestamp corregido para nombre de archivo
    filename = os.path.join(screenshots_dir, f"{screenshot_name}_{timestamp}.png")
    
    screenshot_saved = False
    try:
        driver.save_screenshot(filename)
        logging.error(f"Captura de pantalla guardada: {filename}")
        print(f"Captura de pantalla guardada: {filename}")

        time.sleep(1)  # Espera 1 segundo para asegurar que el archivo se haya escrito correctamente
        screenshot_saved = True
    except WebDriverException as e:
        logging.error(f"No se pudo tomar la captura de pantalla: {e}")
        print(f"Error al tomar captura de pantalla: {e}")

    # Prepara la información sobre la captura de pantalla
    screenshot_info = f"Captura: {os.path.basename(filename)}" if screenshot_saved else "Captura: No disponible"
    
    # Cuerpo del SMS - ¡Sé conciso!
    # Incluimos la ruta relativa para que sepas dónde buscar el archivo localmente.
    sms_body_message = (
        f"ERROR: {error_subject}\n"
        f"{screenshot_info} (en '{screenshots_dir}')\n"
        f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"URL: {driver.current_url if driver else 'N/A'}"
    )

    # Limita el cuerpo del mensaje si es demasiado largo para un SMS estándar
    if len(sms_body_message) > 500:
        sms_body_message = sms_body_message[:497] + "..."

    send_error_email(error_subject, sms_body_message, attachment_path=filename if screenshot_saved else None)
    print(f"DEBUG: Se enviaría un email con el siguiente contenido:\n{sms_body_message}")

#   Cerrar el modal de info
def cerrar_modal_info(driver):
    '''
    Cierra el modal informativo inicial del SIMIT si está presente.
    '''
    try:
        cerrar_modal = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="modalInformation"]/div/div/div[1]/button/span'))
        )
        driver.execute_script("arguments[0].click();", cerrar_modal)
    except Exception as e:
        logging.warning("No se pudo cerrar el modal: %s", str(e))


def esperar_modal(driver):
    '''
    Espera a que desaparezca el loader ('block-ui-message') de la página.
    '''
    try:
        logging.info("Esperando a que desaparezca el modal de espera...")
        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "block-ui-message"))
        )
        logging.info("El modal de espera ha desaparecido.")
    except TimeoutException:
        logging.warning("El modal de espera no desapareció a tiempo (10 segundos).")
        screenshot(driver, "error_no_desapareció_el_modal_esperar", "Error: Modal de espera")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado al esperar el modal: {e}")
        screenshot(driver, "error_inesperado_al_esperar_modal", "Error: Modal de espera")

def click_elemento(driver: webdriver.Chrome, elemento=None, cedula: str = "N/A", locator=None, timeout: int = 10):
    '''
    Realiza un clic en un elemento usando JavaScript, con reintento en caso de stale element.
    Puedes pasar el elemento directamente o un locator (By, valor).
    '''
    try:
        # Si se pasó un locator, buscar el elemento
        if locator:
            elemento = WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
        elif not elemento or not isinstance(elemento, WebElement):
            logging.error(f"[{cedula}] Elemento no válido no se proporcionó locator")
            screenshot(driver, f"click_error_no_element_{cedula}", "Error: Elemento no válido para clic")
            return False

        # Scroll al elemento
        driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
        time.sleep(1)

        # Clic con JS
        driver.execute_script("arguments[0].click();", elemento)
        logging.info(f"[{cedula}] Clic en elemento (JS): {elemento.tag_name} con texto '{elemento.text}'")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '(//div[contains(@class, "form-group")]//p)[1]'))
        )

        return True
    except StaleElementReferenceException:
        # Se crea esta exepcion por posibles errores con el stale element que desaparece despues de darle clic al link de las multas y comparendos
        logging.warning(f"[{cedula}] se le da click 1 vez en el boton del link")
        return False
    except ElementNotInteractableException as e:
        logging.warning(f"[{cedula}] Elemento no interactuable: {e}")
        screenshot(driver, f"click_error_not_interactable_{cedula}", "Elemento no interactuable")
        return False
    except (WebDriverException, TimeoutException) as e:
        logging.warning(f"[{cedula}] WebDriverException al hacer clic: {e}")
        screenshot(driver, f"click_error_webdriver_{cedula}", str(e))
        time.sleep(2)
        return False
    except Exception as e:
        logging.error(f"[{cedula}] Error inesperado al hacer clic: {e}")
        traceback.print_exc()
        screenshot(driver, f"click_error_unexpected_{cedula}", str(e))
        return False

# Alineacion del exel
def alinear_derecha(sheet_obj, rango: str):
    '''
    Aplica alineación a la izquierda en un rango de celdas en una hoja de cálculo.
    '''
    formato = CellFormat(horizontalAlignment='LEFT')
    format_cell_range(sheet_obj, rango, formato)

# Formatetear valores numericos a moneda Colombiana
def formatear_valor(valor):
    if isinstance(valor, (int, float)):
        return f"$ {valor:,.0f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return str(valor)

# Extraer fecha de algun texto
def extraer_fecha(texto):
    '''
    Extrae una fecha con formato DD/MM/AAAA desde un texto dado.
    '''
    match = re.search(r"\d{2}/\d{2}/\d{4}", texto)
    return match.group() if match else texto

# Opciones que puede tomar el boton de devolver en la paguina del simit
def intentar_volver(driver):
    '''
    Intenta hacer clic en el botón 'Volver' desde distintas ubicaciones del sitio.
    '''
    botones_xpaths = [
        "//button[contains(text(), 'Volver')]",
        "//button[contains(@class, 'btn-outline-primary') and contains(text(), 'Volver')]",
        "//*[@id='mainView']/div/div/div[1]/div/div[2]/button",
        "//div[contains(@class, 'mt-3')]//button[contains(text(), 'Volver')]",
        "//button[normalize-space(text())='Volver']",
        "#mainView > div > div > div.col-lg-3.margin-top-info-detalle > div > div.col-lg-12.col-md-6.col-12.p-0.mt-3 > button",
        '//*[@id="mainView"]/div/div/div[1]/div/div[2]/button'
    ]
    for xpath in botones_xpaths:
        try:
            # Detectar si es CSS selector o XPath
            if xpath.startswith("//") or xpath.startswith("/") or xpath.startswith('//') or xpath.startswith('/'):
                btn = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
            else:
                btn = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, xpath))
                )

            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1)  # Dar tiempo a que vuelva
            return True  # Éxito
        except:
            continue  # Intenta con el siguiente
    return False  # Ninguno funcionó

def manejar_modal_coincidencias(driver):
    '''
    Si aparece un modal con múltiples coincidencias, selecciona la opción más apropiada y continúa.
    '''
    prioridad = [
        "Cédula",
        "Cédula de ciudadanía",
        "Nit",
        "Pasaporte",
        "Cédula de extranjería"
    ]
    try:
        # Esperar a que aparezca el modal
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="modal-multiples-personas"]'))
        )
        modal = driver.find_element(By.XPATH, '//*[@id="modal-multiples-personas"]')
        # Obtener todas las opciones de radio
        radios = modal.find_elements(By.XPATH, ".//input[@type='radio']")
        labels = modal.find_elements(By.XPATH, ".//label[contains(@for, 'rdPerRep')]")

        mejor_opcion = None
        mejor_radio = None

        criterio = None
        for criterio in prioridad:
            for radio, label in zip(radios, labels):
                texto = label.text.strip().lower()
                if criterio.lower() in texto:
                    mejor_opcion = label.text.strip()
                    mejor_radio = radio
                    break
            if mejor_opcion:
                break

        if not mejor_radio and radios:
            # Si no se encontró una opción con prioridad, tomar la primera
            mejor_radio = radios[0]
            mejor_opcion = labels[0].text.strip()

        if mejor_radio:
            driver.execute_script("arguments[0].click();", mejor_radio)
            logging.info(f"Opción seleccionada en el modal: {mejor_opcion} ({criterio})")
        else:
            return False
        # Hacer clic en el botón Continuar
        boton_continuar = modal.find_element(By.XPATH, ".//button[contains(text(),'Continuar')]")
        driver.execute_script("arguments[0].click();", boton_continuar)
        return True
    except TimeoutException:
        logging.debug("No apareció el modal de coincidencias.")
        return False
    except Exception as e:
        logging.error(f"Error al manejar el modal de coincidencias: {e}")
        return False

def convertir_a_entero(texto):
    try:
        texto = texto.replace(u'\xa0', ' ')  # Reemplaza el &nbsp que contienen algunos datos necesarios
        texto = texto.replace("$", "").replace(".", "").replace(",", "").strip()
        return int(texto) if texto else 0
    except ValueError:
        logging.warning(f"No se pudo convertir a entero: '{texto}'")
        return 0

def esperar_loader(driver, timeout=20, max_retries=4):
    '''
    Espera a que desaparezca el loader del SIMIT después de cargar una nueva vista.
    '''
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logging.info(f"Intento {attempt}/{max_retries}: Recargando la página...")
                driver.refresh()
                # Opcional: un pequeño tiempo para que la página empiece a cargar el DOM
                time.sleep(2) 
            logging.info(f"Esperando a que el loader ('#loader') desaparezca (Intento {attempt+1}/{max_retries+1})...")
            
            # Usamos invisibility_of_element_located. 
            # Esto funciona para 'display: none' o cuando el elemento se remueve.
            WebDriverWait(driver, timeout).until(
                EC.invisibility_of_element_located((By.ID, "loader"))
            )
            logging.info("El loader ha desaparecido.")
            return True # El loader desapareció, salimos de la función

        except TimeoutException:
            logging.warning(f"El loader no desapareció a tiempo ({timeout} segundos) en el intento {attempt+1}.")
            if attempt < max_retries:
                logging.info("Intentando recargar la página...")
            else:
                logging.error(f"Se agotaron los {max_retries} reintentos. El loader persiste. No se pudo continuar.")
                raise TimeoutError("El loader no desapareció después de los reintentos.")
        except WebDriverException as e:
            logging.error(f"Ocurrió un error de WebDriver inesperado en el intento {attempt+1}: {e}")
            if attempt < max_retries:
                logging.info("Intentando recargar la página...")
            else:
                logging.error(f"Se agotaron los {max_retries} reintentos debido a un error de WebDriver. No se pudo continuar.")
                raise WebDriverException("El loader no desapareció después de los reintentos.")
        except Exception as e:
            logging.error(f"Ocurrió un error inesperado en el intento {attempt+1}: {e}")
            if attempt < max_retries:
                logging.info("Intentando recargar la página...")
            else:
                logging.error(f"Se agotaron los {max_retries} reintentos debido a un error inesperado. No se pudo continuar.")
                raise Exception("EL loader no desaparecio")
    raise # En caso de que algo salga mal y no se retorne antes

def ir_a_pagina(driver, pagina_deseada):
    intentos = 0
    while intentos < 10:
        try:
            try:
                boton_activo = driver.find_element(By.CSS_SELECTOR, "button.number-pagination.active")
                pagina_actual = int(boton_activo.get_attribute("value"))
                
            except NoSuchElementException:
                logging.info("No hay paginación (una sola página). No se requiere cambio de página.")
                return True  # Asumimos que ya está en la única página disponible

            if pagina_actual == pagina_deseada:
                return True  # Ya estamos en la página correcta

            if pagina_actual > pagina_deseada:
                logging.warning(f"Estamos en la página {pagina_actual} pero queremos ir a la {pagina_deseada}. No se puede retroceder.")
                return False

            # Avanzar a la siguiente
            boton_siguiente = driver.find_element(By.CLASS_NAME, "button-next")
            if boton_siguiente.get_attribute("aria-disabled") == "true":
                logging.warning(f"No se puede avanzar más allá de la página {pagina_actual}.")
                return False

            boton_siguiente.click()
            time.sleep(1.5)
            esperar_loader(driver)
            intentos += 1
        except Exception as e:
            logging.warning(f"Error al intentar ir a la página {pagina_deseada}: {e}")
            return False
    return False

def recolectar_multas(driver: webdriver.Chrome, cedula: str):
    '''
    Extrae la información detallada de las multas y acuerdos de pago de una cédula.
    '''
    esperar_loader(driver)
    esperar_modal(driver)
    time.sleep(1.8)
    manejar_modal_coincidencias(driver)
    datos = [] # Lista para almacenar los datos recolectados
    pagina_actual = 1
    try:
        # Esperar la tabla inicial de comparendos o multas
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="multaTable"]/tbody/tr'))
        )
        while True:
            salir_paginacion = False
            if salir_paginacion == True:
                break
            try:
                # Obtenemos el número de filas de los comparendos y multas
                filas = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.page-row:not([style*='display: none'])"))
                )
                # ciclo de número de veces que se repetirá la acción dependiendo de las filas encontradas
                for idx in range(len(filas)):
                    # Cada vez, recargamos la referencia a las filas
                    filas = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.page-row:not([style*='display: none'])"))
                    )
                    try:
                        filas = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.page-row:not([style*='display: none'])"))
                        )
                        fila = filas[idx]
                        celdas = fila.find_elements(By.TAG_NAME, "td")

                        if len(celdas) < 8:
                            continue

                        try:
                            time.sleep(2.1)
                            
                            tipo = celdas[0].find_element(By.TAG_NAME, "p").text
                            texto_completo = celdas[6].text
                            saldo = texto_completo.split("\n")[0]
                            spans = celdas[0].find_elements(By.TAG_NAME, "span")
                            valor_a_pagar_raw = celdas[-2].get_attribute("innerText").split("\n")[0]  # type: ignore
                            valor_a_pagar_num = convertir_a_entero(valor_a_pagar_raw)
                            
                            span_element = celdas[4].find_element(By.TAG_NAME, "span").text
                            codigo_infraccion = span_element.strip()

                            if "Interés" in texto_completo:
                                interes = texto_completo.split("Interés")[-1].strip()
                            else:
                                interes = "0"

                            # Colocar la fecha dependiendo del nombre que comparta con la celda
                            fecha = ""
                            for span in spans:
                                if "Fecha resolución" in span.text:
                                    fecha = span.text
                                    break
                                elif "Fecha imposición" in span.text:
                                    fecha = span.text
                                    break
                                elif "Fecha coactivo" in span.text:
                                    fecha = span.text
                                    break
                            
                            saldo_num = convertir_a_entero(saldo)
                            interes_num = convertir_a_entero(interes)
                            time.sleep(0.3)
                            
                            MAX_REINTENTOS = 3
                            for intento in range(MAX_REINTENTOS):
                                try:
                                    xpath = f"(//tr[contains(@class, 'page-row') and not(contains(@style, 'display: none'))])[{idx + 1}]//td[1]//a"
                                    enlace_detalle = driver.find_element(By.XPATH, xpath)
                                    click_elemento(driver, enlace_detalle, cedula)  # type: ignore
                                    break  # Éxito, salimos del ciclo
                                except StaleElementReferenceException:
                                    logging.warning(f"[{cedula}] Reintento {intento+1}/{MAX_REINTENTOS}: elemento 'stale', reintentando búsqueda...")
                                    screenshot(driver, f"{cedula}_reintento_click.png")
                                    time.sleep(1)
                                    break
                                except NoSuchElementException:
                                    logging.warning(f"[{cedula}] No se encontró enlace de detalle visible en fila {idx + 1}.")
                                    screenshot(driver, f"{cedula}_enlace_click_.png")
                                    break
                                except WebDriverException as e:
                                    logging.warning(f"[{cedula}] WebDriverException al intentar hacer clic en enlace: {e}")
                                    screenshot(driver, f"{cedula}_click_error.png")
                                    break

                            time.sleep(2.4)
                            WebDriverWait(driver, 20).until(
                                EC.presence_of_element_located((By.XPATH, '(//div[contains(@class, "form-group")]//p)[1]'))
                            )
                            try:
                                # lees los campos dinámicos del detalle
                                num_comparendo = driver.find_element(By.XPATH, "(//div[contains(@class, 'form-group')]//p)[1]").text
                                fecha_notificacion_completa = driver.find_element(By.XPATH , "(//div[contains(@class, 'form-group')]//p)[2]").text
                                fecha_resolucion = extraer_fecha(fecha_notificacion_completa)
                                placa = driver.find_element(By.XPATH, '//*[@id="mainView"]/div/div/div[2]/div/div/div[4]/div[1]/p').text
    
                                # Validamos que si por cualquier fallo en la fecha se colocara la fecha que tiene al principio
                                if tipo == "Comparendo":
                                    interes_num = 0

                                interes = valor_a_pagar_num - saldo_num - interes_num
                                total = valor_a_pagar_num

                                if not intentar_volver(driver):
                                    esperar_modal(driver)
                                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@id='txtBusqueda']")))
                                    cerrar_modal_info(driver)
                                    time.sleep(2)
                                    input_cedula = driver.find_element(By.XPATH, "//input[@id='txtBusqueda']")
                                    input_cedula.clear()
                                    time.sleep(2)
                                    
                                    input_cedula.send_keys(cedula)
                                    try:    
                                        try:
                                            btnNumDocPlaca = WebDriverWait(driver, 20).until(
                                                EC.element_to_be_clickable((By.XPATH, '//*[@id="btnNumDocPlaca"]'))
                                            )
                                            btnNumDocPlaca.click()
                                        except Exception:
                                            consultar_btn = WebDriverWait(driver, 20).until(
                                                EC.element_to_be_clickable((By.XPATH, '//*[@id="consultar"]'))
                                            )
                                            consultar_btn.click()
                                        except TimeoutException: # type: ignore
                                            logging.warning("No apareció el boton, se continúa con el flujo.")

                                    except TimeoutException:
                                        logging.warning("No se encontraron los botones del buscador del simit por favor verificarlos")

                                botones_activos = driver.find_elements(By.CSS_SELECTOR, "button.number-pagination.active")
                                if botones_activos:
                                    boton_activo = botones_activos[0]
                                    pagina_actual_text = boton_activo.get_attribute("value")
                                else :
                                    pagina_actual_text = '1'  

                                if not ir_a_pagina(driver, pagina_actual):
                                    logging.warning(f"No se pudo volver a la página {pagina_actual}. Probando con recarga...")
                                    driver.refresh()
                                    esperar_loader(driver)

                                    if not ir_a_pagina(driver, pagina_actual):
                                        logging.warning(f"No se pudo volver ni recargando. Deteniendo recolección.")
                                        screenshot(driver, f"no_volver_ni_recargando_{cedula}_{pagina_actual}", "No se pudo volver ni recargando")
                                        salir_paginacion = True
                                        break

                                if int(pagina_actual_text) != pagina_actual: # type: ignore
                                    logging.info(f"Después de volver, estamos en la página {pagina_actual_text}, pero deberíamos estar en la {pagina_actual}. Corrigiendo...")
                                    if not ir_a_pagina(driver, pagina_actual):
                                        logging.warning(f"No se pudo volver a la página {pagina_actual}. Deteniendo recolección.")
                                        salir_paginacion = True
                                        break

                                # Ingrasar datos a la tabla
                                datos.append([
                                    cedula,
                                    tipo,
                                    "VIGENTE",
                                    num_comparendo,
                                    placa,
                                    fecha_resolucion,
                                    fecha,
                                    formatear_valor(saldo_num),
                                    formatear_valor(interes_num),
                                    formatear_valor(interes),
                                    formatear_valor(total),
                                    codigo_infraccion,
                                    "",
                                    "",
                                    ""
                                ])

                                if not filas:
                                    logging.warning("No hay filas en la tabla de comparendos.")
                                    return
                                
                            except Exception as e:
                                logging.warning(f"[{cedula}] Error al recolectar detalle para %s: %s", cedula, str(e))
                                screenshot(driver, f"error_recolectar_detalle_{cedula}_{pagina_actual}_{idx}", f"Error al recolectar detalle para {cedula}")
                        except StaleElementReferenceException:
                            logging.warning(f"[{cedula}] StaleElementReferenceException en fila {idx} de multas. Reintentando la página actual.")
                            screenshot(driver, f"stale_element_multa_fila_{cedula}_{pagina_actual}_{idx}", f"StaleElement en fila de multa {idx}")
                            # FIX: Re-obtener las filas correctamente con CSS_SELECTOR y romper el bucle interior
                            filas = WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.page-row:not([style*='display: none'])"))
                            )
                            break # Romper el bucle interior para que el bucle exterior re-obtenga las filas y reinicie el 'for idx'

                        except Exception as e:
                            logging.warning(f"[{cedula}] Error al procesar fila {idx} de {cedula}: {e}")
                            traceback.print_exc()
                            screenshot(driver, f"error_procesar_fila_multa_{cedula}_{pagina_actual}_{idx}", f"Error al procesar fila de multa {idx}")
                            continue

                        # asegúrate de que la tabla haya vuelto a cargarse
                        WebDriverWait(driver, 7).until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="multaTable"]/tbody/tr'))
                        )
                    except TimeoutException:
                        logging.warning("Detalle de multa no cargó a tiempo para %s", cedula)
                    except Exception as e:
                        logging.warning(f"[{cedula}] Error al procesar fila {idx} de {cedula}: {e}")
                        traceback.print_exc()
                        screenshot(driver, f"error_procesar_fila_multa_{cedula}_{pagina_actual}_{idx}", f"Error al procesar fila de multa {idx}")
                        continue
                    pass
                # Esperar a que vuelva al listado
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tr.page-row"))
                )
                try:
                    botones = driver.find_elements(By.CSS_SELECTOR, "button.number-pagination")
                    if not botones:
                        logging.warning("No se encontró ninguna paginación. Puede que solo haya una página.")
                        salir_paginacion = True
                        break
                    elif botones:
                        ultima_pagina = int(botones[-1].get_attribute("value")) # type: ignore
                        pagina_actual = int(driver.find_element(By.CSS_SELECTOR, "button.number-pagination.active").get_attribute("value")) # type: ignore

                        if pagina_actual == ultima_pagina:
                            logging.info(f"Última página alcanzada ({pagina_actual}). Terminando recolección.")
                            break
                        else:
                            pagina_actual += 1
                            boton_siguiente = driver.find_element(By.CLASS_NAME, "button-next")
                            boton_siguiente.click()
                            time.sleep(2)
                            esperar_loader(driver)
                            logging.info(f"Avanzando a la página {pagina_actual}")
                    else:
                        logging.warning("No se encontraron botones de paginación. Terminando.")
                        break
                except Exception as e:
                    logging.warning(f"[{cedula}] No se pudo avanzar a la siguiente página de multas desde la {pagina_actual}: {e}")
                    screenshot(driver, f"error_avanzar_pagina_multa_{cedula}_{pagina_actual}", f"Error al avanzar página de multas desde {pagina_actual}")
                    break
            except TimeoutException:
                logging.warning(f"[{cedula}] No se encontraron filas en la tabla de multas. Saliendo del bucle.")
                break
    except TimeoutException:
        logging.info(f"[{cedula}]: No hay comparendos o multas (tablas no encontradas en 3s).")
    except Exception as e:
        logging.error(f"[{cedula}] Error inesperado en la sección de multas: {e}")
        traceback.print_exc()
        screenshot(driver, f"error_seccion_multas_{cedula}", "Error en sección de multas")

    try:
        # Esperar la tabla acuerdos de pago 
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="acuerdoPagoTable"]/tbody/tr'))
        )
        while True:
            try:
                filas_acuerdo_elements = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.XPATH, '//*[@id="acuerdoPagoTable"]/tbody/tr'))
                )
                filas_count_acuerdo = len(filas_acuerdo_elements)
                logging.info(f"[{cedula}] Página {pagina_actual}: Encontradas {filas_count_acuerdo} filas de acuerdos.")
            except TimeoutException:
                logging.info(f"[{cedula}] Página {pagina_actual}: No se encontraron filas visibles en la tabla de acuerdos. Fin de paginación o tabla vacía.")
                break
            except Exception as e:
                logging.error(f"[{cedula}] Error al obtener filas de acuerdos en página {pagina_actual}: {e}")
                screenshot(driver, f"error_get_filas_acuerdos_{cedula}_{pagina_actual}", f"Error al obtener filas de acuerdos en página {pagina_actual}")
                break

            if not filas_acuerdo_elements:
                logging.info(f"[{cedula}] No hay acuerdos de pago en esta página. Saliendo del bucle de paginación de acuerdos.")
                break
            
            for idx1 in range(filas_count_acuerdo):
                # Cada vez, recargamos la referencia a las filas
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="acuerdoPagoTable"]/tbody/tr'))
                )

                filas1 = driver.find_elements(By.XPATH, '//*[@id="acuerdoPagoTable"]/tbody/tr')
                try:
                    fila1 = filas1[idx1]
                    columnas = fila1.find_elements(By.TAG_NAME, "td")
                    if len(columnas) < 6:
                        continue
                    # Dtos que necesita la tabla
                    try:
                        time.sleep(1.5)
                        numero_y_fecha = columnas[0].text.strip().split('\n')
                        numero_acuerdo = numero_y_fecha[0].strip()
                        fecha_acuerdo = extraer_fecha(numero_y_fecha[1].strip()) if len(numero_y_fecha) > 1 else ""

                        valor_acuerdo_raw = columnas[5].text.strip()
                        valor_acuerdo = valor_acuerdo_raw.split('\n')[0].strip()  # Solo la primera línea
                        valor_acuerdo = int(valor_acuerdo.replace('.', '').replace('$', '').strip())
                        valor_cuota = columnas[4].text.strip()
                        saldo = columnas[3].text.strip()
                        saldo_num = int(saldo.replace("$", "").replace(".", "").replace(",", "").strip())

                        # Guardar en una nueva fila en la hoja correspondiente
                        datos.append([
                            cedula,  # si estás iterando por cédula
                            'Acuerdo de pago',
                            'VIGENTE',
                            numero_acuerdo,
                            '',
                            fecha_acuerdo,
                            fecha_acuerdo,
                            formatear_valor(saldo_num),
                            valor_cuota,
                            '$ 0',  # Sin interés
                            formatear_valor(valor_acuerdo),
                            '',
                            '',
                            '',
                            ''
                        ])
                    except StaleElementReferenceException:
                        # si ocurre un stale, reloadeamos el índice
                        filas_count_acuerdo = len(driver.find_elements(By.XPATH, '//*[@id="acuerdoPagoTable"]/tbody/tr'))
                        continue
                    except Exception as e:
                        logging.warning(f"Error al procesar fila {idx1} de {cedula}: {e}")
                        continue
                    if not filas_count_acuerdo:
                        logging.warning("No hay filas en la tabla de acuerdos de pago.")
                        return
                except TimeoutException:
                    logging.warning("Detalle de recolectar acuerdo de pago no se cargo a tiempo para %s", cedula)
                except Exception as e:
                    logging.warning("Error al recolectar acuerdo de pago para %s: %s", cedula, str(e))
            try:
                botones = driver.find_elements(By.CSS_SELECTOR, "button.number-pagination")
                if not botones:
                    logging.info(f"[{cedula}] No se encontraron botones de paginación para acuerdos de pago. Puede que solo haya una página.")
                    salir_paginacion = True
                    break
                elif botones:
                    ultima_pagina = int(botones[-1].get_attribute("value")) # type: ignore
                    pagina_actual = int(driver.find_element(By.CSS_SELECTOR, "button.number-pagination.active").get_attribute("value")) # type: ignore

                    if pagina_actual == ultima_pagina:
                        logging.info(f"Última página alcanzada ({pagina_actual}). Terminando recolección.")
                        break
                    else:
                        pagina_actual += 1
                        boton_siguiente = driver.find_element(By.CLASS_NAME, "button-next")
                        boton_siguiente.click()
                        time.sleep(2)
                        esperar_loader(driver)
                        logging.info(f"Avanzando a la página {pagina_actual}")
                else:
                    logging.warning("No se encontraron botones de paginación. Terminando.")
                    break
            except (TimeoutException, NoSuchElementException) as e:
                logging.warning(f"[{cedula}] Error de paginación (Timeout/NoSuchElement) para acuerdos: {e}. Captura de pantalla para depuración.")
                screenshot(driver, f"error_paginacion_acuerdos_element_{cedula}_{pagina_actual}", f"Error de elemento en paginación de acuerdos para {cedula}")
                break
            except Exception as e:
                logging.error(f"[{cedula}] Error inesperado en la lógica de paginación de acuerdos de pago: {e}")
                traceback.print_exc()
                screenshot(driver, f"error_paginacion_acuerdos_inesperado_{cedula}_{pagina_actual}", f"Error inesperado en paginación de acuerdos para {cedula}")
                break # Si no se puede avanzar, terminar el ciclo
    except TimeoutException:
        logging.info(f"[{cedula}]: No hay acuerdos de pago (tabla acuerdos de Pago no encontrada en 3s).")
    except Exception as e:
        logging.error(f"[{cedula}] Error inesperado en la sección de acuerdos de pago: {e}")
        traceback.print_exc()
        screenshot(driver, f"error_seccion_acuerdos_{cedula}", "Error en sección de acuerdos de pago")
    
    return datos

def asegurar_espacio_filas(sheet_obj, fila_inicio, cantidad_necesaria):
    # Asegura que haya suficientes filas disponibles desde la fila_inicio.
    # Si no hay espacio, inserta filas nuevas.
    total_filas_hoja = sheet_obj.row_count
    filas_disponibles = total_filas_hoja - fila_inicio + 1

    if cantidad_necesaria > filas_disponibles:
        filas_faltantes = cantidad_necesaria - filas_disponibles
        print(f"📄 Insertando {filas_faltantes} filas adicionales en la hoja...")
        sheet_obj.add_rows(filas_faltantes)


def write_block_safe(sheet_obj, fila_inicio, valores, max_retries: int = 3):
    """
    Asegura espacio y escribe un bloque de filas en la hoja.
    - sheet_obj: worksheet de gspread
    - fila_inicio: número de fila (1-based) donde empezar a escribir
    - valores: lista de filas (lista de listas) a escribir
    - max_retries: reintentos ante errores temporales

    Devuelve la siguiente fila libre (fila_inicio + len(valores)).
    Lanza la excepción si no se puede escribir tras los reintentos.
    """
    cantidad = len(valores)
    if cantidad == 0:
        return fila_inicio

    asegurar_espacio_filas(sheet_obj, fila_inicio, cantidad)
    end_row = fila_inicio + cantidad - 1
    # Determinar rango de columnas dinámicamente según la longitud de la primera fila
    max_cols = max(len(row) for row in valores)
    # Limitar a una columna razonable si algo va mal
    if max_cols <= 0:
        max_cols = 1
    # Convertir número de columna a letra (soporta hasta 702 columnas: ZZ)
    def col_to_letter(n):
        result = ''
        while n > 0:
            n, rem = divmod(n-1, 26)
            result = chr(65 + rem) + result
        return result

    last_col = col_to_letter(max_cols)
    rango = f"A{fila_inicio}:{last_col}{end_row}"

    for intento in range(1, max_retries + 1):
        try:
            # gspread espera (range, values) o (A1, [[...],...])
            sheet_obj.update(rango, valores)
            return fila_inicio + cantidad
        except Exception as e:
            logging.warning(f"Intento {intento}/{max_retries}: error al actualizar hoja en rango {rango}: {e}")
            time.sleep(1 + intento)
            # intentar añadir algunas filas extra por si la hoja está cerca del límite
            try:
                sheet_obj.add_rows(max(50, cantidad))
            except Exception as e2:
                logging.debug(f"No se pudieron agregar filas extra durante el reintento: {e2}")
            if intento == max_retries:
                logging.error(f"No se pudo escribir el bloque en la hoja tras {max_retries} intentos.")
                raise

def procesar_cedulas(driver, sheet, sheet2, inicio_desde=1):
    # Definir los encabezados de la tabla
    headers = [
        "Cédula",  # Corregido de "Cédulas" a "Cédula"
        "Tipo",
        "Estado",
        "Número Comparendo",
        "Placa",
        "Fecha Resolución",
        "Fecha",
        "Saldo",
        "Intereses",
        "Interes",
        "Total",
        "Código Infracción",
        "Fecha Consulta",
        "Hora Inicio",
        "Hora Fin"
    ]
    # Escribir los encabezados en la primera fila si no están presentes
    try:
        current_headers = sheet2.row_values(1)
        if not current_headers or current_headers != headers:
            sheet2.update([headers], "A1:R1")
            logging.info("Encabezados escritos en la fila 1 de 'Reporte Comparendos'.")
    except Exception as e:
        logging.error(f"Error al escribir los encabezados en 'Reporte Comparendos': {e}")
        raise
    # Nota: NO limpiar el rango de datos para evitar borrar registros previos.
    # Antes este script borraba A2:Z10000 en cada ejecución; eso eliminaba
    # todos los resultados previos. Ahora no se realiza esa limpieza para
    # que los nuevos registros se agreguen por debajo de los existentes.
    # Obtener la lista de cédulas de la hoja
    cedulas = sheet.col_values(1)[1:]
    resultados_bloque = []
    # Iniciar driver
    try:
        driver.get("https://www.fcm.org.co/simit/#/home-public")
        esperar_modal(driver)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@id='txtBusqueda']")))
        cerrar_modal_info(driver)
    except TimeoutException as e:
        print(f"ERROR: No se cargó la página inicial del SIMIT o elementos principales: {e}")
        screenshot(driver, "pagina_inicial_simit_error", "Error al cargar la página inicial del SIMIT")
        raise  # Usa raise para propagar el error al main y manejarlo allá

    esperar_modal(driver)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@id='txtBusqueda']")))
    cerrar_modal_info(driver)
    fila_actual = len(sheet2.col_values(1)) + 1  # siguiente fila vacía
    time.sleep(3)
    for index, cedula in enumerate(cedulas, start=1):
        if index < inicio_desde:
            continue  # saltar hasta la posición deseada
        
        current_date = datetime.now().strftime("%Y-%m-%d") 
        inicio = datetime.now()
        fin = None # Inicializamos fin aquí para que siempre tenga un valor, incluso si hay un error o no se encuentran comparendos/acuerdos.
        try:
            input_cedula = driver.find_element(By.XPATH, "//input[@id='txtBusqueda']")
            input_cedula.clear()
            print(f"Procesando cédula {index}/{len(cedulas)}: {cedula}")
            input_cedula.send_keys(cedula)
            esperar_loader(driver)
            try:
                try:
                    btnNumDocPlaca = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="btnNumDocPlaca"]'))
                    )
                    btnNumDocPlaca.click()
                except Exception:
                    consultar_btn = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="consultar"]'))
                    )
                    consultar_btn.click()
                except TimeoutException: # type: ignore
                    logging.warning("No apareció el boton, se continúa con el flujo.")
                    raise 

            except TimeoutException:
                logging.warning("No se encontraron los botones del buscador del simit por favor verificarlos")
                raise 

            multas = recolectar_multas(driver, cedula)
            fin = datetime.now()

            if not multas:
                resultados_bloque.append([cedula, "No hay comparendos actuales"] + [""] * 10 + [current_date, inicio.strftime("%H:%M:%S") , fin.strftime("%H:%M:%S")])
            else:
                # Aseguramos que todas las filas de multas tengan las fechas de inicio y fin.
                multas_con_fechas = []
                for multa in multas:
                    if len(multa) < 15: # Si la longitud de la fila no es 14, significa que le faltan las fechas
                        multa.extend([""] * (12 - len(multa) + 3)) # Rellenamos con vacíos hasta la posición correcta si es necesario
                    multa[-3] = current_date
                    multa[-2] = inicio.strftime("%H:%M:%S") # Actualizamos la penúltima posición con la fecha de inicio
                    multa[-1] = fin.strftime("%H:%M:%S")   # Actualizamos la última posición con la fecha de fin
                    multas_con_fechas.append(multa)
                resultados_bloque.extend(multas_con_fechas)
        except Exception as e:
            logging.error("Error con la cédula %s: %s", cedula, str(e))
            fin = datetime.now() # Registramos el fin incluso en caso de error
            # En caso de error, también aseguramos que las fechas se incluyan.
            resultados_bloque.append([cedula, "Error"] + [""] * 10 + [current_date, inicio.strftime("%H:%M:%S"), fin.strftime("%H:%M:%S")])

        # Ingresar datos al exel
        # se repetira X veses antes de guardar en el exel
        if index % 30 == 0 or index == len(cedulas):
            print(f"⏳ Guardando bloque hasta cédula #{index}")
            # Filtrar filas con longitud correcta (15 columnas)
            bloque_filtrado = [fila for fila in resultados_bloque if len(fila) == 15]
            if bloque_filtrado:
                # Antes de escribir, deduplicar contra lo que ya existe en sheet2
                try:
                    existing_pairs = set()
                    existing_cedulas = set()
                    try:
                        existing_vals = sheet2.get_all_values()
                        # Omitir encabezado
                        for row in existing_vals[1:]:
                            ced_exist = str(row[0]).strip() if len(row) > 0 else ''
                            num_exist = str(row[3]).strip() if len(row) > 3 else ''
                            if ced_exist:
                                existing_cedulas.add(ced_exist)
                            if ced_exist and num_exist:
                                existing_pairs.add((ced_exist, num_exist))
                    except Exception as e:
                        logging.warning(f"No se pudieron leer filas existentes de sheet2 para deduplicación: {e}")

                    # Deduplicación también dentro del propio bloque
                    bloque_filtrado_dedup = []
                    seen_pairs = set()
                    seen_ceds = set()
                    for fila in bloque_filtrado:
                        ced = str(fila[0]).strip() if len(fila) > 0 else ''
                        tipo = str(fila[1]).strip() if len(fila) > 1 else ''
                        num = str(fila[3]).strip() if len(fila) > 3 else ''

                        # Si es el caso 'No hay comparendos actuales' o no hay número de comparendo,
                        # aplicamos deduplicación por cédula únicamente.
                        if tipo == "No hay comparendos actuales" or num == '':
                            if (ced in existing_cedulas) or (ced in seen_ceds):
                                logging.debug(f"Omitiendo fila 'No hay comparendos' para cédula {ced} porque ya existe.")
                                continue
                            bloque_filtrado_dedup.append(fila)
                            seen_ceds.add(ced)
                        else:
                            # Deduplicación por par (cédula, número comparendo)
                            key = (ced, num)
                            if key in existing_pairs or key in seen_pairs:
                                logging.debug(f"Omitiendo fila duplicada para (cedula,comparendo)={key}")
                                continue
                            bloque_filtrado_dedup.append(fila)
                            seen_pairs.add(key)

                    if not bloque_filtrado_dedup:
                        logging.info(f"Ninguna fila nueva para escribir en este bloque hasta cédula #{index}. Se omite escritura.")
                        # Guardar checkpoint para indicar que procesamos hasta esta cédula, pero no se añadieron filas
                        try:
                            meta = {
                                'last_cedula_index': int(index),
                                'last_sheet2_row': int(fila_actual - 1),
                                'last_cedula': str(cedula)
                            }
                            guardar_checkpoint_meta(meta)
                            logging.debug(f"Checkpoint meta guardado (sin filas nuevas): {meta}")
                        except Exception as e:
                            logging.warning(f"No se pudo guardar checkpoint meta tras omitir escritura: {e}")
                    else:
                        # Escribir solo las filas no duplicadas
                        try:
                            siguiente_libre = write_block_safe(sheet2, fila_actual, bloque_filtrado_dedup)
                            # Alinear la columna de valores (I) en el rango escrito
                            alinear_derecha(sheet2, f"I{fila_actual}:I{siguiente_libre - 1}")
                            last_written_row = int(siguiente_libre - 1)
                            fila_actual = siguiente_libre
                            # Guardar checkpoint sólo después de que el bloque se haya escrito correctamente
                            try:
                                meta = {
                                    'last_cedula_index': int(index),
                                    'last_sheet2_row': last_written_row,
                                    'last_cedula': str(cedula)
                                }
                                guardar_checkpoint_meta(meta)
                                logging.debug(f"Checkpoint meta guardado tras escribir bloque: {meta}")
                            except Exception as e:
                                logging.warning(f"No se pudo guardar el checkpoint meta tras escribir bloque hasta {index}: {e}")
                        except Exception as e:
                            logging.error(f"Fallo al escribir bloque en Google Sheets (dedup): {e}")
                            # No queremos perder los datos; relanzamos para que el flujo principal lo maneje
                            raise
                except Exception as e:
                    logging.error(f"Error durante la deduplicación/escritura del bloque: {e}")
                    raise
            # limpiar bloque actual para que no se acumule y dañe la informacion
            resultados_bloque.clear()  
            time.sleep(2)
        # Nota: el checkpoint ahora se guarda solo después de escribir bloques en la hoja 2.


def leer_y_subir_cedulas(sheet):
    """
    Lee las cédulas del archivo HTML (disfrazado de .xls) y las sube a Google Sheets.
    Usa BeautifulSoup para parsear HTML de forma confiable.
    """
    from bs4 import BeautifulSoup
    import re

    downloads_path = os.path.expanduser("~/Downloads")
    archivo_xls = os.path.join(downloads_path, "listadoMensajerosActivos.xls")

    if not os.path.exists(archivo_xls):
        logging.error("❌ El archivo listadoMensajerosActivos.xls no se encuentra en Downloads.")
        raise FileNotFoundError(f"El archivo {archivo_xls} no se encuentra en el directorio de descargas.")

    logging.info(f"✅ Archivo encontrado: {archivo_xls}")

    # Leer el archivo
    try:
        with open(archivo_xls, 'r', encoding='utf-8', errors='replace') as f:
            contenido = f.read()
        logging.info("✅ Archivo leído correctamente")
    except Exception as e:
        logging.error(f"❌ Error al leer el archivo {archivo_xls}: {e}")
        raise

    cedulas_extraidas = []
    try:
        logging.info("🔄 Parseando HTML con BeautifulSoup (búsqueda de la tabla correcta)...")
        soup = BeautifulSoup(contenido, 'html.parser')
        tablas = soup.find_all('table')
        logging.info(f"🔎 Tablas encontradas en el HTML: {len(tablas)}")

        if not tablas:
            logging.error("❌ No se encontraron tablas en el HTML")
            raise ValueError("No se encontró tabla en el archivo HTML")

        # Intentar seleccionar la tabla que contiene la cabecera 'CEDULA' (caso-insens)
        tabla_seleccionada = None
        for i, t in enumerate(tablas):
            primeras = t.find_all('tr')[:1]
            header_text = ' '.join([c.get_text(strip=True) for tr in primeras for c in tr.find_all(['th','td'])])
            if 'cedula' in header_text.lower():
                tabla_seleccionada = t
                logging.info(f"✅ Se seleccionó la tabla {i+1} porque contiene 'CEDULA' en el encabezado.")
                break

        # Si no encontramos por texto, escoger la tabla con más filas
        if tabla_seleccionada is None:
            tablas_y_filas = [(i, len(t.find_all('tr'))) for i,t in enumerate(tablas)]
            idx_max, max_filas = max(tablas_y_filas, key=lambda x: x[1])
            tabla_seleccionada = tablas[idx_max]
            logging.info(f"ℹ️ No se encontró 'CEDULA' en encabezados; se seleccionó la tabla {idx_max+1} con {max_filas} filas.")

        filas = tabla_seleccionada.find_all('tr')
        logging.info(f"📊 Filas en la tabla seleccionada: {len(filas)}")

        # Determinar fila de encabezado: buscar fila que contenga 'CEDULA'
        header_idx = 0
        for i, fila in enumerate(filas[:3]):
            textos = [c.get_text(strip=True).lower() for c in fila.find_all(['td','th'])]
            if any('cedula' in t for t in textos):
                header_idx = i
                break

        # Procesar filas posteriores al encabezado
        for idx, fila in enumerate(filas[header_idx+1:], start=1):
            celdas = fila.find_all(['td', 'th'])
            if not celdas:
                continue

            found = None
            # Buscar en cada celda la primera secuencia de dígitos razonable
            for c in celdas:
                txt = c.get_text(strip=True)
                # Normalizar: quitar caracteres no dígito
                clean = re.sub(r'\D', '', txt)
                # Si no quedan dígitos, intentar buscar secuencias de 6-12 dígitos
                if not clean:
                    matches = re.findall(r'\d{6,12}', txt)
                    if matches:
                        clean = matches[0]

                if clean and 6 <= len(clean) <= 12 and clean not in ['12345', '99999']:
                    found = clean
                    break

            if found:
                cedulas_extraidas.append([found])
            else:
                # Para diagnóstico, loguear las celdas de filas problemáticas cada 200 filas
                if idx % 200 == 0:
                    contenidos = [c.get_text(strip=True) for c in celdas]
                    logging.debug(f"Fila {idx} sin cédula detectada. Textos: {contenidos}")

            if idx % 200 == 0:
                logging.info(f"  📍 Procesadas {idx} filas...")

        logging.info(f"✅ Total cédulas extraídas: {len(cedulas_extraidas)}")

        if not cedulas_extraidas:
            logging.error("❌ No se encontraron cédulas válidas")
            raise ValueError("No se encontraron cédulas válidas en la tabla seleccionada")

        # Subir a Google Sheets
        # Preparar lista con cédulas y fechas (Opción 1: todas con la misma fecha de carga)
        fecha_carga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lista_cedulas = [['Cédula', 'Fecha de Carga']]  # Encabezado con dos columnas
        for cedula in cedulas_extraidas:
            lista_cedulas.append([cedula[0], fecha_carga])
        
        try:
            logging.info("🔄 Limpiando hoja de Google Sheets...")
            sheet.clear()
            logging.info(f"🔄 Escribiendo {len(cedulas_extraidas)} cédulas en Google Sheets (A1)...")
            sheet.update('A1', lista_cedulas)
            logging.info(f"✅ Se subieron {len(cedulas_extraidas)} cédulas con fecha de carga a la hoja de Google Sheets.")
            logging.info(f"📅 Fecha de carga: {fecha_carga}")
        except Exception as e:
            logging.exception(f"❌ Error al actualizar Google Sheets: {str(e)}")
            raise

    except Exception as e:
        logging.error(f"❌ Error al procesar cédulas: {e}")
        traceback.print_exc()
        raise
    finally:
        # Intentar eliminar el archivo de forma segura después del procesamiento
        try:
            if os.path.exists(archivo_xls):
                os.remove(archivo_xls)
                logging.info(f"🗑️  Archivo {archivo_xls} eliminado después de procesar.")
        except Exception as e:
            logging.warning(f"⚠️  No se pudo eliminar el archivo {archivo_xls}: {e}")

def descargar_excel(driver):
    """
    Descarga las cédulas desde la página web y las guarda en un archivo Excel.
    """
    # Proceso para descargar las cédulas y luego pasarlas a Excel
    try:
        driver.get('https://domicilios.copservir.com/flota/public/default/index/ver/')
        time.sleep(2) # Una pequeña espera puede ser útil antes de buscar elementos

        # Login elements
        try:
            user_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="alias"]'))
            )
            pass_input = driver.find_element(By.XPATH, '//*[@id="clave"]')
            user_input.send_keys('7690433')
            pass_input.send_keys('7690433')
        except TimeoutException:
            logging.error("Timeout: No se encontraron los campos de usuario/contraseña en la página de login.")
            screenshot(driver, "login_fields_timeout", "Error: Campos de login no encontrados")
            raise # Re-lanza para que el except general del main lo capture
        except NoSuchElementException:
            logging.error("NoSuchElement: No se encontraron los campos de usuario/contraseña en la página de login.")
            screenshot(driver, "login_fields_no_element", "Error: Campos de login no encontrados")
            raise
        
        try:
            boton_Ingresar = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="bEnviar"]'))
            )
            boton_Ingresar.click()
        except TimeoutException:
            logging.error("Timeout: El botón 'Ingresar' no se pudo hacer clic o no apareció.")
            screenshot(driver, "login_button_timeout", "Error: Botón de login no clicable")
            raise
        except NoSuchElementException:
            logging.error("NoSuchElement: El botón 'Ingresar' no se encontró.")
            screenshot(driver, "login_button_no_element", "Error: Botón de login no encontrado")
            raise

        # Manejo de pestañas
        original_tab = driver.current_window_handle
        time.sleep(4) # Espera un poco para que la nueva pestaña se abra
        try:
            driver.execute_script("window.open('https://domicilios.copservir.com/flota/public/admin/login/autenticar/')")
            
            # Esperar a que la nueva ventana/pestaña esté disponible
            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
            all_tabs = driver.window_handles
            
            new_tab = None
            for handle in all_tabs:
                if handle != original_tab:
                    new_tab = handle
                    break
            
            if new_tab:
                driver.switch_to.window(new_tab)
                # Cerrar la pestaña anterior (opcional, pero buena práctica si no se necesita)
                driver.switch_to.window(original_tab)
                driver.close()
                driver.switch_to.window(new_tab)
            else:
                logging.error("No se pudo abrir o encontrar la nueva pestaña después de la ejecución del script.")
                screenshot(driver, "new_tab_not_found", "Error: Nueva pestaña no encontrada")
                raise Exception("No se pudo abrir o encontrar la nueva pestaña.")
                
            time.sleep(5) # Espera para que la nueva pestaña cargue
        except WebDriverException as e:
            logging.error(f"WebDriverException al manejar pestañas: {e}")
            screenshot(driver, "webdriver_exception_tabs", "Error de WebDriver al manejar pestañas")
            raise
        except Exception as e:
            logging.error(f"Error inesperado al manejar pestañas: {e}")
            screenshot(driver, "unexpected_tabs_error", "Error inesperado al manejar pestañas")
            raise

        # Navegación y descarga
        try:
            menu_maestras = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Maestras"))
            )
            menu_maestras.click()
            time.sleep(2) # Espera breve para que se despliegue el submenú
        except TimeoutException:
            logging.error("Timeout: No se encontró el enlace 'Maestras' después de esperar.")
            screenshot(driver, "maestras_link_timeout", "Error: Enlace 'Maestras' no encontrado")
            raise
        except NoSuchElementException:
            logging.error("NoSuchElement: No existe el elemento con texto 'Maestras'.")
            screenshot(driver, "maestras_link_no_element", "Error: Enlace 'Maestras' no encontrado")
            raise

        try:
            admin_mensajeros = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Admin Mensajeros"))
            )
            admin_mensajeros.click()
        except TimeoutException:
            logging.error("Timeout: No se encontró el enlace 'Admin Mensajeros' después de esperar.")
            screenshot(driver, "admin_mensajeros_link_timeout", "Error: Enlace 'Admin Mensajeros' no encontrado")
            raise
        except NoSuchElementException:
            logging.error("NoSuchElement: No existe el elemento con texto 'Admin Mensajeros'.")
            screenshot(driver, "admin_mensajeros_link_no_element", "Error: Enlace 'Admin Mensajeros' no encontrado")
            raise

        try:
            exportar_excel = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'excellistadomensajeros')]"))
            )
            # A veces un solo clic no es suficiente, o la página requiere un doble clic
            exportar_excel.click()
            time.sleep(5) # Pequeña pausa antes del segundo clic si es necesario
            
            logging.info("Se hizo clic en 'Exportar a Excel (Admin Mensajeros)'")
        except TimeoutException:
            logging.error("Timeout: No se encontró el botón para exportar a Excel.")
            screenshot(driver, "export_excel_button_timeout", "Error: Botón de exportar Excel no encontrado")
            raise
        except NoSuchElementException:
            logging.error("NoSuchElement: No existe el botón para exportar a Excel.")
            screenshot(driver, "export_excel_button_no_element", "Error: Botón de exportar Excel no encontrado")
            raise

    except Exception as e:
        error_msg = f"❌ Error inesperado en descargar_exel: {e}"
        logging.error(error_msg)
        print(error_msg)
        traceback.print_exc()
        screenshot(driver, "error_inesperado_descargar_excel", "Error inesperado en descarga de Excel")
        raise # Re-lanza la excepción para el manejo en el main

def enviar_archivo_por_correo(destinatario: str, archivo_path: str, asunto: str = "Archivo descargado", cuerpo: str = "Adjunto encontrarás el archivo descargado.", remitente: str = "tucorreo@gmail.com", contrasena: str = "tu_contraseña"):
    """
    Envía un archivo por correo electrónico como adjunto.

    destinatario (str): Dirección de correo del receptor.
    archivo_path (str): Ruta local del archivo a enviar.
    asunto (str): Asunto del correo.
    cuerpo (str): Cuerpo del mensaje.
    remitente (str): Dirección del remitente (debe coincidir con la cuenta del servidor SMTP).
    contrasena (str): Contraseña o App Password del remitente.
    """
    try:
        msg = EmailMessage()
        msg['Subject'] = asunto
        msg['From'] = remitente
        msg['To'] = destinatario
        msg.set_content(cuerpo)

        # Adjuntar archivo
        with open(archivo_path, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(archivo_path)
            msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)

        # Conectar y enviar usando SMTP (puede cambiar según el proveedor de correo)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(remitente, contrasena)
            smtp.send_message(msg)

        print(f"📩 Correo enviado correctamente a {destinatario} con el archivo {file_name}.")

    except Exception as e:
        print(f"❌ Error al enviar el correo: {e}")

def descargar_y_renombrar_sheet(client, credentials_obj, spreadsheet_id: str, sheet_name: str, download_folder: str = "downloads"):
    '''
    Descargamos una hoja específica de Google Spreadsheet como Excel (.xlsx) y la renombra con la fecha actual.
        client: La instancia de gspread.Client autenticada.
        credentials_obj: El objeto de credenciales de Google que se usó para autenticar gspread.
        spreadsheet_id (str): El ID del Google Spreadsheet.
        sheet_name (str): El nombre de la hoja dentro del Spreadsheet a descargar.
        download_folder (str): La carpeta local donde se guardará el archivo descargado. Por defecto es 'downloads'.
    '''
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Verificar si la hoja existe
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"⚠️ La hoja '{sheet_name}' no se encontró en el Spreadsheet. No se puede descargar.")
            raise SpreadsheetNotFound(f"La hoja '{sheet_name}' no se encontró en el Spreadsheet con ID '{spreadsheet_id}'.")

        # Crear la carpeta de descarga si no existe
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        # Obtener la fecha actual para el nombre del archivo
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        hora_actual = datetime.now().strftime("%H-%M-%S")
        new_file_name = f"{fecha_actual}_{hora_actual}_mensajeros.xlsx"
        download_path = os.path.join(download_folder, new_file_name)

        print(f"🚀 Descargando la hoja '{sheet_name}'...")
        
        # Obtenemos la URL de exportación para XLSX
        export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx&gid={worksheet.id}"
        
        # Acceder al token desde el objeto 'credentials_obj'
        headers = {'Authorization': 'Bearer ' + credentials_obj.token}
        response = requests.get(export_url, headers=headers, stream=True)
        # Comprueba si la solicitud HTTP fue exitosa (código de estado 200). De lo contrario, genera una excepción.
        response.raise_for_status() # Lanza un error para códigos de estado HTTP malos

        # Escritura de archivos: abre el archivo local en modo de escritura binaria ( 'wb') y escribe el contenido recibido de la respuesta en fragmentos.
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Archivo descargado y renombrado como: {new_file_name} en '{download_folder}'")
        
        return download_path
    except SpreadsheetNotFound:
        print(f"❌ Error: Spreadsheet con ID '{spreadsheet_id}' no encontrado.")
    except gspread.exceptions.APIError as e:
        print(f"❌ Error de la API de Google Sheets/Drive al descargar: {e}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red al descargar el archivo: {e}")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante la descarga: {e}")

def limpiar_hoja(sheet3):
    """
    Elimina todas las filas de la hoja excepto la primera (cabecera).
    """
    try:
        data = sheet3.get_all_values()
        if len(data) > 1:
            sheet3.batch_clear(["A2:Z10000"])
            logging.info("La hoja fue limpiada correctamente.")
        else:
            logging.info("La hoja ya estaba vacía (solo encabezados).")
    except Exception as e:
        logging.error(f"Error al limpiar la hoja: {e}")


def limpiar_hojas_inicio():
    """
    Limpia las hojas iniciales usadas por la automatización (Hoja 1: Cédula de Domiciliarios,
    Hoja 2: Reporte Comparendos). Mantiene la primera fila (encabezados) y borra datos
    desde A2 hacia abajo. Retorna True si todo fue exitoso, False en caso contrario.
    """
    try:
        client, credentials, sheet, sheet2, sheet3, SPREADSHEET_ID, SHEET_NAME2 = inicializar_sheets()
        # Limpiar hoja 1 (Cédula de Domiciliarios)
        try:
            data1 = sheet.get_all_values()
            if len(data1) > 1:
                sheet.batch_clear(["A2:Z10000"])
                logging.info("Hoja 'Cédula de Domiciliarios' limpiada (A2:Z10000).")
            else:
                logging.info("Hoja 'Cédula de Domiciliarios' ya estaba vacía.")
        except Exception as e:
            logging.error(f"Error limpiando Hoja 1: {e}")
            return False

        # Limpiar hoja 2 (Reporte Comparendos)
        try:
            data2 = sheet2.get_all_values()
            if len(data2) > 1:
                sheet2.batch_clear(["A2:Z10000"])
                logging.info("Hoja 'Reporte Comparendos' limpiada (A2:Z10000).")
            else:
                logging.info("Hoja 'Reporte Comparendos' ya estaba vacía.")
        except Exception as e:
            logging.error(f"Error limpiando Hoja 2: {e}")
            return False

        return True
    except Exception as e:
        logging.error(f"Error inicializando Google Sheets para limpiar hojas: {e}")
        return False


def borrar_resultados_de_cedula(sheet2, cedula: str):
    """
    Borra todas las filas (desde A2 hacia abajo) en `sheet2` que tengan la cédula indicada en la columna A.
    Mantiene la fila de encabezados en A1.
    Retorna el número de filas eliminadas.
    """
    try:
        all_vals = sheet2.get_all_values()
        if len(all_vals) <= 1:
            return 0
        # Construir nueva matriz manteniendo encabezado y omitiendo filas con la cédula
        header = all_vals[0]
        nuevos = [header]
        removed = 0
        for row in all_vals[1:]:
            if len(row) > 0 and str(row[0]).strip() == str(cedula).strip():
                removed += 1
                continue
            nuevos.append(row)

        if removed == 0:
            logging.info(f"No se encontraron filas para cédula {cedula} en sheet2.")
            return 0

        # Reescribir la hoja completa (encabezado + filas filtradas)
        # Atención: para hojas grandes esto puede ser costoso; asumimos tamaño moderado.
        sheet2.clear()
        # Ajustar ancho de columnas no necesario; solo actualizar valores
        sheet2.update(nuevos)
        logging.info(f"Se eliminaron {removed} filas de sheet2 para la cédula {cedula} y se reescribió la hoja.")
        return removed
    except Exception as e:
        logging.error(f"Error al borrar resultados de cédula {cedula} en sheet2: {e}")
        raise

def activacion(sheet3) -> bool:
    """
    Verifica si debe ejecutarse la automatización leyendo la celda B2 del Google Sheet.
    Si el valor es '1', 'sí' o 'si', cambia B2 a 'En ejecución' y retorna True.
    Si hay un error, deja B2 en 'Sí' y retorna False.
    """
    try:
        valor = sheet3.acell('B2').value.strip().lower()
        if valor in ('si', 'sí', 'en ejecución', '1'):
            sheet3.update_acell('B2', 'En ejecución')  # ✅ CORRECTO
            logging.info("La automatización está activada. Continuando con el proceso.")
            return True
        return False
    except Exception as e:
        logging.error(f"Error al verificar estado de activación en Google Sheets: {e}")
        return False

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    """
    Punto de entrada principal del script.
    Configura el logging, inicializa Google Sheets, y ejecuta un bucle infinito para la automatización.
    """
    # Forzar encoding utf-8 en stdout/stderr para evitar errores al imprimir emojis en consolas Windows
    try:
        # Python 3.7+ tiene reconfigure() en TextIOWrapper
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        else:
            # Fallback: no garantizado en todas las plataformas, intentar envolver
            import codecs
            try:
                sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
                sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
            except Exception:
                # Si falla, no detener la ejecución; el logging FileHandler ya usa utf-8
                pass
    except Exception:
        pass

    # Configuración de logging
    logging.basicConfig(
        level=logging.INFO, # Cambia a DEBUG para más detalles
        format='%(asctime)s - %(levelname)s - %(message)s', # Formato del log
        handlers=[
            logging.StreamHandler(), # Muestra los logs en la consola
            logging.FileHandler("automatizacion.log", encoding='utf-8')  # se agrega encoding
        ]
    )
    client, credentials, sheet, sheet2, sheet3, SPREADSHEET_ID, SHEET_NAME2 = inicializar_sheets()
    # Bucle infinito para la ejecución programada
    while True:
        DRIVER = None # Inicializa DRIVER a None para el bloque finally
        try:
            logging.info("--- Iniciando ciclo de automatización ---")

            # Conexión con Google Sheets
            client, credentials, sheet, sheet2, sheet3, SPREADSHEET_ID, SHEET_NAME2 = inicializar_sheets()
            logging.info("Conexión con Google Sheets inicializada.")

            # Verificar si el proceso está activado en A1
            if not activacion(sheet3):
                logging.warning("⚠ La automatización está desactivada en el Google Sheet. Saltando este ciclo.")
                logging.info(f"Esperando 1 hora antes del siguiente intento ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
                time.sleep(3600) # Espera 1 hora antes del siguiente ciclo
                continue

            # Iniciar driver
            DRIVER = iniciar_driver()
            if DRIVER:
                DRIVER.maximize_window()
                logging.info("WebDriver iniciado y maximizado.")
            else:
                logging.error("No se pudo iniciar el WebDriver. Terminando el ciclo.")
                sys.exit(1) # Termina el ciclo si no se puede iniciar el WebDriver

            DRIVER.set_script_timeout(180) # Establecer un tiempo de espera de script de 180 segundos
            inicio = datetime.now()

            # Reactivar flujo completo: descargar XLS, subir cédulas, procesar en SIMIT
            logging.info("Iniciando descarga de Excel de mensajeros...")
            try:
                descargar_excel(DRIVER)
                logging.info("Descarga de Excel finalizada.")
            except Exception as e:
                logging.warning(f"No se pudo completar la descarga de Excel: {e}")

            logging.info("Iniciando lectura y subida de cédulas a Google Sheets...")
            try:
                leer_y_subir_cedulas(sheet)
                logging.info("Lectura y subida de cédulas finalizada.")
            except Exception as e:
                logging.warning(f"No se pudo leer/subir cédulas: {e}")

            logging.info("Iniciando procesamiento de cédulas en SIMIT...")
            # Normalizar checkpoint meta antiguo (eliminar 'timestamp') y luego reanudar
            try:
                normalize_checkpoint_meta_file()
                inicio_reanudar = leer_checkpoint()
                meta = leer_checkpoint_meta()
                if isinstance(meta, dict):
                    try:
                        cedula_reanudar = None
                        # Priorizar 'last_cedula' si está presente (más robusto a cambios en hoja1)
                        if 'last_cedula' in meta and meta.get('last_cedula'):
                            buscada = str(meta.get('last_cedula')).strip()
                            cedulas_hoja = sheet.col_values(1)
                            # Buscar la cedula en la hoja (la lista incluye header en la posición 0)
                            for pos in range(1, len(cedulas_hoja)):
                                if str(cedulas_hoja[pos]).strip() == buscada:
                                    cedula_reanudar = cedulas_hoja[pos]
                                    idx = pos
                                    break
                            if not cedula_reanudar:
                                logging.warning(f"La cédula {buscada} del checkpoint no se encontró actualmente en Hoja 1. Intentando por índice...")

                        # Si no se pudo determinar por cédula, caer al índice histórico
                        if not cedula_reanudar and 'last_cedula_index' in meta:
                            idx = int(meta.get('last_cedula_index', inicio_reanudar))
                            cedulas_hoja = sheet.col_values(1)
                            if len(cedulas_hoja) >= idx + 1:
                                cedula_reanudar = cedulas_hoja[idx]
                            else:
                                logging.warning(f"No se encontró la cédula en hoja 1 para el índice {idx}. Se reanudará desde {inicio_reanudar}.")

                        if cedula_reanudar:
                            # Borrar posibles filas parciales de esa cédula en sheet2
                            try:
                                removed = borrar_resultados_de_cedula(sheet2, cedula_reanudar)
                                logging.info(f"Se borraron {removed} filas parciales de sheet2 para la cédula {cedula_reanudar} antes de reanudar.")
                                # Reanudar desde la misma cédula para procesarla de nuevo
                                inicio_reanudar = idx
                            except Exception as e:
                                logging.warning(f"No se pudo borrar filas parciales para {cedula_reanudar}: {e}. Se reanudará desde {inicio_reanudar} sin borrar.")
                    except Exception as e:
                        logging.warning(f"Error al interpretar checkpoint meta para reanudar: {e}")

                if not isinstance(inicio_reanudar, int) or inicio_reanudar < 1:
                    inicio_reanudar = 1
            except Exception:
                inicio_reanudar = 1

            logging.info(f"Procesamiento: reanudando desde índice {inicio_reanudar}")
            procesar_cedulas(DRIVER, sheet, sheet2, inicio_desde=inicio_reanudar)
            logging.info("Procesamiento de cédulas en SIMIT finalizado.")

            # Si llegamos aquí sin excepciones, borrar checkpoint
            try:
                borrar_checkpoint()
                logging.info("Checkpoint eliminado tras finalización exitosa.")
            except Exception as e:
                logging.warning(f"No se pudo eliminar el checkpoint tras finalizar: {e}")

            logging.info("Iniciando descarga y renombrado de hoja de resultados...")
            archivo_generado = descargar_y_renombrar_sheet(client, credentials, SPREADSHEET_ID, SHEET_NAME2, download_folder="downloads")

            logging.info("Descarga y renombrado de hoja finalizado.")

            # 👉 Limpiar hoja de entrada después de todo el proceso exitoso
            limpiar_hoja(sheet3)
            logging.info("✅ Hoja de entrada limpiada exitosamente tras ejecución sin errores.")

            final = datetime.now()
            tiempo_total = final - inicio
            logging.info(f"Ciclo de automatización completado en: {tiempo_total}")
            print(f"Tiempo total de ejecución: {tiempo_total}")

            if archivo_generado:
                enviar_archivo_por_correo(
                    destinatario="bibiana_blanco@copservir.com",
                    archivo_path=archivo_generado,
                    asunto= f"Se adjunta Archivo de Reporte de Mensajeros fecha {final}",
                    cuerpo="Hola, adjunto el archivo descargado desde Google Sheets. Esta es la prueba final de la automatización, me indicas si funciona correctamente. muchas gracias.",
                    remitente="santo.silvestre.v.p@gmail.com",
                    contrasena="zpoz yqbw ojkz mqlq"  # Usa una App Password si usas Gmail
                )

        except Exception as e: 
            error_msg = f"❌ Error crítico en el ciclo principal de automatización: {e}"
            logging.critical(error_msg)
            print(error_msg)
            traceback.print_exc()

            # Intentar tomar captura si hay DRIVER
            if DRIVER:
                try:
                    screenshot(DRIVER, "error_critico_main", "Error crítico en el ciclo principal")
                except Exception as se:
                    logging.error(f"Error al intentar tomar screenshot en el main: {se}")
            
            # Intentar restaurar el estado en Google Sheets
            try:
                sheet3.update_acell('B2', 'SI')
                logging.warning("⚠ Como se produjo un error, se restauró el valor 'Sí' en B2 para reactivar la automatización.")
            except Exception as e2:
                logging.error(f"⚠ No se pudo restaurar el valor 'Sí' en B2 tras el error crítico: {e2}")

        finally:
            if DRIVER:
                logging.info("Cerrando WebDriver...")
                DRIVER.quit()
                logging.info("WebDriver cerrado.")
            else:
                logging.warning("WebDriver no estaba activo o no se pudo cerrar.")

        logging.info(f"Esperando 1 hora antes del siguiente ciclo ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
        time.sleep(3600)