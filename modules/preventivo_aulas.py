from datetime import datetime
from database.db import conectar, _sql
from modules.ordenes import crear_orden, obtener_siguiente_numero_ot


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


def crear_tablas_preventivo_aulas():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS preventivo_aulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            revision_id INTEGER,
            elemento TEXT,
            estado TEXT,
            observaciones TEXT,
            foto TEXT,
            crear_correctivo INTEGER DEFAULT 0,
            numero_ot_correctiva TEXT,
            FOREIGN KEY (revision_id) REFERENCES preventivo_aulas(id)
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

    revision_id = cur.lastrowid

    for elemento in ELEMENTOS_REVISION_AULA:
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
    """
    Crea OTs correctivas solo para los elementos marcados como Avería
    y con crear_correctivo = 1.
    No duplica si el item ya tiene numero_ot_correctiva.
    """
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

        descripcion = f"[CORRECTIVO AULA] {elemento} - {espacio}"

        observaciones_ot = f"""
Correctivo generado desde revisión preventiva de aula.

Aula/Espacio: {espacio}
Elemento: {elemento}
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
            "Equipamiento",
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


def resumen_revision_aula(revision_id):
    items = obtener_items_revision_aula(revision_id)

    total = len(items)
    correctos = len([i for i in items if str(i[3]) == "Correcto"])
    revisar = len([i for i in items if str(i[3]) == "Revisar"])
    averias = len([i for i in items if str(i[3]) == "Avería"])

    return {
        "total": total,
        "correctos": correctos,
        "revisar": revisar,
        "averias": averias,
    }
