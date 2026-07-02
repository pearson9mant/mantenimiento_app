from database.db import conectar, _sql

from modules.espacios import (
    coincide_centro,
    coincide_edificio,
    coincide_espacio,
)


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
                coincide_centro(centro_ot, centro)
                and (
                    not edificio
                    or not edificio_ot
                    or coincide_edificio(edificio_ot, edificio)
                )
                and coincide_espacio(espacio_ot, espacio)
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
                coste_estimado,
                cantidad_afectada
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

    trabajos = len(actuaciones)
    activos = len(inventario)
    preventivos_total = len(preventivos)

    activos_danados = 0
    correctivos_pendientes = 0

    diagnostico = []
    recomendaciones = []

    primera_ot = ""

    if actuaciones:
        try:
            primera_ot = str(actuaciones[0][1] or "")
        except Exception:
            primera_ot = ""

    for item in inventario:
        try:
            elemento = str(item[2] or "Elemento")
            estado = str(item[4] or "")
            numero_ot_correctiva = str(item[12] or "")
        except Exception:
            continue

        if estado in ["Dañado", "Falta", "Retirar"]:
            activos_danados += 1
            diagnostico.append(f"El activo {elemento} está en estado {estado}.")

        if numero_ot_correctiva:
            correctivos_pendientes += 1
            diagnostico.append(f"Hay un correctivo pendiente asociado a la OT {numero_ot_correctiva}.")
            recomendaciones.append(f"Finalizar la OT {numero_ot_correctiva}.")

    if trabajos > 0:
        diagnostico.append(f"Hay {trabajos} trabajo(s) pendiente(s) en este espacio.")

        if primera_ot:
            recomendaciones.append(f"Abrir y revisar primero la OT {primera_ot}.")
        else:
            recomendaciones.append("Abrir Trabajos del espacio y revisar las OT pendientes.")

    if activos == 0:
        diagnostico.append("Este espacio todavía no tiene activos registrados.")
        recomendaciones.append("Crear el inventario inicial cuando sea posible.")

    if preventivos_total == 0:
        diagnostico.append("No hay preventivos asociados a este espacio.")

    if trabajos == 0 and activos_danados == 0 and correctivos_pendientes == 0:
        estado_global = "Excelente"
        color = "verde"
        mensaje_estado = "Espacio operativo."
        diagnostico = [
            "Sin trabajos pendientes.",
            "Sin activos dañados.",
            "Sin correctivos pendientes.",
        ]

        if activos == 0:
            diagnostico.append("Inventario pendiente de crear.")

        recomendaciones = ["No es necesaria ninguna actuación inmediata."]

    elif correctivos_pendientes > 0 or activos_danados > 0:
        estado_global = "Requiere intervención"
        color = "rojo"
        mensaje_estado = "Hay elementos que necesitan reparación."

    elif trabajos > 0:
        estado_global = "Requiere intervención"
        color = "rojo"
        mensaje_estado = "Hay trabajos pendientes en este espacio."

    else:
        estado_global = "Requiere revisión"
        color = "amarillo"
        mensaje_estado = "Conviene revisar este espacio."

    resumen_corto = ""

    if trabajos > 0:
        resumen_corto = f"{trabajos} trabajo(s) pendiente(s)"
    elif correctivos_pendientes > 0:
        resumen_corto = f"{correctivos_pendientes} correctivo(s) pendiente(s)"
    elif activos_danados > 0:
        resumen_corto = f"{activos_danados} activo(s) dañado(s)"
    else:
        resumen_corto = "Sin avisos pendientes"

    return {
        "estado_global": estado_global,
        "color": color,
        "diagnostico": mensaje_estado,
        "resumen_corto": resumen_corto,
        "motivos": diagnostico,
        "recomendaciones": recomendaciones,
        "trabajos": trabajos,
        "activos": activos,
        "preventivos": preventivos_total,
        "activos_danados": activos_danados,
        "correctivos_pendientes": correctivos_pendientes,
        "primera_ot": primera_ot,
    }
