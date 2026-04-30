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
        cursor.execute("SAVEPOINT add_column_savepoint")
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
        cursor.execute("RELEASE SAVEPOINT add_column_savepoint")
    except Exception:
        try:
            cursor.execute("ROLLBACK TO SAVEPOINT add_column_savepoint")
            cursor.execute("RELEASE SAVEPOINT add_column_savepoint")
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
    # -------------------------------
    # FOTO INCIDENCIAS
    # -------------------------------
    _add_column(cursor, "ordenes_trabajo", "foto", "TEXT")
    _add_column(cursor, "historico_ordenes", "foto", "TEXT")

    # -------------------------------
    # MIGRACIONES INVENTARIO / COSTES
    # -------------------------------
    _add_column(cursor, "inventario", "precio_unitario", f"{real_sql} DEFAULT 0")
    _add_column(cursor, "inventario", "coste_total", f"{real_sql} DEFAULT 0")
    _add_column(cursor, "inventario", "fecha_compra", "TEXT")
    _add_column(cursor, "inventario", "referencia_factura", "TEXT")
    _add_column(cursor, "inventario", "observaciones_coste", "TEXT")

    # -------------------------------
    # LEGIONELLA
    # -------------------------------
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS legionella_puntos (
            id {id_sql},
            centro TEXT,
            edificio TEXT,
            instalacion TEXT,
            tipo_punto TEXT,
            nombre_punto TEXT,
            ubicacion TEXT,
            activo INTEGER DEFAULT 1,
            observaciones TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS legionella_tareas (
            id {id_sql},
            punto_id INTEGER,
            tarea TEXT,
            tipo_control TEXT,
            frecuencia TEXT,
            valor_minimo {real_sql},
            valor_maximo {real_sql},
            unidad TEXT,
            ultima_fecha TEXT,
            proxima_fecha TEXT,
            activo INTEGER DEFAULT 1,
            observaciones TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS legionella_registros (
            id {id_sql},
            fecha {fecha_sql},
            centro TEXT,
            edificio TEXT,
            instalacion TEXT,
            punto_id INTEGER,
            tarea_id INTEGER,
            punto TEXT,
            tarea TEXT,
            tipo_control TEXT,
            valor {real_sql},
            valor_2 {real_sql},
            unidad TEXT,
            estado TEXT,
            resultado TEXT,
            operario TEXT,
            observaciones TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS legionella_incidencias (
            id {id_sql},
            fecha_apertura {fecha_sql},
            centro TEXT,
            edificio TEXT,
            punto TEXT,
            tarea TEXT,
            descripcion TEXT,
            estado TEXT DEFAULT 'Abierta',
            prioridad TEXT DEFAULT 'Alta',
            operario TEXT,
            fecha_cierre TEXT,
            observaciones_cierre TEXT
        )
    """)

    # -------------------------------
    # MIGRACIONES LEGIONELLA
    # -------------------------------
    _add_column(cursor, "legionella_registros", "centro", "TEXT")
    _add_column(cursor, "legionella_registros", "edificio", "TEXT")
    _add_column(cursor, "legionella_registros", "instalacion", "TEXT")
    _add_column(cursor, "legionella_registros", "punto_id", "INTEGER")
    _add_column(cursor, "legionella_registros", "tarea_id", "INTEGER")
    _add_column(cursor, "legionella_registros", "punto", "TEXT")
    _add_column(cursor, "legionella_registros", "tarea", "TEXT")
    _add_column(cursor, "legionella_registros", "tipo_control", "TEXT")
    _add_column(cursor, "legionella_registros", "valor", real_sql)
    _add_column(cursor, "legionella_registros", "valor_2", real_sql)
    _add_column(cursor, "legionella_registros", "unidad", "TEXT")
    _add_column(cursor, "legionella_registros", "estado", "TEXT")
    _add_column(cursor, "legionella_registros", "resultado", "TEXT")
    _add_column(cursor, "legionella_registros", "operario", "TEXT")
    _add_column(cursor, "legionella_registros", "observaciones", "TEXT")

    _add_column(cursor, "legionella_incidencias", "centro", "TEXT")
    _add_column(cursor, "legionella_incidencias", "edificio", "TEXT")
    _add_column(cursor, "legionella_incidencias", "punto", "TEXT")
    _add_column(cursor, "legionella_incidencias", "tarea", "TEXT")
    _add_column(cursor, "legionella_incidencias", "descripcion", "TEXT")
    _add_column(cursor, "legionella_incidencias", "estado", "TEXT DEFAULT 'Abierta'")
    _add_column(cursor, "legionella_incidencias", "prioridad", "TEXT DEFAULT 'Alta'")
    _add_column(cursor, "legionella_incidencias", "operario", "TEXT")
    _add_column(cursor, "legionella_incidencias", "fecha_cierre", "TEXT")
    _add_column(cursor, "legionella_incidencias", "observaciones_cierre", "TEXT")

    # -------------------------------
    # MIGRACIONES LEGIONELLA PUNTOS
    # -------------------------------
    _add_column(cursor, "legionella_puntos", "centro", "TEXT")
    _add_column(cursor, "legionella_puntos", "edificio", "TEXT")
    _add_column(cursor, "legionella_puntos", "instalacion", "TEXT")
    _add_column(cursor, "legionella_puntos", "tipo_punto", "TEXT")
    _add_column(cursor, "legionella_puntos", "nombre_punto", "TEXT")
    _add_column(cursor, "legionella_puntos", "ubicacion", "TEXT")
    _add_column(cursor, "legionella_puntos", "activo", "INTEGER DEFAULT 1")
    _add_column(cursor, "legionella_puntos", "observaciones", "TEXT")

    conn.commit()
    conn.close()
