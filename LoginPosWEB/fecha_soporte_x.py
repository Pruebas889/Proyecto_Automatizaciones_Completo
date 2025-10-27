"""
Script para automatizar la configuración con Selenium
"""
from datetime import datetime
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException
from selenium.webdriver.common.keys import Keys
from generacion_pdf import generar_pdf_consolidado, escribir_log  # Generador de PDF y logger

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
def configuracion_dia(driver):
    """
    Realiza la configuración del día.
    """
    wait = WebDriverWait(driver, 20)
    capturas = []  # Lista para guardar las rutas de las capturas
    textos = []  # Lista para guardar los textos de descripción
    nombre_automatizacion = "configuracion_dia_pdf"


    try:
        driver.execute_script("""
            if (document.body) {
                var div = document.createElement('div');
                div.innerHTML = 'Se realiza la Configuración';
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

        # Captura y texto: Inicio del proceso de ventas
        ruta_captura_inicio = "configuracion.png"
        driver.save_screenshot(ruta_captura_inicio)
        capturas.append(ruta_captura_inicio)
        textos.append("Se inició el proceso de configuración correctamente.")

        # Clic en "Configuración"
        menu_configuracion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > aside > section > ul > li:nth-child(6) > a")))
        resaltar_elemento(driver, menu_configuracion)
        driver.execute_script("arguments[0].click();", menu_configuracion)
        time.sleep(1)
        escribir_log(nombre_automatizacion, "Acceso al menú 'Configuración' correctamente")

        # Captura y texto: Acceso al menú Configuración
        ruta_captura_configuracion = "captura_configuracion.png"
        driver.save_screenshot(ruta_captura_configuracion)
        capturas.append(ruta_captura_configuracion)
        textos.append("Acceso al menú Configuración realizado correctamente.")

        # Clic en "Inicio"
        menu_inicio = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > aside > section > ul > li.active > ul > li:nth-child(2) > a")))
        resaltar_elemento(driver, menu_inicio)
        driver.execute_script("arguments[0].click();", menu_inicio)
        time.sleep(1)
        escribir_log(nombre_automatizacion, "Se hizo clic correctamente en el menú de 'inicio'")

        # Captura y texto: Acceso a inicio
        ruta_captura_inicio = "captura_inicio.png"
        driver.save_screenshot(ruta_captura_inicio)
        capturas.append(ruta_captura_inicio)
        textos.append("Acceso al módulo Inicio realizado correctamente.")

        # Cierra el menú lateral
        cerrar_menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='sidebar-toggle']")))
        resaltar_elemento(driver, cerrar_menu)
        driver.execute_script("arguments[0].click();", cerrar_menu)
        time.sleep(1)
        escribir_log(nombre_automatizacion, "Se cerró correctamente el menú lateral")

        #Clic en #Limpiar Fecha"
        clic_limpiar_fecha = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='w0-kvdate']/span[2]")))
        resaltar_elemento(driver, clic_limpiar_fecha)
        driver.execute_script("arguments[0].click();", clic_limpiar_fecha)
        time.sleep(1)
        escribir_log(nombre_automatizacion, "Se limpió el campo actual")

        # Captura y texto: Limpiar Fecha 
        ruta_captura_clic_limpiar_fecha = "captura_limpiar_fecha.png"
        driver.save_screenshot(ruta_captura_clic_limpiar_fecha)
        capturas.append(ruta_captura_clic_limpiar_fecha)
        textos.append("El usuario limpio correctamente la fecha que se encontraba en el campo.")

        #Clic en #Seleccionar Fecha"
        clic_seleccionar_fecha = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='w0-kvdate']/span[1]")))
        resaltar_elemento(driver, clic_seleccionar_fecha)
        driver.execute_script("arguments[0].click();", clic_seleccionar_fecha)
        time.sleep(1)
        escribir_log(nombre_automatizacion, "Se seleccionó correctamente el botón de la fecha")

        # Captura y texto: Clic en Seleccionar Fecha
        ruta_captura_clic_seleccionar_fecha = "captura_seleccionar_fecha.png"
        driver.save_screenshot(ruta_captura_clic_seleccionar_fecha)
        capturas.append(ruta_captura_clic_seleccionar_fecha)
        textos.append("El usuario hizo clic correctamente en el botón de selección de fecha.")

        # Obtener la fecha actual en formato YYYY-MM-DD
        fecha_hoy = datetime.today().strftime('%Y-%m-%d')

        # Esperar a que el campo esté disponible
        campo_fecha = wait.until(EC.presence_of_element_located((By.ID, "w0")))

        # Usar JavaScript para establecer la fecha en el campo
        driver.execute_script(f"arguments[0].value = '{fecha_hoy}';", campo_fecha)
        campo_fecha.send_keys(Keys.RETURN)
        escribir_log(nombre_automatizacion, "Se escribió correctamente la fecha en el campo.")

        # Captura y texto: Fecha establecida correctamente
        ruta_captura_fecha_seleccionada = "captura_fecha_seleccionada.png"
        driver.save_screenshot(ruta_captura_fecha_seleccionada)
        capturas.append(ruta_captura_fecha_seleccionada)
        textos.append(f"El usuario ha seleccionado correctamente la fecha '{fecha_hoy}' en el campo de fecha.")

        #Clic en #Guardar"
        clic_guardar = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='botonGuardarDatosBasicos']")))
        resaltar_elemento(driver, clic_guardar)
        driver.execute_script("arguments[0].click();", clic_guardar)
        time.sleep(1)
        escribir_log(nombre_automatizacion, "Se hizo clic en el botón 'Guardar'correctamente.")

        # Captura y texto: Clic en Guardar Datos Básicos
        ruta_captura_clic_guardar_datos_basicos = "captura_guardar_datos_basicos.png"
        driver.save_screenshot(ruta_captura_clic_guardar_datos_basicos)
        capturas.append(ruta_captura_clic_guardar_datos_basicos)
        textos.append("El usuario hizo clic correctamente en el botón de Guardar Datos Básicos.")

        # Generar PDF consolidado
        generar_pdf_consolidado("configuracion_dia_pdf", capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente")

        escribir_log(nombre_automatizacion, "Configuración completada")

    except (TimeoutException, NoSuchElementException, NoSuchWindowException) as e:
        logging.error(f"❌ Error durante el proceso: {e}")
    except WebDriverException as e:
        logging.error(f"❌ Error de webdriver: {e}")