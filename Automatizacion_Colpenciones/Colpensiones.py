import json
import os
import time
import logging
import re
import traceback
from datetime import datetime
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import sys
import gspread
from gspread.exceptions import APIError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException
)
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2.service_account import Credentials

# --- Configuración de logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("automatizacion.log", encoding='utf-8')
    ]
)

# --- Constantes ---
SPREADSHEET_ID = "1qsdXTesrr_v2nyooemhgKMgskA52HQTVRzZ4dQ0Howg"
CREDENTIALS_JSON = "C:\\Users\\dforero\\Pictures\\Proyecto_Automatizaciones_Completo\\Automatizacion_Colpenciones\\continual-lodge-475121-h9-8c726bfd149c.json"
SENDER_EMAIL = "david.forero.cop@gmail.com"
SENDER_PASSWORD = "ndbr hmdn dzmq llot"
RECEIVER_EMAIL = "david.forero.cop@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
BASE_DIR = os.path.dirname(__file__)
ULTIMO_PROGRESO_FILE = os.path.join(BASE_DIR, "ultimo_progreso.json")

def iniciar_driver() -> Optional[webdriver.Chrome]:
    """Inicia el driver de Selenium con opciones para evitar detección y errores."""
    try:
        options = webdriver.ChromeOptions()
        options.binary_location = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
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
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--blink-settings=imagesEnabled=false")
        # options.add_argument("--headless=new")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except WebDriverException as e:
        logging.error("Error al iniciar el driver: %s", e)
        return None

def send_error_email(subject: str, body: str, attachment_path: Optional[str] = None, error_details: Optional[str] = None):
    """Envía un correo electrónico con detalles adicionales del error."""
    time.sleep(1)
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"Error en Automatización - {subject}"
    full_body = f"{body}\n\nDetalles del error:\n{error_details if error_details else 'No disponibles'}"
    msg.attach(MIMEText(full_body, 'plain'))
    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
            msg.attach(part)
        except Exception as e:
            logging.error(f"No se pudo adjuntar el archivo {attachment_path}: {e}")
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        logging.info(f"Correo de error enviado: {subject}")
    except TimeoutException as e:
        error_message = f"ERROR: No se pudo enviar el correo de error debido a un timeout: {e}"
        logging.error(error_message)
        send_error_email("Error al enviar correo de error", error_message)
        raise
    except Exception as e:
        logging.error(f"Fallo al enviar el correo de error: {e}")

def screenshot(driver: Optional[webdriver.Chrome], screenshot_name: str, error_subject: str = "Error General Automatización"):
    """Toma una captura de pantalla y la guarda en la carpeta 'screenshots'."""
    if not driver:
        logging.error("No se puede tomar captura de pantalla: driver es None")
        send_error_email(error_subject, "No se puede tomar captura: driver es None")
        return
    screenshots_dir = "screenshots"
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        logging.info(f"Creado directorio para capturas: {screenshots_dir}")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(screenshots_dir, f"{screenshot_name}_{timestamp}.png")
    screenshot_saved = False
    try:
        driver.save_screenshot(filename)
        logging.error(f"Captura de pantalla guardada: {filename}")
        time.sleep(1)
        screenshot_saved = True
    except Exception as e:
        logging.error(f"No se pudo tomar la captura de pantalla: {e}")
    screenshot_info = f"Captura: {os.path.basename(filename)}" if screenshot_saved else "Captura: No disponible"
    sms_body_message = (
        f"ERROR: {error_subject}\n"
        f"{screenshot_info} (en '{screenshots_dir}')\n"
        f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"URL: {driver.current_url if driver else 'N/A'}"
    )
    if len(sms_body_message) > 500:
        sms_body_message = sms_body_message[:497] + "..."
    send_error_email(error_subject, sms_body_message, filename if screenshot_saved else None)
    logging.debug(f"Email enviado con contenido: {sms_body_message}")

def extraer_tabla(driver: webdriver.Chrome):
    """Extrae datos de la tabla principal de la página."""
    datos = []
    filas = driver.find_elements(By.XPATH, '//table/tbody/tr')
    for fila in filas:
        celdas = fila.find_elements(By.TAG_NAME, 'td')
        if len(celdas) >= 5:
            ciclo = celdas[1].text.strip()
            no_sticker = celdas[2].text.strip()
            valor_deuda = celdas[3].text.strip()
            cotizantes = celdas[4].text.strip()
            datos.append([ciclo, no_sticker, valor_deuda, cotizantes])
    return datos

