import logging
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional, List, Dict
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("automatizacion.log", encoding='utf-8')
    ]
)

# Equipos, sufijos y correos
# Lista de equipos válidos
VALID_TEAMS = [
    # "Team prueba",
    "Team SIICOP v.2",
    "Team QA",
    "Team INTEGRACIONES",
    "Team POSWEB",
    "Team SIICOP"
]

TEAM_SUFFIXES = {
    # "Team prueba": "Prueba",
    "Team SIICOP v.2": "SIICOP V2",
    "Team QA": "QA",
    "Team INTEGRACIONES": "Integraciones - Ecommerce",
    "Team POSWEB": "POSWEB",
    "Team SIICOP": "SIICOP"
}

TEAM_CORREOS = {
    "Team SIICOP v.2": [
        "carlosstivenmarroquin893@gmail.com",
        "miguel.lopez@copservir.co",
        "miguel.lopez@copservir.co",
        "jhon.primero@copservir.co"
    ],
    "Team QA": [
        "yiniher.est.cop@gmail.com",
        "carlosstivenmarroquin893@gmail.com"
    ],
    "Team INTEGRACIONES": [
        "miguel.lopez@copservir.co",
        "miguel.lopez@copservir.co",
        "andres.velasco@copservir.co"
    ],
    "Team POSWEB": [
        "miguel.lopez@copservir.co",
        "miguel.lopez@copservir.co",
        "juan.walteros@copservir.co"
    ],
    "Team SIICOP": [
        "miguel.lopez@copservir.co",
        "miguel.lopez@copservir.co",
        "diego.palacio@copservir.co"
    ]
}

# Conversión de fechas a español
def format_date_to_spanish(date_str: str) -> str:
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        return f"{date_obj.day} {months[date_obj.month - 1]} {date_obj.year}"
    except ValueError:
        logging.error(f"Formato de fecha inválido: {date_str}")
        return date_str

def iniciar_driver() -> Optional[webdriver.Chrome]:
    try:
        options = webdriver.ChromeOptions()
        
        # Opciones básicas
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Opciones para evitar detección
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Opciones de rendimiento
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        
        # Para servidor (sin GUI)
        import platform
        if platform.system() != 'Windows' and 'DISPLAY' not in os.environ:
            logging.info("Ejecutando en modo headless")
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
        else:
            options.add_argument("--start-maximized")
        
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Ejecutar script para ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_page_load_timeout(60)
        
        logging.info("Driver de Chrome iniciado exitosamente.")
        return driver
    except WebDriverException as e:
        logging.error(f"Error al iniciar el driver: {e}")
        return None
    
