from datetime import date
import pandas as pd

from database.db import conectar, _sql


def obtener_estado_aula(centro, edificio, aula):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT *
        FROM estado_aulas
        WHERE centro = ?
          AND edificio = ?
          AND aula = ?
        ORDER BY id DESC
        LIMIT 1
    """), (centro, edificio, aula))

    dato = cursor.fetchone()
    conn.close()
    return dato


def guardar_estado_aula(
    centro,
    edificio,
    aula,
    estado_general,
    estado_pintura,
    fecha_ultima_pintura,
    estado_electricidad,
    estado_iluminacion,
    estado_climatizacion,
    estado_fontaneria,
    estado_mobiliario,
    observaciones,
    foto,
    revisado_por
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        INSERT INTO estado_aulas (
            centro,
            edificio,
            aula,
            estado_general,
            estado_pintura,
            fecha_ultima_pintura,
            estado_electricidad,
            estado_iluminacion,
            estado_climatizacion,
            estado_fontaneria,
            estado_mobiliario,
            observaciones,
            foto,
            fecha_revision,
            revisado_por
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """), (
        centro,
        edificio,
        aula,
        estado_general,
        estado_pintura,
        str(fecha_ultima_pintura) if fecha_ultima_pintura else "",
        estado_electricidad,
        estado_iluminacion,
        estado_climatizacion,
        estado_fontaneria,
        estado_mobiliario,
        observaciones,
        foto,
        str(date.today()),
        revisado_por
    ))

    conn.commit()
    conn.close()


def obtener_historial_estado_aula(centro, edificio, aula):
    conn = conectar()

    try:
        df = pd.read_sql_query(_sql("""
            SELECT
                fecha_revision,
                estado_general,
                estado_pintura,
                fecha_ultima_pintura,
                estado_electricidad,
                estado_iluminacion,
                estado_climatizacion,
                estado_fontaneria,
                estado_mobiliario,
                observaciones,
                revisado_por
            FROM estado_aulas
            WHERE centro = ?
              AND edificio = ?
              AND aula = ?
            ORDER BY id DESC
        """), conn, params=(centro, edificio, aula))
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


def obtener_ordenes_abiertas_aula(centro, edificio, aula):
    conn = conectar()

    try:
        df = pd.read_sql_query(_sql("""
            SELECT
                numero_ot,
                descripcion,
                estado,
                fecha_creacion,
                area,
                prioridad,
                operario,
                origen
            FROM ordenes_trabajo
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
            ORDER BY fecha_creacion DESC
        """), conn, params=(centro, edificio, aula))
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


def obtener_historico_ordenes_aula(centro, edificio, aula):
    conn = conectar()

    try:
        df = pd.read_sql_query(_sql("""
            SELECT
                numero_ot,
                descripcion,
                estado,
                fecha_creacion,
                fecha_cierre,
                area,
                prioridad,
                operario,
                origen,
                observaciones_cierre
            FROM historico_ordenes
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
            ORDER BY fecha_cierre DESC
        """), conn, params=(centro, edificio, aula))
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df
