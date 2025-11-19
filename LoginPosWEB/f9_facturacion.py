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


# Global variable to store sale information
venta_f9_info = {}

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
        time.sleep(0.7)  # Esperar un momento para asegurar que la página esté lista
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
        tomar_captura(driver, "captura_menu_ventas", "Acceso al menú 'Ventas' realizado correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", menu_ventas)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Ventas': {e}")
        raise

def iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton_facturar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > div > section:nth-child(1) > div > div:nth-child(4) > a")))
        resaltar_elemento(driver, boton_facturar)
        escribir_log(nombre_automatizacion, "Accedió a 'Facturar' correctamente.")
        tomar_captura(driver, "captura_facturar", "Se accedió correctamente al botón 'Facturar'.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_facturar)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "acceder a facturar")
        # Esperar hasta 60s para el botón 'Iniciar Factura'
        iniciar_factura = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='BtnIniciarFactura']"))
        )
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "acceder a facturar")
        resaltar_elemento(driver, iniciar_factura)
        escribir_log(nombre_automatizacion, "Accedió a 'Iniciar Factura' correctamente.")
        tomar_captura(driver, "captura_iniciar_factura", "Inicio de factura realizado correctamente.", capturas, textos, nombre_automatizacion)

        driver.execute_script("arguments[0].click();", iniciar_factura)

    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al iniciar factura: {e}")
        raise

def buscar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto="12957"):
    try:
        buscar_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='BuscarProducto']")))
        resaltar_elemento(driver, buscar_input)
        buscar_input.send_keys(codigo_producto)
        escribir_log(nombre_automatizacion, f"Producto '{codigo_producto}' buscado correctamente.")
        tomar_captura(driver, "captura_busqueda_producto", "Se realizó la búsqueda del producto correctamente.", capturas, textos, nombre_automatizacion)

        actions = ActionChains(driver)
        actions.send_keys(Keys.RETURN).perform()
        escribir_log(nombre_automatizacion, "Selección del producto confirmada.")
        tomar_captura(driver, "captura_seleccion_producto", "Se seleccionó el producto correctamente.", capturas, textos, nombre_automatizacion)
        venta_f9_info["codigo_producto"] = codigo_producto
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "seleccionar producto")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al buscar producto: {e}")
        raise


def ingresar_fraccion(driver, wait, capturas, textos, nombre_automatizacion, cantidad="1"):
    try:
        fraccion_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='CantidadFraccionesVenta-12957']")))
        resaltar_elemento(driver, fraccion_input)
        driver.execute_script("arguments[0].click();", fraccion_input)
        fraccion_input.send_keys(Keys.CONTROL, "a")
        fraccion_input.send_keys(Keys.DELETE)
        fraccion_input.send_keys(cantidad)
        escribir_log(nombre_automatizacion, f"Cantidad '{cantidad}' ingresada correctamente.")
        tomar_captura(driver, "captura_cantidad_producto", f"Cantidad de producto ingresada correctamente: {cantidad}.", capturas, textos, nombre_automatizacion)
        time.sleep(0.5)
        fraccion_input.send_keys(Keys.RETURN)
        venta_f9_info["cantidad"] = cantidad
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar fraccion: {e}")
        raise

def ajustar_precio_f9(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        f9_venta = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='TrProductoEnTabla-12957']/td[1]/button")))
        resaltar_elemento(driver, f9_venta)
        driver.execute_script("arguments[0].click();", f9_venta)
        escribir_log(nombre_automatizacion, "Boton 'F9' Presionado  correctamente.")
        time.sleep(0.5) 
        tomar_captura(driver, "captura_f9_venta", "Boton 'F9' Presionado  correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al dar en F9 boton: {e}")
        raise

    time.sleep(0.5)  # Esperar medio segundo para asegurar que el modal se haya cargado 

def modal_f9(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # Esperar a que aparezca el modal completo (div.modal-content)
        modal_content = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal-content")))
        time.sleep(1)  # Pequeño delay para asegurar que el modal esté completamente visible
        # NO resaltar el modal, solo tomar la captura
        tomar_captura(driver, "captura_modal_f9", "Modal de ajuste de precio mostrado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al mostrar modal de F9: {e}")
        raise


def nuevo_precio_fraccion(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # Esperar y hacer clic en el campo de nuevo precio fracción
        input_precio = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='NuevoPrecioFraccion']")))
        resaltar_elemento(driver, input_precio)
        driver.execute_script("arguments[0].click();", input_precio)
        input_precio.clear()
        input_precio.send_keys("50")
        escribir_log(nombre_automatizacion, "Se ingresó el nuevo precio de fracción: 50")
        time.sleep(0.5)
        tomar_captura(driver, "captura_f9_venta", "Nuevo precio de fracción ingresado: 50", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar nuevo precio de fracción: {e}")
        raise

# Nuevo método para hacer clic en el botón guardar
def boton_guardar(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        boton = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='FormAjusteOcasionalPrecio']/div[5]/button")))
        resaltar_elemento(driver, boton)
        driver.execute_script("arguments[0].click();", boton)
        escribir_log(nombre_automatizacion, "Botón Guardar presionado correctamente.")
        tomar_captura(driver, "captura_guardar_precio", "Botón Guardar presionado después de ingresar el nuevo precio de fracción.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al presionar el botón Guardar: {e}")
        raise

# Manejar el error de precio mínimo, extraer el máximo permitido y reintentar
def manejar_error_precio_minimo(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # Esperar a que aparezca el modal de error
        modal_error = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".swal-modal")))
        resaltar_elemento(driver, modal_error)
        # Extraer el texto del error
        texto_error = modal_error.find_element(By.CLASS_NAME, "swal-text").text
        escribir_log(nombre_automatizacion, f"Texto de error capturado: {texto_error}")
        tomar_captura(driver, "captura_error_precio_minimo", texto_error, capturas, textos, nombre_automatizacion)
        # Buscar el máximo permitido en el texto (mejorar regex para tolerar espacios y acentos)
        import re
        match = re.search(r"máximo permitido es[: ]*([0-9]+)", texto_error, re.IGNORECASE)
        if not match:
            match = re.search(r"maximo permitido es[: ]*([0-9]+)", texto_error, re.IGNORECASE)
        if match:
            maximo_permitido = match.group(1)
            escribir_log(nombre_automatizacion, f"Máximo permitido extraído: {maximo_permitido}")
        else:
            escribir_log(nombre_automatizacion, "No se pudo extraer el máximo permitido del mensaje de error.")
            raise ValueError("No se encontró el máximo permitido en el mensaje de error.")
        # Clic en el botón OK del modal (intenta por clase y luego por xpath si falla)
        try:
            boton_ok = modal_error.find_element(By.CSS_SELECTOR, ".swal-button--confirm")
        except Exception:
            try:
                boton_ok = driver.find_element(By.XPATH, "/html/body/div[5]/div/div[4]/div/button")
            except Exception as e:
                escribir_log(nombre_automatizacion, f"No se pudo encontrar el botón OK del modal: {e}")
                raise
        resaltar_elemento(driver, boton_ok)
        driver.execute_script("arguments[0].click();", boton_ok)
        time.sleep(0.5)
        return maximo_permitido
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al manejar el modal de error de precio mínimo: {e}")
        raise

