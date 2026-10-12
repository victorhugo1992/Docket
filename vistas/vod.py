import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from tkcalendar import Calendar
from scipy.signal import savgol_filter
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
from matplotlib.ticker import MultipleLocator
from scipy.stats import linregress
import os
from tkinter import messagebox
from fpdf import FPDF
from PIL import Image, ImageEnhance
from database.datos_db import marcar_medicion_completada,obtener_kpi_por_explosivo

class VistaVOD(tk.Frame):

    def __init__(self, parent, id_vola, proyecto, database,datos,taladros, callback_actualizar=None):
        super().__init__(parent)

        self.id_vola = id_vola
        self.proyecto = proyecto
        self.database = database
        self.datos= datos
        self.datos_mysql = datos.obtener_datos_mysql()
        self.taladros = taladros
        #print(self.database)
        self.root = parent # Para los Toplevel (Calendario/Comentarios)
        self.callback_actualizar = callback_actualizar # Lo guardas
        self.path=""
        
        self.setup_ui()

        # --- NUEVO: Cargamos datos si existen ---
        self.cargar_datos_existentes()

    def setup_ui(self):
        left_panel = tk.Frame(self.root, width=320, bg="#f1f2f6")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=30)

        left_panel2 = tk.Frame(self.root, width=320, bg="#f1f2f6")
        left_panel2.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=30)

        group_generales = tk.LabelFrame(left_panel, text="DATOS GENERALES", font=('Arial', 11, 'bold'), padx=10, pady=10)
        group_generales.pack(fill=tk.X, pady=5)

        group_design = tk.LabelFrame(left_panel2, text="DATOS DE DISEÑO", font=('Arial', 11, 'bold'), padx=10, pady=10)
        group_design.pack(fill=tk.X, pady=5)

        group_explosive = tk.LabelFrame(left_panel, text="DATOS DE EXPLOSIVO", font=('Arial', 11, 'bold'), padx=10, pady=10)
        group_explosive.pack(fill=tk.X, pady=5)

        group_grafico = tk.LabelFrame(left_panel2, text="DATOS DE GRAFICO", font=('Arial', 11, 'bold'), padx=10, pady=10)
        group_grafico.pack(fill=tk.X, pady=17)

        self.inputs_generales = {}
        self.inputs_design = {}
        self.inputs_explosive = {}
        self.inputs_grafico = {}

        # --- NUEVO: Extraer lista de taladros (Solo mostrar Label, guardar ID) ---
        self.lista_taladros = []
        self.mapa_taladros_id = {} # Diccionario: Label -> ID (Para guardar)
        self.mapa_id_a_label = {}  # Diccionario: ID -> Label (Para cargar)
        
        if hasattr(self, 'taladros') and self.taladros:
            for t in self.taladros:
                t_clean = {str(k).lower(): v for k, v in t.items()}
                
                lbl = str(t_clean.get('label', '')).strip()
                # Buscamos el ID (agregué una opción de respaldo por si tu BD lo llama 'id' en vez de 'idtaladro')
                id_tal = str(t_clean.get('idtaladro', '')).strip()
                if not id_tal: id_tal = str(t_clean.get('id', '')).strip()
                
                if lbl:
                    if lbl not in self.lista_taladros:
                        self.lista_taladros.append(lbl) # Solo agregamos el Label limpio al combobox
                    
                    if id_tal:
                        self.mapa_taladros_id[lbl] = id_tal
                        self.mapa_id_a_label[id_tal] = lbl
                    else:
                        self.mapa_taladros_id[lbl] = lbl
                        self.mapa_id_a_label[lbl] = lbl
                    
        self.lista_taladros = sorted(self.lista_taladros)

        fields_generales =[
            ("Controlado por:", "id_persona", list(self.datos_mysql.get("persona",{}).keys())[0],None),
            ("Fecha:", "fecha", "",None),
            ("N° de Voladura:", "nro_voladura", str(self.proyecto),None),
            ("Hora de Voladura:", "hora", "",None),
            ("Fase/Banco/Malla:", "fase_banco_malla", "",None),
            ("Taladro:", "taladro", "",None)
        ]

        fields_design = [
            ("Altura Banco (m):", "altura_banco", "11",None),
            ("Prof. Taladro (m):", "prof_taladro", "10",None),
            ("Diámetro (mm):", "diametro", "270",None),
            ("Booster (gr):", "booster", "900",None),
            ("Altura Carga (m):", "altura_carga", "5",None),
            ("Tipo de Taco:", "tipo_taco", "Detritus",None),
            ("Humedad:", "humedad", "Seco",None)
        ]

        fields_explosive = [
            ("Producto:", "id_explosivo", list(self.datos_mysql.get("explosivo",{}).keys())[0],None),
            ("Densidad (g/cc):", "densidad", "1.25",None),
            ("Camión Fábrica:", "id_camion", list(self.datos_mysql.get("camion_fabrica",{}).keys())[0],None),
            ("Peso Exp. (Kg):", "peso_exp", "120",None),
            ("Iniciación:", "iniciacion", "ELECTRONICO",None),
        ]

        fields_grafico = [
            ("LÍMITE VOD (m):", "limite_vod", "9.5",None), # Clave necesaria para run_analysis
            ("Inicio Probecable (m):", "inicio_probecable", "-4",None), 
            ("Altura Booster (cm):", "altura_booster", "40.0",None),
            ("Continuidad del Handy:", "continuidad_handy", "SI",None),
            ("Paso Ticks Prof. (m):", "paso_ticks_prof", "0.20",None),
            ("VOD Mín. Global:", "vod_min_global", "3000",None),
            ("VOD Máxima Global (m/s):", "vod_max_global", "6000",None),
            ("Long. Cable Coaxial:", "long_cable_coaxial", "50",None)
        ]

        # Definimos qué campos usarán Combobox y de qué lista del JSON vienen
        base = {
            "id_persona": list(self.datos_mysql.get("persona",{}).keys()),
            "taladro": self.lista_taladros,
            "continuidad_handy": ["SI","NO"],
            "diametro":["200","251","270","279","311"],
            "booster":["450","900"],
            "id_camion": list(self.datos_mysql.get("camion_fabrica",{}).keys()),
            "id_explosivo": list(self.datos_mysql.get("explosivo",{}).keys()),
            "humedad": self.datos_mysql.get("condicion_taladro",[]),
            "tipo_taco": ["DETRITUS","GRAVILLA"],
            "iniciacion": ["CONVENCIONAL","ELECTRONICO"]
        }

        #print(base)

        # DISTRIBUCIÓN EN DOS COLUMNAS
        # Calculamos la mitad para saber cuándo saltar a la siguiente columna
        mitad_generales = (len(fields_generales) + 1)
        #mitad_design = (len(fields_design) + 1) 
        #mitad_explosive = (len(fields_explosive) + 1)
        #mitad_grafico = (len(fields_grafico) + 1)

        hora_actual = datetime.now().strftime("%H:%M")

        for i, (label, key, default,opciones) in enumerate(fields_generales):
            col_base = 0
            row_idx = i
 
            tk.Label(group_generales, text=label, font=('Arial', 10)).grid(row=row_idx, column=col_base, sticky="w", pady=1)

            if key in base:
                ent = ttk.Combobox(group_generales, values = base[key],width=15,state="readonly")
                ent.set(default)
                ent.grid(row=row_idx, column=col_base + 1, pady=1, padx=2)

            elif key == "fecha":
                frame_fecha = tk.Frame(group_generales)
                frame_fecha.grid(row=row_idx, column=col_base+1, padx=5, pady=2, sticky="w")
                ent = tk.Entry(frame_fecha, width=15, justify='center')
                ent.insert(0, datetime.now().strftime("%d-%m-%Y"))
                ent.pack(side="left")
                
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

            elif key =="hora":
                ent = tk.Entry(group_generales, width=15, justify='center')
                ent.insert(0, datetime.now().strftime("%H:%M"))
                ent.grid(row=row_idx, column=col_base + 1, pady=1, padx=2)

            else:
                ent = tk.Entry(group_generales, width=15, justify='center')
                ent.insert(0, default)
                ent.grid(row=row_idx, column=col_base + 1, pady=1, padx=2)
            
            self.inputs_generales[key] = ent
            
        for i, (label, key, default,opciones) in enumerate(fields_design):
            col_base = 0
            row_idx = i
            tk.Label(group_design, text=label, font=('Arial', 10)).grid(row=row_idx, column=col_base, sticky="w", pady=1)

            if key in base:
                ent = ttk.Combobox(group_design, values = base[key],width=15,state="readonly")
                ent.set(default)
            else:
                ent = tk.Entry(group_design, width=15, justify='center')
                ent.insert(0, default)

            ent.grid(row=row_idx, column=col_base + 1, pady=1, padx=2)
            self.inputs_design[key] = ent

        for i, (label, key, default,opciones) in enumerate(fields_explosive):
            col_base = 0
            row_idx = i
            tk.Label(group_explosive, text=label, font=('Arial', 10)).grid(row=row_idx, column=col_base, sticky="w", pady=1)

            if key in base:
                ent = ttk.Combobox(group_explosive, values = base[key],width=15,state="readonly")
                ent.set(default)
            else:
                ent = tk.Entry(group_explosive, width=15, justify='center')
                ent.insert(0, default)

            ent.grid(row=row_idx, column=col_base + 1, pady=1, padx=2)
            self.inputs_explosive[key] = ent

        self.val_continuidad = tk.StringVar(value=default)

        for i, (label, key, default,opciones) in enumerate(fields_grafico):
            col_base = 0
            row_idx = i
            tk.Label(group_grafico, text=label, font=('Arial', 10)).grid(row=row_idx, column=col_base, sticky="w", pady=1)

            if key in base:
                ent = ttk.Combobox(group_grafico, values = base[key],width=15,state="readonly",textvariable=self.val_continuidad)
                ent.set(default)
                ent.grid(row=row_idx, column=col_base + 1, pady=1, padx=2)

                if key == "continuidad_handy":
                    self.comentarios_handy=""
                    
                    def abrir_ventana_comentarios():
                        # Crear una pequeña ventana emergente
                        ventana_obs = tk.Toplevel(self.root)
                        ventana_obs.title("Observaciones")
                        ventana_obs.geometry("300x300")
                        ventana_obs.configure(bg="#f1f2f6")
                        
                        # 🟢 1. FORZAR ENFOQUE (Solución para Mac)
                        ventana_obs.transient(self.root) # Mantiene la ventanita siempre encima de la principal
                        ventana_obs.grab_set()           # Bloquea la ventana de atrás para que no le des clic por error
                        ventana_obs.focus_force()        # Obliga al sistema operativo a mirar esta ventana

                        tk.Label(ventana_obs, text="Detalla la razón de la falla:", bg="#f1f2f6", font=('Arial', 11, 'bold')).pack(pady=5)
                        
                        # Caja de texto grande
                        caja_texto = tk.Text(ventana_obs, height=10, width=60)
                        caja_texto.pack( padx=10,pady=5)
                        
                        # Si ya había escrito algo antes, se lo mostramos
                        if hasattr(self, 'comentarios_handy'):
                            caja_texto.insert("1.0", self.comentarios_handy)
                            
                        # 🟢 2. PONER EL CURSOR DENTRO DE LA CAJA AUTOMÁTICAMENTE
                        caja_texto.focus_set()
                            
                        def guardar_obs():
                            # Guardamos lo que escribió en nuestra variable segura
                            self.comentarios_handy = caja_texto.get("1.0", tk.END).strip()
                            
                            # 🟢 3. SOLTAR EL BLOQUEO ANTES DE CERRAR
                            ventana_obs.grab_release()
                            ventana_obs.destroy()
                            
                        tk.Button(ventana_obs, text="Guardar", command=guardar_obs, bg="#27ae60", fg="black").pack(padx=20,pady=6)

                        #ttk.Button(top,text="Guardar Comentarios",command=guardar).pack(pady=5)

                    btn_coment= ttk.Button(group_grafico, text="💬", width=3, command=abrir_ventana_comentarios)

                    # Función para mostrar/ocultar el botón según la selección
                    def verificar_handy(*args):
                        if self.val_continuidad.get() == "NO":
                            #print("Hola presionaste NO")
                            btn_coment.grid(row=row_idx, column=4, padx=1)
                        else:
                            btn_coment.grid_remove()
                            self.comentarios_handy = "" # Limpia si cambian a SI

                    ent.bind("<<ComboboxSelected>>", verificar_handy)

                    # 3. Ponemos el rastreador: ejecuta 'verificar_handy' cada vez que escriba ('w') en la variable
                    self.val_continuidad.trace_add("write", verificar_handy)

                    verificar_handy()

            else:
                ent = tk.Entry(group_grafico, width=15, justify='center')
                ent.insert(0, default)
                ent.grid(row=row_idx, column=col_base + 1, pady=1, padx=2)


            #ent = tk.Entry(group_grafico, width=12, justify='center')
            #ent.insert(0, default)
            
            self.inputs_grafico[key] = ent

        tk.Label(group_grafico, text="Suavizado (Ventana):", fg="blue").grid(row=len(fields_grafico), column=0, sticky="w")
        self.slider_smooth = tk.Scale(group_grafico, from_=5, to=201, orient=tk.HORIZONTAL)
        self.slider_smooth.set(99)
        self.slider_smooth.grid(row=len(fields_grafico), column=1, sticky="ew")

        # --- MODIFICADO: CAJAS DE TEXTO PARA ZOOM TEMPORAL ---
        group_zoom = tk.LabelFrame(left_panel, text="AJUSTE DOMINIO", font=('Arial', 11, 'bold'), padx=10, pady=10, fg="#e67e22")
        group_zoom.pack(fill=tk.X, pady=5)

        tk.Label(group_zoom, text="T. Inicial:").grid(row=0, column=0, sticky="w")
        self.zoom_min_ent = tk.Entry(group_zoom, width=15, justify='center')
        self.zoom_min_ent.insert(0, "-0.25")
        self.zoom_min_ent.grid(row=0, column=1, pady=3, padx=5)
        self.zoom_min_ent.bind("<Return>", lambda e: self.update_plots_only())

        tk.Label(group_zoom, text="T. Final:").grid(row=1, column=0, sticky="w")
        self.zoom_max_ent = tk.Entry(group_zoom, width=15, justify='center')
        self.zoom_max_ent.insert(0, "1.0")
        self.zoom_max_ent.grid(row=1, column=1, pady=3, padx=5)
        self.zoom_max_ent.bind("<Return>", lambda e: self.update_plots_only())

        #group_colors = tk.LabelFrame(left_panel, text="RANGOS DE DESEMPEÑO", font=('Arial', 9, 'bold'), padx=10, pady=5, fg="#2980b9")
        #group_colors.pack(fill=tk.X, pady=5)   

        tk.Label(group_zoom, text="VOD Mín. Óptima:").grid(row=2, column=0, sticky="w")
        self.entry_ok_min = tk.Entry(group_zoom, width=15, justify='center', fg="#27ae60", font=('Arial', 11, 'bold'))
        self.entry_ok_min.insert(0, "4000");
        self.entry_ok_min.grid(row=2, column=1, pady=2, padx=5)

        tk.Label(group_zoom, text="VOD Máx. Óptima:").grid(row=3, column=0, sticky="w")
        self.entry_ok_max = tk.Entry(group_zoom, width=15, justify='center', fg="#2A6E34", font=('Arial', 11, 'bold'))
        self.entry_ok_max.insert(0, "6500"); 
        self.entry_ok_max.grid(row=3, column=1, pady=2, padx=5)

        # --- EVENTO: ACTUALIZAR KPIs AL CAMBIAR EXPLOSIVO ---

        # 🟢 Asociamos la función al evento de cambio en el combobox del Producto
        self.inputs_explosive['id_explosivo'].bind("<<ComboboxSelected>>", self.actualizar_kpis)
        
        # 🟢 La ejecutamos una vez manualmente para que cargue los datos al abrir la ventan


        tk.Button(left_panel, text="IMPORTAR CSV", command=self.load_csv, 
                bg="white", fg="black", font=('Arial', 11, 'bold'), height=2).pack(fill=tk.X, pady=10)

        tk.Button(left_panel, text="ANALIZAR VOD", command=self.run_analysis, 
                bg="white", fg="black", font=('Arial', 11, 'bold'), height=2).pack(fill=tk.X, pady=10)
        
        tk.Button(left_panel2, text="GUARDAR DATOS", command=self.guardar_datos_vod, 
                bg="white", fg="black", font=('Arial', 11, 'bold'), height=2).pack(fill=tk.X, pady=10)
        
        tk.Button(left_panel2, text="GENERAR PDF", command=self.create_pdf_header, 
                bg="white", fg="black", font=('Arial', 11, 'bold'), height=2).pack(fill=tk.X, pady=10)

        self.right_panel = tk.Frame(self.root, bg="white")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=30)
        #left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=30)
        self.right_panel.columnconfigure(0, weight=3); self.right_panel.columnconfigure(1, weight=2)
        self.right_panel.rowconfigure(0, weight=1); self.right_panel.rowconfigure(1, weight=1)

        self.actualizar_kpis()

    def actualizar_kpis(self,event=None):
            # 1. Obtenemos el nombre visual del explosivo seleccionado
            nombre_exp = self.inputs_explosive['id_explosivo'].get()
            
            # 2. Rescatamos el paquete de datos de ese explosivo desde el diccionario general
            dict_exp = self.datos_mysql.get("explosivo", {}).get(nombre_exp)
            
            # Si no hay datos registrados para ese explosivo, detenemos la función
            if not dict_exp:
                return 
                
            # Extraemos su ID numérico
            id_real_explosivo = dict_exp.get("idexplosivo")
            
            # 3. Llamamos a la base de datos para obtener los límites
            if hasattr(self.datos, 'obtener_kpi_por_explosivo'):
                kpis = self.datos.obtener_kpi_por_explosivo(id_real_explosivo)
                
                # 4. Actualizamos la interfaz con los datos traídos
                if kpis:
                    # Rellenar VOD Mínima
                    if kpis.get('vod_minimo') is not None:
                        self.entry_ok_min.delete(0, tk.END)
                        self.entry_ok_min.insert(0, str(int(kpis['vod_minimo'])))
                        
                    # Rellenar VOD Máxima
                    if kpis.get('vod_maximo') is not None:
                        self.entry_ok_max.delete(0, tk.END)
                        self.entry_ok_max.insert(0, str(int(kpis['vod_maximo'])))
                        
                    # Rellenar Densidad Mínima
                    #if kpis.get('densidad_minima') is not None:
                    #    self.inputs_explosive['densidad'].delete(0, tk.END)
                    #    self.inputs_explosive['densidad'].insert(0, str(kpis['densidad_minima']))

    def run_analysis(self):
        if self.df is None: return
        t_ms = self.df['t'].values
        l_csv = self.df['l'].values.copy()
        l_calc = l_csv.copy()
        for j in range(1, len(l_calc)):
            if l_calc[j] < l_calc[j-1] - 0.05: l_calc[j] = l_calc[j-1]
        
        win = self.slider_smooth.get()
        if win % 2 == 0: win += 1
        l_smooth = savgol_filter(l_calc, win, 3)
        dt = np.gradient(t_ms); dt[dt == 0] = 1e-9
        v_inst = (np.gradient(l_smooth) / dt) * 1000.0
        
        lim_l = float(self.inputs_grafico['limite_vod'].get())
        vmin_g = float(self.inputs_grafico['vod_min_global'].get()) 
        vmax_g = float(self.inputs_grafico['vod_max_global'].get())
        ok_min = float(self.entry_ok_min.get()); 
        ok_max = float(self.entry_ok_max.get())
        l_carga_total = float(self.inputs_design['altura_carga'].get())

        self.segments = []
        in_seg = False; start = 0
        for i in range(len(v_inst)):
            if l_smooth[i] <= lim_l:
                v_curr = v_inst[i]
                if (vmin_g * 0.9) < v_curr < (vmax_g * 1.1) and not in_seg:
                    in_seg = True; start = i
                elif (v_curr < vmin_g * 0.4 or v_curr > vmax_g * 1.6) and in_seg:
                    in_seg = False; self.add_segment_logic(t_ms, l_smooth, start, i, ok_min, ok_max, vmin_g, vmax_g)
            elif in_seg:
                in_seg = False; self.add_segment_logic(t_ms, l_smooth, start, i, ok_min, ok_max, vmin_g, vmax_g)
                
        self.total_dist, sum_vl = 0, 0
        for s in self.segments:
            self.total_dist += s['dist']; sum_vl += (s['v_real'] * s['dist'])
        self.weighted_avg = sum_vl / self.total_dist if self.total_dist > 0 else 0

        self.percentage_analized = (self.total_dist / l_carga_total) * 100 if l_carga_total > 0 else 0
        
        self.last_t, self.last_l_csv, self.last_l_smooth, self.last_v_inst = t_ms, l_csv, l_smooth, v_inst
        self.refresh_all_views(t_ms, l_csv, l_smooth, v_inst)
    
    def refresh_all_views(self, t, l_csv, l_smooth, v_inst):
        for w in self.right_panel.winfo_children(): w.destroy()
        
        # PLOT 1: TRAYECTORIA CON LIMITES DE CAJA DE TEXTO
        fig1, ax1 = plt.subplots(figsize=(8, 2))
        ax1.plot(t, l_csv, color='#7f8c8d', alpha=0.4, linewidth=0.5, label="Real (CSV)", zorder=1)
        ax1.plot(t, l_smooth, color='blue', alpha=0.8, linewidth=1, label="Suavizado", zorder=2)
        for s in self.segments:
            ax1.plot(s['t'], s['slope_ms']*s['t'] + s['intercept'], color=s['color'], linewidth=1.5, zorder=3)
            ax1.text(s['t'][-1], s['l_points'][-1], f"{s['v_real']:.0f} m/s", color=s['color'],fontsize=12, fontweight='bold', ha='right', bbox=dict(facecolor='white', alpha=0, edgecolor='none'), zorder=4)
        
        # APLICAR ZOOM DESDE CAJAS DE TEXTO
        try:
            z_min = float(self.zoom_min_ent.get())
            z_max = float(self.zoom_max_ent.get())
            ax1.set_xlim(z_min, z_max)
        except ValueError:
            pass # Si el usuario ingresa texto no numérico, mantiene el zoom automático
        
        res_text = f"VOD Promedio: {self.weighted_avg:.0f} m/s\n ------------------------------------\nLongitud Total: {self.total_dist:.2f} m\nAnalizado: {self.percentage_analized:.1f}%"
        ax1.text(0.05, 0.95, res_text, transform=ax1.transAxes, fontsize=12,fontweight='bold', verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='#f8f9fa', alpha=0.8, edgecolor='gray'))
        
        ax1.axhline(y=float(self.inputs_grafico['limite_vod'].get()), color='#e67e22', linestyle='--', alpha=0.6, zorder=0)
        #ax1.set_title("Trayectoria de Detonación: Real (CSV) vs Analizado");
        ax1.set_ylabel("Longitud (m)",family='arial',fontsize=11); 
        ax1.set_xlabel("Tiempo (ms)",family='arial',fontsize=11); 
        ax1.legend(loc='lower right', fontsize='10')
        fig1.patch.set_alpha(0.0)
        ax1.patch.set_alpha(0.0)
        fig1.tight_layout()
        fig1.subplots_adjust(left=0.1, right=0.99, top=0.90, bottom=0.25) 
        canvas1 = FigureCanvasTkAgg(fig1, self.right_panel) 
        canvas1.get_tk_widget().grid(row=0, column=0,sticky="nsew", pady=(0, 3))
        self.fig_trayectoria = fig1

        # PLOT 2: DISEÑO DE TALADRO
        prof, lc, pb, bh, t_p = float(self.inputs_design['prof_taladro'].get()),float(self.inputs_design['altura_carga'].get()), float(self.inputs_grafico['inicio_probecable'].get()), float(self.inputs_grafico['altura_booster'].get())/100.0, float(self.inputs_grafico['paso_ticks_prof'].get())
        st = prof - lc; fig2, ax2 = plt.subplots(figsize=(5, 9))
        ax2.add_patch(Rectangle((0.2, -prof), 0.6, prof, facecolor='#f5f6fa', edgecolor='black'))
        r_taca = ax2.add_patch(Rectangle((0.2, -st), 0.6, st, facecolor='#cd853f', alpha=0.6, label='Taco'))
        r_exp = ax2.add_patch(Rectangle((0.2, -prof), 0.6, lc, facecolor='#dfe6e9', alpha=0.5, label='Emulsión'))
        r_boost = ax2.add_patch(Rectangle((0.25, -prof), 0.5, bh, facecolor='red', edgecolor='black', label='Booster'))
        y_ref = -prof + pb; sc_pb = ax2.scatter(0.5, y_ref, color='black', marker='D', s=60, zorder=35, label='Probecable')
        h_l, l_l = [r_taca, r_exp, r_boost, sc_pb], ['Taco', 'Emulsión', 'Booster', 'Probecable']
        seen = set()
        for s in self.segments:
            y_s, y_e = y_ref + s['l_points'][0], y_ref + s['l_points'][-1]
            rect = ax2.add_patch(Rectangle((0.3, y_s), 0.4, y_e - y_s, facecolor=s['color'], zorder=30, alpha=0.9))
            if s['seg_label'] not in seen: h_l.append(rect); l_l.append(s['seg_label']); seen.add(s['seg_label'])
            ax2.text(1.2, (y_s + y_e)/2, f"{s['v_real']:.0f} m/s", color=s['color'], fontweight='bold', va='center', fontsize=19, bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))
        ax2.set_ylim(-prof - 0.1, 0.1)
        ax2.set_xlim(0, 4.0)
        ax2.set_xticks([])
        #ax2.set_title("Diseño de Taladro")
        ax2.yaxis.set_major_locator(MultipleLocator(t_p))
        ax2.grid(True, which='both', alpha=0.2, axis='y', color='gray')
        #ax2_alt = ax2.twinx(); 
        #ax2_alt.set_ylim(ax2.get_ylim()[0] + prof, ax2.get_ylim()[1] + prof); 
        #ax2_alt.yaxis.set_major_locator(MultipleLocator(t_p))
        #ax2_alt.set_ylabel("Altura desde el Fondo (m)", color="blue", fontsize=10); 
        ax2.tick_params(axis='y', labelcolor="black", labelsize=12)
        
        fig2.subplots_adjust(left=0.30, right=0.8, top=0.95, bottom=0.05) 
        fig2.patch.set_alpha(0.0)
        ax2.patch.set_alpha(0.0)
        #ax2.legend(h_l, l_l, loc='upper left', bbox_to_anchor=(1.25, 1.05), fontsize='7', framealpha=0.8, title="LEYENDA")
        canvas2 = FigureCanvasTkAgg(fig2, self.right_panel); 
        canvas2.get_tk_widget().grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(0, 10))

        self.fig_taladro = fig2

        # PLOT 3: BARRAS VOD
        fig3, ax3 = plt.subplots(figsize=(7, 1))
        for s in self.segments:
            ax3.bar(s['t_mid'], s['v_real'], width=s['duration'], color=s['color'], alpha=0.8, edgecolor='black', linewidth=0.5)
            ax3.text(s['t_mid'], s['v_real'] + 100, f"{s['v_real']:.0f}", color=s['color'], ha='center', va='bottom', fontsize=8, fontweight='bold')
        if self.segments:
            t_min_b = min(s['t'][0] for s in self.segments); t_max_b = max(s['t'][-1] for s in self.segments)
            ax3.set_xlim(t_min_b - 0.2, t_max_b + 0.2)
        ax3.xaxis.set_major_locator(MultipleLocator(0.20)); ax3.grid(True, which='both', alpha=0.3, axis='x', color='lightgray')
        ax3.set_ylim(float(self.inputs_grafico['vod_min_global'].get()) - 500, float(self.inputs_grafico['vod_max_global'].get()) + 800)
        #ax3.set_title("VOD por Tramos (m/s)"); ax3.set_xlabel("Tiempo (ms)"); ax3.set_ylabel("VOD (m/s)")
        fig3.subplots_adjust(left=0.30, right=0.8, top=0.90, bottom=0.1)

        fig3.tight_layout()
        
        canvas3 = FigureCanvasTkAgg(fig3, self.right_panel)

        canvas3.get_tk_widget().grid(row=1, column=0, sticky="nsew",padx=(50,10))

        self.fig_barras = fig3
    
    def add_segment_logic(self, t, l_s, start, end, ok_min, ok_max, vmin_g, vmax_g):
        if (l_s[end-1] - l_s[start]) > 0.05:
            res = linregress(t[start:end], l_s[start:end])
            v_real = res.slope * 1000.0
            if vmin_g <= v_real <= vmax_g:
                c = "#e74c3c" if v_real < ok_min else ("#2A6E34" if v_real <= ok_max else "#2F4F34")
                lbl = "VOD Falla (< Min)" if v_real < ok_min else ("VOD Óptima" if v_real <= ok_max else "VOD Alta (> Max)")
                self.segments.append({'t': t[start:end], 'l_points': l_s[start:end], 'v_real': v_real, 'dist': l_s[end-1] - l_s[start], 'slope_ms': res.slope, 'intercept': res.intercept, 'color': c, 'seg_label': lbl, 't_mid': (t[start] + t[end-1])/2, 'duration': t[end-1] - t[start]})
    
    def load_csv(self):
        self.path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if self.path:
            self.df = pd.read_csv(self.path, header=None); self.df.columns = ['t', 'l']
            # Ajustar cajas de texto al rango del CSV
            t_min, t_max = self.df['t'].min(), self.df['t'].max()
            self.zoom_min_ent.delete(0, tk.END)
            self.zoom_min_ent.insert(0, f"{t_min:.2f}")
            self.zoom_max_ent.delete(0, tk.END)
            self.zoom_max_ent.insert(0, f"{t_max:.2f}")

            print(self.path)
            self.run_analysis()

    def guardar_datos_vod(self):
        datos_a_guardar = {}
        
        #if self.path!="":
        # Recorremos el diccionario
        datos_a_guardar["id_voladura"]= self.id_vola
        datos_a_guardar["suavizado_ventana"] = float(self.slider_smooth.get())
        datos_a_guardar["t_inicial"]= float(self.zoom_min_ent.get())
        datos_a_guardar["t_final"] = float(self.zoom_max_ent.get())
        datos_a_guardar["vod_min_optima"] = float(self.entry_ok_min.get())
        datos_a_guardar["vod_max_optima"] = float(self.entry_ok_max.get())
        datos_a_guardar["ruta_csv"] = self.path
        datos_a_guardar["densidad"] = float(self.inputs_explosive["densidad"].get())

        for db_key, widget in self.inputs_generales.items():
            if db_key=="id_persona":
                mapa_personas = self.datos_mysql.get("persona", {})
                id_real = mapa_personas.get(widget.get().strip())
                datos_a_guardar[db_key] = id_real

            # --- NUEVA REGLA PARA LA FECHA ---
            elif db_key == "fecha" and widget.get().strip():
                try:
                    # Leemos la fecha en formato DD-MM-YYYY
                    fecha_obj = datetime.strptime(widget.get().strip(), "%d-%m-%Y")
                    # La guardamos en el diccionario en formato YYYY-MM-DD para MySQL
                    datos_a_guardar[db_key] = fecha_obj.strftime("%Y-%m-%d")
                except ValueError:
                    # Si el usuario escribió algo raro que no es una fecha, lo pasamos tal cual
                    datos_a_guardar[db_key] = widget.get().strip()
            # 👇 NUEVO BLOQUE: Guardar el ID del taladro
            elif db_key == "taladro":
                valor_combo = widget.get().strip() # Esto es el Label visual (ej. "644")
                id_a_guardar = getattr(self, 'mapa_taladros_id', {}).get(valor_combo, valor_combo)
                datos_a_guardar[db_key] = id_a_guardar
            else:
                datos_a_guardar[db_key] = widget.get().strip()

        for db_key, widget in self.inputs_design.items():
            datos_a_guardar[db_key] = widget.get().strip()
        for db_key, widget in self.inputs_explosive.items():
            if db_key=="id_explosivo":
                mapa_explosivos = self.datos_mysql.get("explosivo", {})
                #print(mapa_explosivos)
                id_real = mapa_explosivos.get(widget.get().strip())['idexplosivo']
                datos_a_guardar[db_key] = id_real
            elif db_key=="id_camion":
                mapa_camion = self.datos_mysql.get("camion_fabrica", {})
                print(mapa_camion)
                id_real = mapa_camion.get(widget.get().strip())["id"]
                datos_a_guardar[db_key] = id_real
            else:
                datos_a_guardar[db_key] = widget.get().strip()
        for db_key, widget in self.inputs_grafico.items():
            datos_a_guardar[db_key] = widget.get().strip()

        try:
            # (Aquí mantienes tu lógica de traducción de IDs Marco Vargas -> ID_001, etc.)
            
            exito, resultado = self.datos.procesar_guardado_vod(datos_a_guardar)
            
            if exito:
                # 👇 NUEVO: Le avisamos a la tabla principal que esta voladura ya tiene VOD
                marcar_medicion_completada(self.id_vola, "vod")
                # 👇 LA MAGIA: Ejecutamos el control remoto
                if self.callback_actualizar:
                    self.callback_actualizar()
                
                messagebox.showinfo("Sistema. DOCKET", f"El registro fue {resultado} con éxito.")

            else:
                messagebox.showerror("Error", f"No se pudo procesar: {resultado}")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la información: {str(e)}")
    #else:
    #    messagebox.showwarning("Advertencia", "Debes importar un archivo CSV")
    
    def preparar_fondo(self,ruta_original, brillo=1.5, contraste=0.5):
        img = Image.open(ruta_original)
        
        # Ajustar Brillo (1.0 es original, >1.0 es más claro)
        enhancer_brillo = ImageEnhance.Brightness(img)
        img = enhancer_brillo.enhance(brillo)
        
        # Ajustar Contraste (0.5 hace que se vea más tenue/gris)
        enhancer_con = ImageEnhance.Contrast(img)
        img = enhancer_con.enhance(contraste)
        
        img.save("logo_fondo_1.png")

    def agregar_fondo(self,pdf):
        ancho_carta = 215.9
        alto_carta = 279.4
        # Colocamos la imagen en (0,0) cubriendo toda la hoja
        pdf.image("logo_fondo_1.png", x=0, y=0, w=ancho_carta, h=alto_carta)
    
    def create_pdf_header(self):
        ancho_px = 195
        pdf = FPDF(format='Letter')

        pdf.set_margins(10,2,10)

        self.preparar_fondo("./recursos/logo_fondo.png", 1.8, 0.9) # Lo hacemos muy tenue

        pdf.add_page()

        pdf.set_auto_page_break(False, margin=0)

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
        
        pdf.cell(105, 12, "CONTROL DE VELOCIDAD DE DETONACIÓN", 1, 0, 'C')
        pdf.set_font("Arial", '', 7)
        pdf.multi_cell(50, 4, "REC.BOL.OP.MSC.001.3\nRev.: 04\nFecha de Aprob.: 01-04-2021", 1, 'L')
        
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
        pdf.cell(ancho_px*0.15, 8, f"Realizado por:", 0,0,'L')
        pdf.set_font("Arial", '', 9)
        pdf.cell(ancho_px*0.19, 8, f"{self.inputs_generales['id_persona'].get()}", 0,0,'L')

        pdf.set_font("Arial", 'B', 9)
        pdf.cell(ancho_px*0.32, 8, f"Firma:", 0,0,'L')
        pdf.cell(ancho_px*0.12, 8, f"Fecha y Hora:", 0,0,'L')
        pdf.set_font("Arial", '', 9)
        fecha_hora =  self.obtener_fecha_formateada(self.inputs_generales['fecha'].get(),self.inputs_generales['hora'].get())
        pdf.cell(ancho_px*0.18, 8, fecha_hora, 0,0,'L')

        pdf.ln(8)

        pdf.set_text_color(0,0,0)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(ancho_px*0.15, 7, "N° Voladura:", 0,0,'L')
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(ancho_px*0.19, 7, f"{self.inputs_generales['nro_voladura'].get()}", 0,0,'L')

        pdf.set_font("Arial", 'B', 9)
        pdf.cell(ancho_px*0.15, 7, f"Fase/Banco/Malla:", 0,0,'L')
        pdf.set_font("Arial", '', 9)
        pdf.cell(ancho_px*0.17, 7, f"{self.inputs_generales['fase_banco_malla'].get()}", 0,0,'L')

        pdf.set_font("Arial", 'B', 9)
        pdf.cell(ancho_px*0.12, 7, f"Condición :", 0,0,'L')
        pdf.set_font("Arial", '', 9)
        pdf.cell(ancho_px*0.18, 7, f"{self.inputs_design['humedad'].get()}", 0,0,'L')

        
        #--------------------------------
        pdf.ln(8)
        
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(ancho_px*0.15, 7, f"Camión :", 0,0,'L')
        pdf.set_font("Arial", '', 9)
        pdf.cell(ancho_px*0.19, 7, f"{self.inputs_explosive['id_camion'].get()}", 0,0,'L')

        pdf.set_font("Arial", 'B', 9)
        pdf.cell(ancho_px*0.18, 7, f"Longitud Coaxial [m.]:", 0,0,'L')
        pdf.set_font("Arial", '', 9)
        pdf.cell(ancho_px*0.14, 7, f"{self.inputs_grafico['long_cable_coaxial'].get()}", 0,0,'L')

        pdf.set_font("Arial", 'B', 9)
        pdf.cell(ancho_px*0.12, 7, f"Iniciación :", 0,0,'L')
        pdf.set_font("Arial", '', 9)
        pdf.cell(ancho_px*0.18, 7, f"{self.inputs_explosive['iniciacion'].get()}", 0,0,'L')

        #--------------------------------
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(*BLANCO)
        pdf.cell(ancho_px, 7, "2. RESULTADOS OBTENIDOS", 0, 0, 'L',fill=True)
        
        pdf.ln(8)

        pdf.set_text_color(0,0,0)

        continuidad = self.inputs_grafico['continuidad_handy'].get()

        y_inicial_graficas = pdf.get_y()

        prof = self.extraer_numero(self.inputs_design, 'prof_taladro')
        carga = self.extraer_numero(self.inputs_design, 'altura_carga')
    
        taco_calculado = prof - carga if prof > carga else 0.0

        data_reporte = {
            'profundidad': prof,
            'banco':       self.extraer_numero(self.inputs_design, 'altura_banco'),
            'taco':        taco_calculado,
            'carga':       carga,
            'tipo':        self.inputs_explosive['id_explosivo'].get(),
            'tipo_taco':   self.inputs_design['tipo_taco'].get(),
            'dens':        self.inputs_explosive['densidad'].get(),
            'diam':        self.inputs_design['diametro'].get(),
            'kg':          self.inputs_explosive['peso_exp'].get(),
            'booster':     self.inputs_grafico['altura_booster'].get(),
            'tipo_booster': self.inputs_design['booster'].get()
        }

        if continuidad == "SI":

            # Llamamos a la función de dibujo que ya tienes
            ruta_img = self.generar_imagen_perfil_estatica(data_reporte)

            self.fig_trayectoria.savefig("./recursos/temp_trayectoria.png", dpi=145, bbox_inches='tight')
            self.fig_taladro.savefig("./recursos/temp_taladro.png", dpi=280, bbox_inches='tight')

            if ruta_img and os.path.exists(ruta_img):
                pdf.image(ruta_img, x=8, y=y_inicial_graficas, w=50)
                pdf.image("./recursos/temp_taladro.png", x=58, y=y_inicial_graficas+2 , w=27)

                taladro_seleccionado = self.inputs_generales['taladro'].get()

                ruta_malla = self.generar_imagen_malla(self.taladros, taladro_seleccionado)
                if ruta_malla and os.path.exists(ruta_malla):
                    pdf.image(ruta_malla, x=85, y=y_inicial_graficas+2, w=122)
            
            # --- GRAFICAR MALLA ---
            # leyenda
            pdf.set_y(y_inicial_graficas + 82)
            pdf.set_font("Arial", '', 8)
            #pdf.set_text_color(*)
            #pdf.ln(2)
            pdf.cell(ancho_px, 15, "1.- Diámetro   2.- Taco   3.- Explosivo   4.- Densidad   5.- Carga Total   6.- Accesorios ", 0, 0, 'L',fill=False)
            
            y_inicial_graficas = pdf.get_y()+14
            pdf.image("./recursos/temp_trayectoria.png", x=12, y=y_inicial_graficas, w=125)
            #taladro_objetivo_limpio = getattr(self, 'mapa_taladros_label', {}).get(taladro_seleccionado, taladro_seleccionado)

            # --- GRAFICAR GAUGE -----

            mapa_explosivos = self.datos_mysql.get("explosivo", {})
                    #print(mapa_explosivos)
            id_explosivo = mapa_explosivos.get(self.inputs_explosive['id_explosivo'].get())['idexplosivo']
            #print("ID EXPLOSIVO: ",id_explosivo)

            ruta_gauge = self.generar_imagen_gauge(self.weighted_avg,id_explosivo)
            y_inicial_graficas= y_inicial_graficas+10
            
            # Pegar el gauge en el PDF
            if ruta_gauge and os.path.exists(ruta_gauge):
                # AJUSTA LA 'x' y la 'y' PARA UBICARLO DONDE DESEES
                # Por ejemplo, si la malla está a la izquierda (x=20), pon el gauge a la derecha (x=130)
                # y_seccion_3 es la altura a la que lo quieres imprimir.
                pdf.image(ruta_gauge, x=140, y=y_inicial_graficas, w=60)
            
            pdf.set_y(y_inicial_graficas + 55)
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(*BLANCO)
            pdf.cell(ancho_px, 7, "3. COMENTARIOS", 0, 1, 'L',fill=True)
            pdf.ln(2)
            pdf.cell(ancho_px, 15, "", 1, 1, 'L',fill=False)
            
        else:

            ruta_img = self.generar_imagen_perfil_estatica(data_reporte)

            if ruta_img and os.path.exists(ruta_img):
                pdf.image(ruta_img, x=10, y=y_inicial_graficas, w=50)

                taladro_seleccionado = self.inputs_generales['taladro'].get()

                ruta_malla = self.generar_imagen_malla(self.taladros, taladro_seleccionado)
                if ruta_malla and os.path.exists(ruta_malla):
                    pdf.image(ruta_malla, x=85, y=y_inicial_graficas+2, w=122)

            pdf.set_y(y_inicial_graficas + 80)
            y_inicial_graficas = y_inicial_graficas + 30

            pdf.ln(2)
            pdf.set_text_color(100, 101, 103) # Gris MAXAM (#646567)
            pdf.set_font("Arial", '', 10)

            #pdf.set_y(y_inicial_graficas + 80)
            pdf.set_font("Arial", '', 8)
            #pdf.set_text_color(*)
            pdf.cell(ancho_px, 23, "1.- Diámetro   2.- Taco   3.- Explosivo   4.- Densidad   5.- Carga Total   6.- Accesorios ", 0, 0, 'L',fill=False)

            pdf.set_y(y_inicial_graficas + 72)

            observaciones_seguras = getattr(self, 'comentarios_handy', 'Sin observaciones.')
            texto_falla = f"AVISO: No se obtuvo medida de VOD. \n\nObservaciones: {observaciones_seguras}"
            pdf.ln(1)
            # Multi_cell permite el ajuste de línea automático y justificación
            # align='J' es para Justificado
            pdf.multi_cell(ancho_px, 6, texto_falla, border=1, align='J')

        
        #y_inicial_graficas = pdf.get_y()+85
        pdf.set_y(y_inicial_graficas + 86)

        pdf.ln(8)
        pdf.set_font("Arial", 'I', 9)
        pdf.set_text_color(0,0,0)
        pdf.cell(70, 5, "Verificado por: ______________________", 0, 0, 'L')
        pdf.cell(50, 5, "Firma : ________________", 0, 0, 'L')

        pdf.set_auto_page_break(True, margin=20)

        nro_vola = self.inputs_generales['nro_voladura'].get()
        nombre_sugerido = f"Reporte_VOD_Voladura_{nro_vola}.pdf"

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

    def cargar_datos_existentes(self):
        # Asumiendo que self.proyecto tiene el N° de voladura actual
        #nro_vola = str(self.proyecto)
        registro = self.datos.obtener_registro_vod(self.id_vola)

        #print(registro)
        
        if not registro:
            return # Si no hay datos previos, no hacemos nada y dejamos los valores por defecto

        print("Cargando datos existentes...")

        # 1. Unimos todos los inputs en un solo diccionario gigante para iterar fácilmente
        todos_los_inputs = {**self.inputs_generales, **self.inputs_design, **self.inputs_explosive, **self.inputs_grafico}
        
        # 2. Diccionarios inversos (Para traducir ID -> Nombre)
        mapa_personas_inverso = {v: k for k, v in self.datos_mysql.get("persona", {}).items()}
        
        # Ojo: tu mapa_explosivos guarda un dict interno {'idexplosivo': X}. 
        # Ajusta esta línea según la estructura exacta de tu JSON/MySQL.
        try:
            mapa_explosivos_inverso = {v['idexplosivo']: k for k, v in self.datos_mysql.get("explosivo", {}).items()}
        except TypeError:
            mapa_explosivos_inverso = {v: k for k, v in self.datos_mysql.get("explosivo", {}).items()}
            
        #mapa_camiones_inverso = {v: k for k, v in self.datos_mysql.get("camion_fabrica", {}).items()}

        mapa_camiones_inverso = {}
        for nombre, datos in self.datos_mysql.get("camion_fabrica", {}).items():
            # Sacamos el ID numérico del paquetito de datos
            id_del_camion = datos.get("id")
            if id_del_camion is not None:
                mapa_camiones_inverso[id_del_camion] = nombre

        # 👇 NUEVO: Mapa inverso para recuperar el nombre del taladro
        mapa_taladros_inverso = {v: k for k, v in getattr(self, 'mapa_taladros_id', {}).items()}

        # 3. Repartimos la información en la interfaz
        for columna_db, valor in registro.items():
            if columna_db in todos_los_inputs and valor is not None:
                widget = todos_los_inputs[columna_db]
                
                # Borramos lo que tenga el widget actualmente (por defecto)
                widget.delete(0, tk.END) if not isinstance(widget, ttk.Combobox) else widget.set('')
                
                # --- LA MAGIA DE LA TRADUCCIÓN INVERSA ---
                if columna_db == "id_persona":
                    nombre = mapa_personas_inverso.get(valor, valor)
                    widget.insert(0, nombre) if not isinstance(widget, ttk.Combobox) else widget.set(nombre)
                    
                elif columna_db == "id_explosivo":
                    nombre = mapa_explosivos_inverso.get(valor, valor)
                    widget.insert(0, nombre) if not isinstance(widget, ttk.Combobox) else widget.set(nombre)
                    
                elif columna_db == "id_camion":
                    nombre = mapa_camiones_inverso.get(valor, valor)
                    widget.insert(0, nombre) if not isinstance(widget, ttk.Combobox) else widget.set(nombre)
                
                # 👇 NUEVO: Mostrar el texto amigable en la interfaz (ej. "644 (ID: 10245)")
                elif columna_db == "taladro":
                    # 'valor' es el ID que viene de la BD (ej. 10245)
                    label_recuperado = getattr(self, 'mapa_id_a_label', {}).get(str(valor), str(valor))
                    widget.set(label_recuperado)
                
                elif columna_db == "fecha":
                    # 'valor' es el ID que viene de la BD (ej. 10245)
                    print(valor)
                    label_recuperado = datetime.strftime(valor, "%d-%m-%Y")
                    widget.insert(0,label_recuperado)

                elif columna_db == "densidad":
                    # 'valor' es el ID que viene de la BD (ej. 10245)
                    print(valor)
                    #label_recuperado = datetime.strftime(valor, "%d-%m-%Y")
                    widget.insert(0,valor)
                
                # Para todos los demás campos (textos normales y números)
                else:
                    widget.insert(0, str(valor)) if not isinstance(widget, ttk.Combobox) else widget.set(str(valor))

        self.actualizar_kpis()

        # 4. (Opcional) Cargar el CSV si guardaste la ruta
        ruta_guardada = registro.get("ruta_csv")
        if ruta_guardada and os.path.exists(ruta_guardada):
            self.path = ruta_guardada
            self.df = pd.read_csv(ruta_guardada, header=None)
            self.df.columns = ['t', 'l']
            self.run_analysis() # Dibuja la gráfica automáticamente

    def generar_imagen_perfil_estatica(self, datos):
        """Genera el esquema técnico en una imagen temporal (Versión Taladro Angosto)."""
        
        fig, ax = plt.subplots(figsize=(4, 7))
        
        try:
            p, b = datos['profundidad'], datos['banco']
            t, c = datos['taco'], datos['carga']
            lc = p - t 
            sp = round(p - b,1)
            boos = datos['booster']
            diam = datos.get('diam', '0')
            tipo_taco = datos.get('tipo_taco')
            tipo_booster = datos.get('tipo_booster')
            tamsize=12
            #print("taco:",tipo_taco)
            
            # 🟢 AJUSTE DE GROSOR: Centro en X=0.5, Ancho=0.2 (Empieza en 0.4 y termina en 0.6)
            x_inicio = 0.4
            ancho = 0.1
            x_fin = x_inicio + ancho

            # Dibujo de capas (Taco y Carga) más angostas
            ax.add_patch(Rectangle((x_inicio, 0), ancho, t, facecolor="#ffb700", edgecolor='black', lw=1)) 
            ax.add_patch(Rectangle((x_inicio, t), ancho, c, facecolor="#aee9ff", edgecolor='black', lw=1)) 

            # Acotamiento del DIÁMETRO en la parte superior (ajustado a las nuevas paredes)
            ax.plot([x_inicio, x_inicio], [0, -0.15], color='black', lw=1)
            ax.plot([x_fin, x_fin], [0, -0.15], color='black', lw=1)
            ax.annotate('', xy=(x_inicio, -0.1), xytext=(x_fin, -0.1), arrowprops=dict(arrowstyle='<->', color='black'))
            ax.text(0.5, -0.12, f"1.- Ø {diam} mm", ha='center', va='bottom', fontweight='bold', fontsize=tamsize)

            # 🟢 2. DIBUJO DEL BOOSTER Y CABLE
            # Determinar la posición del booster. 
            # Por defecto, lo ubicamos en el fondo del taladro (0.3m sobre el piso)
            # Si tienes el dato en tu BD, puedes pasarlo en el diccionario: datos.get('prof_booster')
            prof_booster = float(datos.get('prof_booster', (t + c) - float(boos)*0.01))
            alto_booster = 0.1
            ancho_booster = ancho * 0.2
            x_booster = x_inicio + (ancho_booster / 2)
            
            # Línea del cable de iniciación (desde la superficie Y=0 hasta el booster)
            #ax.plot([x_inicio+ancho_booster*0.5, 0], [x_inicio+ancho_booster*0.5, prof_booster], color='#c0392b', lw=1.5, linestyle='-', zorder=2)
            
            # Rectángulo del Booster (Rojo intenso)
            ax.add_patch(Rectangle((x_booster, prof_booster), ancho_booster, alto_booster, 
                                   facecolor='#e74c3c', edgecolor='black', lw=1, zorder=3))
            
            # Etiqueta del Booster
            ax.annotate(f"6.- Booster\n   {tipo_booster}gr\n   {boos}cm", xy=(x_fin, prof_booster + alto_booster/2), 
                        xytext=(x_fin + 0.1, prof_booster + alto_booster/2),
                        arrowprops=dict(arrowstyle='-', color='black'),
                        va='center', ha='left', fontsize=tamsize, fontweight='bold')

            # Acotaciones de profundidad y banco (Las acerqué un poco más al taladro)
            ax.annotate('', xy=(0.18, p), xytext=(0.18, 0), arrowprops=dict(arrowstyle='<->', color='black'),fontsize=tamsize)
            ax.text(0.16, p/2, f'Prof: {p}m', rotation=90, va='center', ha='center', fontweight='bold',fontsize=tamsize)

            ax.annotate('', xy=(0.10, b), xytext=(0.10, 0), arrowprops=dict(arrowstyle='<->', color='blue'),fontsize=tamsize)
            ax.text(0.06, b/2, f'Banco: {b}m', rotation=90, va='center', ha='center', color='blue', fontweight='bold',fontsize=tamsize)

            ax.annotate('', xy=(0.10, b), xytext=(0.10, p), arrowprops=dict(arrowstyle='<->', color='blue'),fontsize=tamsize)
            ax.text(0.06, b + sp/2, f'Sp: {sp}m', rotation=90, va='center', ha='center',color='blue', fontweight='bold',fontsize=tamsize)

            # Textos descriptivos (Estilo "Etiqueta Flotante" con borde, ya que el taladro es delgado)
            texto_taco = f"2.- {tipo_taco}\n{t}m" if tipo_taco else f"2.- TACO\n{t}m"
            ax.text(0.45, t/2, texto_taco, ha='center', va='center', color='black', fontweight='bold', fontsize=tamsize, 
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='#bdc3c7'))
            
            #txt_explosivo = f"{datos['tipo']}\n {datos['dens']} g/cc\n {datos['kg']}kg"
            txt_explosivo = f"3.- {datos['tipo']} \n {lc}m\n-------------------\n4.- {datos['dens']} g/cc\n 5.- {datos['kg']} kg"
            ax.text(0.45, t + (c/2), txt_explosivo, ha='center', va='center',fontweight='bold', fontsize=tamsize, 
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='#bdc3c7'))

            # Configuración final de la gráfica
            ax.set_ylim(max(p, b) + 0.5, -0.3)
            ax.set_xlim(0, 1)
            ax.axis('off')
            
            if not os.path.exists("./recursos"):
                os.makedirs("./recursos")
                
            ruta = "./recursos/temp_perfil_reporte.png"
            fig.savefig(ruta, dpi=250, bbox_inches='tight',transparent=True)
            plt.close(fig)
            return ruta
            
        except Exception as e:
            print(f"Error interno dibujando: {e}")
            plt.close(fig)
            return None

    def extraer_numero(self, diccionario, clave):
        try:
            val = diccionario[clave].get().strip()
            return float(val) if val else 0.0
        except:
            return 0.0

    def generar_imagen_malla(self, datos_taladros, taladro_objetivo_label):

        # 🟢 1. Ajustar el tamaño de la figura a un rectángulo (Ej. 8 de ancho x 4.5 de alto)
        fig, ax = plt.subplots(figsize=(8, 6.5))

        # Transparencia y color
        color_fondo = '#e8e8e8'
        fig.patch.set_facecolor(color_fondo)
        ax.set_facecolor(color_fondo)
        fig.patch.set_alpha(0.0) 
        ax.patch.set_alpha(0.0) 

        # Borde exterior
        fig.patch.set_edgecolor('black') 
        fig.patch.set_linewidth(0.02) 

        # 1. Encontrar coordenadas del taladro VOD (Para usarlas de pivote)
        x_centro, y_centro = None, None
        
        for t in datos_taladros:
            t_clean = {str(k).lower(): v for k, v in t.items()}
            lbl = str(t_clean.get('label', '')).strip()
            
            if lbl == str(taladro_objetivo_label).strip():
                # 🟢 CORRECCIÓN: Aseguramos que sea un número (float)
                x_centro = float(t_clean.get('x', 0.0) or 0.0)
                y_centro = float(t_clean.get('y', 0.0) or 0.0)
                break
        
        if x_centro is None or (x_centro == 0.0 and y_centro == 0.0):
            print(f"Alerta: Taladro {taladro_objetivo_label} no encontrado o sin coordenadas.")
            plt.close(fig)
            return None

        # 2. Nivel de Zoom 
        radio_zoom_y = 40  # Mantiene la altura que ya tenías
        radio_zoom_x = 60  # Doble de visión hacia los lados (horizontal)
        
        x_malla, y_malla, labels = [], [], []

        # 3. Procesar el resto de la malla aplicando la RESTA (Coordenadas Relativas)
        for t in datos_taladros:
            t_clean = {str(k).lower(): v for k, v in t.items()}
            lbl = str(t_clean.get('label', '')).strip()
            
            # 🟢 CORRECCIÓN: Convertir a float
            x_actual = float(t_clean.get('x', 0.0) or 0.0)
            y_actual = float(t_clean.get('y', 0.0) or 0.0)
            
            # Evitar basura de BD
            if x_actual == 0.0 and y_actual == 0.0:
                continue
                
            # Restamos las coordenadas del objetivo
            x_relativa = x_actual - x_centro
            y_relativa = y_actual - y_centro
                
            # 🟢 CORRECCIÓN CLAVE: Usar radio_zoom_x y radio_zoom_y
            if (-radio_zoom_x) <= x_relativa <= radio_zoom_x and (-radio_zoom_y) <= y_relativa <= radio_zoom_y:
                if lbl != str(taladro_objetivo_label).strip():
                    x_malla.append(x_relativa)
                    y_malla.append(y_relativa)
                    labels.append(lbl)

        # --- DIBUJO DE LA MALLA ---

        # A) Resto de los taladros (Círculos blancos)
        if len(x_malla) > 0:
            ax.scatter(x_malla, y_malla, color="#e6e6e6", edgecolors="#ebebeb", s=140, zorder=2, linewidths=0)
            for i in range(len(x_malla)):
                ax.text(x_malla[i], y_malla[i], labels[i], ha='center', va='center', 
                        fontsize=7.5, color='black', zorder=3)
        else:
            print("Alerta: No se encontraron taladros válidos alrededor de este punto.")

        # B) Taladro VOD (Rojo, SE DIBUJA EXACTAMENTE EN 0,0)
        ax.scatter([0], [0], color="#94bef8", s=190, zorder=4, linewidths=0)
        ax.text(0, 0, str(taladro_objetivo_label).strip(), ha='center', va='center', 
                fontsize=8, color='black', fontweight='bold', zorder=5)

        # C) Establecer el Zoom (Centrado en el 0,0 de la coordenada relativa)
        # 🟢 CORRECCIÓN CLAVE: Asignar límites rectangulares independientes
        ax.set_xlim(-radio_zoom_x, radio_zoom_x)
        ax.set_ylim(-radio_zoom_y, radio_zoom_y)
        
        # --- ESTÉTICA FINAL ---
        ax.set_aspect('equal') # Evita que los círculos se vuelvan óvalos
        
        ax.set_xticks([])
        ax.set_yticks([])

        # Forzar que el marco del gráfico sea visible, negro y con grosor
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color('black')
            spine.set_linewidth(0.5)
        
        # 🟢 NUEVA BRÚJULA: Dibujada usando coordenadas geográficas (Metros reales)
        # Posicionamos la brújula en la esquina superior derecha
        cx = radio_zoom_x * 0.85     # 85% a la derecha
        cy = radio_zoom_y * 0.75     # 75% hacia arriba
        radio_brujula = radio_zoom_y * 0.15 # Tamaño del círculo en metros (aprox 6.7m)

        # Dibujamos la flecha y la letra N
        ax.annotate('N', 
                    xy=(cx, cy + radio_brujula * 0.8),       # Punta de la flecha roja
                    xytext=(cx, cy - radio_brujula * 0.6),   # Base de la flecha y letra N
                    arrowprops=dict(facecolor='red', edgecolor='red', width=1.0, headwidth=5),
                    ha='center', va='center', fontsize=8, color='black', fontweight='bold', zorder=11)
        
        # Al no usar 'transform', se dibuja usando el aspect='equal', siendo un círculo perfecto
        circulo_n = plt.Circle((cx, cy), radio_brujula, color='white', fill=True, lw=0.8, zorder=10)
        ax.add_patch(circulo_n)


        ax.text(0.02, 0.96, f"Taladro {taladro_objetivo_label}", transform=ax.transAxes, 
                fontsize=12, fontweight='bold', va='top', bbox=dict(facecolor='white', alpha=1.0, edgecolor='none'))

        if not os.path.exists("./recursos"): os.makedirs("./recursos")
        ruta = "./recursos/temp_malla.png"
        fig.savefig(ruta, dpi=150, bbox_inches='tight', transparent=True)
        plt.close(fig)
        return ruta

    def generar_imagen_gauge(self, valor_vod, id_explosivo):
        """Genera un gráfico tipo medidor de aguja (Gauge) transparente e inteligente."""
        import matplotlib.pyplot as plt
        import numpy as np
        import os

        # Tamaño compacto
        fig, ax = plt.subplots(figsize=(4, 3))
        
        # Fondo transparente
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        # 1. Traer los datos de la base de datos
        # (Asegúrate de cómo llamas a tu función. Si está dentro de la clase datos_db, podría ser self.datos.obtener_kpi_por_explosivo)
        datos_kpi = obtener_kpi_por_explosivo(id_explosivo)
        
        # Mecanismo de seguridad por si la BD falla o el explosivo no tiene KPIs registrados
        if not datos_kpi:
            datos_kpi = {'vod_minimo': 3000, 'vod_maximo': 5000}

        vod_min = float(datos_kpi['vod_minimo'])
        vod_max = float(datos_kpi['vod_maximo'])

        # 2. Definir el límite máximo del medidor (holgura dinámica)
        # Si la VOD máxima es 6500, el medidor llegará a 8000 para que la aguja no se rompa
        limite_superior = max(7000.0, vod_max + 1500.0)

        # 3. Calcular los tamaños reales de cada tramo de color
        colores = ["#e7923c", "#0ff144", "#005021", (0,0,0,0)] # Naranja, Verde Claro, Verde Oscuro, Transparente
        
        tramo_bajo = vod_min
        tramo_optimo = vod_max - vod_min
        tramo_alto = limite_superior - vod_max
        tamanos = [tramo_bajo, tramo_optimo, tramo_alto, limite_superior] # El último bloque es la mitad transparente
        
        # Dibujar el "anillo"
        ax.pie(tamanos, colors=colores, startangle=180, radius=1.0, counterclock=False,
               wedgeprops=dict(width=0.3, edgecolor='white', lw=1.5))

        # 4. Etiquetas dinámicas POR FUERA del anillo
        r_text = 1.05
        
        # Matemáticas para encontrar los ángulos exactos donde se unen los colores
        ang_min_grados = 180 - (vod_min / limite_superior) * 180
        ang_max_grados = 180 - (vod_max / limite_superior) * 180
        ang_minimo = np.radians(ang_min_grados)
        ang_maximo = np.radians(ang_max_grados)

        # Textos automáticos
        ax.text(-r_text, 0.1, "0", ha='center', va='bottom', fontsize=12, fontweight='bold')
        ax.text(r_text * np.cos(ang_minimo), r_text * np.sin(ang_minimo), f"{int(vod_min)}", ha='center', va='bottom', fontsize=12, fontweight='bold')
        ax.text((r_text) * np.cos(ang_maximo), r_text * np.sin(ang_maximo), f"{int(vod_max)}", ha='left', va='bottom', fontsize=12, fontweight='bold')
        ax.text(r_text, 0.1, f"{int(limite_superior)}", ha='left', va='bottom', fontsize=12, fontweight='bold')

        # 5. Matemáticas para inclinar la aguja
        valor_seguro = max(0, min(valor_vod, limite_superior)) # Evita que la aguja se salga de la pantalla
        angulo_grados = 180 - (valor_seguro / limite_superior) * 180
        angulo_rad = np.radians(angulo_grados)

        x_aguja = 0.65 * np.cos(angulo_rad)
        y_aguja = 0.65 * np.sin(angulo_rad)

        # Dibujar la aguja
        ax.annotate('', xy=(x_aguja, y_aguja), xytext=(0, 0),
                    arrowprops=dict(facecolor='#2c3e50', edgecolor='black', width=3, headwidth=8))
        ax.plot(0, 0, marker='o', color='gray', markeredgecolor='black', markersize=14) 
        ax.plot(0, 0, marker='o', color='black', markersize=4) 

        # 6. Textos centrales (Valor exacto y Calificación)
        if valor_vod < vod_min:
            estado = "BAJO"
            color_texto = colores[0]
        elif valor_vod <= vod_max:
            estado = "ÓPTIMO"
            color_texto = colores[1]
        else:
            estado = "ALTO"
            color_texto = colores[2]

        ax.text(0, -0.3, f"{valor_vod:.0f} m/s", ha='center', va='center', fontsize=16, fontweight='bold', color='black')
        ax.text(0, -0.5, estado, ha='center', va='center', fontsize=13, fontweight='bold', color='black')

        # 7. Ajustar los límites del lienzo para que los números exteriores no se corten
        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-0.6, 1.3)
        ax.set_aspect('equal')
        ax.axis('off')
        
        ax.set_title("Desempeño VOD", fontweight='bold', fontsize=12, y=0.95)

        if not os.path.exists("./recursos"): os.makedirs("./recursos")
        ruta = "./recursos/temp_gauge.png"
        fig.savefig(ruta, dpi=150, bbox_inches='tight', transparent=True)
        plt.close(fig)
        return ruta
    
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

