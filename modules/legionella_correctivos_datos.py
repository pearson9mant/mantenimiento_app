import json
import os
from datetime import datetime

from database.db import conectar, _sql




def _adaptar_sql(sql):
    return sql.replace("?", "%s") if os.getenv("DATABASE_URL") else sql


def asegurar_tabla_correctivos_especializados():
    conn = conectar()
    cur = conn.cursor()
    try:
        if os.getenv("DATABASE_URL"):
            cur.execute(_adaptar_sql("""
                CREATE TABLE IF NOT EXISTS legionella_correctivos_especializados (
                    id SERIAL PRIMARY KEY,
                    numero_ot TEXT NOT NULL,
                    tipo_correctivo TEXT NOT NULL,
                    datos_json TEXT NOT NULL DEFAULT '{}',
                    completado INTEGER NOT NULL DEFAULT 0,
                    fecha_actualizacion TEXT,
                    UNIQUE(numero_ot, tipo_correctivo)
                )
            """))
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS legionella_correctivos_especializados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_ot TEXT NOT NULL,
                    tipo_correctivo TEXT NOT NULL,
                    datos_json TEXT NOT NULL DEFAULT '{}',
                    completado INTEGER NOT NULL DEFAULT 0,
                    fecha_actualizacion TEXT,
                    UNIQUE(numero_ot, tipo_correctivo)
                )
            """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_correctivo_especializado(numero_ot, tipo_correctivo):
    asegurar_tabla_correctivos_especializados()
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            _adaptar_sql("""
                SELECT datos_json, completado, fecha_actualizacion
                FROM legionella_correctivos_especializados
                WHERE numero_ot = ? AND tipo_correctivo = ?
                ORDER BY id DESC
                LIMIT 1
            """),
            (str(numero_ot), str(tipo_correctivo)),
        )
        fila = cur.fetchone()
    finally:
        conn.close()

    if not fila:
        return None

    try:
        datos = json.loads(fila[0] or "{}")
    except Exception:
        datos = {}

    datos["_completado"] = bool(fila[1])
    datos["_fecha_actualizacion"] = fila[2]
    return datos


def guardar_correctivo_especializado(numero_ot, tipo_correctivo, datos, completado=False):
    asegurar_tabla_correctivos_especializados()
    numero_ot = str(numero_ot)
    tipo_correctivo = str(tipo_correctivo)
    datos_json = json.dumps(datos or {}, ensure_ascii=False)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            _adaptar_sql("""
                SELECT id
                FROM legionella_correctivos_especializados
                WHERE numero_ot = ? AND tipo_correctivo = ?
                LIMIT 1
            """),
            (numero_ot, tipo_correctivo),
        )
        fila = cur.fetchone()

        if fila:
            cur.execute(
                _adaptar_sql("""
                    UPDATE legionella_correctivos_especializados
                    SET datos_json = ?, completado = ?, fecha_actualizacion = ?
                    WHERE id = ?
                """),
                (datos_json, 1 if completado else 0, fecha, int(fila[0])),
            )
        else:
            cur.execute(
                _adaptar_sql("""
                    INSERT INTO legionella_correctivos_especializados
                    (numero_ot, tipo_correctivo, datos_json, completado, fecha_actualizacion)
                    VALUES (?, ?, ?, ?, ?)
                """),
                (numero_ot, tipo_correctivo, datos_json, 1 if completado else 0, fecha),
            )

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def borrar_correctivo_especializado(numero_ot, tipo_correctivo):
    asegurar_tabla_correctivos_especializados()
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            _adaptar_sql("""
                DELETE FROM legionella_correctivos_especializados
                WHERE numero_ot = ? AND tipo_correctivo = ?
            """),
            (str(numero_ot), str(tipo_correctivo)),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
