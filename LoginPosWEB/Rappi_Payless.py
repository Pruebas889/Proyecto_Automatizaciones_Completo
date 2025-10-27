import time
import os
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchWindowException,
    WebDriverException,
    StaleElementReferenceException,
)
from generacion_pdf import generar_pdf_consolidado, escribir_log

Rappi_Payless_info = {}

def resaltar_elemento(driver, elemento, color="green", grosor="4px", duracion_ms=2000):
    try:
        driver.execute_script(
            f"""
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
            """,
            elemento,
        )
    except WebDriverException as e:
        logging.error(f"Error al resaltar elemento: {e}")
        raise

def mostrar_mensaje(driver, mensaje, nombre_automatizacion):
    try:
        driver.execute_script(
            f"""
            if (document.body) {{
                var div = document.createElement('div');
                div.innerHTML = '{mensaje}';
                div.style.position = 'fixed';
                div.style.top = '10px';
                div.style.right = '10px';
                div.style.backgroundColor = 'yellow';
                div.style.padding = '10px';
                div.style.fontSize = '20px';
                div.style.zIndex = '9999';
                div.id = 'mensaje_login';
                document.body.appendChild(div);
                setTimeout(function(){{ document.body.removeChild(div); }}, 2000);
            }} else {{
                console.log('Error: document.body is null');
            }}
            """
        )
        escribir_log(nombre_automatizacion, f"Mensaje mostrado: {mensaje}")
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error al mostrar mensaje: {e}")
        raise

def tomar_captura(driver, nombre_archivo, texto, capturas, textos, nombre_automatizacion):
    try:
        time.sleep(0.7)
        # Asegurarse de que la carpeta existe
        carpeta_capturas = "capturas"
        os.makedirs(carpeta_capturas, exist_ok=True)
        ruta_captura = os.path.join(carpeta_capturas, f"{nombre_archivo}.png")
        driver.save_screenshot(ruta_captura)
        capturas.append(ruta_captura)
        textos.append(texto)
        # escribir_log(nombre_automatizacion, f"Captura tomada: {ruta_captura}") 
        # Agregar el texto a la lista de textos con nombre de captura
        time.sleep(1)
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error al tomar captura {nombre_archivo}: {e}")
        raise

def esperar_carga_desaparezca(driver, wait, nombre_automatizacion, contexto):
    try:
        escribir_log(nombre_automatizacion, f"Esperando a que desaparezca el gif de carga tras {contexto}.")
        WebDriverWait(driver, 60).until(EC.invisibility_of_element_located((By.ID, "loading")))
        WebDriverWait(driver, 60).until(EC.invisibility_of_element_located((By.CLASS_NAME, "swal-overlay")))
        escribir_log(nombre_automatizacion, f"Carga y overlay desaparecidos tras {contexto}.")
    except TimeoutException:
        escribir_log(nombre_automatizacion, f"Advertencia: Carga o overlay no desaparecieron tras {contexto}, continuando.")

def abrir_menu_lateral(driver, wait, nombre_automatizacion):
    try:
        logo = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".logo")))
        resaltar_elemento(driver, logo)
        driver.execute_script("arguments[0].click();", logo)
        escribir_log(nombre_automatizacion, "Menú lateral abierto correctamente.")
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al abrir menú lateral: {e}")
        raise

def navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_cajero = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > aside > section > ul > li:nth-child(4) > a")))
        resaltar_elemento(driver, menu_cajero)
        escribir_log(nombre_automatizacion, "Accediendo al menú 'Cajero'.")
        tomar_captura(driver, "captura_menu_cajero", "Acceso al menú 'Cajero' realizado correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", menu_cajero)
        escribir_log(nombre_automatizacion, "Accedió al menú 'Cajero' correctamente.")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Cajero': {e}")
        raise

def navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_ventas = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class, 'active')]//ul//li[1]//a")))
        resaltar_elemento(driver, menu_ventas)
        escribir_log(nombre_automatizacion, "Accedió a 'Ventas' correctamente.")
        tomar_captura(driver, "captura_menu_ventas", "Se accedió correctamente al botón 'Ventas'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", menu_ventas)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Ventas': {e}")
        raise

