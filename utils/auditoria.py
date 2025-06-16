# utils/auditoria.py
from datetime import datetime
from db_config import get_connection
import json

def registrar_auditoria(id_usuario, accion, tabla, id_registro, valores_anteriores=None, valores_nuevos=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                INSERT INTO auditoria (
                    idUsuario, accion, tabla, idRegistro,
                    valoresAnteriores, valoresNuevos, fechaAccion
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                id_usuario,
                accion,
                tabla,
                id_registro,
                json_or_none(valores_anteriores),
                json_or_none(valores_nuevos),
                datetime.now()
            ))
            conn.commit()
    except Exception as e:
        print("Error al registrar auditoría:", e)
        conn.rollback()
    finally:
        conn.close()

def json_or_none(data):
    try:
        return json.dumps(data, ensure_ascii=False) if data else None
    except Exception:
        return None
