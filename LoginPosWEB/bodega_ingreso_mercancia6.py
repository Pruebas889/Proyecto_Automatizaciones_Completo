"""
Script para automatizar el ingreso de mercancia a bodega 6
"""
import os
import time
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

# Global variable to store inventory receipt information
ingreso_mercancia6_info = {}

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
        escribir_log("ingreso_mercancia6_pdf", f"Error al resaltar elemento: {e}")
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

def navegar_a_bodega(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_bodega = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > aside > section > ul > li:nth-child(3) > a")))
        resaltar_elemento(driver, menu_bodega)
        driver.execute_script("arguments[0].click();", menu_bodega)
        escribir_log(nombre_automatizacion, "Accedió a 'Bodega No Disponible Venta' correctamente.")
        tomar_captura(driver, "captura_menu_bodega", "El usuario ha accedido correctamente a 'Bodega No Disponible Venta'.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Bodega No Disponible Venta': {e}")
        raise

def seleccionar_ingresar_mercancia(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        ingresar_mercancia = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > aside > section > ul > li.active > ul > li:nth-child(2) > a")))
        resaltar_elemento(driver, ingresar_mercancia)
        driver.execute_script("arguments[0].click();", ingresar_mercancia)
        escribir_log(nombre_automatizacion, "Accedió a la opción 'Ingresar Mercancía' correctamente.")
        tomar_captura(driver, "captura_ingreso_mercancia", "El usuario ha accedido correctamente a la opción 'Ingresar Mercancía'.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Ingresar Mercancía': {e}")
        raise

def buscar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto="12957"):
    try:
        campo_busqueda = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='NombreProductoBusq']")))
        resaltar_elemento(driver, campo_busqueda)
        campo_busqueda.click()
        campo_busqueda.send_keys(codigo_producto)
        escribir_log(nombre_automatizacion, f"Número de referencia '{codigo_producto}' ingresado correctamente.")
        tomar_captura(driver, "captura_campo_busqueda", "El usuario ha activado correctamente el campo de búsqueda de productos.", capturas, textos, nombre_automatizacion)
        time.sleep(1)  # Allow list to load
        campo_busqueda.send_keys(Keys.ARROW_DOWN)
        escribir_log(nombre_automatizacion, "Opción seleccionada en el menú desplegable.")
        tomar_captura(driver, "captura_opcion_seleccionada", "El usuario ha seleccionado correctamente la opción en el menú desplegable.", capturas, textos, nombre_automatizacion)
        campo_busqueda.send_keys(Keys.RETURN)
        escribir_log(nombre_automatizacion, "Selección del producto confirmada.")
        tomar_captura(driver, "captura_confirmacion_seleccion", "El usuario ha confirmado correctamente la selección del producto.", capturas, textos, nombre_automatizacion)
        ingreso_mercancia6_info["codigo_producto"] = codigo_producto
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al buscar producto: {e}")
        raise

def esperar_carga(driver, nombre_automatizacion, etapa):
    try:
        WebDriverWait(driver, 40).until(EC.invisibility_of_element_located((By.XPATH, "//div[@id='loading']")))
        escribir_log(nombre_automatizacion, f"Carga completada antes de '{etapa}'.")
    except TimeoutException:
        escribir_log(nombre_automatizacion, f"Advertencia: Gif de carga no desapareció antes de '{etapa}', continuando igual.")

def seleccionar_tipo_transaccion(driver, wait, capturas, textos, nombre_automatizacion, tipo_transaccion_index=1):
    try:
        tipo_transaccion = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='IdTipoTransaccion']")))
        resaltar_elemento(driver, tipo_transaccion)
        driver.execute_script("arguments[0].scrollIntoView(true);", tipo_transaccion)
        
        # Uso de la clase Select
        select_tipo = Select(tipo_transaccion)
        select_tipo.select_by_index(tipo_transaccion_index)
        
        # ✅ Obtener el texto del elemento seleccionado
        opcion_seleccionada = select_tipo.first_selected_option
        texto_opcion = opcion_seleccionada.text
        
        escribir_log(nombre_automatizacion, f"Opción '{texto_opcion}' (índice {tipo_transaccion_index}) seleccionada en 'Tipo de Transacción'.")
        
        # ✅ Guardar el texto en el diccionario
        ingreso_mercancia6_info["tipo_transaccion"] = texto_opcion
        
        tomar_captura(driver, "captura_tipo_transaccion", f"El usuario ha seleccionado correctamente la opción '{texto_opcion}' en el desplegable de 'Tipo de Transacción'.", capturas, textos, nombre_automatizacion)
        
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Tipo de Transacción': {e}")
        raise

