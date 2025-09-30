import os
from werkzeug.utils import secure_filename
from db_config import get_connection


def subir_archivo(tabla, id_registro, archivo, campo, carpeta, user_id_actor=None):
    # Eliminar archivo anterior si existe
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT {campo} FROM {tabla} WHERE id{tabla[:-1].capitalize()} = %s", (id_registro,))
            archivo_anterior = cursor.fetchone()

            if archivo_anterior and archivo_anterior[0]:
                eliminar_archivo(archivo_anterior[0], carpeta)
    finally:
        conn.close()

    # Subir nuevo archivo
    nombre_seguro = secure_filename(archivo.filename)
    nombre_archivo = f'{id_registro}_{nombre_seguro}'
    ruta_directorio = f'uploads/{carpeta}'
    os.makedirs(ruta_directorio, exist_ok=True)

    ruta_completa = os.path.join(ruta_directorio, nombre_archivo)
    archivo.save(ruta_completa)

    # Actualizar base de datos
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                UPDATE {tabla}
                SET {campo} = %s
                WHERE id{tabla[:-1].capitalize()} = %s
            """, (nombre_archivo, id_registro))
            conn.commit()
    finally:
        conn.close()

    return nombre_archivo


def eliminar_archivo(nombre_archivo, carpeta):
    if not nombre_archivo:
        return False

    try:
        ruta_archivo = os.path.join('uploads', carpeta, nombre_archivo)
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
            return True
        return False
    except Exception as e:
        print(f"Error al eliminar archivo: {e}")
        return False