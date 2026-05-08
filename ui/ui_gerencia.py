import streamlit as st
import pandas as pd
from datetime import datetime

from database.db import conectar


CENTROS_GERENCIA = ["Pearson 9", "Pearson 22"]

ESTADOS_CERRADOS = [
    "Finalizada",
    "Finalizado",
    "Cerrada",
    "Cerrado"
]

ESTADOS_MATERIAL = [
    "Pendiente material",
    "Esperando material"
]


# =====================================================
# ESTILO VISUAL GERENCIA SIMPLE
# =====================================================

def aplicar_estilo_gerencia():
    st.markdown("""
    <style>
    .gerencia-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
        color: white;
        border-radius: 24px;
        padding: 24px 28px;
        margin-bottom: 22px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.18);
    }

    .gerencia-title {
        font-size: 30px;
        font-weight: 900;
        margin-bottom: 4px;
    }

    .gerencia-subtitle {
        font-size: 16px;
        font-weight: 600;
        opacity: 0.92;
    }

    .gerencia-section-title {
        font-size: 24px;
        font-weight: 900;
        color: #0f172a;
        margin-top: 20px;
        margin-bottom: 12px;
    }

    .gerencia-card-info {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 14px 16px;
        margin-bottom: 14px;
        color: #334155;
        font-weight: 700;
    }

    div.stButton > button {
        min-height: 92px;
        border-radius: 20px;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
        font-size: 18px;
        font-weight: 900;
        color: #0f172a;
        white-space: pre-line;
    }

    div.stButton > button:hover {
        border: 1px solid #2563eb;
        background: #eff6ff;
        color: #1d4ed8;
    }

    div[data-testid="stExpander"] {
        border-radius: 18px !important;
        border: 1px solid #e5e7eb !important;
        box-shadow: 0 5px 16px rgba(15, 23, 42, 0.05);
        margin-bottom: 10px;
    }

    @media (max-width: 768px) {
        .gerencia-title {
            font-size: 24px;
        }

        .gerencia-subtitle {
            font-size: 14px;
        }

        .gerencia-hero {
            padding: 20px 18px;
            border-radius: 20px;
        }

        div.stButton > button {
            min-height: 82px;
            font-size: 16px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# =====================================================
# LECTURA DATOS
# =====================================================

def leer_tabla(nombre_tabla):
    conn = conectar()

    try:
        df = pd.read_sql_query(f"SELECT * FROM {nombre_tabla}", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


def preparar_ordenes():
    ordenes = leer_tabla("ordenes_trabajo")
    historico = leer_tabla("historico_ordenes")

    if not ordenes.empty:
        ordenes["origen_tabla"] = "activas"

    if not historico.empty:
        historico["origen_tabla"] = "historico"
        historico["estado"] = "Finalizada"

    if ordenes.empty and historico.empty:
        return pd.DataFrame()

    df = pd.concat([ordenes, historico], ignore_index=True)

    columnas_defecto = {
        "numero_ot": "",
        "fecha_creacion": "",
        "fecha_cierre": "",
        "centro": "Sin centro",
        "edificio": "",
        "espacio": "",
        "descripcion": "",
        "estado": "Abierta",
        "operario": "",
        "solicitante": "",
        "origen": "",
        "area": "",
        "prioridad": "",
        "origen_tabla": "",
    }

    for col, valor in columnas_defecto.items():
        if col not in df.columns:
            df[col] = valor

    df["estado"] = df["estado"].fillna("").astype(str).str.strip()
    df["centro"] = df["centro"].fillna("").astype(str).str.strip()
    df["origen"] = df["origen"].fillna("").astype(str).str.strip()
    df["area"] = df["area"].fillna("").astype(str).str.strip()

    df["fecha_dt"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["fecha_cierre_dt"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")

    return df


# =====================================================
# FILTROS Y CONTADORES
# =====================================================

def es_cerrada(df):
    return (
        df["estado"].isin(ESTADOS_CERRADOS)
        | (df["origen_tabla"] == "historico")
    )


def es_esperando_material(df):
    return df["estado"].isin(ESTADOS_MATERIAL)


def es_abierta(df):
    return (
        (df["origen_tabla"] == "activas")
        & (~df["estado"].isin(ESTADOS_CERRADOS))
        & (~df["estado"].isin(ESTADOS_MATERIAL))
    )


def obtener_df_tarjeta(df, centro, tipo):
    datos = df[df["centro"] == centro].copy()

    if tipo == "abiertas":
        return datos[es_abierta(datos)]

    if tipo == "cerradas":
        return datos[es_cerrada(datos)]

    if tipo == "material":
        return datos[es_esperando_material(datos)]

    if tipo == "legionella_mes":
        return filtrar_realizadas_mes(datos, "legionella")

    if tipo == "preventivas_mes":
        return filtrar_realizadas_mes(datos, "preventivo")

    return pd.DataFrame()


def filtrar_realizadas_mes(df, origen_busqueda):
    if df.empty:
        return df

    hoy = datetime.today()
    mes_actual = hoy.month
    año_actual = hoy.year

    datos = df[es_cerrada(df)].copy()

    if datos.empty:
        return datos

    fecha_ref = datos["fecha_cierre_dt"]

    if fecha_ref.isna().all():
        fecha_ref = datos["fecha_dt"]

    datos = datos[
        (fecha_ref.dt.month == mes_actual)
        & (fecha_ref.dt.year == año_actual)
    ]

    texto = (
        datos["origen"].fillna("").astype(str)
        + " "
        + datos["area"].fillna("").astype(str)
        + " "
        + datos["descripcion"].fillna("").astype(str)
    ).str.lower()

    return datos[texto.str.contains(origen_busqueda, na=False)]


def contar(df, centro, tipo):
    return len(obtener_df_tarjeta(df, centro, tipo))


# =====================================================
# TARJETAS
# =====================================================

def boton_tarjeta(titulo, cantidad, centro, tipo, icono):
    texto = f"{icono} {cantidad}\n{titulo}"

    if st.button(texto, key=f"gerencia_{centro}_{tipo}", use_container_width=True):
        st.session_state["gerencia_detalle"] = {
            "centro": centro,
            "tipo": tipo,
            "titulo": titulo
        }
        st.rerun()


def mostrar_tarjetas_centro(df, centro):
    st.markdown(
        f"<div class='gerencia-section-title'>🏫 {centro}</div>",
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        boton_tarjeta(
            "Órdenes abiertas",
            contar(df, centro, "abiertas"),
            centro,
            "abiertas",
            "📂"
        )

    with c2:
        boton_tarjeta(
            "Órdenes cerradas",
            contar(df, centro, "cerradas"),
            centro,
            "cerradas",
            "✅"
        )

    with c3:
        boton_tarjeta(
            "Esperando material",
            contar(df, centro, "material"),
            centro,
            "material",
            "📦"
        )


def mostrar_tarjetas_legionella(df):
    st.markdown(
        "<div class='gerencia-section-title'>💧 Legionella realizadas este mes</div>",
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:
        boton_tarjeta(
            "Legionella Pearson 9",
            contar(df, "Pearson 9", "legionella_mes"),
            "Pearson 9",
            "legionella_mes",
            "💧"
        )

    with c2:
        boton_tarjeta(
            "Legionella Pearson 22",
            contar(df, "Pearson 22", "legionella_mes"),
            "Pearson 22",
            "legionella_mes",
            "💧"
        )


def mostrar_tarjetas_preventivas(df):
    st.markdown(
        "<div class='gerencia-section-title'>🛠️ Preventivas realizadas este mes</div>",
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:
        boton_tarjeta(
            "Preventivas Pearson 9",
            contar(df, "Pearson 9", "preventivas_mes"),
            "Pearson 9",
            "preventivas_mes",
            "🛠️"
        )

    with c2:
        boton_tarjeta(
            "Preventivas Pearson 22",
            contar(df, "Pearson 22", "preventivas_mes"),
            "Pearson 22",
            "preventivas_mes",
            "🛠️"
        )


# =====================================================
# DETALLE
# =====================================================

def mostrar_detalle(df):
    detalle = st.session_state.get("gerencia_detalle")

    if not detalle:
        return

    centro = detalle.get("centro")
    tipo = detalle.get("tipo")
    titulo = detalle.get("titulo")

    datos = obtener_df_tarjeta(df, centro, tipo)

    st.markdown("---")
    st.markdown(
        f"<div class='gerencia-section-title'>📋 Detalle · {titulo} · {centro}</div>",
        unsafe_allow_html=True
    )

    if st.button("❌ Cerrar detalle", use_container_width=True):
        st.session_state.pop("gerencia_detalle", None)
        st.rerun()

    if datos.empty:
        st.info("No hay registros para mostrar.")
        return

    columnas = [
        "numero_ot",
        "fecha_creacion",
        "fecha_cierre",
        "centro",
        "edificio",
        "espacio",
        "descripcion",
        "estado",
        "operario",
        "solicitante",
        "origen",
        "area",
        "prioridad",
    ]

    columnas = [c for c in columnas if c in datos.columns]

    st.dataframe(
        datos[columnas],
        use_container_width=True,
        hide_index=True
    )


# =====================================================
# PANTALLA PRINCIPAL
# =====================================================

def pantalla_gerencia():
    aplicar_estilo_gerencia()

    st.markdown("""
    <div class="gerencia-hero">
        <div class="gerencia-title">📊 Gerencia</div>
        <div class="gerencia-subtitle">
            Resumen simple por centro: abiertas, cerradas, material, Legionella y preventivas
        </div>
    </div>
    """, unsafe_allow_html=True)

    df = preparar_ordenes()

    if df.empty:
        st.warning("No hay órdenes para mostrar todavía.")
        return

    st.markdown(
        "<div class='gerencia-card-info'>Pulsa una tarjeta para ver el detalle filtrado.</div>",
        unsafe_allow_html=True
    )

    for centro in CENTROS_GERENCIA:
        mostrar_tarjetas_centro(df, centro)

    st.markdown("---")

    mostrar_tarjetas_legionella(df)

    st.markdown("---")

    mostrar_tarjetas_preventivas(df)

    mostrar_detalle(df)