def navegar_a_Rappi(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_Rappi = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/section[1]/div/div[8]/a")))
        resaltar_elemento(driver, menu_Rappi)
        escribir_log(nombre_automatizacion, "Accedió a 'Rappi' correctamente.")
        tomar_captura(driver, "captura_menu_Rappi", "Se accedió correctamente al botón 'Rappi'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", menu_Rappi)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Rappi': {e}")
        raise

def iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # Esperar hasta 60s para el botón 'Iniciar Factura'
        iniciar_factura_btn = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnIniciarFactura']"))
        )
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "acceder a facturar")
        resaltar_elemento(driver, iniciar_factura_btn)
        escribir_log(nombre_automatizacion, "Accedió a 'Iniciar Factura' correctamente.")
        tomar_captura(driver, "captura_iniciar_factura", "Inicio de factura realizado correctamente.", capturas, textos, nombre_automatizacion)

        driver.execute_script("arguments[0].click();", iniciar_factura_btn)

    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al iniciar factura: {e}")
        raise

def ingresar_No_Transaccion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_No_Transaccion = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnNumeroTransaccionRappiFactura']")))
        resaltar_elemento(driver, menu_No_Transaccion)
        escribir_log(nombre_automatizacion, "Accedió a 'No Transacción' correctamente.")
        tomar_captura(driver, "captura_menu_No_Transaccion", "Se accedió correctamente al botón 'No Transacción'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", menu_No_Transaccion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'No Transacción': {e}")
        raise

def ingresar_numero_transaccion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        numero_transaccion = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='NumeroTransaccionRappi']")))
        resaltar_elemento(driver, numero_transaccion)
        numero_transaccion.send_keys("123456789")
        escribir_log(nombre_automatizacion, "Número de transacción ingresado: 123456789")
        time.sleep(0.7)
        tomar_captura(driver, "captura_numero_transaccion_ingresado", "Número de transacción ingresado correctamente: 123456789.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", numero_transaccion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar número de transacción: {e}")
        raise

def confirmar_numero_transaccion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        numero_transaccion = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='NumeroTransaccionRappi2']")))
        resaltar_elemento(driver, numero_transaccion)
        driver.execute_script("arguments[0].click();", numero_transaccion)
        numero_transaccion.clear()
        numero_transaccion.send_keys("123456789")
        escribir_log(nombre_automatizacion, "Confirmar número de transacción '123456789' ingresado correctamente.")
        Rappi_Payless_info["numero_transaccion"] = "123456789"
        time.sleep(0.7)
        tomar_captura(driver, "captura_numero_transaccion_confirmado", "Confirmar número de transacción ingresado correctamente: 123456789.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar número de transacción: {e}")
        raise

def Pulsar_boton_asignar(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        Boton_Asignar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='FormTransaccionRappi']/div[3]/button")))
        resaltar_elemento(driver, Boton_Asignar)
        escribir_log(nombre_automatizacion, "Accedió al botón 'Asignar' correctamente.")
        tomar_captura(driver, "captura_boton_asignar", "Se accedió correctamente al botón 'Asignar'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", Boton_Asignar)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Asignar': {e}")
        raise

def Modal_existente(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        existe = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='FormTransaccionRappi']/div[3]/button")))
        resaltar_elemento(driver, existe)
        escribir_log(nombre_automatizacion, "Accedió al botón 'Asignar' correctamente.")
        tomar_captura(driver, "captura_modal_existente", "Se accedió correctamente al modal existente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", existe)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Asignar': {e}")
        raise


def rappi_payless(driver):
    
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "Rappi_Payless_pdf"

    try:
        Rappi_Payless_info["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se inició el proceso de RappiPayless.", nombre_automatizacion)
        time.sleep(1)
        tomar_captura(driver, "cajero_ventas", "Se inició el proceso de RappiPayless.", capturas, textos, nombre_automatizacion)
        navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_Rappi(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        ingresar_No_Transaccion(driver, wait, capturas, textos, nombre_automatizacion)
        ingresar_numero_transaccion(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_numero_transaccion(driver, wait, capturas, textos, nombre_automatizacion)
        # Pulsar el botón Asignar
        Pulsar_boton_asignar(driver, wait, capturas, textos, nombre_automatizacion)
        # Esperar el modal de error tipo swal-modal
        try:
            modal_error = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "swal-modal")))
            resaltar_elemento(driver, modal_error)
            tomar_captura(driver, "captura_modal_error_existente", "Modal de error: Ya existe una factura con el mismo Número de transacción.", capturas, textos, nombre_automatizacion)
        except Exception as e:
            escribir_log(nombre_automatizacion, f"No se encontró el modal de error swal-modal: {e}")
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles de Rappi Payless: Timestamp: {Rappi_Payless_info.get('timestamp', 'No capturado')}")
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de venta con Rappi Payless: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise
