from datetime import date
import pandas as pd

from database.db import conectar, _sql

from modules.inteligencia_preventivos import construir_panel_preventivo
from modules.inteligencia_legionella import construir_panel_sanitario_legionella


ESTADOS_CIERRE = [
    "finalizada",
    "finalizado",
    "cerrada",
    "cerrado",
    "cancelada",
    "cancelado",
]


def leer_df_corazon(sql, params=()):
    conn = conectar()
    try:
        return pd.read_sql_query(_sql(sql), conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def normalizar(valor):
    return str(valor or "").strip().lower()


def obtener_ordenes_abiertas_corazon(centro=None, operario=None):
    params = []
    filtro = ""

    if centro:
        filtro += " AND centro = ?"
        params.append(centro)

    if operario:
        filtro += " AND operario = ?"
        params.append(operario)

    df = leer_df_corazon(f"""
        SELECT *
        FROM ordenes_trabajo
        WHERE LOWER(COALESCE(estado,'')) NOT IN (
            'finalizada',
            'finalizado',
            'cerrada',
            'cerrado',
            'cancelada',
            'cancelado'
        )
        {filtro}
    """, tuple(params))

    return df


def puntuar_orden(row):
    score = 0

    area = normalizar(row.get("area"))
    origen = normalizar(row.get("origen"))
    prioridad = normalizar(row.get("prioridad"))
    descripcion = normalizar(row.get("descripcion"))

    if "legionella" in area or "legionella" in origen or "legionella" in descripcion:
        score += 95

    elif "urgente" in prioridad:
        score += 90

    elif "alta" in prioridad:
        score += 75

    elif origen == "preventivo":
        score += 60

    elif origen in ["app", "outlook", "profesores", "externa"]:
        score += 55

    else:
        score += 40

    if "fuga" in descripcion or "agua" in descripcion:
        score += 10

    if "eléctr" in descripcion or "electric" in descripcion:
        score += 8

    if "clima" in descripcion or "aire" in descripcion:
        score += 6

    return min(score, 100)


def construir_prioridades_globales(centro=None, operario=None, limite=10):
    df = obtener_ordenes_abiertas_corazon(centro, operario)

    if df.empty:
        return []

    prioridades = []

    for _, row in df.iterrows():
        score = puntuar_orden(row)

        prioridades.append({
            "score": score,
            "numero_ot": row.get("numero_ot", ""),
            "titulo": row.get("descripcion", ""),
            "centro": row.get("centro", ""),
            "edificio": row.get("edificio", ""),
            "espacio": row.get("espacio", ""),
            "area": row.get("area", ""),
            "origen": row.get("origen", ""),
            "prioridad": row.get("prioridad", ""),
            "operario": row.get("operario", ""),
            "estado": row.get("estado", ""),
            "accion": "Atender esta actuación antes que el resto.",
            "motivo": "El sistema la considera prioritaria por origen, área, prioridad y riesgo operativo.",
        })

    prioridades.sort(key=lambda x: x["score"], reverse=True)

    return prioridades[:limite]


def diagnosticar_corazon_sistema(centro=None, operario=None):
    df = obtener_ordenes_abiertas_corazon(centro, operario)

    abiertas = len(df) if not df.empty else 0
    incidencias = 0
    preventivos = 0
    legionella = 0
    urgentes = 0

    if not df.empty:
        origen = df["origen"].fillna("").astype(str).str.upper()
        area = df["area"].fillna("").astype(str).str.lower()
        prioridad = df["prioridad"].fillna("").astype(str).str.lower()
        descripcion = df["descripcion"].fillna("").astype(str).str.lower()

        preventivos = len(df[origen == "PREVENTIVO"])
        legionella = len(df[
            (origen == "LEGIONELLA")
            | (area == "legionella")
            | (descripcion.str.contains("legionella", na=False))
        ])
        incidencias = len(df[
            origen.isin(["APP", "OUTLOOK", "PROFESORES", "EXTERNA"])
        ])
        urgentes = len(df[
            prioridad.str.contains("urgente|alta", case=False, na=False)
        ])

    try:
        preventivo = construir_panel_preventivo(centro)
        score_preventivo = preventivo.get("resumen", {}).get("score", 100)
    except Exception:
        preventivo = {}
        score_preventivo = 100

    try:
        legionella_panel = construir_panel_sanitario_legionella(centro)
        score_legionella = legionella_panel.get("resumen", {}).get("score", 100)
    except Exception:
        legionella_panel = {}
        score_legionella = 100

    score_operativo = 100
    score_operativo -= abiertas * 2
    score_operativo -= urgentes * 8
    score_operativo -= legionella * 8
    score_operativo -= preventivos * 2
    score_operativo = max(0, min(100, score_operativo))

    score_global = round(
        (score_operativo + score_preventivo + score_legionella) / 3
    )

    if score_global < 60:
        color = "rojo"
        estado = "Atención prioritaria"
        mensaje = "El colegio requiere actuar sobre trabajos críticos antes de considerar la situación estable."
    elif score_global < 85:
        color = "amarillo"
        estado = "Seguimiento operativo"
        mensaje = "El colegio está operativo, pero conviene reducir carga pendiente y cerrar actuaciones prioritarias."
    else:
        color = "verde"
        estado = "Colegio bajo control"
        mensaje = "La situación general es estable. Mantener ritmo de cierre y seguimiento."

    prioridades = construir_prioridades_globales(centro, operario, limite=10)

    prioridad_hoy = prioridades[0] if prioridades else None

    return {
        "fecha": str(date.today()),
        "centro": centro or "Todos",
        "operario": operario or "Todos",
        "score_global": score_global,
        "score_operativo": score_operativo,
        "score_preventivo": score_preventivo,
        "score_legionella": score_legionella,
        "color": color,
        "estado": estado,
        "mensaje": mensaje,
        "kpis": {
            "abiertas": abiertas,
            "incidencias": incidencias,
            "preventivos": preventivos,
            "legionella": legionella,
            "urgentes": urgentes,
        },
        "prioridad_hoy": prioridad_hoy,
        "prioridades": prioridades,
        "preventivo": preventivo,
        "legionella": legionella_panel,
    }
