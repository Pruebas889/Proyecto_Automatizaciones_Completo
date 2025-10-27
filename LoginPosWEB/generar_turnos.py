"""
Script para automatizar la generación de turnos del empleado
"""
import time
import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)
from generacion_pdf import generar_pdf_consolidado, escribir_log

# Global variable to store shift information
turnos_info = {}

def resaltar_elemento(driver, elemento, color="green", grosor="3px", duracion_ms=1500):
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
        # escribir_log(nombre_automatizacion, f"Captura tomada: {ruta_captura}") # descomentar si s requiere ver la adicion de las imagenes por medio del log
        # Agregar el texto a la lista de textos con nombre de captura
        time.sleep(1)
    except WebDriverException as e:
        escribir_log(nombre_automatizacion, f"Error al tomar captura {nombre_archivo}: {e}")
        raise

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

def navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_administrador = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.wrapper > aside > section > ul > li:nth-child(2) > a")))
        resaltar_elemento(driver, menu_administrador)
        tomar_captura(driver, "captura_menu_admin", "Acceso al menú 'Administrador' realizado correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", menu_administrador)
        escribir_log(nombre_automatizacion, "Accedió al menú 'Administrador' correctamente.")
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Administrador': {e}")
        raise

def navegar_a_turnos(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_turnos = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/aside/section/ul/li[2]/ul/li[15]/a")))
        resaltar_elemento(driver, menu_turnos)
        driver.execute_script("arguments[0].click();", menu_turnos)
        escribir_log(nombre_automatizacion, "Accedió al módulo 'Turnos' correctamente.")
        tomar_captura(driver, "captura_menu_turnos", "Acceso al módulo 'Turnos' realizado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al navegar a 'Turnos': {e}")
        raise

def seleccionar_empleado(driver, wait, capturas, textos, nombre_automatizacion, documento="70165482"):
    try:
        documento_empleado = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='DocumentoEmpleado']")))
        resaltar_elemento(driver, documento_empleado)
        driver.execute_script("arguments[0].click();", documento_empleado)
        documento_empleado.send_keys(documento)
        documento_empleado.send_keys(Keys.ENTER)
        time.sleep(1)
        documento_empleado.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        documento_empleado.send_keys(Keys.ENTER)
        time.sleep(1)
        escribir_log(nombre_automatizacion, f"Empleado con documento {documento} seleccionado correctamente.")
        tomar_captura(driver, "captura_seleccion_empleado", f"Empleado con documento {documento} seleccionado correctamente.", capturas, textos, nombre_automatizacion)
        turnos_info["documento_empleado"] = documento
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar empleado: {e}")
        raise

def seleccionar_turno(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        seleccion_turno = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='seleccionTurno']")))
        resaltar_elemento(driver, seleccion_turno)
        driver.execute_script("arguments[0].click();", seleccion_turno)
        escribir_log(nombre_automatizacion, "Turno seleccionado correctamente.")
        tomar_captura(driver, "captura_seleccion_turno", "Turno seleccionado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar turno: {e}")
        raise

def seleccionar_dia_inicial(driver, wait, capturas, textos, nombre_automatizacion, xpath_dia="//div[@class='calendar left']//td[normalize-space(text())='10']"):
    try:
        dia_inicial = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_dia)))
        resaltar_elemento(driver, dia_inicial)

        numero_dia = dia_inicial.get_attribute("innerText").strip()

        driver.execute_script("arguments[0].click();", dia_inicial)
        escribir_log(nombre_automatizacion, "Día inicial seleccionado correctamente.")
        tomar_captura(driver, "captura_dia_inicial", "Día inicial del turno seleccionado correctamente.", capturas, textos, nombre_automatizacion)
        
        turnos_info["dia_inicial"] = numero_dia
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar día inicial: {e}")
        raise

def seleccionar_dia_final(driver, wait, capturas, textos, nombre_automatizacion, xpath_dia="//div[@class='calendar right']//td[normalize-space(text())='10']"):
    try:
        dia_final = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_dia)))
        resaltar_elemento(driver, dia_final)

        # Capturamos directamente el número que aparece en el elemento
        numero_dia = dia_final.get_attribute("innerText").strip()

        driver.execute_script("arguments[0].click();", dia_final)
        escribir_log(nombre_automatizacion, f"Día final '{numero_dia}' seleccionado correctamente.")
        tomar_captura(driver, "captura_dia_final", f"Día final {numero_dia} del turno seleccionado correctamente.", capturas, textos, nombre_automatizacion)

        # Guardamos solo el número del día
        turnos_info["dia_final"] = numero_dia
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al seleccionar día final: {e}")
        raise

def asignar_turno(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        asignar_turno = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Aplicar')]")))
        resaltar_elemento(driver, asignar_turno)
        driver.execute_script("arguments[0].click();", asignar_turno)
        escribir_log(nombre_automatizacion, "Turno asignado correctamente.")
        tomar_captura(driver, "captura_asignar_turno", "Turno asignado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al asignar turno: {e}")
        raise

def guardar_turno(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        guardar_turno = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='guardarTurno']")))
        resaltar_elemento(driver, guardar_turno)
        driver.execute_script("arguments[0].click();", guardar_turno)
        escribir_log(nombre_automatizacion, "Turno guardado correctamente.")
        tomar_captura(driver, "captura_guardar_turno", "Turno guardado correctamente.", capturas, textos, nombre_automatizacion)
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error al guardar turno: {e}")
        raise

def turnos(driver):
    """
    Automatiza el proceso de generación de turnos para un empleado en el sistema, con logs y capturas.
    """
    wait = WebDriverWait(driver, 30)
    capturas = []
    textos = []
    nombre_automatizacion = "generar_turnos_pdf"

    try:
        abrir_menu_lateral(driver, wait, nombre_automatizacion)
        mostrar_mensaje(driver, "Se realiza la Generación de Turnos", nombre_automatizacion)
        tomar_captura(driver, "captura_inicio_turnos", "Se inició el proceso de Generación de Turnos correctamente.", capturas, textos, nombre_automatizacion)

        navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_turnos(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_empleado(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_turno(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_dia_inicial(driver, wait, capturas, textos, nombre_automatizacion)
        seleccionar_dia_final(driver, wait, capturas, textos, nombre_automatizacion)
        asignar_turno(driver, wait, capturas, textos, nombre_automatizacion)
        guardar_turno(driver, wait, capturas, textos, nombre_automatizacion)

        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        print(f"Detalles del turno: Documento empleado: {turnos_info.get('documento_empleado', 'No capturado')}, Día inicial: {turnos_info.get('dia_inicial', 'No capturado')}, Día final: {turnos_info.get('dia_final', 'No capturado')}")

    except (TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de generación de turnos: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise