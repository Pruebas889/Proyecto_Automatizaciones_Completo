from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Configuración para Google Sheets
scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file("C:\\Users\\dforero\\Pictures\\Proyecto_Automatizaciones_Completo\\Docuseal_Automatizacion\\docuseal2025-9b64ba667ffb.json", scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open_by_key('1Q1hKsx8QiYPc1y2MSHeNOvX-y4XRGz8WMBUlzzPmSaM').get_worksheet(0)  # Cambia 'YOUR_SHEET_ID' por el ID real

# Lee los datos de la hoja como DataFrame (asumiendo headers en la primera fila)
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Configuración de opciones para Chrome
chrome_options = Options()
chrome_options.add_argument('--start-maximized')

# Inicializa el driver
driver = webdriver.Chrome(options=chrome_options)

# Abre la página
driver.get("https://firmasdigitales.copservir.com/")
# Espera a que el botón esté presente
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/a/span"))
)

# Hace clic en el elemento por XPath
xpath = "/html/body/div[1]/div[2]/a/span"
element = driver.find_element(By.XPATH, xpath)
element.click()

# Espera a que el campo de correo esté presente
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//*[@id='user_email']"))
)

# Ingresa el correo en el campo correspondiente
import sys
# Obtener credenciales desde argumentos de línea de comandos
if len(sys.argv) != 3:
    print("Error: Se requieren email y contraseña como argumentos.")
    sys.exit(1)
email = sys.argv[1]
password = sys.argv[2]

email_xpath = "//*[@id='user_email']"
email_element = driver.find_element(By.XPATH, email_xpath)
email_element.send_keys(email)

# Espera a que el campo de contraseña esté presente
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//*[@id='user_password']"))
)
# Ingresa la contraseña en el campo correspondiente
password_xpath = "//*[@id='user_password']"
password_element = driver.find_element(By.XPATH, password_xpath)
password_element.send_keys(password)

# Espera a que el botón de inicio de sesión esté presente
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//*[@id='new_user']/div[2]/button"))
)
# Hace clic en el botón de inicio de sesión
login_button_xpath = "//*[@id='new_user']/div[2]/button"
login_button = driver.find_element(By.XPATH, login_button_xpath)
login_button.click()

# Espera y cierra el mensaje de 'Signed in successfully.'
try:
    cerrar_mensaje_xpath = "//a[@class='mr-1' and contains(text(),'×')]"
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, cerrar_mensaje_xpath))
    )
    cerrar_mensaje = driver.find_element(By.XPATH, cerrar_mensaje_xpath)
    driver.execute_script("arguments[0].scrollIntoView();", cerrar_mensaje)
    time.sleep(0.3) 
    cerrar_mensaje.click()
    time.sleep(0.3) 
except Exception as e:
    print(f"No se pudo cerrar el mensaje de login exitoso: {e}")

# Espera para que puedas ver la siguiente pantalla
time.sleep(0.2)
# Usar plantilla fija (solicitada):
plantilla_name = "Firmas Asociado"
print(f"Usando plantilla fija: {plantilla_name}")

# Haz clic en el botón de búsqueda (una vez)
WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and @title='Buscar']"))
)
buscar_btn = driver.find_element(By.XPATH, "//button[@type='submit' and @title='Buscar']")
buscar_btn.click()
time.sleep(0.2)

# Espera el campo de búsqueda y escribe el nombre de la plantilla
WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.XPATH, "//input[@id='search' and @name='q']"))
)
search_input = driver.find_element(By.XPATH, "//input[@id='search' and @name='q']")
search_input.clear()
search_input.send_keys(plantilla_name)
time.sleep(0.2)
search_input.send_keys(Keys.ENTER)
time.sleep(0.5)

# Haz clic en el resultado de la búsqueda
WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.XPATH, f"//a[contains(@class, 'flex') and .//div[contains(text(), '{plantilla_name}')]]"))
)
resultado_busqueda = driver.find_element(By.XPATH, f"//a[contains(@class, 'flex') and .//div[contains(text(), '{plantilla_name}')]]")
driver.execute_script("arguments[0].scrollIntoView();", resultado_busqueda)
time.sleep(0.2)
resultado_busqueda.click()
time.sleep(0.5)


# Intentar localizar directamente el enlace 'Editar' específico de la plantilla
try:
    editar_xpath = "//a[@href='/templates/3410/edit' and contains(., 'Editar')]"
    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, editar_xpath))
    )
    editar_link = driver.find_element(By.XPATH, editar_xpath)
    driver.execute_script("arguments[0].scrollIntoView();", editar_link)
    time.sleep(0.2)
    editar_link.click()
    time.sleep(0.5)
except Exception:
    # Fallback: usar el comportamiento anterior si no se encuentra el enlace específico
    WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.XPATH, "/html/body/div[2]/dashboard-dropzone/div[2]/div/a"))
    )
    resultados = driver.find_elements(By.XPATH, "/html/body/div[2]/dashboard-dropzone/div[2]/div/a")
    if not resultados:
        raise Exception("No se encontraron enlaces de plantilla en el dashboard-dropzone")
    resultado_original = resultados[-1]
    driver.execute_script("arguments[0].scrollIntoView();", resultado_original)
    resultado_original.click()
    time.sleep(0.5)

# Asegurarse de que la plantilla esté cargada (espera al botón de enviar)
WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.ID, "send_button"))
)
template_url = driver.current_url
print(f"Plantilla abierta y URL guardada: {template_url}")

# Detectar automáticamente columnas de nombres y correos en el DataFrame (case-insensitive)
cols = list(df.columns)
name_columns = [c for c in cols if 'nombre' in c.lower()]
email_columns = [c for c in cols if ('correo' in c.lower()) or ('correro' in c.lower()) or ('email' in c.lower())]

# Si no encuentra la columna específica que mencionaste, intenta el encabezado exacto 'Nombres -Punto Venta-Celular'
if not name_columns and 'Nombres -Punto Venta-Celular' in cols:
    name_columns = ['Nombres -Punto Venta-Celular']

if not email_columns and 'Correo' in cols:
    email_columns = ['Correo']

print(f"Columnas detectadas -> names: {name_columns}, emails: {email_columns}")

# Preparar lista global de destinatarios (una entrada por fila no enviada)
pending_rows = []  # list of (index, name, email)
# Queremos tomar los nombres desde la columna F (F2 hacia abajo). Si la hoja tiene
# al menos 6 columnas, usaremos la columna en la posición 5 (0-indexed). Si no,
# caemos al comportamiento anterior (detección por encabezados).
use_col_f_for_names = False
if len(df.columns) >= 6:
    use_col_f_for_names = True
    col_f_name = df.columns[5]

for index, row in df.iterrows():
    if str(row.get('Proceso de Envio', '')).strip().lower() == 'enviado':
        continue
    # Nombre: preferir columna F si existe
    name = ''
    if use_col_f_for_names:
        name = str(row.get(col_f_name, '')).strip()
    else:
        for c in name_columns:
            v = str(row.get(c, '')).strip()
            if v:
                name = v
                break

    # Email: mantener detección automática por encabezado
    email = ''
    for c in email_columns:
        v = str(row.get(c, '')).strip()
        if v:
            email = v
            break

    if name and email:
        pending_rows.append((index, name, email))

print(f"Filas pendientes a procesar: {len(pending_rows)}")
if not pending_rows:
    print("No hay destinatarios pendientes. Saliendo.")
