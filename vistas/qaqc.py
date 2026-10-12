# vistas/panel_qaqc.py
import tkinter as tk
from tkinter import ttk, messagebox
from vistas.vod import VistaVOD
from vistas.densidad import VistaDensidad
from vistas.vibraciones import VistaVibraciones
import database.datos_db as datos

class qaqc(tk.Toplevel):

    def __init__(self, parent, id_vola, proyecto,database, callback_actualizar=None):
        super().__init__(parent)
        self.id_vola = id_vola
        self.proyecto = proyecto
        self.database= database
        self.datos_mysql = datos.obtener_datos_mysql()
        # Obtener el ancho y alto de la pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # obtener taladros
        self.taladros_completos = datos.obtener_taladros_por_proyecto(id_vola)

        # Guardamos el callback en la memoria de la ventana qaqc
        self.callback_actualizar = callback_actualizar
        
        # Aplicar la geometría (Ancho x Alto + Posición X + Posición Y)
        self.geometry(f"{screen_width}x{screen_height}+0+0")
        
        self.title(f"Panel QA/QC - Proyecto: {self.proyecto}")
        #self.geometry("900x700")  # Más ancho para acomodar formularios y tablas
       
        self.grab_set()
        
        self.setup_ui()

    def setup_ui(self):
        # 1. Encabezado informativo
        #header = tk.Frame(self, bg="#002060", pady=10)
        #header.pack(fill="x")
        #tk.Label(header, text=f"GESTIÓN TÉCNICA - ID VOLADURA: {self.id_vola}", 
        #         fg="white", bg="#002060", font=("Arial", 12, "bold")).pack()

        # 2. Creación del Notebook (Tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # 3. Definición de las Pestañas
        self.tab_vod = VistaVOD(self.notebook,self.id_vola,self.proyecto,self.database,datos,self.taladros_completos, self.callback_actualizar)
        self.tab_sismo = VistaVibraciones(self.notebook,self.id_vola,self.proyecto,self.database,datos,self.callback_actualizar)
        self.tab_densidad = VistaDensidad(self.notebook,self.id_vola,self.proyecto,self.database,datos,self.taladros_completos,self.callback_actualizar)
        self.tab_taladros = tk.Frame(self.notebook)
        self.tab_frag = tk.Frame(self.notebook)
        self.tab_horario = tk.Frame(self.notebook)

        # 4. Agregar pestañas al Notebook
        self.notebook.add(self.tab_vod, text=" 📈 VOD ")
        self.notebook.add(self.tab_sismo, text=" 📳 Vibraciones ")
        self.notebook.add(self.tab_densidad, text=" ⚖️ Densidades ")
        self.notebook.add(self.tab_taladros, text=" 📏 Taladros ")
        self.notebook.add(self.tab_frag, text=" 📸 Fragmentación ")
        self.notebook.add(self.tab_horario, text=" ⏰ Horario ")

        # 5. Inicializar el contenido de cada pestaña
        #self.init_tab_vod()
        #self.init_tab_sismo()
        #self.init_tab_frag()
        # Puedes ir agregando los init para las demás pestañas...

         # Detectar cuando se cambia de pestaña
        self.notebook.bind("<<NotebookTabChanged>>", self.forzar_redibujado)

    # --- DISEÑO DE CADA PESTAÑA ---

    def forzar_redibujado(self, event):
        """Fuerza a Tkinter a procesar la cola de tareas visuales y repintar la pantalla."""
        self.update_idletasks()

    def init_tab_vod(self):
        self.tab_vod = VistaVOD(self.notebook,self.id_vola,self.proyecto,self.database)
        #"""Aquí va el formulario VOD que vimos en la captura"""
        #tk.Label(self.tab_vod, text="Registro de Velocidad de Detonación", font=("Arial", 11, "bold")).pack(pady=10)
        # Aquí puedes meter el código del formulario que ya tenemos
        # Ejemplo: tk.Entry(self.tab_vod)...

    def init_tab_sismo(self):
        """Interfaz para carga de datos THOR"""
        tk.Label(self.tab_sismo, text="Análisis de Sismografía (Instantel THOR)", font=("Arial", 11, "bold")).pack(pady=10)
        btn_importar = tk.Button(self.tab_sismo, text="Importar CSV de THOR", 
                                 bg="#ED7D31", fg="white", command=self.importar_sismo_click)
        btn_importar.pack(pady=20)

    def init_tab_frag(self):
        """Interfaz para fotos y resultados D50/D80"""
        tk.Label(self.tab_frag, text="Análisis de Fragmentación", font=("Arial", 11, "bold")).pack(pady=10)
        # Botón para subir foto
        btn_foto = tk.Button(self.tab_frag, text="Vincular Foto de Fragmentación", command=self.subir_foto_click)
        btn_foto.pack(pady=10)

    # --- LÓGICA DE BOTONES ---

    def importar_sismo_click(self):
        from database.voladuras_db import cargar_todo_el_csv_thor
        # Lógica de filedialog...
        messagebox.showinfo("Procesando", f"Cargando serie de tiempo para voladura {self.id_vola}")

    def subir_foto_click(self):
        # Lógica de filedialog y guardado por ruta...
        pass