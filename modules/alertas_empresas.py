import os
import pandas as pd
from datetime import date

from database.db import conectar


def adaptar_sql(sql):
    if os.getenv("DATABASE_URL"):
        return sql.replace("?", "%s")
    return sql


def obtener_alertas_empresas_externas():
    conn = conectar()

    try:
        df = pd.read_sql_query(
            adaptar_sql("""
                SELECT id, tipo_informe, empresa, centro, punto, proxima_fecha
                FROM legionella_informes
                WHERE proxima_fecha IS NOT NULL
                  AND TRIM(COALESCE(proxima_fecha, '')) <> ''
            """),
            conn
        )
    finally:
        conn.close()

    if df.empty:
        return {
            "toca": [],
            "proximo": []
        }

    hoy = pd.Timestamp(date.today())
    margen = hoy + pd.Timedelta(days=30)

    toca = []
    proximo = []

    for _, row in df.iterrows():
        try:
            fecha = pd.to_datetime(row["proxima_fecha"])
        except Exception:
            continue

        item = {
            "id": row["id"],
            "tipo": row["tipo_informe"],
            "empresa": row["empresa"],
            "centro": row["centro"],
            "punto": row["punto"],
            "fecha": row["proxima_fecha"],
        }

        if fecha <= hoy:
            toca.append(item)
        elif fecha <= margen:
            proximo.append(item)

    return {
        "toca": toca,
        "proximo": proximo
    }
