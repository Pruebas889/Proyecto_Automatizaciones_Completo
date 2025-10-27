"""
Script para automatizar los gastos
"""
import time
import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchWindowException,
    WebDriverException,
    StaleElementReferenceException,
)
from generacion_pdf import generar_pdf_consolidado, escribir_log

# Global variable to store expense information
control_gastos_info = {}

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

def navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_administrador = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.wrapper > aside > section > ul > li:nth-child(2) > a")))
        resaltar_elemento(driver, menu_administrador)
        driver.execute_script("arguments[0].click();", menu_administrador)
        escribir_log(nombre_automatizacion, "Accedió al menú 'Administrador' correctamente.")
        tomar_captura(driver, "captura_menu_admin", "Acceso al menú 'Administrador' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Administrador': {e}")
        raise

def navegar_a_gastos(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        gastos = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/aside/section/ul/li[2]/ul/li[8]/a")))
        resaltar_elemento(driver, gastos)
        driver.execute_script("arguments[0].click();", gastos)
        escribir_log(nombre_automatizacion, "Accedió al módulo 'Gastos' correctamente.")
        tomar_captura(driver, "captura_gastos", "Acceso al módulo 'Gastos' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Gastos': {e}")
        raise

def seleccionar_categoria_gasto(driver, wait, capturas, textos, nombre_automatizacion, categoria_index=2):
    try:
        categoria = wait.until(EC.presence_of_element_located((By.ID, "tgasto-idgastopadre")))
        resaltar_elemento(driver, categoria)
        select = Select(categoria)
        select.select_by_index(categoria_index)
        escribir_log(nombre_automatizacion, f"Categoría de gasto (índice {categoria_index}) seleccionada correctamente.")
        tomar_captura(driver, "captura_categoria", f"Categoría de gasto (índice {categoria_index}) seleccionada correctamente.", capturas, textos, nombre_automatizacion)
        control_gastos_info["categoria_index"] = categoria_index
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar categoría de gasto: {e}")
        raise

def seleccionar_nombre_gasto(driver, wait, capturas, textos, nombre_automatizacion, nombre_gasto_index=1):
    try:
        nombre_gasto = wait.until(EC.presence_of_element_located((By.ID, "tgasto-idgastohijo")))
        resaltar_elemento(driver, nombre_gasto)
        select = Select(nombre_gasto)
        select.select_by_index(nombre_gasto_index)
        escribir_log(nombre_automatizacion, f"Nombre del gasto (índice {nombre_gasto_index}) seleccionado correctamente.")
        tomar_captura(driver, "captura_nombre_gasto", f"Nombre del gasto (índice {nombre_gasto_index}) seleccionado correctamente.", capturas, textos, nombre_automatizacion)
        control_gastos_info["nombre_gasto_index"] = nombre_gasto_index
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar nombre del gasto: {e}")
        raise

def ingresar_valor_gasto(driver, wait, capturas, textos, nombre_automatizacion, valor="30000"):
    try:
        valor_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='tgasto-valor']")))
        resaltar_elemento(driver, valor_input)
        driver.execute_script("arguments[0].click();", valor_input)
        valor_input.send_keys(valor)
        escribir_log(nombre_automatizacion, f"Valor del gasto {valor} ingresado correctamente.")
        tomar_captura(driver, "captura_valor", f"Valor del gasto ingresado correctamente: {valor}.", capturas, textos, nombre_automatizacion)
        control_gastos_info["valor"] = valor
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar valor del gasto: {e}")
        raise

def ingresar_observacion_gasto(driver, wait, capturas, textos, nombre_automatizacion, observacion="prueba"):
    try:
        observacion_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='tgasto-observacion']")))
        resaltar_elemento(driver, observacion_input)
        driver.execute_script("arguments[0].click();", observacion_input)
        observacion_input.send_keys(observacion)
        escribir_log(nombre_automatizacion, f"Observación del gasto '{observacion}' ingresada correctamente.")
        tomar_captura(driver, "captura_observacion", f"Observación del gasto '{observacion}' ingresada correctamente.", capturas, textos, nombre_automatizacion)
        control_gastos_info["observacion"] = observacion
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar observación del gasto: {e}")
        raise

def ingresar_gasto(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        ingresar_gasto = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='ingresar']")))
        resaltar_elemento(driver, ingresar_gasto)
        driver.execute_script("arguments[0].click();", ingresar_gasto)
        escribir_log(nombre_automatizacion, "Gasto ingresado correctamente.")
        tomar_captura(driver, "captura_ingresar_gasto", "Gasto ingresado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar gasto: {e}")
        raise

def confirmar_gasto(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_si = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay.swal-overlay--show-modal > div > div.swal-footer > div:nth-child(2) > button")))
        resaltar_elemento(driver, clic_si)
        driver.execute_script("arguments[0].click();", clic_si)
        escribir_log(nombre_automatizacion, "Confirmación del gasto realizada correctamente.")
        tomar_captura(driver, "captura_confirmacion_si", "Confirmación del gasto realizada correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar gasto: {e}")
        raise

def control_gastos(driver, categoria_index=2, nombre_gasto_index=1, valor="30000", observacion="prueba"):
    """
    Automatiza el proceso de gestión de gastos en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 40)
    capturas = []
    textos = []
    nombre_automatizacion = "gestion_gastos_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza el ingreso de gastos", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_gestion_gastos", "Se inició el proceso de gestión de control de gastos correctamente.", capturas, textos, nombre_automatizacion)
        
        navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_gastos(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_categoria_gasto(driver, wait, capturas, textos, nombre_automatizacion, categoria_index)
        seleccionar_nombre_gasto(driver, wait, capturas, textos, nombre_automatizacion, nombre_gasto_index)
        ingresar_valor_gasto(driver, wait, capturas, textos, nombre_automatizacion, valor)
        ingresar_observacion_gasto(driver, wait, capturas, textos, nombre_automatizacion, observacion)
        ingresar_gasto(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_gasto(driver, wait, capturas, textos, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles del gasto: Categoría (índice): {control_gastos_info.get('categoria_index', 'No capturado')}, "
              f"Nombre del gasto (índice): {control_gastos_info.get('nombre_gasto_index', 'No capturado')}, "
              f"Valor: {control_gastos_info.get('valor', 'No capturado')}, "
              f"Observación: {control_gastos_info.get('observacion', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de gestión de gastos: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise