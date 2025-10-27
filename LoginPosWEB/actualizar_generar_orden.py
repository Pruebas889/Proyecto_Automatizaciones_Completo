"""
Script para automatizar la generación y actualización de orden de una compra. 
"""
import logging
from generar_orden_compra import orden_compra
from actualizar_orden_compra import actualizar_orden

def actualizacion_y_generacion_orden (driver):
    """
    Realiza la generación de una compra, 
    y la actualización de la compra que realizó
    """
    logging.info("Iniciando generación orden de compra...")
    orden_compra(driver)

    logging.info("Ejecutando actualización orden de compra...")
    actualizar_orden(driver)