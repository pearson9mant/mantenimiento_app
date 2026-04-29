from database.db import conectar
from datetime import datetime


def crear_tabla_inventario_aulas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario_aulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    centro, edificio, espacio, elemento, cantidad, estado,
    ancho, alto, fondo, unidad, observaciones, foto, operario
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO inventario_aulas (
            fecha_revision, centro, edificio, espacio, elemento,
            cantidad, estado, ancho, alto, fondo, unidad,
            observaciones, foto, operario, fecha_creacion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d"),
        centro, edificio, espacio, elemento,
        cantidad, estado, ancho, alto, fondo, unidad,
        observaciones, foto, operario,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def obtener_inventario_aulas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id, fecha_revision, centro, edificio, espacio, elemento,
            cantidad, estado, ancho, alto, fondo, unidad,
            observaciones, foto, operario, fecha_creacion
        FROM inventario_aulas
        ORDER BY fecha_creacion DESC
    """)

    datos = cursor.fetchall()
    conn.close()
    return datos