else:
    try:
        # Abrir la plantilla y clicar ENVIAR solo UNA vez
        try:
            driver.get(template_url)
            time.sleep(0.4)
        except Exception as e:
            print(f"No se pudo navegar a la plantilla: {e}")

        try:
            WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "send_button")))
            boton_enviar = driver.find_element(By.ID, "send_button")
            driver.execute_script("arguments[0].scrollIntoView();", boton_enviar)
            time.sleep(0.3)
            boton_enviar.click()
            time.sleep(1)
        except Exception as e:
            print(f"Error al abrir el modal Enviar: {e}")
            raise

        # Activar Detallado
        try:
            detallado_radio = driver.find_element(By.XPATH, "//input[@id='option_detailed']")
            if not detallado_radio.is_selected():
                driver.execute_script("arguments[0].click();", detallado_radio)
                time.sleep(0.5)
                print("  Activada pestaña 'Detallado'")
        except Exception as e:
            print(f"No se pudo activar pestaña Detallado: {e}")

        # Ubicar el form detallado
        try:
            detailed_form = driver.find_element(By.XPATH, "//div[@id='detailed']//form")
        except Exception as e:
            print(f"No se encontró el formulario detallado: {e}")
            detailed_form = None

        if detailed_form is None:
            print("No se puede continuar sin el formulario Detallado.")
        else:
            # construir bloques seleccionando explícitamente los <submitter-item> (cada uno es un bloque)
            recipient_blocks = detailed_form.find_elements(By.XPATH, ".//submitter-item")
            needed = len(pending_rows)
            print(f"  Bloques existentes: {len(recipient_blocks)}, necesarios: {needed}")

            if needed > len(recipient_blocks):
                to_add = needed - len(recipient_blocks)
                print(f"  Agregando {to_add} bloques...")
                for _ in range(to_add):
                    try:
                        add_link = detailed_form.find_element(By.XPATH, ".//a[contains(., 'Agregar nuevo') or contains(., 'Agregar')]")
                        driver.execute_script("arguments[0].scrollIntoView();", add_link)
                        driver.execute_script("arguments[0].click();", add_link)
                        time.sleep(0.45)
                    except Exception as e:
                        print(f"  No se pudo agregar nuevo bloque: {e}")
                        break
                recipient_blocks = detailed_form.find_elements(By.XPATH, ".//submitter-item")

            print(f"  Bloques disponibles tras añadir: {len(recipient_blocks)}")

            # rellenar cada bloque con la fila correspondiente (orden normal: fila1->bloque1)
            pairs_to_fill = min(needed, len(recipient_blocks))
            for i in range(pairs_to_fill):
                idx, name_val, email_val = pending_rows[i]
                try:
                    block = recipient_blocks[i]
                    # inputs identificados por id que contiene 'detailed_name' / 'detailed_email'
                    n_el = block.find_element(By.XPATH, ".//input[contains(@id, 'detailed_name')]")
                    e_el = block.find_element(By.XPATH, ".//input[contains(@id, 'detailed_email')]")

                    # asegurar foco real en el input usando ActionChains + focus
                    driver.execute_script("arguments[0].scrollIntoView(true);", n_el)
                    ActionChains(driver).move_to_element(n_el).click(n_el).perform()
                    time.sleep(0.08)

                    # escribir con send_keys y luego ENTER para que el autocomplete acepte
                    try:
                        n_el.clear()
                        n_el.send_keys(name_val)
                        time.sleep(0.2)
                        n_el.send_keys(Keys.ENTER)
                        time.sleep(0.12)
                    except Exception:
                        # fallback JS
                        driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change')); arguments[0].blur();", n_el, name_val)
                        time.sleep(0.08)

                    # email input
                    driver.execute_script("arguments[0].scrollIntoView(true);", e_el)
                    ActionChains(driver).move_to_element(e_el).click(e_el).perform()
                    time.sleep(0.08)
                    try:
                        e_el.clear()
                        e_el.send_keys(email_val)
                        time.sleep(0.2)
                        e_el.send_keys(Keys.ENTER)
                        time.sleep(0.12)
                    except Exception:
                        driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change')); arguments[0].blur();", e_el, email_val)
                        time.sleep(0.08)

                    # comprobar si los valores quedaron aplicados; si no, forzar con JS
                    try:
                        current_name = n_el.get_attribute('value') or ''
                        current_email = e_el.get_attribute('value') or ''
                        if current_name.strip() != name_val.strip():
                            driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));", n_el, name_val)
                        if current_email.strip() != email_val.strip():
                            driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));", e_el, email_val)
                    except Exception:
                        pass

                    # pequeño delay
                    time.sleep(0.12)
                    print(f"  Bloque {i+1} rellenado: {name_val} / {email_val} (fila {idx+1})")
                except Exception as e:
                    print(f"  Error rellenando bloque {i+1} para fila {idx+1}: {e}")

            # Click final: intentar varios selectores y fallback a JS click
            # Antes de clicar Add/Enviar: localizar y DESELECCIONAR el checkbox 'preserve_order' para enviar en paralelo
            try:
                print("  Buscando checkboxes en el form detallado...")
                # Buscar todos los checkboxes con clase base-checkbox
                all_checkboxes = detailed_form.find_elements(By.XPATH, ".//input[@type='checkbox' and contains(@class, 'base-checkbox')]")
                print(f"  Encontrados {len(all_checkboxes)} checkboxes")
                
                checkbox_found = False
                for idx, chk in enumerate(all_checkboxes):
                    try:
                        chk_name = chk.get_attribute('name') or 'sin_name'
                        chk_id = chk.get_attribute('id') or 'sin_id'
                        print(f"    Checkbox {idx+1}: name='{chk_name}', id='{chk_id}', checked={chk.is_selected()}")
                        
                        # Si encuentra preserve_order, lo DESMARCAR (para envío paralelo)
                        if 'preserve' in chk_name.lower() or 'preserve' in chk_id.lower():
                            if chk.is_selected():
                                driver.execute_script("arguments[0].scrollIntoView(true);", chk)
                                time.sleep(0.2)
                                try:
                                    chk.click()
                                except Exception:
                                    driver.execute_script("arguments[0].click();", chk)
                                time.sleep(0.2)
                                print(f"  Checkbox 'preserve_order' DESMARCADO (envío paralelo activado)")
                                checkbox_found = True
                                break
                            else:
                                print(f"  Checkbox 'preserve_order' ya estaba desmarcado")
                                checkbox_found = True
                                break
                    except Exception as e:
                        print(f"    Error procesando checkbox {idx+1}: {e}")
                
                if not checkbox_found:
                    print("  Checkbox 'preserve_order' no encontrado. Intentando con JS directo...")
                    # Fallback: usar JS para encontrar y desmarcar
                    result = driver.execute_script("""
                    const checkboxes = document.querySelectorAll('input[type="checkbox"].base-checkbox');
                    for(let i = 0; i < checkboxes.length; i++){
                        const name = (checkboxes[i].getAttribute('name') || '').toLowerCase();
                        if(name.includes('preserve')){
                            if(checkboxes[i].checked){ checkboxes[i].click(); }
                            return 'desmarcado: ' + checkboxes[i].getAttribute('name');
                        }
                    }
                    return 'no encontrado';
                    """)
                    print(f"  Resultado JS: {result}")
                    
            except Exception as e:
                print(f"  Error buscando/desactivando checkbox preserve_order: {e}")

            add_clicked = False
            add_button_selectors = [
                "//div[@id='detailed']//button[contains(., 'Agregar') or contains(., 'agregar')]",
                "//div[@id='detailed']//button[@type='submit']",
                "//button[contains(., 'Agregar destinatarios') or contains(., 'agregar destinatarios')]",
                "//button[@id='send_button']",
            ]
            for sel in add_button_selectors:
                try:
                    add_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, sel)))
                    driver.execute_script("arguments[0].scrollIntoView();", add_button)
                    time.sleep(0.5)  # Esperar más tiempo después del checkbox
                    try:
                        add_button.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", add_button)
                    time.sleep(1)
                    print(f"  Click en Agregar/Enviar realizado (selector: {sel})")
                    add_clicked = True
                    break
                except Exception as e:
                    print(f"  Selector no encontrado/clicable: {sel} -> {e}")

            if not add_clicked:
                print("Error: no se pudo localizar ni clicar el botón Agregar/Enviar.")
            else:
                # Esperar después de clickear Agregar/Enviar
                print("  Esperando procesamiento de envío...")
                time.sleep(2)
                
                # Buscar y clickear el botón "Vista" de forma flexible
                try:
                    print("  Buscando botón 'Vista' para confirmar envío...")
                    vista_button_selectors = [
                        "//a[contains(@href, '/submissions/') and contains(text(), 'Vista')]",
                        "//a[contains(@class, 'btn') and contains(@class, 'btn-outline') and contains(text(), 'Vista')]",
                        "//a[contains(text(), 'Vista') and contains(@class, 'btn')]",
                        "//a[contains(text(), 'Vista')]",
                    ]
                    
                    vista_clicked = False
                    for sel in vista_button_selectors:
                        try:
                            vista_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, sel)))
                            driver.execute_script("arguments[0].scrollIntoView();", vista_button)
                            time.sleep(0.3)
                            try:
                                vista_button.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", vista_button)
                            time.sleep(1)
                            print(f"  Click en botón 'Vista' realizado (selector: {sel})")
                            vista_clicked = True
                            break
                        except Exception as e:
                            print(f"  Selector 'Vista' no encontrado/clicable: {sel}")
                    
                    if not vista_clicked:
                        print("  Advertencia: no se pudo localizar ni clicar el botón 'Vista'.")
                    else:
                        # Esperar a que cargue la página después de clickear Vista
                        print("  Esperando carga de página de detalles...")
                        time.sleep(2)
                        
                        # Buscar y clickear el botón "Firma en persona" de forma flexible
                        try:
                            print("  Buscando botón 'Firma en persona'...")
                            firma_button_selectors = [
                                "//a[@target='_blank' and contains(text(), 'Firma en persona')]",
                                "//a[contains(@class, 'btn-primary') and contains(text(), 'Firma en persona')]",
                                "//a[contains(@class, 'btn') and contains(@class, 'btn-primary') and contains(text(), 'Firma en persona')]",
                                "//a[contains(text(), 'Firma en persona')]",
                            ]
                            
                            firma_clicked = False
                            for sel in firma_button_selectors:
                                try:
                                    firma_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, sel)))
                                    driver.execute_script("arguments[0].scrollIntoView();", firma_button)
                                    time.sleep(0.3)
                                    # Guardar handles actuales antes del click (el enlace a veces abre en nueva pestaña)
                                    before_handles = driver.window_handles
                                    try:
                                        firma_button.click()
                                    except Exception:
                                        driver.execute_script("arguments[0].click();", firma_button)

                                    # Esperar un poco a que se abra la nueva pestaña/ventana
                                    new_handle = None
                                    for _ in range(10):
                                        handles = driver.window_handles
                                        if len(handles) > len(before_handles):
                                            # obtener el handle nuevo
                                            new_handle = [h for h in handles if h not in before_handles][0]
                                            break
                                        time.sleep(0.25)

                                    # Si detectamos nueva pestaña, cambiamos a ella
                                    if new_handle:
                                        try:
                                            driver.switch_to.window(new_handle)
                                            time.sleep(0.5)
                                            print("  Nueva pestaña detectada y activada para 'Firma en persona'.")
                                        except Exception as e:
                                            print(f"  No se pudo cambiar a la nueva pestaña: {e}")
                                    else:
                                        # si no hay nueva pestaña, dejamos el foco donde está
                                        time.sleep(0.5)

                                    print(f"  Click en botón 'Firma en persona' realizado (selector: {sel})")
                                    firma_clicked = True
                                    break
                                except Exception as e:
                                    print(f"  Selector 'Firma en persona' no encontrado/clicable: {sel}")
                            
                            if not firma_clicked:
                                print("  Advertencia: no se pudo localizar ni clicar el botón 'Firma en persona'.")
                            
                        except Exception as e:
                            print(f"  Error buscando/clickeando botón 'Firma en persona': {e}")
                    
                    # Si se hizo click en 'Firma en persona', procedemos a llenar el formulario por pasos
                    if firma_clicked:
                        try:
                            # Esperar al contenedor del formulario
                            form_container = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.ID, 'form_container'))
                            )
                            driver.execute_script("arguments[0].scrollIntoView(true);", form_container)
                            time.sleep(0.4)

                            # Para cada fila pendiente (pairs_to_fill corresponde al número de destinatarios rellenados)
                            processed_sheet_rows = []
                            for idx, _, _ in pending_rows[:pairs_to_fill]:
                                sheet_row = idx + 2  # corresponde al número de fila en Google Sheets
                                # Saltar filas antes de la fila 3 (el usuario pidió empezar en la fila 3)
                                if sheet_row < 3:
                                    print(f"    Saltando fila {sheet_row} (antes de la fila 3)")
                                    continue
                                try:
                                    # Obtener valores A,B,C de la hoja
                                    try:
                                        a_val = sheet.cell(sheet_row, 1).value or ''
                                    except Exception:
                                        a_val = ''
                                    try:
                                        b_val = sheet.cell(sheet_row, 2).value or ''
                                    except Exception:
                                        b_val = ''
                                    try:
                                        c_val = sheet.cell(sheet_row, 3).value or ''
                                    except Exception:
                                        c_val = ''

                                    print(f"    Llenando pasos para fila {sheet_row}: A='{a_val}' B='{b_val}' C='{c_val}'")

                                    # Paso 1: encontrar primer input visible dentro del form_container y escribir A
                                    try:
                                        input_el = WebDriverWait(form_container, 6).until(
                                            EC.visibility_of_element_located((By.XPATH, ".//form//input[@type='text' and (contains(@name,'values') or contains(@class,'base-input'))]"))
                                        )
                                        driver.execute_script("arguments[0].scrollIntoView(true);", input_el)
                                        input_el.clear()
                                        input_el.send_keys(str(a_val))
                                        time.sleep(0.2)
                                    except Exception as e:
                                        print(f"      No se encontró/llenó input paso 1 para fila {sheet_row}: {e}")

                                    # Click siguiente
                                    try:
                                        next_btn = WebDriverWait(form_container, 6).until(
                                            EC.element_to_be_clickable((By.ID, 'submit_form_button'))
                                        )
                                        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                                        time.sleep(0.15)
                                        try:
                                            next_btn.click()
                                        except Exception:
                                            driver.execute_script("arguments[0].click();", next_btn)
                                        time.sleep(0.8)
                                    except Exception as e:
                                        print(f"      No se pudo clicar 'siguiente' paso 1 para fila {sheet_row}: {e}")

                                    # Paso 2: rellenar con B
                                    try:
                                        input_el = WebDriverWait(form_container, 6).until(
                                            EC.visibility_of_element_located((By.XPATH, ".//form//input[@type='text' and (contains(@name,'values') or contains(@class,'base-input'))]"))
                                        )
                                        driver.execute_script("arguments[0].scrollIntoView(true);", input_el)
                                        input_el.clear()
                                        input_el.send_keys(str(b_val))
                                        time.sleep(0.2)
                                    except Exception as e:
                                        print(f"      No se encontró/llenó input paso 2 para fila {sheet_row}: {e}")

                                    # Click siguiente (paso 2)
                                    try:
                                        next_btn = WebDriverWait(form_container, 6).until(
                                            EC.element_to_be_clickable((By.ID, 'submit_form_button'))
                                        )
                                        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                                        time.sleep(0.15)
                                        try:
                                            next_btn.click()
                                        except Exception:
                                            driver.execute_script("arguments[0].click();", next_btn)
                                        time.sleep(0.8)
                                    except Exception as e:
                                        print(f"      No se pudo clicar 'siguiente' paso 2 para fila {sheet_row}: {e}")

                                    # Paso 3: rellenar con C
                                    try:
                                        input_el = WebDriverWait(form_container, 6).until(
                                            EC.visibility_of_element_located((By.XPATH, ".//form//input[@type='text' and (contains(@name,'values') or contains(@class,'base-input'))]"))
                                        )
                                        driver.execute_script("arguments[0].scrollIntoView(true);", input_el)
                                        input_el.clear()
                                        input_el.send_keys(str(c_val))
                                        time.sleep(0.2)
                                    except Exception as e:
                                        print(f"      No se encontró/llenó input paso 3 para fila {sheet_row}: {e}")

                                    # Click siguiente (finalizar este registro)
                                    try:
                                        next_btn = WebDriverWait(form_container, 6).until(
                                            EC.element_to_be_clickable((By.ID, 'submit_form_button'))
                                        )
                                        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                                        time.sleep(0.15)
                                        try:
                                            next_btn.click()
                                        except Exception:
                                            driver.execute_script("arguments[0].click();", next_btn)
                                        time.sleep(1)
                                        print(f"    Registro fila {sheet_row} completado (3 pasos).")
                                        # Registrar fila procesada para marcarla como 'Enviado' después
                                        processed_sheet_rows.append(sheet_row)
                                    except Exception as e:
                                        print(f"      No se pudo clicar 'siguiente' paso final para fila {sheet_row}: {e}")

                                except Exception as e:
                                    print(f"    Error procesando fila {sheet_row}: {e}")

                        except Exception as e:
                            print(f"    Error inicializando llenado de formulario: {e}")
                    
                except Exception as e:
                    print(f"  Error buscando/clickeando botón 'Vista': {e}")
                
                # marcar filas que realmente fueron procesadas como 'Enviado'
                for sheet_row in processed_sheet_rows:
                    try:
                        # convertir a idx visible en logs
                        log_idx = sheet_row - 1
                        sheet.update_cell(sheet_row, 7, 'Enviado')
                        print(f"Fila {log_idx} marcada como 'Enviado' en la hoja (G{sheet_row}).")
                    except Exception as e:
                        print(f"No se pudo marcar la fila {sheet_row} como Enviado: {e}")
    except Exception as e:
        print(f"Error en procesamiento global: {e}")

# Cierra el navegador al final de todos los envíos
driver.quit()
