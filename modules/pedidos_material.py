from datetime import datetime
from database.db import conectar, _sql
from modules.ordenes import guardar_foto_ot


ESTADOS_PEDIDO = [
    "Pendiente",
    "Preparado",
    "Entregado",
    "Sin stock",
    "Cancelado"
]


def _es_postgres_conn(conn):
    modulo = conn.__class__.__module__.lower()
    return "psycopg2" in modulo or "postgres" in modulo


def _id_sql(conn):
    return "SERIAL PRIMARY KEY" if _es_postgres_conn(conn) else "INTEGER PRIMARY KEY AUTOINCREMENT"


def _add_column(cur, tabla, columna, tipo):
    try:
        cur.execute(_sql(f"""
            ALTER TABLE {tabla}
            ADD COLUMN {columna} {tipo}
        """))
    except Exception:
        pass


def crear_tabla_pedidos_material():
    conn = conectar()
    cur = conn.cursor()

    id_sql = _id_sql(conn)

    # CABECERA DEL PEDIDO
    cur.execute(_sql(f"""
        CREATE TABLE IF NOT EXISTS pedidos_material (
            id {id_sql},
            numero_pedido TEXT,
            fecha TEXT,
            operario TEXT,
            centro TEXT,
            edificio TEXT,
            prioridad TEXT,
            estado TEXT,
            observaciones TEXT,
            link_material TEXT,
            foto TEXT,
            fecha_preparado TEXT,
            fecha_entrega TEXT
        )
    """))

    # Por compatibilidad con pedidos antiguos
    columnas_cabecera = [
        ("numero_pedido", "TEXT"),
        ("fecha", "TEXT"),
        ("operario", "TEXT"),
        ("centro", "TEXT"),
        ("edificio", "TEXT"),
        ("material", "TEXT"),
        ("cantidad", "REAL"),
        ("prioridad", "TEXT"),
        ("estado", "TEXT"),
        ("observaciones", "TEXT"),
        ("link_material", "TEXT"),
        ("foto", "TEXT"),
        ("fecha_preparado", "TEXT"),
        ("fecha_entrega", "TEXT"),
    ]

    for columna, tipo in columnas_cabecera:
        _add_column(cur, "pedidos_material", columna, tipo)

    # LÍNEAS DEL PEDIDO
    cur.execute(_sql(f"""
        CREATE TABLE IF NOT EXISTS pedidos_material_lineas (
            id {id_sql},
            pedido_id INTEGER,
            codigo_material TEXT,
            material TEXT,
            cantidad REAL,
            estado TEXT,
            observaciones TEXT,
            link_material TEXT,
            fecha_preparado TEXT,
            fecha_entrega TEXT
        )
    """))

    columnas_lineas = [
        ("pedido_id", "INTEGER"),
        ("codigo_material", "TEXT"),
        ("material", "TEXT"),
        ("cantidad", "REAL"),
        ("estado", "TEXT"),
        ("observaciones", "TEXT"),
        ("link_material", "TEXT"),
        ("fecha_preparado", "TEXT"),
        ("fecha_entrega", "TEXT"),
    ]

    for columna, tipo in columnas_lineas:
        _add_column(cur, "pedidos_material_lineas", columna, tipo)

    conn.commit()
    conn.close()

    migrar_pedidos_antiguos_a_lineas()


def formatear_numero_pedido(id_pedido):
    return f"PED-MAT-{int(id_pedido):04d}"


