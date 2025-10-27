"""
Script para automatizar todos los archivos de ingreso y salida
de mercancia a bodega. 
"""
import logging
from bodega_ingreso_mercancia1 import ingreso_mercancia1
from bodega_salida_mercancia1 import salida_mercancia1
from bodega_ingreso_mercancia2 import ingreso_mercancia2
from bodega_salida_mercancia2 import salida_mercancia2
from bodega_ingreso_mercancia3 import ingreso_mercancia3
from bodega_salida_mercancia3 import salida_mercancia3
from bodega_ingreso_mercancia4 import ingreso_mercancia4
from bodega_salida_mercancia4 import salida_mercancia4
from bodega_ingreso_mercancia5 import ingreso_mercancia5
from bodega_salida_mercancia5 import salida_mercancia5
from bodega_ingreso_mercancia6 import ingreso_mercancia6
from bodega_salida_mercancia6 import salida_mercancia6
from bodega_ingreso_mercancia7 import ingreso_mercancia7
from bodega_salida_mercancia7 import salida_mercancia7
from bodega_ingreso_mercancia8 import ingreso_mercancia8
from bodega_salida_mercancia8 import salida_mercancia8

def mercancia_final(driver):
    """
    Realiza el procedimiento de Bodega No Disponible Venta, 
    de todos los archivos 
    """
    logging.info("Iniciando Ingreso de mercancia a Bodega 1...")
    ingreso_mercancia1(driver)
    
    logging.info("Iniciando Salida de mercancia a Bodega 1...")
    salida_mercancia1(driver)

    logging.info("Iniciando Ingreso de mercancia a Bodega 2...")
    ingreso_mercancia2(driver)
    
    logging.info("Iniciando Salida de mercancia a Bodega 2...")
    salida_mercancia2(driver)

    logging.info("Iniciando Ingreso de mercancia a Bodega 3...")
    ingreso_mercancia3(driver)
    
    logging.info("Iniciando Salida de mercancia a Bodega 3...")
    salida_mercancia3(driver)

    logging.info("Iniciando Ingreso de mercancia a Bodega 4...")
    ingreso_mercancia4(driver)
    
    logging.info("Iniciando Salida de mercancia a Bodega 4...")
    salida_mercancia4(driver)

    logging.info("Iniciando Ingreso de mercancia a Bodega 5...")
    ingreso_mercancia5(driver)

    logging.info("Iniciando Salida de mercancia a Bodega 5...")
    salida_mercancia5(driver)
    
    logging.info("Iniciando Ingreso de mercancia a Bodega 6...")
    ingreso_mercancia6(driver)
    
    logging.info("Iniciando Salida de mercancia a Bodega 6...")
    salida_mercancia6(driver)

    logging.info("Iniciando Ingreso de mercancia a Bodega 7...")
    ingreso_mercancia7(driver)
    
    logging.info("Iniciando Salida de mercancia a Bodega 7...")
    salida_mercancia7(driver)

    logging.info("Iniciando Ingreso de mercancia a Bodega 8...")
    ingreso_mercancia8(driver)
    
    logging.info("Iniciando Salida de mercancia a Bodega 8...")
    salida_mercancia8(driver)