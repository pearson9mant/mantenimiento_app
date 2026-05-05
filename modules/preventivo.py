from datetime import datetime, timedelta
from database.db import conectar, _sql
from modules.ordenes import crear_orden, obtener_siguiente_numero_ot


def hoy_str():
    return datetime.now().strftime("%Y-%m-%d")


def sumar_frecuencia(fecha, frecuencia):
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    frecuencia = str(frecuencia or "").lower()

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

    return (fecha_dt + timedelta(days=30)).strftime("%Y-%m-%d")


def operario_por_centro_preventivo(centro, operario=""):
    operario = str(operario or "").strip()
    centro = str(centro or "").strip()

    if operario:
        return operario

    if centro == "Pearson 9":
        return "Luis Lozano"

    if centro == "Pearson 22":
        return "J.A. Almeda"

    return ""


def obtener_items_checklist_por_tarea(tarea):
    tarea_txt = str(tarea or "").strip().lower()

    if "cuadro" in tarea_txt and "electric" in tarea_txt:
        return [
            "Revisión visual del cuadro eléctrico",
            "Comprobación de magnetotérmicos",
            "Comprobación de diferenciales con botón TEST",
            "Revisión de calentamientos, olores o ruidos",
            "Apriete visual de bornes si procede",
            "Limpieza interior de polvo si procede",
            "Comprobación de tapas y señalización",
        ]

    if "enchufe" in tarea_txt or "toma" in tarea_txt:
        return [
            "Revisar enchufes sueltos",
            "Comprobar tapas y mecanismos",
            "Revisar calentamientos o marcas",
            "Comprobar fijación a pared",
        ]

    if "luz" in tarea_txt or "ilumin" in tarea_txt or "emergencia" in tarea_txt:
        return [
            "Comprobar encendido correcto",
            "Revisar lámparas o tubos fundidos",
            "Revisar pantallas o difusores",
            "Comprobar interruptores o pulsadores",
            "Comprobar luces de emergencia si aplica",
        ]

    if "baño" in tarea_txt or "grifo" in tarea_txt or "cisterna" in tarea_txt or "fontaner" in tarea_txt:
        return [
            "Comprobar fugas visibles",
            "Revisar grifos y pulsadores",
            "Revisar cisternas o fluxores",
            "Comprobar desagües",
            "Comprobar malos olores",
        ]

    return [
        "Revisión visual general",
        "Comprobación de funcionamiento",
        "Anotar incidencias detectadas",
        "Dejar zona en condiciones correctas",
    ]


def existe_ot_preventiva_abierta(tarea_id, tarea):
    conn = conectar()
    cursor = conn.cursor()

    texto_buscar = f"[PREVENTIVO] {tarea}"

    cursor.execute(_sql("""
        SELECT COUNT(*)
        FROM ordenes_trabajo
        WHERE origen = ?
          AND descripcion = ?
    """), ("PREVENTIVO", texto_buscar))

    total = cursor.fetchone()[0]

    conn.close()
    return total > 0


def crear_checklist_preventivo(numero_ot, tarea_id, tarea, operario):
    items = obtener_items_checklist_por_tarea(tarea)

    conn = conectar()
    cursor = conn.cursor()

    for item in items:
        cursor.execute(_sql("""
            INSERT INTO preventivo_checklist
            (
                numero_ot,
                tarea_id,
                item,
                hecho,
                fecha_hecho,
                operario,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (
            numero_ot,
            tarea_id,
            item,
            0,
            "",
            operario,
            ""
        ))

    conn.commit()
    conn.close()


def obtener_checklist_preventivo(numero_ot):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT id, numero_ot, tarea_id, item, hecho, fecha_hecho, operario, observaciones
        FROM preventivo_checklist
        WHERE numero_ot = ?
        ORDER BY id ASC
    """), (numero_ot,))

    datos = cursor.fetchall()

    conn.close()
    return datos


def actualizar_checklist_preventivo(id_check, hecho, operario=""):
    conn = conectar()
    cursor = conn.cursor()

    fecha_hecho = hoy_str() if hecho else ""

    cursor.execute(_sql("""
        UPDATE preventivo_checklist
        SET hecho = ?, fecha_hecho = ?, operario = ?
        WHERE id = ?
    """), (
        1 if hecho else 0,
        fecha_hecho,
        operario,
        id_check
    ))

    conn.commit()
    conn.close()
    return True


def checklist_preventivo_completo(numero_ot):
    checks = obtener_checklist_preventivo(numero_ot)

    if not checks:
        return False

    total = len(checks)
    hechos = len([c for c in checks if int(c[4] or 0) == 1])

    return total == hechos


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

        operario = operario_por_centro_preventivo(centro, operario)

        if not proxima_fecha:
            proxima_fecha = hoy

        if str(proxima_fecha) <= hoy:
            if existe_ot_preventiva_abierta(tarea_id, tarea):
                continue

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

            crear_checklist_preventivo(numero, tarea_id, tarea, operario)

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
