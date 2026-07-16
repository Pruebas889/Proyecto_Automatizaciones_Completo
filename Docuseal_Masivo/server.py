# -*- coding: utf-8 -*-
"""
Arranque del panel Firmas Masivas (envio masivo DocuSeal) dentro del gateway.

El server.py raiz lo lanza igual que a los demas microservicios:
    subprocess.Popen(["python", "Docuseal_Masivo/server.py"], cwd=raiz)

El servidor real es panel/panel.py (libreria estandar pura, sin Flask ni MySQL,
con su propio login de DocuSeal). Este archivo solo lo arranca en el puerto
definido en panel/config.json (8450). Tambien puede ejecutarse solo:
    python Docuseal_Masivo/server.py
"""
import os
import runpy
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(BASE, 'panel', 'panel.py')

if __name__ == '__main__':
    if not os.path.exists(PANEL):
        print(f"Error: No se encontró {PANEL}")
        sys.exit(1)
    # panel.py resuelve config.json relativo a su propia carpeta, asi que da
    # igual desde donde lo lance el gateway
    sys.argv = [PANEL]
    runpy.run_path(PANEL, run_name='__main__')
