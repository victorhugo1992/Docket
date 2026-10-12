import tkinter as tk
from tkinter import ttk, messagebox
from database.voladuras_db import obtener_voladuras_por_rango, eliminar_voladura
from vistas.qaqc import qaqc
import os
from tkinter import filedialog
from database.datos_db import actualizar_fase_nivel_mallas
#from vistas.diseno import VistaDiseno

class VistaVoladuras(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.setup_ui()

    def setup_ui(self):
        # --- Título y Botones Superiores ---
        frame_top = tk.Frame(self,bg="#f5f6fa")
        frame_top.pack(fill="x", pady=10)

        self.configure(style="TFrame") # Vincula al estilo unificado #f5f6fa

        # Si usas marcos de Tkinter nativo (tk.Frame) dentro de esta pestaña:
        #marco_izquierdo = tk.Frame(self, bg="#f5f6fa")
        #marco_derecho = tk.Frame(self, bg="#f5f6fa")
        
        tk.Label(frame_top, text="Gestión de Voladuras", font=("Arial", 14, "bold")).pack(side="left", padx=10)
        
        btn_refrescar = tk.Button(frame_top, text="🔄 Refrescar", command=self.cargar_datos)
        btn_refrescar.pack(side="right", padx=5)

        # 1. Crear un objeto de estilo
        style = ttk.Style()
                        
        # --- Tabla (Treeview) ---
        columnas = ("id", "proyecto", "fecha", "fase", "nivel","mallas","frag","vibra","vod","densidad","med_tal","horario","acciones")
        self.tabla = ttk.Treeview(self, columns=columnas, show="headings")

          # Configura esto justo debajo de donde creas self.tabla
        self.tabla.tag_configure('impar', background='#ffffff')  # Fila Blanca
        self.tabla.tag_configure('par', background='#e8edf3')    # Fila Azul/Grisáceo muy claro (como el de tu cabecera)
        self.tabla.tag_configure('seleccionado', background='#4a6984', foreground='white') # Color al hacer clic

        # 2. Elegir un tema que soporte bien las líneas (como 'clam' o 'default')
        # (Si ya usas otro tema, puedes omitir esta línea, pero 'clam' suele verse mejor)
        style.theme_use("clam")

        # 3. Configurar el estilo del Treeview para mostrar líneas
        # Esto añade bordes ligeros a las celdas
        style.configure("Treeview", 
                        background="white",
                        foreground="black",
                        rowheight=28,       # Altura de cada fila (ajusta a tu gusto)
                        fieldbackground="white",
                        bordercolor="#0a0a0a", # Color de la línea separadora (gris claro)
                        borderwidth=5)

        # 4. (Opcional pero recomendado) Mejorar la cabecera
        style.configure("Treeview.Heading", 
                        font=('Arial', 10, 'bold'),
                        background="#D6D6D6",
                        foreground="black",
                        relief="flat")
        
        # Definir encabezados
        self.tabla.heading("id", text="ID")
        self.tabla.heading("proyecto", text="Voladura")
        self.tabla.heading("fecha", text="Fecha")
        self.tabla.heading("fase", text="Fase")
        self.tabla.heading("nivel", text="Nivel")
        self.tabla.heading("mallas", text="Mallas")
        self.tabla.heading("frag", text="Fragm.")
        self.tabla.heading("vibra", text="Vibra.")
        self.tabla.heading("vod", text="VOD")
        self.tabla.heading("densidad", text="Densidad")
        self.tabla.heading("med_tal", text="Medicion_Tal")
        self.tabla.heading("horario", text="Horario")
        self.tabla.heading("acciones", text="⚙️")

        # Ajustar ancho de columnas
        self.tabla.column("id", width=30, anchor="center")
        self.tabla.column("proyecto", width=60)
        self.tabla.column("fecha", width=90)
        self.tabla.column("fase", width=50)
        self.tabla.column("nivel", width=50)
        self.tabla.column("mallas", width=100)
        self.tabla.column("frag", width=30)
        self.tabla.column("vibra", width=30)
        self.tabla.column("vod", width=30)
        self.tabla.column("densidad", width=40)
        self.tabla.column("med_tal", width=30)
        self.tabla.column("horario", width=30)
        self.tabla.column("acciones", width=30, anchor="center")
        
        self.tabla.pack(fill="both", expand=True, padx=10)

        # ==========================================
        # NUEVO: CREAR EL MENÚ CONTEXTUAL (CLIC DERECHO)
        # ==========================================
        self.tabla.heading("acciones", text="⚙️ Opciones")
        self.tabla.column("acciones", width=80, anchor="center")

        # ... (Justo donde empacas el menú contextual, agrega este evento) ...
        self.menu_opciones = tk.Menu(self.tabla, tearoff=0)
        self.menu_opciones.add_command(label="Ver Voladura", command=self.ver_voladura)
        self.menu_opciones.add_separator()
        self.menu_opciones.add_command(label="📋 Asignar mallas", command=self.accion_asignar_mallas)
        self.menu_opciones.add_command(label="✏️ Editar", command=self.accion_editar)
        self.menu_opciones.add_separator()
        self.menu_opciones.add_command(label="📤 Exportar Hanwha", command=self.accion_exportar_hanwha)

        # 👇 VINCULAMOS EL CLIC AL "FALSO BOTÓN"
        self.tabla.bind("<ButtonRelease-1>", self.clic_boton_opciones)

        # --- Botones de Acción Inferiores ---
        frame_btns = tk.Frame(self)
        frame_btns.pack(fill="x", pady=10)

        #tk.Button(frame_btns, text="Editar Seleccionado", bg="#ffc107", command=self.editar).pack(side="left", padx=10)
        #tk.Button(frame_btns, text="Eliminar", bg="#dc3545", fg="white", command=self.confirmar_eliminacion).pack(side="left")

        # Frame de acciones QA/QC
        frame_acciones = tk.Frame(self)
        frame_acciones.pack(fill="x", pady=10, padx=10)

        self.btn_qaqc = tk.Button(
            frame_acciones, 
            text="🛠️ Asignar Medición / QAQC", 
            command=self.abrir_panel_qaqc,
            bg="#0070C0", 
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10
        )
        self.btn_qaqc.pack(side="left")

        self.cargar_datos()


    def abrir_panel_qaqc(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione una voladura de la lista.")
            return

        # Extraer ID y nombre del proyecto de la tabla
        valores = self.tabla.item(seleccion)['values']
        id_vola = valores[0]
        proyecto = valores[1]

        # Instanciar el panel externo
        app_principal = self.master.master # Esto sube niveles hasta llegar a la clase principal

        qaqc(self, id_vola, proyecto,valores,callback_actualizar=app_principal.tab_home.aplicar_filtro_fechas)

    def cargar_datos(self,f_inicio=None, f_fin=None):
        # Limpiar tabla
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        
       # Si no vienen fechas, podrías cargar las de hoy o todas
        if f_inicio and f_fin:
            registros = obtener_voladuras_por_rango(f_inicio, f_fin)
        else:
            # Lógica por defecto (ejemplo: cargar todas o las del mes)
            from database.voladuras_db import listar_voladuras 
            registros = listar_voladuras()


        # Agregamos 'enumerate' para que nos dé un índice (0, 1, 2, 3...) en cada vuelta
        for index, r in enumerate(registros):
            
            # Lo convertimos a un Check
            check_vibra = "✔" if r['vibra'] == 1 else ""
            check_vod = "✔" if r['vod'] == 1 else ""
            check_densidad = "✔" if r['densidad'] == 1 else ""
            nueva_fecha = r['fecha_hora'].strftime("%d-%m-%Y  %I:%M %p").lower()
            
            # 👇 NUEVO: Decidimos si la fila es par o impar usando matemáticas (módulo)
            etiqueta = 'par' if index % 2 == 0 else 'impar'

            # Insertamos los datos y le pegamos la etiqueta al final
            self.tabla.insert("", "end", 
                              values=(
                                  r['idproyecto'], 
                                  r['nombre'], 
                                  nueva_fecha, 
                                  r['fase'], 
                                  r['nivel'], 
                                  r['mallas'], 
                                  r['frag'], 
                                  check_vibra, 
                                  check_vod,
                                  check_densidad,
                                  "",
                                  "",
                                  "[  ⋮  ]"
                                  ),
                              tags=(etiqueta,)) # <--- AGREGAMOS ESTO
        
       
        # Busca esta línea en tu configuración inicial de la tabla
        self.tabla.column("vibra", width=40, anchor="center")
        self.tabla.column("vod", width=40, anchor="center")
        self.tabla.column("densidad", width=40, anchor="center")
        self.tabla.column("fase", width=40, anchor="center")
        self.tabla.column("nivel", width=40, anchor="center")
        self.tabla.column("mallas", width=200, anchor="center")

    def confirmar_eliminacion(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Selecciona una voladura para eliminar.")
            return

        item = self.tabla.item(seleccion)
        id_v = item['values'][0]

        if messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar la voladura ID {id_v}?"):
            eliminar_voladura(id_v)
            self.cargar_datos()
            messagebox.showinfo("Éxito", "Registro eliminado.")

    def editar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Selecciona un registro para editar.")
            return
        # Aquí abrirías una ventana Toplevel con un formulario para UPDATE
        messagebox.showinfo("Editar", "Función de edición: Abrir formulario con datos.")

    def clic_boton_opciones(self, event):
        """Detecta si se presionó el 'falso botón' y despliega el menú pegado a él."""
        # 1. Verificar que el clic fue dentro de una celda de datos
        region = self.tabla.identify_region(event.x, event.y)
        if region != "cell":
            return

        # 2. Obtener qué fila y qué columna se clickearon
        item_id = self.tabla.identify_row(event.y)
        columna_id = self.tabla.identify_column(event.x)

        # 3. Si es la columna de acciones (la #13 en tu lista)
        if item_id and columna_id == '#13':
            # Seleccionar la fila visualmente
            self.tabla.selection_set(item_id)
            
            # MAGIA: Obtener las coordenadas exactas de la celda ("el botón")
            bbox = self.tabla.bbox(item_id, column=columna_id)
            if bbox:
                # bbox devuelve (x, y, ancho, alto) relativos a la tabla
                # Convertimos a coordenadas de toda la pantalla para que el menú salga justo DEBAJO del botón
                x_pantalla = self.tabla.winfo_rootx() + bbox[0]
                y_pantalla = self.tabla.winfo_rooty() + bbox[1] + bbox[3] 
                
                # Desplegar el menú
                self.menu_opciones.post(x_pantalla, y_pantalla)

    def obtener_id_voladura_seleccionada(self):
        """Función auxiliar para obtener el ID de la fila seleccionada."""
        seleccion = self.tabla.selection()
        if not seleccion: return None

        id_interno = seleccion[0]
        paquete_fila = self.tabla.item(id_interno)
        valores_reales = paquete_fila["values"]

        # Asumiendo que el ID de la voladura está en la PRIMERA columna (índice 0)
        return valores_reales[0]

    def accion_asignar_mallas(self):
        id_vola = self.obtener_id_voladura_seleccionada()
        if not id_vola: return

        app_principal = self.winfo_toplevel()

        # 2. Si el Jefe aún no tiene la memoria creada, se la inventamos ahora mismo
        if not hasattr(app_principal, 'memoria_ruta_mallas'):
            app_principal.memoria_ruta_mallas = None

        # 3. Leemos la memoria del Jefe
        if app_principal.memoria_ruta_mallas:
            carpeta_madre = filedialog.askdirectory(
                title=f"Carpeta base para Voladura {id_vola}",
                initialdir=app_principal.memoria_ruta_mallas
            )
        else:
            carpeta_madre = filedialog.askdirectory(title=f"Carpeta base para Voladura {id_vola}")
        
        if not carpeta_madre: 
            return
        
        app_principal.memoria_ruta_mallas = carpeta_madre
        
        # 2. Leer qué subcarpetas existen ahí adentro
        try:
            # Lista solo los elementos que sean "directorios" (carpetas)
            subcarpetas = [nombre for nombre in os.listdir(carpeta_madre) if os.path.isdir(os.path.join(carpeta_madre, nombre))]
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la carpeta:\n{e}")
            return

        if not subcarpetas:
            messagebox.showwarning("Vacío", "No se encontraron carpetas dentro del directorio seleccionado.")
            return

        # 3. Crear una ventana flotante para la selección múltiple
        ventana_mallas = tk.Toplevel(self)
        ventana_mallas.title(f"Asignar Mallas a Voladura {id_vola}")
        ventana_mallas.geometry("400x450")
        ventana_mallas.grab_set() # Bloquea la ventana principal hasta que cierres esta

        tk.Label(ventana_mallas, text="Selecciona las mallas a asignar:", font=("Arial", 11, "bold"), pady=10).pack()
        tk.Label(ventana_mallas, text="(Usa Ctrl o Shift + Clic para seleccionar varias)", fg="gray", font=("Arial", 9)).pack()

        # Marco para la lista con su barra de desplazamiento
        frame_lista = tk.Frame(ventana_mallas)
        frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

        scroll = tk.Scrollbar(frame_lista)
        scroll.pack(side="right", fill="y")

        # selectmode=tk.EXTENDED permite selección con Ctrl y Shift (Estilo nativo de OS)
        lista_carpetas = tk.Listbox(frame_lista, selectmode=tk.EXTENDED, yscrollcommand=scroll.set, font=("Arial", 11))
        lista_carpetas.pack(side="left", fill="both", expand=True)
        scroll.config(command=lista_carpetas.yview)

        # Llenar la lista con las carpetas encontradas
        for carpeta in subcarpetas:
            lista_carpetas.insert(tk.END, carpeta)

        # 4. Función de Guardado (Se ejecuta al presionar Confirmar)
        def confirmar_seleccion():
            indices_seleccionados = lista_carpetas.curselection()
            if not indices_seleccionados:
                messagebox.showwarning("Atención", "Debes seleccionar al menos una malla.")
                return
            
            lista_solo_mallas = []
            # Extraemos los nombres y creamos las rutas completas
            carpetas_elegidas = [lista_carpetas.get(i) for i in indices_seleccionados]
            rutas_completas = [os.path.join(carpeta_madre, c) for c in carpetas_elegidas]

            # ====================================================
            # 🚀 AQUÍ VA TU LÓGICA PARA GUARDAR EN LA BASE DE DATOS
            # ====================================================
            #print(f"--- Mallas para Voladura ID: {id_vola} ---")
            for ruta in rutas_completas:
                # 1. Normalizamos la ruta para evitar problemas entre Mac y Windows
                ruta_limpia = os.path.normpath(ruta)
                # 2. Partimos la ruta en una lista, cortando por cada separador ("/" o "\")
                partes = ruta_limpia.split(os.sep)
                # 3. Extraemos de atrás hacia adelante usando índices negativos
                # -1 es el último, -2 es el penúltimo, -3 es el antepenúltimo
                malla = partes[-1]  # Ej: "Malla 12"
                lista_solo_mallas.append(malla)
                nivel = partes[-2]  # Ej: "4320"
                fase = partes[-3]   # Ej: "Fase 8"
                
                print(f"Ruta completa: {ruta}")
                print(f"👉 Detectado -> FASE: {fase} | NIVEL: {nivel} | MALLA: {malla}\n")
            
            # (Ejemplo: self.datos.guardar_rutas_mallas(id_vola, rutas_completas))
            mallas_unidas = ", ".join(lista_solo_mallas)
            exito = actualizar_fase_nivel_mallas(id_vola, fase, nivel, mallas_unidas)

            if exito:
                seleccion = self.tabla.selection()

                if seleccion:
                    item_id = seleccion[0] 
                    # Extraemos la fila actual
                    valores_actuales = list(self.tabla.item(item_id, "values"))
                    
                    # Inyectamos los nuevos datos (Asegúrate de que los índices 3, 4 y 5 correspondan a Fase, Nivel y Mallas en tus columnas)
                    valores_actuales[3] = fase
                    valores_actuales[4] = nivel
                    valores_actuales[5] = mallas_unidas
                    
                    # Guardamos la fila modificada
                    self.tabla.item(item_id, values=valores_actuales)

                messagebox.showinfo("Éxito", f"Se asignaron correctamente las mallas a la voladura {id_vola}.")
                ventana_mallas.destroy() 
                
                # 🔄 RECARGAMOS LA TABLA VISUAL PARA VER LOS CAMBIOS
                if hasattr(self, 'cargar_datos'):
                    self.cargar_datos()
            else:
                messagebox.showerror("Error", "Hubo un problema al guardar en la base de datos.")

                messagebox.showinfo("Éxito", f"Se asignaron {len(carpetas_elegidas)} carpetas de mallas a la voladura {id_vola}.")
                ventana_mallas.destroy()

        # Botón para confirmar
        tk.Button(ventana_mallas, text="✅ Confirmar Asignación", bg="#28a745", fg="white", font=("Arial", 11, "bold"), command=confirmar_seleccion).pack(pady=15)

    def accion_editar(self):
        id_vola = self.obtener_id_voladura_seleccionada()
        if not id_vola: return
        print(f"Abriendo modo edición para la voladura ID: {id_vola}")
        # Aquí pones tu lógica para editar

    def accion_exportar_hanwha(self):
        id_vola = self.obtener_id_voladura_seleccionada()
        if not id_vola: return
        print(f"Exportando formato Hanwha para la voladura ID: {id_vola}")
        import tkinter.messagebox as messagebox
        messagebox.showinfo("Exportar", f"Iniciando exportación Hanwha para Voladura {id_vola}...")
        # Aquí pones tu lógica de exportación

    def ver_voladura(self):
        id_vola = self.obtener_id_voladura_seleccionada()
        if not id_vola: return

        print(id_vola)
        app_principal = self.master.master # Esto sube niveles hasta llegar a la clase principal
        app_principal.tab_diseno.dibujar_malla(id_vola)
        app_principal.notebook.select(app_principal.tab_diseno)
