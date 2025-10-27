# Mensajeros - Checkpoint para reanudación

Este repositorio contiene la automatización para consultar comparendos de mensajeros.

Se añadió un mecanismo simple de checkpoint para que, si la automatización se detiene, pueda reanudarse desde la última cédula procesada.

Cómo funciona:

- El script crea/actualiza un archivo `checkpoint.txt` en el mismo directorio cuando procesa cada cédula, escribiendo el índice (entero) de la cédula.
- Al iniciar, el script lee `checkpoint.txt` (si existe) y reanuda desde ese índice.
- Al completar exitosamente todo el procesamiento de cédulas, el script borra el `checkpoint.txt`.

Operaciones manuales útiles:

- Forzar reanudar desde el inicio: borrar `checkpoint.txt` antes de ejecutar el script.
- Reanudar donde quedó: ejecutar el script normalmente; si existe `checkpoint.txt`, reanudará desde ese índice.

Ruta del checkpoint (local): `checkpoint.txt` (en el mismo directorio que `mensajeros.py`).

Notas:
- El checkpoint almacena el índice (posición) en la lista de cédulas leídas desde Google Sheets, no la cédula en sí.
- Si modificas el orden de la hoja de cédulas, considera limpiar `checkpoint.txt` para evitar inconsistencias.

### Interfaz web (server)

He añadido un servidor web ligero basado en Flask llamado `server.py` que expone una interfaz básica para consultar el estado y manipular el `checkpoint` desde el navegador.

Archivos creados:
- `server.py` - servidor Flask que sirve la UI y varios endpoints API (`/api/status`, `/api/checkpoint`, `/api/start`).
- `templates/index.html` - página HTML básica con botones para consultar estado, leer/guardar checkpoint y solicitar inicio de la automatización (demo).
- `static/css/style.css` - estilos mínimos para la UI.
- `requirements.txt` - lista de dependencias sugeridas.

Cómo ejecutar (Windows PowerShell):

1. Crear y activar un entorno virtual (recomendado):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

3. Ejecutar el servidor:

```powershell
python server.py
```

El servidor escuchará en todas las interfaces (0.0.0.0) y puerto `5007`. Desde otra máquina en la misma red, abre http://<IP_DEL_PC>:5007 (por ejemplo http://192.168.1.5:5007).

Notas de seguridad y funcionamiento:
- Por seguridad, el botón "Iniciar automatización" en la UI no lanzará automáticamente el bucle infinito de `mensajeros.py` en esta primera versión; solo lanza un hilo de demostración.
- No expongas este servidor a Internet público sin agregar autenticación y HTTPS.
- El servidor asume que `mensajeros.py` está en el mismo directorio y puede importarse; ya comprobamos que `leer_checkpoint()` es llamable.

Si quieres que el servidor pueda iniciar/parar la automatización real, puedo agregar endpoints seguros y confirmaciones, y evitar ejecutar el bucle infinito directamente desde la importación.
