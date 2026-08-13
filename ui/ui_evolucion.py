import streamlit as st
import pandas as pd
from datetime import date

from database.db import conectar


def _leer_df(sql):
    conn = conectar()
    try:
        return pd.read_sql_query(sql, conn)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def _preparar_historico():
    df = _leer_df("""
        SELECT
            id,
            numero_ot,
            fecha_creacion,
            fecha_cierre,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            descripcion
        FROM historico_ordenes
        ORDER BY fecha_cierre
    """)

    if df.empty:
        return df

    df["fecha"] = pd.to_datetime(
        df["fecha_cierre"],
        errors="coerce"
    )

    df = df[df["fecha"].notna()].copy()

    df["origen_txt"] = (
        df["origen"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["descripcion_txt"] = (
        df["descripcion"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    df["tipo_evolucion"] = "OT correctivas"

    es_preventivo = (
        (df["origen_txt"] == "PREVENTIVO")
        | df["descripcion_txt"].str.startswith("[PREVENTIVO]")
    )

    es_legionella = (
        (df["origen_txt"] == "LEGIONELLA")
        | (df["area"].fillna("").astype(str).str.upper() == "LEGIONELLA")
    )

    es_incidencia = df["origen_txt"].isin(
        [
            "APP",
            "OUTLOOK",
            "PROFESORES",
            "INVENTARIO",
            "EXTERNA",
        ]
    )

    df.loc[es_incidencia, "tipo_evolucion"] = "Incidencias / correctivas"
    df.loc[es_legionella, "tipo_evolucion"] = "Legionella"
    df.loc[es_preventivo, "tipo_evolucion"] = "Preventivas"

    return df


def _filtros_evolucion(df):
    if df.empty:
        return df

    fechas = df["fecha"].dropna()

    fecha_min = fechas.min().date()
    fecha_max = fechas.max().date()

    c1, c2, c3 = st.columns(3)

    with c1:
        desde = st.date_input(
            "Desde",
            value=fecha_min,
            key="evol_desde"
        )

    with c2:
        hasta = st.date_input(
            "Hasta",
            value=fecha_max,
            key="evol_hasta"
        )

    with c3:
        centros = ["Todos"] + sorted(
            df["centro"]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda s: s != ""]
            .unique()
            .tolist()
        )

        centro = st.selectbox(
            "Centro",
            centros,
            key="evol_centro"
        )

    filtrado = df[
        (df["fecha"].dt.date >= desde)
        & (df["fecha"].dt.date <= hasta)
    ].copy()

    if centro != "Todos":
        filtrado = filtrado[
            filtrado["centro"].astype(str) == centro
        ]

    return filtrado


def pantalla_evolucion():
    st.subheader("📈 Evolución")

    st.caption(
        "Solo gráficos. La pantalla muestra la evolución real "
        "a partir del histórico de trabajos finalizados."
    )

    df = _preparar_historico()

    if df.empty:
        st.info(
            "Todavía no hay histórico suficiente para mostrar evolución."
        )
        return

    df = _filtros_evolucion(df)

    if df.empty:
        st.info("No hay datos en el periodo seleccionado.")
        return

    # =====================================================
    # GRÁFICO 1 · EVOLUCIÓN MENSUAL POR TIPO
    # =====================================================
    mensual = df.copy()
    mensual["mes"] = mensual["fecha"].dt.to_period("M").astype(str)

    graf_mes = (
        mensual.groupby(
            ["mes", "tipo_evolucion"]
        )
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )

    st.markdown("### Trabajos finalizados por mes")
    st.line_chart(
        graf_mes,
        use_container_width=True
    )

    # =====================================================
    # GRÁFICO 2 · OT POR ÁREA
    # =====================================================
    areas = (
        df.assign(
            area_limpia=df["area"]
            .fillna("Sin área")
            .astype(str)
            .replace("", "Sin área")
        )
        .groupby("area_limpia")
        .size()
        .sort_values(ascending=False)
        .head(12)
        .to_frame("OT finalizadas")
    )

    st.markdown("### OT finalizadas por área")
    st.bar_chart(
        areas,
        use_container_width=True,
        horizontal=True
    )

    # =====================================================
    # GRÁFICO 3 · TRABAJO POR OPERARIO
    # =====================================================
    operarios = (
        df.assign(
            operario_limpio=df["operario"]
            .fillna("Sin asignar")
            .astype(str)
            .replace("", "Sin asignar")
        )
        .groupby("operario_limpio")
        .size()
        .sort_values(ascending=False)
        .to_frame("Trabajos finalizados")
    )

    st.markdown("### Trabajos finalizados por operario")
    st.bar_chart(
        operarios,
        use_container_width=True,
        horizontal=True
    )

    # =====================================================
    # GRÁFICO 4 · TRABAJOS POR CENTRO
    # =====================================================
    centros = (
        df.assign(
            centro_limpio=df["centro"]
            .fillna("Sin centro")
            .astype(str)
            .replace("", "Sin centro")
        )
        .groupby("centro_limpio")
        .size()
        .sort_values(ascending=False)
        .to_frame("Trabajos finalizados")
    )

    st.markdown("### Trabajos finalizados por centro")
    st.bar_chart(
        centros,
        use_container_width=True
    )

    # =====================================================
    # GRÁFICO 5 · CONTROLES LEGIONELLA POR MES
    # Se alimenta del registro sanitario, no de la OT.
    # =====================================================
    df_leg = _leer_df("""
        SELECT fecha, centro, estado
        FROM legionella_registros
        WHERE fecha IS NOT NULL
        ORDER BY fecha
    """)

    if not df_leg.empty:
        df_leg["fecha"] = pd.to_datetime(
            df_leg["fecha"],
            errors="coerce"
        )

        df_leg = df_leg[df_leg["fecha"].notna()].copy()

        if not df_leg.empty:
            if st.session_state.get("evol_centro") not in [None, "Todos"]:
                df_leg = df_leg[
                    df_leg["centro"].astype(str)
                    == st.session_state.get("evol_centro")
                ]

            desde = st.session_state.get("evol_desde")
            hasta = st.session_state.get("evol_hasta")

            if desde:
                df_leg = df_leg[
                    df_leg["fecha"].dt.date >= desde
                ]

            if hasta:
                df_leg = df_leg[
                    df_leg["fecha"].dt.date <= hasta
                ]

            if not df_leg.empty:
                df_leg["mes"] = (
                    df_leg["fecha"]
                    .dt.to_period("M")
                    .astype(str)
                )

                leg_mes = (
                    df_leg.groupby("mes")
                    .size()
                    .sort_index()
                    .to_frame("Controles Legionella")
                )

                st.markdown("### Controles Legionella por mes")
                st.line_chart(
                    leg_mes,
                    use_container_width=True
                )
