from db_config import get_connection

def verificar_permiso(id_usuario, tabla, accion):
    try:
        conexion = get_connection()
        with conexion.cursor() as cursor:
            # Buscar permisos asignados directamente al usuarios
            cursor.execute("""
                SELECT 1 FROM usuario_permisos up
                JOIN permisos p ON up.idPermiso = p.idPermiso
                WHERE up.idUsuario = %s AND p.tabla = %s AND p.accion = %s
                LIMIT 1
            """, (id_usuario, tabla, accion))
            if cursor.fetchone():
                return True

            # Buscar permisos por rol del usuarios
            cursor.execute("""
                SELECT 1 FROM usuarios u
                JOIN rol_permisos rp ON u.idRol = rp.idRol
                JOIN permisos p ON rp.idPermiso = p.idPermiso
                WHERE u.idUsuario = %s AND p.tabla = %s AND p.accion = %s
                LIMIT 1
            """, (id_usuario, tabla, accion))
            if cursor.fetchone():
                return True

        return False

    except Exception as e:
        print("Error en verificar_permiso:", e)
        return False

    finally:
        if conexion:
            conexion.close()
