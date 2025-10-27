"""
Script para automatizar el logout, guardando logs y ejecutándose en Firefox
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException
from generacion_pdf import generar_pdf_consolidado, escribir_log  # Generador de PDF y logger

def resaltar_elemento(driver, elemento, color="red", grosor="5px", duracion_ms=1000):
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
    """Muestra un mensaje en pantalla indicando el inicio del cierre de sesión."""
    try:
        driver.execute_script("""
            if (document.body) {
                var div = document.createElement('div');
                div.innerHTML = 'Se realiza el cierre de sesión';
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
        driver.execute_script("document.getElementById('mensaje_login').style.display='none';")
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error al ejecutar el script de mensaje: {e}")
        raise

def capturar_pantalla(driver, ruta, texto, capturas, textos, nombre_automatizacion):
    """Toma una captura de pantalla y la agrega a las listas correspondientes."""
    try:
        driver.save_screenshot(ruta)
        capturas.append(ruta)
        textos.append(texto)
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error al tomar la captura {ruta}: {e}")
        raise

def localizar_logout(driver, wait, nombre_automatizacion):
    """Localiza y resalta el botón de logout."""
    try:
        logout = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/header/nav/div/ul/li[6]/a")))
        resaltar_elemento(driver, logout)
        escribir_log(nombre_automatizacion, "Se hizo clic en el botón del logo de 'POSWEB' correctamente.")
        time.sleep(0.5)
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: Tiempo excedido al localizar el botón de logout.")
        raise
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el botón de logout.")
        raise
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error de webdriver al localizar logout: {e}")
        raise

def realizar_logout(driver, wait, nombre_automatizacion):
    """Realiza el clic en el botón de logout."""
    try:
        logout = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/header/nav/div/ul/li[6]/a")))
        logout.click()
        escribir_log(nombre_automatizacion, "Se hizo clic en el botón de 'Logout' correctamente.")
        time.sleep(2)
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: Tiempo excedido al hacer clic en el botón de logout.")
        raise
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el botón de logout para hacer clic.")
        raise
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error de webdriver al realizar logout: {e}")
        raise

def generar_pdf(capturas, textos, nombre_automatizacion):
    """Genera un PDF consolidado con las capturas y textos."""
    try:
        generar_pdf_consolidado("logout_usuario_soporte_pdf", capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al generar el PDF consolidado: {e}")
        raise

def logout_posweb(driver):
    """
    Realiza el logout en POSWeb, guardando evidencia en un PDF consolidado.
    """
    wait = WebDriverWait(driver, 20)
    capturas = []
    textos = []
    nombre_automatizacion = "logout_usuario_soporte_pdf"

    try:
        mostrar_mensaje_inicio(driver, nombre_automatizacion)
        capturar_pantalla(driver, "capturas/logout.png", "Se inició el proceso de cierre de sesión correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)

        localizar_logout(driver, wait, nombre_automatizacion)
        capturar_pantalla(driver, "capturas/captura_logout.png", "El botón de logout está resaltado y listo para ser presionado.", capturas, textos, nombre_automatizacion)
        time.sleep(1)

        realizar_logout(driver, wait, nombre_automatizacion)
        capturar_pantalla(driver, "capturas/captura_logout_final.png", "Logout completado exitosamente, se redirigió al usuario.", capturas, textos, nombre_automatizacion)
        time.sleep(1)

        generar_pdf(capturas, textos, nombre_automatizacion)

    except (TimeoutException, NoSuchElementException, NoSuchWindowException) as e:
        logging.error(f"❌ Error durante el proceso: {e}")
    except WebDriverException as e:
        logging.error(f"❌ Error de webdriver: {e}")
