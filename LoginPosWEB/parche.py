"""
Muestra un tipo de modal con la información
de que se busca realizar con la automatización.
"""
import tkinter as tk
import threading
import time

def parche_modal(titulo="Automatización en curso...", mensaje="Iniciando pruebas...", duracion=4):
    """
    Muestra una ventana tipo modal centrada en la pantalla con un mensaje de inicio.
    Se ejecuta en un hilo separado para no bloquear el programa principal.
    """
    def mostrar_ventana():
        root = tk.Tk()
        root.title(titulo)

        width = 600
        height = 180
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        background_color = "#6ecf5f"  # Verde suave
        text_color = "white"

        root.configure(bg=background_color)
        root.overrideredirect(True)
        root.attributes('-topmost', True)

        label = tk.Label(
            root,
            text=mensaje,
            fg=text_color,
            bg=background_color,
            font=("Segoe UI", 14, "bold"),
            wraplength=520,
            justify="center",
            pady=40
        )
        label.pack(expand=True)

        threading.Thread(target=lambda: (time.sleep(duracion), root.destroy()), daemon=True).start()
        root.mainloop()

    # Inicia la ventana en un hilo separado
    threading.Thread(target=mostrar_ventana, daemon=True).start()
