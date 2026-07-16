# -*- coding: utf-8 -*-
"""
Panel web de envio masivo DocuSeal - Copservir.

Cero dependencias: solo libreria estandar de Python (>=3.10).
Arranque:  python panel.py            (usa config.json junto al script)
           python panel.py --config otra_config.json

config.json:
  {
    "docuseal_url": "https://firmasdigitales.copservir.com",
    "puerto": 8450,
    "escuchar": "0.0.0.0"
  }

Login: cada persona entra con SU correo y clave de DocuSeal; el panel valida contra
DocuSeal, obtiene el token de API de esa cuenta y los envios salen a SU nombre.
La clave no se almacena; el token vive solo en la sesion en memoria.
Cada envio queda registrado en envios_log.csv.
"""
import argparse
import base64
import csv
import http.cookiejar
import io
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http import cookies

BASE = os.path.dirname(os.path.abspath(__file__))
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-']+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
COL_EMAIL = ('email', 'correo', 'correo electronico', 'correo electrónico', 'e-mail', 'mail')
COL_NOMBRE = ('nombre', 'name', 'nombres', 'empleado')

CONFIG = {}
SESIONES = {}          # cookie de sesion -> {'usuario': email, 'token': token DocuSeal del usuario}
TRABAJOS = {}          # id -> estado del envio
LOCK = threading.Lock()

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# ----------------------------- DocuSeal API -----------------------------

def docuseal(metodo, ruta, token, cuerpo=None):
    """Llama a la API de DocuSeal con el token del usuario en sesion."""
    req = urllib.request.Request(
        CONFIG['docuseal_url'].rstrip('/') + ruta,
        method=metodo,
        data=json.dumps(cuerpo).encode('utf-8') if cuerpo is not None else None,
        headers={'X-Auth-Token': token, 'Content-Type': 'application/json'},
    )
    with OPENER.open(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def login_docuseal(email, clave):
    """Valida las credenciales contra DocuSeal (web) y devuelve el token de API
    del propio usuario, para que sus envios salgan de SU cuenta. None si fallan."""
    base = CONFIG['docuseal_url'].rstrip('/')
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj),
                                     urllib.request.ProxyHandler({}))
    try:
        html = op.open(base + '/sign_in', timeout=30).read().decode('utf-8', 'replace')
        m = re.search(r'name="csrf-token" content="([^"]+)"', html)
        if not m:
            return None
        datos = urllib.parse.urlencode({'authenticity_token': m.group(1),
                                        'user[email]': email,
                                        'user[password]': clave}).encode()
        op.open(urllib.request.Request(base + '/sign_in', data=datos), timeout=30)

        # si la sesion quedo activa, /settings/api muestra el token; si no, el formulario de login
        html = op.open(base + '/settings/api', timeout=30).read().decode('utf-8', 'replace')
        if 'user[password]' in html:
            return None
        for cand in dict.fromkeys(re.findall(r'[A-Za-z0-9]{40,64}', html)):
            try:
                req = urllib.request.Request(base + '/api/templates?limit=1',
                                             headers={'X-Auth-Token': cand})
                OPENER.open(req, timeout=30)
                return cand
            except Exception:
                continue
    except Exception:
        return None
    return None


# ----------------------------- lectura de listas -----------------------------

def filas_desde_xlsx(datos):
    """Lee la primera hoja de un .xlsx usando solo zipfile+xml (sin openpyxl)."""
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        compartidas = []
        if 'xl/sharedStrings.xml' in z.namelist():
            raiz = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in raiz.findall('m:si', ns):
                compartidas.append(''.join(t.text or '' for t in si.iter(
                    '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')))
        hoja = next((n for n in ('xl/worksheets/sheet1.xml',)
                     if n in z.namelist()), None)
        if hoja is None:
            hoja = next((n for n in sorted(z.namelist())
                         if n.startswith('xl/worksheets/sheet')), None)
        if hoja is None:
            raise ValueError('El .xlsx no tiene hojas legibles.')
        raiz = ET.fromstring(z.read(hoja))
        filas = []
        for fila in raiz.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
            celdas = []
            for c in fila.findall('m:c', ns):
                v = c.find('m:v', ns)
                if v is None:
                    t_inline = c.find('m:is/m:t', ns)
                    celdas.append(t_inline.text or '' if t_inline is not None else '')
                elif c.get('t') == 's':
                    celdas.append(compartidas[int(v.text)])
                else:
                    celdas.append(v.text or '')
            filas.append(celdas)
        return filas


def filas_desde_texto(datos):
    texto = datos.decode('utf-8-sig', 'replace')
    try:
        dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=',;\t')
    except csv.Error:
        dialecto = csv.excel
    return [list(f) for f in csv.reader(io.StringIO(texto), dialecto)]


def extraer_correos(nombre_archivo, datos):
    """Devuelve [(email, nombre|None), ...] sin duplicados.
    Acepta xlsx/csv/txt: usa columnas 'correo'/'nombre' si existen; si no, regex."""
    if nombre_archivo.lower().endswith('.xlsx'):
        filas = filas_desde_xlsx(datos)
    else:
        filas = filas_desde_texto(datos)
    if not filas:
        return []

    encabezado = [str(c).strip().lower() for c in filas[0]]
    idx_email = next((i for i, c in enumerate(encabezado) if c in COL_EMAIL), None)
    idx_nombre = next((i for i, c in enumerate(encabezado) if c in COL_NOMBRE), None)
    vistos, lista = set(), []

    def agregar(email, nombre=None):
        email = str(email).strip().lower()
        if email and email not in vistos and EMAIL_RE.fullmatch(email):
            vistos.add(email)
            lista.append((email, (str(nombre).strip() if nombre else None) or None))

    if idx_email is not None:
        for fila in filas[1:]:
            if len(fila) > idx_email:
                nombre = fila[idx_nombre] if idx_nombre is not None and len(fila) > idx_nombre else None
                agregar(fila[idx_email], nombre)
    else:
        for fila in filas:
            for celda in fila:
                for email in EMAIL_RE.findall(str(celda)):
                    agregar(email)
    return lista


# ----------------------------- envio en segundo plano -----------------------------

def ejecutar_envio(trabajo_id):
    t = TRABAJOS[trabajo_id]
    for email, nombre in t['lista']:
        if t.get('cancelado'):
            break
        firmante = {'role': t['rol'], 'email': email}
        if nombre:
            firmante['name'] = nombre
        cuerpo = {
            'template_id': t['template_id'],
            'send_email': not t['modo_prueba'],
            'submitters': [firmante],
        }
        try:
            docuseal('POST', '/api/submissions', t['token'], cuerpo)
            t['ok'] += 1
        except urllib.error.HTTPError as e:
            t['errores'].append({'email': email, 'error': f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:200]}'})
        except Exception as e:
            t['errores'].append({'email': email, 'error': str(e)})
        t['procesados'] += 1
        time.sleep(0.1)
    t['estado'] = 'terminado'
    registrar_log(t)


def registrar_log(t):
    ruta = os.path.join(BASE, 'envios_log.csv')
    nuevo = not os.path.exists(ruta)
    with LOCK, open(ruta, 'a', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(['fecha', 'usuario', 'plantilla_id', 'plantilla', 'rol',
                        'archivo', 'total', 'ok', 'errores', 'modo_prueba'])
        w.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), t['usuario'],
                    t['template_id'], t['plantilla'], t['rol'], t['archivo'],
                    len(t['lista']), t['ok'], len(t['errores']),
                    'SI' if t['modo_prueba'] else 'NO'])


# ----------------------------- HTML embebido -----------------------------

PAGINA_LOGIN = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Firmas Digitales Copservir - Ingreso</title><style>
:root{--acento:#0E7490;--acento-osc:#155E75;--rojo:#C0392B;--tinta:#1F2933;--gris:#5A6572;--borde:#D3DCE1}
*{box-sizing:border-box}
body{font-family:"Segoe UI",system-ui,Arial,sans-serif;margin:0;min-height:100vh;display:flex;flex-direction:column;
  align-items:center;justify-content:center;background:linear-gradient(165deg,#F5F8FA 0%,#E9EFF3 100%)}
.marca{text-align:center;margin-bottom:1.4rem}
.marca svg{width:64px;height:64px}
.marca .sistema{font-size:1.15rem;color:var(--tinta);font-weight:700;letter-spacing:.3px;margin-top:.5rem}
.caja{background:#fff;padding:2.6rem 2.8rem;border-radius:16px;width:min(460px,92vw);
  box-shadow:0 10px 34px rgba(34,51,63,.16);border-top:6px solid var(--acento)}
h1{font-size:1.5rem;margin:0 0 .4rem;color:var(--tinta);font-weight:700}
.ayuda{color:var(--gris);font-size:1rem;margin:0 0 1.6rem}
label{display:block;font-weight:600;font-size:1.02rem;color:var(--tinta);margin-bottom:.4rem}
input{width:100%;padding:.95rem 1rem;margin-bottom:1.2rem;border:2px solid var(--borde);border-radius:10px;
  font-size:1.1rem;color:var(--tinta)}
input:focus{outline:3px solid rgba(14,116,144,.35);border-color:var(--acento)}
button{width:100%;padding:1rem;background:var(--acento-osc);color:#fff;border:0;border-radius:10px;
  font-size:1.15rem;font-weight:700;cursor:pointer;letter-spacing:.3px}
button:hover,button:focus-visible{background:#0F4C5C;outline:3px solid rgba(14,116,144,.4)}
.error{display:none;background:#FDECEC;border:2px solid var(--rojo);color:#8E1418;border-radius:10px;
  padding:.8rem 1rem;font-size:1rem;margin-bottom:1.2rem;font-weight:600}
.pie{font-size:.85rem;color:var(--gris);text-align:center;margin-top:1.6rem}
</style></head><body>
<div class="marca">
  <svg viewBox="0 0 48 48" role="img" aria-label="Firmas Masivas">
    <rect x="5" y="11" width="26" height="32" rx="3" fill="#155E75" opacity=".22"/>
    <rect x="10" y="6.5" width="26" height="32" rx="3" fill="#155E75" opacity=".5"/>
    <rect x="15" y="2" width="26" height="32" rx="3" fill="#0E7490"/>
    <line x1="20" y1="10" x2="36" y2="10" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".85"/>
    <line x1="20" y1="16" x2="36" y2="16" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".55"/>
    <path d="M19 27c3-6 5 3 8-2s3 2 9-3" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  </svg>
  <div class="sistema">Firmas Masivas &middot; Envío de documentos</div>
</div>
<form class="caja" method="post" action="/login">
  <h1>Ingreso al sistema</h1>
  <p class="ayuda">Ingresa con tu cuenta de Firmas Digitales (DocuSeal). Los envíos que hagas saldrán a nombre de tu propia cuenta.</p>
  <div class="error" id="err" role="alert">Correo o clave incorrectos, o la cuenta no pudo validarse en Firmas Digitales.</div>
  <label for="usuario">Correo de Firmas Digitales</label>
  <input id="usuario" name="usuario" type="email" required autofocus autocomplete="username">
  <label for="clave">Clave de Firmas Digitales</label>
  <input id="clave" name="clave" type="password" required autocomplete="current-password">
  <button>Ingresar</button>
  <p class="pie">Uso interno &middot; todos los envíos quedan registrados</p>
</form>
<script>if(location.search.includes('error')){document.getElementById('err').style.display='block'}</script>
</body></html>"""

PAGINA_PANEL = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Firmas Digitales Copservir - Envío masivo</title><style>
:root{--acento:#0E7490;--acento-osc:#155E75;--acento-suave:#E8F3F6;--rojo:#C0392B;--rojo-suave:#FBEDEB;
  --tinta:#1F2933;--gris:#5A6572;--borde:#D3DCE1;--ambar:#B7791F;--ambar-suave:#FCF5E7}
*{box-sizing:border-box}
body{font-family:"Segoe UI",system-ui,Arial,sans-serif;margin:0;background:#F1F5F7;color:var(--tinta);min-height:100vh;
  display:flex;flex-direction:column}
header{background:#22333F;border-bottom:3px solid var(--acento);padding:.65rem clamp(1rem,4vw,2.5rem);
  display:flex;align-items:center;justify-content:space-between;gap:1rem}
header svg{height:32px;width:32px;flex-shrink:0}
.titulo{font-size:1.1rem;font-weight:700;color:#F3F7F9;display:flex;align-items:center;gap:.65rem}
.titulo small{display:block;font-weight:400;color:#9FB4BF;font-size:.8rem}
.usuario{display:flex;align-items:center;gap:.8rem;font-size:.92rem;color:#9FB4BF}
.usuario b{color:#F3F7F9}
.salir{color:#8E1418;background:var(--rojo-suave);border:1px solid var(--rojo);border-radius:8px;
  padding:.45rem .9rem;text-decoration:none;font-weight:600;font-size:.9rem}
.salir:hover,.salir:focus-visible{background:var(--rojo);color:#fff;outline:3px solid rgba(224,39,46,.3)}
main{flex:1;width:min(760px,94vw);margin:2rem auto}
.paso{background:#fff;border:1px solid var(--borde);border-radius:14px;padding:1.5rem 1.7rem;margin-bottom:1.2rem;
  box-shadow:0 3px 14px rgba(0,0,0,.04)}
.paso h2{display:flex;align-items:center;gap:.7rem;font-size:1.12rem;margin:0 0 .4rem}
.num{background:var(--acento-osc);color:#fff;border-radius:50%;width:2rem;height:2rem;display:inline-flex;
  align-items:center;justify-content:center;font-size:1rem;flex-shrink:0}
.explica{color:var(--gris);font-size:.95rem;margin:0 0 1rem}
label{display:block;font-weight:600;font-size:1rem;margin:.9rem 0 .4rem}
select,input[type=file]{width:100%;padding:.85rem .9rem;border:2px solid var(--borde);border-radius:10px;
  font-size:1.05rem;background:#fff;color:var(--tinta)}
select:focus,input:focus{outline:3px solid rgba(14,116,144,.35);border-color:var(--acento)}
#resumen{display:none;border-radius:10px;padding:.9rem 1.1rem;font-size:1rem;margin-top:1rem;font-weight:600}
#resumen.bien{background:var(--acento-suave);border:2px solid var(--acento);color:#0B4C60}
#resumen.mal{background:var(--rojo-suave);border:2px solid var(--rojo);color:#8E1418}
.check{display:flex;gap:.7rem;align-items:flex-start;background:var(--ambar-suave);border:2px solid var(--ambar);
  border-radius:10px;padding:.9rem 1.1rem;margin-top:.3rem}
.check input{width:1.35rem;height:1.35rem;margin-top:.15rem;accent-color:var(--ambar);flex-shrink:0}
.check label{margin:0;font-weight:600;font-size:1rem;color:#7A5310}
.check small{display:block;font-weight:400;color:#7A5310;margin-top:.15rem}
#btnEnviar{background:var(--acento-osc);color:#fff;border:0;border-radius:10px;width:100%;padding:1.05rem;
  font-size:1.2rem;font-weight:700;cursor:pointer;margin-top:1.2rem;letter-spacing:.3px}
#btnEnviar:hover:not(:disabled),#btnEnviar:focus-visible{background:#0F4C5C;outline:3px solid rgba(14,116,144,.4)}
#btnEnviar:disabled{background:#9FB6C0;cursor:not-allowed}
#barraCaja{background:#DCE5EA;border-radius:10px;height:20px;margin-top:1.3rem;overflow:hidden;display:none}
#barra{background:linear-gradient(90deg,var(--acento),var(--acento-osc));height:100%;width:0%;transition:width .3s}
#estado{font-size:1.02rem;margin-top:.7rem;white-space:pre-line;font-weight:600}
#errores{font-size:.9rem;color:#8E1418;background:var(--rojo-suave);border-radius:10px;margin-top:.7rem;
  max-height:160px;overflow:auto;white-space:pre-line}
#errores:not(:empty){padding:.8rem 1rem;border:2px solid var(--rojo)}
footer{background:#fff;border-top:1px solid var(--borde);padding:.8rem;text-align:center;font-size:.85rem;
  color:var(--gris)}
</style></head><body>
<header>
  <div class="titulo">
    <svg viewBox="0 0 48 48" role="img" aria-label="Firmas Masivas">
      <rect x="5" y="11" width="26" height="32" rx="3" fill="#7FB3C4" opacity=".35"/>
      <rect x="10" y="6.5" width="26" height="32" rx="3" fill="#7FB3C4" opacity=".6"/>
      <rect x="15" y="2" width="26" height="32" rx="3" fill="#3FA3C0"/>
      <line x1="20" y1="10" x2="36" y2="10" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".85"/>
      <line x1="20" y1="16" x2="36" y2="16" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".55"/>
      <path d="M19 27c3-6 5 3 8-2s3 2 9-3" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round"/>
    </svg>
    <span>Firmas Masivas<small>Cada correo de la lista recibe su propia copia para firmar</small></span>
  </div>
  <div class="usuario"><span>Sesión: <b>{USUARIO}</b></span><a class="salir" href="/logout">Salir</a></div>
</header>
<main>
  <section class="paso">
    <h2><span class="num">1</span>Elige el documento</h2>
    <p class="explica">Selecciona la plantilla ya configurada en Firmas Digitales. Si tiene varios roles, elige cuál firmará.</p>
    <label for="plantilla">Plantilla</label>
    <select id="plantilla"><option>Cargando plantillas...</option></select>
    <label id="lblRol" for="rol" style="display:none">Rol que firmará</label>
    <select id="rol" style="display:none"></select>
  </section>
  <section class="paso">
    <h2><span class="num">2</span>Carga la lista de correos</h2>
    <p class="explica">Acepta Excel (.xlsx), .csv o .txt. Ideal: columnas <b>nombre</b> y <b>correo</b> en la primera fila. Se descartan duplicados y correos mal escritos.</p>
    <input type="file" id="archivo" accept=".xlsx,.csv,.txt" aria-describedby="resumen">
    <div id="resumen" role="status"></div>
  </section>
  <section class="paso">
    <h2><span class="num">3</span>Envía</h2>
    <!-- Modo prueba desactivado (2026-07-15). Para reactivarlo, descomenta este bloque:
    <div class="check"><input type="checkbox" id="prueba">
      <label for="prueba">Modo prueba: NO manda correos
      <small>Crea los envíos en el sistema para revisarlos, pero ningún destinatario recibe nada. Desmárcalo para el envío real.</small></label></div>
    -->
    <p class="explica">Al confirmar, cada correo de la lista recibirá su documento para firmar.</p>
    <button id="btnEnviar" disabled>Iniciar envío masivo</button>
    <div id="barraCaja"><div id="barra"></div></div>
    <div id="estado" role="status" aria-live="polite"></div><div id="errores"></div>
  </section>
</main>
<footer>Firmas Masivas &middot; herramienta interna &middot; todos los envíos quedan registrados con tu usuario</footer>
<script>
let correos=0, plantillas=[];
const $=id=>document.getElementById(id);

fetch('/api/plantillas').then(r=>r.json()).then(d=>{
  plantillas=d.plantillas;
  $('plantilla').innerHTML='<option value="">-- selecciona --</option>'+
    plantillas.map(p=>`<option value="${p.id}">${p.id} - ${p.nombre}</option>`).join('');
}).catch(()=>{$('plantilla').innerHTML='<option>Error cargando plantillas</option>'});

$('plantilla').onchange=()=>{
  const p=plantillas.find(x=>String(x.id)===$('plantilla').value);
  const multi=p&&p.roles.length>1;
  $('lblRol').style.display=$('rol').style.display=multi?'block':'none';
  if(p){
    const mejor=p.roles.reduce((a,b)=>b.campos>a.campos?b:a);
    $('rol').innerHTML=p.roles.map(r=>
      `<option value="${r.nombre}" ${r.nombre===mejor.nombre?'selected':''} ${r.campos===0?'disabled':''}>`+
      `${r.nombre} (${r.campos} campo${r.campos===1?'':'s'})${r.campos===0?' - vacío, no usar':''}</option>`).join('');
  }
  validar();
};

$('archivo').onchange=async()=>{
  const f=$('archivo').files[0]; if(!f) return;
  const r=await fetch('/api/analizar?nombre='+encodeURIComponent(f.name),{method:'POST',body:f});
  const d=await r.json();
  correos=d.total||0;
  $('resumen').style.display='block';
  $('resumen').className=d.total?'bien':'mal';
  $('resumen').textContent=d.total?`Se encontraron ${d.total} correos válidos. Primeros: ${d.muestra.join(', ')}`:'No se encontraron correos válidos en el archivo. Revisa que tenga una columna de correos.';
  validar();
};

function validar(){$('btnEnviar').disabled=!(correos>0&&$('plantilla').value)}

$('btnEnviar').onclick=async()=>{
  const chk=$('prueba');               // tolera que el checkbox de modo prueba este comentado
  const enPrueba=!!(chk&&chk.checked);
  const aviso=enPrueba
    ?`MODO PRUEBA: se crearán ${correos} envíos pero NO se mandará ningún correo. ¿Continuar?`
    :`Se enviarán ${correos} documentos REALES con la plantilla seleccionada. ¿Continuar?`;
  if(!confirm(aviso))return;
  $('btnEnviar').disabled=true;
  const f=$('archivo').files[0];
  const params=new URLSearchParams({nombre:f.name,template_id:$('plantilla').value,
    rol:$('rol').style.display!=='none'?$('rol').value:'',prueba:enPrueba?'1':'0'});
  const r=await fetch('/api/enviar?'+params,{method:'POST',body:f});
  const d=await r.json();
  if(d.error){$('estado').textContent='Error: '+d.error;$('btnEnviar').disabled=false;return}
  $('barraCaja').style.display='block';
  const timer=setInterval(async()=>{
    const p=await(await fetch('/api/progreso?id='+d.id)).json();
    $('barra').style.width=(100*p.procesados/p.total)+'%';
    $('estado').textContent=`${p.procesados}/${p.total} procesados - ${p.ok} enviados, ${p.errores.length} errores`;
    if(p.errores.length)$('errores').textContent=p.errores.map(e=>e.email+': '+e.error).join('\\n');
    if(p.estado==='terminado'){clearInterval(timer);
      $('estado').textContent+=enPrueba?'\\nFinalizado en MODO PRUEBA: NO se mandaron correos. Desmarca la casilla para el envío real.':'\\nEnvío finalizado: los correos fueron despachados.';
      $('btnEnviar').disabled=false}
  },800);
};
</script></body></html>"""


# ----------------------------- servidor HTTP -----------------------------

class Manejador(BaseHTTPRequestHandler):
    server_version = 'PanelEnvioMasivo/1.0'

    # --- utilidades ---
    def _responder(self, cuerpo, tipo='text/html; charset=utf-8', codigo=200, extra=None):
        datos = cuerpo.encode('utf-8') if isinstance(cuerpo, str) else cuerpo
        self.send_response(codigo)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(datos)))
        if 'Cache-Control' not in (extra or {}):
            self.send_header('Cache-Control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(datos)

    def _json(self, obj, codigo=200):
        self._responder(json.dumps(obj), 'application/json; charset=utf-8', codigo)

    def _redirigir(self, destino, cookie=None):
        extra = {'Location': destino}
        if cookie:
            extra['Set-Cookie'] = cookie
        self._responder('', codigo=302, extra=extra)

    def _usuario(self):
        c = cookies.SimpleCookie(self.headers.get('Cookie', ''))
        token = c['sesion'].value if 'sesion' in c else None
        return SESIONES.get(token)

    def _leer_cuerpo(self):
        largo = int(self.headers.get('Content-Length', 0))
        if largo > 30 * 1024 * 1024:
            raise ValueError('Archivo demasiado grande (max 30 MB).')
        return self.rfile.read(largo)

    def _params(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        return {k: v[0] for k, v in q.items()}

    def log_message(self, fmt, *args):  # silenciar log por peticion
        pass

    # --- rutas GET ---
    def do_GET(self):
        ruta = self.path.split('?')[0]
        usuario = self._usuario()

        if ruta in ('/logo_copservir.png', '/logo_docuseal.png'):
            archivo = os.path.join(BASE, ruta.lstrip('/'))
            if os.path.exists(archivo):
                with open(archivo, 'rb') as f:
                    return self._responder(f.read(), 'image/png',
                                           extra={'Cache-Control': 'max-age=86400'})
            return self._responder('No encontrado', codigo=404)

        if ruta == '/':
            if not usuario:
                return self._responder(PAGINA_LOGIN)
            return self._responder(PAGINA_PANEL.replace('{USUARIO}', usuario['usuario']))

        if ruta == '/logout':
            c = cookies.SimpleCookie(self.headers.get('Cookie', ''))
            if 'sesion' in c:
                SESIONES.pop(c['sesion'].value, None)
            return self._redirigir('/', 'sesion=; Max-Age=0; Path=/')

        if not usuario:
            return self._json({'error': 'no autenticado'}, 401)

        if ruta == '/api/plantillas':
            try:
                r = docuseal('GET', '/api/templates?limit=100', usuario['token'])
                plantillas = []
                for p in r['data']:
                    if p.get('archived_at'):
                        continue
                    campos = p.get('fields') or []
                    plantillas.append({
                        'id': p['id'], 'nombre': p['name'],
                        'roles': [{'nombre': s['name'],
                                   'campos': sum(1 for f in campos if f.get('submitter_uuid') == s['uuid'])}
                                  for s in p['submitters']],
                    })
                return self._json({'plantillas': plantillas})
            except Exception as e:
                return self._json({'error': str(e)}, 502)

        if ruta == '/api/progreso':
            t = TRABAJOS.get(self._params().get('id', ''))
            if not t:
                return self._json({'error': 'trabajo no encontrado'}, 404)
            return self._json({'total': len(t['lista']), 'procesados': t['procesados'],
                               'ok': t['ok'], 'errores': t['errores'][-50:], 'estado': t['estado']})

        return self._responder('No encontrado', codigo=404)

    # --- rutas POST ---
    def do_POST(self):
        ruta = self.path.split('?')[0]

        if ruta == '/login':
            from urllib.parse import parse_qs
            datos = parse_qs(self._leer_cuerpo().decode('utf-8'))
            email = datos.get('usuario', [''])[0].strip().lower()
            clave = datos.get('clave', [''])[0]
            token_ds = login_docuseal(email, clave) if email and clave else None
            if token_ds:
                token = secrets.token_urlsafe(32)
                SESIONES[token] = {'usuario': email, 'token': token_ds}
                return self._redirigir('/', f'sesion={token}; Path=/; HttpOnly; SameSite=Lax')
            return self._redirigir('/?error=1')

        usuario = self._usuario()
        if not usuario:
            return self._json({'error': 'no autenticado'}, 401)

        if ruta == '/api/analizar':
            try:
                p = self._params()
                lista = extraer_correos(p.get('nombre', 'lista.csv'), self._leer_cuerpo())
                return self._json({'total': len(lista), 'muestra': [e for e, _ in lista[:5]]})
            except Exception as e:
                return self._json({'error': str(e), 'total': 0, 'muestra': []})

        if ruta == '/api/enviar':
            p = self._params()
            try:
                template_id = int(p['template_id'])
                lista = extraer_correos(p.get('nombre', 'lista.csv'), self._leer_cuerpo())
                if not lista:
                    return self._json({'error': 'no hay correos validos en el archivo'})
                plantilla = docuseal('GET', f'/api/templates/{template_id}', usuario['token'])
                campos = plantilla.get('fields') or []
                conteo = {s['name']: sum(1 for f in campos if f.get('submitter_uuid') == s['uuid'])
                          for s in plantilla['submitters']}
                rol = p.get('rol') or max(conteo, key=conteo.get)
                if rol not in conteo:
                    return self._json({'error': f'rol {rol} no existe en la plantilla'})
                if conteo[rol] == 0:
                    return self._json({'error': f"el rol '{rol}' no tiene campos en la plantilla: "
                                                'el firmante no tendria nada que llenar. Elige otro rol '
                                                'o borra ese rol vacio de la plantilla.'})
                trabajo_id = secrets.token_hex(8)
                TRABAJOS[trabajo_id] = {
                    'usuario': usuario['usuario'], 'token': usuario['token'],
                    'template_id': template_id,
                    'plantilla': plantilla['name'], 'rol': rol,
                    'archivo': p.get('nombre', ''), 'lista': lista,
                    'modo_prueba': p.get('prueba') == '1',
                    'procesados': 0, 'ok': 0, 'errores': [], 'estado': 'enviando',
                }
                threading.Thread(target=ejecutar_envio, args=(trabajo_id,), daemon=True).start()
                return self._json({'id': trabajo_id, 'total': len(lista)})
            except Exception as e:
                return self._json({'error': str(e)})

        return self._responder('No encontrado', codigo=404)


# ----------------------------- arranque -----------------------------

def main():
    global CONFIG
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=os.path.join(BASE, 'config.json'))
    args = p.parse_args()

    with open(args.config, encoding='utf-8-sig') as f:
        CONFIG = json.load(f)

    host = CONFIG.get('escuchar', '0.0.0.0')
    puerto = int(CONFIG.get('puerto', 8450))
    print('Panel Firmas Masivas iniciado (Ctrl+C para apagar)')
    print(f'  Abre en este equipo:   http://localhost:{puerto}')
    if host == '0.0.0.0':
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            print(f'  Desde otras maquinas:  http://{ip}:{puerto}')
        except OSError:
            pass
    print(f'  DocuSeal destino:      {CONFIG["docuseal_url"]}')
    ThreadingHTTPServer((host, puerto), Manejador).serve_forever()


if __name__ == '__main__':
    main()
