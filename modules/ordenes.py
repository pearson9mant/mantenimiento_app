from datetime import date, datetime
from database.db import conectar, _sql, _add_column
from modules.areas import sugerir_area_ot

try:
    from modules.telegram_alertas import enviar_telegram
except Exception:
    enviar_telegram = None

try:
    from modules.espacios_historial import registrar_historial_espacio
except Exception:
    registrar_historial_espacio = None


ESTADOS_VALIDOS = [
    "Abierta",
    "En curso",
    "En pausa",
    "Pendiente material",
    "Finalizada",
    "Pendiente proveedor",
    "Avisado",
    "Pendiente presupuesto",
    "En ejecución",
    "Cerrado"
]

_COLUMNAS_ORDENES_ASEGURADAS = False
_TABLA_CONTADOR_ASEGURADA = False
_TABLA_FOTOS_ASEGURADA = False


# =====================================================
# ASEGURAR COLUMNAS
# =====================================================

def _add_column_seguro(cursor, tabla, columna, tipo):
    try:
        _add_column(cursor, tabla, columna, tipo)
    except Exception:
        pass


def asegurar_columnas_observaciones_estado():
    global _COLUMNAS_ORDENES_ASEGURADAS

    if _COLUMNAS_ORDENES_ASEGURADAS:
        return

    conn = conectar()
    cursor = conn.cursor()

    tablas = ["ordenes_trabajo", "historico_ordenes"]

    columnas = [
        ("observaciones_estado", "TEXT DEFAULT ''"),
        ("planta", "TEXT"),
        ("tipo_orden", "TEXT DEFAULT 'Interna'"),
        ("empresa_externa", "TEXT"),
        ("contacto_empresa", "TEXT"),
        ("telefono_empresa", "TEXT"),
        ("email_empresa", "TEXT"),
        ("fecha_programada", "TEXT"),
        ("fecha_aviso_empresa", "TEXT"),
        ("fecha_realizacion", "TEXT"),
        ("trabajo_a_realizar", "TEXT"),
        ("trabajo_realizado", "TEXT"),
        ("firma_operario", "TEXT"),
        ("fecha_firma_operario", "TEXT"),
        ("coste_estimado", "REAL DEFAULT 0"),
        ("coste_final", "REAL DEFAULT 0"),
        ("foto", "TEXT"),

        # VINCULACIÓN SEGURA DEL CORAZÓN DEL SISTEMA
        ("origen_tabla", "TEXT"),
        ("origen_id", "INTEGER"),
        ("id_punto_legionella", "INTEGER"),
        ("id_preventivo", "INTEGER"),
        ("id_incidencia", "INTEGER"),
    ]

    for tabla in tablas:
        for columna, tipo in columnas:
            _add_column_seguro(cursor, tabla, columna, tipo)

    conn.commit()
    conn.close()

    _COLUMNAS_ORDENES_ASEGURADAS = True


# =====================================================
# NUMERACIÓN OT
# =====================================================

def obtener_curso_escolar(fecha=None):
    if fecha is None:
        fecha = date.today()

    año = fecha.year

    # El nuevo curso de mantenimiento comienza el 24 de agosto.
    if fecha.month > 8 or (fecha.month == 8 and fecha.day >= 24):
        return f"{año}-{año + 1}"

    return f"{año - 1}-{año}"


def obtener_codigo_curso_escolar(fecha=None):
    curso = obtener_curso_escolar(fecha)
    inicio, fin = curso.split("-")
    return f"{inicio[-2:]}{fin[-2:]}"


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


def asegurar_tabla_contador_ot():
    global _TABLA_CONTADOR_ASEGURADA

    if _TABLA_CONTADOR_ASEGURADA:
        return

    conn = conectar()
    cursor = conn.cursor()

    modulo = conn.__class__.__module__.lower()
    es_postgres = "psycopg2" in modulo or "postgres" in modulo

    if es_postgres:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contador_ot (
                id SERIAL PRIMARY KEY,
                centro_codigo TEXT NOT NULL,
                tipo_codigo TEXT NOT NULL,
                ultimo_numero INTEGER DEFAULT 0,
                UNIQUE(centro_codigo, tipo_codigo)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contador_ot_curso (
                id SERIAL PRIMARY KEY,
                centro_codigo TEXT NOT NULL,
                tipo_codigo TEXT NOT NULL,
                curso_escolar TEXT NOT NULL,
                curso_codigo TEXT NOT NULL,
                ultimo_numero INTEGER DEFAULT 0,
                UNIQUE(centro_codigo, tipo_codigo, curso_escolar)
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contador_ot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                centro_codigo TEXT NOT NULL,
                tipo_codigo TEXT NOT NULL,
                ultimo_numero INTEGER DEFAULT 0,
                UNIQUE(centro_codigo, tipo_codigo)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contador_ot_curso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                centro_codigo TEXT NOT NULL,
                tipo_codigo TEXT NOT NULL,
                curso_escolar TEXT NOT NULL,
                curso_codigo TEXT NOT NULL,
                ultimo_numero INTEGER DEFAULT 0,
                UNIQUE(centro_codigo, tipo_codigo, curso_escolar)
            )
        """)

    conn.commit()
    conn.close()

    _TABLA_CONTADOR_ASEGURADA = True


def obtener_siguiente_numero_ot(centro="", tipo_ot="INC"):
    """
    Genera el siguiente número de OT de forma segura.

    PostgreSQL:
    - incremento atómico;
    - evita números duplicados si dos usuarios crean OT a la vez.

    SQLite:
    - mantiene compatibilidad para uso local;
    - bloquea brevemente la escritura durante la numeración.
    """
    asegurar_tabla_contador_ot()

    conn = conectar()
    cursor = conn.cursor()

    centro_codigo = obtener_codigo_centro(
        centro
    )

    tipo_codigo = obtener_codigo_tipo(
        tipo_ot
    )

    curso_escolar = obtener_curso_escolar()
    curso_codigo = obtener_codigo_curso_escolar()

    modulo = conn.__class__.__module__.lower()

    es_postgres = (
        "psycopg2" in modulo
        or "postgres" in modulo
    )

    try:

        # =================================================
        # POSTGRESQL / RENDER
        # =================================================
        if es_postgres:

            cursor.execute("""
                INSERT INTO contador_ot_curso
                (
                    centro_codigo,
                    tipo_codigo,
                    curso_escolar,
                    curso_codigo,
                    ultimo_numero
                )
                VALUES (%s, %s, %s, %s, 1)

                ON CONFLICT
                (
                    centro_codigo,
                    tipo_codigo,
                    curso_escolar
                )

                DO UPDATE
                SET ultimo_numero =
                    contador_ot_curso.ultimo_numero + 1,
                    curso_codigo = EXCLUDED.curso_codigo

                RETURNING ultimo_numero
            """, (
                centro_codigo,
                tipo_codigo,
                curso_escolar,
                curso_codigo,
            ))

            fila = cursor.fetchone()

            siguiente = int(
                fila[0]
            )

        # =================================================
        # SQLITE / LOCAL
        # =================================================
        else:

            cursor.execute(
                "BEGIN IMMEDIATE"
            )

            cursor.execute("""
                SELECT ultimo_numero
                FROM contador_ot_curso
                WHERE centro_codigo = ?
                  AND tipo_codigo = ?
                  AND curso_escolar = ?
            """, (
                centro_codigo,
                tipo_codigo,
                curso_escolar,
            ))

            fila = cursor.fetchone()

            if fila:

                siguiente = (
                    int(fila[0])
                    + 1
                )

                cursor.execute("""
                    UPDATE contador_ot_curso
                    SET ultimo_numero = ?,
                        curso_codigo = ?
                    WHERE centro_codigo = ?
                      AND tipo_codigo = ?
                      AND curso_escolar = ?
                """, (
                    siguiente,
                    curso_codigo,
                    centro_codigo,
                    tipo_codigo,
                    curso_escolar,
                ))

            else:

                siguiente = 1

                cursor.execute("""
                    INSERT INTO contador_ot_curso
                    (
                        centro_codigo,
                        tipo_codigo,
                        curso_escolar,
                        curso_codigo,
                        ultimo_numero
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    centro_codigo,
                    tipo_codigo,
                    curso_escolar,
                    curso_codigo,
                    siguiente,
                ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return (
        f"{tipo_codigo}-"
        f"{centro_codigo}-"
        f"{curso_codigo}-"
        f"{siguiente:04d}"
    )


def detectar_tipo_ot_para_numero(origen="", tipo_orden="Interna"):
    origen_txt = str(origen or "").strip().upper()
    tipo_orden_txt = str(tipo_orden or "").strip().lower()

    if origen_txt in ["LEGIONELLA", "LEG"]:
        return "LEG"

    if origen_txt in ["PREVENTIVO", "PREV"]:
        return "PREV"

    if tipo_orden_txt == "externa" or origen_txt in ["EXTERNA", "EXT", "EMPRESA"]:
        return "EXT"

    return "INC"


# =====================================================
# VINCULACIÓN ORIGEN OT
# =====================================================

def vincular_origen_ot(
    numero_ot,
    origen_tabla=None,
    origen_id=None,
    id_punto_legionella=None,
    id_preventivo=None,
    id_incidencia=None,
):
    """
    Vincula una OT con su origen real.
    Permite que el Corazón del Sistema abra la OT sin depender de textos.
    """

    asegurar_columnas_observaciones_estado()

    if not numero_ot:
        return False

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE ordenes_trabajo
            SET origen_tabla = ?,
                origen_id = ?,
                id_punto_legionella = ?,
                id_preventivo = ?,
                id_incidencia = ?
            WHERE numero_ot = ?
        """), (
            origen_tabla,
            origen_id,
            id_punto_legionella,
            id_preventivo,
            id_incidencia,
            numero_ot,
        ))

        conn.commit()
        ok = True

    except Exception:
        ok = False

    finally:
        conn.close()

    return ok


def obtener_vinculacion_ot(numero_ot=None, id_orden=None):
    """
    Devuelve la vinculación de una OT, si existe.
    """

    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    try:
        if id_orden is not None:
            cursor.execute(_sql("""
                SELECT origen_tabla,
                       origen_id,
                       id_punto_legionella,
                       id_preventivo,
                       id_incidencia
                FROM ordenes_trabajo
                WHERE id = ?
            """), (id_orden,))
        else:
            cursor.execute(_sql("""
                SELECT origen_tabla,
                       origen_id,
                       id_punto_legionella,
                       id_preventivo,
                       id_incidencia
                FROM ordenes_trabajo
                WHERE numero_ot = ?
            """), (numero_ot,))

        fila = cursor.fetchone()

    except Exception:
        fila = None

    finally:
        conn.close()

    if not fila:
        return {
            "origen_tabla": None,
            "origen_id": None,
            "id_punto_legionella": None,
            "id_preventivo": None,
            "id_incidencia": None,
        }

    return {
        "origen_tabla": fila[0],
        "origen_id": fila[1],
        "id_punto_legionella": fila[2],
        "id_preventivo": fila[3],
        "id_incidencia": fila[4],
    }


# =====================================================
# TELEGRAM
# =====================================================

def avisar_telegram_nueva_ot(
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
    tipo_orden
):
    if enviar_telegram is None:
        return False

    try:
        origen_txt = str(origen or "").strip().upper()
        prioridad_txt = str(prioridad or "").strip().upper()

        icono = "🔔"

        if origen_txt in ["LEGIONELLA", "LEG"]:
            icono = "🚨"
        elif prioridad_txt in ["ALTA", "URGENTE"]:
            icono = "⚠️"
        elif origen_txt in ["OUTLOOK", "APP", "PROFESORES"]:
            icono = "📩"
        elif origen_txt in ["PREVENTIVO", "PREV"]:
            icono = "🔧"
        elif origen_txt in ["EXTERNA", "EXT", "EMPRESA"]:
            icono = "🏢"

        mensaje = f"""
{icono} NUEVA ORDEN DE TRABAJO

OT: {numero_ot}
Estado: {estado}
Prioridad: {prioridad or "-"}
Tipo: {tipo_orden or "-"}
Origen: {origen or "-"}

Centro: {centro or "-"}
Edificio: {edificio or "-"}
Espacio: {espacio or "-"}
Área: {area or "-"}

Operario asignado: {operario or "-"}
Solicitante: {solicitante or "-"}

Descripción:
{descripcion or "-"}
"""

        return enviar_telegram(mensaje, centro)

    except Exception:
        return False


# =====================================================
# CREAR / OBTENER ÓRDENES
# =====================================================

def crear_orden(datos):
    asegurar_columnas_observaciones_estado()

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

    tipo_orden = datos[14] if len(datos) > 14 else "Interna"
    empresa_externa = datos[15] if len(datos) > 15 else ""
    contacto_empresa = datos[16] if len(datos) > 16 else ""
    telefono_empresa = datos[17] if len(datos) > 17 else ""
    email_empresa = datos[18] if len(datos) > 18 else ""
    # Dato opcional añadido al final para no romper llamadas antiguas
    

    if len(datos) > 27:
        fecha_aviso_empresa = datos[19] if len(datos) > 19 else ""
        fecha_realizacion = datos[20] if len(datos) > 20 else ""
        trabajo_a_realizar = datos[21] if len(datos) > 21 else ""
        trabajo_realizado = datos[22] if len(datos) > 22 else ""
        firma_operario = datos[23] if len(datos) > 23 else ""
        fecha_firma_operario = datos[24] if len(datos) > 24 else ""
        coste_estimado = datos[25] if len(datos) > 25 else 0
        coste_final = datos[26] if len(datos) > 26 else 0
        observaciones_estado = datos[27] if len(datos) > 27 else ""
    else:
        fecha_aviso_empresa = datos[19] if len(datos) > 19 else ""
        fecha_realizacion = datos[20] if len(datos) > 20 else ""
        trabajo_a_realizar = ""
        trabajo_realizado = ""
        firma_operario = ""
        fecha_firma_operario = ""
        coste_estimado = datos[21] if len(datos) > 21 else 0
        coste_final = datos[22] if len(datos) > 22 else 0
        observaciones_estado = datos[23] if len(datos) > 23 else ""

    fecha_programada = fecha_aviso_empresa

    if not tipo_solicitante:
        tipo_solicitante = "Operarios"

    if not tipo_orden:
        tipo_orden = "Interna"

    if tipo_orden == "Externa":
        operario = "Proveedor externo"

        if not estado or estado == "Abierta":
            estado = "Avisado"

        if not origen or origen == "APP":
            origen = "EXTERNA"

    # -------------------------------------------------
    # CLASIFICACIÓN AUTOMÁTICA DEL ÁREA
    # -------------------------------------------------
    area = sugerir_area_ot(
        descripcion=descripcion,
        area_actual=area,
        origen=origen,
        tipo_orden=tipo_orden
    )

    if not numero_ot:
        tipo_para_numero = detectar_tipo_ot_para_numero(origen, tipo_orden)
        numero_ot = obtener_siguiente_numero_ot(centro, tipo_para_numero)

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
            fecha_aviso_empresa,
            fecha_realizacion,
            trabajo_a_realizar,
            trabajo_realizado,
            firma_operario,
            fecha_firma_operario,
            coste_estimado,
            coste_final,
            observaciones_estado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        fecha_aviso_empresa,
        fecha_realizacion,
        trabajo_a_realizar,
        trabajo_realizado,
        firma_operario,
        fecha_firma_operario,
        coste_estimado,
        coste_final,
        observaciones_estado
    ))

    conn.commit()
    conn.close()

    avisar_telegram_nueva_ot(
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
        tipo_orden
    )

    return numero_ot


def obtener_ordenes():
    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, numero_ot, descripcion, estado, fecha_creacion,
               centro, edificio, espacio, area, prioridad, operario, origen,
               solicitante, fecha_origen, foto, tipo_solicitante,
               tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
               email_empresa, fecha_programada, fecha_realizacion,
               coste_estimado, coste_final, observaciones_estado
        FROM ordenes_trabajo
        ORDER BY id DESC
    """)

    datos = cursor.fetchall()
    conn.close()
    return datos

def obtener_historico_operario(operario, limite=500):
    """
    Devuelve únicamente el histórico del operario solicitado.

    No sustituye obtener_historico(), para mantener compatibilidad
    con las pantallas existentes.

    El límite protege la pantalla del operario cuando el histórico
    crezca con los años.
    """
    asegurar_columnas_observaciones_estado()

    operario = str(operario or "").strip()

    if not operario:
        return []

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT id, numero_ot, descripcion, estado, fecha_creacion,
                   centro, edificio, espacio, area, prioridad, operario, origen,
                   solicitante, fecha_origen, fecha_cierre,
                   observaciones_cierre, foto,
                   tipo_solicitante,
                   tipo_orden, empresa_externa, contacto_empresa,
                   telefono_empresa, email_empresa,
                   fecha_programada, fecha_realizacion,
                   coste_estimado, coste_final,
                   observaciones_estado
            FROM historico_ordenes
            WHERE LOWER(TRIM(COALESCE(operario, ''))) =
                  LOWER(TRIM(?))
            ORDER BY id DESC
            LIMIT ?
        """), (
            operario,
            int(limite),
        ))

        return cursor.fetchall()

    finally:
        conn.close()

def obtener_historico_reciente(limite=500):
    """
    Devuelve las últimas OT del histórico.

    Se mantiene obtener_historico() para compatibilidad
    con otras partes de la aplicación.
    """
    asegurar_columnas_observaciones_estado()

    try:
        limite = int(limite)
    except Exception:
        limite = 500

    limite = max(1, min(limite, 2000))

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT id, numero_ot, descripcion, estado, fecha_creacion,
                   centro, edificio, espacio, area, prioridad, operario,
                   origen, solicitante, fecha_origen, fecha_cierre,
                   observaciones_cierre, foto, tipo_solicitante,
                   tipo_orden, empresa_externa, contacto_empresa,
                   telefono_empresa, email_empresa,
                   fecha_programada, fecha_realizacion,
                   coste_estimado, coste_final,
                   observaciones_estado
            FROM historico_ordenes
            ORDER BY id DESC
            LIMIT ?
        """), (
            limite,
        ))

        return cursor.fetchall()

    finally:
        conn.close()


