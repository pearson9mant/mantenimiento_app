from datetime import datetime
from database.db import conectar, _sql


def crear_tabla_espacios_historial():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS espacios_historial (
            id SERIAL PRIMARY KEY,
            fecha TEXT,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            elemento TEXT,
            tipo TEXT,
            numero_ot TEXT,
            descripcion TEXT,
            area TEXT,
            estado TEXT,
            operario TEXT,
            observaciones TEXT
        )
    """))

    conn.commit()
    conn.close()


def registrar_historial_espacio(
    centro="",
    edificio="",
    espacio="",
    elemento="",
    tipo="OT",
    numero_ot="",
    descripcion="",
    area="",
    estado="",
    operario="",
    observaciones=""
):
    crear_tabla_espacios_historial()

    if not str(espacio or "").strip():
        return False

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        INSERT INTO espacios_historial (
            fecha,
            centro,
            edificio,
            espacio,
            elemento,
            tipo,
            numero_ot,
            descripcion,
            area,
            estado,
            operario,
            observaciones
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """), (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        centro,
        edificio,
        espacio,
        elemento,
        tipo,
        numero_ot,
        descripcion,
        area,
        estado,
        operario,
        observaciones
    ))

    conn.commit()
    conn.close()

    return True


def obtener_historial_espacios(centro="", edificio="", espacio=""):
    crear_tabla_espacios_historial()

    conn = conectar()
    cur = conn.cursor()

    sql = """
        SELECT id, fecha, centro, edificio, espacio, elemento,
               tipo, numero_ot, descripcion, area, estado,
               operario, observaciones
        FROM espacios_historial
        WHERE 1 = 1
    """

    params = []

    if centro:
        sql += " AND centro = ?"
        params.append(centro)

    if edificio:
        sql += " AND edificio = ?"
        params.append(edificio)

    if espacio:
        sql += " AND espacio = ?"
        params.append(espacio)

    sql += " ORDER BY id DESC"

    cur.execute(_sql(sql), tuple(params))

    datos = cur.fetchall()
    conn.close()

    return datos
