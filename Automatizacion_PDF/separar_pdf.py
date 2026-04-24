import os
from PyPDF2 import PdfReader, PdfWriter

def dividir_pdf_por_paginas(ruta_pdf, carpeta_salida="paginas_separadas"):
    """
    Divide un PDF en archivos individuales (una página por archivo)
    
    Args:
        ruta_pdf: Ruta del archivo PDF original
        carpeta_salida: Carpeta donde guardar las páginas separadas
    """
    
    # Crear carpeta de salida si no existe
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)
        print(f"📁 Creada carpeta: {carpeta_salida}")
    
    # Leer el PDF original
    print(f"📄 Leyendo PDF: {ruta_pdf}")
    lector = PdfReader(ruta_pdf)
    total_paginas = len(lector.pages)
    print(f"✅ El PDF tiene {total_paginas} páginas\n")
    
    # Dividir página por página
    for num_pagina in range(total_paginas):
        # Crear escritor para esta página
        escritor = PdfWriter()
        escritor.add_page(lector.pages[num_pagina])
        
        # Nombre del archivo (con ceros a la izquierda para ordenar)
        nombre_archivo = f"pagina_{num_pagina + 1:04d}.pdf"
        ruta_completa = os.path.join(carpeta_salida, nombre_archivo)
        
        # Guardar la página individual
        with open(ruta_completa, "wb") as archivo_salida:
            escritor.write(archivo_salida)
        
        print(f"✅ Guardada página {num_pagina + 1} de {total_paginas} -> {nombre_archivo}")
    
    print(f"\n🎉 ¡Completado! {total_paginas} archivos guardados en '{carpeta_salida}'")

if __name__ == "__main__":
    # Cambia esta ruta por la ubicación de tu PDF
    ruta_pdf = "enel.pdf"  # Si está en la misma carpeta
    # ruta_pdf = "C:/Users/tu_usuario/Descargas/enel.pdf"  # Ruta completa
    
    dividir_pdf_por_paginas(ruta_pdf)