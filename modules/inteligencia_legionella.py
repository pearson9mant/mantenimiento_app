from datetime import date
import pandas as pd

from database.db import conectar, _sql


def leer_df_legionella(sql, params=()):
    conn = conectar()
    try:
        return pd.read_sql_query(_sql(sql), conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def diagnosticar_legionella_global(centro=None):
    """
    Motor sanitario Legionella.
    Solo lee datos. No crea, no borra, no modifica.
    """

    filtros = []
    params = []

    if centro:
        filtros.append("centro = ?")
        params.append(centro)

    where = ""
    if filtros:
        where = "WHERE " + " AND ".join(filtros)

    puntos = leer_df_legionella(f"""
        SELECT *
        FROM legionella_puntos
        {where}
    """, tuple(params))

    tareas = leer_df_legionella(f"""
        SELECT *
        FROM legionella_tareas
        {where}
    """, tuple(params))

    incidencias = leer_df_legionella(f"""
        SELECT *
        FROM legionella_incidencias
        {where}
    """, tuple(params))

    registros = leer_df_legionella(f"""
        SELECT *
        FROM legionella_registros
        {where}
        ORDER BY fecha DESC
    """, tuple(params))

    hoy = pd.Timestamp(date.today())

    total_puntos = 0 if puntos.empty else len(puntos)
    puntos_activos = 0

    if not puntos.empty and "activo" in puntos.columns:
        puntos_activos = len(puntos[puntos["activo"].fillna(0).astype(int) == 1])

    tareas_activas = 0 if tareas.empty else len(tareas[tareas["activo"].fillna(0).astype(int) == 1])

    vencidas = 0
    proximas = 0

    if not tareas.empty and "proxima_fecha" in tareas.columns:
        tareas["proxima_fecha_dt"] = pd.to_datetime(tareas["proxima_fecha"], errors="coerce")
        tareas_activas_df = tareas[tareas["activo"].fillna(0).astype(int) == 1].copy()

        vencidas = len(tareas_activas_df[tareas_activas_df["proxima_fecha_dt"] <= hoy])
        proximas = len(
            tareas_activas_df[
                (tareas_activas_df["proxima_fecha_dt"] > hoy)
                & (tareas_activas_df["proxima_fecha_dt"] <= hoy + pd.Timedelta(days=15))
            ]
        )

    incidencias_abiertas = 0

    if not incidencias.empty and "estado" in incidencias.columns:
        estado = incidencias["estado"].fillna("").astype(str).str.lower()
        incidencias_abiertas = len(
            incidencias[
                ~estado.isin(["cerrada", "cerrado", "finalizada", "finalizado"])
            ]
        )

    riesgos_registro = 0

    if not registros.empty and "estado" in registros.columns:
        riesgos_registro = len(
            registros[
                registros["estado"].fillna("").astype(str).str.upper().isin(["RIESGO", "INCIDENCIA"])
            ]
        )

    score = 100
    score -= incidencias_abiertas * 15
    score -= vencidas * 8
    score -= proximas * 3
    score -= min(riesgos_registro, 5) * 5
    score = max(0, min(100, score))

    if incidencias_abiertas > 0 or vencidas > 0:
        color = "rojo"
        estado = "Atención sanitaria"
        recomendacion = "Revisar primero incidencias abiertas y controles vencidos."
    elif proximas > 0:
        color = "amarillo"
        estado = "Seguimiento preventivo"
        recomendacion = "Programar los controles próximos antes de su vencimiento."
    else:
        color = "verde"
        estado = "Correcto"
        recomendacion = "Mantener planificación preventiva."

    return {
        "centro": centro or "Todos",
        "estado": estado,
        "color": color,
        "score": score,
        "puntos_total": total_puntos,
        "puntos_activos": puntos_activos,
        "tareas_activas": tareas_activas,
        "controles_vencidos": vencidas,
        "controles_proximos": proximas,
        "incidencias_abiertas": incidencias_abiertas,
        "riesgos_registro": riesgos_registro,
        "recomendacion": recomendacion,
    }
