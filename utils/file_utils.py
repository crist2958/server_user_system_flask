# utils/file_utils.py
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def guardar_imagen(file, carpeta_destino='usuarios', nombre_personalizado=None):
    if not allowed_file(file.filename):
        raise ValueError("Formato de imagen no permitido")

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()

    if nombre_personalizado:
        filename = f"{nombre_personalizado}.{ext}"

    ruta_base = os.path.join('uploads', carpeta_destino)
    os.makedirs(ruta_base, exist_ok=True)

    ruta_relativa = os.path.join(ruta_base, filename)
    file.save(ruta_relativa)

    return ruta_relativa
