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

# Force output under the LoginPosWEB/capturas directory (same folder as this module)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CAPTURAS_ROOT = os.path.join(BASE_DIR, 'capturas')
os.makedirs(CAPTURAS_ROOT, exist_ok=True)

# The "parche" folder will be created lazily when needed (e.g. when starting the automation)
FECHA_HORA_PARCHE = None
CARPETA_PRINCIPAL_PARCHE = None

def init_parche(name=None):
    """Create the Parche folder under BASE_DIR and return its path.

    If name is provided it will be used as folder name, otherwise a timestamp is generated.
    """
    global FECHA_HORA_PARCHE, CARPETA_PRINCIPAL_PARCHE
    if name:
        FECHA_HORA_PARCHE = name
    else:
        FECHA_HORA_PARCHE = datetime.now().strftime("Parche_%d-%m-%Y_%H-%M-%S")
    CARPETA_PRINCIPAL_PARCHE = os.path.join(BASE_DIR, FECHA_HORA_PARCHE)
    os.makedirs(CARPETA_PRINCIPAL_PARCHE, exist_ok=True)
    return CARPETA_PRINCIPAL_PARCHE

def ensure_parche():
    """Ensure a parche folder exists and return its path."""
    global CARPETA_PRINCIPAL_PARCHE
    if CARPETA_PRINCIPAL_PARCHE and os.path.exists(CARPETA_PRINCIPAL_PARCHE):
        return CARPETA_PRINCIPAL_PARCHE
    return init_parche()

def escribir_log(nombre_automatizacion, mensaje):
    """
    Escribe un mensaje en el archivo log_automatizacion.txt dentro de la subcarpeta de la automatización.
    """
    carpeta_parche = ensure_parche()
    carpeta_automatizacion = os.path.join(carpeta_parche, nombre_automatizacion)
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
        carpeta_parche = ensure_parche()
        carpeta_automatizacion = os.path.join(carpeta_parche, nombre_automatizacion)
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
                try:
                    os.remove(captura)
                except Exception:
                    pass

    except Exception as e:
        escribir_log(nombre_automatizacion, f"❌ Error al generar PDF: {str(e)}")
        print(f"❌ Error al generar PDF: {e}")
        raise

def guardar_captura_modal_en_pdf(nombre_archivo, mensaje_pdf):
    """
    Toma una captura de pantalla del modal y la guarda en un PDF independiente.
    """
    try:
        # Ensure parche folder exists and get its path
        carpeta_parche = ensure_parche()

        # Tomar la captura de pantalla (guardar temporalmente en CAPTURAS_ROOT)
        captura_path = os.path.join(CAPTURAS_ROOT, "captura_modal_parche.png")
        pyautogui.screenshot(captura_path)

        # Crear el PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, mensaje_pdf)

        # Añadir la imagen al PDF
        if os.path.exists(captura_path):
            try:
                pdf.image(captura_path, x=10, y=40, w=180)
            except Exception:
                # imagen podría no ajustarse; continuar
                pass

        pdf_path = os.path.join(carpeta_parche, f"{nombre_archivo}.pdf")
        pdf.output(pdf_path)

        # Eliminar la imagen temporal
        try:
            if os.path.exists(captura_path):
                os.remove(captura_path)
        except Exception:
            pass

        print(f"✅ PDF del modal guardado correctamente en: {pdf_path}")
    except Exception as e:
        print(f"❌ Error al guardar el PDF del modal: {e}")
