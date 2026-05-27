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


def crear_tabla_pedidos_material():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS pedidos_material (
            id SERIAL PRIMARY KEY,
            numero_pedido TEXT,
            fecha TEXT,
            operario TEXT,
            centro TEXT,
            material TEXT,
            cantidad REAL,
            prioridad TEXT,
            estado TEXT,
            observaciones TEXT,
            link_material TEXT,
            foto TEXT,
            fecha_preparado TEXT,
            fecha_entrega TEXT
        )
    """))

    conn.commit()

    for columna, tipo in [
        ("numero_pedido", "TEXT"),
        ("link_material", "TEXT"),
        ("foto", "TEXT"),
        ("fecha_preparado", "TEXT"),
        ("fecha_entrega", "TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE pedidos_material ADD COLUMN {columna} {tipo}")
            conn.commit()
        except Exception:
            pass

    conn.close()


def formatear_numero_pedido(id_pedido):
    return f"PED-MAT-{int(id_pedido):04d}"


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
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    modulo = conn.__class__.__module__.lower()
    es_postgres = "psycopg2" in modulo or "postgres" in modulo

    if es_postgres:
        cur.execute(_sql("""
            INSERT INTO pedidos_material
            (fecha, operario, centro, material, cantidad, prioridad, estado, observaciones, link_material, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """), (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            operario,
            centro,
            material,
            cantidad,
            prioridad,
            "Pendiente",
            observaciones,
            link_material,
            foto
        ))

        fila = cur.fetchone()
        id_pedido = fila[0] if fila else None

    else:
        cur.execute(_sql("""
            INSERT INTO pedidos_material
            (fecha, operario, centro, material, cantidad, prioridad, estado, observaciones, link_material, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            operario,
            centro,
            material,
            cantidad,
            prioridad,
            "Pendiente",
            observaciones,
            link_material,
            foto
        ))

        id_pedido = cur.lastrowid

    numero_pedido = ""

    if id_pedido:
        numero_pedido = formatear_numero_pedido(id_pedido)

        cur.execute(_sql("""
            UPDATE pedidos_material
            SET numero_pedido = ?
            WHERE id = ?
        """), (
            numero_pedido,
            id_pedido
        ))

    conn.commit()
    conn.close()

    return id_pedido


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


def obtener_pedidos_material(operario=None, solo_pendientes=False):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    query = "SELECT * FROM pedidos_material WHERE 1=1"
    params = []

    if operario:
        query += " AND operario = ?"
        params.append(operario)

    if solo_pendientes:
        query += " AND estado IN ('Pendiente', 'Preparado', 'Sin stock')"

    query += " ORDER BY id DESC"

    cur.execute(_sql(query), params)
    datos = cur.fetchall()

    conn.close()
    return datos


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


def borrar_pedido_material(id_pedido):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        DELETE FROM pedidos_material
        WHERE id = ?
    """), (id_pedido,))

    conn.commit()
    conn.close()

    return True
