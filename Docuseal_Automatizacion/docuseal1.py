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
creds = Credentials.from_service_account_file('C:\\Users\\dforero\\Pictures\\Proyecto_Automatizaciones_Completo\\Docuseal_Automatizacion\\docuseal2025-9b64ba667ffb.json', scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open_by_key('1c2U7Pz7azlzah04zYtOvn_UTsBSYlEqRU1Sf2kE48Tc').get_worksheet(0)  # Cambia 'YOUR_SHEET_ID' por el ID real

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

# Ahora, loop para cada fila en el DataFrame
for index, row in df.iterrows():
    # Omitir filas ya enviadas
    if str(row.get('Proceso de Envio', '')).strip().lower() == 'enviado':
        print(f"Fila {index+1} ya enviada, se omite.")
        continue
    try:
        print(f"Procesando fila {index + 1}: {row['Documento']} (Plantilla: {row['Plantilla']})")

        # Vuelve a la página inicial
        driver.get("https://firmasdigitales.copservir.com/")
        time.sleep(0.3)  # Espera breve para asegurar carga

        # Extrae los datos de la fila
        doc_name = row['Documento']
        jefe_name = row['Nombre 1 Jefe Inmediato']
        jefe_email = row['Correo 1 Jefe Inmediato']
        trabajador_name = row['Nombre 2 Trabajador']
        trabajador_email = row['Correo 2 Trabajador']
        supervisor_name = row['Nombre 3 Supervisor']
        supervisor_email = row['Correo 3 Supervisor']
        plantilla_name = row['Plantilla']  # Nueva columna para la plantilla

       # Haz clic en el botón de búsqueda
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
        search_input.clear()  # Limpia el campo antes de escribir
        search_input.send_keys(plantilla_name)
        time.sleep(0.2)
        search_input.send_keys(Keys.ENTER)
        time.sleep(0.2)

        # Haz clic en el resultado de la búsqueda
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[contains(@class, 'flex') and .//div[contains(text(), '{plantilla_name}')]]"))
        )
        resultado_busqueda = driver.find_element(By.XPATH, f"//a[contains(@class, 'flex') and .//div[contains(text(), '{plantilla_name}')]]")
        driver.execute_script("arguments[0].scrollIntoView();", resultado_busqueda)
        time.sleep(0.2)
        resultado_busqueda.click()
        time.sleep(0.3) 

        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, "/html/body/div[2]/dashboard-dropzone/div[2]/div/a"))
        )
        resultados = driver.find_elements(By.XPATH, "/html/body/div[2]/dashboard-dropzone/div[2]/div/a")
        if not resultados:
            raise Exception("No se encontraron enlaces de plantilla en el dashboard-dropzone")
        resultado_original = resultados[-1]  # El último de la derecha (el original)
        driver.execute_script("arguments[0].scrollIntoView();", resultado_original)
        resultado_original.click()
        time.sleep(0.2)


        # Chico SENA
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[1]/div[2]/a[2]"))
        )
        elemento_final = driver.find_element(By.XPATH, "/html/body/div[2]/div[1]/div[2]/a[2]")
        driver.execute_script("arguments[0].scrollIntoView();", elemento_final)
        time.sleep(0.2)
        elemento_final.click()
        time.sleep(0.3) 

        # Haz clic en el botón de enviar con id 'send_button'
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "send_button"))
        )
        boton_enviar2 = driver.find_element(By.ID, "send_button")
        driver.execute_script("arguments[0].scrollIntoView();", boton_enviar2)
        time.sleep(0.2)
        boton_enviar2.click()
        time.sleep(0.3) 

        # Haz clic en el siguiente elemento por XPath
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='modal']/turbo-modal/div[2]/div[2]/toggle-visible/div/div[3]/label"))
        )
        elemento_final = driver.find_element(By.XPATH, "//*[@id='modal']/turbo-modal/div[2]/div[2]/toggle-visible/div/div[3]/label")
        driver.execute_script("arguments[0].scrollIntoView();", elemento_final)
        time.sleep(0.2)
        elemento_final.click()
        time.sleep(0.3) 

        # Llenar campos de nombre y correo
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' and contains(@class, 'base-input') and @placeholder='Nombre']")
        emails = driver.find_elements(By.XPATH, "//input[@type='email' and contains(@class, 'base-input')]")

        # Jefe Inmediato
        if len(inputs) > 0:
            inputs[0].click()
            inputs[0].clear()
            inputs[0].send_keys(jefe_name)
            time.sleep(0.2)
            for email in emails:
                if email.is_displayed() and email.is_enabled() and email.get_attribute('value') == "":
                    try:
                        driver.execute_script("arguments[0].scrollIntoView();", email)
                        email.clear()
                        email.send_keys(jefe_email)
                        time.sleep(0.2)
                        break
                    except Exception as e:
                        print(f"No se pudo escribir el correo de Jefe Inmediato: {e}")

        # Trabajador Evaluado
        if len(inputs) > 1:
            inputs[1].click()
            inputs[1].clear()
            inputs[1].send_keys(trabajador_name)
            time.sleep(0.2)
            for email in emails:
                if email.is_displayed() and email.is_enabled() and email.get_attribute('value') == "":
                    try:
                        driver.execute_script("arguments[0].scrollIntoView();", email)
                        email.clear()
                        email.send_keys(trabajador_email)
                        time.sleep(0.2)
                        break
                    except Exception as e:
                        print(f"No se pudo escribir el correo de Trabajador Evaluado: {e}")

        # Supervisor
        if len(inputs) > 2:
            inputs[2].click()
            inputs[2].clear()
            inputs[2].send_keys(supervisor_name)
            time.sleep(0.2)
            for email in emails:
                if email.is_displayed() and email.is_enabled() and email.get_attribute('value') == "":
                    try:
                        driver.execute_script("arguments[0].scrollIntoView();", email)
                        email.clear()
                        email.send_keys(supervisor_email)
                        time.sleep(0.2)
                        break
                    except Exception as e:
                        print(f"No se pudo escribir el correo de Supervisor: {e}")

        # Cuarta persona (si hay 4 campos)
        if len(inputs) > 3:
            director_name = row.get('Nombre 4 Director', '')
            director_email = row.get('Correo 4 Director', '')
            if director_name and director_email:
                inputs[3].click()
                inputs[3].clear()
                inputs[3].send_keys(director_name)
                time.sleep(0.2)
                for email in emails:
                    if email.is_displayed() and email.is_enabled() and email.get_attribute('value') == "":
                        try:
                            driver.execute_script("arguments[0].scrollIntoView();", email)
                            email.clear()
                            email.send_keys(director_email)
                            time.sleep(0.2)
                            break
                        except Exception as e:
                            print(f"No se pudo escribir el correo de la cuarta persona: {e}")
        
        # Haz clic en el botón final
        try:
            WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='detailed']/form/div[2]/button"))
            )
            boton_final = driver.find_element(By.XPATH, "//*[@id='detailed']/form/div[2]/button")
            driver.execute_script("arguments[0].scrollIntoView();", boton_final)
            time.sleep(0.2)
            boton_final.click()
            time.sleep(15)
        except Exception as e:
            print(f"No se pudo hacer clic en el botón final para fila {index + 1}: {e}")

    except Exception as e:
        print(f"Error procesando fila {index + 1}: {e}")
        continue

# Cierra el navegador al final de todos los envíos
driver.quit()
