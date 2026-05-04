import streamlit as st
import pandas as pd
from database.db import conectar

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


def leer_tabla(nombre_tabla):
    conn = conectar()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {nombre_tabla}", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


def clasificar_estado(estado):
    estado = str(estado).strip()

    if estado in ESTADOS_HECHAS:
        return "Hechas"

    if estado in ESTADOS_EN_PROCESO:
        return "En proceso"

    if estado in ESTADOS_FALTAN:
        return "Faltan"

    return "Faltan"


def clasificar_solicitante(row):
    solicitante = str(row.get("solicitante", "")).strip()
    origen = str(row.get("origen", "")).strip()

    texto = f"{solicitante} {origen}".lower()

    for tipo, nombres in TIPOS_SOLICITANTE.items():
        for nombre in nombres:
            if nombre.lower() in texto:
                return tipo

    if "profesor" in texto:
        return "Profesores"

    if "forms" in texto:
        return "Profesores"

    if "outlook" in texto:
        return "Profesores"

    if "incidencia profesor" in texto:
        return "Profesores"

    if "profesores" in texto:
        return "Profesores"

    if solicitante:
        return "Profesores"

    return "Sin clasificar"


def preparar_ordenes():
    ordenes = leer_tabla("ordenes_trabajo")
    historico = leer_tabla("historico_ordenes")

    if ordenes.empty and historico.empty:
        return pd.DataFrame()

    if not historico.empty:
        historico["estado"] = "Finalizada"

    df = pd.concat([ordenes, historico], ignore_index=True)

    if "fecha" not in df.columns:
        df["fecha"] = ""

    if "fecha_cierre" not in df.columns:
        df["fecha_cierre"] = ""

    if "estado" not in df.columns:
        df["estado"] = "Abierta"

    if "centro" not in df.columns:
        df["centro"] = "Sin centro"

    if "operario" not in df.columns:
        df["operario"] = "Sin asignar"

    if "solicitante" not in df.columns:
        df["solicitante"] = ""

    if "origen" not in df.columns:
        df["origen"] = ""

    df["grupo_estado"] = df["estado"].apply(clasificar_estado)
    df["tipo_solicitante"] = df.apply(clasificar_solicitante, axis=1)

    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["fecha_cierre_dt"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")

    df["mes"] = df["fecha_dt"].dt.strftime("%Y-%m")
    df["mes"] = df["mes"].fillna("Sin fecha")

    df["dias_resolucion"] = (
        df["fecha_cierre_dt"] - df["fecha_dt"]
    ).dt.days

    return df


def mostrar_metricas(df):
    total = len(df)
    hechas = len(df[df["grupo_estado"] == "Hechas"])
    proceso = len(df[df["grupo_estado"] == "En proceso"])
    faltan = len(df[df["grupo_estado"] == "Faltan"])

    rendimiento = round((hechas / total) * 100, 1) if total else 0

    if "dias_resolucion" in df.columns:
        tiempo = df["dias_resolucion"].dropna()
        tiempo_medio = round(tiempo.mean(), 1) if not tiempo.empty else 0
    else:
        tiempo_medio = 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Total OTs", total)
    c2.metric("Hechas", hechas)
    c3.metric("En proceso", proceso)
    c4.metric("Faltan", faltan)
    c5.metric("Rendimiento", f"{rendimiento}%")
    c6.metric("Media cierre", f"{tiempo_medio} días")


def mostrar_tabla_resumen(df, columnas):
    if df.empty:
        st.info("No hay datos para mostrar.")
        return

    tabla = (
        df.groupby(columnas + ["grupo_estado"])
        .size()
        .reset_index(name="cantidad")
    )

    pivot = tabla.pivot_table(
        index=columnas,
        columns="grupo_estado",
        values="cantidad",
        fill_value=0
    ).reset_index()

    for col in ["Hechas", "En proceso", "Faltan"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot["Total"] = pivot["Hechas"] + pivot["En proceso"] + pivot["Faltan"]

    columnas_orden = columnas + ["Hechas", "En proceso", "Faltan", "Total"]
    pivot = pivot[columnas_orden]

    st.dataframe(
        pivot,
        use_container_width=True,
        hide_index=True
    )


def mostrar_rendimiento_operarios(df):
    if df.empty:
        st.info("No hay datos para mostrar.")
        return

    if "operario" not in df.columns:
        st.info("No hay columna de operario.")
        return

    tabla = (
        df.groupby("operario")
        .agg(
            Total=("grupo_estado", "count"),
            Hechas=("grupo_estado", lambda x: (x == "Hechas").sum()),
            En_proceso=("grupo_estado", lambda x: (x == "En proceso").sum()),
            Faltan=("grupo_estado", lambda x: (x == "Faltan").sum()),
            Media_cierre_dias=("dias_resolucion", "mean"),
        )
        .reset_index()
    )

    tabla["Rendimiento %"] = tabla.apply(
        lambda r: round((r["Hechas"] / r["Total"]) * 100, 1) if r["Total"] else 0,
        axis=1
    )

    tabla["Media_cierre_dias"] = tabla["Media_cierre_dias"].fillna(0).round(1)

    tabla = tabla.rename(columns={
        "operario": "Operario",
        "En_proceso": "En proceso",
        "Media_cierre_dias": "Media cierre días",
    })

    tabla = tabla[
        [
            "Operario",
            "Total",
            "Hechas",
            "En proceso",
            "Faltan",
            "Rendimiento %",
            "Media cierre días",
        ]
    ]

    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True
    )


def mostrar_inventario():
    inventario = leer_tabla("inventario")

    if inventario.empty:
        st.info("No hay inventario registrado.")
        return

    st.markdown("### 📦 Inventario")

    if "activo" in inventario.columns:
        inventario = inventario[inventario["activo"].fillna(1).astype(int) == 1]

    if "stock" not in inventario.columns:
        inventario["stock"] = 0

    inventario["stock"] = pd.to_numeric(inventario["stock"], errors="coerce").fillna(0)

    bajo_stock = inventario[inventario["stock"] <= STOCK_BAJO]

    c1, c2, c3 = st.columns(3)

    c1.metric("Materiales activos", len(inventario))
    c2.metric("Stock bajo", len(bajo_stock))

    if "coste_total" in inventario.columns:
        inventario["coste_total"] = pd.to_numeric(
            inventario["coste_total"],
            errors="coerce"
        ).fillna(0)

        coste_total = inventario["coste_total"].sum()
        c3.metric("Valor inventario", f"{coste_total:,.2f} €")
    else:
        c3.metric("Valor inventario", "Sin datos")

    with st.expander("📉 Materiales con stock bajo", expanded=False):
        if bajo_stock.empty:
            st.success("No hay materiales con stock bajo.")
        else:
            columnas = [
                "codigo",
                "material",
                "categoria",
                "stock",
                "ubicacion",
            ]

            columnas = [c for c in columnas if c in bajo_stock.columns]

            st.dataframe(
                bajo_stock[columnas],
                use_container_width=True,
                hide_index=True
            )

    with st.expander("📦 Inventario completo", expanded=False):
        columnas = [
            "codigo",
            "material",
            "categoria",
            "stock",
            "precio_unitario",
            "coste_total",
            "ubicacion",
        ]

        columnas = [c for c in columnas if c in inventario.columns]

        st.dataframe(
            inventario[columnas],
            use_container_width=True,
            hide_index=True
        )


def pantalla_gerencia():
    st.subheader("📊 Gerencia Pro")

    df = preparar_ordenes()

    if df.empty:
        st.warning("No hay órdenes para analizar.")
        return

    st.markdown("### 🔎 Filtros")

    col1, col2 = st.columns(2)

    centros = ["Todos"] + sorted(df["centro"].dropna().astype(str).unique().tolist())
    centro_sel = col1.selectbox("Centro", centros)

    meses = ["Todos"] + sorted(df["mes"].dropna().astype(str).unique().tolist(), reverse=True)
    mes_sel = col2.selectbox("Mes", meses)

    if centro_sel != "Todos":
        df = df[df["centro"] == centro_sel]

    if mes_sel != "Todos":
        df = df[df["mes"] == mes_sel]

    st.markdown("---")

    mostrar_metricas(df)

    st.markdown("---")

    with st.expander("📌 Órdenes por tipo de solicitante", expanded=True):
        mostrar_tabla_resumen(df, ["tipo_solicitante"])

    with st.expander("👷 Órdenes por operario", expanded=False):
        mostrar_tabla_resumen(df, ["operario"])

    with st.expander("📈 Rendimiento real por operario", expanded=True):
        mostrar_rendimiento_operarios(df)

    if MOSTRAR_CENTROS:
        with st.expander("🏫 Órdenes por centro", expanded=False):
            mostrar_tabla_resumen(df, ["centro"])

    if MOSTRAR_MESES:
        with st.expander("📅 Órdenes por mes", expanded=False):
            mostrar_tabla_resumen(df, ["mes"])

    with st.expander("📋 Detalle de órdenes", expanded=False):
        columnas = [
            "numero_ot",
            "fecha",
            "fecha_cierre",
            "centro",
            "edificio",
            "espacio",
            "descripcion",
            "estado",
            "grupo_estado",
            "operario",
            "solicitante",
            "tipo_solicitante",
            "origen",
            "dias_resolucion",
        ]

        columnas = [c for c in columnas if c in df.columns]

        st.dataframe(
            df[columnas],
            use_container_width=True,
            hide_index=True
        )

    if MOSTRAR_INVENTARIO:
        st.markdown("---")
        mostrar_inventario()
