from flask import Blueprint, send_from_directory, jsonify, g
from db_config import get_connection
import os

visor_bp = Blueprint('visor_archivo', __name__)

@visor_bp.route('/archivo/<string:tabla>/<int:id_registro>/<string:campo>', methods=['GET'])
def obtener_archivo(tabla, id_registro, campo):
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Construir dinámicamente el nombre de la columna ID
            id_columna = f"id{tabla[:-1].capitalize()}"  # Quita la 's' y pone mayúscula

            cursor.execute(f"SELECT {campo} FROM {tabla} WHERE {id_columna} = %s", (id_registro,))
            resultado = cursor.fetchone()

            if not resultado:
                return jsonify({'error': f'{tabla.capitalize()} no encontrado'}), 404

            nombre_archivo = resultado.get(campo)
            if not nombre_archivo:
                return jsonify({'error': f'{campo} no definido para este registro'}), 404

            carpeta = os.path.join("uploads", tabla)
            ruta_archivo = os.path.join(carpeta, nombre_archivo)

            if not os.path.exists(ruta_archivo):
                return jsonify({'error': 'Archivo no encontrado'}), 404

            return send_from_directory(carpeta, nombre_archivo)

    except Exception as e:
        print("Error al obtener archivo:", e)
        return jsonify({'error': 'Error interno al obtener archivo'}), 500

    finally:
        conexion.close()
