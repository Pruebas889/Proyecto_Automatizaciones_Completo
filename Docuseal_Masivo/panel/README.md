# Firmas Masivas — Panel de envío masivo de documentos (DocuSeal)

Herramienta web interna para enviar un documento de DocuSeal a una lista masiva de
correos: **cada correo recibe su propia copia independiente para firmar**. Pensada para
usarse dentro de la red de Copservir contra `https://firmasdigitales.copservir.com`.

Es **un solo archivo Python sin dependencias externas** (solo librería estándar,
Python 3.10+). No hay nada que instalar: ni Flask, ni openpyxl, ni npm. El Excel
`.xlsx` se lee con `zipfile` + XML de la librería estándar.

---

## Archivos

| Archivo | Qué es |
|---|---|
| `panel.py` | Todo el sistema: servidor HTTP, API interna y las dos pantallas (login y panel) embebidas. |
| `config.json` | URL de la instancia DocuSeal y puerto del servidor. |
| `iniciar_panel.bat` | Arranque con doble clic en Windows. |
| `envios_log.csv` | Auditoría: se genera solo; una fila por cada envío masivo ejecutado. |
| `probar_login.py`, `probar_xlsx.py` | Pruebas automáticas (opcionales, para devs). |

En la carpeta padre (`..\`) están los scripts de línea de comandos que precedieron al
panel: `envio_masivo.py` (mismo motor que el panel, por consola) y
`contrafirma_masiva.py` (flujo jefe-firma-una-vez + N empleados, no incluido en el panel).

---

## Cómo correrlo

```bat
:: opción 1: doble clic
iniciar_panel.bat

:: opción 2: consola
python panel.py

:: opción 3: con otra configuración (ej. apuntando al DocuSeal local de desarrollo)
python panel.py --config config_local.json
```

Queda disponible en `http://localhost:8450` (o el puerto de `config.json`). Para
apagarlo: `Ctrl+C` o cerrar la ventana. **No necesita quedar prendido**: se arranca
cuando se va a usar.

Para que otras máquinas de la red lo usen (`http://IP-del-server:8450`), el firewall
de Windows debe permitir el puerto:

```powershell
New-NetFirewallRule -DisplayName "Firmas Masivas" -Direction Inbound -Protocol TCP -LocalPort 8450 -Action Allow
```

---

## Configuración (`config.json`)

```json
{
  "docuseal_url": "https://firmasdigitales.copservir.com",
  "puerto": 8450,
  "escuchar": "0.0.0.0"
}
```

| Campo | Significado |
|---|---|
| `docuseal_url` | Instancia de DocuSeal contra la que se valida el login y se envía. |
| `puerto` | Puerto del panel. |
| `escuchar` | `0.0.0.0` = accesible desde la red; `127.0.0.1` = solo esta máquina. |

Cualquier cambio en `config.json` requiere reiniciar el panel.

---

## Login y cuentas: cada envío sale de la cuenta de quien lo hace

**No hay usuarios propios del panel.** Cada persona ingresa con su **correo y clave de
DocuSeal** (los mismos de `firmasdigitales.copservir.com`). En el login, el panel:

1. Valida las credenciales contra la web de DocuSeal (misma pantalla `/sign_in`).
2. Obtiene automáticamente el **token de API de esa cuenta** (el de Configuración → API).
3. Guarda el token solo **en la sesión en memoria** — la clave no se almacena en
   ninguna parte y el token nunca llega al navegador.

Resultado: **los envíos de cada usuario salen a nombre de su propia cuenta DocuSeal**
(creador, certificado y auditoría correctos), y cada quien ve sus plantillas.

Implicaciones prácticas:

- Dar acceso a alguien = crearle su cuenta en DocuSeal (no hay nada que hacer en el panel).
- Quitar acceso = desactivar su cuenta DocuSeal.
- Cambio de clave: se hace en DocuSeal; el panel lo toma automáticamente en el
  siguiente login.
- Cerrar el panel (reiniciarlo) cierra todas las sesiones activas.
- Si la cuenta tiene verificación en dos pasos (2FA) activa en DocuSeal, el login del
  panel no podrá validarla — usar una cuenta sin 2FA o desactivarla.

---

## Uso (lo que ve el usuario final)

1. **Elegir plantilla**: lista las últimas 100 plantillas no archivadas de la cuenta.
   Si la plantilla tiene varios roles, aparece un selector que muestra cuántos campos
   tiene cada rol; los roles sin campos salen bloqueados ("vacío, no usar") y el
   backend también los rechaza.
2. **Cargar la lista**: `.xlsx`, `.csv` o `.txt` (máx. 30 MB).
   - Ideal: primera fila con encabezados `correo` (o `email`) y opcionalmente `nombre`
     — el nombre queda prellenado en el documento.
   - Sin encabezados reconocidos: extrae por patrón todo lo que parezca correo
     (cuidado si hay dos columnas de correos: toma ambas).
   - Descarta duplicados y correos con formato inválido; muestra el total detectado
     y una muestra **antes** de enviar.
3. **Iniciar envío masivo**: pide confirmación, muestra barra de progreso en vivo
   (~8 envíos/segundo) y lista los errores por correo si los hay.

Cada envío crea una *submission* independiente en DocuSeal asignada al rol elegido;
los demás roles de la plantilla no se incluyen.

### Modo prueba (desactivado)

Existía un checkbox "Modo prueba" (crear envíos sin mandar correos). Está **comentado**
en el HTML dentro de `panel.py` — buscar `Modo prueba desactivado` y descomentar el
bloque para reactivarlo. El backend lo sigue soportando (`prueba=1` en `/api/enviar`).

---

## Implementarlo en un servidor nuevo

1. Verificar que el servidor tenga **Python 3.10+** (`python --version`). Es lo único.
2. Copiar la carpeta `panel\` completa (sin `envios_log.csv` ni `config_local.json`).
3. Revisar `config.json` (URL de DocuSeal, puerto).
4. Verificar que el servidor tenga salida de red hacia `docuseal_url` (el login depende de eso).
5. Abrir el puerto en el firewall (comando arriba).
6. Arrancar con `iniciar_panel.bat` cuando se vaya a usar.

> Seguridad: el panel habla HTTP plano — es para **red interna solamente**, nunca
> exponerlo a internet. Las claves de DocuSeal solo se reenvían al `docuseal_url`
> (HTTPS) durante el login y no se almacenan.

---

## API interna (para integraciones o debugging)

Todas requieren la cookie de sesión del login, excepto `/login`.

| Método y ruta | Función |
|---|---|
| `POST /login` | form-urlencoded `usuario` (correo DocuSeal), `clave`. Valida contra DocuSeal y devuelve cookie `sesion`. |
| `GET /logout` | Cierra la sesión. |
| `GET /api/plantillas` | Plantillas de la cuenta con roles y conteo de campos. |
| `POST /api/analizar?nombre=archivo.xlsx` | Body = archivo crudo. Devuelve `{total, muestra}`. |
| `POST /api/enviar?nombre=...&template_id=...&rol=...&prueba=0` | Body = archivo crudo. Inicia el envío en segundo plano, devuelve `{id}`. |
| `GET /api/progreso?id=...` | `{total, procesados, ok, errores, estado}` para la barra de progreso. |

---

## Problemas frecuentes

| Síntoma | Causa probable / solución |
|---|---|
| No arranca: `Address already in use` | Ya hay una instancia corriendo en ese puerto. Cerrarla o cambiar `puerto`. |
| Login rechaza credenciales correctas | ¿La cuenta tiene 2FA activo en DocuSeal? ¿El servidor tiene red hacia `docuseal_url`? Probar con `python probar_login.py correo clave`. |
| "Error cargando plantillas" | El token de la sesión fue revocado en DocuSeal, o se cayó la red hacia `docuseal_url`. Salir y volver a entrar. |
| Los correos no llegan | 1) Revisar spam. 2) Verificar el SMTP de la instancia DocuSeal (en local no hay SMTP: los envíos se crean pero no sale ningún correo). 3) ¿El envío se hizo con modo prueba activo? Ver columna `modo_prueba` en `envios_log.csv`. |
| "No se encontraron correos válidos" | La tabla no tiene columna de correos legible; revisar encabezados o exportar a CSV. |
| El destinatario abre y no tiene campos | Se envió a un rol sin campos (versiones viejas) o la plantilla está mal configurada; el panel actual bloquea esos roles. |
| Otras máquinas no acceden | `escuchar` debe ser `0.0.0.0` y el puerto abierto en el firewall del servidor. |
