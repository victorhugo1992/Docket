# Archivo: vistas/home_tab.py
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import calendar
from database.voladuras_db import obtener_voladuras_por_rango
from database.datos_db import obtener_datos_dashboard_kpi,obtener_distribucion_taladros_gauss,obtener_proyectos,obtener_vods
import os
import pandas as pd
from tkinter import filedialog, messagebox

# ==========================================================
# COLORES REFINADOS PARA UN LOOK INDUSTRIAL / MINERO (DASHBOARD)
# ==========================================================
COLOR_FONDO_MAIN = "#f5f6fa"   
COLOR_CARD_BG    = "#ffffff"   
COLOR_TEXTO_MUTE = "#7f8c8d"   
COLOR_TEXTO_DARK = "#2c3e50"   

PALETA_BORDES = {
    "VOLADURAS":     "#2980b9",  
    "VOD":           "#e67e22",  
    "SISMOGRAFIA":   "#c0392b",  
    "FRAGMENTACION": "#8e44ad",  
    "DENS_ANFO":     "#16a085",  
    "DENS_RIOFLEX":  "#27ae60",
    "GAUSS":         "#34495e"
}

class InfoCard(tk.Frame):
    """Tarjeta de indicadores con estilo Dashboard moderno."""
    def __init__(self, parent, title, main_value, sub_text, accent_color, width=220, height=130):
        super().__init__(parent, bg="#dcdde1", width=width, height=height)
        self.pack_propagate(False)
        
        self.inner_frame = tk.Frame(self, bg=COLOR_CARD_BG)
        self.inner_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.inner_frame.pack_propagate(False)
        
        self.accent_bar = tk.Frame(self.inner_frame, bg=accent_color, height=4)
        self.accent_bar.pack(fill=tk.X, side=tk.TOP)
        
        self.lbl_title = tk.Label(self.inner_frame, text=title.upper(), bg=COLOR_CARD_BG, fg=COLOR_TEXTO_MUTE, font=("Arial", 9, "bold"))
        self.lbl_title.pack(pady=(12, 2), anchor="w", padx=15)
        
        self.lbl_main = tk.Label(self.inner_frame, text=main_value, bg=COLOR_CARD_BG, fg=COLOR_TEXTO_DARK, font=("Helvetica", 24, "bold"))
        self.lbl_main.pack(pady=2, anchor="w", padx=15)
        
        self.lbl_sub = tk.Label(self.inner_frame, text=sub_text, bg=COLOR_CARD_BG, fg=COLOR_TEXTO_MUTE, font=("Arial", 8, "italic"))
        self.lbl_sub.pack(side=tk.BOTTOM, pady=(0, 12), anchor="w", padx=15)

    def actualizar_datos(self, nuevo_valor_principal, nuevo_subtexto):
        self.lbl_main.config(text=nuevo_valor_principal)
        self.lbl_sub.config(text=nuevo_subtexto)


