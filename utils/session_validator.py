from functools import wraps
from flask import request, jsonify, g
from utils.verificador_permisos import verificar_permiso
from db_config import get_connection

def session_validator(tabla=None, accion=None):
    """
    Decorador que valida el token de sesión activa y, opcionalmente, permisos para una acción sobre una tabla.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization')

            if not token:
                return jsonify({"error": "Token no proporcionado"}), 401

            if token.lower().startswith("bearer "):
                token = token[7:]

            try:
                conexion = get_connection()
                with conexion.cursor() as cursor:
                    cursor.execute("""
                        SELECT idUsuario FROM historico_sesiones 
                        WHERE token_sesion = %s AND fechaLogout IS NULL
                    """, (token,))
                    result = cursor.fetchone()

                    if not result:
                        return jsonify({"error": "Sesión inválida"}), 401

                    g.user_id = result[0]  # Guarda el ID del usuarios en contexto global

                    # Validación de permiso, si se especifican
                    if tabla and accion:
                        if not verificar_permiso(g.user_id, tabla, accion):
                            return jsonify({"error": "No tienes permiso para realizar esta acción"}), 403

            except Exception as e:
                print("Error en session_validator:", e)
                return jsonify({"error": "Error interno en la validación de sesión"}), 500
            finally:
                conexion.close()

            return f(*args, **kwargs)
        return decorated_function
    return decorator
