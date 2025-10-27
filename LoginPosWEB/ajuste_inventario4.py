"""
Script para automatizar el ajuste de inventario 4.
"""
import time
import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchWindowException,
    WebDriverException,
    StaleElementReferenceException,
)
from generacion_pdf import generar_pdf_consolidado, escribir_log

# Global variable to store inventory adjustment information
ajuste_inventario4_info = {}

def resaltar_elemento(driver, elemento, color="green", grosor="4px", duracion_ms=1000):
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

def navegar_a_ajuste_inventario(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_ajuste_inventario = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/aside/section/ul/li[2]/ul/li[4]/a")))
        resaltar_elemento(driver, menu_ajuste_inventario)
        driver.execute_script("arguments[0].click();", menu_ajuste_inventario)
        escribir_log(nombre_automatizacion, "Accedió a 'Ajuste de inventario' correctamente.")
        tomar_captura(driver, "captura_menu_ajuste_inventario", "Acceso a 'Ajuste de inventario' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Ajuste de inventario': {e}")
        raise

def seleccionar_opcion_ajuste(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_ajuste = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div/section[1]/div/div[2]/a")))
        resaltar_elemento(driver, clic_ajuste)
        driver.execute_script("arguments[0].click();", clic_ajuste)
        escribir_log(nombre_automatizacion, "Accedió a la sección 'Ajuste' correctamente.")
        tomar_captura(driver, "captura_ajuste", "Acceso a la sección 'Ajuste' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar opción 'Ajuste': {e}")
        raise

def ingresar_referencia_producto(driver, wait, capturas, textos, nombre_automatizacion, referencia="12957"):
    try:
        buscar_referencia = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='NombreProductoBusq']")))
        resaltar_elemento(driver, buscar_referencia)
        driver.execute_script("arguments[0].click();", buscar_referencia)
        buscar_referencia.send_keys(referencia, Keys.RETURN)
        escribir_log(nombre_automatizacion, f"Referencia de producto {referencia} ingresada correctamente.")
        tomar_captura(driver, "captura_referencia", f"Referencia de producto {referencia} ingresada correctamente.", capturas, textos, nombre_automatizacion)
        ajuste_inventario4_info["referencia_producto"] = referencia
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar referencia de producto: {e}")
        raise

def seleccionar_tipo_transaccion(driver, wait, capturas, textos, nombre_automatizacion, tipo_transaccion="A+"):
    try:
        tipo_transaccion_element = wait.until(EC.presence_of_element_located((By.ID, "tipoTransaccion-12957-0")))
        resaltar_elemento(driver, tipo_transaccion_element)
        select = Select(tipo_transaccion_element)
        select.select_by_value(tipo_transaccion)
        escribir_log(nombre_automatizacion, f"Tipo de transacción '{tipo_transaccion}' seleccionado correctamente.")
        tomar_captura(driver, "captura_tipo_transaccion", f"Tipo de transacción '{tipo_transaccion}' seleccionado correctamente.", capturas, textos, nombre_automatizacion)
        ajuste_inventario4_info["tipo_transaccion"] = tipo_transaccion
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar tipo de transacción: {e}")
        raise

def seleccionar_causal_transaccion(driver, wait, capturas, textos, nombre_automatizacion, causal_index=4):
    try:
        causal_transaccion = wait.until(EC.presence_of_element_located((By.ID, "causalTransaccion-12957-0")))
        resaltar_elemento(driver, causal_transaccion)
        select = Select(causal_transaccion)
        select.select_by_index(causal_index)
        escribir_log(nombre_automatizacion, f"Causal de transacción (índice {causal_index}) seleccionada correctamente.")
        tomar_captura(driver, "captura_causal_transaccion", f"Causal de transacción (índice {causal_index}) seleccionada correctamente.", capturas, textos, nombre_automatizacion)
        ajuste_inventario4_info["causal_transaccion"] = f"Índice {causal_index}"
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar causal de transacción: {e}")
        raise

def ingresar_cantidad_unidades(driver, wait, capturas, textos, nombre_automatizacion, unidades="1"):
    try:
        unidad_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='unidades-12957-0']")))
        driver.execute_script("arguments[0].click();", unidad_input)
        unidad_input.send_keys(Keys.CONTROL, "a")
        unidad_input.send_keys(Keys.DELETE)
        unidad_input.send_keys(unidades)
        unidad_input.send_keys(Keys.ENTER)
        escribir_log(nombre_automatizacion, f"Cantidad de unidades {unidades} ajustada correctamente.")
        resaltar_elemento(driver, unidad_input)
        time.sleep(0.5)
        tomar_captura(driver, "captura_cantidad_unidades", f"Cantidad de unidades ajustada correctamente: {unidades}.", capturas, textos, nombre_automatizacion)
        ajuste_inventario4_info["cantidad_unidades"] = unidades
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar cantidad de unidades: {e}")
        raise

def realizar_ajuste(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        realizar_ajuste = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='realizarAjuste']")))
        resaltar_elemento(driver, realizar_ajuste)
        driver.execute_script("arguments[0].click();", realizar_ajuste)
        escribir_log(nombre_automatizacion, "Ajuste realizado correctamente.")
        tomar_captura(driver, "captura_realizar_ajuste", "Ajuste realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al realizar ajuste: {e}")
        raise

def confirmar_ajuste(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_si = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay.swal-overlay--show-modal > div > div.swal-footer > div:nth-child(2) > button")))
        resaltar_elemento(driver, clic_si)
        driver.execute_script("arguments[0].click();", clic_si)
        escribir_log(nombre_automatizacion, "Confirmación del ajuste realizada correctamente.")
        tomar_captura(driver, "captura_confirmacion_si", "Confirmación del ajuste realizada correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar ajuste: {e}")
        raise

def inventario4(driver, referencia="12957", tipo_transaccion="A+", causal_index=4, unidades="1"):
    """
    Automatiza el proceso de ajuste de inventario4 en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 40)
    capturas = []
    textos = []
    nombre_automatizacion = "ajuste_inventario4_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza el ajuste de inventario 4", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_ajuste_inventario", "Se inició el proceso de ajuste de inventario 4 correctamente.", capturas, textos, nombre_automatizacion)
        
        navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_ajuste_inventario(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_opcion_ajuste(driver, wait, capturas, textos, nombre_automatizacion)
        ingresar_referencia_producto(driver, wait, capturas, textos, nombre_automatizacion, referencia)
        seleccionar_tipo_transaccion(driver, wait, capturas, textos, nombre_automatizacion, tipo_transaccion)
        seleccionar_causal_transaccion(driver, wait, capturas, textos, nombre_automatizacion, causal_index)
        ingresar_cantidad_unidades(driver, wait, capturas, textos, nombre_automatizacion, unidades)
        realizar_ajuste(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_ajuste(driver, wait, capturas, textos, nombre_automatizacion)
        tomar_captura(driver, "captura_confirmacion_final", "Ajuste realizado correctamente.", capturas, textos, nombre_automatizacion)

        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles del ajuste: Referencia producto: {ajuste_inventario4_info.get('referencia_producto', 'No capturado')}, "
              f"Tipo transacción: {ajuste_inventario4_info.get('tipo_transaccion', 'No capturado')}, "
              f"Causal transacción: {ajuste_inventario4_info.get('causal_transaccion', 'No capturado')}, "
              f"unidades: {ajuste_inventario4_info.get('cantidad_unidades', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de ajuste de inventario4: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise