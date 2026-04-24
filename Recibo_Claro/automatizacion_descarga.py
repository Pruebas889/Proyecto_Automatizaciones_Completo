import logging
import os
import time
import random
import glob
import json
import sys
import threading
from control_flow import stop_automation_flag
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



# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Funciones para verificar archivos descargados
def obtener_nombres_facturas_descargadas(directorio_descarga):
    archivos = glob.glob(os.path.join(directorio_descarga, "Factura_*.pdf"))
    nombres = set(os.path.basename(f) for f in archivos)
    return nombres

# Funciones para manejar progreso
def cargar_progreso(ruta_archivo: str = 'progreso_descargas.json') -> dict:
    try:
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'r') as f:
                progreso = json.load(f)
                if not all(key in progreso for key in ['ultima_pagina', 'facturas_descargadas', 'facturas_fallidas']):
                    raise ValueError("Estructura de progreso inválida")
                return progreso
    except Exception as e:
        logging.warning(f"Error al cargar progreso: {e}. Creando nuevo archivo.")
    return {
        'ultima_pagina': 1,
        'facturas_descargadas': [],
        'facturas_fallidas': [],
        'ultima_factura_procesada': None
    }

def guardar_progreso(progreso: dict, ruta_archivo: str = 'progreso_descargas.json'):
    try:
        progreso['facturas_descargadas'] = list(dict.fromkeys(progreso['facturas_descargadas']))
        progreso['facturas_fallidas'] = list(dict.fromkeys(progreso['facturas_fallidas']))
        with open(ruta_archivo, 'w') as f:
            json.dump(progreso, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error al guardar progreso: {e}")

def esperar_descarga_completa_con_nombre(directorio_descarga, nombre_archivo, timeout=90):
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

# Funciones Auxiliares
def esperar_clickable(driver, selector, timeout=15, intentos=2):
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


def debug_encontrar_paneles(driver):
    """
    Función de depuración: Muestra todos los elementos que podrían ser paneles/acordeones
    """
    logging.info("=== DEPURACIÓN: Buscando estructuras de paneles ===")
    
    # Buscar por diferentes patrones comunes
    patrones = [
        "//div[@role='tab']",
        "//div[@role='button']",
        "//*[contains(@class, 'accordion')]",
        "//*[contains(@class, 'tab')]",
        "//*[contains(@class, 'panel')]",
        "//*[contains(@class, 'collapse')]",
        "//button[contains(@class, 'accordion')]",
        "//h3[contains(@class, 'accordion')]",
        "//span[contains(@class, 'accordion')]"
    ]
    
    for i, patron in enumerate(patrones):
        try:
            elementos = driver.find_elements(By.XPATH, patron)
            if elementos:
                logging.info(f"Patrón {i+1} '{patron}': Encontré {len(elementos)} elementos")
                for j, elem in enumerate(elementos[:3]):  # Mostrar solo primeros 3
                    logging.info(f"  Elemento {j+1}: tag={elem.tag_name}, class='{elem.get_attribute('class')}', text='{elem.text[:50]}'")
        except Exception as e:
            pass
    
    # Buscar específicamente el texto "Soluciones Fijas"
    try:
        elementos = driver.find_elements(By.XPATH, "//*[contains(text(), 'Soluciones Fijas')]")
        logging.info(f"\n🔍 Elementos que contienen 'Soluciones Fijas': {len(elementos)}")
        for j, elem in enumerate(elementos):
            logging.info(f"  Elemento {j+1}: tag={elem.tag_name}, class='{elem.get_attribute('class')}', id='{elem.get_attribute('id')}'")
            logging.info(f"    XPATH sugerido: {elem.tag_name}[@class='{elem.get_attribute('class')}']")
            # Mostrar el padre
            padre = elem.find_element(By.XPATH, "..")
            logging.info(f"    Padre: {padre.tag_name}[@class='{padre.get_attribute('class')}']")
    except Exception as e:
        logging.error(f"Error en búsqueda de texto: {e}")
    
    logging.info("=== FIN DEPURACIÓN ===")

# ========== AGREGAR ESTA NUEVA FUNCIÓN AQUÍ (después de cerrar_popup) ==========
def seleccionar_soluciones_fijas(driver):
    """
    Busca y selecciona 'Soluciones Fijas (HFC)' - Versión mejorada con múltiples estrategias
    """
    try:
        logging.info("🔍 Buscando 'Soluciones Fijas (HFC)' después del clic en facturas...")
        
        # Esperar a que aparezca el popup/panel
        time.sleep(3)
        
        # ESTRATEGIA 1: Buscar por texto exacto en cualquier lugar
        try:
            elemento_hfc = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Soluciones Fijas (HFC)') or contains(text(), 'Soluciones Fijas')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", elemento_hfc)
            time.sleep(0.5)
            mover_mouse_humano(driver, elemento_hfc)
            elemento_hfc.click()
            logging.info("✅ Clic en 'Soluciones Fijas (HFC)' - Estrategia 1 exitosa")
            time.sleep(2)
            return True
        except:
            logging.info("Estrategia 1 falló, intentando Estrategia 2...")
        
        # ESTRATEGIA 2: Buscar por clase de acordeón/panel
        try:
            paneles = driver.find_elements(By.XPATH, 
                "//div[contains(@class, 'accordion')] | " +
                "//div[contains(@class, 'panel')] | " +
                "//div[contains(@class, 'collapse')] | " +
                "//div[@role='tab'] | " +
                "//button[contains(@class, 'accordion')]"
            )
            
            for panel in paneles:
                texto = panel.text
                if "Soluciones Fijas" in texto:
                    driver.execute_script("arguments[0].scrollIntoView(true);", panel)
                    time.sleep(0.5)
                    mover_mouse_humano(driver, panel)
                    panel.click()
                    logging.info(f"✅ Clic en panel con texto: '{texto[:50]}'")
                    time.sleep(2)
                    return True
        except:
            logging.info("Estrategia 2 falló...")
        
        # ESTRATEGIA 3: Buscar en iframes si existe
        try:
            driver.switch_to.default_content()
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    elementos = driver.find_elements(By.XPATH, "//*[contains(text(), 'Soluciones Fijas')]")
                    if elementos:
                        elementos[0].click()
                        logging.info(f"✅ Clic en 'Soluciones Fijas' dentro del iframe {i+1}")

                        time.sleep(2)
                        return True
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
        except Exception as e:
            logging.info(f"Búsqueda en iframes falló: {e}")
        
        logging.warning("❌ No se encontró 'Soluciones Fijas (HFC)' después de todas las estrategias")
        return False
        
    except Exception as e:
        logging.error(f"❌ Error general en seleccionar_soluciones_fijas: {e}")
        return False
# ========== FIN DE LA NUEVA FUNCIÓN ==========

# ========== NUEVAS FUNCIONES PARA BÚSQUEDA DINÁMICA ==========

def encontrar_contenedores_facturas_dinamico(driver, timeout=15):
    """
    Busca contenedores de facturas usando múltiples estrategias.
    Retorna lista de elementos contenedores encontrados.
    """
    logging.info("🔍 Iniciando búsqueda dinámica de contenedores de facturas...")
    
    estrategias = [
        # Estrategia 1: Buscar por estructura con información de cuenta y factura
        {
            "nombre": "Por contenedor con Nro. cuenta + Nro. factura",
            "xpath": "//div[contains(., 'Nro. cuenta') and contains(., 'Nro. factura')]"
        },
        # Estrategia 2: Buscar por filas de tabla
        {
            "nombre": "Por filas de tabla",
            "xpath": "//table//tbody//tr[contains(., 'Nro. cuenta')]"
        },
        # Estrategia 3: Buscar por divs con estructura de tarjeta/panel
        {
            "nombre": "Por divs con clase 'row' o 'card'",
            "xpath": "//div[contains(@class, 'row') or contains(@class, 'card') or contains(@class, 'item')][contains(., '$')]"
        },
        # Estrategia 4: Buscar por divs que contengan información de monto
        {
            "nombre": "Por divs con monto ($)",
            "xpath": "//div[contains(text(), '$') and contains(., 'Nro.')]"
        },
        # Estrategia 5: Buscar divs simples con estructura numérica
        {
            "nombre": "Por divs con estructura de factura",
            "xpath": "//div[contains(@class, 'factura') or contains(@class, 'bill') or contains(@class, 'invoice')]"
        }
    ]
    
    for estrategia in estrategias:
        try:
            logging.info(f"  Intentando: {estrategia['nombre']}")
            contenedores = WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((By.XPATH, estrategia['xpath']))
            )
            
            if contenedores and len(contenedores) > 0:
                logging.info(f"  ✅ Éxito: Se encontraron {len(contenedores)} contenedores")
                return contenedores, estrategia['nombre']
        except (TimeoutException, NoSuchElementException):
            logging.info(f"  ❌ Falló esta estrategia")
            continue
    
    logging.warning("⚠️ No se encontraron contenedores con ninguna estrategia")
    return [], "Ninguna"


def encontrar_boton_descarga_en_contenedor(driver, contenedor, indice_contenedor):
    """
    Busca el botón de descarga dentro de un contenedor específico.
    Retorna el botón o None si no lo encuentra.
    """
    logging.info(f"  🔍 Buscando botón de descarga en contenedor {indice_contenedor + 1}...")
    # 🔥 FIX REAL: buscar SOLO dentro del contenedor (NO rompe el acordeón)
    try:
        img = contenedor.find_element(By.XPATH, ".//img[@alt='DescargaFactura']")

        boton = driver.execute_script("""
            let el = arguments[0];
            while (el && el.tagName != 'BUTTON' && el.tagName != 'A') {
                el = el.parentElement;
            }
            return el;
        """, img)

        if boton:
            logging.info("    ✅ BOTÓN ENCONTRADO POR ALT (FIX REAL)")
            return boton

    except Exception:
        logging.info("    ❌ ALT dentro del contenedor no encontrado")

    estrategias_boton = [
        # ⭐ ESTRATEGIA PRINCIPAL: Buscar la imagen con alt="DescargaFactura"
        {
            "nombre": "Por imagen alt 'DescargaFactura' exacto",
            "xpath": ".//img[@alt='DescargaFactura']/ancestor::button | .//img[@alt='DescargaFactura']/ancestor::a | .//img[@alt='DescargaFactura']/parent::*"
        },
        # Estrategia 1: Por aria-label con "Descargar"
        {
            "nombre": "Por aria-label 'Descargar'",
            "xpath": ".//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'descargar')]"
        },
        # Estrategia 2: Por title con "Descargar"
        {
            "nombre": "Por title 'Descargar'",
            "xpath": ".//*[@title and contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'descargar')]"
        },
        # Estrategia 3: Por button con clase descarga
        {
            "nombre": "Por button con clase descarga",
            "xpath": ".//button[contains(@class, 'descarga') or contains(@class, 'download') or contains(@class, 'download-btn')]"
        },
        # Estrategia 4: Por div/a/button dentro del contenedor con ícono SVG
        {
            "nombre": "Por elemento con SVG de descarga",
            "xpath": ".//*[contains(@class, 'download') or contains(@class, 'descarga')]//button | .//*[contains(@class, 'download') or contains(@class, 'descarga')]//a"
        },
        # Estrategia 5: Por button que sea clickeable sin clase específica
        {
            "nombre": "Por primer button clickeable",
            "xpath": ".//button[not(contains(@disabled, 'disabled'))]"
        },
        # Estrategia 6: Por elemento con atributo onclick o data-action
        {
            "nombre": "Por onclick o data-action",
            "xpath": ".//*[@onclick or @data-action or @data-download]"
        },
        # Estrategia 7: Por spans/divs dentro de botones
        {
            "nombre": "Por span/div con ícono dentro de botón",
            "xpath": ".//button//span | .//button//div | .//a//span[contains(@class, 'icon')]"
        }
    ]
    
    for estrategia_btn in estrategias_boton:
        try:
            elemento = contenedor.find_element(By.XPATH, estrategia_btn['xpath'])
            
            # Si encontramos un span/div, obtener su padre button
            if elemento.tag_name in ['span', 'div']:
                try:
                    elemento = elemento.find_element(By.XPATH, "./ancestor::button")
                except:
                    try:
                        elemento = elemento.find_element(By.XPATH, "./ancestor::a")
                    except:
                        continue
            
            logging.info(f"    ✅ {estrategia_btn['nombre']}: Encontrado ({elemento.tag_name})")
            return elemento
            
        except (NoSuchElementException, StaleElementReferenceException):
            logging.info(f"    ❌ {estrategia_btn['nombre']}: No encontrado")
            continue
        except Exception as e:
            logging.debug(f"    ⚠️ {estrategia_btn['nombre']}: Error {str(e)[:50]}")
            continue
    
    logging.warning(f"    ❌ No se encontró botón de descarga en contenedor {indice_contenedor + 1}")
    return None


def extraer_info_factura(contenedor):
    """
    Extrae información de la factura desde el contenedor para logging.
    """
    try:
        nro_cuenta = None
        nro_factura = None
        monto = None
        
        # Intentar extraer número de cuenta
        try:
            nro_cuenta = contenedor.find_element(By.XPATH, ".//*[contains(text(), 'Nro. cuenta')]/following-sibling::*").text
        except:
            pass
        
        # Intentar extraer número de factura
        try:
            nro_factura = contenedor.find_element(By.XPATH, ".//*[contains(text(), 'Nro. factura')]/following-sibling::*").text
        except:
            pass
        
        # Intentar extraer monto
        try:
            monto = contenedor.find_element(By.XPATH, ".//*[contains(text(), '$')]/ancestor::*[1]").text.split('$')[1].split()[0]
        except:
            pass
        
        info = []
        if nro_cuenta:
            info.append(f"Cuenta: {nro_cuenta}")
        if nro_factura:
            info.append(f"Factura: {nro_factura}")
        if monto:
            info.append(f"Monto: ${monto}")
        
        return " | ".join(info) if info else "Sin información"
    except:
        return "Información no disponible"


def procesar_contenedores_facturas_dinamico(driver, download_dir, progreso):
    """
    Procesa contenedores de facturas encontrados dinámicamente.
    Esta es la función PRINCIPAL que reemplaza las anteriores.
    """
    logging.info("="*60)
    logging.info("🎯 INICIANDO PROCESAMIENTO DINÁMICO DE FACTURAS")
    logging.info("="*60)
    
    try:
        # PASO 1: Encontrar contenedores
        contenedores, estrategia_usada = encontrar_contenedores_facturas_dinamico(driver)
        
        if not contenedores:
            logging.error("❌ No se encontraron contenedores de facturas")
            return 0
        
        logging.info(f"📊 Estrategia usada: {estrategia_usada}")
        logging.info(f"📦 Total de facturas encontradas: {len(contenedores)}")
        logging.info("-"*60)
        
        # PASO 2: Procesar cada contenedor
        descargas_exitosas = 0

        
        for idx, contenedor in enumerate(contenedores):
            if stop_automation_flag.is_set():
                logging.info("🛑 Proceso detenido por el usuario")
                break
            
            try:
                # Extraer información para logging
                info_factura = extraer_info_factura(contenedor)
                logging.info(f"\n📋 Factura {idx + 1}/{len(contenedores)}: {info_factura}")
                
                # Hacer scroll al contenedor
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", contenedor)
                time.sleep(1)
                
                # Encontrar botón de descarga
                boton_descarga = encontrar_boton_descarga_en_contenedor(driver, contenedor, idx)
                
                if not boton_descarga:
                    logging.warning(f"  ⚠️ No se encontró botón para factura {idx + 1}")
                    progreso['facturas_fallidas'].append(f"dinamico_{idx}")
                    continue
                
                # Hacer clic en el botón
                try:
                    mover_mouse_humano(driver, boton_descarga)
                    driver.execute_script("arguments[0].click();", boton_descarga)
                    logging.info(f"  ✅ Clic exitoso en botón de descarga")
                    pausa_humana(2, 4)
                    descargas_exitosas += 1
                    progreso['facturas_descargadas'].append(f"dinamico_{idx}")
                    
                except Exception as e:
                    logging.error(f"  ❌ Error al hacer clic: {e}")
                    progreso['facturas_fallidas'].append(f"dinamico_{idx}")
                    continue
                
            except Exception as e:
                logging.error(f"  ❌ Error procesando factura {idx + 1}: {e}")
                continue
        
        logging.info("\n" + "="*60)
        logging.info(f"✅ Descargas exitosas: {descargas_exitosas}/{len(contenedores)}")
        logging.info("="*60)
        
        return descargas_exitosas
        
    except Exception as e:
        logging.error(f"❌ Error general en procesar_contenedores_facturas_dinamico: {e}")
        return 0

# ========== FIN NUEVAS FUNCIONES ==========

# ========== FUNCIÓN PARA BOTÓN DE DESCARGA POR TEXTO ==========
def hacer_clic_boton_descarga_dinamico(driver):
    """
    Busca y hace clic en el botón con el texto "Descargar factura"
    """
    try:
        logging.info("🔍 Buscando botón con texto 'Descargar factura'...")
        
        # Esperar a que aparezca el botón
        time.sleep(2)
        
        # Buscar botones dentro de cada bloque de factura (más robusto)
        facturas = driver.find_elements(By.XPATH, "//div[contains(., 'Nro. cuenta')]")

        botones = []

        for factura in facturas:
            try:
                btn = factura.find_element(By.XPATH, ".//button | .//a | .//*[name()='svg']/ancestor::button")
                botones.append(btn)
            except:
                continue
        
        logging.info(f"✅ Se encontraron {len(botones)} botón(es) 'Descargar factura'")
        
        if not botones:
            logging.warning("❌ No se encontraron botones de descarga dentro de facturas")
            return False
            for i, btn in enumerate(todos_botones[:5]):
                logging.info(f"  Botón {i+1}: texto='{btn.text}', class='{btn.get_attribute('class')}'")
            return False
        
        # Hacer clic en CADA botón de "Descargar factura" encontrado
        for i, boton in enumerate(botones):
            try:
                logging.info(f"🎯 Procesando botón {i+1} de {len(botones)}...")
                
                # Intentar obtener el número de cuenta asociado (si existe)
                try:
                    # Buscar el número de cuenta cercano al botón
                    cuenta = boton.find_element(By.XPATH, "./ancestor::tr/preceding-sibling::tr//td[contains(text(), 'Nro. cuenta')] | ./preceding::*[contains(text(), 'Nro. cuenta')][1]")
                    texto_cuenta = cuenta.text if cuenta else "desconocida"
                    logging.info(f"📄 Descargando factura para cuenta: {texto_cuenta}")
                except:
                    logging.info(f"📄 Descargando factura {i+1}")
                
                # Hacer scroll hasta el botón
                driver.execute_script("arguments[0].scrollIntoView(true);", boton)
                time.sleep(1)
                
                # Hacer clic en el botón
                mover_mouse_humano(driver, boton)
                driver.execute_script("arguments[0].click();", boton)
                logging.info(f"✅ Clic exitoso en botón {i+1}")
                time.sleep(3)  # Esperar entre descargas
                
            except Exception as e:
                logging.error(f"❌ Error al hacer clic en botón {i+1}: {e}")
                continue
        
        logging.info(f"🎉 Procesados {len(botones)} botón(es) 'Descargar factura'")
        return len(botones) > 0
        
    except Exception as e:
        logging.error(f"❌ Error general en hacer_clic_boton_descarga_dinamico: {e}")
        return False
