from datetime import datetime
from database.db import conectar


ELEMENTOS_BASE_AULA = [
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


def hoy():
    return datetime.now().strftime("%Y-%m-%d")


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def crear_tabla_inventario_aulas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario_aulas (
            id SERIAL PRIMARY KEY,
            fecha_revision TEXT,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            elemento TEXT,
            cantidad INTEGER,
            estado TEXT,
            ancho REAL,
            alto REAL,
            fondo REAL,
            unidad TEXT,
            observaciones TEXT,
            foto TEXT,
            operario TEXT,
            fecha_creacion TEXT
        )
    """)

    conn.commit()
    conn.close()


def guardar_inventario_aula(
    centro,
    edificio,
    espacio,
    elemento,
    cantidad,
    estado,
    ancho,
    alto,
    fondo,
    unidad,
    observaciones,
    foto,
    operario
):
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO inventario_aulas (
            fecha_revision,
            centro,
            edificio,
            espacio,
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
            fecha_creacion
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        hoy(),
        centro,
        edificio,
        espacio,
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
        ahora()
    ))

    conn.commit()
    conn.close()
    return True


def obtener_inventario_aulas():
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            fecha_revision,
            centro,
            edificio,
            espacio,
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
            fecha_creacion
        FROM inventario_aulas
        ORDER BY fecha_creacion DESC
    """)

    datos = cursor.fetchall()
    conn.close()
    return datos


def obtener_inventario_por_aula(centro, edificio, espacio):
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            fecha_revision,
            centro,
            edificio,
            espacio,
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
            fecha_creacion
        FROM inventario_aulas
        WHERE centro = %s
          AND edificio = %s
          AND espacio = %s
        ORDER BY elemento ASC, fecha_creacion DESC
    """, (
        centro,
        edificio,
        espacio
    ))

    datos = cursor.fetchall()
    conn.close()
    return datos


def obtener_elementos_aula_para_revision(centro, edificio, espacio):
    inventario = obtener_inventario_por_aula(centro, edificio, espacio)

    if inventario:
        elementos = []

        for item in inventario:
            elemento = str(item[5] or "").strip()
            cantidad = item[6]

            if not elemento:
                continue

            try:
                cantidad_num = int(float(cantidad or 0))
            except Exception:
                cantidad_num = 0

            if cantidad_num > 1:
                texto = f"{elemento} ({cantidad_num})"
            else:
                texto = elemento

            if texto not in elementos:
                elementos.append(texto)

        if elementos:
            return elementos

    return ELEMENTOS_BASE_AULA


def eliminar_elemento_inventario_aula(id_elemento):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM inventario_aulas
        WHERE id = %s
    """, (id_elemento,))

    conn.commit()
    conn.close()
    return True
