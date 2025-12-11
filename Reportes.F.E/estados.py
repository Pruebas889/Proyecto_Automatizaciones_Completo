import mysql.connector
from flask import Flask, request, render_template
import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import random
import sys
import json
import traceback
import time as _time
import os

# Configuración de la base de datos
DB_CONFIG = {
    'host': '10.77.11.252',  # Ej: 'localhost' o '192.168.x.x'
    'user': 'jperdomo',
    'password': 'P3rd0m#L',
    'database': 'be_feco_v2',
    'port': 3306  # Ajusta si usas otro puerto
}

# Configuración de Google Sheets
SHEET_ID = '1m6FU7RFKpKhhbOp_bjwzSjLHJWiQwiONCJPqmLFMEhI'  # Del URL
# Use a raw string for Windows path to avoid unicode escape errors (e.g. \U)
CREDENTIALS_FILE = r"C:\Users\ymongui\Videos\Proyecto_Automatizaciones_Completo\Reportes.F.E\estados-476114-a49973226bb3.json"
SHEET_NAME_1 = 'Rechazados'  # Pestaña para la primera consulta
SHEET_NAME_2 = 'General'  # Pestaña para la segunda consulta
# Si APPEND_MODE = True, el script no limpiará los datos previos (salvo fila 1) y
# añadirá los registros nuevos debajo de los existentes. Si False, reemplaza todo (fila 1 preservada).
APPEND_MODE = True


def check_credentials_and_access():
    """Verifica que el archivo de credenciales exista, muestre el client_email, compruebe la hora
    y pruebe acceso de lectura a la hoja de cálculo.

    Lanza excepciones descriptivas si detecta problemas.
    """
    # 1) Archivo existe
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Archivo de credenciales no encontrado: {CREDENTIALS_FILE}")

    # 2) Leer JSON y mostrar client_email
    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            j = json.load(f)
        client_email = j.get('client_email')
        print(f"Service account email: {client_email}")
    except Exception as e:
        print("Error leyendo el JSON de credenciales:", e)
        traceback.print_exc()
        raise

    # 3) Comprobar hora del sistema
    now = int(_time.time())
    print(f"Hora actual (epoch): {now}")

    # 4) Intentar autenticar y abrir la hoja (lectura)
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        sh = client.open_by_key(SHEET_ID)
        print(f"Acceso a la hoja OK: {getattr(sh, 'title', 'UNKNOWN')}")
    except Exception as e:
        print("Google Sheets:", repr(e))
        traceback.print_exc()
        raise


# Consulta 1 (plantilla; se rellenará con el rango de fecha del día anterior)
QUERY_1_TEMPLATE = """
SELECT 
    fechaPedido, 
    areaVentas, 
    idComercial,
    mensajeEstatusCarvajal, 
    SUBSTRING_INDEX(detalleError, ',', 2) AS detalleError,
    COUNT(mensajeEstatusCarvajal) AS cantidad_rechazados
FROM 
    be_feco_v2.t_Factura 
WHERE 
    fechaHoraEmisionFactura BETWEEN '{start}' AND '{end}'
    AND mensajeEstatusCarvajal = 'RECHAZADO'
GROUP BY 
    mensajeEstatusCarvajal, 
    fechaPedido, 
    SUBSTRING_INDEX(detalleError, ',', 2), 
    areaVentas,
    idComercial;
"""

# Consulta 2 (plantilla simplificada — fechaPedido, mensajeEstatusCarvajal, COUNT AS cantidad)
QUERY_2_TEMPLATE = """
SELECT
    fechaPedido,
    mensajeEstatusCarvajal,
    COUNT(mensajeEstatusCarvajal) AS cantidad
FROM
    be_feco_v2.t_Factura
WHERE
    fechaHoraEmisionFactura BETWEEN '{start}' AND '{end}'
GROUP BY
    mensajeEstatusCarvajal,
    fechaPedido;
"""


# Función para ejecutar una consulta
def ejecutar_consulta(query):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)  # Resultados como diccionarios
        cursor.execute(query)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados
    except mysql.connector.Error as err:
        print(f"Error en la base de datos: {err}")
        return []