def login_asana(driver):
    try: 
        driver.get("http://app.asana.com/0/portfolio/1205257480867940/1207672212054810")
        logging.info("Navegando a la página de Asana.")

        # Ingresar credenciales
        input_correo = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='email' and @name='e']")))
        input_correo.click()
        input_correo.clear()
        input_correo.send_keys(os.getenv('ASANA_EMAIL', 'javier.perdomo@copservir.co'))
        logging.info("Correo ingresado.")

        # Reintentar el proceso de continuar hasta que aparezca el campo contraseña
        max_intentos = 3
        for intento in range(max_intentos):
            # Hacer TAB y luego ENTER para continuar
            try:
                # Opción 1: TAB + ENTER (más simple)
                input_correo.send_keys(Keys.TAB)  # Tab para mover el foco al botón
                time.sleep(0.5)
                input_correo.send_keys(Keys.ENTER)  # Enter para hacer clic
                logging.info(f"TAB + ENTER ejecutado para continuar (intento {intento + 1})")
                
            except Exception as e:
                logging.warning(f"Error con TAB+ENTER: {e}")
                
                # Opción 2: TAB y buscar el botón específicamente
                try:
                    input_correo.send_keys(Keys.TAB)
                    time.sleep(0.5)
                    
                    # El elemento que tiene el foco después del TAB
                    focused_element = driver.switch_to.active_element
                    focused_element.click()
                    logging.info(f"Click en elemento con foco después de TAB (intento {intento + 1})")
                except:
                    pass

            # VERIFICAR si apareció el campo contraseña
            try:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='password' and @name='p']")))
                logging.info("Campo contraseña encontrado, continuando...")
                break  # Salir del bucle si encontramos el campo
            except:
                logging.warning(f"Campo contraseña no encontrado en intento {intento + 1}, reintentando...")
                if intento < max_intentos - 1:
                    # Volver a cargar la URL del portafolio
                    try:
                        driver.get("http://app.asana.com/0/portfolio/1205257480867940/1207672212054810")
                        logging.info(f"Recargando página del portafolio (intento {intento + 2})")
                        time.sleep(30)
                        
                        # Volver a encontrar el campo de correo
                        input_correo = WebDriverWait(driver, 30).until(
                            EC.element_to_be_clickable((By.XPATH, "//input[@type='email' and @name='e']")))
                        input_correo.click()
                        input_correo.clear()
                        input_correo.send_keys(os.getenv('ASANA_EMAIL', 'javier.perdomo@copservir.co'))
                        logging.info(f"Correo reingresado después de recargar (intento {intento + 2})")
                        time.sleep(0.5)
                    except Exception as e:
                        logging.error(f"Error al recargar la página: {e}")
                else:
                    logging.error("No se pudo acceder al campo contraseña después de 3 intentos")
                    return False

        # Esperar campo de contraseña (por si acaso)
        input_contrasena = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='password' and @name='p']")))
        input_contrasena.click()
        input_contrasena.clear()
        input_contrasena.send_keys(os.getenv('ASANA_PASSWORD', 'Clave123+-'))
        logging.info("Contraseña ingresada.")

        # Para el login, también usar TAB + ENTER
        try:
            input_contrasena.send_keys(Keys.TAB)  # Tab al botón "Iniciar sesión"
            time.sleep(0.5)
            input_contrasena.send_keys(Keys.ENTER)  # Enter para hacer clic
            logging.info("TAB + ENTER para iniciar sesión")
        except Exception as e:
            logging.warning(f"Error en login con TAB+ENTER: {e}")

        # Verificar login
        WebDriverWait(driver, 30).until(
            EC.url_contains("/0/portfolio/"))
        logging.info("Login completado exitosamente.")
        return True
        
    except Exception as e:
        logging.error(f"Error durante el login: {e}")
        return False

def navigate_to_team(driver, team_name):
    try:
        team_xpath = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class,'SpreadsheetPortfolioGridNameAndDetailsCellGroup-title')]//a[.//span[normalize-space()='{team_name}']]")))
        driver.execute_script("arguments[0].click();", team_xpath)
        WebDriverWait(driver, 30).until(
            EC.url_contains("/0/portfolio/"))
        logging.info(f"Equipo '{team_name}' seleccionado.")
        return True
    except Exception as e:
        logging.error(f"Error al navegar al equipo '{team_name}': {e}")
        return False

def agregar_invitados_team(driver, correos: List[str]):
    """
    Agrega invitados al portafolio ingresando correos y presionando Enter por cada uno.
    """
    try:
        # XPath único recomendado para el input
        input_xpath = "//input[@data-testid='tokenizer-input' and contains(@class,'TokenizerInput-input')]"

        for correo in correos:
            # reintentar varias veces si la UI se refresca
            for attempt in range(3):
                try:
                    time.sleep(0.5)  # pequeña pausa para evitar problemas de carga
                    WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, input_xpath))
                    )

                    input_emails = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, input_xpath))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", input_emails)

                    # Intentar clicks seguros
                    try:
                        input_emails.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", input_emails)

                    # Limpiar cualquier texto previo
                    try:
                        input_emails.send_keys(Keys.CONTROL, 'a')
                        input_emails.send_keys(Keys.BACKSPACE)
                    except Exception:
                        # fallback: enviar backspaces cortos
                        input_emails.send_keys('\b' * 10)

                    time.sleep(0.4)  # dejar que la UI procese el cambio

                    # Escribir el correo/usuario
                    input_emails.send_keys(correo)
                    time.sleep(0.6)  # esperar sugerencias si las hay

                    # Si es un email (contiene @), normalmente Asana acepta ENTER directamente.
                    # Para nombres o equipos, a veces hay que navegar la lista con ARROW_DOWN
                    if '@' in correo:
                        input_emails.send_keys(Keys.ENTER)
                    else:
                        input_emails.send_keys(Keys.ARROW_DOWN)
                        time.sleep(0.2)
                        input_emails.send_keys(Keys.ENTER)

                    logging.info(f"Correo/entrada '{correo}' ingresado y confirmado.")
                    time.sleep(0.4)
                    break
                except StaleElementReferenceException:
                    logging.warning(f"Elemento para correo '{correo}' se refrescó. Reintentando... (intento {attempt+1})")
                    time.sleep(1)
                    continue
                except Exception as e:
                    logging.warning(f"Error al ingresar '{correo}' (intento {attempt+1}): {e}")
                    time.sleep(1)
                    continue
        # esperar un poco a que se procesen los tokens y luego presionar Invitar
        time.sleep(1.5)
        boton_invitar = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'ButtonPrimaryPresentation') and normalize-space()='Invitar']"))
        )
        driver.execute_script("arguments[0].click();", boton_invitar)
        logging.info("Botón 'Invitar' clickeado. Invitaciones enviadas.")
        time.sleep(1.5)
        return True
    except Exception as e:
        logging.error(f"Error al agregar invitados: {e}")
        return False

def create_portfolio(driver, portfolio_name, team_name):
    try:
        more_actions = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(@aria-label,'More actions')]")))
        driver.execute_script("arguments[0].click();", more_actions)
        logging.info("Menú 'More actions' abierto.")

        create_portfolio_option = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='menuitem']//span[contains(text(), 'Crear un portafolio nuevo')]")))
        driver.execute_script("arguments[0].click();", create_portfolio_option)
        logging.info("Opción 'Crear un portafolio nuevo' seleccionada.")

        input_nombre_portafolio = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='new_portfolio_dialog_content_name_input']")))
        input_nombre_portafolio.click()
        input_nombre_portafolio.clear()
        input_nombre_portafolio.send_keys(portfolio_name)
        logging.info(f"Nombre del portafolio ingresado: {portfolio_name}")

        continue_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(text(), 'Continuar')]")))
        driver.execute_script("arguments[0].click();", continue_button)
        logging.info("Botón 'Continuar' para portafolio clickeado.")

        opcion_compartir = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='CreatePortfolioModalNextStepForm-rowItem']//label[contains(., 'Comparte con compañeros de equipo')]")))
        driver.execute_script("arguments[0].click();", opcion_compartir)
        logging.info("Opción 'Comparte con compañeros de equipo' seleccionada.")

        go_to_portfolio = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(text(), 'Ve al portafolio')]")))
        driver.execute_script("arguments[0].click();", go_to_portfolio)
        logging.info(f"Portafolio '{portfolio_name}' creado y accedido exitosamente.")

        correos_team = TEAM_CORREOS.get(team_name, [])
        if correos_team:
            if agregar_invitados_team(driver, correos_team):
                logging.info(f"Invitados agregados al portafolio '{portfolio_name}' para el equipo '{team_name}'.")
            else:
                logging.warning(f"No se pudieron agregar invitados al portafolio '{portfolio_name}' para el equipo '{team_name}'.")
        else:
            logging.warning(f"No hay correos configurados para el equipo '{team_name}'.")

        WebDriverWait(driver, 30).until(
            EC.url_contains("/0/portfolio/"))
        return True
    except Exception as e:
        logging.error(f"Error al crear portafolio: {e}")
        return False

