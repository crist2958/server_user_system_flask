from flask import Flask, request, jsonify
from flask_cors import CORS
import bcrypt
import uuid
from datetime import datetime
from db_config import get_connection

app = Flask(__name__)
CORS(app)


# --------------------------
# LOGIN DE USUARIO
# --------------------------
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    direccion_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener al usuarios con o sin importar el estatus para verificar después
    cursor.execute("""
        SELECT u.idUsuario, u.nombreUsuario, u.email, u.idRol, r.nombreRol, u.password_hash, u.estatus
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
        return jsonify({"error": "El usuarios está inactivo"}), 403

    if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        token = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO historico_sesiones (idUsuario, direccion_ip, user_agent, token_sesion)
            VALUES (%s, %s, %s, %s)
        """, (user['idUsuario'], direccion_ip, user_agent, token))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "mensaje": "Login exitoso",
            "token": token,
            "usuarios": {
                "idUsuario": user['idUsuario'],
                "nombreUsuario": user['nombreUsuario'],
                "email": user['email'],
                "idRol": user['idRol'],
                "nombreRol": user['nombreRol']
            }
        }), 200

    cursor.close()
    conn.close()
    return jsonify({"error": "Contraseña incorrecta"}), 401

# --------------------------
# LOGOUT DE USUARIO
# --------------------------
@app.route('/logout', methods=['POST'])
def logout():
    data = request.get_json()
    token = data.get('token')

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
# VERIFICAR TOKEN DE SESIÓN
# --------------------------
@app.route('/auth/verify', methods=['GET'])
def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Token faltante o mal formado'}), 401

    token = auth_header.split(" ")[1]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # También obtenemos el nombre del rol
    cursor.execute("""
        SELECT u.idUsuario, u.nombreUsuario, u.email, u.idRol, r.nombreRol
        FROM historico_sesiones hs
        JOIN usuarios u ON hs.idUsuario = u.idUsuario
        JOIN roles r ON u.idRol = r.idRol
        WHERE hs.token_sesion = %s AND hs.fechaLogout IS NULL
    """, (token,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return jsonify({'usuarios': user}), 200
    else:
        return jsonify({'error': 'Token inválido o sesión expirada'}), 401


# --------------------------
# EJECUCIÓN DEL SERVIDOR
# --------------------------
if __name__ == '__main__':
    app.run(debug=True)
