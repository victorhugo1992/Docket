import tkinter as tk
import math
from PIL import Image, ImageTk, ImageDraw
import ezdxf

class MotorGraficoMalla(tk.Canvas):
    """Motor gráfico 2D interactivo puro. 100% Nativo, sin dependencias."""
    
    def __init__(self, parent, **kwargs):
        # Modo oscuro (CAD Style) para que resalten los taladros
        background = kwargs.pop('bg', "#E9E9E9")
        super().__init__(parent, bg=background, highlightthickness=0, **kwargs) 

        #self.coordenadas = []
        #self.taladros_norm = []

        self.taladros_norm = []
        self.items_dibujados = []
        
        # Variables de la Cámara Virtualq
        self.zoom = 1.0
        self.pan_x = 400
        self.pan_y = 300
        self.rotacion = 0.0
        
        self.last_x = 0
        self.last_y = 0

        # --- Bindings del Ratón (Multiplataforma) ---
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag_rotate)   # Click Izquierdo = Rotar
        
        self.bind("<ButtonPress-2>", self.on_press)     # Rueda (Click)
        self.bind("<ButtonPress-3>", self.on_press)     # Click Derecho
        self.bind("<B2-Motion>", self.on_drag_pan)      # Click Der/Medio = Mover
        self.bind("<B3-Motion>", self.on_drag_pan)
        
        # Rueda para Zoom (Detecta Mac y Windows)
        self.bind("<MouseWheel>", self.on_zoom)
        self.bind("<Button-4>", self.on_zoom)
        self.bind("<Button-5>", self.on_zoom)

        # Si el usuario estira la ventana, redibujamos
        self.bind("<Configure>", lambda e: self.renderizar() if self.taladros_norm else None)

    def cargar_taladros(self, nuevas_coordenadas):
        """Carga una nueva malla y resetea el estado gráfico."""
        self.coordenadas = nuevas_coordenadas
        # 🛡️ Limpiamos los taladros normalizados para que no haya descalce de índices
        self.taladros_norm = []
        self.items_dibujados = []
        self.items_labels = []
        
        # Opcional: limpiar conexiones viejas de la memoria inmediatamente
        if hasattr(self, 'datos_conexiones_render'):
            self.datos_conexiones_render = []
            
        self.enfocar_malla()

    def enfocar_malla(self):
        """Calcula el Bounding Box, centra la cámara y ajusta el zoom al 85%."""
        if not hasattr(self, 'coordenadas') or not self.coordenadas:
            return
        
        self.mapa_id_a_label = {}
        
        # 1. Bounding Box (Límites extremos) - Desempaquetando 4 valores
        xs = [x for id_tal, lbl, x, y in self.coordenadas]
        ys = [y for id_tal, lbl, x, y in self.coordenadas]
        
        # Guardamos el mapa relacionando el ID con el Label visual
        for id_tal, lbl, x, y in self.coordenadas:
            self.mapa_id_a_label[str(id_tal)] = str(lbl)
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # 2. Centro Visual exacto
        self.centro_x = (min_x + max_x) / 2.0
        self.centro_y = (min_y + max_y) / 2.0
        
        # 3. Normalizar - Desempaquetando 4 valores
        self.taladros_norm = [(x - self.centro_x, y - self.centro_y) for id_tal, lbl, x, y in self.coordenadas]
        
        # 4. Obtener medidas reales de la pantalla
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        
        # Fallback de seguridad (por si acaso)
        if w < 50: w = 800
        if h < 50: h = 600
        
        # 5. Calcular el Zoom perfecto para ocupar el 85% de la pantalla (Margen elegante)
        ancho_malla = max_x - min_x
        alto_malla = max_y - min_y
        
        if ancho_malla == 0: ancho_malla = 1
        if alto_malla == 0: alto_malla = 1
        
        zoom_x = (w * 0.85) / ancho_malla
        zoom_y = (h * 0.85) / alto_malla
        
        # Configuramos la cámara
        self.zoom = min(zoom_x, zoom_y)
        self.pan_x = w / 2
        self.pan_y = h / 2
        self.rotacion = 0.0

        # 6. Crear los círculos y los textos en memoria
        self.delete("taladros", "labels") # Borramos también los labels viejos
        self.items_dibujados = []
        self.items_labels = [] # Nueva lista para guardar las etiquetas
        
        # Valores por defecto si no se han tocado los controles
        self.mostrar_labels = getattr(self, 'mostrar_labels', True)
        self.label_size = getattr(self, 'label_size', 1)
        self.label_offset_x = getattr(self, 'label_offset_x', 0.2)
        self.label_offset_y = getattr(self, 'label_offset_y', 0.2)
        estado_inicial = "normal" if self.mostrar_labels else "hidden"

        for i, (x, y) in enumerate(self.taladros_norm):
            item_taladro = self.create_oval(0, 0, 0, 0, fill="#E8E7E7", outline="#484848", width=1, tags="taladros")
            self.items_dibujados.append(item_taladro)
            
            # Extraemos los 4 valores de nuestra lista de coordenadas real
            id_tal, lbl, orig_x, orig_y = self.coordenadas[i]
            
            # Limpiamos el texto por si venía con decimales desde la DB ("1.0" -> "1")
            try:
                texto_id = str(int(float(lbl)))
            except ValueError:
                texto_id = str(lbl)

            item_label = self.create_text(0, 0, text=texto_id, fill="#111111", 
                                          font=("Arial", int(self.label_size)), state=estado_inicial, tags="labels")
            self.items_labels.append(item_label)

        if hasattr(self, 'datos_conexiones_crudas'):
            self._construir_conexiones()
        
        # 7. Renderizar todo de golpe
        self.renderizar()

    def renderizar(self):
        """Aplica las matrices de transformación y mueve/escala los puntos instantáneamente."""
        self.delete("grid","brujula")
        
        cos_a = math.cos(self.rotacion)
        sin_a = math.sin(self.rotacion)
        ox, oy = self.pan_x, self.pan_y

        # 👇 LA MAGIA DE RENDERIZADO OPTIMIZADO
        if getattr(self, 'topo_vectores', None) is not None and getattr(self, 'items_topo', None) is not None:
            # zip une las matemáticas en memoria con la línea real en la pantalla
            for (coords_planas, color), item in zip(self.topo_vectores, self.items_topo):
                
                coords_pantalla = []
                
                # Iteramos la lista plana saltando de 2 en 2 (X, Y)
                for i in range(0, len(coords_planas), 2):
                    x = coords_planas[i]
                    y = coords_planas[i+1]
                    
                    rot_x = x * cos_a - y * sin_a
                    rot_y = x * sin_a + y * cos_a
                    
                    screen_x = ox + (rot_x * self.zoom)
                    screen_y = oy - (rot_y * self.zoom)
                    
                    coords_pantalla.extend([screen_x, screen_y])
                
                # Actualizamos la polilínea entera con un solo comando
                if coords_pantalla:
                    self.coords(item, *coords_pantalla)
        
        # --- 2. DIBUJAR BRÚJULA (Norte Dinámico) ---
        w = self.winfo_width()
        if w < 10: w = 800 # Fallback de seguridad
        
        # Coordenadas fijas en la esquina superior derecha
        cx, cy = w - 60, 60
        radio_brujula = 25
        
        # Dibujar el anillo exterior de la brújula (opcional, le da toque CAD)
        self.create_oval(cx - radio_brujula, cy - radio_brujula, 
                         cx + radio_brujula, cy + radio_brujula,
                         outline="#888888", width=2, tags="brujula")
        
        # Matemáticas para rotar la aguja sincronizada con la malla
        # El Norte (Y positivo en el mundo real) va hacia arriba, por eso restamos en Tkinter
        norte_x = cx - (radio_brujula * sin_a)
        norte_y = cy - (radio_brujula * cos_a)
        
        sur_x = cx + (radio_brujula * sin_a)
        sur_y = cy + (radio_brujula * cos_a)
        
        # Dibujar Aguja Sur (Gris)
        self.create_line(cx, cy, sur_x, sur_y, fill="#AAAAAA", width=3, tags="brujula")
        # Dibujar Aguja Norte (Roja con flecha)
        self.create_line(cx, cy, norte_x, norte_y, fill="#E63946", width=3, arrow=tk.LAST, tags="brujula")
        
        # Colocar la letra "N" flotando sobre la flecha roja
        text_x = cx - ((radio_brujula + 15) * sin_a)
        text_y = cy - ((radio_brujula + 15) * cos_a)
        self.create_text(text_x, text_y, text="N", fill="#E63946", font=("Arial", 10, "bold"), tags="brujula")

        if hasattr(self, 'topo_vectores'):
            self.tag_lower("topo") # Manda la topografía al fondo

        # --- 4. RENDERIZAR TALADROS Y ETIQUETAS DINÁMICAS ---
        radio_visual = max(2.0, 1.2 * self.zoom)

        if hasattr(self, 'taladros_norm') and hasattr(self, 'items_dibujados'):
            
            # 👇 A. MATEMÁTICA DE ESCALA PARA TEXTOS Y OFFSETS
            # Calculamos cuántas veces nos hemos acercado respecto al inicio
            factor_zoom = self.zoom / getattr(self, 'zoom_base', 1.0)
            
            # El nuevo tamaño base (desde tu slider) multiplicado por el zoom
            # Lo limitamos entre 2 y 100 para que Tkinter no colapse si haces un zoom extremo
            size_base = getattr(self, 'label_size', 9)
            # Usamos max(1, ...) para garantizar que la fuente nunca sea menor a 1
            nuevo_size = max(1, min(100, int(size_base * factor_zoom)))
            
            # TRUCO DE RENDIMIENTO: Solo cambiamos la fuente si el número entero cambió.
            # Esto mantiene los Paneos y Rotaciones súper fluidos sin lag.
            if getattr(self, 'current_font_size', 0) != nuevo_size:
                self.current_font_size = nuevo_size
                if hasattr(self, 'items_labels'):
                    for lbl in self.items_labels:
                        self.itemconfig(lbl, font=("Arial", nuevo_size, "bold"))

            extra_espacio = 1.5 if getattr(self, 'modo_texto_taladro', 'id') == 'isocrona' else 1.0
            off_x = getattr(self, 'label_offset_x', 10) * factor_zoom * extra_espacio
            off_y = getattr(self, 'label_offset_y', -10) * factor_zoom

            # Escalamos los Offsets para que la distancia se vea natural con el nuevo tamaño
           # off_x = getattr(self, 'label_offset_x', 10) * factor_zoom
            #off_y = getattr(self, 'label_offset_y', -10) * factor_zoom

            # 👇 B. MOVER TODOS LOS ELEMENTOS
            for i, (x, y) in enumerate(self.taladros_norm):
                if i < len(self.items_dibujados):
                    rot_x = x * cos_a - y * sin_a
                    rot_y = x * sin_a + y * cos_a
                    
                    screen_x = ox + (rot_x * self.zoom)
                    screen_y = oy - (rot_y * self.zoom)
                    
                    # 1. Mover Círculo
                    self.coords(self.items_dibujados[i], 
                                screen_x - radio_visual, screen_y - radio_visual, 
                                screen_x + radio_visual, screen_y + radio_visual)
                    
                    # 2. Mover Etiqueta
                    if hasattr(self, 'items_labels') and i < len(self.items_labels):
                        self.coords(self.items_labels[i], screen_x + off_x, screen_y + off_y)

            # --- NUEVO: RENDERIZAR CONEXIONES ---
       
        if hasattr(self, 'datos_conexiones_render'):
            factor_zoom = self.zoom / getattr(self, 'zoom_base', 1.0)
            
            base_grosor = getattr(self, 'base_flecha_size', 2.0)
            base_tiempo = getattr(self, 'base_tiempo_size', 2.0)
            
            # 👇 REDUCIMOS LOS MULTIPLICADORES AQUÍ
            nuevo_grosor = max(1, int((base_grosor / 10) * factor_zoom)) 
            size_texto_con = max(1, int((base_tiempo * 0.5) * factor_zoom))

            # ==========================================
            # 🎯 NUEVO: CÁLCULO DINÁMICO DE LA FLECHA
            # ==========================================
            # Usamos tu factor_zoom para escalar la geometría. 
            # (El divisor 5.0 es para que no sea absurdamente gigante, puedes ajustarlo)
            escala_flecha = factor_zoom * (base_grosor / 12.0) 

            d1 = max(6, int(8 * escala_flecha))  # Largo interno
            d2 = max(8, int(10 * escala_flecha)) # Largo total
            d3 = max(3, int(4 * escala_flecha))  # Ancho de las alas (¡Ahora sí!)
            
            #ala = max(3, int(8 * escala_flecha))    # Ancho de las puntas
            #largo = max(4, int(10 * escala_flecha)) # Largo de la punta
            #tallo = max(1, nuevo_grosor)            # El tallo sigue el grosor de la línea
            # ==========================================

            actualizar_estilo = False
            # Actualizamos la tupla de validación para incluir d1, d2, d3
            if getattr(self, 'current_con_style', None) != (nuevo_grosor, size_texto_con, d1, d2, d3):
                self.current_con_style = (nuevo_grosor, size_texto_con, d1, d2, d3)
                actualizar_estilo = True

            for con in self.datos_conexiones_render:
                rot_x1 = con["x1"] * cos_a - con["y1"] * sin_a
                rot_y1 = con["x1"] * sin_a + con["y1"] * cos_a
                rot_x2 = con["x2"] * cos_a - con["y2"] * sin_a
                rot_y2 = con["x2"] * sin_a + con["y2"] * cos_a
                
                # Estos son los centros exactos de los taladros en la pantalla
                sx1 = ox + (rot_x1 * self.zoom)
                sy1 = oy - (rot_y1 * self.zoom)
                sx2 = ox + (rot_x2 * self.zoom)
                sy2 = oy - (rot_y2 * self.zoom)
                
                # =======================================================
                # 🛑 MATEMÁTICA CAD: Recortar línea a los bordes
                # =======================================================
                dx = sx2 - sx1
                dy = sy2 - sy1
                distancia = math.hypot(dx, dy)

                # 👇 EL NÚMERO MÁGICO (Ajuste Fino)
                # Como 10 era demasiado, bajamos el radio base a 4.
                # (Si sigue separado, bájalo a 3. Si entra un poquito al taladro, súbelo a 5)
                radio_pantalla = 1.2 * self.zoom 

                # ESCUDO para cuando alejamos mucho la cámara
                if (radio_pantalla * 2) >= distancia:
                    radio_pantalla = distancia * 0.30

                if distancia > 0.1: 
                    ux = dx / distancia
                    uy = dy / distancia
                    
                    # 1. Recorte del ORIGEN (Donde nace la línea)
                    cx1 = sx1 + (ux * radio_pantalla)
                    cy1 = sy1 + (uy * radio_pantalla)
                    
                    # 2. Recorte del DESTINO (Donde clava la flecha)
                    # Le multiplicamos por 0.8 porque a veces Tkinter dibuja la punta de 
                    # la flecha un poquito hacia atrás de su coordenada final real.
                    cx2 = sx2 - (ux * (radio_pantalla * 0.8))
                    cy2 = sy2 - (uy * (radio_pantalla * 0.8))
                else:
                    cx1, cy1, cx2, cy2 = sx1, sy1, sx2, sy2
                # =======================================================

                # Calcular el centro exacto para la caja de texto (en la línea ya recortada)
                medio_x = (cx1 + cx2) / 2
                medio_y = (cy1 + cy2) / 2
                
                # Mover línea y texto
                self.coords(con["linea"], cx1, cy1, cx2, cy2)
                self.coords(con["texto"], medio_x, medio_y) 
                
                # Matemáticas rápidas para el borde del rectángulo
                pad_x = (con["len_txt"] * size_texto_con * 0.35) + 1
                pad_y = (size_texto_con * 0.5) + 1
                
                # Mover rectángulo
                self.coords(con["fondo"], medio_x - pad_x, medio_y - pad_y, medio_x + pad_x, medio_y + pad_y)

                if actualizar_estilo:
                    self.itemconfig(con["linea"], width=nuevo_grosor, arrowshape=(d1, d2, d3))
                    self.itemconfig(con["texto"], font=("Arial", size_texto_con, "bold"))
        
    def on_press(self, event):
        self.last_x, self.last_y = event.x, event.y

    def on_drag_pan(self, event):
        self.pan_x += (event.x - self.last_x)
        self.pan_y += (event.y - self.last_y)
        self.last_x, self.last_y = event.x, event.y

        self.renderizar()

    def on_drag_rotate(self, event):
        """Rotación radial interactiva. Gira como si agarraras la malla con la mano."""
        import math
        
        # 1. Calculamos el ángulo anterior respecto al centro visual (pan_x, pan_y)
        angulo_ant = math.atan2(self.last_y - self.pan_y, self.last_x - self.pan_x)
        
        # 2. Calculamos el nuevo ángulo con la posición actual del ratón
        angulo_nuevo = math.atan2(event.y - self.pan_y, event.x - self.pan_x)
        
        # 3. ¿Cuánto giró la mano?
        delta_angulo = angulo_nuevo - angulo_ant
        
        # 4. Corrección matemática de seguridad (evita saltos bruscos si cruzas el eje 0)
        if delta_angulo > math.pi:
            delta_angulo -= 2 * math.pi
        elif delta_angulo < -math.pi:
            delta_angulo += 2 * math.pi
            
        # 5. Aplicamos el giro (Cámbialo a += si prefieres el giro invertido)
        self.rotacion -= delta_angulo
        
        # Actualizamos la posición del ratón para el siguiente cuadro
        self.last_x = event.x
        self.last_y = event.y
        self.renderizar()

    def on_zoom(self, event):
        """Calcula el factor de escala asegurando la dirección correcta."""
        # Detectar dirección del scroll
        if hasattr(event, 'delta') and event.delta != 0:
            # En Mac, un delta positivo es scroll arriba (queremos Zoom IN)
            factor = 1.1 if event.delta > 0 else 0.9
        else:
            # Para Linux/Tkinter clásico (Button 4 es scroll arriba)
            factor = 1.1 if event.num == 4 else 0.9
            
        # Zoom apuntando exactamente a donde está el cursor
        self.pan_x = event.x - (event.x - self.pan_x) * factor
        self.pan_y = event.y - (event.y - self.pan_y) * factor
        
        # Multiplicamos el nivel general de zoom
        self.zoom *= factor
        
        self.renderizar()

    def cargar_dxf_como_fondo2(self, ruta_dxf):
        """Lee el DXF filtrando solo un radio de 200m alrededor de la malla."""
        
        # Guardamos el centro en el motor por si lo necesitamos después
        #self.centro_x = centro_x
        #self.centro_y = centro_y

        # --- 2. MOSTRAR PANTALLA DE CARGA ---
        self.delete("all")
        centro_pantalla_x = self.winfo_width() / 2 if self.winfo_width() > 10 else 400
        centro_pantalla_y = self.winfo_height() / 2 if self.winfo_height() > 10 else 300
        
        self.create_text(centro_pantalla_x, centro_pantalla_y, 
                         text="⏳ Recortando Topografía a 200m...\nEsto será rápido.",
                         fill="gray", font=("Arial", 14, "bold"), justify="center", tags="cargando")
        self.update() 

        try:
            doc = ezdxf.readfile(ruta_dxf)
            msp = doc.modelspace()
            
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            lineas = []
            
            # --- 3. CONFIGURAR EL FILTRO ESPACIAL (Bounding Box de 200m) ---
            radio = 200.0
            limite_izq = self.centro_x - radio
            limite_der = self.centro_x + radio
            limite_abj = self.centro_y - radio
            limite_arr = self.centro_y + radio

            def punto_en_radio(x, y):
                """Función rápida para saber si un punto está dentro del cuadro de 200m"""
                return (limite_izq <= x <= limite_der) and (limite_abj <= y <= limite_arr)

            # --- 4. EL ESCÁNER FILTRADO ---
            for entity in msp.query('LINE LWPOLYLINE POLYLINE SPLINE 3DFACE'):
                puntos_temp = []

                if entity.dxftype() == '3DFACE':
                    puntos_temp = [(entity.dxf.vtx0.x, entity.dxf.vtx0.y), 
                                   (entity.dxf.vtx1.x, entity.dxf.vtx1.y),
                                   (entity.dxf.vtx2.x, entity.dxf.vtx2.y), 
                                   (entity.dxf.vtx3.x, entity.dxf.vtx3.y)]
                    # Cerramos el triángulo/cuadrado
                    puntos_temp.append(puntos_temp[0]) 

                elif entity.dxftype() == 'LINE':
                    puntos_temp = [(entity.dxf.start.x, entity.dxf.start.y), 
                                   (entity.dxf.end.x, entity.dxf.end.y)]
                    
                elif entity.dxftype() == 'LWPOLYLINE':
                    puntos_temp = [(p[0], p[1]) for p in entity.get_points('xy')]

                elif entity.dxftype() == 'POLYLINE':
                    puntos_temp = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]

                # Convertir a segmentos y FILTRAR
                if len(puntos_temp) >= 2:
                    for i in range(len(puntos_temp) - 1):
                        x1, y1 = puntos_temp[i]
                        x2, y2 = puntos_temp[i+1]
                        
                        # ⚡ EL FILTRO: Solo guardamos la línea si AL MENOS UN extremo está cerca de la malla
                        if punto_en_radio(x1, y1) or punto_en_radio(x2, y2):
                            lineas.append((x1, y1, x2, y2))
                            min_x = min(min_x, x1, x2)
                            max_x = max(max_x, x1, x2)
                            min_y = min(min_y, y1, y2)
                            max_y = max(max_y, y1, y2)

            if not lineas:
                self.delete("cargando")
                self.create_text(centro_pantalla_x, centro_pantalla_y, 
                                 text="⚠️ El DXF cargó, pero no hay topografía a menos de 200m de esta malla.\nVerifica las coordenadas.", 
                                 fill="red", font=("Arial", 12), justify="center")
                # Si falla, igual redibujamos la malla que estaba antes
                self.after(2000, self.renderizar) 
                return

            self.itemconfig("cargando", text="🖌️ Dibujando alta resolución...")
            self.update()

            # --- 5. DIBUJAR LA IMAGEN OPTIMIZADA ---
            ancho_m = max_x - min_x
            alto_m = max_y - min_y

            # Como ahora la zona es pequeña (max 400x400m), podemos darle MUCHA resolución (10px por metro)
            width_px = int(max(ancho_m * 3, 1))
            height_px = int(max(alto_m * 3, 1))
            
            img = Image.new("RGBA", (width_px, height_px), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            fact_x = width_px / ancho_m
            fact_y = height_px / alto_m

            for x1, y1, x2, y2 in lineas:
                px1 = (x1 - min_x) * fact_x
                py1 = height_px - (y1 - min_y) * fact_y
                px2 = (x2 - min_x) * fact_x
                py2 = height_px - (y2 - min_y) * fact_y
                # Subimos el grosor a 2 para que resalte más al tener más resolución
                draw.line([(px1, py1), (px2, py2)], fill=(120, 120, 120, 150), width=2)

            self.img_original = img
            self.img_centro_x = (min_x + max_x) / 2.0
            self.img_centro_y = (min_y + max_y) / 2.0
            self.img_ancho_real = ancho_m

            self.delete("cargando")
            print("✅ Topografía recortada y cargada al instante.")

            # 👇 LA CORRECCIÓN DE ORO: Reconstruimos la malla y enfocamos la cámara
            if hasattr(self, 'coordenadas') and self.coordenadas:
                self.enfocar_malla()
            else:
                self.renderizar()

        except Exception as e:
            self.delete("cargando")
            self.create_text(centro_pantalla_x, centro_pantalla_y, 
                             text=f"🚨 Error fatal:\n{e}", fill="red", font=("Arial", 12))

    def cargar_dxf_como_fondo(self, rutas_dxf,color):
        """Lee uno o MÚLTIPLES archivos DXF y los fusiona visualmente."""
        #self.centro_x = centro_x
        #self.centro_y = centro_y
        # 1. INICIALIZACIÓN SEGURA: Garantiza que la memoria exista sin borrarla
        if getattr(self, 'topo_vectores', None) is None:
            self.topo_vectores = []
        if getattr(self, 'items_topo', None) is None:
            self.items_topo = []

        #self.delete("all")
        self.update_idletasks()
        w, h = max(self.winfo_width(), 800), max(self.winfo_height(), 600)
        
        self.create_text(w/2, h/2, text="⏳ Fusionando Cresta, Toe y Topografía...",
                         fill="gray", font=("Arial", 14, "bold"), tags="cargando")
        self.update() 

        try:
            radio_maximo = 1000.0
            limite_izq, limite_der = self.centro_x - radio_maximo, self.centro_x + radio_maximo
            limite_abj, limite_arr = self.centro_y - radio_maximo, self.centro_y + radio_maximo

            def punto_en_radio(x, y):
                return (limite_izq <= x <= limite_der) and (limite_abj <= y <= limite_arr)

            # Si por algún error enviaron un texto normal (1 archivo), lo volvemos lista
            nuevos_vectores = []
            if isinstance(rutas_dxf, str):
                rutas_dxf = [rutas_dxf]

            # 👇 EL BUCLE MAESTRO: Lee el Toe, extrae líneas, luego lee la Cresta, extrae líneas...
            for ruta in rutas_dxf:
                doc = ezdxf.readfile(ruta)
                msp = doc.modelspace()

                for entity in msp.query('LINE LWPOLYLINE POLYLINE SPLINE 3DFACE'):
                    puntos_temp = []

                    if entity.dxftype() == 'LINE':
                        puntos_temp = [(entity.dxf.start.x, entity.dxf.start.y), (entity.dxf.end.x, entity.dxf.end.y)]
                    elif entity.dxftype() == 'LWPOLYLINE':
                        puntos_temp = [(p[0], p[1]) for p in entity.get_points('xy')]
                    elif entity.dxftype() == 'POLYLINE':
                        puntos_temp = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                    elif entity.dxftype() == '3DFACE':
                        puntos_temp = [(entity.dxf.vtx0.x, entity.dxf.vtx0.y), (entity.dxf.vtx1.x, entity.dxf.vtx1.y),
                                       (entity.dxf.vtx2.x, entity.dxf.vtx2.y), (entity.dxf.vtx3.x, entity.dxf.vtx3.y)]
                        puntos_temp.append(puntos_temp[0])

                    if len(puntos_temp) >= 2:
                        # Revisar si AL MENOS un punto de toda la línea está en el radio
                        adentro = False
                        for x, y in puntos_temp:
                            if punto_en_radio(x, y):
                                adentro = True
                                break
                        
                        if adentro:
                            # 👇 LA MAGIA: Guardamos todos los puntos en una sola lista plana
                            coords_planas = []
                            for x, y in puntos_temp:
                                coords_planas.extend([x - self.centro_x, y - self.centro_y])
                            
                            #self.topo_vectores.append((coords_planas, color))
                            nuevos_vectores.append((coords_planas, color))

            # --- Crear todas las líneas recolectadas en el lienzo ---
            self.delete("cargando")

            self.topo_vectores.extend(nuevos_vectores)
            
            # 4. SUMAR A LA PANTALLA (Añadimos sin tocar las capas anteriores)
            for coords_planas, col in nuevos_vectores:
                coords_falsas = [0] * len(coords_planas)
                item = self.create_line(*coords_falsas, fill=col, width=1, tags="topo")
                # 👇 ESTO ES VITAL: Añadimos el nuevo objeto a la lista sin reiniciarla
                self.items_topo.append(item)
                
            self.tag_lower("topo")

           # 5. RENDERIZAR
            if hasattr(self, 'coordenadas') and self.coordenadas:
                self.enfocar_malla()
            else:
                self.renderizar()

            if hasattr(self, 'aplicar_filtro_radio'):
                self.aplicar_filtro_radio(1000)

        except Exception as e:
            self.delete("cargando")
            self.create_text(w/2, h/2, text=f"🚨 Error al leer archivos:\n{e}", fill="red", font=("Arial", 12))

    def aplicar_filtro_radio(self, nuevo_radio):
        """Oculta o muestra las líneas topográficas continuas según el radio del slider."""
        if not hasattr(self, 'topo_vectores') or not hasattr(self, 'items_topo'):
            return

        radio_sq = nuevo_radio ** 2

        for (coords_planas, color), item in zip(self.topo_vectores, self.items_topo):
            adentro = False
            
            # Revisamos rápido si algún vértice de la línea entra en el círculo
            for i in range(0, len(coords_planas), 2):
                x = coords_planas[i]
                y = coords_planas[i+1]
                if (x**2 + y**2) <= radio_sq:
                    adentro = True
                    break # Con que un pedacito toque el círculo, la mostramos entera
            
            if adentro:
                self.itemconfig(item, state="normal")
            else:
                self.itemconfig(item, state="hidden")

    def limpiar_topografia(self):
        """Borra la memoria de la topografía pero deja intactos los taladros y la brújula."""
        self.topo_vectores = []
        self.items_topo = []
        self.delete("topo")

    def _mezclar_color_con_fondo(self, color_original, opacidad_pct):
        """Simula transparencia aclarando el color hacia blanco brillante para no perder el tono original."""
        
        # 👇 EL CAMBIO CLAVE: Usamos Blanco Puro en lugar del gris del fondo
        bg_r, bg_g, bg_b = 255, 255, 255 
        
        # Si la opacidad es menor a 20%, la forzamos a 20% para que nunca desaparezca del todo
        opacidad = max(opacidad_pct, 20) / 100.0

        #color_original = color_original.lower()
        
        # Identificamos los colores (agregué también sus versiones Hexadecimales por si acaso)
        if color_original == "red" or color_original == "#F23800":
            fg_r, fg_g, fg_b = 242, 56, 0     # Rojo intenso puro
        elif color_original == "blue" or color_original == "#0005F2":
            fg_r, fg_g, fg_b = 0, 5, 242    # Azul puro
        elif color_original == "#686868":
            fg_r, fg_g, fg_b = 104, 104, 104 # Gris de topografía normal
        else:
            fg_r, fg_g, fg_b = 100, 100, 100 

        # Matemática de Blending Luminoso
        r = int((fg_r * opacidad) + (bg_r * (1 - opacidad)))
        g = int((fg_g * opacidad) + (bg_g * (1 - opacidad)))
        b = int((fg_b * opacidad) + (bg_b * (1 - opacidad)))

        # Asegurarnos de que no pase de 255
        r, g, b = min(r, 255), min(g, 255), min(b, 255)

        return f"#{r:02x}{g:02x}{b:02x}"

    def actualizar_apariencia_topo(self, opacidad_pct, modo_punteado):
        """Actualiza el color (transparencia) y el patrón (dash) de todas las líneas topográficas."""
        if not hasattr(self, 'topo_vectores') or not hasattr(self, 'items_topo'):
            return

        # Si modo_punteado es True, aplicamos dash=(2, 4) (2 pintados, 4 vacíos). Si no, dash=() que es línea sólida.
        patron_dash = (2, 4) if modo_punteado else ()

        # Recorremos todas las líneas y las actualizamos al instante
        for (coords_planas, color_original), item in zip(self.topo_vectores, self.items_topo):
            
            # Calculamos el color simulado si hay opacidad
            nuevo_color = color_original
            if opacidad_pct < 100:
                nuevo_color = self._mezclar_color_con_fondo(color_original, opacidad_pct)

            # itemconfig actualiza propiedades visuales al instante sin cambiar las coordenadas matemáticas
            self.itemconfig(item, fill=nuevo_color, dash=patron_dash)

    def actualizar_config_labels(self, mostrar, size, off_x, off_y):
        self.mostrar_labels = mostrar
        self.label_size = size
        self.label_offset_x = off_x
        self.label_offset_y = off_y

        # 🟢 Determinamos el estado físico
        estado = "normal" if mostrar else "hidden"
        
        if hasattr(self, 'items_labels'):
            for item in self.items_labels:
                # Aplicamos el estado a cada etiqueta
                self.itemconfig(item, state=estado)
        
        # Reset para que renderizar recalcule la fuente
        self.current_font_size = 0 
        self.renderizar()

    def cargar_conexiones(self, lista_conexiones, diccionario_tiempos):
        """Recibe los datos listos para graficar (sin hacer cálculos lógicos)."""
        self.datos_conexiones_crudas = lista_conexiones
        # Guardamos el diccionario que ya calculó diseno.py y secuencia.py
        self.tiempos_acumulados = diccionario_tiempos 
                
        # Procedemos directo a dibujar
        if hasattr(self, 'centro_x'):
            self._construir_conexiones()
            self._actualizar_textos_taladros()

    def _construir_conexiones(self):
        """Crea los objetos de Tkinter para los cables."""
        self.delete("conexiones") 
        self.datos_conexiones_render = []

        if not hasattr(self, 'datos_conexiones_crudas') or not hasattr(self, 'taladros_norm'):
            return

        mapa_posiciones = {}
        for i, (id_tal, lbl, x_orig, y_orig) in enumerate(self.coordenadas):
            mapa_posiciones[str(id_tal)] = self.taladros_norm[i]

        modo_relief = getattr(self, 'mostrar_relief', False)

        for con in self.datos_conexiones_crudas:
            origen = str(con.get("origen"))
            destino = str(con.get("destino"))

            if origen in mapa_posiciones and destino in mapa_posiciones:
                x1, y1 = mapa_posiciones[origen]
                x2, y2 = mapa_posiciones[destino]
                color_cable = con.get("color", "#FF0000")

                # --- 🟢 LA CORRECCIÓN AQUÍ ---
                tiempo = float(con.get("tiempo", 0))
                relief = float(con.get("relief", 0)) # Obtenemos el relief calculado en diseno.py
                
                # Seleccionamos el texto inicial según el modo actual
                valor_txt = f"{relief:.1f}" if modo_relief else str(int(tiempo))
                color_fondo_caja = self._obtener_color_fondo_contraste(color_cable)

                item_linea = self.create_line(0, 0, 0, 0, fill=color_cable, width=2, 
                                              arrow=tk.LAST, arrowshape=(10, 12, 4), tags="conexiones")
                item_fondo = self.create_rectangle(0, 0, 0, 0, fill=color_fondo_caja, outline="", tags="conexiones")
                item_texto = self.create_text(0, 0, text=valor_txt, fill=color_cable, 
                                              font=("Arial", 2), tags="conexiones")

                # Guardamos TODO en la memoria de renderizado
                self.datos_conexiones_render.append({
                    "x1": x1, "y1": y1,
                    "x2": x2, "y2": y2,
                    "linea": item_linea,
                    "fondo": item_fondo,
                    "texto": item_texto,
                    "tiempo": tiempo,     # 👈 Guardamos para uso futuro
                    "relief": relief,     # 👈 Guardamos para uso futuro
                    "len_txt": len(valor_txt)
                })
        
        self.renderizar()

    def actualizar_config_conexiones(self, size_flecha, size_tiempo, modo_relief=False):
        self.base_flecha_size = size_flecha
        self.base_tiempo_size = size_tiempo
        self.mostrar_relief = modo_relief 

        for con in self.datos_conexiones_render:
            # 🟢 Intercambio dinámico de etiquetas
            if self.mostrar_relief:
                nuevo_texto = f"{con['relief']:.1f}"
            else:
                nuevo_texto = str(int(con['tiempo']))
            
            # Actualizamos el texto visual y el registro de su longitud para el fondo CAD
            self.itemconfig(con["texto"], text=nuevo_texto)
            con["len_txt"] = len(nuevo_texto) 
            
        self.renderizar()

    def _obtener_color_fondo_contraste(self, hex_color):
        """Calcula el brillo de un color Hexadecimal y devuelve Blanco o Negro."""
        hex_color = str(hex_color).lstrip('#')
        
        # Si por alguna razón el color no es un Hex válido de 6 letras, devolvemos blanco
        if len(hex_color) != 6:
            return "white"
            
        try:
            # Convertimos Hexadecimal a RGB clásico (0-255)
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Fórmula de luminancia (cómo el ojo humano percibe el brillo)
            luminancia = (0.299 * r) + (0.587 * g) + (0.114 * b)
            
            # Si el brillo es mayor a 140 (claro como amarillo, cyan o blanco) -> Fondo Negro
            # Si es menor a 140 (oscuro como rojo, azul oscuro o verde oscuro) -> Fondo Blanco
            if luminancia > 140:
                return "black"
            else:
                return "white"
        except ValueError:
            return "white"

    def _calcular_tiempos_acumulados(self):
        """Calcula la secuencia de disparo usando los LABELS de los taladros."""
        import collections
        self.tiempos_acumulados = {}
        
        if not hasattr(self, 'datos_conexiones_crudas') or not self.datos_conexiones_crudas:
            return

        # 1. Construcción del Grafo usando los nombres visuales (Labels)
        grafo = collections.defaultdict(list)
        for con in self.datos_conexiones_crudas:
            # Usamos 'origen' y 'destino' que ahora contienen los labels de la query
            u = str(con["labelorigen"])
            v = str(con["labeldestino"])
            t = float(con["tiempo"])
            grafo[u].append((v, t))

        # 2. Definición de Inicios (Puntos de partida 0 ms)
        # Asegúrate que 'taladros_inicio' ahora contenga LABELS, no IDs
        queue = collections.deque()
        inicios = getattr(self, 'taladros_inicio', [])
        #print(inicios)
        
        for ini in inicios:
            ini_str = str(ini)
            self.tiempos_acumulados[ini_str] = 0.0
            queue.append(ini_str)

        # 3. Algoritmo de Propagación (Dijkstra/BFS para tiempos mínimos)
        while queue:
            actual = queue.popleft()
            tiempo_actual = self.tiempos_acumulados[actual]

            for vecino, retardo in grafo.get(actual, []):
                nuevo_tiempo = tiempo_actual + retardo
                
                # Si el vecino no tiene tiempo o llegamos más rápido por este cable
                if vecino not in self.tiempos_acumulados or nuevo_tiempo < self.tiempos_acumulados[vecino]:
                    self.tiempos_acumulados[vecino] = nuevo_tiempo
                    queue.append(vecino)
        
        #print(self.tiempos_acumulados)

    def actualizar_modo_textos(self, modo):
        """Cambia el modo (id / isocrona) y refresca la pantalla."""
        self.modo_texto_taladro = modo
        self._actualizar_textos_taladros()

    def _actualizar_textos_taladros(self):
        """Intercambia el contenido de los labels entre ID visual y Tiempos de Detonación."""
        if not hasattr(self, 'items_labels') or not hasattr(self, 'coordenadas'):
            return

        modo = getattr(self, 'modo_texto_taladro', 'id')
        tiempos = getattr(self, 'tiempos_acumulados', {})

        # Desempaquetamos los 4 valores obligatorios
        for i, (id_tal, lbl, x, y) in enumerate(self.coordenadas):
            if i < len(self.items_labels):
                
                # 1. Limpiamos el texto visual ("1.0" pasa a "1")
                try:
                    label_limpio = str(int(float(lbl)))
                except ValueError:
                    label_limpio = str(lbl)

                # 2. Selección de Modo
                if modo == 'isocrona':
                    # Buscamos el tiempo usando el ID inquebrantable de la BD
                    t = tiempos.get(str(id_tal))
                    
                    if t is not None:
                        # Si tiene tiempo calculado, lo mostramos en ms
                        texto = f"{int(t)} ms"
                    else:
                        # Si no tiene tiempo (ej. no está conectado a nada), ponemos un guion
                        texto = "-"
                else:
                    # Modo diseño: Volvemos a mostrar el Label normal
                    texto = label_limpio
                
                # 3. Aplicamos el cambio físico en la pantalla
                self.itemconfig(self.items_labels[i], text=texto)





