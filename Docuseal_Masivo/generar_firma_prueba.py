# -*- coding: utf-8 -*-
"""Genera firma_prueba.png (trazo tipo firma) sin dependencias externas."""
import math
import struct
import zlib

W, H = 400, 120
# lienzo RGBA transparente
pix = [[(0, 0, 0, 0)] * W for _ in range(H)]

def punto(x, y):
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            px, py = int(x) + dx, int(y) + dy
            if 0 <= px < W and 0 <= py < H:
                pix[py][px] = (20, 30, 90, 255)  # azul tinta

# trazo: onda tipo rubrica
for i in range(2000):
    t = i / 2000 * 4 * math.pi
    x = 20 + (i / 2000) * 360
    y = 60 + 30 * math.sin(t) * math.exp(-i / 2500) + 10 * math.sin(3 * t)
    punto(x, y)
# rubrica final: circulo
for i in range(600):
    a = i / 600 * 2 * math.pi
    punto(330 + 25 * math.cos(a), 60 + 18 * math.sin(a))

filas = b''
for fila in pix:
    filas += b'\x00' + b''.join(struct.pack('4B', *p) for p in fila)

def chunk(tipo, datos):
    c = tipo + datos
    return struct.pack('>I', len(datos)) + c + struct.pack('>I', zlib.crc32(c))

png = (b'\x89PNG\r\n\x1a\n'
       + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 6, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(filas))
       + chunk(b'IEND', b''))

with open('firma_prueba.png', 'wb') as f:
    f.write(png)
print('firma_prueba.png generada (400x120)')
