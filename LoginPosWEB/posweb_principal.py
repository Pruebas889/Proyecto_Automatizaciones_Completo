"""
Script principal para automatizar procesos en POSWeb.
Incluye inicialización robusta del driver y manejo avanzado de excepciones.
"""

# 📌 Librerías estándar de Python
import logging
import time
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import threading
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchWindowException,
    WebDriverException,
)
import os

# 📌 Módulos internos del proyecto (first-party)
from loginposweb import login_posweb
from logoutposweb import logout_posweb
from login_soporte import login_usuario_soporte
from logout_soporte import logout_usuario_soporte
from asignacion_caja import asignar_caja
from generar_turnos import turnos
from cliente_generico import generico
from Rappi_Payless import rappi_payless
from Globo_descuentos import descuentos
# from Addi_congelar import Addi_congelacion
# from orden_compra_actualizacion import orden_y_actualizacion
from ventas_devolucion_cliente import venta_y_devolucion_cliente
from venta_devolucion_sincliente import venta_y_devolucion_sin_cliente
from fracciones_devolucion_cliente import fracciones_devolucion_cliente
from fracciones_devolucion_sincliente import fracciones_devolucion_sincliente
from facturacion_mixta_debito import facturacion_mixto_debito
from facturacion_mixta_exito import facturacion_mixto_exito
from compra_tarjeta_sodexo import venta_tarjeta_sodexo
from compra_drogueria import comprar_a_drogueria
from congelar_y_descongelar import congelar_descongelar_factura
from visualizar_copia_factura import copia_factura
from reporte_f9_facturacion import tecla_f9_reportes
from ajuste_inventario_final import inventario_final
from inventario_ajuste_final import inventario_final_ajuste
from actualizar_generar_orden import actualizacion_y_generacion_orden
from gastos import control_gastos
from ventas_vendedor_pdv import reportes_ventas_vendedor_pdv
from generacion_pdf import guardar_captura_modal_en_pdf
from bodega_final import mercancia_final
from parche import parche_modal

# Nombre del archivo para guardar la versión
VERSION_FILE = "version_posweb.txt"

# 📌 Función para inicializar el driver
def initialize_driver():
    """
    Inicializa el WebDriver de Firefox con configuraciones personalizadas.
    
    Args:
        headless (bool): Si True, ejecuta el navegador en modo headless.
        timeout (int): Tiempo de espera en segundos para operaciones del driver.
    
    Returns:
        webdriver: Instancia del WebDriver configurada.
    """
    try:
        logging.info("Inicializando WebDriver de Firefox...")
        options = webdriver.FirefoxOptions()
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--profile-directory=Profile 1")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-save-password-bubble")
        # options.add_argument("-headless")  # Modo sin interfaz gráfica
        
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)

        logging.info("WebDriver inicializado correctamente.")
        return driver
    except WebDriverException as e:
        logging.error("Error al inicializar el WebDriver: %s", e)
        raise
    except Exception as e:
        logging.critical("Error inesperado al inicializar el WebDriver: %s", e)
        raise

# 📌 Función para cargar la versión guardada
def load_version():
    """
    Carga el número de versión desde un archivo de texto.
    """
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    return "Desconocida"

# 📌 Función para guardar la versión
def save_version(version):
    """
    Guarda el número de versión en un archivo de texto.
    """
    with open(VERSION_FILE, "w") as f:
        f.write(version)
    logging.info(f"Versión {version} guardada para futuras ejecuciones.")

# 📌 Función principal para ejecutar la automatización
# Stop event for cooperative cancellation
stop_event = threading.Event()


def request_stop():
    """Signal the automation to stop as soon as possible."""
    stop_event.set()


def clear_stop():
    """Clear any previous stop request."""
    stop_event.clear()