# ========== FIN FUNCIÓN BOTÓN DINÁMICO ==========







def pausa_humana(min_s=0.3, max_s=0.7):
    time.sleep(random.uniform(min_s, max_s))

def mover_mouse_humano(driver, elemento):
    try:
        actions = ActionChains(driver)
        actions.move_to_element(elemento).perform()
        pausa_humana(0.5, 1)
    except Exception as e:
        logging.debug(f"No se pudo mover el mouse de forma humana: {e}")

# FUNCIÓN PRINCIPAL
def automatizar_claro_empresas_completo(username, password, download_dir, anio, mes, max_reintentos=7):
    try:
        anio = int(anio)
        mes = mes.zfill(2)
        current_year = datetime.now().year
        if anio not in [current_year, current_year - 1] or mes not in [f"{i:02d}" for i in range(1, 13)]:
            logging.error("Año o mes inválido.")
            return None
    except ValueError:
        logging.error("Año o mes no son valores válidos.")
        return None

    progreso = cargar_progreso()
    
    options = ChromeOptions()
    options.add_argument("--start-maximized")
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    driver = None
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        # 🔥 PERMITIR DESCARGAS AUTOMÁTICAS (FIX REAL)
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": download_dir
            }
        )
        logging.info("Navegador Chrome iniciado correctamente en pantalla completa. 🚀")
    except WebDriverException as e:
        logging.error(f"Error iniciando el navegador Chrome: {e} ❌")
        return None

    try:
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

        cerrar_popup(driver, "//button[text()='Aceptar']", "popup de bienvenida")
        cerrar_popup(driver, '/html/body/div[5]/div[3]/div/img', "Popup de información después del login")
        cerrar_popup(driver, '//img[@src="https://siteintercept.qualtrics.com/static/q-siteintercept/~/img/svg-close-btn-black-7.svg"]', "Popup de encuesta Qualtrics")


        
        
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
        cerrar_popup(driver, '//*[@id="senna_surface1"]/div[5]/div[3]/div/img', "Popup post-submenu de descarga")
        pausa_humana(1, 2)

        logging.info("🎯 Intentando seleccionar 'Soluciones Fijas (HFC)' después del popup...")
        seleccionar_soluciones_fijas(driver)

        logging.info("Esperando que el panel se expanda....")
        time.sleep(5)

        # 🔥 LOOP ESTABLE (REEMPLAZO)

        logging.info("🔥 Iniciando ciclo con paginación automática...")

        pagina = 1

        contador_facturas = 0

        while True:
            logging.info(f"📄 Procesando página {pagina}")

            i = 0

            while True:
                if stop_automation_flag.is_set():
                    break

                botones = driver.find_elements(By.XPATH, "//img[@alt='DescargaFactura']")

                if i >= len(botones):
                    logging.info("✅ Facturas de esta página terminadas")
                    break

                try:
                    logging.info(f"📄 Factura {i+1} de {len(botones)} (página {pagina})")

                    btn = botones[i]
                    

                    # 🔥 FILTRO POR MES ACTUAL

                    meses_map = {
                        "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr",
                        "05": "May", "06": "Jun", "07": "Jul", "08": "Ago",
                        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic"
                    }

                    mes_actual_txt = meses_map[mes]

                    try:
                        contenedor = btn.find_element(By.XPATH, "./ancestor::div[contains(., 'Fecha límite de pago')]")

                        texto_fecha = contenedor.text

                        if mes_actual_txt not in texto_fecha:
                            logging.info(f"🛑 Se detectó cambio de mes ({texto_fecha}). Fin del proceso.")
                            
                            # 🔥 SALIR COMPLETAMENTE
                            return driver

                    except Exception as e:
                        logging.warning(f"⚠️ No se pudo validar mes en factura {i+1}: {e}")
                        i += 1
                        continue

                    

                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(1)

                    boton_real = driver.execute_script("""
                        let el = arguments[0];
                        while (el && el.tagName != 'BUTTON' && el.tagName != 'A') {
                            el = el.parentElement;
                        }
                        return el;
                    """, btn)

                    driver.execute_script("arguments[0].click();", boton_real)
                    time.sleep(5)

                    pdf_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//img[@alt='Imagen_PDF']"))
                    )

                    pdf_real = driver.execute_script("""
                        let el = arguments[0];
                        while (el && el.tagName != 'BUTTON' && el.tagName != 'A') {
                            el = el.parentElement;
                        }
                        return el;
                    """, pdf_btn)
                    time.sleep(5)

                    driver.execute_script("arguments[0].click();", pdf_real)
                    # 🔥 ESPERA PARA QUE DESCARGUE Y ESTABILICE
                    time.sleep(4)

                    logging.info(f"✅ Descarga OK factura {i+1}")
                    contador_facturas += 1

                    factura_id = f"pagina_{pagina}_factura_{i+1}"
                    progreso['facturas_descargadas'].append(factura_id)
                    guardar_progreso(progreso)

                    if contador_facturas % 10 == 0:
                        pausa_random = random.randint(30, 60)
                        logging.info(f"⏸️ Pausa aleatoria de {pausa_random} segundos (anti-bloqueo)...")
                        time.sleep(pausa_random)
                    factura_id = f"pagina_{pagina}_factura_{i+1}"
                    progreso['facturas_descargadas'].append(factura_id)
                    guardar_progreso(progreso)
                    time.sleep(5)

                    # 🔥 CIERRE ROBUSTO DEL MODAL PDF

                    cerrado = False

                    # intento 1: ESC
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(2)
                        cerrado = True
                    except:
                        pass

                    # intento 2: botón cerrar (X)
                    if not cerrado:
                        try:
                            btn_close = driver.find_element(By.XPATH, "//button[contains(@class,'close') or contains(@aria-label,'Close')]")
                            driver.execute_script("arguments[0].click();", btn_close)
                            time.sleep(2)
                            cerrado = True
                        except:
                            pass

                    # intento 3: clic fuera del modal
                    if not cerrado:
                        try:
                            driver.execute_script("document.body.click();")
                            time.sleep(2)
                            cerrado = True
                        except:
                            pass

                    # intento 4: verificación final
                    try:
                        WebDriverWait(driver, 3).until_not(
                            EC.presence_of_element_located((By.XPATH, "//img[@alt='Imagen_PDF']"))
                        )
                    except:
                        logging.warning("⚠️ Modal PDF sigue abierto, forzando ESC adicional")
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(2)

                    i += 1

                except Exception as e:
                    logging.error(f"❌ Error en factura {i+1}: {e}")
                    factura_id = f"pagina_{pagina}_factura_{i+1}"
                    progreso['facturas_fallidas'].append(factura_id)
                    guardar_progreso(progreso)
                    i += 1
                    continue

            # 🔥 SIGUIENTE PÁGINA

            try:
                logging.info("➡️ Buscando botón 'Next page'...")

                btn_next = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//a[contains(@class,'rz-pager-next') and (@aria-label='Go to next page.' or @title='Next page')]"
                    ))
                )

                if btn_next.get_attribute("aria-disabled") == "true":
                    logging.info("🏁 No hay más páginas. FIN.")
                    break

                driver.execute_script("arguments[0].click();", btn_next)

                logging.info("➡️ Avanzando a la siguiente página...")
                time.sleep(5)

                pagina += 1

            except Exception as e:
                logging.warning(f"⚠️ No se pudo avanzar de página: {e}")
                break

        # 🔥 AQUÍ VA (FUERA DEL WHILE)
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

# ========== EJECUCIÓN PRINCIPAL ==========
if __name__ == "__main__":
    if len(sys.argv) != 6:
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

    driver_claro = automatizar_claro_empresas_completo(
        mi_usuario,
        mi_contrasena,
        mi_carpeta_descarga,
        mi_anio,
        mi_mes
    )