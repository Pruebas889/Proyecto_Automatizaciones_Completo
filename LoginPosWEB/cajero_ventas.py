"""
Script para automatizar la venta sin con cliente en Selenium, incluyendo logs y almacenándolo en una variable.
"""
import time
import os
import logging
import keyboard
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

# Global variable to store invoice information
venta_cliente_info = {}

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

def buscar_y_seleccionar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto="12957"):
    try:
        buscar_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='BuscarProducto']")))
        resaltar_elemento(driver, buscar_input)
        buscar_input.send_keys(codigo_producto)
        escribir_log(nombre_automatizacion, f"Producto {codigo_producto} buscado correctamente.")
        tomar_captura(driver, "captura_buscar_producto", "Se realizó la búsqueda del producto correctamente.", capturas, textos, nombre_automatizacion)

        actions = ActionChains(driver)
        actions.send_keys(Keys.RETURN).perform()
        escribir_log(nombre_automatizacion, "Producto seleccionado con Enter.")
        tomar_captura(driver, "captura_busqueda_producto", "Se realizó la búsqueda del producto correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "seleccionar producto")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error al buscar o seleccionar producto: {e}")
        raise

def cerrar_modal_lasa(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, "//*[@id='ModalLasa']")))
        cerrar = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div/div/div[3]/form/button")))
        resaltar_elemento(driver, cerrar)
        driver.execute_script("arguments[0].click();", cerrar)
        escribir_log(nombre_automatizacion, "Modal de producto lasa cerrado correctamente.")
        tomar_captura(driver, "captura_producto_lasa", "Modal de producto lasa cerrado correctamente.", capturas, textos, nombre_automatizacion)
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Advertencia: No se encontró el popup de carga del producto (ModalLasa), continuando.")
    except (NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al cerrar modal lasa: {e}")
        raise

def capturar_precio_producto(driver, wait, nombre_automatizacion, max_retries=3):
    attempt = 0
    while attempt < max_retries:
        try:
            # Try multiple selectors to locate the price element
            selectors = [
                (By.XPATH, "//*[@id='TdPrecioUnidadProducto-12957']"),
                (By.CSS_SELECTOR, "td[id*='TdPrecioUnidadProducto']"),
                (By.XPATH, "//td[contains(@id, 'TdPrecioUnidadProducto')]")
            ]
            precio_element = None
            for selector_type, selector_value in selectors:
                try:
                    precio_element = wait.until(EC.visibility_of_element_located((selector_type, selector_value)))
                    break
                except TimeoutException:
                    continue

            if not precio_element:
                raise NoSuchElementException("No se encontró el elemento de precio con ningún selector.")

            resaltar_elemento(driver, precio_element)
            precio_texto = precio_element.text.strip()
            precio_limpio = int(precio_texto.replace("$", "").replace(".", "").replace(",", ""))
            escribir_log(nombre_automatizacion, f"Precio del producto capturado: {precio_limpio}")
            venta_cliente_info["precio"] = precio_limpio
            return precio_limpio
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException, ValueError) as e:
            attempt += 1
            escribir_log(nombre_automatizacion, f"Intento {attempt} fallido al capturar precio del producto: {e}")
            if attempt == max_retries:
                # Take a debug screenshot on final failure
                debug_captura = os.path.join("capturas", f"debug_precio_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                driver.save_screenshot(debug_captura)
                escribir_log(nombre_automatizacion, f"Captura de depuración guardada: {debug_captura}")
                raise NoSuchElementException(f"Error al capturar precio del producto tras {max_retries} intentos: {e}")
            time.sleep(1)  # Wait before retrying

def seleccionar_unidad_producto(driver, wait, capturas, textos, nombre_automatizacion, cantidad="1"):
    try:
        unidad_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='CantidadUnidadesVenta-12957']")))
        resaltar_elemento(driver, unidad_input)
        driver.execute_script("arguments[0].click();", unidad_input)
        unidad_input.send_keys(Keys.CONTROL, "a")
        unidad_input.send_keys(Keys.DELETE)
        unidad_input.send_keys(cantidad)
        escribir_log(nombre_automatizacion, f"Unidad seleccionada: {cantidad}.")
        tomar_captura(driver, "captura_unidad_seleccionada", "Unidad de producto seleccionada correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "seleccionar unidad")
        time.sleep(0.5)
        unidad_input.send_keys(Keys.RETURN)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar unidad: {e}")
        raise

def asignar_cliente(driver, wait, capturas, textos, nombre_automatizacion, documento_cliente="35317479"):
    try:
        boton_cliente = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnClienteFactura']")))
        resaltar_elemento(driver, boton_cliente)
        driver.execute_script("arguments[0].click();", boton_cliente)
        escribir_log(nombre_automatizacion, "Accedió a la sección 'Cliente'.")
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
        tomar_captura(driver, "captura_buscar_cliente", "Se realizó la búsqueda del cliente correctamente.", capturas, textos, nombre_automatizacion)
        
        # Presionar Enter para mostrar la lista
        buscar_cliente_input.send_keys(Keys.RETURN)
        time.sleep(0.5)
        
        # Usar keyboard para simular la tecla flecha abajo y enter
        keyboard.press_and_release('down')
        time.sleep(0.5)
        keyboard.press_and_release('enter')
        
        escribir_log(nombre_automatizacion, "Cliente seleccionado de la lista.")
        tomar_captura(driver, "captura_cliente_seleccionado", "Cliente seleccionado correctamente de la lista.", capturas, textos, nombre_automatizacion)
        
        boton_confirmar_cliente = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnContinuarCliente']")))
        resaltar_elemento(driver, boton_confirmar_cliente)
        driver.execute_script("arguments[0].click();", boton_confirmar_cliente)
        escribir_log(nombre_automatizacion, "Cliente confirmado correctamente.")
        tomar_captura(driver, "captura_confirmar_cliente", "Cliente confirmado correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error al asignar cliente: {e}")
        raise

def facturar_venta(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        facturar_venta = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnFacturarVenta']")))
        resaltar_elemento(driver, facturar_venta)
        driver.execute_script("arguments[0].click();", facturar_venta)
        escribir_log(nombre_automatizacion, "Accedió a 'Facturar Venta' correctamente.")
        tomar_captura(driver, "captura_facturar_venta", "Venta facturada correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al facturar venta: {e}")
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
            venta_cliente_info["factura"] = factura_numero
            escribir_log(nombre_automatizacion, f"Número de factura capturado: {factura_numero}")
        else:
            escribir_log(nombre_automatizacion, f"Error al extraer el número de factura: {texto_factura}")
            raise ValueError("Formato de número de factura inválido")

        tomar_captura(driver, "captura_factura_numero", "Número de factura mostrado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, AttributeError) as e:
        escribir_log(nombre_automatizacion, f"Error al capturar número de factura: {e}")
        raise

def cerrar_modal_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        cerrar_factura = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#modalLarge > div > div > div.modal-body > div > div.col-md-6.text-right > button")))
        resaltar_elemento(driver, cerrar_factura)
        driver.execute_script("arguments[0].click();", cerrar_factura)
        escribir_log(nombre_automatizacion, "Cerró la 'Factura de la Venta' correctamente.")
        tomar_captura(driver, "captura_modal_cerrado", "Modal cerrado correctamente después de mostrar el número de factura.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al cerrar modal de factura: {e}")
        raise

def cajero_ventas(driver):
    """
    Automatiza el proceso de venta con cliente en el sistema de cajero, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "cajero_ventas_pdf"

    try:
        venta_cliente_info["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza la venta con cliente", nombre_automatizacion)
        tomar_captura(driver, "cajero_ventas", "Se inició el proceso de ventas correctamente.", capturas, textos, nombre_automatizacion)

        navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        buscar_y_seleccionar_producto(driver, wait, capturas, textos, nombre_automatizacion)
        cerrar_modal_lasa(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_unidad_producto(driver, wait, capturas, textos, nombre_automatizacion)
        asignar_cliente(driver, wait, capturas, textos, nombre_automatizacion)
        facturar_venta(driver, wait, capturas, textos, nombre_automatizacion)
        realizar_pago(driver, wait, capturas, textos, nombre_automatizacion)
        capturar_numero_factura(driver, wait, capturas, textos, nombre_automatizacion)
        cerrar_modal_factura(driver, wait, capturas, textos, nombre_automatizacion)

        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles de facturación venta de unidades con cliente: Timestamp: {venta_cliente_info.get('timestamp', 'No capturado')}, "
              f"Número de factura capturado: {venta_cliente_info.get('factura', 'No capturado')}, "
              f"Precio: {venta_cliente_info.get('precio', 'No capturado')}")

    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de venta con cliente: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise