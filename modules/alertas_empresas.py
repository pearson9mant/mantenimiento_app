import os
from datetime import date

import pandas as pd

from database.db import conectar, _sql
from modules.ordenes import (
    obtener_siguiente_numero_ot,
    crear_orden,
    vincular_origen_ot,
)


def adaptar_sql(sql):
    if os.getenv("DATABASE_URL"):
        return sql.replace("?", "%s")
    return sql


def asegurar_tabla_legionella_informes():
    conn = conectar()
    cur = conn.cursor()

    try:
        if os.getenv("DATABASE_URL"):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS legionella_informes (
                    id SERIAL PRIMARY KEY,
                    tipo_informe TEXT,
                    empresa TEXT,
                    centro TEXT,
                    edificio TEXT,
                    instalacion TEXT,
                    punto TEXT,
                    fecha_actuacion TEXT,
                    fecha_informe TEXT,
                    resultado TEXT,
                    numero_informe TEXT,
                    pdf TEXT,
                    pdf_nombre TEXT,
                    pdf_data BYTEA,
                    proxima_fecha TEXT,
                    observaciones TEXT,
                    numero_ot_recordatorio TEXT,
                    fecha_recordatorio TEXT
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS legionella_informes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_informe TEXT,
                    empresa TEXT,
                    centro TEXT,
                    edificio TEXT,
                    instalacion TEXT,
                    punto TEXT,
                    fecha_actuacion TEXT,
                    fecha_informe TEXT,
                    resultado TEXT,
                    numero_informe TEXT,
                    pdf TEXT,
                    pdf_nombre TEXT,
                    pdf_data BLOB,
                    proxima_fecha TEXT,
                    observaciones TEXT,
                    numero_ot_recordatorio TEXT,
                    fecha_recordatorio TEXT
                )
            """)

        for columna, tipo in [
            ("numero_ot_recordatorio", "TEXT"),
            ("fecha_recordatorio", "TEXT"),
        ]:
            try:
                cur.execute(
                    f"""
                    ALTER TABLE legionella_informes
                    ADD COLUMN {columna} {tipo}
                    """
                )
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def operario_por_centro(centro):
    if str(centro or "").strip() == "Pearson 9":
        return "Luis Lozano"

    if str(centro or "").strip() == "Pearson 22":
        return "J.A. Almeda"

    return ""


def obtener_alertas_empresas_externas():
    asegurar_tabla_legionella_informes()

    conn = conectar()

    try:
        df = pd.read_sql_query(
            adaptar_sql("""
                SELECT
                    id,
                    tipo_informe,
                    empresa,
                    centro,
                    edificio,
                    instalacion,
                    punto,
                    proxima_fecha,
                    numero_ot_recordatorio
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
            "proximo": [],
        }

    hoy = pd.Timestamp(date.today())
    margen = hoy + pd.Timedelta(days=30)

    toca = []
    proximo = []

    for _, row in df.iterrows():
        try:
            fecha = pd.to_datetime(
                row["proxima_fecha"]
            )
        except Exception:
            continue

        item = {
            "id": row["id"],
            "tipo": row["tipo_informe"],
            "empresa": row["empresa"],
            "centro": row["centro"],
            "edificio": row["edificio"],
            "instalacion": row["instalacion"],
            "punto": row["punto"],
            "fecha": row["proxima_fecha"],
            "numero_ot_recordatorio": (
                row.get("numero_ot_recordatorio")
                or ""
            ),
        }

        if fecha <= hoy:
            toca.append(item)

        elif fecha <= margen:
            proximo.append(item)

    return {
        "toca": toca,
        "proximo": proximo,
    }


def existe_ot_externa_abierta(
    centro,
    descripcion
):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(
            _sql("""
                SELECT COUNT(*)
                FROM ordenes_trabajo
                WHERE centro = ?
                  AND descripcion = ?
                  AND UPPER(COALESCE(origen, '')) = 'EXTERNA'
                  AND LOWER(COALESCE(estado, '')) NOT IN (
                      'finalizada',
                      'finalizado',
                      'cerrada',
                      'cerrado',
                      'cancelada',
                      'cancelado'
                  )
            """),
            (
                centro,
                descripcion,
            )
        )

        total = int(
            cur.fetchone()[0] or 0
        )

        return total > 0

    finally:
        conn.close()


