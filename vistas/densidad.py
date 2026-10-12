import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import Calendar
from database.datos_db import obtener_taladros
from tkinter import filedialog, messagebox, ttk
from fpdf import FPDF
from PIL import Image, ImageEnhance
import matplotlib.patheffects as path_effects
from matplotlib.ticker import FormatStrFormatter
import os
from database.datos_db import marcar_medicion_completada,obtener_kpi_por_explosivo
import numpy as np

class VistaDensidad(tk.Frame):
    def __init__(self, parent, id_vola, proyecto, database, datos,taladros, callback_actualizar=None):
        super().__init__(parent)
        self.contador=0
        self.id_vola = id_vola
        self.proyecto = proyecto
        self.database = database
        self.datos= datos
        self.datos_mysql = datos.obtener_datos_mysql()
        self.root = parent
        self.callback_actualizar = callback_actualizar # Lo guardas

        # 1. Recibimos el SÚPER DICCIONARIO de taladros
        self.datos_taladros_completos = obtener_taladros(self.id_vola)
        #print(len(self.datos_taladros_completos))
        #print(len(taladros))
        #self.datos_taladros_completos = taladros
        
        # 1. Cargamos los taladros de esta voladura desde la BD
        self.lista_taladros = list(self.datos_taladros_completos.keys()) # Lista de strings ej: ["1", "2", "3A", "4B"]
        
        # Guardamos la lista completa de camiones
        self.todos_los_camiones = list(self.datos_mysql.get("camion_fabrica", {}).keys())

        # Datos de Rioflex
        self.datos_proporciones_mezcla = {
            "50/50":"0.50",
            "70/30":"0.7",
            "100/0":"1"
        }

        self.datos_proporciones_diesel = {
            "30/ANFO":"0.18",
            "50/ANFO":"0.3"
        }

        self.datos_densidad_prill = {
            "porous_prill":"1.3",
            "high_density_prill":"1.48"
        }

        #print(self.datos_mysql.get("camion_fabrica", {}))
        self.camiones_data = []
        self.setup_ui()
        self.cargar_datos_guardados()

        #self.curva_profundidad(4,[])

        self.verificar_rioflex()

    def setup_ui(self):
        # --- ESTILO TIPO EXCEL PARA LAS TABLAS ---
        style = ttk.Style()
        # El tema 'clam' es el único que nos deja manipular bien los bordes
        style.theme_use("clam")
        
        # Configuramos las celdas
        style.configure("Treeview", 
                        background="white",
                        fieldbackground="white",
                        rowheight=25,
                        bordercolor="#5f5f5f", # Color de línea gris
                        lightcolor="#b0b0b0",
                        darkcolor="#b0b0b0",
                        borderwidth=1)
        
        # Configuramos los encabezados (Gris como en Excel)
        style.configure("Treeview.Heading",
                        background="#e0e0e0",
                        font=('Arial', 9, 'bold'),
                        bordercolor="#b0b0b0",
                        borderwidth=1)
                        
        style.map('Treeview', background=[('selected', "#0256af")]) # Selección azul claro

        left_panel = tk.Frame(self, width=320, bg="#f1f2f6")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        right_panel = tk.Frame(self, bg="white")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ==========================================
        # PANEL IZQUIERDO: DATOS BÁSICOS
        # ==========================================
        group_generales = tk.LabelFrame(left_panel, text="1. DATOS INICIALES", font=('Arial', 11, 'bold'), padx=10, pady=10)
        group_generales.pack(fill=tk.X, pady=5)

        self.inputs = {}
        fields_generales = [
            ("Controlado por:", "id_persona", list(self.datos_mysql.get("persona", {}).keys())),
            ("Fecha:", "fecha", ""),
            ("Hora Inicio:", "hora_inicio", datetime.now().strftime("%H:%M")),
            ("Hora Fin:", "hora_fin", datetime.now().strftime("%H:%M")),
            ("Diámetro (mm):", "diametro", "311"),
            ("Explosivo:", "id_explosivo", list(self.datos_mysql.get("explosivo",{}).keys())),
            ("Tipo de Taco:", "tipo_taco", ["DETRITUS","GRAVILLA"])
        ]

        for i, (label, key, opciones) in enumerate(fields_generales):
            tk.Label(group_generales, text=label, font=('Arial', 11)).grid(row=i, column=0, sticky="w", pady=4)
            if key in ["id_persona","id_explosivo","tipo_taco"]:
                ent = ttk.Combobox(group_generales, values=opciones, state="readonly", width=18)
                if opciones: ent.set(opciones[0])
            elif key == "fecha":
                frame_fecha = tk.Frame(group_generales)
                ent = tk.Entry(frame_fecha, width=12, justify='center')
                ent.insert(0, datetime.now().strftime("%d-%m-%Y"))
                ent.pack(side=tk.LEFT)

                # ... (Lógica del calendario omitida por brevedad, asume la misma que ya tenías)
                frame_fecha.grid(row=i, column=1, pady=4, sticky="w")
                self.inputs[key] = ent

                # --- FUNCIÓN CORREGIDA ---
                def elegir_fecha(e=ent):
                    # Usamos winfo_toplevel() para asegurar que dependa del PanelQAQC
                    top = tk.Toplevel(self.winfo_toplevel())
                    top.title("Seleccionar Fecha")
                    
                    cal = Calendar(top, selectmode='day', date_pattern='dd-mm-yyyy')
                    cal.pack(padx=10, pady=10)

                    def set_date():
                        e.delete(0, tk.END)
                        e.insert(0, cal.get_date())
                        top.destroy()

                    tk.Button(top, text="Seleccionar", command=set_date).pack(pady=5)

                    # --- LA SOLUCIÓN ---
                    top.transient(self.winfo_toplevel()) # Obliga al calendario a estar siempre encima
                    top.grab_set()                   # Le roba los clics al panel de atrás
                    top.focus_set()                      # Le da el foco del teclado
                    top.wait_window()                    # Pausa hasta que el usuario cierre el calendario
                
                btn_cal = ttk.Button(frame_fecha, text="📅", width=2, command=elegir_fecha)
                btn_cal.pack(side="left", padx=2)
                
                continue
            
            # 👇 NUEVO: Interceptamos el diámetro para volverlo reactivo
            elif key == "diametro":
                # Creamos la variable y le damos el valor por defecto ("311" o el que venga en opciones)
                self.var_diametro = tk.StringVar(value=str(opciones))
                
                # Le conectamos el rastreador de cambios
                self.var_diametro.trace_add("write", self.al_cambiar_diametro)
                
                # Creamos el Entry pero lo atamos a nuestra nueva variable
                ent = tk.Entry(group_generales, width=21, justify='center', textvariable=self.var_diametro)
            else:
                ent = tk.Entry(group_generales, width=21, justify='center')
                if isinstance(opciones, str): ent.insert(0, opciones)
            ent.grid(row=i, column=1, pady=4, padx=5, sticky="w")

            self.inputs[key] = ent

    
        # Scroll Canvas
        canvas = tk.Canvas(right_panel, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="white")
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- TIPO DE EXPLOSIVO (Filtro de Camiones) ---
        group_tipo = tk.LabelFrame(left_panel, text="TIPO DE EXPLOSIVO", font=('Arial', 11, 'bold'), padx=10, pady=5, fg="#e67e22")
        group_tipo.pack(fill=tk.X, pady=10)

        self.tipo_explosivo_izq = tk.StringVar(value="ANFO")
        #print(tipo)
        self.radio_anfo = ttk.Radiobutton(group_tipo, text="ANFO", variable=self.tipo_explosivo_izq,command=self.cargar_datos_guardados, value="ANFO").pack(side=tk.LEFT, padx=10)
        self.radio_rioflex= ttk.Radiobutton(group_tipo, text="RIOFLEX", variable=self.tipo_explosivo_izq,command=self.cargar_datos_guardados, value="RIOFLEX").pack(side=tk.LEFT, padx=10)

        self.dia_seleccionado = tk.StringVar(value="DIA 1") # <-- NUEVA VARIABLE
        group_dia = tk.LabelFrame(left_panel, text="DÍA DE CARGUIO", font=('Arial', 11, 'bold'), padx=10, pady=5, fg="#e67e22")
        group_dia.pack(fill=tk.X, pady=10)
        # --- Fila 2: Selección de Día (LO NUEVO) ---
        #ttk.Separator(group_dia, orient="horizontal").pack(fill="x", pady=5)
        #ttk.Label(group_dia, text="Seleccione el Día de Carga:", font=("Arial", 9, "bold")).pack(anchor="w")

        dias = ["DIA 1", "DIA 2", "DIA 3", "DIA 4"]
        for dia in dias:
            ttk.Radiobutton(
                group_dia,
                text=dia, 
                variable=self.dia_seleccionado, 
                value=dia,
                command=self.cargar_datos_guardados # <-- Gatilla recarga al cambiar de día
            ).pack(side="left", padx=5)

        self.contenedor_rioflex = tk.Frame(left_panel)
        self.contenedor_rioflex.pack(fill=tk.X)

        self.marco_rioflex = tk.LabelFrame(self.contenedor_rioflex, text="PARÁMETROS RIOFLEX", font=('Arial', 11, 'bold'), padx=10, pady=5, fg="#2980b9")
        
        # 1. Columna de Agua
        tk.Label(self.marco_rioflex, text="Columna de Agua (m):", font=("Arial", 11)).grid(row=0, column=0, sticky="w", pady=(5, 0))
        self.inputs["columna_de_agua"] = ttk.Entry(self.marco_rioflex, font=("Arial", 11))
        self.inputs["columna_de_agua"].grid(row=1, column=0, sticky="ew", pady=(0, 5))

         # 2. Longitud de Carga
        tk.Label(self.marco_rioflex, text="Longitud Carga (m):", font=("Arial", 11)).grid(row=2, column=0, sticky="w", pady=(5, 0))
        self.inputs["longitud_carga"] = ttk.Entry(self.marco_rioflex, font=("Arial", 11))
        self.inputs["longitud_carga"].grid(row=3, column=0, sticky="ew", pady=(0, 5))

        # 3. Densidad Teórica
        tk.Label(self.marco_rioflex, text="Densidad Teórica (g/cc):", font=("Arial", 11)).grid(row=4, column=0, sticky="w")
        self.inputs["densidad_teorica"] = ttk.Entry(self.marco_rioflex, font=("Arial", 11))
        self.inputs["densidad_teorica"].grid(row=5, column=0, sticky="ew", pady=(0, 5))
        self.inputs["densidad_teorica"].insert(0, "1.42")

        # 4. Densidad Final
        tk.Label(self.marco_rioflex, text="Densidad Final (g/cc):", font=("Arial", 11)).grid(row=6, column=0, sticky="w")
        self.inputs["densidad_final"] = ttk.Entry(self.marco_rioflex, font=("Arial", 11))
        self.inputs["densidad_final"].grid(row=7, column=0, sticky="ew", pady=(0, 5))

        # 4. Longitud de Taco
        tk.Label(self.marco_rioflex, text="Taco (m):", font=("Arial", 11)).grid(row=8, column=0, sticky="w")
        self.inputs["taco"] = ttk.Entry(self.marco_rioflex, font=("Arial", 11))
        self.inputs["taco"].grid(row=9, column=0, sticky="ew", pady=(0, 5))

        self.marco_rioflex.columnconfigure(0, weight=1)

        # Conectamos un 'espía' a la variable del Radiobutton
        self.tipo_explosivo_izq.trace_add("write", self.verificar_rioflex)


        # Botones Generales
        frame_botones = tk.Frame(left_panel, bg="#f1f2f6")
        frame_botones.pack(fill=tk.X, pady=10)

        # Botón GUARDAR (Verde, grande y llamativo)
        tk.Button(frame_botones, text="💾 GUARDAR TODO", command=self.guardar_datos, 
                  bg="#27ae60", fg="white", font=('Arial', 11, 'bold'), height=2).pack(fill=tk.X, pady=3)
        
        #tk.Button(frame_botones, text="GENERAR PDF", command=self.generar_pdf, bg="white", font=('Arial', 11, 'bold'), height=2).pack(fill=tk.X)

        tk.Button(frame_botones, text="GENERAR PDF", command=self.crear_pdf, 
                bg="white", fg="black", font=('Arial', 11, 'bold'), height=2).pack(fill=tk.X, pady=3)
        
        # Filtramos inicialmente para que los camiones coincidan con ANFO
        #self.actualizar_columnas_tablas()
        #self.filtrar_camiones()

    def crear_pdf(self):
        if self.tipo_explosivo_izq.get() =="RIOFLEX":
            self.create_pdf_rioflex()
        else:
            self.create_pdf_anfo()

    def verificar_rioflex(self, *args):
        """Oculta o muestra dinámicamente los parámetros de Rioflex"""
        if self.tipo_explosivo_izq.get() == "RIOFLEX":
            # Lo mostramos dentro del contenedor que reservamos
            self.marco_rioflex.pack(fill=tk.X, pady=5)
        else:
            # Lo ocultamos
            self.marco_rioflex.pack_forget()

    def crear_bloque_camion(self, index):
        frame_camion = tk.LabelFrame(self.scrollable_frame, text=f"UNIDAD FÁBRICA {index + 1}", font=('Arial', 11, 'bold'), bg="white", fg="#2980b9", padx=10, pady=10)
        frame_camion.pack(fill=tk.X, pady=2, padx=10)

        header_frame = tk.Frame(frame_camion, bg="white")
        header_frame.pack(fill=tk.X, pady=5)

        var_habilitado = tk.BooleanVar(value=(index == 0))
        chk_habilitar = tk.Checkbutton(header_frame, text="Habilitar", variable=var_habilitado, font=('Arial', 10, 'bold'), bg="white", command=lambda idx=index: self.toggle_estado_camion(idx))
        chk_habilitar.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(header_frame, text="Camión:", bg="white").pack(side=tk.LEFT)
        combo_camion = ttk.Combobox(header_frame, state="readonly", width=15)
        combo_camion.pack(side=tk.LEFT, padx=5)

        # La Tabla
        tree_frame = tk.Frame(frame_camion)
        tree_frame.pack(fill=tk.X, pady=5)

        tipo_exp = self.tipo_explosivo_izq.get()

        if tipo_exp == "ANFO":
            columnas = ("n_muestra", "taladro", "altura_diesel", "peso1", "peso2", "peso3", "p_diesel", "p_na", "error", "desviacion", "densidad")
        else:
            columnas = ("n_muestra", "taladro", "hora_muestra", "peso_bruto", "peso_vaso", "temperatura", "ph","densidad")

        tree = ttk.Treeview(tree_frame, show='headings', height=6,columns=columnas)
        tree.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- CONFIGURACIÓN DE ANCHOS Y TÍTULOS ---
        tree.heading("#0", text="", anchor="w")
        tree.column("#0", width=0, stretch=tk.NO)

        if tipo_exp == "ANFO":
            tree.column("n_muestra", width=40, anchor='center', stretch=tk.NO)
            tree.column("taladro", width=80, anchor='center', stretch=tk.NO)
            tree.column("altura_diesel", width=90, anchor='center', stretch=tk.NO)
            tree.column("peso1", width=70, anchor='center', stretch=tk.NO)
            tree.column("peso2", width=70, anchor='center', stretch=tk.NO)
            tree.column("peso3", width=70, anchor='center', stretch=tk.NO)
            tree.column("p_diesel", width=80, anchor='center', stretch=tk.NO)
            tree.column("p_na", width=80, anchor='center', stretch=tk.NO)
            tree.column("error", width=80, anchor='center', stretch=tk.NO)
            tree.column("desviacion", width=90, anchor='center', stretch=tk.NO)
            tree.column("densidad", width=90, anchor='center', stretch=tk.NO)
            
            tree.heading("n_muestra", text="N°")
            tree.heading("taladro", text="Taladro")
            tree.heading("altura_diesel", text="Alt. Diesel")
            tree.heading("peso1", text="Peso 1")
            tree.heading("peso2", text="Peso 2")
            tree.heading("peso3", text="Peso 3")
            tree.heading("p_diesel", text="% Diesel")
            tree.heading("p_na", text="% NA")
            tree.heading("error", text="Error")
            tree.heading("desviacion", text="Desviación")
            tree.heading("densidad", text="Dens(g/cc)")
        else:
            tree.column("n_muestra", width=40, anchor='center', stretch=tk.NO)
            tree.column("taladro", width=100, anchor='center', stretch=tk.NO)
            tree.column("hora_muestra", width=100, anchor='center', stretch=tk.NO)
            tree.column("peso_bruto", width=90, anchor='center', stretch=tk.NO)
            tree.column("peso_vaso", width=90, anchor='center', stretch=tk.NO)
            tree.column("temperatura", width=90, anchor='center', stretch=tk.NO)
            tree.column("ph", width=80, anchor='center', stretch=tk.NO)
            tree.column("densidad", width=80, anchor='center', stretch=tk.NO)
            
            tree.heading("n_muestra", text="N°")
            tree.heading("taladro", text="Taladro")
            tree.heading("hora_muestra", text="Hora")
            tree.heading("peso_bruto", text="Peso Bruto")
            tree.heading("peso_vaso", text="Peso Vaso")
            tree.heading("temperatura", text="Temper.")
            tree.heading("ph", text="Ph")
            tree.heading("densidad", text="Dens(g/cc)")

        # --- MAGIA: HACER LA TABLA EDITABLE ---
        tree.bind("<ButtonRelease-1>", lambda event, idx=index: self.on_single_click(event, idx))

        # Botones Inferiores por Camión
        btn_frame = tk.Frame(frame_camion, bg="white")
        btn_frame.pack(fill=tk.X, pady=2)
        
        btn_add = ttk.Button(btn_frame, text="➕ Muestra", command=lambda idx=index: self.agregar_fila(idx))
        btn_add.pack(side=tk.LEFT, padx=5)
        
        btn_del = ttk.Button(btn_frame, text="➖ Eliminar", command=lambda idx=index: self.eliminar_fila(idx))
        btn_del.pack(side=tk.LEFT, padx=5)

        # 👇 NUEVO: Creamos la etiqueta de la Carga Lineal (en la zona roja)
        lbl_carga = tk.Label(header_frame, text="Carga Lineal: -- kg/m", font=('Arial', 12, 'bold'), bg="white", fg="#244400")
        lbl_carga.pack(side=tk.LEFT, padx=30)

        self.camiones_data.append({
            "frame": frame_camion, 
            "var_habilitado": var_habilitado, 
            "combo_camion": combo_camion,
            "tree": tree,
            "btn_add": btn_add, 
            "btn_del": btn_del,
            "lbl_carga": lbl_carga
        })
       
        self.toggle_estado_camion(index)

    def filtrar_camiones(self):
        """Filtra los camiones de los combobox según el radiobutton de la izquierda"""
        
        tipo_global = self.tipo_explosivo_izq.get()
        
        # 1. Creamos una lista vacía donde iremos metiendo los nombres válidos
        camiones_filtrados = [] 

        # 2. Llenamos la lista según el tipo global seleccionado
        if tipo_global == 'ANFO':
            for key, dato in self.datos_mysql.get("camion_fabrica", {}).items():
                if dato.get('funcion') == 'ANFO' or dato.get('funcion') == 'MIXTO':
                    camiones_filtrados.append(key) # Guardamos el camión en la lista
        else: # Si no es ANFO, lógicamente es RIOFLEX
            for key, dato in self.datos_mysql.get("camion_fabrica", {}).items():
                if dato.get('funcion') == 'RIOFLEX' or dato.get('funcion') == 'MIXTO':
                    camiones_filtrados.append(key) # Guardamos el camión en la lista
        
        # Por seguridad: Si no encontró ninguno, ponemos un aviso
        if not camiones_filtrados:
            camiones_filtrados = ["(No hay camiones)"]

        # 3. Actualizamos la interfaz
        for data in self.camiones_data:
            data["combo_camion"]['values'] = camiones_filtrados
            
            if camiones_filtrados:
                data["combo_camion"].set(camiones_filtrados[0]) 
            
            # nuevo_tipo_tabla = "ANFO" if tipo_global == "ANFO" else "MIXTO"
            #data["combo_tipo"].set(nuevo_tipo_tabla)
            
            #idx = self.camiones_data.index(data)
            #self.actualizar_encabezados(idx)
    
    def al_cambiar_diametro(self, *args):
        """Se ejecuta automáticamente cada vez que el usuario teclea algo en el input de Diámetro."""
        # Recorremos los 3 bloques de camiones y forzamos la actualización de su texto rojo
        for idx in range(len(self.camiones_data)):
            self.actualizar_carga_lineal(idx)

    def toggle_estado_camion(self, index):
        """Activa o desactiva visualmente los controles de un bloque de camión"""
        datos = self.camiones_data[index]
        esta_habilitado = datos["var_habilitado"].get()
        
        # Definimos los estados según el checkbox
        estado_btn = tk.NORMAL if esta_habilitado else tk.DISABLED
        estado_combo = "readonly" if esta_habilitado else tk.DISABLED
        
        # Aplicamos los estados a los controles
        datos["combo_camion"].config(state=estado_combo)
        
        # Verificamos que los botones existan en el diccionario antes de cambiarlos
        if "btn_add" in datos: datos["btn_add"].config(state=estado_btn)
        if "btn_remove" in datos: datos["btn_remove"].config(state=estado_btn)

    # ==========================================
    def on_single_click(self, event, index):
        tree = self.camiones_data[index]["tree"]
        region = tree.identify("region", event.x, event.y)
        if region != "cell": return

        item = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        col_idx = int(column.replace('#', '')) - 1
        col_name = tree["columns"][col_idx]

        # No permitimos editar el N° de muestra ni los campos calculados automáticamente
        if col_name in ["n_muestra", "p_diesel", "p_na", "error", "desviacion", "densidad"]: 
            return # Bloquea la edición

        x, y, w, h = tree.bbox(item, column)
        valor_actual = tree.set(item, column)

        # --- MAGIA DEL EDITOR ---
        if col_name == "taladro":
            valores_combo = self.lista_taladros if self.lista_taladros else ["(Sin taladros)"]
            editor = ttk.Combobox(tree, values=valores_combo)
            editor.set(valor_actual)

            #print(valor_actual)
            
            # 1. Filtro dinámico al escribir
            def al_escribir(e):
                # Ignoramos teclas de navegación para que puedas usar las flechas y Enter sin problemas
                if e.keysym in ('Up', 'Down', 'Left', 'Right', 'Return', 'Escape', 'Tab'):
                    return
                
                escrito = editor.get().lower()
                if escrito == '':
                    editor['values'] = self.lista_taladros
                else:
                    # Filtra buscando coincidencias en cualquier parte del nombre del taladro
                    editor['values'] = [t for t in self.lista_taladros if escrito in str(t).lower()]
                
                # Despliega la lista actualizada
                editor.tk.eval(f'ttk::combobox::Post {editor}')
                
            editor.bind('<KeyRelease>', al_escribir)
            
            # 2. Confirmar inmediatamente al hacer clic en un elemento de la lista
            editor.bind("<<ComboboxSelected>>", lambda e: confirmar_edicion())
            
        else:
            # ESTILO EXCEL para celdas normales
            editor = tk.Entry(tree, justify='center', relief='solid', bd=1, highlightthickness=1, highlightcolor="#217346")
            editor.insert(0, valor_actual)
            editor.select_range(0, tk.END) 

        # Colocamos el editor exactamente sobre la celda
        editor.place(x=x, y=y, width=w, height=h)
        editor.focus_set()

        # Abrimos la lista automáticamente al hacer el primer clic (Para Mac)
        #if col_name == "taladro":
        #    tree.after(100, lambda: editor.tk.eval(f'ttk::combobox::Post {editor}'))

        # --- FUNCIÓN DE GUARDADO MEJORADA ---
        def confirmar_edicion(e=None):
            try:
                nuevo_valor = editor.get()
                tree.set(item, column, nuevo_valor)
                editor.destroy()
                
                print(f"✅ Celda guardada. Llamando a recalcular_fila para el item: {item}")
                self.recalcular_fila(tree, item) 
                
            except Exception as ex:
                # Si hay CUALQUIER error, lo imprimirá en la consola en letras grandes
                print(f"🚨 ERROR EN CONFIRMAR EDICION O RECALCULAR: {ex}")

        # Guardado por teclado (Enter) o al hacer clic fuera (FocusOut)
        editor.bind("<Return>", confirmar_edicion)
        editor.bind("<FocusOut>", confirmar_edicion)

    def recalcular_fila(self, tree, item):
        """Calcula automáticamente el Diesel, NA y la Densidad según las fórmulas de campo."""
        valores = list(tree.item(item, "values"))
        
        # Función auxiliar para extraer números sin que el programa colapse si hay texto o vacíos
        def obtener_numero(texto):
            try:
                return float(str(texto).strip())
            except ValueError:
                return None
            
        if self.tipo_explosivo_izq.get() == "ANFO":
            # Extraemos los datos tipeados por el operador
            altura = obtener_numero(valores[2])
            peso1 = obtener_numero(valores[3])
            peso2 = obtener_numero(valores[4])
            peso3 = obtener_numero(valores[5])

            # ==========================================
            if altura is not None:
                # (8.1 - 3) / (4 - 1.45) da exactamente 2.0
                p_diesel = (2.0 * (altura - 1.45)) + 3.0
                p_na = 100.0 - p_diesel
                
                # Guardamos redondeado a 2 decimales
                valores[6] = f"{p_diesel:.2f}"
                valores[7] = f"{p_na:.2f}"
            else:
                valores[6] = " "
                valores[7] = " "

            # ==========================================
            # 2. CÁLCULO DE DENSIDAD, ERROR Y DESVIACIÓN
            # Fórmula Densidad = peso (gr) / 400 (cm3)
            # ==========================================
            # Recolectamos solo los pesos que el operador ya escribió
            pesos_ingresados = [p for p in [peso1, peso2, peso3] if p is not None]
            
            if len(pesos_ingresados) > 0:
                # Primero promediamos los pesos ingresados (así sean 1, 2 o los 3)
                peso_promedio = sum(pesos_ingresados) / len(pesos_ingresados)
                
                # Calculamos la densidad final
                densidad_actual = peso_promedio / 400.0
                
                # Guardamos en la columna 10 (Densidad)
                if densidad_actual != 0 or densidad_actual != None:
                    valores[10] = f"{densidad_actual:.2f}"

                    

                     # --- ERROR Y DESVIACIÓN ---
                    # Define aquí tu Densidad Promedio o Teórica para la comparación
                    #densidad_teorica = 0.80 
                    
                    # Fórmulas exactas solicitadas
                    #error = densidad_actual - densidad_teorica
                    #desviacion = error ** 2
                    
                    #valores[8] = f"{error:.4f}"
                    #valores[9] = f"{desviacion:.6f}"
                else:
                    valores[10] = 0
                    valores[8] = 0
                    valores[9] = 0
            else:
                valores[8] = " "
                valores[9] = " "
                valores[10] = " "

        else:
            # --- LÓGICA RIOFLEX (NUEVA) ---
            # En Rioflex, los índices son: [3] Peso Bruto, [4] Peso Vaso, [5] Densidad
            peso_bruto = obtener_numero(valores[3])
            peso_vaso = obtener_numero(valores[4])
            
            if peso_bruto is not None and peso_vaso is not None:
                # 👇 CAMBIA ESTE 1000 POR EL VOLUMEN DEL VASO QUE USEN EN MINA
                volumen_vaso = 1246.0 
                densidad_rioflex = (peso_bruto - peso_vaso) / volumen_vaso
                
                # Guardamos la densidad calculada en la columna 5
                valores[7] = f"{densidad_rioflex:.3f}"
            else:
                valores[7] = " "

        # Finalmente, inyectamos los nuevos valores calculados de vuelta en la tabla
        tree.item(item, values=valores)

        # 👇 NUEVO: Buscar a qué camión pertenece esta tabla y actualizar su cabecera
        for idx, data in enumerate(self.camiones_data):
            if data["tree"] == tree:
                self.actualizar_carga_lineal(idx)
                break

    def agregar_fila(self, index):
        tree = self.camiones_data[index]["tree"]
        n_actual = len(tree.get_children()) + 1
        
        # 1. Configuramos los colores de las cajas (celdas)
        tree.tag_configure("impar", background="#f2f2f2", foreground="black") # Gris clarito
        tree.tag_configure("par", background="#ffffff", foreground="black")   # Blanco puro
        tree.tag_configure("seleccionado", background="#005cbf")              # Azul al seleccionar
        
        # 2. Determinamos qué color le toca a esta nueva fila
        etiqueta_color = "impar" if n_actual % 2 != 0 else "par"
        
        # 3. Llenamos con espacios " " para que las celdas tengan volumen y aplicamos el color
        # Ahora son 11 valores en total (El número + 10 espacios)
        tree.insert("", "end", values=(str(n_actual), " ", " ", " ", " ", " ", " ", " ", " ", " ", " "), tags=(etiqueta_color,))

    def eliminar_fila(self, index):
        tree = self.camiones_data[index]["tree"]
        seleccionado = tree.selection()
        if seleccionado: tree.delete(seleccionado)

    def guardar_unidad(self, index):
        """Guarda la información específica de la tabla a la que se le hizo clic"""
        datos = self.camiones_data[index]
        camion = datos["combo_camion"].get()
        tipo = datos["combo_tipo"].get()
        
        # Extraer datos de la tabla
        muestras = []
        for item in datos["tree"].get_children():
            valores = datos["tree"].item(item, 'values')
            if valores[1]: # Solo guarda filas donde hayan puesto un N° de Taladro
                muestras.append(valores)
        
        if not muestras:
            messagebox.showwarning("Aviso", f"La tabla del camión {camion} está vacía o sin taladros.")
            return

        #print(f"Guardando {len(muestras)} muestras para {camion} ({tipo})...")
        messagebox.showinfo("AXON", f"Datos del {camion} listos para MySQL.\n(Implementar lógica procesar_guardado_densidad)")

    def generar_pdf(self):
        messagebox.showinfo("PDF", "Generación de PDF en construcción.")

    def actualizar_carga_lineal(self, index):
        """Calcula la Carga Lineal promedio y muestra diagnósticos en consola."""
        import math
        
       # print(f"\n--- INICIANDO CÁLCULO DE CARGA LINEAL (Camión {index}) ---")
        
        # Extraemos los widgets
        datos = self.camiones_data[index]
        tree = datos["tree"]
        lbl_carga = datos["lbl_carga"]

        # 1. Verificar si está habilitado
        if not datos["var_habilitado"].get():
            #print("❌ El camión está deshabilitado. Cancelando cálculo.")
            lbl_carga.config(text="")
            return
        
        tipo_exp = self.tipo_explosivo_izq.get()
        # En ANFO la densidad es la columna 10. En RIOFLEX es la columna 5.
        indice_densidad = 10 if tipo_exp == "ANFO" else 7

        # 2. Recolectar las densidades de la tabla
        densidades = []
        for item in tree.get_children():
            valores = tree.item(item, "values")
            try:
                # Buscamos en el índice exacto que calculamos arriba
                den = float(str(valores[indice_densidad]).strip()) 
                densidades.append(den)
            except (ValueError, IndexError):
                pass # Ignora las filas vacías o con texto inválido

        # Si aún no hay densidades calculadas, mostramos las rayitas
        if not densidades:
            lbl_carga.config(text="Carga Lineal: -- kg/m")
            return

        densidad_promedio = sum(densidades) / len(densidades)
        #print(f"📈 Densidad promedio calculada: {densidad_promedio:.4f}")

        # 3. OBTENER EL DIÁMETRO
        try:
            # Protegemos por si self.var_diametro aún no existe en memoria
            if not hasattr(self, 'var_diametro'):
                #print("🚨 ERROR: self.var_diametro no existe. Revisa el loop de fields_generales.")
                lbl_carga.config(text="Carga Lineal: Error de sistema")
                return

            diametro_texto = self.var_diametro.get().strip()
            #print(f"📏 Texto leído en el input de diámetro: '{diametro_texto}'")
            
            diametro_mm = float(diametro_texto)
            
        except ValueError:
            #print("🚨 ERROR: El valor del diámetro no es un número válido.")
            lbl_carga.config(text="Carga Lineal: Error de diámetro")
            return

        if diametro_mm <= 0:
            #print("🚨 ERROR: El diámetro es cero o negativo.")
            lbl_carga.config(text="Carga Lineal: Diámetro inválido")
            return

        # 4. LA FÓRMULA MATEMÁTICA
        carga_lineal = ((math.pi * ((diametro_mm / 1000) ** 2)) / 4 * 1000) * densidad_promedio
        #print(f"✅ Resultado final de Carga Lineal: {carga_lineal:.2f} kg/m")

        # 5. Mostrar en pantalla
        lbl_carga.config(text=f"Carga Lineal: {carga_lineal:.2f} kg/m")
        #print("--------------------------------------------------\n")

    def parse_float(val):
        v = str(val).strip()
        return float(v) if v else None

    def guardar_datos(self):
        # 1. TRAEMOS LOS DICCIONARIOS DE MYSQL
        diccionario_camiones = self.datos_mysql.get("camion_fabrica", {})
        diccionario_personas = self.datos_mysql.get("persona", {})     
        diccionario_explosivos = self.datos_mysql.get("explosivo", {})
        
        # ==========================================
        # 2. EXTRAER DATOS DIRECTO DE TU INTERFAZ
        # ==========================================
        nombre_persona = self.inputs["id_persona"].get().strip()
        nombre_explosivo = self.inputs["id_explosivo"].get().strip()
        
        fecha_pantalla = self.inputs["fecha"].get()
        hora_inicio_pantalla = self.inputs["hora_inicio"].get()
        hora_fin_pantalla = self.inputs["hora_fin"].get()
        diametro_pantalla = self.var_diametro.get().strip()
        
       # PERSONA
        data_persona = diccionario_personas.get(nombre_persona)
        id_persona = data_persona.get("id") if isinstance(data_persona, dict) else data_persona
        
        # EXPLOSIVO
        data_explosivo = diccionario_explosivos.get(nombre_explosivo)
        id_explosivo = data_explosivo.get("idexplosivo") if isinstance(data_explosivo, dict) else data_explosivo

        # DIA DE CARGUIO
        dia_carga = self.dia_seleccionado.get()
            
        # 👇 NUEVO: Validación estricta (is None) para que no confunda un ID '0' con un error
        if id_persona is None or id_explosivo is None:
            messagebox.showwarning("Atención", "Seleccione un usuario y un tipo de explosivo válido.")
            return

        # ==========================================
        # 3. GUARDAR CAMIONES
        # ==========================================
        camiones_ids_a_guardar = []
        for data in self.camiones_data:
            if data["var_habilitado"].get():
                nombre_camion = data["combo_camion"].get()
                if nombre_camion in diccionario_camiones: 
                    camiones_ids_a_guardar.append(diccionario_camiones[nombre_camion]["id"])

        camiones_ids_a_guardar = list(set(camiones_ids_a_guardar))

        if not camiones_ids_a_guardar:
            messagebox.showwarning("Atención", "No hay ningún camión habilitado.")
            return
        
        tipo_exp_seleccionado = self.tipo_explosivo_izq.get()

        col_agua = float(self.inputs["columna_de_agua"].get() or 0.0)
        den_teo = float(self.inputs["densidad_teorica"].get() or 0.0)
        den_fin = float(self.inputs["densidad_final"].get() or 0.0)
        long_carga = float(self.inputs["longitud_carga"].get() or 0.0)
        tipo_taco = self.inputs["tipo_taco"].get().strip()
        taco = self.inputs["taco"].get().strip()

        id_densidad_maestra = self.datos.gestionar_densidad_voladura(
            self.id_vola, 
            tipo_exp_seleccionado,
            id_explosivo,
            fecha_pantalla,
            hora_inicio_pantalla,
            hora_fin_pantalla,
            diametro_pantalla,
            id_persona,
            col_agua,
            den_teo,
            den_fin,
            long_carga,
            tipo_taco,
            taco,
            dia_carga
        )

        if not id_densidad_maestra:
            messagebox.showerror("Error", "No se pudo generar el registro maestro de la voladura.")
            return
        
        # ==========================================
        # 4. EXTRAER FILAS E INYECTAR TODO A MYSQL
        # ==========================================
        muestras_a_guardar = []
        for data in self.camiones_data:
            if data["var_habilitado"].get():
                nombre_camion = data["combo_camion"].get()
                
                if nombre_camion in diccionario_camiones: 
                    id_camion = diccionario_camiones[nombre_camion]["id"]

                    tree = data["tree"]
                    for item in tree.get_children():
                        valores = tree.item(item, "values")

                        tala = valores[1]

                        if not tala:
                            tala = "0"
                        else:
                            tala = str(valores[1]).strip()

                        # Si la fila no tiene un taladro asignado, la ignoramos (fila en blanco)
                        #if not str(valores[1]).strip():
                        #    continue

                        try:
                            if tipo_exp_seleccionado == "ANFO":
                                print(valores)
                                densidad = float(str(valores[10]).strip())

                                # 👇 2. NUEVO: Extraemos y limpiamos los 3 pesos
                                peso_1 = str(valores[3]).strip()
                                peso_2 = str(valores[4]).strip()
                                peso_3 = str(valores[5]).strip()

                                # Juntamos solo los pesos que el usuario realmente escribió (ignoramos los vacíos)
                                pesos_ingresados = [p for p in [peso_1, peso_2, peso_3] if p]
                                
                                # Los unimos con una barra o guion (Ejemplo: "4.5 / 4.6 / 4.5")
                                pesos_combinados = " / ".join(pesos_ingresados)
                                
                                fila = (     
                                    id_camion,          # <-- ID DIRECTO DEL CAMIÓN
                                    tala, 
                                    str(valores[2]).strip(), 
                                    pesos_combinados,        
                                    densidad,
                                    id_densidad_maestra
                                )
                                muestras_a_guardar.append(fila)
                            else:
                                # --- LÓGICA DE EXTRACCIÓN RIOFLEX ---
                                # Función segura para números vacíos (evita que MySQL explote)
                                def parse_float(val):
                                    v = str(val).strip()
                                    return float(v) if v else None

                                p_bruto = parse_float(valores[3])
                                p_vaso = parse_float(valores[4])
                                temp = parse_float(valores[5])
                                ph_val = parse_float(valores[6])
                                densidad = parse_float(valores[7])

                                # El orden exacto que requiere la base de datos de Rioflex
                                fila = ( 
                                    id_camion, 
                                    p_bruto,                 # peso_bruto
                                    p_vaso,                  # peso_vaso
                                    str(valores[2]).strip(), # hora_muestra
                                    temp,                    # temperatura
                                    ph_val,                  # ph
                                    tala, # taladro
                                    densidad,
                                    id_densidad_maestra         
                                )
                                muestras_a_guardar.append(fila)

                        except (ValueError, IndexError):
                            pass

        # ==========================================
        # 5. GUARDADO FINAL Y ACTUALIZACIÓN
        # ==========================================
        # Enviamos las muestras a su tabla correspondiente
        exito = False
        
        if tipo_exp_seleccionado == "ANFO":
            exito = self.datos.guardar_muestras_densidad(id_densidad_maestra, muestras_a_guardar)
        else:
            exito = self.datos.guardar_muestras_rioflex(id_densidad_maestra, muestras_a_guardar)

        if not exito:
            messagebox.showerror("Error", "Error al guardar el detalle de las densidades.")
            return

        from database.datos_db import marcar_medicion_completada
        marcar_medicion_completada(self.id_vola, "densidad")

        if self.callback_actualizar:
            #self.callback_actualizar()
            messagebox.showinfo("Éxito", f"Densidades de {tipo_exp_seleccionado} guardadas correctamente.")
            self.focus_force()

    def cargar_datos_guardados(self):

        """Carga la cabecera, adapta la UI, extrae las muestras y las agrupa por camión."""
        # Usamos la nueva función para traer la cabecera
        cabecera = self.datos.obtener_cabecera_densidad(self.id_vola,self.tipo_explosivo_izq.get(),self.dia_seleccionado.get())

        #print("TIPO SELECCIONADO 1:... ",self.tipo_explosivo_izq.get()," - ",self.contador," - ",cabecera)
        self.contador=self.contador+1

        if not cabecera:
            # Voladura virgen: Forzamos ANFO y terminamos.
            #self.tipo_explosivo_izq.set("ANFO")
            self.actualizar_columnas_tablas()
            #return
        
        #print("TIPO SELECCIONADO 2:... ",self.tipo_explosivo_izq.get())
        
        if self.contador ==0:
            # Adaptar interfaz al tipo guardado (Con sanitización para evitar errores por espacios)
            tipo_cargado = str(cabecera.get('tipo') or "ANFO").strip().upper()
            self.tipo_explosivo_izq.set(tipo_cargado)
            #tipo_cargado = "ANFO"
            self.actualizar_columnas_tablas()
        else:
            if self.tipo_explosivo_izq.get()=="ANFO":
                tipo_cargado ="ANFO"
                self.actualizar_columnas_tablas()
            else:
                tipo_cargado ="RIOFLEX"
                self.actualizar_columnas_tablas()

        if cabecera:
            # Rellenar Persona (desde la cabecera)
            diccionario_personas = self.datos_mysql.get("persona", {})    
            mapa_personas = { str(d.get("id") if isinstance(d, dict) else d).strip(): nombre for nombre, d in diccionario_personas.items() }

            id_per_db = str(cabecera.get('id_persona') or "").strip()
            nombre_per = mapa_personas.get(id_per_db, "")

            if nombre_per: 
                self.inputs["id_persona"].set(nombre_per)

            # Rellenar Horas (desde la cabecera)
            self.inputs["fecha"].delete(0, 'end')
            self.inputs["fecha"].insert(0, cabecera.get('fecha') or "")

            self.inputs["hora_inicio"].delete(0, 'end')
            self.inputs["hora_inicio"].insert(0, cabecera.get('hora_inicio') or "")
            
            self.inputs["hora_fin"].delete(0, 'end')
            self.inputs["hora_fin"].insert(0, cabecera.get('hora_fin') or "")

            # 1. Columna de Agua
            self.inputs["columna_de_agua"].delete(0, 'end')
            if cabecera.get('columna_de_agua') is not None:
                self.inputs["columna_de_agua"].insert(0, cabecera.get('columna_de_agua'))
            else:
                self.inputs["columna_de_agua"].insert(0, "0.0")

            # 2. Densidad Teórica
            self.inputs["densidad_teorica"].delete(0, 'end')
            if cabecera.get('densidad_teorica') is not None:
                self.inputs["densidad_teorica"].insert(0, cabecera.get('densidad_teorica'))
            else:
                self.inputs["densidad_teorica"].insert(0, "1.39")

            # 3. Densidad Final
            self.inputs["densidad_final"].delete(0, 'end')
            if cabecera.get('densidad_final') is not None:
                self.inputs["densidad_final"].insert(0, cabecera.get('densidad_final'))
            else:
                self.inputs["densidad_final"].insert(0, "1.10")

            
            # 3. Longitud Carga
            self.inputs["longitud_carga"].delete(0, 'end')
            if cabecera.get('longitud_carga') is not None:
                self.inputs["longitud_carga"].insert(0, cabecera.get('longitud_carga'))
            else:
                self.inputs["longitud_carga"].insert(0, "5")

            # 4. Tipo Taco
            #self.inputs["tipo_taco"].delete(0, 'end')
            if cabecera.get('tipo_taco') is not None:
                self.inputs["tipo_taco"].set(cabecera.get('tipo_taco'))
            else:
                self.inputs["tipo_taco"].set("DETRITUS")

             # 5. Taco
            self.inputs["taco"].delete(0, 'end')
            if cabecera.get('taco') is not None:
                self.inputs["taco"].insert(0, cabecera.get('taco'))
            else:
                self.inputs["taco"].insert(0, "5")

            # ==========================================
            # 2. TRAER MUESTRAS DETALLE
            # ==========================================
            
            if tipo_cargado == "ANFO":
                registros = self.datos.obtener_densidades_guardadas(self.id_vola,self.dia_seleccionado.get())
            else:
                registros = self.datos.obtener_densidades_rioflex_guardadas(self.id_vola,self.dia_seleccionado.get())

            if not registros:
                return

            # Rellenar el Tipo de Explosivo (Lo sacamos de la primera fila de la tabla de muestras)
            diccionario_explosivos = self.datos_mysql.get("explosivo", {})
            mapa_explosivos = { str(d.get("idexplosivo", d.get("id")) if isinstance(d, dict) else d).strip(): nombre for nombre, d in diccionario_explosivos.items() }
            
            id_exp_db = str(cabecera.get('id_explosivo') or "").strip()
            nombre_exp = mapa_explosivos.get(id_exp_db, "")

            if nombre_exp: 
                self.inputs["id_explosivo"].set(nombre_exp)

            # ==========================================
            # 3. AGRUPAR MUESTRAS POR CAMIÓN
            # ==========================================
            datos_por_camion = {}
            for r in registros:
                # Usamos el id_camion directo (y agregamos la compatibilidad por si se llama id_camion_voladura)
                id_cam = r.get('id_camion')
                if not id_cam: continue

                if id_cam not in datos_por_camion:
                    datos_por_camion[id_cam] = []
                
                if r.get('taladro') is not None: 
                    datos_por_camion[id_cam].append(r)

            # ==========================================
            # 4. LLENAR LAS TABLAS SEGÚN EL TIPO
            # ==========================================
            diccionario_camiones = self.datos_mysql.get("camion_fabrica", {})
            mapa_camiones = { d["id"]: nombre for nombre, d in diccionario_camiones.items() }
            
            def seguro(val): return "" if val is None else str(val)

            camiones_disponibles_bd = list(datos_por_camion.keys())
            
            for i, id_camion_bd in enumerate(camiones_disponibles_bd):
                if i < len(self.camiones_data): 
                    data_ui = self.camiones_data[i]
        
                    # Encendemos el bloque visual y seleccionamos el camión
                    data_ui["var_habilitado"].set(True)
                    data_ui["combo_camion"].set(mapa_camiones.get(id_camion_bd, ""))
                    
                    if hasattr(self, 'toggle_estado_camion'):
                        self.toggle_estado_camion(i) 

                    tree = data_ui["tree"]
                    for item in tree.get_children():
                        tree.delete(item)
                        
                    for idx, fila_bd in enumerate(datos_por_camion[id_camion_bd], start=1):
                        
                        if tipo_cargado == "ANFO":
                            pesos_str = seguro(fila_bd.get('peso'))
                            pesos_lista = [p.strip() for p in pesos_str.split("/") if p.strip()]
                            p1 = pesos_lista[0] if len(pesos_lista) > 0 else ""
                            p2 = pesos_lista[1] if len(pesos_lista) > 1 else ""
                            p3 = pesos_lista[2] if len(pesos_lista) > 2 else ""

                            valores_insertar = (
                                idx,
                                seguro(fila_bd.get('taladro')),
                                seguro(fila_bd.get('altura')),
                                p1, p2, p3,
                                "", "", "", "",
                                seguro(fila_bd.get('densidad_real'))
                            )
                        else: 
                            valores_insertar = (
                                idx,
                                seguro(fila_bd.get('taladro')),
                                seguro(fila_bd.get('hora_muestra')),
                                seguro(fila_bd.get('peso_bruto')),
                                seguro(fila_bd.get('peso_vaso')),
                                seguro(fila_bd.get('temperatura')), 
                                seguro(fila_bd.get('ph')),
                                seguro(fila_bd.get('densidad'))
                            )
                        
                        item_id = tree.insert("", "end", values=valores_insertar)

                        # 5. FORZAR CÁLCULOS PARA AMBOS (ANFO Y RIOFLEX)
                        try:
                            self.recalcular_fila(tree, item_id)
                        except TypeError:
                            self.recalcular_fila(event=None, tree=tree, item_id=item_id)
            
            # Rellenar Diámetro (desde la cabecera)
            diametro_guardado = cabecera.get('diametro')
            if diametro_guardado and hasattr(self, 'var_diametro'):
                self.var_diametro.set(str(diametro_guardado))
        
    def actualizar_columnas_tablas(self):
        """Cambia las columnas, mantiene proporciones y usa un espaciador para no romper el diseño."""
        tipo_exp = self.tipo_explosivo_izq.get()

        # 1. DESTRUIR LOS PANELES VIEJOS VISUALMENTE
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # 2. VACIAR LA MEMORIA
        if len(self.camiones_data)>0:
            self.camiones_data.clear()

        # 3. CREAR LOS PANELES NUEVOS
        if tipo_exp == "ANFO":
            for i in range(3):
                self.crear_bloque_camion(i)
        else: # RIOFLEX
            for i in range(2): # Lo dejé en 3 para RIOFLEX también, cámbialo a 2 si solo usas dos
                self.crear_bloque_camion(i)
                
        # Refrescamos los camiones disponibles en los selectores
        self.filtrar_camiones()

    def agregar_fondo(self,pdf):
        ancho_carta = 215.9
        alto_carta = 279.4
        # Colocamos la imagen en (0,0) cubriendo toda la hoja
        pdf.image("logo_fondo_1.png", x=0, y=0, w=ancho_carta, h=alto_carta)
    
    def preparar_fondo(self,ruta_original, brillo=1.5, contraste=0.5):
        img = Image.open(ruta_original)
        
        # Ajustar Brillo (1.0 es original, >1.0 es más claro)
        enhancer_brillo = ImageEnhance.Brightness(img)
        img = enhancer_brillo.enhance(brillo)
        
        # Ajustar Contraste (0.5 hace que se vea más tenue/gris)
        enhancer_con = ImageEnhance.Contrast(img)
        img = enhancer_con.enhance(contraste)
        
        img.save("logo_fondo_1.png")

    def create_pdf_anfo(self):
        
        ancho_px = 195
        pdf = FPDF(format='Letter')

        #pdf.set_auto_page_break(0,)

        dias_carguios = self.datos.obtener_cantidad_dias_carguio(self.id_vola,"ANFO")

        #print(dias_carguios)

        for i in range(len(dias_carguios)):

            id = dias_carguios[i]["id"]
            dia_carga = dias_carguios[i]["dia_carga"]
            diametro = float(dias_carguios[i]["diametro"])
            id_persona = dias_carguios[i]["id_persona"] # FALTA ESTE
            fecha = dias_carguios[i]["fecha"]
            hora_inicio = dias_carguios[i]["hora_inicio"]
            hora_fin = dias_carguios[i]["hora_fin"]
            id_explosivo = dias_carguios[i]["id_explosivo"]

            datos_anfo = self.datos.obtener_densidades_guardadas(self.id_vola,dia_carga) or []
        
            diccionario_personas = self.datos_mysql.get("persona", {})
            invertido = {id: nombre for nombre, id in diccionario_personas.items()}
            info_persona = invertido.get(id_persona)
                
            # 🟢 LLAMAS A LA FUNCIÓN MÁGICA
            print("datos anfo por dia :",datos_anfo)
            resumen_camiones = self.obtener_resumen_anfo_por_camion(datos_anfo,diametro)
            
            # Extraemos los datos de la interfaz de forma segura
            val_persona = str(info_persona)
            val_fecha = str(fecha)
            val_h_inicio = str(hora_inicio)
            val_h_fin = str(hora_fin)
            val_diametro = f"{diametro} mm"

            pdf.set_margins(10,2,10)
            
            self.preparar_fondo("./recursos/logo_fondo.png", 1.8, 0.9) # Lo hacemos muy tenue

            pdf.add_page()

            #pdf.set_auto_page_break(False, margin=0)

            pdf.ln(0)

            self.agregar_fondo(pdf)

            pdf.set_font("Arial", 'B', 10)

            ROJO = (229, 46, 43)   # #E52E2B
            GRIS = (100, 101, 103)  # #646567
            GRIS_CLARO= (236, 236, 236)  # #646567
            BLANCO = (255, 255, 255)
            
            # Asegúrate de tener el archivo 'logo_delion.png' en la carpeta del script
            try:
                pdf.image("./recursos/logo.png", x=12, y=5.5, w=35)
            except:
                pdf.cell(40, 12, "LOGO DELION", 1, 0, 'C') # Celda vacía si no halla imagen
            else:
                pdf.cell(40, 12, "", 1, 0, 'C') # Celda con borde para el logo
            
            pdf.cell(105, 12, "CONTROL DE DENSIDAD DE ANFO", 1, 0, 'C')
            pdf.set_font("Arial", '', 7)
            pdf.multi_cell(50, 4, "REC.BOL.ST.MSC.001.1\nRev.: 05\nFecha de Aprob.: 05-04-2021", 1, 'L')
            
            #--------------------------------
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(*ROJO) # Gris muy claro de fondo
            pdf.set_text_color(*BLANCO)
            pdf.set_line_width(0.0)
            pdf.cell(ancho_px, 7, "1. DATOS GENERALES", 0, 0, 'L', fill=True)
            pdf.ln(8)

            pdf.set_text_color(0,0,0)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(ancho_px*0.15, 8, f"Controlado por:", 0,0,'L')
            pdf.set_font("Arial", '', 9)
            pdf.cell(ancho_px*0.19, 8,val_persona, 0,0,'L')

            pdf.set_font("Arial", 'B', 9)
            pdf.cell(ancho_px*0.32, 8, f"Firma:", 0,0,'L')
            pdf.cell(ancho_px*0.12, 8, f"Fecha y Hora:", 0,0,'L')
            pdf.set_font("Arial", '', 9)
            fecha_hora =  self.obtener_fecha_formateada(val_fecha,val_h_inicio)
            pdf.cell(ancho_px*0.18, 8, fecha_hora, 0,0,'L')

            pdf.ln(8)

            pdf.set_text_color(0,0,0)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(ancho_px*0.15, 7, "N° Voladura:", 0,0,'L')
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(ancho_px*0.19, 7,self.proyecto, 0,0,'L')

            pdf.set_font("Arial", 'B', 9)
            pdf.cell(ancho_px*0.12, 7, f"Diámetro :", 0,0,'L')
            pdf.set_font("Arial", '', 9)
            pdf.cell(ancho_px*0.18, 7, val_diametro, 0,0,'L')

            #--------------------------------
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(*BLANCO)
            pdf.cell(ancho_px, 7, "2. RESULTADOS OBTENIDOS", 0, 0, 'L',fill=True)
            
            pdf.ln(5)
            
            id_explosivo_actual = "ANFO"

            pos_x = 10
            pos_y = pdf.get_y() + 5
                
            # Nuevas medidas calculadas para 3 columnas
            ancho_imagen = 60  
            salto_horizontal = 65 # 60 de imagen + 5 de separación
            salto_vertical = 110  # Altura proporcional de la imagen
            fontsize=14

            # 🟢 NUEVA LÓGICA: Condicionar según la cantidad de camiones
            if len(resumen_camiones) == 1:
                #print("entro aqui el reporte .....")
                # ---> UN SOLO CAMIÓN: DASHBOARD HORIZONTAL PANORÁMICO <---
                res = resumen_camiones[0]
                ruta_dashboard = self.generar_dashboard_horizontal_camion(res, id_explosivo_actual,fontsize,dia_carga)
                
                if ruta_dashboard and os.path.exists(ruta_dashboard):
                    # Lo centramos en la hoja ocupando casi todo el ancho (w=180)
                    pdf.image(ruta_dashboard, x=15, y=pos_y+5, w=180)
                    pos_y -= 10  # Saltamos solo la altura de este dashboard horizontal
                
                pos_y = pdf.get_y() + 90
            else:
                # ---> MÚLTIPLES CAMIONES: DASHBOARDS VERTICALES EN 3 COLUMNAS <---
                for i, res in enumerate(resumen_camiones):
                    #print ()
                    ruta_dashboard = self.generar_dashboard_vertical_camion(res,i, id_explosivo_actual,fontsize,dia_carga)
                    
                    if ruta_dashboard and os.path.exists(ruta_dashboard):
                        pdf.image(ruta_dashboard, x=pos_x, y=pos_y, w=ancho_imagen)
                        
                        pos_x += salto_horizontal
                        
                        if (i + 1) % 3 == 0:
                            pos_x = 10             
                            pos_y += salto_vertical 
                            
                            if pos_y > 250:
                                pdf.add_page()
                                pos_y = 20 
                
                #if len(resumen_camiones) % 3 != 0:
                #    pos_y += salto_vertical
                
                pos_y = pdf.get_y() + 95

            # Traemos los datos crudos que contienen cada taladro individual
            datos_crudos_anfo = self.datos.obtener_densidades_guardadas(self.id_vola,dia_carga) or []

            # 🟢 CORRECCIÓN: Le pasamos los datos crudos, NO el resumen
            ruta_mapa = self.generar_mapa_global_camiones(datos_crudos_anfo, self.datos_taladros_completos,dia_carga)

            if ruta_mapa and os.path.exists(ruta_mapa):
                # Pegar el mapa centrado (ancho 180mm)
                pdf.image(ruta_mapa, x=10, y=pos_y+10, w=190,h=95)
            
            pdf.set_y(pos_y + 102)
            pdf.set_text_color(0,0,0)

            pdf.ln(5)
            pdf.set_font("Arial", 'I', 9)
            pdf.set_text_color(0,0,0)
            pdf.cell(70, 5, "Verificado por: ______________________", 0, 0, 'L')
            pdf.cell(50, 5, "Firma : ________________", 0, 0, 'L')

        pdf.set_auto_page_break(True, margin=5)

        #nro_vola = self.inputs_generales['nro_voladura'].get()
        nombre_sugerido = f"Reporte_MEDICION_ANFO_{self.proyecto}.pdf"

        # 2. Abrimos la ventana del explorador de archivos
        ruta_guardado = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=nombre_sugerido,
            title="Guardar Reporte PDF",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
        )

        # 3. Verificamos si el usuario eligió una ruta (o si le dio a Cancelar)
        if ruta_guardado:
            try:
                pdf.output(ruta_guardado)
                messagebox.showinfo("Reporte Exitoso", f"El reporte fue generado y guardado en:\n{ruta_guardado}")
            except Exception as e:
                # Por si el archivo está abierto y Windows/Mac no deja sobreescribirlo
                messagebox.showerror("Error", f"No se pudo guardar el archivo. Asegúrese de que no esté abierto en otro programa.\n\nDetalle: {e}")

    def create_pdf_rioflex(self):
        
        ancho_px = 195
        pdf = FPDF(format='Letter')

        #pdf.set_auto_page_break(auto=True, margin=15)

        dias_carguios = self.datos.obtener_cantidad_dias_carguio(self.id_vola,"RIOFLEX")

        for i in range(len(dias_carguios)):

            id = dias_carguios[i]["id"]
            dia_carga = dias_carguios[i]["dia_carga"]
            diametro = float(dias_carguios[i]["diametro"])
            id_persona = dias_carguios[i]["id_persona"] # FALTA ESTE
            fecha = dias_carguios[i]["fecha"]
            hora_inicio = dias_carguios[i]["hora_inicio"]
            hora_fin = dias_carguios[i]["hora_fin"]
            id_explosivo = dias_carguios[i]["id_explosivo"]

            datos_riolfex = self.datos.obtener_densidades_rioflex_guardadas(self.id_vola,dia_carga) or []

            diccionario_personas = self.datos_mysql.get("persona", {})
            invertido = {id: nombre for nombre, id in diccionario_personas.items()}
            info_persona = invertido.get(id_persona)

            resumen_camiones = self.obtener_resumen_rioflex_por_camion(datos_riolfex, diametro)

            # Extraemos los datos de la interfaz de forma segura
            val_persona = str(info_persona)
            val_fecha = str(fecha)
            val_h_inicio = str(hora_inicio)
            val_h_fin = str(hora_fin)
            val_diametro = f"{diametro} mm"

            pdf.set_margins(10,2,10)

            self.preparar_fondo("./recursos/logo_fondo.png", 1.8, 0.9) # Lo hacemos muy tenue

            pdf.add_page()
            pdf.ln(0)

            self.agregar_fondo(pdf)

            pdf.set_font("Arial", 'B', 10)

            ROJO = (229, 46, 43)   # #E52E2B
            GRIS = (100, 101, 103)  # #646567
            GRIS_CLARO= (236, 236, 236)  # #646567
            BLANCO = (255, 255, 255)
            
            # Asegúrate de tener el archivo 'logo_delion.png' en la carpeta del script
            try:
                pdf.image("./recursos/logo.png", x=12, y=5.5, w=35)
            except:
                pdf.cell(40, 12, "LOGO DELION", 1, 0, 'C') # Celda vacía si no halla imagen
            else:
                pdf.cell(40, 12, "", 1, 0, 'C') # Celda con borde para el logo
            
            pdf.cell(105, 12, "CONTROL DE DENSIDAD DE RIOFLEX", 1, 0, 'C')
            pdf.set_font("Arial", '', 7)
            pdf.multi_cell(50, 4, "REC.BOL.ST.MSC.001.1\nRev.: 05\nFecha de Aprob.: 05-04-2021", 1, 'L')
            
            #--------------------------------
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(*ROJO) # Gris muy claro de fondo
            pdf.set_text_color(*BLANCO)
            pdf.set_line_width(0.0)
            pdf.cell(ancho_px, 7, "1. DATOS GENERALES", 0, 0, 'L', fill=True)
            pdf.ln(8)

            pdf.set_text_color(0,0,0)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(ancho_px*0.15, 8, f"Controlado por:", 0,0,'L')
            pdf.set_font("Arial", '', 9)
            pdf.cell(ancho_px*0.19, 8,val_persona, 0,0,'L')

            pdf.set_font("Arial", 'B', 9)
            pdf.cell(ancho_px*0.32, 8, f"Firma:", 0,0,'L')
            pdf.cell(ancho_px*0.12, 8, f"Fecha y Hora:", 0,0,'L')
            pdf.set_font("Arial", '', 9)
            fecha_hora =  self.obtener_fecha_formateada(val_fecha,val_h_inicio)
            pdf.cell(ancho_px*0.18, 8, fecha_hora, 0,0,'L')

            pdf.ln(8)

            pdf.set_text_color(0,0,0)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(ancho_px*0.15, 7, "N° Voladura:", 0,0,'L')
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(ancho_px*0.19, 7,self.proyecto, 0,0,'L')

            pdf.set_font("Arial", 'B', 9)
            pdf.cell(ancho_px*0.12, 7, f"Diámetro :", 0,0,'L')
            pdf.set_font("Arial", '', 9)
            pdf.cell(ancho_px*0.18, 7, val_diametro, 0,0,'L')

            #--------------------------------
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(*BLANCO)
            pdf.cell(ancho_px, 7, "2. RESULTADOS OBTENIDOS", 0, 0, 'L',fill=True)
            
            pdf.ln(5)

            # Buscamos el taladro en el diccionario completo
            #self.explosivos = self.datos_mysql.get("explosivo",{}).get(id_explosivo)
            #id_explosivo_actual = self.datos_taladros_completos.get(self.inputs["id_explosivo"].get())
            
            #print("EXPLOSIVOS: ",self.explosivos)

            #id_explosivo_actual = self.explosivos['idexplosivo']

            pos_x = 10
            pos_y = pdf.get_y() + 2
                
            # Nuevas medidas calculadas para 3 columnas
            ancho_imagen = 60  
            salto_horizontal = 65 # 60 de imagen + 5 de separación
            salto_vertical = 110  # Altura proporcional de la imagen


            # 🟢 NUEVA LÓGICA: Condicionar según la cantidad de camiones
            if len(resumen_camiones) == 1:
                # ---> UN SOLO CAMIÓN: DASHBOARD HORIZONTAL PANORÁMICO <---
                res = resumen_camiones[0]
                ruta_dashboard = self.generar_dashboard_horizontal_camion_rioflex(res, id_explosivo,dia_carga)
                
                if ruta_dashboard and os.path.exists(ruta_dashboard):
                    # Lo centramos en la hoja ocupando casi todo el ancho (w=180)
                    pdf.image(ruta_dashboard, x=15, y=pos_y+3, w=180)
                    pos_y -= 10  # Saltamos solo la altura de este dashboard horizontal
            else:
                # ---> MÚLTIPLES CAMIONES: DASHBOARDS VERTICALES EN 3 COLUMNAS <---
                datos_grupo = []

                for i, res in enumerate(resumen_camiones):
                    nombre = res.get('nombre_camion', 'N/A').upper()
                    
                    # Desempaquetamos de forma segura lo que retorna tu curva_profundidad
                    datos_prof = self.curva_profundidad(id_explosivo)

                    densidades_x = datos_prof['densidad']
                    profundidades_y = datos_prof['longitud']

                    try:
                        longitud_carga = float(self.inputs["longitud_carga"].get() or 0.0)
                    except (ValueError, KeyError):
                        longitud_carga = 0.0

                    densidad_punto_interp = np.interp(longitud_carga, profundidades_y, densidades_x)

                    # 🟢 CAMBIO 2: Creamos un diccionario individual exclusivo para ESTE camión
                    item_camion = {
                        "nombre_camion": nombre,
                        "longitud": profundidades_y,
                        "densidad": densidades_x,
                        "interop": densidad_punto_interp
                    }
                    # Lo añadimos a la lista grupal
                    datos_grupo.append(item_camion)
                    
                    # Pegamos el dashboard estadístico del camión actual
                    ruta_dashboard = self.generar_dashboard_vertical_camion_rioflex(res, i, id_explosivo,dia_carga)
                    if ruta_dashboard and os.path.exists(ruta_dashboard):
                        pdf.image(ruta_dashboard, x=pos_x, y=pos_y+4, w=ancho_imagen)
                        
                        pos_x += salto_horizontal
                        
                        if (i + 1) % 3 == 0:
                            pos_x = 10             
                            pos_y += salto_vertical 
                            
                            if pos_y > 250:
                                pdf.add_page()
                                pos_y = 20

                #print("datos_grupo: ",datos_grupo)

                ruta_prof = self.generar_dashboard_vertical_profundidad_rioflex(id_explosivo, datos_grupo)
                
                if ruta_prof and os.path.exists(ruta_prof):
                    # Si las 3 columnas de camiones llenaron la fila, verificamos si necesitamos bajar de fila
                    if pos_x == 10:
                        pass 
                    
                    # Pegamos la gráfica del perfil de profundidad en la posición disponible en la grilla
                    pdf.image(ruta_prof, x=pos_x, y=pos_y, w=ancho_imagen)
                    pos_x += salto_horizontal
                
                #if len(resumen_camiones) % 3 != 0:
                #    pos_y += salto_vertical

            # Traemos los datos crudos que contienen cada taladro individual
            datos_crudos = self.datos.obtener_densidades_rioflex_guardadas(self.id_vola,dia_carga) or []

            #print("DIA:", dia_)

            # 🟢 CORRECCIÓN: Le pasamos los datos crudos, NO el resumen
            ruta_prof = self.generar_mapa_global_camiones_rioflex(datos_crudos, self.datos_taladros_completos,dia_carga)

            if ruta_prof and os.path.exists(ruta_prof):
                pos_y = pdf.get_y() + 85
                # Pegar el mapa centrado (ancho 180mm)
                pdf.image(ruta_prof, x=10, y=pos_y, w=190,h=100)
            
            pdf.set_y(pos_y + 105)
            pdf.set_text_color(0,0,0)

            pdf.ln(8)
            pdf.set_font("Arial", 'I', 9)
            pdf.set_text_color(0,0,0)
            pdf.cell(70, 5, "Verificado por: ______________________", 0, 0, 'L')
            pdf.cell(50, 5, "Firma : ________________", 0, 0, 'L')

        #pdf.set_auto_page_break(True, margin=20)

        #nro_vola = self.inputs_generales['nro_voladura'].get()
        nombre_sugerido = f"Reporte_MEDICION_RIOFLEX_{self.proyecto}.pdf"

        # 2. Abrimos la ventana del explorador de archivos
        ruta_guardado = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=nombre_sugerido,
            title="Guardar Reporte PDF",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
        )

        # 3. Verificamos si el usuario eligió una ruta (o si le dio a Cancelar)
        if ruta_guardado:
            try:
                pdf.output(ruta_guardado)
                messagebox.showinfo("Reporte Exitoso", f"El reporte fue generado y guardado en:\n{ruta_guardado}")
            except Exception as e:
                # Por si el archivo está abierto y Windows/Mac no deja sobreescribirlo
                messagebox.showerror("Error", f"No se pudo guardar el archivo. Asegúrese de que no esté abierto en otro programa.\n\nDetalle: {e}")

    def obtener_fecha_formateada(self, fecha_cruda, hora_cruda):
        """
        Recibe una fecha ('2026-04-16') y una hora ('18:09:00')
        y devuelve un string amigable ('16 de abril del 2026 - 18:09').
        """
        # 1. Limpieza de datos (evita errores si viene nulo o con espacios)
        fecha = str(fecha_cruda).strip() if fecha_cruda else ""
        hora = str(hora_cruda).strip() if hora_cruda else ""
        
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", 
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        # 2. Transformar la Fecha
        fecha_formateada = fecha
        try:
            if "-" in fecha:
                partes = fecha.split("-")
                # Verificamos si empieza por el año (AAAA-MM-DD) o por el día (DD-MM-AAAA)
                if len(partes[0]) == 4:
                    anio, mes, dia = partes[0], int(partes[1]), partes[2]
                else:
                    dia, mes, anio = partes[0], int(partes[1]), partes[2]
                
                fecha_formateada = f"{dia} de {meses[mes]} del {anio}"
        except Exception:
            pass # Si falla, devuelve la fecha tal como entró

        # 3. Transformar la Hora
        hora_formateada = hora
        try:
            if ":" in hora:
                partes_hora = hora.split(":")
                hora_formateada = f"{partes_hora[0]}:{partes_hora[1]}"
        except Exception:
            pass

        if fecha_formateada and hora_formateada:  # <--- CORREGIDO
            return f"{fecha_formateada} - {hora_formateada}"
        elif fecha_formateada:
            return fecha_formateada
        elif hora_formateada:
            return hora_formateada
        else:
            return ""

    def obtener_resumen_anfo_por_camion(self, datos_anfo, diametro_mm):
        import math
        resumen_matematico = {}
        
        # 1. Obtener el diccionario para traducir ID a Nombre del Camión
        diccionario_camiones = self.datos_mysql.get("camion_fabrica", {})
        mapa_camiones = { str(d["id"]): nombre for nombre, d in diccionario_camiones.items() }

        # 2. Agrupar y sumar los datos crudos
        for fila in datos_anfo:
            id_cam = str(fila.get('id_camion'))
            if not id_cam or id_cam == "None": 
                continue
            
            if id_cam not in resumen_matematico:
                resumen_matematico[id_cam] = {
                    'nombre_camion': mapa_camiones.get(id_cam, f"ID {id_cam}"),
                    'taladros': 0, 
                    'sum_den': 0.0, 
                    'sum_diesel': 0.0, 
                    'count_diesel': 0,
                    'sum_error':0,
                    'sum_desv':0
                }
            
            resumen_matematico[id_cam]['taladros'] += 1
            
            # Sumar Densidad
            try:
                den = float(str(fila.get('densidad_real', 0)).strip())
                resumen_matematico[id_cam]['sum_den'] += den
            except (ValueError, TypeError): 
                pass
            
            # Sumar Diesel y Nitrato usando la fórmula de calibración de altura
            try:
                alt = float(str(fila.get('altura', 0)).strip())
                # Fórmula de calibración que tienes en tu código:
                p_diesel = (2.0 * (alt - 1.45)) + 3.0 
                resumen_matematico[id_cam]['sum_diesel'] += p_diesel
                resumen_matematico[id_cam]['count_diesel'] += 1
            except (ValueError, TypeError): 
                pass

        # 3. Calcular Promedios y Carga Lineal
        resultados_finales = []
        
        # Factor base para la carga lineal: Área del círculo * 1000
        factor_carga = ((math.pi * ((diametro_mm / 1000.0) ** 2)) / 4.0 * 1000.0)

        for id_cam, agg in resumen_matematico.items():
            n_taladros = agg['taladros']
            
            # Promedio Densidad
            prom_den = agg['sum_den'] / n_taladros if n_taladros > 0 else 0.0
            
            # Carga Lineal Promedio
            carga_lin = factor_carga * prom_den
            
            # Promedios de Mezcla
            n_d = agg['count_diesel']
            prom_diesel = agg['sum_diesel'] / n_d if n_d > 0 else 0.0
            prom_nitrato = 100.0 - prom_diesel if n_d > 0 else 0.0

            # Guardamos el resumen limpio en la lista final
            resultados_finales.append({
                'id_camion': id_cam,
                'nombre_camion': agg['nombre_camion'],
                'cantidad_taladros': n_taladros,
                'promedio_densidad': round(prom_den, 3),
                'carga_lineal': round(carga_lin, 2),
                'promedio_diesel': round(prom_diesel, 2),
                'promedio_nitrato': round(prom_nitrato, 2)
            })

        return resultados_finales
    
    def generar_dashboard_vertical_camion(self, datos_resumen_camion,id_camion, id_explosivo,fontsize,dia_carga):
        """
        Genera un dashboard vertical (1 sola columna) por camión con:
        Título -> Torta de Mezcla -> Caja de KPIs -> Gauge de Densidad.
        """
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        import numpy as np
        import os
        import time

        # ==========================================
        # 1. EXTRACCIÓN DE DATOS
        # ==========================================
        nombre = datos_resumen_camion.get('nombre_camion', 'N/A').upper()
        p_na = datos_resumen_camion.get('promedio_nitrato', 0.0)
        p_diesel = datos_resumen_camion.get('promedio_diesel', 0.0)
        carga = datos_resumen_camion.get('carga_lineal', 0.0)
        den = datos_resumen_camion.get('promedio_densidad', 0.0)
        taladros = datos_resumen_camion.get('cantidad_taladros', 0)

        # Buscar KPIs de densidad en base de datos
        try:
            from database.datos_db import obtener_kpi_por_explosivo
            datos_kpi = obtener_kpi_por_explosivo(id_explosivo)
        except Exception:
            datos_kpi = None

        if not datos_kpi or 'densidad_minima' not in datos_kpi:
            datos_kpi = {'densidad_minima': 0.75, 'densidad_maxima': 0.85}

        densidad_min = float(datos_kpi.get('densidad_minima', datos_kpi.get('densidad_minimo', 0.75)))
        densidad_max = float(datos_kpi.get('densidad_maxima', datos_kpi.get('densidad_maximo', 0.85)))

        # ==========================================
        # 2. CONFIGURACIÓN DEL LIENZO VERTICAL
        # ==========================================
        plt.rcParams['font.family'] = 'Arial'
        # Lienzo angosto (5.5) y alto (9.5) para el formato de columna
        fig = plt.figure(figsize=(5.5, 9.5)) 
        fig.patch.set_facecolor('white')
        fig.patch.set_alpha(0.0)

        # TÍTULO PRINCIPAL (En la cima absoluta)
        fig.suptitle(f"{nombre}", fontweight='bold', size=20, color='black', y=0.95)

        # Cuadrícula: 3 filas x 1 columna
        gs = gridspec.GridSpec(3, 1, height_ratios=[3.5, 1.2, 3.5], hspace=0.15)
        ax_pie = fig.add_subplot(gs[0])    # 1. Torta Arriba
        ax_text = fig.add_subplot(gs[1])   # 2. Resumen Medio
        ax_gauge = fig.add_subplot(gs[2])  # 3. Gauge Abajo

        # ==========================================
        # 3. GRÁFICA DE TORTA (ANILLO)
        # ==========================================
        if p_na > 0 or p_diesel > 0:
            sizes = [p_na, p_diesel]
            labels = ['NITRATO DE\nAMONIO', 'DIESEL']  # <--- El \n crea el salto de línea
            colors = ["#a5a5a5", "#fd4f3c"]

            wedges, texts, autotexts = ax_pie.pie(
                sizes, colors=colors, autopct='%1.1f%%', pctdistance=0.75,
                startangle=90, counterclock=False,
                wedgeprops=dict(width=0.45, edgecolor='none', linewidth=1)
            )

            # Porcentajes internos blancos y grandes
            for i, autotext in enumerate(autotexts):
                autotext.set_color("black")  # Relleno del número (Plomo y Rojo)
                autotext.set_fontsize(20)
                autotext.set_fontweight('bold')
                
                # 🟢 MAGIA AQUÍ: Borde blanco grueso alrededor del número
                autotext.set_path_effects([path_effects.withStroke(linewidth=2, foreground='white')])

            ax_pie.text(0, 0, "MEZCLA\nTOTAL", ha='center', va='center', fontsize=12, fontweight='bold', color='#555')

            # Flechas (Callouts)
            bbox_props = dict(boxstyle="square,pad=0.2", fc="white", ec="none")
            kw = dict(arrowprops=dict(arrowstyle="-", color="grey", lw=1.2), bbox=bbox_props, zorder=0, va="center")

            for i, p in enumerate(wedges):
                ang = (p.theta2 - p.theta1) / 2. + p.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))
                horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connectionstyle = f"angle,angleA=0,angleB={ang}"
                kw["arrowprops"].update({"connectionstyle": connectionstyle})
                
                ax_pie.annotate(labels[i], xy=(x, y), xytext=(1.2 * np.sign(x), 1.2 * y),
                                horizontalalignment=horizontalalignment, **kw,
                                fontsize=13, fontweight='bold', color="black",backgroundcolor="#fdfdfd00")
            ax_pie.axis('equal')
        else:
            ax_pie.text(0.5, 0.5, "Sin datos de altura de combustible", ha='center', va='center', color='grey')
            ax_pie.axis('off')

        # ==========================================
        # 4. CAJA DE RESUMEN DE PROMEDIOS (MEDIO)
        # ==========================================
        ax_text.axis('off')
        
        # Texto con saltos de línea para el formato columna
        info_text = (
            f"Carga Lineal: {carga:.1f} kg/m\n"
            f"Densidad Prom.: {den:.2f} g/cc\n"
            f"Taladros Medidos: {taladros}"
        )
        
        bbox_args = dict(boxstyle="round,pad=1.0", facecolor="#fdfdfd00", edgecolor="#cccccc", linewidth=1.5)
        
        ax_text.text(0.5, 1, " DATOS DE AUDITORÍA ", ha='center', va='center',
                     fontsize=15, color="#FFFFFF", backgroundcolor="#424242", zorder=10)
                     
        ax_text.text(0.5, 0.2, info_text, ha='center', va='center',
                     fontsize=17, color='black',backgroundcolor="#fdfdfd00", fontweight='bold', linespacing=1.8, bbox=bbox_args, zorder=1)

        # ==========================================
        # 5. GRÁFICA DE GAUGE (ABAJO)
        # ==========================================
        limite_superior = max(densidad_max, densidad_max + 0.2)
        colores_gauge = ["#e7923c", "#0ff144", "#005021", (0,0,0,0)] 
        tamanos_g = [densidad_min, densidad_max - densidad_min, limite_superior - densidad_max, limite_superior]

        ax_gauge.pie(tamanos_g, colors=colores_gauge, startangle=180, radius=1.0, counterclock=False,
                     wedgeprops=dict(width=0.3, edgecolor="#0ff14400", lw=1.5))

        r_text = 1.05
        ang_minimo = np.radians(180 - (densidad_min / limite_superior) * 180)
        ang_maximo = np.radians(180 - (densidad_max / limite_superior) * 180)

        # Números límite del Gauge
        ax_gauge.text(-r_text, 0.05, "0", ha='center', va='bottom', fontsize=15, fontweight='bold')
        ax_gauge.text(r_text * np.cos(ang_minimo), r_text * np.sin(ang_minimo), f"{densidad_min:.2f}", ha='center', va='bottom', fontsize=15, fontweight='bold')
        ax_gauge.text(r_text * np.cos(ang_maximo), r_text * np.sin(ang_maximo), f"{densidad_max:.2f}", ha='center', va='bottom', fontsize=15, fontweight='bold')
        ax_gauge.text(r_text, 0.05, f"{limite_superior:.2f}", ha='center', va='bottom', fontsize=15, fontweight='bold')

        # Dibujar Aguja
        valor_seguro = max(0, min(den, limite_superior))
        angulo_rad = np.radians(180 - (valor_seguro / limite_superior) * 180)
        ax_gauge.annotate('', xy=(0.65 * np.cos(angulo_rad), 0.65 * np.sin(angulo_rad)), xytext=(0, 0),
                          arrowprops=dict(facecolor='#2c3e50', edgecolor='black', width=3, headwidth=8))
        ax_gauge.plot(0, 0, marker='o', color='gray', markeredgecolor='black', markersize=14)
        ax_gauge.plot(0, 0, marker='o', color='black', markersize=4)

        # Estado Central
        if den < densidad_min:
            estado, col_txt = "BAJO", colores_gauge[0]
        elif den <= densidad_max:
            estado, col_txt = "ÓPTIMO", colores_gauge[1]
        else:
            estado, col_txt = "ALTO", colores_gauge[2]

        ax_gauge.text(0, -0.3, f"{den:.2f} g/cc", ha='center', va='center', fontsize=20, fontweight='bold', color='black')
        ax_gauge.text(0, -0.5, estado, ha='center', va='center', fontsize=16, fontweight='bold', color='black')

        ax_gauge.set_xlim(-1.3, 1.3)
        ax_gauge.set_ylim(-0.6, 1.2)
        ax_gauge.set_aspect('equal')
        ax_gauge.axis('off')

        # ==========================================
        # 6. GUARDAR IMAGEN
        # ==========================================
        if not os.path.exists("./recursos"): os.makedirs("./recursos")
        
        ruta_temp = f"./recursos/dash_vert_camion_{id_camion}_{dia_carga}.png"
        fig.savefig(ruta_temp, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return ruta_temp

    def generar_mapa_global_camiones(self, datos_anfo, datos_taladros,dia_carga):

        import matplotlib.pyplot as plt
        import matplotlib.patheffects as path_effects
        import os
        import time

        fig, ax = plt.subplots(figsize=(12, 6.5)) # Lienzo grande y panorámico

        # Fondo completamente transparente
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        # 1. Traer nombres de camiones desde la BD
        diccionario_camiones = self.datos_mysql.get("camion_fabrica", {})
        mapa_camiones = { str(d["id"]): str(nombre).upper() for nombre, d in diccionario_camiones.items() }

        # 2. Cruzar datos: Crear un diccionario { 'taladro': 'NOMBRE DEL CAMIÓN' }
        taladros_muestreados = {}
        
        if not datos_anfo:
            print("🚨 ERROR: datos_anfo está vacío. No hay datos crudos para este ID de voladura.")
            
        for fila in datos_anfo:
            # 🟢 Buscamos el nombre del pozo en diferentes posibles columnas
            tal = str(fila.get('taladro', fila.get('pozo', fila.get('id_pozo', fila.get('label', ''))))).strip().lower()
            id_cam = str(fila.get('id_camion', ''))
            
            if tal and id_cam:
                taladros_muestreados[tal] = mapa_camiones.get(id_cam, f"CAMIÓN {id_cam}")
        
        print(f"✅ Taladros muestreados encontrados en BD: {list(taladros_muestreados.keys())}")

        # 3. Separar las coordenadas de la malla
        x_fondo, y_fondo, labels_fondo = [], [], []
        x_medidos_reales, y_medidos_reales = [], []
        datos_por_camion = {} 
        
        nombres_malla_debug = [] # Para ver qué hay realmente en la malla

        is_dict = isinstance(datos_taladros, dict)
        taladros_iterables = datos_taladros.items() if is_dict else enumerate(datos_taladros)

        for clave, t in taladros_iterables:
            if not isinstance(t, dict): continue
            
            t_clean = {str(k).lower(): v for k, v in t.items()}
            
            # 🟢 EXTRACCIÓN SÚPER AGRESIVA DEL NOMBRE EN LA MALLA
            lbl_candidato = str(t_clean.get('label', t_clean.get('pozo', t_clean.get('nombre', t_clean.get('id', ''))))).strip()
            if not lbl_candidato and is_dict:
                lbl_candidato = str(clave).strip()
                
            lbl_original = lbl_candidato
            lbl_lower = lbl_original.lower()
            try:
                # Buscamos 'x', si no está buscamos 'este', si no 'easting'
                x_val = float(t_clean.get('x', t_clean.get('coorx_t', t_clean.get('coorx_t', 0.0))) or 0.0)
                y_val = float(t_clean.get('y', t_clean.get('coory_t', t_clean.get('coory_t', 0.0))) or 0.0)
            except ValueError:
                continue
                
            if x_val == 0.0 and y_val == 0.0:
                # print(f"⚠️ Omite taladro '{lbl_original}' porque no tiene coordenadas válidas.")
                continue
                
            # ¿Este taladro fue muestreado?
            if lbl_lower in taladros_muestreados:
                camion = taladros_muestreados[lbl_lower]
                #print("CAMION: ",camion)
                
                if camion not in datos_por_camion:
                    datos_por_camion[camion] = {'x': [], 'y': [], 'labels': []}
                    
                datos_por_camion[camion]['x'].append(x_val)
                datos_por_camion[camion]['y'].append(y_val)
                datos_por_camion[camion]['labels'].append(lbl_original)
                
                x_medidos_reales.append(x_val)
                y_medidos_reales.append(y_val)
            else:
                # Taladro normal de la malla
                x_fondo.append(x_val)
                y_fondo.append(y_val)
                labels_fondo.append(lbl_original)

        # Mecanismo de seguridad
        if not x_medidos_reales:
            print("🚨 ERROR: No hubo cruce. Los taladros medidos no coinciden con los de la malla.")
            print(f"🕵️‍♂️ Los primeros 15 taladros que el sistema encontró en tu malla son: {nombres_malla_debug}")
            print("--- FIN DEBUG ---")
            plt.close(fig)
            return None
            
        print(f"✅ ¡Cruce exitoso! Se dibujarán {len(x_medidos_reales)} taladros muestreados.")
     
        # 4. Encontrar el Centroide para la cámara
        x_centro = sum(x_medidos_reales) / len(x_medidos_reales)
        y_centro = sum(y_medidos_reales) / len(y_medidos_reales)

        # Calcular zoom dinámico
        radio_zoom_x, radio_zoom_y = 80, 35
        max_dist_x = max([abs(x - x_centro) for x in x_medidos_reales]) + 15
        max_dist_y = max([abs(y - y_centro) for y in y_medidos_reales]) + 15
        
        radio_zoom_x = max(radio_zoom_x, max_dist_x)
        radio_zoom_y = max(radio_zoom_y, max_dist_y)

        # 5. DIBUJAR TALADROS DE FONDO (Grises)
        x_fondo_rel = [x - x_centro for x in x_fondo]
        y_fondo_rel = [y - y_centro for y in y_fondo]
        
        # Filtramos para dibujar solo los que están dentro de la cámara
        x_f_plot, y_f_plot, lbl_f_plot = [], [], []
        for i in range(len(x_fondo_rel)):
            if abs(x_fondo_rel[i]) <= radio_zoom_x and abs(y_fondo_rel[i]) <= radio_zoom_y:
                x_f_plot.append(x_fondo_rel[i])
                y_f_plot.append(y_fondo_rel[i])
                lbl_f_plot.append(labels_fondo[i])

        if x_f_plot:
            ax.scatter(x_f_plot, y_f_plot, color="#e6e6e6", edgecolors="none", s=125, zorder=2)
            for i in range(len(x_f_plot)):
                ax.text(x_f_plot[i], y_f_plot[i], lbl_f_plot[i], ha='center', va='center', 
                        fontsize=7, color="#000000", zorder=3)

        # 6. DIBUJAR TALADROS MUESTREADOS (Un color por camión)
        colores_camiones = ["#ff7c6e", "#51a7e0", "#67e99d", "#f1ad41", "#b864db", "#ca6f33"]
        
        # Efecto de borde blanco para que las letras destaquen
        efecto_borde = [path_effects.withStroke(linewidth=2, foreground='white')]

        for index, (camion, datos) in enumerate(datos_por_camion.items()):
            color_actual = colores_camiones[index % len(colores_camiones)]
            
            x_rel = [x - x_centro for x in datos['x']]
            y_rel = [y - y_centro for y in datos['y']]
            lbls = datos['labels']
            
            # Dibujar los puntos del camión
            ax.scatter(x_rel, y_rel, color=color_actual, edgecolors='none', s=200, zorder=4, label=camion)
            
            # Etiquetar cada punto
            for i in range(len(x_rel)):
                # Número del taladro
                ax.text(x_rel[i], y_rel[i], lbls[i], ha='center', va='center', 
                        fontsize=10, color='black', fontweight='bold', zorder=5)
                
                # Nombre del camión debajo del taladro
                #txt_camion = ax.text(x_rel[i], y_rel[i] - 2.5, camion, ha='center', va='top', 
                #                     fontsize=6, color=color_actual, fontweight='bold', zorder=5)
                #txt_camion.set_path_effects(efecto_borde)

        # 7. ESTÉTICA Y LÍMITES
        ax.set_xlim(-radio_zoom_x, radio_zoom_x)
        ax.set_ylim(-radio_zoom_y, radio_zoom_y)
        ax.set_aspect('equal') 
        ax.axis('off') # Apagamos ejes

        # Leyenda oficial (Cuadro con los colores de los camiones)
        ax.legend(loc='upper right', title="CAMIONES", fontsize=8, title_fontsize=9,
                  facecolor='white', framealpha=0.9, edgecolor='#ccc', markerscale=0.4)

        # Título en la esquina
        ax.text(0.02, 1.04 , "MAPA GLOBAL DE MUESTREO DE DENSIDAD", transform=ax.transAxes, 
                fontsize=13, fontweight='bold', va='center', color='#333', 
                bbox=dict(facecolor='white', alpha=0.9, edgecolor='none'))

        if not os.path.exists("./recursos"): os.makedirs("./recursos")
        ruta = f"./recursos/mapa_global_densidad_{dia_carga}.png"
        fig.savefig(ruta, dpi=230, bbox_inches='tight', transparent=True)
        plt.close(fig)
        
        return ruta

    def generar_dashboard_horizontal_camion(self, datos_resumen_camion, id_explosivo,fontsize,dia_carga):
        """
        Genera un dashboard horizontal (1 fila, 3 columnas) por camión.
        Torta Izquierda -> Resumen Centro -> Gauge Derecha
        """
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        import matplotlib.patheffects as path_effects
        import numpy as np
        import os
        import time

        nombre = datos_resumen_camion.get('nombre_camion', 'N/A').upper()
        p_na = datos_resumen_camion.get('promedio_nitrato', 0.0)
        p_diesel = datos_resumen_camion.get('promedio_diesel', 0.0)
        carga = datos_resumen_camion.get('carga_lineal', 0.0)
        den = datos_resumen_camion.get('promedio_densidad', 0.0)
        taladros = datos_resumen_camion.get('cantidad_taladros', 0)

        try:
            from database.datos_db import obtener_kpi_por_explosivo
            datos_kpi = obtener_kpi_por_explosivo(id_explosivo)
        except Exception:
            datos_kpi = None

        if not datos_kpi or 'densidad_minima' not in datos_kpi:
            datos_kpi = {'densidad_minima': 0.75, 'densidad_maxima': 0.85}

        densidad_min = float(datos_kpi.get('densidad_minima', datos_kpi.get('densidad_minimo', 0.75)))
        densidad_max = float(datos_kpi.get('densidad_maxima', datos_kpi.get('densidad_maximo', 0.85)))

        # 🟢 LIENZO HORIZONTAL (12 de ancho x 4 de alto)
        plt.rcParams['font.family'] = 'Arial'
        fig = plt.figure(figsize=(12, 4)) 
        fig.patch.set_alpha(0.0)

        fig.suptitle(f"{nombre}", fontweight='bold', size=17, color='black', y=1.0)

        # 🟢 CUADRÍCULA: 1 fila x 3 columnas
        gs = gridspec.GridSpec(1, 3, width_ratios=[1, 1, 1], wspace=0.1)
        ax_pie = fig.add_subplot(gs[0])    # 1. Izquierda
        ax_text = fig.add_subplot(gs[1])   # 2. Centro
        ax_gauge = fig.add_subplot(gs[2])  # 3. Derecha
        
        ax_pie.patch.set_alpha(0.0)
        ax_text.patch.set_alpha(0.0)
        ax_gauge.patch.set_alpha(0.0)

        # ==========================================
        # A) TORTA (Izquierda)
        # ==========================================
        if p_na > 0 or p_diesel > 0:
            sizes = [p_na, p_diesel]
            labels = ['NITRATO DE\nAMONIO', 'DIESEL']
            colors = ["#a5a5a5", "#fd4f3c"]

            wedges, texts, autotexts = ax_pie.pie(
                sizes, colors=colors, autopct='%1.1f%%', pctdistance=0.75,
                startangle=90, counterclock=False,
                wedgeprops=dict(width=0.45, edgecolor='none')
            )

            for i, autotext in enumerate(autotexts):
                autotext.set_color("black")
                autotext.set_fontsize(13)
                autotext.set_fontweight('bold')
                autotext.set_path_effects([path_effects.withStroke(linewidth=3, foreground='white')])

            ax_pie.text(0, 0, "MEZCLA\nTOTAL", ha='center', va='center', fontsize=12, fontweight='bold', color='black')

            bbox_props = dict(boxstyle="square,pad=0.2", fc="white", ec="none", alpha=0.0)
            kw = dict(arrowprops=dict(arrowstyle="-", color="grey", lw=1.2), bbox=bbox_props, zorder=0, va="center")

            for i, p in enumerate(wedges):
                ang = (p.theta2 - p.theta1) / 2. + p.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))
                horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connectionstyle = f"angle,angleA=0,angleB={ang}"
                kw["arrowprops"].update({"connectionstyle": connectionstyle})
                
                ax_pie.annotate(labels[i], xy=(x, y), xytext=(1.2 * np.sign(x), 1.2 * y),
                                horizontalalignment=horizontalalignment, **kw,
                                fontsize=fontsize, fontweight='bold', color='black')
            ax_pie.axis('equal')
        else:
            ax_pie.text(0.5, 0.5, "Sin datos", ha='center', va='center', color='grey')
            ax_pie.axis('off')

        # ==========================================
        # B) RESUMEN (Centro)
        # ==========================================
        ax_text.axis('off')
        info_text = (
            f"CARGA LINEAL: {carga:.1f} kg/m\n"
            f"DENSIDAD EN COPA: {den:.2f} g/cc\n"
            f"TALADROS MEDIDOS: {taladros}"
        )
        bbox_args = dict(boxstyle="round,pad=1.0", facecolor="#ffffff", edgecolor="#cccccc", linewidth=1.5, alpha=0.9)
        
        ax_text.text(0.5, 0.85, " DATOS DE AUDITORÍA ", ha='center', va='center',
                     fontsize=11, color='white', backgroundcolor='#424242', zorder=10, fontweight='bold')
                     
        ax_text.text(0.5, 0.45, info_text, ha='center', va='center',
                     fontsize=11, color='black', fontweight='bold', linespacing=1.8, bbox=bbox_args, zorder=1)

        # ==========================================
        # C) GAUGE (Derecha)
        # ==========================================
        limite_superior = max(densidad_max, densidad_max + 0.2)
        colores_gauge = ["#e7923c", "#0ff144", "#005021", (0,0,0,0)] 
        tamanos_g = [densidad_min, densidad_max - densidad_min, limite_superior - densidad_max, limite_superior]

        ax_gauge.pie(tamanos_g, colors=colores_gauge, startangle=180, radius=1.0, counterclock=False,
                     wedgeprops=dict(width=0.3, edgecolor='none'))

        r_text = 1.05
        ang_minimo = np.radians(180 - (densidad_min / limite_superior) * 180)
        ang_maximo = np.radians(180 - (densidad_max / limite_superior) * 180)

        ax_gauge.text(-r_text, 0.05, "0", ha='center', va='bottom', fontsize=11, fontweight='bold')
        ax_gauge.text(r_text * np.cos(ang_minimo), r_text * np.sin(ang_minimo), f"{densidad_min:.2f}", ha='center', va='bottom', fontsize=11, fontweight='bold')
        ax_gauge.text(r_text * np.cos(ang_maximo), r_text * np.sin(ang_maximo), f"{densidad_max:.2f}", ha='center', va='baseline', fontsize=11, fontweight='bold')
        ax_gauge.text(r_text, 0.05, f"{limite_superior:.2f}", ha='left', va='bottom', fontsize=11, fontweight='bold')

        valor_seguro = max(0, min(den, limite_superior))
        angulo_rad = np.radians(180 - (valor_seguro / limite_superior) * 180)
        ax_gauge.annotate('', xy=(0.65 * np.cos(angulo_rad), 0.65 * np.sin(angulo_rad)), xytext=(0, 0),
                          arrowprops=dict(facecolor='#2c3e50', edgecolor='black', width=3, headwidth=8))
        ax_gauge.plot(0, 0, marker='o', color='gray', markeredgecolor='black', markersize=14)
        ax_gauge.plot(0, 0, marker='o', color='black', markersize=4)

        if den < densidad_min:
            estado, col_txt = "BAJO", colores_gauge[0]
        elif den <= densidad_max:
            estado, col_txt = "ÓPTIMO", colores_gauge[1]
        else:
            estado, col_txt = "ALTO", colores_gauge[2]

        ax_gauge.text(0, -0.3, f"{den:.2f} g/cc", ha='center', va='center', fontsize=14, fontweight='bold', color='black')
        ax_gauge.text(0, -0.65, estado, ha='center', va='center', fontsize=12, fontweight='bold', color='black')

        ax_gauge.set_xlim(-1.3, 1.3)
        ax_gauge.set_ylim(-0.6, 1.2)
        ax_gauge.set_aspect('equal')
        ax_gauge.axis('off')

        if not os.path.exists("./recursos"): os.makedirs("./recursos")
        ruta_temp = f"./recursos/dash_horiz_camion_{dia_carga}.png"
        fig.savefig(ruta_temp, dpi=150, bbox_inches='tight', transparent=True)
        plt.close(fig)
        return ruta_temp

    def curva_profundidad(self,idexplosivo):
        
        #print(float(self.inputs["columna_de_agua"].get()))
        
        tipo_taco = self.inputs["tipo_taco"].get().strip() if self.inputs["tipo_taco"].get() else ""
        taco = float(self.inputs["taco"].get().strip()) if self.inputs["taco"].get() else 0.0
        columna_agua = float(self.inputs["columna_de_agua"].get()) if self.inputs["columna_de_agua"].get() else 0.0
        densidad_teo = float(self.inputs["densidad_teorica"].get()) if self.inputs["densidad_teorica"].get() else 1.0
        #densidad_carga = float(datos['densidad_carga'])
        densidad_final = float(self.inputs["densidad_final"].get()) if self.inputs["densidad_final"].get() else 1.0
        long_carga = float(self.inputs["longitud_carga"].get()) if self.inputs["longitud_carga"].get() else 1.0
        #presion_atm = float(datos['presion_atm'])
        #gravedad = float(datos['gravedad'])
        diametro = float(self.inputs["diametro"].get()) if self.inputs["diametro"].get() else 1.0

        densidad_aparente = 1.27
        presion_atm = 1
        gravedad = 9.81

        presion_retacado = 0
        if tipo_taco == "GRAVILLA":
            #print("TIPO DE TACO:",tipo_taco)
            presion_retacado = (densidad_aparente*1000)*9.81* (2*diametro/1000)*0.987*0.00001
        else:
            presion_retacado=(densidad_aparente*1000)* 9.81 *taco * 0.987 * 10/1000000

        gas_prof = []
        densidades=[]
        datos = {"longitud":[],"densidad":[]}

        #print("PRESION DE RETACADO :",presion_retacado)
        #print("PRESION DE  :",presion_retacado)

        if idexplosivo == 4 or 6: #rioflex 7000
            #rioflex_matriz = 1.39
            #volume_gas_an = 1/float(self.datos_densidad_prill['high_density_prill'])-(1/an_crystal)*(1-float(self.datos_proporciones_mezcla["70/30"]))

            #print("PRESION RETACADO: ",presion_retacado)

            #print(volume_gas_an)
            total_pressure = presion_atm+presion_retacado+ columna_agua/10.2

            #print("PRESION: ",total_pressure)

            density_at_depth = 1/((1/densidad_teo) + (1/densidad_final - 1/densidad_teo)*presion_atm/total_pressure)

            #print("DENSIDAD: ",density_at_depth)


            gas_depth = 1/density_at_depth - 1/densidad_teo

            gas_prof.append(gas_depth)

            #total_gas_depth = gas_depth + volume_gas_an
            #porc_gas_depth = total_gas_depth * 1/density_at_depth

            densidad_prom = density_at_depth

            datos['longitud'].append(0)
            datos['densidad'].append(densidad_prom)
            densidades.append(densidad_prom)

            for i in range(1,int(long_carga*10+30)):
                prof = i/10

                total_pressure_prof =presion_retacado+ presion_atm+ columna_agua/10.2 + (datos['densidad'][i-1]*1000)*gravedad*prof*0.00001
                density_at_prof = 1/(1/densidad_teo + (1/densidad_final - 1/densidad_teo)*presion_atm/total_pressure_prof)
                #gas_depth_prof = 1/density_at_prof - 1/densidad_teo
                #total_gas_depth_prof = gas_depth_prof + volume_gas_an
                #porc_gas_depth_prof = total_gas_depth_prof * 1/density_at_prof
                #gas_prof.append(gas_depth_prof)

                #densidad_prom = 1/(1/densidad_teo +np.mean(gas_prof))
                densidades.append(density_at_prof)
                #print("Prof: ",prof," - "," densidad_prom: ",densidad_prom)

                datos['longitud'].append(prof)
                datos['densidad'].append(np.mean(densidades))
            
            #print(datos)
            
            return datos
                
    def obtener_resumen_rioflex_por_camion(self, datos_rioflex, diametro_mm):

        import math
        resumen_matematico = {}
        
        # 1. Obtener el diccionario para traducir ID a Nombre del Camión
        diccionario_camiones = self.datos_mysql.get("camion_fabrica", {})
        mapa_camiones = { str(d["id"]): nombre for nombre, d in diccionario_camiones.items() }

        # 2. Agrupar y sumar los datos crudos
        for fila in datos_rioflex:
            id_cam = str(fila.get('id_camion'))
            if not id_cam or id_cam == "None":
                continue
            
            if id_cam not in resumen_matematico:
                resumen_matematico[id_cam] = {
                    'nombre_camion': mapa_camiones.get(id_cam, f"ID {id_cam}"),
                    'taladros': 0, 
                    'sum_den': 0.0, 
                    'count_den': 0,
                    'sum_temp': 0.0,
                    'count_temp': 0,
                    'sum_ph': 0.0,
                    'count_ph': 0
                }
            
            resumen_matematico[id_cam]['taladros'] += 1
            
            # Sumar Densidad
            try:
                # El campo en la BD de Rioflex se suele llamar 'densidad'
                den = float(str(fila.get('densidad', 0)).strip())
                if den > 0:
                    resumen_matematico[id_cam]['sum_den'] += den
                    resumen_matematico[id_cam]['count_den'] += 1
            except (ValueError, TypeError): 
                pass

            # Sumar Temperatura
            try:
                temp = float(str(fila.get('temperatura', 0)).strip())
                if temp > 0:
                    resumen_matematico[id_cam]['sum_temp'] += temp
                    resumen_matematico[id_cam]['count_temp'] += 1
            except (ValueError, TypeError): 
                pass

            # Sumar pH
            try:
                ph = float(str(fila.get('ph', 0)).strip())
                if ph > 0:
                    resumen_matematico[id_cam]['sum_ph'] += ph
                    resumen_matematico[id_cam]['count_ph'] += 1
            except (ValueError, TypeError): 
                pass

        # 3. Calcular Promedios y Carga Lineal
        resultados_finales = []
        
        # Factor base para la carga lineal: Área del círculo * 1000
        factor_carga = ((math.pi * ((diametro_mm / 1000.0) ** 2)) / 4.0 * 1000.0)

        for id_cam, agg in resumen_matematico.items():
            n_taladros = agg['taladros']
            
            # Promedio Densidad
            c_den = agg['count_den']
            prom_den = agg['sum_den'] / c_den if c_den > 0 else 0.0
            
            # Carga Lineal Promedio
            carga_lin = factor_carga * prom_den
            
            # Promedios de Temperatura y pH
            c_temp = agg['count_temp']
            prom_temp = agg['sum_temp'] / c_temp if c_temp > 0 else 0.0

            c_ph = agg['count_ph']
            prom_ph = agg['sum_ph'] / c_ph if c_ph > 0 else 0.0

            # Guardamos el resumen limpio en la lista final que consumirá el PDF
            resultados_finales.append({
                'id_camion': id_cam,
                'nombre_camion': agg['nombre_camion'].upper(),
                'cantidad_taladros': n_taladros,
                'promedio_densidad': round(prom_den, 3),
                'carga_lineal': round(carga_lin, 2),
                'promedio_temperatura': round(prom_temp, 1),
                'promedio_ph': round(prom_ph, 1)
            })

        return resultados_finales
    
    def generar_dashboard_horizontal_camion_rioflex(self, datos_resumen_camion, id_explosivo,dia_carga):

        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        import matplotlib.patheffects as path_effects
        import numpy as np
        import os

        nombre = datos_resumen_camion.get('nombre_camion', 'N/A').upper()
        p_temp = datos_resumen_camion.get('promedio_temperatura', 0.0)
        p_ph = datos_resumen_camion.get('promedio_ph', 0.0)
        carga = datos_resumen_camion.get('carga_lineal', 0.0)
        den = datos_resumen_camion.get('promedio_densidad', 0.0)
        taladros = datos_resumen_camion.get('cantidad_taladros', 0)

        try:
            from database.datos_db import obtener_kpi_por_explosivo
            datos_kpi = obtener_kpi_por_explosivo(id_explosivo)
        except Exception:
            datos_kpi = None


        if not datos_kpi or 'densidad_minima' not in datos_kpi:
            datos_kpi = {'densidad_minima': 0.75, 'densidad_maxima': 0.85}

        densidad_min = float(datos_kpi.get('densidad_minima', datos_kpi.get('densidad_minimo', 0.75)))
        densidad_max = float(datos_kpi.get('densidad_maxima', datos_kpi.get('densidad_maximo', 0.85)))

        # 🟢 LIENZO HORIZONTAL (12 de ancho x 4 de alto)
        plt.rcParams['font.family'] = 'Arial'
        fig = plt.figure(figsize=(12, 4)) 
        fig.patch.set_alpha(0.0)

        fig.suptitle(f"{nombre}", fontweight='bold', size=18, color='black', y=1.0)

        # 🟢 CUADRÍCULA: 1 fila x 3 columnas
        gs = gridspec.GridSpec(1, 3, width_ratios=[1, 1, 1], wspace=0.1)
        ax_densidad = fig.add_subplot(gs[0])    # 1. Izquierda
        ax_text = fig.add_subplot(gs[1])   # 2. Centro
        ax_gauge = fig.add_subplot(gs[2])  # 3. Derecha
        
        ax_densidad.patch.set_alpha(0.0)
        ax_text.patch.set_alpha(0.0)
        ax_gauge.patch.set_alpha(0.0)

        # ==========================================
        # A) TORTA (Izquierda)
        # ==========================================
        datos_profundidad = self.curva_profundidad(id_explosivo)
        densidades_x = datos_profundidad['densidad']
        profundidades_y = datos_profundidad['longitud']

        densidad_punto_interp = np.interp(float(self.inputs["longitud_carga"].get()), profundidades_y, densidades_x)

        # Trazar la curva (Pintamos el área bajo la curva de verde claro simulando el explosivo)
        ax_densidad.plot(densidades_x, profundidades_y, color='green', linewidth=2)

        #ax_densidad.axvspan(densidad_min, densidad_max, 
        #   color='#2ecc71', alpha=0.18, 
        #   label=f'Rango Óptimo ({densidad_min:.2f} - {densidad_max:.2f} g/cc)')

        # Dibujar las líneas guías punteadas en los bordes del KPI
        ax_densidad.axvline(densidad_min, color="#3ede81", linestyle='--', alpha=0.6, linewidth=1.2)
        ax_densidad.axvline(densidad_max, color='#27ae60', linestyle='--', alpha=0.6, linewidth=1.2)

        # Validamos que el input no exceda la profundidad máxima calculada
        if float(self.inputs["longitud_carga"].get()) <= max(profundidades_y):
            # Pintar el marcador circular rojo sobre la curva
            ax_densidad.scatter(densidad_punto_interp, float(self.inputs["longitud_carga"].get()), 
                    color='#e74c3c', s=100, zorder=5, edgecolors='black', 
                    label=f'Input: {float(self.inputs["longitud_carga"].get())}m')
            
            # Agregar la línea guía horizontal punteada hacia el eje de profundidad (Y)
            ax_densidad.plot([min(densidades_x) - 0.1, densidad_punto_interp], [float(self.inputs["longitud_carga"].get()), float(self.inputs["longitud_carga"].get())], 
                    color='#e74c3c', linestyle=':', alpha=0.7, linewidth=1.2)
            
            # Añadir un cuadro de texto informativo al lado del punto
            texto_anotacion = f" {densidad_punto_interp:.2f} g/cc\n a {float(self.inputs['longitud_carga'].get()):.1f} m "
            
            ax_densidad.annotate(texto_anotacion, 
                        xy=(densidad_punto_interp, float(self.inputs["longitud_carga"].get())),
                        xytext=(15, -10), # Desplazamiento del texto en píxeles hacia la derecha/abajo
                        textcoords='offset points',
                        fontsize=9, fontweight='bold', color='white',
                        bbox=dict(boxstyle='round,pad=0.4', facecolor='#2c3e50', alpha=0.9, edgecolor='none', zorder=6),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.1', color='#2c3e50', lw=1))
        #ax_densidad.fill_betweenx(profundidades_y, densidades_x, color='#a8e6cf', alpha=0.5)

        # 3. 🟢 INVERTIR EL EJE Y (Para que 0m esté arriba simulando el taladro)
        ax_densidad.invert_yaxis()

        # Estética
        ax_densidad.set_title('Densidad vs Longitud de Carga', fontweight='bold')
        ax_densidad.set_xlabel('Densidad (g/cc)',fontsize=11)
        ax_densidad.set_ylabel('Longfitud de Carga (m)',fontsize=11)
        ax_densidad.grid(True, linestyle='--', alpha=0.7)
        ax_densidad.tick_params(axis='x',labelsize=11)

        # Opcional: Ajustar los límites de X para que la curva sea más visible
        ax_densidad.set_xlim(min(densidades_x) - 0.05, max(densidades_x) + 0.05)

        # ==========================================
        # B) RESUMEN (Centro)
        # ==========================================
        ax_text.axis('off')
        info_text = (
            f"CARGA LINEAL: {carga:.1f} kg/m\n"
            f"DENSIDAD EN COPA: {den:.2f} g/cc\n"
            f"TEMPERATURA: {p_temp:.2f} °C\n"
            f"PH: {p_ph:.2f}\n"
            f"TALADROS MEDIDOS: {taladros}"
        )
        bbox_args = dict(boxstyle="round,pad=1.0", facecolor="#ffffff", edgecolor="#cccccc", linewidth=1.5, alpha=0.9)
        
        ax_text.text(0.5, 0.85, " DATOS DE AUDITORÍA ", ha='center', va='center',
                     fontsize=10, color='white', backgroundcolor='#424242', zorder=10, fontweight='bold')
                     
        ax_text.text(0.5, 0.45, info_text, ha='center', va='center',
                     fontsize=10, color='black', fontweight='bold', linespacing=1.8, bbox=bbox_args, zorder=1)

        # ==========================================
        # C) GAUGE (Derecha)
        # ==========================================
        limite_superior = max(densidad_max, densidad_max + 0.2)
        colores_gauge = ["#e7923c", "#0ff144", "#005021", (0,0,0,0)] 
        tamanos_g = [densidad_min, densidad_max - densidad_min, limite_superior - densidad_max, limite_superior]

        ax_gauge.pie(tamanos_g, colors=colores_gauge, startangle=180, radius=1.0, counterclock=False,
                     wedgeprops=dict(width=0.3, edgecolor='none'))

        r_text = 1.05
        ang_minimo = np.radians(180 - (densidad_min / limite_superior) * 180)
        ang_maximo = np.radians(180 - (densidad_max / limite_superior) * 180)

        ax_gauge.text(-r_text, 0.05, "0", ha='center', va='bottom', fontsize=10, fontweight='bold')
        ax_gauge.text(r_text * np.cos(ang_minimo), r_text * np.sin(ang_minimo), f"{densidad_min:.2f}", ha='center', va='bottom', fontsize=10, fontweight='bold')
        ax_gauge.text(r_text * np.cos(ang_maximo), r_text * np.sin(ang_maximo), f"{densidad_max:.2f}", ha='center', va='baseline', fontsize=10, fontweight='bold')
        ax_gauge.text(r_text, 0.05, f"{limite_superior:.2f}", ha='left', va='bottom', fontsize=10, fontweight='bold')

        valor_seguro = max(0, min(den, limite_superior))
        angulo_rad = np.radians(180 - (valor_seguro / limite_superior) * 180)
        ax_gauge.annotate('', xy=(0.65 * np.cos(angulo_rad), 0.65 * np.sin(angulo_rad)), xytext=(0, 0),
                          arrowprops=dict(facecolor='#2c3e50', edgecolor='black', width=3, headwidth=8))
        ax_gauge.plot(0, 0, marker='o', color='gray', markeredgecolor='black', markersize=14)
        ax_gauge.plot(0, 0, marker='o', color='black', markersize=4)

        if den < densidad_min:
            estado, col_txt = "BAJO", colores_gauge[0]
        elif den <= densidad_max:
            estado, col_txt = "ÓPTIMO", colores_gauge[1]
        else:
            estado, col_txt = "ALTO", colores_gauge[2]

        ax_gauge.text(0, -0.3, f"{den:.2f} g/cc", ha='center', va='center', fontsize=13, fontweight='bold', color='black')
        ax_gauge.text(0, -0.5, estado, ha='center', va='center', fontsize=10, fontweight='bold', color='black')

        ax_gauge.set_xlim(-1.3, 1.3)
        ax_gauge.set_ylim(-0.6, 1.2)
        ax_gauge.set_aspect('equal')
        ax_gauge.axis('off')

        if not os.path.exists("./recursos"): os.makedirs("./recursos")
        ruta_temp = f"./recursos/dash_horiz_camion_riolfex_{dia_carga}.png"
        fig.savefig(ruta_temp, dpi=150, bbox_inches='tight', transparent=True)
        plt.close(fig)
        return ruta_temp

    def generar_dashboard_vertical_camion_rioflex(self, datos_resumen_camion,id_camion, id_explosivo,dia_carga):

        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        import numpy as np
        import os
        import time

        # ==========================================
        # 1. EXTRACCIÓN DE DATOS
        # ==========================================
        nombre = datos_resumen_camion.get('nombre_camion', 'N/A').upper()
        p_temp = datos_resumen_camion.get('promedio_temperatura', 0.0)
        p_ph = datos_resumen_camion.get('promedio_ph', 0.0)
        carga = datos_resumen_camion.get('carga_lineal', 0.0)
        den = datos_resumen_camion.get('promedio_densidad', 0.0)
        taladros = datos_resumen_camion.get('cantidad_taladros', 0)

        # Buscar KPIs de densidad en base de datos
        try:
            from database.datos_db import obtener_kpi_por_explosivo
            datos_kpi = obtener_kpi_por_explosivo(id_explosivo)
        except Exception:
            datos_kpi = None

        if not datos_kpi or 'densidad_minima' not in datos_kpi:
            datos_kpi = {'densidad_minima': 0.75, 'densidad_maxima': 0.95}

        densidad_min = float(datos_kpi.get('densidad_minima', datos_kpi.get('densidad_minimo', 0.75)))
        densidad_max = float(datos_kpi.get('densidad_maxima', datos_kpi.get('densidad_maximo', 0.85)))

        # ==========================================
        # 2. CONFIGURACIÓN DEL LIENZO VERTICAL
        # ==========================================
        plt.rcParams['font.family'] = 'Arial'
        # Lienzo angosto (5.5) y alto (9.5) para el formato de columna
        fig = plt.figure(figsize=(5.5, 7)) 
        fig.patch.set_facecolor('white')
        fig.patch.set_alpha(0.0)

        # TÍTULO PRINCIPAL (En la cima absoluta)
        fig.suptitle(f"{nombre}", fontweight='bold', size=19, color='black', y=0.86)

        # Cuadrícula: 3 filas x 1 columna
        gs = gridspec.GridSpec(2, 1, height_ratios=[2, 2], hspace=0.10)
        #ax_densidad = fig.add_subplot(gs[0])    # 1. Torta Arriba
        ax_text = fig.add_subplot(gs[0])   # 2. Resumen Medio
        ax_gauge = fig.add_subplot(gs[1])  # 3. Gauge Abajo

        # ==========================================
        # 4. CAJA DE RESUMEN DE PROMEDIOS (MEDIO)
        # ==========================================
        ax_text.axis('off')
        
        # Texto con saltos de línea para el formato columna
        info_text = (
            f"CARGA LINEAL: {carga:.1f} kg/m\n"
            f"DENSIDAD EN COPA: {den:.2f} g/cc\n"
            f"TEMPERATURA: {p_temp:.2f} °C\n"
            f"PH: {p_ph:.2f} \n"
            f"TALADROS MEDIDOS: {taladros}"
        )
        
        bbox_args = dict(boxstyle="round,pad=1.0", facecolor="#fdfdfd00", edgecolor="#cccccc", linewidth=1.5)
        
        ax_text.text(0.5, 0.78, " DATOS DE AUDITORÍA ", ha='center', va='center',
                     fontsize=11, color="#FFFFFF", backgroundcolor="#424242", zorder=10)
                     
        ax_text.text(0.5, 0.4, info_text, ha='center', va='center',
                     fontsize=14, color='black',backgroundcolor="#fdfdfd00", fontweight='bold', linespacing=1.8, bbox=bbox_args, zorder=1)

        # ==========================================
        # 5. GRÁFICA DE GAUGE (ABAJO)
        # ==========================================
        limite_superior = max(densidad_max, densidad_max + 0.2)
        colores_gauge = ["#e7923c", "#0ff144", "#005021", (0,0,0,0)] 
        tamanos_g = [densidad_min, densidad_max - densidad_min, limite_superior - densidad_max, limite_superior]

        ax_gauge.pie(tamanos_g, colors=colores_gauge, startangle=180, radius=1.0, counterclock=False,
                     wedgeprops=dict(width=0.3, edgecolor="#0ff14400", lw=1.5))

        r_text = 1.05
        ang_minimo = np.radians(180 - (densidad_min / limite_superior) * 180)
        ang_maximo = np.radians(180 - (densidad_max / limite_superior) * 180)

        # Números límite del Gauge
        ax_gauge.text(-r_text, 0.05, "0", ha='center', va='bottom', fontsize=13, fontweight='bold')
        ax_gauge.text(r_text * np.cos(ang_minimo), r_text * np.sin(ang_minimo), f"{densidad_min:.2f}", ha='center', va='bottom', fontsize=13, fontweight='bold')
        ax_gauge.text(r_text * np.cos(ang_maximo), r_text * np.sin(ang_maximo), f"{densidad_max:.2f}", ha='left', va='bottom', fontsize=13, fontweight='bold')
        ax_gauge.text(r_text, 0.05, f"{limite_superior:.2f}", ha='left', va='bottom', fontsize=13, fontweight='bold')

        # Dibujar Aguja
        valor_seguro = max(0, min(den, limite_superior))
        angulo_rad = np.radians(180 - (valor_seguro / limite_superior) * 180)
        ax_gauge.annotate('', xy=(0.65 * np.cos(angulo_rad), 0.65 * np.sin(angulo_rad)), xytext=(0, 0),
                          arrowprops=dict(facecolor='#2c3e50', edgecolor='black', width=3, headwidth=8))
        ax_gauge.plot(0, 0, marker='o', color='gray', markeredgecolor='black', markersize=14)
        ax_gauge.plot(0, 0, marker='o', color='black', markersize=4)

        # Estado Central
        if den < densidad_min:
            estado, col_txt = "BAJO", colores_gauge[0]
        elif den <= densidad_max:
            estado, col_txt = "ÓPTIMO", colores_gauge[1]
        else:
            estado, col_txt = "ALTO", colores_gauge[2]

        ax_gauge.text(0, -0.3, f"{den:.2f} g/cc", ha='center', va='center', fontsize=16, fontweight='bold', color='black')
        ax_gauge.text(0, -0.5, estado, ha='center', va='center', fontsize=12, fontweight='bold', color='black')

        ax_gauge.set_xlim(-1.3, 1.3)
        ax_gauge.set_ylim(-0.6, 1.2)
        ax_gauge.set_aspect('equal')
        ax_gauge.axis('off')

        # ==========================================
        # 6. GUARDAR IMAGEN
        # ==========================================
        if not os.path.exists("./recursos"): os.makedirs("./recursos")
        
        ruta_temp = f"./recursos/dash_vert_camion_rioflex_{id_camion}_{dia_carga}.png"
        fig.savefig(ruta_temp, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return ruta_temp

    def generar_dashboard_vertical_profundidad_rioflex(self, id_explosivo, datos_grupo):
        import matplotlib.pyplot as plt
        import numpy as np
        import os
        import time

        # Buscar KPIs de densidad en base de datos
        try:
            from database.datos_db import obtener_kpi_por_explosivo
            datos_kpi = obtener_kpi_por_explosivo(id_explosivo)
        except Exception:
            datos_kpi = None

        if not datos_kpi or 'densidad_minima' not in datos_kpi:
            datos_kpi = {'densidad_minima': 0.75, 'densidad_maxima': 0.85}

        densidad_min = float(datos_kpi.get('densidad_minima', datos_kpi.get('densidad_minimo', 0.75)))
        densidad_max = float(datos_kpi.get('densidad_maxima', datos_kpi.get('densidad_maximo', 0.85)))

        # Extraer longitud de carga ingresada por el usuario
        try:
            longitud_carga_usuario = float(self.inputs["longitud_carga"].get() or 0.0)
        except (ValueError, KeyError, TypeError):
            longitud_carga_usuario = 0.0

        # ==========================================================
        # 1. CONFIGURACIÓN CORRECTA DEL LIENZO Y EJES
        # ==========================================================
        plt.rcParams['font.family'] = 'Arial'
        # Usamos subplots para obtener fig y ax correctamente
        fig, ax = plt.subplots(figsize=(5.5, 7)) 
        fig.patch.set_facecolor('white')
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        # Pintar la franja del rango óptimo (KPI) compartida de fondo
        ax.axvspan(densidad_min, densidad_max, color='#2ecc71', alpha=0.12, 
                   label=f'Rango Óptimo ({densidad_min:.2f} - {densidad_max:.2f})')
        
        # Líneas guías discontinuas en los bordes del KPI
        ax.axvline(densidad_min, color="#27ae60", linestyle='--', alpha=0.5, linewidth=1.2)
        ax.axvline(densidad_max, color='#27ae60', linestyle='--', alpha=0.5, linewidth=1.2)

        # Paleta de colores para diferenciar los camiones en caso de haber varios
        colores_camiones = ['#16a085', '#2980b9', '#8e44ad', '#f39c12']
        
        todos_los_x = [] # Guardará todas las densidades para ajustar el límite del eje X al final
        todas_las_longitudes = [1.0] # Resguardo para evitar error en max() si viene vacío

        # ==========================================================
        # 2. PROCESAMIENTO Y TRAZADO DE CURVAS POR CAMIÓN
        # ==========================================
        for idx, cat in enumerate(datos_grupo):
            # 🟢 CONTROL DE ERRORES: Si 'cat' es un texto o no es un diccionario, lo saltamos de forma segura
            if not isinstance(cat, dict):
                print(f"⚠️ Advertencia: El elemento en el índice {idx} de datos_grupo no es un diccionario válido.")
                continue

            nombre_camion = str(cat.get('nombre_camion', f'Camión {idx+1}')).upper()
            densidades = cat.get('densidad', [])
            longitudes = cat.get('longitud', [])
            interop_val = cat.get('interop', None)

            if len(densidades) == 0 or len(longitudes) == 0:
                continue

            todos_los_x.extend(densidades)
            todas_las_longitudes.extend(longitudes)
            
            color_actual = colores_camiones[idx % len(colores_camiones)]

            # A) Trazar la curva de este camión específico
            ax.plot(densidades, longitudes, color=color_actual, linewidth=2.5, label=f'Perfil {nombre_camion}')

            # B) Evaluar y pintar el punto interactivo de control sobre esta curva
            # Validamos si el valor ingresado entra dentro del rango simulado del taladro
            if longitud_carga_usuario <= max(longitudes):
                # Si no calculaste previamente la interpolación en tu modelo, la hacemos en caliente:
                if interop_val is None:
                    interop_val = float(np.interp(longitud_carga_usuario, longitudes, densidades))

                # Pintar marcador circular sobre la curva
                ax.scatter(interop_val, longitud_carga_usuario, 
                           color=color_actual, s=80, zorder=5, edgecolors='black')
                
                # Proyectar línea guía punteada horizontal hacia el margen izquierdo
                ax.plot([0.5, interop_val], [longitud_carga_usuario, longitud_carga_usuario], 
                        color=color_actual, linestyle=':', alpha=0.5, linewidth=1.0)
                
                # Desplazar alternadamente los textos si es el segundo camión para que no se pisen
                desplazamiento_x = 15 if idx % 2 == 0 else -65
                desplazamiento_y = -15 if idx % 2 == 0 else 15

                # Cuadro informativo flotante al lado del punto de control
                texto_anotacion = f"{nombre_camion}\n{interop_val:.2f} g/cc a {longitud_carga_usuario:.1f}m"
                ax.annotate(texto_anotacion, 
                            xy=(interop_val, longitud_carga_usuario),
                            xytext=(desplazamiento_x, desplazamiento_y),
                            textcoords='offset points',
                            fontsize=13, fontweight='bold', color='white',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor=color_actual, alpha=0.85, edgecolor='none', zorder=6),
                            arrowprops=dict(arrowstyle='->', color=color_actual, lw=1, alpha=0.7))

        # ==========================================================
        # 3. COMPORTAMIENTO ESTÉTICO, FORMATO E INVERSIÓN
        # ==========================================================
        # Invertir el eje Y para simular la bajada al fondo del pozo
        ax.invert_yaxis()

        ax.set_title('PERFIL DE DENSIDAD EN PROFUNDIDAD', fontweight='bold', fontsize=14, pad=12)
        ax.set_xlabel('Densidad (g/cc)', fontweight='bold', fontsize=13)
        ax.set_ylabel('Longitud de Carga (m)', fontweight='bold', fontsize=13)
        ax.grid(True, linestyle=':', alpha=0.5)

        # Ajuste inteligente de límites en base a los datos recolectados
        if todos_los_x:
            ax.set_xlim(min(todos_los_x) - 0.08, max(todos_los_x) + 0.08)
        else:
            ax.set_xlim(0.6, 1.5)

        # Añadir leyenda de identificación abajo en el centro
        ax.legend(loc='lower center', fontsize=12, framealpha=0.9, ncol=1)
        ax.tick_params(axis='both', which='major', labelsize=12)

        # ==========================================================
        # 4. GUARDADO DE IMAGEN CON MARCA DE TIEMPO ÚNICA
        # ==========================================================
        if not os.path.exists("./recursos"): 
            os.makedirs("./recursos")
        
        # Le añadí un timestamp para evitar que el PDF cargue una versión antigua en caché de disco
        ruta_temp = f"./recursos/dash_vert_camion_rioflex_prof_.png"
        fig.savefig(ruta_temp, dpi=150, bbox_inches='tight', transparent=True)
        plt.close(fig)
        
        return ruta_temp

    def generar_mapa_global_camiones_rioflex(self, datos_rioflex, datos_taladros,dia_carga):

        import matplotlib.pyplot as plt
        import matplotlib.patheffects as path_effects
        import os
        import time

        fig, ax = plt.subplots(figsize=(12, 7.0)) # Lienzo grande y panorámico

        # Fondo completamente transparente
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        # 1. Traer nombres de camiones desde la BD
        diccionario_camiones = self.datos_mysql.get("camion_fabrica", {})
        mapa_camiones = { str(d["id"]): str(nombre).upper() for nombre, d in diccionario_camiones.items() }

        # 2. Cruzar datos: Crear un diccionario { 'taladro': 'NOMBRE DEL CAMIÓN' }
        taladros_muestreados = {}
        
        if not datos_rioflex:
            print("🚨 ERROR: datos_anfo está vacío. No hay datos crudos para este ID de voladura.")
            
        for fila in datos_rioflex:
            # 🟢 Buscamos el nombre del pozo en diferentes posibles columnas
            tal = str(fila.get('taladro', fila.get('pozo', fila.get('id_pozo', fila.get('label', ''))))).strip().lower()
            id_cam = str(fila.get('id_camion', ''))
            
            if tal and id_cam:
                taladros_muestreados[tal] = mapa_camiones.get(id_cam, f"CAMIÓN {id_cam}")
        
        print(f"✅ Taladros muestreados encontrados en BD: {list(taladros_muestreados.keys())}")

        # 3. Separar las coordenadas de la malla
        x_fondo, y_fondo, labels_fondo = [], [], []
        x_medidos_reales, y_medidos_reales = [], []
        datos_por_camion = {} 
        
        nombres_malla_debug = [] # Para ver qué hay realmente en la malla

        is_dict = isinstance(datos_taladros, dict)
        taladros_iterables = datos_taladros.items() if is_dict else enumerate(datos_taladros)

        for clave, t in taladros_iterables:
            if not isinstance(t, dict): continue
            
            t_clean = {str(k).lower(): v for k, v in t.items()}
            
            # 🟢 EXTRACCIÓN SÚPER AGRESIVA DEL NOMBRE EN LA MALLA
            lbl_candidato = str(t_clean.get('label', t_clean.get('pozo', t_clean.get('nombre', t_clean.get('id', ''))))).strip()
            if not lbl_candidato and is_dict:
                lbl_candidato = str(clave).strip()
                
            lbl_original = lbl_candidato
            lbl_lower = lbl_original.lower()
                
            try:
                # Buscamos 'x', si no está buscamos 'este', si no 'easting'
                x_val = float(t_clean.get('x', t_clean.get('coorx_t', t_clean.get('coorx_t', 0.0))) or 0.0)
                y_val = float(t_clean.get('y', t_clean.get('coory_t', t_clean.get('coory_t', 0.0))) or 0.0)
            except ValueError:
                continue
                
            if x_val == 0.0 and y_val == 0.0:
                # print(f"⚠️ Omite taladro '{lbl_original}' porque no tiene coordenadas válidas.")
                continue
                
            # ¿Este taladro fue muestreado?
            if lbl_lower in taladros_muestreados:
                camion = taladros_muestreados[lbl_lower]
                #print("CAMION: ",camion)
                
                if camion not in datos_por_camion:
                    datos_por_camion[camion] = {'x': [], 'y': [], 'labels': []}
                    
                datos_por_camion[camion]['x'].append(x_val)
                datos_por_camion[camion]['y'].append(y_val)
                datos_por_camion[camion]['labels'].append(lbl_original)
                
                x_medidos_reales.append(x_val)
                y_medidos_reales.append(y_val)
            else:
                # Taladro normal de la malla
                x_fondo.append(x_val)
                y_fondo.append(y_val)
                labels_fondo.append(lbl_original)

        # Mecanismo de seguridad
        if not x_medidos_reales:
            print("🚨 ERROR: No hubo cruce. Los taladros medidos no coinciden con los de la malla.")
            print(f"🕵️‍♂️ Los primeros 15 taladros que el sistema encontró en tu malla son: {nombres_malla_debug}")
            print("--- FIN DEBUG ---")
            plt.close(fig)
            return None
            
        print(f"✅ ¡Cruce exitoso! Se dibujarán {len(x_medidos_reales)} taladros muestreados.")
     
        # 4. Encontrar el Centroide para la cámara
        x_centro = sum(x_medidos_reales) / len(x_medidos_reales)
        y_centro = sum(y_medidos_reales) / len(y_medidos_reales)

        # Calcular zoom dinámico
        radio_zoom_x, radio_zoom_y = 80, 50
        max_dist_x = max([abs(x - x_centro) for x in x_medidos_reales]) + 15
        max_dist_y = max([abs(y - y_centro) for y in y_medidos_reales]) + 15
        
        radio_zoom_x = max(radio_zoom_x, max_dist_x)
        radio_zoom_y = max(radio_zoom_y, max_dist_y)

        # 5. DIBUJAR TALADROS DE FONDO (Grises)
        x_fondo_rel = [x - x_centro for x in x_fondo]
        y_fondo_rel = [y - y_centro for y in y_fondo]
        
        # Filtramos para dibujar solo los que están dentro de la cámara
        x_f_plot, y_f_plot, lbl_f_plot = [], [], []
        for i in range(len(x_fondo_rel)):
            if abs(x_fondo_rel[i]) <= radio_zoom_x and abs(y_fondo_rel[i]) <= radio_zoom_y:
                x_f_plot.append(x_fondo_rel[i])
                y_f_plot.append(y_fondo_rel[i])
                lbl_f_plot.append(labels_fondo[i])

        if x_f_plot:
            ax.scatter(x_f_plot, y_f_plot, color="#e6e6e6", edgecolors="none", s=140, zorder=2)
            for i in range(len(x_f_plot)):
                ax.text(x_f_plot[i], y_f_plot[i], lbl_f_plot[i], ha='center', va='center', 
                        fontsize=6, color="#000000", zorder=3)

        # 6. DIBUJAR TALADROS MUESTREADOS (Un color por camión)
        colores_camiones = ["#ff7c6e", "#51a7e0", "#67e99d", "#f1ad41", "#b864db", "#ca6f33"]
        
        # Efecto de borde blanco para que las letras destaquen
        efecto_borde = [path_effects.withStroke(linewidth=2, foreground='white')]

        for index, (camion, datos) in enumerate(datos_por_camion.items()):
            color_actual = colores_camiones[index % len(colores_camiones)]
            
            x_rel = [x - x_centro for x in datos['x']]
            y_rel = [y - y_centro for y in datos['y']]
            lbls = datos['labels']
            
            # Dibujar los puntos del camión
            ax.scatter(x_rel, y_rel, color=color_actual, edgecolors='none', s=240, zorder=4, label=camion)
            
            # Etiquetar cada punto
            for i in range(len(x_rel)):
                # Número del taladro
                ax.text(x_rel[i], y_rel[i], lbls[i], ha='center', va='center', 
                        fontsize=12, color='black', fontweight='bold', zorder=5)

        # 7. ESTÉTICA Y LÍMITES
        ax.set_xlim(-radio_zoom_x, radio_zoom_x)
        ax.set_ylim(-radio_zoom_y, radio_zoom_y)
        ax.set_aspect('equal') 
        ax.axis('off') # Apagamos ejes

        # Leyenda oficial (Cuadro con los colores de los camiones)
        ax.legend(loc='upper right', title="CAMIONES", fontsize=10, title_fontsize=12,
                  facecolor='white', framealpha=0.9, edgecolor='#ccc', markerscale=0.4)

        # Título en la esquina
        ax.text(0.05, 1.02 , "MAPA GLOBAL DE MUESTREO DE DENSIDAD", transform=ax.transAxes, 
                fontsize=16, fontweight='bold',ha='center', va='top', color='#333', 
                bbox=dict(facecolor='white', alpha=0.9, edgecolor='none'))

        if not os.path.exists("./recursos"): os.makedirs("./recursos")
        ruta = f"./recursos/mapa_global_densidad_rioflex_{dia_carga}.png"
        fig.savefig(ruta, dpi=220, bbox_inches='tight', transparent=True)
        plt.close(fig)
        
        return ruta




