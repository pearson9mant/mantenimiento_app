from datetime import datetime
from database.db import conectar, _sql
from modules.ordenes import crear_orden, obtener_siguiente_numero_ot

try:
    from modules.inventario_aulas import obtener_elementos_aula_para_revision
except Exception:
    obtener_elementos_aula_para_revision = None


ELEMENTOS_REVISION_AULA = [
    "Mesas",
    "Sillas",
    "Pantalla / proyector",
    "Pizarra",
    "Iluminación",
    "Enchufes visibles",
    "Puerta / maneta",
    "Ventanas / persianas",
    "Papeleras",
    "Estado general del aula",
]


ESTADOS_REVISION_AULA = [
    "Correcto",
    "Revisar",
    "Avería",
]


def hoy_str():
    return datetime.now().strftime("%Y-%m-%d")


def normalizar_texto(texto):
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


def area_por_elemento_aula(elemento):
    elemento_txt = normalizar_texto(elemento)

    if any(x in elemento_txt for x in [
        "luz", "ilumin", "enchufe", "interruptor", "canaleta",
        "cable", "toma corriente", "emergencia"
    ]):
        return "Electricidad"

    if any(x in elemento_txt for x in [
        "proyector", "pantalla", "hdmi", "altavoz", "ordenador",
        "pc", "monitor", "informat", "red", "switch", "wifi",
        "mando", "pizarra digital"
    ]):
        return "Informática"

    if any(x in elemento_txt for x in [
        "puerta", "maneta", "cerradura", "cierrapuertas",
        "ventana", "persiana", "carpinter", "bisagra"
    ]):
        return "Carpintería"

    if any(x in elemento_txt for x in [
        "grifo", "lavabo", "agua", "desague", "cisterna",
        "wc", "inodoro", "fregadero", "fontaner"
    ]):
        return "Fontanería"

    if any(x in elemento_txt for x in [
        "split", "aire", "clima", "climatizacion", "radiador",
        "termostato"
    ]):
        return "Climatización"

    if any(x in elemento_txt for x in [
        "mesa", "silla", "pizarra", "papelera", "estanteria",
        "armario", "mueble", "corcho", "mobiliario"
    ]):
        return "Equipamiento"

    return "Equipamiento"


def elementos_para_revision_aula(centro, edificio, espacio):
    if obtener_elementos_aula_para_revision:
        try:
            elementos = obtener_elementos_aula_para_revision(centro, edificio, espacio)
            if elementos:
                return elementos
        except Exception:
            pass

    return ELEMENTOS_REVISION_AULA


def crear_tablas_preventivo_aulas():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS preventivo_aulas (
            id SERIAL PRIMARY KEY,
            fecha TEXT,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            operario TEXT,
            estado TEXT,
            observaciones TEXT,
            numero_ot_preventiva TEXT
        )
    """))

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS preventivo_aulas_items (
            id SERIAL PRIMARY KEY,
            revision_id INTEGER,
            elemento TEXT,
            estado TEXT,
            observaciones TEXT,
            foto TEXT,
            crear_correctivo INTEGER DEFAULT 0,
            numero_ot_correctiva TEXT
        )
    """))

    conn.commit()
    conn.close()


def crear_revision_aula(
    centro,
    edificio,
    espacio,
    operario,
    observaciones="",
    numero_ot_preventiva=""
):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        INSERT INTO preventivo_aulas
        (
            fecha,
            centro,
            edificio,
            espacio,
            operario,
            estado,
            observaciones,
            numero_ot_preventiva
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """), (
        hoy_str(),
        centro,
        edificio,
        espacio,
        operario,
        "Abierta",
        observaciones,
        numero_ot_preventiva
    ))

    revision_id = cur.fetchone()[0]

    elementos_revision = elementos_para_revision_aula(centro, edificio, espacio)

    for elemento in elementos_revision:
        cur.execute(_sql("""
            INSERT INTO preventivo_aulas_items
            (
                revision_id,
                elemento,
                estado,
                observaciones,
                foto,
                crear_correctivo,
                numero_ot_correctiva
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (
            revision_id,
            elemento,
            "Correcto",
            "",
            "",
            0,
            ""
        ))

    conn.commit()
    conn.close()

    return revision_id


def obtener_revisiones_aulas(limite=100):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, fecha, centro, edificio, espacio, operario,
               estado, observaciones, numero_ot_preventiva
        FROM preventivo_aulas
        ORDER BY id DESC
        LIMIT ?
    """), (limite,))

    datos = cur.fetchall()
    conn.close()

    return datos


def obtener_revision_aula(revision_id):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, fecha, centro, edificio, espacio, operario,
               estado, observaciones, numero_ot_preventiva
        FROM preventivo_aulas
        WHERE id = ?
    """), (revision_id,))

    dato = cur.fetchone()
    conn.close()

    return dato