def crear_proyecto(driver, project_name, portfolio_name):
    try:
        more_actions = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(@aria-label,'More actions')]")))
        driver.execute_script("arguments[0].click();", more_actions)
        logging.info("Menú 'More actions' abierto para proyecto.")

        create_project_option = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='menuitem']//span[contains(text(), 'Crear un proyecto nuevo')]")))
        driver.execute_script("arguments[0].click();", create_project_option)
        logging.info("Opción 'Crear un proyecto nuevo' seleccionada.")

        blank_project = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(text(), 'Proyecto en blanco')]")))
        driver.execute_script("arguments[0].click();", blank_project)
        logging.info("Tipo 'Proyecto en blanco' seleccionado.")

        input_nombre_proyecto = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='new_project_dialog_content_name_input']")))
        input_nombre_proyecto.click()
        input_nombre_proyecto.clear()
        input_nombre_proyecto.send_keys(project_name)
        logging.info(f"Nombre del proyecto ingresado: {project_name}")

        continue_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(text(), 'Continuar')]")))
        driver.execute_script("arguments[0].click();", continue_button)
        logging.info("Botón 'Continuar' para proyecto clickeado.")

        create_project = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(text(), 'Crear proyecto')]")))
        driver.execute_script("arguments[0].click();", create_project)
        logging.info(f"Proyecto '{project_name}' creado exitosamente.")

        project_url = driver.current_url

        logging.info("Regresando usando botón atrás del navegador")

        driver.back()

        time.sleep(5)

        WebDriverWait(driver, 30).until(
            EC.url_contains("/portfolio/")
        )

        logging.info("Se regresó correctamente al portafolio")
        return True, project_url
    except Exception as e:
        logging.error(f"Error al crear proyecto '{project_name}': {e}")
        return False, ""

def procesar_teams(driver, sprint_number: int, start_date: str, end_date: str) -> List[Dict]:
    portfolio_name = f"Sprint {sprint_number} - {format_date_to_spanish(start_date)} al {format_date_to_spanish(end_date)}"
    projects = [f"Proyecto {sprint_number}", f"Soporte {sprint_number}"]
    results = []

    try:
        if not portfolio_name or not projects:
            logging.error("No hay datos válidos para procesar.")
            return results

        for team in VALID_TEAMS:
            logging.info(f"Procesando equipo: {team}")

            if not navigate_to_team(driver, team):
                logging.error(f"No se pudo navegar al team {team}. Se continúa con el siguiente.")
                continue

            if create_portfolio(driver, portfolio_name, team):
                current_url = driver.current_url
                logging.info(f"Tipo: Portafolio, Nombre: {team} {portfolio_name}, Link: {current_url}, Team: {team}")
                results.append({
                    "type": "Portafolio",
                    "name": f"{team} {portfolio_name}",
                    "team": team,
                    "url": current_url
                })
            else:
                logging.error(f"No se pudo crear portafolio {portfolio_name} en team {team}.")
                continue

            suffix = TEAM_SUFFIXES.get(team, team)
            for project in projects:
                project_name = f"{project} - {suffix}"
                success, project_url = crear_proyecto(driver, project_name, portfolio_name)
                if success:
                    logging.info(f"Tipo: Proyecto, Nombre: {project_name}, Link: {project_url}, Team: {team}")
                    results.append({
                        "type": "Proyecto",
                        "name": project_name,
                        "team": team,
                        "url": project_url
                    })
                else:
                    logging.warning(f"No se pudo crear proyecto {project_name} en {team}")

            try:
                logging.info("Regresando a la URL principal de Sprints")

                driver.get("http://app.asana.com/0/portfolio/1205257480867940/1207672212054810")

                WebDriverWait(driver, 30).until(
                    EC.url_contains("/0/portfolio/")
                )

                time.sleep(5)

                logging.info("Regresado correctamente a la URL principal")

            except Exception as e:
                logging.error(f"No se pudo regresar a la URL principal: {e}")

        logging.info("Procesamiento completado para todos los teams.")
        return results
    except Exception as e:
        logging.error(f"Error en procesar_teams: {e}")
        return results

def run_automatizacion(sprint_number: int, start_date: str, end_date: str) -> tuple[bool, List[Dict]]:
    driver = iniciar_driver()
    if not driver:
        logging.error("No se pudo iniciar el driver. Terminando.")
        return False, []

    try:
        if not login_asana(driver):
            logging.error("Fallo en el login. Terminando.")
            return False, []

        results = procesar_teams(driver, sprint_number, start_date, end_date)
        logging.info("Automatización completada exitosamente.")
        return True, results
    except Exception as e:
        logging.error(f"Error general en la ejecución: {e}")
        return False, []
    finally:
        if driver:
            driver.quit()
            logging.info("Driver cerrado.")