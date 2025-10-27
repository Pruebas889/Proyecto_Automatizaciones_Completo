"""
Script para automatizar el login en la tienda virtual. Captura los tiempos de carga, 
realiza el proceso de inicio y cierre de sesión y guarda los datos en Google Sheets.
"""
import os
import signal
import sys, io
import time
import socket
import gspread
import logging
import mysql.connector
from datetime import datetime
from selenium import webdriver
from typing import Callable, Optional
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
    InvalidSessionIdException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from oauth2client.service_account import ServiceAccountCredentials
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Envio por correo para visualizacion de errores
import smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

driver = None

# Envio por correo para visualizacion de errores
def send_error_email(subject: str, body: str, attachment_path: Optional[str] = None):
    """
    Envía un correo electrónico con el asunto, cuerpo y opcionalmente un archivo adjunto.
    Configuración de correo electrónico para enviar errores.
    Asegúrate de que las credenciales y el servidor SMTP estén configurados correctamente.
    """
    SENDER_EMAIL = "david.forero.cop@gmail.com"
    SENDER_PASSWORD = 'ndbr hmdn dzmq llot'
    RECEIVER_EMAIL = "pruebaslogin360@gmail.com"
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465
    
    time.sleep(1)
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
    except Exception as e:
        logging.error(f"Fallo al enviar el correo de error: {e}")
        logging.exception("Detalle del error al enviar correo:") # Esto te dará el traceback completo
        print(f"Fallo al enviar el correo de error: {e}")

# Obtener la IP del equipo
def obtener_ip() -> str:
    """ Obtiene la dirección IP del equipo. """
    try:
        return socket.gethostbyname(socket.gethostname())
    except (TimeoutException, NoSuchElementException, WebDriverException) as e:  # Capturar cualquier error
        logging.error("Error obteniendo la IP: %s", e)
        return "Desconocida"

