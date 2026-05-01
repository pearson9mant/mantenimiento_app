import streamlit as st
import pandas as pd

from modules.ordenes import obtener_ordenes, obtener_historico
from modules.inventario import listar_inventario

from config_gerencia import (
    TIPOS_SOLICITANTE,
    ESTADOS_HECHAS,
    ESTADOS_EN_PROCESO,
    ESTADOS_FALTAN,
    MOSTRAR_MESES,
    MOSTRAR_CENTROS,
    MOSTRAR_INVENTARIO,
    STOCK_BAJO,
)


def normalizar_texto(valor):
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
    ordenes = pd.DataFrame(obtener_ordenes())
    historico = pd.DataFrame(obtener_historico())

    if ordenes.empty and historico.empty:
        return pd.DataFrame()

    df = pd.concat([ordenes, historico], ignore_index=True)

    if "estado" not in df.columns:
        df["estado"] = "Abierta"

    if "tipo_solicitante" not in df.columns:
        df["tipo_solicitante"] = "Sin clasificar"

    if "centro" not in df.columns:
        df["centro"] = "Sin centro"

    if "fecha_creacion" in df.columns:
        df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
        df["mes"] = df["fecha_creacion"].dt.strftime("%Y-%m")
        df["mes"] = df["mes"].fillna("Sin fecha")
    else:
        df["mes"] = "Sin fecha"

    df["estado_resumen"] = df["estado"].apply(normalizar_estado)
    df["tipo_solicitante"] = df["tipo_solicitante"].fillna("Sin clasificar")

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
    total = len(df)
    hechas = len(df[df["estado_resumen"] == "Hechas"])
    proceso = len(df[df["estado_resumen"] == "En proceso"])
    faltan = len(df[df["estado_resumen"] == "Faltan"])

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total órdenes", total)
    col2.metric("Hechas", hechas)
    col3.metric("En proceso", proceso)
    col4.metric("Faltan", faltan)


def pintar_inventario():
    try:
       inventario = pd.DataFrame(listar_inventario())

        if inventario.empty:
            st.info("No hay inventario registrado.")
            return

        total_material = len(inventario)

        columna_stock = None

        if "stock" in inventario.columns:
            columna_stock = "stock"
        elif "cantidad" in inventario.columns:
            columna_stock = "cantidad"

        if columna_stock:
            inventario[columna_stock] = pd.to_numeric(
                inventario[columna_stock], errors="coerce"
            ).fillna(0)

            bajo_stock = len(inventario[inventario[columna_stock] <= STOCK_BAJO])
            sin_stock = len(inventario[inventario[columna_stock] <= 0])
        else:
            bajo_stock = 0
            sin_stock = 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total materiales", total_material)
        c2.metric("Bajo stock", bajo_stock)
        c3.metric("Sin stock", sin_stock)

        st.dataframe(inventario, use_container_width=True, hide_index=True)

    except Exception as e:
        st.warning("No se pudo cargar el inventario.")
        st.caption(str(e))


def pantalla_gerencia():
    st.title("📊 Panel Gerencia")

    df = preparar_dataframe_ordenes()

    if df.empty:
        st.warning("No hay órdenes registradas todavía.")
        return

    pintar_metricas_generales(df)

    st.markdown("---")

    with st.expander("📌 Órdenes por solicitante", expanded=True):
        tabla = tabla_resumen(df, "tipo_solicitante", TIPOS_SOLICITANTE)
        st.dataframe(tabla, use_container_width=True, hide_index=True)

    if MOSTRAR_MESES:
        with st.expander("📅 Órdenes por meses", expanded=False):
            tabla = tabla_resumen(df, "mes")
            st.dataframe(tabla, use_container_width=True, hide_index=True)

    if MOSTRAR_CENTROS:
        with st.expander("🏫 Órdenes por centro", expanded=False):
            tabla = tabla_resumen(df, "centro")
            st.dataframe(tabla, use_container_width=True, hide_index=True)

    if MOSTRAR_INVENTARIO:
        with st.expander("📦 Inventario", expanded=False):
            pintar_inventario()
