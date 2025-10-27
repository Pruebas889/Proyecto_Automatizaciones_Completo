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

cliente_generico_info = {}

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

def iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_facturar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > div > section:nth-child(1) > div > div:nth-child(4) > a")))
        resaltar_elemento(driver, boton_facturar)
        escribir_log(nombre_automatizacion, "Accedió a 'Facturar' correctamente.")
        tomar_captura(driver, "captura_facturar_facturar", "Acceso al botón 'Facturar' realizado correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_facturar)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "acceder a facturar")
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
def asignar_cliente(driver, wait, capturas, textos, nombre_automatizacion, documento_cliente="222222222"):
    try:
        boton_cliente = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnClienteFactura']")))
        resaltar_elemento(driver, boton_cliente)
        driver.execute_script("arguments[0].click();", boton_cliente)
        escribir_log(nombre_automatizacion, "Accedió a la sección 'Cliente'.")
        time.sleep(1)
        tomar_captura(driver, "captura_cliente", "Se accedió correctamente a la sección 'Cliente'.", capturas, textos, nombre_automatizacion)
        
        descuento_cliente = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='OmitirCliente']")))
        resaltar_elemento(driver, descuento_cliente)
        escribir_log(nombre_automatizacion, "Omitió documento del cliente.")
        tomar_captura(driver, "captura_omitir_documento_cliente", "Se omitió el documento del cliente correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", descuento_cliente)

        buscar_cliente_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='Cliente']")))
        resaltar_elemento(driver, buscar_cliente_input)
        buscar_cliente_input.send_keys(documento_cliente)
        escribir_log(nombre_automatizacion, f"Cliente {documento_cliente} buscado correctamente.")
        tomar_captura(driver, "captura_buscar_cliente", "Se intentó buscar el cliente genérico (222222222).", capturas, textos, nombre_automatizacion)


    # Simular Enter para buscar
        buscar_cliente_input.send_keys(Keys.RETURN)
        time.sleep(2.5)  # Espera más larga para que termine la búsqueda y la UI se estabilice

        # Mostrar mensaje amarillo personalizado
        driver.execute_script(
            """
            if (document.body) {
                var div = document.createElement('div');
                div.innerHTML = 'Se comprobó restricción para crear clientes en Posweb';
                div.style.position = 'fixed';
                div.style.top = '10px';
                div.style.right = '10px';
                div.style.backgroundColor = 'yellow';
                div.style.padding = '10px';
                div.style.fontSize = '20px';
                div.style.zIndex = '9999';
                div.id = 'mensaje_restriccion_cliente';
                document.body.appendChild(div);
                setTimeout(function(){ document.body.removeChild(div); }, 2000);
            }
            """
        )
        escribir_log(nombre_automatizacion, "Mensaje de restricción mostrado en pantalla.")
        tomar_captura(driver, "captura_mensaje_restriccion", "Se comprobó restricción para crear clientes en Posweb.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error al asignar cliente: {e}")
        raise

def generico(driver):
    
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "cliente_generico_pdf"

    try:
        cliente_generico_info["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Implementación de restricción para crear clientes en Posweb Consumidor Final", nombre_automatizacion)
        tomar_captura(driver, "cajero_ventas", "Se inició el proceso de cliente genérico.", capturas, textos, nombre_automatizacion)
        navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        asignar_cliente(driver, wait, capturas, textos, nombre_automatizacion)
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles de cliente genérico: Timestamp: {cliente_generico_info.get('timestamp', 'No capturado')}")
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de venta con cliente: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise
