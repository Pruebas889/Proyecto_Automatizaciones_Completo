"""
Script para automatizar la devolución sin cliente, incluyendo logs y guardando los datos en una variable.
"""
import time
import os
import logging
from datetime import datetime
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
from ventas_sincliente import venta_sin_cliente_info
from generacion_pdf import generar_pdf_consolidado, escribir_log

# Tiempo (segundos) para esperar que el loader/overlay desaparezcan.
# Cambia este valor para reducir o aumentar los timeouts de espera de carga.
CARGA_TIMEOUT = 15

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
                setTimeout(function(){{ document.body.removeChild(div); }}, 1000);
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
        escribir_log(nombre_automatizacion, f"Error al tomar captura {ruta_captura}: {e}") # type: ignore
        raise

def esperar_carga_desaparezca(driver, nombre_automatizacion, contexto):
    try:
        escribir_log(nombre_automatizacion, f"Esperando a que desaparezca el gif de carga tras {contexto}.")
        # Usar la constante CARGA_TIMEOUT para controlar fácilmente el tiempo de espera.
        WebDriverWait(driver, CARGA_TIMEOUT).until(EC.invisibility_of_element_located((By.ID, "loading")))
        WebDriverWait(driver, CARGA_TIMEOUT).until(EC.invisibility_of_element_located((By.CLASS_NAME, "swal-overlay")))
        escribir_log(nombre_automatizacion, f"Carga y overlay desaparecidos tras {contexto}.")
    except TimeoutException:
        escribir_log(nombre_automatizacion, f"Advertencia: Carga o overlay no desaparecieron tras {contexto}, continuando.")

def iniciar_devolucion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_devolucion = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnDevolucionFactura']")))
        resaltar_elemento(driver, boton_devolucion)
        esperar_carga_desaparezca(driver, nombre_automatizacion, "iniciar devolución")
        escribir_log(nombre_automatizacion, "Accedió a 'Devolución' correctamente.")
        tomar_captura(driver, "captura_devolucion", "Accedió al módulo de 'Devolución' correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_devolucion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al iniciar devolución: {e}")
        raise

def seleccionar_devolucion_por_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        devolucion_numero_factura = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='modalSmall']/div/div/div[2]/div/div[1]/div/button")))
        resaltar_elemento(driver, devolucion_numero_factura)
        tomar_captura(driver, "captura_seleccion_factura", "Seleccionada la opción 'Devolución con número de factura'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", devolucion_numero_factura)
        escribir_log(nombre_automatizacion, "Seleccionó 'Devolución con número de factura' correctamente.")
        esperar_carga_desaparezca(driver, nombre_automatizacion, "seleccionar devolución por factura")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar devolución por factura: {e}")
        raise

def ingresar_numero_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        factura = venta_sin_cliente_info.get("factura")
        if not factura:
            escribir_log(nombre_automatizacion, "Error: El número de factura no se ha capturado. Abortando la devolución.")
            raise ValueError("Número de factura no disponible")
        
        numero_factura = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='NumeroFactura']")))
        resaltar_elemento(driver, numero_factura)
        numero_factura.send_keys(factura)
        escribir_log(nombre_automatizacion, f"Número de factura ingresado: {factura}")
        tomar_captura(driver, "captura_numero_factura", f"Número de factura ingresado correctamente: {factura}.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", numero_factura)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, ValueError) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar número de factura: {e}")
        raise

def ingresar_numero_caja(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        with open("caja_asignada.txt", "r") as f:
            numero_caja_asignada = f.read().strip()
    except FileNotFoundError:
        escribir_log(nombre_automatizacion, "Error: Archivo caja_asignada.txt no encontrado.")
        raise
    
    if not numero_caja_asignada or numero_caja_asignada == "0":
        escribir_log(nombre_automatizacion, "Error: No se asignó número de caja válido.")
        raise ValueError("Número de caja no válido")
    
    try:
        numero_caja = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='NumeroCaja']")))
        resaltar_elemento(driver, numero_caja)
        driver.execute_script("arguments[0].click();", numero_caja)
        numero_caja.clear()
        numero_caja.send_keys(numero_caja_asignada)
        escribir_log(nombre_automatizacion, f"Número de caja '{numero_caja_asignada}' ingresado correctamente.")
        venta_sin_cliente_info["numero_caja"] = numero_caja_asignada
        tomar_captura(driver, "captura_numero_caja", f"Número de caja ingresado correctamente: {numero_caja_asignada}.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar número de caja: {e}")
        raise

def ejecutar_devolucion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_devolver = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='FormDevolucionFacturaTipo']/div[2]/button")))
        resaltar_elemento(driver, boton_devolver)
        driver.execute_script("arguments[0].click();", boton_devolver)
        escribir_log(nombre_automatizacion, "Clic en 'Devolver' realizado correctamente.")
        tomar_captura(driver, "captura_devolver", "Devolución ejecutada correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, nombre_automatizacion, "seleccionar devolución por factura")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ejecutar devolución: {e}")
        raise

