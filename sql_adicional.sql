-- 1. Tabla de VOD (Velocity of Detonation)
CREATE TABLE vod (
    id INT AUTO_INCREMENT PRIMARY KEY,
    -- DATOS GENERALES
    id_persona INT,
    fecha DATE,
    hora TIME,
    nro_voladura VARCHAR(50),
    id_explosivo INT,
    fase_banco_malla VARCHAR(100),
    taladro VARCHAR(50),

    ruta_csv VARCHAR(255) DEFAULT NULL,

    -- DATOS DE DISEÑO
    altura_banco DECIMAL(10,2),
    prof_taladro DECIMAL(10,2),
    diametro VARCHAR(50),
    booster VARCHAR(50),
    altura_carga DECIMAL(10,2),
    tipo_taco VARCHAR(50),
    humedad VARCHAR(50),

    -- DATOS DE EXPLOSIVO
    id_explosivo INT,
    densidad DECIMAL(10,2),
    id_camion INT,
    peso_exp DECIMAL(10,2),
    iniciacion VARCHAR(50),

    -- DATOS DE GRAFICO
    limite_vod DECIMAL(10,2),
    inicio_probecable DECIMAL(10,2),
    altura_booster DECIMAL(10,2),
    continuidad_handy VARCHAR(5), -- SI/NO
    suavizado_ventana INT,
    paso_ticks_prof DECIMAL(10,2),
    vod_min_global INT,
    vod_max_global INT,
    long_cable_coaxial INT,

    -- AJUSTE DOMINIO
    t_inicial DECIMAL(10,3),
    t_final DECIMAL(10,3),
    vod_min_optima INT,
    vod_max_optima INT,

    -- METADATOS
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Sismografía (Vibraciones)
CREATE TABLE IF NOT EXISTS sismografia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_voladura INT,
    pvs DECIMAL(10,2),
    pvx DECIMAL(10,2),
    pvy DECIMAL(10,2),
    pvz DECIMAL(10,2),
    fmax DECIMAL(10,2),
    fx DECIMAL(10,2),
    fy DECIMAL(10,2),
    fz DECIMAL(10,2),
    duracion_total DECIMAL(10,2),
    id_punto_monitoreo VARCHAR(100),
    distancia DECIMAL(10,2),
    carga_operante DECIMAL(10,2), -- 👈 ¡Aquí faltaba esta coma!
    vpp_diseno DECIMAL(10,2),
    k DECIMAL(10,2),
    alpha DECIMAL(10,2),
    ruta VARCHAR(255), -- 💡 TIP: Te subí esto a 255 (o usa TEXT) porque las rutas de Mac/Windows pueden ser muy largas
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla de Densidades
CREATE TABLE IF NOT EXISTS densidades_anfo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_voladura INT,
    id_camion INT,
    taladro VARCHAR(100),
    altura VARCHAR(100),
    peso VARCHAR(100),
    densidad_real DECIMAL(10,2),
    comentarios TEXT
);

-- 3. Tabla de Densidades
CREATE TABLE IF NOT EXISTS densidades_rioflex (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_voladura INT,
    id_camion INT,
    peso_bruto DECIMAL(10,2),
    peso_vaso DECIMAL(10,2),
    hora_muestra VARCHAR(100),
    temperatura DECIMAL(10,2),
    ph DECIMAL(10,2),
    taladro VARCHAR(100),
    densidad DECIMAL(10,2),
    comentarios TEXT
);

-- 4. Tabla de Fragmentación
CREATE TABLE IF NOT EXISTS fragmentacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_voladura INT,
    d50 DECIMAL(10,2),
    d80 DECIMAL(10,2),
    finos_porcentaje DECIMAL(10,2),
    optimos_porcentaje DECIMAL(10,2),
    oversize_porcentaje DECIMAL(10,2),
    zona VARCHAR(100),
    coor_x DECIMAL(10,2),
    coor_y DECIMAL(10,2),
    coor_z DECIMAL(10,2),
    ruta_foto VARCHAR(100),
    metodo_analisis VARCHAR(100) -- Ej. "Explorer 24/7" o "Photogrammetry"
);

-- 5. Tabla de Medición de Taladros
CREATE TABLE IF NOT EXISTS medicion_taladros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_voladura INT,
    taladro_nro VARCHAR(20),
    profundidad_diseno DECIMAL(10,2),
    profundidad_real DECIMAL(10,2),
    pasadura DECIMAL(10,2),
    agua_presencia BOOLEAN DEFAULT FALSE,
    nivel_agua DECIMAL(10,2)
);

-- 6. Tabla de Horario de Voladura
CREATE TABLE IF NOT EXISTS horario_voladura (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_voladura INT,
    hora_programada TIME,
    hora_ejecutada TIME,
    encargado VARCHAR(100),
    estado VARCHAR(50) DEFAULT 'Pendiente'
);

-- 7. Tabla de Targets (Objetivos/KPIs)
CREATE TABLE IF NOT EXISTS target (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mes_año DATE, -- Para control mensual
    indicador VARCHAR(100), -- Ej. "Cumplimiento de Profundidad"
    valor_objetivo DECIMAL(10,2),
    unidad VARCHAR(20) -- Ej. "%", "m/s", "mm/s"
);

-- Tabla para gestionar el personal (Ariel Guzman, Marco Vargas, etc.)
CREATE TABLE IF NOT EXISTS persona (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    cargo VARCHAR(100), -- Ej. "Quality Control", "Supervisor", "Ingeniero de Minas"
    dni_ce VARCHAR(20) UNIQUE, -- Documento de identidad para evitar duplicados
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Opcional: Insertar algunos de tus colaboradores actuales para probar
INSERT INTO persona (nombres, apellidos, cargo) VALUES 
('Ariel', 'Guzman', 'Quality Control'),
('Marco', 'Vargas', 'Design and Planning'),
('Leonardo', 'Dorado', 'Quality Control'),
('Luis', 'Peredo', 'Design and Planning'),
('Diego', 'Limacgi', 'Design and Planning');


-- Tabla de Camiones Fábrica
CREATE TABLE IF NOT EXISTS camion_fabrica (
    id INT AUTO_INCREMENT PRIMARY KEY,
    modelo VARCHAR(50) NOT NULL
);

-- Tabla de Condiciones de Taladro (Humedad)
CREATE TABLE IF NOT EXISTS condicion_taladro (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estado VARCHAR(50) NOT NULL
);

-- Tabla de Configuración General (Una sola fila para los datos de la empresa)
CREATE TABLE IF NOT EXISTS configuracion_sistema_qaqc (
    id INT PRIMARY KEY,
    empresa VARCHAR(150),
    ruc VARCHAR(20),
    vod_min_global INT,
    vod_max_global INT,
    vod_min_optima INT,
    vod_max_optima INT,
    ventana_suavizado INT
);

-- Insertar Camiones
INSERT INTO cat_camion_fabrica (modelo) VALUES ('Volvo 244'), ('Volvo 119'), ('Volvo 2210'), ('Volvo 3732');

-- Insertar Configuración por Defecto
INSERT INTO configuracion_sistema_qaqc (id, empresa, ruc, vod_min_global, vod_max_global, vod_min_optima, vod_max_optima, ventana_suavizado)
VALUES (1, 'DELION TECHNOLOGY S.A.C.', '20605586440', 3000, 6000, 4000, 6500, 99);

-- Insertar Condiciones de Humedad
INSERT INTO cat_condicion_taladro (estado) VALUES ('Seco'), ('Con Agua'), ('Agua Dinámica'), ('Tapado');

-- Cambia "proyecto" por el nombre exacto de tu tabla si es diferente (ej. voladura, mallas)
ALTER TABLE proyecto 
    -- Datos de ubicación minera
    ADD COLUMN fase VARCHAR(50),
    ADD COLUMN nivel VARCHAR(50),
    ADD COLUMN mallas VARCHAR(100),
    -- Checklists de QA/QC (0 = Pendiente, 1 = Completado)
    ADD COLUMN frag TINYINT(1) DEFAULT 0,
    ADD COLUMN vibra TINYINT(1) DEFAULT 0,
    ADD COLUMN vod TINYINT(1) DEFAULT 0,
    ADD COLUMN densidad TINYINT(1) DEFAULT 0,
    ADD COLUMN med_tal TINYINT(1) DEFAULT 0,
    ADD COLUMN horario TINYINT(1) DEFAULT 0;
    ADD COLUMN rutas_mallas TEXT DEFAULT NULL;

CREATE TABLE densidad_voladura (
  id INT(11) NOT NULL AUTO_INCREMENT,
  id_voladura INT(11) NOT NULL,
  id_explosivo INT(11) NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  hora_inicio VARCHAR(100) DEFAULT NULL,
  hora_fin VARCHAR(100) DEFAULT NULL,
  diametro VARCHAR(50) DEFAULT NULL,
  id_persona INT(11) DEFAULT NULL,
  columna_de_agua DECIMAL(10,2),
    densidad_teorica DECIMAL(10,2),
    densidad_final DECIMAL(10,2),
  fecha VARCHAR(100) DEFAULT NULL,
  tipo_taco VARCHAR(100),
  taco VARCHAR(100)
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


CREATE TABLE kpis (
    id_kpi INT AUTO_INCREMENT PRIMARY KEY,
    id_explosivo INT NOT NULL,
    vod_minimo DECIMAL(10,2) NOT NULL,
    vod_maximo DECIMAL(10,2) NOT NULL,
    densidad_minima DECIMAL(10,2) NOT NULL,
    densidad_maxima DECIMAL(10,2) NOT NULL,
    
    -- Creamos la relación lógica con la tabla de explosivos
    -- (Asegúrate de que tu tabla de explosivos se llame "explosivo" y su ID "idexplosivo")
    CONSTRAINT fk_kpi_explosivo 
        FOREIGN KEY (id_explosivo) 
        REFERENCES explosivo(idexplosivo) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);