def _marcar_recordatorio_generado(
    id_informe,
    numero_ot
):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(
            _sql("""
                UPDATE legionella_informes
                SET numero_ot_recordatorio = ?,
                    fecha_recordatorio = ?
                WHERE id = ?
            """),
            (
                numero_ot,
                date.today().strftime("%Y-%m-%d"),
                int(id_informe),
            )
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def crear_ots_empresas_externas_si_toca():
    """
    Convierte un vencimiento de informe/actuación externa en una OT.

    Ejemplo:
    - Analítica laboratorio con próxima fecha 15/09
    - Al llegar el día crea una única OT EXTERNA
    - El informe conserva su próxima_fecha como trazabilidad
    - numero_ot_recordatorio evita volver a crearla después de cerrarla

    La nueva periodicidad se establece cuando se archiva el nuevo informe.
    """
    asegurar_tabla_legionella_informes()

    conn = conectar()

    try:
        df = pd.read_sql_query(
            adaptar_sql("""
                SELECT
                    id,
                    tipo_informe,
                    empresa,
                    centro,
                    edificio,
                    instalacion,
                    punto,
                    proxima_fecha,
                    numero_ot_recordatorio,
                    observaciones
                FROM legionella_informes
                WHERE proxima_fecha IS NOT NULL
                  AND TRIM(COALESCE(proxima_fecha, '')) <> ''
                  AND SUBSTR(proxima_fecha, 1, 10) <= ?
                  AND TRIM(
                        COALESCE(numero_ot_recordatorio, '')
                  ) = ''
                ORDER BY proxima_fecha ASC, id ASC
            """),
            conn,
            params=(
                date.today().strftime("%Y-%m-%d"),
            )
        )
    finally:
        conn.close()

    if df.empty:
        return 0, 0

    creadas = 0
    omitidas = 0

    for _, row in df.iterrows():
        id_informe = int(
            row["id"]
        )

        tipo = str(
            row["tipo_informe"]
            or "Actuación externa Legionella"
        ).strip()

        empresa = str(
            row["empresa"]
            or ""
        ).strip()

        centro = str(
            row["centro"]
            or ""
        ).strip()

        edificio = str(
            row["edificio"]
            or ""
        ).strip()

        punto = str(
            row["punto"]
            or row["instalacion"]
            or "Legionella"
        ).strip()

        fecha_objetivo = str(
            row["proxima_fecha"]
            or ""
        )[:10]

        descripcion = (
            f"[LEGIONELLA EXTERNA] {tipo}"
            f" - {punto}"
        )

        if empresa:
            descripcion += (
                f" - {empresa}"
            )

        if existe_ot_externa_abierta(
            centro,
            descripcion
        ):
            omitidas += 1
            continue

        numero_ot = obtener_siguiente_numero_ot(
            centro,
            "EXT"
        )

        observaciones = (
            f"Actuación externa programada de Legionella.\n"
            f"Tipo: {tipo}\n"
            f"Empresa: {empresa or '-'}\n"
            f"Instalación/punto: {punto or '-'}\n"
            f"Fecha prevista: {fecha_objetivo or '-'}\n"
            f"Origen: informe externo #{id_informe}"
        )

        datos_orden = (
            numero_ot,
            descripcion,
            "Abierta",
            centro,
            edificio,
            punto,
            "Legionella",
            "Alta",
            operario_por_centro(
                centro
            ),
            "EXTERNA",
            empresa or "Empresa externa",
            fecha_objetivo,
            "",
            "Operarios",
            "Externa",
            empresa,
            "",
            "",
            "",
            fecha_objetivo,
            "",
            0,
            0,
            observaciones,
        )

        try:
            crear_orden(
                datos_orden
            )

            vincular_origen_ot(
                numero_ot=numero_ot,
                origen_tabla="legionella_informes",
                origen_id=id_informe,
            )

            _marcar_recordatorio_generado(
                id_informe,
                numero_ot
            )

            creadas += 1

        except Exception:
            omitidas += 1

    return creadas, omitidas
