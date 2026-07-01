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
            SELECT
                id,
                fecha_revision,
                elemento,
                cantidad,
                estado,
                ancho,
                alto,
                fondo,
                unidad,
                observaciones,
                foto,
                operario,
                numero_ot_correctiva,
                fecha_correctivo,
                fabricante,
                modelo,
                numero_serie,
                fecha_instalacion,
                proveedor,
                vida_util_anios,
                coste_estimado
            FROM inventario_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
            ORDER BY elemento ASC
        """), (
            centro,
            edificio,
            espacio
        ))

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

def obtener_cabecera_inteligente_espacio(centro, edificio, espacio):
    actuaciones = obtener_actuaciones_espacio(centro, edificio, espacio)
    inventario = obtener_inventario_espacio(centro, edificio, espacio)
    preventivos = obtener_preventivos_espacio(centro, edificio, espacio)

    total_trabajos = len(actuaciones)
    total_inventario = len(inventario)
    total_preventivos = len(preventivos)

    elementos_mal = 0
    correctivos_pendientes = 0

    for item in inventario:
        try:
            estado = str(item[4] or "")
            numero_ot_correctiva = str(item[12] or "")
        except Exception:
            continue

        if estado in ["Dañado", "Falta", "Retirar"]:
            elementos_mal += 1

        if numero_ot_correctiva:
            correctivos_pendientes += 1

    estado_global = "Correcto"

    if total_trabajos > 0 or elementos_mal > 0 or correctivos_pendientes > 0:
        estado_global = "Atención"

    return {
        "estado_global": estado_global,
        "trabajos": total_trabajos,
        "inventario": total_inventario,
        "preventivos": total_preventivos,
        "elementos_mal": elementos_mal,
        "correctivos_pendientes": correctivos_pendientes,
    }
