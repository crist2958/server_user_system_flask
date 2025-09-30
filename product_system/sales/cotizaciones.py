# sales/cotizaciones.py
from flask import Blueprint, request, jsonify, g
from db_config import get_connection
from utils.session_validator import session_validator
from utils.auditoria import registrar_auditoria
from decimal import Decimal
import uuid
from datetime import datetime

cotizaciones_bp = Blueprint('cotizaciones', __name__)

# ----------------------------
# Helpers
# ----------------------------

def _format_folio(id_cot):
    return f"Q-{int(id_cot):05d}"

def _to_decimal(x, default="0"):
    if x is None:
        x = default
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal(default)

def _calc_totales(items, desc_pct, iva_enabled, iva_pct):
    """
    Calcula subtotal, descuento importe, iva importe y total con Decimal.
    items: [{precioUnitario, cantidad}]
    """
    subtotal = Decimal("0")
    for it in items:
        precio = _to_decimal(it.get("precioUnitario"))
        cantidad = Decimal(str(int(it.get("cantidad", 1))))
        if cantidad < 1:
            cantidad = Decimal("1")
        subtotal += (precio * cantidad)

    descuento_imp = (subtotal * (desc_pct / Decimal("100"))).quantize(Decimal("0.01"))
    base = (subtotal - descuento_imp)
    iva_imp = (base * (iva_pct / Decimal("100"))).quantize(Decimal("0.01")) if iva_enabled else Decimal("0.00")
    total = (base + iva_imp).quantize(Decimal("0.01"))

    # Redondeos a 2 decimales
    subtotal = subtotal.quantize(Decimal("0.01"))
    return subtotal, descuento_imp, iva_imp, total

def _cliente_nombre_expr():
    """
    Devuelve SQL para nombre de cliente completo en una expresión CASE.
    Evitamos usar alias en WHERE y lo repetimos cuando sea necesario.
    """
    return ("CASE WHEN c.tipoCliente = 'Persona' "
            "THEN CONCAT(c.nombre, ' ', COALESCE(c.apellidoP,''), ' ', COALESCE(c.apellidoM,'')) "
            "ELSE c.nombre END")

def _fetch_cotizacion(conn, id_cot):
    with conn.cursor(dictionary=True) as cur:
        # Header
        cur.execute(f"""
            SELECT
                ct.idCotizacion      AS id,
                ct.folio,
                ct.fecha,
                ct.idCliente,
                {_cliente_nombre_expr()} AS clienteNombre,
                ct.idContacto,
                ct.idUsuario,
                ct.estatus,
                ct.descuentoPorcentaje,
                ct.ivaHabilitado,
                ct.ivaPorcentaje,
                ct.subtotal,
                ct.descuentoImporte,
                ct.ivaImporte,
                ct.total,
                ct.fechaCreacion,
                ct.fechaActualizacion
            FROM cotizaciones ct
            JOIN clientes c ON c.idCliente = ct.idCliente
            WHERE ct.idCotizacion = %s
        """, (id_cot,))
        header = cur.fetchone()
        if not header:
            return None

        # Items
        cur.execute("""
            SELECT
                idItem       AS idItem,
                idProducto   AS idProducto,
                nombre, marca, modelo, NoSerie,
                precioUnitario, cantidad
            FROM cotizacion_items
            WHERE idCotizacion = %s
            ORDER BY idItem ASC
        """, (id_cot,))
        items = cur.fetchall()

        # Normalizar Decimals a float para JSON
        for k in ("subtotal", "descuentoImporte", "ivaImporte", "total"):
            if isinstance(header.get(k), Decimal):
                header[k] = float(header[k])

        for it in items:
            if isinstance(it.get("precioUnitario"), Decimal):
                it["precioUnitario"] = float(it["precioUnitario"])

        header["items"] = items
        return header


# ----------------------------
# Endpoints
# ----------------------------

