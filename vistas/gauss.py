import numpy as np
from scipy.stats import norm
import tkinter as tk

# Librerías para el histograma
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import tkinter as tk
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class VentanaGauss(tk.Toplevel):
    def __init__(self, maestro):
        super().__init__(maestro)
        self.title("Análisis Dinámico de Relief")
        self.geometry("950x850") 
        self.maestro = maestro

        # 1. PANEL DE CONTROL (Superior)
        frame_controles = tk.Frame(self, pady=10)
        frame_controles.pack(side="top", fill="x")
        
        tk.Label(frame_controles, text="Umbral de Cuidados (ms/m):", font=("Arial", 11, "bold")).pack(side="left", padx=10)
        self.var_umbral = tk.DoubleVar(value=9.0)
        self.entry_umbral = tk.Entry(frame_controles, textvariable=self.var_umbral, width=8, font=("Arial", 11))
        self.entry_umbral.pack(side="left", padx=5)

        tk.Button(frame_controles, text="Actualizar Análisis", command=self.actualizar, 
                  bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), padx=10).pack(side="left", padx=10)

        # --- 🟢 2. PANEL DE LEYENDA GENERAL (Inferior con Prioridad) ---
        # Empacamos esto al fondo (side="bottom") ANTES que el canvas para que no se oculte
        self.frame_leyenda = tk.LabelFrame(self, text=" Glosario de Análisis Técnico ", 
                                           padx=20, pady=15, fg="#2c3e50", font=("Arial", 12, "bold"))
        self.frame_leyenda.pack(side="bottom", fill="x", padx=20, pady=20)

        texto_glosario = (
            "• CURVA DE GAUSS: Representa la 'firma' del diseño. Una campana alta y estrecha indica una voladura altamente uniforme y controlada.\n\n"
            "• MEDIA (µ): Es el valor de relief promedio real. Si se aleja de su target, el amarre no está cumpliendo la secuencia diseñada.\n\n"
            "• DESVIACIÓN (σ): Mide el 'ruido' o inconsistencia. \n"
            "  - σ < 1.0: Diseño de alta precisión. | σ > 2.5: Diseño errático con alto riesgo de fragmentación irregular y vibraciones."
        )
        
        # Usamos font size 11 y wraplength dinámico
        self.lbl_glosario = tk.Label(self.frame_leyenda, text=texto_glosario, justify="left", 
                                     font=("Arial", 11), fg="#34495e", wraplength=850)
        self.lbl_glosario.pack(fill="x", anchor="w")
        
        # Ajuste automático del texto al cambiar el ancho de la ventana
        self.bind("<Configure>", self._ajustar_texto_leyenda)

        # 3. GRÁFICAS (Centro) - Se expande en el espacio restante
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 7))
        self.fig.subplots_adjust(hspace=0.5, top=0.92, bottom=0.12)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        
        self.actualizar()
        
    def _ajustar_texto_leyenda(self, event):
        """Evita que el texto se oculte al achicar el ancho de la ventana."""
        # Calculamos el nuevo ancho disponible restando los márgenes
        nuevo_ancho = self.winfo_width() - 80
        if nuevo_ancho > 100:
            self.lbl_glosario.config(wraplength=nuevo_ancho)

    def actualizar(self):
        """Filtra los datos según el umbral ingresado y dibuja las campanas."""
        try:
            umbral = self.var_umbral.get()
        except:
            umbral = 9.0

        # Recuperamos los datos crudos del maestro (diseno.py)
        datos_crudos = self.maestro.datos_graficar_actuales
        
        # SEPARACIÓN DINÁMICA POR UMBRAL
        reliefs_produccion = [d['relief'] for d in datos_crudos if d['relief'] < umbral]
        reliefs_cuidados = [d['relief'] for d in datos_crudos if d['relief'] >= umbral]

        # Dibujar Producción
        self.dibujar_campana(self.ax1, reliefs_produccion, f"Relief de Producción (< {umbral} ms/m)", "#3498db")
        
        # Dibujar Cuidados
        self.dibujar_campana(self.ax2, reliefs_cuidados, f"Alivios por Cuidados (>= {umbral} ms/m)", "#E67E22")
        
        self.canvas.draw()

    def dibujar_campana(self, ax, datos, titulo, color):
        ax.clear()
        if not datos or len(datos) < 2:
            ax.text(0.5, 0.5, f"No hay datos para\n{titulo}", 
                    ha='center', va='center', color='gray', fontsize=11)
            ax.set_title(titulo)
            return

        mu, sigma = np.mean(datos), np.std(datos)
        x = np.linspace(min(datos) - 5, max(datos) + 5, 100)
        p = norm.pdf(x, mu, sigma)

        # Graficar histograma y campana
        ax.hist(datos, bins=15, density=True, alpha=0.3, color='gray')
        ax.plot(x, p, color=color, linewidth=2, label=f'Media (µ): {mu:.2f} ms/m')
        ax.fill_between(x, p, color=color, alpha=0.1, label=f'Desviación (σ): {sigma:.2f}')
        
        ax.set_title(titulo, fontsize=11, fontweight='bold')
        ax.set_xlabel("Relief (ms/m)")
        ax.set_ylabel("Densidad")
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, linestyle=':', alpha=0.4)