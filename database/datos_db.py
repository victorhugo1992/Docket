from mysql.connector import Error
from .conexion import crear_conexion # Ajusta la importación según tu proyecto

def obtener_datos_mysql():
    db = crear_conexion()
    
    # Diccionario inicial. Lo que no viene de BD se puede dejar estático o vacío por ahora.
    base = {
        "persona": [],
        "camion_fabrica": [],
        "explosivo": [],
        "explosivo_nombre": [],
        "condicion_taladro": []
    }
    
    if not db:
        print("No hay conexión a MySQL.")
        return base

    # Usamos dictionary=True para poder acceder a las columnas por su nombre
    cursor = db.cursor(dictionary=True)
    
    try:
        # 1. Tabla: personas (Asumiendo que tienes columnas 'nombres' y 'apellidos')
        cursor.execute("SELECT id,CONCAT(nombres, ' ', apellidos) AS nombre_completo FROM persona")
        base["persona"] = {row["nombre_completo"]:row["id"] for row in cursor.fetchall()}
        
        # 2. Tabla: camiones_fabrica (Asumiendo que la columna se llama 'modelo' o 'nombre')
        # Si tu columna se llama diferente, cámbialo en el SELECT
        cursor.execute("SELECT id,modelo,funcion FROM camion_fabrica") 
        base["camion_fabrica"] = {
            row["modelo"]: {
                "id": row["id"], 
                "funcion": row["funcion"]
            } 
            for row in cursor.fetchall() if row["modelo"]
        }
        
        # 3. Tabla: explosivos (Asumiendo que la columna se llama 'nombre')
        cursor.execute("SELECT idexplosivo,nombre, densidad, vod FROM explosivo")
        resultados_exp = cursor.fetchall()

        # 1. Guardamos solo los nombres para el menú desplegable
        base["explosivo_nombre"] = [row["nombre"] for row in resultados_exp]

        base["explosivo"] = {
            row["nombre"]: {"idexplosivo":row["idexplosivo"], "densidad": row["densidad"], "vod": row.get("vod", "")}
            for row in resultados_exp
        }
        #base["explosivo"] = [row["nombre"] for row in cursor.fetchall()]
        
        # 4. Tabla: condiciones_taladro (Asumiendo que la columna se llama 'estado' o 'condicion')
        cursor.execute("SELECT estado FROM condicion_taladro") 
        base["condicion_taladro"] = [row["estado"] for row in cursor.fetchall()]
        
        return base
        
    except Exception as e:
        print(f"Error consultando MySQL: {e}")
        return base
    finally:
        db.close()

# ----------------- TALADROS -----------------------------------
def obtener_taladros(id_proyecto):
    db = None
    cursor = None
    try:
        db = crear_conexion()
        cursor = db.cursor(dictionary=True) 
        
        query = "SELECT * FROM taladro WHERE proyecto_idproyecto = %s AND is_delete=0 ORDER BY label ASC"
        cursor.execute(query, (id_proyecto,))
        
        taladros_crudos = cursor.fetchall()
        
        # --- LA MAGIA DEL DICCIONARIO ---
        # Convertimos la lista de resultados en un diccionario.
        # Usamos row['label'] como la llave principal.
        diccionario_taladros = {row['label']: row for row in taladros_crudos if row.get('label')}
        
        return diccionario_taladros

    except Exception as e:
        print(f"Error al obtener estructura de taladros: {e}")
        return {} # Devuelve un diccionario vacío en caso de error
    finally:
        if cursor: cursor.close()
        if db: db.close()

