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

from modules.ordenes import obtener_siguiente_numero_ot, crear_orden


def existe_ot_externa_abierta(centro, descripcion):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(
            adaptar_sql("""
                SELECT COUNT(*)
                FROM ordenes_trabajo
                WHERE centro = ?
                  AND descripcion = ?
                  AND origen = 'EXTERNA'
                  AND LOWER(COALESCE(estado, '')) NOT IN ('finalizada', 'cerrada')
            """),
            (centro, descripcion)
        )

        total = cur.fetchone()[0]
        return total > 0

    finally:
        conn.close()


def crear_ots_empresas_externas_si_toca():
    alertas = obtener_alertas_empresas_externas()
    toca = alertas.get("toca", [])

    creadas = 0
    ya_existian = 0

    for item in toca:
        centro = item.get("centro", "")
        tipo = item.get("tipo", "")
        empresa = item.get("empresa", "")
        punto = item.get("punto", "")
        fecha = item.get("fecha", "")

        descripcion = (
            f"Gestionar actuación externa vencida - {tipo} - "
            f"{empresa} - {punto} - Fecha prevista {fecha}"
        )

        if existe_ot_externa_abierta(centro, descripcion):
            ya_existian += 1
            continue

        numero_ot = obtener_siguiente_numero_ot(centro, "EXT")

        datos_orden = (
            numero_ot,
            descripcion,
            "Abierta",
            centro,
            "",
            punto,
            "Legionella",
            "Alta",
            "Abel Vasquez",
            "EXTERNA",
            "",
            "",
            "",
            "Operarios",
            "Externa",
            empresa,
            "",
            "",
            "",
            "",
            "",
            fecha,
            "",
            "",
            "",
            0,
            0,
            ""
        )

        crear_orden(datos_orden)
        creadas += 1

    return creadas, ya_existian