def migrar_pedidos_antiguos_a_lineas():
    """
    Si ya tenías pedidos antiguos con un solo material,
    los pasa automáticamente a pedidos_material_lineas.
    No borra nada.
    """
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id, material, cantidad, estado, observaciones, link_material
            FROM pedidos_material
            WHERE material IS NOT NULL
            AND material <> ''
        """))

        pedidos = cur.fetchall()

        for p in pedidos:
            pedido_id = p[0]
            material = p[1]
            cantidad = p[2]
            estado = p[3] or "Pendiente"
            observaciones = p[4] or ""
            link_material = p[5] or ""

            cur.execute(_sql("""
                SELECT COUNT(*)
                FROM pedidos_material_lineas
                WHERE pedido_id = ?
            """), (pedido_id,))

            existe = cur.fetchone()[0]

            if existe == 0:
                cur.execute(_sql("""
                    INSERT INTO pedidos_material_lineas
                    (pedido_id, material, cantidad, estado, observaciones, link_material)
                    VALUES (?, ?, ?, ?, ?, ?)
                """), (
                    pedido_id,
                    material,
                    cantidad,
                    estado,
                    observaciones,
                    link_material
                ))

        conn.commit()

    except Exception:
        pass

    conn.close()


def crear_pedido_material_multiple(
    operario,
    centro,
    edificio="",
    prioridad="Media",
    observaciones="",
    lineas=None,
    foto="postgres_fotos"
):
    """
    lineas debe ser una lista de diccionarios:
    [
        {
            "codigo_material": "",
            "material": "Tubo PVC 32",
            "cantidad": 2,
            "observaciones": "",
            "link_material": ""
        }
    ]
    """

    crear_tabla_pedidos_material()

    if not lineas:
        return None

    conn = conectar()
    cur = conn.cursor()

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    if _es_postgres_conn(conn):
        cur.execute(_sql("""
            INSERT INTO pedidos_material
            (fecha, operario, centro, edificio, prioridad, estado, observaciones, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """), (
            fecha,
            operario,
            centro,
            edificio,
            prioridad,
            "Pendiente",
            observaciones,
            foto
        ))

        fila = cur.fetchone()
        id_pedido = fila[0] if fila else None

    else:
        cur.execute(_sql("""
            INSERT INTO pedidos_material
            (fecha, operario, centro, edificio, prioridad, estado, observaciones, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (
            fecha,
            operario,
            centro,
            edificio,
            prioridad,
            "Pendiente",
            observaciones,
            foto
        ))

        id_pedido = cur.lastrowid

    if not id_pedido:
        conn.close()
        return None

    numero_pedido = formatear_numero_pedido(id_pedido)

    cur.execute(_sql("""
        UPDATE pedidos_material
        SET numero_pedido = ?
        WHERE id = ?
    """), (
        numero_pedido,
        id_pedido
    ))

    for linea in lineas:
        material = str(linea.get("material", "")).strip()

        if not material:
            continue

        cantidad = linea.get("cantidad", 1)
        codigo_material = linea.get("codigo_material", "")
        obs_linea = linea.get("observaciones", "")
        link_material = linea.get("link_material", "")

        cur.execute(_sql("""
            INSERT INTO pedidos_material_lineas
            (pedido_id, codigo_material, material, cantidad, estado, observaciones, link_material)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (
            id_pedido,
            codigo_material,
            material,
            cantidad,
            "Pendiente",
            obs_linea,
            link_material
        ))

    conn.commit()
    conn.close()

    return id_pedido


def crear_pedido_material(
    operario,
    centro,
    material,
    cantidad,
    prioridad,
    observaciones="",
    link_material="",
    foto="postgres_fotos"
):
    """
    Función antigua.
    Se mantiene para que no se rompa nada.
    Ahora crea un pedido con una sola línea.
    """

    return crear_pedido_material_multiple(
        operario=operario,
        centro=centro,
        edificio="",
        prioridad=prioridad,
        observaciones=observaciones,
        foto=foto,
        lineas=[
            {
                "codigo_material": "",
                "material": material,
                "cantidad": cantidad,
                "observaciones": observaciones,
                "link_material": link_material
            }
        ]
    )


def obtener_numero_pedido(id_pedido):
    if not id_pedido:
        return ""

    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT numero_pedido
        FROM pedidos_material
        WHERE id = ?
    """), (id_pedido,))

    fila = cur.fetchone()
    conn.close()

    if fila and fila[0]:
        return fila[0]

    return formatear_numero_pedido(id_pedido)


def guardar_fotos_pedido_material(id_pedido, fotos):
    if not id_pedido or not fotos:
        return

    numero_pedido = obtener_numero_pedido(id_pedido)

    if not numero_pedido:
        return

    for i, foto in enumerate(fotos, start=1):
        try:
            foto_bytes = foto.read()
            nombre_foto = f"{numero_pedido}_{i}_{foto.name}"

            guardar_foto_ot(
                numero_ot=numero_pedido,
                nombre_foto=nombre_foto,
                foto_data=foto_bytes
            )

        except Exception:
            pass


def obtener_lineas_pedido(id_pedido):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT
            id,
            pedido_id,
            codigo_material,
            material,
            cantidad,
            estado,
            observaciones,
            link_material,
            fecha_preparado,
            fecha_entrega
        FROM pedidos_material_lineas
        WHERE pedido_id = ?
        ORDER BY id ASC
    """), (id_pedido,))

    datos = cur.fetchall()
    conn.close()

    return datos


def obtener_resumen_materiales_pedido(id_pedido):
    lineas = obtener_lineas_pedido(id_pedido)

    materiales = []

    for l in lineas:
        material = l[3]
        cantidad = l[4]
        materiales.append(f"{material} x {cantidad}")

    return " | ".join(materiales)


def obtener_pedidos_material(operario=None, solo_pendientes=False):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    query = """
        SELECT
            id,
            numero_pedido,
            fecha,
            operario,
            centro,
            prioridad,
            estado,
            observaciones,
            link_material,
            foto,
            fecha_preparado,
            fecha_entrega,
            edificio
        FROM pedidos_material
        WHERE 1=1
    """

    params = []

    if operario:
        query += " AND operario = ?"
        params.append(operario)

    if solo_pendientes:
        query += " AND estado IN ('Pendiente', 'Preparado', 'Sin stock')"

    query += " ORDER BY id DESC"

    cur.execute(_sql(query), params)
    pedidos = cur.fetchall()
    conn.close()

    resultado = []

    for p in pedidos:
        id_pedido = p[0]
        resumen_materiales = obtener_resumen_materiales_pedido(id_pedido)

        # Devuelve formato parecido al antiguo para no romper la pantalla:
        resultado.append((
            p[0],                    # id
            p[1],                    # numero_pedido
            p[2],                    # fecha
            p[3],                    # operario
            p[4],                    # centro
            resumen_materiales,      # material/resumen
            "",                      # cantidad antigua
            p[5],                    # prioridad
            p[6],                    # estado
            p[7],                    # observaciones
            p[8],                    # link_material
            p[9],                    # foto
            p[10],                   # fecha_preparado
            p[11],                   # fecha_entrega
        ))

    return resultado


def recalcular_estado_pedido(id_pedido):
    """
    Calcula el estado general según las líneas.
    """

    lineas = obtener_lineas_pedido(id_pedido)

    if not lineas:
        return

    estados = [l[5] for l in lineas]

    if all(e == "Entregado" for e in estados):
        nuevo_estado = "Entregado"
    elif all(e == "Cancelado" for e in estados):
        nuevo_estado = "Cancelado"
    elif any(e == "Preparado" for e in estados):
        nuevo_estado = "Preparado"
    elif any(e == "Sin stock" for e in estados):
        nuevo_estado = "Sin stock"
    else:
        nuevo_estado = "Pendiente"

    conn = conectar()
    cur = conn.cursor()

    if nuevo_estado == "Preparado":
        cur.execute(_sql("""
            UPDATE pedidos_material
            SET estado = ?, fecha_preparado = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            id_pedido
        ))

    elif nuevo_estado == "Entregado":
        cur.execute(_sql("""
            UPDATE pedidos_material
            SET estado = ?, fecha_entrega = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            id_pedido
        ))

    else:
        cur.execute(_sql("""
            UPDATE pedidos_material
            SET estado = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            id_pedido
        ))

    conn.commit()
    conn.close()


def cambiar_estado_linea_pedido(id_linea, nuevo_estado):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT pedido_id
        FROM pedidos_material_lineas
        WHERE id = ?
    """), (id_linea,))

    fila = cur.fetchone()

    if not fila:
        conn.close()
        return False

    pedido_id = fila[0]

    if nuevo_estado == "Preparado":
        cur.execute(_sql("""
            UPDATE pedidos_material_lineas
            SET estado = ?, fecha_preparado = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            id_linea
        ))

    elif nuevo_estado == "Entregado":
        cur.execute(_sql("""
            UPDATE pedidos_material_lineas
            SET estado = ?, fecha_entrega = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            id_linea
        ))

    else:
        cur.execute(_sql("""
            UPDATE pedidos_material_lineas
            SET estado = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            id_linea
        ))

    conn.commit()
    conn.close()

    recalcular_estado_pedido(pedido_id)

    return True


def cambiar_estado_pedido(id_pedido, nuevo_estado):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    if nuevo_estado == "Preparado":
        cur.execute(_sql("""
            UPDATE pedidos_material
            SET estado = ?, fecha_preparado = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            id_pedido
        ))

        cur.execute(_sql("""
            UPDATE pedidos_material_lineas
            SET estado = ?, fecha_preparado = ?
            WHERE pedido_id = ?
        """), (
            nuevo_estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            id_pedido
        ))

    elif nuevo_estado == "Entregado":
        cur.execute(_sql("""
            UPDATE pedidos_material
            SET estado = ?, fecha_entrega = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            id_pedido
        ))

        cur.execute(_sql("""
            UPDATE pedidos_material_lineas
            SET estado = ?, fecha_entrega = ?
            WHERE pedido_id = ?
        """), (
            nuevo_estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            id_pedido
        ))

    else:
        cur.execute(_sql("""
            UPDATE pedidos_material
            SET estado = ?
            WHERE id = ?
        """), (
            nuevo_estado,
            id_pedido
        ))

        cur.execute(_sql("""
            UPDATE pedidos_material_lineas
            SET estado = ?
            WHERE pedido_id = ?
        """), (
            nuevo_estado,
            id_pedido
        ))

    conn.commit()
    conn.close()


def borrar_pedido_material(id_pedido):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        DELETE FROM pedidos_material_lineas
        WHERE pedido_id = ?
    """), (id_pedido,))

    cur.execute(_sql("""
        DELETE FROM pedidos_material
        WHERE id = ?
    """), (id_pedido,))

    conn.commit()
    conn.close()

    return True
