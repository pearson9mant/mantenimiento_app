import sqlite3
from pathlib import Path
from config import DB

def conectar():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB, timeout=30)

def inicializar_db():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ordenes_trabajo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_ot TEXT,
            descripcion TEXT,
            estado TEXT,
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            area TEXT,
            prioridad TEXT,
            operario TEXT,
            origen TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_ordenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_ot TEXT,
            descripcion TEXT,
            estado TEXT,
            fecha_creacion DATETIME,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            area TEXT,
            prioridad TEXT,
            operario TEXT,
            observaciones_cierre TEXT,
            fecha_cierre DATETIME DEFAULT CURRENT_TIMESTAMP,
            origen TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            material TEXT,
            categoria TEXT,
            unidad TEXT,
            stock_actual REAL DEFAULT 0,
            stock_minimo REAL DEFAULT 0,
            centro TEXT,
            edificio TEXT,
            ubicacion TEXT,
            proveedor TEXT,
            observaciones TEXT,
            fecha_alta DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_material TEXT,
            material TEXT,
            tipo_movimiento TEXT,
            cantidad REAL,
            motivo TEXT,
            numero_ot TEXT,
            operario TEXT,
            fecha_movimiento DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------
    # INCIDENCIAS OUTLOOK
    # -----------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidencias_outlook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_outlook TEXT UNIQUE,
            asunto TEXT,
            cuerpo TEXT,
            remitente TEXT,
            fecha TEXT,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            prioridad TEXT,
            solicitante TEXT,
            procesado INTEGER DEFAULT 0
        )
    """)

    # -----------------------
    # CONTADOR OT (NUEVO)
    # -----------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contador_ot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            centro_codigo TEXT NOT NULL,
            tipo_codigo TEXT NOT NULL,
            ultimo_numero INTEGER NOT NULL DEFAULT 0,
            UNIQUE(centro_codigo, tipo_codigo)
        )
    """)

    conn.commit()
    conn.close()