class HomeTab(ttk.Frame):
    """Pestaña principal con selector de fechas y Dashboard KPI robusto."""
    def __init__(self, parent):
        super().__init__(parent)
        self.valores_iniciales = {}
        
        # 🟢 NUEVO: Guardamos la referencia directa de la base de datos que viene de main.py
        
        #self.datos_db = datos_db
        self.config_style = ttk.Style()
        self.config_style.configure("Home.TFrame", background=COLOR_FONDO_MAIN)
        self.configure(style="Home.TFrame")
        
        self.main_container = tk.Frame(self, bg=COLOR_FONDO_MAIN)
        self.main_container.pack(expand=True, fill=tk.BOTH, padx=30, pady=20)
        
        # ==========================================================
        # BLOQUE DE FILTRADO DE FECHAS (SUPERIOR)
        # ==========================================================
        frame_filtros = tk.Frame(self.main_container, bg=COLOR_FONDO_MAIN)
        frame_filtros.pack(fill=tk.X, pady=(0, 15), anchor="w")
        
        tk.Label(frame_filtros, text="Desde:", bg=COLOR_FONDO_MAIN, fg=COLOR_TEXTO_DARK, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.dia_inf, self.mes_inf, self.ano_inf = self.crear_selector_fecha_original(frame_filtros, defecto_inicio=True)
        
        tk.Label(frame_filtros, text="  Hasta:", bg=COLOR_FONDO_MAIN, fg=COLOR_TEXTO_DARK, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.dia_sup, self.mes_sup, self.ano_sup = self.crear_selector_fecha_original(frame_filtros, defecto_inicio=False)
        
        btn_filtrar = tk.Button(
            frame_filtros, text="🔍 Filtrar", command=self.aplicar_filtro_fechas,
            font=("Arial", 9, "bold"),
            cursor="hand2"
        )
        btn_filtrar.pack(side=tk.LEFT, padx=15)

        btn_exportar = ttk.Button(
            frame_filtros, 
            text="📊 Exportar a Excel", 
            command=self.exportar_qaqc_excel
        )
        btn_exportar.pack(side="left", padx=10)

        self.sep = tk.Frame(self.main_container, bg="#dcdde1", height=1)
        self.sep.pack(fill=tk.X, pady=(0, 20))

        lbl_welcome = tk.Label(
            self.main_container, text="INDICADORES CRÍTICOS - OFICINA TÉCNICA", 
            bg=COLOR_FONDO_MAIN, fg=COLOR_TEXTO_DARK, font=("Arial", 12, "bold")
        )
        lbl_welcome.pack(anchor="w", pady=(0, 15))
        
        self.cards_grid = tk.Frame(self.main_container, bg=COLOR_FONDO_MAIN)
        self.cards_grid.pack(anchor="w")

        self.crear_las_6_cartas()

        self.card_gauss_outer = tk.Frame(self.main_container, bg="#dcdde1", width=700, height=360)
        self.card_gauss_outer.pack(anchor="w", pady=(20, 10))
        self.card_gauss_outer.pack_propagate(False)
        
        self.card_gauss_inner = tk.Frame(self.card_gauss_outer, bg=COLOR_CARD_BG)
        self.card_gauss_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.card_gauss_inner.pack_propagate(False)
        
        # Línea estética superior del Card de Gauss
        self.accent_bar_gauss = tk.Frame(self.card_gauss_inner, bg=PALETA_BORDES["GAUSS"], height=4)
        self.accent_bar_gauss.pack(fill=tk.X, side=tk.TOP)
        
        # Label contenedor donde se incrustará la imagen PNG renderizada por Matplotlib
        self.lbl_contenedor_grafica = tk.Label(self.card_gauss_inner, text="Cargando distribución de taladros...", bg=COLOR_CARD_BG, fg=COLOR_TEXTO_MUTE, font=("Arial", 10, "italic"))
        self.lbl_contenedor_grafica.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


        # Carga automática inicial usando la referencia local segura
        self.after(100, self.cargar_datos_iniciales_automatico)

    def crear_las_6_cartas(self):
        """Inicializa las 6 cartas con los valores cargados."""
        self.card_voladuras = InfoCard(self.cards_grid, "Voladuras", self.valores_iniciales.get("total_voladuras", "0"), "Registradas en el periodo", PALETA_BORDES["VOLADURAS"])
        self.card_voladuras.grid(row=0, column=0, padx=10, pady=10)

        self.card_vod = InfoCard(self.cards_grid, "VOD Total", self.valores_iniciales.get("vod_promedio", "0.0"), "Metros por segundo (m/s)", PALETA_BORDES["VOD"])
        self.card_vod.grid(row=0, column=1, padx=10, pady=10)

        self.card_sismografia = InfoCard(self.cards_grid, "Sismografía", self.valores_iniciales.get("max_ppv", "0.00"), "Máximo PPV detectado (mm/s)", PALETA_BORDES["SISMOGRAFIA"])
        self.card_sismografia.grid(row=0, column=2, padx=10, pady=10)

        self.card_fragmentacion = InfoCard(self.cards_grid, "Fragmentación", self.valores_iniciales.get("p80_promedio", "0.0"), "P80 óptimo promedio (pulg)", PALETA_BORDES["FRAGMENTACION"])
        self.card_fragmentacion.grid(row=1, column=0, padx=10, pady=10)

        self.card_anfo = InfoCard(self.cards_grid, "Densidad ANFO", self.valores_iniciales.get("densidad_anfo", "0.82"), "Promedio en copa (g/cc)", PALETA_BORDES["DENS_ANFO"])
        self.card_anfo.grid(row=1, column=1, padx=10, pady=10)

        self.card_rioflex = InfoCard(self.cards_grid, "Densidad RIOFLEX", self.valores_iniciales.get("densidad_rioflex", "1.12"), "Promedio en copa (g/cc)", PALETA_BORDES["DENS_RIOFLEX"])
        self.card_rioflex.grid(row=1, column=2, padx=10, pady=10)

    def crear_selector_fecha_original(self, parent, defecto_inicio=True):
        container = tk.Frame(parent, bg=COLOR_FONDO_MAIN)
        container.pack(side=tk.LEFT, padx=2)
        
        now = datetime.now()
        dia_actual = 1 if defecto_inicio else calendar.monthrange(now.year, now.month)[1]
        mes_actual = now.month
        ano_actual = now.year
        
        dias_lista = [f"{i:02d}" for i in range(1, 32)]
        meses_lista = [f"{i:02d}" for i in range(1, 13)]
        anos_lista = [str(i) for i in range(ano_actual - 5, ano_actual + 2)]
        
        d = ttk.Combobox(container, values=dias_lista, width=3, state="readonly")
        d.set(f"{dia_actual:02d}")
        d.pack(side=tk.LEFT, padx=1)
        
        tk.Label(container, text="/", bg=COLOR_FONDO_MAIN, fg=COLOR_TEXTO_DARK, font=("Arial", 10)).pack(side=tk.LEFT)
        
        m = ttk.Combobox(container, values=meses_lista, width=3, state="readonly")
        m.set(f"{mes_actual:02d}")
        m.pack(side=tk.LEFT, padx=1)
        
        tk.Label(container, text="/", bg=COLOR_FONDO_MAIN, fg=COLOR_TEXTO_DARK, font=("Arial", 10)).pack(side=tk.LEFT)
        
        a = ttk.Combobox(container, values=anos_lista, width=5, state="readonly")
        a.set(str(ano_actual))
        a.pack(side=tk.LEFT, padx=1)

        return d, m, a

    def aplicar_filtro_fechas(self):
        """Filtrado ejecutado al hacer click en el botón."""
        f_inicio = f"{self.ano_inf.get()}-{self.mes_inf.get().zfill(2)}-{self.dia_inf.get().zfill(2)}"
        f_fin = f"{self.ano_sup.get()}-{self.mes_sup.get().zfill(2)}-{self.dia_sup.get().zfill(2)}"
        
        # 1. Consultar y refrescar las cartas locales usando la referencia de datos directa
        nuevos_kpis = obtener_datos_dashboard_kpi(f_inicio, f_fin)

        #print(nuevos_kpis)
        self.refrescar_dashboard(nuevos_kpis)
        self.actualizar_grafica_gauss_visual(f_inicio, f_fin)
        
        # 2. Refrescar la tabla de la pestaña Voladuras y cambiar visualmente a ella
        try:
            # Buscamos la app raíz para interactuar con las otras pestañas de forma segura
            top = self
            while hasattr(top, "master") and top.master is not None:
                top = top.master
            
            if hasattr(top, "tab_voladuras"):
                top.tab_voladuras.cargar_datos(f_inicio, f_fin)
                
            if hasattr(self, "master") and self.master is not None:
                self.master.select(1) # Cambiar a la pestaña de Voladuras
        except Exception as e:
            print(f"Error al redirigir pestaña: {e}")

    def exportar_qaqc_excel(self):
        # 1. Obtener las fechas de tu filtro actual en la interfaz
        fecha_ini = f"{self.ano_inf.get()}-{self.mes_inf.get().zfill(2)}-{self.dia_inf.get().zfill(2)}"
        fecha_fin = f"{self.ano_sup.get()}-{self.mes_sup.get().zfill(2)}-{self.dia_sup.get().zfill(2)}"
        
        #fecha_ini = self.input_fecha_inicio.get() # Ajusta al nombre real de tu variable
        #fecha_fin = self.input_fecha_fin.get()    # Ajusta al nombre real de tu variable
        
        if not fecha_ini or not fecha_fin:
            messagebox.showwarning("Advertencia", "Por favor selecciona un rango de fechas.")
            return

        # 2. Abrir ventana de diálogo para que el usuario elija dónde guardar
        ruta_archivo = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Archivos de Excel", "*.xlsx")],
            title="Exportar Datos QAQC",
            initialfile=f"Reporte_QAQC_{fecha_ini}_al_{fecha_fin}.xlsx"
        )

        if not ruta_archivo:
            return  # El usuario canceló la ventana

        try:
            print("⏳ Generando archivo Excel...")
            
            # A) Proyectos / Voladuras
            df_proyectos = obtener_proyectos(fecha_ini,fecha_fin)
            #print("PROYECTOS: ",df_proyectos)

            # B) VOD
            df_vod = obtener_vods(fecha_ini,fecha_fin)
            print("VOD: ",df_vod)

            # C) Densidades RIOFLEX
            query_rioflex = f"""
                SELECT r.*, p.nombre_proyecto, p.fecha 
                FROM densidades_rioflex r
                JOIN proyectos p ON r.id_proyecto = p.id
                WHERE p.fecha BETWEEN '{fecha_ini}' AND '{fecha_fin}'
            """
            print("sql RIOFLEX: ",query_rioflex)
            df_rioflex = pd.read_sql(query_rioflex, self.datos.conexion)
            print("RIOFLEX: ",query_rioflex)

            # D) Densidades ANFO
            query_anfo = f"""
                SELECT a.*, p.nombre_proyecto, p.fecha 
                FROM densidad_anfo a
                JOIN proyectos p ON a.id_proyecto = p.id
                WHERE p.fecha BETWEEN '{fecha_ini}' AND '{fecha_fin}'
            """
            df_anfo = pd.read_sql(query_anfo, self.datos.conexion)

            print("ANFO: ",df_anfo)

            df_proyectos = pd.DataFrame(df_proyectos)
            df_vod = pd.DataFrame(df_vod)



            if df_proyectos.empty and df_vod.empty and df_rioflex.empty and df_anfo.empty:
                messagebox.showinfo(
                    "Sin Datos", 
                    f"No se encontraron registros entre {fecha_ini} y {fecha_fin}."
                )
                print("⚠️ Exportación cancelada: No hay datos en estas fechas.")
                return # Detiene el proceso

            # 4. Escribir los DataFrames en un solo Excel con múltiples hojas
            with pd.ExcelWriter(ruta_archivo, engine='openpyxl') as writer:
                df_proyectos.to_excel(writer, sheet_name='Proyectos', index=False)
                df_vod.to_excel(writer, sheet_name='Registro VOD', index=False)
                df_rioflex.to_excel(writer, sheet_name='Densidad Rioflex', index=False)
                df_anfo.to_excel(writer, sheet_name='Densidad ANFO', index=False)

            messagebox.showinfo("Éxito", f"¡Reporte Excel generado correctamente en:\n{ruta_archivo}")
            print("✅ Excel exportado con éxito.")

        except Exception as e:
            print(e)
            messagebox.showerror("Error de Exportación", f"Hubo un problema al crear el Excel:\n{e}")

    def cargar_datos_iniciales_automatico(self):
        """Carga inicial automática al abrir el software usando la referencia local."""
        f_inicio = f"{self.ano_inf.get()}-{self.mes_inf.get().zfill(2)}-{self.dia_inf.get().zfill(2)}"
        f_fin = f"{self.ano_sup.get()}-{self.mes_sup.get().zfill(2)}-{self.dia_sup.get().zfill(2)}"
        
        try:
            print("Fecha Inicio: ",f_inicio," - ","Fecha Fin: ",f_fin)
            nuevos_kpis = obtener_datos_dashboard_kpi(f_inicio, f_fin)
            #print(nuevos_kpis)
            self.refrescar_dashboard(nuevos_kpis)
            self.actualizar_grafica_gauss_visual(f_inicio, f_fin)
            print(f"📊 Dashboard precargado con éxito para el rango: {f_inicio} al {f_fin}")
        except Exception as e:
            print(f"⚠️ Error al consultar KPIs en la precarga automática: {e}")

    def refrescar_dashboard(self, nuevos_datos):
        """Actualiza los valores de texto de los KPIs."""
        self.card_voladuras.actualizar_datos(nuevos_datos.get("total_voladuras", "0"), "Registradas en el periodo")
        self.card_vod.actualizar_datos(nuevos_datos.get("vod_total", "0"), "Registros")
        self.card_sismografia.actualizar_datos(nuevos_datos.get("sismo_total", "0"), "Registros")
        self.card_fragmentacion.actualizar_datos(nuevos_datos.get("p80_total", "0"), "Registros")
        self.card_anfo.actualizar_datos(nuevos_datos.get("densidad_anfo", "0"), "Registros")
        self.card_rioflex.actualizar_datos(nuevos_datos.get("densidad_rioflex", "0"), "Registros")

    def graficar_campana_gauss_taladros(self, lista_taladros):
        """Módulo Matplotlib optimizado con márgenes ajustados para evitar recortes en la tarjeta."""
        import matplotlib.pyplot as plt
        import numpy as np
        from scipy.stats import norm
        import os

        datos = np.array(lista_taladros)
        media = np.mean(datos)
        desviacion_estandar = np.std(datos)

        plt.rcParams['font.family'] = 'Arial'
        
        # 🟢 CORRECCIÓN 1: Definimos un tamaño ligeramente más compacto y alto proporcional
        fig, ax = plt.subplots(figsize=(6.2, 3.2)) 
        fig.patch.set_facecolor(COLOR_CARD_BG)
        ax.set_facecolor('#ffffff')

        # Histograma real
        ax.hist(datos, bins='auto', density=True, alpha=0.35, color='#3498db', edgecolor='#2980b9')

        # Curva de Gauss suavizada
        x = np.linspace(media - 3.5 * desviacion_estandar, media + 3.5 * desviacion_estandar, 200)
        y = norm.pdf(x, media, desviacion_estandar)
        ax.plot(x, y, color='#2c3e50', linewidth=2.0, label='Curva Gaussiana')
        ax.fill_between(x, y, color='#34495e', alpha=0.08)

        # Eje de la media
        ax.axvline(media, color='#e74c3c', linestyle='--', linewidth=1.2, label=f'Media: {media:.1f} tal.')

        # Estética minera ajustada
        ax.set_title('DISTRIBUCIÓN DE TALADROS POR VOLADURA', fontweight='bold', fontsize=9, color=COLOR_TEXTO_DARK, pad=10)
        ax.set_xlabel('Taladros en el Diseño', fontsize=8, fontweight='bold', color=COLOR_TEXTO_MUTE)
        ax.set_ylabel('Densidad de Probabilidad', fontsize=8, fontweight='bold', color=COLOR_TEXTO_MUTE)
        
        ax.tick_params(labelsize=8, colors=COLOR_TEXTO_DARK)
        ax.grid(True, linestyle=':', alpha=0.4)
        ax.legend(loc='upper left', fontsize=7, framealpha=0.8)

        # Cuadro de texto resumen
        texto = f"Proyectos: {len(datos)}\nμ: {media:.1f} tal.\nσ: {desviacion_estandar:.1f} tal."
        ax.text(0.97, 0.90, texto, transform=ax.transAxes, fontsize=7, fontweight='bold',
                verticalalignment='top', horizontalalignment='right', color='#2c3e50',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#f5f6fa', edgecolor='#dcdde1', alpha=0.9))

        # 🟢 CORRECCIÓN 2: Control absoluto de márgenes internos para forzar que todo quepa perfectamente
        fig.subplots_adjust(left=0.10, right=0.96, top=0.86, bottom=0.16)

        if not os.path.exists("./recursos"): 
            os.makedirs("./recursos")
            
        ruta_grafica = f"./recursos/gauss_taladros_home.png"
        
        # Guardamos ignorando cualquier desborde externo
        fig.savefig(ruta_grafica, dpi=115, bbox_inches='tight', transparent=True)
        plt.close(fig)
        
        return ruta_grafica

    def actualizar_grafica_gauss_visual(self, f_inicio, f_fin):

        try:
            # A. Solicitamos la lista pura de taladros por proyecto al conector DB
            lista_taladros = obtener_distribucion_taladros_gauss(f_inicio, f_fin)
            
            print("TALADROS: ",lista_taladros)
            if len(lista_taladros) < 2:
                self.lbl_contenedor_grafica.config(
                    image="",
                    text=f"Muestras insuficientes ({len(lista_taladros)} proyectos) en este periodo\npara calcular la campana de Gauss."
                )
                return

            # B. Llamamos a tu función graficadora (debe estar declarada en tu app o herencia)
            # Para este ejemplo asumimos que mapea la función que creamos en el paso anterior:
            ruta_png = self.graficar_campana_gauss_taladros(lista_taladros)
            
            if ruta_png and os.path.exists(ruta_png):
                # Convertimos el archivo en un objeto entendible por Tkinter
                self.imagen_gauss_actual = tk.PhotoImage(file=ruta_png)
                
                # Seteamos la imagen en el Label matando el texto informativo
                self.lbl_contenedor_grafica.config(image=self.imagen_gauss_actual, text="")
            else:
                self.lbl_contenedor_grafica.config(image="", text="Error al generar el lienzo de la gráfica.")

        except Exception as ex:
            print(f"⚠️ Error al renderizar gráfico de Gauss en la interfaz: {ex}")
            self.lbl_contenedor_grafica.config(image="", text="No se pudo procesar la distribución estadística.")







