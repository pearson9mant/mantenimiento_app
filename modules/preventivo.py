from datetime import datetime, timedelta
from database.db import conectar, _sql
from modules.ordenes import (
    crear_orden,
    obtener_siguiente_numero_ot,
    crear_correctiva_desde_ot,
)


_ESTRUCTURA_PREVENTIVO_ASEGURADA = False


def hoy_str():
    return datetime.now().strftime("%Y-%m-%d")

def asegurar_estructura_preventivo():
    """
    Asegura una sola vez por proceso las columnas nuevas del módulo.
    No elimina ni renombra columnas existentes.
    """
    global _ESTRUCTURA_PREVENTIVO_ASEGURADA

    if _ESTRUCTURA_PREVENTIVO_ASEGURADA:
        return

    conn = conectar()
    cursor = conn.cursor()

    cambios = [
        ("preventivo_checklist", "estado_revision", "TEXT DEFAULT ''"),
        ("preventivo_checklist", "observaciones_revision", "TEXT DEFAULT ''"),
        ("preventivo_checklist", "crear_correctivo", "INTEGER DEFAULT 0"),
        ("preventivo_checklist", "numero_ot_correctiva", "TEXT DEFAULT ''"),
        ("preventivo_tareas", "planta", "TEXT DEFAULT ''"),
        ("preventivo_registros", "planta", "TEXT DEFAULT ''"),
    ]

    try:
        for tabla, columna, tipo in cambios:
            try:
                cursor.execute(
                    f"""
                    ALTER TABLE {tabla}
                    ADD COLUMN {columna} {tipo}
                    """
                )
                conn.commit()
            except Exception:
                conn.rollback()

        _ESTRUCTURA_PREVENTIVO_ASEGURADA = True

    finally:
        conn.close()


def asegurar_columnas_checklist_preventivo():
    asegurar_estructura_preventivo()


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


def normalizar_tarea(texto):
    texto = str(texto or "").strip().lower()
    cambios = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }

    for a, b in cambios.items():
        texto = texto.replace(a, b)

    return texto


def obtener_items_checklist_configurado(tarea):
    """
    Primero intenta usar los modelos configurados en Configuración.
    Si no encuentra coincidencia, devuelve lista vacía y se usará el checklist por defecto.
    """
    tarea_txt = normalizar_tarea(tarea)

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT tarea_clave, item
            FROM preventivo_checklist_modelos
            WHERE activo = 1
            ORDER BY categoria, tarea_clave, id
        """)
        modelos = cursor.fetchall()
    except Exception:
        modelos = []

    conn.close()

    items = []

    for tarea_clave, item in modelos:
        clave = normalizar_tarea(tarea_clave)

        if clave and clave in tarea_txt:
            items.append(item)

    return items


def obtener_items_checklist_por_tarea(tarea):
    items_configurados = obtener_items_checklist_configurado(tarea)

    if items_configurados:
        return items_configurados

    tarea_txt = normalizar_tarea(tarea)

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

    if "split" in tarea_txt or "aire acondicionado" in tarea_txt or "climatizacion" in tarea_txt:
        return [
            "Revisión visual de unidad interior",
            "Limpieza de filtros",
            "Comprobación de desagüe de condensados",
            "Comprobación de mando y encendido",
            "Comprobación de frío/calor",
            "Revisión de ruidos o vibraciones",
            "Revisión visual de unidad exterior",
            "Comprobación de soportes y fijaciones",
            "Comprobación de suciedad en batería exterior",
            "Anotar incidencias detectadas",
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

    if "bano" in tarea_txt or "grifo" in tarea_txt or "cisterna" in tarea_txt or "fontaner" in tarea_txt:
        return [
            "Comprobar fugas visibles",
            "Revisar grifos y pulsadores",
            "Revisar cisternas o fluxores",
            "Comprobar desagües",
            "Comprobar malos olores",
        ]

    if "limpieza" in tarea_txt:
        return [
            "Preparar zona de trabajo",
            "Realizar limpieza",
            "Retirar residuos",
            "Comprobar acabado final",
            "Dejar zona limpia y segura",
        ]

    return [
        "Revisión visual general",
        "Comprobación de funcionamiento",
        "Anotar incidencias detectadas",
        "Dejar zona en condiciones correctas",
    ]


def existe_ot_preventiva_abierta(
    tarea_id,
    tarea,
    centro,
    edificio,
    planta,
    espacio
):
    """
    Comprueba primero la vinculación tarea_id -> numero_ot.
    """
    asegurar_estructura_preventivo()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT COUNT(*)
            FROM preventivo_registros pr
            INNER JOIN ordenes_trabajo ot
                ON ot.numero_ot = pr.numero_ot
            WHERE pr.tarea_id = ?
              AND LOWER(COALESCE(ot.estado, ''))
                  NOT IN ('finalizada', 'finalizado', 'cerrada', 'cerrado', 'cancelada', 'cancelado')
        """), (int(tarea_id),))

        total = int(cursor.fetchone()[0] or 0)

        if total > 0:
            return True

        texto_buscar = f"[PREVENTIVO] {tarea}"

        cursor.execute(_sql("""
            SELECT COUNT(*)
            FROM ordenes_trabajo
            WHERE origen = ?
              AND descripcion = ?
              AND centro = ?
              AND edificio = ?
              AND espacio = ?
              AND LOWER(COALESCE(estado, ''))
                  NOT IN ('finalizada', 'finalizado', 'cerrada', 'cerrado', 'cancelada', 'cancelado')
        """), (
            "PREVENTIVO",
            texto_buscar,
            centro,
            edificio,
            espacio
        ))

        return int(cursor.fetchone()[0] or 0) > 0

    finally:
        conn.close()


