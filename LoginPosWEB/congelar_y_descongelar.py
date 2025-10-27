"""
Script para automatizar la congelación y descongelación de una factura
"""
import logging
from congelar_factura import congelacion_factura
from descongelar_factura import descongelacion_factura

def congelar_descongelar_factura(driver):
    """
    Realiza la congelación de una venta y luego la descongelación de 
    la factura.
    """
    logging.info("Iniciando congelación de factura...")
    congelacion_factura(driver)
    
    logging.info("Ejecutando descongelación de factura...")
    descongelacion_factura(driver)