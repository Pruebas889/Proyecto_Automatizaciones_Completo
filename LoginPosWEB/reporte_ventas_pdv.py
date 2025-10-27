"""
Script para automatizar el reporte de ventas por PDV
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

# Global variable to store report information
reporte_pdv_info = {}

def resaltar_elemento(driver, elemento, color="green", grosor="3px", duracion_ms=2000):
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

def navegar_a_reportes(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_reportes = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/aside/section/ul/li[8]/a")))
        resaltar_elemento(driver, menu_reportes)
        escribir_log(nombre_automatizacion, "Accedió al módulo 'Reportes' correctamente.")
        tomar_captura(driver, "captura_menu_reportes", "Acceso al módulo 'Reportes' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", menu_reportes)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Reportes': {e}")
        raise

def navegar_a_reporte_ventas(driver, capturas, textos, wait, nombre_automatizacion):
    try:
        reporte_ventas = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/aside/section/ul/li[8]/ul/li[11]/a")))
        resaltar_elemento(driver, reporte_ventas)
        driver.execute_script("arguments[0].click();", reporte_ventas)
        escribir_log(nombre_automatizacion, "Accedió al reporte de ventas correctamente.")
        tomar_captura(driver, "captura_menu_reportes", "Acceso al módulo 'Reportes Ventas' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
        driver.execute_script("arguments[0].scrollIntoView(true);", reporte_ventas)
        time.sleep(10)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Reporte Ventas': {e}")
        raise

def revision_elemento(wait, nombre_automatizacion):
    try:
        try:
            time.sleep(0.5)
            wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/section[3]/div[9]/div/div[2]")))
        except TimeoutException:
            pass
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="DataTables_Table_0"]')))
        except TimeoutException:
            logging.error("No se encontró el elemento")
            raise
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al revisar el reporte de ventas: {e}")
        raise

def reporte_pdv(driver):
    """
    Automatiza el proceso de generación del reporte de ventas por PDV en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 40)
    capturas = []
    textos = []
    nombre_automatizacion = "reporte_ventas_pdv_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza el reporte por PDV", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_reporte_pdv", "Se inició el proceso de reporte de las ventas por PDV correctamente.", capturas, textos, nombre_automatizacion)
        
        navegar_a_reportes(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_reporte_ventas(driver, capturas, textos, wait, nombre_automatizacion)
        revision_elemento(wait, nombre_automatizacion)
        tomar_captura(driver, "captura_reporte_ventas", "Acceso al reporte de ventas realizado correctamente.", capturas, textos, nombre_automatizacion)

        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        reporte_pdv_info["reporte_tipo"] = "Ventas por PDV"
        print(f"Detalles del reporte: Tipo: {reporte_pdv_info.get('reporte_tipo', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de reporte de ventas por PDV: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise