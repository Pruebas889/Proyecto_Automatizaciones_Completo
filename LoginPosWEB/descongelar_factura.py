"""
Script para automatizar la descongelación de una factura.
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

# Global variable to store invoice information (reused from original script)
venta_sin_cliente_info = {}

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
        escribir_log("descongelar_factura_pdf", f"Error al resaltar elemento: {e}")
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

def iniciar_descongelacion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_descongelar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnDescongelarVentas']")))
        resaltar_elemento(driver, boton_descongelar)
        escribir_log(nombre_automatizacion, "Clic en 'Descongelar Venta' realizado correctamente.")
        tomar_captura(driver, "captura_descongelar", "El usuario ha hecho clic en 'Descongelar Venta' correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_descongelar)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "iniciar descongelación")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al iniciar descongelación: {e}")
        raise

def ultima_descongelacion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#w0 > div.row > div.col-xs-8 > ul > li.last > a")))
        resaltar_elemento(driver, clic_ok)
        driver.execute_script("arguments[0].click();", clic_ok)
        escribir_log(nombre_automatizacion, "Confirmación de congelación realizada correctamente.")
        time.sleep(2)  # Reduced from 7 seconds, adjust if needed
        # Captura del botón 'Ultima' clickeado
        tomar_captura(driver, "captura_boton_ultima", "Boton 'Ultima' clickeado.", capturas, textos, nombre_automatizacion)
        # Captura del estado final del proceso de descongelación (se toma después de 'Boton Ultima')
        tomar_captura(driver, "captura_proceso_descongelacion_finalizado", "Proceso de descongelación finalizado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar la última descongelación: {e}")
        raise

def seleccionar_ultima_congelacion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        descongelar_venta = wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[contains(@class, 'btn-primary btn-sm abrir')])[last()]")))
        resaltar_elemento(driver, descongelar_venta)
        driver.execute_script("arguments[0].click();", descongelar_venta)
        escribir_log(nombre_automatizacion, "Última venta congelada seleccionada correctamente.")
        tomar_captura(driver, "captura_ultima_venta_seleccionada", "El usuario ha seleccionado la última venta congelada correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "seleccionar última congelación")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar la última venta congelada: {e}")
        raise

def descongelar_venta(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        descongelar_venta = wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[contains(@class, 'btn-success') and contains(@class, 'btn-lg') and contains(text(), 'Descongelar Venta')])[last()]")))
        resaltar_elemento(driver, descongelar_venta)
        driver.execute_script("arguments[0].click();", descongelar_venta)
        escribir_log(nombre_automatizacion, "Venta descongelada correctamente.")
        tomar_captura(driver, "captura_venta_descongelada", "El usuario ha descongelado la venta correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "descongelar venta")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al descongelar venta: {e}")
        raise

def iniciar_facturacion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        facturar_venta = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnFacturarVenta']")))
        resaltar_elemento(driver, facturar_venta)
        driver.execute_script("arguments[0].click();", facturar_venta)
        escribir_log(nombre_automatizacion, "Proceso de facturación iniciado correctamente.")
        tomar_captura(driver, "captura_facturar_venta", "El usuario ha iniciado correctamente el proceso de facturación de la venta.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al iniciar facturación: {e}")
        raise

def realizar_pago(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        try:
            clic_facturar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnFacturar']")))
            resaltar_elemento(driver, clic_facturar)
            driver.execute_script("arguments[0].click();", clic_facturar)
            escribir_log(nombre_automatizacion, "Clic en 'Facturar' realizado correctamente.")
        except TimeoutException:
            try:
                clic_facturar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#FormValoresFormasPago > div:nth-child(3) > div:nth-child(2) > div:nth-child(2)")))
                resaltar_elemento(driver, clic_facturar)
                driver.execute_script("arguments[0].click();", clic_facturar)
                escribir_log(nombre_automatizacion, "Clic en 'Facturar' (intento 2) realizado correctamente.")
            except TimeoutException:
                escribir_log(nombre_automatizacion, "Error: Tiempo excedido en ambos intentos para localizar 'Facturar'.")
                raise
        except NoSuchElementException:
            escribir_log(nombre_automatizacion, "Error: No se encontró el botón 'Facturar' en el primer intento.")
            raise
        except StaleElementReferenceException:
            escribir_log(nombre_automatizacion, "Error: El botón 'Facturar' se volvió obsoleto en el primer intento.")
            raise

        tomar_captura(driver, "captura_pago", "Pago realizado correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "realizar pago")
        try:
            escribir_log(nombre_automatizacion, "Realizando captura de confirmación de pago.")
            # Clic en "OK" para confirmar el pago
            ok_pago = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".swal-button")))
            resaltar_elemento(driver, ok_pago)
            tomar_captura(driver, "captura_confirmacion_pago", "Confirmación de pago realizada correctamente.", capturas, textos, nombre_automatizacion)
            # Esperar a que el overlay de swal esté visible y clickeable
            driver.execute_script("arguments[0].click();", ok_pago)
            escribir_log(nombre_automatizacion, "Clic en 'OK' realizado correctamente.")
        except NoSuchElementException:
            escribir_log(nombre_automatizacion, "Error: No se pudo localizar el botón 'OK' para confirmar el pago.")
            raise
        except TimeoutException:
            escribir_log(nombre_automatizacion, "Advertencia: El overlay de swal no desapareció o el botón 'OK' no estuvo disponible, continuando igual.")
        except StaleElementReferenceException:
            escribir_log(nombre_automatizacion, "Error: El botón 'OK' se volvió obsoleto.")
            raise

    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al realizar pago: {e}")
        raise

def capturar_numero_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        try:
            wait.until(EC.visibility_of_element_located((
                By.XPATH,
                "//div[contains(@class,'modal-content')]//h4[normalize-space(text())='Resumen Factura']"
            )))
        except TimeoutException:
            escribir_log(nombre_automatizacion, "Error: No se encontró el modal 'Resumen Factura'.")
            raise

        # Esperar hasta que el botón 'Cerrar' esté listo para clic
        try:
            btn_cerrar = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "div.col-md-6:nth-child(3) > button:nth-child(1)"
            )))
            escribir_log(nombre_automatizacion, "Botón 'Cerrar' localizado correctamente.")
            resaltar_elemento(driver, btn_cerrar)
        except TimeoutException:
            escribir_log(nombre_automatizacion, "Error: Tiempo excedido al localizar el botón 'Cerrar'.")
            raise
        except NoSuchElementException:
            escribir_log(nombre_automatizacion, "Error: No se encontró el botón 'Cerrar'.")
            raise
        except StaleElementReferenceException:
            escribir_log(nombre_automatizacion, "Error: El botón 'Cerrar' se volvió obsoleto.")
            raise

        # Esperar que el botón 'OK' esté visible y clickeable
        try:
            ok_pago = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".swal-button.swal-button--confirm")))
            escribir_log(nombre_automatizacion, "El botón 'OK' está clickeable.")
            driver.execute_script("arguments[0].scrollIntoView(true);", ok_pago)
            resaltar_elemento(driver, ok_pago)
            driver.execute_script("arguments[0].click();", ok_pago)
            escribir_log(nombre_automatizacion, "Clic en 'OK' realizado correctamente.")
        except NoSuchElementException:
            escribir_log(nombre_automatizacion, "Error: No se pudo hacer clic en el botón 'OK', la espera excedió el tiempo.")
        except TimeoutException:
            escribir_log(nombre_automatizacion, "Error: No se pudo hacer clic en el botón 'OK', la espera excedió el tiempo.")
        except StaleElementReferenceException:
            escribir_log(nombre_automatizacion, "Error: El botón 'OK' se volvió obsoleto.")

        # Esperar a que el modal que muestra el número de factura aparezca
        try:
            numero_factura_elemento = wait.until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="modalLarge"]/div/div/div[2]/div/div[2]/h2')))
            resaltar_elemento(driver, numero_factura_elemento)
        except TimeoutException:
            escribir_log(nombre_automatizacion, "Error: Tiempo excedido al localizar el número de factura.")
            raise
        except NoSuchElementException:
            escribir_log(nombre_automatizacion, "Error: No se encontró el elemento del número de factura.")
            raise
        except StaleElementReferenceException:
            escribir_log(nombre_automatizacion, "Error: El elemento del número de factura se volvió obsoleto.")
            raise
        texto_factura = numero_factura_elemento.text.strip()
        escribir_log(nombre_automatizacion, f"Texto obtenido del modal de factura: {texto_factura}")

        if "No. Factura:" in texto_factura:
            factura_numero = texto_factura.replace("No. Factura:", "").strip()
            venta_sin_cliente_info["factura"] = factura_numero
            escribir_log(nombre_automatizacion, f"Número de factura capturado: {factura_numero}")
        else:
            escribir_log(nombre_automatizacion, f"Error al extraer el número de factura: {texto_factura}")
            raise ValueError("Formato de número de factura inválido")

        tomar_captura(driver, "captura_factura_numero", "Número de factura mostrado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, AttributeError) as e:
        escribir_log(nombre_automatizacion, f"Error al capturar número de factura: {e}")
        raise

def cerrar_resumen_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        cerrar_factura = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#modalLarge > div > div > div.modal-body > div > div.col-md-6.text-right > button")))
        resaltar_elemento(driver, cerrar_factura)
        driver.execute_script("arguments[0].click();", cerrar_factura)
        escribir_log(nombre_automatizacion, "Cerró la 'Factura de la Venta' correctamente.")
        tomar_captura(driver, "captura_modal_cerrado", "Modal cerrado correctamente después de mostrar el número de factura.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al cerrar resumen de factura: {e}")
        raise

def descongelacion_factura(driver):
    """
    Automatiza el proceso de descongelación de una factura en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "descongelar_factura_pdf"

    try:
        venta_sin_cliente_info["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mostrar_mensaje(driver, "Se realiza la descongelación de una factura", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_descongelar_factura", "Se inició el proceso de descongelación de factura.", capturas, textos, nombre_automatizacion)
        
        iniciar_descongelacion(driver, wait, capturas, textos, nombre_automatizacion)
        ultima_descongelacion(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_ultima_congelacion(driver, wait, capturas, textos, nombre_automatizacion)
        descongelar_venta(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_facturacion(driver, wait, capturas, textos, nombre_automatizacion)
        realizar_pago(driver, wait, capturas, textos, nombre_automatizacion)
        capturar_numero_factura(driver, wait, capturas, textos, nombre_automatizacion)
        cerrar_resumen_factura(driver, wait, capturas, textos, nombre_automatizacion)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        venta_sin_cliente_info["estado_factura"] = "Descongelada y pagada"
        print(f"Detalles de la descongelación: Estado factura: {venta_sin_cliente_info.get('estado_factura', 'No capturado')}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de descongelación de factura: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise