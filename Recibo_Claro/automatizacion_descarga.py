import logging
import os
import time
import random
import glob
import json
import sys
from selenium.webdriver.support.ui import Select
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

# <<<<<< MODIFICACIÓN: Importar de control_flow.py en lugar de server.py
from control_flow import stop_automation_flag

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# -----------------------------------------------------------------------------
# Funciones para verificar archivos descargados en disco
# -----------------------------------------------------------------------------

def obtener_nombres_facturas_descargadas(directorio_descarga):
    archivos = glob.glob(os.path.join(directorio_descarga, "Factura_*.pdf"))
    nombres = set(os.path.basename(f) for f in archivos)
    return nombres

# -----------------------------------------------------------------------------
# Funciones para manejar el progreso
# -----------------------------------------------------------------------------

def cargar_progreso(ruta_archivo: str = 'progreso_descargas.json') -> dict:
    """Carga el progreso guardado desde un archivo JSON con verificación mejorada"""
    try:
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'r') as f:
                progreso = json.load(f)
                # Verificar estructura del archivo
                if not all(key in progreso for key in ['ultima_pagina', 'facturas_descargadas', 'facturas_fallidas']):
                    raise ValueError("Estructura de progreso inválida")
                return progreso
    except Exception as e:
        logging.warning(f"Error al cargar progreso: {e}. Creando nuevo archivo.")
    return {
        'ultima_pagina': 1,
        'facturas_descargadas': [],
        'facturas_fallidas': [],
        'ultima_factura_procesada': None  # Nuevo campo para tracking preciso
    }

def guardar_progreso(progreso: dict, ruta_archivo: str = 'progreso_descargas.json'):
    """Guarda el progreso actual en un archivo JSON con verificación y sin duplicados"""
    try:
        # Eliminar duplicados antes de guardar
        # Eliminar duplicados conservando el orden
        progreso['facturas_descargadas'] = list(dict.fromkeys(progreso['facturas_descargadas']))
        progreso['facturas_fallidas'] = list(dict.fromkeys(progreso['facturas_fallidas']))

        with open(ruta_archivo, 'w') as f:
            json.dump(progreso, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error al guardar progreso: {e}")


def esperar_descarga_completa_con_nombre(directorio_descarga, nombre_archivo, timeout=90):
    """
    Espera a que un archivo específico termine de descargarse.
    Timeout en segundos.
    """
    ruta_completa = os.path.join(directorio_descarga, nombre_archivo)
    fin_tiempo = time.time() + timeout
    while time.time() < fin_tiempo:
        if os.path.exists(ruta_completa) and not (ruta_completa.endswith(".part") or ruta_completa.endswith(".tmp")):
            if os.path.getsize(ruta_completa) > 0:
                logging.info(f"Descarga de '{nombre_archivo}' completada. ✅")
                return True
        time.sleep(1)
    logging.warning(f"Tiempo de espera agotado para la descarga de '{nombre_archivo}'. ❌")
    return False


# -----------------------------------------------------------------------------
## Funciones Auxiliares (mantenidas igual)
# -----------------------------------------------------------------------------

def esperar_clickable(driver, selector, timeout=15, intentos=2):
    """Espera a que el elemento esté clickable, puede ser XPath o CSS selector."""
    for intento in range(intentos):
        try:
            if selector.startswith("/") or selector.startswith("//"):
                elemento = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
            else:
                elemento = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
            logging.info(f"Elemento '{selector}' encontrado y clickable.")
            return elemento
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
            logging.warning(f"Intento {intento + 1}/{intentos}: Elemento '{selector}' no clickeable. Error: {e}. Reintentando...")
            time.sleep(random.uniform(0.5, 1))
    logging.error(f"Fallo al encontrar o hacer clickeable el elemento '{selector}' después de {intentos} intentos.")
    raise TimeoutException(f"No se pudo encontrar elemento clickable tras {intentos} intentos: {selector}")

def esperar_visible(driver, selector, timeout=30, intentos=3):
    """Espera a que el elemento esté visible, puede ser XPath o CSS selector."""
    for intento in range(intentos):
        try:
            if selector.startswith("/") or selector.startswith("//") or selector.startswith('('):
                elemento = WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.XPATH, selector))
                )
            else:
                elemento = WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                )
            logging.info(f"Elemento '{selector}' encontrado y visible.")
            return elemento
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
            logging.warning(f"Intento {intento + 1}/{intentos}: No se encontró elemento visible: {selector}. Error: {e}. Reintentando...")
            time.sleep(random.uniform(1, 2))
    logging.error(f"Fallo al encontrar o hacer visible el elemento '{selector}' después de {intentos} intentos.")
    raise TimeoutException(f"No se pudo encontrar elemento visible tras {intentos} intentos: {selector}")

