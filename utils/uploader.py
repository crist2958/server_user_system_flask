import os
from werkzeug.utils import secure_filename
from db_config import get_connection


def subir_archivo(tabla, id_registro, archivo, campo, carpeta, user_id_actor=None):
    nombre_seguro = secure_filename(archivo.filename)
    nombre_archivo = f'{id_registro}_{nombre_seguro}'
    ruta_directorio = f'uploads/{carpeta}'
    os.makedirs(ruta_directorio, exist_ok=True)

    ruta_completa = os.path.join(ruta_directorio, nombre_archivo)
    archivo.save(ruta_completa)

    # Solo guardar el nombre del archivo (no la ruta completa)
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                UPDATE {tabla}
                SET {campo} = %s
                WHERE id{tabla[:-1].capitalize()} = %s
            """, (nombre_archivo, id_registro))  # 👈 solo el nombre
            conn.commit()
    finally:
        conn.close()

    return ruta_completa  # se puede seguir retornando la ruta completa si lo necesitas internamente
