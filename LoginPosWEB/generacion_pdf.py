"""
Genera una carpeta padre, donde guarde todos los pdfs de 
las automatizaciones.
"""
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from fpdf import FPDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Image as ReportLabImage, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
import pyautogui

# Carpeta principal del parche (se crea una vez por ejecución)
FECHA_HORA_PARCHE = datetime.now().strftime("Parche_%d-%m-%Y_%H-%M-%S")
CARPETA_PRINCIPAL_PARCHE = os.path.join(os.getcwd(), FECHA_HORA_PARCHE)
os.makedirs(CARPETA_PRINCIPAL_PARCHE, exist_ok=True)

def escribir_log(nombre_automatizacion, mensaje):
    """
    Escribe un mensaje en el archivo log_automatizacion.txt dentro de la subcarpeta de la automatización.
    """
    carpeta_automatizacion = os.path.join(CARPETA_PRINCIPAL_PARCHE, nombre_automatizacion)
    os.makedirs(carpeta_automatizacion, exist_ok=True)
    log_path = os.path.join(carpeta_automatizacion, "log_automatizacion.txt")

    fecha_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{fecha_hora} - {mensaje}\n")

def compress_image(image_path, max_size=(1200, 900), quality=95):
    """Compress an image to reduce file size while preserving quality."""
    if not os.path.exists(image_path):
        print(f"⚠️ Imagen no encontrada para compresión: {image_path}")
        escribir_log("generacion_pdf", f"⚠️ Imagen no encontrada para compresión: {image_path}")
        return image_path
    try:
        with Image.open(image_path) as img:
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            compressed_path = image_path.replace(".png", "_compressed.png")
            img.save(compressed_path, "PNG", quality=quality, optimize=True)
            return compressed_path
    except Exception as e:
        print(f"⚠️ Error al comprimir imagen {image_path}: {e}")
        escribir_log("generacion_pdf", f"⚠️ Error al comprimir imagen {image_path}: {e}")
        return image_path

def generar_pdf_consolidado(nombre_automatizacion, capturas, textos):
    """
    Genera un único PDF consolidado con múltiples capturas y textos, optimizado para velocidad,
    con un diseño similar al original (una imagen y texto por página).
    Usa reportlab si está disponible; de lo contrario, usa FPDF como fallback.
    """
    start_time = time.time()
    try:
        carpeta_automatizacion = os.path.join(CARPETA_PRINCIPAL_PARCHE, nombre_automatizacion)
        os.makedirs(carpeta_automatizacion, exist_ok=True)
        pdf_path = os.path.join(carpeta_automatizacion, "reporte_consolidado.pdf")

        if not capturas or not textos:
            escribir_log(nombre_automatizacion, "❌ Error: No hay datos para agregar al PDF.")
            print("❌ Error: No hay datos para agregar al PDF.")
            return

        # Compress images in parallel
        with ThreadPoolExecutor() as executor:
            compressed_capturas = list(executor.map(compress_image, capturas))

        if REPORTLAB_AVAILABLE:
            # Use reportlab for faster PDF generation
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)  # type: ignore
            styles = getSampleStyleSheet()  # type: ignore
            story = []

            # Configurar estilo similar a Arial 12
            style_normal = styles["Normal"]
            style_normal.fontName = "Helvetica"  # Más cercano a Arial en reportlab
            style_normal.fontSize = 12

            for captura, texto in zip(compressed_capturas, textos):
                # Añadir fecha y hora
                fecha_hora_actual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                story.append(Paragraph(f"Fecha y hora: {fecha_hora_actual}", style_normal))  # type: ignore
                story.append(Spacer(1, 5 * mm))  # type: ignore

                # Añadir texto
                story.append(Paragraph(texto, style_normal))  # type: ignore
                story.append(Spacer(1, 10 * mm))  # type: ignore

                # Añadir imagen
                if os.path.exists(captura):
                    with Image.open(captura) as img:
                        orig_width, orig_height = img.size
                        aspect_ratio = orig_width / orig_height
                        target_width = 170 * mm  # type: ignore # Aproximadamente 180mm ajustado por márgenes
                        target_height = target_width / aspect_ratio if aspect_ratio > 1 else target_width * aspect_ratio
                        img_obj = ReportLabImage(captura, width=target_width, height=target_height)  # type: ignore
                        img_obj.hAlign = "CENTER"
                        story.append(img_obj)
                        escribir_log(nombre_automatizacion, f"✅ Imagen agregada al PDF: {captura}")
                else:
                    story.append(Paragraph("⚠️ Imagen no encontrada", style_normal))  # type: ignore
                    escribir_log(nombre_automatizacion, f"⚠️ Imagen no encontrada: {captura}")

                # Forzar nueva página después de cada imagen
                story.append(PageBreak())  # type: ignore

            # Eliminar el último PageBreak para evitar página vacía
            if story and isinstance(story[-1], PageBreak): #type: ignore
                story.pop()

            doc.build(story)  # type: ignore
        else:
            # Fallback to FPDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            for captura, texto in zip(compressed_capturas, textos):
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                fecha_hora_actual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                pdf.cell(0, 10, text=f"Fecha y hora: {fecha_hora_actual}", ln=True)
                pdf.multi_cell(0, 10, texto)
                if os.path.exists(captura):
                    pdf.image(captura, x=10, y=40, w=180)
                    escribir_log(nombre_automatizacion, f"✅ Imagen agregada al PDF: {captura}")
                else:
                    pdf.cell(0, 10, text="⚠️ Imagen no encontrada", ln=True)
                    escribir_log(nombre_automatizacion, f"⚠️ Imagen no encontrada: {captura}")
            pdf.output(pdf_path)

        if os.path.exists(pdf_path):
            escribir_log(nombre_automatizacion, f"✅ PDF guardado correctamente en {time.time() - start_time:.2f} segundos.")
            print(f"✅ PDF guardado correctamente en: {pdf_path}")
        else:
            escribir_log(nombre_automatizacion, f"❌ Error: El PDF no se creó.")
            print("❌ Error: El PDF no se creó.")

        # Clean up compressed images
        for captura in compressed_capturas:
            if "_compressed.png" in captura and os.path.exists(captura):
                os.remove(captura)
                # escribir_log(nombre_automatizacion, f"✅ Imagen comprimida eliminada: {captura}")

    except Exception as e:
        escribir_log(nombre_automatizacion, f"❌ Error al generar PDF: {str(e)}")
        print(f"❌ Error al generar PDF: {e}")
        raise

def guardar_captura_modal_en_pdf(nombre_archivo, mensaje_pdf):
    """
    Toma una captura de pantalla del modal y la guarda en un PDF independiente.
    """
    try:
        # Tomar la captura de pantalla
        captura_path = "captura_modal_parche.png"
        pyautogui.screenshot(captura_path)
        
        # Crear el PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, mensaje_pdf)
        
        # Añadir la imagen al PDF
        if os.path.exists(captura_path):
            pdf.image(captura_path, x=10, y=40, w=180)
            
        pdf_path = os.path.join(CARPETA_PRINCIPAL_PARCHE, f"{nombre_archivo}.pdf")
        pdf.output(pdf_path)
        
        # Eliminar la imagen temporal
        os.remove(captura_path)
        
        print(f"✅ PDF del modal guardado correctamente en: {pdf_path}")
        
    except Exception as e:
        print(f"❌ Error al guardar el PDF del modal: {e}")
