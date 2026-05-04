import streamlit as st
import pandas as pd

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

    ordenes = pd.DataFrame(datos_ordenes, columns=COLUMNAS_ORDENES) if datos_ordenes else pd.DataFrame(columns=COLUMNAS_ORDENES)
    historico = pd.DataFrame(datos_historico, columns=COLUMNAS_HISTORICO) if datos_historico else pd.DataFrame(columns=COLUMNAS_HISTORICO)

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
    tabla = df.groupby([campo, "estado_resumen"]).size().unstack(fill_value=0).reset_index()

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


def pintar_inventario_mantenimiento():
    columnas = [
        "id", "codigo", "material", "categoria", "unidad",
        "stock_actual", "stock_minimo", "centro", "edificio",
        "ubicacion", "proveedor", "observaciones", "fecha_alta",
        "foto", "activo", "precio_unitario", "coste_total",
        "fecha_compra", "referencia_factura", "observaciones_coste"
    ]

    inventario = pd.DataFrame(obtener_materiales_inventario(), columns=columnas)

    if inventario.empty:
        st.info("No hay inventario de mantenimiento.")
        return

    inventario["stock_actual"] = pd.to_numeric(inventario["stock_actual"], errors="coerce").fillna(0)
    inventario["stock_minimo"] = pd.to_numeric(inventario["stock_minimo"], errors="coerce").fillna(0)

    bajo_stock = inventario[inventario["stock_actual"] <= inventario["stock_minimo"]]
    sin_stock = inventario[inventario["stock_actual"] <= 0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Materiales", len(inventario))
    c2.metric("Bajo stock", len(bajo_stock))
    c3.metric("Sin stock", len(sin_stock))

    resumen_centro = inventario.groupby("centro").size().reset_index(name="Materiales")
    st.markdown("#### Por centro")
    st.dataframe(resumen_centro, use_container_width=True, hide_index=True)

    if not bajo_stock.empty:
        st.markdown("#### Alertas de stock")
        st.dataframe(
            bajo_stock[["codigo", "material", "stock_actual", "stock_minimo", "centro", "ubicacion"]],
            use_container_width=True,
            hide_index=True
        )


def pintar_inventario_aulas_gerencia():
    crear_tabla_inventario_aulas()

    columnas = [
        "id", "fecha_revision", "centro", "edificio", "espacio", "elemento",
        "cantidad", "estado", "ancho", "alto", "fondo", "unidad",
        "observaciones", "foto", "operario", "fecha_creacion"
    ]

    registros = obtener_inventario_aulas()
    aulas = pd.DataFrame(registros, columns=columnas) if registros else pd.DataFrame(columns=columnas)

    if aulas.empty:
        st.info("No hay inventario de aulas registrado.")
        return

    aulas["cantidad"] = pd.to_numeric(aulas["cantidad"], errors="coerce").fillna(0)

    total = len(aulas)
    correctos = len(aulas[aulas["estado"] == "Correcto"])
    regular = len(aulas[aulas["estado"] == "Regular"])
    revisar = len(aulas[aulas["estado"].isin(["Dañado", "Falta", "Retirar"])])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", total)
    c2.metric("Correctos", correctos)
    c3.metric("Regular", regular)
    c4.metric("Revisar", revisar)

    st.markdown("#### Por estado")
    estado_df = aulas.groupby("estado")["cantidad"].sum().reset_index(name="Cantidad")
    st.dataframe(estado_df, use_container_width=True, hide_index=True)

    st.markdown("#### Por centro")
    centro_df = aulas.groupby(["centro", "estado"]).size().unstack(fill_value=0).reset_index()
    st.dataframe(centro_df, use_container_width=True, hide_index=True)

    st.markdown("#### Últimos registros")
    ultimos = aulas.sort_values("fecha_revision", ascending=False).head(20)
    st.dataframe(
        ultimos[["fecha_revision", "centro", "edificio", "espacio", "elemento", "cantidad", "estado"]],
        use_container_width=True,
        hide_index=True
    )


def pantalla_gerencia():
    st.title("📊 Panel Gerencia")

    df = preparar_dataframe_ordenes()

    if df.empty:
        st.warning("No hay órdenes registradas todavía.")
        return

    pintar_metricas_generales(df)
    st.markdown("---")

    with st.expander("📌 Órdenes por solicitante", expanded=True):
        st.dataframe(tabla_resumen(df, "tipo_solicitante", TIPOS_SOLICITANTE), use_container_width=True, hide_index=True)

    if MOSTRAR_MESES:
        with st.expander("📅 Órdenes por meses", expanded=False):
            st.dataframe(tabla_resumen(df, "mes"), use_container_width=True, hide_index=True)

    if MOSTRAR_CENTROS:
        with st.expander("🏫 Órdenes por centro", expanded=False):
            st.dataframe(tabla_resumen(df, "centro"), use_container_width=True, hide_index=True)

    if MOSTRAR_INVENTARIO:
    with st.expander("📦 Inventario mantenimiento completo", expanded=False):
        pantalla_inventario()

    with st.expander("🏫 Inventario aulas completo", expanded=False):
        pantalla_inventario_aulas()
