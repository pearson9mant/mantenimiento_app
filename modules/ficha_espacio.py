from database.db import conectar, _sql


def obtener_actuaciones_espacio(centro, edificio, espacio):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id, numero_ot, descripcion, estado, prioridad,
                   operario, origen, area, fecha_creacion
            FROM ordenes_trabajo
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
              AND LOWER(COALESCE(estado, '')) NOT IN (
                    'finalizada',
                    'cerrado',
                    'cerrada',
                    'cancelada'
              )
            ORDER BY id DESC
        """), (centro, edificio, espacio))

        datos = cur.fetchall()
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
    inventario = obtener_inventario_espacio(centro, edificio, espacio)
    preventivos = obtener_preventivos_espacio(centro, edificio, espacio)
    historial = obtener_historial_tecnico_espacio(centro, edificio, espacio)

    actuaciones_abiertas = actuaciones

    return {
        "actuaciones": len(actuaciones),
        "actuaciones_abiertas": len(actuaciones_abiertas),
        "inventario": len(inventario),
        "preventivos": len(preventivos),
        "historial": len(historial),
    }
