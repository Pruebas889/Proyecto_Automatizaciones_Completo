"""
Script para automatizar los reportes de ventas 
por Vendedor y por PDV.
"""

import logging
from reporte_ventas_vendedor import reporte_vendedor
from reporte_ventas_pdv import reporte_pdv

def reportes_ventas_vendedor_pdv(driver):
    """
    Realiza el reporte de ventas por vendedor y por pdv, 
    además guarda logs.
    """
    logging.info("Iniciando reportes de ventas por pdv...")
    reporte_pdv(driver)
    
    logging.info("Iniciando reportes de ventas por vendedor...")
    reporte_vendedor(driver)