# Función para actualizar Google Sheets
def actualizar_google_sheets(resultados, sheet_name):
    def _retry(func, *args, max_attempts=5, initial_backoff=1.0, **kwargs):
        """Retry helper with exponential backoff and jitter for API calls."""
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except APIError as api_err:
                # Inspect status code/message if available
                status = getattr(api_err, 'response', None)
                attempt += 1
                if attempt >= max_attempts:
                    raise
                backoff = initial_backoff * (2 ** (attempt - 1))
                # Add jitter
                jitter = random.uniform(0, 1)
                sleep_time = backoff + jitter
                print(f"APIError on attempt {attempt}/{max_attempts}: {api_err} — retrying in {sleep_time:.1f}s")
                time.sleep(sleep_time)
            except Exception:
                # Non-API errors should bubble up
                raise

    try:
        # Autenticación con Google Sheets
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(creds)

        # Abrir la hoja y la pestaña
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)

        # Nota: el usuario colocará manualmente los títulos en la fila 1.
        # Aquí sólo escribimos los datos empezando en A2 y dejamos la fila 1 intacta.
        if resultados:
            headers = list(resultados[0].keys())
            # Preparar solo las filas de datos (sin headers)
            # Si existe la columna 'detalleError', la limpiamos y la separamos en 2 columnas
            def clean_and_split_detalle(s):
                if s is None:
                    return ['', '']
                # Handle bytes directly
                if isinstance(s, (bytes, bytearray)):
                    text = s.decode('utf-8', errors='ignore')
                else:
                    text = str(s)
                    # Quitar prefijo b' o b" si existe en representaciones como "b'...'")
                    if text.startswith("b'") or text.startswith('b"'):
                        text = text[2:]

                # Quitar corchetes y comillas exteriores
                text = text.strip()
                text = text.strip("[]'\" ")

                # Intentar decodificar secuencias de escape como \xc3\xad -> 'í'
                try:
                    # Primero interpretar escapes como \xNN
                    unescaped = text.encode('utf-8').decode('unicode_escape')
                    # Después convertir los bytes resultantes interpretados en latin-1 a utf-8
                    unescaped = unescaped.encode('latin-1').decode('utf-8')
                    text = unescaped
                except Exception:
                    # Si falla, mantener el texto original
                    pass

                # Ahora split por la primera coma
                parts = [p.strip() for p in text.split(',', 1)]
                if len(parts) == 1:
                    parts.append('')
                return parts[0], parts[1]

            data_values = []
            for row in resultados:
                row_vals = []
                for key in headers:
                    if key == 'detalleError':
                        p1, p2 = clean_and_split_detalle(row.get(key, ''))
                        row_vals.append(p1)
                        row_vals.append(p2)
                    elif key == 'mensajeEstatusCarvajal':
                        val = row.get(key, '')
                        # If it's bytes, decode; if it's a str like "b'RECHAZADO'", strip the b' prefix
                        if isinstance(val, (bytes, bytearray)):
                            text = val.decode('utf-8', errors='ignore')
                        else:
                            text = str(val)
                            if text.startswith("b'") or text.startswith('b"'):
                                text = text[2:]
                        # Strip surrounding quotes/spaces
                        text = text.strip("'\" ")
                        row_vals.append(text)
                    else:
                        row_vals.append(str(row.get(key, '')))
                data_values.append(row_vals)

            # Helper: convertir número de columna a letra (1 -> A, 27 -> AA)
            def col_letter(n):
                letters = ''
                while n > 0:
                    n, rem = divmod(n - 1, 26)
                    letters = chr(65 + rem) + letters
                return letters

            # Si dividimos 'detalleError' en 2, ajustar el número de columnas finales
            final_col_count = len(headers)
            if 'detalleError' in headers:
                final_col_count = final_col_count + 1  # detalleError -> 2 columnas en lugar de 1

            if APPEND_MODE:
                # Obtener la primera fila vacía (considerando que row 1 son títulos)
                try:
                    existing = _retry(sheet.get_all_values)
                    start_row = len(existing) + 1 if existing is not None else 2
                except Exception:
                    start_row = 2

                start_cell = f'A{start_row}'
                # Asegurarse de que la hoja tenga suficientes filas para recibir los datos
                needed_end_row = start_row + len(data_values) - 1
                try:
                    if needed_end_row > sheet.row_count:
                        add = needed_end_row - sheet.row_count
                        print(f"Agregando {add} filas a la hoja para acomodar los datos...")
                        _retry(sheet.add_rows, add)
                except Exception:
                    # Si no se puede agregar filas, la actualización fallará y el retry lo manejará
                    pass

                # Asegurarse de que la hoja tenga suficientes columnas (final_col_count calculado arriba)
                try:
                    if final_col_count > sheet.col_count:
                        addc = final_col_count - sheet.col_count
                        print(f"Agregando {addc} columnas a la hoja para acomodar los datos...")
                        # add_cols may not be available in some environments; try it and ignore errors
                        _retry(getattr(sheet, 'add_cols'), addc)
                except Exception:
                    pass

                # Use named args (values=..., range_name=...) to avoid deprecation warning
                _retry(sheet.update, values=data_values, range_name=start_cell)
                print(f"Anexados {len(resultados)} registros en la pestaña {sheet_name} empezando en {start_cell} (fila 1 preservada).")
            else:
                # Calcular columna final para limpieza usando todas las columnas actuales de la hoja
                clear_last_col = col_letter(sheet.col_count if sheet.col_count else final_col_count)

                # Limpiar datos previos desde A2 hasta la última fila y última columna existente de la hoja,
                # para evitar restos y preservar la fila 1 (títulos)
                try:
                    _retry(sheet.batch_clear, [f'A2:{clear_last_col}{sheet.row_count}'])
                except Exception:
                    # Si batch_clear no está disponible o falla, ignoramos y seguiremos con la actualización
                    pass

                # Escribir solo los datos (sin fila de headers) empezando en A2
                _retry(sheet.update, values=data_values, range_name='A2')
                print(f"Actualizados {len(resultados)} registros en la pestaña {sheet_name} (datos solo, fila 1 preservada).")
        else:
            print(f"No hay datos para la pestaña {sheet_name}.")

    except APIError as e:
        print(f"Error de API al actualizar Google Sheets: {e}")
    except Exception as e:
        print(f"Error al actualizar Google Sheets: {e}")


