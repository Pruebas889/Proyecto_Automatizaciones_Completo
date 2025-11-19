"""
Script para automatizar el login con usuario de soporte, guardando logs y ejecutándose en Firefox
"""
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException
from selenium.webdriver.support.ui import Select
from generacion_pdf import generar_pdf_consolidado, escribir_log  # Generador de PDF y logger
import logging


# Funciones auxiliares que sirven para resaltar elementos y manejar los procesos fundamentales de la automatizacion 
# Tener en cuenta estos primeros (resaltar_elemento, mostrar_mensaje_inicio, capturar_pantalla y aunque no este en este mismo scripy tambien esta esperar_carga o algo asi  que sive para cuando sale el modal de carga)

def resaltar_elemento(driver, elemento, color="red", grosor="3px", duracion_ms=1000):
    driver.execute_script(f"""
        var elem = arguments[0];
        var original = elem.getAttribute('style');
        elem.style.border = '{grosor} solid {color}';
        setTimeout(function(){{
            if (original) {{
                elem.setAttribute('style', original);
            }} else {{
                elem.removeAttribute('style');
            }}
        }}, {duracion_ms});
    """, elemento)

def mostrar_mensaje_inicio(driver, nombre_automatizacion):
    """Muestra un mensaje en pantalla indicando el inicio de sesión."""
    try:
        driver.execute_script("""
            if (document.body) {
                var div = document.createElement('div');
                div.innerHTML = 'Se realiza el inicio de sesión';
                div.style.position = 'fixed';
                div.style.top = '10px';
                div.style.right = '10px';
                div.style.backgroundColor = 'yellow';
                div.style.padding = '10px';
                div.style.fontSize = '20px';
                div.style.zIndex = '9999';
                div.id = 'mensaje_login';
                document.body.appendChild(div);
            } else {
                console.log('Error: document.body is null');
            }
        """)
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error al ejecutar el script de mensaje: {e}")
        raise

def capturar_pantalla(driver, ruta, texto, capturas, textos, nombre_automatizacion):
    """Toma una captura de pantalla y la agrega a las listas correspondientes."""
    try:
        time.sleep(0.5)
        # Asegurarse de que la carpeta existe
        carpeta_capturas = "capturas"
        os.makedirs(carpeta_capturas, exist_ok=True)
        ruta_completa = os.path.join(carpeta_capturas, ruta)
        driver.save_screenshot(ruta_completa)
        capturas.append(ruta_completa)
        textos.append(texto)
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error al tomar la captura {ruta_completa}: {e}") # type: ignore
        raise

def redirigir_a_login(driver, wait, nombre_automatizacion):
    """Redirige a la página de login haciendo clic en el enlace de login."""
    try:
        login_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//ul[@class='sidebar-menu']//a[@href='/login']")))
        resaltar_elemento(driver, login_link)
        driver.execute_script("arguments[0].click();", login_link)
        escribir_log(nombre_automatizacion, "Redirigido a la página de login")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: Tiempo excedido al localizar o hacer clic en el enlace de login.")
        raise
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el enlace de login.")
        raise
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error de webdriver al redirigir a login: {e}")
        raise

def ingresar_usuario(driver, wait, nombre_automatizacion):
    """Ingresa el usuario en el campo correspondiente."""
    try:
        usuario_input = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='loginform-username']")))
        usuario_input.send_keys("1085251409")
        resaltar_elemento(driver, usuario_input)
        escribir_log(nombre_automatizacion, "Usuario ingresado")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: Tiempo excedido al localizar el campo de usuario.")
        raise
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el campo de usuario.")
        raise
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error de webdriver al ingresar usuario: {e}")
        raise

def ingresar_contrasena(driver, wait, nombre_automatizacion):
    """Ingresa la contraseña en el campo correspondiente."""
    try:
        password_input = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='loginform-password']")))
        password_input.send_keys("1085251409")
        resaltar_elemento(driver, password_input)
        escribir_log(nombre_automatizacion, "Contraseña ingresada")
        time.sleep(0.5)
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: Tiempo excedido al localizar el campo de contraseña.")
        raise
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el campo de contraseña.")
        raise
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error de webdriver al ingresar contraseña: {e}")
        raise

def seleccionar_perfil(driver, wait, nombre_automatizacion):
    """Selecciona el perfil 'Soporte' en el dropdown."""
    try:
        perfil_dropdown = wait.until(EC.presence_of_element_located((By.ID, "authitem-name")))
        resaltar_elemento(driver, perfil_dropdown)
        Select(perfil_dropdown).select_by_visible_text("Soporte")
        escribir_log(nombre_automatizacion, "Perfil 'Soporte' seleccionado")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: Tiempo excedido al localizar el dropdown de perfil.")
        raise
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el dropdown de perfil.")
        raise
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error de webdriver al seleccionar perfil: {e}")
        raise

def realizar_login(driver, wait, nombre_automatizacion):
    """Realiza el clic en el botón de login."""
    try:
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        resaltar_elemento(driver, login_button)
        login_button.click()
        escribir_log(nombre_automatizacion, "Botón de login presionado")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: Tiempo excedido al localizar o hacer clic en el botón de login.")
        raise
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el botón de login.")
        raise
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error de webdriver al presionar el botón de login: {e}")
        raise

def generar_pdf(capturas, textos, nombre_automatizacion):
    """Genera un PDF consolidado con las capturas y textos."""
    try:
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al generar el PDF consolidado: {e}")
        raise

def login_usuario_soporte(driver):
    """
    Realiza el login de un usuario soporte en POSWeb con flecha y resaltado.
    """
    wait = WebDriverWait(driver, 20)
    capturas = []
    textos = []
    nombre_automatizacion = "login_soporte_pdf"

    try:
        mostrar_mensaje_inicio(driver, nombre_automatizacion)
        capturar_pantalla(driver, "captura_inicio_login.png", "Iniciando proceso de inicio de sesión con el usuario de soporte.", capturas, textos, nombre_automatizacion)

        escribir_log(nombre_automatizacion, "Navegador abierto y página cargada")

        redirigir_a_login(driver, wait, nombre_automatizacion)
        capturar_pantalla(driver, "captura_login_link.png", "El usuario ha sido redirigido a la página de login.", capturas, textos, nombre_automatizacion)

        ingresar_usuario(driver, wait, nombre_automatizacion)
        capturar_pantalla(driver, "captura_usuario.png", "El usuario ha ingresado correctamente su número de identificación en el campo de login.", capturas, textos, nombre_automatizacion)

        ingresar_contrasena(driver, wait, nombre_automatizacion)
        capturar_pantalla(driver, "captura_password.png", "El usuario ha ingresado correctamente su contraseña en el campo de login.", capturas, textos, nombre_automatizacion)

        seleccionar_perfil(driver, wait, nombre_automatizacion)
        capturar_pantalla(driver, "captura_perfil.png", "El usuario ha seleccionado correctamente el perfil de 'Soporte.", capturas, textos, nombre_automatizacion)

        realizar_login(driver, wait, nombre_automatizacion)
        capturar_pantalla(driver, "captura_login.png", "Inicio de sesión completado correctamente. El usuario ha accedido exitosamente a la plataforma POSWeb.", capturas, textos, nombre_automatizacion)

        generar_pdf(capturas, textos, nombre_automatizacion)

    except (TimeoutException, NoSuchElementException, NoSuchWindowException) as e:
        escribir_log(nombre_automatizacion, f"❌ Error general durante el proceso: {e}")
        logging.error(f"❌ Error general durante el proceso: {e}")
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"❌ Error de webdriver general: {e}")
        logging.error(f"❌ Error de webdriver general: {e}")