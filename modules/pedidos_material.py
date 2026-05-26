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
            fecha TEXT,
            operario TEXT,
            centro TEXT,
            material TEXT,
            cantidad REAL,
            prioridad TEXT,
            estado TEXT,
            observaciones TEXT,
            foto TEXT,
            fecha_preparado TEXT,
            fecha_entrega TEXT
        )
    """))

    conn.commit()

    # Por si la tabla ya existía antes sin la columna foto
    try:
        cur.execute(_sql("""
            ALTER TABLE pedidos_material
            ADD COLUMN foto TEXT
        """))
        conn.commit()
    except Exception:
        pass

    conn.close()


def crear_pedido_material(
    operario,
    centro,
    material,
    cantidad,
    prioridad,
    observaciones="",
    foto="postgres_fotos"
):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        INSERT INTO pedidos_material
        (fecha, operario, centro, material, cantidad, prioridad, estado, observaciones, foto)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """), (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        operario,
        centro,
        material,
        cantidad,
        prioridad,
        "Pendiente",
        observaciones,
        foto
    ))

    id_pedido = None

    try:
        id_pedido = cur.lastrowid
    except Exception:
        pass

    conn.commit()

    if not id_pedido:
        try:
            cur.execute(_sql("""
                SELECT id
                FROM pedidos_material
                WHERE operario = ?
                  AND centro = ?
                  AND material = ?
                  AND cantidad = ?
                  AND prioridad = ?
                ORDER BY id DESC
                LIMIT 1
            """), (
                operario,
                centro,
                material,
                cantidad,
                prioridad
            ))

            fila = cur.fetchone()

            if fila:
                id_pedido = fila[0]

        except Exception:
            id_pedido = None

    conn.close()
    return id_pedido


def guardar_fotos_pedido_material(id_pedido, fotos):
    if not id_pedido or not fotos:
        return

    referencia_pedido = f"PEDIDO-MATERIAL-{id_pedido}"

    for i, foto in enumerate(fotos, start=1):
        try:
            foto_bytes = foto.read()
            nombre_foto = f"{referencia_pedido}_{i}_{foto.name}"

            guardar_foto_ot(
                numero_ot=referencia_pedido,
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
