"""
Script para automatizar la facturación y devolución de una venta realizada con cliente.
Se ejecuta el proceso de venta con cliente y, a continuación, la devolución usando el número de factura capturado.
"""
import logging
from cajero_ventas import cajero_ventas
from devolucion_ventas import devolucion_factura

def venta_y_devolucion_cliente(driver):
    """
    Realiza una venta con cliente y luego la devuelve automáticamente, 
    utilizando el número de factura capturado durante la venta.
    """
    logging.info("Iniciando venta con cliente...")
    cajero_ventas(driver)
        
    logging.info("Ejecutando devolución de la venta con cliente...")
    devolucion_factura(driver)
