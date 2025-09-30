from flask import Blueprint, request, jsonify
import bcrypt
import jwt
from datetime import datetime, timedelta
from db_config import get_connection
from utils.token_validator import SECRET_KEY

auth_bp = Blueprint('auth', __name__)


def obtener_permisos_usuario(id_usuario):
    """Obtiene todos los permisos del usuario (directos y heredados) en formato agrupado"""
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT p.tabla, p.accion
                FROM (
                    -- Permisos heredados del rol
                    SELECT p.tabla, p.accion
                    FROM usuarios u
                    JOIN rol_permisos rp ON u.idRol = rp.idRol
                    JOIN permisos p ON rp.idPermiso = p.idPermiso
                    WHERE u.idUsuario = %s

                    UNION ALL

                    -- Permisos directos
                    SELECT p.tabla, p.accion
                    FROM usuario_permisos up
                    JOIN permisos p ON up.idPermiso = p.idPermiso
                    WHERE up.idUsuario = %s
                ) AS p
            """, (id_usuario, id_usuario))

            # Convertir a formato agrupado que necesita el frontend
            permisos = {}
            for row in cursor.fetchall():
                tabla = row['tabla']
                accion = row['accion']

                if tabla not in permisos:
                    permisos[tabla] = {}

                permisos[tabla][accion] = 1

            # Convertir a lista de objetos
            return [{"tabla": tabla, **acciones} for tabla, acciones in permisos.items()]
    finally:
        conn.close()

#login
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    direccion_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.idUsuario, u.nombreUsuario, u.email, u.idRol, r.nombreRol,
               u.password_hash, u.estatus, u.foto, u.is_superadmin
        FROM usuarios u
        JOIN roles r ON u.idRol = r.idRol
        WHERE u.email = %s
    """, (email,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    if user['estatus'] != 'Activo':
        cursor.close()
        conn.close()
        return jsonify({"error": "El usuario está inactivo"}), 403

    if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        payload = {
            'idUsuario': user['idUsuario'],
            'exp': datetime.utcnow() + timedelta(hours=2),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        cursor.execute("""
            INSERT INTO historico_sesiones (idUsuario, direccion_ip, user_agent, token_sesion)
            VALUES (%s, %s, %s, %s)
        """, (user['idUsuario'], direccion_ip, user_agent, token))
        conn.commit()

        # CORRECCIÓN: Usar el mismo formato que en /usuarios
        foto_url = (
            f"/archivo/usuarios/{user['idUsuario']}/foto"
            if user['foto'] else None
        )

        # Obtener permisos del usuario
        permisos = obtener_permisos_usuario(user['idUsuario'])

        cursor.close()
        conn.close()

        return jsonify({
            "mensaje": "Login exitoso",
            "token": token,
            "usuario": {
                "idUsuario": user['idUsuario'],
                "nombreUsuario": user['nombreUsuario'],
                "email": user['email'],
                "idRol": user['idRol'],
                "nombreRol": user['nombreRol'],
                "foto_url": foto_url,  # Formato consistente
                "is_superadmin": bool(user['is_superadmin'])
            },
            "permisos": permisos
        }), 200

    cursor.close()
    conn.close()
    return jsonify({"error": "Contraseña incorrecta"}), 401

# --------------------------
# LOGOUT DE USUARIO
# --------------------------
@auth_bp.route('/logout', methods=['POST'])
def logout():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Token faltante o mal formado'}), 401

    token = auth_header.split(" ")[1]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE historico_sesiones
        SET fechaLogout = NOW()
        WHERE token_sesion = %s AND fechaLogout IS NULL
    """, (token,))
    conn.commit()

    updated = cursor.rowcount

    cursor.close()
    conn.close()

    if updated == 0:
        return jsonify({"error": "Token inválido o ya cerrado"}), 400

    return jsonify({"mensaje": "Logout exitoso"}), 200


# --------------------------
# VERIFICAR TOKEN
# --------------------------
@auth_bp.route('/auth/verify', methods=['GET'])
def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Token faltante o mal formado'}), 401

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        id_usuario = payload['idUsuario']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expirado'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Token inválido'}), 401

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.idUsuario, u.nombreUsuario, u.email, u.idRol, r.nombreRol, u.foto, u.is_superadmin
        FROM historico_sesiones hs
        JOIN usuarios u ON hs.idUsuario = u.idUsuario
        JOIN roles r ON u.idRol = r.idRol
        WHERE hs.token_sesion = %s AND hs.fechaLogout IS NULL
    """, (token,))

    user = cursor.fetchone()

    if user:
        # Construir ruta relativa para la foto
        foto_url = (
            f"/archivo/usuarios/{user['idUsuario']}/foto"
            if user['foto'] else None
        )

        # Obtener permisos actualizados
        permisos = obtener_permisos_usuario(user['idUsuario'])

        cursor.close()
        conn.close()

        return jsonify({
            'usuario': {
                'idUsuario': user['idUsuario'],
                'nombreUsuario': user['nombreUsuario'],
                'email': user['email'],
                'idRol': user['idRol'],
                'nombreRol': user['nombreRol'],
                'foto_url': foto_url,  # Ruta relativa
                'is_superadmin': bool(user['is_superadmin'])
            },
            'permisos': permisos
        }), 200
    else:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Token inválido o sesión cerrada'}), 401

    # --------------------------
    # OBTENER PERMISOS ACTUALIZADOS
    # --------------------------
@auth_bp.route('/auth/permissions', methods=['GET'])
def get_permissions():
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token faltante o mal formado'}), 401

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            id_usuario = payload['idUsuario']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar que el token está activo
        cursor.execute("""
            SELECT idSesion 
            FROM historico_sesiones 
            WHERE token_sesion = %s AND fechaLogout IS NULL
        """, (token,))
        session = cursor.fetchone()

        if not session:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Token inválido o sesión cerrada'}), 401

        # Obtener permisos actualizados
        permisos = obtener_permisos_usuario(id_usuario)

        # Obtener estado de superadmin
        cursor.execute("""
            SELECT is_superadmin 
            FROM usuarios 
            WHERE idUsuario = %s
        """, (id_usuario,))
        user = cursor.fetchone()
        is_superadmin = user['is_superadmin'] if user else False

        cursor.close()
        conn.close()

        return jsonify({
            'permisos': permisos,
            'is_superadmin': bool(is_superadmin)
        }), 200