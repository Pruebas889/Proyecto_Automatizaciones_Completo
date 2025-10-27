"""
Script para automatizar el ajuste de inventario de tipo de transacción A-
con todos los distintos causales, fracciones y unidades. 
"""
import logging
from inventario_ajuste1 import inventario_ajuste1
from inventario_ajuste2 import inventario_ajuste2
from inventario_ajuste3 import inventario_ajuste3
from inventario_ajuste4 import inventario_ajuste4

def inventario_final_ajuste(driver):
    """
    Realiza el ajuste de inventario de todos los causales
    incluyendo unidades y fracciones, utilizando los diferentes causales.
    """

    logging.info("Iniciando ajuste de inventario1...")
    inventario_ajuste1(driver)

    logging.info("Iniciando ajuste de inventario2...")
    inventario_ajuste2(driver)

    logging.info("Iniciando ajuste de inventario3...")
    inventario_ajuste3(driver)
    
    logging.info("Iniciando ajuste de inventario4...")
    inventario_ajuste4(driver)