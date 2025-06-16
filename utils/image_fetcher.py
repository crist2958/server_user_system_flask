from flask import url_for

def obtener_url_imagen(nombre_archivo, carpeta='usuarios'):
    """
    Construye la URL pública para acceder a una imagen almacenada en la carpeta static.

    :param nombre_archivo: Nombre del archivo (ej. 'foto_3.jpg')
    :param carpeta: Carpeta dentro de 'static/uploads/' donde está el archivo (ej. 'usuarios')
    :return: URL completa o None si no hay imagen
    """
    if not nombre_archivo:
        return None

    ruta = f'uploads/{carpeta}/{nombre_archivo}'
    return url_for('static', filename=ruta, _external=True)
