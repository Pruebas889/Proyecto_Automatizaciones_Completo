
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

descuento_globo_info = {}

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


def asignar_cliente(driver, wait, capturas, textos, nombre_automatizacion, documento_cliente="1022947165"):
    try:
        boton_cliente = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnClienteFactura']")))
        resaltar_elemento(driver, boton_cliente)
        driver.execute_script("arguments[0].click();", boton_cliente)
        escribir_log(nombre_automatizacion, "Accedió a la sección 'Cliente'.")
        time.sleep(1.2)
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
        
        actions = ActionChains(driver)
        actions.send_keys(Keys.RETURN).pause(0.5).send_keys(Keys.ARROW_DOWN).pause(0.5).send_keys(Keys.RETURN).perform()
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

def convenio_beneficio(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # Esperar y capturar el modal de nota (alert-info) que aparece tras confirmar cliente
        try:
            nota_info = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-info")))
            resaltar_elemento(driver, nota_info)
            tomar_captura(driver, "captura_modal_nota_info", "Ingreso a la sección de convenios.", capturas, textos, nombre_automatizacion)
        except Exception as e:
            escribir_log(nombre_automatizacion, f"No se encontró el modal de nota info: {e}")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Convenio': {e}")
        raise

def convenio_beneficio_boton(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        convenio = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='modalNormal']/div/div/div[2]/div[2]/table/tbody/tr[2]/td[5]/button")))
        resaltar_elemento(driver, convenio)
        escribir_log(nombre_automatizacion, "Accedió a 'Convenio' correctamente.")
        tomar_captura(driver, "captura_menu_convenio", "Se accedió correctamente al botón 'Convenio'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", convenio)
        # Esperar el modal de éxito swal-modal
        try:
            modal_exito = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".swal-modal .swal-icon--success")))
            resaltar_elemento(driver, modal_exito)
            tomar_captura(driver, "captura_modal_exito_convenio", "Modal de éxito: Debe ingresar nuevamente todos los productos a la factura.", capturas, textos, nombre_automatizacion)
            # Cerrar el modal dando clic al botón OK
            boton_ok = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div/div[4]/div/button")))
            driver.execute_script("arguments[0].click();", boton_ok)
        except Exception as e:
            escribir_log(nombre_automatizacion, f"No se encontró el modal de éxito de convenio: {e}")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Convenio': {e}")
        raise

def confirmacion_convenio(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # Esperar a que aparezca el modal de advertencia
        modal_advertencia = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".swal-modal .swal-icon--warning")))
        resaltar_elemento(driver, modal_advertencia)
        escribir_log(nombre_automatizacion, "Modal de advertencia de convenio visible.")
        tomar_captura(driver, "captura_modal_advertencia_convenio", "Modal de advertencia: ¿Desea aplicar al convenio de los beneficios de la empresa COPSERVIR?", capturas, textos, nombre_automatizacion)

        # Buscar y hacer clic en el botón 'Sí'
        boton_si = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".swal-button--Si.btn-success")))
        resaltar_elemento(driver, boton_si)
        escribir_log(nombre_automatizacion, "Botón 'Sí' del convenio localizado y resaltado.")
        tomar_captura(driver, "captura_boton_si_convenio", "Se va a confirmar el convenio haciendo clic en 'Sí'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_si)
        escribir_log(nombre_automatizacion, "Se hizo clic en el botón 'Sí' para confirmar el convenio.")

        # Esperar el modal de éxito tras confirmar convenio
        try:
            modal_exito = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".swal-modal .swal-icon--success")))
            resaltar_elemento(driver, modal_exito)
            escribir_log(nombre_automatizacion, "Modal de éxito tras confirmar convenio visible.")
            tomar_captura(driver, "captura_modal_exito_confirmar_convenio", "Modal de éxito: Debe ingresar nuevamente todos los productos a la factura.", capturas, textos, nombre_automatizacion)
            # Cerrar el modal dando clic al botón OK
            boton_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".swal-button--confirm")))
            resaltar_elemento(driver, boton_ok)
            driver.execute_script("arguments[0].click();", boton_ok)
            escribir_log(nombre_automatizacion, "Se hizo clic en el botón OK del modal de éxito.")
        except Exception as e:
            escribir_log(nombre_automatizacion, f"No se encontró el modal de éxito tras confirmar convenio: {e}")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al interactuar con el modal de confirmación de convenio: {e}")
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

