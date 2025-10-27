"""
Script para automatizar la generación de la orden de compra
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException
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
def orden_compra(driver):
    """
    Realiza la generación de orden de compra.
    """
    wait = WebDriverWait(driver, 20)
    capturas = []  # Lista para guardar las rutas de las capturas
    textos = []  # Lista para guardar los textos de descripción
    nombre_automatizacion = "generar_orden_compra_pdf"
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
                div.innerHTML = 'Se realiza la generación de orden de compra';
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

        # 🔑 Clic en "Orden de Compra"
        orden_de_compra = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/aside/section/ul/li[2]/ul/li[11]/a")))
        resaltar_elemento(driver, orden_de_compra)
        driver.execute_script("arguments[0].click();", orden_de_compra)
        time.sleep(1)

        # 📌 Captura y texto: Acceso a 'Orden de Compra'
        ruta_captura_orden_compra = "captura_orden_compra.png"
        driver.save_screenshot(ruta_captura_orden_compra)
        capturas.append(ruta_captura_orden_compra)
        textos.append("El usuario accedió correctamente al módulo 'Orden de Compra.")

        # 🔑 Clic en "Generar"
        clic_generar = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div/section[1]/div/div[2]/a")))
        resaltar_elemento(driver, clic_generar)
        driver.execute_script("arguments[0].click();", clic_generar)
        time.sleep(1)
        driver.execute_script("window.scrollBy(0, 100);")

        # 📌 Captura y texto: Generación de orden de compra iniciada
        ruta_captura_generar_orden = "captura_generar_orden.png"
        driver.save_screenshot(ruta_captura_generar_orden)
        capturas.append(ruta_captura_generar_orden)
        textos.append("El usuario ha iniciado correctamente la generación de la orden de compra.")

        # 🔎 Clic en "Search" para buscar el distribuidor
        clic_search = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='DataTables_Table_0']/thead/tr[2]/td[2]/input")))
        resaltar_elemento(driver, clic_search)
        driver.execute_script("arguments[0].click();", clic_search)
        time.sleep(1)
        clic_search.send_keys("MEALS")
        time.sleep(3)

        # 📌 Captura y texto: Búsqueda del distribuidor en la orden de compra
        ruta_captura_busqueda_meals = "captura_busqueda_meals.png"
        driver.save_screenshot(ruta_captura_busqueda_meals)
        capturas.append(ruta_captura_busqueda_meals)
        textos.append("El usuario ha realizado correctamente la búsqueda del distribuidor 'MEALS DE COLOMBIA S.A..")

        # 🔑 Clic en "MEALS DE COLOMBIA S.A." para generar orden de compra
        meals_orden = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div/section[3]/div[8]/div/div[2]/div/div[1]/table/tbody/tr/td[1]")))
        resaltar_elemento(driver, meals_orden)
        driver.execute_script("arguments[0].click();", meals_orden)
        time.sleep(1)

        # 📌 Captura y texto: Selección del distribuidor
        ruta_captura_seleccion_meals = "captura_seleccion_meals.png"
        driver.save_screenshot(ruta_captura_seleccion_meals)
        capturas.append(ruta_captura_seleccion_meals)
        textos.append("El usuario ha seleccionado correctamente el distribuidor 'MEALS DE COLOMBIA S.A..")

        # 🔑 Clic en "Generar orden" 
        generar_orden = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='generarOrden']")))
        resaltar_elemento(driver, generar_orden)
        driver.execute_script("arguments[0].click();", generar_orden)
        time.sleep(1)
        driver.execute_script("window.scrollBy(0, 1500);")

        # 📌 Captura y texto: Orden de compra generada correctamente
        ruta_captura_orden_generada = "captura_orden_generada.png"
        driver.save_screenshot(ruta_captura_orden_generada)
        capturas.append(ruta_captura_orden_generada)
        textos.append("El usuario ha generado correctamente la orden de compra.")

        # Generar PDF consolidado
        generar_pdf_consolidado("generar_orden_compra_pdf", capturas, textos)

    except (TimeoutException, NoSuchElementException, NoSuchWindowException) as e:
        logging.error(f"❌ Error durante el proceso: {e}")
    except WebDriverException as e:
        logging.error(f"❌ Error de webdriver: {e}")
        