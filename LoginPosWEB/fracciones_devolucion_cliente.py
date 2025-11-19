"""
Script para automatizar la facturación y devolución de una venta realizada sin cliente. 
"""
import logging
from venta_fraccion_cliente import fraccion_venta_cliente
from devolucion_fraccion_cliente import fraccion_devolucion_cliente

def fracciones_devolucion_cliente(driver):
    """
    Realiza una venta sin cliente y luego la devuelve automáticamente, 
    sin importar si se capturó la factura o no.
    """
    logging.info("Iniciando venta con cliente...")
    fraccion_venta_cliente(driver)
        
    logging.info("Ejecutando devolución de la venta con cliente...")
    fraccion_devolucion_cliente(driver)