# coding: utf-8
import PyPDF2
import re
import sys

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

def debug_pdf(pdf_path):
    """Extrae y muestra la zona ASEO de un PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            
            print(f"\n{'='*70}")
            print(f"📄 ANALIZANDO: {pdf_path}")
            print(f"📊 Total de páginas: {total_pages}")
            print(f"{'='*70}\n")
            
            # Procesar cada página
            for num_pagina, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                
                if not page_text:
                    continue
                
                # Limpiar espacios
                texto = page_text.replace('\xa0', ' ')
                
                # Buscar ASEO
                match_aseo = re.search(r'ASEO', texto, re.IGNORECASE)
                
                if match_aseo:
                    print(f"\n{'='*70}")
                    print(f"✅ PÁGINA {num_pagina} - ENCONTRÉ 'ASEO'")
                    print(f"{'='*70}\n")
                    
                    inicio = match_aseo.start()
                    bloque = texto[inicio:inicio + 1500]
                    
                    print("🔍 ZONA ASEO (1500 caracteres):")
                    print("-" * 70)
                    print(bloque)
                    print("-" * 70)
                    
                    # Buscar PRESTADOR en esa zona
                    if 'PRESTADOR' in bloque.upper():
                        print("\n✅ Contiene 'PRESTADOR'")
                        match_prest = re.search(r'PRESTADOR:\s*(.+)', bloque, re.IGNORECASE)
                        if match_prest:
                            print(f"📌 Texto después de PRESTADOR: '{match_prest.group(1)}'")
                    else:
                        print("\n❌ NO contiene 'PRESTADOR'")
                    
                    # Buscar NIT en esa zona
                    if 'NIT' in bloque.upper():
                        print("\n✅ Contiene 'NIT'")
                        match_nit = re.search(r'NIT:\s*(\d{10}-\d)', bloque)
                        if match_nit:
                            print(f"📌 NIT encontrado: {match_nit.group(1)}")
                    else:
                        print("\n❌ NO contiene 'NIT'")
                    
                else:
                    print(f"\n⏭️ Página {num_pagina} - Sin ASEO")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def extraer_valor_unitario_debug(pdf_path):
    """Busca el valor unitario REAL desde la línea de consumo"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)

            for num_pagina, page in enumerate(reader.pages, 1):
                texto = page.extract_text()

                if not texto:
                    continue

                texto = texto.replace('\xa0', ' ')

                print(f"\n🔎 Analizando página {num_pagina}...")

                for linea in texto.split('\n'):

                    if 'CONSUMO ACTIVA SENCILLA' in linea.upper():

                        print(f"\n📌 LÍNEA ENCONTRADA:")
                        print(linea)

                        # 🔥 EXTRAER TODOS LOS NÚMEROS (NO solo $)
                        numeros = re.findall(r'\d{1,3}(?:\.\d{3})*', linea)

                        print(f"🔢 Números encontrados: {numeros}")

                        # 🔥 VALIDAR ESTRUCTURA
                        if len(numeros) >= 6:
                            lectura_actual = numeros[0]
                            lectura_anterior = numeros[1]
                            diferencia = numeros[2]
                            factor = numeros[3]
                            energia_consumida = numeros[4]

                            print(f"\n📊 DATOS DETECTADOS:")
                            print(f"   Lectura actual: {lectura_actual}")
                            print(f"   Lectura anterior: {lectura_anterior}")
                            print(f"   Diferencia: {diferencia}")
                            print(f"   Factor: {factor}")
                            print(f"   🔥 Energía consumida REAL: {energia_consumida}")

                            # limpiar formato
                            energia_limpia = energia_consumida.replace('.', '')

                        # 🔥 VALOR UNITARIO (lo que ya tenías)
                        valores = re.findall(r'\$([\d\.,]+)', linea)

                        print(f"\n💰 Valores encontrados: {valores}")

                        if len(valores) >= 2:
                            valor_unitario = valores[0]
                            valor_limpio = valor_unitario.replace('.', '').replace(',', '.')

                            print(f"\n✅ VALOR UNITARIO REAL: {valor_limpio}")

                            return {
                                "Costo_Unitario": float(valor_limpio),
                                "Energia_Consumida": float(energia_limpia)
                            }

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # 📝 CAMBIAR ESTA RUTA A TU PDF
    pdf_file = r"C:\Users\cmarroquin\Music\PDF python\PDF_DIR\enelprueba cuenta contrato aseo.pdf"
    
    resultado = extraer_valor_unitario_debug(pdf_file)

    print("\n" + "="*70)
    print(f"🎯 RESULTADO FINAL: {resultado}")
    print("="*70)