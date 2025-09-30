# agenda_evidencias.py
# Endpoints para subir/listar/eliminar/servir evidencias de agenda
# Estructura en disco: uploads/agenda/item-<idItem>/<idItem>_<archivo>(n).ext

from flask import Blueprint, jsonify, request, g, send_file
import os
from werkzeug.utils import secure_filename
from db_config import get_connection
from utils.session_validator import session_validator
from utils.auditoria import registrar_auditoria

# Blueprints
agenda_bp = Blueprint('agenda', __name__)
archivos_agenda_bp = Blueprint('archivo_agenda', __name__)

# ---------- Config / Helpers ----------
UPLOADS_ROOT = 'uploads'
AGENDA_BASE = os.path.join(UPLOADS_ROOT, 'agenda')
os.makedirs(AGENDA_BASE, exist_ok=True)  # asegura carpeta base

def _carpeta_item_agenda(id_item: int) -> str:
    """
    Crea (si no existe) y devuelve la carpeta única por item:
    uploads/agenda/item-<idItem>
    """
    ruta = os.path.join(AGENDA_BASE, f'item-{id_item}')
    os.makedirs(ruta, exist_ok=True)
    return ruta

def _nombre_unico(directorio: str, nombre_original: str, prefijo: str = '') -> str:
    """
    Genera un nombre de archivo único en 'directorio' evitando sobrescribir:
    file.jpg -> file.jpg / file(1).jpg / file(2).jpg ...
    """
    base = secure_filename(nombre_original)
    if prefijo:
        base = f"{prefijo}{base}"
    nombre, ext = os.path.splitext(base)
    candidato = base
    i = 1
    while os.path.exists(os.path.join(directorio, candidato)):
        candidato = f"{nombre}({i}){ext}"
        i += 1
    return candidato

def _guardar_archivo_agenda(id_item: int, file_storage) -> dict:
    """
    Guarda archivo en uploads/agenda/item-<idItem>/ y devuelve metadata para DB.
    """
    carpeta = _carpeta_item_agenda(id_item)
    nombre_final = _nombre_unico(carpeta, file_storage.filename, prefijo=f"{id_item}_")
    ruta_fs = os.path.join(carpeta, nombre_final)
    file_storage.save(ruta_fs)

    tam = os.path.getsize(ruta_fs)
    # guardamos ruta relativa legible bajo uploads/ (como en fotos de usuario)
    ruta_rel = f"agenda/item-{id_item}/{nombre_final}"

    return {
        'nombreArchivo': nombre_final,
        'rutaRelativa': ruta_rel,
        'tamanoBytes': tam,
    }

def _eliminar_archivo_agenda(id_item: int, nombre_archivo: str) -> bool:
    """
    Borra el archivo físico si existe. No falla si no está.
    También intenta borrar la carpeta si queda vacía (opcional).
    """
    ruta = os.path.join(AGENDA_BASE, f'item-{id_item}', nombre_archivo)
    if os.path.exists(ruta):
        try:
            os.remove(ruta)
            # intenta quitar carpeta si queda vacía
            try:
                os.rmdir(os.path.dirname(ruta))
            except OSError:
                pass
            return True
        except Exception:
            return False
    return False

