import mysql.connector
from mysql.connector import Error

def crear_conexion():
    try:
        conexion = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='',  # Por defecto en DBngin es vacío
            database='famewaredelion', # Cambia esto por tu base de datos
            port=3308
        )
        if conexion.is_connected():
            print("Conexión exitosa a MariaDB")
            return conexion
    except Error as e:
        print(f"Error al conectar: {e}")
        return None