from database.db import conectar, _sql

ESTADOS_VALIDOS = [
    "Abierta",
    "En curso",
    "Pendiente material",
    "Finalizada",
    "Pendiente proveedor",
    "Avisado",
    "En ejecución"
]


def obtener_codigo_centro(centro):
    centro = str(centro or "").strip().lower()
    if centro in ["pearson 22", "p22", "pearson22"]:
        return "P22"
    if centro in ["pearson 9", "p9", "pearson9"]:
        return "P9"
    return "GEN"


def obtener_codigo_tipo(tipo_ot):
    tipo_ot = str(tipo_ot or "").strip().upper()
    if tipo_ot in ["LEG", "LEGIONELLA"]:
        return "LEG"
    if tipo_ot in ["PREV", "PREVENTIVO"]:
        return "PREV"
    if tipo_ot in ["EXT", "EXTERNA", "EXTERNO"]:
        return "EXT"
    return "INC"


def obtener_siguiente_numero_ot(centro="", tipo_ot="INC"):
    conn = conectar()
    cursor = conn.cursor()

    centro_codigo = obtener_codigo_centro(centro)
    tipo_codigo = obtener_codigo_tipo(tipo_ot)

    cursor.execute(_sql("""
        SELECT ultimo_numero FROM contador_ot
        WHERE centro_codigo = ? AND tipo_codigo = ?
    """), (centro_codigo, tipo_codigo))

    fila = cursor.fetchone()

    if fila:
        siguiente = int(fila[0]) + 1
        cursor.execute(_sql("""
            UPDATE contador_ot SET ultimo_numero = ?
            WHERE centro_codigo = ? AND tipo_codigo = ?
        """), (siguiente, centro_codigo, tipo_codigo))
    else:
        siguiente = 1
        cursor.execute(_sql("""
            INSERT INTO contador_ot (centro_codigo, tipo_codigo, ultimo_numero)
            VALUES (?, ?, ?)
        """), (centro_codigo, tipo_codigo, siguiente))

    conn.commit()
    conn.close()

    return f"{centro_codigo}-{tipo_codigo}-{siguiente:05d}"


def crear_orden(datos):
    conn = conectar()
    cursor = conn.cursor()

    datos = tuple(datos)

    numero_ot = datos[0] if len(datos) > 0 else ""
    descripcion = datos[1] if len(datos) > 1 else ""
    estado = datos[2] if len(datos) > 2 else "Abierta"
    centro = datos[3] if len(datos) > 3 else ""
    edificio = datos[4] if len(datos) > 4 else ""
    espacio = datos[5] if len(datos) > 5 else ""
    area = datos[6] if len(datos) > 6 else ""
    prioridad = datos[7] if len(datos) > 7 else ""
    operario = datos[8] if len(datos) > 8 else ""
    origen = datos[9] if len(datos) > 9 else "APP"

    solicitante = datos[10] if len(datos) > 10 else ""
    fecha_origen = datos[11] if len(datos) > 11 else ""
    foto = datos[12] if len(datos) > 12 else ""

    tipo_solicitante = datos[13] if len(datos) > 13 else "Operarios"

    # -------------------------------
    # TAREAS EXTERNAS
    # Campos nuevos al final para no romper llamadas antiguas
    # -------------------------------
    tipo_orden = datos[14] if len(datos) > 14 else "Interna"
    empresa_externa = datos[15] if len(datos) > 15 else ""
    contacto_empresa = datos[16] if len(datos) > 16 else ""
    telefono_empresa = datos[17] if len(datos) > 17 else ""
    email_empresa = datos[18] if len(datos) > 18 else ""
    fecha_programada = datos[19] if len(datos) > 19 else ""
    fecha_realizacion = datos[20] if len(datos) > 20 else ""
    coste_estimado = datos[21] if len(datos) > 21 else 0
    coste_final = datos[22] if len(datos) > 22 else 0

    if not tipo_solicitante:
        tipo_solicitante = "Operarios"

    if not tipo_orden:
        tipo_orden = "Interna"

    if tipo_orden == "Externa":
        operario = ""

        if not estado or estado == "Abierta":
            estado = "Pendiente proveedor"

        if not origen:
            origen = "EXTERNA"

    cursor.execute(_sql("""
        INSERT INTO ordenes_trabajo
        (
            numero_ot,
            descripcion,
            estado,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            fecha_origen,
            foto,
            tipo_solicitante,
            tipo_orden,
            empresa_externa,
            contacto_empresa,
            telefono_empresa,
            email_empresa,
            fecha_programada,
            fecha_realizacion,
            coste_estimado,
            coste_final
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """), (
        numero_ot,
        descripcion,
        estado,
        centro,
        edificio,
        espacio,
        area,
        prioridad,
        operario,
        origen,
        solicitante,
        fecha_origen,
        foto,
        tipo_solicitante,
        tipo_orden,
        empresa_externa,
        contacto_empresa,
        telefono_empresa,
        email_empresa,
        fecha_programada,
        fecha_realizacion,
        coste_estimado,
        coste_final
    ))

    conn.commit()
    conn.close()