def _item_existe(id_item: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT 1 FROM agenda_items WHERE idItem=%s", (id_item,))
            return c.fetchone() is not None
    finally:
        conn.close()

# ---------- Endpoints Evidencias ----------

@agenda_bp.post('/agenda/<int:id_item>/archivos')
@session_validator(tabla="agenda_archivos", accion="create")
def subir_archivos_agenda(id_item):
    """
    multipart/form-data:
      - files[] (múltiples)  o bien  'archivo' / 'imagen' (uno solo)
      - notas (opcional)
      - subidoPor (opcional) -> si no, usa g.user_id si existe
    """
    if not _item_existe(id_item):
        return jsonify({'error': 'Item no encontrado'}), 404

    # Soportar múltiples nombres de campo como en foto de perfil
    files = []
    if 'files' in request.files:
        files = request.files.getlist('files')
    elif 'archivo' in request.files:
        files = [request.files['archivo']]
    elif 'imagen' in request.files:
        files = [request.files['imagen']]

    # Filtra vacíos
    files = [f for f in files if f and f.filename]

    if not files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400

    notas = request.form.get('notas')
    subidoPor = request.form.get('subidoPor', None)
    try:
        subidoPor = int(subidoPor) if subidoPor is not None else getattr(g, 'user_id', None)
    except:
        subidoPor = getattr(g, 'user_id', None)

    guardados = []
    conn = get_connection()
    try:
        conn.start_transaction()
        with conn.cursor(dictionary=True) as c:
            for f in files:
                meta = _guardar_archivo_agenda(id_item, f)

                c.execute("""
                    INSERT INTO agenda_archivos
                    (idItem, nombreArchivo, tipoMime, rutaArchivo, tamanoBytes, notas, subidoPor)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    id_item,
                    meta['nombreArchivo'],
                    f.mimetype or 'application/octet-stream',
                    meta['rutaRelativa'],
                    meta['tamanoBytes'],
                    notas,
                    subidoPor
                ))
                new_id = c.lastrowid

                # Auditoría
                try:
                    registrar_auditoria(
                        getattr(g, 'user_id', None),
                        'create',
                        'agenda_archivos',
                        new_id,
                        valores_anteriores=None,
                        valores_nuevos={
                            'idItem': id_item,
                            'nombreArchivo': meta['nombreArchivo'],
                            'ruta': meta['rutaRelativa'],
                            'tamanoBytes': meta['tamanoBytes'],
                            'notas': notas,
                            'subidoPor': subidoPor
                        }
                    )
                except Exception:
                    pass

                guardados.append({
                    'idArchivo': new_id,
                    'idItem': id_item,
                    'nombreArchivo': meta['nombreArchivo'],
                    'tipoMime': f.mimetype or 'application/octet-stream',
                    'tamanoBytes': meta['tamanoBytes'],
                    'notas': notas,
                    'subidoPor': subidoPor,
                    'ruta': f"/archivo/agenda/{id_item}/{new_id}"
                })

        conn.commit()
        return jsonify({'mensaje': f'{len(guardados)} archivo(s) subido(s)', 'archivos': guardados}), 201

    except Exception as e:
        conn.rollback()
        print("Error subir_archivos_agenda:", e)
        return jsonify({'error': 'Error al subir archivos'}), 500
    finally:
        conn.close()


@agenda_bp.get('/agenda/<int:id_item>/archivos')
@session_validator(tabla="agenda_archivos", accion="read")
def listar_archivos_agenda(id_item):
    if not _item_existe(id_item):
        return jsonify({'error': 'Item no encontrado'}), 404

    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as c:
            c.execute("""
                SELECT idArchivo, idItem, nombreArchivo, tipoMime, rutaArchivo, tamanoBytes, notas, subidoPor, subidoEn
                FROM agenda_archivos
                WHERE idItem=%s
                ORDER BY subidoEn DESC, idArchivo DESC
            """, (id_item,))
            rows = c.fetchall()
            for r in rows:
                r['ruta'] = f"/archivo/agenda/{id_item}/{r['idArchivo']}"
        return jsonify(rows), 200
    except Exception as e:
        print("Error listar_archivos_agenda:", e)
        return jsonify({'error': 'Error al listar archivos'}), 500
    finally:
        conn.close()


@agenda_bp.delete('/agenda/archivos/<int:id_archivo>')
@session_validator(tabla="agenda_archivos", accion="delete")
def eliminar_archivo_agenda(id_archivo):
    conn = get_connection()
    try:
        conn.start_transaction()
        with conn.cursor(dictionary=True) as c:
            c.execute("""
                SELECT idArchivo, idItem, nombreArchivo
                FROM agenda_archivos
                WHERE idArchivo=%s
            """, (id_archivo,))
            row = c.fetchone()
            if not row:
                conn.rollback()
                return jsonify({'error': 'Archivo no encontrado'}), 404

            id_item = row['idItem']
            nombre = row['nombreArchivo']

            # 1) Borrar físico
            _eliminar_archivo_agenda(id_item, nombre)

            # 2) Borrar DB
            c.execute("DELETE FROM agenda_archivos WHERE idArchivo=%s", (id_archivo,))

        conn.commit()

        # Auditoría
        try:
            registrar_auditoria(
                getattr(g, 'user_id', None),
                'delete',
                'agenda_archivos',
                id_archivo,
                valores_anteriores={'idItem': id_item, 'nombreArchivo': nombre},
                valores_nuevos=None
            )
        except Exception:
            pass

        return jsonify({'mensaje': 'Archivo eliminado'}), 200

    except Exception as e:
        conn.rollback()
        print("Error eliminar_archivo_agenda:", e)
        return jsonify({'error': 'Error al eliminar archivo'}), 500
    finally:
        conn.close()


# ---------- Servir archivos (igual patrón que /archivo/usuarios/<id>/foto) ----------

@archivos_agenda_bp.get('/archivo/agenda/<int:id_item>/<int:id_archivo>')
def servir_archivo_agenda(id_item, id_archivo):
    """
    Sirve un archivo de evidencias por su id/file, con mimetype desde DB.
    Ruta física: uploads/agenda/item-<idItem>/<nombreArchivo>
    """
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as c:
            c.execute("""
                SELECT nombreArchivo, tipoMime
                FROM agenda_archivos
                WHERE idArchivo=%s AND idItem=%s
            """, (id_archivo, id_item))
            row = c.fetchone()
            if not row:
                return jsonify({'error': 'Archivo no encontrado'}), 404

            nombre_archivo = row['nombreArchivo']
            mimetype = row['tipoMime'] or 'application/octet-stream'

            ruta = os.path.join(AGENDA_BASE, f'item-{id_item}', nombre_archivo)
            if not os.path.exists(ruta):
                return jsonify({'error': 'Archivo no encontrado en disco'}), 404

            return send_file(ruta, mimetype=mimetype)

    except Exception as e:
        print("Error al servir archivo agenda:", e)
        return jsonify({"error": "Error al obtener archivo"}), 500
    finally:
        conn.close()
