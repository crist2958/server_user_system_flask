# utils/verificador_permisos.py

from db_config import get_connection


def verificar_permiso(id_usuario, tabla, accion):
    """
    Verifica si un usuario tiene permiso para realizar una acción en una tabla.
    Considera permisos directos y heredados del rol.
    """
    try:
        conexion = get_connection()
        with conexion.cursor() as cursor:
            # Verificar si el usuario es superusuario
            cursor.execute("""
                SELECT is_superadmin 
                FROM usuarios 
                WHERE idUsuario = %s
            """, (id_usuario,))
            usuario = cursor.fetchone()

            if usuario and usuario[0]:  # Si es superusuario
                return True

            # Buscar permisos asignados directamente al usuario
            cursor.execute("""
                SELECT 1 FROM usuario_permisos up
                JOIN permisos p ON up.idPermiso = p.idPermiso
                WHERE up.idUsuario = %s AND p.tabla = %s AND p.accion = %s
                LIMIT 1
            """, (id_usuario, tabla, accion))
            if cursor.fetchone():
                return True

            # Buscar permisos por rol de usuario
            cursor.execute("""
                SELECT 1 FROM usuarios u
                JOIN rol_permisos rp ON u.idRol = rp.idRol
                JOIN permisos p ON rp.idPermiso = p.idPermiso
                WHERE u.idUsuario = %s AND p.tabla = %s AND p.accion = %s
                LIMIT 1
            """, (id_usuario, tabla, accion))
            return cursor.fetchone() is not None

    except Exception as e:
        print("Error en verificar_permiso:", e)
        return False

    finally:
        if conexion:
            conexion.close()