def run_automation(version=None, interactive=True, selected_steps=None):
    """Ejecuta la automatización completa de POSWeb con manejo de excepciones.

    Args:
        interactive (bool): Si False, evita cualquier prompt interactivo (input()) y
                            usa la versión guardada tal cual. Por defecto True.
    """
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO, # Cambia a DEBUG para más detalles
        format='%(asctime)s - %(levelname)s - %(message)s', # Formato del log
        handlers=[
            logging.StreamHandler(), # Muestra los logs en la consola
            logging.FileHandler("parche_posweb.log", encoding='utf-8')  # se agrega encoding
        ]
    )
    # Garantizar que las rutas relativas se creen dentro de la carpeta LoginPosWEB
    base_dir = os.path.abspath(os.path.dirname(__file__))
    try:
        os.chdir(base_dir)
        logging.info("Directorio de trabajo cambiado a: %s", base_dir)
    except Exception as e:
        logging.warning("No se pudo cambiar el directorio de trabajo: %s", e)
    
    # 1. Cargar la versión guardada
    current_version = load_version()
    print(f"Versión actual del parche: {current_version}")

    # 2. Determinar versión a usar
    if version:
        # Si el llamador pasó una versión explícita, usarla y guardarla
        save_version(version)
        logging.info("Versión especificada por parámetro: %s", version)
    else:
        # Si estamos en modo interactivo, ofrecer actualizar
        version = current_version
        if interactive:
            while True:
                respuesta = input("¿Quieres actualizar la versión del POSWeb? (y/n): ").lower()
                if respuesta == 'y':
                    version_input = input("Por favor, ingresa la nueva versión del parche: ")
                    save_version(version_input) # Se guarda la nueva versión
                    version = version_input
                    break
                elif respuesta != 'y':
                    logging.info(f"El usuario no quiere actualizar. Se usará la versión actual: {version}")
                    break
                else:
                    print("Respuesta no válida. Por favor, responde 'y' o 'n'.")
        else:
            logging.info("Ejecución no interactiva: usando versión guardada %s", version)

    # Inicializar driver
    driver = None
    try:
        driver = initialize_driver()

        driver.maximize_window()
        
        # 🌐 URL de POSWeb
        driver.get("http://192.168.100.63/")
        time.sleep(3)
        
        logging.info("Accediendo a %s", "http://192.168.100.63")

        # 📌 Llamar a la nueva función
        logging.info("Ejecutando parche_modal y tomando captura de pantalla...")
        
        # Creamos un hilo para la captura para que no se bloquee la ventana del modal
        captura_modal = threading.Thread(target=lambda: (time.sleep(1), guardar_captura_modal_en_pdf("reporte_modal_parche", "Captura de pantalla del modal del parche antes de iniciar la automatización.")))
        captura_modal.start()

        parche_modal(mensaje=f"Iniciando automatización de POSWeb del Parche {version}", duracion=4)
        captura_modal.join() # Esperar a que el hilo de la captura termine
        time.sleep(3)
        
        # The sequence of available processes is defined via helper so it can be queried/filtered by the UI
        def get_all_processes():
            return [
                ("Login usuario soporte", login_usuario_soporte),
                ("Cierre de sesión usuario soporte", logout_usuario_soporte),
                ("Login en POSWeb", login_posweb),
                ("Asignación de caja", asignar_caja),
                ("Ventas y devolución sin cliente", venta_y_devolucion_sin_cliente),
                ("Ventas y devolución con cliente", venta_y_devolucion_cliente),
                ("Ventas y devolución fracciones con cliente", fracciones_devolucion_cliente),
                ("Ventas y devolución fracciones sin cliente", fracciones_devolucion_sincliente),
                ("Facturación mixta con tarjeta Éxito", facturacion_mixto_exito),
                ("Facturación mixta con tarjeta débito", facturacion_mixto_debito),
                ("Facturación con tarjeta Sodexo", venta_tarjeta_sodexo),
                ("Generación de turnos", turnos),
                # ("Addi Descongelacion", Addi_congelacion),
                ("Cliente Generico", generico),
                ("Rappi Payless", rappi_payless),
                ("Descuentos Globo", descuentos),
                # ("Orden de compra y actualización",orden_y_actualizacion),
                ("Visualización copia de factura", copia_factura),
                ("Reportes con tecla F9", tecla_f9_reportes),
                ("Compra a droguería", comprar_a_drogueria),
                ("Ajuste de inventario A+", inventario_final),
                ("Ajuste de inventario A-", inventario_final_ajuste),
                ("Gestión de gastos", control_gastos),
                ("Reporte de ventas por PDV y vendedor", reportes_ventas_vendedor_pdv),
                ("Congelar y descongelar factura", congelar_descongelar_factura),
                ("Ingreso y salida de mercancía", mercancia_final),
                ("Cierre de sesión", logout_posweb),
            ]

        def get_available_process_names():
            """
            Retrieves a list of available process names.

            Returns:
                list: A list containing the names of all available processes.
            """
            return [name for name, _ in get_all_processes()]

        # Allow caller to pass a filtered list of step names (selected_steps). If None, run all.
        # If the caller passed selected_steps via kwargs it will be handled by the caller scope.
        # Build processes list now and possibly filter it later from the outer scope.
        processes = get_all_processes()

        # If caller provided selected_steps (list of names), filter processes accordingly
        if selected_steps and isinstance(selected_steps, (list, tuple, set)):
            selected_set = set(selected_steps)
            processes_to_run = [(n, f) for (n, f) in processes if n in selected_set]
        else:
            processes_to_run = processes

        for process_name, process_func in processes_to_run:
            # check for stop request before each major step
            if stop_event.is_set():
                logging.info("Stop requested before %s. Aborting sequence.", process_name)
                break

            logging.info("Ejecutando: %s", process_name)
            try:
                process_func(driver)
                time.sleep(0.5) # Pausa para estabilidad
            except (TimeoutException) as e:
                logging.error("Timeout en %s: %s", process_name, e)
                logging.info("Intentando continuar con el siguiente proceso...")
                continue
            except NoSuchElementException as e:
                logging.error("Elemento no encontrado en %s: %s", process_name, e)
                continue
            except NoSuchWindowException as e:
                logging.error("Ventana no disponible en %s: %s", process_name, e)
                break
            except Exception as e:
                logging.error("Error inesperado en %s: %s", process_name, e)
                continue
        
    except Exception as e:
        logging.critical("Error crítico en la automatización: %s", e)
        raise
    finally:
        if driver:
            try:
                logging.info("Cerrando el WebDriver...")
                driver.quit()
                logging.info("WebDriver cerrado correctamente.")
            except Exception as e:
                logging.error("Error al cerrar el WebDriver: %s", e)
        # clear stop event after finishing/aborting so future runs start fresh
        stop_event.clear()
        logging.info("Automatización finalizada. Logs guardados en: %s", "parche_posweb.log")

