import streamlit as st
import pandas as pd
from datetime import datetime

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

    if "fecha_cierre" not in df.columns:
        df["fecha_cierre"] = None

    df["estado"] = df["estado"].fillna("Abierta")
    df["tipo_solicitante"] = df["tipo_solicitante"].fillna("Sin clasificar")
    df["centro"] = df["centro"].fillna("Sin centro")
    df["area"] = df["area"].fillna("Sin área")
    df["operario"] = df["operario"].fillna("Sin asignar")

    df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["fecha_cierre"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")

    df["mes"] = df["fecha_creacion"].dt.strftime("%Y-%m").fillna("Sin fecha")
    df["estado_resumen"] = df["estado"].apply(normalizar_estado)

    hoy = pd.Timestamp(datetime.now())
    df["dias_abierta"] = (hoy - df["fecha_creacion"]).dt.days
    df["dias_resolucion"] = (df["fecha_cierre"] - df["fecha_creacion"]).dt.days

    return df


def aplicar_filtros(df):
    st.markdown("### 🔎 Filtros")

    col1, col2 = st.columns(2)

    centros = ["Todos"] + sorted([c for c in df["centro"].dropna().unique() if c])
    meses = ["Todos"] + sorted([m for m in df["mes"].dropna().unique() if m])

    with col1:
        filtro_centro = st.selectbox("Centro", centros, key="gerencia_filtro_centro")

    with col2:
        filtro_mes = st.selectbox("Mes", meses, key="gerencia_filtro_mes")

    df_filtrado = df.copy()

    if filtro_centro != "Todos":
        df_filtrado = df_filtrado[df_filtrado["centro"] == filtro_centro]

    if filtro_mes != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes"] == filtro_mes]

    return df_filtrado


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


def pintar_alertas(df):
    abiertas_antiguas = df[
        (df["estado_resumen"] != "Hechas") &
        (df["dias_abierta"] >= 7)
    ]

    pendientes_material = df[df["estado"] == "Pendiente material"]

    finalizadas = df[df["estado_resumen"] == "Hechas"].copy()
    tiempo_medio = finalizadas["dias_resolucion"].dropna().mean()

    col1, col2, col3 = st.columns(3)

    col1.metric("Órdenes +7 días", len(abiertas_antiguas))
    col2.metric("Pendientes material", len(pendientes_material))

    if pd.notna(tiempo_medio):
        col3.metric("Tiempo medio cierre", f"{tiempo_medio:.1f} días")
    else:
        col3.metric("Tiempo medio cierre", "-")


def pintar_dashboard_visual(df):
    st.subheader("📈 Dashboard visual")

    tabla_solicitante = tabla_resumen(df, "tipo_solicitante", TIPOS_SOLICITANTE)

    if not tabla_solicitante.empty:
        tabla_solicitante = tabla_solicitante.set_index("tipo_solicitante")
        st.markdown("#### Órdenes por solicitante")
        st.bar_chart(tabla_solicitante[["Hechas", "En proceso", "Faltan"]])

    if MOSTRAR_MESES:
        tabla_meses = tabla_resumen(df, "mes")

        if not tabla_meses.empty:
            tabla_meses = tabla_meses.set_index("mes")
            st.markdown("#### Órdenes por meses")
            st.bar_chart(tabla_meses[["Hechas", "En proceso", "Faltan"]])

    if MOSTRAR_CENTROS:
        tabla_centros = tabla_resumen(df, "centro")

        if not tabla_centros.empty:
            tabla_centros = tabla_centros.set_index("centro")
            st.markdown("#### Órdenes por centro")
            st.bar_chart(tabla_centros[["Hechas", "En proceso", "Faltan"]])


def pintar_extra_gerencia(df):
    with st.expander("👷 Órdenes por operario", expanded=False):
        st.dataframe(
            tabla_resumen(df, "operario"),
            use_container_width=True,
            hide_index=True
        )

    with st.expander("🔧 Órdenes por área", expanded=False):
        st.dataframe(
            tabla_resumen(df, "area"),
            use_container_width=True,
            hide_index=True
        )

    with st.expander("⚠️ Órdenes abiertas de más de 7 días", expanded=False):
        antiguas = df[
            (df["estado_resumen"] != "Hechas") &
            (df["dias_abierta"] >= 7)
        ].copy()

        if antiguas.empty:
            st.success("No hay órdenes abiertas con más de 7 días.")
        else:
            st.dataframe(
                antiguas[[
                    "numero_ot", "descripcion", "estado", "centro",
                    "espacio", "area", "operario", "dias_abierta"
                ]],
                use_container_width=True,
                hide_index=True
            )


def pantalla_gerencia():
    st.title("📊 Panel Gerencia")

    df = preparar_dataframe_ordenes()

    if df.empty:
        st.warning("No hay órdenes registradas todavía.")
        return

    df = aplicar_filtros(df)

    if df.empty:
        st.warning("No hay datos con estos filtros.")
        return

    st.markdown("---")

    pintar_metricas_generales(df)
    st.markdown("---")

    pintar_alertas(df)
    st.markdown("---")

    pintar_dashboard_visual(df)
    st.markdown("---")

    pintar_extra_gerencia(df)

    with st.expander("📌 Órdenes por solicitante", expanded=False):
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
