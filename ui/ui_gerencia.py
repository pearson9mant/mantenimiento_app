import streamlit as st
import pandas as pd
from datetime import datetime

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
        return "Pendientes"

    if estado in ESTADOS_FALTAN:
        return "Pendientes"

    return "Pendientes"


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

    if "fecha_cierre" not in df.columns:
        df["fecha_cierre"] = None

    df["estado"] = df["estado"].fillna("Abierta")
    df["centro"] = df["centro"].fillna("Sin centro")

    df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["fecha_cierre"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")

    df["mes"] = df["fecha_creacion"].dt.strftime("%Y-%m").fillna("Sin fecha")
    df["estado_resumen"] = df["estado"].apply(normalizar_estado)

    hoy = pd.Timestamp(datetime.now())
    df["dias_abierta"] = (hoy - df["fecha_creacion"]).dt.days

    return df


def calcular_resumen(df):
    total = len(df)
    terminadas = len(df[df["estado_resumen"] == "Terminadas"])
    pendientes = len(df[df["estado_resumen"] == "Pendientes"])

    cumplimiento = 0
    if total > 0:
        cumplimiento = round((terminadas / total) * 100, 1)

    return total, terminadas, pendientes, cumplimiento


def pintar_resumen_general(df):
    total, terminadas, pendientes, cumplimiento = calcular_resumen(df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total órdenes", total)
    c2.metric("Terminadas", terminadas)
    c3.metric("Pendientes", pendientes)
    c4.metric("% cumplimiento", f"{cumplimiento}%")


def pintar_tarjeta_centro(df, centro):
    total, terminadas, pendientes, cumplimiento = calcular_resumen(df)

    st.markdown(f"### 🏫 {centro}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("Terminadas", terminadas)
    c3.metric("Pendientes", pendientes)
    c4.metric("Cumplimiento", f"{cumplimiento}%")

    st.markdown("---")


def pintar_evolucion_mensual(df):
    st.markdown("### 📅 Evolución mensual")

    tabla = (
        df.groupby(["mes", "estado_resumen"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for col in ["Terminadas", "Pendientes"]:
        if col not in tabla.columns:
            tabla[col] = 0

    tabla = tabla[["mes", "Terminadas", "Pendientes"]]

    if tabla.empty:
        st.info("Sin datos por meses.")
        return

    st.bar_chart(tabla.set_index("mes"))


def pintar_alertas(df):
    st.markdown("### ⚠️ Alertas")

    antiguas = df[
        (df["estado_resumen"] != "Terminadas") &
        (df["dias_abierta"] >= 7)
    ]

    pendientes_material = df[df["estado"] == "Pendiente material"]

    c1, c2 = st.columns(2)
    c1.metric("Órdenes +7 días", len(antiguas))
    c2.metric("Pendiente material", len(pendientes_material))


def pantalla_gerencia():
    st.title("📊 Panel Gerencia")

    df = preparar_dataframe_ordenes()

    if df.empty:
        st.warning("No hay órdenes registradas todavía.")
        return

    pintar_resumen_general(df)

    st.markdown("---")

    for centro in ["Pearson 22", "Pearson 9"]:
        df_centro = df[df["centro"] == centro]
        pintar_tarjeta_centro(df_centro, centro)

    pintar_evolucion_mensual(df)

    st.markdown("---")

    pintar_alertas(df)

    st.markdown("---")

    if MOSTRAR_INVENTARIO:
        with st.expander("📦 Inventario mantenimiento", expanded=False):
            pantalla_inventario()

        with st.expander("🏫 Inventario aulas", expanded=False):
            pantalla_inventario_aulas()