def cerrar_popup(driver, selector, nombre="popup"):
    """
    Intenta cerrar un popup usando un clic normal y, si falla, un clic con JavaScript.
    Maneja TimeoutException si el popup no aparece.
    """
    try:
        popup = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, selector))
        )
        logging.info(f"Popup '{nombre}' detectado. Intentando cerrar. 🚪")
        
        try:
            popup.click()
            logging.info(f"{nombre} cerrado correctamente con clic normal. 👍")
        except WebDriverException:
            logging.warning(f"Clic normal falló para {nombre}. Intentando con JavaScript.")
            driver.execute_script("arguments[0].click();", popup)
            logging.info(f"{nombre} cerrado correctamente con JavaScript. ✅")
            
        time.sleep(1)
    except TimeoutException:
        logging.info(f"No apareció el {nombre} a tiempo, continuando.")
    except Exception as e:
        logging.warning(f"Error inesperado al intentar cerrar {nombre}: {e}. Continuando.")

def pausa_humana(min_s=0.3, max_s=0.7):
    """Pausa aleatoria para simular comportamiento humano."""
    time.sleep(random.uniform(min_s, max_s))
    

def mover_mouse_humano(driver, elemento):
    """Mueve el mouse a un elemento de forma más humana."""
    try:
        actions = ActionChains(driver)
        actions.move_to_element(elemento).perform()
        pausa_humana(0.5, 1)
    except Exception as e:
        logging.debug(f"No se pudo mover el mouse de forma humana: {e}")


# -----------------------------------------------------------------------------
## Función Principal de Automatización MODIFICADA para usar progreso
# -----------------------------------------------------------------------------

