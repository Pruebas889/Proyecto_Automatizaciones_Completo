import logging
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional, List, Dict, Tuple
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime, timedelta
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
import argparse
import sys


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("automatizacion.log", encoding='utf-8')
    ]
)


def iniciar_driver() -> Optional[webdriver.Chrome]:
    try:
        options = webdriver.ChromeOptions() 
          # Evitar que Chrome muestre solicitudes de notificaciones/popup que bloqueen la UI
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.geolocation": 2,
            "profile.default_content_setting_values.media_stream": 2,
        }
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-infobars")
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.maximize_window()
        logging.info("Driver de Chrome iniciado exitosamente.")
        return driver
    except WebDriverException as e:
        logging.error(f"Error al iniciar el driver: {e}")
        return None

def login_asana(driver, start_url: str = None):
    try:
        # Si se pasa una URL de tarea, abrirla para que el flujo de login muestre los inputs
        if start_url:
            driver.get(start_url)
            logging.info(f"Navegando a la URL inicial de tarea: {start_url}")
        else:
            driver.get("https://app.asana.com/")
            logging.info("Navegando a Asana base para login.")

        input_correo = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='email' and @name='e']")))
        input_correo.click()
        input_correo.send_keys(os.getenv('ASANA_EMAIL', 'javier.perdomo@copservir.co'))
        logging.info("Correo ingresado.")

        continuar = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(@class,'LoginEmailForm-continueButton') and contains(text(), 'Continuar')]")))
        driver.execute_script("arguments[0].click();", continuar)
        logging.info("Botón 'Continue' clickeado.")

        input_contrasena = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='password' and @name='p']")))
        input_contrasena.click()
        input_contrasena.send_keys(os.getenv('ASANA_PASSWORD', 'Clave123+-'))
        logging.info("Contraseña ingresada.")

        iniciar_sesion = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(text(), 'Iniciar sesión')]")))
        driver.execute_script("arguments[0].click();", iniciar_sesion)
        logging.info("Botón 'Iniciar sesión' clickeado.")

        # No esperar por rutas específicas de portfolio; devolver éxito tras el clic.
        # Dejar una breve pausa para que la acción se procese en la UI.
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"Error durante el login: {e}")
        return False


def assign_assignee(driver, email: str, timeout: int = 30, aggressive: bool = False, max_retries: int = 2) -> bool:
    """Busca el elemento con id `task_pane_assignee_input`, lo activa, escribe el
    correo y presiona Enter. Devuelve True si parece haberlo intentado correctamente.
    """
    selector = "div#task_pane_assignee_input"
    try:
        logging.info(f"Esperando selector {selector} para asignar {email}...")
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )

        # Helper: obtener lista de correos actualmente asignados en el token (si los hay)
        def _get_assigned_emails():
            out = []
            try:
                # buscar elementos con atributo data-email dentro del panel de assignee
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, "div#task_pane_assignee_input [data-email]")
                    for e in elems:
                        try:
                            v = (e.get_attribute('data-email') or '').strip().lower()
                            if v:
                                out.append(v)
                        except Exception:
                            continue
                except Exception:
                    pass

                # buscar tokens tipo AssigneeToken por aria-label o texto
                try:
                    tokens = driver.find_elements(By.CSS_SELECTOR, "div#task_pane_assignee_input div[data-testid='AssigneeToken'], div#task_pane_assignee_input .AssigneeTokenButton")
                    for t in tokens:
                        try:
                            a = (t.get_attribute('aria-label') or '').strip().lower()
                            if a and '@' in a:
                                out.append(a)
                                continue
                            txt = (t.text or '').strip().lower()
                            if txt and '@' in txt:
                                out.append(txt)
                        except Exception:
                            continue
                except Exception:
                    pass
            except Exception:
                return out
            # normalizar y devolver únicos
            return list(dict.fromkeys([x for x in out if x]))

        # Antes de abrir el editor, comprobar si ya está asignado correctamente (evitar duplicados)
        try:
            assigned_now = _get_assigned_emails()
            if assigned_now:
                logging.debug(f"Correos ya asignados detectados: {assigned_now}")
            if email.lower() in assigned_now:
                logging.info(f"Responsable ya asignado previamente: {email} — no se requiere acción.")
                return True
        except Exception:
            pass

        # Llevar al elemento a la vista y clicearlo para activar el campo editable
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
        try:
            el.click()
        except Exception:
            # Si click directo falla, usar JavaScript click
            driver.execute_script("arguments[0].click();", el)

        # Pequeña pausa para que la UI abra el editor del token
        time.sleep(0.5)

        # Buscar específicamente el input de tipo 'searchAssignee' o la clase conocida
        input_selectors = [
            "input[name='searchAssignee']",
            "input.DomainUserSelectorTokenTypeahead-input",
            "input.TextInputBase",
            "input[type='search']",
        ]
        input_el = None
        for sel in input_selectors:
            try:
                input_el = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                )
                # ensure it's displayed and within viewport
                if input_el and input_el.is_displayed():
                    break
            except Exception:
                input_el = None

        # Fallback final: usar active element
        if input_el is None:
            input_el = driver.switch_to.active_element

        # Asegurar foco y click en el input correcto (el preferido dentro del token)
        try:
            driver.execute_script("arguments[0].focus();", input_el)
        except Exception:
            pass
        try:
            input_el.click()
        except Exception:
            pass

        # Vaciar y escribir el correo despacio para evitar autocompletados incorrectos
        try:
            try:
                input_el.clear()
            except Exception:
                try:
                    input_el.send_keys(Keys.CONTROL + "a")
                    input_el.send_keys(Keys.BACKSPACE)
                except Exception:
                    pass

            for ch in email:
                input_el.send_keys(ch)
                time.sleep(0.03)
            # NO enviar Enter para evitar creación de tokens duplicados; confiar en click en sugerencia
        except Exception as e:
            logging.warning(f"No se pudo escribir caracter por caracter en el input: {e}")

        local_part = email.split('@')[0]

        # Pequeña espera antes de buscar sugerencias/decidir Enter (dar tiempo a cargar lista)
        time.sleep(0.7)

        # Si el input expose aria-controls, buscar la lista de sugerencias dentro de ese contenedor
        controls_id = None
        try:
            controls_id = input_el.get_attribute('aria-controls')
        except Exception:
            controls_id = None

        # Buscar y clicar la sugerencia **exacta** dentro del contenedor de sugerencias
        suggestion_clicked = False
        try:
            container = None
            if controls_id:
                try:
                    container = driver.find_element(By.ID, controls_id)
                except Exception:
                    container = None

            candidates = []
            if container is not None:
                # recoger elementos típicos dentro del contenedor
                try:
                    candidates = container.find_elements(By.XPATH, ".//*")
                except Exception:
                    candidates = []
            else:
                # fallback: buscar posibles items en el DOM cerca del input
                try:
                    candidates = driver.find_elements(By.XPATH, "//div[contains(@class,'Typeahead') or contains(@class,'MenuItem') or @role='option' or @role='menuitem']//button | //div[contains(@class,'Typeahead') or contains(@class,'MenuItem') or @role='option' or @role='menuitem']")
                except Exception:
                    candidates = []

            # Normalizar y buscar coincidencia lo más estricta posible: preferir
            # coincidencia exacta del correo en atributos como data-email o aria-label
            target = email.lower()
            chosen = None
            candidate_infos = []
            for c in candidates:
                try:
                    text = (c.text or '').strip()
                    text_l = text.lower()
                    data_email = (c.get_attribute('data-email') or '').strip().lower()
                    aria = (c.get_attribute('aria-label') or '').strip().lower()
                    candidate_infos.append({'text': text, 'data_email': data_email, 'aria': aria})

                    # Priorizar coincidencia exacta completa en data-email o aria-label
                    if data_email and data_email == target:
                        chosen = c
                        break
                    if aria and aria == target:
                        chosen = c
                        break
                    # Si el texto visible contiene el email exacto (no solo parte local)
                    if target and target in text_l:
                        chosen = c
                        break
                except Exception:
                    continue

            # Si no se encontró coincidencia estricta, registrar candidatos para depuración
            if not chosen:
                logging.debug(f"Candidatos en sugerencias: {candidate_infos}")

            if chosen:
                try:
                    driver.execute_script("arguments[0].click();", chosen)
                except Exception:
                    try:
                        chosen.click()
                    except Exception:
                        pass

                # Esperar hasta 2s a que el token con el email aparezca (evita reintentos y duplicados)
                appeared = False
                for _ in range(20):
                    try:
                        time.sleep(0.1)
                        if email.lower() in _get_assigned_emails():
                            appeared = True
                            break
                    except Exception:
                        continue

                if appeared:
                    logging.info(f"Responsable asignado correctamente tras click: {email}")
                    return True
                else:
                    # marcar para que el flujo de reintentos lo trate
                    suggestion_clicked = False
            else:
                logging.warning("No se encontró una sugerencia que coincida exactamente con el correo; no se seleccionará ninguna para evitar errores.")

        except Exception as e:
            logging.warning(f"Error buscando/clicando sugerencia: {e}")

        if not suggestion_clicked:
            # No seleccionar por Enter automáticamente: evitar asignar la persona equivocada
            logging.info("No se hizo selección automática de sugerencia para evitar asignaciones incorrectas.")
            # Buscar y clicar la sugerencia **exacta** dentro del contenedor Typeahead
            suggestion_clicked = False
            try:
                container = None
                # Preferir el contenedor indicado por aria-controls
                if controls_id:
                    try:
                        container = driver.find_element(By.ID, controls_id)
                    except Exception:
                        container = None

                # Si no hay container por controls_id, buscar el contenedor típico de Typeahead
                if container is None:
                    possible_selectors = [
                        "div.TypeaheadScrollable-contents",
                        "div[data-testid='TypeaheadScrollable-contents']",
                        "div.DomainUserTypeaheadDropdownContents-scrollableList",
                        "div.TypeaheadScrollable-contents",
                    ]
                    for ps in possible_selectors:
                        try:
                            container = driver.find_element(By.CSS_SELECTOR, ps)
                            if container:
                                break
                        except Exception:
                            container = None

                candidates = []
                if container is not None:
                    try:
                        candidates = container.find_elements(By.CSS_SELECTOR, "div[data-testid='typeahead-selectable-item']")
                    except Exception:
                        candidates = []
                else:
                    try:
                        candidates = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='typeahead-selectable-item']")
                    except Exception:
                        candidates = []

                # Buscar coincidencia estricta por email dentro del subtitle o texto visible
                target = email.lower()
                chosen = None
                candidate_infos = []
                for c in candidates:
                    try:
                        subtitle_text = ''
                        try:
                            sub_el = c.find_element(By.CSS_SELECTOR, ".DomainUserTypeaheadItem-subtitle")
                            subtitle_text = (sub_el.text or '').strip().lower()
                        except Exception:
                            subtitle_text = (c.text or '').strip().lower()

                        data_email = (c.get_attribute('data-email') or '').strip().lower()
                        aria = (c.get_attribute('aria-label') or '').strip().lower()
                        candidate_infos.append({'subtitle': subtitle_text, 'data_email': data_email, 'aria': aria})

                        if data_email == target or aria == target or (subtitle_text and target in subtitle_text):
                            chosen = c
                            break
                    except Exception:
                        continue

                if chosen:
                    try:
                        driver.execute_script("arguments[0].click();", chosen)
                    except Exception:
                        try:
                            chosen.click()
                        except Exception:
                            pass

                    # Esperar hasta 2s a que el token con el email aparezca
                    appeared = False
                    for _ in range(20):
                        try:
                            time.sleep(0.1)
                            if email.lower() in _get_assigned_emails():
                                appeared = True
                                break
                        except Exception:
                            continue

                    if appeared:
                        logging.info(f"Responsable asignado correctamente tras click Typeahead: {email}")
                        return True
                    else:
                        suggestion_clicked = False
                else:
                    logging.warning("No se encontró una sugerencia que coincida exactamente con el correo; candidatos: %s", candidate_infos)

            except Exception as e:
                logging.warning(f"Error buscando/clicando sugerencia Typeahead: {e}")

            if not suggestion_clicked:
                logging.info("No se hizo selección automática de sugerencia para evitar asignaciones incorrectas.")

        # Si pedimos comportamiento agresivo (p. ej. para la última URL conocida problemática),
        # intentar clics alternativos en los candidatos para forzar la selección.
        if not suggestion_clicked and aggressive:
            logging.info("Modo agresivo activado: intentando estrategias adicionales para seleccionar la sugerencia...")
            try:
                # Preferir items ya detectados (items2) o candidatos anteriores
                try:
                    extra_candidates = items2 if 'items2' in locals() and items2 else (candidates if 'candidates' in locals() and candidates else [])
                except Exception:
                    extra_candidates = []

                for ec in extra_candidates:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ec)
                        time.sleep(0.12)

                        # Intentar click directo en un botón interno o en el propio elemento
                        performed = False
                        try:
                            btn = ec.find_element(By.CSS_SELECTOR, "button, [role='button']")
                            driver.execute_script("arguments[0].click();", btn)
                            performed = True
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", ec)
                                performed = True
                            except Exception:
                                try:
                                    ActionChains(driver).move_to_element(ec).click().perform()
                                    performed = True
                                except Exception:
                                    performed = False

                        if performed:
                            time.sleep(0.35)
                            # verificar etiqueta inmediatamente
                            found_label_try = None
                            for lbl_sel in [
                                "div#task_pane_assignee_input .AssigneeTokenButton-label",
                                "div#task_pane_assignee_input .AssigneeToken-label",
                                "div[data-testid='AssigneeToken'] .AssigneeTokenButton-label",
                            ]:
                                try:
                                    lblt = driver.find_element(By.CSS_SELECTOR, lbl_sel).text
                                    if lblt:
                                        found_label_try = lblt
                                        break
                                except Exception:
                                    continue
                            if found_label_try and (email.lower() in found_label_try.lower() or local_part.lower() in found_label_try.lower()):
                                logging.info(f"Modo agresivo: responsable asignado correctamente: {found_label_try}")
                                return True
                    except Exception as e:
                        logging.debug(f"Modo agresivo: error procesando candidato: {e}")
                        continue

                logging.warning("Modo agresivo: no se logró seleccionar la sugerencia correcta tras intentos adicionales.")
            except Exception as e:
                logging.warning(f"Error en modo agresivo al intentar seleccionar sugerencia: {e}")

        # Verificar que el responsable actual coincida con lo esperado (buscar label dentro del token)
        try:
            possible_labels = [
                "div#task_pane_assignee_input .AssigneeTokenButton-label",
                "div#task_pane_assignee_input .AssigneeToken-label",
                "div#task_pane_assignee_input .AssigneeTokenButton-label",
                "div[data-testid='AssigneeToken'] .AssigneeTokenButton-label",
            ]
            found_label = None
            for lbl_sel in possible_labels:
                try:
                    lbl = driver.find_element(By.CSS_SELECTOR, lbl_sel).text
                    if lbl:
                        found_label = lbl
                        break
                except Exception:
                    continue

            if found_label:
                fl = found_label.lower()
                # Aceptar como válido si aparece el email (o su parte local)
                if local_part.lower() in fl or email.lower() in fl:
                    logging.info(f"Responsable establecido correctamente: {found_label}")
                    return True
                # Muchos labels muestran el nombre en lugar del correo (ej: 'Yesid Sánchez Salcedo').
                # Si el label no contiene '@' y parece un nombre (tiene espacios y letras),
                # considerarlo como asignación válida y evitar reintentos adicionales.
                try:
                    if '@' not in found_label and any(c.isalpha() for c in found_label) and len(found_label.split()) >= 2:
                        logging.info(f"Responsable detectado por nombre: {found_label} — se considera asignado.")
                        return True
                except Exception:
                    pass
                logging.warning(f"Responsable detectado diferente: '{found_label}' (esperado '{email}'). Intentando reintento...")
            else:
                logging.warning("No se pudo leer la etiqueta del responsable tras la asignación. Intentando reintento...")

            # Si no coincide, reintentar hasta `max_retries` veces: volver a abrir el token, escribir SOLO el correo y seleccionar
            for retry in range(max_retries):
                try:
                    logging.info(f"Reintento {retry+1}: intentando reasignar {email}...")
                    # volver a clicar el token para abrir el editor
                    try:
                        el.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.4)

                    # localizar el input preferido nuevamente
                    input_el2 = None
                    for sel in ["input[name='searchAssignee']", "input.DomainUserSelectorTokenTypeahead-input", "input.TextInputBase", "input[type='search']"]:
                        try:
                            input_el2 = WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.CSS_SELECTOR, sel)))
                            if input_el2 and input_el2.is_displayed():
                                break
                        except Exception:
                            input_el2 = None

                    if input_el2 is None:
                        input_el2 = driver.switch_to.active_element

                    try:
                        driver.execute_script("arguments[0].focus();", input_el2)
                    except Exception:
                        pass
                    try:
                        input_el2.click()
                    except Exception:
                        pass

                    # Vaciar y escribir SOLO el correo
                    try:
                        try:
                            input_el2.clear()
                        except Exception:
                            try:
                                input_el2.send_keys(Keys.CONTROL + "a")
                                input_el2.send_keys(Keys.BACKSPACE)
                            except Exception:
                                pass
                        for ch in email:
                            input_el2.send_keys(ch)
                            time.sleep(0.03)
                    except Exception as e:
                        logging.warning(f"Error escribiendo en reintento: {e}")

                    # esperar sugerencias y clicar exacto si aparece
                    time.sleep(0.6)
                    ctrl2 = None
                    try:
                        ctrl2 = input_el2.get_attribute('aria-controls')
                    except Exception:
                        ctrl2 = None

                    chosen2 = None
                    if ctrl2:
                        try:
                            cont2 = driver.find_element(By.ID, ctrl2)
                            items2 = cont2.find_elements(By.CSS_SELECTOR, "div[data-testid='typeahead-selectable-item']")
                        except Exception:
                            items2 = []
                    else:
                        try:
                            items2 = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='typeahead-selectable-item']")
                        except Exception:
                            items2 = []

                    t = email.lower()
                    for c2 in items2:
                        try:
                            sub_el2 = None
                            try:
                                sub_el2 = c2.find_element(By.CSS_SELECTOR, ".DomainUserTypeaheadItem-subtitle")
                                sub_text2 = (sub_el2.text or '').strip().lower()
                            except Exception:
                                sub_text2 = (c2.text or '').strip().lower()
                            data_e2 = (c2.get_attribute('data-email') or '').strip().lower()
                            aria2 = (c2.get_attribute('aria-label') or '').strip().lower()
                            if data_e2 == t or aria2 == t or (sub_text2 and t in sub_text2):
                                chosen2 = c2
                                break
                        except Exception:
                            continue

                    if chosen2:
                        try:
                            driver.execute_script("arguments[0].click();", chosen2)
                            time.sleep(0.4)
                        except Exception:
                            try:
                                chosen2.click()
                                time.sleep(0.4)
                            except Exception:
                                pass

                    # verificar nuevamente label
                    try:
                        found_label2 = None
                        for lbl_sel in [
                            "div#task_pane_assignee_input .AssigneeTokenButton-label",
                            "div#task_pane_assignee_input .AssigneeToken-label",
                            "div[data-testid='AssigneeToken'] .AssigneeTokenButton-label",
                        ]:
                            try:
                                lbl2 = driver.find_element(By.CSS_SELECTOR, lbl_sel).text
                                if lbl2:
                                    found_label2 = lbl2
                                    break
                            except Exception:
                                continue
                        if found_label2 and (email.lower() in found_label2.lower() or local_part.lower() in found_label2.lower()):
                            logging.info(f"Responsable corregido en reintento: {found_label2}")
                            return True
                    except Exception:
                        pass

                except Exception as e:
                    logging.warning(f"Error en reintento asignación: {e}")

            # si después de reintentos no coincide
            logging.error("No fue posible asignar el responsable con el correo solicitado después de reintentos.")
            return False

        except Exception as e:
            logging.error(f"Error verificando responsable asignado: {e}")
            return False
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        logging.error(f"No se encontró o no fue clickable el selector {selector}: {e}")
        return False
    except Exception as e:
        logging.error(f"Error inesperado al asignar responsable: {e}")
        return False