def seleccionar_tipo_causal(driver, wait, capturas, textos, nombre_automatizacion, tipo_causal_index=6):
    try:
        tipo_causal = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='IdCausalConcepto']")))
        resaltar_elemento(driver, tipo_causal)
        
        # Uso de la clase Select
        select_tipo_causal = Select(tipo_causal)
        select_tipo_causal.select_by_index(tipo_causal_index)
        
        # ✅ Obtener el texto del elemento seleccionado
        opcion_seleccionada = select_tipo_causal.first_selected_option
        texto_opcion = opcion_seleccionada.text
        
        escribir_log(nombre_automatizacion, f"Opción '{texto_opcion}' (índice {tipo_causal_index}) seleccionada en 'Tipo de Causal'.")
        
        # ✅ Guardar el texto en el diccionario
        ingreso_mercancia6_info["tipo_causal"] = texto_opcion
        
        tomar_captura(driver, "captura_tipo_causal", f"El usuario ha seleccionado correctamente la opción '{texto_opcion}' en el desplegable de 'Tipo de Causal'.", capturas, textos, nombre_automatizacion)
        
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Tipo de Causal': {e}")
        raise

def ingresar_unidades(driver, wait, capturas, textos, nombre_automatizacion, unidades="53"):
    try:
        unidades_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='unidades-12957']")))
        resaltar_elemento(driver, unidades_input)
        driver.execute_script("arguments[0].click();", unidades_input)
        escribir_log(nombre_automatizacion, "Campo de unidades activado correctamente.")
        tomar_captura(driver, "captura_unidades", "El usuario ha activado correctamente el campo de unidades.", capturas, textos, nombre_automatizacion)
        unidades_input.send_keys(Keys.CONTROL, "a")
        unidades_input.send_keys(Keys.DELETE)
        escribir_log(nombre_automatizacion, "Contenido del campo de unidades borrado correctamente.")
        tomar_captura(driver, "captura_unidades_vacias", "Se ha borrado correctamente el contenido del campo de unidades.", capturas, textos, nombre_automatizacion)
        unidades_input.send_keys(unidades)
        unidades_input.send_keys(Keys.RETURN)
        escribir_log(nombre_automatizacion, f"Cantidad '{unidades}' ingresada correctamente en el campo de unidades.")
        tomar_captura(driver, "captura_unidades_modificadas", f"El usuario ha ingresado correctamente la cantidad '{unidades}' en el campo de unidades.", capturas, textos, nombre_automatizacion)
        ingreso_mercancia6_info["unidades"] = unidades
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar unidades: {e}")
        raise

def enviar_productos(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_enviar_productos = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='enviarIngresoBMND']")))
        resaltar_elemento(driver, clic_enviar_productos)
        driver.execute_script("arguments[0].click();", clic_enviar_productos)
        escribir_log(nombre_automatizacion, "Productos enviados correctamente.")
        tomar_captura(driver, "captura_enviar_productos", "El usuario ha enviado correctamente los productos.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al enviar productos: {e}")
        raise

def confirmar_envio(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay.swal-overlay--show-modal > div > div.swal-footer > div > button")))
        resaltar_elemento(driver, clic_ok)
        driver.execute_script("arguments[0].click();", clic_ok)
        escribir_log(nombre_automatizacion, "Envío de productos confirmado correctamente.")
        tomar_captura(driver, "captura_confirmacion", "El usuario ha confirmado correctamente el envío de los productos.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar envío: {e}")
        raise

def ingreso_mercancia6(driver, codigo_producto="12957", tipo_transaccion_index=1, tipo_causal_index=6, unidades="53"):
    """
    Automatiza el proceso de ingreso de mercancía a bodega en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "ingreso_mercancia6_pdf"

    try:
        # abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza el ingreso de mercancía a bodega 6", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_mercancia", "Se inició el proceso de ingreso de mercancía a bodega.", capturas, textos, nombre_automatizacion)
        
        # navegar_a_bodega(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_ingresar_mercancia(driver, wait, capturas, textos, nombre_automatizacion)
        buscar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto)
        esperar_carga(driver, nombre_automatizacion, "Tipo de Transacción")
        seleccionar_tipo_transaccion(driver, wait, capturas, textos, nombre_automatizacion, tipo_transaccion_index)
        esperar_carga(driver, nombre_automatizacion, "Tipo de Causal")
        seleccionar_tipo_causal(driver, wait, capturas, textos, nombre_automatizacion, tipo_causal_index)
        ingresar_unidades(driver, wait, capturas, textos, nombre_automatizacion, unidades)
        enviar_productos(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_envio(driver, wait, capturas, textos, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles del ingreso de mercancía: Código producto: {ingreso_mercancia6_info.get('codigo_producto', 'No capturado')}, "
              f"Tipo de transacción: {ingreso_mercancia6_info.get('tipo_transaccion', 'No capturado')}, "
              f"Tipo de causal: {ingreso_mercancia6_info.get('tipo_causal', 'No capturado')}, "
              f"Unidades: {ingreso_mercancia6_info.get('unidades', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de ingreso de mercancía: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise