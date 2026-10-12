import tkinter as tk
from tkinter import ttk
import database.datos_db as datos
from core.secuenciaLogica import calcular_isocronas
from core.motorGrafico import MotorGraficoMalla
from core.secuenciaLogica import agrupar_conexiones_por_lista, vincular_detonadores_a_conexiones, SecuenciaLogica
from vistas.configuracion import VentanaConfiguracionMalla
from vistas.gauss import VentanaGauss

import math
from scipy.stats import norm

# Librerías para el histograma
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class VistaDiseno(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.id_vola = None
        self.ventana_gauss = None
        self.panel_opt_abierto = False
        self.var_mostrar_ids = tk.BooleanVar(value=True)
        self.var_modo_texto = tk.BooleanVar(value=False)
        self.ventana_config = None # Referencia para no abrir mil ventanas

        # Variables de control
        self.var_label_size = tk.DoubleVar(value=2.0)
        self.var_label_x = tk.DoubleVar(value=0.2)
        self.var_label_y = tk.DoubleVar(value=0.2)
        self.var_flecha_size = tk.DoubleVar(value=3.0)
        self.var_tiempo_size = tk.DoubleVar(value=2.0)
        self.var_mostrar_relief = tk.BooleanVar(value=False)
        
        self.setup_ui()
        self.setup_traces()

        # --- ⚙️ BOTÓN FLOTANTE DE CONFIGURACIÓN ---
        self.btn_config = tk.Button(
            self.lienzo_interactivo, 
            text="⚙️", 
            font=("Arial", 18),
            command=self.abrir_configuracion,
            bg="white", 
            relief="raised",
            cursor="hand2",
            width=2
        )
        # Lo colocamos flotando arriba a la izquierda con un pequeño margen
        self.btn_config.place(x=10, y=10)

        self.btn_optimizacion = tk.Button(
            self.lienzo_interactivo, 
            text="📊", 
            font=("Arial", 18),
            command=self.abrir_optimizacion,
            bg="white", 
            relief="raised",
            cursor="hand2",
            width=2
        )
        # Lo colocamos debajo del de configuración (y=60)
        self.btn_optimizacion.place(x=10, y=70)

        # Almacén de datos para la gráfica
        self.datos_graficar_actuales = []
        self.tiempos_por_id_actual = {}

        self.var_label_size.trace_add("write", self.al_cambiar_labels)
        self.var_flecha_size.trace_add("write", self.al_cambiar_conexiones)
        self.var_tiempo_size.trace_add("write", self.al_cambiar_conexiones)
        self.var_mostrar_ids.trace_add("write", self.al_cambiar_labels)
        self.var_mostrar_relief.trace_add("write", self.al_cambiar_conexiones)

        #self.dibujar_malla()

    def setup_ui(self):
        """Configuración para ventana flotante (sin división de pantalla)."""
        # Eliminamos el PanedWindow para que el motor ocupe todo
        self.lienzo_interactivo = MotorGraficoMalla(self, bg="#E5E5E5")
        self.lienzo_interactivo.pack(fill="both", expand=True)

        # Botones flotantes
        self.btn_config = tk.Button(self.lienzo_interactivo, text="⚙️", font=("Arial", 18),
                                   command=self.abrir_configuracion, bg="white", relief="raised", cursor="hand2", width=2)
        self.btn_config.place(x=10, y=10)

        self.btn_optimizacion = tk.Button(self.lienzo_interactivo, text="📊", font=("Arial", 18),
                                         command=self.abrir_optimizacion, bg="white", relief="raised", cursor="hand2", width=2)
        self.btn_optimizacion.place(x=10, y=70)

    def setup_traces(self):
        self.var_label_size.trace_add("write", self.al_cambiar_labels)
        self.var_flecha_size.trace_add("write", self.al_cambiar_conexiones)
        self.var_tiempo_size.trace_add("write", self.al_cambiar_conexiones)
        self.var_mostrar_ids.trace_add("write", self.al_cambiar_labels)
        self.var_mostrar_relief.trace_add("write", self.al_cambiar_conexiones)

    def actualizar_histograma(self):
        """Redirige la actualización a la ventana flotante si está abierta."""
        if self.ventana_gauss and self.ventana_gauss.winfo_exists():
            self.ventana_gauss.actualizar()

    def abrir_configuracion(self):
        """Abre la ventana de configuración desde el botón de la interfaz."""
        # Si ya existe y está abierta, solo la traemos al frente
        if self.ventana_config is not None and self.ventana_config.winfo_exists():
            self.ventana_config.lift()
            self.ventana_config.focus_force()
            return
        
        # Le pasamos 'self' como padre
        self.ventana_config = VentanaConfiguracionMalla(self)
        
        # 💡 TRUCO MAC: Forzamos a que la ventana se procese antes de seguir
        self.ventana_config.update_idletasks()
        self.ventana_config.lift()
        self.ventana_config.focus_force()

    def al_mover_slider_radio(self, *args):
        """Envía el nuevo radio al motor gráfico para que filtre las líneas en tiempo real."""
        if hasattr(self, 'lienzo_interactivo'):
            nuevo_radio = self.var_radio_topo.get()
            self.lienzo_interactivo.aplicar_filtro_radio(nuevo_radio)

    def dibujar_malla(self,id_vola):
        
        taladros_completos = datos.obtener_taladros_por_proyecto(id_vola)
        
        if not taladros_completos:
            self.lienzo_interactivo.cargar_taladros([])
            centro_x = self.lienzo_interactivo.winfo_width() / 2
            centro_y = self.lienzo_interactivo.winfo_height() / 2
            self.lienzo_interactivo.create_text(
                centro_x if centro_x > 0 else 400, 
                centro_y if centro_y > 0 else 300, 
                text="No hay taladros activos para esta voladura", fill="gray", font=("Arial", 14))
            return

        # 2. Empaquetamos para el motor gráfico (Ahora pasamos el ID_Taladro como primer valor)
        coordenadas_2d = [(t["id_taladro"], t["label"], t["x"], t["y"]) for t in taladros_completos]
        self.lienzo_interactivo.cargar_taladros(coordenadas_2d)

        # 👇 2. NUEVO: Cargamos las conexiones
        #conexiones = datos.obtener_conexiones_voladura(id_vola)
        conexiones = datos.obtener_conexiones_por_proyecto(id_vola)
        detonadorportaladro = datos.obtener_detonadores_por_proyecto(id_vola)
        inicios = datos.obtener_inicios_voladura(id_vola)

        if conexiones:
            conexiones_vinculadas = vincular_detonadores_a_conexiones(conexiones, detonadorportaladro)
            conexiones_agrupadas = agrupar_conexiones_por_lista(conexiones_vinculadas)

            # Motor lógico (Usa IDs puros)
            motor_secuencia = SecuenciaLogica()
            secuencia_ordenada = motor_secuencia.crear_secuencia_ordenada_db2(
                conexion=conexiones_agrupadas,
                conexion_ordenada=[],
                taladros=taladros_completos
            )

            conexiones_finales_planas = [con for ramal in secuencia_ordenada for con in ramal]
            datos_para_graficar = []
            
            mapa_taladros = {str(t["id_taladro"]): t for t in taladros_completos}
            
            self.reliefs_produccion = []
            self.reliefs_cuidados = []
            
            for con in conexiones_finales_planas:
                id_origen = str(con.get("hole1", {}).get("id_taladro", ""))
                id_destino = str(con.get("hole2", {}).get("id_taladro", ""))
                
                t1 = mapa_taladros.get(id_origen)
                t2 = mapa_taladros.get(id_destino)

                if not t1 or not t2: continue

                distancia = math.hypot(t2["x"] - t1["x"], t2["y"] - t1["y"])
                tiempo = float(con.get("tiempo_taladro", 0))
                relief = round(tiempo / distancia if distancia > 0 else 0, 2)

                # --- 2. Lógica de clasificación ---
                label_dest = str(t2.get("label", "")).upper()
                # Consideramos buffer si el label contiene "BUF" o el tipo es "BUFFER"
                es_buffer = "BUF" in label_dest or t2.get("tipo") == "BUFFER"

                if es_buffer:
                    self.reliefs_cuidados.append(relief)
                    color_bg = "#E67E22" # Naranja para Cuidados
                else:
                    self.reliefs_produccion.append(relief)
                    color_bg = "#3498db" # Azul para Producción

                datos_para_graficar.append({
                    "origen": id_origen,
                    "destino": id_destino,
                    "tiempo": tiempo,
                    "relief": relief,
                    "color": con.get("color", "#FF0000"),
                    "color_bg": color_bg # Para que el motor gráfico pinte los círculos
                })

                # Guardamos para que la ventana flotante pueda acceder
            self.datos_graficar_actuales = datos_para_graficar 
            self.actualizar_histograma()

            # 4. Calcular Isocronas usando los IDs
            
            inicios_id = [str(t.get("id_taladro")) for t in taladros_completos if t.get("is_inicio")]
            
            # Este diccionario ya está ligado a los IDs, no hay que traducirlo
            tiempos_por_id = calcular_isocronas(conexiones_finales_planas, inicios)

            #print(tiempos_por_id)

            self.lienzo_interactivo.cargar_conexiones(datos_para_graficar, tiempos_por_id)

            self.datos_graficar_actuales = datos_para_graficar 
            self.tiempos_por_id_actual = tiempos_por_id

            self.actualizar_histograma()

    def importar_dxf_rapido(self):
        from tkinter import filedialog, messagebox
        
        # 1. El usuario elige el archivo
        ruta_dxf = filedialog.askopenfilename(
            title="Seleccionar Topografía DXF", 
            filetypes=(("Archivos DXF", "*.dxf"), ("Todos", "*.*"))
        )
        
        if ruta_dxf:
            # 2. Llamamos al método del motor gráfico
            # (El motor hace la conversión pesada y se encarga de mostrarla)
            self.lienzo_interactivo.cargar_dxf_como_fondo(ruta_dxf)

    def validar_centro_malla(self):
        """Revisa si hay una malla cargada antes de importar DXF."""
        if not hasattr(self.lienzo_interactivo, 'centro_x') or not hasattr(self.lienzo_interactivo, 'centro_y'):
            from tkinter import messagebox
            messagebox.showwarning("Atención", "Por favor, carga o selecciona una voladura primero.")
            return False
        return True
    
    def importar_toe(self):
        from tkinter import filedialog
        if not self.validar_centro_malla(): return
        ruta = filedialog.askopenfilename(title="Seleccionar archivo Toe (Pie)", filetypes=[("DXF", "*.dxf")])
        if ruta:
            # Mandamos a cargar la capa y le forzamos el color "red"
            self.lienzo_interactivo.cargar_dxf_como_fondo(ruta,"#F23800")
            # Re-aplicamos el radio del slider para que filtre las líneas nuevas
            self.lienzo_interactivo.aplicar_filtro_radio(self.var_radio_topo.get())

    def importar_cresta(self):
        from tkinter import filedialog
        if not self.validar_centro_malla(): return
        ruta = filedialog.askopenfilename(title="Seleccionar archivo Cresta", filetypes=[("DXF", "*.dxf")])
        if ruta:
            # Mandamos a cargar la capa y le forzamos el color "blue"
            self.lienzo_interactivo.cargar_dxf_como_fondo(ruta, "#0005F2")
            self.lienzo_interactivo.aplicar_filtro_radio(self.var_radio_topo.get())

    def limpiar_topografia(self):
        """Botón de emergencia para borrar todas las capas sin borrar los taladros."""
        if hasattr(self, 'lienzo_interactivo'):
            self.lienzo_interactivo.limpiar_topografia()

    def al_cambiar_estilo(self, *args):
        """Envía la opacidad y el estilo al motor gráfico al instante."""
        if hasattr(self, 'lienzo_interactivo'):
            opacidad_pct = self.var_opacidad.get()
            punteado = self.var_punteado.get()
            self.lienzo_interactivo.actualizar_apariencia_topo(opacidad_pct, punteado)

    def al_cambiar_labels(self, *args):
        """Actualiza el tamaño y visibilidad de los IDs de los taladros."""
        # 🛡️ CORRECCIÓN: Usar 'var_mostrar_ids' que es el nombre real
        if not hasattr(self, 'var_mostrar_ids'):
            return

        if hasattr(self, 'lienzo_interactivo'):
            # Obtenemos los valores de las variables de control
            mostrar = self.var_mostrar_ids.get()
            size = self.var_label_size.get()
            off_x = self.var_label_x.get()
            off_y = self.var_label_y.get()
            
            # 🟢 VITAL: Llamamos al método que cambia el 'state' (normal/hidden)
            # No basta con llamar a renderizar(), hay que cambiar la visibilidad
            self.lienzo_interactivo.actualizar_config_labels(mostrar, size, off_x, off_y)

    def al_cambiar_conexiones(self, *args):
        """Actualiza flechas, textos de tiempo y modo relief."""
        if hasattr(self, 'lienzo_interactivo'):
            size_flecha = self.var_flecha_size.get()
            size_tiempo = self.var_tiempo_size.get()
            # 🟢 Verificamos que se esté leyendo correctamente la variable del Checkbutton
            modo_relief = self.var_mostrar_relief.get() 
            
            # Pasamos los 3 parámetros al motor
            self.lienzo_interactivo.actualizar_config_conexiones(size_flecha, size_tiempo, modo_relief)

    def al_cambiar_modo_texto(self, *args):
        """Cambia entre modo ID y modo Isocrona (Tiempos)."""
        if hasattr(self, 'lienzo_interactivo'):
            modo = 'isocrona' if self.var_modo_texto.get() else 'id'
            self.lienzo_interactivo.actualizar_modo_textos(modo)
            self.lienzo_interactivo.renderizar()

    def abrir_optimizacion(self):
        """Abre o trae al frente la ventana flotante de Gauss."""
        # Si la ventana no existe o fue cerrada, la creamos
        if self.ventana_gauss is None or not self.ventana_gauss.winfo_exists():
            from vistas.gauss import VentanaGauss # O donde tengas la clase
            self.ventana_gauss = VentanaGauss(self)
        else:
            # Si ya existe, la traemos al frente y actualizamos
            self.ventana_gauss.lift()
            self.ventana_gauss.focus_force()
            self.ventana_gauss.actualizar()

    def _ajustar_divisor(self):
        """Mueve físicamente la barra divisoria para que el panel inferior sea bajo."""
        altura_total = self.winfo_height()
        # Colocamos la barra a 180 píxeles del borde inferior
        posicion_sash = altura_total - 180
        if posicion_sash > 0:
            self.pw.sash_place(0, 0, posicion_sash)