# Configurar navegador
def iniciar_driver() -> Optional[webdriver.Chrome]:
    """
    Inicia el driver de Selenium con varias opciones para evitar detección y errores,
    optimizado para entornos sin GPU y modo headless.
    """
    try:
        options = webdriver.ChromeOptions()

        # --- Estabilidad y compatibilidad ---
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")  # mejora compatibilidad en entornos limitados

        # --- Evitar uso de GPU y rasterización (quita los mensajes de GLES) ---
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")

        # --- Anti-detección ---
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # --- Comportamiento visual ---
        options.add_argument("--start-maximized")
        # options.add_argument("--headless=new")  # Descomenta si quieres que corra sin ventana

        # --- Quitar popups y notificaciones ---
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-save-password-bubble")

        # --- Silenciar logs de Chrome ---
        options.add_argument("--log-level=3")
        options.add_argument("--silent")

        # --- Servicio ---
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Evitar detección básica
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
            '''
        })

        return driver
    except WebDriverException as e:
        logging.error("Error al iniciar el driver: %s", e)
        return None

# Manejador de señales para cerrar el navegador
def signal_handler(sig, frame):
    global DRIVER  # Cambiar de 'driver' a 'DRIVER'
    print("Recibiendo señal de terminación, cerrando navegador...")
    logging.info("Recibiendo señal de terminación, cerrando navegador...")
    if DRIVER:
        try:
            DRIVER.quit()
            print("Navegador cerrado correctamente.")
            logging.info("Navegador cerrado correctamente.")
        except Exception as e:
            print(f"Error cerrando navegador: {e}")
            logging.error(f"Error cerrando navegador: {e}")
    sys.exit(0)
# Registrar manejadores de señales
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Decorador para medir tiempos
def medir_tiempo(func: Callable[..., Optional[float]]) -> Callable[..., Optional[float]]:
    """
    Decorador que mide el tiempo de ejecución de una función y lo registra en logs.
    """
    def wrapper(*args, **kwargs) -> Optional[float]:
        inicio = time.time()
        try:
            resultado = func(*args, **kwargs)
            fin = time.time()
            duracion = round(fin - inicio, 3)
            logging.info("✅ Tiempo de %s: %.3f segundos", func.__name__, duracion)
            print(f"Tiempo de {func.__name__}: {duracion} segundos")
            return duracion if resultado is None else resultado
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            logging.error("Error en %s: %s", func.__name__, e)
            return None
    return wrapper

#     Función para Tomar Capturas de Pantalla
def screenshot(driver: webdriver.Chrome, screenshot_name: str, error_subject: str = "Error General Automatización"):
    """
    Toma una captura de pantalla y la guarda en una carpeta 'screenshots'.
    """
    screenshots_dir = "screenshots"
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        logging.info(f"Creado directorio para capturas de pantalla: {screenshots_dir}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(screenshots_dir, f"{screenshot_name}_{timestamp}.png")
    
    screenshot_saved = False
    try:
        driver.save_screenshot(filename)
        logging.error(f"Captura de pantalla guardada: {filename}")
        print(f"Captura de pantalla guardada: {filename}")

        time.sleep(2)  # Espera 1 segundo para asegurar que el archivo se haya escrito correctamente
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
        f"Hora: {timestamp}\n"
        f"URL: {driver.current_url if driver else 'N/A'}"
    )

    # Limita el cuerpo del mensaje si es demasiado largo para un SMS estándar
    # La mayoría de los mensajes SMS tienen un límite de 160 caracteres por segmento.
    # Los mensajes más largos se dividen, pero es mejor ser conciso.
    if len(sms_body_message) > 600: # Un límite razonable para evitar muchos segmentos
        sms_body_message = sms_body_message[:597] + "..." # Truncar y añadir puntos suspensivos

    # Llama a la función de envío de SMS
    # La función send_error_sms solo necesita el asunto y el cuerpo.
    send_error_email(error_subject, sms_body_message, attachment_path=filename if screenshot_saved else None)

def cerrar_modal(driver: webdriver.Chrome, timeout = 1) -> bool:
    """
    Intenta cerrar un modal común si está presente, probando diferentes selectores.

    Args:
        driver: Instancia de Selenium WebDriver.
        timeout: Tiempo máximo en segundos para esperar que el modal aparezca y su botón de cierre sea clickeable.

    Returns:
        True si un modal fue encontrado y cerrado, False en caso contrario o si falla.
    """
    modal_selectors = [
        # 1. XPath más específico para el SVG del botón de cierre que ya tenías
        (By.XPATH, "//svg[.//polygon and contains(@viewBox, '0 0 357 357')]"),

        # 2. XPath por el atributo href del enlace <a>
        (By.XPATH, "//a[@href='#__cn_close_content']"),
        
        # 3. XPath por la clase que empieza con 'cn_content_close-' y el enlace <a> hijo
        (By.XPATH, "//div[starts-with(@class, 'cn_content_close-')]/a"),

        # 4. CSS Selector por el href del enlace <a> (equivalente al XPath anterior)
        (By.CSS_SELECTOR, 'a[href="#__cn_close_content"]'),

        # 5. CSS Selector por la clase que empieza con 'cn_content_close-' y el enlace <a> hijo
        (By.CSS_SELECTOR, "div[class^='cn_content_close-'] > a"),

        # 6. Selectores genéricos para botones de cierre comunes
        (By.CSS_SELECTOR, "button[aria-label='Close'], .close-button, .modal-close, [data-dismiss='modal']"),

        # 7. XPath genérico para botones de cierre dentro de un diálogo modal
        (By.XPATH, "//*[contains(@class, 'modal-dialog')]//button[contains(text(), 'Cerrar') or contains(text(), 'No, gracias')]"),

        # # 8. Selector para el fondo del modal (backdrop)
        (By.CLASS_NAME, "modal-backdrop"),

        (By.XPATH, "//*[@id='modalAddressLocator--ModalN']/div/button")


    ]

    for by_type, selector in modal_selectors:
        try:
            logging.debug(f"Intentando encontrar y cerrar modal con selector: {selector} ({by_type})")
            
            # Caso especial para el backdrop, ya que no es un botón tradicional
            if by_type == By.CLASS_NAME and selector == "modal-backdrop":
                backdrop = WebDriverWait(driver, timeout / 2).until(
                    EC.element_to_be_clickable((by_type, selector))
                )
                driver.execute_script("arguments[0].click();", backdrop)
                logging.info("Modal cerrado clickeando el fondo (backdrop).")
                return True
            else:
                # Intenta encontrar y clickear el elemento de cierre (botón o enlace)
                close_element = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((by_type, selector))
                )
                driver.execute_script("arguments[0].click();", close_element)
                logging.info(f"Modal cerrado exitosamente usando selector: {selector}")
                return True
            
        except TimeoutException:
            logging.debug(f"Modal con selector '{selector}' no encontrado o no clickeable en el tiempo esperado.")
            continue # Intentar con el siguiente selector
        except ElementClickInterceptedException:
            logging.warning(f"Click en el modal '{selector}' interceptado por otro elemento. Reintentando o probando otro selector.")
            screenshot(driver, f"click_intercepted_modal_{selector.replace('/', '_').replace(' ', '_').replace(':', '_').replace('[', '').replace(']', '').replace('#', '')}")
            continue # Intentar con el siguiente selector
        except Exception as e:
            logging.error(f"Error inesperado al intentar cerrar modal con selector '{selector}': {e}")
            screenshot(driver, f"error_cerrar_modal_{selector.replace('/', '_').replace(' ', '_').replace(':', '_').replace('[', '').replace(']', '').replace('#', '')}")
            continue # Intentar con el siguiente selector
            
    logging.info("No se encontró ningún modal para cerrar o todos los intentos fallaron.")
    return False

@medir_tiempo 
def abrir_pagina(driver: webdriver.Chrome) -> bool:
    """
    Abre la página principal de la tienda virtual La Rebaja.
    Verifica que se haya cargado correctamente y que la URL y elementos clave estén presentes.
    Devuelve True si la carga es exitosa, False en caso contrario.
    """
    try:
        # Abrir la URL
        driver.get("https://www.larebajavirtual.com/")
        logging.info("Página solicitada: https://www.larebajavirtual.com/")
        
        # Esperar a que el <body> esté presente como indicio de carga básica
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logging.info("✅ Etiqueta <body> detectada. Carga inicial completada.")

        # Verificar que la URL sea la correcta
        url_actual = driver.current_url
        if "larebajavirtual.com" not in url_actual:
            logging.error("URL inesperada detectada: %s. Cerrando navegador.", url_actual)
            driver.quit()
            return False

        # Esperar un elemento representativo del sitio (ej. logo o menú principal)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'logo')]"))
        )
        logging.info("Logo de La Rebaja detectado. Página cargada correctamente.")

        # Intentar cerrar el modal de bienvenida (opcional)
        cerrar_modal(driver)
        return True

    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"Error al cargar la página de La Rebaja: {e}")
        screenshot(driver, "error_abrir_pagina")
        return False
    except Exception as e:
        logging.error(f"Error inesperado al abrir la página: {e}")
        screenshot(driver, "error_inesperado_abrir_pagina")
        return False

@medir_tiempo
def login_google(driver: webdriver.Chrome):
    """
    Intenta iniciar sesión con Google, con manejo de errores detallado.
    """
    ventana_principal = driver.current_window_handle
    login_successful = False

    try:
        try:
            WebDriverWait(driver, 20).until(EC.number_of_windows_to_be(2))  # Esperar que se abra una nueva ventana
            for handle in driver.window_handles:
                if handle != ventana_principal:
                    driver.switch_to.window(handle)  # Cambiar al nuevo contexto (ventana emergente)
        except:
            pass
        
        user_input_google = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="identifierId"]'))
        )
        user_input_google.send_keys("pruebaslogin360@gmail.com")
        logging.info("Email de Google ingresado en pop-up.")

        boton_google = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="identifierNext"]'))
        )

        driver.execute_script("arguments[0].click();", boton_google)
        logging.info("Clic en botón 'Siguiente' de Google en pop-up.")

        # Esperar hasta que el campo de contraseña sea visible
        pass_input_google = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="password"]/div[1]/div/div[1]/input'))
        )
        pass_input_google.send_keys("Clave12345678-")
        logging.info("Contraseña de Google ingresada en pop-up.")

        ingresar_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="passwordNext"]'))
        )
        driver.execute_script("arguments[0].click();", ingresar_btn)
        logging.info("Clic en botón 'Ingresar' de Google en pop-up.")

        # Esperar a que la ventana de Google se cierre y la URL principal se cargue
        WebDriverWait(driver, 20).until(EC.number_of_windows_to_be(1))
        driver.switch_to.window(ventana_principal) # Volver a la ventana principal
        WebDriverWait(driver, 20).until(EC.url_contains("larebajavirtual.com"))
        logging.info("Autenticación con Google exitosa y retorno a la página principal.")
        print("Login con Google realizado exitosamente.")
        login_successful = True

    except TimeoutException as e:
        logging.error(f"Timeout durante el login con Google: {e}. Un elemento esperado no apareció a tiempo.")
        screenshot(driver, "error_tiempo_esperado_login_email_contraseña.png")
        print(f"Error de tiempo de espera en login con Google: {e}.")
    except NoSuchElementException as e:
        logging.error(f"Elemento no encontrado durante el login con Google: {e}. Revisa los XPaths.")
        screenshot(driver, "error_elemento_no_login_email_contraseña.png")
        print(f"Error de elemento no encontrado en login con Google: {e}.")
    except WebDriverException as e:
        logging.error(f"Error del WebDriver durante el login con Google: {e}. Podría ser un problema de conexión o navegador.")
        screenshot(driver, "error_navegador_login_google.png")
        print(f"Error del navegador en login con Google: {e}.")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado durante el login con Google: {e}")
        screenshot(driver, "error_login_google.png")
        print(f"Error inesperado en login con Google: {e}.")
    finally:
        # Asegurarse de volver a la ventana principal si hay múltiples ventanas abiertas
        if len(driver.window_handles) > 1 and driver.current_window_handle != ventana_principal:
            for handle in driver.window_handles:
                if handle != ventana_principal:
                    try:
                        driver.switch_to.window(handle)
                        driver.close()
                    except:
                        pass # La ventana ya pudo haberse cerrado
            driver.switch_to.window(ventana_principal)
        # Revisamos que la url es la correcta
        if not login_successful and "larebajavirtual.com" not in driver.current_url:
            logging.error("La URL final no es la esperada después de intentar login con Google. Cerrando navegador.")
            driver.quit()
            raise RuntimeError("No se pudo cargar la URL esperada después del login.")
        
    return login_successful

@medir_tiempo
def login_email_password(driver: webdriver.Chrome):
    """
    Intenta iniciar sesión con email y contraseña, con manejo de errores detallado.
    """
    ventana_principal = driver.current_window_handle
    login_successful = False

    try:
        # Guardar el contexto de la ventana original
        # Si se abre una nueva ventana, cambiar a esa ventana emergente
        try:
            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))  # Esperar que se abra una nueva ventana
            for handle in driver.window_handles:
                if handle != ventana_principal:
                    driver.switch_to.window(handle)  # Cambiar al nuevo contexto (ventana emergente)
        except:
            pass

        time.sleep(1)
        try:
            boton_try_again = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space(text())='Try again']"))
            )
            driver.execute_script("arguments[0].click();", boton_try_again)
            print("Se hizo clic en 'Try again'.")
        except TimeoutException:
            print("El botón 'Try again' no apareció. Continuando sin error.")

        # Ahora esperamos a que el formulario esté presente en la nueva ventana
        user_input = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//*[@id='mat-input-0']")))
        pass_input = driver.find_element(By.XPATH, "//*[@id='mat-input-1']")

        # Rellenar los campos de usuario y contraseña
        user_input.send_keys("pruebaslogin360@gmail.com")
        pass_input.send_keys("Clave12345678-")

        # Si se requiere hacer clic en el botón de "Ingresar" (después de habilitarlo)
        ingresar_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//button[@class='submit-button mat-raised-button mat-button-base mat-accent']")))
        driver.execute_script("arguments[0].click();", ingresar_btn)

        # Esperar que la autenticación se complete y redirija a la página principal
        WebDriverWait(driver, 20).until(EC.url_contains("larebajavirtual.com"))

        # Volver al contexto de la ventana principal (si es necesario)
        driver.switch_to.window(ventana_principal)

        logging.info("Credenciales ingresadas y autenticación realizada exitosamente.")
        print("Credenciales ingresadas y autenticación realizada exitosamente.")

        try:
            WebDriverWait(driver, 20).until(EC.url_contains("larebajavirtual.com"))
        except Exception as e:
            print("Error esperando la URL:", e)
            # Aquí puedes tomar acción: reiniciar navegador, cerrar sesión, loggear en Sheets, etc.
            driver.quit()
            raise RuntimeError("No se pudo cargar la URL esperada después del login.") from e

        login_successful = True
    except TimeoutException as e:
        logging.error(f"Timeout durante el login con Email y Contraseña: {e}. Un elemento esperado no apareció a tiempo.")
        screenshot(driver, "error_tiempo_espera_email_contraseña.png")
        print(f"Error de tiempo de espera en login con Email y Contraseña: {e}.")
    except NoSuchElementException as e:
        logging.error(f"Elemento no encontrado durante el login con Email y Contraseña: {e}. Revisa los XPaths.")
        screenshot(driver, "error_elemento_no_encontrado_login_email_contraseña.png")
        print(f"Error de elemento no encontrado en login con Email y Contraseña: {e}.")
    except WebDriverException as e:
        logging.error(f"Error del WebDriver durante el login con Email y Contraseña: {e}. Podría ser un problema de conexión o navegador.")
        screenshot(driver, "error_navegador_email_contraseña.png")
        print(f"Error del navegador en login con Email y Contraseña: {e}.")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado durante el login con Email y Contraseña: {e}")
        screenshot(driver, "error_login_email_contraseña.png")
        print(f"Error inesperado en login con Email y Contraseña: {e}.")
    return login_successful

@medir_tiempo
def login_codigo_validacion(driver: webdriver.Chrome) -> Optional[float]:
    """
    Intenta iniciar sesión con código de validación, con manejo de errores detallado.
    """
    ventana_principal = driver.current_window_handle
    gmail_tab = None # Se inicializa para asegurar que siempre tenga un valor para el finally
    login_start_time = time.time()

    try:
        try:
            if not cerrar_modal(driver):
                logging.warning("La modal de Connectif no pudo ser cerrada, el flujo podría verse afectado.")
        except TimeoutException:
            logging.warning("No se encontró modal adicional para cerrar después de Mi Cuenta.")
        except Exception as e:
            logging.warning(f"Error al intentar cerrar modal adicional después de Mi Cuenta: {e}")
            screenshot(driver, "error_cerrar_modal_despues_mi_cuenta")

        # 1. Ingresar Email y Enviar Código
        user_input_email = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//input[@name='email']"))
        )
        user_input_email.send_keys("pruebaslogin360@gmail.com")
        logging.info("Email para código de validación ingresado.")
        
        time.sleep(1) # Pequeña pausa para que el valor se asiente
        
        boton_enviar_mail = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//button//div[.//span[text()='Enviar']]"))
        )
        driver.execute_script("arguments[0].click();", boton_enviar_mail)
        logging.info("Clic en botón 'Enviar' para código de validación.")
        
        time.sleep(3) # Pequeña pausa para estabilidad después de enviar el email

        logging.info("Abriendo Gmail en una nueva pestaña...")
        driver.execute_script("window.open('https://mail.google.com/mail/u/0/');")

        # Esperar hasta que haya 2 ventanas Y la segunda ventana no sea la principal
        WebDriverWait(driver, 20).until(lambda d: len(d.window_handles) == 2 and d.window_handles[1] != ventana_principal)
        
        all_tabs = driver.window_handles
        # El handle de la pestaña de Gmail debe ser el que no es la ventana principal
        gmail_tab = [handle for handle in all_tabs if handle != ventana_principal][0]
        driver.switch_to.window(gmail_tab)
        logging.info("Cambio a la pestaña de Gmail.")
        
        try:
            boton_try_again = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space(text())='Try again']"))
            )
            driver.execute_script("arguments[0].click();", boton_try_again)
            print("Se hizo clic en 'Try again'.")
        except TimeoutException:
            print("El botón 'Try again' no apareció. Continuando sin error.")

        time.sleep(2)

        # Aumentar tiempo para Gmail, ya que las cargas pueden ser lentas
        user_input_gmail = WebDriverWait(driver, 30).until( 
            EC.presence_of_element_located((By.XPATH, '//*[@id="identifierId"]'))
        )
        user_input_gmail.send_keys("pruebaslogin360@gmail.com")
        logging.info("Email de Gmail ingresado.")

        next1 = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="identifierNext"]'))
        )
        driver.execute_script("arguments[0].click();", next1)

        time.sleep(2)

        password_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="password"]/div[1]/div/div[1]/input'))
        )
        password_input.send_keys("Clave12345678-")
        logging.info("Contraseña de Gmail ingresada.")

        next = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="passwordNext"]'))
        )
        driver.execute_script("arguments[0].click();", next)
        
        # Solo colocarlos  con los expath de saltar y canselar para el inicio de sesion por este medio cambiar expath
        # try:
        #     cancelar = WebDriverWait(driver, 5).until( # Tiempo de espera para encontrar el correo
        #         EC.element_to_be_clickable((By.XPATH, "//tr[@role='row'][1]")) 
        #     )
        #     cancelar.click()
        #     logging.info("saltando cancelar.")
        # except TimeoutException:
        #     pass

        # try:
        #     saltar = WebDriverWait(driver, 5).until( # Tiempo de espera para encontrar el correo
        #         EC.element_to_be_clickable((By.XPATH, "//tr[@role='row'][1]")) 
        #     )
        #     saltar.click()
        #     logging.info("saltando saltar.")
        # except TimeoutException:
        #     pass

        logging.info("Clic en Ingresar en Gmail.")
        time.sleep(2)

        # Refrescar y obtener el código
        driver.refresh() # Refrescar para asegurar que el email más reciente aparezca
        time.sleep(2)
        logging.info("Gmail inbox refrescado. Esperando correo de validación.")

        # Iterar para buscar el correo con el código, ya que a veces tarda en aparecer
        max_retries = 5 # Número máximo de veces que intentaremos refrescar y buscar el correo
        retry_delay = 2 # Segundos entre reintentos
        correo_encontrado = False
        
        for i in range(max_retries):
            try:
                driver.refresh()
                time.sleep(2)
                # Esperar a que el primer correo aparezca y sea clickeable
                # Mejorar XPath para ser más específico si es posible
                correo_envio = WebDriverWait(driver, 30).until( # Tiempo de espera para encontrar el correo
                    EC.element_to_be_clickable((By.XPATH, "//tr[@role='row'][1]")) 
                )
                
                driver.execute_script("arguments[0].click();", correo_envio)
                logging.info(f"Clic en el correo de validación (intento {i+1}).")
                correo_encontrado = True
                break # Salir del bucle si se encuentra el correo
            except TimeoutException:
                logging.warning(f"Correo de validación no encontrado en el intento {i+1}/{max_retries}. Refrescando Gmail...")
                driver.refresh()
                time.sleep(retry_delay)
            except Exception as e:
                logging.error(f"Error inesperado al buscar/clicar el correo de validación: {e}")
                screenshot(driver, f"error_buscar_correo_validacion_intento_{i+1}", f"Gmail - Error Buscando Correo (Intento {i+1})")
                raise # Re-lanza la excepción si no es solo un timeout

        if not correo_encontrado:
            logging.error("No se pudo encontrar el correo de validación de Gmail después de varios intentos.")
            screenshot(driver, "error_correo_validacion_no_encontrado", "Gmail - Correo de Validación No Encontrado")
            raise TimeoutException("No se encontró el correo de validación en Gmail.")

        time.sleep(2)

        num_validacion_element = WebDriverWait(driver, 30).until( # Aumentar espera por si el código no aparece de inmediato
            EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'color:#e72026') and contains(@style, 'text-align:center')]//strong"))
        )
        num_validacion = num_validacion_element.text.strip()
        logging.info(f"Código de validación obtenido: {num_validacion}")
        
        time.sleep(2) # Pequeña pausa
        
        driver.switch_to.window(ventana_principal)
        
        time.sleep(5) # Pequeña pausa para estabilidad después de cambiar de ventana

        if not cerrar_modal(driver):
            logging.warning("La modal de Connectif no pudo ser cerrada, el flujo podría verse afectado.")

        numero_validacion_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//input[@name='token' and @type='text']"))
        )
        numero_validacion_input.send_keys(num_validacion)
        logging.info("Código de validación ingresado en el campo.")

        boton_confirmar = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'vtex-button') and .//span[text()='Confirmar']]"))
        )
        driver.execute_script("arguments[0].click();", boton_confirmar)
        logging.info("Clic en botón 'Confirmar' para el código de validación.")
        
        # 6. Verificar Login Exitoso (Redirección al Home)
        WebDriverWait(driver, 30).until(EC.url_contains("larebajavirtual.com"))
        logging.info("Autenticación con Código de Validación exitosa y redirección a la página principal.")
        print("Login con Código de Validación realizado exitosamente.")
        
        final_time = time.time()
        total_time = round(final_time - login_start_time, 3)
        logging.info(f"Tiempo total de login_codigo_validacion: {total_time} segundos")
        return total_time

    except (TimeoutException, NoSuchElementException) as e:
        error_subject = "Error de Elemento/Timeout - Login Codigo Validacion"
        logging.error(f"❌ Error de elemento/timeout durante el login con Código de Validación: {e}. Un elemento esperado no apareció a tiempo o no se encontró. Revisa los XPaths y tiempos de espera.")
        screenshot(driver, "error_elemento_timeout_login_codigo_de_validacion", error_subject)
        print(f"Error de tiempo de espera o elemento no encontrado en login con Código de Validación: {e}.")
        return None
    except InvalidSessionIdException as e:
        error_subject = "Error de Sesion Invalida - Login Codigo Validacion"
        logging.error(f"❌ Sesión de WebDriver inválida durante el login con Código de Validación: {e}. La ventana fue cerrada o la sesión expiró.")
        # No se puede tomar captura si la sesión es inválida
        send_error_email(error_subject, f"Sesión de WebDriver inválida: {e}. No se pudo tomar captura.")
        print(f"Error de sesión inválida en login con Código de Validación: {e}.")
        return None
    except WebDriverException as e:
        error_subject = "Error de WebDriver - Login Codigo Validacion"
        logging.error(f"❌ Error del WebDriver durante el login con Código de Validación: {e}. Podría ser un problema de conexión o navegador.")
        screenshot(driver, "error_webdriver_login_codigo_de_validacion", error_subject)
        print(f"Error del navegador en login con Código de Validación: {e}.")
        return None
    except Exception as e:
        error_subject = "Error Inesperado - Login Codigo Validacion"
        error_msg = str(e)
        logging.error(f"❌ Ocurrió un error inesperado durante el login con Código de Validación: {error_msg}")
        screenshot(driver, "error_inesperado_login_codigo_de_validacion", error_subject)
        print(f"Error inesperado en login con Código de Validación: {error_msg}.")
        return None

@medir_tiempo
def clic_mi_cuenta(driver: webdriver.Chrome, login_option: str) -> Optional[float]:
    """
    Hace clic en el botón "Mi Cuenta" y luego en la opción de login especificada.
    Incluye manejo de errores y captura de pantalla.
    """
    inicio = time.time() # Inicia el cronómetro al principio de la función

    try:
        logging.info("Intentando hacer clic en el botón 'Mi Cuenta'.")
        boton_mi_cuenta = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'LoginPopUpCustom_button') and .//span[text()='Mi cuenta']]"))
        )
        driver.execute_script("arguments[0].click();", boton_mi_cuenta)
        logging.info("Clic realizado en el botón 'Mi Cuenta'.")
        time.sleep(1) # Espera breve para estabilidad
        
        # Verificación de URL inesperada
        url_actual = driver.current_url
        if "larebajavirtual.com" not in url_actual:
            logging.error("URL inesperada detectada después de clic en Mi Cuenta: %s. No es la página de La Rebaja Virtual.", url_actual)
            screenshot(driver, "url_inesperada_despues_mi_cuenta")
            # Podrías decidir si quieres lanzar una excepción o simplemente retornar None
            raise RuntimeError(f"URL inesperada: {url_actual} después de clic en Mi Cuenta.")

        time.sleep(1) # Espera breve para estabilidad después del clic
        cerrar_modal(driver)
        # Lógica para hacer clic en la opción de login específica
        logging.info(f"Intentando hacer clic en la opción de login: '{login_option}'.")
        if login_option == "Google":
            google_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Entrar con') and .//span[contains(text(), 'Google')]]"))
            )
            driver.execute_script("arguments[0].click();", google_btn)
            logging.info("Clic realizado en 'Entrar con Google'.")
        elif login_option == "Email y contraseña":
            email_pass_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Ingresar con email y contraseña']"))
            )
            driver.execute_script("arguments[0].click();", email_pass_btn)
            logging.info("Clic realizado en 'Ingresar con email y contraseña'.")
        elif login_option == "Codigo de validacion":
            codigo_mail_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'vtex-button') and .//span[text()='Recibir código de acceso por e-mail']]"))
            )
            driver.execute_script("arguments[0].click();", codigo_mail_btn)
            logging.info("Clic realizado en 'Recibir código de acceso por e-mail'.")
        else:
            logging.error(f"Opción de login no reconocida: {login_option}")
            screenshot(driver, f"opcion_login_no_reconocida_{login_option}")
            raise ValueError(f"Opción de login no reconocida: {login_option}")

        # Esperar a que cargue el formulario/pantalla de login específica
        if login_option == "Google":
            WebDriverWait(driver, 15).until(EC.number_of_windows_to_be(2))
            logging.info("Se esperó la apertura de la nueva ventana para Google.")
        else:
            logging.info(f"Esperando campos de email para '{login_option}'.")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//input[@formcontrolname='email'] | //input[@name='email']")))
            logging.info("Campos de email encontrados.")

        fin = time.time()

        tiempo_renderizado_formulario = round(fin - inicio, 3)
        logging.info(f"Tiempo de Renderizado del Formulario/Pantalla de Login ({login_option}): {tiempo_renderizado_formulario} segundos")
        print(f"Tiempo de Renderizado del Formulario/Pantalla de Login ({login_option}): {tiempo_renderizado_formulario} segundos")

    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"ERROR en clic_mi_cuenta: Elemento no encontrado o tiempo de espera excedido. {e}")
        screenshot(driver, f"error_elemento_clic_mi_cuenta_{login_option}")
        print(f"Error de elemento/timeout en clic_mi_cuenta para '{login_option}': {e}")
        return None
    except WebDriverException as e:
        logging.error(f"ERROR del WebDriver en clic_mi_cuenta: {e}")
        screenshot(driver, f"error_webdriver_clic_mi_cuenta_{login_option}")
        print(f"Error del navegador en clic_mi_cuenta para '{login_option}': {e}")
        return None
    except RuntimeError as e: # Captura el error de URL inesperada
        logging.error(f"ERROR de RuntimeError en clic_mi_cuenta: {e}")
        print(f"Error de ejecución en clic_mi_cuenta para '{login_option}': {e}")
        return None
    except ValueError as e: # Captura el error de opción de login no reconocida
        logging.error(f"ERROR de ValueError en clic_mi_cuenta: {e}")
        print(f"Error de valor en clic_mi_cuenta para '{login_option}': {e}")
        return None
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado en clic_mi_cuenta: {e}")
        screenshot(driver, f"error_inesperado_clic_mi_cuenta_{login_option}")
        print(f"Error inesperado en clic_mi_cuenta para '{login_option}': {e}")
        return None
    
    return tiempo_renderizado_formulario

@medir_tiempo
def clic_ingresar(driver: webdriver.Chrome) -> Optional[float]:
    """
    Hace clic en el botón 'Ingresar' (después de credenciales) y espera que se cargue el home.
    Devuelve el tiempo que tardó en renderizarse el home o None si falla.
    """
    inicio = time.time() # Inicia el cronómetro al principio

    try:
        logging.info("Esperando que la URL sea la del home y detección de elementos clave.")

        # Aumentamos el tiempo de espera por si el home tarda en cargar
        wait_time = 20 
        
        WebDriverWait(driver, wait_time).until(
            lambda d: "larebajavirtual.com" in d.current_url and 
            (
                # Estas son tus condiciones existentes
                EC.presence_of_element_located((By.XPATH, '//*[@id="modalAddressLocator--ModalN"]/div/div'))(d) or
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'vtex-store-header')]"))(d) or
                EC.presence_of_element_located((By.XPATH, "//header[contains(@class, 'header')]"))(d) or
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Buscar productos')]"))(d)
            )
        )
        logging.info("✅ Redirección al home y detección de elementos clave confirmada.")

        fin = time.time()
        tiempo_renderizado_home = round(fin - inicio, 3)
        logging.info("✅ Tiempo de Renderizado del Home: %.3f segundos", tiempo_renderizado_home)
        print(f"Tiempo de Renderizado del Home: {tiempo_renderizado_home} segundos")
        return tiempo_renderizado_home

    except TimeoutException as e:
        logging.error(f"❌ Error Timeout: No se detectó el home dentro del tiempo de espera ({wait_time} segundos). La página no cargó correctamente o los elementos clave no aparecieron. {e}") # type: ignore
        return None
    
    except NoSuchElementException as e:
        # Esto capturaría si algún `find_element` dentro de la lambda falla
        logging.error(f"❌ Error NoSuchElement: Se encontró la URL, pero no se encontró un elemento clave del home. {e}")
        screenshot(driver, "error_home_element_not_found")
        return None

    except WebDriverException as e:
        # Captura errores generales del WebDriver (ej. navegador se cerró inesperadamente)
        logging.error(f"❌ Error del WebDriver al verificar el home: {e}")
        screenshot(driver, "error_webdriver_verificar_home")
        return None

    except Exception as e:
        # Captura cualquier otra excepción inesperada
        logging.error(f"❌ Ocurrió un error inesperado al verificar el home: {e}")
        screenshot(driver, "error_inesperado_verificar_home")
        return None
    
@medir_tiempo
def confirmar_login(driver: webdriver.Chrome):
    """
    Confirma el inicio de sesión presionando el botón "Confirmar"
    y cierra la modal si aparece.
    """
    try:
        time.sleep(1)

        cerrar_modal(driver)  # Intentar cerrar modal si aparece

        time.sleep(1)

        # Esperar y dar clic al botón "Confirmar"
        try:
            boton = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//div[text()='Confirmar']")))
            driver.execute_script("arguments[0].click();", boton)
        except TimeoutException:
            logging.warning("No se encontró el boton confirmar adicional para cerrar.")
        except Exception as e:
            logging.warning(f"Error al intentar cerrar modal adicional: {e}")

        # Esperar un poco que se refresque/renderice
        time.sleep(1)
        
        cerrar_modal(driver)  # Cerrar modal si aparece después de hacer clic en "Confirmar"
        
    except (TimeoutException, NoSuchElementException) as exc:
        screenshot(driver, "error_boton_confirmar")
        logging.error("Error crítico: No se encontró el botón 'Confirmar'. Deteniendo ejecución.")
        raise RuntimeError("No se encontró el botón 'Confirmar'. Verificar flujo de login.") from exc
    except WebDriverException as e:
        screenshot(driver, "error_confirmar_login")
        logging.error("Error en confirmar_login: %s", e)
        raise

def que_estas_buscando(driver: webdriver.Chrome):
    """
    Escribe el producto en la barra de búsqueda, hace clic en la lupa y espera la carga de resultados.
    Luego, hace zoom para mejorar la visibilidad.
    """
    try:
        # Localizar el campo de búsqueda
        campo_busqueda = WebDriverWait(driver, 20).until(EC.presence_of_element_located((
            By.XPATH, "//input[@placeholder='¿Qué estás buscando?']"))
        )
        campo_busqueda.clear()
        campo_busqueda.send_keys("PAÑAL HUGGIES PANTS ACTIVE SEC ETAPA 5/XXG X 25")
        time.sleep(1)

        # Clic en la lupa sin recargar la página
        boton_lupa = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Buscar Productos']"))
        )
        driver.execute_script("arguments[0].click();", boton_lupa)
        time.sleep(1)

        # Aplicar zoom en lugar de hacer scroll
        driver.execute_script("document.body.style.zoom='70%'")

        # Esperar que el producto esté en la página
        producto = WebDriverWait(driver, 20).until(EC.presence_of_element_located((
            By.XPATH, "//h3/span[contains(text(), 'PAÑAL HUGGIES PANTS ACTIVE SEC')]"))
        )
        print(f"Producto encontrado: {producto.text}")  # 🔹 Evita warning de variable no usada

        # 🔹 Verificar si el botón "Comprar" es visible
        try:
            boton_comprar = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((
                    By.XPATH, "//button[.//span[normalize-space(text())='Comprar']]"))
            )
            print(f"Botón 'Comprar' encontrado: {boton_comprar.tag_name}")  # 🔹 Evita warning de variable no usada
        except TimeoutException:
            screenshot(driver, "error_boton_comprar")
            logging.error("No se encontró el botón 'Comprar' después de minimizar la página.")

    except TimeoutException as e:
        screenshot(driver, "error_interactuar_busqueda")
        logging.error("Timeout al interactuar con la búsqueda: %s", e)

    except NoSuchElementException as e:
        screenshot(driver, "error_elemento_no_encontrado")
        logging.error("Elemento no encontrado: %s", e)

    except StaleElementReferenceException:
        logging.warning("Elemento obsoleto, intentando nuevamente...")
        time.sleep(1)
        return que_estas_buscando(driver)

def clic_lupa(driver: webdriver.Chrome) -> Optional[float]:
    """
    Hace un scroll corto hacia abajo, luego clic en la lupa y devuelve el tiempo en segundos.
    """
    try:
        wait = WebDriverWait(driver, 20)

        boton = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Buscar Productos']")))

        tiempo_inicio = time.time()
        driver.execute_script("arguments[0].click();", boton)  # 🔹 Clic con JavaScript
        tiempo_total = round(time.time() - tiempo_inicio, 3)

        logging.info("Tiempo de clic_lupa: %s segundos", tiempo_total)
        return tiempo_total
    except (TimeoutException, NoSuchElementException) as e:
        screenshot(driver, "error_clic_en_lupa")
        logging.error("Error al hacer clic en la lupa: %s", e)
        return None
    
def clic_comprar(driver: webdriver.Chrome) -> bool:
    '''
    Hace clic en el botón "Comprar" asegurando que está presente y habilitado en la pantalla.
    Implementa un manejo robusto de excepciones y toma capturas de pantalla en caso de error.
    Retorna True si el clic fue exitoso, False en caso contrario.
    '''
    success = False # Variable para controlar el éxito de la operación
    
    try:
        logging.info("Intentando encontrar y hacer clic en el botón 'Comprar'.")
        # Esperar a que el botón "Comprar" esté presente y sea clickeable
        # Aumentamos el tiempo de espera por si la página tarda en cargar el elemento
        boton_comprar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='gallery-layout-container']/div/section/a/article/div[7]/div/div/button/div/div/span"))
        )

        # Verificar si el botón está habilitado y visible antes de hacer clic
        if boton_comprar.is_enabled() and boton_comprar.is_displayed():
            driver.execute_script("arguments[0].click();", boton_comprar)
            logging.info("✅ Se hizo clic en el botón 'Comprar' exitosamente.")
            print("✅ Se hizo clic en el botón 'Comprar'")
            success = True
        else:
            logging.error("⛔ El botón 'Comprar' no está habilitado o visible para clic.")
            screenshot(driver, "error_boton_comprar_no_enabled_visible") # Captura si no está clickeable
            success = False

    except TimeoutException:
        # Si el elemento no se encuentra dentro del tiempo de espera
        logging.error("⛔ Timeout: No se encontró el botón 'Comprar' dentro del tiempo de espera. Verificar XPATH o si el elemento no se carga.")
        screenshot(driver, "error_timeout_boton_comprar")
        success = False

    except NoSuchElementException:
        # Si el elemento no existe en el DOM (aunque el TimeoutException suele cubrir esto)
        logging.error("⛔ NoSuchElement: El botón 'Comprar' no se encontró en el DOM con el XPATH especificado. Verificar XPATH.")
        screenshot(driver, "error_no_such_element_boton_comprar")
        success = False

    except ElementClickInterceptedException:
        # Si otro elemento bloquea el clic
        logging.warning("⚠ ElementClickIntercepted: El botón 'Comprar' estaba bloqueado por otro elemento. Intentando hacer clic con JavaScript.")
        try:
            # Intentar hacer clic con JavaScript para evadir el elemento interceptor
            driver.execute_script("arguments[0].click();", boton_comprar) # type: ignore
            logging.info("✅ Clic realizado en el botón 'Comprar' usando JavaScript.")
            print("✅ Se hizo clic en el botón 'Comprar' usando JavaScript.")
            success = True
        except (WebDriverException, Exception) as js_click_e:
            # Si el clic con JavaScript también falla
            logging.error(f"⛔ Fallo al hacer clic en 'Comprar' incluso con JavaScript: {js_click_e}")
            screenshot(driver, "error_js_click_fallido_boton_comprar")
            success = False

    except StaleElementReferenceException:
        # Si el elemento se vuelve obsoleto (la página cambió)
        logging.error("⛔ StaleElementReference: El botón 'Comprar' ya no es accesible en el DOM (la página pudo haberse recargado).")
        screenshot(driver, "error_stale_element_boton_comprar")
        success = False

    except WebDriverException as e:
        # Captura errores generales del WebDriver (problemas de conexión, navegador crash, etc.)
        logging.error(f"⛔ WebDriverException: Ocurrió un error general del WebDriver al intentar hacer clic en 'Comprar': {e}")
        screenshot(driver, "error_webdriver_general_boton_comprar")
        success = False

    except Exception as e:
        # Captura cualquier otra excepción inesperada
        logging.error(f"⛔ Error inesperado al intentar hacer clic en el botón 'Comprar': {e}")
        screenshot(driver, "error_inesperado_boton_comprar")
        success = False

    return success

@medir_tiempo
def salir_cuenta(driver: webdriver.Chrome) -> float:
    """
    Cierra sesión desde la sección "Mi Cuenta" y mide el tiempo de ejecución.
    """
    try:
        time.sleep(1)
        inicio = time.time()  # Registrar inicio de tiempo
        logging.info("Intentando hacer clic en el botón 'Mi Cuenta'...")
        # Esperar y hacer clic en el botón "Mi Cuenta"
        boton_cuenta = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'vtex-login-2-x-profile') and contains(text(), 'Hola,')]"))
        )
        driver.execute_script("arguments[0].click();", boton_cuenta)
        logging.info("Clic realizado en el botón 'Mi Cuenta'.")

        # Esperar y hacer clic en el botón "Salir"
        logging.info("Intentando hacer clic en el botón 'Salir'...")
        boton_salir = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//*[text()='Salir']"))
        )
        driver.execute_script("arguments[0].click();", boton_salir)
        logging.info("Clic realizado en el botón 'Salir'.")

        # Calcular y retornar el tiempo de ejecución
        fin = time.time()
        time.sleep(1)
        tiempo = round(fin - inicio, 3)
        logging.info("Tiempo de ejecución de salir_cuenta: %.3f segundos", tiempo)
        return tiempo

    except (TimeoutException, NoSuchElementException) as e:
        fin = time.time()
        tiempo_fallo = round(fin - inicio, 3) # type: ignore
        logging.error(f"ERROR en salir_cuenta: Elemento no encontrado o tiempo de espera excedido: {e}")
        screenshot(driver, "error_elemento_salir_cuenta") # Captura de pantalla
        logging.info("Tiempo medido hasta el fallo: %.3f segundos", tiempo_fallo)
        return 0.0
    except WebDriverException as e:
        fin = time.time()
        tiempo_fallo = round(fin - inicio, 3) # type: ignore
        logging.error(f"ERROR en salir_cuenta (WebDriver): {e}")
        screenshot(driver, "error_webdriver_salir_cuenta") # Captura de pantalla
        logging.info("Tiempo medido hasta el fallo: %.3f segundos", tiempo_fallo)
        return 0.0
    except Exception as e:
        fin = time.time()
        tiempo_fallo = round(fin - inicio, 3) # type: ignore
        logging.error(f"ERROR inesperado en salir_cuenta: {e}")
        screenshot(driver, "error_inesperado_salir_cuenta") # Captura de pantalla
        logging.info("Tiempo medido hasta el fallo: %.3f segundos", tiempo_fallo)
        return 0.0
    
@medir_tiempo
def autenticado_salir(driver: webdriver.Chrome) -> Optional[float]:
    """
    Cierra sesión desde la autenticación del usuario y mide el tiempo.
    Debe esperar hasta que se complete el proceso de cierre de sesión.
    """
    try:
        time.sleep(1)
        # busca si el elemento no se encuentra usando el until_not
        inicio = time.time()

        # Esperar a que se redirija a la página de inicio de sesión
        WebDriverWait(driver, 5).until_not(
            EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'icon-mi-ubicacion')]"))
        )
        logging.info("no se encuentra el elemento se considera que cerro sesión")

        fin = time.time()
        tiempo = round(fin - inicio, 3) # type: ignore

        logging.info("Tiempo de autenticado_salir: %.3f segundos", tiempo)
    
    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"Error en autenticado_salir: Elemento no encontrado o tiempo de espera excedido: {e}")
        screenshot(driver, "error_elemento_autenticado_salir") # Captura de pantalla
        fin = time.time()
        tiempo = round(fin - inicio, 3) # type: ignore
        logging.info("Tiempo de autenticado_salir en caso de error (elemento): %.3f segundos", tiempo)
        return tiempo
    except WebDriverException as e:
        logging.error(f"Error en autenticado_salir (WebDriver): {e}")
        screenshot(driver, "error_webdriver_autenticado_salir") # Captura de pantalla
        fin = time.time()
        tiempo = round(fin - inicio, 3) # type: ignore
        logging.info("Tiempo de autenticado_salir en caso de error (WebDriver): %.3f segundos", tiempo)
        return tiempo
    except Exception as e:
        logging.error(f"Error inesperado en autenticado_salir: {e}")
        screenshot(driver, "error_inesperado_autenticado_salir") # Captura de pantalla
        fin = time.time()
        tiempo = round(fin - inicio, 3) # type: ignore
        logging.info("Tiempo de autenticado_salir en caso de error (inesperado): %.3f segundos", tiempo)
        return tiempo
    return tiempo

def cerrar_navegador(driver: webdriver.Chrome):
    """
    Cierra el navegador de manera segura.
    """
    driver.quit()

def guardar_en_mysql(datos):
    """
    guarda los datos en la tabla de la base de datos
    """
    try:
        conexion = mysql.connector.connect(
            host="192.168.100.130",
            user="userdesarrollo",
            password="Ivhq5YQKu7*",
            database="lopido"
        )
        cursor = conexion.cursor()
        consulta = """
        INSERT INTO conexionloginqa 
        (dia, horaInicio, usuario, ip, tiempoRenderizado, timepoTomaRender, miCuentaSalir, autenticadoSalir, estado) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        print("Ejecutando consulta:", consulta % tuple(datos))  # Debugging
        cursor.execute(consulta, datos)
        conexion.commit()
        cursor.close()
        conexion.close()
        print("✅ Datos guardados en MySQL correctamente.")
    except mysql.connector.Error as error:
        print(f"❌ Error al guardar en MySQL: {error}")

def guardar_en_google_sheets(datos, url_valida=True):
    """
    guarda los datos en la hoja de cálculo de google sheets
    """
    if not url_valida:
        print("URL incorrecta. No se guardarán los datos en Google Sheets.")
        return
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            r"C:\Users\jperdomolc\Music\LoginRebaja\booming-mission-451620-a9-fbad2efec009.json", scope # type: ignore
        )
        client = gspread.authorize(creds) # type: ignore
        sheet = client.open_by_key("1EcCiF1nRMfqKgHv7z4wPxy-QRvW1z2-sLQXlZSvgDgw").worksheet("TiemposAutomatización")
        sheet.insert_row(datos, 2)
        print("✅ Datos guardados en Google Sheets correctamente en la fila 2.")
    except (TimeoutException, NoSuchElementException, WebDriverException) as e:
        print(f"❌ Error al guardar en Google Sheets: {e}")

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    while True:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("automatizacion.log", encoding='utf-8')
            ]
        )

        print("⏳ Iniciando ciclo de ejecución de pruebas de login...")
        logging.info("Iniciando ciclo de ejecución de pruebas de login...")

        # Se crea una lista que guarde los metodos para logearse
        login_methods = [
            "Codigo de validacion",
            "Google",
            "Email y contraseña"
        ]

        # Iteramos los metodos en el for usando la variable login_method
        for login_method in login_methods:
            DRIVER = None # Initialize driver for each iteration
            try:
                DRIVER = iniciar_driver()
                driver = DRIVER
                if not DRIVER:
                    logging.error("Error al iniciar el navegador. Saltando al siguiente método de login...")
                    continue

                DRIVER.maximize_window()

                DIA = datetime.now().strftime("%Y/%m/%d")
                HORA_DE_INICIO = datetime.now().strftime("%H:%M:%S")
                USUARIO = "pruebaslogin360@gmail.com"
                IP = obtener_ip()
                LOGIN_TYPE_USED = login_method # Store the current login method

                if not abrir_pagina(DRIVER): # Check if page opened successfully
                    logging.error(f"No se pudo abrir la página para el método {login_method}. Saltando al siguiente...")
                    cerrar_navegador(DRIVER)
                    continue

                inicio_tiempo_formulario = time.time()
                TIEMPO_RENDERIZADO_FORMULARIO_LOGIN = clic_mi_cuenta(DRIVER, LOGIN_TYPE_USED) or round(time.time() - inicio_tiempo_formulario, 3)

                # Conditional login based on type
                login_success = False
                
                if LOGIN_TYPE_USED == "Google":
                    login_success = login_google(DRIVER)
                elif LOGIN_TYPE_USED == "Email y contraseña":
                    login_success = login_email_password(DRIVER)
                elif LOGIN_TYPE_USED == "Codigo de validacion":
                    login_success = login_codigo_validacion(DRIVER)
                else:
                    logging.error(f"Tipo de login desconocido: {LOGIN_TYPE_USED}")
                    login_success = False

                TIEMPO_RENDERIZADO_HOME = clic_ingresar(DRIVER)
                TIEMPO_RENDERIZADO_HOME = TIEMPO_RENDERIZADO_HOME if TIEMPO_RENDERIZADO_HOME is not None else -1

                if not login_success:
                    logging.error(f"Fallo el login para el método {LOGIN_TYPE_USED}. Saltando al siguiente...")
                    ESTADO = "Fallido"
                    DATOS = [DIA, HORA_DE_INICIO, USUARIO, IP, TIEMPO_RENDERIZADO_FORMULARIO_LOGIN, TIEMPO_RENDERIZADO_HOME, -1, -1, ESTADO, LOGIN_TYPE_USED]
                    guardar_en_google_sheets(DATOS, True)
                    # guardar_en_mysql(DATOS)
                    cerrar_navegador(DRIVER)
                    continue # Skip to the next login method

                confirmar_login(DRIVER)
                que_estas_buscando(DRIVER)

                time.sleep(1)
                TIEMPO_CLIC_LUPA = clic_lupa(DRIVER)
                time.sleep(1)
                clic_comprar(DRIVER)
                time.sleep(1)

                TIEMPO_CERRAR_MI_CUENTA = salir_cuenta(DRIVER) or 0.0
                TIEMPO_AUTENTICADO_SALIR = autenticado_salir(DRIVER) or 0.0

                logging.info("Tiempo cerrar mi cuenta: %.3f", TIEMPO_CERRAR_MI_CUENTA)
                logging.info("Tiempo autenticado salir: %.3f", TIEMPO_AUTENTICADO_SALIR)

                ESTADO = "Exitoso" if (TIEMPO_RENDERIZADO_FORMULARIO_LOGIN is not None and TIEMPO_RENDERIZADO_FORMULARIO_LOGIN > 0 and
                                    TIEMPO_CERRAR_MI_CUENTA is not None and TIEMPO_CERRAR_MI_CUENTA > 0 and
                                    TIEMPO_AUTENTICADO_SALIR is not None and TIEMPO_AUTENTICADO_SALIR > 0) else "Fallido"

                DATOS = [DIA, HORA_DE_INICIO, USUARIO, IP, TIEMPO_RENDERIZADO_FORMULARIO_LOGIN, TIEMPO_RENDERIZADO_HOME,
                        TIEMPO_CERRAR_MI_CUENTA, TIEMPO_AUTENTICADO_SALIR, ESTADO, LOGIN_TYPE_USED]

                url_correcta = DRIVER.current_url if DRIVER else ""
                if "larebajavirtual.com" in url_correcta:
                    logging.info("✅ URL válida para Google Sheets guardando datos.")
                    guardar_en_google_sheets(DATOS, True)
                else:
                    logging.warning("URL inválida. No se guarda en Google Sheets.")
                    guardar_en_google_sheets(DATOS, False)
                
                # guardar_en_mysql(DATOS)

            except (TimeoutException, NoSuchElementException, WebDriverException) as e:
                logging.error(f"Error en la ejecución para el método {login_method}: {e}")
                ESTADO = "Fallido por Excepción"
                DATOS = [DIA if DIA in locals() else '', HORA_DE_INICIO if HORA_DE_INICIO in locals() else '',  # type: ignore
                        USUARIO if USUARIO in locals() else '', IP if IP in locals() else '', # type: ignore
                        -1, -1, -1, -1, ESTADO, login_method]
                guardar_en_google_sheets(DATOS, True)
                # guardar_en_mysql(DATOS)
            finally:
                if DRIVER:
                    cerrar_navegador(DRIVER)

            time.sleep(10)  # Pausa entre métodos

        # Al finalizar todos los métodos
        print("✅ Ciclo de ejecución finalizado. Esperando 3 minutos para reiniciar...")
        logging.info("✅ Ciclo de ejecución finalizado. Esperando 3 minutos para reiniciar...\n")


        time.sleep(180)  # Espera de 3 minutos antes de repetir

# Permite que server.py importe y ejecute la automatización
def main_automation():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    while True:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("automatizacion.log", encoding='utf-8')
            ]
        )

        print("⏳ Iniciando ciclo de ejecución de pruebas de login...")
        logging.info("Iniciando ciclo de ejecución de pruebas de login...")
 
        login_methods = [
            "Codigo de validacion",
            "Google",
            "Email y contraseña"
        ]

        for login_method in login_methods:
            DRIVER = None
            try:
                DRIVER = iniciar_driver()
                driver = DRIVER
                if not DRIVER:
                    logging.error("Error al iniciar el navegador. Saltando al siguiente método de login...")
                    continue

                DRIVER.maximize_window()

                DIA = datetime.now().strftime("%Y/%m/%d")
                HORA_DE_INICIO = datetime.now().strftime("%H:%M:%S")
                USUARIO = "pruebaslogin360@gmail.com"
                IP = obtener_ip()
                LOGIN_TYPE_USED = login_method

                if not abrir_pagina(DRIVER):
                    logging.error(f"No se pudo abrir la página para el método {login_method}. Saltando al siguiente...")
                    cerrar_navegador(DRIVER)
                    continue

                inicio_tiempo_formulario = time.time()
                TIEMPO_RENDERIZADO_FORMULARIO_LOGIN = clic_mi_cuenta(DRIVER, LOGIN_TYPE_USED) or round(time.time() - inicio_tiempo_formulario, 3)

                login_success = False
                if LOGIN_TYPE_USED == "Google":
                    login_success = login_google(DRIVER)
                elif LOGIN_TYPE_USED == "Email y contraseña":
                    login_success = login_email_password(DRIVER)
                elif LOGIN_TYPE_USED == "Codigo de validacion":
                    login_success = login_codigo_validacion(DRIVER)
                else:
                    logging.error(f"Tipo de login desconocido: {LOGIN_TYPE_USED}")
                    login_success = False

                TIEMPO_RENDERIZADO_HOME = clic_ingresar(DRIVER)
                TIEMPO_RENDERIZADO_HOME = TIEMPO_RENDERIZADO_HOME if TIEMPO_RENDERIZADO_HOME is not None else -1

                if not login_success:
                    logging.error(f"Fallo el login para el método {LOGIN_TYPE_USED}. Saltando al siguiente...")
                    ESTADO = "Fallido"
                    DATOS = [DIA, HORA_DE_INICIO, USUARIO, IP, TIEMPO_RENDERIZADO_FORMULARIO_LOGIN, TIEMPO_RENDERIZADO_HOME, -1, -1, ESTADO, LOGIN_TYPE_USED]
                    guardar_en_google_sheets(DATOS, True)
                    cerrar_navegador(DRIVER)
                    continue

                confirmar_login(DRIVER)
                que_estas_buscando(DRIVER)

                time.sleep(1)
                TIEMPO_CLIC_LUPA = clic_lupa(DRIVER)
                time.sleep(1)
                clic_comprar(DRIVER)
                time.sleep(1)

                TIEMPO_CERRAR_MI_CUENTA = salir_cuenta(DRIVER) or 0.0
                TIEMPO_AUTENTICADO_SALIR = autenticado_salir(DRIVER) or 0.0

                logging.info("Tiempo cerrar mi cuenta: %.3f", TIEMPO_CERRAR_MI_CUENTA)
                logging.info("Tiempo autenticado salir: %.3f", TIEMPO_AUTENTICADO_SALIR)

                ESTADO = "Exitoso" if (TIEMPO_RENDERIZADO_FORMULARIO_LOGIN is not None and TIEMPO_RENDERIZADO_FORMULARIO_LOGIN > 0 and
                                    TIEMPO_CERRAR_MI_CUENTA is not None and TIEMPO_CERRAR_MI_CUENTA > 0 and
                                    TIEMPO_AUTENTICADO_SALIR is not None and TIEMPO_AUTENTICADO_SALIR > 0) else "Fallido"

                DATOS = [DIA, HORA_DE_INICIO, USUARIO, IP, TIEMPO_RENDERIZADO_FORMULARIO_LOGIN, TIEMPO_RENDERIZADO_HOME,
                        TIEMPO_CERRAR_MI_CUENTA, TIEMPO_AUTENTICADO_SALIR, ESTADO, LOGIN_TYPE_USED]

                url_correcta = DRIVER.current_url if DRIVER else ""
                if "larebajavirtual.com" in url_correcta:
                    logging.info("✅ URL válida para Google Sheets guardando datos.")
                    guardar_en_google_sheets(DATOS, True)
                else:
                    logging.warning("URL inválida. No se guarda en Google Sheets.")
                    guardar_en_google_sheets(DATOS, False)

            except (TimeoutException, NoSuchElementException, WebDriverException) as e:
                logging.error(f"Error en la ejecución para el método {login_method}: {e}")
                ESTADO = "Fallido por Excepción"
                DATOS = [DIA if DIA in locals() else '', HORA_DE_INICIO if HORA_DE_INICIO in locals() else '',
                        USUARIO if USUARIO in locals() else '', IP if IP in locals() else '',
                        -1, -1, -1, -1, ESTADO, login_method]
                guardar_en_google_sheets(DATOS, True)
            finally:
                if DRIVER:
                    cerrar_navegador(DRIVER)

            time.sleep(10)

        print("✅ Ciclo de ejecución finalizado. Esperando 3 minutos para reiniciar...")
        logging.info("✅ Ciclo de ejecución finalizado. Esperando 3 minutos para reiniciar...\n")
        time.sleep(180)