def crear_checklist_preventivo(numero_ot, tarea_id, tarea, operario):
    asegurar_estructura_preventivo()

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
    asegurar_columnas_checklist_preventivo()
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

def obtener_checklist_preventivo_detallado(numero_ot):
    asegurar_columnas_checklist_preventivo()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT
            id,
            numero_ot,
            tarea_id,
            item,
            hecho,
            fecha_hecho,
            operario,
            observaciones,
            estado_revision,
            observaciones_revision,
            crear_correctivo,
            numero_ot_correctiva
        FROM preventivo_checklist
        WHERE numero_ot = ?
        ORDER BY id ASC
    """), (numero_ot,))

    datos = cursor.fetchall()

    conn.close()
    return datos


def actualizar_item_checklist_preventivo(
    id_check,
    estado_revision,
    observaciones_revision="",
    crear_correctivo=False,
    operario=""
):
    asegurar_columnas_checklist_preventivo()

    estado_revision = str(estado_revision or "").strip()

    estados_validos = [
        "",
        "Correcto",
        "Revisar",
        "Avería",
    ]

    if estado_revision not in estados_validos:
        return False

    hecho = 1 if estado_revision else 0
    fecha_hecho = hoy_str() if hecho else ""

    if estado_revision != "Avería":
        crear_correctivo = False

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE preventivo_checklist
        SET estado_revision = ?,
            observaciones_revision = ?,
            crear_correctivo = ?,
            hecho = ?,
            fecha_hecho = ?,
            operario = ?
        WHERE id = ?
    """), (
        estado_revision,
        str(observaciones_revision or "").strip(),
        1 if crear_correctivo else 0,
        hecho,
        fecha_hecho,
        operario,
        id_check
    ))

    conn.commit()
    conn.close()

    return True