def guardar_tabla_local(tabla, archivo=None):
    """Guarda la tabla en un archivo JSON local."""
    if archivo is None:
        archivo = os.path.join(BASE_DIR, "tabla_guardada.json")
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(tabla, f, ensure_ascii=False, indent=2)

def cargar_tabla_local(archivo=None):
    """Carga la tabla desde un archivo JSON local."""
    if archivo is None:
        archivo = os.path.join(BASE_DIR, "tabla_guardada.json")
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def mostrar_por_bloques(tabla, tamano_bloque=20):
    """Muestra los datos de la tabla en bloques de tamaño especificado."""
    for i in range(0, len(tabla), tamano_bloque):
        bloque = tabla[i:i+tamano_bloque]
        logging.info(f"Bloque {i//tamano_bloque + 1}")
        for fila in bloque:
            logging.info(f"{fila}")
    logging.info("Fin de los bloques")
    logging.info(f"Numero de filas encontradas para procesamiento: {len(tabla)}")

def guardar_ultimo_progreso(no_sticker, documento=None, archivo=None):
    """Guarda el progreso del último sticker y documento procesado en un archivo JSON."""
    if archivo is None:
        archivo = ULTIMO_PROGRESO_FILE
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump({"ultimo_sticker": no_sticker, "ultimo_documento": documento}, f, ensure_ascii=False, indent=2)

def cargar_ultimo_progreso(archivo=None):
    """Carga el progreso del último sticker y documento procesado desde un archivo JSON."""
    if archivo is None:
        archivo = ULTIMO_PROGRESO_FILE
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("ultimo_sticker"), data.get("ultimo_documento")
    return None, None

def guardar_en_google_sheets(tabla, spreadsheet_id, hoja="Hoja 1", clear_sheet=False, max_retries=5, backoff_factor=2):
    """Guarda los datos en Google Sheets con reintentos en caso de errores 503."""
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_JSON, scopes=scopes)
    cliente = gspread.authorize(creds)
    for attempt in range(max_retries):
        try:
            sh = cliente.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(hoja)
            if clear_sheet:
                worksheet.clear()
                encabezados = [
                    "🕒 Fecha Ingreso",
                    "🔄 Ciclo",
                    "🏷️ No. Sticker",
                    "💰 Valor Deuda",
                    "👥 Cotizantes",
                    "📅 Fecha de Pago",
                    "💸 Valor Cotización",
                    "🤝 Fondo Solidaridad",
                    "💵 Valor Total",
                    "🛠️ Corrección Sticker",
                    "📝 Descripción Deuda",
                    "🙍 Nombre",
                    "🆔 Documento",
                    "💲 Valor",
                    "⚡ Novedad"
                ]
                worksheet.append_row(encabezados)
                worksheet.format("A1:O1", {
                    "backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.93},
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"bold": True, "fontSize": 12}
                })
            worksheet.append_rows(tabla)
            logging.info(f"✅ Datos guardados en Google Sheets ({spreadsheet_id})")
            return
        except APIError as e:
            if "503" in str(e):
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor ** attempt
                    logging.warning(f"APIError 503 en intento {attempt + 1}/{max_retries}. Reintentando en {sleep_time} segundos...")
                    time.sleep(sleep_time)
                    continue
                else:
                    logging.error(f"Agotados los reintentos para APIError 503: {e}")
                    raise
            else:
                logging.error(f"APIError no manejado: {e}")
                raise
        except Exception as e:
            logging.error(f"Error inesperado al guardar en Google Sheets: {e}")
            raise

def safe_get_text(wait, xpath):
    try:
        el = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        return el.text.strip()
    except Exception:
        return "N/A"

