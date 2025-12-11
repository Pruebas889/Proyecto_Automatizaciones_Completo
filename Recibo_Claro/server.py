# coding: utf-8
from functools import wraps
from flask import Flask, request, jsonify, render_template_string, Response, session, redirect
import threading
import time
import subprocess
import os
import logging
from collections import deque
from datetime import datetime
from control_flow import stop_automation_flag, start_automation, stop_automation

app = Flask(__name__)
app.secret_key = '3103487201022947165sG'  # Misma clave que el servidor principal
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos de expiración de sesión

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('username') != 'claro':
            return redirect('http://192.168.21.56:5000')
        return f(*args, **kwargs)
    return decorated_function

# Configuración de los logs
log_queue = deque(maxlen=200)
class QueueHandler(logging.Handler):
    def emit(self, record):
        log_queue.append(self.format(record))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[QueueHandler(), logging.StreamHandler()]
)

automation_process = None
is_running = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automatización de Facturas</title>
    <script src="http://cdn.tailwindcss.com"></script>
    <script src="http://unpkg.com/lucide@latest"></script>
    <link rel="icon" type="image/x-icon" href="images/Logo_Copservir.png">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #1a202c;
            color: #e2e8f0;
        }
    </style>
</head>
<body class="bg-gray-900 min-h-screen p-8 antialiased">
    <div class="max-w-4xl mx-auto space-y-8">
        <header class="text-center">
            <h1 class="text-4xl font-extrabold text-blue-400 mb-2">Automatización de Facturas</h1>
            <p class="text-gray-300">Interfaz de control para el script de descarga de facturas de Claro Empresas.</p>
        </header>

        <!-- Panel de Control -->
        <div class="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700">
            <h2 class="text-2xl font-bold text-gray-100 mb-4">Panel de Control</h2>
            <!-- Formulario para Año y Mes -->
            <form id="automation-form" class="mb-6 space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label for="anio" class="block text-sm font-medium text-gray-300">Selecciona el Año</label>
                        <select id="anio" name="anio" class="mt-1 block w-full p-2 rounded-md bg-gray-700 border border-gray-600 text-gray-200 focus:ring-blue-500 focus:border-blue-500" required>
                            <option value="">-- Elige un año --</option>
                        </select>
                    </div>
                    <div>
                        <label for="mes" class="block text-sm font-medium text-gray-300">Selecciona el Mes</label>
                        <select id="mes" name="mes" class="mt-1 block w-full p-2 rounded-md bg-gray-700 border border-gray-600 text-gray-200 focus:ring-blue-500 focus:border-blue-500" required>
                            <option value="">-- Elige un mes --</option>
                            <option value="01">Enero</option>
                            <option value="02">Febrero</option>
                            <option value="03">Marzo</option>
                            <option value="04">Abril</option>
                            <option value="05">Mayo</option>
                            <option value="06">Junio</option>
                            <option value="07">Julio</option>
                            <option value="08">Agosto</option>
                            <option value="09">Septiembre</option>
                            <option value="10">Octubre</option>
                            <option value="11">Noviembre</option>
                            <option value="12">Diciembre</option>
                        </select>
                    </div>
                </div>
            </form>
            <div class="flex items-center justify-between">
                <div class="flex space-x-2">
                    <button id="startButton" class="flex items-center space-x-2 px-6 py-3 rounded-full text-white font-semibold transition-transform duration-200 transform hover:scale-105 shadow-md bg-green-600 hover:bg-green-700 active:bg-green-800">
                        <i data-lucide="play" class="h-5 w-5"></i>
                        <span>Iniciar</span>
                    </button>
                    <button id="restartButton" class="flex items-center space-x-2 px-6 py-3 rounded-full text-white font-semibold transition-transform duration-200 transform hover:scale-105 shadow-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800">
                        <i data-lucide="rotate-ccw" class="h-5 w-5"></i>
                        <span>Reiniciar</span>
                    </button>
                    <button id="stopButton" disabled class="flex items-center space-x-2 px-6 py-3 rounded-full text-white font-semibold transition-transform duration-200 transform hover:scale-105 shadow-md bg-gray-600 cursor-not-allowed">
                        <i data-lucide="stop-circle" class="h-5 w-5"></i>
                        <span>Detener</span>
                    </button>
                    <button id="procesarRecibosButton" class="flex items-center space-x-2 px-6 py-3 rounded-full text-white font-semibold transition-transform duration-200 transform hover:scale-105 shadow-md bg-purple-600 hover:bg-purple-700 active:bg-purple-800">
                        <i data-lucide="file-text" class="h-5 w-5"></i>
                        <span>Procesar Recibos PDF</span>
                    </button>
                    <button id="borrarProgresoButton" class="flex items-center space-x-2 px-6 py-3 rounded-full text-white font-semibold transition-transform duration-200 transform hover:scale-105 shadow-md bg-red-600 hover:bg-red-700 active:bg-red-800">
                        <i data-lucide="trash-2" class="h-5 w-5"></i>
                        <span>Borrar Progreso Descargas</span>
                    </button>
                </div>
            </div>
        </div>

        <!-- Estado y Resumen -->
        <div class="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700">
            <h2 class="text-2xl font-bold text-gray-100 mb-2">Estado Actual</h2>
            <div class="flex items-center space-x-3 mb-4 text-lg">
                <div id="statusIcon">
                    <i data-lucide="info" class="text-gray-500"></i>
                </div>
                <span id="statusText" class="font-semibold text-gray-200">En espera</span>
            </div>
            <div id="resultsPanel" class="hidden bg-gray-900 p-4 rounded-lg border border-gray-700">
                <h3 class="font-bold text-lg mb-2 text-gray-100">Resumen del Proceso</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-gray-800 p-4 rounded-md shadow-inner flex items-center justify-between">
                        <div class="flex items-center space-x-2">
                            <i data-lucide="check-circle" class="text-green-500"></i>
                            <span class="font-medium text-gray-300">Facturas descargadas con éxito</span>
                        </div>
                        <span id="downloadedCount" class="text-2xl font-bold text-green-400">0</span>
                    </div>
                    <div class="bg-gray-800 p-4 rounded-md shadow-inner flex items-center justify-between">
                        <div class="flex items-center space-x-2">
                            <i data-lucide="x-circle" class="text-red-500"></i>
                            <span class="font-medium text-gray-300">Facturas fallidas</span>
                        </div>
                        <span id="failedCount" class="text-2xl font-bold text-red-400">0</span>
                    </div>
                </div>
                <div id="warningMessage" class="hidden mt-4 bg-yellow-900 bg-opacity-30 border border-yellow-800 p-4 rounded-md">
                    <div class="flex items-start space-x-3 text-yellow-300">
                        <i data-lucide="info" class="h-5 w-5 mt-1"></i>
                        <p class="text-sm">
                            Hay facturas fallidas. Por favor, revisa manualmente estas facturas en el portal de Claro.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Consola de Logs -->
        <div class="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700">
            <h2 class="text-2xl font-bold text-gray-100 mb-4">Consola de Logs</h2>
            <div id="logConsole" class="bg-gray-900 p-4 rounded-lg h-96 overflow-y-auto text-sm leading-6 tracking-wide font-mono">
                <p class="text-gray-500 animate-pulse">Esperando para iniciar la automatización...</p>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const anioSelect = document.getElementById('anio');
            const mesSelect = document.getElementById('mes');
            const currentYear = new Date().getFullYear();
            const currentMonth = String(new Date().getMonth() + 1).padStart(2, '0');
            const years = [currentYear - 1, currentYear];

            years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                anioSelect.appendChild(option);
            });

            anioSelect.value = currentYear;
            mesSelect.value = currentMonth;
        });

        const startButton = document.getElementById('startButton');
        const restartButton = document.getElementById('restartButton');
        const stopButton = document.getElementById('stopButton');
        const procesarRecibosButton = document.getElementById('procesarRecibosButton');
        const borrarProgresoButton = document.getElementById('borrarProgresoButton');
        const automationForm = document.getElementById('automation-form');
        const statusText = document.getElementById('statusText');
        const statusIconContainer = document.getElementById('statusIcon');
        const logConsole = document.getElementById('logConsole');
        const resultsPanel = document.getElementById('resultsPanel');
        const downloadedCountSpan = document.getElementById('downloadedCount');
        const failedCountSpan = document.getElementById('failedCount');
        const warningMessage = document.getElementById('warningMessage');

        let eventSource;
        let downloadedCount = 0;
        let failedCount = 0;
        let isRunning = false;

        const updateStatus = (status, iconHtml) => {
            statusText.textContent = status;
            statusIconContainer.innerHTML = iconHtml;
            lucide.createIcons();
        };

        const updateButtons = (running) => {
            isRunning = running;
            startButton.disabled = running;
            stopButton.disabled = !running;
            restartButton.disabled = running;
            startButton.classList.toggle('bg-gray-600', running);
            startButton.classList.toggle('hover:bg-green-700', !running);
            startButton.classList.toggle('cursor-not-allowed', running);
            stopButton.classList.toggle('bg-gray-600', !running);
            stopButton.classList.toggle('hover:bg-red-700', running);
            stopButton.classList.toggle('cursor-not-allowed', !running);
            restartButton.classList.toggle('bg-gray-600', running);
            restartButton.classList.toggle('hover:bg-blue-700', !running);
            restartButton.classList.toggle('cursor-not-allowed', running);
        };

        const getLogColor = (message) => {
            if (message.includes("🎉") || message.includes("✅")) return "text-green-500";
            if (message.includes("❌") || message.includes("🚨")) return "text-red-500";
            if (message.includes("⚠️") || message.includes("🚫")) return "text-yellow-500";
            return "text-gray-400";
        };

        const appendLog = (message) => {
            const p = document.createElement('p');
            p.textContent = message;
            p.className = `font-mono whitespace-pre-wrap ${getLogColor(message)}`;
            logConsole.appendChild(p);
            logConsole.scrollTop = logConsole.scrollHeight;
        };

        const updateCounts = () => {
            downloadedCountSpan.textContent = downloadedCount;
            failedCountSpan.textContent = failedCount;
            if (failedCount > 0) {
                warningMessage.classList.remove('hidden');
            } else {
                warningMessage.classList.add('hidden');
            }
        };

        const startAutomation = async () => {
            if (isRunning) return;

            const formData = new FormData(automationForm);
            const anio = formData.get('anio');
            const mes = formData.get('mes');

            if (!anio || !mes) {
                appendLog("❌ Por favor, selecciona un año y mes válidos.");
                return;
            }

            updateButtons(true);
            resultsPanel.classList.add('hidden');
            logConsole.innerHTML = '';
            downloadedCount = 0;
            failedCount = 0;
            updateCounts();

            updateStatus("Iniciando automatización...", `<i data-lucide="loader-2" class="animate-spin text-blue-500 h-6 w-6"></i>`);

            try {
                const response = await fetch('/start', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.success) {
                    startLogStream();
                } else {
                    stopLogStream();
                    updateButtons(false);
                    updateStatus("Error al iniciar", `<i data-lucide="x-circle" class="text-red-500 h-6 w-6"></i>`);
                    appendLog("Error: " + data.message);
                }
            } catch (error) {
                console.error('Error al iniciar la automatización:', error);
                updateButtons(false);
                updateStatus("Error de conexión", `<i data-lucide="x-circle" class="text-red-500 h-6 w-6"></i>`);
                appendLog("Error de conexión con el servidor.");
            }
        };

        const stopAutomation = async () => {
            if (!isRunning) return;

            updateButtons(false);
            updateStatus("Deteniendo...", `<i data-lucide="alert-triangle" class="text-yellow-500 h-6 w-6"></i>`);

            try {
                const response = await fetch('/stop', { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    appendLog("Proceso detenido por el usuario. 🛑");
                    updateStatus("Detenido por el usuario", `<i data-lucide="alert-triangle" class="text-yellow-500 h-6 w-6"></i>`);
                } else {
                    appendLog("Advertencia: No se pudo detener la automatización de inmediato.");
                    updateStatus("Detenido (parcial)", `<i data-lucide="alert-triangle" class="text-yellow-500 h-6 w-6"></i>`);
                }
            } catch (error) {
                console.error('Error al detener la automatización:', error);
            }
        };

        const restartAutomation = () => {
            stopAutomation();
            updateButtons(false);
            resultsPanel.classList.add('hidden');
            logConsole.innerHTML = '<p class="text-gray-500 animate-pulse">Esperando para iniciar la automatización...</p>';
            updateStatus("En espera", `<i data-lucide="info" class="text-gray-500 h-6 w-6"></i>`);
        };

        function startLogStream() {
            if (eventSource) {
                eventSource.close();
            }
            eventSource = new EventSource('/stream_logs');
            eventSource.onmessage = function(event) {
                const logMessage = event.data;
                appendLog(logMessage);

                if (logMessage.includes("descargada con éxito")) {
                    downloadedCount++;
                } else if (logMessage.includes("Descarga fallida para factura")) {
                    failedCount++;
                }

                if (logMessage.includes("Automatización finalizada con éxito")) {
                    updateButtons(false);
                    resultsPanel.classList.remove('hidden');
                    updateStatus("Finalizado con éxito", `<i data-lucide="check-circle" class="text-green-500 h-6 w-6"></i>`);
                } else if (logMessage.includes("Finalizado con errores")) {
                    updateButtons(false);
                    resultsPanel.classList.remove('hidden');
                    updateStatus("Finalizado con errores", `<i data-lucide="alert-triangle" class="text-yellow-500 h-6 w-6"></i>`);
                    warningMessage.classList.remove('hidden');
                }

                updateCounts();
            };
            eventSource.onerror = function(event) {
                console.error('Error en el stream de logs', event);
                stopLogStream();
            };
        }

        function stopLogStream() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        }

        startButton.addEventListener('click', startAutomation);
        stopButton.addEventListener('click', stopAutomation);
        restartButton.addEventListener('click', restartAutomation);

        procesarRecibosButton.addEventListener('click', async () => {
            appendLog("Procesando recibos PDF...");
            updateStatus("Procesando recibos PDF...", `<i data-lucide="file-text" class="text-purple-500 h-6 w-6"></i>`);
            try {
                const response = await fetch('/procesar_recibos', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    appendLog("✅ Recibos procesados correctamente.");
                    updateStatus("Recibos procesados", `<i data-lucide="check-circle" class="text-green-500 h-6 w-6"></i>`);
                } else {
                    appendLog("❌ Error al procesar recibos: " + data.message);
                    updateStatus("Error al procesar recibos", `<i data-lucide="x-circle" class="text-red-500 h-6 w-6"></i>`);
                }
            } catch (error) {
                appendLog("❌ Error de conexión al procesar recibos.");
                updateStatus("Error de conexión", `<i data-lucide="x-circle" class="text-red-500 h-6 w-6"></i>`);
            }
            lucide.createIcons();
        });

        borrarProgresoButton.addEventListener('click', async () => {
            appendLog("Borrando progreso y facturas...");
            updateStatus("Borrando progreso...", `<i data-lucide="trash-2" class="text-red-500 h-6 w-6"></i>`);
            try {
                const response = await fetch('/borrar_progreso', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    appendLog("✅ Progreso y facturas borrados correctamente.");
                    updateStatus("Progreso borrado", `<i data-lucide="check-circle" class="text-green-500 h-6 w-6"></i>`);
                } else {
                    appendLog("❌ Error al borrar progreso: " + data.message);
                    updateStatus("Error al borrar progreso", `<i data-lucide="x-circle" class="text-red-500 h-6 w-6"></i>`);
                }
            } catch (error) {
                appendLog("❌ Error de conexión al borrar progreso.");
                updateStatus("Error de conexión", `<i data-lucide="x-circle" class="text-red-500 h-6 w-6"></i>`);
            }
            lucide.createIcons();
        });

        lucide.createIcons();
    </script>
</body>
</html>
"""

def read_logs_from_subprocess():
    global automation_process, is_running
    if not automation_process or automation_process.stdout is None:
        logging.error("No se pudo iniciar el lector de logs. El proceso no está disponible o no tiene salida estándar.")
        return
    logging.info("Iniciando la lectura de logs del subproceso...")
    for line in iter(automation_process.stdout.readline, ''):
        try:
            decoded_line = line.strip()
            if decoded_line:
                logging.info(decoded_line)
        except Exception as e:
            logging.error(f"Error al procesar la línea de log: {e}")
    automation_process.wait()
    is_running = False
    logging.info("El subproceso de automatización ha finalizado.")

@app.route('/')
@login_required
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start', methods=['POST'])
@login_required
def start():
    global automation_process, is_running
    if is_running:
        return jsonify({'success': False, 'message': 'La automatización ya está en ejecución.'})

    is_running = True
    
    username = "maria_garcia@copservir.com"
    password = "Clave1234*"
    download_dir = r"C:\Users\dforero\Downloads\Facturas_Claro_Pruebas"
    
    anio = request.form.get('anio')
    mes = request.form.get('mes')

    try:
        anio = int(anio) # type: ignore
        mes = mes.zfill(2) # type: ignore
        current_year = datetime.now().year
        if anio not in [current_year, current_year - 1] or mes not in [f"{i:02d}" for i in range(1, 13)]:
            is_running = False
            logging.error(f"Año o mes inválido: anio={anio}, mes={mes}")
            return jsonify({'success': False, 'message': f'Año o mes inválido: anio={anio}, mes={mes}'})
        logging.info(f"Iniciando automatización con anio={anio}, mes={mes}")
    except (ValueError, TypeError) as e:
        is_running = False
        logging.error(f"Año o mes no proporcionados o no válidos: anio={anio}, mes={mes}, error={e}")
        return jsonify({'success': False, 'message': f'Año o mes no proporcionados o no válidos: {e}'})

    try:
        automation_process = start_automation(username, password, download_dir, anio, mes)
        logging.info("Automatización iniciada. Revisa los logs para el progreso.")
        threading.Thread(target=read_logs_from_subprocess, daemon=True).start()
        return jsonify({'success': True, 'message': 'Automatización iniciada. Revisa los logs para el progreso.'})
    except Exception as e:
        is_running = False
        logging.error(f"Error al iniciar la automatización: {e}")
        return jsonify({'success': False, 'message': f"Error al iniciar la automatización: {e}"})

@app.route('/stop', methods=['POST'])
@login_required
def stop():
    global automation_process, is_running
    if not is_running:
        return jsonify({'success': False, 'message': 'No hay ninguna automatización en ejecución para detener.'})

    stop_automation()
    if automation_process and automation_process.poll() is None:
        try:
            if os.name == 'nt':
                automation_process.kill()
            else:
                automation_process.terminate()
            logging.warning("Señal de detención enviada. El proceso debería terminar pronto.")
            time.sleep(2)
            if automation_process.poll() is not None:
                is_running = False
                logging.info('Proceso de automatización detenido exitosamente.')
                return jsonify({'success': True, 'message': 'Proceso de automatización detenido exitosamente.'})
            else:
                logging.warning('Proceso de automatización no se detuvo de forma inmediata.')
                return jsonify({'success': False, 'message': 'Proceso de automatización no se detuvo de forma inmediata.'})
        except Exception as e:
            logging.error(f'Error al intentar detener el proceso: {e}')
            return jsonify({'success': False, 'message': f'Error al intentar detener el proceso: {e}'})
    else:
        is_running = False
        return jsonify({'success': True, 'message': 'El proceso ya había finalizado o no estaba corriendo.'})

@app.route('/procesar_recibos', methods=['POST'])
@login_required
def procesar_recibos():
    try:
        result = subprocess.run(
            ['python', 'procesador_recibos.py'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=1000
        )
        output = (result.stdout or "") + (result.stderr or "")
        if output:
            for line in output.splitlines():
                if line.strip():
                    logging.info(line.strip())
        else:
            logging.warning("No se capturó salida estándar ni de error de procesador_recibos.py")
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Recibos procesados correctamente.'})
        else:
            logging.error(f"procesador_recibos.py finalizó con código de error: {result.returncode}")
            return jsonify({'success': False, 'message': f"Error en procesador_recibos.py: {output or 'Sin detalles'}"})
    except subprocess.TimeoutExpired:
        logging.error("El proceso de procesador_recibos.py excedió el tiempo límite (500 segundos)")
        return jsonify({'success': False, 'message': 'El proceso excedió el tiempo límite'})
    except Exception as e:
        logging.error(f"Error al ejecutar procesador_recibos.py: {e}")
        return jsonify({'success': False, 'message': f"Error al ejecutar procesador_recibos.py: {e}"})

@app.route('/borrar_progreso', methods=['POST'])
@login_required
def borrar_progreso():
    try:
        progreso_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'progreso_descargas.json')
        progreso_inicial = {
            "ultima_pagina": 0,
            "facturas_descargadas": [],
            "facturas_fallidas": [],
            "ultima_factura_procesada": 0
        }
        with open(progreso_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(progreso_inicial, f, indent=4, ensure_ascii=False)
        
        facturas_dir = r"C:\Users\dforero\Downloads\Facturas_Claro_Pruebas"
        import shutil
        if os.path.exists(facturas_dir):
            for filename in os.listdir(facturas_dir):
                file_path = os.path.join(facturas_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logging.error(f"No se pudo borrar {file_path}: {e}")
        return jsonify({'success': True, 'message': 'Progreso y facturas borrados correctamente.'})
    except Exception as e:
        logging.error(f"Error al borrar progreso: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/stream_logs')
@login_required
def stream_logs():
    def generate_logs():
        for log_line in list(log_queue):
            yield f"data: {log_line}\n\n"
        last_log_index = len(log_queue)
        while True:
            if len(log_queue) > last_log_index:
                new_log = log_queue[last_log_index]
                yield f"data: {new_log}\n\n"
                last_log_index += 1
            time.sleep(0.5)
    return Response(generate_logs(), mimetype='text/event-stream')

if __name__ == '__main__':
    logging.info("Iniciando el servidor de la interfaz web... 🚀")
    app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)