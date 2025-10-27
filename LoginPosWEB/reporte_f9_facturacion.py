"""
Script para automatizar la facturación con tecla F9, y asimismo 
poder realizar el reporte de F9 por medio de Facturas y por
vendedor. 
"""
import logging
from f9_facturacion import tecla_f9
from reporte_f9_facturas import reporte_f9_factura
from reporte_f9_vendedor import reportes_f9_vendedor

def tecla_f9_reportes(driver):
    """
    Realiza la facturación con tecla F9, y asimismo 
    poder realizar el reporte de F9 por medio de Facturas y por
    vendedor. 
    """
    logging.info("Iniciando facturación con tecla F9...")
    tecla_f9(driver)
    
    logging.info("Ejecutando reporte F9 por medio de Facturas...")
    reporte_f9_factura(driver)

    logging.info("Ejecutando reporte F9 por medio de vendedor...")
    reportes_f9_vendedor(driver)