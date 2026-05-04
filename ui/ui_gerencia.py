import streamlit as st
import pandas as pd

from modules.ordenes import obtener_ordenes, obtener_historico

from ui.ui_inventario import pantalla_inventario
from ui.ui_inventario_aulas import pantalla_inventario_aulas

from config_gerencia import (
    ESTADOS_HECHAS,
    ESTADOS_EN_PROCESO,
    ESTADOS_FALTAN,
    MOSTRAR_INVENTARIO,
)


COLUMNAS_ORDENES = [
    "id", "numero_ot", "descripcion", "estado", "fecha_creacion",
    "centro", "edificio", "espacio", "area", "prioridad", "operario",
    "origen", "solicitante", "fecha_origen", "foto", "tipo_solicitante"
]

COLUMNAS_HISTORICO = [
    "id", "numero_ot", "descripcion", "estado", "fecha_creacion",
    "centro", "edificio", "espacio", "area", "prioridad", "operario",
    "origen", "solicitante", "fecha_origen", "fecha_cierre",
    "observaciones_cierre", "foto", "tipo_solicitante"
]


def normalizar_texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def normalizar_estado(estado):
    estado = normalizar_texto(estado)

    if estado in ESTADOS_HECHAS:
        return "Terminadas"

    if estado in ESTADOS_EN_PROCESO:
        return "Por hacer"

    if estado in ESTADOS_FALTAN:
        return "Por hacer"

    return "Por hacer"


def preparar_dataframe_ordenes():
    datos_ordenes = obtener_ordenes()
    datos_historico = obtener_historico()

    ordenes = (
        pd.DataFrame(datos_ordenes, columns=COLUMNAS_ORDENES)
        if datos_ordenes
        else pd.DataFrame(columns=COLUMNAS_ORDENES)
    )

    historico = (
        pd.DataFrame(datos_historico, columns=COLUMNAS_HISTORICO)
        if datos_historico
        else pd.DataFrame(columns=COLUMNAS_HISTORICO)
    )

    if ordenes.empty and historico.empty:
        return pd.DataFrame()

    df = pd.concat([ordenes, historico], ignore_index=True)

    df["estado"] = df["estado"].fillna("Abierta")
    df["centro"] = df["centro"].fillna("Sin centro")

    df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["mes"] = df["fecha_creacion"].dt.strftime("%Y-%m").fillna("Sin fecha")
    df["estado_resumen"] = df["estado"].apply(normalizar_estado)

    return df


def resumen_centro(df):
    terminadas = len(df[df["estado_resumen"] == "Terminadas"])
    por_hacer = len(df[df["estado_resumen"] == "Por hacer"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total órdenes", len(df))
    c2.metric("Terminadas", terminadas)
    c3.metric("Por hacer", por_hacer)


def grafico_meses(df):
    tabla = (
        df.groupby(["mes", "estado_resumen"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for col in ["Terminadas", "Por hacer"]:
        if col not in tabla.columns:
            tabla[col] = 0

    tabla = tabla[["mes", "Terminadas", "Por hacer"]]

    if tabla.empty:
        st.info("Sin datos por meses.")
        return

    st.bar_chart(tabla.set_index("mes"))


def pintar_centro(df, centro):
    with st.expander(f"🏫 {centro}", expanded=False):
        resumen_centro(df)

        st.markdown("### 📅 Por meses")
        grafico_meses(df)


def pantalla_gerencia():
    st.title("📊 Panel Gerencia")

    df = preparar_dataframe_ordenes()

    if df.empty:
        st.warning("No hay órdenes registradas todavía.")
        return

    centros = sorted([c for c in df["centro"].dropna().unique().tolist() if c])

    for centro in centros:
        df_centro = df[df["centro"] == centro]
        pintar_centro(df_centro, centro)

    st.markdown("---")

    if MOSTRAR_INVENTARIO:
        with st.expander("📦 Inventario mantenimiento completo", expanded=False):
            pantalla_inventario()

        with st.expander("🏫 Inventario aulas completo", expanded=False):
            pantalla_inventario_aulas()