def obtener_taladros_por_proyecto(id_proyecto):
    """Extrae toda la data clave de los taladros en una sola consulta."""
    conexion_db = crear_conexion() 
    if not conexion_db: return []

    try:
        cursor = conexion_db.cursor()
        
        # Ajusta coorx_t y coory_t al nombre exacto de tus columnas
        sql = """
            SELECT 
                idtaladro,   
                label,       
                is_inicio,
                coorx_t,
                coory_t
            FROM taladro 
            WHERE proyecto_idproyecto = %s AND (is_delete = 0 OR is_delete IS NULL)
        """
        cursor.execute(sql, (id_proyecto,))
        registros = cursor.fetchall()
        
        taladros_limpios = []
        for fila in registros:
            taladros_limpios.append({
                "id_taladro": int(fila[0]) if fila[0] else 0,
                "label": str(fila[1]) if fila[1] else str(fila[0]),
                "is_inicio": bool(fila[2]),
                "x": float(fila[3]) if fila[3] else 0.0,
                "y": float(fila[4]) if fila[4] else 0.0
            })
            
        return taladros_limpios
    except Exception as e:
        print(f"Error al obtener taladros completos: {e}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion_db' in locals(): conexion_db.close()

def obtener_distribucion_taladros_gauss(fecha_inicio, fecha_fin):
        conexion_db = crear_conexion() 
        cursor = conexion_db.cursor()
        lista_conteos = []
        
        # SQL robusto: Aseguramos filtrar nulos desde la base de datos
        sql = """
            SELECT COUNT(t.idtaladro) as total_taladros
            FROM taladro t
            INNER JOIN proyecto p ON t.proyecto_idproyecto = p.idproyecto
            WHERE (t.is_delete IS NULL OR t.is_delete = 0)
              AND p.fecha_hora BETWEEN %s AND %s
            GROUP BY t.proyecto_idproyecto
            HAVING total_taladros > 0;
        """
        
        try:
            print(f"🔍 Consultando taladros desde {fecha_inicio} hasta {fecha_fin}...")
            cursor.execute(sql, (fecha_inicio, fecha_fin))
            registros = cursor.fetchall()
            
            print(f"📊 Filas brutas devueltas por MySQL: {len(registros)}")
            
            # 🟢 PROCESAMIENTO SEGURO: Validamos que la clave exista y no sea None
            for r in registros:
                if r and r[0] is not None:
                    conteo = int(r[0])
                    if conteo > 0:
                        lista_conteos.append(conteo)
                        
            print(f"✅ Lista final de mallas procesadas para Gauss: {lista_conteos}")
            
        except Exception as e:
            print(f"❌ Error crítico de MySQL en obtener_distribucion_taladros_gauss: {e}")
            lista_conteos = []
        finally:
            cursor.close()
            
        return lista_conteos

# ---------------- VOD -----------------------------------------

def procesar_guardado_vod(datos_vod):
    """
    Implementa lógica de UPSERT: Si el nro_voladura existe, actualiza.
    Si no existe, inserta uno nuevo.
    """
    db= None
    cursor = None
    nro_vola = datos_vod.get("nro_voladura")
    
    try:
        db = crear_conexion()
        cursor = db.cursor()
        
        # 1. Verificar si ya existe un registro con ese nro_voladura
        check_query = "SELECT COUNT(*) FROM vod WHERE nro_voladura = %s"

        cursor.execute(check_query, (nro_vola,))
        existe = cursor.fetchone()[0] > 0

        print(existe)

        if existe:
            # 2. Lógica de UPDATE
            # Creamos el set dinámico: "columna1=%s, columna2=%s..."
            columnas = [f"{k} = %s" for k in datos_vod.keys() if k != "nro_voladura"]
            valores = [v for k, v in datos_vod.items() if k != "nro_voladura"]
            valores.append(nro_vola) # Para el WHERE al final

            query = f"UPDATE vod SET {', '.join(columnas)} WHERE nro_voladura = %s"
            cursor.execute(query, tuple(valores))
            accion = "actualizado"
        else:
            # 3. Lógica de INSERT (la que ya tenías)
            columnas = list(datos_vod.keys())
            valores = tuple(datos_vod.values())
            placeholders = ", ".join(["%s"] * len(valores))
            query = f"INSERT INTO vod ({', '.join(columnas)}) VALUES ({placeholders})"

            #print(query)

            cursor.execute(query, valores)
            accion = "insertado"

        db.commit()
        return True, accion

    except Error as e:
        print(f"Error en base de datos: {e}")
        db.rollback()
        return False, str(e)
    finally:
        if cursor: cursor.close()
        if db:db.close()

def eliminar_registro_vod(conexion, nro_voladura):
    """Elimina el registro asociado a una voladura específica."""
    cursor = None
    try:
        cursor = conexion.cursor()
        query = "DELETE FROM registro_vod WHERE nro_voladura = %s"
        cursor.execute(query, (nro_voladura,))
        conexion.commit()
        # Verificamos si realmente se borró algo
        return cursor.rowcount > 0
    except Error as e:
        print(f"Error al eliminar: {e}")
        conexion.rollback()
        return False
    finally:
        if cursor: cursor.close()

def obtener_registro_vod(id):
    db = None
    cursor = None
    try:
        db = crear_conexion()
        # El parámetro dictionary=True hace que MySQL nos devuelva 
        # {"altura_banco": 11, "id_persona": 1} en lugar de una tupla simple (11, 1)
        cursor = db.cursor(dictionary=True) 
        
        query = "SELECT * FROM vod WHERE id_voladura = %s"
        cursor.execute(query, (id,))
        
        registro = cursor.fetchone()
        return registro # Devolverá el diccionario o None si no existe

    except Exception as e:
        print(f"Error al obtener VOD: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if db: db.close()

def obtener_vods(fecha_ini,fecha_fin):
    db = None
    cursor = None
    try:
        db = crear_conexion()
        # El parámetro dictionary=True hace que MySQL nos devuelva 
        # {"altura_banco": 11, "id_persona": 1} en lugar de una tupla simple (11, 1)
        cursor = db.cursor(dictionary=True)
        
        query = "SELECT v.*, p.nombre, p.fecha_hora FROM vod v JOIN proyecto p ON v.id_voladura = p.idproyecto WHERE p.fecha_hora BETWEEN %s AND %s"
        cursor.execute(query, (fecha_ini,fecha_fin))
        
        registro = cursor.fetchall()
        return registro # Devolverá el diccionario o None si no existe

    except Exception as e:
        print(f"Error al obtener VOD: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if db: db.close()


# -------- VOLADURAS ---
def marcar_medicion_completada(id_vola, tipo_medicion="vod"):
    """
    Actualiza la tabla principal para encender el check de una medición.
    tipo_medicion puede ser 'vod', 'densidad', etc.
    """
    db = None
    cursor = None
    try:
        # Reemplaza crear_conexion() por como llames a tu función de conexión
        db = crear_conexion() 
        cursor = db.cursor()
        
        # Asumiendo que tu tabla principal se llama 'proyecto'
        # Esto armará: UPDATE proyecto SET estado_vod = 1 WHERE id = ...
        query = f"UPDATE proyecto SET {tipo_medicion} = 1 WHERE idproyecto = %s"
        
        cursor.execute(query, (id_vola,))
        db.commit()
        print(f"✅ Estado de {tipo_medicion} actualizado para la voladura {id_vola}")
        
    except Exception as e:
        print(f"🚨 Error al actualizar el estado en BD: {e}")
    finally:
        if cursor: cursor.close()
        if db: db.close()

def obtener_proyectos(fecha_ini,fecha_fin):
    db = None
    cursor = None
    try:
        db = crear_conexion()
        # El parámetro dictionary=True hace que MySQL nos devuelva 
        cursor = db.cursor(dictionary=True)
        
        query = "SELECT * FROM proyecto WHERE fecha_hora BETWEEN %s AND %s"
        cursor.execute(query, (fecha_ini,fecha_fin))
        registro = cursor.fetchall()
        return registro # Devolverá el diccionario o None si no existe

    except Exception as e:
        print(f"Error al obtener VOD: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if db: db.close()


# -------- DENSIDADES CAMIONES --------

def gestionar_densidad_voladura(id_vola, tipo_explosivo,id_explosivo,fecha, hora_inicio, hora_fin, 
                                diametro, id_persona,col_agua,den_teo,den_fin,long_carga,tipo_taco,taco,dia_carga):
    """Crea o actualiza la cabecera de forma independiente para ANFO o RIOFLEX."""
    conexion = crear_conexion()
    if not conexion: return None
    try:
        cursor = conexion.cursor(buffered=True)
        
        #print("DIA SELECCIONADO: ",dia_carga)
        # 👇 LA MAGIA AQUÍ: Buscamos si ya existe una cabecera para ESTA voladura y ESTE tipo específico
        cursor.execute("SELECT id FROM densidad_voladura WHERE id_voladura = %s AND tipo = %s AND dia_carga = %s", (id_vola, tipo_explosivo,dia_carga))
        resultado = cursor.fetchone()

        print(resultado)
        
        if resultado:
            id_maestro = resultado[0]
            # ACTUALIZAMOS solo los datos variables si ya existía ese tipo
            cursor.execute("""
                UPDATE densidad_voladura 
                SET fecha=%s, hora_inicio = %s, hora_fin = %s, diametro = %s, id_persona = %s, id_explosivo = %s, columna_de_agua=%s, densidad_teorica=%s, densidad_final=%s,longitud_carga=%s, tipo_taco=%s,taco=%s,dia_carga=%s WHERE id = %s
                """, (fecha,hora_inicio, hora_fin, diametro, id_persona, id_explosivo,col_agua, den_teo, den_fin,long_carga,tipo_taco,taco,dia_carga,id_maestro))
        else:
            # INSERTAMOS una nueva cabecera si es un tipo de explosivo nuevo en esta voladura
            cursor.execute("""
                INSERT INTO densidad_voladura (id_voladura, tipo,fecha, hora_inicio, hora_fin, diametro, id_persona, id_explosivo,columna_de_agua,densidad_teorica, densidad_final,longitud_carga,tipo_taco,taco,dia_carga) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s,%s,%s,%s)
            """, (id_vola, tipo_explosivo,fecha, hora_inicio, hora_fin, diametro, id_persona, id_explosivo, col_agua, den_teo, den_fin,long_carga,tipo_taco,taco,dia_carga))
            id_maestro = cursor.lastrowid
            
        conexion.commit()
        return id_maestro
    except Exception as e:
        print(f"🚨 Error en gestionar_densidad_voladura: {e}")
        conexion.rollback()
        return None
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()

def guardar_muestras_densidad(id_maestro, lista_muestras):
    """Guarda las muestras usando el id_camion_voladura explícito."""
    conexion = crear_conexion()
    if not conexion: return False

    try:
        cursor = conexion.cursor()

        # 1. Borramos las muestras anteriores de esta voladura
        cursor.execute("""
            DELETE FROM densidades_anfo 
            WHERE id_densidad_voladura = %s
        """, (id_maestro,))

        if not lista_muestras:
            conexion.commit()
            return True

        # 2. Insertamos con el ID exacto (%s en la primera posición)
        query_insert = """
                INSERT INTO densidades_anfo 
                (id_camion, taladro, altura, peso, densidad_real,id_densidad_voladura) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
        
        cursor.executemany(query_insert, lista_muestras)
        conexion.commit()
        return True

    except Exception as e:
        print(f"🚨 Error al guardar densidades_anfo: {e}")
        conexion.rollback()
        return False
    finally:
        cursor.close()
        conexion.close()

def obtener_mapa_camiones_voladura(id_vola):
    """Devuelve un diccionario {id_camion: id_camion_voladura}."""
    conexion = crear_conexion()
    if not conexion: return {}

    mapa = {}
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT id_camion, id FROM voladura_camion WHERE id_voladura = %s", (id_vola,))
        
        for row in cursor.fetchall():
            # Adaptación por si usas diccionarios o tuplas
            if isinstance(row, dict):
                mapa[row['id_camion']] = row['id']
            else:
                mapa[row[0]] = row[1]
        return mapa
    except Exception as e:
        print(f"🚨 Error al obtener mapa de camiones: {e}")
        return {}
    finally:
        cursor.close()
        conexion.close()

def obtener_densidades_guardadas(id_vola,dia_carga):
    """Trae las muestras ANFO usando la conexión con la tabla maestra."""
    conexion = crear_conexion()
    if not conexion: return []
    try:
        cursor = conexion.cursor(dictionary=True)
        # Traemos todo de ANFO (da.*) uniéndolo con el ID de la voladura
        query = """
            SELECT da.* FROM densidad_voladura dv
            JOIN densidades_anfo da ON dv.id = da.id_densidad_voladura
            WHERE dv.id_voladura = %s AND dv.dia_carga=%s
        """
        cursor.execute(query, (id_vola,dia_carga))
        return cursor.fetchall() or []
    except Exception as e:
        print(f"🚨 Error al leer ANFO: {e}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()

def obtener_densidades_rioflex_guardadas(id_vola,dia_carga):
    """Trae las muestras RIOFLEX usando la conexión con la tabla maestra."""
    conexion = crear_conexion()
    if not conexion: return []
    try:
        cursor = conexion.cursor(dictionary=True)
        # Traemos todo de RIOFLEX (dr.*) uniéndolo con el ID de la voladura
        query = """
            SELECT dr.* FROM densidad_voladura dv
            JOIN densidades_rioflex dr ON dv.id = dr.id_densidad_voladura
            WHERE dv.id_voladura = %s AND dv.dia_carga= %s
        """
        cursor.execute(query, (id_vola,dia_carga))
        return cursor.fetchall() or []
    except Exception as e:
        print(f"🚨 Error al leer RIOFLEX: {e}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()

def guardar_muestras_rioflex(id_maestro, lista_muestras):
    """Guarda las muestras en la tabla densidades_rioflex."""
    conexion = crear_conexion()
    if not conexion: return False

    try:
        cursor = conexion.cursor()

        # 1. Borramos las muestras anteriores de esta voladura
        cursor.execute("""
            DELETE FROM densidades_rioflex 
            WHERE id_densidad_voladura = %s
        """, (id_maestro,))

        if not lista_muestras:
            conexion.commit()
            return True

        # 2. Insertamos las nuevas
        query_insert = """
            INSERT INTO densidades_rioflex 
            (id_camion,
                peso_bruto, peso_vaso, hora_muestra, temperatura, ph, taladro, densidad,id_densidad_voladura) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(query_insert, lista_muestras)
        conexion.commit()
        return True

    except Exception as e:
        print(f"🚨 Error al guardar densidades_rioflex: {e}")
        conexion.rollback()
        return False
    finally:
        cursor.close()
        conexion.close()

def obtener_cabecera_densidad(id_vola, tipo_explosivo=None,dia_carga=None):
    """Trae los datos generales. Si se le pasa el tipo, trae ese específico."""
    conexion = crear_conexion()
    if not conexion: return None
    try:
        cursor = conexion.cursor(dictionary=True, buffered=True)
        
        # 👇 Si la pantalla pide un tipo específico, lo buscamos. Si no, traemos el último guardado.
        if tipo_explosivo:
            query = "SELECT * FROM densidad_voladura WHERE id_voladura = %s AND tipo = %s AND dia_carga=%s ORDER BY id DESC LIMIT 1"
            cursor.execute(query, (id_vola, tipo_explosivo,dia_carga))
        else:
            query = "SELECT * FROM densidad_voladura WHERE id_voladura = %s ORDER BY id DESC LIMIT 1"
            cursor.execute(query, (id_vola,))
            
        return cursor.fetchone() 
    except Exception as e:
        print(f"🚨 Error al leer cabecera_densidad: {e}")
        return None
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()

def actualizar_fase_nivel_mallas(id_vola, fase, nivel, mallas_concatenadas):
    """Actualiza la fase, nivel y las mallas concatenadas de una voladura."""
    conexion = crear_conexion()
    if not conexion: return False
    try:
        cursor = conexion.cursor()
        # ⚠️ IMPORTANTE: Ajusta 'voladura' al nombre real de tu tabla
        # y asegúrate de que las columnas 'fase', 'nivel' y 'mallas' se llamen así.
        query = """
            UPDATE proyecto 
            SET fase = %s, nivel = %s, mallas = %s
            WHERE idproyecto = %s
        """
        cursor.execute(query, (fase, nivel, mallas_concatenadas, id_vola))
        conexion.commit()
        
        return True
    except Exception as e:
        print(f"🚨 Error al actualizar mallas en BD: {e}")
        conexion.rollback()
        return False
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()

def obtener_cantidad_dias_carguio(id_proyecto,tipo_explosivo):
    db = None
    cursor = None
    try:
        db = crear_conexion() # O la forma en que instancies tu conexión
        cursor = db.cursor(dictionary=True) 
        
        # --- LA QUERY EXACTA ---
        # Filtramos por el proyecto Y por el tipo de explosivo
        query = """
            SELECT id, dia_carga,diametro,id_persona,fecha,hora_inicio,hora_fin,id_explosivo 
            FROM densidad_voladura 
            WHERE id_voladura = %s AND tipo = %s
            ORDER BY dia_carga ASC
        """
        cursor.execute(query, (id_proyecto, tipo_explosivo))
        
        dias_crudos = cursor.fetchall()
        
        # Devuelve una lista de diccionarios, ej: [{'id': 1, 'dia': 'DIA 1'}, {'id': 3, 'dia': 'DIA 2'}]
        return dias_crudos

    except Exception as e:
        print(f"Error al obtener los días de carguío para {tipo_explosivo}: {e}")
        return [] # Devuelve lista vacía en caso de error
    finally:
        if cursor: cursor.close()
        if db: db.close()

# --------------- SISMOGRAFIA ----------------------

def guardar_datos_sismografia(id_vola, pvs, pvx, pvy, pvz, fx, fy, fz, 
                                  distancia, carga, vpp_diseno, k, alpha, ruta,
                                  id_punto):
    """Guarda los datos operativos y los resultados del sismograma en la BD."""
    conexion = crear_conexion()
    if not conexion: return False
    
    try:
        cursor = conexion.cursor()
        
        # Verificamos si ya existe
        cursor.execute("SELECT id FROM sismografia WHERE id_voladura = %s", (id_vola,))
        resultado = cursor.fetchone()
        
        if resultado:
            # Si existe, ACTUALIZAMOS
            query = """
                UPDATE sismografia 
                SET pvs=%s, pvx=%s, pvy=%s, pvz=%s, 
                    fx=%s, fy=%s, fz=%s, 
                    distancia=%s, carga_operante=%s, vpp_diseno=%s, 
                    k=%s, alpha=%s, ruta=%s, id_punto_monitoreo=%s  
                WHERE id_voladura=%s
            """
            cursor.execute(query, (pvs, pvx, pvy, pvz, fx, fy, fz, 
                                    distancia, carga, vpp_diseno, k, alpha, ruta,id_punto, 
                                    id_vola))
        else:
            # Si no existe, INSERTAMOS
            query = """
                INSERT INTO sismografia 
                (id_voladura,pvs,pvx,pvy,pvz,fx,fy,fz,distancia,carga_operante,vpp_diseno, 
                k, alpha, ruta,id_punto_monitoreo) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
            """
            cursor.execute(query, (id_vola, pvs, pvx, pvy, pvz, fx, fy, fz, 
                                    distancia, carga, vpp_diseno, k, alpha, ruta,id_punto))
        
        # --- 2. ACTUALIZAR TABLA PROYECTOS (¡LO NUEVO!) ---
        query_proyecto = """
            UPDATE proyecto 
            SET vibra = 1 
            WHERE idproyecto = %s
        """
        cursor.execute(query_proyecto,(id_vola,))

        conexion.commit()
        return True
        
    except Exception as e:
        print(f"🚨 Error al guardar sismografía en BD: {e}")
        conexion.rollback()
        return False
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()

def obtener_datos_sismografia(id_vola):
    """Busca si hay datos de sismografía guardados para una voladura."""
    conexion = crear_conexion()
    if not conexion: return None
    
    try:
        cursor = conexion.cursor()
        # Traemos las columnas exactas que necesitamos rellenar en la interfaz
        query = """
            SELECT distancia, carga_operante, vpp_diseno, k, alpha, ruta,id_punto_monitoreo  
            FROM sismografia 
            WHERE id_voladura = %s
        """
        cursor.execute(query, (id_vola,))
        resultado = cursor.fetchone()
        
        # Devuelve una tupla: (distancia, carga, vpp, k, alpha, ruta) o None si no hay nada
        return resultado 
        
    except Exception as e:
        print(f"🚨 Error al consultar sismografía: {e}")
        return None
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()


# ---------------- PUNTOS DE MONITOREO ---------------
def obtener_puntos_monitoreo():
        """Trae todos los puntos de monitoreo disponibles."""
        conexion = crear_conexion()
        if not conexion: return []
        try:
            cursor = conexion.cursor()
            # Ajusta las columnas a las reales de tu tabla puntomonitoreoproyecto
            cursor.execute("SELECT proyecto_idproyecto, nombre, coorx, coory, coorz,ondap,k,alpha FROM puntomonitoreoproyecto")
            return cursor.fetchall() # Retorna lista de tuplas: (1, 'Punto A', 100.5, 200.5, 50.0)
        except Exception as e:
            print(f"Error al obtener puntos: {e}")
            return []
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conexion' in locals(): conexion.close()


# ---------------- TALADROS ----------------

def obtener_coordenadas_taladros(id_vola):
    """Trae las coordenadas X, Y, Z de todos los taladros de una voladura."""
    conexion = crear_conexion()
    if not conexion: return []
    try:
        cursor = conexion.cursor()
        # Ajusta 'taladro' y las columnas x,y,z a tu tabla real
        cursor.execute("SELECT label, coorx_t, coory_t, cota_cresta_t,profundidad_t,diametro,proyecto_idproyecto FROM taladro WHERE proyecto_idproyecto = %s", (id_vola,))
        return cursor.fetchall() # Retorna: [(10, 20, 30), (12, 22, 30), ...]
    except Exception as e:
        print(f"Error al obtener taladros: {e}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()


# ---------------- CONEXIONES Y RETARDOS ---------------
def obtener_conexiones_voladura(id_vola):
    """
    Busca los pares de taladros que comparten un id_conexion 
    y devuelve una lista de diccionarios con el origen, destino y color.
    """
    conexion = crear_conexion()
    if not conexion: return []

    try:
        cursor = conexion.cursor()

        sql = """
            SELECT 
        t1.label as labelorigen,
        dt1.id_taladro AS origen,
        t2.label as labeldestino,
        dt2.id_taladro AS destino,
        c.color,
        c.tiempo_taladro AS tiempo,
        t1.coorx_t AS origen_x,
        t1.coory_t AS origen_y,
        t2.coorx_t AS destino_x,
        t2.coory_t AS destino_y,
        -- 1. Cálculo de la Distancia
        SQRT(POW(t2.coorx_t - t1.coorx_t, 2) + POW(t2.coory_t - t1.coory_t, 2)) AS distancia,
        
        -- 2. Cálculo del Relief condicionado
        CASE 
            -- Si la distancia es mayor o igual a 10 metros, devuelve -1
            WHEN SQRT(POW(t2.coorx_t - t1.coorx_t, 2) + POW(t2.coory_t - t1.coory_t, 2)) >= 10 THEN -1
            -- Si la distancia es 0 (error de coordenadas iguales), evita dividir entre 0 y devuelve -1
            WHEN SQRT(POW(t2.coorx_t - t1.coorx_t, 2) + POW(t2.coory_t - t1.coory_t, 2)) = 0 THEN -1
            -- Si cumple (menor a 10 y mayor a 0), hace el cálculo: tiempo / distancia
            ELSE c.tiempo_taladro / SQRT(POW(t2.coorx_t - t1.coorx_t, 2) + POW(t2.coory_t - t1.coory_t, 2))
        END AS relief

        FROM conexion c
        INNER JOIN detonadortaladro dt1 ON c.id_conexion = dt1.id_conexion
        INNER JOIN detonadortaladro dt2 ON c.id_conexion = dt2.id_conexion 
            AND dt1.id_detonador_taladro < dt2.id_detonador_taladro
        INNER JOIN taladro t1 ON dt1.id_taladro = t1.idtaladro
        INNER JOIN taladro t2 ON dt2.id_taladro = t2.idtaladro
        WHERE t1.proyecto_idproyecto =  %s
        """
        cursor.execute(sql, (id_vola,))
        registros = cursor.fetchall()
        
        conexiones_limpias = []
        for fila in registros:
            # Índices de la consulta SQL:
            # 0: origen, 1: destino, 2: color, 3: tiempo, 
            # 4: origen_x, 5: origen_y, 6: destino_x, 7: destino_y
            
            # Transformamos el texto '255,255,255,255' a Hexadecimal (#FFFFFF)
            color_rgb = str(fila[4])
            try:
                partes_color = color_rgb.split(',')
                r, g, b = int(partes_color[0]), int(partes_color[1]), int(partes_color[2])
                color_hex = f"#{r:02x}{g:02x}{b:02x}"
            except Exception:
                color_hex = "#FF0000" # Rojo por defecto

            # Guardamos el paquete usando los índices numéricos de la Tupla
            conexiones_limpias.append({
                "labelorigen": fila[0],
                "origen": int(fila[1]),
                "labeldestino": fila[2],
                "destino": int(fila[3]),
                "tiempo": fila[5],
                "color": color_hex,
                "origen_x": float(fila[6]),
                "origen_y": float(fila[7]),
                "destino_x": float(fila[8]),
                "destino_y": float(fila[9]),
                "distancia": float(fila[10]),
                "relief": float(fila[11])
            })
            
        return conexiones_limpias

    except Exception as e:
        print(f"Error al obtener conexiones: {e}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion' in locals(): conexion.close()

def obtener_inicios_voladura(id_vola):
    """Obtiene una lista con los IDs de los taladros marcados como is_inicio = 1 o True."""
    try:
        conexion = crear_conexion()
        if not conexion: return []

        cursor = conexion.cursor()
        
        # Buscamos directamente en detonadortaladro los que sean inicio
        sql = """
            SELECT DISTINCT dt.id_taladro 
            FROM detonadortaladro dt
            INNER JOIN taladro t ON dt.id_taladro = t.idtaladro
            WHERE t.proyecto_idproyecto = %s AND dt.is_inicio = 1
        """
        cursor.execute(sql, (id_vola,))
        registros = cursor.fetchall()
        
        # Devolvemos una lista simple de Python con los números de taladro: Ej [14822, 14901]
        inicios = [int(fila[0]) for fila in registros]
        return inicios
        
    except Exception as e:
        print(f"Error al obtener inicios: {e}")
        return []
    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

def obtener_conexiones_por_proyecto(id_proyecto):
    """
    Extrae todos los registros de la tabla 'conexion' filtrados por proyecto
    y devuelve una lista de diccionarios limpios y formateados.
    """
    conexion_db = crear_conexion() # Asegúrate de usar el nombre correcto de tu función de conexión
    if not conexion_db: return []

    try:
        cursor = conexion_db.cursor()

        # Query directa y limpia a la tabla conexion
        sql = """
            SELECT 
                id_conexion,          -- Índice 0
                tiempo_taladro,       -- Índice 1
                color,                -- Índice 2
                proyecto_id_proyecto, -- Índice 3
                idlista,              -- Índice 4
                is_pirotecnico,       -- Índice 5
                id_detonador          -- Índice 6
            FROM conexion 
            WHERE proyecto_id_proyecto = %s
        """
        cursor.execute(sql, (id_proyecto,))
        registros = cursor.fetchall()
        
        conexiones_limpias = []
        for fila in registros:
            # 1. Transformamos el texto '255,255,255,255' a Hexadecimal (#FFFFFF)
            color_rgb = str(fila[2])
            try:
                partes_color = color_rgb.split(',')
                # Tomamos los primeros 3 valores (R, G, B) e ignoramos el Alpha si lo hay
                r, g, b = int(partes_color[0]), int(partes_color[1]), int(partes_color[2])
                color_hex = f"#{r:02x}{g:02x}{b:02x}"
            except Exception:
                color_hex = "#FFFFFF" # Blanco por defecto si el formato falla

            # 2. Guardamos el paquete usando los índices numéricos de la Tupla
            conexiones_limpias.append({
                "id_conexion": int(fila[0]),
                "tiempo_taladro": int(fila[1]),
                "color": color_hex,
                "proyecto_id_proyecto": int(fila[3]) if fila[3] is not None else 0,
                "idlista": int(fila[4]),
                "is_pirotecnico": bool(fila[5]), # Convierte el 0/1 de tinyint a False/True
                "id_detonador": int(fila[6])
            })
            
        return conexiones_limpias

    except Exception as e:
        print(f"Error al obtener la tabla conexion: {e}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion_db' in locals(): conexion_db.close()

def _safe_int(valor, default=0):
    """Convierte a entero de forma segura. Si está vacío o falla, devuelve el default."""
    if valor is None or str(valor).strip() == "":
        return default
    try:
        # Usamos float() primero por si el dato viene como "1.0" desde la DB
        return int(float(valor))
    except (ValueError, TypeError):
        return default

def _string_to_list_int(cadena):
    """Convierte '1,2,3' a [1, 2, 3] ignorando vacíos y errores."""
    if not cadena or str(cadena).strip() == "":
        return []
    try:
        # Separa por comas, limpia espacios y convierte a enteros de forma segura
        return [int(float(x.strip())) for x in str(cadena).split(',') if x.strip()]
    except Exception:
        return []
    
def obtener_detonadores_por_proyecto(id_proyecto):
    """
    Extrae los registros de detonadortaladro filtrados por proyecto,
    asegurando que los datos vacíos no rompan el programa.
    """
    conexion_db = crear_conexion() # Usa tu función de conexión aquí
    if not conexion_db: return []

    try:
        cursor = conexion_db.cursor()

        sql = """
            SELECT 
                dt.id_detonador_taladro, -- Índice 0 
                dt.ids_conector,          -- Índice 1
                dt.tiempos,               -- Índice 2
                dt.ordens,                -- Índice 3
                dt.tiempo_deck,          -- Índice 4
                dt.is_inicio,            -- Índice 5
                dt.is_inicio_ramal,      -- Índice 6
                dt.is_repetido,          -- Índice 7
                dt.id_taladro,           -- Índice 8
                dt.id_conexion,          -- Índice 9
                dt.tiempo_superficie,    -- Índice 10
                dt.tiempo_fondo,         -- Índice 11
                dt.tiempo_inicio         -- Índice 12
            FROM detonadortaladro dt
            INNER JOIN taladro t ON dt.id_taladro = t.idtaladro
            WHERE t.proyecto_idproyecto = %s
        """
        cursor.execute(sql, (id_proyecto,))
        registros = cursor.fetchall()
        
        detonadores_limpios = []
        for fila in registros:
            # 👇 AHORA USAMOS _safe_int PARA PROTEGER CADA CAMPO NUMÉRICO
            detonadores_limpios.append({
                "id_detonador_taladro": _safe_int(fila[0]),
                "id_conector": _string_to_list_int(fila[1]),
                "tiempo": _string_to_list_int(fila[2]),
                "orden": _string_to_list_int(fila[3]),
                "tiempo_deck": _safe_int(fila[4]),
                "is_inicio": bool(_safe_int(fila[5])),
                "is_inicio_ramal": bool(_safe_int(fila[6])),
                "is_repetido": bool(_safe_int(fila[7])),
                "id_taladro": _safe_int(fila[8]),
                "id_conexion": _safe_int(fila[9]),
                "tiempo_superficie": _string_to_list_int(fila[10]),
                "tiempo_fondo": _string_to_list_int(fila[11]),
                "tiempo_inicio": _safe_int(fila[12])
            })
            
        return detonadores_limpios

    except Exception as e:
        print(f"Error al obtener la tabla detonadortaladro: {e}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conexion_db' in locals(): conexion_db.close()


# ------------ KPIS ----------
def obtener_kpi_por_explosivo(id_explosivo):

    db = crear_conexion()
    if not db:
        print("No hay conexión a MySQL para buscar KPIs.")
        return None
        
    cursor = db.cursor(dictionary=True)
    try:
        # Consulta filtrada por el ID del explosivo
        consulta = """
            SELECT 
                vod_minimo, 
                vod_maximo, 
                densidad_minima, 
                densidad_maxima 
            FROM kpis 
            WHERE id_explosivo = %s
        """
        # Ejecutamos pasando el ID de forma segura
        cursor.execute(consulta, (id_explosivo,))
        resultado = cursor.fetchone() # Trae solo 1 fila (diccionario)
        
        return resultado # Ejemplo de lo que devuelve: {'vod_minimo': 4000.00, 'vod_maximo': 6500.00, ...}

    except Error as e:
        print(f"Error al obtener KPIs de la base de datos: {e}")
        return None
    finally:
        if db.is_connected():
            cursor.close()
            db.close()


# ------ OBTENER DATOS PARA EL HOME ------
def obtener_datos_dashboard_kpi(fecha_inicio, fecha_fin):

    db = crear_conexion()
    cursor = db.cursor(dictionary=True)
    
    resultados = {
        "total_voladuras": 0,
        "vod_total": 0.0,
        "sismo_total": 0.00,
        "p80_total": 0.0,
        "densidad_anfo": 0.00, # Valor técnico base por si no hay registros
        "densidad_rioflex": 0.00
    }

    try:
        # 1. 📊 TOTAL DE VOLADURAS
        sql_voladuras = """SELECT COUNT(idproyecto) as total 
        FROM proyecto WHERE fecha_hora BETWEEN %s AND %s"""
        cursor.execute(sql_voladuras, (fecha_inicio, fecha_fin))
        res = cursor.fetchone()
        resultados["total_voladuras"] = res['total']

        print("VOLADURAS:",res['total'])

        # 2. ⚡ VOD PROMEDIO (Velocidad de detonación de los proyectos medidos)
        sql_vod = """SELECT COUNT(vod) as cantidad 
                        FROM proyecto
                        WHERE fecha_hora BETWEEN %s AND %s AND vod > 0 """
        cursor.execute(sql_vod, (fecha_inicio, fecha_fin))
        res = cursor.fetchone()
        resultados["vod_total"] = round(res['cantidad'], 1)

        print("VOD:",res['cantidad'])

        # 3. 🎛️ SISMOGRAFÍA: MÁXIMO PPV DETECTADO (Vibraciones)
        sql_sismo = """SELECT COUNT(vibra) as cantidad
                        FROM proyecto
                        WHERE fecha_hora BETWEEN %s AND %s AND vibra>0"""
                        # Nota: Ajusta 'sismografia' o 'vibraciones' según tu tabla real
        cursor.execute(sql_sismo, (fecha_inicio, fecha_fin))
        res = cursor.fetchone()
        resultados["sismo_total"] = round(res['cantidad'], 2)

        print("VIBRACIONES:",res['cantidad'])


        # 4. 🪨 FRAGMENTACIÓN PROMEDIO (P80 obtenido del modelo JKRMC o mediciones de planta)
        sql_frag = """SELECT COUNT(frag) as cantidad 
                        FROM proyecto 
                        WHERE fecha_hora BETWEEN %s AND %s AND frag > 0"""
        cursor.execute(sql_frag, (fecha_inicio, fecha_fin))
        res = cursor.fetchone()
        resultados["p80_total"] = round(res['cantidad'], 1)

        print("FRAGMENTACION:",res['cantidad'])


        # 5. 🛢️ CANTIDAD DE MUESTRAS DE DENSIDAD ANFO
        sql_anfo = """SELECT COUNT(densidad) as cantidad 
                          FROM proyecto proy
                          INNER JOIN densidad_voladura dv ON proy.idproyecto = dv.id_voladura
                          WHERE proy.fecha_hora BETWEEN %s AND %s AND dv.tipo='ANFO' """
        cursor.execute(sql_anfo, (fecha_inicio, fecha_fin))
        res = cursor.fetchone()
        resultados["densidad_anfo"] = res['cantidad']

        print("ANFO:",res['cantidad'])

        # 6. 🧪 DENSIDAD PROMEDIO DE RIOFLEX
        sql_rioflex = """SELECT COUNT(densidad) as cantidad 
                          FROM proyecto proy
                          INNER JOIN densidad_voladura dv ON proy.idproyecto = dv.id_voladura
                          WHERE proy.fecha_hora BETWEEN %s AND %s AND dv.tipo='RIOFLEX' """
                            # Nota: Ajusta los nombres de tus columnas ('densidad' vs 'densidad_real')
        cursor.execute(sql_rioflex, (fecha_inicio, fecha_fin))
        res = cursor.fetchone()
        resultados["densidad_rioflex"] = round(res['cantidad'], 2)

        print("RIOFLEX:",res['cantidad'])


    except Exception as e:
        print(f"⚠️ Error al recolectar KPIs del Dashboard: {e}")
    finally:
        cursor.close()

    return resultados





