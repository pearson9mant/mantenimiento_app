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

# ======================================================
# PANEL INTELIGENTE PREVENTIVO
# ======================================================

def _color_a_icono(color):
    if color == "rojo":
        return "🔴"
    if color == "amarillo":
        return "🟠"
    return "🟢"


def construir_panel_preventivo(centro=None):
    """
    Capa preparada para UI, Gerencia y futura pantalla diaria.
    No modifica datos.
    """

    estado = diagnosticar_preventivos_global(centro)
    prioridades = obtener_prioridades_preventivas(centro, limite=5)
    areas = evaluar_areas_preventivas(centro)

    prioridad_hoy = None

    if prioridades:
        p = prioridades[0]
        prioridad_hoy = {
            "titulo": p.get("descripcion", "Preventivo prioritario"),
            "numero_ot": p.get("numero_ot", ""),
            "centro": p.get("centro", ""),
            "edificio": p.get("edificio", ""),
            "espacio": p.get("espacio", ""),
            "area": p.get("area", ""),
            "fecha_programada": p.get("fecha_programada", ""),
            "accion": p.get("accion", "Realizar preventivo y completar checklist."),
            "motivo": "Es el preventivo abierto más prioritario según fecha y planificación.",
        }

    semaforo = [
        {
            "nombre": "Vencidos",
            "color": "rojo" if estado.get("vencidas", 0) > 0 else "verde",
            "icono": "🔴" if estado.get("vencidas", 0) > 0 else "🟢",
            "estado": f"{estado.get('vencidas', 0)} vencido(s)",
            "score": max(0, 100 - estado.get("vencidas", 0) * 20),
            "mensaje": "Preventivos fuera de plazo.",
        },
        {
            "nombre": "Próximos",
            "color": "amarillo" if estado.get("proximas", 0) > 0 else "verde",
            "icono": "🟠" if estado.get("proximas", 0) > 0 else "🟢",
            "estado": f"{estado.get('proximas', 0)} próximos",
            "score": max(0, 100 - estado.get("proximas", 0) * 5),
            "mensaje": "Preventivos próximos 7 días.",
        },
        {
            "nombre": "Abiertos",
            "color": "amarillo" if estado.get("abiertas", 0) > 0 else "verde",
            "icono": "🟠" if estado.get("abiertas", 0) > 0 else "🟢",
            "estado": f"{estado.get('abiertas', 0)} abiertos",
            "score": max(0, 100 - estado.get("abiertas", 0) * 3),
            "mensaje": "Preventivos pendientes.",
        },
    ]

    return {
        "resumen": {
            "centro": centro or "Todos",
            "estado": estado.get("estado", ""),
            "color": estado.get("color", "verde"),
            "icono": _color_a_icono(estado.get("color", "verde")),
            "score": estado.get("score", 0),
            "total": estado.get("total", 0),
            "abiertas": estado.get("abiertas", 0),
            "finalizadas": estado.get("finalizadas", 0),
            "vencidas": estado.get("vencidas", 0),
            "proximas": estado.get("proximas", 0),
            "recomendacion": estado.get("recomendacion", ""),
            "diagnostico": estado.get("diagnostico", []),
        },
        "semaforo": semaforo,
        "prioridad_hoy": prioridad_hoy,
        "prioridades": prioridades,
    }

def evaluar_areas_preventivas(centro=None):
    """
    Evalúa el estado preventivo por áreas.
    """

    params = []
    filtro = ""

    if centro:
        filtro = "AND centro = ?"
        params.append(centro)

    df = leer_df_preventivos(f"""
        SELECT area,
               estado,
               fecha_programada
        FROM ordenes_trabajo
        WHERE UPPER(COALESCE(origen,''))='PREVENTIVO'
        {filtro}
    """, tuple(params))

    if df.empty:
        return []

    hoy = pd.Timestamp(date.today())

    resultado = []

    for area, grupo in df.groupby("area"):

        total = len(grupo)

        abiertas = grupo[
            ~grupo["estado"].fillna("").str.lower().isin(ESTADOS_CIERRE)
        ]

        vencidas = 0

        if "fecha_programada" in abiertas.columns:

            fechas = pd.to_datetime(
                abiertas["fecha_programada"],
                errors="coerce"
            )

            vencidas = len(fechas[fechas < hoy])

        score = 100

        score -= vencidas * 20

        score = max(0, score)

        if score >= 85:
            color = "verde"
            icono = "🟢"
            estado = "Correcto"

        elif score >= 60:
            color = "amarillo"
            icono = "🟠"
            estado = "Seguimiento"

        else:
            color = "rojo"
            icono = "🔴"
            estado = "Crítico"

        resultado.append({
            "area": area,
            "total": total,
            "vencidas": vencidas,
            "score": score,
            "estado": estado,
            "color": color,
            "icono": icono,
        })

    resultado.sort(key=lambda x: x["score"])

    return resultado