def automatizar_claro_empresas_completo(username, password, download_dir, anio, mes, max_reintentos=7):  
    
    """
    Automatiza el proceso de login y descarga de facturas en Mi Claro Empresas.
    """
    try:
        anio = int(anio)
        mes = mes.zfill(2)  # Asegura formato "01" a "12"
        current_year = datetime.now().year
        if anio not in [current_year, current_year - 1] or mes not in [f"{i:02d}" for i in range(1, 13)]:
            logging.error("Año o mes inválido.")
            return None
    except ValueError:
        logging.error("Año o mes no son valores válidos.")
        return None


    # Cargar progreso anterior
    progreso = cargar_progreso()
    
    # Opciones para Chrome
    options = ChromeOptions()
    options.add_argument("--start-maximized") 

    # Configuración de descarga para Chrome
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_setting_values.automatic_downloads": 1  # <<<<<< MODIFICACIÓN: Permitir descargas automáticas múltiples sin confirmar
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    driver = None
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("Navegador Chrome iniciado correctamente en pantalla completa. 🚀")
    except WebDriverException as e:
        logging.error(f"Error iniciando el navegador Chrome: {e} ❌")
        return None

    try:
        # Proceso de login (se mantiene igual)
        driver.get("https://miclaroempresas.com.co/login")
        logging.info("Página de login cargada.")

        for intento in range(1, max_reintentos + 1):
            try:
                driver.delete_all_cookies()
                time.sleep(2)
                campo_usuario = esperar_visible(driver, '//*[@id="_cenLoginPortlet_userName"]')
                mover_mouse_humano(driver, campo_usuario)
                campo_usuario.click()
                pausa_humana()
                campo_usuario.clear()
                campo_usuario.send_keys(username)
                pausa_humana()
                campo_pass = esperar_visible(driver, '//*[@id="_cenLoginPortlet_password"]')
                mover_mouse_humano(driver, campo_pass)
                campo_pass.click()
                pausa_humana()
                campo_pass.clear()
                campo_pass.send_keys(password)
                pausa_humana()
                boton_login = esperar_clickable(driver, '//*[@id="buttonSign"]')
                mover_mouse_humano(driver, boton_login)
                boton_login.click()
                pausa_humana(2, 5)
                logging.info(f"Intento {intento}: Credenciales ingresadas y login enviado. 🔒")
                time.sleep(10)
                try:
                    popup_error = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="errorRecaptcha"]/div/div/div[2]/button'))
                    )
                    logging.warning(f"Intento {intento}: Se detectó popup de error de login (reCAPTCHA), cerrándolo. 🚫")
                    popup_error.click()
                    time.sleep(2)
                    continue
                except TimeoutException:
                    logging.info("No apareció el popup de error de reCAPTCHA, continuando flujo. ✅")
                    break
            except Exception as e:
                logging.error(f"Intento {intento}: Error durante el login: {e} 🚨")
                time.sleep(3)
        else:
            logging.error("No fue posible iniciar sesión tras varios intentos. 😞")
            driver.quit()
            return None

        # Cierre de popups (se mantiene igual)
        cerrar_popup(driver, "//button[text()='Aceptar']", "popup de bienvenida")
        cerrar_popup(driver, '/html/body/div[5]/div[3]/div/img', "Popup de información después del login")
        cerrar_popup(driver, '//img[@src="https://siteintercept.qualtrics.com/static/q-siteintercept/~/img/svg-close-btn-black-7.svg"]', "Popup de encuesta Qualtrics")

        # Navegación a facturas (se mantiene igual)
        try:
            btn_consulta_facturas = esperar_clickable(driver, '#js-portlet-_cenaccesosrapidosportlet_INSTANCE_xU0BvWLZHNBp_ > div > div > div > div > div:nth-child(1) > div > div:nth-child(2) > div > a > div > div.text-box')
            mover_mouse_humano(driver, btn_consulta_facturas)
            pausa_humana()
            btn_consulta_facturas.click()
            logging.info("Botón 'Consulta tus facturas' clickeado correctamente. 🧾")
            pausa_humana(0.5, 1)
        except Exception as e:
            logging.error(f"No se pudo hacer clic en 'Consulta tus facturas': {e} ❌")
            driver.quit()
            return None

        submenu_btn = esperar_clickable(driver, '//*[@id="js-portlet-_censubmenuportlet_INSTANCE_Ac02F1Jm9hsz_"]/div/div/div/div[2]/div[1]')
        mover_mouse_humano(driver, submenu_btn)
        pausa_humana()
        submenu_btn.click()
        logging.info("Sección de descarga de factura abierta. 📂")
        pausa_humana(0.5, 1)

        cerrar_popup(driver, '//*[@id="senna_surface1"]/div[5]/div[3]/div/img', "Popup post-submenu de descarga")
        pausa_humana(1, 2)

   
      
        # Cierra cualquier popup que pueda aparecer después del clic en el submenú
        cerrar_popup(driver, '//*[@id="senna_surface1"]/div[5]/div[3]/div/img', "Popup post-submenu de descarga")
        pausa_humana(1, 2)

        # <<<<<< COMIENZO DEL NUEVO PASO INTEGRADO Y REFORZADO >>>>>>
        try:
            logging.info("Añadiendo una pausa para que la página principal cargue el iframe. 🧘‍♂️")
            pausa_humana(2, 4)
            
            iframe_xpath = "//iframe[contains(@src, 'https://facturasclaro.paradigma.com.co/ebpClaroCorp/Pages/Bill/Proxy.aspx')]"
            WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframe_xpath)))
            logging.info("Cambiado al contexto del iframe de facturas. ✅")
            
            logging.info(f"Seleccionando filtro por Año: {anio} y Mes: {mes}.")
            try:
                select_anio = esperar_visible(driver, '//*[@id="selectYear"]', timeout=10)  # Aumentado timeout
                select_obj = Select(select_anio)  # Usar Select para mayor fiabilidad
                select_obj.select_by_value(str(anio))  # Seleccionar por valor "2024" o "2025"
                pausa_humana(0.3, 0.7)
                logging.info(f"Año {anio} seleccionado. ✅")
            except Exception as e:
                logging.error(f"Error al seleccionar año {anio}: {e}")
                driver.switch_to.default_content()
                driver.quit()
                return None
            
            try:
                select_mes = esperar_visible(driver, '//*[@id="selectMonth"]', timeout=10)
                select_obj = Select(select_mes)
                select_obj.select_by_value(mes)
                pausa_humana(0.3, 0.7)
                logging.info(f"Mes {mes} seleccionado. ✅")
            except Exception as e:
                logging.error(f"Error al seleccionar mes {mes}: {e}")
                driver.switch_to.default_content()
                driver.quit()
                return None
            
            pausa_humana(0.3, 0.7)
            boton_consultar = esperar_clickable(driver, '//*[@id="btnFindByFilter"]', timeout=15)
            mover_mouse_humano(driver, boton_consultar)
            pausa_humana()
            try:
                driver.execute_script("arguments[0].click();", boton_consultar)
                logging.info("Botón 'Consultar' clickeado para aplicar filtro personalizado. ✅")
            except Exception as e:
                logging.error(f"Error al hacer clic en 'Consultar': {e}")
                driver.switch_to.default_content()
                driver.quit()
                return None

            logging.info("Esperando que la tabla de facturas se recargue... ⏳")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[1]"))
            )
            logging.info("Tabla de facturas recargada. ✔️")
            driver.switch_to.default_content()
            logging.info("Volviendo al contenido principal. 🔄")
        except Exception as e:
            logging.error(f"No se pudo aplicar el filtro personalizado: {e} ❌")
            try:
                driver.switch_to.default_content()
            except:
                pass
            driver.quit()
            return None
        # <<<<<< FIN DEL NUEVO PASO INTEGRADO Y REFORZADO >>>>>>
        
        

        # Procesamiento con paginación - MODIFICADO para usar progreso
        logging.info("Iniciando procesamiento de facturas con paginación... 📊")
        iframe_xpath = "//iframe[contains(@src, 'https://facturasclaro.paradigma.com.co/ebpClaroCorp/Pages/Bill/Proxy.aspx')]"
        segundo_iframe_xpath = '//*[@id="frameBill"]'
        boton_descarga_pdf_final_xpath = '//*[@id="exportPdf"]'
        boton_siguiente_pagina_xpath = "//a[@title='Ir a siguiente página' and contains(@class, 'k-pager-nav')]"
        contenedor_facturas_xpath = "/html/body/div[2]/div[1]/section/div[3]/div[2]"
        base_boton_descarga_xpath = ".//table//tbody//tr//td[5]//button"

        # Comenzar desde la última página guardada o desde 1
        pagina_actual = progreso.get('ultima_pagina', 1)
        if pagina_actual > 1:
            logging.info(f"Reanudando desde página {pagina_actual}, navegando paso a paso...")
        for _ in range(pagina_actual - 1): # Modificación aquí

            try:
                WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframe_xpath)))
                btn_siguiente_pagina = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, boton_siguiente_pagina_xpath))
                )
                mover_mouse_humano(driver, btn_siguiente_pagina)
                btn_siguiente_pagina.click()
                pausa_humana(5, 8)
                driver.switch_to.default_content()
            except Exception as e:
                logging.error(f"Error al navegar hasta la página {pagina_actual}: {e}")
                return None
        logging.info(f"Se alcanzó la página {pagina_actual}. Reanudando procesamiento normal.")


        while True:
            # <<<< AÑADIDO: Comprobar la bandera de detención
            if stop_automation_flag.is_set():
                logging.info("🛑 Proceso detenido por el usuario.")
                if driver:
                    driver.quit()
                return None
            
            # Actualizar progreso
            progreso['ultima_pagina'] = pagina_actual
            progreso['ultima_factura_procesada'] = 0  # <-- reiniciar al entrar
            guardar_progreso(progreso)


            logging.info(f"Procesando Página {pagina_actual} de facturas. 📑")

            try:
                driver.switch_to.default_content()
                WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframe_xpath)))
                logging.info(f"Cambiado al contexto del iframe de facturas (tabla) para Página {pagina_actual}. ✔️")
                pausa_humana(5, 8)
            except TimeoutException:
                logging.error(f"No se pudo cambiar al iframe de facturas a tiempo (40s) en Página {pagina_actual}. ❌")
                break
            except NoSuchElementException:
                logging.error(f"El iframe de facturas no fue encontrado en Página {pagina_actual}. ❌")
                break

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[1]"))
            )
            logging.info(f"La primera fila de la tabla de facturas dentro del iframe está presente en Página {pagina_actual}. ✔️")

            try:
                contenedor_facturas = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, contenedor_facturas_xpath))
                )
                botones_descarga = contenedor_facturas.find_elements(By.XPATH, base_boton_descarga_xpath)
                logging.info(f"Se encontraron {len(botones_descarga)} botones de descarga en Página {pagina_actual}. 🟢")
            except TimeoutException:
                logging.warning("No se encontró el contenedor de facturas o no contiene botones de descarga. ⚠️")
                botones_descarga = []

            if not botones_descarga and pagina_actual == 1:
                logging.warning(f"No se detectaron facturas con botones de descarga en la Página {pagina_actual}. 🚫")
                break
            elif not botones_descarga:
                logging.info(f"No hay facturas con botones de descarga en la Página {pagina_actual}. Probando ir a siguiente página. 🚶‍♂️")

            processed_count_on_page = 0
            inicio_idx = progreso.get('ultima_factura_procesada', 0)
            for idx in range(inicio_idx, len(botones_descarga)):

                # <<<< AÑADIDO: Comprobar la bandera de detención
                if stop_automation_flag.is_set():
                    logging.info("🛑 Proceso detenido por el usuario.")
                    if driver:
                        driver.quit()
                    return None
                    
                factura_id = f"pagina_{pagina_actual}_factura_{idx+1}"

                # Comprobación por existencia real del archivo en disco
                nombres_pdf_en_disco = obtener_nombres_facturas_descargadas(download_dir)
                nombre_esperado = f"Factura_{factura_id.upper().replace('PAGINA_', '').replace('_FACTURA_', '_')}.pdf"

                if nombre_esperado in nombres_pdf_en_disco:
                    logging.info(f"Factura ya existe en disco como archivo PDF: {nombre_esperado}, omitiendo...")
                    progreso['facturas_descargadas'].append(factura_id)
                    continue

                
                # Saltar si ya fue descargada exitosamente
                if factura_id in progreso['facturas_descargadas']:
                    logging.info(f"Factura {factura_id} ya descargada, omitiendo...")
                    continue
                
                # Saltar si falló más de 3 veces
                if progreso['facturas_fallidas'].count(factura_id) >= 3:
                    logging.warning(f"Factura {factura_id} falló 3 veces, omitiendo...")
                    continue

                logging.info(f"Intentando procesar factura {idx+1} de {len(botones_descarga)} en Página {pagina_actual} 👇")

                MAX_REINTENTOS_CLIC = 3
                found_and_clicked = False
                for intento_clic in range(MAX_REINTENTOS_CLIC):
                    try:
                        current_buttons_list = WebDriverWait(driver, 5).until(
                            EC.presence_of_all_elements_located((By.XPATH, base_boton_descarga_xpath))
                        )
                        if idx >= len(current_buttons_list):
                            logging.warning(f"Índice {idx+1} fuera de rango para botones actuales ({len(current_buttons_list)}). Terminando facturas de página.")
                            found_and_clicked = True
                            break
                        boton_actual = current_buttons_list[idx]
                        mover_mouse_humano(driver, boton_actual)
                        
                        # Solo se usa el clic con JavaScript, ya que el clic normal falla
                        driver.execute_script("arguments[0].click();", boton_actual)
                        logging.info(f"Clic JS exitoso en botón descarga {idx+1} de Página {pagina_actual}. ✅")
                        found_and_clicked = True
                        break # Salir del bucle de reintentos si el clic JS es exitoso
                        
                    except (StaleElementReferenceException, TimeoutException, NoSuchElementException, WebDriverException) as e:
                        # Se incluye WebDriverException aquí por si el JS click también falla por alguna razón
                        logging.warning(f"Reintento {intento_clic+1}: problema al hacer clic en el botón de descarga de la fila {idx+1}: {e}. Reintentando...")
                        pausa_humana(1,2)
                    except Exception as e:
                        logging.error(f"Error inesperado en reintentos clic botón {idx+1}: {e}")
                        pausa_humana(1,2)
                
                if not found_and_clicked:
                    logging.error(f"No se pudo hacer clic en la factura {idx+1} después de {MAX_REINTENTOS_CLIC} intentos, saltando.")
                    progreso['facturas_fallidas'].append(factura_id)
                    progreso['ultima_factura_procesada'] = idx + 1
                    guardar_progreso(progreso)

                    continue

                processed_count_on_page += 1
                pausa_humana(3, 5)


                logging.info(f"Cambiando a iframe visor PDF para factura {idx+1} de Página {pagina_actual}. 📄")

                descarga_exitosa = False  # Aquí va al inicio de cada factura
                nombre_descargado = None

                try:
                    WebDriverWait(driver, 40).until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, segundo_iframe_xpath)))
                    logging.info("Contexto cambiado al iframe visor PDF. ✔️")
                    pausa_humana(15, 18)

                    archivos_antes_descarga = obtener_nombres_facturas_descargadas(download_dir)

                    for intento_export in range(3):
                        try:
                            boton_descarga_final = esperar_clickable(driver, boton_descarga_pdf_final_xpath, timeout=50)
                            mover_mouse_humano(driver, boton_descarga_final)
                            driver.execute_script("arguments[0].click();", boton_descarga_final)
                            logging.info(f"Intento {intento_export+1}: Botón exportPdf clickeado mediante JavaScript.")
                            pausa_humana(5, 10)

                            archivos_despues_descarga = obtener_nombres_facturas_descargadas(download_dir)
                            nuevos_archivos = archivos_despues_descarga - archivos_antes_descarga
                            
                            if nuevos_archivos:
                                nombre_descargado = list(nuevos_archivos)[0]
                                if esperar_descarga_completa_con_nombre(directorio_descarga=download_dir, nombre_archivo=nombre_descargado, timeout=190):
                                    descarga_exitosa = True
                                    break
                                else:
                                    logging.warning(f"Archivo {nombre_descargado} no se completó tras intento {intento_export+1}. Reintentando...")
                                    pausa_humana(3, 6)
                            else:
                                logging.warning(f"No se detectó un nuevo archivo PDF tras intento {intento_export+1}. Reintentando...")
                                pausa_humana(3, 6)

                        except TimeoutException:
                            logging.error(f"No se cargó el iframe visor PDF para factura {idx+1} Página {pagina_actual}.")
                            pausa_humana(0.5, 1)

                        except Exception as e:
                            logging.error(f"Error inesperado en visor PDF para factura {idx+1}: {e}")
                            pausa_humana(0.5, 1)

                except TimeoutException:
                    logging.error(f"No se encontró iframe para factura {idx+1} de Página {pagina_actual}.")
                except Exception as e:
                    logging.error(f"Error al interactuar en el iframe PDF factura {idx+1}: {e}")
                
                # Lógica de registro FINAL
                driver.switch_to.default_content() 

                if descarga_exitosa:
                    progreso['facturas_descargadas'].append(factura_id)
                    if factura_id in progreso['facturas_fallidas']:
                        progreso['facturas_fallidas'].remove(factura_id)
                    logging.info(f"✅ Factura {factura_id} descargada con éxito. Archivo: {nombre_descargado}")
                else:
                    logging.warning(f"❌ Descarga fallida para factura {factura_id}.")
                    progreso['facturas_fallidas'].append(factura_id)

                progreso['ultima_factura_procesada'] = idx + 1
                guardar_progreso(progreso)

                driver.switch_to.default_content()
                logging.info(f"Volviendo a contenido principal tras factura {idx+1} de Página {pagina_actual}. 🔄")
                pausa_humana(1, 2)

                logging.info(f"Intentando cerrar modal overlay PDF para factura {idx+1} de Página {pagina_actual}...")
                try:
                    boton_cerrar_modal_overlay = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/div[5]/div[1]/div/a/span'))
                    )
                    mover_mouse_humano(driver, boton_cerrar_modal_overlay)
                    boton_cerrar_modal_overlay.click()
                    logging.info(f"Modal PDF cerrado factura {idx+1} de Página {pagina_actual}. ✖️")
                    pausa_humana(1, 2)
                except TimeoutException:
                    logging.info(f"No se encontró botón cierre modal factura {idx+1}, asumiendo cerrado.")
                except Exception as e:
                    logging.warning(f"Error cerrando modal factura {idx+1}: {e}")

                try:
                    WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframe_xpath)))
                    logging.info(f"Vuelto al iframe de facturas para siguiente factura en Página {pagina_actual}. ✔️")
                except Exception as e:
                    logging.error(f"No se pudo volver al iframe de facturas tras PDF factura {idx+1}: {e}")
                    driver.quit()
                    return None

            logging.info(f"Procesadas {processed_count_on_page} facturas de {len(botones_descarga)} intentos en Página {pagina_actual}.")
            if processed_count_on_page == 0 and len(botones_descarga) > 0 and pagina_actual > 1:
                logging.warning(f"No se pudo procesar ninguna factura en Página {pagina_actual}, a pesar de detectar {len(botones_descarga)}. Intentando avanzar.")

            # Paginación
            logging.info(f"Intentando avanzar a la siguiente página desde Página {pagina_actual}. ▶️")
            try:
                btn_siguiente_pagina = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, boton_siguiente_pagina_xpath))
                )
                is_disabled = btn_siguiente_pagina.get_attribute('aria-disabled') == 'true' or \
                             btn_siguiente_pagina.get_attribute('disabled') == 'true' or \
                             ("k-state-disabled" in (btn_siguiente_pagina.get_attribute('class') or ""))
                if is_disabled:
                    logging.info(f"Botón 'Siguiente Página' deshabilitado en Página {pagina_actual}. Fin de la paginación.")
                    break
                else:
                    mover_mouse_humano(driver, btn_siguiente_pagina)
                    try:
                        btn_siguiente_pagina.click()
                        logging.info(f"Clic normal en botón 'Siguiente Página' Página {pagina_actual}.")
                    except WebDriverException:
                        logging.warning("Clic normal falló en 'Siguiente Página', usando JS.")
                        driver.execute_script("arguments[0].click();", btn_siguiente_pagina)
                        logging.info(f"Clic JS exitoso en botón 'Siguiente Página' Página {pagina_actual}.")

                    pausa_humana(5, 8)
                    if pagina_actual % 10 == 0:
                        logging.info("Pausa larga para aliviar el navegador tras 10 páginas.")
                        pausa_humana(30, 45)
                    pagina_actual += 1
                    progreso['ultima_factura_procesada'] = 0
                    guardar_progreso(progreso)

            except TimeoutException:
                logging.info(f"No se encontró botón 'Siguiente Página' en Página {pagina_actual}. Asumiendo final de paginación.")
                break
            except Exception as e:
                logging.error(f"Error al clicar botón 'Siguiente Página' en Página {pagina_actual}: {e}")
                break

        logging.info("Todas las páginas de facturas procesadas correctamente. ✔️")
        driver.switch_to.default_content()
        logging.info("Vuelto al contenido principal al finalizar. 🔄")
        
        # Resumen final
        logging.info("Resumen de descargas:")
        logging.info(f"- Total facturas descargadas: {len(progreso['facturas_descargadas'])}")
        logging.info(f"- Facturas con errores: {len(progreso['facturas_fallidas'])}")
        
        logging.info("Automatización finalizada con éxito. 🎉")
        return driver

    except Exception as e:
        logging.error(f"Error general en la automatización: {e}")
        if driver:
            driver.quit()
        return None

# <<<< AÑADIDO: Bloque de ejecución principal para recibir argumentos desde el server
if __name__ == "__main__":
    if len(sys.argv) != 6:  # Ahora espera 6 argumentos
        logging.error("Uso: python automatizacion_descarga.py <usuario> <contraseña> <directorio_descarga> <anio> <mes>")
        sys.exit(1)
    
    mi_usuario = sys.argv[1]
    mi_contrasena = sys.argv[2]
    mi_carpeta_descarga = sys.argv[3]
    mi_anio = sys.argv[4]
    mi_mes = sys.argv[5]

    if not os.path.exists(mi_carpeta_descarga):
        logging.info(f"Creando carpeta de descarga: {mi_carpeta_descarga} 📁")
        os.makedirs(mi_carpeta_descarga)

    logging.info("Iniciando el proceso de automatización... 🚀")
    driver_claro = automatizar_claro_empresas_completo(mi_usuario, mi_contrasena, mi_carpeta_descarga, mi_anio, mi_mes) # type: ignore

    if driver_claro:
        logging.info("Automatización completada. Cerrando el navegador.")
        driver_claro.quit()