def obtener_items_revision_aula(revision_id):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, revision_id, elemento, estado,
               observaciones, foto, crear_correctivo,
               numero_ot_correctiva
        FROM preventivo_aulas_items
        WHERE revision_id = ?
        ORDER BY id ASC
    """), (revision_id,))

    datos = cur.fetchall()
    conn.close()

    return datos


def actualizar_item_revision_aula(
    item_id,
    estado,
    observaciones="",
    foto="",
    crear_correctivo=0
):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        UPDATE preventivo_aulas_items
        SET estado = ?,
            observaciones = ?,
            foto = ?,
            crear_correctivo = ?
        WHERE id = ?
    """), (
        estado,
        observaciones,
        foto,
        1 if crear_correctivo else 0,
        item_id
    ))

    conn.commit()
    conn.close()

    return True


def cerrar_revision_aula(revision_id, observaciones=""):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        UPDATE preventivo_aulas
        SET estado = ?,
            observaciones = ?
        WHERE id = ?
    """), (
        "Cerrada",
        observaciones,
        revision_id
    ))

    conn.commit()
    conn.close()

    return True


def obtener_items_con_averia(revision_id):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, revision_id, elemento, estado,
               observaciones, foto, crear_correctivo,
               numero_ot_correctiva
        FROM preventivo_aulas_items
        WHERE revision_id = ?
          AND estado = ?
    """), (
        revision_id,
        "Avería"
    ))

    datos = cur.fetchall()
    conn.close()

    return datos


def obtener_items_a_revisar(revision_id):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, revision_id, elemento, estado,
               observaciones, foto, crear_correctivo,
               numero_ot_correctiva
        FROM preventivo_aulas_items
        WHERE revision_id = ?
          AND estado = ?
    """), (
        revision_id,
        "Revisar"
    ))

    datos = cur.fetchall()
    conn.close()

    return datos


def crear_correctivos_desde_revision(revision_id):
    crear_tablas_preventivo_aulas()

    revision = obtener_revision_aula(revision_id)

    if not revision:
        return 0

    (
        _id,
        fecha,
        centro,
        edificio,
        espacio,
        operario,
        estado_revision,
        observaciones_revision,
        numero_ot_preventiva
    ) = revision

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, elemento, observaciones, foto, numero_ot_correctiva
        FROM preventivo_aulas_items
        WHERE revision_id = ?
          AND estado = ?
          AND crear_correctivo = 1
    """), (
        revision_id,
        "Avería"
    ))

    items = cur.fetchall()

    creadas = 0

    for item in items:
        item_id, elemento, observaciones_item, foto, numero_ot_correctiva = item

        if numero_ot_correctiva:
            continue

        numero = obtener_siguiente_numero_ot(centro, "CORR")

        area = area_por_elemento_aula(elemento)

        descripcion = f"[CORRECTIVO AULA] {elemento} - {espacio}"

        observaciones_ot = f"""
Correctivo generado desde revisión preventiva de aula.

Aula/Espacio: {espacio}
Elemento: {elemento}
Área asignada automáticamente: {area}
Observación: {observaciones_item or "-"}
Fecha revisión: {fecha or hoy_str()}
OT preventiva origen: {numero_ot_preventiva or "-"}
""".strip()

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
            "PREVENTIVO_AULA",
            observaciones_ot,
            foto or "",
            "",
            "Operarios"
        )

        crear_orden(datos_orden)

        cur.execute(_sql("""
            UPDATE preventivo_aulas_items
            SET numero_ot_correctiva = ?
            WHERE id = ?
        """), (
            numero,
            item_id
        ))

        creadas += 1

    conn.commit()
    conn.close()

    return creadas


def obtener_estado_ot(numero_ot):
    if not numero_ot:
        return ""

    posibles_columnas = ["numero_ot", "numero", "codigo"]

    for columna in posibles_columnas:
        conn = conectar()
        cur = conn.cursor()

        try:
            cur.execute(_sql(f"""
                SELECT estado
                FROM ordenes_trabajo
                WHERE {columna} = ?
                LIMIT 1
            """), (numero_ot,))

            fila = cur.fetchone()
            conn.close()

            if fila:
                return str(fila[0] or "")

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()

    return ""


def ot_correctiva_cerrada(numero_ot):
    estado = obtener_estado_ot(numero_ot).lower()

    return estado in [
        "finalizada",
        "cerrado",
        "cerrada",
        "cancelada",
    ]


def resumen_revision_aula(revision_id):
    items = obtener_items_revision_aula(revision_id)

    total = len(items)
    correctos = len([i for i in items if str(i[3]) == "Correcto"])
    revisar = len([i for i in items if str(i[3]) == "Revisar"])

    averias_detectadas = 0
    averias_pendientes = 0
    averias_resueltas = 0

    for i in items:
        estado_item = str(i[3] or "")
        numero_ot_correctiva = str(i[7] or "")

        if estado_item == "Avería":
            averias_detectadas += 1

            if numero_ot_correctiva and ot_correctiva_cerrada(numero_ot_correctiva):
                averias_resueltas += 1
            else:
                averias_pendientes += 1

    return {
        "total": total,
        "correctos": correctos,
        "revisar": revisar,
        "averias": averias_detectadas,
        "averias_detectadas": averias_detectadas,
        "averias_pendientes": averias_pendientes,
        "averias_resueltas": averias_resueltas,
    }
