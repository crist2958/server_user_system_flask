from flask import request, jsonify, g, Blueprint
import bcrypt
from db_config import get_connection
from utils.session_validator import session_validator
from utils.auditoria import registrar_auditoria

asign_bp = Blueprint('asignar', __name__)

@asign_bp.route('/asign', methods=['POST'])
@session_validator(tabla="permisos", accion="create")
def asignar_permiso():
    datos = request.json
    campos_requeridos = ['tipoDestino', 'idDestino', 'tabla', 'accion', 'operacion']

    if not all(c in datos for c in campos_requeridos):
        return jsonify({'error': 'Faltan campos requeridos'}), 400

    tipo_destino = datos['tipoDestino']
    id_destino = datos['idDestino']
    tabla_permiso = datos['tabla']
    accion_permiso = datos['accion']
    operacion = datos['operacion']  # 'asignar' o 'revocar'

    if tipo_destino not in ('usuarios', 'rol'):
        return jsonify({'error': 'tipoDestino inválido, debe ser "usuarios" o "rol"'}), 400

    if operacion not in ('asignar', 'revocar'):
        return jsonify({'error': 'operacion inválida, debe ser "asignar" o "revocar"'}), 400

    try:
        conexion = get_connection()
        with conexion.cursor(dictionary=True) as cursor:
            # Buscar ID del permiso
            cursor.execute("SELECT idPermiso FROM permisos WHERE tabla = %s AND accion = %s", (tabla_permiso, accion_permiso))
            resultado = cursor.fetchone()
            id_permiso = resultado['idPermiso'] if resultado else None

            # Ejecutar el procedimiento
            cursor.callproc('sp_GestionarPermiso', (
                tipo_destino,
                id_destino,
                tabla_permiso,
                accion_permiso,
                operacion
            ))
            conexion.commit()

            # Determinar valores anteriores y nuevos
            valores_anteriores = ""
            valores_nuevos = ""

            if operacion == 'revocar':
                valores_anteriores = f"permiso: {accion_permiso} sobre {tabla_permiso}"
                valores_nuevos = "sin permiso"
            else:  # asignar
                valores_anteriores = "sin permiso"
                valores_nuevos = f"permiso: {accion_permiso} sobre {tabla_permiso}"
#----------------------------------------------------------------------------------------------------

            # 1. Obtener usuarios desde g
            id_usuario_actor = getattr(g, 'user_id', None) or getattr(g, 'usuarios', {}).get('idUsuario', None)
            # 2. Determinar nombre lógico de tabla
            tabla_auditoria = 'rol_permisos' if tipo_destino == 'rol' else 'usuario_permisos'
            # 3. Preparar datos de auditoría
            valores_anteriores = None
            valores_nuevos = None
            if operacion == 'revocar':
                valores_anteriores = {'permiso': f'{accion_permiso} sobre {tabla_permiso}'}
                valores_nuevos = {'permiso': 'sin permiso'}
            else:
                valores_anteriores = {'permiso': 'sin permiso'}
                valores_nuevos = {'permiso': f'{accion_permiso} sobre {tabla_permiso}'}

            # 4. Registrar en auditoría
            registrar_auditoria(
                id_usuario_actor,
                'update',
                tabla_auditoria,
                id_destino,
                valores_anteriores,
                valores_nuevos
            )

            # ----------------------------------------------------------------------------------------------------

            conexion.commit()
        return jsonify({'mensaje': f'Permiso {operacion} correctamente'}), 200

    except Exception as e:
        print("Error en asignación/revocación de permiso:", e)
        return jsonify({'error': str(e)}), 500

    finally:
        conexion.close()