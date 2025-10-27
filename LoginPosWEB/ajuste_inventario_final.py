"""
Script para automatizar el ajuste de inventario de tipo de transacción A+
con todos los distintos causales, fracciones y unidades. 
"""
import logging
from ajuste_inventario1 import inventario1
from ajuste_inventario2 import inventario2
from ajuste_inventario3 import inventario3
# from ajuste_inventario4 import inventario4

def inventario_final(driver):
    """
    Realiza el ajuste de inventario de todos los causales
    incluyendo unidades y fracciones, utilizando los diferentes causales.
    """

    logging.info("Iniciando ajuste de inventario1...")
    inventario1(driver)

    logging.info("Iniciando ajuste de inventario2...")
    inventario2(driver)

    logging.info("Iniciando ajuste de inventario3...")
    inventario3(driver)
    
    # logging.info("Iniciando ajuste de inventario4...")
    # inventario4(driver)