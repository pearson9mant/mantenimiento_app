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


def tabla_resumen(df, campo, orden=None):
    if df.empty or campo not in df.columns:
        return pd.DataFrame()

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


def crear_dashboard_centro(df, centro_nombre):
    total = len(df)
    hechas = len(df[df["estado_resumen"] == "Hechas"])
    en_proceso = len(df[df["estado_resumen"] == "En proceso"])
    faltan = len(df[df["estado_resumen"] == "Faltan"])
    pendientes_material = len(df[df["estado"] == "Pendiente material"])
    antiguas = len(df[(df["estado_resumen"] != "Hechas") & (df["dias_abierta"] >= 7)])

    finalizadas = df[df["estado_resumen"] == "Hechas"]
    tiempo_medio = finalizadas["dias_resolucion"].dropna().mean()

    datos = {
        "Centro": centro_nombre,
        "Total órdenes": total,
        "Hechas": hechas,
        "En proceso": en_proceso,
        "Sin finalizar": faltan,
        "Pendiente material": pendientes_material,
        "+7 días": antiguas,
        "Tiempo medio cierre": f"{tiempo_medio:.1f} días" if pd.notna(tiempo_medio) else "-",
    }

    for tipo in TIPOS_SOLICITANTE:
        datos[tipo] = len(df[df["tipo_solicitante"] == tipo])

    area_principal = "-"
    if "area" in df.columns and not df.empty:
        areas = df["area"].dropna()
        if not areas.empty:
            area_principal = areas.value_counts().idxmax()

    operario_principal = "-"
    if "operario" in df.columns and not df.empty:
        operarios = df["operario"].dropna()
        if not operarios.empty:
            operario_principal = operarios.value_counts().idxmax()

    datos["Área principal"] = area_principal
    datos["Operario principal"] = operario_principal

    return pd.DataFrame([datos])


def pintar_bloque_centro(df, centro_nombre):
    with st.expander(f"🏫 {centro_nombre}", expanded=False):
        dashboard = crear_dashboard_centro(df, centro_nombre)
        st.dataframe(dashboard, use_container_width=True, hide_index=True)

        st.markdown("#### 📌 Solicitantes")
        st.dataframe(
            tabla_resumen(df, "tipo_solicitante", TIPOS_SOLICITANTE),
            use_container_width=True,
            hide_index=True
        )

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 🔧 Áreas")
            st.dataframe(
                tabla_resumen(df, "area"),
                use_container_width=True,
                hide_index=True
            )

        with c2:
            st.markdown("#### 👷 Operarios")
            st.dataframe(
                tabla_resumen(df, "operario"),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("#### 📅 Meses")
        st.dataframe(
            tabla_resumen(df, "mes"),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### ⚠️ Órdenes abiertas +7 días")
        antiguas = df[(df["estado_resumen"] != "Hechas") & (df["dias_abierta"] >= 7)]

        if antiguas.empty:
            st.success("Todo al día 👍")
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

    centros = ["Todos"] + sorted([c for c in df["centro"].dropna().unique().tolist() if c])
    centro_sel = st.selectbox("🏫 Selecciona centro", centros, key="gerencia_centro_dashboard")

    if centro_sel != "Todos":
        df_vista = df[df["centro"] == centro_sel]
        pintar_bloque_centro(df_vista, centro_sel)
    else:
        pintar_bloque_centro(df, "Todos los centros")

        for centro in sorted([c for c in df["centro"].dropna().unique().tolist() if c]):
            df_centro = df[df["centro"] == centro]
            pintar_bloque_centro(df_centro, centro)

    st.markdown("---")

    if MOSTRAR_INVENTARIO:
        with st.expander("📦 Inventario mantenimiento completo", expanded=False):
            pantalla_inventario()

        with st.expander("🏫 Inventario aulas completo", expanded=False):
            pantalla_inventario_aulas()
