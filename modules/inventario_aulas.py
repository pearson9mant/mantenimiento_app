from database.db import conectar
from datetime import datetime


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
        datetime.now().strftime("%Y-%m-%d"),
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
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


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
        ORDER BY elemento ASC
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

            if elemento:
                if cantidad and int(cantidad) > 1:
                    elementos.append(f"{elemento} ({cantidad})")
                else:
                    elementos.append(elemento)

        return elementos

    return [
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
