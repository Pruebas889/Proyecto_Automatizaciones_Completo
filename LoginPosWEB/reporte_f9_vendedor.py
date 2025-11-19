"""
Script para automatizar el reporte de ventas de la tecla F9 por vendedor.
"""
import time
import os
import logging
from datetime import datetime
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
reporte_f9_vendedor_info = {}

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
        escribir_log("reporte_f9_vendedor_pdf", f"Error al resaltar elemento: {e}")
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
        xpath_menu_reportes = "//aside//a[.//span[normalize-space(text())='Reportes'] and .//i[contains(@class,'fa-bars')]]"
        menu_reportes = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_menu_reportes)))
        resaltar_elemento(driver, menu_reportes)
        driver.execute_script("arguments[0].click();", menu_reportes)
        escribir_log(nombre_automatizacion, "Accedió al menú 'Reportes' correctamente.")
        tomar_captura(driver, "captura_menu_reportes", "Acceso al menú 'Reportes' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Reportes': {e}")
        raise

def seleccionar_reporte_f9(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        xpath_menu_reporte_f9 = "//aside//a[contains(@href,'/reportes/reporte-f9/generar') and .//span[normalize-space(text())='Reporte F9'] and .//i[contains(@class,'fa-usd')]]"
        menu_reporte_f9 = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_menu_reporte_f9)))
        resaltar_elemento(driver, menu_reporte_f9)
        driver.execute_script("arguments[0].click();", menu_reporte_f9)
        escribir_log(nombre_automatizacion, "Accedió a 'Reporte F9' correctamente.")
        tomar_captura(driver, "captura_menu_reporte_f9", "Acceso al módulo 'Reporte F9' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Reporte F9': {e}")
        raise

def seleccionar_por_vendedor(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        elemento_por_vendedor = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='TipoConsulta'][value='2']")))
        resaltar_elemento(driver, elemento_por_vendedor)
        driver.execute_script("arguments[0].click();", elemento_por_vendedor)
        escribir_log(nombre_automatizacion, "Opción 'Por Vendedor' seleccionada correctamente.")
        tomar_captura(driver, "captura_opcion_por_vendedor", "Hizo clic en 'Por Vendedor' realizado correctamente.", capturas, textos, nombre_automatizacion)
        reporte_f9_vendedor_info["filtro"] = "Por Vendedor"
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Por Vendedor': {e}")
        raise

def generar_reporte(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_buscar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='buscarPorFecha']")))
        resaltar_elemento(driver, clic_buscar)
        driver.execute_script("arguments[0].click();", clic_buscar)
        escribir_log(nombre_automatizacion, "Clic en 'Buscar' realizado correctamente.")
        tomar_captura(driver, "captura_boton_buscar", "Acceso al módulo 'Buscar' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)  # Allow report to load
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al generar reporte: {e}")
        raise

def reportes_f9_vendedor(driver):
    """
    Automatiza el proceso de generación del reporte de facturación con tecla F9 por vendedor, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "reporte_f9_vendedor_pdf"

    try:
        reporte_f9_vendedor_info["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza el reporte de facturación con tecla F9 por medio de vendedor", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_reporte_f9_vendedor", "Se inició el proceso de reporte de facturación con la tecla F9 por medio de vendedor correctamente.", capturas, textos, nombre_automatizacion)
        
        navegar_a_reportes(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_reporte_f9(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_por_vendedor(driver, wait, capturas, textos, nombre_automatizacion)
        generar_reporte(driver, wait, capturas, textos, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles del reporte F9 por vendedor: Timestamp: {reporte_f9_vendedor_info.get('timestamp', 'No capturado')}, "
              f"Filtro: {reporte_f9_vendedor_info.get('filtro', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de reporte de facturación con F9 por vendedor: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise