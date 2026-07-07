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
        WHERE 1=1
        {filtro}
    """, tuple(params))

    if df.empty:
        return df

    estados_cierre = [
        "finalizada",
        "finalizado",
        "cerrada",
        "cerrado",
        "cancelada",
        "cancelado",
        "cerrado definitivo",
    ]

    estados = df["estado"].fillna("").astype(str).str.strip().str.lower()

    df_abiertas = df[
        ~estados.isin(estados_cierre)
    ].copy()

    return df_abiertas


from datetime import date
import pandas as pd


def puntuar_orden(row):
    score = 0
    motivos = []

    area = normalizar(row.get("area"))
    origen = normalizar(row.get("origen"))
    prioridad = normalizar(row.get("prioridad"))
    descripcion = normalizar(row.get("descripcion"))

    # -----------------------------
    # Prioridad principal
    # -----------------------------
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

    # -----------------------------
    # Riesgos detectados
    # -----------------------------
    if "fuga" in descripcion or "agua" in descripcion or "perdida" in descripcion:
        score += 10
        motivos.append("Posible afectación por agua.")

    if "eléctr" in descripcion or "electric" in descripcion:
        score += 8
        motivos.append("Posible riesgo eléctrico.")

    if "clima" in descripcion or "aire" in descripcion:
        score += 6
        motivos.append("Afecta a climatización o confort.")

    # -----------------------------
    # Antigüedad de la OT
    # -----------------------------
    fecha_txt = (
        row.get("fecha")
        or row.get("fecha_creacion")
        or row.get("fecha_alta")
        or ""
    )

    try:
        fecha_ot = pd.to_datetime(fecha_txt, errors="coerce")

        if pd.notna(fecha_ot):
            dias = (pd.Timestamp(date.today()) - fecha_ot).days

            if dias >= 90:
                score += 25
                motivos.append(f"Abierta desde hace {dias} días.")

            elif dias >= 60:
                score += 18
                motivos.append(f"Pendiente desde hace {dias} días.")

            elif dias >= 30:
                score += 12
                motivos.append(f"Más de un mes abierta ({dias} días).")

            elif dias >= 15:
                score += 6
                motivos.append(f"{dias} días sin resolver.")

    except Exception:
        pass

    # -----------------------------
    # Límite máximo
    # -----------------------------
    score = min(score, 100)

    return score, motivos


def construir_prioridades_globales(centro=None, operario=None, limite=100):
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
    print("========== CORAZÓN ==========")
    print("OT leídas:", len(df))
    
    try:
        print(df[[
            "numero_ot",
            "estado",
            "centro",
            "edificio",
            "origen"
        ]].to_string())
    except Exception:
        pass
    
    print("=============================")
    return prioridades[:limite]

def construir_grupos_inteligentes(prioridades):

    grupos = {}

    for p in prioridades:

        clave = (
            p.get("centro", ""),
            p.get("edificio", ""),
        )

        grupos.setdefault(clave, []).append(p)

    resultado = []

    for (centro, edificio), lista in grupos.items():

        score = max(x["score"] for x in lista)

        resultado.append({

            "centro": centro,
            "edificio": edificio,
            "cantidad": len(lista),
            "score": score,
            "trabajos": lista

        })

    resultado.sort(

        key=lambda x: (
            x["score"],
            x["cantidad"]
        ),

        reverse=True

    )

    return resultado

def construir_ruta_inteligente(grupos, limite=5):
    ruta = []

    for g in grupos[:limite]:
        trabajos = g.get("trabajos", [])

        tipos = {}
        for t in trabajos:
            tipo = t.get("tipo_prioridad", "Otros")
            tipos[tipo] = tipos.get(tipo, 0) + 1

        ruta.append({
            "centro": g.get("centro", ""),
            "edificio": g.get("edificio", ""),
            "cantidad": g.get("cantidad", 0),
            "score": g.get("score", 0),
            "tipos": tipos,
            "trabajos": trabajos,
            "mensaje": (
                f"Concentrar trabajos en {g.get('edificio', '')} "
                f"permite resolver {g.get('cantidad', 0)} actuaciones en una misma zona."
            )
        })

    return ruta

def construir_carga_por_edificio(prioridades):
    edificios = {}

    for p in prioridades:
        centro = p.get("centro", "") or "Sin centro"
        edificio = normalizar_edificio(p.get("edificio", "")) or "Sin edificio"
        clave = (centro, edificio)

        if clave not in edificios:
            edificios[clave] = {
                "centro": centro,
                "edificio": edificio,
                "total": 0,
                "score_max": 0,
                "sanitarias": 0,
                "preventivas": 0,
                "incidencias": 0,
                "urgentes": 0,
            }

        edificios[clave]["total"] += 1
        edificios[clave]["score_max"] = max(edificios[clave]["score_max"], p.get("score", 0))

        tipo = p.get("tipo_prioridad", "")

        if tipo == "Sanitaria":
            edificios[clave]["sanitarias"] += 1
        elif tipo == "Preventiva":
            edificios[clave]["preventivas"] += 1
        elif tipo in ["Urgente", "Alta"]:
            edificios[clave]["urgentes"] += 1
        else:
            edificios[clave]["incidencias"] += 1

    resultado = list(edificios.values())

    for e in resultado:
        score = 100
        score -= e["total"] * 3
        score -= e["sanitarias"] * 8
        score -= e["urgentes"] * 6
        score = max(0, min(100, score))

        e["salud"] = score

        if score >= 85:
            e["estado"] = "Controlado"
            e["color"] = "verde"
        elif score >= 60:
            e["estado"] = "Seguimiento"
            e["color"] = "amarillo"
        else:
            e["estado"] = "Carga alta"
            e["color"] = "rojo"

    resultado.sort(key=lambda x: (x["salud"], -x["total"]))

    return resultado


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

    prioridades = construir_prioridades_globales(centro, operario, limite=100)
    grupos = construir_grupos_inteligentes(prioridades)
    ruta = construir_ruta_inteligente(grupos)
    carga_edificios = construir_carga_por_edificio(prioridades)

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
        "grupos": grupos,
        "ruta": ruta,
        "carga_edificios": carga_edificios,
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

def normalizar_edificio(edificio):
    e = str(edificio or "").strip()

    equivalencias = {
        "Infantil/Primaria": "Edif. Infantil/Primaria",
        "Edif Infantil/Primaria": "Edif. Infantil/Primaria",
        "Edif. Infantil Primaria": "Edif. Infantil/Primaria",

        "Llar": "Edif. Llar (Anexo)",
        "Edif. Llar": "Edif. Llar (Anexo)",
        "Llar (Anexo)": "Edif. Llar (Anexo)",

        "A": "Edif. A",
        "B": "Edif. B",
        "C": "Edif. C",
    }

    return equivalencias.get(e, e)
