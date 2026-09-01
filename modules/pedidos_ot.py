from datetime import datetime

from database.db import conectar, _sql


_ESTRUCTURA_PEDIDOS_OT_ASEGURADA = False


def _es_postgres_conn(conn):
    modulo = conn.__class__.__module__.lower()
    return "psycopg2" in modulo or "postgres" in modulo


def _id_sql(conn):
    if _es_postgres_conn(conn):
        return "SERIAL PRIMARY KEY"
    return "INTEGER PRIMARY KEY AUTOINCREMENT"


def crear_tabla_pedidos_ot():
    """
    Relación no destructiva entre pedidos de material y OT.

    No modifica la tabla histórica pedidos_material.
    Los pedidos normales siguen funcionando sin OT asociada.
    """
    global _ESTRUCTURA_PEDIDOS_OT_ASEGURADA

    if _ESTRUCTURA_PEDIDOS_OT_ASEGURADA:
        return

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql(f"""
            CREATE TABLE IF NOT EXISTS pedidos_material_ot (
                id {_id_sql(conn)},
                pedido_id INTEGER NOT NULL,
                id_orden INTEGER,
                numero_ot TEXT NOT NULL,
                centro TEXT,
                edificio TEXT,
                planta TEXT,
                espacio TEXT,
                descripcion_ot TEXT,
                fecha_vinculo TEXT
            )
        """))

        indices = [
            (
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "idx_pedidos_material_ot_pedido "
                "ON pedidos_material_ot(pedido_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_pedidos_material_ot_numero "
                "ON pedidos_material_ot(numero_ot)"
            ),
        ]

        for sql_indice in indices:
            try:
                cur.execute(sql_indice)
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        conn.commit()
        _ESTRUCTURA_PEDIDOS_OT_ASEGURADA = True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def vincular_pedido_a_ot(
    pedido_id,
    numero_ot,
    id_orden=None,
    centro="",
    edificio="",
    planta="",
    espacio="",
    descripcion_ot="",
):
    crear_tabla_pedidos_ot()

    pedido_id = int(pedido_id)
    numero_ot = str(numero_ot or "").strip()

    if not pedido_id or not numero_ot:
        return False

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id
            FROM pedidos_material_ot
            WHERE pedido_id = ?
        """), (
            pedido_id,
        ))

        existente = cur.fetchone()

        valores = (
            id_orden,
            numero_ot,
            str(centro or "").strip(),
            str(edificio or "").strip(),
            str(planta or "").strip(),
            str(espacio or "").strip(),
            str(descripcion_ot or "").strip(),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        if existente:
            cur.execute(_sql("""
                UPDATE pedidos_material_ot
                SET id_orden = ?,
                    numero_ot = ?,
                    centro = ?,
                    edificio = ?,
                    planta = ?,
                    espacio = ?,
                    descripcion_ot = ?,
                    fecha_vinculo = ?
                WHERE pedido_id = ?
            """), valores + (pedido_id,))

        else:
            cur.execute(_sql("""
                INSERT INTO pedidos_material_ot
                (
                    id_orden,
                    numero_ot,
                    centro,
                    edificio,
                    planta,
                    espacio,
                    descripcion_ot,
                    fecha_vinculo,
                    pedido_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), valores + (pedido_id,))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def obtener_ot_de_pedido(pedido_id):
    crear_tabla_pedidos_ot()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                pedido_id,
                id_orden,
                numero_ot,
                centro,
                edificio,
                planta,
                espacio,
                descripcion_ot,
                fecha_vinculo
            FROM pedidos_material_ot
            WHERE pedido_id = ?
            LIMIT 1
        """), (
            int(pedido_id),
        ))

        fila = cur.fetchone()

        if not fila:
            return None

        return {
            "pedido_id": fila[0],
            "id_orden": fila[1],
            "numero_ot": fila[2] or "",
            "centro": fila[3] or "",
            "edificio": fila[4] or "",
            "planta": fila[5] or "",
            "espacio": fila[6] or "",
            "descripcion_ot": fila[7] or "",
            "fecha_vinculo": fila[8] or "",
        }

    finally:
        conn.close()



def obtener_mapa_ot_pedidos(ids_pedido):
    """
    Recupera en una sola consulta las OT vinculadas a una lista de pedidos.
    Evita una consulta por tarjeta en la pantalla de Abel.
    """
    crear_tabla_pedidos_ot()

    ids = []

    for valor in ids_pedido or []:
        try:
            ids.append(int(valor))
        except Exception:
            continue

    if not ids:
        return {}

    marcadores = ",".join(
        ["?"] * len(ids)
    )

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(
            _sql(f"""
                SELECT
                    pedido_id,
                    id_orden,
                    numero_ot,
                    centro,
                    edificio,
                    planta,
                    espacio,
                    descripcion_ot,
                    fecha_vinculo
                FROM pedidos_material_ot
                WHERE pedido_id IN ({marcadores})
            """),
            tuple(ids),
        )

        resultado = {}

        for fila in cur.fetchall():
            resultado[int(fila[0])] = {
                "pedido_id": fila[0],
                "id_orden": fila[1],
                "numero_ot": fila[2] or "",
                "centro": fila[3] or "",
                "edificio": fila[4] or "",
                "planta": fila[5] or "",
                "espacio": fila[6] or "",
                "descripcion_ot": fila[7] or "",
                "fecha_vinculo": fila[8] or "",
            }

        return resultado

    finally:
        conn.close()

def obtener_pedidos_de_ot(numero_ot, solo_activos=False):
    crear_tabla_pedidos_ot()

    numero_ot = str(numero_ot or "").strip()

    if not numero_ot:
        return []

    conn = conectar()
    cur = conn.cursor()

    query = """
        SELECT
            p.id,
            p.numero_pedido,
            p.estado,
            p.fecha,
            p.prioridad
        FROM pedidos_material p
        INNER JOIN pedidos_material_ot po
            ON po.pedido_id = p.id
        WHERE po.numero_ot = ?
    """

    params = [numero_ot]

    if solo_activos:
        query += (
            " AND p.estado IN "
            "('Pendiente', 'Preparado', 'Sin stock')"
        )

    query += " ORDER BY p.id DESC"

    try:
        cur.execute(
            _sql(query),
            tuple(params),
        )
        return cur.fetchall()

    finally:
        conn.close()
