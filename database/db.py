import os
import sqlite3
from pathlib import Path
from config import DB

try:
    import psycopg2
except Exception:
    psycopg2 = None


def _es_postgres():
    return bool(os.getenv("DATABASE_URL"))


def _sql(query):
    if _es_postgres():
        return query.replace("?", "%s")
    return query


def conectar():
    database_url = os.getenv("DATABASE_URL")

    if database_url and psycopg2:
        return psycopg2.connect(database_url)

    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB, timeout=30)


def _add_column(cursor, tabla, columna, tipo):
    try:
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
    except Exception:
        pass


def inicializar_db():
    conn = conectar()
    cursor = conn.cursor()

    if _es_postgres():
        id_sql = "SERIAL PRIMARY KEY"
        fecha_sql = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        fecha_tipo = "TIMESTAMP"
        real_sql = "REAL"
    else:
        id_sql = "INTEGER PRIMARY KEY AUTOINCREMENT"
        fecha_sql = "DATETIME DEFAULT CURRENT_TIMESTAMP"
        fecha_tipo = "DATETIME"
        real_sql = "REAL"

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS ordenes_trabajo (
            id {id_sql},
            numero_ot TEXT,
            descripcion TEXT,
            estado TEXT,
            fecha_creacion {fecha_sql},
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            area TEXT,
            prioridad TEXT,
            operario TEXT,
            origen TEXT,
            solicitante TEXT,
            fecha_origen TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS historico_ordenes (
            id {id_sql},
            numero_ot TEXT,
            descripcion TEXT,
            estado TEXT,
            fecha_creacion {fecha_tipo},
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            area TEXT,
            prioridad TEXT,
            operario TEXT,
            observaciones_cierre TEXT,
            fecha_cierre {fecha_sql},
            origen TEXT,
            solicitante TEXT,
            fecha_origen TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS inventario (
            id {id_sql},
            codigo TEXT UNIQUE,
            material TEXT,
            categoria TEXT,
            unidad TEXT,
            stock_actual {real_sql} DEFAULT 0,
            stock_minimo {real_sql} DEFAULT 0,
            centro TEXT,
            edificio TEXT,
            ubicacion TEXT,
            proveedor TEXT,
            observaciones TEXT,
            fecha_alta {fecha_sql}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id {id_sql},
            codigo_material TEXT,
            material TEXT,
            tipo_movimiento TEXT,
            cantidad {real_sql},
            motivo TEXT,
            numero_ot TEXT,
            operario TEXT,
            fecha_movimiento {fecha_sql}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS incidencias_outlook (
            id {id_sql},
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

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS contador_ot (
            id {id_sql},
            centro_codigo TEXT NOT NULL,
            tipo_codigo TEXT NOT NULL,
            ultimo_numero INTEGER NOT NULL DEFAULT 0,
            UNIQUE(centro_codigo, tipo_codigo)
        )
    """)

    # Por si las tablas ya existían antiguas
    _add_column(cursor, "ordenes_trabajo", "solicitante", "TEXT")
    _add_column(cursor, "ordenes_trabajo", "fecha_origen", "TEXT")
    _add_column(cursor, "historico_ordenes", "solicitante", "TEXT")
    _add_column(cursor, "historico_ordenes", "fecha_origen", "TEXT")

    conn.commit()
    conn.close()
