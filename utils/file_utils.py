# /user_system/user/utils/file_utils.py

import os
import bcrypt
from werkzeug.utils import secure_filename


def subir_archivo(tabla, id_registro, archivo, campo, carpeta):
    """Sube un archivo al sistema y actualiza la base de datos"""
    # Crear directorio si no existe
    ruta_directorio = os.path.join('uploads', carpeta)
    os.makedirs(ruta_directorio, exist_ok=True)

    # Generar nombre seguro
    nombre_seguro = secure_filename(archivo.filename)
    nombre_archivo = f'{id_registro}_{nombre_seguro}'
    ruta_completa = os.path.join(ruta_directorio, nombre_archivo)

    # Guardar archivo
    archivo.save(ruta_completa)

    return nombre_archivo


def eliminar_archivo(nombre_archivo, carpeta):
    """Elimina un archivo del sistema"""
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