@cotizaciones_bp.route('/cotizaciones', methods=['POST'])
@session_validator(tabla="cotizaciones", accion="create")
def crear_cotizacion():
    """
    Crea cotización con items.
    Body esperado:
    {
      "idCliente": 1,
      "idContacto": null | 5,
      "estatus": "guardada"|"enviada"|"borrador"|"cancelada", (opcional, default guardada)
      "descuentoPorcentaje": 0..100,
      "ivaHabilitado": true|false,
      "ivaPorcentaje": 0..100,
      "items": [
        {"idProducto": 1, "nombre":"...", "marca":"...", "modelo":"...", "NoSerie":"...", "precioUnitario": 123.45, "cantidad": 2},
        ...
      ]
    }
    """
    data = request.get_json(silent=True) or {}
    id_cliente  = data.get("idCliente")
    id_contacto = data.get("idContacto")
    estatus     = data.get("estatus", "guardada")
    items       = data.get("items", [])

    # Parámetros fiscales
    desc_pct    = _to_decimal(data.get("descuentoPorcentaje", "0"))
    iva_enabled = bool(data.get("ivaHabilitado", True))
    iva_pct     = _to_decimal(data.get("ivaPorcentaje", "16"))

    if not id_cliente or not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "idCliente e items son obligatorios"}), 400

    # Calcular totales (backend manda)
    subtotal, desc_imp, iva_imp, total = _calc_totales(items, desc_pct, iva_enabled, iva_pct)

    conn = get_connection()
    try:
        conn.start_transaction()
        with conn.cursor() as cur:
            # Valida cliente (simple)
            cur.execute("SELECT 1 FROM clientes WHERE idCliente = %s", (id_cliente,))
            if not cur.fetchone():
                return jsonify({"error": "Cliente no encontrado"}), 400

            # Valida contacto si viene
            if id_contacto:
                cur.execute("SELECT 1 FROM contacto WHERE idContacto = %s", (id_contacto,))
                if not cur.fetchone():
                    return jsonify({"error": "Contacto no encontrado"}), 400

            # Insert header con folio provisional único
            folio_prov = f"PEND-{uuid.uuid4().hex[:12]}"
            cur.execute("""
                INSERT INTO cotizaciones(
                    folio, fecha, idCliente, idContacto, idUsuario, estatus,
                    descuentoPorcentaje, ivaHabilitado, ivaPorcentaje,
                    subtotal, descuentoImporte, ivaImporte, total
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                folio_prov,
                datetime.now(),
                id_cliente,
                id_contacto,
                g.user_id,  # del validador de sesión
                estatus,
                str(desc_pct), int(iva_enabled), str(iva_pct),
                str(subtotal), str(desc_imp), str(iva_imp), str(total)
            ))
            id_cot = cur.lastrowid

            # Actualiza folio definitivo
            folio_final = _format_folio(id_cot)
            cur.execute("UPDATE cotizaciones SET folio = %s WHERE idCotizacion = %s", (folio_final, id_cot,))

            # Insert items
            for it in items:
                cur.execute("""
                    INSERT INTO cotizacion_items(
                        idCotizacion, idProducto, nombre, marca, modelo, NoSerie,
                        precioUnitario, cantidad
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_cot,
                    it.get("idProducto"),
                    it.get("nombre", ""),
                    it.get("marca", ""),
                    it.get("modelo", ""),
                    it.get("NoSerie"),
                    str(_to_decimal(it.get("precioUnitario"))),
                    int(it.get("cantidad", 1))
                ))

        conn.commit()

        # Auditoría
        registrar_auditoria(
            g.user_id, 'create', 'cotizaciones', id_cot,
            valores_anteriores=None,
            valores_nuevos={
                "idCotizacion": id_cot,
                "folio": folio_final,
                "idCliente": id_cliente,
                "idContacto": id_contacto,
                "idUsuario": g.user_id,
                "estatus": estatus,
                "descuentoPorcentaje": float(desc_pct),
                "ivaHabilitado": iva_enabled,
                "ivaPorcentaje": float(iva_pct),
                "subtotal": float(subtotal),
                "descuentoImporte": float(desc_imp),
                "ivaImporte": float(iva_imp),
                "total": float(total),
                "items": items
            }
        )

        return jsonify({"mensaje": "Cotización creada", "id": id_cot, "folio": folio_final}), 201

    except Exception as e:
        conn.rollback()
        print("Error crear cotización:", e)
        return jsonify({"error": "Error al crear cotización"}), 500
    finally:
        conn.close()


@cotizaciones_bp.route('/cotizaciones', methods=['GET'])
@session_validator(tabla="cotizaciones", accion="read")
def listar_cotizaciones():
    """
    Lista de cotizaciones con filtros/sort/paginación.
    Query params:
      search: filtra por folio o cliente
      status: guardada|enviada|borrador|cancelada|todos (default todos)
      sort: fecha_desc|fecha_asc|folio_asc|folio_desc|cliente_asc|cliente_desc|total_desc|total_asc (default fecha_desc)
      page: 1..n (default 1)
      per_page: (default 10)
    """
    search = (request.args.get('search') or '').strip()
    status = request.args.get('status', 'todos')
    sort = request.args.get('sort', 'fecha_desc')
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = max(1, min(100, int(request.args.get('per_page', 10))))
    except ValueError:
        page, per_page = 1, 10

    where = ["1=1"]
    params = []

    # Filtro status
    if status in ('guardada','enviada','borrador','cancelada'):
        where.append("ct.estatus = %s")
        params.append(status)

    # Filtro búsqueda
    if search:
        # Coincidir por folio o por nombre de cliente (persona o empresa)
        where.append("("
                     "ct.folio LIKE %s OR "
                     "(c.tipoCliente = 'Persona' AND CONCAT(c.nombre,' ',COALESCE(c.apellidoP,''),' ',COALESCE(c.apellidoM,'')) LIKE %s) OR "
                     "(c.tipoCliente <> 'Persona' AND c.nombre LIKE %s)"
                     ")")
        s = f"%{search}%"
        params.extend([s, s, s])

    # Orden
    order = "ct.fecha DESC"
    if sort == 'fecha_asc': order = "ct.fecha ASC"
    elif sort == 'folio_asc': order = "ct.folio ASC"
    elif sort == 'folio_desc': order = "ct.folio DESC"
    elif sort == 'cliente_asc': order = f"{_cliente_nombre_expr()} ASC"
    elif sort == 'cliente_desc': order = f"{_cliente_nombre_expr()} DESC"
    elif sort == 'total_asc': order = "ct.total ASC"
    elif sort == 'total_desc': order = "ct.total DESC"

    offset = (page - 1) * per_page

    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            # Total
            cur.execute(f"""
                SELECT COUNT(*) AS total
                FROM cotizaciones ct
                JOIN clientes c ON c.idCliente = ct.idCliente
                WHERE {' AND '.join(where)}
            """, tuple(params))
            total = cur.fetchone()['total']

            # Datos
            cur.execute(f"""
                SELECT
                    ct.idCotizacion  AS id,
                    ct.folio,
                    ct.fecha,
                    ct.total,
                    ct.estatus,
                    {_cliente_nombre_expr()} AS clienteNombre
                FROM cotizaciones ct
                JOIN clientes c ON c.idCliente = ct.idCliente
                WHERE {' AND '.join(where)}
                ORDER BY {order}
                LIMIT %s OFFSET %s
            """, (*params, per_page, offset))
            rows = cur.fetchall()

            # Normalizar tipos
            for r in rows:
                if isinstance(r.get("total"), Decimal):
                    r["total"] = float(r["total"])

        return jsonify({
            "data": rows,
            "meta": {"page": page, "per_page": per_page, "total": total}
        }), 200

    except Exception as e:
        print("Error listar cotizaciones:", e)
        return jsonify({"error": "Error al listar cotizaciones"}), 500
    finally:
        conn.close()


@cotizaciones_bp.route('/cotizaciones/<int:id_cot>', methods=['GET'])
@session_validator(tabla="cotizaciones", accion="read")
def detalle_cotizacion(id_cot):
    conn = get_connection()
    try:
        data = _fetch_cotizacion(conn, id_cot)
        if not data:
            return jsonify({"error": "Cotización no encontrada"}), 404
        return jsonify(data), 200
    except Exception as e:
        print("Error obtener detalle:", e)
        return jsonify({"error": "Error al obtener cotización"}), 500
    finally:
        conn.close()


# --- reemplaza por esto en actualizar_cotizacion ---
@cotizaciones_bp.route('/cotizaciones/<int:id_cot>', methods=['PUT'])
@session_validator(tabla="cotizaciones", accion="update")
def actualizar_cotizacion(id_cot):
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "items es obligatorio"}), 400

    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            # 1) Lee anterior (SIN start_transaction)
            anterior = _fetch_cotizacion(conn, id_cot)
            if not anterior:
                return jsonify({"error": "Cotización no encontrada"}), 404

            # 2) Calcula totales
            desc_pct    = _to_decimal(data.get("descuentoPorcentaje", anterior["descuentoPorcentaje"]))
            iva_enabled = bool(data.get("ivaHabilitado", anterior["ivaHabilitado"]))
            iva_pct     = _to_decimal(data.get("ivaPorcentaje", anterior["ivaPorcentaje"]))
            estatus     = data.get("estatus", anterior["estatus"])

            subtotal, desc_imp, iva_imp, total = _calc_totales(items, desc_pct, iva_enabled, iva_pct)

            # 3) Actualiza header
            cur.execute("""
                UPDATE cotizaciones
                   SET estatus = %s,
                       descuentoPorcentaje = %s,
                       ivaHabilitado = %s,
                       ivaPorcentaje = %s,
                       subtotal = %s,
                       descuentoImporte = %s,
                       ivaImporte = %s,
                       total = %s
                 WHERE idCotizacion = %s
            """, (estatus, str(desc_pct), int(iva_enabled), str(iva_pct),
                  str(subtotal), str(desc_imp), str(iva_imp), str(total),
                  id_cot))

            # 4) Reemplaza items
            cur.execute("DELETE FROM cotizacion_items WHERE idCotizacion = %s", (id_cot,))
            for it in items:
                cur.execute("""
                    INSERT INTO cotizacion_items(
                        idCotizacion, idProducto, nombre, marca, modelo, NoSerie,
                        precioUnitario, cantidad
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (id_cot, it.get("idProducto"), it.get("nombre", ""), it.get("marca", ""),
                      it.get("modelo", ""), it.get("NoSerie"),
                      str(_to_decimal(it.get("precioUnitario"))), int(it.get("cantidad", 1))))

        conn.commit()

        nuevo = _fetch_cotizacion(conn, id_cot)
        registrar_auditoria(g.user_id, 'update', 'cotizaciones', id_cot,
                            valores_anteriores=anterior, valores_nuevos=nuevo)
        return jsonify({"mensaje": "Cotización actualizada"}), 200

    except Exception as e:
        conn.rollback()
        print("Error actualizar cotización:", e)
        return jsonify({"error": "Error al actualizar cotización"}), 500
    finally:
        conn.close()


# --- reemplaza por esto en eliminar_cotizacion ---
@cotizaciones_bp.route('/cotizaciones/<int:id_cot>', methods=['DELETE'])
@session_validator(tabla="cotizaciones", accion="delete")
def eliminar_cotizacion(id_cot):
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            anterior = _fetch_cotizacion(conn, id_cot)
            if not anterior:
                return jsonify({"error": "Cotización no encontrada"}), 404

            cur.execute("DELETE FROM cotizacion_items WHERE idCotizacion = %s", (id_cot,))
            cur.execute("DELETE FROM cotizaciones WHERE idCotizacion = %s", (id_cot,))

        conn.commit()

        registrar_auditoria(g.user_id, 'delete', 'cotizaciones', id_cot,
                            valores_anteriores=anterior, valores_nuevos=None)
        return jsonify({"mensaje": "Cotización eliminada"}), 200

    except Exception as e:
        conn.rollback()
        print("Error eliminar cotización:", e)
        return jsonify({"error": "Error al eliminar cotización"}), 500
    finally:
        conn.close()



# exportacion pdf

# user_system/cotizaciones.py
from flask import jsonify, request, send_file, render_template, g
from db_config import get_connection
from utils.session_validator import session_validator
from datetime import datetime, timedelta
import pdfkit, io


@cotizaciones_bp.route('/cotizaciones/<int:id_cotizacion>/pdf', methods=['GET'])
@session_validator(tabla="cotizaciones", accion="read")
def exportar_cotizacion_pdf(id_cotizacion):
    dias_validez = int(request.args.get('dias', 7))

    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT 
                    c.*,
                    u.nombre       AS asesor_nombre,
                    u.apellidop    AS asesor_apellidop,
                    u.apellidom    AS asesor_apellidom,
                    u.telefono     AS asesor_telefono,
                    u.email        AS asesor_email,
                    cl.tipoCliente,
                    cl.nombre      AS cli_nombre,
                    cl.apellidoP   AS cli_apellidoP,
                    cl.apellidoM   AS cli_apellidoM,
                    cl.rfc         AS cli_rfc,
                    cl.telefono    AS cli_telefono,
                    cl.email       AS cli_email,
                    cl.direccion   AS cli_direccion
                FROM cotizaciones c
                JOIN usuarios  u  ON u.idUsuario  = c.idUsuario
                JOIN clientes  cl ON cl.idCliente = c.idCliente
                WHERE c.idCotizacion = %s
            """, (id_cotizacion,))
            cot = cursor.fetchone()
            if not cot:
                return jsonify({'error': 'Cotización no encontrada'}), 404

            cursor.execute("""
                SELECT nombre, marca, modelo, precioUnitario, cantidad
                FROM cotizacion_items
                WHERE idCotizacion = %s
            """, (id_cotizacion,))
            items = cursor.fetchall()

        # Fechas
        fecha_dt = cot['fecha'] if isinstance(cot['fecha'], datetime) else datetime.fromisoformat(str(cot['fecha']))
        valido_hasta_dt = fecha_dt + timedelta(days=dias_validez)

        # Nombres
        asesor_nombre_completo = " ".join([x for x in [
            cot.get('asesor_nombre'), cot.get('asesor_apellidop'), cot.get('asesor_apellidom')
        ] if x])

        if cot['tipoCliente'] == 'Persona':
            cliente_nombre = " ".join([x for x in [
                cot.get('cli_nombre'), cot.get('cli_apellidoP'), cot.get('cli_apellidoM')
            ] if x])
        else:
            cliente_nombre = cot.get('cli_nombre')

        def money(v):
            try: return f"{float(v):,.2f}"
            except Exception: return str(v)

        # OJO: usa los nombres REALES de tus columnas
        html = render_template(
            "cotizaciones/cotizacion_formato.html",
            titulo=f"COTIZACIÓN {cot['folio']}",
            fecha=fecha_dt.strftime("%d/%m/%Y"),
            folio=cot['folio'],
            valido_hasta=valido_hasta_dt.strftime("%d/%m/%Y"),

            # Asesor
            asesor_nombre=asesor_nombre_completo,
            asesor_telefono=cot.get('asesor_telefono'),
            asesor_email=cot.get('asesor_email'),

            # Cliente
            cliente_nombre=cliente_nombre,
            cliente_rfc=cot.get('cli_rfc'),
            cliente_direccion=cot.get('cli_direccion'),
            cliente_telefono=cot.get('cli_telefono'),
            cliente_email=cot.get('cli_email'),

            # Items / totales (nombres corregidos)
            items=items,
            subtotal=cot['subtotal'],
            descuento_porcentaje=cot['descuentoPorcentaje'],
            descuento_monto=cot['descuentoImporte'],        # <-- antes: descuentoMonto
            iva_aplica=bool(cot['ivaHabilitado']),          # <-- antes: ivaAplica
            iva_porcentaje=cot['ivaPorcentaje'],
            iva_monto=cot['ivaImporte'],                    # <-- antes: ivaMonto
            total=cot['total'],
            money=money
        )

        config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
        pdf = pdfkit.from_string(html, False, configuration=config)

        return send_file(
            io.BytesIO(pdf),
            as_attachment=True,
            download_name=f"cotizacion_{cot['folio']}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        print("Error al generar PDF de cotización:", e)
        return jsonify({'error': 'Error generando PDF'}), 500
    finally:
        conn.close()
