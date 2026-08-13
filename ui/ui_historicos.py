import streamlit as st
import pandas as pd
from datetime import date

from database.db import conectar


def _leer_df(sql, params=None):
    conn = conectar()

    try:
        if params:
            return pd.read_sql_query(sql, conn, params=params)
        return pd.read_sql_query(sql, conn)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def _fecha_segura(serie):
    return pd.to_datetime(serie, errors="coerce")


def _filtros_comunes(df, prefijo, columna_fecha="fecha_cierre"):
    if df.empty:
        return df

    filtrado = df.copy()

    if columna_fecha in filtrado.columns:
        filtrado["_fecha_filtro"] = _fecha_segura(
            filtrado[columna_fecha]
        )

        fechas_validas = filtrado["_fecha_filtro"].dropna()

        if not fechas_validas.empty:
            fecha_min = fechas_validas.min().date()
            fecha_max = fechas_validas.max().date()
        else:
            fecha_min = date.today()
            fecha_max = date.today()
    else:
        fecha_min = date.today()
        fecha_max = date.today()

    c1, c2, c3 = st.columns(3)

    with c1:
        desde = st.date_input(
            "Desde",
            value=fecha_min,
            key=f"{prefijo}_desde"
        )

    with c2:
        hasta = st.date_input(
            "Hasta",
            value=fecha_max,
            key=f"{prefijo}_hasta"
        )

    with c3:
        centros = ["Todos"]

        if "centro" in filtrado.columns:
            centros += sorted(
                filtrado["centro"]
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
            key=f"{prefijo}_centro"
        )

    if columna_fecha in filtrado.columns:
        filtrado = filtrado[
            filtrado["_fecha_filtro"].notna()
            & (filtrado["_fecha_filtro"].dt.date >= desde)
            & (filtrado["_fecha_filtro"].dt.date <= hasta)
        ]

    if centro != "Todos" and "centro" in filtrado.columns:
        filtrado = filtrado[
            filtrado["centro"].astype(str) == centro
        ]

    return filtrado


def _historico_ot():
    st.markdown("### 🛠️ Histórico de OT")

    df = _leer_df("""
        SELECT
            id,
            numero_ot,
            descripcion,
            fecha_creacion,
            fecha_cierre,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            observaciones_cierre
        FROM historico_ordenes
        ORDER BY fecha_cierre DESC, id DESC
    """)

    if df.empty:
        st.info("No hay órdenes finalizadas en el histórico.")
        return

    df = _filtros_comunes(
        df,
        prefijo="hist_ot",
        columna_fecha="fecha_cierre"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        operarios = ["Todos"] + sorted(
            df["operario"]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda s: s != ""]
            .unique()
            .tolist()
        )

        operario = st.selectbox(
            "Operario",
            operarios,
            key="hist_ot_operario"
        )

    with c2:
        areas = ["Todas"] + sorted(
            df["area"]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda s: s != ""]
            .unique()
            .tolist()
        )

        area = st.selectbox(
            "Área",
            areas,
            key="hist_ot_area"
        )

    with c3:
        buscar = st.text_input(
            "Buscar",
            placeholder="OT, tarea, espacio, descripción...",
            key="hist_ot_buscar"
        ).strip().lower()

    if operario != "Todos":
        df = df[df["operario"].astype(str) == operario]

    if area != "Todas":
        df = df[df["area"].astype(str) == area]

    if buscar:
        texto = (
            df["numero_ot"].fillna("").astype(str) + " "
            + df["descripcion"].fillna("").astype(str) + " "
            + df["espacio"].fillna("").astype(str) + " "
            + df["edificio"].fillna("").astype(str) + " "
            + df["origen"].fillna("").astype(str)
        ).str.lower()

        df = df[texto.str.contains(buscar, regex=False)]

    st.caption(f"Resultados: {len(df)}")

    if df.empty:
        st.info("No hay resultados con estos filtros.")
        return

    mostrar = df[
        [
            "fecha_cierre",
            "numero_ot",
            "centro",
            "edificio",
            "espacio",
            "area",
            "operario",
            "origen",
            "descripcion",
        ]
    ].copy()

    st.dataframe(
        mostrar,
        use_container_width=True,
        hide_index=True
    )


def _historico_legionella():
    st.markdown("### 💧 Histórico de Legionella")

    df = _leer_df("""
        SELECT
            id,
            fecha,
            centro,
            edificio,
            instalacion,
            punto,
            tarea,
            tipo_control,
            valor,
            valor_2,
            valor_3,
            unidad,
            estado,
            resultado,
            operario,
            observaciones
        FROM legionella_registros
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY fecha DESC, id DESC
    """)

    if df.empty:
        st.info("No hay controles de Legionella registrados.")
        return

    df = _filtros_comunes(
        df,
        prefijo="hist_leg",
        columna_fecha="fecha"
    )

    c1, c2 = st.columns(2)

    with c1:
        estados = ["Todos"] + sorted(
            df["estado"]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda s: s != ""]
            .unique()
            .tolist()
        )

        estado = st.selectbox(
            "Estado",
            estados,
            key="hist_leg_estado"
        )

    with c2:
        buscar = st.text_input(
            "Buscar punto o control",
            key="hist_leg_buscar"
        ).strip().lower()

    if estado != "Todos":
        df = df[df["estado"].astype(str) == estado]

    if buscar:
        texto = (
            df["punto"].fillna("").astype(str) + " "
            + df["tarea"].fillna("").astype(str) + " "
            + df["edificio"].fillna("").astype(str) + " "
            + df["resultado"].fillna("").astype(str)
        ).str.lower()

        df = df[texto.str.contains(buscar, regex=False)]

    st.caption(f"Controles encontrados: {len(df)}")

    st.dataframe(
        df[
            [
                "fecha",
                "centro",
                "edificio",
                "punto",
                "tarea",
                "valor",
                "valor_2",
                "valor_3",
                "unidad",
                "estado",
                "resultado",
                "operario",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


def _historico_preventivos():
    st.markdown("### 🔧 Histórico de Preventivos")

    df = _leer_df("""
        SELECT
            h.id,
            h.numero_ot,
            h.descripcion,
            h.fecha_creacion,
            h.fecha_cierre,
            h.centro,
            h.edificio,
            COALESCE(pr.planta, '') AS planta,
            h.espacio,
            h.area,
            h.operario,
            h.observaciones_cierre,
            COALESCE(pr.tarea, '') AS tarea,
            COALESCE(pr.frecuencia, '') AS frecuencia
        FROM historico_ordenes h
        LEFT JOIN preventivo_registros pr
            ON pr.numero_ot = h.numero_ot
        WHERE UPPER(COALESCE(h.origen, '')) = 'PREVENTIVO'
           OR UPPER(COALESCE(h.descripcion, '')) LIKE '[PREVENTIVO]%'
        ORDER BY h.fecha_cierre DESC, h.id DESC
    """)

    if df.empty:
        st.info("No hay preventivos finalizados.")
        return

    df = _filtros_comunes(
        df,
        prefijo="hist_prev",
        columna_fecha="fecha_cierre"
    )

    buscar = st.text_input(
        "Buscar preventivo",
        placeholder="Tarea, OT, planta o espacio...",
        key="hist_prev_buscar_global"
    ).strip().lower()

    if buscar:
        texto = (
            df["numero_ot"].fillna("").astype(str) + " "
            + df["tarea"].fillna("").astype(str) + " "
            + df["descripcion"].fillna("").astype(str) + " "
            + df["planta"].fillna("").astype(str) + " "
            + df["espacio"].fillna("").astype(str)
        ).str.lower()

        df = df[texto.str.contains(buscar, regex=False)]

    st.caption(f"Preventivos encontrados: {len(df)}")

    st.dataframe(
        df[
            [
                "fecha_cierre",
                "numero_ot",
                "centro",
                "edificio",
                "planta",
                "espacio",
                "area",
                "tarea",
                "frecuencia",
                "operario",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


def _historico_informes_externos():
    st.markdown("### 📁 Informes externos de Legionella")

    df = _leer_df("""
        SELECT
            id,
            tipo_informe,
            empresa,
            centro,
            edificio,
            instalacion,
            punto,
            fecha_actuacion,
            fecha_informe,
            resultado,
            numero_informe,
            proxima_fecha,
            observaciones,
            pdf_nombre
        FROM legionella_informes
        ORDER BY fecha_actuacion DESC, id DESC
    """)

    if df.empty:
        st.info("No hay informes externos registrados.")
        return

    df = _filtros_comunes(
        df,
        prefijo="hist_inf_leg",
        columna_fecha="fecha_actuacion"
    )

    st.caption(f"Informes encontrados: {len(df)}")

    st.dataframe(
        df[
            [
                "fecha_actuacion",
                "tipo_informe",
                "empresa",
                "centro",
                "edificio",
                "instalacion",
                "punto",
                "resultado",
                "numero_informe",
                "proxima_fecha",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


def pantalla_historicos():
    st.subheader("📚 Históricos")

    st.caption(
        "Archivo central de mantenimiento. "
        "Consulta por fechas sin entrar en cada módulo."
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🛠️ OT",
            "💧 Legionella",
            "🔧 Preventivos",
            "📁 Informes externos",
        ]
    )

    with tab1:
        _historico_ot()

    with tab2:
        _historico_legionella()

    with tab3:
        _historico_preventivos()

    with tab4:
        _historico_informes_externos()