def obtener_historico():
    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, numero_ot, descripcion, estado, fecha_creacion,
               centro, edificio, espacio, area, prioridad, operario, origen,
               solicitante, fecha_origen, fecha_cierre, observaciones_cierre, foto,
               tipo_solicitante,
               tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
               email_empresa, fecha_programada, fecha_realizacion,
               coste_estimado, coste_final, observaciones_estado
        FROM historico_ordenes
        ORDER BY id DESC
    """)

    datos = cursor.fetchall()
    conn.close()
    return datos


def obtener_ordenes_operario(operario):
    asegurar_columnas_observaciones_estado()

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
                   coste_estimado, coste_final, observaciones_estado
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
                   coste_estimado, coste_final, observaciones_estado
            FROM ordenes_trabajo
            ORDER BY id DESC
        """)

    datos = cursor.fetchall()
    conn.close()
    return datos


def obtener_detalle_orden_externa(id_orden):
    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT fecha_aviso_empresa,
               trabajo_a_realizar,
               trabajo_realizado,
               firma_operario,
               fecha_firma_operario
        FROM ordenes_trabajo
        WHERE id = ?
    """), (id_orden,))

    fila = cursor.fetchone()
    conn.close()

    if not fila:
        return {
            "fecha_aviso_empresa": "",
            "trabajo_a_realizar": "",
            "trabajo_realizado": "",
            "firma_operario": "",
            "fecha_firma_operario": "",
        }

    return {
        "fecha_aviso_empresa": fila[0] or "",
        "trabajo_a_realizar": fila[1] or "",
        "trabajo_realizado": fila[2] or "",
        "firma_operario": fila[3] or "",
        "fecha_firma_operario": fila[4] or "",
    }


# =====================================================
# ACTUALIZAR ESTADO / OBSERVACIONES
# =====================================================

def _pausar_ot_en_curso_del_operario(
    cursor,
    id_orden_nueva,
    operario,
    numero_ot_nueva="",
):
    """
    Garantiza una sola OT en curso por operario.

    Las demás OT en curso del mismo operario pasan a En pausa.
    No toca órdenes bloqueadas, finalizadas ni de otros operarios.
    """
    operario_txt = str(operario or "").strip()

    if not operario_txt:
        return []

    cursor.execute(_sql("""
        SELECT id, numero_ot, observaciones_estado
        FROM ordenes_trabajo
        WHERE operario = ?
          AND estado = 'En curso'
          AND id <> ?
    """), (operario_txt, id_orden_nueva))

    anteriores = cursor.fetchall()
    pausadas = []
    fecha_pausa = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for id_anterior, numero_ot_anterior, observaciones_anteriores in anteriores:
        nota = (
            f"Pausada automáticamente el {fecha_pausa} al iniciar "
            f"la OT {numero_ot_nueva or id_orden_nueva}."
        )

        observaciones_previas = str(observaciones_anteriores or "").strip()
        observaciones_nuevas = (
            f"{observaciones_previas}\n{nota}"
            if observaciones_previas
            else nota
        )

        cursor.execute(_sql("""
            UPDATE ordenes_trabajo
            SET estado = 'En pausa',
                observaciones_estado = ?
            WHERE id = ?
        """), (observaciones_nuevas, id_anterior))

        pausadas.append({
            "id": id_anterior,
            "numero_ot": numero_ot_anterior,
        })

    return pausadas


def actualizar_estado(id_orden, nuevo_estado, observaciones_estado=None):
    """
    Actualiza el estado de una OT.

    Regla Corazón 4.0:
    al poner una OT En curso, cualquier otra OT En curso del mismo
    operario pasa automáticamente a En pausa.
    """
    if nuevo_estado not in ESTADOS_VALIDOS:
        return {
            "ok": False,
            "motivo": "estado_no_valido",
            "estado": nuevo_estado,
            "pausadas": [],
        }

    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT numero_ot, operario, estado
            FROM ordenes_trabajo
            WHERE id = ?
        """), (id_orden,))

        orden = cursor.fetchone()

        if not orden:
            return {
                "ok": False,
                "motivo": "orden_no_encontrada",
                "estado": nuevo_estado,
                "pausadas": [],
            }

        numero_ot, operario, estado_anterior = orden
        pausadas = []

        if nuevo_estado == "En curso":
            pausadas = _pausar_ot_en_curso_del_operario(
                cursor=cursor,
                id_orden_nueva=id_orden,
                operario=operario,
                numero_ot_nueva=numero_ot,
            )

        if observaciones_estado is None:
            cursor.execute(_sql("""
                UPDATE ordenes_trabajo
                SET estado = ?
                WHERE id = ?
            """), (nuevo_estado, id_orden))
        else:
            cursor.execute(_sql("""
                UPDATE ordenes_trabajo
                SET estado = ?,
                    observaciones_estado = ?
                WHERE id = ?
            """), (nuevo_estado, observaciones_estado, id_orden))

        conn.commit()

        return {
            "ok": True,
            "id_orden": id_orden,
            "numero_ot": numero_ot,
            "operario": operario,
            "estado_anterior": estado_anterior,
            "estado": nuevo_estado,
            "pausadas": pausadas,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def actualizar_observaciones_estado(id_orden, observaciones_estado):
    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE ordenes_trabajo
        SET observaciones_estado = ?
        WHERE id = ?
    """), (observaciones_estado, id_orden))

    conn.commit()
    conn.close()

    return True


def finalizar_trabajo_externo(
    id_orden,
    trabajo_realizado="",
    firma_operario="",
    coste_final=0,
    observaciones_estado=""
):
    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(_sql("""
        UPDATE ordenes_trabajo
        SET trabajo_realizado = ?,
            firma_operario = ?,
            fecha_firma_operario = ?,
            fecha_realizacion = ?,
            coste_final = ?,
            observaciones_estado = ?,
            estado = 'Cerrado'
        WHERE id = ?
    """), (
        trabajo_realizado,
        firma_operario,
        fecha_actual,
        fecha_actual,
        coste_final,
        observaciones_estado,
        id_orden
    ))

    conn.commit()
    conn.close()

    return True


# =====================================================
# FINALIZAR
# =====================================================

def finalizar_orden(id_orden, observaciones=""):
    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT numero_ot, descripcion, estado, fecha_creacion,
               centro, edificio, espacio, area, prioridad, operario, origen,
               solicitante, fecha_origen, foto, tipo_solicitante,
               tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
               email_empresa, fecha_programada, fecha_aviso_empresa, fecha_realizacion,
               trabajo_a_realizar, trabajo_realizado, firma_operario,
               fecha_firma_operario, coste_estimado, coste_final,
               observaciones_estado,
               origen_tabla, origen_id, id_punto_legionella, id_preventivo, id_incidencia
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
            email_empresa, fecha_programada, fecha_aviso_empresa, fecha_realizacion,
            trabajo_a_realizar, trabajo_realizado, firma_operario,
            fecha_firma_operario, coste_estimado, coste_final,
            observaciones_estado,
            origen_tabla, origen_id, id_punto_legionella, id_preventivo, id_incidencia
        ) = orden

        if tipo_orden == "Externa":
            if not operario:
                operario = "Proveedor externo"

            if not origen:
                origen = "EXTERNA"

            if not fecha_realizacion:
                fecha_realizacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                fecha_aviso_empresa,
                fecha_realizacion,
                trabajo_a_realizar,
                trabajo_realizado,
                firma_operario,
                fecha_firma_operario,
                coste_estimado,
                coste_final,
                observaciones_estado,
                origen_tabla,
                origen_id,
                id_punto_legionella,
                id_preventivo,
                id_incidencia
            )
            VALUES (?, ?, 'Finalizada', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            fecha_aviso_empresa,
            fecha_realizacion,
            trabajo_a_realizar,
            trabajo_realizado,
            firma_operario,
            fecha_firma_operario,
            coste_estimado,
            coste_final,
            observaciones_estado,
            origen_tabla,
            origen_id,
            id_punto_legionella,
            id_preventivo,
            id_incidencia
        ))

        if registrar_historial_espacio is not None:
            try:
                registrar_historial_espacio(
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    elemento="",
                    tipo="OT finalizada",
                    numero_ot=numero_ot,
                    descripcion=descripcion,
                    area=area,
                    estado="Finalizada",
                    operario=operario,
                    observaciones=observaciones
                )
            except Exception:
                pass

        try:
            origen_txt = str(origen or "").upper()
            descripcion_txt = str(descripcion or "")

            if origen_txt == "INVENTARIO":
                import re
                match = re.search(r"OT origen:\s*INV-(\d+)", descripcion_txt)

                if match:
                    id_elemento_inv = int(match.group(1))

                    from modules.inventario_aulas import cerrar_correctivo_inventario

                    cerrar_correctivo_inventario(
                        id_elemento=id_elemento_inv,
                        estado_final="Correcto"
                    )

        except Exception:
            pass

        cursor.execute(_sql("DELETE FROM ordenes_trabajo WHERE id = ?"), (id_orden,))

    conn.commit()
    conn.close()
# =====================================================
# RECLASIFICAR ÁREAS DE OT ANTIGUAS
# =====================================================

def _area_pendiente_clasificacion(area):
    """
    Indica si un área puede ser reclasificada automáticamente.
    Solo considera áreas vacías, Otro u Otros.
    """

    area_txt = str(area or "").strip().lower()

    return area_txt in [
        "",
        "otro",
        "otros",
        "-",
        "sin área",
        "sin area",
        "no definida",
        "no definido",
    ]


def obtener_propuestas_reclasificacion_areas():
    """
    Analiza OT abiertas e históricas sin modificar la base de datos.

    Devuelve una lista de propuestas con:
    - tabla
    - id
    - numero_ot
    - descripcion
    - area_actual
    - area_propuesta
    - origen
    """

    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    propuestas = []

    tablas = [
        "ordenes_trabajo",
        "historico_ordenes",
    ]

    try:
        for tabla in tablas:
            cursor.execute(f"""
                SELECT id,
                       numero_ot,
                       descripcion,
                       area,
                       origen,
                       tipo_orden
                FROM {tabla}
                ORDER BY id DESC
            """)

            filas = cursor.fetchall()

            for fila in filas:
                (
                    id_orden,
                    numero_ot,
                    descripcion,
                    area_actual,
                    origen,
                    tipo_orden,
                ) = fila

                if not _area_pendiente_clasificacion(area_actual):
                    continue

                area_propuesta = sugerir_area_ot(
                    descripcion=descripcion,
                    area_actual=area_actual,
                    origen=origen,
                    tipo_orden=tipo_orden,
                )

                if not area_propuesta:
                    continue

                if str(area_propuesta).strip().lower() == "otros":
                    continue

                propuestas.append({
                    "tabla": tabla,
                    "id": id_orden,
                    "numero_ot": numero_ot or "",
                    "descripcion": descripcion or "",
                    "area_actual": area_actual or "Otros",
                    "area_propuesta": area_propuesta,
                    "origen": origen or "",
                })

    except Exception as e:
        propuestas = []
        raise RuntimeError(
            f"No se pudieron obtener las propuestas de reclasificación: {e}"
        )

    finally:
        conn.close()

    return propuestas


def aplicar_reclasificacion_areas(propuestas):
    """
    Aplica las propuestas previamente revisadas.

    Solo actualiza registros cuyo área todavía continúa vacía,
    como Otro u Otros. Esto evita sobrescribir cambios manuales
    realizados después de generar la vista previa.
    """

    if not propuestas:
        return {
            "actualizadas": 0,
            "omitidas": 0,
            "errores": [],
            "por_area": {},
        }

    asegurar_columnas_observaciones_estado()

    conn = conectar()
    cursor = conn.cursor()

    actualizadas = 0
    omitidas = 0
    errores = []
    por_area = {}

    tablas_permitidas = {
        "ordenes_trabajo",
        "historico_ordenes",
    }

    try:
        for propuesta in propuestas:
            tabla = str(propuesta.get("tabla") or "").strip()
            id_orden = propuesta.get("id")
            area_propuesta = str(
                propuesta.get("area_propuesta") or ""
            ).strip()

            if tabla not in tablas_permitidas:
                omitidas += 1
                continue

            if not id_orden or not area_propuesta:
                omitidas += 1
                continue

            if area_propuesta == "Otros":
                omitidas += 1
                continue

            cursor.execute(
                _sql(f"""
                    SELECT area
                    FROM {tabla}
                    WHERE id = ?
                """),
                (id_orden,)
            )

            fila_actual = cursor.fetchone()

            if not fila_actual:
                omitidas += 1
                continue

            area_actual = fila_actual[0]

            if not _area_pendiente_clasificacion(area_actual):
                omitidas += 1
                continue

            cursor.execute(
                _sql(f"""
                    UPDATE {tabla}
                    SET area = ?
                    WHERE id = ?
                """),
                (
                    area_propuesta,
                    id_orden,
                )
            )

            actualizadas += 1

            por_area[area_propuesta] = (
                por_area.get(area_propuesta, 0) + 1
            )

        conn.commit()

    except Exception as e:
        conn.rollback()
        errores.append(str(e))

    finally:
        conn.close()

    return {
        "actualizadas": actualizadas,
        "omitidas": omitidas,
        "errores": errores,
        "por_area": por_area,
    }

# =====================================================
# BORRADOS
# =====================================================

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


# =====================================================
# OTROS
# =====================================================

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

def _texto_normalizado_correctiva(texto):
    texto = str(texto or "").strip().lower()

    cambios = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }

    for origen, destino in cambios.items():
        texto = texto.replace(origen, destino)

    return texto


def clasificar_correctiva_desde_revision(
    descripcion_defecto,
    area_origen="",
    prioridad_origen="Media",
):
    """
    Clasifica una avería encontrada durante una revisión/preventivo.

    Filosofía:
    - La correctiva no hereda ciegamente 'Preventivo' como área.
    - Agua, electricidad y climatización tienen peso operativo.
    - Urgente solo cuando el texto indica riesgo/afectación activa.
    """
    texto = _texto_normalizado_correctiva(
        descripcion_defecto
    )

    area_final = str(area_origen or "").strip()
    prioridad_final = str(
        prioridad_origen or "Media"
    ).strip()

    # -------------------------------------------------
    # FONTANERÍA / AGUA
    # -------------------------------------------------
    palabras_agua = [
        "fluxor",
        "cisterna",
        "grifo",
        "lavabo",
        "lavamanos",
        "inodoro",
        "wc",
        "tuberia",
        "desague",
        "sifon",
        "valvula",
        "agua",
        "fuga",
    ]

    if any(palabra in texto for palabra in palabras_agua):
        area_final = "Fontanería"

        # Elemento de agua averiado = prioridad alta.
        prioridad_final = "Alta"

        # Riesgo activo = urgente.
        riesgo_activo = [
            "fuga",
            "pierde agua",
            "perdiendo agua",
            "sale agua",
            "chorro",
            "inund",
            "revent",
            "no corta",
            "no cierra",
        ]

        if any(palabra in texto for palabra in riesgo_activo):
            prioridad_final = "Urgente"

        return area_final, prioridad_final

    # -------------------------------------------------
    # ELECTRICIDAD
    # -------------------------------------------------
    palabras_electricidad = [
        "electrico",
        "electricidad",
        "enchufe",
        "magnetotermico",
        "diferencial",
        "cuadro electrico",
        "cortocircuito",
        "chisp",
        "cable",
    ]

    if any(
        palabra in texto
        for palabra in palabras_electricidad
    ):
        area_final = "Electricidad"
        prioridad_final = "Alta"

        if any(
            palabra in texto
            for palabra in [
                "chisp",
                "quem",
                "humo",
                "cortocircuito",
                "descarga",
            ]
        ):
            prioridad_final = "Urgente"

        return area_final, prioridad_final

    # -------------------------------------------------
    # CLIMATIZACIÓN
    # -------------------------------------------------
    palabras_clima = [
        "climatizacion",
        "aire acondicionado",
        "split",
        "calefaccion",
        "radiador",
        "caldera",
    ]

    if any(
        palabra in texto
        for palabra in palabras_clima
    ):
        area_final = "Climatización"

        if prioridad_final.lower() in [
            "",
            "baja",
            "media",
        ]:
            prioridad_final = "Alta"

        return area_final, prioridad_final

    # -------------------------------------------------
    # RESTO
    # -------------------------------------------------
    if not area_final or area_final.lower() in [
        "preventivo",
        "preventiva",
        "mantenimiento",
    ]:
        try:
            area_detectada = sugerir_area_ot(
                descripcion=descripcion_defecto,
                area_actual="",
                origen="",
                tipo_orden="Interna",
            )

            if area_detectada:
                area_final = area_detectada

        except Exception:
            pass

    if not area_final:
        area_final = "Otros"

    return area_final, prioridad_final
def crear_correctiva_desde_ot(
    centro,
    edificio,
    espacio,
    area,
    prioridad,
    operario,
    descripcion_defecto,
    numero_ot_origen="",
    origen="Preventivo",
    solicitante="Operarios",
):
    descripcion_defecto = str(
        descripcion_defecto or ""
    ).strip()

    if not descripcion_defecto:
        return False, "No hay defecto indicado."

    numero_ot = obtener_siguiente_numero_ot(
        centro,
        "INC"
    )

    # La correctiva analiza el defecto encontrado.
    # No hereda ciegamente área/prioridad del preventivo.
    area_correctiva, prioridad_correctiva = (
        clasificar_correctiva_desde_revision(
            descripcion_defecto=descripcion_defecto,
            area_origen=area,
            prioridad_origen=prioridad,
        )
    )

    descripcion = (
        f"[CORRECTIVA DESDE {str(origen or '').upper()}]\n"
        f"OT origen: {numero_ot_origen}\n\n"
        f"{descripcion_defecto}"
    )

    numero_creado = crear_orden((
        numero_ot,
        descripcion,
        "Abierta",
        centro,
        edificio,
        espacio,
        area_correctiva,
        prioridad_correctiva,
        operario,
        origen,                 # Conservamos trazabilidad
        solicitante,
        "",
        "",
        "Operarios",
        "Interna",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        0,
        0,
        ""
    ))

    return (
        True,
        f"Correctiva creada correctamente: "
        f"{numero_creado or numero_ot}"
    )


# =====================================================
# FOTOS OT
# =====================================================

def asegurar_tabla_ordenes_fotos():
    global _TABLA_FOTOS_ASEGURADA

    if _TABLA_FOTOS_ASEGURADA:
        return

    conn = conectar()
    cursor = conn.cursor()

    modulo = conn.__class__.__module__.lower()
    es_postgres = "psycopg2" in modulo or "postgres" in modulo

    if es_postgres:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordenes_fotos (
                id SERIAL PRIMARY KEY,
                numero_ot TEXT,
                nombre_foto TEXT,
                foto_data BYTEA,
                fecha_subida TEXT
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordenes_fotos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_ot TEXT,
                nombre_foto TEXT,
                foto_data BLOB,
                fecha_subida TEXT
            )
        """)

    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ordenes_fotos_numero_ot
            ON ordenes_fotos(numero_ot)
        """)
    except Exception:
        pass

    conn.commit()
    conn.close()

    _TABLA_FOTOS_ASEGURADA = True


def guardar_foto_ot(numero_ot, nombre_foto, foto_data):
    asegurar_tabla_ordenes_fotos()

    conn = conectar()
    cursor = conn.cursor()

    fecha_subida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(_sql("""
        INSERT INTO ordenes_fotos
        (
            numero_ot,
            nombre_foto,
            foto_data,
            fecha_subida
        )
        VALUES (?, ?, ?, ?)
    """), (
        numero_ot,
        nombre_foto,
        foto_data,
        fecha_subida
    ))

    conn.commit()
    conn.close()


def obtener_fotos_ot(numero_ot):
    asegurar_tabla_ordenes_fotos()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT nombre_foto, foto_data
        FROM ordenes_fotos
        WHERE numero_ot = ?
        ORDER BY id ASC
    """), (numero_ot,))

    datos = cursor.fetchall()
    conn.close()

    return datos
