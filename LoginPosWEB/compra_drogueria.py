"""
Script para automatizar la compra a drogueria.
"""
import time
import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
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

# Global variable to store purchase information
compra_drogueria_info = {}

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
        sidebar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".logo")))
        resaltar_elemento(driver, sidebar)
        driver.execute_script("arguments[0].click();", sidebar)
        escribir_log(nombre_automatizacion, "Menú lateral abierto correctamente.")
        time.sleep(1)
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
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Administrador': {e}")
        raise

def navegar_a_compra_drogueria(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_compra_drogueria = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/aside/section/ul/li[2]/ul/li[6]/a")))
        resaltar_elemento(driver, menu_compra_drogueria)
        driver.execute_script("arguments[0].click();", menu_compra_drogueria)
        escribir_log(nombre_automatizacion, "Accedió a 'Compra a Droguería' correctamente.")
        tomar_captura(driver, "captura_menu_compra_drogueria", "Acceso a 'Compra a Droguería' realizado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Compra a Droguería': {e}")
        raise

def ingresar_referencia_producto(driver, wait, capturas, textos, nombre_automatizacion, referencia="12957"):
    try:
        referencia_producto = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='NombreProductoBusq']")))
        resaltar_elemento(driver, referencia_producto)
        referencia_producto.send_keys(referencia)
        escribir_log(nombre_automatizacion, f"Referencia de producto {referencia} ingresada correctamente.")
        time.sleep(0.5)
        tomar_captura(driver, "captura_referencia_producto", f"Referencia del producto {referencia} ingresada correctamente.", capturas, textos, nombre_automatizacion)
        compra_drogueria_info["referencia_producto"] = referencia
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar referencia de producto: {e}")
        raise

def buscar_producto(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_buscar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='buscarProducto']")))
        resaltar_elemento(driver, clic_buscar)
        driver.execute_script("arguments[0].click();", clic_buscar)
        time.sleep(1)
        escribir_log(nombre_automatizacion, "Búsqueda de producto realizada correctamente.")
        tomar_captura(driver, "captura_busqueda", "Búsqueda de producto realizada correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al buscar producto: {e}")
        raise

def ingresar_documento_cruce(driver, wait, capturas, textos, nombre_automatizacion, documento="12345678"):
    try:
        documento_cruce = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='documentoCruce']")))
        resaltar_elemento(driver, documento_cruce)
        documento_cruce.send_keys(documento)
        escribir_log(nombre_automatizacion, f"Documento de cruce {documento} ingresado correctamente.")
        tomar_captura(driver, "captura_documento_cruce", f"Documento de cruce {documento} ingresado correctamente.", capturas, textos, nombre_automatizacion)
        compra_drogueria_info["documento_cruce"] = documento
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar documento de cruce: {e}")
        raise

def ingresar_cantidad_unidades(driver, wait, capturas, textos, nombre_automatizacion, unidades="2"):
    try:
        cantidad_unidades = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='unidades-12957']")))
        cantidad_unidades.send_keys(Keys.CONTROL, "a")
        cantidad_unidades.send_keys(Keys.DELETE)
        cantidad_unidades.send_keys(unidades)
        resaltar_elemento(driver, cantidad_unidades)
        time.sleep(0.5)
        escribir_log(nombre_automatizacion, f"Cantidad de unidades {unidades} ingresada correctamente.")
        tomar_captura(driver, "captura_cantidad_unidades", f"Cantidad de unidades ingresada correctamente: {unidades}.", capturas, textos, nombre_automatizacion)
        compra_drogueria_info["cantidad_unidades"] = unidades
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar cantidad de unidades: {e}")
        raise

def ingresar_cantidad_fracciones(driver, wait, capturas, textos, nombre_automatizacion, fracciones="2"):
    try:
        cantidad_fracciones = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='fracciones-12957']")))
        cantidad_fracciones.send_keys(Keys.CONTROL, "a")
        cantidad_fracciones.send_keys(Keys.DELETE)
        cantidad_fracciones.send_keys(fracciones)
        resaltar_elemento(driver, cantidad_fracciones)
        time.sleep(0.5)
        escribir_log(nombre_automatizacion, f"Cantidad de fracciones {fracciones} ingresada correctamente.")
        tomar_captura(driver, "captura_cantidad_fracciones", f"Cantidad de fracciones ingresada correctamente: {fracciones}.", capturas, textos, nombre_automatizacion)
        compra_drogueria_info["cantidad_fracciones"] = fracciones
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar cantidad de fracciones: {e}")
        raise

def ingresar_valor_unidades(driver, wait, capturas, textos, nombre_automatizacion, valor="800"):
    try:
        valor_unidades = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='valorNeto-12957']")))
        valor_unidades.send_keys(Keys.CONTROL, "a")
        valor_unidades.send_keys(Keys.DELETE)
        valor_unidades.send_keys(valor)
        resaltar_elemento(driver, valor_unidades)
        time.sleep(0.5)
        escribir_log(nombre_automatizacion, f"Valor de unidades {valor} ingresado correctamente.")
        tomar_captura(driver, "captura_valor_unidades", f"Valor de unidades ingresado correctamente: {valor}.", capturas, textos, nombre_automatizacion)
        compra_drogueria_info["valor_unidades"] = valor
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar valor de unidades: {e}")
        raise

