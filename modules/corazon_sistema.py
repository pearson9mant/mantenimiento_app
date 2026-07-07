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
    motivos = []

    area = normalizar(row.get("area"))
    origen = normalizar(row.get("origen"))
    prioridad = normalizar(row.get("prioridad"))
    descripcion = normalizar(row.get("descripcion"))

    if "legionella" in area or "legionella" in origen or "legionella" in descripcion:
        score += 95
        motivos.append("Riesgo sanitario / Legionella.")

    elif "urgente" in prioridad:
        score += 90
        motivos.append("Prioridad urgente.")

    elif "alta" in prioridad:
        score += 75
        motivos.append("Prioridad alta.")

    elif origen == "preventivo":
        score += 60
        motivos.append("Actuación preventiva pendiente.")

    elif origen in ["app", "outlook", "profesores", "externa"]:
        score += 55
        motivos.append("Incidencia o actuación externa abierta.")

    else:
        score += 40
        motivos.append("Orden abierta pendiente de gestión.")

    if "fuga" in descripcion or "agua" in descripcion or "perdida" in descripcion:
        score += 10
        motivos.append("Posible afectación por agua o fuga.")

    if "eléctr" in descripcion or "electric" in descripcion:
        score += 8
        motivos.append("Posible riesgo eléctrico.")

    if "clima" in descripcion or "aire" in descripcion:
        score += 6
        motivos.append("Afecta a climatización o confort.")

    score = min(score, 100)

    return score, motivos


def construir_prioridades_globales(centro=None, operario=None, limite=10):
    df = obtener_ordenes_abiertas_corazon(centro, operario)

    if df.empty:
        return []

    prioridades = []

    for _, row in df.iterrows():
        score, motivos = puntuar_orden(row)
    
        prioridades.append({
            "score": score,
    
            "tipo_prioridad": (
                "Sanitaria"
                if "legionella" in str(row.get("area", "")).lower()
                or "legionella" in str(row.get("origen", "")).lower()
                or "legionella" in str(row.get("descripcion", "")).lower()
                else "Urgente"
                if "urgente" in str(row.get("prioridad", "")).lower()
                else "Alta"
                if "alta" in str(row.get("prioridad", "")).lower()
                else "Preventiva"
                if str(row.get("origen", "")).upper() == "PREVENTIVO"
                else "Incidencia"
            ),
    
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
            "motivos": motivos,
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

import streamlit as st

from config import CENTROS
from modules.corazon_sistema import diagnosticar_corazon_sistema


def mostrar_corazon_sistema():
    st.markdown("## ❤️ Corazón del Sistema")

    centro_panel = st.selectbox(
        "Centro",
        ["Todos"] + CENTROS,
        key="corazon_centro"
    )

    centro_motor = None if centro_panel == "Todos" else centro_panel

    panel = diagnosticar_corazon_sistema(centro=centro_motor)

    color = panel.get("color", "verde")
    score = panel.get("score_global", 0)

    if color == "rojo":
        st.error(f"🔴 Estado global · {score}% · {panel.get('estado', '')}")
    elif color == "amarillo":
        st.warning(f"🟠 Estado global · {score}% · {panel.get('estado', '')}")
    else:
        st.success(f"🟢 Estado global · {score}% · {panel.get('estado', '')}")

    st.markdown(f"**{panel.get('mensaje', '')}**")

    kpis = panel.get("kpis", {})

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("OT abiertas", kpis.get("abiertas", 0))
    c2.metric("Incidencias", kpis.get("incidencias", 0))
    c3.metric("Preventivos", kpis.get("preventivos", 0))
    c4.metric("Legionella", kpis.get("legionella", 0))
    c5.metric("Alta/Urgente", kpis.get("urgentes", 0))

    st.markdown("### 🧠 Índices principales")

    i1, i2, i3 = st.columns(3)
    i1.metric("Operativo", f"{panel.get('score_operativo', 0)}%")
    i2.metric("Preventivo", f"{panel.get('score_preventivo', 0)}%")
    i3.metric("Sanitario", f"{panel.get('score_legionella', 0)}%")

    st.markdown("## 🎯 Si hoy solo hicieras una cosa...")

    prioridad = panel.get("prioridad_hoy")

    with st.container(border=True):
        if prioridad:
            st.markdown(f"### ⭐ {prioridad.get('numero_ot', '')}")
            st.markdown(f"## {prioridad.get('titulo', '')}")

            st.caption(
                f"{prioridad.get('centro', '')} · "
                f"{prioridad.get('edificio', '')} · "
                f"{prioridad.get('espacio', '')}"
            )

            st.markdown(f"**Área:** {prioridad.get('area', '-')}")
            st.markdown(f"**Origen:** {prioridad.get('origen', '-')}")
            st.markdown(f"**Prioridad:** {prioridad.get('prioridad', '-')}")
            st.markdown(f"**Puntuación:** {prioridad.get('score', 0)}/100")

            st.info(prioridad.get("accion", "Atender actuación."))

            st.markdown("#### 🧠 Motivo")
            st.markdown(prioridad.get("motivo", ""))
        else:
            st.success("No hay actuaciones prioritarias pendientes.")

    st.markdown("## 🚦 Prioridades globales")

    prioridades = panel.get("prioridades", [])

    if not prioridades:
        st.success("No hay trabajos pendientes prioritarios.")
    else:
        for i, p in enumerate(prioridades, start=1):
            with st.expander(
                f"{i}. {p.get('score', 0)}/100 · "
                f"{p.get('numero_ot', '')} · "
                f"{p.get('origen', '')} · "
                f"{p.get('area', '')}",
                expanded=False
            ):
                st.markdown(f"### {p.get('titulo', '')}")
                st.caption(
                    f"{p.get('centro', '')} · "
                    f"{p.get('edificio', '')} · "
                    f"{p.get('espacio', '')}"
                )

                st.markdown(f"**Estado:** {p.get('estado', '-')}")
                st.markdown(f"**Prioridad:** {p.get('prioridad', '-')}")
                st.markdown(f"**Operario:** {p.get('operario', '-')}")
                st.info(p.get("accion", ""))
                st.caption(p.get("motivo", ""))

    st.markdown("---")
