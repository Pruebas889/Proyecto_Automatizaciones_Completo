import logging
import time
from ventas_sincliente import ventas_sincliente
from devolucion_sincliente import devolucion_factura_sincliente

def venta_y_devolucion_sin_cliente(driver):
    """
    Realiza una venta sin cliente y luego la devuelve automáticamente,
    sin importar si se capturó la factura o no.
    """
    logging.info("Iniciando venta sin cliente...")
    ventas_sincliente(driver)
    
    logging.info("Ejecutando devolución de la venta sin cliente...")
    devolucion_factura_sincliente(driver)