def guardar_checklist_preventivo_completo(items, operario=""):
    """
    Guarda todos los puntos del checklist en una sola operación.

    items debe ser una lista de diccionarios:
    {
        "id_check": 1,
        "estado_revision": "Correcto",
        "observaciones_revision": "",
        "crear_correctivo": False,
    }
    """
    asegurar_columnas_checklist_preventivo()

    if not items:
        return False

    estados_validos = [
        "",
        "Correcto",
        "Ajustado",
        "Revisar",
        "Avería",
    ]

    conn = conectar()
    cursor = conn.cursor()

    try:
        for item in items:
            id_check = int(item["id_check"])

            estado_revision = str(
                item.get("estado_revision") or ""
            ).strip()

            observaciones_revision = str(
                item.get("observaciones_revision") or ""
            ).strip()

            crear_correctivo = bool(
                item.get("crear_correctivo", False)
            )

            if estado_revision not in estados_validos:
                raise ValueError(
                    f"Estado preventivo no válido: {estado_revision}"
                )

            hecho = 1 if estado_revision else 0
            fecha_hecho = hoy_str() if hecho else ""

            if estado_revision != "Avería":
                crear_correctivo = False

            cursor.execute(_sql("""
                UPDATE preventivo_checklist
                SET estado_revision = ?,
                    observaciones_revision = ?,
                    crear_correctivo = ?,
                    hecho = ?,
                    fecha_hecho = ?,
                    operario = ?
                WHERE id = ?
            """), (
                estado_revision,
                observaciones_revision,
                1 if crear_correctivo else 0,
                hecho,
                fecha_hecho,
                operario,
                id_check
            ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


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
    asegurar_estructura_preventivo()

    conn = conectar()
    cursor = conn.cursor()

    hoy = hoy_str()
    generadas = 0

    cursor.execute("""
        SELECT id, centro, edificio, planta, espacio, area, tarea,
               frecuencia, ultima_fecha, proxima_fecha, operario,
               tipo, prioridad, duracion_prevista,
               material_necesario, empresa_externa, fecha_limite
        FROM preventivo_tareas
        WHERE activo = 1
    """)

    tareas = cursor.fetchall()

    for t in tareas:
        (
            tarea_id, centro, edificio, planta, espacio, area, tarea,
            frecuencia, ultima_fecha, proxima_fecha, operario,
            tipo, prioridad, duracion_prevista,
            material_necesario, empresa_externa, fecha_limite
        ) = t

        operario = operario_por_centro_preventivo(centro, operario)

        if not proxima_fecha:
            proxima_fecha = hoy

        if str(proxima_fecha) <= hoy:
            if existe_ot_preventiva_abierta(tarea_id, tarea, centro, edificio, planta, espacio):
                continue

            numero = obtener_siguiente_numero_ot(centro, "PREV")

            descripcion = f"[PREVENTIVO] {tarea}"

            observaciones_ot = f"""
Tipo preventivo: {tipo or 'Preventivo'}
Planta: {planta or '-'}
Frecuencia: {frecuencia or '-'}
Duración prevista: {duracion_prevista or '-'}
Material necesario: {material_necesario or '-'}
Empresa externa / mantenedor: {empresa_externa or '-'}
Fecha límite: {fecha_limite or '-'}
""".strip()

            datos_orden = (
                numero,
                descripcion,
                "Abierta",
                centro,
                edificio,
                espacio,
                area,
                prioridad or "Media",
                operario,
                "PREVENTIVO",
                observaciones_ot,
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
                    planta,
                    espacio,
                    area,
                    tarea,
                    frecuencia,
                    operario
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), (
                tarea_id,
                numero,
                centro,
                edificio,
                planta,
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

def crear_correctivas_checklist_preventivo(numero_ot):
    """
    Crea una OT correctiva por cada punto del checklist marcado como:
    - estado_revision = Avería
    - crear_correctivo = 1
    - todavía sin OT correctiva asociada

    Devuelve:
        (cantidad_creadas, mensajes)
    """
    asegurar_columnas_checklist_preventivo()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT
                pc.id,
                pc.tarea_id,
                pc.item,
                pc.observaciones_revision,
                pc.numero_ot_correctiva,
                pt.centro,
                pt.edificio,
                pt.planta,
                pt.espacio,
                pt.area,
                pt.prioridad,
                pt.operario
            FROM preventivo_checklist pc
            LEFT JOIN preventivo_tareas pt
                ON pt.id = pc.tarea_id
            WHERE pc.numero_ot = ?
              AND pc.estado_revision = 'Avería'
              AND pc.crear_correctivo = 1
              AND TRIM(COALESCE(pc.numero_ot_correctiva, '')) = ''
            ORDER BY pc.id ASC
        """), (numero_ot,))

        averias = cursor.fetchall()

    finally:
        conn.close()

    creadas = 0
    mensajes = []

    for averia in averias:
        (
            id_check,
            tarea_id,
            item,
            observaciones_revision,
            numero_ot_correctiva,
            centro,
            edificio,
            planta,
            espacio,
            area,
            prioridad,
            operario,
        ) = averia

        descripcion_defecto = str(item or "").strip()

        if planta:
            descripcion_defecto = f"Planta: {planta}\n{descripcion_defecto}"

        if observaciones_revision:
            descripcion_defecto += (
                f"\n\nObservaciones del preventivo: "
                f"{observaciones_revision}"
            )

        ok, mensaje = crear_correctiva_desde_ot(
            centro=centro,
            edificio=edificio,
            espacio=espacio,
            area=area or "Mantenimiento",
            prioridad=prioridad or "Media",
            operario=operario or "",
            descripcion_defecto=descripcion_defecto,
            numero_ot_origen=numero_ot,
            origen="Preventivo",
            solicitante="Operarios",
        )

        if not ok:
            mensajes.append(mensaje)
            continue

        numero_correctiva = ""

        texto_mensaje = str(mensaje or "")

        if ":" in texto_mensaje:
            numero_correctiva = texto_mensaje.split(":")[-1].strip()

        conn = conectar()
        cursor = conn.cursor()

        try:
            cursor.execute(_sql("""
                UPDATE preventivo_checklist
                SET numero_ot_correctiva = ?
                WHERE id = ?
            """), (
                numero_correctiva,
                int(id_check)
            ))

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

        creadas += 1
        mensajes.append(mensaje)

    return creadas, mensajes