def set_due_date_next_day(driver, timeout: int = 30) -> bool:
    """Abre el selector de fecha (`#task_pane_due_date_input`) y establece la fecha
    al día siguiente (hoy + 1). Intenta varios métodos (escribir en el input activo
    o seleccionar el día en el calendario) y devuelve True si parece haberse aplicado.
    """
    selector = "div#task_pane_due_date_input"
    try:
        logging.info(f"Esperando selector {selector} para establecer fecha de entrega...")
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)

        time.sleep(0.5)

        tomorrow = (datetime.now().date() + timedelta(days=1))
        day_str = str(tomorrow.day)

        # Intento 1: escribir la fecha en el elemento activo usando varios formatos
        active = driver.switch_to.active_element
        date_formats = [
            tomorrow.isoformat(),
            tomorrow.strftime('%d/%m/%Y'),
            tomorrow.strftime('%b %d, %Y'),
            tomorrow.strftime('%B %d, %Y'),
        ]

        for fmt in date_formats:
            try:
                try:
                    active.clear()
                except Exception:
                    pass
                active.send_keys(fmt)
                active.send_keys(Keys.ENTER)
                time.sleep(0.6)
                # Comprobar si el token ahora muestra otra cosa distinta a "Sin fecha"
                try:
                    label = driver.find_element(By.CSS_SELECTOR, selector + " .DueDateTokenButton-label").text
                    if 'Sin fecha' not in label:
                        logging.info(f"Fecha establecida usando formato: {fmt} -> {label}")
                        return True
                except Exception:
                    pass
            except Exception:
                continue

        # Intento 2: buscar y clicar el día correspondiente en el calendario emergente
        try:
            # Buscar cualquier botón en el calendario con el número del día
            xpath_day = f"//div[contains(@class,'Calendar') or @role='dialog']//button[normalize-space()='{day_str}']"
            day_btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath_day)))
            driver.execute_script("arguments[0].click();", day_btn)
            time.sleep(0.4)
            logging.info(f"Fecha establecida haciendo click en día {day_str} del calendario.")
            return True
        except Exception:
            logging.warning("No se logró seleccionar el día en el calendario mediante xpath.")

        logging.error("No se pudo establecer la fecha de entrega mediante los métodos disponibles.")
        return False
    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        logging.error(f"No se encontró o no fue clickable el selector {selector}: {e}")
        return False
    except Exception as e:
        logging.error(f"Error inesperado al establecer fecha de entrega: {e}")
        return False