def extraer_detalle_stickers(driver: webdriver.Chrome, tabla_principal, spreadsheet_id, max_retries=10):
    """Extrae detalles de cada sticker, incluyendo datos del modal y afiliados."""
    datos_finales = []
    contador = 0
    ultimo_sticker, ultimo_documento = cargar_ultimo_progreso()
    start_processing = ultimo_sticker is None
    for fila in tabla_principal:
        ciclo, no_sticker, valor_deuda, cotizantes = fila
        if not start_processing:
            if no_sticker == ultimo_sticker:
                start_processing = True
                if ultimo_documento is None:
                    continue
            else:
                continue
        retries = 0
        while retries < max_retries:
            ultimo_sticker, ultimo_documento = cargar_ultimo_progreso()
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.XPATH, '//table/tbody/tr'))
                )
                elemento_icon = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        f"//tr[td[@id='t2' and text()='{no_sticker}']]//td[@id='t5']//span[@title='Ver detalle...']"
                    ))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento_icon)
                time.sleep(0.5)
                elemento_icon.click()
                try:
                    WebDriverWait(driver, 70).until(
                        EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'modal-content modalCont')]"))
                    )
                    time.sleep(2)
                except TimeoutException:
                    logging.error(f"Timeout esperando el detalle del icono para sticker {no_sticker}")
                    raise
                time.sleep(0.8)
                try:
                    wait = WebDriverWait(driver, 10)
                    fecha_pago = safe_get_text(wait, "//div[@class='txtCombo' and text()='Fecha de pago']/following-sibling::div[@class='valCombo']")
                    valor_cotizacion = safe_get_text(wait, "//div[@class='txtCombo' and text()='Valor cotizacion']/following-sibling::div[@class='valCombo']")
                    fondo_solidaridad = safe_get_text(wait, "//div[@class='txtCombo' and text()='Fondo solidaridad']/following-sibling::div[@class='valCombo']")
                    valor_total = safe_get_text(wait, "//div[@class='txtCombo' and text()='Valor total']/following-sibling::div[@class='valCombo']")
                    correccion_sticker = safe_get_text(wait, "//div[@class='txtCombo' and text()='Corrección sticker']/following-sibling::div[@class='valCombo']")
                    descripcion_deuda = safe_get_text(wait, "//div[@class='txtCombo' and text()='Descripcion deuda']/following-sibling::div[@class='valCombo']")
                except NoSuchElementException as e:
                    logging.error(f"No se encontraron los campos del modal para sticker {no_sticker}: {e}")
                    fecha_pago = valor_cotizacion = fondo_solidaridad = valor_total = correccion_sticker = descripcion_deuda = "N/A"
                try:
                    close_btn = driver.find_element(By.XPATH, "//button[contains(@class,'closeM') and contains(@class,'glyphicon-remove')]")
                    driver.execute_script("arguments[0].click();", close_btn)
                    WebDriverWait(driver, 70).until(
                        EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class,'modal-content modalCont')]"))
                    )
                    time.sleep(0.8)
                except (TimeoutException, NoSuchElementException) as e:
                    logging.error(f"Error cerrando el detalle del icono para sticker {no_sticker}: {e}")
                    raise
                elemento = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.XPATH, f"//td[contains(text(), '{no_sticker}')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
                time.sleep(0.7)
                elemento.click()
                try:
                    WebDriverWait(driver, 70).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, '.edesk-prisma-loading-box'))
                    )
                except TimeoutException:
                    logging.error(f"Timeout esperando loader para sticker {no_sticker}")
                    raise
                time.sleep(6)
                try:
                    expected_rows = int(cotizantes)
                    min_rows = max(10, expected_rows // 10)
                    def rows_loaded(driver):
                        filas = driver.find_elements(By.CSS_SELECTOR, ".boxItemAcordeon.boxAC_ec_det_acco_item")
                        return len(filas) >= min_rows
                    WebDriverWait(driver, 4).until(rows_loaded)
                    filas_detalle = driver.find_elements(By.CSS_SELECTOR, ".boxItemAcordeon.boxAC_ec_det_acco_item")
                    if len(filas_detalle) != expected_rows:
                        logging.warning(f"Discrepancia detectada: {len(filas_detalle)} filas cargadas, {expected_rows} cotizantes esperados para sticker {no_sticker}")
                    else:
                        logging.info(f"Se detectaron {len(filas_detalle)} filas para sticker {no_sticker}, cotizantes esperados: {cotizantes}")
                except TimeoutException:
                    filas_detalle = driver.find_elements(By.CSS_SELECTOR, ".boxItemAcordeon.boxAC_ec_det_acco_item")
                    logging.warning(f"Timeout esperando al menos {min_rows} filas para sticker {no_sticker}. Se detectaron {len(filas_detalle)} filas, continuando...")
                    # Si no se cargaron filas, registrar y saltar al siguiente sticker
                    if len(filas_detalle) == 0:
                        logging.warning(f"No se cargaron filas para sticker {no_sticker}. Saltando al siguiente sticker sin interrumpir el proceso.")
                        # Guardar progreso y romper el bucle de reintentos para continuar con el siguiente sticker
                        guardar_ultimo_progreso(no_sticker, None)
                        break
                is_resume_sticker = (no_sticker == ultimo_sticker) and (ultimo_documento is not None)
                start_collecting = not is_resume_sticker
                if is_resume_sticker:
                    logging.info(f"Reanudando sticker {no_sticker} despues del documento {ultimo_documento}")
                for detalle in filas_detalle:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", detalle)
                    time.sleep(0.32)
                    columnas = detalle.find_elements(By.CSS_SELECTOR, ".row > div")
                    if len(columnas) >= 4:
                        fecha_hora_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        nombre = columnas[0].text.strip()
                        documento = columnas[1].text.strip()
                        documento = re.sub(r'\D', '', documento) if documento else "N/A"
                        valor = columnas[2].text.strip()
                        novedad = columnas[3].text.strip()
                        if is_resume_sticker and not start_collecting:
                            if documento == ultimo_documento:
                                start_collecting = True
                                continue
                            else:
                                continue
                        datos_finales.append([
                            fecha_hora_inicio, ciclo, no_sticker, valor_deuda, cotizantes,
                            fecha_pago, valor_cotizacion, fondo_solidaridad, valor_total,
                            correccion_sticker, descripcion_deuda,
                            nombre, documento, valor, novedad
                        ])
                        contador += 1
                        if len(datos_finales) >= 100:
                            guardar_ultimo_progreso(no_sticker, documento)
                            guardar_en_google_sheets(datos_finales, spreadsheet_id, clear_sheet=False)
                            datos_finales.clear()
                guardar_ultimo_progreso(no_sticker, None)
                break
            except (TimeoutException, WebDriverException, NoSuchElementException) as e:
                retries += 1
                logging.error(f"Error procesando sticker {no_sticker}, intento {retries}/{max_retries}: {e}")
                screenshot(driver, f"error_sticker_{no_sticker}", f"Error procesando sticker {no_sticker}")
                # Si no quedan reintentos, registrar y saltar al siguiente sticker
                if retries >= max_retries:
                    logging.error(f"Se agotaron los reintentos para sticker {no_sticker}. Saltando al siguiente sticker.")
                    guardar_ultimo_progreso(no_sticker, None)
                    break
                # Si aún hay reintentos, reiniciar driver y reintentar
                logging.info(f"Reintentando sticker {no_sticker} despues de error...")
                time.sleep(5)
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                driver = iniciar_driver()
                if not driver:
                    logging.error("No se pudo reiniciar el WebDriver. Terminando.")
                    sys.exit(1)
                driver.maximize_window()
                driver.set_script_timeout(180)
                driver.get('http://pwa.colpensionestransaccional.gov.co/')
                time.sleep(2)
                try:
                    user_input = WebDriverWait(driver, 50).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="frmsyclogin"]/div[1]/input[2]'))
                    )
                    pass_input = driver.find_element(By.XPATH, '//*[@id="frmsyclogin"]/div[2]/input[1]')
                    user_input.send_keys('79541079')
                    pass_input.send_keys('Sabiduria*465')
                    login_button = WebDriverWait(driver, 50).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="frmsyclogin"]/input[2]'))
                    )
                    driver.execute_script("arguments[0].click();", login_button)
                except (TimeoutException, NoSuchElementException) as e:
                    logging.error(f"Error en login: {e}")
                    screenshot(driver, "login_error", "Error en login")
                    raise
                try:
                    time.sleep(1)
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="modalAlertCOLP"]'))
                    )
                    time.sleep(1)
                    certificacion_name = "Certificacion Documental vencera pronto"
                    screenshots = "screenshots"
                    if not os.path.exists(screenshots):
                        os.makedirs(screenshots)
                        logging.info(f"Creado directorio para capturas: {screenshots}")
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    filename = os.path.join(screenshots, f"{certificacion_name}_{timestamp}.png")
                    driver.save_screenshot(filename)
                    time.sleep(1)
                    modal_alerta = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continuar')]"))
                    )
                    driver.execute_script("arguments[0].click();", modal_alerta)
                except (TimeoutException, NoSuchElementException) as e:
                    logging.error("Certificacion Documental")
                try:
                    time.sleep(1)
                    WebDriverWait(driver, 50).until(
                        EC.invisibility_of_element((By.XPATH, '/html/body/div[6]/div/div[2]'))
                    )
                    time.sleep(1)
                except (TimeoutException, NoSuchElementException) as e:
                    logging.error(f"Error esperando loader: {e}")
                    screenshot(driver, "loader_error", "Error esperando loader")
                    raise
                try:
                    estado_cuenta = WebDriverWait(driver, 50).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="acti_0_3"]/div[1]/div[1]'))
                    )
                    time.sleep(1)
                    if not estado_cuenta:
                        menu = WebDriverWait(driver, 20).until(
                            EC.visibility_of_element_located((By.XPATH, '/html/body/div[3]/div[3]/div/nav/div[1]/button'))
                        )
                        driver.execute_script("arguments[0].click();", menu)
                        time.sleep(1)
                        estado_cuenta = WebDriverWait(driver, 50).until(
                            EC.visibility_of_element_located((By.XPATH, '//*[@id="acti_0_3"]/div[1]/div[1]'))
                        )
                    driver.execute_script("arguments[0].click();", estado_cuenta)
                except (TimeoutException, NoSuchElementException) as e:
                    logging.error(f"Error navegando a Estado de Cuenta: {e}")
                    screenshot(driver, "estado_cuenta_error", "Error en Estado de Cuenta")
                    raise
                try:
                    cerrar_loader = WebDriverWait(driver, 50).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="idECMsgModal"]/div/div/button'))
                    )
                    driver.execute_script("arguments[0].click();", cerrar_loader)
                    clic_entrar = WebDriverWait(driver, 50).until(
                        EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'zonaAC parent_CardItemPWA parent_rounded parent_dangerCard col-lg-0')]"))
                    )
                    driver.execute_script("arguments[0].click();", clic_entrar)
                except (TimeoutException, NoSuchElementException) as e:
                    logging.error(f"Error en modal de Estado de Cuenta: {e}")
                    screenshot(driver, "modal_error", "Error en modal de Estado de Cuenta")
                    raise
                try:
                    WebDriverWait(driver, 50).until(
                        EC.invisibility_of_element((By.XPATH, '/html/body/div[8]/div/div[2]'))
                    )
                    time.sleep(5)
                except (TimeoutException, NoSuchElementException) as e:
                    logging.error(f"Error esperando loader final: {e}")
                    screenshot(driver, "loader_final_error", "Error esperando loader final")
                    raise
                WebDriverWait(driver, 50).until(
                    EC.invisibility_of_element((By.XPATH, '/html/body/div[8]/div/div[2]'))
                )
                time.sleep(5)
                WebDriverWait(driver, 50).until(
                    EC.visibility_of_all_elements_located((By.XPATH, '//table/tbody'))
                )
            else:
                logging.error(f"Se agotaron los reintentos para sticker {no_sticker}. Saltando al siguiente sticker.")
                logging.warning(f"Se agotaron los reintentos para sticker {no_sticker}. Saltando al siguiente.")
                guardar_ultimo_progreso(no_sticker, None)
                break
    if len(datos_finales) > 0:
        guardar_en_google_sheets(datos_finales, spreadsheet_id, clear_sheet=False)
        datos_finales.clear()
    logging.info(f"Extraccion completa. Total registros: {contador}")