def seleccionar_unidad_producto(driver, wait, capturas, textos, nombre_automatizacion, cantidad="1"):
    try:
        unidad_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='CantidadUnidadesVenta-12957']")))
        resaltar_elemento(driver, unidad_input)
        driver.execute_script("arguments[0].click();", unidad_input)
        unidad_input.send_keys(Keys.CONTROL, "a")
        unidad_input.send_keys(Keys.DELETE)
        unidad_input.send_keys(cantidad)
        unidad_input.send_keys(Keys.RETURN)
        escribir_log(nombre_automatizacion, f"Unidad seleccionada: {cantidad} y se simuló Enter.")
        tomar_captura(driver, "captura_unidad_seleccionada", "Unidad de producto seleccionada correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "seleccionar unidad")
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar unidad: {e}")
        raise

def mostrar_detalle_descuento(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto="12957"):
    try:
        enlace_descuento = wait.until(EC.element_to_be_clickable((By.ID, f"BtnDetalleDescuentoRefe-{codigo_producto}")))
        resaltar_elemento(driver, enlace_descuento)
        escribir_log(nombre_automatizacion, "Enlace de detalle de descuento localizado y resaltado.")
        tomar_captura(driver, "captura_enlace_detalle_descuento", "Se va a mostrar el detalle de descuento del producto.", capturas, textos, nombre_automatizacion)
        popover = None
        for intento in range(3):
            driver.execute_script("arguments[0].click();", enlace_descuento)
            escribir_log(nombre_automatizacion, f"Intento {intento+1}: clic en el enlace de descuento.")
            try:
                popover = wait.until(lambda d: d.find_element(By.CSS_SELECTOR, ".popover.fade.top.in[role='tooltip']") if d.find_elements(By.CSS_SELECTOR, ".popover.fade.top.in[role='tooltip']") else False)
                break
            except TimeoutException:
                time.sleep(0.5)
        if popover:
            resaltar_elemento(driver, popover)
            escribir_log(nombre_automatizacion, "Popover de descuentos visible.")
            tomar_captura(driver, "captura_popover_descuento", "Detalle de descuentos del producto.", capturas, textos, nombre_automatizacion)
            # Cerrar el popover haciendo clic de nuevo en el botón
            try:
                driver.execute_script("arguments[0].click();", enlace_descuento)
                escribir_log(nombre_automatizacion, "Popover de descuento cerrado tras segundo clic (dentro de mostrar_detalle_descuento).")
            except Exception as e:
                escribir_log(nombre_automatizacion, f"No se pudo cerrar el popover de descuento tras segundo clic: {e}")
        else:
            escribir_log(nombre_automatizacion, "No se pudo mostrar el popover de descuentos tras varios intentos.")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error al mostrar detalle de descuento: {e}")
        raise
  
# Buscar producto DOLEX 500 MG CAJA X 200 TAB
    try:
        buscar_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BuscarProducto']")))
        resaltar_elemento(driver, buscar_input)
        driver.execute_script("arguments[0].click();", buscar_input)
        buscar_input.clear()
        buscar_input.send_keys("DOLEX 500 MG CAJA X 200 TAB")
        buscar_input.send_keys(Keys.RETURN)
        escribir_log(nombre_automatizacion, "Se buscó el producto DOLEX 500 MG CAJA X 200 TAB y se simuló Enter.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al buscar producto DOLEX: {e}")

    # Esperar el modal de resultados y capturar
    try:
        input_term = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@id='Term' and @value='DOLEX 500 MG CAJA X 200 TAB']")))
        resaltar_elemento(driver, input_term)
        tomar_captura(driver, "captura_modal_busqueda_dolex", "Modal de resultados de búsqueda para DOLEX 500 MG CAJA X 200 TAB.", capturas, textos, nombre_automatizacion)
    except Exception as e:
        escribir_log(nombre_automatizacion, f"No se encontró el modal de resultados de búsqueda: {e}")

    # Resaltar y capturar el span de descuento -12%
    try:
        span_descuento = wait.until(EC.visibility_of_element_located((By.XPATH, "//span[contains(text(),'-12%') and contains(@style,'background-color: red')]")))
        resaltar_elemento(driver, span_descuento)
        tomar_captura(driver, "captura_span_descuento_dolex", "Etiqueta de descuento -12% resaltada en el modal de resultados.", capturas, textos, nombre_automatizacion)
    except Exception as e:
        escribir_log(nombre_automatizacion, f"No se pudo resaltar/capturar el span de descuento: {e}")


def descuentos(driver):
    
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "descuento_globo_pdf"

    try:
        descuento_globo_info["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, " Globo de descuento en el Beneficio 134.", nombre_automatizacion)
        tomar_captura(driver, "cajero_ventas", "Se inició el proceso de Globo de descuento en el Beneficio 134.", capturas, textos, nombre_automatizacion)
        navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        asignar_cliente(driver, wait, capturas, textos, nombre_automatizacion)
        convenio_beneficio(driver, wait, capturas, textos, nombre_automatizacion)
        convenio_beneficio_boton(driver, wait, capturas, textos, nombre_automatizacion)
        confirmacion_convenio(driver, wait, capturas, textos, nombre_automatizacion)
        buscar_y_seleccionar_producto(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_unidad_producto(driver, wait, capturas, textos, nombre_automatizacion)
        mostrar_detalle_descuento(driver, wait, capturas, textos, nombre_automatizacion)

        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles de descuento globo: Timestamp: {descuento_globo_info.get('timestamp', 'No capturado')}")
        # Forzar navegación a la página principal para el siguiente proceso
        driver.get("http://192.168.100.63/")
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de venta con cliente: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise
