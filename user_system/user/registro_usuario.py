from flask import request, jsonify, g, Blueprint
import bcrypt
from db_config import get_connection
from utils.session_validator import session_validator
from utils.auditoria import registrar_auditoria
from utils.uploader import subir_archivo


registro_bp = Blueprint('registro', __name__)

@registro_bp.route('/usuarios/registro', methods=['POST'])
@session_validator(tabla="usuarios", accion="create")

# registro
def registrar_usuario():
    datos = request.json
    campos_requeridos = [
        'nombreUsuario', 'nombre', 'apellidop',
        'apellidom', 'email', 'password', 'idRol'
    ]

    # 1) Validar que todos los campos estén
    if not all(c in datos for c in campos_requeridos):
        return jsonify({'error': 'Faltan campos requeridos'}), 400

    # 2) Hashear la contraseña
    password_bytes = datos['password'].encode('utf-8')
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    conexion = get_connection()
    try:
        with conexion.cursor() as cursor:
            # 3) INSERT incluyendo idRol
            cursor.execute("""
                INSERT INTO usuarios 
                    (nombreUsuario, nombre, apellidop, apellidom, email, password_hash, idRol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                datos['nombreUsuario'],
                datos['nombre'],
                datos['apellidop'],
                datos['apellidom'],
                datos['email'],
                password_hash,
                datos['idRol']
            ))
            conexion.commit()

            nuevo_id = cursor.lastrowid

            # 4) Registrar auditoría con todos los valores
            id_usuario_actor = getattr(g, 'user_id', None)
            registrar_auditoria(
                id_usuario_actor,
                'create',
                'usuarios',
                nuevo_id,
                valores_anteriores=None,
                valores_nuevos={
                    'nombreUsuario': datos['nombreUsuario'],
                    'nombre': datos['nombre'],
                    'apellidop': datos['apellidop'],
                    'apellidom': datos['apellidom'],
                    'email': datos['email'],
                    'idRol': datos['idRol']
                }
            )

        return jsonify({'mensaje': 'Usuario registrado correctamente', 'id': nuevo_id}), 201

    except Exception as e:
        conexion.rollback()
        print("Error al registrar usuarios:", e)
        return jsonify({'error': 'Error al registrar usuarios'}), 500

    finally:
        conexion.close()


# editar

@registro_bp.route('/usuarios/<int:id_usuario>', methods=['PUT'])
@session_validator(tabla="usuarios", accion="update")
def actualizar_usuario(id_usuario):
    datos = request.json
    campos_requeridos = ['nombreUsuario', 'nombre', 'apellidop', 'apellidom', 'email', 'idRol']

    if not all(c in datos for c in campos_requeridos):
        return jsonify({'error': 'Faltan campos requeridos'}), 400

    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener valores anteriores
            cursor.execute("SELECT * FROM usuarios WHERE idUsuario = %s", (id_usuario,))
            usuario_anterior = cursor.fetchone()
            if not usuario_anterior:
                return jsonify({'error': 'Usuario no encontrado'}), 404

            # Actualizar usuarios
            cursor.execute("""
                UPDATE usuarios
                SET nombreUsuario = %s, nombre = %s, apellidop = %s, apellidom = %s,
                    email = %s, idRol = %s
                WHERE idUsuario = %s
            """, (
                datos['nombreUsuario'], datos['nombre'], datos['apellidop'],
                datos['apellidom'], datos['email'], datos['idRol'], id_usuario
            ))
            conexion.commit()

            # Auditoría
            id_usuario_actor = getattr(g, 'user_id', None)
            registrar_auditoria(
                id_usuario_actor,
                'update',
                'usuarios',
                id_usuario,
                valores_anteriores={
                    k: usuario_anterior[k] for k in campos_requeridos
                },
                valores_nuevos={
                    k: datos[k] for k in campos_requeridos
                }
            )

        return jsonify({'mensaje': 'Usuario actualizado correctamente'}), 200

    except Exception as e:
        conexion.rollback()
        print("Error al actualizar usuarios:", e)
        return jsonify({'error': 'Error al actualizar usuarios'}), 500

    finally:
        conexion.close()



# eliminar

@registro_bp.route('/usuarios/<int:id_usuario>', methods=['DELETE'])
@session_validator(tabla="usuarios", accion="delete")
def eliminar_usuario(id_usuario):
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener datos antes de eliminar
            cursor.execute("SELECT * FROM usuarios WHERE idUsuario = %s", (id_usuario,))
            usuario = cursor.fetchone()
            if not usuario:
                return jsonify({'error': 'Usuario no encontrado'}), 404

            # Eliminar usuarios
            cursor.execute("DELETE FROM usuarios WHERE idUsuario = %s", (id_usuario,))
            conexion.commit()

            # Auditoría
            id_usuario_actor = getattr(g, 'user_id', None)
            registrar_auditoria(
                id_usuario_actor,
                'delete',
                'usuarios',
                id_usuario,
                valores_anteriores={
                    k: usuario[k] for k in usuario if k != 'password_hash'
                },
                valores_nuevos=None
            )

        return jsonify({'mensaje': 'Usuario eliminado correctamente'}), 200

    except Exception as e:
        conexion.rollback()
        print("Error al eliminar usuarios:", e)
        return jsonify({'error': 'Error al eliminar usuarios'}), 500

    finally:
        conexion.close()


# cargar foto de perfil

@registro_bp.route('/usuarios/<int:id_usuario>/foto', methods=['POST'])
@session_validator(tabla="usuarios", accion="update")
def subir_foto_usuario(id_usuario):
    if 'imagen' not in request.files:
        return jsonify({'error': 'No se envió ninguna imagen'}), 400

    archivo = request.files['imagen']

    if archivo.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener valor anterior de 'foto'
            cursor.execute("SELECT foto FROM usuarios WHERE idUsuario = %s", (id_usuario,))
            usuario = cursor.fetchone()

            if not usuario:
                return jsonify({'error': 'Usuario no encontrado'}), 404

            foto_anterior = usuario.get('foto')

        # Subir el archivo
        ruta_guardada = subir_archivo(
            tabla='usuarios',
            id_registro=id_usuario,
            archivo=archivo,
            campo='foto',
            carpeta='usuarios',
            user_id_actor=g.user_id
        )

        # Registrar auditoría
        registrar_auditoria(
            g.user_id,
            'update',
            'usuarios',
            id_usuario,
            valores_anteriores={'foto': foto_anterior},
            valores_nuevos={'foto': ruta_guardada}
        )

        return jsonify({
            'mensaje': 'Foto de perfil actualizada correctamente',
            'ruta': ruta_guardada
        }), 200

    except Exception as e:
        print("Error al subir la foto de perfil:", e)
        return jsonify({'error': 'Error al subir la foto de perfil'}), 500

    finally:
        conexion.close()


# consulta


from utils.image_fetcher import obtener_url_imagen

@registro_bp.route('/usuarios', methods=['GET'])
@session_validator(tabla="usuarios", accion="read")
def obtener_usuarios():
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT 
                    idUsuario, nombreUsuario, nombre, apellidop, apellidom,
                    email, telefono, idRol, estatus, fechaRegistro, foto
                FROM usuarios
            """)
            usuarios = cursor.fetchall()

            for u in usuarios:
                u['foto_url'] = obtener_url_imagen(u['foto'])

            # Auditoría
            id_usuario_actor = getattr(g, 'user_id', None)
            registrar_auditoria(
                id_usuario_actor,
                'read',
                'usuarios',
                None,
                valores_anteriores=None,
                valores_nuevos=None
            )

        return jsonify({'usuarios': usuarios}), 200

    except Exception as e:
        print("Error al obtener usuarios:", e)
        return jsonify({'error': 'Error al obtener usuarios'}), 500

    finally:
        conexion.close()

