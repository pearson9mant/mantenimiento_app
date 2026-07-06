from datetime import date
import pandas as pd

from database.db import conectar, _sql


ESTADOS_CIERRE = [
    "finalizada",
    "finalizado",
    "cerrada",
    "cerrado",
    "cancelada",
    "cancelado",
]


def leer_df_preventivos(sql, params=()):
    conn = conectar()
    try:
        return pd.read_sql_query(_sql(sql), conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def diagnosticar_preventivos_global(centro=None):
    """
    Motor inteligente preventivo.
    Solo lee datos. No modifica nada.
    """

    params = []
    filtro_centro = ""

    if centro:
        filtro_centro = "AND centro = ?"
        params.append(centro)

    ots = leer_df_preventivos(f"""
        SELECT *
        FROM ordenes_trabajo
        WHERE UPPER(COALESCE(origen, '')) = 'PREVENTIVO'
        {filtro_centro}
    """, tuple(params))

    hoy = pd.Timestamp(date.today())

    total = len(ots) if not ots.empty else 0
    abiertas = 0
    vencidas = 0
    proximas = 0
    finalizadas = 0

    if not ots.empty:
        estado = ots["estado"].fillna("").astype(str).str.lower()

        finalizadas = len(ots[estado.isin(ESTADOS_CIERRE)])
        abiertas_df = ots[~estado.isin(ESTADOS_CIERRE)].copy()
        abiertas = len(abiertas_df)

        if "fecha_programada" in abiertas_df.columns:
            abiertas_df["fecha_programada_dt"] = pd.to_datetime(
                abiertas_df["fecha_programada"],
                errors="coerce"
            )

            vencidas = len(
                abiertas_df[
                    abiertas_df["fecha_programada_dt"].notna()
                    & (abiertas_df["fecha_programada_dt"] < hoy)
                ]
            )

            proximas = len(
                abiertas_df[
                    abiertas_df["fecha_programada_dt"].notna()
                    & (abiertas_df["fecha_programada_dt"] >= hoy)
                    & (abiertas_df["fecha_programada_dt"] <= hoy + pd.Timedelta(days=7))
                ]
            )

    score = 100
    score -= vencidas * 12
    score -= abiertas * 3
    score -= proximas * 2
    score = max(0, min(100, int(score)))

    if vencidas > 0:
        color = "rojo"
        estado_txt = "Preventivos vencidos"
        recomendacion = "Atender primero los preventivos vencidos."
    elif proximas > 0:
        color = "amarillo"
        estado_txt = "Seguimiento preventivo"
        recomendacion = "Programar los preventivos próximos de esta semana."
    else:
        color = "verde"
        estado_txt = "Preventivos controlados"
        recomendacion = "Mantener planificación preventiva."

    diagnostico = [
        f"{total} preventivo(s) registrados.",
        f"{abiertas} preventivo(s) abiertos.",
        f"{finalizadas} preventivo(s) finalizados.",
    ]

    if vencidas > 0:
        diagnostico.append(f"{vencidas} preventivo(s) vencido(s).")

    if proximas > 0:
        diagnostico.append(f"{proximas} preventivo(s) próximos en 7 días.")

    return {
        "centro": centro or "Todos",
        "estado": estado_txt,
        "color": color,
        "score": score,
        "total": total,
        "abiertas": abiertas,
        "finalizadas": finalizadas,
        "vencidas": vencidas,
        "proximas": proximas,
        "diagnostico": diagnostico,
        "recomendacion": recomendacion,
    }


def obtener_prioridades_preventivas(centro=None, limite=5):
    params = []
    filtro_centro = ""

    if centro:
        filtro_centro = "AND centro = ?"
        params.append(centro)

    df = leer_df_preventivos(f"""
        SELECT *
        FROM ordenes_trabajo
        WHERE UPPER(COALESCE(origen, '')) = 'PREVENTIVO'
          AND LOWER(COALESCE(estado, '')) NOT IN (
            'finalizada',
            'finalizado',
            'cerrada',
            'cerrado',
            'cancelada',
            'cancelado'
          )
        {filtro_centro}
        ORDER BY fecha_programada ASC, prioridad DESC
    """, tuple(params))

    if df.empty:
        return []

    prioridades = []

    for _, row in df.head(limite).iterrows():
        prioridades.append({
            "numero_ot": row.get("numero_ot", ""),
            "centro": row.get("centro", ""),
            "edificio": row.get("edificio", ""),
            "espacio": row.get("espacio", ""),
            "area": row.get("area", ""),
            "prioridad": row.get("prioridad", ""),
            "descripcion": row.get("descripcion", ""),
            "fecha_programada": row.get("fecha_programada", ""),
            "accion": "Realizar preventivo y completar checklist.",
        })

    return prioridades
