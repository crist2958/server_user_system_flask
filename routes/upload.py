from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
import os

from utils.uploader import subir_archivo

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload/imagen', methods=['POST'])
def upload_imagen():
    tabla = request.form.get('tabla')
    id_registro = request.form.get('id_registro')
    campo = request.form.get('campo')
    archivo = request.files.get('archivo')

    if not all([tabla, id_registro, campo, archivo]):
        return jsonify({'error': 'Faltan datos para realizar la subida'}), 400

    try:
        id_usuario_actor = getattr(g, 'user_id', None)
        ruta_guardada = subir_archivo(
            tabla=tabla,
            id_registro=id_registro,
            archivo=archivo,
            campo=campo,
            carpeta=tabla,
            user_id_actor=id_usuario_actor
        )

        return jsonify({
            'mensaje': 'Archivo subido correctamente',
            'ruta': ruta_guardada
        }), 200

    except Exception as e:
        print("❌ Error al subir archivo:", e)
        return jsonify({'error': 'Error interno al subir archivo'}), 500
