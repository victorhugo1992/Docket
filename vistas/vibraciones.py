import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import csv

# Librerías para incrustar gráficos en Tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class VistaVibraciones(tk.Frame):
    def __init__(self, parent, id_vola, proyecto, database,datos, callback_actualizar=None):
        super().__init__(parent)

        self.id_vola = id_vola
        self.proyecto = proyecto
        self.database = database
        self.datos= datos
        self.datos_mysql = datos.obtener_datos_mysql()
        #print(self.database)
        self.root = parent # Para los Toplevel (Calendario/Comentarios)
        self.callback_actualizar = callback_actualizar # Lo guardas

        #self.controlador = controlador
        self.ruta_actual_csv = ""  
        self.metadata_sismo = {} # También aseguramos esta por si acaso

        self.setup_ui()

    def setup_ui(self):
        """Construye la interfaz visual de la pestaña de Vibraciones."""
        # --- Título y Botones Superiores ---
        frame_top = tk.Frame(self)
        frame_top.pack(fill="x", pady=10, padx=10)
        
        tk.Label(frame_top, text="Análisis de Vibraciones (Sismografía)", font=("Arial", 14, "bold")).pack(side="left")
        
        btn_importar = tk.Button(frame_top, text="📈 Importar CSV Instantel", bg="#0070C0", fg="white", font=("Arial", 10, "bold"), command=self.accion_importar_instantel)
        btn_importar.pack(side="right", padx=5)

        # --- Panel de Resultados (Metadata) ---
        self.frame_info = tk.LabelFrame(self, text="Resultados del Evento", font=("Arial", 11, "bold"), padx=10, pady=10)
        self.frame_info.pack(fill="x", padx=10, pady=5)
        
        # Etiquetas variables para mostrar los datos extraídos
        self.var_tran = tk.StringVar(value="Transversal: -- mm/s a -- Hz")
        self.var_vert = tk.StringVar(value="Vertical: -- mm/s a -- Hz")
        self.var_long = tk.StringVar(value="Longitudinal: -- mm/s a -- Hz")
        self.var_mic = tk.StringVar(value="Micrófono: -- pa a -- Hz")

        tk.Label(self.frame_info, textvariable=self.var_tran, font=("Arial", 10), fg="#0070C0").grid(row=0, column=0, padx=20, sticky="w")
        tk.Label(self.frame_info, textvariable=self.var_vert, font=("Arial", 10), fg="#28a745").grid(row=0, column=1, padx=20, sticky="w")
        tk.Label(self.frame_info, textvariable=self.var_long, font=("Arial", 10), fg="#dc3545").grid(row=0, column=2, padx=20, sticky="w")
        tk.Label(self.frame_info, textvariable=self.var_mic, font=("Arial", 10), fg="purple").grid(row=0, column=3, padx=20, sticky="w")


        # --- Panel de Datos de Campo y Diseño ---
        frame_inputs = tk.LabelFrame(self, text="Datos Operativos y de Diseño", font=("Arial", 11, "bold"), padx=10, pady=10)
        frame_inputs.pack(fill="x", padx=10, pady=5)

        # 👇 ESTA ES LA LÍNEA QUE FALTA O QUE SE BORRÓ
        self.entradas_sismo = {} 

        campos = [
            ("Distancia (m):", "distancia"), 
            ("Carga Operante (kg):", "carga"), 
            ("VPP Diseño (mm/s):", "vpp"), 
            ("Factor K:", "k"), 
            ("Factor Alpha:", "alpha")
        ]

        for i, (label_text, key) in enumerate(campos):
            tk.Label(frame_inputs, text=label_text, font=("Arial", 10)).grid(row=0, column=i*2, padx=(15, 2), sticky="e")
            entry = tk.Entry(frame_inputs, width=10, font=("Arial", 10), justify="center")
            entry.grid(row=0, column=i*2+1, padx=5, sticky="w")
            
            # Aquí es donde guardamos el input en la caja que acabamos de crear arriba
            self.entradas_sismo[key] = entry

        # --- Selector de Punto de Monitoreo ---
        frame_monitoreo = tk.Frame(frame_inputs)
        frame_monitoreo.grid(row=1, column=0, columnspan=10, pady=10, sticky="w")
        
        tk.Label(frame_monitoreo, text="Punto de Monitoreo:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        self.combo_punto = ttk.Combobox(frame_monitoreo, state="readonly", width=25)
        self.combo_punto.pack(side="left", padx=5)
        
        # Botón para detonar el cálculo automático
        #btn_calc_dist = tk.Button(frame_monitoreo, text="🎯 Calcular Distancia desde CG", bg="#17a2b8", fg="white", command=self.calcular_distancia_cg)
        #btn_calc_dist.pack(side="left", padx=10)

        # Cargar los puntos de monitoreo desde la BD al abrir la ventana
        self.cargar_puntos_en_combo()
        
        # --- Botón Guardar Sismografía ---
        self.btn_guardar = tk.Button(
            frame_top, # Asegúrate de que apunte al marco donde están tus cajas de texto
            text="💾 Guardar Sismografía", 
            bg="#28a745", # Color verde estilo éxito
            fg="white", 
            font=("Arial", 10, "bold"), 
            command=self.accion_guardar_sismografia
        )
        # Lo ubicamos en la columna 10 para que quede a la derecha de los 5 inputs (que ocupan las columnas 0 a 9)
        self.btn_guardar.pack(side="right", padx=5)

        # --- Contenedor del Gráfico (Sismograma) ---
        self.frame_grafico = tk.Frame(self, bg="white", bd=2, relief="groove")
        self.frame_grafico.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Etiqueta inicial antes de cargar el gráfico
        tk.Label(self.frame_grafico, text="Importa un archivo CSV de Instantel para visualizar el sismograma.", fg="gray").pack(expand=True)

        self.cargar_datos_desde_bd()

    # ==========================================
    # LÓGICA DE IMPORTACIÓN Y PROCESAMIENTO
    # ==========================================
    def accion_importar_instantel(self):
        """Abre el explorador para buscar el CSV del Instantel."""
        self.ruta_actual_csv = filedialog.askopenfilename(
            title="Seleccionar CSV de Instantel",
            filetypes=(("Archivos CSV", "*.csv *.CSV"), ("Todos los archivos", "*.*"))
        )
        
        if not self.ruta_actual_csv: return 
        self.procesar_csv_instantel(self.ruta_actual_csv)

    def procesar_csv_instantel(self, file_path):
        """Lee la metadata y los datos del sismograma sin recalcular la matemática pesada."""
        metadata = {}
        data_start_row = 0
        
        try:
            # 1. Leer Metadata (Cabecera del CSV)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if len(row) >= 2:
                        if row[0] == "SampleRate":
                            metadata["SampleRate"] = float(row[1].replace(" sps", "").strip())
                        elif "PPV" in row[0] or "Freq" in row[0]:
                            metadata[row[0]] = row[1]
                    
                    # Detectar dónde inician los datos de onda
                    if len(row) >= 3 and row[0] == "Tran" and row[1] == "Vert" and row[2] == "Long":
                        data_start_row = i
                        break
            
            # 2. Extraer datos para el panel de información
            s_rate = metadata.get("SampleRate", 1024)
            self.var_tran.set(f"Transversal: {metadata.get('TranPPV', '--')} a {metadata.get('TranZCFreq', '--')}")
            self.var_vert.set(f"Vertical: {metadata.get('VertPPV', '--')} a {metadata.get('VertZCFreq', '--')}")
            self.var_long.set(f"Longitudinal: {metadata.get('LongPPV', '--')} a {metadata.get('LongZCFreq', '--')}")
            self.var_mic.set(f"Micrófono: {metadata.get('MicPSPL', '--')} a {metadata.get('MicZCFreq', '--')}")

            # 3. Leer los datos de onda usando Pandas (saltando la metadata)
            df = pd.read_csv(file_path, skiprows=data_start_row)
            
            # 4. Crear el eje de Tiempo (X) usando la frecuencia de muestreo
            dt = 1.0 / s_rate
            df['Time'] = np.arange(len(df)) * dt
            
            # 5. Dibujar el gráfico
            self.dibujar_sismogramas(df)
            
        except Exception as e:
            messagebox.showerror("Error de Lectura", f"No se pudo procesar el archivo CSV.\n{e}")

    def dibujar_sismogramas(self, df):
        """Dibuja los canales y los incrusta en el frame de Tkinter."""
        # Limpiar el gráfico/texto anterior
        for widget in self.frame_grafico.winfo_children():
            widget.destroy()
            
        # Crear figura de Matplotlib
        fig, axs = plt.subplots(3, 1, figsize=(10, 6), sharex=True)
        fig.subplots_adjust(hspace=0.4, left=0.08, right=0.98, top=0.95, bottom=0.1) 
        
        # Canal Transversal
        axs[0].plot(df['Time'], df['Tran'], color='#0070C0', linewidth=0.8)
        axs[0].set_ylabel('Tran\n(mm/s)', fontsize=9, fontweight='bold')
        axs[0].grid(True, linestyle='--', alpha=0.6)
        
        # Canal Vertical
        axs[1].plot(df['Time'], df['Vert'], color='#28a745', linewidth=0.8)
        axs[1].set_ylabel('Vert\n(mm/s)', fontsize=9, fontweight='bold')
        axs[1].grid(True, linestyle='--', alpha=0.6)
        
        # Canal Longitudinal
        axs[2].plot(df['Time'], df['Long'], color='#dc3545', linewidth=0.8)
        axs[2].set_ylabel('Long\n(mm/s)', fontsize=9, fontweight='bold')
        axs[2].set_xlabel('Tiempo (segundos)', fontsize=10, fontweight='bold')
        axs[2].grid(True, linestyle='--', alpha=0.6)
        
        # Incrustar en Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def accion_guardar_sismografia(self):
        """Recopila los datos manuales y los del Instantel para guardarlos."""
        # 1. Validar que exista una voladura
        if not hasattr(self, 'id_vola') or not self.id_vola:
            messagebox.showwarning("Atención", "No hay una voladura seleccionada.")
            return

        # 2. Extraer los datos MANUALES de los inputs 
        def obtener_valor(key):
            val = self.entradas_sismo[key].get().strip()
            return float(val) if val else None

        try:
            dist = obtener_valor("distancia")
            carga = obtener_valor("carga")
            vpp = obtener_valor("vpp")
            k = obtener_valor("k")
            alpha = obtener_valor("alpha")
        except ValueError:
            messagebox.showerror("Error", "Ingresa solo números válidos (usa punto para decimales).")
            return

        # 3. Extraer los datos AUTOMÁTICOS del Instantel (si se cargó el CSV)
        # Limpiamos el " mm/s" o " Hz" para guardar solo el número en el DECIMAL de MySQL
        def extraer_numero(texto):
            if not texto: return None
            # Elimina letras y deja solo el número
            return float(''.join(c for c in texto if c.isdigit() or c == '.'))

        # Valores por defecto si no ha importado nada
        pvs = pvx = pvy = pvz = fx = fy = fz = None
        
        if hasattr(self, 'metadata_sismo'):

            # 🛡️ 1. Extraemos el ID del punto de monitoreo seleccionado
            id_punto_seleccionado = None
            seleccion_combo = self.combo_punto.get()
            
            if seleccion_combo and seleccion_combo != "No hay puntos registrados":
                # Buscamos ese nombre dentro de nuestra lista guardada para sacar su ID (posición 0)
                punto_encontrado = next((p for p in getattr(self, 'lista_puntos', []) if p[1] == seleccion_combo), None)
                if punto_encontrado:
                    id_punto_seleccionado = punto_encontrado[0]

            pvs = extraer_numero(self.metadata_sismo.get('PeakVectorSum'))
            pvx = extraer_numero(self.metadata_sismo.get('TranPPV'))
            pvy = extraer_numero(self.metadata_sismo.get('VertPPV'))
            pvz = extraer_numero(self.metadata_sismo.get('LongPPV'))
            
            fx = extraer_numero(self.metadata_sismo.get('TranZCFreq'))
            fy = extraer_numero(self.metadata_sismo.get('VertZCFreq'))
            fz = extraer_numero(self.metadata_sismo.get('LongZCFreq'))

            self.ruta_segura = getattr(self, 'ruta_actual_csv', "")

        # 4. Guardar TODO en la Base de Datos
        exito = self.datos.guardar_datos_sismografia(
            self.id_vola, 
            pvs, pvx, pvy, pvz, fx, fy, fz,  
            dist, carga, vpp, k, alpha,      
            self.ruta_actual_csv,
            id_punto_seleccionado
        )

        if exito:
             if self.callback_actualizar:
                self.callback_actualizar()
                messagebox.showinfo("Éxito", "Los datos operativos y lecturas del Instantel se han guardado correctamente.")
        else:
            messagebox.showerror("Error", "Ocurrió un problema al guardar en la base de datos. Revisa la consola.")

    def cargar_puntos_en_combo(self):
        """Descarga los puntos de la BD y los guarda en la memoria del programa."""
        self.lista_puntos = self.datos.obtener_puntos_monitoreo()
        
        if self.lista_puntos:
            # Creamos una lista solo con los nombres (ej: "Punto A")
            nombres = [punto[1] for punto in self.lista_puntos]
            self.combo_punto.config(values=nombres)
        else:
            self.combo_punto.set("No hay puntos registrados")

    def cargar_datos_desde_bd(self):
        """Busca datos guardados en MySQL y los carga automáticamente en la pantalla."""
        import os
        
        # 1. Consultar a la base de datos
        datos_guardados = self.datos.obtener_datos_sismografia(self.id_vola)
        
        if not datos_guardados:
            return # Si no hay datos guardados, no hacemos nada (es una voladura nueva)
            
        # 2. Desempaquetar los datos (el orden debe coincidir con el SELECT en datos_db.py)
        dist, carga, vpp, k, alpha, ruta,id_punto_db = datos_guardados
        
        # 3. Rellenar las cajas de texto (inputs)
        # Diccionario para mapear las variables con las llaves de tus inputs
        valores_a_insertar = {
            "distancia": dist,
            "carga": carga,
            "vpp": vpp,
            "k": k,
            "alpha": alpha
        }
        
        for key, valor in valores_a_insertar.items():
            if valor is not None:
                caja_texto = self.entradas_sismo[key]
                caja_texto.delete(0, tk.END)
                caja_texto.insert(0, str(valor))
                
        # 4. Cargar el CSV y dibujar el gráfico automáticamente

        # 👇 NUEVO: 3. Seleccionar el punto de monitoreo correcto en el Combobox
        if id_punto_db and hasattr(self, 'lista_puntos'):
            # Buscamos el nombre que corresponde a este ID
            punto_match = next((p for p in self.lista_puntos if str(p[0]) == str(id_punto_db)), None)
            if punto_match:
                self.combo_punto.set(punto_match[1]) # Ponemos el nombre (ej. "Punto Sur") en la cajita

        if ruta:
            # 🛡️ Blindaje: Verificar si el archivo aún existe en la computadora
            if os.path.exists(ruta):
                self.ruta_actual_csv = ruta # Guardamos la ruta en memoria
                print(f"🔄 Autocargando sismograma desde: {ruta}")
                
                # ¡Magia pura! Reutilizamos tu función que ya dibuja todo
                self.procesar_csv_instantel(ruta)
            else:
                # Si el usuario movió el archivo a otra carpeta o lo borró
                self.ruta_actual_csv = ""