# 📌 Punto de entrada
if __name__ == "__main__":
    try:
        run_automation()
    except KeyboardInterrupt:
        logging.warning("Automatización interrumpida por el usuario.")
    except Exception as e:
        logging.critical("Error en la ejecución del programa: %s", e)

# Public helper so external code (the Flask server) can query available process names
def available_processes():
    """Return the list of available process names in order."""
    try:
        # create a temporary run_automation context to access the helper defined inside
        # Use the helper functions we added earlier by invoking a lightweight wrapper
        return [
            "Login usuario soporte",
            "Cierre de sesión usuario soporte",
            "Login en POSWeb",
            "Asignación de caja",
            "Ventas y devolución sin cliente",
            "Ventas y devolución con cliente",
            "Ventas y devolución fracciones con cliente",
            "Ventas y devolución fracciones sin cliente",
            "Facturación mixta con tarjeta Éxito",
            "Facturación mixta con tarjeta débito",
            "Facturación con tarjeta Sodexo",
            "Generación de turnos",
            # "Addi Descongelacion",
            "Cliente Generico",
            "Rappi Payless",
            "Descuentos Globo",
            # "Orden de compra y actualización",
            "Visualización copia de factura",
            "Reportes con tecla F9",
            "Compra a droguería",
            "Ajuste de inventario A+",
            "Ajuste de inventario A-",
            "Gestión de gastos",
            "Reporte de ventas por PDV y vendedor",
            "Congelar y descongelar factura",
            "Ingreso y salida de mercancía",
            "Cierre de sesión",
        ]
    except Exception:
        return []