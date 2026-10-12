import tkinter as tk

class VentanaConfiguracionMalla(tk.Toplevel):
    def __init__(self, vista_diseno):
        super().__init__(vista_diseno)
        
        self.vista_diseno = vista_diseno
        self.motor = vista_diseno.lienzo_interactivo
        
        self.title("Ajustes de Diseño")
        self.geometry("300x600")
        
        # --- CONFIGURACIÓN LIMPIA ---
        self.resizable(False, True)
        
        # En Mac, a veces 'topmost' ayuda, pero el 'grab' debe estar APAGADO
        self.attributes('-topmost', True) 
        
        # Aseguramos que la ventana reciba clics después de aparecer
        self.after(100, self.focus_force)
        
        self.setup_ui()

    def setup_ui(self):
        contenedor = tk.Frame(self, padx=15, pady=15)
        contenedor.pack(fill="both", expand=True)

        tk.Label(contenedor, text="Etiquetas de Taladros", font=("Arial", 10, "bold")).pack(anchor="w")

        # 🟢 QUITAMOS el 'command', dejamos solo la 'variable'
        tk.Checkbutton(contenedor, text="Mostrar IDs/Labels", 
               variable=self.vista_diseno.var_mostrar_ids).pack(anchor="w")

        tk.Label(contenedor, text="Tamaño Texto:").pack(anchor="w", pady=(5,0))
        # 🟢 QUITAMOS el 'command', el trace en diseno.py se encargará de todo
        self.sld_txt = tk.Scale(contenedor, from_=0.5, to=10, resolution=0.5, orient="horizontal", 
                                variable=self.vista_diseno.var_label_size)
        self.sld_txt.pack(fill="x")

        tk.Frame(contenedor, height=2, bd=1, relief="sunken").pack(fill="x", pady=15)

        # --- SECCIÓN: CONEXIONES ---
        tk.Label(contenedor, text="Conexiones y Retardos", font=("Arial", 10, "bold")).pack(anchor="w")
        
        tk.Label(contenedor, text="Tamaño Flecha:").pack(anchor="w", pady=(5,0))
        tk.Scale(contenedor, from_=1, to=15, orient="horizontal", 
                 variable=self.vista_diseno.var_flecha_size, command=self.vista_diseno.al_cambiar_conexiones).pack(fill="x")

        tk.Label(contenedor, text="Tamaño Texto Tiempo:").pack(anchor="w", pady=(5,0))
        tk.Scale(contenedor, from_=1, to=15, resolution=0.5, orient="horizontal", 
                 variable=self.vista_diseno.var_tiempo_size, command=self.vista_diseno.al_cambiar_conexiones).pack(fill="x")

        tk.Checkbutton(contenedor, text="Mostrar Relief (ms/m)", 
                       variable=self.vista_diseno.var_mostrar_relief, 
                       command=self.vista_diseno.al_cambiar_conexiones).pack(anchor="w", pady=5)

        tk.Checkbutton(contenedor, text="Mostrar Isocronas (Tiempos)", 
                       variable=self.vista_diseno.var_modo_texto, 
                       command=self.vista_diseno.al_cambiar_modo_texto).pack(anchor="w")