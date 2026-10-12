# database/consultas.py
from .conexion import crear_conexion

def listar_voladuras():
    db = crear_conexion()
    if not db: return []
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT idproyecto, nombre, fecha_hora,fase,nivel,mallas,frag,vibra,vod,densidad,med_tal,horario FROM proyecto")
    res = cursor.fetchall()
    db.close()
    return res

def obtener_voladuras_por_rango(fecha_inicio, fecha_fin):
    db = crear_conexion()
    cursor = db.cursor(dictionary=True)
    try:
        # Corregimos el error del : y usamos parámetros %s
        sql = """
            SELECT idproyecto, nombre, fecha_hora,fase,nivel,mallas,frag,vibra,vod,densidad,med_tal,horario 
            FROM proyecto 
            WHERE fecha_hora BETWEEN %s AND %s
            ORDER BY fecha_hora ASC
        """
        # Pasar las fechas como tupla para que el conector las limpie automáticamente
        cursor.execute(sql, (fecha_inicio, fecha_fin))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error en la query: {e}")
        return []
    finally:
        db.close()

def eliminar_voladura(id_voladura):
    db = crear_conexion()
    cursor = db.cursor()
    cursor.execute("DELETE FROM proyecto WHERE id = %s", (id_voladura,))
    db.commit()
    db.close()