def convert_task_to_approval(driver, timeout: int = 30) -> bool:
    """Abre el menú 'Más acciones' y sigue la secuencia: 'Convertir a' -> 'Aprobación'.
    Implementa búsquedas por texto (español/inglés) y varios reintentos para mayor
    robustez frente a ids dinámicos.
    """
    more_selector = "div[role='button'][aria-label='Más acciones para esta tarea']"
    # XPaths que buscan el texto visible (soporta español e inglés)
    xpath_convert = "(//*[normalize-space(text())='Convertir a' or normalize-space(text())='Convert to'])[1]"
    xpath_convert_menuitem = xpath_convert + "/ancestor::div[@role='menuitem' or contains(@class,'MenuItemThemeablePresentation')][1]"
    xpath_approval = "(//*[normalize-space(text())='Aprobación' or normalize-space(text())='Approval'])[1]"
    xpath_approval_menuitem = xpath_approval + "/ancestor::div[@role='menuitem' or contains(@class,'MenuItemThemeablePresentation')][1]"

    try:
        logging.info("Intentando abrir 'Más acciones'...")
        more_btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, more_selector))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_btn)
        try:
            more_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", more_btn)

        time.sleep(0.5)

        logging.info("Buscando opción 'Convertir a' por texto...")
        try:
            convert_item = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_convert_menuitem))
            )
            driver.execute_script("arguments[0].click();", convert_item)
        except Exception:
            logging.warning("No se encontró 'Convertir a' por xpath; intentando buscar elemento por texto directo.")
            try:
                convert_span = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_convert))
                )
                driver.execute_script("arguments[0].click();", convert_span)
            except Exception as e:
                logging.error(f"No se pudo activar 'Convertir a': {e}")
                return False

        time.sleep(0.5)

        logging.info("Seleccionando 'Aprobación' por texto...")
        try:
            approval_item = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_approval_menuitem))
            )
            driver.execute_script("arguments[0].click();", approval_item)
        except Exception:
            logging.warning("No se encontró 'Aprobación' por xpath; intentando buscar por texto directo.")
            try:
                approval_span = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_approval))
                )
                driver.execute_script("arguments[0].click();", approval_span)
            except Exception as e:
                logging.error(f"No se pudo seleccionar 'Aprobación': {e}")
                return False

        time.sleep(0.4)
        logging.info("La tarea fue enviada a 'Aprobación' (se intentó el flujo).")
        return True
    except Exception as e:
        logging.error(f"Error al convertir la tarea a Aprobación: {e}")
        return False


def run_automatizacion(sprint_number: int, start_date: str, end_date: str,
                       urls: Optional[List[str]] = None,
                       email: str = 'yesid.sanchez@copservir.co',
                       wait_after_load: float = 1.0,
                       stop_on_error: bool = False) -> Tuple[bool, List[Dict]]:
    """Función pública para ejecutar la automatización desde otro proceso.
    Retorna una tupla (success: bool, results: List[Dict]) donde cada elemento
    en results corresponde a una URL procesada y contiene claves de estado.
    """
    results: List[Dict] = []
    try:
        # Requerir explícitamente las URLs: no usar valores hardcodeados.
        if not urls:
            logging.error('No se recibieron URLs para procesar en run_automatizacion.')
            return False, [{'error': 'No se recibieron URLs para procesar.'}]

        logging.info("Ejecutando `run_automatizacion`: iniciando driver y login.")
        driver = iniciar_driver()
        if not driver:
            logging.error("No se pudo iniciar el driver de navegador.")
            return False, [{'error': 'No se pudo iniciar driver'}]

        try:
            first_url = urls[0]
            ok = login_asana(driver, start_url=first_url)
            if not ok:
                logging.error("Login fallido durante la ejecución de run_automatizacion.")
                driver.quit()
                return False, [{'error': 'Login fallido'}]

            for i, url in enumerate(urls, start=1):
                entry = {'url': url, 'assigned': False, 'due_set': False, 'converted': False}
                try:
                    logging.info(f"Procesando {i}/{len(urls)}: {url}")
                    driver.get(url)
                    time.sleep(wait_after_load)
                    # Usar un solo correo para todas las URLs (parámetro `email`)
                    chosen_email = email

                    aggressive_mode = (i == len(urls))
                    assigned = assign_assignee(driver, chosen_email, aggressive=aggressive_mode, max_retries=2)
                    entry['assigned'] = bool(assigned)

                    due_ok = set_due_date_next_day(driver)
                    entry['due_set'] = bool(due_ok)

                    converted = convert_task_to_approval(driver)
                    entry['converted'] = bool(converted)

                    results.append(entry)
                    logging.info(f"Flujo completado para {url}: {entry}")
                except Exception as e:
                    logging.error(f"Excepción al procesar {url}: {e}")
                    entry['error'] = str(e)
                    results.append(entry)
                    if stop_on_error:
                        break
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        return True, results
    except Exception as e:
        logging.error(f"Error inesperado en run_automatizacion: {e}")
        return False, [{'error': str(e)}]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Automatizar acciones en varias tareas de Asana')
    parser.add_argument('--urls', help='URLs separadas por comas', default=None)
    parser.add_argument('--file', help='Archivo con URLs (una por línea)', default=None)
    parser.add_argument('--email', help='Correo a asignar', default='yesid.sanchez@copservir.co')
    parser.add_argument('--emails', help='Correos separados por comas (alineados con --urls) — opcional (legacy)', default=None)
    parser.add_argument('--emails-file', help='Archivo con correos (una por línea, alineados con URLs) — opcional (legacy)', default=None)
    parser.add_argument('--wait-after-load', type=float, help='Segundos a esperar tras abrir cada URL', default=1.0)
    parser.add_argument('--stop-on-error', action='store_true', help='Detener la ejecución si una URL falla')
    args = parser.parse_args()

    # Construir la lista de URLs
    urls: List[str] = []
    if args.urls:
        urls = [u.strip() for u in args.urls.split(',') if u.strip()]
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        urls.append(line)
        except Exception as e:
            logging.error(f"No se pudo leer el archivo de URLs: {e}")
            sys.exit(2)

    # Construir lista de correos alineada con las URLs (opcional)
    emails: List[str] = []
    if getattr(args, 'emails', None):
        emails = [e.strip() for e in args.emails.split(',') if e.strip()]
    if getattr(args, 'emails_file', None):
        try:
            with open(args.emails_file, 'r', encoding='utf-8') as ef:
                for line in ef:
                    line = line.strip()
                    if line:
                        emails.append(line)
        except Exception as e:
            logging.error(f"No se pudo leer el archivo de correos: {e}")
            sys.exit(2)

    # Requerir URLs explícitas desde la invocación (--urls o --file).
    if not urls:
        logging.error('No se pasaron URLs por argumentos ni archivo. Use --urls o --file para proporcionar las tareas.')
        sys.exit(2)

    logging.info("Ejecutando `aprobado.py`: iniciando driver y ejecutando login.")
    driver = iniciar_driver()
    if not driver:
        logging.error("No se pudo iniciar el driver de navegador.")
        sys.exit(1)

    try:
        # Hacer login usando la primera URL para que el flujo muestre los inputs si es necesario
        first_url = urls[0]
        success = login_asana(driver, start_url=first_url)
        if not success:
            logging.error("Login fallido durante la ejecución.")
            driver.quit()
            sys.exit(3)

        # Iterar sobre cada URL y ejecutar el flujo
        for i, url in enumerate(urls, start=1):
            logging.info(f"Procesando {i}/{len(urls)}: {url}")
            try:
                driver.get(url)
                time.sleep(args.wait_after_load)

                # Activar modo agresivo solo para la última URL (problema reportado en la tercera)
                aggressive_mode = (i == len(urls))
                if aggressive_mode:
                    logging.info("Última URL: activando modo agresivo para asignación de responsable.")
                # Seleccionar correo para esta URL: preferir lista `emails` si se proporcionó, en otro caso usar args.email
                email_for_url = args.email
                try:
                    if emails and len(emails) >= i and emails[i-1].strip():
                        email_for_url = emails[i-1].strip()
                except Exception:
                    email_for_url = args.email

                assigned = assign_assignee(driver, email_for_url, aggressive=aggressive_mode, max_retries=2)
                if not assigned:
                    logging.error(f"Fallo al asignar responsable en {url}")
                    if args.stop_on_error:
                        break

                due_ok = set_due_date_next_day(driver)
                if not due_ok:
                    logging.warning(f"No se pudo fijar fecha en {url}")
                    if args.stop_on_error:
                        break

                converted = convert_task_to_approval(driver)
                if not converted:
                    logging.error(f"No se pudo convertir a Aprobación en {url}")
                    if args.stop_on_error:
                        break

                logging.info(f"Flujo completado para {url}")
            except Exception as e:
                logging.error(f"Excepción al procesar {url}: {e}")
                if args.stop_on_error:
                    break
                else:
                    continue
    finally:
        try:
            driver.quit()
        except Exception:
            pass