def run_job_for_date(fecha_str):
    """Ejecuta las consultas y actualiza Google Sheets para la fecha dada (YYYY-MM-DD)."""
    start_str = fecha_str + ' 00:00:00'
    end_str = fecha_str + ' 23:59:59'
    print(f"Usando rango de fechas: {start_str} a {end_str}")

    # Ejecutar y guardar Consulta 1 (plantilla formateada)
    q1 = QUERY_1_TEMPLATE.format(start=start_str, end=end_str)
    resultados_1 = ejecutar_consulta(q1)
    actualizar_google_sheets(resultados_1, SHEET_NAME_1)

    # Ejecutar y guardar Consulta 2 (plantilla formateada)
    q2 = QUERY_2_TEMPLATE.format(start=start_str, end=end_str)
    resultados_2 = ejecutar_consulta(q2)
    actualizar_google_sheets(resultados_2, SHEET_NAME_2)



if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Si se pasa una fecha como argumento, usarla
        fecha_str = sys.argv[1]
        print(f"Iniciando automatización para la fecha: {fecha_str}")
        try:
            check_credentials_and_access()
        except Exception as e:
            print("Fallo la validación de credenciales. Revisa el mensaje anterior para más detalles.")
            sys.exit(2)
        run_job_for_date(fecha_str)
        print(f"Automatización completada para la fecha: {fecha_str}")
        # Mensaje final explícito que la UI/servidor buscará para marcar 'Terminado'
        print("Terminado")
    else:
        print("Error: No se proporcionó una fecha. Debe especificar una fecha en formato YYYY-MM-DD")
        sys.exit(1)