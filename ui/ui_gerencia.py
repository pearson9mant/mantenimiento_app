import streamlit as st
import pandas as pd

from modules.ordenes import obtener_ordenes, obtener_historico

from ui.ui_inventario import pantalla_inventario
from ui.ui_inventario_aulas import pantalla_inventario_aulas

from config_gerencia import (
    TIPOS_SOLICITANTE,
    ESTADOS_HECHAS,
    ESTADOS_EN_PROCESO,
    ESTADOS_FALTAN,
    MOSTRAR_MESES,
    MOSTRAR_CENTROS,
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
        return "Hechas"

    if estado in ESTADOS_EN_PROCESO:
        return "En proceso"

    if estado in ESTADOS_FALTAN:
        return "Faltan"

    return "Faltan"


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
    df["tipo_solicitante"] = df["tipo_solicitante"].fillna("Sin clasificar")
    df["centro"] = df["centro"].fillna("Sin centro")

    df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["mes"] = df["fecha_creacion"].dt.strftime("%Y-%m").fillna("Sin fecha")
    df["estado_resumen"] = df["estado"].apply(normalizar_estado)

    return df


def tabla_resumen(df, campo, orden=None):
    if df.empty or campo not in df.columns:
        return pd.DataFrame()

    tabla = (
        df.groupby([campo, "estado_resumen"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for col in ["Hechas", "En proceso", "Faltan"]:
        if col not in tabla.columns:
            tabla[col] = 0

    tabla["Total"] = tabla["Hechas"] + tabla["En proceso"] + tabla["Faltan"]
    tabla = tabla[[campo, "Total", "Hechas", "En proceso", "Faltan"]]

    if orden:
        tabla[campo] = pd.Categorical(tabla[campo], categories=orden, ordered=True)
        tabla = tabla.sort_values(campo)
        tabla[campo] = tabla[campo].astype(str)

    return tabla


def pintar_metricas_generales(df):
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total órdenes", len(df))
    col2.metric("Hechas", len(df[df["estado_resumen"] == "Hechas"]))
    col3.metric("En proceso", len(df[df["estado_resumen"] == "En proceso"]))
    col4.metric("Faltan", len(df[df["estado_resumen"] == "Faltan"]))


def pantalla_gerencia():
    st.title("📊 Panel Gerencia")

    df = preparar_dataframe_ordenes()

    if df.empty:
        st.warning("No hay órdenes registradas todavía.")
        return

    pintar_metricas_generales(df)
    st.markdown("---")

    with st.expander("📌 Órdenes por solicitante", expanded=True):
        st.dataframe(
            tabla_resumen(df, "tipo_solicitante", TIPOS_SOLICITANTE),
            use_container_width=True,
            hide_index=True
        )

    if MOSTRAR_MESES:
        with st.expander("📅 Órdenes por meses", expanded=False):
            st.dataframe(
                tabla_resumen(df, "mes"),
                use_container_width=True,
                hide_index=True
            )

    if MOSTRAR_CENTROS:
        with st.expander("🏫 Órdenes por centro", expanded=False):
            st.dataframe(
                tabla_resumen(df, "centro"),
                use_container_width=True,
                hide_index=True
            )

    if MOSTRAR_INVENTARIO:
        with st.expander("📦 Inventario mantenimiento completo", expanded=False):
            pantalla_inventario()

        with st.expander("🏫 Inventario aulas completo", expanded=False):
            pantalla_inventario_aulas()
