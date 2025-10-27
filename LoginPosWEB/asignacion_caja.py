"""
Script para automatizar la gestión de caja con Selenium
"""
import time
import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchWindowException,
    WebDriverException,
)
from generacion_pdf import generar_pdf_consolidado, escribir_log

def resaltar_elemento(driver, elemento, color="green", grosor="3px", duracion_ms=2000):
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
        escribir_log(nombre_automatizacion, f"Error al tomar captura {ruta_captura}: {e}") # type: ignore
        raise

def esperar_carga_desaparezca(driver, wait, nombre_automatizacion, contexto):
    try:
        escribir_log(nombre_automatizacion, f"Esperando a que desaparezca el gif de carga tras {contexto}.")
        WebDriverWait(driver, 40).until(EC.invisibility_of_element_located((By.XPATH, "//div[@id='loading']")))
        escribir_log(nombre_automatizacion, f"Gif de carga desaparecido tras {contexto}.")
    except TimeoutException:
        escribir_log(nombre_automatizacion, f"Advertencia: Gif de carga no desapareció tras {contexto}, continuando.")

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

def navegar_a_gestion_caja(driver, wait, capturas, textos, nombre_automatizacion):
    try:
        menu_gestion_caja = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='/administrador/caja/gestionar']")))
        resaltar_elemento(driver, menu_gestion_caja)
        escribir_log(nombre_automatizacion, "Clic en 'Gestión Caja' correcto.")
        tomar_captura(driver, "captura_gestion_caja", "Acceso al módulo Gestión Caja realizado correctamente.", capturas, textos, nombre_automatizacion)
        driver.execute_script("arguments[0].click();", menu_gestion_caja)
    except TimeoutException:
        try:
            menu_gestion_caja = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Gestion Caja')]")))
            resaltar_elemento(driver, menu_gestion_caja)
            escribir_log(nombre_automatizacion, "Clic en 'Gestión Caja' (selector alternativo) correcto.")
            tomar_captura(driver, "captura_gestion_caja", "Acceso al módulo Gestión Caja realizado correctamente.", capturas, textos, nombre_automatizacion)
            driver.execute_script("arguments[0].click();", menu_gestion_caja)
        except TimeoutException:
            escribir_log(nombre_automatizacion, "Error: No se pudo localizar 'Gestión Caja' con selector alternativo.")
            raise

def cerrar_menu_lateral(driver, wait, nombre_automatizacion):
    try:
        cerrar_menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='sidebar-toggle']")))
        resaltar_elemento(driver, cerrar_menu)
        driver.execute_script("arguments[0].click();", cerrar_menu)
        escribir_log(nombre_automatizacion, "Menú lateral cerrado correctamente.")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Advertencia: No se pudo cerrar el menú lateral, continuando.")

def obtener_estado_cajas(driver, nombre_automatizacion):
    estado_10 = "DESCONOCIDO"
    estado_20 = "DESCONOCIDO"
    try:
        estado_10 = driver.find_element(By.ID, "estado-1").text.strip()
        escribir_log(nombre_automatizacion, f"Estado de Caja 10: {estado_10}")
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el elemento 'estado-1'.")
    try:
        estado_20 = driver.find_element(By.ID, "estado-2").text.strip()
        escribir_log(nombre_automatizacion, f"Estado de Caja 20: {estado_20}")
    except NoSuchElementException:
        escribir_log(nombre_automatizacion, "Error: No se encontró el elemento 'estado-2'.")
    return estado_10, estado_20

def cerrar_caja(driver, wait, caja_id, capturas, textos, nombre_automatizacion):
    try:
        boton_cerrar = wait.until(EC.element_to_be_clickable((By.ID, f"cerrar-caja-{caja_id}")))
        resaltar_elemento(driver, boton_cerrar)
        boton_cerrar.click()
        time.sleep(0.5)

        # Asegurarse de que la carpeta existe
        carpeta_capturas = "capturas"
        os.makedirs(carpeta_capturas, exist_ok=True)
        ruta_captura_cerrar = os.path.join(carpeta_capturas, f"Captura_asignacion_caja_04_cerrar_{caja_id * 10}.png")
        driver.save_screenshot(ruta_captura_cerrar)
        capturas.append(ruta_captura_cerrar)
        textos.append(f"Se hizo clic en 'Cerrar Caja {caja_id * 10}' y se muestra la ventana de confirmación.")
        escribir_log(nombre_automatizacion, f"Captura tomada: Ventana de confirmación para cerrar Caja {caja_id * 10}.")
        
        confirmar = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div/div[4]/div[2]/button")))
        resaltar_elemento(driver, confirmar)
        time.sleep(0.5)
        
        confirmar.click()
        time.sleep(0.5)

        ruta_captura_verificacion = os.path.join(carpeta_capturas, "Captura_asignacion_caja_verificacion.png")
        driver.save_screenshot(ruta_captura_verificacion)
        capturas.append(ruta_captura_verificacion)
        textos.append(f"Se verifica el cierre de la Caja {caja_id * 10}.")

        escribir_log(nombre_automatizacion, f"Captura tomada: Cierre de Caja {caja_id * 10} verificado.")
    except (TimeoutException, NoSuchElementException) as e:
        escribir_log(nombre_automatizacion, f"Error al cerrar Caja {caja_id * 10}: {e}")
        raise

def abrir_caja(driver, wait, caja_id, capturas, textos, nombre_automatizacion):
    try:
        boton_abrir = wait.until(EC.element_to_be_clickable((By.ID, f"abrir-caja-{caja_id}")))
        resaltar_elemento(driver, boton_abrir)
        boton_abrir.click()
        time.sleep(0.5)
        # Asegurarse de que la carpeta existe
        carpeta_capturas = "capturas"
        os.makedirs(carpeta_capturas, exist_ok=True)
        ruta_captura_abrir = os.path.join(carpeta_capturas, f"Captura_asignacion_caja_04_abrir_{caja_id * 10}.png")
        driver.save_screenshot(ruta_captura_abrir)
        capturas.append(ruta_captura_abrir)
        textos.append(f"Se procedió a abrir la Caja {caja_id * 10}.")
        escribir_log(nombre_automatizacion, f"Captura tomada: Caja {caja_id * 10} abierta.")
        time.sleep(1)
        escribir_log(nombre_automatizacion, f"Se abrió la Caja {caja_id * 10}")
        return "90" if caja_id == 1 else "91"
    except (TimeoutException, NoSuchElementException) as e:
        escribir_log(nombre_automatizacion, f"Error al abrir Caja {caja_id * 10}: {e}")
        raise

def alternar_cajas(driver, wait, capturas, textos, nombre_automatizacion):
    numero = "0"
    tomar_captura(driver, "captura_caja", "Acceso al módulo Gestión Caja.", capturas, textos, nombre_automatizacion)

    esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "acceder a Gestión Caja")
    estado_10, estado_20 = obtener_estado_cajas(driver, nombre_automatizacion)
    
    if estado_10 == "ABIERTA":
        escribir_log(nombre_automatizacion, "Caja 10 ABIERTA: cerrando 10 y abriendo 20.")
        cerrar_caja(driver, wait, 1, capturas, textos, nombre_automatizacion)
        numero = abrir_caja(driver, wait, 2, capturas, textos, nombre_automatizacion)
    elif estado_20 == "ABIERTA":
        escribir_log(nombre_automatizacion, "Caja 20 ABIERTA: cerrando 20 y abriendo 10.")
        cerrar_caja(driver, wait, 2, capturas, textos, nombre_automatizacion)
        numero = abrir_caja(driver, wait, 1, capturas, textos, nombre_automatizacion)
    else:
        escribir_log(nombre_automatizacion, "Ninguna caja ABIERTA: abriendo Caja 10 por defecto.")
        numero = abrir_caja(driver, wait, 1, capturas, textos, nombre_automatizacion)
    
    with open("caja_asignada.txt", "w") as f:
        f.write(str(numero))
    return numero

def asignar_cajero(driver, wait, capturas, textos, nombre_automatizacion, documento="70165482"):
    try:
        cajero_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@id='NumeroDocumentoCajero']")))
        resaltar_elemento(driver, cajero_input)
        time.sleep(0.5)
        driver.execute_script("arguments[0].value = '';", cajero_input)
        cajero_input.send_keys(documento)
        escribir_log(nombre_automatizacion, "Cédula del cajero ingresada.")
        tomar_captura(driver, "Captura_asignacion_caja_05_cedula_cajero", "Se ingresó el número de documento del cajero correctamente.", capturas, textos, nombre_automatizacion)
        
        vendedor_fijo = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@id='VendedorFijo']")))
        resaltar_elemento(driver, vendedor_fijo)
        driver.execute_script("arguments[0].click();", vendedor_fijo)
        escribir_log(nombre_automatizacion, "Opción 'Vendedor Fijo' marcada.")
        tomar_captura(driver, "Captura_opcion_vendedor_fijo", "Se marcó la opción de 'Vendedor Fijo'.", capturas, textos, nombre_automatizacion)
        
        cajero_asignado = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='AsignarCajero']")))
        resaltar_elemento(driver, cajero_asignado)
        driver.execute_script("arguments[0].click();", cajero_asignado)
        escribir_log(nombre_automatizacion, "Cajero asignado correctamente.")
        esperar_carga_desaparezca(driver, wait, nombre_automatizacion, "asignar cajero")
        
    except (TimeoutException, NoSuchElementException) as e:
        escribir_log(nombre_automatizacion, f"Error al asignar cajero: {e}")
        raise

def verificar_cajero_asignado(driver, wait, numero_caja, nombre_automatizacion, capturas, textos):
    try:
        if numero_caja == "90":
            persona_asignada = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="usuario-asignador-1"]')))
            resaltar_elemento(driver, persona_asignada)
            escribir_log(nombre_automatizacion, "Cajero asignado verificado para Caja 10.")
            time.sleep(0.5)
            tomar_captura(driver, "Captura_asignacion_caja_06_cajero_asignado", "Asignación de cajero realizada correctamente.", capturas, textos, nombre_automatizacion)
        elif numero_caja == "91":
            persona_asignada = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="usuario-asignador-2"]')))
            resaltar_elemento(driver, persona_asignada)
            escribir_log(nombre_automatizacion, "Cajero asignado verificado para Caja 20.")
            time.sleep(0.5)
            tomar_captura(driver, "Captura_asignacion_caja_06_cajero_asignado", "Asignación de cajero realizada correctamente.", capturas, textos, nombre_automatizacion)
        else:
            escribir_log(nombre_automatizacion, "Advertencia: No se asignó ninguna caja válida, no se verifica cajero.")
    except TimeoutException:
        escribir_log(nombre_automatizacion, "Advertencia: No se encontró el elemento del cajero asignado, continuando.")
    time.sleep(0.5)

def asignar_caja(driver):
    """
    Automatiza la gestión de caja dentro de la sesión activa.
    """
    wait = WebDriverWait(driver, 40)
    capturas = []
    textos = []
    nombre_automatizacion = "asignacion_caja_pdf"

    try:
        mostrar_mensaje(driver, "Se realiza la asignación de Caja", nombre_automatizacion)
        tomar_captura(driver, "asignacion_caja", "Se inició el proceso de asignación de caja correctamente.", capturas, textos, nombre_automatizacion)
        
        navegar_a_administrador(driver, wait, capturas, textos, nombre_automatizacion)
        navegar_a_gestion_caja(driver, wait, capturas, textos, nombre_automatizacion)
        cerrar_menu_lateral(driver, wait, nombre_automatizacion)
        numero_caja_asignada = alternar_cajas(driver, wait, capturas, textos, nombre_automatizacion)
        asignar_cajero(driver, wait, capturas, textos, nombre_automatizacion)
        verificar_cajero_asignado(driver, wait, numero_caja_asignada, nombre_automatizacion, capturas, textos)
        
        generar_pdf_consolidado(nombre_automatizacion, capturas, textos)
        escribir_log(nombre_automatizacion, "PDF consolidado generado exitosamente.")
        escribir_log(nombre_automatizacion, f"Gestión de Caja completada. Caja asignada: {numero_caja_asignada}")
        print(f"Número de caja asignado tras alternar: {numero_caja_asignada}")
        
    except (TimeoutException, NoSuchElementException, NoSuchWindowException, WebDriverException) as e:
        escribir_log(nombre_automatizacion, f"Error durante el proceso de asignación de caja: {e}")
        logging.error(f"❌ Error durante el proceso: {e}")
        raise