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

Orden_compra_info = {}

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


def navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_administrador = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.wrapper > aside > section > ul > li:nth-child(2) > a")))
        resaltar_elemento(driver, menu_administrador)
        driver.execute_script("arguments[0].click();", menu_administrador)
        escribir_log(nombre_automatizacion, "Clic en menú 'Administrador' correcto.")
        tomar_captura(driver, "captura_administrador", "Acceso al menú Administrador realizado correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "clic en 'Administrador'")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: No se pudo localizar o hacer clic en 'Administrador'.")
        raise

def ordenar_compra(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        Orden_de_compra = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.wrapper > aside > section > ul > li.active > ul > li:nth-child(11) > a")))
        resaltar_elemento(driver, Orden_de_compra)
        driver.execute_script("arguments[0].click();", Orden_de_compra)
        escribir_log(nombre_automatizacion, "Clic en menú 'Orden de Compra' correcto.")
        tomar_captura(driver, "captura_orden_de_compra", "Acceso al menú Orden de Compra realizado correctamente.", capturas, textos, nombre_automatizacion)
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "clic en 'Orden de Compra'")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Error: No se pudo localizar o hacer clic en 'Orden de Compra'.")
        raise

def anular_todas_las_ordenes(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        # Esperar el contenedor de órdenes de compra
        contenedor = wait.until(EC.visibility_of_element_located((By.ID, "ordenesCompra")))
        paneles = contenedor.find_elements(By.CSS_SELECTOR, ".panelOrdenCompra")
        if not paneles:
            escribir_log(nombre_automatizacion, "No se encontraron órdenes de compra para anular.")
            # No return, continuar con el flujo
        for idx, panel in enumerate(paneles, 1):
            try:
                resaltar_elemento(driver, panel)
                panel_id = panel.get_attribute("id")
                tomar_captura(driver, f"captura_panel_orden_{panel_id}", f"Panel de Orden de Compra #{panel_id} seleccionado.", capturas, textos, nombre_automatizacion)
                driver.execute_script("arguments[0].scrollIntoView(true);", panel)
                driver.execute_script("arguments[0].click();", panel)
                escribir_log(nombre_automatizacion, f"Panel de orden de compra #{panel_id} clickeado.")
                # Esperar y hacer clic en el botón de anular
                try:
                    boton_anular = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='anularOrden']")))
                    resaltar_elemento(driver, boton_anular)
                    tomar_captura(driver, f"captura_boton_anular_{panel_id}", f"Botón de anular orden para #{panel_id} resaltado.", capturas, textos, nombre_automatizacion)
                    driver.execute_script("arguments[0].click();", boton_anular)
                    escribir_log(nombre_automatizacion, f"Botón de anular orden clickeado para #{panel_id}.")
                    time.sleep(1)
                except Exception as e:
                    escribir_log(nombre_automatizacion, f"No se pudo hacer clic en el botón de anular para #{panel_id}: {e}")
            except Exception as e:
                escribir_log(nombre_automatizacion, f"Error al procesar panel de orden de compra: {e}")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error general al anular órdenes: {e}")
    
def generar_boton(driver, capturas, textos, nombre_automatizacion):
    try:
        # Esperar hasta 1s para el botón 'Boton generar'
        boton_generar = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/section[1]/div/div[2]/a"))
        )
        resaltar_elemento(driver, boton_generar)
        escribir_log(nombre_automatizacion, "Accedió a 'Botón Generar' correctamente.")
        tomar_captura(driver, "Boton_generar", "Boton generar realizado correctamente.", capturas, textos, nombre_automatizacion)

        driver.execute_script("arguments[0].click();", boton_generar)

    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al dar a Botón Generar: {e}")
        raise

def buscar_y_seleccionar_nit(driver, wait, capturas, textos, nombre_automatizacion, nit="900818921"):
    try:
        # Esperar el input de búsqueda en la tabla
        input_nit = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='DataTables_Table_0']/thead/tr[2]/td[1]/input")))
        resaltar_elemento(driver, input_nit)
        input_nit.clear()
        input_nit.send_keys(nit)
        escribir_log(nombre_automatizacion, f"NIT {nit} ingresado en el filtro de la tabla.")
        tomar_captura(driver, "captura_input_nit", f"Se ingresó el NIT {nit} en el filtro de la tabla.", capturas, textos, nombre_automatizacion)
        time.sleep(1)
        # Esperar y seleccionar la fila correspondiente
        fila_nit = wait.until(EC.element_to_be_clickable((By.XPATH, f"//tr[@data-id][td/b[text()='{nit}']]")))
        resaltar_elemento(driver, fila_nit)
        tomar_captura(driver, "captura_fila_nit", f"Fila de NIT {nit} encontrada y resaltada.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", fila_nit)
        escribir_log(nombre_automatizacion, f"Fila de NIT {nit} seleccionada.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al buscar o seleccionar NIT {nit}: {e}")

def generar_orden(driver, wait, capturas, textos, nombre_automatizacion):
    """Hace clic en el botón 'Generar Orden', toma captura y registra en el log."""
    try:
        boton_generar_orden = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='generarOrden']")))
        resaltar_elemento(driver, boton_generar_orden)
        tomar_captura(driver, "boton_generar_orden", "Botón 'Generar Orden' resaltado y listo para hacer clic.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_generar_orden)
        escribir_log(nombre_automatizacion, "Botón 'Generar Orden' clickeado correctamente.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al hacer clic en el botón 'Generar Orden': {e}")

def capturar_mensaje_exito_orden(driver, wait, capturas, textos, nombre_automatizacion):
    """Captura el mensaje de éxito tras generar la orden de compra."""
    try:
        mensaje_exito = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'alert-success') and contains(., 'La orden de compra fue generada exitosamente.')]"))
        )
        resaltar_elemento(driver, mensaje_exito)
        tomar_captura(driver, "mensaje_exito_orden", "Mensaje de éxito: La orden de compra fue generada exitosamente.", capturas, textos, nombre_automatizacion)
        escribir_log(nombre_automatizacion, "Mensaje de éxito de orden de compra capturado correctamente.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"No se encontró el mensaje de éxito de orden de compra: {e}")

def clic_boton_volver_orden(driver, wait, capturas, textos, nombre_automatizacion):
    """Hace clic en el botón de volver tras generar la orden de compra."""
    try:
        boton_volver = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/section[1]/div/div[1]/a")))
        resaltar_elemento(driver, boton_volver)
        tomar_captura(driver, "boton_volver_orden", "Botón 'Actualizar' resaltado y listo para hacer clic.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_volver)
        escribir_log(nombre_automatizacion, "Botón 'Actualizar' clickeado correctamente tras generar la orden.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al hacer clic en el botón 'Actualizar' tras generar la orden: {e}")

def seleccionar_ultima_orden_generada(driver, wait, capturas, textos, nombre_automatizacion):
    """Selecciona la última orden de compra generada, toma captura y log, sin anularla."""
    try:
        contenedor = wait.until(EC.visibility_of_element_located((By.ID, "ordenesCompra")))
        paneles = contenedor.find_elements(By.CSS_SELECTOR, ".panelOrdenCompra")
        if not paneles:
            escribir_log(nombre_automatizacion, "No se encontraron órdenes de compra para seleccionar.")
            return
        # Seleccionar solo el último panel (el más reciente)
        panel = paneles[-1]
        resaltar_elemento(driver, panel)
        panel_id = panel.get_attribute("id")
        tomar_captura(driver, f"captura_panel_orden_seleccionada_{panel_id}", f"Panel de Orden de Compra #{panel_id} seleccionado para acción.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].scrollIntoView(true);", panel)
        driver.execute_script("arguments[0].click();", panel)
        escribir_log(nombre_automatizacion, f"Panel de orden de compra #{panel_id} seleccionado para acción.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar la última orden generada: {e}")
    
def buscar_producto_en_orden_compra(driver, wait, capturas, textos, nombre_automatizacion):
    """Busca un producto en la orden de compra escribiendo el código y simulando Enter."""
    try:
        # Buscar la primera referencia en la tabla
        try:
            ref_cell1 = wait.until(EC.visibility_of_element_located((By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[1]/td[1]")))
            primera_referencia = ref_cell1.text.strip()
            input_cantidad1 = driver.find_element(By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[1]//input[contains(@id, 'modificarOrden-')]")
            cantidad1 = int(input_cantidad1.get_attribute("value") or 0)
            escribir_log(nombre_automatizacion, f"Primera referencia encontrada: {primera_referencia} con cantidad {cantidad1}")
        except Exception as e:
            escribir_log(nombre_automatizacion, f"No se pudo obtener la primera referencia de la tabla para buscar producto: {e}")
            return

        referencia_a_usar = primera_referencia
        fila_usada = 1
        if cantidad1 <= 1:
            # Intentar con la segunda referencia
            try:
                ref_cell2 = driver.find_element(By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[2]/td[1]")
                segunda_referencia = ref_cell2.text.strip()
                input_cantidad2 = driver.find_element(By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[2]//input[contains(@id, 'modificarOrden-')]")
                cantidad2 = int(input_cantidad2.get_attribute("value") or 0)
                escribir_log(nombre_automatizacion, f"Segunda referencia encontrada: {segunda_referencia} con cantidad {cantidad2}")
                if cantidad2 > 1:
                    referencia_a_usar = segunda_referencia
                    fila_usada = 2
                else:
                    escribir_log(nombre_automatizacion, "Ninguna de las dos primeras referencias tiene cantidad mayor a 1. No se buscará producto.")
                    return
            except Exception as e:
                escribir_log(nombre_automatizacion, f"No se pudo obtener la segunda referencia o su cantidad: {e}")
                return

        # Guardar la referencia y fila usada para el resto del flujo
        global Orden_compra_info
        Orden_compra_info["referencia_a_usar"] = referencia_a_usar
        Orden_compra_info["fila_usada"] = fila_usada

        input_buscar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BuscarProductoOrdenCompra']")))
        resaltar_elemento(driver, input_buscar)
        input_buscar.clear()
        input_buscar.send_keys(referencia_a_usar)
        tomar_captura(driver, "input_buscar_producto_orden", f"Se ingresó el código de producto {referencia_a_usar} en la orden de compra.", capturas, textos, nombre_automatizacion)
        input_buscar.send_keys(Keys.ENTER)
        escribir_log(nombre_automatizacion, f"Código de producto {referencia_a_usar} ingresado y se simuló Enter en la orden de compra.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al buscar producto en orden de compra: {e}")

def modificar_cantidad_producto_orden(driver, wait, capturas, textos, nombre_automatizacion,):
    """Modifica la cantidad del producto en la orden de compra sumando 1 al valor actual del input (dinámico)."""
    try:
        global Orden_compra_info
        codigo = Orden_compra_info.get("referencia_a_usar", None)
        fila_usada = Orden_compra_info.get("fila_usada", 1)
        if not codigo:
            escribir_log(nombre_automatizacion, "No hay referencia seleccionada para modificar cantidad.")
            return
    # Línea eliminada: paréntesis extra
        xpath_input = f"//table[@id='tableOrdenCompra']//tbody/tr[{fila_usada}]//input[contains(@id, 'modificarOrden-{codigo}')]"
        input_cantidad = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_input)))
        resaltar_elemento(driver, input_cantidad)
        valor_actual = input_cantidad.get_attribute("value")
        try:
            valor_nuevo = str(int(valor_actual) + 1)
        except Exception:
            valor_nuevo = "1"  # fallback si no es numérico
        input_cantidad.clear()
        time.sleep(0.2)
        input_cantidad.send_keys(valor_nuevo)
        time.sleep(0.2)
        valor_post = input_cantidad.get_attribute("value")
        if valor_post != valor_nuevo:
            driver.execute_script("arguments[0].value = arguments[1];", input_cantidad, valor_nuevo)
            escribir_log(nombre_automatizacion, f"Valor forzado con JS para {codigo}: {valor_nuevo}")
        # Disparar eventos input y change para que el sistema detecte el cambio
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", input_cantidad)
        tomar_captura(driver, f"input_modificar_cantidad_{codigo}", f"Cantidad del producto {codigo} ajustada dinámicamente a {valor_nuevo} en la orden de compra.", capturas, textos, nombre_automatizacion)
        escribir_log(nombre_automatizacion, f"Cantidad del producto {codigo} ajustada dinámicamente a {valor_nuevo} en la orden de compra.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al modificar cantidad del producto en orden de compra: {e}")

def capturar_y_aceptar_alerta_max(driver, wait, capturas, textos, nombre_automatizacion):
    """Captura el modal de error 'Excedio MAX' y hace clic en el botón OK."""
    try:
        modal = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'swal-modal') and .//div[contains(text(), 'Excedio MAX')]]")))
        resaltar_elemento(driver, modal)
        tomar_captura(driver, "modal_excedio_max", "Modal de error: Excedio MAX - cantidad supera el valor máximo.", capturas, textos, nombre_automatizacion)
        escribir_log(nombre_automatizacion, "Modal de error 'Excedio MAX' capturado correctamente.")
        boton_ok = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div/div[4]/div/button")))
        resaltar_elemento(driver, boton_ok)
        tomar_captura(driver, "boton_ok_excedio_max", "Botón OK del modal 'Excedio MAX' resaltado.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_ok)
        escribir_log(nombre_automatizacion, "Botón OK del modal 'Excedio MAX' clickeado correctamente.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al capturar o aceptar el modal 'Excedio MAX': {e}")

def restaurar_cantidad_producto_orden(driver, wait, capturas, textos, nombre_automatizacion):
    """Restaura la cantidad del producto en la orden de compra restando 1 al valor actual del input."""
    try:
        # Volver a buscar la referencia y fila actualizadas en la tabla (igual que buscar_producto_en_orden_compra)
        try:
            ref_cell1 = wait.until(EC.visibility_of_element_located((By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[1]/td[1]")))
            primera_referencia = ref_cell1.text.strip()
            input_cantidad1 = driver.find_element(By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[1]//input[contains(@id, 'modificarOrden-')]")
            cantidad1 = int(input_cantidad1.get_attribute("value") or 0)
            escribir_log(nombre_automatizacion, f"[Restaurar] Primera referencia encontrada: {primera_referencia} con cantidad {cantidad1}")
        except Exception as e:
            escribir_log(nombre_automatizacion, f"[Restaurar] No se pudo obtener la primera referencia de la tabla: {e}")
            return

        referencia_a_usar = primera_referencia
        fila_usada = 1
        if cantidad1 <= 1:
            try:
                ref_cell2 = driver.find_element(By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[2]/td[1]")
                segunda_referencia = ref_cell2.text.strip()
                input_cantidad2 = driver.find_element(By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[2]//input[contains(@id, 'modificarOrden-')]")
                cantidad2 = int(input_cantidad2.get_attribute("value") or 0)
                escribir_log(nombre_automatizacion, f"[Restaurar] Segunda referencia encontrada: {segunda_referencia} con cantidad {cantidad2}")
                if cantidad2 > 1:
                    referencia_a_usar = segunda_referencia
                    fila_usada = 2
                else:
                    escribir_log(nombre_automatizacion, "[Restaurar] Ninguna de las dos primeras referencias tiene cantidad mayor a 1. No se restaurará cantidad.")
                    return
            except Exception as e:
                escribir_log(nombre_automatizacion, f"[Restaurar] No se pudo obtener la segunda referencia o su cantidad: {e}")
                return

        # Actualizar el global para el resto del flujo
        global Orden_compra_info
        Orden_compra_info["referencia_a_usar"] = referencia_a_usar
        Orden_compra_info["fila_usada"] = fila_usada

        # Validar que la fila existe antes de operar
        filas = driver.find_elements(By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr")
        escribir_log(nombre_automatizacion, f"[Restaurar] Filas detectadas en la tabla de orden de compra: {len(filas)}. Se intentará usar la fila {fila_usada}.")
        if fila_usada > len(filas) or fila_usada < 1:
            escribir_log(nombre_automatizacion, f"[Restaurar] Fila {fila_usada} no existe en la tabla. No se puede restaurar cantidad.")
            return
        xpath_input = f"//table[@id='tableOrdenCompra']//tbody/tr[{fila_usada}]//input[contains(@id, 'modificarOrden-{referencia_a_usar}')]"
        try:
            input_cantidad = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_input)))
            resaltar_elemento(driver, input_cantidad)
            valor_actual = input_cantidad.get_attribute("value")
            try:
                valor_nuevo = str(int(valor_actual) - 1)
            except Exception:
                valor_nuevo = "1"  # fallback si no es numérico
            input_cantidad.clear()
            time.sleep(0.2)
            input_cantidad.send_keys(valor_nuevo)
            time.sleep(0.2)
            valor_post = input_cantidad.get_attribute("value")
            if valor_post != valor_nuevo:
                driver.execute_script("arguments[0].value = arguments[1];", input_cantidad, valor_nuevo)
                escribir_log(nombre_automatizacion, f"[Restaurar] Valor forzado con JS para {referencia_a_usar}: {valor_nuevo}")
            # Disparar eventos input y change para que el sistema detecte el cambio
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", input_cantidad)
            tomar_captura(driver, f"input_restaurar_cantidad_{referencia_a_usar}", f"Cantidad del producto {referencia_a_usar} ajustada dinámicamente a {valor_nuevo} en la orden de compra.", capturas, textos, nombre_automatizacion)
            escribir_log(nombre_automatizacion, f"[Restaurar] Cantidad del producto {referencia_a_usar} ajustada dinámicamente a {valor_nuevo} en la orden de compra.")
        except Exception as e:
            escribir_log(nombre_automatizacion, f"[Restaurar] No se encontró el input de cantidad en la fila {fila_usada} para la referencia {referencia_a_usar}: {e}")
            return
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al restaurar cantidad del producto en orden de compra: {e}")

def clic_boton_guardar_producto_orden(driver, wait, capturas, textos, nombre_automatizacion):
    """Hace clic en el botón de guardar/cambiar producto en la primera fila de la tabla de la orden de compra."""
    try:
        global Orden_compra_info
        fila_usada = Orden_compra_info.get("fila_usada", 1)
        boton_guardar = wait.until(EC.element_to_be_clickable((By.XPATH, f"//table[@id='tableOrdenCompra']/tbody/tr[{fila_usada}]/td[8]/button")))
        resaltar_elemento(driver, boton_guardar)
        tomar_captura(driver, "boton_guardar_producto_orden", "Aceptar Costo Total", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_guardar)
        escribir_log(nombre_automatizacion, "Aceptar Costo Total clickeado correctamente en la orden de compra.")

        # Esperar a que el valor total se actualice después de guardar
        time.sleep(1.5)
        try:
            header_total_factura = wait.until(EC.visibility_of_element_located((By.XPATH, "//h2[@id='headerTotalFactura']")))
            total_text = header_total_factura.text
            import re
            match = re.search(r"\$([\d,.]+)", total_text)
            if match:
                valor_total_factura = match.group(1).replace(",", "")
                Orden_compra_info["valor_total_factura"] = valor_total_factura
                # Guardar en archivo txt
                with open("valor_total_factura.txt", "w", encoding="utf-8") as f:
                    f.write(valor_total_factura)
                escribir_log(nombre_automatizacion, f"Valor total de la orden capturado y guardado en txt: {valor_total_factura}")
            else:
                escribir_log(nombre_automatizacion, f"No se pudo extraer el valor de: {total_text}")
        except Exception as e:
            escribir_log(nombre_automatizacion, f"Error al capturar el valor total de la orden de <h2 id='headerTotalFactura'>: {e}")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al hacer clic en el botón de guardar/cambiar producto en la orden de compra: {e}")


def clic_boton_actualizar_orden(driver, wait, capturas, textos, nombre_automatizacion):
    """Hace clic en el botón 'Actualizar Orden', toma captura y log."""
    try:
        boton_actualizar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='actualizarOrden']")))
        resaltar_elemento(driver, boton_actualizar)
        tomar_captura(driver, "boton_actualizar_orden", "Botón 'Actualizar Orden' resaltado y listo para hacer clic.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_actualizar)
        escribir_log(nombre_automatizacion, "Botón 'Actualizar Orden' clickeado correctamente.")

    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al hacer clic en el botón 'Actualizar Orden': {e}")

def capturar_y_confirmar_alerta_actualizar(driver, wait, capturas, textos, nombre_automatizacion):
    """Captura el modal de advertencia tras actualizar y hace clic en el botón 'Continuar'."""
    try:
        modal = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'swal-modal') and .//div[contains(text(), 'Los productos no escaneados se pondran en 0.')]]")))
        resaltar_elemento(driver, modal)
        tomar_captura(driver, "modal_alerta_actualizar_orden", "Modal de advertencia: Los productos no escaneados se pondrán en 0.", capturas, textos, nombre_automatizacion)
        escribir_log(nombre_automatizacion, "Modal de advertencia tras actualizar capturado correctamente.")
        boton_continuar = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div/div[4]/div[2]/button")))
        resaltar_elemento(driver, boton_continuar)
        tomar_captura(driver, "boton_continuar_alerta_actualizar", "Botón 'Continuar' del modal de advertencia resaltado.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_continuar)
        escribir_log(nombre_automatizacion, "Botón 'Continuar' del modal de advertencia clickeado correctamente.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al capturar o confirmar el modal de advertencia tras actualizar: {e}")

def escribir_documento_cruce(driver, wait, capturas, textos, nombre_automatizacion, valor="12345678"):
    """Escribe el valor en el input documentoCruce."""
    try:
        # Obtener el valor del primer input hidden en la tabla (ejemplo: id='unidades-XXXXX')
        try:
            hidden_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//table[@id='tableOrdenCompra']//tbody/tr[1]//input[contains(@id, 'unidades-') and @type='hidden']")))
            valor_cruce = hidden_input.get_attribute("value").strip()
            escribir_log(nombre_automatizacion, f"Valor de documento de cruce obtenido de la tabla: {valor_cruce}")
        except Exception as e:
            escribir_log(nombre_automatizacion, f"No se pudo obtener el valor de documento de cruce de la tabla, usando valor por defecto: {e}")
            valor_cruce = valor

        input_cruce = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='documentoCruce']")))
        resaltar_elemento(driver, input_cruce)
        input_cruce.clear()
        input_cruce.send_keys(valor_cruce)
        tomar_captura(driver, "input_documento_cruce", f"Se ingresó el documento de cruce: {valor_cruce}.", capturas, textos, nombre_automatizacion)
        escribir_log(nombre_automatizacion, f"Documento de cruce {valor_cruce} ingresado correctamente.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar documento de cruce: {e}")

def poner_valor_factura_total(driver, wait, capturas, textos, nombre_automatizacion):
    """Toma el valor guardado de headerTotal (total de la orden) y lo pone en valorFactura."""
    try:
        global Orden_compra_info
        valor_factura = Orden_compra_info.get("valor_total_factura", "")
        if not valor_factura:
            # Intentar leer de archivo si no está en memoria
            try:
                with open("valor_total_factura.txt", "r", encoding="utf-8") as f:
                    valor_factura = f.read().strip()
                escribir_log(nombre_automatizacion, f"Valor de factura leído desde archivo txt: {valor_factura}")
            except Exception as e:
                escribir_log(nombre_automatizacion, f"No se pudo leer valor de factura desde archivo txt: {e}")
                valor_factura = ""
        valor = "$" + valor_factura if valor_factura else ""
        input_valor = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='valorFactura']")))
        resaltar_elemento(driver, input_valor)
        input_valor.clear()
        input_valor.send_keys(valor)
        tomar_captura(driver, "input_valor_factura", f"Se ingresó el valor de la factura: {valor}.", capturas, textos, nombre_automatizacion)
        escribir_log(nombre_automatizacion, f"Valor de factura {valor} ingresado correctamente.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al ingresar valor de factura: {e}")

def clic_boton_concretar_orden_compra(driver, wait, capturas, textos, nombre_automatizacion, tiempo_espera=2):
    """Hace clic en el botón 'Concretar Orden Compra', toma captura y espera un tiempo."""
    try:
        boton_concretar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='concretarOrdenCompra']")))
        resaltar_elemento(driver, boton_concretar)
        tomar_captura(driver, "boton_concretar_orden_compra", "Botón 'Concretar Orden Compra' resaltado y listo para hacer clic.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", boton_concretar)
        escribir_log(nombre_automatizacion, "Botón 'Concretar Orden Compra' clickeado correctamente.")
        time.sleep(tiempo_espera)
    except Exception as e:
        escribir_log(nombre_automatizacion, f"Error al hacer clic en el botón 'Concretar Orden Compra': {e}")

def capturar_mensaje_exito_actualizacion(driver, wait, capturas, textos, nombre_automatizacion):
    """Captura el mensaje de éxito tras actualizar la orden de compra (alert-success)."""
    try:
        mensaje_exito = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//div[@id='ordenCompra']//div[contains(@class, 'alert-success') and contains(., 'Orden de compra actualizada exitosamente.')]"))
        )
        resaltar_elemento(driver, mensaje_exito)
        tomar_captura(driver, "mensaje_exito_actualizacion_orden", "Mensaje de éxito: Orden de compra actualizada exitosamente.", capturas, textos, nombre_automatizacion)
        escribir_log(nombre_automatizacion, "Mensaje de éxito de actualización de orden de compra capturado correctamente.")
    except Exception as e:
        escribir_log(nombre_automatizacion, f"No se encontró el mensaje de éxito de actualización de orden de compra: {e}")


def orden_y_actualizacion(driver):
    
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "orden_compra_pdf"

    try:
        # Limpiar el contenido de valor_total_factura.txt al inicio de la automatización
        try:
            with open("valor_total_factura.txt", "w", encoding="utf-8") as f:
                f.write("")
            escribir_log(nombre_automatizacion, "Contenido de valor_total_factura.txt limpiado al inicio de la automatización.")
        except Exception as e:
            escribir_log(nombre_automatizacion, f"No se pudo limpiar valor_total_factura.txt: {e}")
        Orden_compra_info["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mostrar_mensaje(driver, "Se inició el proceso de orden de compra y actualización.", nombre_automatizacion)
        time.sleep(1)
        tomar_captura(driver, "Administrador", "Se inició el proceso de orden de compra y actualización.", capturas, textos, nombre_automatizacion)
        navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion)
        ordenar_compra(driver, wait, capturas, textos, nombre_automatizacion)
        anular_todas_las_ordenes(driver, wait, capturas, textos, nombre_automatizacion)
        generar_boton(driver, capturas, textos, nombre_automatizacion)
        buscar_y_seleccionar_nit(driver, wait, capturas, textos, nombre_automatizacion, nit="900818921")
        generar_orden(driver, wait, capturas, textos, nombre_automatizacion)
        capturar_mensaje_exito_orden(driver, wait, capturas, textos, nombre_automatizacion)
        clic_boton_volver_orden(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_ultima_orden_generada(driver, wait, capturas, textos, nombre_automatizacion)
        buscar_producto_en_orden_compra(driver, wait, capturas, textos, nombre_automatizacion)
        modificar_cantidad_producto_orden(driver, wait, capturas, textos, nombre_automatizacion)
        capturar_y_aceptar_alerta_max(driver, wait, capturas, textos, nombre_automatizacion)
        restaurar_cantidad_producto_orden(driver, wait, capturas, textos, nombre_automatizacion)
        clic_boton_guardar_producto_orden(driver, wait, capturas, textos, nombre_automatizacion)
        clic_boton_actualizar_orden(driver, wait, capturas, textos, nombre_automatizacion)
        capturar_y_confirmar_alerta_actualizar(driver, wait, capturas, textos, nombre_automatizacion)
        escribir_documento_cruce(driver, wait, capturas, textos, nombre_automatizacion)
        poner_valor_factura_total(driver, wait, capturas, textos, nombre_automatizacion)
        clic_boton_concretar_orden_compra(driver, wait, capturas, textos, nombre_automatizacion, tiempo_espera=1)

        # Capturar mensaje de éxito final de actualización de orden de compra
        capturar_mensaje_exito_actualizacion(driver, wait, capturas, textos, nombre_automatizacion)

        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles de Orden de Compra: Timestamp: {Orden_compra_info.get('timestamp', 'No capturado')}")
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de venta con Orden de Compra: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise
   