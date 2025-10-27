"""
Script para automatizar la facturación y devolución de una venta realizada sin cliente. 
"""
import logging
from venta_fraccion_sincliente import ventas_fracciones_sincliente
from devolucion_fraccion_sincliente import fraccion_venta_sincliente

def fracciones_devolucion_sincliente(driver):
    """
    Realiza una venta sin cliente y luego la devuelve automáticamente, 
    sin importar si se capturó la factura o no.
    """
    logging.info("Iniciando venta sin cliente...")
    ventas_fracciones_sincliente(driver)
        
    logging.info("Ejecutando devolución de la venta sin cliente...")
    fraccion_venta_sincliente(driver)