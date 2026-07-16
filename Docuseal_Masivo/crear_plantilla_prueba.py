# -*- coding: utf-8 -*-
"""Crea una plantilla de prueba con UN solo rol y un campo de firma via API."""
import base64
import json
import sys
import urllib.request

from fpdf import FPDF

URL = 'http://localhost:3000'
TOKEN = sys.argv[1]

pdf = FPDF()
pdf.add_page()
pdf.set_font('Arial', size=14)
pdf.cell(0, 10, 'Formato de prueba - envio masivo', ln=1)
pdf.set_font('Arial', size=11)
pdf.multi_cell(0, 8, 'Documento de prueba: cada empleado recibe su copia y la firma.')
salida = pdf.output(dest='S')
pdf_bytes = salida.encode('latin-1') if isinstance(salida, str) else bytes(salida)
pdf_b64 = base64.b64encode(pdf_bytes).decode()

cuerpo = {
    'name': 'prueba-envio-masivo-un-rol',
    'documents': [{
        'name': 'formato.pdf',
        'file': pdf_b64,
        'fields': [{
            'name': 'Firma empleado',
            'type': 'signature',
            'role': 'Empleado',
            'areas': [{'x': 100, 'y': 200, 'w': 160, 'h': 60, 'page': 1}],
        }],
    }],
}
req = urllib.request.Request(
    f'{URL}/api/templates/pdf', method='POST',
    data=json.dumps(cuerpo).encode(),
    headers={'X-Auth-Token': TOKEN, 'Content-Type': 'application/json'},
)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(req, timeout=60) as r:
    data = json.loads(r.read().decode())
print(f"Plantilla creada: id={data['id']} nombre={data['name']} roles={[s['name'] for s in data['submitters']]}")
