from database.db import conectar, _sql


def _normalizar_comparacion(texto):
    return (
        str(texto or "")
        .lower()
        .replace("edif.", "")
        .replace("edificio", "")
        .replace(" ", "")
        .replace("·", "")
        .strip()
    )


def obtener_actuaciones_espacio(centro, edificio, espacio):
    conn = conectar()
    cur = conn.cursor()

    datos = []

    try:
        cur.execute(_sql("""
            SELECT id, numero_ot, descripcion, estado, prioridad,
                   operario, origen, area, fecha_creacion,
                   centro, edificio, espacio
            FROM ordenes_trabajo
            WHERE TRIM(LOWER(COALESCE(estado, ''))) NOT IN (
                    'finalizada',
                    'cerrado',
                    'cerrada',
                    'cancelada'
              )
            ORDER BY id DESC
        """))

        filas = cur.fetchall()

        centro_obj = _normalizar_comparacion(centro)
        edificio_obj = _normalizar_comparacion(edificio)
        espacio_obj = _normalizar_comparacion(espacio)

        for fila in filas:
            (
                id_ot,
                numero_ot,
                descripcion,
                estado,
                prioridad,
                operario,
                origen,
                area,
                fecha_creacion,
                centro_ot,
                edificio_ot,
                espacio_ot,
            ) = fila

            if (
                _normalizar_comparacion(centro_ot) == centro_obj
                and _normalizar_comparacion(espacio_ot) == espacio_obj
            ):
                datos.append((
                    id_ot,
                    numero_ot,
                    descripcion,
                    estado,
                    prioridad,
                    operario,
                    origen,
                    area,
                    fecha_creacion,
                ))

    except Exception:
        datos = []

    conn.close()
    return datos


def obtener_inventario_espacio(centro, edificio, espacio):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id, fecha_revision, elemento, cantidad, estado,
                   ancho, alto, fondo, unidad, observaciones, foto, operario
            FROM inventario_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
            ORDER BY elemento ASC
        """), (centro, edificio, espacio))

        datos = cur.fetchall()
    except Exception:
        datos = []

    conn.close()
    return datos


def obtener_preventivos_espacio(centro, edificio, espacio):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id, fecha, operario, estado, observaciones, numero_ot_preventiva
            FROM preventivo_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
            ORDER BY id DESC
        """), (centro, edificio, espacio))

        datos = cur.fetchall()
    except Exception:
        datos = []

    conn.close()
    return datos


def obtener_historial_tecnico_espacio(centro, edificio, espacio):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id, fecha, elemento, tipo, numero_ot, descripcion,
                   area, estado, operario, observaciones, origen,
                   tipo_orden, coste, foto, fecha_reparacion
            FROM espacios_historial
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
            ORDER BY id DESC
        """), (centro, edificio, espacio))

        datos = cur.fetchall()
    except Exception:
        datos = []

    conn.close()
    return datos


def obtener_resumen_ficha_espacio(centro, edificio, espacio):
    actuaciones = obtener_actuaciones_espacio(centro, edificio, espacio)

    return {
        "actuaciones": len(actuaciones),
        "actuaciones_abiertas": len(actuaciones),
        "inventario": 0,
        "preventivos": 0,
        "historial": 0,
    }
