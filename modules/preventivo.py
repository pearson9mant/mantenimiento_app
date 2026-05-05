from datetime import datetime, timedelta
from database.db import conectar, _sql
from modules.ordenes import crear_orden, obtener_siguiente_numero_ot


# =====================================================
# UTILIDADES
# =====================================================

def hoy_str():
    return datetime.now().strftime("%Y-%m-%d")


def sumar_frecuencia(fecha, frecuencia):
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")

    frecuencia = (frecuencia or "").lower()

    if "semanal" in frecuencia:
        return (fecha_dt + timedelta(days=7)).strftime("%Y-%m-%d")

    if "mensual" in frecuencia:
        return (fecha_dt + timedelta(days=30)).strftime("%Y-%m-%d")

    if "trimestral" in frecuencia:
        return (fecha_dt + timedelta(days=90)).strftime("%Y-%m-%d")

    if "semestral" in frecuencia:
        return (fecha_dt + timedelta(days=180)).strftime("%Y-%m-%d")

    if "anual" in frecuencia:
        return (fecha_dt + timedelta(days=365)).strftime("%Y-%m-%d")

    # fallback
    return (fecha_dt + timedelta(days=30)).strftime("%Y-%m-%d")


# =====================================================
# GENERADOR DE OTs PREVENTIVAS
# =====================================================

def generar_ots_preventivo_si_toca():
    conn = conectar()
    cursor = conn.cursor()

    hoy = hoy_str()
    generadas = 0

    cursor.execute("""
        SELECT id, centro, edificio, espacio, area, tarea,
               frecuencia, ultima_fecha, proxima_fecha, operario
        FROM preventivo_tareas
        WHERE activo = 1
    """)

    tareas = cursor.fetchall()

    for t in tareas:
        (
            tarea_id, centro, edificio, espacio, area, tarea,
            frecuencia, ultima_fecha, proxima_fecha, operario
        ) = t

        # Si no hay próxima fecha → inicializamos
        if not proxima_fecha:
            proxima_fecha = hoy

        if proxima_fecha <= hoy:
            # -----------------------------------
            # Crear OT
            # -----------------------------------
            numero = obtener_siguiente_numero_ot(centro, "PREV")

            descripcion = f"[PREVENTIVO] {tarea}"

            datos_orden = (
                numero,
                descripcion,
                "Abierta",
                centro,
                edificio,
                espacio,
                area,
                "Media",
                operario,
                "PREVENTIVO",
                "",
                "",
                "",
                "Operarios"
            )

            crear_orden(datos_orden)

            # -----------------------------------
            # Registrar
            # -----------------------------------
            cursor.execute(_sql("""
                INSERT INTO preventivo_registros
                (
                    tarea_id,
                    numero_ot,
                    centro,
                    edificio,
                    espacio,
                    area,
                    tarea,
                    frecuencia,
                    operario
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), (
                tarea_id,
                numero,
                centro,
                edificio,
                espacio,
                area,
                tarea,
                frecuencia,
                operario
            ))

            # -----------------------------------
            # Actualizar fechas
            # -----------------------------------
            nueva_proxima = sumar_frecuencia(hoy, frecuencia)

            cursor.execute(_sql("""
                UPDATE preventivo_tareas
                SET ultima_fecha = ?, proxima_fecha = ?
                WHERE id = ?
            """), (hoy, nueva_proxima, tarea_id))

            generadas += 1

    conn.commit()
    conn.close()

    return generadas
