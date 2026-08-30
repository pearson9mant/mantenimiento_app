import re
from datetime import datetime, timedelta
from database.db import conectar, _sql
from modules.ordenes import (
    crear_orden,
    obtener_siguiente_numero_ot,
    crear_correctiva_desde_ot,
    vincular_origen_ot,
)

from modules.preventivo_aulas import crear_revision_aula


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


def frecuencia_a_dias(frecuencia, defecto=30):
    """
    Convierte la frecuencia a días.

    Compatibilidad:
    - Nuevas planificaciones: se guardan directamente como número de días.
    - Planificaciones antiguas: Semanal, Mensual, Trimestral,
      Semestral y Anual siguen funcionando sin migración previa.
    """
    texto = str(frecuencia or "").strip().lower()

    if not texto:
        return int(defecto)

    try:
        dias = int(float(texto.replace(",", ".")))
        return max(1, dias)
    except (TypeError, ValueError):
        pass

    equivalencias = {
        "semanal": 7,
        "mensual": 30,
        "trimestral": 90,
        "semestral": 180,
        "anual": 365,
    }

    for nombre, dias in equivalencias.items():
        if nombre in texto:
            return dias

    return int(defecto)


def sumar_frecuencia(fecha, frecuencia):
    fecha_dt = datetime.strptime(str(fecha)[:10], "%Y-%m-%d")
    dias = frecuencia_a_dias(frecuencia)
    return (fecha_dt + timedelta(days=dias)).strftime("%Y-%m-%d")


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


def normalizar_clave_checklist(texto):
    """
    Normaliza nombres equivalentes para que una misma plantilla
    funcione aunque la tarea se llame WC, baño, baños, aseo o aseos.

    No modifica el nombre real de la tarea almacenada.
    Solo se usa para localizar el modelo de checklist.
    """
    texto = normalizar_tarea(texto)

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto,
    )

    palabras = texto.split()

    equivalencias = {
        "wc": "bano",
        "aseo": "bano",
        "aseos": "bano",
        "bano": "bano",
        "banos": "bano",
    }

    palabras = [
        equivalencias.get(palabra, palabra)
        for palabra in palabras
    ]

    return " ".join(palabras)


def es_preventivo_integral_espacio(area, tarea):
    """
    Identifica el flujo de revisión general de un espacio.

    Compatibilidad:
    - Los antiguos "Preventivo aulas" siguen entrando exactamente igual.
    - Las nuevas planificaciones con área "Mantenimiento general" usan el
      mismo flujo integral para cualquier espacio del catálogo.

    El resto de preventivos (cuadros, split, legionella, etc.) conserva su
    checklist tradicional.
    """
    tarea_txt = normalizar_clave_checklist(tarea)
    area_txt = normalizar_clave_checklist(area)

    if (
        tarea_txt == "preventivo aulas"
        or "preventivo aulas" in tarea_txt
        or "preventivo aula" in tarea_txt
    ):
        return True

    return area_txt in {
        "mantenimiento general",
        "mantenimiento general aulas",
    }


def es_preventivo_integral_aulas(area, tarea):
    """Alias histórico para no romper imports ni llamadas existentes."""
    return es_preventivo_integral_espacio(area, tarea)


def obtener_items_checklist_configurado(tarea):
    """
    Primero intenta usar los modelos configurados en Configuración.

    WC, baño y aseo se consideran la misma familia.
    Si no encuentra coincidencia, devuelve lista vacía y se usará
    el checklist por defecto.

    Elimina duplicados conservando el orden.
    """
    tarea_txt = normalizar_clave_checklist(tarea)

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

    finally:
        conn.close()

    items = []

    for tarea_clave, item in modelos:
        clave = normalizar_clave_checklist(
            tarea_clave
        )

        if clave and clave in tarea_txt:
            item_txt = str(
                item or ""
            ).strip()

            if (
                item_txt
                and item_txt not in items
            ):
                items.append(item_txt)

    return items


def obtener_items_checklist_por_tarea(tarea):
    items_configurados = obtener_items_checklist_configurado(tarea)

    if items_configurados:
        return items_configurados

    tarea_txt = normalizar_clave_checklist(tarea)

    if "cuadro" in tarea_txt and "electric" in tarea_txt:
        return [
            "Estado general del cuadro",
            "Comprobación de magnetotérmicos",
            "Prueba de diferenciales (botón TEST)",
            "Inspección visual de bornes y conexiones",
            "Comprobación de calentamientos, olores o ruidos anómalos",
            "Limpieza interior del cuadro (si procede)",
            "Estado de tapas, protecciones y señalización",
            "Accesibilidad y espacio libre del cuadro",
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

    if (
        "bano" in tarea_txt
        or "grifo" in tarea_txt
        or "cisterna" in tarea_txt
        or "fontaner" in tarea_txt
    ):
        return [
            "Estado general del baño",
            "Comprobación de inodoros (descarga y fijación)",
            "Comprobación de lavabos",
            "Comprobación de grifos o sistemas Presto",
            "Comprobación de cisternas o fluxores",
            "Comprobación de fugas visibles",
            "Comprobación de desagües y sifones",
            "Estado de puertas y herrajes",
            "Comprobación de iluminación",
            "Comprobación de ventilación (si dispone)",
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
    Evita duplicar una OT preventiva.

    Orden de comprobación:
    1. Vinculación estructural id_preventivo -> OT.
    2. Registro preventivo -> numero_ot.
    3. Compatibilidad con OT antiguas por texto y ubicación.

    En las OT antiguas la planta pudo quedar escrita dentro de
    solicitante u observaciones_estado, por lo que se revisan ambos.
    """
    asegurar_estructura_preventivo()

    conn = conectar()
    cursor = conn.cursor()

    try:
        # 1. Vinculación moderna y fiable.
        try:
            cursor.execute(_sql("""
                SELECT COUNT(*)
                FROM ordenes_trabajo
                WHERE id_preventivo = ?
                  AND LOWER(COALESCE(estado, ''))
                      NOT IN (
                          'finalizada',
                          'finalizado',
                          'cerrada',
                          'cerrado',
                          'cancelada',
                          'cancelado'
                      )
            """), (int(tarea_id),))

            total = int(
                cursor.fetchone()[0] or 0
            )

            if total > 0:
                return True

        except Exception:
            # Compatibilidad por si una instalación antigua
            # todavía no tuviera id_preventivo.
            try:
                conn.rollback()
            except Exception:
                pass

        # 2. Vinculación histórica mediante preventivo_registros.
        cursor.execute(_sql("""
            SELECT COUNT(*)
            FROM preventivo_registros pr
            INNER JOIN ordenes_trabajo ot
                ON ot.numero_ot = pr.numero_ot
            WHERE pr.tarea_id = ?
              AND LOWER(COALESCE(ot.estado, ''))
                  NOT IN (
                      'finalizada',
                      'finalizado',
                      'cerrada',
                      'cerrado',
                      'cancelada',
                      'cancelado'
                  )
        """), (int(tarea_id),))

        total = int(
            cursor.fetchone()[0] or 0
        )

        if total > 0:
            return True

        # 3. Respaldo para OT antiguas no vinculadas.
        texto_buscar = f"[PREVENTIVO] {tarea}"
        planta_txt = str(planta or "").strip()

        if planta_txt:
            patron_planta = f"%Planta: {planta_txt}%"

            cursor.execute(_sql("""
                SELECT COUNT(*)
                FROM ordenes_trabajo
                WHERE origen = ?
                  AND descripcion = ?
                  AND centro = ?
                  AND edificio = ?
                  AND espacio = ?
                  AND (
                        COALESCE(observaciones_estado, '') LIKE ?
                        OR COALESCE(solicitante, '') LIKE ?
                  )
                  AND LOWER(COALESCE(estado, ''))
                      NOT IN (
                          'finalizada',
                          'finalizado',
                          'cerrada',
                          'cerrado',
                          'cancelada',
                          'cancelado'
                      )
            """), (
                "PREVENTIVO",
                texto_buscar,
                centro,
                edificio,
                espacio,
                patron_planta,
                patron_planta,
            ))

        else:
            cursor.execute(_sql("""
                SELECT COUNT(*)
                FROM ordenes_trabajo
                WHERE origen = ?
                  AND descripcion = ?
                  AND centro = ?
                  AND edificio = ?
                  AND espacio = ?
                  AND LOWER(COALESCE(estado, ''))
                      NOT IN (
                          'finalizada',
                          'finalizado',
                          'cerrada',
                          'cerrado',
                          'cancelada',
                          'cancelado'
                      )
            """), (
                "PREVENTIVO",
                texto_buscar,
                centro,
                edificio,
                espacio,
            ))

        return int(
            cursor.fetchone()[0] or 0
        ) > 0

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
        "Ajustado",
        "Revisar",
        "Avería",
    ]

    if estado_revision not in estados_validos:
        return False

    observaciones_revision = str(
        observaciones_revision or ""
    ).strip()

    if (
        estado_revision in ["Ajustado", "Revisar", "Avería"]
        and not observaciones_revision
    ):
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
        observaciones_revision,
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

            if (
                estado_revision in ["Ajustado", "Revisar", "Avería"]
                and not observaciones_revision
            ):
                raise ValueError(
                    "Los puntos marcados como Ajustado, Revisar o Avería "
                    "deben incluir una observación técnica."
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


def resumen_checklist_preventivo(numero_ot):
    """
    Resume el estado técnico del checklist preventivo.

    Reglas:
    - Correcto: no requiere observación.
    - Ajustado / Revisar / Avería: requieren observación técnica.
    - Avería con "crear_correctivo" marcado: debe tener OT correctiva
      vinculada antes de considerar el preventivo listo para cerrar.
    """
    checks = obtener_checklist_preventivo_detallado(numero_ot)

    resumen = {
        "total": 0,
        "completados": 0,
        "pendientes": 0,
        "correctos": 0,
        "ajustados": 0,
        "revisar": 0,
        "averias": 0,
        "observaciones_faltantes": 0,
        "correctivas_pendientes": 0,
        "correctivas_creadas": 0,
        "listo_para_cerrar": False,
    }

    if not checks:
        return resumen

    resumen["total"] = len(checks)

    for check in checks:
        (
            id_check,
            check_numero_ot,
            tarea_id,
            item,
            hecho,
            fecha_hecho,
            operario,
            observaciones_antiguas,
            estado_revision,
            observaciones_revision,
            crear_correctivo,
            numero_ot_correctiva,
        ) = check

        estado = str(estado_revision or "").strip()

        # Compatibilidad con checklists antiguos.
        if not estado and bool(hecho):
            estado = "Correcto"

        observacion = str(
            observaciones_revision
            or observaciones_antiguas
            or ""
        ).strip()

        if not estado:
            resumen["pendientes"] += 1
            continue

        resumen["completados"] += 1

        if estado == "Correcto":
            resumen["correctos"] += 1

        elif estado == "Ajustado":
            resumen["ajustados"] += 1

        elif estado == "Revisar":
            resumen["revisar"] += 1

        elif estado == "Avería":
            resumen["averias"] += 1

        if (
            estado in ["Ajustado", "Revisar", "Avería"]
            and not observacion
        ):
            resumen["observaciones_faltantes"] += 1

        if estado == "Avería" and bool(crear_correctivo):
            if str(numero_ot_correctiva or "").strip():
                resumen["correctivas_creadas"] += 1
            else:
                resumen["correctivas_pendientes"] += 1

    resumen["listo_para_cerrar"] = (
        resumen["total"] > 0
        and resumen["completados"] == resumen["total"]
        and resumen["observaciones_faltantes"] == 0
        and resumen["correctivas_pendientes"] == 0
    )

    return resumen


def checklist_preventivo_completo(numero_ot):
    """
    Indica si la inspección preventiva puede cerrarse.

    Se permite cerrar con puntos Ajustado, Revisar o Avería porque
    la revisión preventiva ya se ha ejecutado, pero:
    - todos los puntos deben tener resultado,
    - Ajustado/Revisar/Avería deben tener observación,
    - si una Avería está marcada para crear correctiva, esa OT debe
      estar ya creada y vinculada.
    """
    return bool(
        resumen_checklist_preventivo(numero_ot).get(
            "listo_para_cerrar",
            False
        )
    )


def generar_ots_preventivo_si_toca():
    """
    Genera una única OT por tarea preventiva vencida.

    Criterios:
    - No duplica una OT ya abierta.
    - Mantiene centro, edificio, planta, espacio y tarea.
    - Vincula estructuralmente la OT con preventivo_tareas.
    - Guarda la información preventiva en observaciones_estado,
      no en solicitante.
    - Si la planificación lleva retraso, genera una sola OT y
      avanza la próxima fecha hasta el siguiente vencimiento futuro,
      manteniendo el calendario anclado.
    """
    asegurar_estructura_preventivo()

    conn = conectar()
    cursor = conn.cursor()

    hoy = hoy_str()
    generadas = 0

    try:
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
                tarea_id,
                centro,
                edificio,
                planta,
                espacio,
                area,
                tarea,
                frecuencia,
                ultima_fecha,
                proxima_fecha,
                operario,
                tipo,
                prioridad,
                duracion_prevista,
                material_necesario,
                empresa_externa,
                fecha_limite,
            ) = t

            operario = operario_por_centro_preventivo(
                centro,
                operario
            )

            if not proxima_fecha:
                proxima_fecha = hoy

            fecha_programada = str(
                proxima_fecha
            )[:10]

            if fecha_programada > hoy:
                continue

            if existe_ot_preventiva_abierta(
                tarea_id,
                tarea,
                centro,
                edificio,
                planta,
                espacio
            ):
                continue

            numero = obtener_siguiente_numero_ot(
                centro,
                "PREV"
            )

            es_revision_general_espacio = es_preventivo_integral_espacio(
                area,
                tarea,
            )

            if es_revision_general_espacio:
                descripcion = f"[PREVENTIVO ESPACIO] {tarea}"
            else:
                descripcion = f"[PREVENTIVO] {tarea}"

            observaciones_ot = f"""
Tipo preventivo: {tipo or 'Preventivo'}
Planta: {planta or '-'}
Frecuencia: {frecuencia or '-'} días
Duración prevista: {duracion_prevista or '-'}
Material necesario: {material_necesario or '-'}
Empresa externa / mantenedor: {empresa_externa or '-'}
Fecha planificada: {fecha_programada or '-'}
Fecha límite: {fecha_limite or '-'}
""".strip()

            # crear_orden mantiene compatibilidad por posición.
            # IMPORTANTE:
            # - solicitante = "Mantenimiento preventivo"
            # - fecha_programada = fecha_programada
            # - observaciones_estado = observaciones_ot
            datos_orden = (
                numero,                         # 0 numero_ot
                descripcion,                    # 1 descripcion
                "Abierta",                      # 2 estado
                centro,                         # 3 centro
                edificio,                       # 4 edificio
                espacio,                        # 5 espacio
                area,                           # 6 area
                prioridad or "Media",           # 7 prioridad
                operario,                       # 8 operario
                "PREVENTIVO",                   # 9 origen
                "Mantenimiento preventivo",     # 10 solicitante
                fecha_programada,               # 11 fecha_origen
                "",                             # 12 foto
                "Operarios",                    # 13 tipo_solicitante
                "Interna",                      # 14 tipo_orden
                "",                             # 15 empresa_externa
                "",                             # 16 contacto_empresa
                "",                             # 17 telefono_empresa
                "",                             # 18 email_empresa
                fecha_programada,               # 19 fecha_aviso/programada
                "",                             # 20 fecha_realizacion
                "",                             # 21 trabajo_a_realizar
                "",                             # 22 trabajo_realizado
                "",                             # 23 firma_operario
                "",                             # 24 fecha_firma_operario
                0,                              # 25 coste_estimado
                0,                              # 26 coste_final
                observaciones_ot,               # 27 observaciones_estado
                planta or "",                   # 28 planta
            )

            crear_orden(
                datos_orden
            )

            # Vinculación estructural: evita depender de textos.
            vincular_origen_ot(
                numero_ot=numero,
                origen_tabla="preventivo_tareas",
                origen_id=int(tarea_id),
                id_preventivo=int(tarea_id),
            )

            if es_revision_general_espacio:
                # -------------------------------------------------
                # REVISIÓN GENERAL DE ESPACIO
                # -------------------------------------------------
                # Conservamos las tablas/funciones históricas de aulas para
                # no romper nada, pero el flujo ya sirve para cualquier
                # espacio: aula, WC, despacho, informática, cocina, etc.
                crear_revision_aula(
                    centro=centro,
                    edificio=edificio,
                    planta=planta or "",
                    espacio=espacio,
                    operario=operario,
                    observaciones=observaciones_ot,
                    numero_ot_preventiva=numero,
                )

            else:
                # -------------------------------------------------
                # TODOS LOS PREVENTIVOS EXISTENTES
                # -------------------------------------------------
                # Conservan exactamente el checklist tradicional.
                crear_checklist_preventivo(
                    numero,
                    tarea_id,
                    tarea,
                    operario
                )

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

            # Mantener el calendario anclado, pero sin crear
            # una cascada de OT atrasadas una detrás de otra.
            nueva_proxima = sumar_frecuencia(
                fecha_programada,
                frecuencia
            )

            while nueva_proxima <= hoy:
                nueva_proxima = sumar_frecuencia(
                    nueva_proxima,
                    frecuencia
                )

            cursor.execute(_sql("""
                UPDATE preventivo_tareas
                SET ultima_fecha = ?,
                    proxima_fecha = ?
                WHERE id = ?
            """), (
                hoy,
                nueva_proxima,
                tarea_id
            ))

            generadas += 1

        conn.commit()
        return generadas

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


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

        texto_mensaje = str(mensaje or "").strip()

        # La función histórica devuelve normalmente un texto con el número
        # de OT al final. Conservamos compatibilidad sin depender de una
        # redacción exacta.
        if ":" in texto_mensaje:
            numero_correctiva = texto_mensaje.split(":")[-1].strip()

        if not numero_correctiva:
            partes = texto_mensaje.split()

            for parte in reversed(partes):
                candidata = parte.strip(".,;()[]{}")

                if (
                    candidata
                    and any(ch.isdigit() for ch in candidata)
                    and (
                        "OT" in candidata.upper()
                        or "COR" in candidata.upper()
                        or "INC" in candidata.upper()
                    )
                ):
                    numero_correctiva = candidata
                    break

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
