from datetime import datetime
from database.db import conectar, _sql


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
            fecha TEXT,
            operario TEXT,
            centro TEXT,
            material TEXT,
            cantidad REAL,
            prioridad TEXT,
            estado TEXT,
            observaciones TEXT,
            fecha_preparado TEXT,
            fecha_entrega TEXT
        )
    """))

    conn.commit()
    conn.close()


def crear_pedido_material(operario, centro, material, cantidad, prioridad, observaciones=""):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        INSERT INTO pedidos_material
        (fecha, operario, centro, material, cantidad, prioridad, estado, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """), (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        operario,
        centro,
        material,
        cantidad,
        prioridad,
        "Pendiente",
        observaciones
    ))

    conn.commit()
    conn.close()


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