def buscar_distribuidor(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        buscar_distribuidor = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='buscarDistribuidor-12957']")))
        resaltar_elemento(driver, buscar_distribuidor)
        driver.execute_script("arguments[0].click();", buscar_distribuidor)
        escribir_log(nombre_automatizacion, "Búsqueda de distribuidor realizada correctamente.")
        tomar_captura(driver, "captura_buscar_distribuidor", "Búsqueda de distribuidor realizada correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al buscar distribuidor: {e}")
        raise

def seleccionar_distribuidor(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        seleccionar_distribuidor = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='tablaDistribuidores']/tbody/tr[3]/td[2]")))
        resaltar_elemento(driver, seleccionar_distribuidor)
        driver.execute_script("arguments[0].click();", seleccionar_distribuidor)
        escribir_log(nombre_automatizacion, "Distribuidor seleccionado correctamente.")
        tomar_captura(driver, "captura_seleccionar_distribuidor", "Distribuidor seleccionado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar distribuidor: {e}")
        raise

def confirmar_distribuidor(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_distribuidor = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='seleccionarDistribuidor']")))
        resaltar_elemento(driver, clic_distribuidor)
        driver.execute_script("arguments[0].click();", clic_distribuidor)
        escribir_log(nombre_automatizacion, "Confirmación de selección de distribuidor realizada correctamente.")
        tomar_captura(driver, "captura_confirmar_distribuidor", "Confirmación de selección de distribuidor realizada correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar distribuidor: {e}")
        raise

def realizar_compra(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        realizar_compra = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='realizarCompra']")))
        resaltar_elemento(driver, realizar_compra)
        driver.execute_script("arguments[0].click();", realizar_compra)
        escribir_log(nombre_automatizacion, "Compra realizada correctamente.")
        tomar_captura(driver, "captura_realizar_compra", "Compra realizada correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al realizar compra: {e}")
        raise

def confirmar_compra_si(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_si = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay.swal-overlay--show-modal > div > div.swal-footer > div:nth-child(2) > button")))
        resaltar_elemento(driver, clic_si)
        escribir_log(nombre_automatizacion, "Confirmación inicial de compra realizada correctamente.")
        tomar_captura(driver, "captura_confirmacion_si", "Confirmación inicial de compra realizada correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", clic_si)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar compra (Sí): {e}")
        raise

def confirmar_compra_ok(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay.swal-overlay--show-modal > div > div.swal-footer > div > button")))
        resaltar_elemento(driver, boton_ok)
        escribir_log(nombre_automatizacion, "Confirmación final de compra aceptada correctamente.")
        tomar_captura(driver, "captura_ok", "Confirmación final aceptada correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", boton_ok)
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar compra (OK): {e}")
        raise

def comprar_a_drogueria(driver, referencia="12957", documento="12345678", unidades="2", fracciones="2", valor="800"):
    """
    Automatiza el proceso de compra a una droguería en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 40)
    capturas = []
    textos = []
    nombre_automatizacion = "compra_drogueria_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza la Compra a Droguería", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_compra_drogueria", "Se inició el proceso de la compra a una droguería correctamente.", capturas, textos, nombre_automatizacion)
        
        navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_compra_drogueria(driver, wait, capturas, textos, nombre_automatizacion)
        ingresar_referencia_producto(driver, wait, capturas, textos, nombre_automatizacion, referencia)
        buscar_producto(driver, wait, capturas, textos, nombre_automatizacion)
        ingresar_documento_cruce(driver, wait, capturas, textos, nombre_automatizacion, documento)
        ingresar_cantidad_unidades(driver, wait, capturas, textos, nombre_automatizacion, unidades)
        ingresar_cantidad_fracciones(driver, wait, capturas, textos, nombre_automatizacion, fracciones)
        ingresar_valor_unidades(driver, wait, capturas, textos, nombre_automatizacion, valor)
        buscar_distribuidor(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_distribuidor(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_distribuidor(driver, wait, capturas, textos, nombre_automatizacion)
        realizar_compra(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_compra_si(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_compra_ok(driver, wait, capturas, textos, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles de la compra: Referencia producto: {compra_drogueria_info.get('referencia_producto', 'No capturado')}, "
              f"Documento cruce: {compra_drogueria_info.get('documento_cruce', 'No capturado')}, "
              f"Unidades: {compra_drogueria_info.get('cantidad_unidades', 'No capturado')}, "
              f"Fracciones: {compra_drogueria_info.get('cantidad_fracciones', 'No capturado')}, "
              f"Valor unidades: {compra_drogueria_info.get('valor_unidades', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de compra a droguería: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise