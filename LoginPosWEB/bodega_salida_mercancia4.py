"""
Script para automatizar la salida de mercancia a bodega 4
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

# Global variable to store inventory dispatch information
salida_mercancia4_info = {}

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
        escribir_log("salida_mercancia4_pdf", f"Error al resaltar elemento: {e}")
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

def abrir_menu_lateral(driver, wait, nombre_automatizacion):
    try:
        logo = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".logo")))
        resaltar_elemento(driver, logo)
        driver.execute_script("arguments[0].click();", logo)
        escribir_log(nombre_automatizacion, "Menú lateral abierto correctamente.")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al abrir menú lateral: {e}")
        raise

def navegar_a_bodega(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_bodega = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > aside > section > ul > li:nth-child(3) > a")))
        resaltar_elemento(driver, menu_bodega)
        driver.execute_script("arguments[0].click();", menu_bodega)
        escribir_log(nombre_automatizacion, "Accedió a 'Bodega No Disponible Venta' correctamente.")
        tomar_captura(driver, "captura_menu_bodega", "El usuario ha accedido correctamente a 'Bodega No Disponible Venta'.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Bodega No Disponible Venta': {e}")
        raise

def seleccionar_salida_mercancia(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        salida_mercancia = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > aside > section > ul > li.active > ul > li:nth-child(5) > a")))
        resaltar_elemento(driver, salida_mercancia)
        driver.execute_script("arguments[0].click();", salida_mercancia)
        escribir_log(nombre_automatizacion, "Accedió a la opción 'Salida Mercancía' correctamente.")
        tomar_captura(driver, "captura_salida_mercancia", "El usuario ha accedido correctamente a la opción 'Salida Mercancía'.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Salida Mercancía': {e}")
        raise

def clic_crear(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_crear = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.wrapper > div > section:nth-child(1) > div > div:nth-child(2) > a")))
        resaltar_elemento(driver, clic_crear)
        driver.execute_script("arguments[0].click();", clic_crear)
        escribir_log(nombre_automatizacion, "Clic en 'Crear' realizado correctamente.")
        tomar_captura(driver, "captura_clic_crear", "El usuario ha accedido correctamente a la opción 'Crear'.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al hacer clic en 'Crear': {e}")
        raise

def seleccionar_tipo_transaccion(driver, wait, capturas, textos, nombre_automatizacion, tipo_transaccion_index=2):
    try:
        tipo_transaccion = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='IdTipoTransaccion']")))
        resaltar_elemento(driver, tipo_transaccion)
        driver.execute_script("arguments[0].scrollIntoView(true);", tipo_transaccion)
        driver.execute_script("arguments[0].click();", tipo_transaccion)
        time.sleep(0.5)

        select_tipo = Select(tipo_transaccion)
        select_tipo.select_by_index(tipo_transaccion_index)
        
        # ✅ Get the text of the selected option
        texto_opcion = select_tipo.first_selected_option.text
        
        escribir_log(nombre_automatizacion, f"Opción '{texto_opcion}' (índice {tipo_transaccion_index}) seleccionada en 'Tipo de Transacción'.")
        
        # ✅ Save the text to the dictionary
        salida_mercancia4_info["tipo_transaccion"] = texto_opcion
        
        tomar_captura(driver, "captura_tipo_transaccion", f"El usuario ha seleccionado correctamente la opción '{texto_opcion}' en el desplegable de 'Tipo de Transacción'.", capturas, textos, nombre_automatizacion)
        
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Tipo de Transacción': {e}")
        raise

def seleccionar_tipo_causal(driver, wait, capturas, textos, nombre_automatizacion, tipo_causal_index=1):
    try:
        tipo_causal = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='IdCausalConcepto']")))
        resaltar_elemento(driver, tipo_causal)
        select_tipo_causal = Select(tipo_causal)
        select_tipo_causal.select_by_index(tipo_causal_index)
        
        # ✅ Get the text of the selected option
        texto_opcion = select_tipo_causal.first_selected_option.text
        
        escribir_log(nombre_automatizacion, f"Opción '{texto_opcion}' (índice {tipo_causal_index}) seleccionada en 'Tipo de Causal'.")
        
        # ✅ Save the text to the dictionary
        salida_mercancia4_info["tipo_causal"] = texto_opcion
        
        tomar_captura(driver, "captura_tipo_causal", f"El usuario ha seleccionado correctamente la opción '{texto_opcion}' en el desplegable de 'Tipo de Causal'.", capturas, textos, nombre_automatizacion)
        
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Tipo de Causal': {e}")
        raise

def buscar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto="12957"):
    try:
        campo_busqueda = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='NombreProductoBusq']")))
        resaltar_elemento(driver, campo_busqueda)
        campo_busqueda.click()
        campo_busqueda.send_keys(codigo_producto)
        escribir_log(nombre_automatizacion, f"Número de referencia '{codigo_producto}' ingresado correctamente.")
        tomar_captura(driver, "captura_campo_busqueda", "El usuario ha activado y escrito correctamente en el campo de búsqueda de productos.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
        salida_mercancia4_info["codigo_producto"] = codigo_producto
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al buscar producto: {e}")
        raise

def esperar_carga(driver, wait, nombre_automatizacion):
    try:
        WebDriverWait(driver, 60).until(EC.invisibility_of_element_located((By.ID, "loading")))
        WebDriverWait(driver, 60).until(EC.invisibility_of_element_located((By.CLASS_NAME, "swal-overlay")))
        escribir_log(nombre_automatizacion, "Carga completada correctamente.")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Advertencia: Carga no completada completamente, continuando igual.")

def agregar_producto(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        agregar_producto = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='buscarProducto']")))
        resaltar_elemento(driver, agregar_producto)
        escribir_log(nombre_automatizacion, "Producto agregado correctamente.")
        tomar_captura(driver, "captura_agregar_producto", "El usuario ha agregado correctamente el producto.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
        agregar_producto.click()
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al agregar producto: {e}")
        raise

def crear_documento(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        crear_documento = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='enviarSalida']")))
        resaltar_elemento(driver, crear_documento)
        driver.execute_script("arguments[0].click();", crear_documento)
        escribir_log(nombre_automatizacion, "Clic en 'Crear Documento' realizado correctamente.")
        tomar_captura(driver, "captura_crear_documento", "El usuario ha clickeado correctamente en el botón de 'Crear Documento'.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al crear documento: {e}")
        raise

def confirmar_envio(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay.swal-overlay--show-modal > div > div.swal-footer > div > button")))
        resaltar_elemento(driver, clic_ok)
        clic_ok.click()
        escribir_log(nombre_automatizacion, "Envío confirmado correctamente.")
        tomar_captura(driver, "captura_clic_ok", "El usuario ha clickeado correctamente en el botón de 'OK'.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar envío: {e}")
        raise

def salida_mercancia4(driver, codigo_producto="12957", tipo_transaccion_index=2, tipo_causal_index=1):
    """
    Automatiza el proceso de salida de mercancía de bodega en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "salida_mercancia4_pdf"

    try:
        # abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza la salida de mercancía a bodega 4", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_salida_mercancia", "Se inició el proceso de salida de mercancía a bodega.", capturas, textos, nombre_automatizacion)
        
        # navegar_a_bodega(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_salida_mercancia(driver, wait, capturas, textos, nombre_automatizacion)
        clic_crear(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_tipo_transaccion(driver, wait, capturas, textos, nombre_automatizacion, tipo_transaccion_index)
        seleccionar_tipo_causal(driver, wait, capturas, textos, nombre_automatizacion, tipo_causal_index)
        buscar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto)
        esperar_carga(driver, wait, nombre_automatizacion)
        agregar_producto(driver, wait, capturas, textos, nombre_automatizacion)
        esperar_carga(driver, wait, nombre_automatizacion)
        crear_documento(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_envio(driver, wait, capturas, textos, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")

        print(f"Detalles de la salida de mercancía: Código producto: {salida_mercancia4_info.get('codigo_producto', 'No capturado')}, "
              f"Tipo de transacción: {salida_mercancia4_info.get('tipo_transaccion', 'No capturado')}, "
              f"Tipo de causal: {salida_mercancia4_info.get('tipo_causal', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de salida de mercancía: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise