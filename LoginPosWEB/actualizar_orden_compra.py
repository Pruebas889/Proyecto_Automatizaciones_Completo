"""
Script para automatizar la actualización de la orden de compra
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException
from selenium.webdriver.common.keys import Keys
from generacion_pdf import generar_pdf_consolidado, escribir_log

# Función para resaltar un elemento en rojo
def resaltar_elemento(driver, elemento, color="green", grosor="3px", duracion_ms=1500):
    driver.execute_script(f"""
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
    """, elemento)

# Función para ejecutar la asignación de caja sin abrir otro navegador
def actualizar_orden(driver):
    """
    Realiza la generación de orden de compra.
    """
    wait = WebDriverWait(driver, 20)
    capturas = []  # Lista para guardar las rutas de las capturas
    textos = []  # Lista para guardar los textos de descripción
    nombre_automatizacion = "actualizar_orden_compra_pdf"

    try:
        # Abre el menú lateral
        logo = driver.find_element(By.CSS_SELECTOR, ".logo")
        resaltar_elemento(driver, logo)
        driver.execute_script("arguments[0].click();", logo)
        time.sleep(0.5)
        escribir_log(nombre_automatizacion, "Se abrió el menú lateral.")

        driver.execute_script("""
            if (document.body) {
                var div = document.createElement('div');
                div.innerHTML = 'Se realiza la actualización de orden de compra';
                div.style.position = 'fixed';
                div.style.top = '10px';
                div.style.right = '10px';
                div.style.backgroundColor = 'yellow';
                div.style.padding = '10px';
                div.style.fontSize = '20px';
                div.style.zIndex = '9999';
                div.id = 'mensaje_login';
                document.body.appendChild(div);
            } else {
                console.log('Error: document.body is null');
            }
        """)
        # 📌 Captura y texto: Acceso al módulo 'Administrador'
        ruta_captura_admin = "captura_inicio.png"
        driver.save_screenshot(ruta_captura_admin)
        capturas.append(ruta_captura_admin)
        textos.append("Se realizará el proceso de generación de orden de compra.")

        # 🔑 Clic en "Administrador"
        menu_administrador = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.wrapper > aside > section > ul > li:nth-child(2) > a")))
        resaltar_elemento(driver, menu_administrador)
        driver.execute_script("arguments[0].click();", menu_administrador)
        time.sleep(1)

        # 📌 Captura y texto: Acceso al módulo 'Administrador'
        ruta_captura_admin = "captura_admin.png"
        driver.save_screenshot(ruta_captura_admin)
        capturas.append(ruta_captura_admin)
        textos.append("El usuario accedió correctamente al módulo 'Administrador.")
        escribir_log(nombre_automatizacion, "El usuario accedió correctamente al módulo 'Administrador.")
        time.sleep(1)

        # 🔑 Clic en el menú de "Orden de Compra"
        orden_de_compra = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/aside/section/ul/li[2]/ul/li[11]/a")))
        resaltar_elemento(driver, orden_de_compra)
        driver.execute_script("arguments[0].click();", orden_de_compra)

        # 📌 Captura y texto: Acceso al menú 'Orden de Compra'
        ruta_captura_orden_de_compra = "captura_orden_de_compra.png"
        driver.save_screenshot(ruta_captura_orden_de_compra)
        capturas.append(ruta_captura_orden_de_compra)
        textos.append("El usuario accedió correctamente al menú 'Orden de Compra.")
        escribir_log(nombre_automatizacion, "El usuario accedió correctamente al menú 'Orden de Compra.")
        time.sleep(1)

        # 🔑 Clic en "Orden de Compra"
        orden_compra = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'panelOrdenCompra')]")))
        resaltar_elemento(driver, orden_compra)
        driver.execute_script("arguments[0].click();", orden_compra)

        # 📌 Captura y texto: Acceso al panel 'Orden de Compra'
        ruta_captura_orden_compra = "captura_orden_compra.png"
        driver.save_screenshot(ruta_captura_orden_compra)
        capturas.append(ruta_captura_orden_compra)
        textos.append("El usuario accedió correctamente al panel de 'Orden de Compra.")
        escribir_log(nombre_automatizacion, "El usuario accedió correctamente al panel de 'Orden de Compra.")
        time.sleep(1)

        driver.execute_script("window.scrollBy(0, 300);")

        #Encuentra el primer producto, y toma su referencia para poder actualizar la orden
        producto_referencia = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='tableOrdenCompra']/tbody/tr[1]/td[1]")))
        resaltar_elemento(driver, producto_referencia)
        driver.execute_script("arguments[0].click();", producto_referencia)

        # Encuentra el primer producto y extrae su referencia
        producto_referencia = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='tableOrdenCompra']/tbody/tr[1]/td[1]")))
        referencia_producto = producto_referencia.text  # Captura el número de referencia

        print(f"Referencia del producto: {referencia_producto}")  # Para verificar

        # 📌 Captura y texto: Referencia obtenida correctamente
        ruta_captura_referencia = "captura_referencia.png"
        driver.save_screenshot(ruta_captura_referencia)
        capturas.append(ruta_captura_referencia)
        textos.append(f"Se ha extraído correctamente la referencia del producto: {referencia_producto}")
        escribir_log(nombre_automatizacion, f"Se ha extraído correctamente la referencia del producto: {referencia_producto}")
        time.sleep(1)

        # 🔎 Clic en "Buscar Referencia"
        buscar_referencia = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='BuscarProductoOrdenCompra']")))
        resaltar_elemento(driver, buscar_referencia)
        driver.execute_script("arguments[0].click();", buscar_referencia)
        time.sleep(0.5)

        # 🔢 Ingresar la referencia en el campo de búsqueda
        buscar_referencia.send_keys(referencia_producto)
        buscar_referencia.send_keys(Keys.RETURN)  # Presiona Enter para realizar la búsqueda

        # 📌 Captura y texto: Referencia ingresada en la búsqueda
        ruta_captura_busqueda_referencia = "captura_busqueda_referencia.png"
        driver.save_screenshot(ruta_captura_busqueda_referencia)
        capturas.append(ruta_captura_busqueda_referencia)
        textos.append(f"El usuario ha ingresado correctamente la referencia '{referencia_producto}' en el campo de búsqueda.")
        escribir_log(nombre_automatizacion, f"El usuario ha ingresado correctamente la referencia '{referencia_producto}' en el campo de búsqueda.")
        time.sleep(1)

        # 🔎 Clic en la celda que contiene el campo de entrada
        clic_unidades = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='tableOrdenCompra']/tbody/tr[1]/td[3]")))
        resaltar_elemento(driver, clic_unidades)
        driver.execute_script("arguments[0].click();", clic_unidades)
        time.sleep(1)

        # 📌 Ahora espera que el campo dentro de la celda esté disponible
        campo_unidades = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='tableOrdenCompra']/tbody/tr[1]/td[3]//input")))

        # 🔄 Asegurar que el campo esté activo
        campo_unidades.click()
        time.sleep(1)

        # 🔄 Seleccionar todo el contenido y borrarlo
        campo_unidades.send_keys(Keys.CONTROL, "a")  # En Windows/Linux
        campo_unidades.send_keys(Keys.DELETE)
        time.sleep(1)  # Pausa corta para asegurar la eliminación

        # 🔢 Escribir el nuevo valor "2"
        campo_unidades.send_keys("2")
        time.sleep(1)  # Pequeña pausa antes de confirmar

        # ✅ Presionar Enter para confirmar
        campo_unidades.send_keys(Keys.RETURN)

        # 📌 Captura y texto: Unidad modificada correctamente
        ruta_captura_unidades_modificado = "captura_unidades_modificado.png"
        driver.save_screenshot(ruta_captura_unidades_modificado)
        capturas.append(ruta_captura_unidades_modificado)
        textos.append("El usuario ha ingresado correctamente la cantidad '2' en el campo de unidades.")
        escribir_log(nombre_automatizacion, "El usuario ha ingresado correctamente la cantidad '2' en el campo de unidades.")
        time.sleep(1)

        # 🔑 Extraer el valor de "Orden de Factura"
        orden_factura = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='headerTotalFactura']")))
        valor_extraido = orden_factura.text  # Captura el número de factura

        print(f"Valor extraído de Orden de Factura: {valor_extraido}")  # Para verificar

        # 📌 Captura y texto: Valor extraído correctamente
        ruta_captura_orden_factura = "captura_orden_factura.png"
        driver.save_screenshot(ruta_captura_orden_factura)
        capturas.append(ruta_captura_orden_factura)
        textos.append(f"Se ha extraído correctamente el valor '{valor_extraido}' de la Orden de Factura.")
        escribir_log(nombre_automatizacion, "Se ha extraído correctamente el valor '{valor_extraido}' de la Orden de Factura.")
        time.sleep(1)

        # 🔑 Clic en "Aprobación"
        clic_aprobación = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='tableOrdenCompra']/tbody/tr[1]/td[8]/button")))
        resaltar_elemento(driver, clic_aprobación)
        driver.execute_script("arguments[0].click();", clic_aprobación)

        # 📌 Captura y texto: Orden aprobada correctamente
        ruta_captura_aprobacion = "captura_aprobacion.png"
        driver.save_screenshot(ruta_captura_aprobacion)
        capturas.append(ruta_captura_aprobacion)
        textos.append("El usuario ha aprobado la orden de compra correctamente.")
        escribir_log(nombre_automatizacion, "El usuario ha aprobado la orden de compra correctamente.")
        time.sleep(1)

        # 🔑 Seleccionar "Orden de Factura"
        orden_factura = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='headerTotalFactura']")))
        resaltar_elemento(driver, orden_factura)
        driver.execute_script("arguments[0].click();", orden_factura)
        escribir_log(nombre_automatizacion, "")
        time.sleep(1)

        # 🔑 Clic en "Actualizar orden"
        actualizacion_orden = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='actualizarOrden']")))
        resaltar_elemento(driver, actualizacion_orden)
        driver.execute_script("arguments[0].click();", actualizacion_orden)

        # 📌 Captura y texto: Orden actualizada correctamente
        ruta_captura_orden_actualizada = "captura_orden_actualizada.png"
        driver.save_screenshot(ruta_captura_orden_actualizada)
        capturas.append(ruta_captura_orden_actualizada)
        textos.append("El usuario ha actualizado la orden correctamente.")
        escribir_log(nombre_automatizacion, "El usuario ha actualizado la orden correctamente.")
        time.sleep(1)

        # 🔑 Clic en "Continuar"
        clic_continuar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.swal-overlay.swal-overlay--show-modal > div > div.swal-footer > div:nth-child(2) > button")))
        resaltar_elemento(driver, clic_continuar)
        driver.execute_script("arguments[0].click();", clic_continuar)
        time.sleep(1)

        # 📌 Captura y texto: Confirmación de la actualización
        ruta_captura_continuar = "captura_continuar.png"
        driver.save_screenshot(ruta_captura_continuar)
        capturas.append(ruta_captura_continuar)
        textos.append("El usuario ha confirmado la actualización de la orden.")
        escribir_log(nombre_automatizacion, "El usuario ha confirmado la actualización de la orden.")
        time.sleep(1)

        # 🔑 Clic en "Número de Factura"
        numero_factura = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='documentoCruce']")))
        resaltar_elemento(driver, numero_factura)
        driver.execute_script("arguments[0].click();", numero_factura)
        time.sleep(1)

        # 📌 Captura y texto: Campo de número de factura activado
        ruta_captura_numero_factura = "captura_numero_factura.png"
        driver.save_screenshot(ruta_captura_numero_factura)
        capturas.append(ruta_captura_numero_factura)
        textos.append("El usuario ha activado correctamente el campo de número de factura.")
        escribir_log(nombre_automatizacion, "El usuario ha activado correctamente el campo de número de factura.")
        time.sleep(1)

        # 🔢 Escribir el número de factura y confirmar con 'Tab'
        numero_factura.send_keys("12345678")
        numero_factura.send_keys(Keys.TAB)

        # 📌 Captura y texto: Número de factura ingresado correctamente
        ruta_captura_factura_ingresada = "captura_factura_ingresada.png"
        driver.save_screenshot(ruta_captura_factura_ingresada)
        capturas.append(ruta_captura_factura_ingresada)
        textos.append("El usuario ha ingresado correctamente el número de factura '12345678.")
        escribir_log(nombre_automatizacion, "El usuario ha ingresado correctamente el número de factura '12345678.")
        time.sleep(1)

        # 🔑 Clic en "Valor de Factura"
        valor_factura = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='valorFactura']")))
        resaltar_elemento(driver, valor_factura)
        driver.execute_script("arguments[0].click();", valor_factura)
        time.sleep(1)

        # 📌 Asegurar que el campo de entrada esté activo
        campo_valor_factura = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='valorFactura']")))
        campo_valor_factura.click()
        time.sleep(1)

        # 🔄 Borrar cualquier valor previo en el campo
        campo_valor_factura.send_keys(Keys.CONTROL, "a")  # Seleccionar todo el texto existente
        campo_valor_factura.send_keys(Keys.DELETE)  # Borrar el contenido actual
        time.sleep(1)

        # 🔢 Escribir el valor extraído
        campo_valor_factura.send_keys(valor_extraido)
        time.sleep(1)

        # ✅ Presionar Enter para confirmar
        campo_valor_factura.send_keys(Keys.RETURN)

        # 📌 Captura y texto: Valor de Factura ingresado correctamente
        ruta_captura_valor_factura = "captura_valor_factura.png"
        driver.save_screenshot(ruta_captura_valor_factura)
        capturas.append(ruta_captura_valor_factura)
        textos.append(f"El usuario ha ingresado correctamente el valor '{valor_extraido}' en el campo de Factura.")
        escribir_log(nombre_automatizacion, "El usuario ha ingresado correctamente el valor '{valor_extraido}' en el campo de Factura.")
        time.sleep(1)

        # 🔑 Clic en "Concretar Orden"
        concretar_orden = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='concretarOrdenCompra']")))
        resaltar_elemento(driver, concretar_orden)
        driver.execute_script("arguments[0].click();", concretar_orden)
        time.sleep(1)

        # 📌 Captura y texto: Orden de compra concretada correctamente
        ruta_captura_concretar_orden = "captura_concretar_orden.png"
        driver.save_screenshot(ruta_captura_concretar_orden)
        capturas.append(ruta_captura_concretar_orden)
        textos.append("El usuario ha concretado correctamente la orden de compra.")
        escribir_log(nombre_automatizacion, "El usuario ha concretado correctamente la orden de compra.")
        time.sleep(1)

        # 🔄 Ajustar desplazamiento de la ventana
        driver.execute_script("window.scrollBy(0, -300);")

        # 📌 Captura y texto: Vista final después de concretar la orden
        ruta_captura_final = "captura_vista_final.png"
        driver.save_screenshot(ruta_captura_final)
        capturas.append(ruta_captura_final)
        textos.append("El sistema ha ajustado la vista después de concretar la orden de compra.")
        escribir_log(nombre_automatizacion, "El sistema ha ajustado la vista después de concretar la orden de compra.")

        # Generar PDF consolidado
        generar_pdf_consolidado("actualizar_orden_compra_pdf", capturas, textos)

    except (TimeoutException, NoSuchElementException, NoSuchWindowException) as e:
        logging.error(f"❌ Error durante el proceso: {e}")
    except WebDriverException as e:
        logging.error(f"❌ Error de webdriver: {e}")