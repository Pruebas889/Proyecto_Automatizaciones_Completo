"""Helper para calcular y guardar el checkpoint basado en la hoja 'Reporte Comparendos'.

Uso: python set_checkpoint.py

Este script usa la función `inicializar_sheets` y `guardar_checkpoint` definidas en `mensajeros.py`.
"""
from mensajeros import inicializar_sheets, guardar_checkpoint
import logging
import argparse


def main(argv=None):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Set checkpoint based on Reporte Comparendos or given last cédula')
    parser.add_argument('cedulas', nargs='*', help='Última cédula(s) procesada(s). Si se pasa más de una, se toma la última.')
    args = parser.parse_args(argv)

    client, credentials, sheet, sheet2, sheet3, SPREADSHEET_ID, SHEET_NAME2 = inicializar_sheets()

    # Lista de cédulas en la hoja de entrada
    cedulas = sheet.col_values(1)[1:]

    # Lista de cédulas (posibles repetidas) en el reporte de salida
    reporte = sheet2.col_values(1)[1:]

    # Si el usuario proporcionó una cédula por CLI, úsala
    if args.cedulas:
        last_processed = args.cedulas[-1].strip()
        logging.info(f"Se usará la cédula pasada por argumento: {last_processed}")
    else:
        # Encontrar la última cédula procesada no vacía en el reporte
        last_processed = None
        for v in reversed(reporte):
            if v and v.strip():
                last_processed = v.strip()
                break

    if not last_processed:
        logging.info("No se encontró ninguna cédula procesada en 'Reporte Comparendos'. Se recomienda iniciar desde el inicio (índice 1).")
        print("No se encontró cédula en 'Reporte Comparendos'. Si quieres empezar desde el inicio, crea/edita 'checkpoint.txt' con el valor 1.")
        return

    logging.info(f"Última cédula usada para checkpoint: {last_processed}")

    try:
        pos = cedulas.index(last_processed)
    except ValueError:
        logging.error("La cédula encontrada/no proporcionada no está en la hoja de cédulas de entrada. Revisa si el orden cambió o limpia el checkpoint manualmente.")
        print("ERROR: La cédula no coincide con la hoja de entrada. Revisa manualmente o pasa la cédula correcta como argumento.")
        return

    # convertimos a índice del script: enumerate(cedulas, start=1)
    ultimo_indice = pos + 1
    siguiente_indice = ultimo_indice + 1

    logging.info(f"La cédula corresponde al índice {ultimo_indice} en la lista de entrada. Guardando checkpoint con valor {siguiente_indice} para reanudar desde la siguiente cédula.")
    guardar_checkpoint(siguiente_indice)
    print(f"Checkpoint guardado con el valor {siguiente_indice} (reanudará desde ahí).")


if __name__ == '__main__':
    main()