def calcular_suma_cotizantes(tabla):
    """Calcula la suma de los valores en la cuarta columna (cotizantes) de la tabla."""
    try:
        suma_cotizantes = sum(int(fila[3]) for fila in tabla if fila[3].strip().isdigit())
        logging.info(f"Suma total de cotizantes esperados en la tabla: {suma_cotizantes}")
        return suma_cotizantes
    except ValueError as e:
        logging.error(f"Error al calcular la suma de cotizantes: {e}")
        return 0
    except Exception as e:
        logging.error(f"Error inesperado al calcular la suma de cotizantes: {e}")
        return 0

def main():
    """Flujo principal de la automatización."""
    driver = iniciar_driver()
    if not driver:
        logging.error("No se pudo iniciar el WebDriver. Terminando.")
        sys.exit(1)
    try:
        driver.maximize_window()
        logging.info("WebDriver iniciado y maximizado.")
        driver.set_script_timeout(180)
        driver.get('http://pwa.colpensionestransaccional.gov.co/')
        time.sleep(2)
        try:
            user_input = WebDriverWait(driver, 50).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="frmsyclogin"]/div[1]/input[2]'))
            )
            pass_input = driver.find_element(By.XPATH, '//*[@id="frmsyclogin"]/div[2]/input[1]')
            user_input.send_keys('79541079')
            pass_input.send_keys('Sabiduria*465')
            login_button = WebDriverWait(driver, 50).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="frmsyclogin"]/input[2]'))
            )
            driver.execute_script("arguments[0].click();", login_button)
            time.sleep(1)
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Error en login: {e}")
            screenshot(driver, "login_error", "Error en login")
            raise
        try:
            time.sleep(1)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="modalAlertCOLP"]'))
            )
            time.sleep(1)
            certificacion_name = "La certificación Documental vencera pronto"
            screenshots = "screenshots"
            if not os.path.exists(screenshots):
                os.makedirs(screenshots)
                logging.info(f"Creado directorio para capturas: {screenshots}")
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.join(screenshots, f"{certificacion_name}_{timestamp}.png")
            driver.save_screenshot(filename)
            time.sleep(1)
            modal_alerta = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continuar')]"))
            )
            driver.execute_script("arguments[0].click();", modal_alerta)
        except (TimeoutException, NoSuchElementException) as e:
            logging.error("certificación Documental")
        try:
            time.sleep(1)
            WebDriverWait(driver, 50).until(
                EC.invisibility_of_element((By.XPATH, '/html/body/div[6]/div/div[2]'))
            )
            time.sleep(1)
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Error esperando loader: {e}")
            screenshot(driver, "loader_error", "Error esperando loader")
            raise
        try:
            estado_cuenta = WebDriverWait(driver, 50).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="acti_0_3"]/div[1]/div[1]'))
            )
            time.sleep(1)
            if not estado_cuenta:
                menu = WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.XPATH, '/html/body/div[3]/div[3]/div/nav/div[1]/button'))
                )
                driver.execute_script("arguments[0].click();", menu)
                time.sleep(1)
                estado_cuenta = WebDriverWait(driver, 50).until(
                    EC.visibility_of_element_located((By.XPATH, '//*[@id="acti_0_3"]/div[1]/div[1]'))
                )
            driver.execute_script("arguments[0].click();", estado_cuenta)
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Error navegando a Estado de Cuenta: {e}")
            screenshot(driver, "estado_cuenta_error", "Error en Estado de Cuenta")
            raise
        try:
            cerrar_loader = WebDriverWait(driver, 50).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="idECMsgModal"]/div/div/button'))
            )
            driver.execute_script("arguments[0].click();", cerrar_loader)
            clic_entrar = WebDriverWait(driver, 50).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'zonaAC parent_CardItemPWA parent_rounded parent_dangerCard col-lg-0')]"))
            )
            driver.execute_script("arguments[0].click();", clic_entrar)
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Error en modal de Estado de Cuenta: {e}")
            screenshot(driver, "modal_error", "Error en modal de Estado de Cuenta")
            raise
        try:
            WebDriverWait(driver, 50).until(
                EC.invisibility_of_element((By.XPATH, '/html/body/div[8]/div/div[2]'))
            )
            time.sleep(5)
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Error esperando loader final: {e}")
            screenshot(driver, "loader_final_error", "Error esperando loader final")
            raise
        WebDriverWait(driver, 50).until(
            EC.invisibility_of_element((By.XPATH, '/html/body/div[8]/div/div[2]'))
        )
        time.sleep(5)
        WebDriverWait(driver, 50).until(
            EC.visibility_of_all_elements_located((By.XPATH, '//table/tbody'))
        )
        tabla_actual = extraer_tabla(driver)
        tabla_anterior = cargar_tabla_local()
        mostrar_por_bloques(tabla_actual, 20)
        calcular_suma_cotizantes(tabla_actual)
        if tabla_anterior is None:
            logging.info("No hay registro previo, guardando por primera vez...")
            guardar_tabla_local(tabla_actual)
        elif tabla_actual != tabla_anterior:
            logging.info("Cambios detectados en la tabla")
            guardar_tabla_local(tabla_actual)
        else:
            logging.info("La tabla no cambio desde la ultima ejecucion")
        time.sleep(3)
        guardar_en_google_sheets([], SPREADSHEET_ID, clear_sheet=False)
        extraer_detalle_stickers(driver, tabla_actual, SPREADSHEET_ID)
    except Exception as e:
        error_msg = f"Error inesperado en el proceso: {e}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        screenshot(driver, "error_inesperado_proceso", "Error inesperado")
        raise
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()