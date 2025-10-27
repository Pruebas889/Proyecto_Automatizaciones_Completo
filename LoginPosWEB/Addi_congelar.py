"""
Script para automatizar la venta sin con cliente en Selenium, incluyendo logs y almacenándolo en una variable.
"""
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

# Global variable to store invoice information
Addi_cliente_info = {}

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

def capturar_modal_efimero(driver, capturas, textos, nombre_automatizacion, selector, nombre_archivo_base, texto_descriptivo, timeout=2.0, poll_interval=0.15):
    """
    Detecta y captura un modal/elemento efímero que aparece brevemente.
    Realiza polling rápido durante `timeout` segundos buscando `selector`. Si aparece,
    toma la captura inmediatamente y devuelve True. Si no aparece, devuelve False.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            if elems:
                # Resaltar y capturar la primera ocurrencia
                try:
                    resaltar_elemento(driver, elems[0])
                except Exception:
                    pass
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                nombre_archivo = f"{nombre_archivo_base}_{timestamp}"
                tomar_captura(driver, nombre_archivo, texto_descriptivo, capturas, textos, nombre_automatizacion)
                return True
        except Exception:
            # Ignorar errores menores durante polling
            pass
        time.sleep(poll_interval)
    return False

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

def asignar_cliente(driver, wait, capturas, textos, nombre_automatizacion, documento_cliente="35317479"):
    try:
        boton_cliente = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnClienteFactura']")))
        time.sleep(1)
        # Resaltar y capturar el botón antes de hacer click
        resaltar_elemento(driver, boton_cliente)
        time.sleep(0.25)
        tomar_captura(driver, "captura_boton_cliente", "Botón 'Cliente' resaltado antes de hacer click.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_cliente)
        escribir_log(nombre_automatizacion, "Accedió a la sección 'Cliente'.")

        # Evitar captura inmediata: tomaremos la captura cuando el campo de búsqueda esté visible
        descuento_cliente = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='OmitirCliente']")))
        resaltar_elemento(driver, descuento_cliente)
        escribir_log(nombre_automatizacion, "Omitió documento del cliente.")
        tomar_captura(driver, "captura_omitir_documento_cliente", "Se omitió el documento del cliente correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", descuento_cliente)

        # Esperar a que el campo de búsqueda del cliente sea realmente interactuable (clickeable)
        buscar_cliente_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='Cliente']")))
        resaltar_elemento(driver, buscar_cliente_input)
        # Pequeña pausa para animaciones/renderer
        time.sleep(0.3)
        # Capturar el modal/entrada del cliente justo cuando está interactuable
        tomar_captura(driver, "captura_cliente_modal", "Modal/entrada Cliente visible y listo para buscar.", capturas, textos, nombre_automatizacion)
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

def seleccionar_formas_pago(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        formas_pago = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnFormasPagoFactura']")))
        time.sleep(1)
        resaltar_elemento(driver, formas_pago)
        driver.execute_script("arguments[0].click();", formas_pago)
        escribir_log(nombre_automatizacion, "Accedió a 'Formas de pago' correctamente.")
        tomar_captura(driver, "captura_formas_pago", "Acceso a 'Formas de pago' realizado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar formas de pago: {e}")
        raise

def asignar_pago_Addi(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # El checkbox de Addi tiene id 'formaPago-35' dentro de la modal de formas de pago.
        # Usar By.ID es más sencillo y evita problemas con comillas en el XPath.
        tarjeta_addi = wait.until(EC.element_to_be_clickable((By.ID, "formaPago-35")))
        # Resaltar el checkbox y capturarlo mientras está resaltado (antes de click)
        resaltar_elemento(driver, tarjeta_addi)
        # Pequeña pausa para que el borde resaltado se renderice y aparezca en la captura
        time.sleep(0.25)
        tomar_captura(driver, "captura_tarjeta_addi_resaltada", "Checkbox 'ADDI' resaltado antes del click.", capturas, textos, nombre_automatizacion)

        # Si el checkbox no está checked, hacer click para marcarlo.
        try:
            is_checked = driver.execute_script("return arguments[0].checked;", tarjeta_addi)
        except Exception:
            is_checked = False
        if not is_checked:
            try:
                driver.execute_script("arguments[0].click();", tarjeta_addi)
                escribir_log(nombre_automatizacion, "Checkbox 'ADDI' marcado.")
            except Exception:
                # Fallback a dispatchEvent o click nativo si el click por script falla
                try:
                    driver.execute_script(
                        "var el=arguments[0]; var ev=document.createEvent('MouseEvents'); ev.initEvent('click', true, true); el.dispatchEvent(ev);",
                        tarjeta_addi,
                    )
                    escribir_log(nombre_automatizacion, "Checkbox 'ADDI' marcado (dispatchEvent fallback).")
                except Exception:
                    try:
                        tarjeta_addi.click()
                        escribir_log(nombre_automatizacion, "Checkbox 'ADDI' marcado (native click fallback).")
                    except Exception as e:
                        escribir_log(nombre_automatizacion, f"Error al marcar checkbox 'ADDI' por ningún método: {e}")
                        tomar_captura(driver, "captura_error_click_addi", "Diagnóstico: no se pudo clickear checkbox 'ADDI'", capturas, textos, nombre_automatizacion)
                        raise
        else:
            escribir_log(nombre_automatizacion, "Checkbox 'ADDI' ya estaba marcado.")

        time.sleep(0.5)
        # Captura final del estado después del click/selección
        tomar_captura(driver, "captura_tarjeta_addi", "Seleccionada la opción de pago 'ADDI'.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error al asignar forma de pago Addi: {e}")
        raise



def buscar_y_seleccionar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto="12287"):
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

def seleccionar_unidad_producto(driver, wait, capturas, textos, nombre_automatizacion, cantidad="3"):
    try:
        unidad_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='CantidadUnidadesVenta-12287']")))
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

        # Diagnóstico: esperar hasta que el botón de 'Congelar' sea clickeable.
        try:
            escribir_log(nombre_automatizacion, "Esperando botón '#BtnCongelarVenta' tras seleccionar unidad...")
            WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#BtnCongelarVenta")))
            escribir_log(nombre_automatizacion, "Botón 'Congelar' disponible. Continuando flujo.")
        except TimeoutException:
            escribir_log(nombre_automatizacion, "Advertencia: el botón 'Congelar' no apareció tras seleccionar unidad en 8s.")
            # Tomar captura para diagnóstico
            tomar_captura(driver, "captura_diagnostico_no_congelar", "Diagnóstico: botón 'Congelar' no apareció tras seleccionar unidad", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar unidad: {e}")
        raise

def congelar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_congelar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#BtnCongelarVenta")))
        resaltar_elemento(driver, boton_congelar)
        try:
            # Intento principal: click por script
            driver.execute_script("arguments[0].click();", boton_congelar)
        except Exception as e:
            escribir_log(nombre_automatizacion, f"Advertencia: click por script falló: {e}. Intentando dispatchEvent fallback.")
            try:
                driver.execute_script(
                    "var el=arguments[0]; var ev=document.createEvent('MouseEvents'); ev.initEvent('click', true, true); el.dispatchEvent(ev);",
                    boton_congelar,
                )
            except Exception as e2:
                escribir_log(nombre_automatizacion, f"Advertencia: dispatchEvent también falló: {e2}. Intentando click nativo.")
                try:
                    boton_congelar.click()
                except Exception as e3:
                    escribir_log(nombre_automatizacion, f"Error: no se pudo hacer click en 'Congelar' por ningún método: {e3}")
                    # Tomar captura diagnóstica y lanzar para que el flujo lo capture
                    tomar_captura(driver, "captura_error_click_congelar", "Diagnóstico: no se pudo clickear 'Congelar'", capturas, textos, nombre_automatizacion)
                    raise
        escribir_log(nombre_automatizacion, "Clic en 'Congelar' realizado correctamente.")
        tomar_captura(driver, "captura_congelar", "El usuario ha hecho clic en la opción 'Congelar' correctamente.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al congelar factura: {e}")
        raise

def confirmar_congelacion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # Intentar detectar y capturar el modal efímero justo cuando aparece (polling rápido)
        appeared = capturar_modal_efimero(
            driver,
            capturas,
            textos,
            nombre_automatizacion,
            selector="#campoVentaCongelada",
            nombre_archivo_base="captura_modal_confirmacion",
            texto_descriptivo="Modal de confirmación de congelación (antes de click)",
            timeout=2.0,
            poll_interval=0.12,
        )
        # Si no apareció durante el polling, aún podemos esperar por el elemento clickeable de forma normal
        if not appeared:
            clic_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#campoVentaCongelada")))
            resaltar_elemento(driver, clic_ok)
            # Tomar captura ahora como fallback
            tomar_captura(driver, "captura_modal_confirmacion_fallback", "Modal de confirmación de congelación (fallback)", capturas, textos, nombre_automatizacion)
        else:
            # Cuando capturar_modal_efimero devuelve True, intentamos localizar el elemento para hacer click
            clic_ok = None
            try:
                clic_ok = driver.find_element(By.CSS_SELECTOR, "#campoVentaCongelada")
            except Exception:
                pass
        # Hacer click para confirmar la congelación si encontramos el elemento
        if clic_ok:
            try:
                driver.execute_script("arguments[0].click();", clic_ok)
            except Exception as e:
                escribir_log(nombre_automatizacion, f"Advertencia: no se pudo hacer click directamente: {e}")
        else:
            escribir_log(nombre_automatizacion, "Advertencia: elemento de confirmación no encontrado para click, continuando.")
        escribir_log(nombre_automatizacion, "Confirmación de congelación realizada correctamente.")
        # Esperar que el modal/overlay desaparezca para evitar capturas del siguiente proceso
        try:
            WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "#campoVentaCongelada")))
        except TimeoutException:
            # Si no desaparece, continuar pero tomar captura de verificación final
            escribir_log(nombre_automatizacion, "Advertencia: el modal de confirmación no desapareció en 10s, continuando.")
        time.sleep(0.5)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar congelación: {e}")
        raise

def iniciar_descongelacion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_descongelar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#BtnDescongelarVentas")))
        resaltar_elemento(driver, boton_descongelar)
        # Intento robusto de click (script -> dispatch -> native)
        try:
            driver.execute_script("arguments[0].click();", boton_descongelar)
        except Exception as e:
            escribir_log(nombre_automatizacion, f"Advertencia: click por script falló en descongelar: {e}. Intentando dispatchEvent.")
            try:
                driver.execute_script(
                    "var el=arguments[0]; var ev=document.createEvent('MouseEvents'); ev.initEvent('click', true, true); el.dispatchEvent(ev);",
                    boton_descongelar,
                )
            except Exception:
                try:
                    boton_descongelar.click()
                except Exception as e2:
                    escribir_log(nombre_automatizacion, f"Error: no se pudo clickear 'Descongelar': {e2}")
                    tomar_captura(driver, "captura_error_click_descongelar", "Diagnóstico: no se pudo clickear 'Descongelar'", capturas, textos, nombre_automatizacion)
                    raise

        escribir_log(nombre_automatizacion, "Clic en 'Descongelar' realizado (intento).")
        # Esperar al overlay/loading que se dispara tras el click (hasta 20s)
        try:
            WebDriverWait(driver, 20).until(EC.invisibility_of_element_located((By.CLASS_NAME, "swal-overlay")))
            WebDriverWait(driver, 20).until(EC.invisibility_of_element_located((By.ID, "loading")))
            escribir_log(nombre_automatizacion, "Descongelación: overlay y loading desaparecieron.")
        except TimeoutException:
            escribir_log(nombre_automatizacion, "Advertencia: la descongelación quedó en carga más de 20s.")
        time.sleep(1)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar descongelacion: {e}")
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

def anular_venta(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        clic_ok = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#abrir-136651")))
        resaltar_elemento(driver, clic_ok)
        driver.execute_script("arguments[0].click();", clic_ok)
        escribir_log(nombre_automatizacion, "Confirmación de anulación de venta realizada correctamente.")
        time.sleep(2)  # Reduced from 7 seconds, adjust if needed
        tomar_captura(driver, "captura_finalizado", "El proceso de anulación de la venta ha finalizado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al confirmar la última descongelación: {e}")
        raise



def Addi_congelacion(driver):
    """
    Automatiza el proceso de venta con cliente en el sistema de cajero, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "Addi_Descongelacion_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza forma de pago Addi", nombre_automatizacion)
        tomar_captura(driver, "cajero_ventas", "Se inició el proceso de ventas correctamente.", capturas, textos, nombre_automatizacion)
        navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        asignar_cliente(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_formas_pago(driver, wait, capturas, textos, nombre_automatizacion)
        asignar_pago_Addi(driver, wait, capturas, textos, nombre_automatizacion)
        buscar_y_seleccionar_producto(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_unidad_producto(driver, wait, capturas, textos, nombre_automatizacion)
        congelar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        confirmar_congelacion(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_descongelacion(driver, wait, capturas, textos, nombre_automatizacion)
        ultima_descongelacion(driver, wait, capturas, textos, nombre_automatizacion)
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de venta con cliente: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise