from datetime import datetime
from database.db import conectar, _sql


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def crear_tabla_activos():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS activos (
            id SERIAL PRIMARY KEY,
            id_inventario INTEGER,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            elemento TEXT,
            fabricante TEXT,
            modelo TEXT,
            numero_serie TEXT,
            fecha_instalacion TEXT,
            proveedor TEXT,
            vida_util_anios INTEGER DEFAULT 0,
            coste_estimado REAL DEFAULT 0,
            garantia_hasta TEXT,
            manual_pdf TEXT,
            observaciones TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
        )
    """))

    for columna, tipo in [
        ("id_inventario", "INTEGER"),
        ("centro", "TEXT"),
        ("edificio", "TEXT"),
        ("espacio", "TEXT"),
        ("elemento", "TEXT"),
        ("fabricante", "TEXT"),
        ("modelo", "TEXT"),
        ("numero_serie", "TEXT"),
        ("fecha_instalacion", "TEXT"),
        ("proveedor", "TEXT"),
        ("vida_util_anios", "INTEGER DEFAULT 0"),
        ("coste_estimado", "REAL DEFAULT 0"),
        ("garantia_hasta", "TEXT"),
        ("manual_pdf", "TEXT"),
        ("observaciones", "TEXT"),
        ("fecha_creacion", "TEXT"),
        ("fecha_actualizacion", "TEXT"),
    ]:
        try:
            cur.execute(_sql(f"""
                ALTER TABLE activos
                ADD COLUMN IF NOT EXISTS {columna} {tipo}
            """))
        except Exception:
            pass

    conn.commit()
    conn.close()


def obtener_activo_por_inventario(id_inventario):
    crear_tabla_activos()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                id,
                id_inventario,
                centro,
                edificio,
                espacio,
                elemento,
                fabricante,
                modelo,
                numero_serie,
                fecha_instalacion,
                proveedor,
                vida_util_anios,
                coste_estimado,
                garantia_hasta,
                manual_pdf,
                observaciones,
                fecha_creacion,
                fecha_actualizacion
            FROM activos
            WHERE id_inventario = ?
            ORDER BY id DESC
            LIMIT 1
        """), (id_inventario,))

        fila = cur.fetchone()

    except Exception:
        fila = None

    conn.close()
    return fila


def guardar_o_actualizar_activo(
    id_inventario,
    centro,
    edificio,
    espacio,
    elemento,
    fabricante="",
    modelo="",
    numero_serie="",
    fecha_instalacion="",
    proveedor="",
    vida_util_anios=0,
    coste_estimado=0,
    garantia_hasta="",
    manual_pdf="",
    observaciones=""
):
    crear_tabla_activos()

    try:
        vida_util_anios = int(vida_util_anios or 0)
    except Exception:
        vida_util_anios = 0

    try:
        coste_estimado = float(coste_estimado or 0)
    except Exception:
        coste_estimado = 0

    existente = obtener_activo_por_inventario(id_inventario)

    conn = conectar()
    cur = conn.cursor()

    try:
        if existente:
            cur.execute(_sql("""
                UPDATE activos
                SET centro = ?,
                    edificio = ?,
                    espacio = ?,
                    elemento = ?,
                    fabricante = ?,
                    modelo = ?,
                    numero_serie = ?,
                    fecha_instalacion = ?,
                    proveedor = ?,
                    vida_util_anios = ?,
                    coste_estimado = ?,
                    garantia_hasta = ?,
                    manual_pdf = ?,
                    observaciones = ?,
                    fecha_actualizacion = ?
                WHERE id_inventario = ?
            """), (
                centro,
                edificio,
                espacio,
                elemento,
                fabricante,
                modelo,
                numero_serie,
                fecha_instalacion,
                proveedor,
                vida_util_anios,
                coste_estimado,
                garantia_hasta,
                manual_pdf,
                observaciones,
                ahora(),
                id_inventario
            ))
        else:
            cur.execute(_sql("""
                INSERT INTO activos (
                    id_inventario,
                    centro,
                    edificio,
                    espacio,
                    elemento,
                    fabricante,
                    modelo,
                    numero_serie,
                    fecha_instalacion,
                    proveedor,
                    vida_util_anios,
                    coste_estimado,
                    garantia_hasta,
                    manual_pdf,
                    observaciones,
                    fecha_creacion,
                    fecha_actualizacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), (
                id_inventario,
                centro,
                edificio,
                espacio,
                elemento,
                fabricante,
                modelo,
                numero_serie,
                fecha_instalacion,
                proveedor,
                vida_util_anios,
                coste_estimado,
                garantia_hasta,
                manual_pdf,
                observaciones,
                ahora(),
                ahora()
            ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()
