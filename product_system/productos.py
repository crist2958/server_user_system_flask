# /user_system/user/productos.py

from flask import request, jsonify, g, Blueprint, send_file
import os
from werkzeug.utils import secure_filename
from db_config import get_connection
from utils.session_validator import session_validator
from utils.auditoria import registrar_auditoria
from utils.file_utils import subir_archivo, eliminar_archivo  # Asumiré que creamos estas funciones

# Crear blueprints
categorias_bp = Blueprint('categorias', __name__)
proveedores_bp = Blueprint('proveedores', __name__)
contactos_bp = Blueprint('contactos', __name__)
productos_bp = Blueprint('productos', __name__)
archivos_productos_bp = Blueprint('archivos_productos', __name__)  # Nuevo blueprint para archivos de productos


# Configuración de carpetas para imágenes
UPLOAD_FOLDER = 'uploads'
PRODUCTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'productos')
os.makedirs(PRODUCTOS_FOLDER, exist_ok=True)


# ================================
#        ENDPOINTS CATEGORÍAS
# ================================

@categorias_bp.route('/categorias', methods=['GET'])
@session_validator(tabla="categorias", accion="read")
def obtener_categorias():
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM categorias")
            categorias = cursor.fetchall()
        return jsonify(categorias), 200
    except Exception as e:
        print(f"Error al obtener categorías: {e}")
        return jsonify({"error": "Error al obtener categorías"}), 500
    finally:
        conexion.close()


@categorias_bp.route('/categorias', methods=['POST'])
@session_validator(tabla="categorias", accion="create")
def crear_categoria():
    datos = request.json
    if 'nombre' not in datos:
        return jsonify({"error": "Falta el campo nombre"}), 400

    conexion = get_connection()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "INSERT INTO categorias (nombre, descripcion) VALUES (%s, %s)",
                (datos['nombre'], datos.get('descripcion', None)))
            id_categoria = cursor.lastrowid
            conexion.commit()

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'create',
                'categorias',
                id_categoria,
                valores_anteriores=None,
                valores_nuevos=datos
            )

        return jsonify({"mensaje": "Categoría creada", "id": id_categoria}), 201
    except Exception as e:
        conexion.rollback()
        print(f"Error al crear categoría: {e}")
        return jsonify({"error": "Error al crear categoría"}), 500
    finally:
        conexion.close()


@categorias_bp.route('/categorias/<int:id_categoria>', methods=['PUT'])
@session_validator(tabla="categorias", accion="update")
def actualizar_categoria(id_categoria):
    datos = request.json
    if 'nombre' not in datos:
        return jsonify({"error": "Falta el campo nombre"}), 400

    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener valores anteriores
            cursor.execute("SELECT * FROM categorias WHERE idCategoria = %s", (id_categoria,))
            categoria_anterior = cursor.fetchone()
            if not categoria_anterior:
                return jsonify({"error": "Categoría no encontrada"}), 404

            # Actualizar
            cursor.execute(
                "UPDATE categorias SET nombre = %s, descripcion = %s WHERE idCategoria = %s",
                (datos['nombre'], datos.get('descripcion', None), id_categoria))
            conexion.commit()

            # Preparar auditoría
            valores_anteriores = {
                'nombre': categoria_anterior['nombre'],
                'descripcion': categoria_anterior['descripcion']
            }
            valores_nuevos = {
                'nombre': datos['nombre'],
                'descripcion': datos.get('descripcion', None)
            }
            registrar_auditoria(
                g.user_id,
                'update',
                'categorias',
                id_categoria,
                valores_anteriores=valores_anteriores,
                valores_nuevos=valores_nuevos
            )

        return jsonify({"mensaje": "Categoría actualizada"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al actualizar categoría: {e}")
        return jsonify({"error": "Error al actualizar categoría"}), 500
    finally:
        conexion.close()


@categorias_bp.route('/categorias/<int:id_categoria>', methods=['DELETE'])
@session_validator(tabla="categorias", accion="delete")
def eliminar_categoria(id_categoria):
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener la categoría a eliminar
            cursor.execute("SELECT * FROM categorias WHERE idCategoria = %s", (id_categoria,))
            categoria = cursor.fetchone()
            if not categoria:
                return jsonify({"error": "Categoría no encontrada"}), 404

            # Verificar si tiene productos asociados
            cursor.execute("SELECT COUNT(*) AS total FROM productos WHERE idCategoria = %s", (id_categoria,))
            resultado = cursor.fetchone()
            if resultado['total'] > 0:
                return jsonify({"error": "No se puede eliminar categoría con productos asociados"}), 400

            # Eliminar
            cursor.execute("DELETE FROM categorias WHERE idCategoria = %s", (id_categoria,))
            conexion.commit()

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'delete',
                'categorias',
                id_categoria,
                valores_anteriores=categoria,
                valores_nuevos=None
            )

        return jsonify({"mensaje": "Categoría eliminada"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al eliminar categoría: {e}")
        return jsonify({"error": "Error al eliminar categoría"}), 500
    finally:
        conexion.close()


# ================================
#        ENDPOINTS PROVEEDORES
# ================================

@proveedores_bp.route('/proveedores', methods=['GET'])
@session_validator(tabla="proveedores", accion="read")
def obtener_proveedores():
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM proveedores")
            proveedores = cursor.fetchall()
        return jsonify(proveedores), 200
    except Exception as e:
        print(f"Error al obtener proveedores: {e}")
        return jsonify({"error": "Error al obtener proveedores"}), 500
    finally:
        conexion.close()


@proveedores_bp.route('/proveedores', methods=['POST'])
@session_validator(tabla="proveedores", accion="create")
def crear_proveedor():
    datos = request.json
    campos_requeridos = ['nombre', 'telefono', 'idCategoria']
    if not all(campo in datos for campo in campos_requeridos):
        return jsonify({"error": f"Faltan campos: {', '.join(campos_requeridos)}"}), 400

    conexion = get_connection()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """INSERT INTO proveedores 
                (nombre, telefono, email, direccion, pagWeb, idCategoria) 
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (datos['nombre'], datos['telefono'], datos.get('email'),
                 datos.get('direccion'), datos.get('pagWeb'), datos['idCategoria']))
            id_proveedor = cursor.lastrowid
            conexion.commit()

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'create',
                'proveedores',
                id_proveedor,
                valores_anteriores=None,
                valores_nuevos=datos
            )

        return jsonify({"mensaje": "Proveedor creado", "id": id_proveedor}), 201
    except Exception as e:
        conexion.rollback()
        print(f"Error al crear proveedor: {e}")
        return jsonify({"error": "Error al crear proveedor"}), 500
    finally:
        conexion.close()


@proveedores_bp.route('/proveedores/<int:id_proveedor>', methods=['PUT'])
@session_validator(tabla="proveedores", accion="update")
def actualizar_proveedor(id_proveedor):
    datos = request.json
    campos_requeridos = ['nombre', 'telefono', 'idCategoria']
    if not all(campo in datos for campo in campos_requeridos):
        return jsonify({"error": f"Faltan campos: {', '.join(campos_requeridos)}"}), 400

    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener proveedor anterior
            cursor.execute("SELECT * FROM proveedores WHERE idProveedor = %s", (id_proveedor,))
            proveedor_anterior = cursor.fetchone()
            if not proveedor_anterior:
                return jsonify({"error": "Proveedor no encontrado"}), 404

            # Actualizar
            cursor.execute(
                """UPDATE proveedores 
                SET nombre = %s, telefono = %s, email = %s, direccion = %s, pagWeb = %s, idCategoria = %s 
                WHERE idProveedor = %s""",
                (datos['nombre'], datos['telefono'], datos.get('email'),
                 datos.get('direccion'), datos.get('pagWeb'), datos['idCategoria'], id_proveedor))
            conexion.commit()

            # Preparar auditoría
            valores_anteriores = {k: proveedor_anterior[k] for k in proveedor_anterior}
            valores_nuevos = datos

            registrar_auditoria(
                g.user_id,
                'update',
                'proveedores',
                id_proveedor,
                valores_anteriores=valores_anteriores,
                valores_nuevos=valores_nuevos
            )

        return jsonify({"mensaje": "Proveedor actualizado"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al actualizar proveedor: {e}")
        return jsonify({"error": "Error al actualizar proveedor"}), 500
    finally:
        conexion.close()


@proveedores_bp.route('/proveedores/<int:id_proveedor>', methods=['DELETE'])
@session_validator(tabla="proveedores", accion="delete")
def eliminar_proveedor(id_proveedor):
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener proveedor
            cursor.execute("SELECT * FROM proveedores WHERE idProveedor = %s", (id_proveedor,))
            proveedor = cursor.fetchone()
            if not proveedor:
                return jsonify({"error": "Proveedor no encontrado"}), 404

            # Verificar si tiene productos asociados
            cursor.execute("SELECT COUNT(*) AS total FROM productos WHERE idProveedor = %s", (id_proveedor,))
            resultado = cursor.fetchone()
            if resultado['total'] > 0:
                return jsonify({"error": "No se puede eliminar proveedor con productos asociados"}), 400

            # Eliminar contactos primero
            cursor.execute("DELETE FROM contacto_proveedor WHERE idProveedor = %s", (id_proveedor,))

            # Eliminar proveedor
            cursor.execute("DELETE FROM proveedores WHERE idProveedor = %s", (id_proveedor,))
            conexion.commit()

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'delete',
                'proveedores',
                id_proveedor,
                valores_anteriores=proveedor,
                valores_nuevos=None
            )

        return jsonify({"mensaje": "Proveedor eliminado"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al eliminar proveedor: {e}")
        return jsonify({"error": "Error al eliminar proveedor"}), 500
    finally:
        conexion.close()


# =================================
#        ENDPOINTS CONTACTOS
# =================================

@contactos_bp.route('/proveedores/<int:id_proveedor>/contactos', methods=['GET'])
@session_validator(tabla="contacto_proveedor", accion="read")
def obtener_contactos_proveedor(id_proveedor):
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM contacto_proveedor WHERE idProveedor = %s", (id_proveedor,))
            contactos = cursor.fetchall()
        return jsonify(contactos), 200
    except Exception as e:
        print(f"Error al obtener contactos: {e}")
        return jsonify({"error": "Error al obtener contactos"}), 500
    finally:
        conexion.close()


@contactos_bp.route('/contactos', methods=['POST'])
@session_validator(tabla="contacto_proveedor", accion="create")
def crear_contacto():
    datos = request.json
    campos_requeridos = ['idProveedor', 'nombre', 'telefono', 'email']
    if not all(campo in datos for campo in campos_requeridos):
        return jsonify({"error": f"Faltan campos: {', '.join(campos_requeridos)}"}), 400

    conexion = get_connection()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """INSERT INTO contacto_proveedor 
                (idProveedor, nombre, area, telefono, email) 
                VALUES (%s, %s, %s, %s, %s)""",
                (datos['idProveedor'], datos['nombre'], datos.get('area'),
                 datos['telefono'], datos['email']))
            id_contacto = cursor.lastrowid
            conexion.commit()

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'create',
                'contacto_proveedor',
                id_contacto,
                valores_anteriores=None,
                valores_nuevos=datos
            )

        return jsonify({"mensaje": "Contacto creado", "id": id_contacto}), 201
    except Exception as e:
        conexion.rollback()
        print(f"Error al crear contacto: {e}")
        return jsonify({"error": "Error al crear contacto"}), 500
    finally:
        conexion.close()


@contactos_bp.route('/contactos/<int:id_contacto>', methods=['PUT'])
@session_validator(tabla="contacto_proveedor", accion="update")
def actualizar_contacto(id_contacto):
    datos = request.json
    campos_requeridos = ['nombre', 'telefono', 'email']
    if not all(campo in datos for campo in campos_requeridos):
        return jsonify({"error": f"Faltan campos: {', '.join(campos_requeridos)}"}), 400

    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener contacto anterior
            cursor.execute("SELECT * FROM contacto_proveedor WHERE idContaProv = %s", (id_contacto,))
            contacto_anterior = cursor.fetchone()
            if not contacto_anterior:
                return jsonify({"error": "Contacto no encontrado"}), 404

            # Actualizar
            cursor.execute(
                """UPDATE contacto_proveedor 
                SET nombre = %s, area = %s, telefono = %s, email = %s 
                WHERE idContaProv = %s""",
                (datos['nombre'], datos.get('area'), datos['telefono'], datos['email'], id_contacto))
            conexion.commit()

            # Preparar auditoría
            valores_anteriores = {k: contacto_anterior[k] for k in contacto_anterior}
            valores_nuevos = datos

            registrar_auditoria(
                g.user_id,
                'update',
                'contacto_proveedor',
                id_contacto,
                valores_anteriores=valores_anteriores,
                valores_nuevos=valores_nuevos
            )

        return jsonify({"mensaje": "Contacto actualizado"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al actualizar contacto: {e}")
        return jsonify({"error": "Error al actualizar contacto"}), 500
    finally:
        conexion.close()


@contactos_bp.route('/contactos/<int:id_contacto>', methods=['DELETE'])
@session_validator(tabla="contacto_proveedor", accion="delete")
def eliminar_contacto(id_contacto):
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener contacto
            cursor.execute("SELECT * FROM contacto_proveedor WHERE idContaProv = %s", (id_contacto,))
            contacto = cursor.fetchone()
            if not contacto:
                return jsonify({"error": "Contacto no encontrado"}), 404

            # Eliminar
            cursor.execute("DELETE FROM contacto_proveedor WHERE idContaProv = %s", (id_contacto,))
            conexion.commit()

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'delete',
                'contacto_proveedor',
                id_contacto,
                valores_anteriores=contacto,
                valores_nuevos=None
            )

        return jsonify({"mensaje": "Contacto eliminado"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al eliminar contacto: {e}")
        return jsonify({"error": "Error al eliminar contacto"}), 500
    finally:
        conexion.close()


# ================================
#        ENDPOINTS PRODUCTOS
# ================================

@productos_bp.route('/productos', methods=['GET'])
@session_validator(tabla="productos", accion="read")
def obtener_productos():
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM productos")
            productos = cursor.fetchall()
            # Agregar URL de imagen si existe
            for p in productos:
                if p['foto']:
                    p['foto_url'] = f"/archivo/productos/{p['idProducto']}/foto"
                else:
                    p['foto_url'] = None
        return jsonify(productos), 200
    except Exception as e:
        print(f"Error al obtener productos: {e}")
        return jsonify({"error": "Error al obtener productos"}), 500
    finally:
        conexion.close()


@productos_bp.route('/productos', methods=['POST'])
@session_validator(tabla="productos", accion="create")
def crear_producto():
    datos = request.form
    campos_requeridos = ['nombre', 'NoSerie', 'marca', 'modelo', 'precio', 'stock', 'idProveedor', 'idCategoria']
    if not all(campo in datos for campo in campos_requeridos):
        return jsonify({"error": f"Faltan campos: {', '.join(campos_requeridos)}"}), 400

    # Obtener archivo si existe
    archivo = request.files.get('foto', None)

    # Validar precio
    precio = float(datos['precio'])
    if precio < 0:
        return jsonify({"error": "El precio no puede ser negativo"}), 400

    conexion = get_connection()
    try:
        with conexion.cursor() as cursor:
            # Insertar producto
            cursor.execute(
                """INSERT INTO productos 
                (nombre, NoSerie, marca, modelo, descripcion, precio, stock, idProveedor, idCategoria) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (datos['nombre'], datos['NoSerie'], datos['marca'], datos['modelo'],
                 datos.get('descripcion'), precio, datos['stock'], datos['idProveedor'], datos['idCategoria']))
            id_producto = cursor.lastrowid

            # Si se envió una imagen, guardarla
            nombre_archivo = None
            if archivo:
                nombre_archivo = subir_archivo(
                    tabla='productos',
                    id_registro=id_producto,
                    archivo=archivo,
                    campo='foto',
                    carpeta='productos'
                )
                # Actualizar el registro con el nombre del archivo
                cursor.execute(
                    "UPDATE productos SET foto = %s WHERE idProducto = %s",
                    (nombre_archivo, id_producto))

            conexion.commit()

            # Preparar datos para auditoría
            datos_auditoria = {k: datos[k] for k in datos}
            if nombre_archivo:
                datos_auditoria['foto'] = nombre_archivo

            registrar_auditoria(
                g.user_id,
                'create',
                'productos',
                id_producto,
                valores_anteriores=None,
                valores_nuevos=datos_auditoria
            )

        return jsonify({"mensaje": "Producto creado", "id": id_producto}), 201
    except Exception as e:
        conexion.rollback()
        print(f"Error al crear producto: {e}")
        return jsonify({"error": "Error al crear producto"}), 500
    finally:
        conexion.close()


@productos_bp.route('/productos/<int:id_producto>', methods=['PUT'])
@session_validator(tabla="productos", accion="update")
def actualizar_producto(id_producto):
    datos = request.form
    campos_requeridos = ['nombre', 'NoSerie', 'marca', 'modelo', 'precio', 'stock', 'idProveedor', 'idCategoria']
    if not all(campo in datos for campo in campos_requeridos):
        return jsonify({"error": f"Faltan campos: {', '.join(campos_requeridos)}"}), 400

    archivo = request.files.get('foto', None)
    precio = float(datos['precio'])
    if precio < 0:
        return jsonify({"error": "El precio no puede ser negativo"}), 400

    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener producto anterior
            cursor.execute("SELECT * FROM productos WHERE idProducto = %s", (id_producto,))
            producto_anterior = cursor.fetchone()
            if not producto_anterior:
                return jsonify({"error": "Producto no encontrado"}), 404

            # Actualizar datos
            cursor.execute(
                """UPDATE productos 
                SET nombre = %s, NoSerie = %s, marca = %s, modelo = %s, descripcion = %s, 
                precio = %s, stock = %s, idProveedor = %s, idCategoria = %s 
                WHERE idProducto = %s""",
                (datos['nombre'], datos['NoSerie'], datos['marca'], datos['modelo'],
                 datos.get('descripcion'), precio, datos['stock'], datos['idProveedor'],
                 datos['idCategoria'], id_producto))

            # Manejo de imagen
            nombre_archivo = None
            if archivo:
                nombre_archivo = subir_archivo(
                    tabla='productos',
                    id_registro=id_producto,
                    archivo=archivo,
                    campo='foto',
                    carpeta='productos'
                )
                cursor.execute(
                    "UPDATE productos SET foto = %s WHERE idProducto = %s",
                    (nombre_archivo, id_producto))
            elif 'foto' in datos and datos['foto'] == '':  # Si se indica borrar la imagen
                # Eliminar imagen actual si existe
                if producto_anterior['foto']:
                    eliminar_archivo(producto_anterior['foto'], 'productos')
                cursor.execute(
                    "UPDATE productos SET foto = NULL WHERE idProducto = %s",
                    (id_producto,))

            conexion.commit()

            # Preparar auditoría
            valores_anteriores = {k: producto_anterior[k] for k in producto_anterior}
            valores_nuevos = {k: datos[k] for k in datos}
            if nombre_archivo:
                valores_nuevos['foto'] = nombre_archivo
            elif 'foto' in datos and datos['foto'] == '':
                valores_nuevos['foto'] = None

            registrar_auditoria(
                g.user_id,
                'update',
                'productos',
                id_producto,
                valores_anteriores=valores_anteriores,
                valores_nuevos=valores_nuevos
            )

        return jsonify({"mensaje": "Producto actualizado"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al actualizar producto: {e}")
        return jsonify({"error": "Error al actualizar producto"}), 500
    finally:
        conexion.close()


@productos_bp.route('/productos/<int:id_producto>', methods=['DELETE'])
@session_validator(tabla="productos", accion="delete")
def eliminar_producto(id_producto):
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            # Obtener producto
            cursor.execute("SELECT * FROM productos WHERE idProducto = %s", (id_producto,))
            producto = cursor.fetchone()
            if not producto:
                return jsonify({"error": "Producto no encontrado"}), 404

            # Eliminar imagen si existe
            if producto['foto']:
                eliminar_archivo(producto['foto'], 'productos')

            # Eliminar producto
            cursor.execute("DELETE FROM productos WHERE idProducto = %s", (id_producto,))
            conexion.commit()

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'delete',
                'productos',
                id_producto,
                valores_anteriores=producto,
                valores_nuevos=None
            )

        return jsonify({"mensaje": "Producto eliminado"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al eliminar producto: {e}")
        return jsonify({"error": "Error al eliminar producto"}), 500
    finally:
        conexion.close()


# Servir imagen del producto
@archivos_productos_bp.route('/archivo/productos/<int:id_producto>/foto', methods=['GET'])
def servir_foto_producto(id_producto):
    conexion = get_connection()
    try:
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT foto FROM productos WHERE idProducto = %s", (id_producto,))
            producto = cursor.fetchone()
            if not producto or not producto['foto']:
                return jsonify({'error': 'Foto no encontrada'}), 404

            nombre_archivo = producto['foto']
            ruta_archivo = os.path.join(PRODUCTOS_FOLDER, nombre_archivo)

            if not os.path.exists(ruta_archivo):
                return jsonify({'error': 'Archivo no encontrado'}), 404

            return send_file(ruta_archivo, mimetype='image/jpeg')
    except Exception as e:
        print("Error al servir archivo:", e)
        return jsonify({"error": "Error al obtener foto"}), 500
    finally:
        conexion.close()


# Nuevo endpoint en productos.py
@proveedores_bp.route('/proveedores/<int:id_proveedor>/reasignar', methods=['POST'])
@session_validator(tabla="proveedores", accion="update")
def reasignar_productos_proveedor(id_proveedor):
    datos = request.json
    if 'nuevo_proveedor_id' not in datos:
        return jsonify({"error": "Falta ID de nuevo proveedor"}), 400

    nuevo_id = datos['nuevo_proveedor_id']
    conexion = get_connection()
    try:
        with conexion.cursor() as cursor:
            # Reasignar productos
            cursor.execute(
                "UPDATE productos SET idProveedor = %s WHERE idProveedor = %s",
                (nuevo_id, id_proveedor)
            )

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'reasign',
                'proveedores',
                id_proveedor,
                valores_anteriores={'proveedor_original': id_proveedor},
                valores_nuevos={'nuevo_proveedor': nuevo_id}
            )

            conexion.commit()
        return jsonify({"mensaje": "Productos reasignados"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al reasignar productos: {e}")
        return jsonify({"error": "Error al reasignar productos"}), 500
    finally:
        conexion.close()


# En categorias_bp (productos.py)
@categorias_bp.route('/categorias/<int:id_categoria>/reasignar', methods=['POST'])
@session_validator(tabla="categorias", accion="update")
def reasignar_productos_categoria(id_categoria):
    datos = request.json
    if 'nueva_categoria_id' not in datos:
        return jsonify({"error": "Falta ID de nueva categoría"}), 400

    nueva_id = datos['nueva_categoria_id']
    conexion = get_connection()
    try:
        with conexion.cursor() as cursor:
            # Reasignar productos
            cursor.execute(
                "UPDATE productos SET idCategoria = %s WHERE idCategoria = %s",
                (nueva_id, id_categoria)
            )

            # Auditoría
            registrar_auditoria(
                g.user_id,
                'reasign',
                'categorias',
                id_categoria,
                valores_anteriores={'categoria_original': id_categoria},
                valores_nuevos={'nueva_categoria': nueva_id}
            )

            conexion.commit()
        return jsonify({"mensaje": "Productos reasignados"}), 200
    except Exception as e:
        conexion.rollback()
        print(f"Error al reasignar productos: {e}")
        return jsonify({"error": "Error al reasignar productos"}), 500
    finally:
        conexion.close()