def obtener_ordenes():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, numero_ot, descripcion, estado, fecha_creacion,
               centro, edificio, espacio, area, prioridad, operario, origen,
               solicitante, fecha_origen, foto, tipo_solicitante,
               tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
               email_empresa, fecha_programada, fecha_realizacion,
               coste_estimado, coste_final
        FROM ordenes_trabajo
        ORDER BY id DESC
    """)
    datos = cursor.fetchall()

    conn.close()
    return datos


def obtener_historico():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, numero_ot, descripcion, estado, fecha_creacion,
               centro, edificio, espacio, area, prioridad, operario, origen,
               solicitante, fecha_origen, fecha_cierre, observaciones_cierre, foto,
               tipo_solicitante,
               tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
               email_empresa, fecha_programada, fecha_realizacion,
               coste_estimado, coste_final
        FROM historico_ordenes
        ORDER BY id DESC
    """)
    datos = cursor.fetchall()

    conn.close()
    return datos


def obtener_ordenes_operario(operario):
    conn = conectar()
    cursor = conn.cursor()

    mapa_operario_centro = {
        "Luis Lozano": "Pearson 9",
        "J.A. Almeda": "Pearson 22",
        "Abel Vasquez": None
    }

    centro = mapa_operario_centro.get(operario)

    if centro:
        cursor.execute(_sql("""
            SELECT id, numero_ot, descripcion, estado, fecha_creacion,
                   centro, edificio, espacio, area, prioridad, operario, origen,
                   solicitante, fecha_origen, foto, tipo_solicitante,
                   tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
                   email_empresa, fecha_programada, fecha_realizacion,
                   coste_estimado, coste_final
            FROM ordenes_trabajo
            WHERE centro = ?
            ORDER BY id DESC
        """), (centro,))
    else:
        cursor.execute("""
            SELECT id, numero_ot, descripcion, estado, fecha_creacion,
                   centro, edificio, espacio, area, prioridad, operario, origen,
                   solicitante, fecha_origen, foto, tipo_solicitante,
                   tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
                   email_empresa, fecha_programada, fecha_realizacion,
                   coste_estimado, coste_final
            FROM ordenes_trabajo
            ORDER BY id DESC
        """)

    datos = cursor.fetchall()
    conn.close()
    return datos


def actualizar_estado(id_orden, nuevo_estado):
    if nuevo_estado not in ESTADOS_VALIDOS:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE ordenes_trabajo
        SET estado = ?
        WHERE id = ?
    """), (nuevo_estado, id_orden))

    conn.commit()
    conn.close()


def finalizar_orden(id_orden, observaciones=""):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT numero_ot, descripcion, estado, fecha_creacion,
               centro, edificio, espacio, area, prioridad, operario, origen,
               solicitante, fecha_origen, foto, tipo_solicitante,
               tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
               email_empresa, fecha_programada, fecha_realizacion,
               coste_estimado, coste_final
        FROM ordenes_trabajo
        WHERE id = ?
    """), (id_orden,))

    orden = cursor.fetchone()

    if orden:
        (
            numero_ot, descripcion, estado, fecha_creacion,
            centro, edificio, espacio, area, prioridad, operario, origen,
            solicitante, fecha_origen, foto, tipo_solicitante,
            tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
            email_empresa, fecha_programada, fecha_realizacion,
            coste_estimado, coste_final
        ) = orden

        if tipo_orden == "Externa" and not fecha_realizacion:
            fecha_realizacion = ""

        cursor.execute(_sql("""
            INSERT INTO historico_ordenes
            (
                numero_ot,
                descripcion,
                estado,
                fecha_creacion,
                centro,
                edificio,
                espacio,
                area,
                prioridad,
                operario,
                origen,
                solicitante,
                fecha_origen,
                observaciones_cierre,
                foto,
                tipo_solicitante,
                tipo_orden,
                empresa_externa,
                contacto_empresa,
                telefono_empresa,
                email_empresa,
                fecha_programada,
                fecha_realizacion,
                coste_estimado,
                coste_final
            )
            VALUES (?, ?, 'Finalizada', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (
            numero_ot,
            descripcion,
            fecha_creacion,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            fecha_origen,
            observaciones,
            foto,
            tipo_solicitante,
            tipo_orden,
            empresa_externa,
            contacto_empresa,
            telefono_empresa,
            email_empresa,
            fecha_programada,
            fecha_realizacion,
            coste_estimado,
            coste_final
        ))

        cursor.execute(_sql("DELETE FROM ordenes_trabajo WHERE id = ?"), (id_orden,))

    conn.commit()
    conn.close()


def borrar_orden(id_orden):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("DELETE FROM ordenes_trabajo WHERE id = ?"), (id_orden,))

    conn.commit()
    conn.close()
    return True


def borrar_orden_historico(id_orden):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("DELETE FROM historico_ordenes WHERE id = ?"), (id_orden,))

    conn.commit()
    conn.close()
    return True


def actualizar_tipo_solicitante_por_numero(numero_ot, tipo_solicitante):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE ordenes_trabajo
        SET tipo_solicitante = ?
        WHERE numero_ot = ?
    """), (tipo_solicitante, numero_ot))

    conn.commit()
    conn.close()
    return True