def confirmar_devolucion_inicial(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay > div > div.swal-footer > div > button")))
        resaltar_elemento(driver, boton_ok)
        escribir_log(nombre_automatizacion, "Confirmación inicial de devolución aceptada.")
        tomar_captura(driver, "captura_confirmacion_ok", "Confirmación inicial de devolución aceptada correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_ok)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar devolución inicial: {e}")
        raise

def seleccionar_causal_devolucion(driver, wait, capturas, textos, nombre_automatizacion, indice_causal=3):
    try:
        # Esperar a que desaparezca el loader antes de interactuar
        esperar_carga_desaparezca(driver, nombre_automatizacion, "seleccionar devolución por factura")

        # Ahora esperamos que el dropdown esté visible y habilitado
        causal_devolucion_dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#CausalDevolucion")))

        resaltar_elemento(driver, causal_devolucion_dropdown)
        select = Select(causal_devolucion_dropdown)
        select.select_by_index(indice_causal)
        causal_texto = select.first_selected_option.text
        venta_sin_cliente_info["causal"] = causal_texto
        escribir_log(nombre_automatizacion, f"Causal de devolución seleccionada: {causal_texto} (índice {indice_causal}).")
        tomar_captura(driver, "captura_causal_devolucion", f"Causal de devolución seleccionada correctamente: {causal_texto}.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar causal de devolución: {e}")
        raise

def efectuar_devolucion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        efectuar_devolucion = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='efectuarDevolucion']")))
        resaltar_elemento(driver, efectuar_devolucion)
        driver.execute_script("arguments[0].click();", efectuar_devolucion)
        escribir_log(nombre_automatizacion, "Clic en 'Efectuar Devolución' realizado correctamente.")
        tomar_captura(driver, "captura_efectuar_devolucion", "Devolución efectuada correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al efectuar devolución: {e}")
        raise

def confirmar_devolucion_final(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_ok_devolucion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal-button.swal-button--confirm.swal-button--danger")))
        resaltar_elemento(driver, boton_ok_devolucion)
        escribir_log(nombre_automatizacion, "Confirmación final de devolución aceptada.")
        tomar_captura(driver, "captura_confirmacion_final", "Confirmación final de devolución aceptada correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_ok_devolucion)

        esperar_carga_desaparezca(driver, nombre_automatizacion, "seleccionar devolución por factura")

        boton_ok_devolucion_final = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay > div > div.swal-footer > div > button")))
        resaltar_elemento(driver, boton_ok_devolucion_final)
        escribir_log(nombre_automatizacion, "Proceso de devolución completado correctamente.")
        venta_sin_cliente_info["estado"] = "completado"
        esperar_carga_desaparezca(driver, nombre_automatizacion, "proceso de devolución completado")
        tomar_captura(driver, "captura_proceso_completado", "Proceso de devolución completado correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_ok_devolucion_final)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar devolución final: {e}")
        raise

def cerrar_pantalla(driver, nombre_automatizacion):
    try:
        driver.execute_script("document.elementFromPoint(0, 0).click();")
        escribir_log(nombre_automatizacion, "Clic en coordenada vacía para cerrar pantalla.")
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error al cerrar pantalla: {e}")
        raise

def devolucion_factura_sincliente(driver):
    """
    Automatiza el proceso de devolución sin cliente en el sistema de cajero, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "devolucion_sincliente_pdf"

    try:
        factura = venta_sin_cliente_info.get("factura")
        if not factura:
            escribir_log(nombre_automatizacion, "Error: No se capturó el número de factura. Abortando devolución.")
            raise ValueError("Número de factura no disponible")
        
        escribir_log(nombre_automatizacion, f"Iniciando devolución para factura: {factura}")
        mostrar_mensaje(driver, "Se efectuará la devolución de la compra sin cliente", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_devolucion_sincliente", "Se inició el proceso de devolución correctamente.", capturas, textos, nombre_automatizacion)
        
        iniciar_devolucion(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_devolucion_por_factura(driver, wait, capturas, textos, nombre_automatizacion)
        ingresar_numero_factura(driver, wait, capturas, textos, nombre_automatizacion)
        ingresar_numero_caja(driver, wait, capturas, textos, nombre_automatizacion)
        ejecutar_devolucion(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_devolucion_inicial(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_causal_devolucion(driver, wait, capturas, textos, nombre_automatizacion)
        efectuar_devolucion(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_devolucion_final(driver, wait, capturas, textos, nombre_automatizacion)
        cerrar_pantalla(driver, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Devolución completada para factura: {factura}, Caja: {venta_sin_cliente_info.get('numero_caja', 'No capturado')}, Causal: {venta_sin_cliente_info.get('causal', 'No capturada')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException, ValueError) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de devolución sin cliente: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise