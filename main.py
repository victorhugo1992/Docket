# Archivo: main.py
import tkinter as tk
from tkinter import ttk
import sys
import matplotlib.pyplot as plt

# IMPORTANTE: Aquí importamos la vista desde tu nueva carpeta
from vistas.home import HomeTab
from vistas.voladuras import VistaVoladuras
from vistas.diseno import VistaDiseno

class DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # Obtener el ancho y alto de la pantalla
        #screen_width = self.winfo_screenwidth()
        #screen_height = self.winfo_screenheight()

        self.ultima_ruta_mallas = None
        
        # Aplicar la geometría (Ancho x Alto + Posición X + Posición Y)
        #self.geometry(f"{screen_width}x{screen_height}+0+0")

        self.title("Sistema de Control y Reportes - Docket Suite")
        self.state("zoomed")
        #self.geometry("950x600")
        self.configure(bg="#E6E6E6")
        #self.grab_set()
        
        self.build_menu()
        self.build_tabs()

        # 🟢 NUEVO: Interceptar el cierre de la ventana
        self.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion_limpio)

    def build_menu(self):
        menubar = tk.Menu(self)

        # --- MENÚ ARCHIVO ---
        menu_archivo = tk.Menu(menubar, tearoff=0)
        menu_archivo.add_command(label="Salir", command=self.quit)
        menubar.add_cascade(label="Menú", menu=menu_archivo) # Esto crea el desplegable

        # --- MENÚ AYUDA (Para que no salgan solo botones sueltos) ---
        menu_ayuda = tk.Menu(menubar, tearoff=0)
        menu_ayuda.add_command(label="Acerca de")
        menu_ayuda.add_command(label="Ayuda")
        menubar.add_cascade(label="Ayuda", menu=menu_ayuda) # Esto agrupa Acerca de y Ayuda

        self.config(menu=menubar)

    def build_tabs(self):
        style = ttk.Style()
        # Esto forzará automáticamente a VistaDiseno, VistaVoladuras y HomeTab a usar el fondo gris ejecutivo
        style.configure("TFrame", background="#f5f6fa")
        # 2. Cambia el fondo de la pestaña activa e inactivas
        style.configure("TNotebook.Tab", background="#dcdde1", foreground="#2c3e50", padding=[10, 4])
        style.map("TNotebook.Tab", background=[("selected", "#f5f6fa")], foreground=[("selected", "#2c3e50")])

        style.configure("TFrame", background="#f5f6fa")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Le pasamos self.datos (o el nombre de tu objeto conector de base de datos)
        self.tab_home = HomeTab(self.notebook)
        self.notebook.add(self.tab_home, text="Home")

        self.tab_voladuras = VistaVoladuras(self.notebook)
        self.notebook.add(self.tab_voladuras, text="Voladuras")

        self.tab_diseno = VistaDiseno(self.notebook)
        self.notebook.add(self.tab_diseno, text="Diseño")

        # Pestañas en blanco
        #tabs_restantes = ["Vibraciones", "Fragmentación", "Retardos", "Reportes"]
        #for tab_name in tabs_restantes:
        #    frame = ttk.Frame(self.notebook)
        #    self.notebook.add(frame, text=tab_name)

        # --- SOLUCIÓN AQUÍ ---
        # Detectar cuando se cambia de pestaña
        self.notebook.bind("<<NotebookTabChanged>>", self.forzar_redibujado)
    
    def forzar_redibujado(self, event):
        """Fuerza a Tkinter a procesar la cola de tareas visuales y repintar la pantalla."""
        self.update_idletasks()

    def cerrar_aplicacion_limpio(self):
        try:
            # 1. Apagamos Matplotlib para liberar los hilos de la campana de Gauss
            import matplotlib.pyplot as plt
            plt.close('all')
        except Exception:
            pass
            
        try:
            # 2. Si tu objeto de base de datos tiene un método para cerrar conexión, lo llamamos
            if hasattr(self, "datos") and hasattr(self.datos, "conexion"):
                self.datos.conexion.close()
                print("🗄️ Conexión a MySQL liberada.")
        except Exception:
            pass

        # 3. Destruimos la interfaz y forzamos la salida del sistema operativo
        self.destroy()
        import sys
        sys.exit(0) # 👈 Esto le avisa a macOS que limpie el proceso de la terminal por completo el proceso de Python


if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()