# Flujo para intentar guardar precio, manejar error y reintentar con el máximo permitido
def flujo_guardar_precio_con_reintento(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        nuevo_precio_fraccion(driver, wait, capturas, textos, nombre_automatizacion)
        boton_guardar(driver, wait, capturas, textos, nombre_automatizacion)
        # Si aparece el modal de error, manejarlo y reintentar
        try:
            maximo = manejar_error_precio_minimo(driver, wait, capturas, textos, nombre_automatizacion)
            # Reintentar con el máximo permitido
            nuevo_precio_fraccion_valor(driver, wait, capturas, textos, nombre_automatizacion, maximo)
            boton_guardar(driver, wait, capturas, textos, nombre_automatizacion)
        except Exception:
            # Si no hay error, continuar
            pass
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error en el flujo de guardar precio con reintento: {e}")
        raise

# Variante de nuevo_precio_fraccion para ingresar un valor específico
def nuevo_precio_fraccion_valor(driver, wait, capturas, textos, nombre_automatizacion, valor):
    try:
        input_precio = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='NuevoPrecioFraccion']")))
        resaltar_elemento(driver, input_precio)
        driver.execute_script("arguments[0].click();", input_precio)
        input_precio.clear()
        input_precio.send_keys(str(valor))
        escribir_log(nombre_automatizacion, f"Se ingresó el nuevo precio de fracción: {valor}")
        time.sleep(0.5)
        tomar_captura(driver, "captura_f9_venta_reintento", f"Nuevo precio de fracción ingresado: {valor}", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar nuevo precio de fracción (reintento): {e}")
        raise

    time.sleep(0.5)  # Esperar medio segundo para asegurar que el modal se haya cargado


def capturar_resaltar_cantidad_y_subtotal(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto="12957"):
    try:
        # Buscar el <tr> del producto
        tr_producto = wait.until(EC.visibility_of_element_located((By.ID, f"TrProductoEnTabla-{codigo_producto}")))
        # Buscar el input de cantidad dentro del <tr>
        try:
            input_cantidad = tr_producto.find_element(By.ID, f"CantidadUnidadesVenta-{codigo_producto}")
        except Exception:
            # Fallback: buscar el input dentro del 5to <td> del <tr>
            input_cantidad = tr_producto.find_element(By.XPATH, "./td[5]//input")
        resaltar_elemento(driver, input_cantidad)
        tomar_captura(driver, f"captura_cantidad_unidades_{codigo_producto}", "Input de cantidad resaltado (readonly por F9)", capturas, textos, nombre_automatizacion)
        # Buscar el subtotal dentro del <tr>
        try:
            td_subtotal = tr_producto.find_element(By.ID, f"TdSubtotalProducto-{codigo_producto}")
        except Exception:
            td_subtotal = tr_producto.find_element(By.XPATH, "./td[7]")
        resaltar_elemento(driver, td_subtotal)
        tomar_captura(driver, f"captura_subtotal_producto_{codigo_producto}", "Subtotal del producto resaltado (antes y después de F9)", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al capturar y resaltar cantidad y subtotal: {e}")
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

        tomar_captura(driver, "captura_pago_realizado", "Pago realizado correctamente.", capturas, textos, nombre_automatizacion)
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
            venta_f9_info["factura"] = factura_numero
            escribir_log(nombre_automatizacion, f"Número de factura capturado: {factura_numero}")
        else:
            escribir_log(nombre_automatizacion, f"Error al extraer el número de factura: {texto_factura}")
            raise ValueError("Formato de número de factura inválido")

        tomar_captura(driver, "captura_factura_numero", "Número de factura mostrado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, AttributeError) as e:
        escribir_log(nombre_automatizacion, f"Error al capturar número de factura: {e}")
        raise

def cerrar_factura(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        cerrar_factura = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#modalLarge > div > div > div.modal-body > div > div.col-md-6.text-right > button")))
        resaltar_elemento(driver, cerrar_factura)
        driver.execute_script("arguments[0].click();", cerrar_factura)
        escribir_log(nombre_automatizacion, "Factura cerrada correctamente.")
        tomar_captura(driver, "captura_modal_cerrado", "Modal cerrado correctamente después de mostrar la factura.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al cerrar factura: {e}")
        raise

def tecla_f9(driver, codigo_producto="12957", cantidad="1"):
    """
    Automatiza el proceso de facturación de una venta con la tecla F9, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "f9_facturacion_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza la facturación de una venta con la tecla F9", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_f9", "Se inició el proceso de facturación con la tecla F9 correctamente.", capturas, textos, nombre_automatizacion)
        navegar_a_cajero(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_ventas(driver, wait, capturas, textos, nombre_automatizacion)
        iniciar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        buscar_producto(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "seleccionar producto")
        ingresar_fraccion(driver, wait, capturas, textos, nombre_automatizacion, cantidad)
        ajustar_precio_f9(driver, wait, capturas, textos, nombre_automatizacion)
        modal_f9(driver, wait, capturas, textos, nombre_automatizacion)
        flujo_guardar_precio_con_reintento(driver, wait, capturas, textos, nombre_automatizacion)
        capturar_resaltar_cantidad_y_subtotal(driver, wait, capturas, textos, nombre_automatizacion, codigo_producto)
        facturar_venta(driver, wait, capturas, textos, nombre_automatizacion)
        realizar_pago(driver, wait, capturas, textos, nombre_automatizacion)
        capturar_numero_factura(driver, wait, capturas, textos, nombre_automatizacion)
        cerrar_factura(driver, wait, capturas, textos, nombre_automatizacion)
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles de la venta con F9: Código producto: {venta_f9_info.get('codigo_producto', 'No capturado')}, "
              f"Cantidad: {venta_f9_info.get('cantidad', 'No capturado')}, "
              f"Precio original: {venta_f9_info.get('precio_original', 'No capturado')}, "
              f"Precio ajustado: {venta_f9_info.get('precio_ajustado', 'No capturado')}, "
              f"Número de factura: {venta_f9_info.get('numero_factura', 'No capturado')}")
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de facturación con F9: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise