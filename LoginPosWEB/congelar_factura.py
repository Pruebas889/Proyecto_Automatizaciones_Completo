"""
Script para automatizar la congelación de una factura.
"""
import time
import os
import logging
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

# Global variable to store invoice information (reused from original script)
congelar_venta = {}

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

def navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_cajero = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > aside > section > ul > li:nth-child(4) > a")))
        resaltar_elemento(driver, menu_cajero)
        tomar_captura(driver, "captura_cajero", "El usuario accedió correctamente al menú 'Cajero'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", menu_cajero)
        escribir_log(nombre_automatizacion, "Accedió al menú 'Cajero' correctamente.")
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Cajero': {e}")
        raise

def navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_ventas = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class, 'active')]//ul//li[1]//a")))
        resaltar_elemento(driver, menu_ventas)
        driver.execute_script("arguments[0].click();", menu_ventas)
        escribir_log(nombre_automatizacion, "Accedió al módulo 'Ventas' correctamente.")
        tomar_captura(driver, "captura_ventas", "El usuario ingresó correctamente al módulo 'Ventas'.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Ventas': {e}")
        raise

def seleccionar_facturar(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_facturar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > div > section:nth-child(1) > div > div:nth-child(4) > a")))
        resaltar_elemento(driver, boton_facturar)
        driver.execute_script("arguments[0].click();", boton_facturar)
        escribir_log(nombre_automatizacion, "Accedió a la opción 'Facturar' correctamente.")
        tomar_captura(driver, "captura_facturar", "El usuario accedió correctamente a la opción 'Facturar'.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar 'Facturar': {e}")
        raise

def iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        iniciar_factura = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnIniciarFactura']")))
        resaltar_elemento(driver, iniciar_factura)
        escribir_log(nombre_automatizacion, "Inició el proceso de facturación correctamente.")
        tomar_captura(driver, "captura_iniciar_factura", "El usuario inició correctamente el proceso de facturación.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", iniciar_factura)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al iniciar factura: {e}")
        raise

def buscar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto="12957"):
    try:
        buscar_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='BuscarProducto']")))
        resaltar_elemento(driver, buscar_input)
        buscar_input.send_keys(codigo_producto)
        escribir_log(nombre_automatizacion, f"Código de producto {codigo_producto} ingresado correctamente.")
        tomar_captura(driver, "captura_busqueda_producto", f"Se ingresó correctamente el código del producto '{codigo_producto}' en el campo de búsqueda.", capturas, textos, nombre_automatizacion)

        actions = ActionChains(driver)
        actions.send_keys(Keys.RETURN)
        actions.perform()
        escribir_log(nombre_automatizacion, "Producto seleccionado con Enter correctamente.")
        tomar_captura(driver, "captura_seleccion_opcion", "Se seleccionó correctamente la primera opción en el campo y se confirmó con Enter.", capturas, textos, nombre_automatizacion)
        congelar_venta["codigo_producto"] = codigo_producto
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al buscar producto: {e}")
        raise

def cerrar_modal_lasa(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, "//*[@id='ModalLasa']")))
        cerrar = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div/div/div[3]/form/button")))
        resaltar_elemento(driver, cerrar)
        cerrar.click()
        escribir_log(nombre_automatizacion, "Modal de producto LASA cerrado correctamente.")
        tomar_captura(driver, "captura_producto_lasa", "Modal de producto LASA cerrado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
        escribir_log(nombre_automatizacion, "Advertencia: No se encontró el modal LASA, continuando la automatización.")
        pass

def esperar_carga(driver, capturas, textos, nombre_automatizacion):
    try:
        WebDriverWait(driver, 40).until(EC.invisibility_of_element_located((By.ID, "loading")))
        WebDriverWait(driver, 40).until(EC.invisibility_of_element_located((By.CLASS_NAME, "swal-overlay")))
        escribir_log(nombre_automatizacion, "Carga de página completada correctamente.")
        tomar_captura(driver, "captura_post_carga", "La página ha terminado de cargar correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al esperar carga: {e}")
        raise

def ingresar_cantidad_fracciones(driver, wait, capturas, textos, nombre_automatizacion, cantidad="3"):
    try:
        unidad_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='CantidadFraccionesVenta-12957']")))
        resaltar_elemento(driver, unidad_input)
        driver.execute_script("arguments[0].click();", unidad_input)
        unidad_input.send_keys(Keys.CONTROL, "a")
        unidad_input.send_keys(Keys.DELETE)
        unidad_input.send_keys(cantidad)
        escribir_log(nombre_automatizacion, f"Cantidad {cantidad} ingresada correctamente.")
        tomar_captura(driver, "captura_cantidad_nueva", f"Se ingresó correctamente la cantidad '{cantidad}' en el campo de fracciones.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
        unidad_input.send_keys(Keys.RETURN)
        congelar_venta["cantidad_fracciones"] = cantidad
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar cantidad de fracciones: {e}")
        raise

def congelar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_congelar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnCongelarVenta']")))
        resaltar_elemento(driver, boton_congelar)
        driver.execute_script("arguments[0].click();", boton_congelar)
        escribir_log(nombre_automatizacion, "Clic en 'Congelar' realizado correctamente.")
        tomar_captura(driver, "captura_congelar", "El usuario ha hecho clic en la opción 'Congelar' correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al congelar factura: {e}")
        raise

def confirmar_congelacion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#campoVentaCongelada")))
        resaltar_elemento(driver, clic_ok)
        driver.execute_script("arguments[0].click();", clic_ok)
        escribir_log(nombre_automatizacion, "Confirmación de congelación realizada correctamente.")
        time.sleep(2)  # Reduced from 7 seconds, adjust if needed
        tomar_captura(driver, "captura_finalizado", "El proceso de congelación de la venta ha finalizado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar congelación: {e}")
        raise

def congelacion_factura(driver, codigo_producto="12957", cantidad="3"):
    """
    Automatiza el proceso de congelación de una factura en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "congelar_factura_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza la congelación de una factura", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_congelar_factura", "Se inició el proceso de congelación de factura.", capturas, textos, nombre_automatizacion)
        
        navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_facturar(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        buscar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto)
        cerrar_modal_lasa(driver, wait, capturas, textos, nombre_automatizacion)
        esperar_carga(driver, capturas, textos, nombre_automatizacion)
        ingresar_cantidad_fracciones(driver, wait, capturas, textos, nombre_automatizacion, cantidad)
        congelar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_congelacion(driver, wait, capturas, textos, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles de la congelación: Código producto: {congelar_venta.get('codigo_producto', 'No capturado')}, "
              f"Cantidad fracciones: {congelar_venta.get('cantidad_fracciones', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de congelación de factura: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise