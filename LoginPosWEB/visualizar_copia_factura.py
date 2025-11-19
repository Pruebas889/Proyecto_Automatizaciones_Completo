"""
Script para automatizar la visualización de la copia de factura. 
"""
import time
import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchWindowException,
    WebDriverException,
    StaleElementReferenceException,
)
from generacion_pdf import generar_pdf_consolidado, escribir_log

# Global variable to store invoice information
copia_factura_info = {}

def resaltar_elemento(driver, elemento, color="green", grosor="3px", duracion_ms=1500):
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

def tomar_captura(driver, nombre_archivo, texto, capturas, textos, nombre_automatizacion):
    try:
        time.sleep(0.5)
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

def navegar_a_reportes(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_reportes = wait.until(EC.element_to_be_clickable((By.XPATH, "//aside//a[.//span[normalize-space(text())='Reportes'] and .//i[contains(@class,'fa-bars')]]")))
        resaltar_elemento(driver, menu_reportes)
        driver.execute_script("arguments[0].click();", menu_reportes)
        escribir_log(nombre_automatizacion, "Accedió al menú 'Reportes' correctamente.")
        tomar_captura(driver, "captura_menu_reportes", "Acceso al menú 'Reportes' realizado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Reportes': {e}")
        raise

def navegar_a_facturas(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_facturas = wait.until(EC.element_to_be_clickable((By.XPATH, "//aside//a[contains(@href,'/reportes/facturas') and .//span[normalize-space(text())='Facturas'] and .//i[contains(@class,'fa-usd')]]")))
        resaltar_elemento(driver, menu_facturas)
        driver.execute_script("arguments[0].click();", menu_facturas)
        escribir_log(nombre_automatizacion, "Accedió al módulo 'Facturas' correctamente.")
        tomar_captura(driver, "captura_menu_facturas", "Acceso al módulo 'Facturas' realizado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Facturas': {e}")
        raise

def seleccionar_opcion_imprimir(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_imprimir = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/section[1]/div/div[2]/a")))
        resaltar_elemento(driver, boton_imprimir)
        driver.execute_script("arguments[0].click();", boton_imprimir)
        escribir_log(nombre_automatizacion, "Seleccionó la opción 'Imprimir' correctamente.")
        tomar_captura(driver, "captura_imprimir", "Opción 'Imprimir' seleccionada correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar opción 'Imprimir': {e}")
        raise

def ingresar_numero_factura(driver, wait, capturas, textos, nombre_automatizacion, numero_factura="18758"):
    try:
        campo_factura = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='factura']")))
        resaltar_elemento(driver, campo_factura)
        driver.execute_script("arguments[0].click();", campo_factura)
        campo_factura.send_keys(numero_factura)
        escribir_log(nombre_automatizacion, f"Número de factura {numero_factura} ingresado correctamente.")
        tomar_captura(driver, "captura_numero_factura", f"Campo para ingresar número de factura {numero_factura} seleccionado correctamente.", capturas, textos, nombre_automatizacion)
        copia_factura_info["numero_factura"] = numero_factura
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar número de factura: {e}")
        raise

def consultar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_consultar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='impresion-factura']/button[2]")))
        resaltar_elemento(driver, boton_consultar)
        driver.execute_script("arguments[0].click();", boton_consultar)
        escribir_log(nombre_automatizacion, "Consulta de factura realizada correctamente.")
        tomar_captura(driver, "captura_consulta", "Consulta de factura realizada correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al consultar factura: {e}")
        raise

def visualizar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        visualizar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='tabla-respuestas']/tbody/tr/td[6]/a")))
        resaltar_elemento(driver, visualizar)
        driver.execute_script("arguments[0].click();", visualizar)
        escribir_log(nombre_automatizacion, "Factura visualizada correctamente.")
        WebDriverWait(driver, 40).until(EC.invisibility_of_element_located((By.ID, "loading")))
        WebDriverWait(driver, 40).until(EC.invisibility_of_element_located((By.CLASS_NAME, "swal-overlay")))
        tomar_captura(driver, "captura_visualizar", "Factura visualizada correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al visualizar factura: {e}")
        raise

def cerrar_modal_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_cerrar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='pdfModal']/div/div/div[3]/button")))
        resaltar_elemento(driver, clic_cerrar)
        driver.execute_script("arguments[0].click();", clic_cerrar)
        escribir_log(nombre_automatizacion, "Modal de factura cerrado correctamente.")
        time.sleep(1)
        tomar_captura(driver, "captura_cerrar_modal", "Modal cerrado correctamente después de visualizar la factura.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al cerrar modal de factura: {e}")
        raise

def copia_factura(driver, numero_factura="18758"):
    """
    Automatiza el proceso de visualización de la copia de una factura en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "visualizar_copia_factura_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza la Visualización de Copia de la Factura", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_copia_factura", "Se inició el proceso de visualización de copia de factura correctamente.", capturas, textos, nombre_automatizacion)
        
        navegar_a_reportes(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_facturas(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_opcion_imprimir(driver, wait, capturas, textos, nombre_automatizacion)
        ingresar_numero_factura(driver, wait, capturas, textos, nombre_automatizacion, numero_factura)
        consultar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        visualizar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        cerrar_modal_factura(driver, wait, capturas, textos, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Número de factura visualizada: {copia_factura_info.get('numero_factura', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de visualización de copia de factura: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise