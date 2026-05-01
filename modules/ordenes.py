from database.db import conectar, _sql

ESTADOS_VALIDOS = ["Abierta", "En curso", "Pendiente material", "Finalizada"]


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

    # Compatibilidad con llamadas antiguas
    if len(datos) == 10:
        datos = (*datos, "", "", "", "Operarios")

    elif len(datos) == 12:
        datos = (*datos, "", "Operarios")

    elif len(datos) == 13:
        datos = (*datos, "Operarios")

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
            tipo_solicitante
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """), datos)

    conn.commit()
    conn.close()


def obtener_ordenes():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, numero_ot, descripcion, estado, fecha_creacion,
               centro, edificio, espacio, area, prioridad, operario, origen,
               solicitante, fecha_origen, foto, tipo_solicitante
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
               tipo_solicitante
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
                   solicitante, fecha_origen, foto, tipo_solicitante
            FROM ordenes_trabajo
            WHERE centro = ?
            ORDER BY id DESC
        """), (centro,))
    else:
        cursor.execute("""
            SELECT id, numero_ot, descripcion, estado, fecha_creacion,
                   centro, edificio, espacio, area, prioridad, operario, origen,
                   solicitante, fecha_origen, foto, tipo_solicitante
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
               solicitante, fecha_origen, foto, tipo_solicitante
        FROM ordenes_trabajo
        WHERE id = ?
    """), (id_orden,))

    orden = cursor.fetchone()

    if orden:
        (
            numero_ot, descripcion, estado, fecha_creacion,
            centro, edificio, espacio, area, prioridad, operario, origen,
            solicitante, fecha_origen, foto, tipo_solicitante
        ) = orden

        cursor.execute(_sql("""
            INSERT INTO historico_ordenes
            (numero_ot, descripcion, estado, fecha_creacion, centro, edificio,
             espacio, area, prioridad, operario, origen, solicitante,
             fecha_origen, observaciones_cierre, foto, tipo_solicitante)
            VALUES (?, ?, 'Finalizada', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            tipo_solicitante
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
