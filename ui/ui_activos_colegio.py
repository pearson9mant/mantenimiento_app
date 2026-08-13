import streamlit as st
import pandas as pd

from database.db import conectar


def _leer_activos_colegio():
    """
    Censo global basado en inventario_aulas.

    No crea ni duplica datos.
    La tabla activos se usa únicamente para enriquecer cada registro
    con ficha técnica cuando exista.
    """
    conn = conectar()

    sql = """
        SELECT
            ia.id AS id_inventario,
            ia.fecha_revision,
            ia.centro,
            ia.edificio,
            ia.espacio,
            ia.elemento,
            COALESCE(ia.cantidad, 0) AS cantidad,
            COALESCE(ia.cantidad_afectada, 0) AS cantidad_afectada,
            COALESCE(ia.estado, '') AS estado,
            COALESCE(ia.operario, '') AS operario,
            COALESCE(ia.numero_ot_correctiva, '') AS numero_ot_correctiva,

            COALESCE(a.fabricante, '') AS fabricante,
            COALESCE(a.modelo, '') AS modelo,
            COALESCE(a.numero_serie, '') AS numero_serie,
            COALESCE(a.fecha_instalacion, '') AS fecha_instalacion,
            COALESCE(a.proveedor, '') AS proveedor,
            COALESCE(a.vida_util_anios, 0) AS vida_util_anios,
            COALESCE(a.coste_estimado, 0) AS coste_estimado,
            COALESCE(a.garantia_hasta, '') AS garantia_hasta

        FROM inventario_aulas ia

        LEFT JOIN activos a
            ON a.id = (
                SELECT MAX(a2.id)
                FROM activos a2
                WHERE a2.id_inventario = ia.id
            )

        ORDER BY
            ia.elemento ASC,
            ia.centro ASC,
            ia.edificio ASC,
            ia.espacio ASC
    """

    try:
        df = pd.read_sql_query(sql, conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


def _texto_limpio(serie, defecto=""):
    return (
        serie
        .fillna(defecto)
        .astype(str)
        .str.strip()
    )


def _preparar_datos(df):
    if df.empty:
        return df

    df = df.copy()

    for columna in [
        "centro",
        "edificio",
        "espacio",
        "elemento",
        "estado",
        "operario",
        "numero_ot_correctiva",
        "fabricante",
        "modelo",
        "numero_serie",
        "fecha_instalacion",
        "proveedor",
        "garantia_hasta",
    ]:
        if columna in df.columns:
            df[columna] = _texto_limpio(
                df[columna]
            )

    df["cantidad"] = pd.to_numeric(
        df["cantidad"],
        errors="coerce"
    ).fillna(0).astype(int)

    df["cantidad_afectada"] = pd.to_numeric(
        df["cantidad_afectada"],
        errors="coerce"
    ).fillna(0).astype(int)

    df["vida_util_anios"] = pd.to_numeric(
        df["vida_util_anios"],
        errors="coerce"
    ).fillna(0).astype(int)

    df["coste_estimado"] = pd.to_numeric(
        df["coste_estimado"],
        errors="coerce"
    ).fillna(0.0)

    df["tiene_ficha"] = (
        (df["fabricante"] != "")
        | (df["modelo"] != "")
        | (df["numero_serie"] != "")
        | (df["fecha_instalacion"] != "")
        | (df["vida_util_anios"] > 0)
        | (df["coste_estimado"] > 0)
    )

    return df


def _aplicar_filtros(df):
    filtrado = df.copy()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        centros = ["Todos"] + sorted(
            [
                x for x in filtrado["centro"].unique().tolist()
                if x
            ]
        )

        centro = st.selectbox(
            "Centro",
            centros,
            key="activos_global_centro"
        )

    if centro != "Todos":
        filtrado = filtrado[
            filtrado["centro"] == centro
        ]

    with c2:
        edificios = ["Todos"] + sorted(
            [
                x for x in filtrado["edificio"].unique().tolist()
                if x
            ]
        )

        edificio = st.selectbox(
            "Edificio",
            edificios,
            key="activos_global_edificio"
        )

    if edificio != "Todos":
        filtrado = filtrado[
            filtrado["edificio"] == edificio
        ]

    with c3:
        estados = ["Todos"] + sorted(
            [
                x for x in filtrado["estado"].unique().tolist()
                if x
            ]
        )

        estado = st.selectbox(
            "Estado",
            estados,
            key="activos_global_estado"
        )

    if estado != "Todos":
        filtrado = filtrado[
            filtrado["estado"] == estado
        ]

    with c4:
        buscar = st.text_input(
            "Buscar elemento",
            placeholder="Aire acondicionado, proyector...",
            key="activos_global_buscar"
        ).strip().lower()

    if buscar:
        filtrado = filtrado[
            filtrado["elemento"]
            .str.lower()
            .str.contains(
                buscar,
                regex=False,
                na=False
            )
        ]

    return filtrado


def _mostrar_metricas(df):
    total_unidades = int(
        df["cantidad"].sum()
    )

    tipos_elemento = int(
        df.loc[
            df["elemento"] != "",
            "elemento"
        ].nunique()
    )

    espacios = int(
        df[
            ["centro", "edificio", "espacio"]
        ]
        .drop_duplicates()
        .shape[0]
    )

    afectadas = int(
        df["cantidad_afectada"].sum()
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "📦 Unidades",
        total_unidades
    )

    m2.metric(
        "🧩 Tipos",
        tipos_elemento
    )

    m3.metric(
        "🏫 Espacios",
        espacios
    )

    m4.metric(
        "⚠️ Afectadas",
        afectadas
    )


def _resumen_elementos(df):
    resumen = (
        df[df["elemento"] != ""]
        .groupby("elemento", as_index=False)
        .agg(
            unidades=("cantidad", "sum"),
            espacios=("espacio", "nunique"),
            afectadas=("cantidad_afectada", "sum"),
            registros=("id_inventario", "count"),
            fichas=("tiene_ficha", "sum"),
        )
    )

    if resumen.empty:
        return resumen

    resumen = resumen.sort_values(
        by=[
            "unidades",
            "elemento",
        ],
        ascending=[
            False,
            True,
        ]
    )

    return resumen


def _mostrar_resumen(df):
    st.markdown("### 📊 Censo de elementos")

    resumen = _resumen_elementos(
        df
    )

    if resumen.empty:
        st.info(
            "No hay elementos con los filtros seleccionados."
        )
        return

    mostrar = resumen.rename(
        columns={
            "elemento": "Elemento",
            "unidades": "Unidades",
            "espacios": "Espacios",
            "afectadas": "Afectadas",
            "fichas": "Con ficha técnica",
        }
    )[
        [
            "Elemento",
            "Unidades",
            "Espacios",
            "Afectadas",
            "Con ficha técnica",
        ]
    ]

    st.dataframe(
        mostrar,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### 🔎 Ver dónde está cada elemento")

    opciones = resumen[
        "elemento"
    ].tolist()

    elemento_sel = st.selectbox(
        "Elemento",
        opciones,
        key="activos_global_elemento_detalle"
    )

    detalle = df[
        df["elemento"] == elemento_sel
    ].copy()

    total = int(
        detalle["cantidad"].sum()
    )

    afectados = int(
        detalle["cantidad_afectada"].sum()
    )

    st.info(
        f"**{elemento_sel}** · "
        f"{total} unidades · "
        f"{len(detalle)} ubicaciones registradas"
        + (
            f" · {afectados} afectadas"
            if afectados > 0
            else ""
        )
    )

    columnas = [
        "centro",
        "edificio",
        "espacio",
        "cantidad",
        "estado",
        "cantidad_afectada",
        "numero_ot_correctiva",
        "fabricante",
        "modelo",
        "numero_serie",
        "fecha_instalacion",
        "vida_util_anios",
    ]

    detalle_mostrar = detalle[
        columnas
    ].rename(
        columns={
            "centro": "Centro",
            "edificio": "Edificio",
            "espacio": "Espacio",
            "cantidad": "Cantidad",
            "estado": "Estado",
            "cantidad_afectada": "Afectadas",
            "numero_ot_correctiva": "OT correctiva",
            "fabricante": "Fabricante",
            "modelo": "Modelo",
            "numero_serie": "Nº serie",
            "fecha_instalacion": "Fecha instalación",
            "vida_util_anios": "Vida útil",
        }
    )

    st.dataframe(
        detalle_mostrar,
        use_container_width=True,
        hide_index=True
    )


def _mostrar_por_centro(df):
    st.markdown("### 🏢 Distribución por centro")

    agrupado = (
        df[df["elemento"] != ""]
        .groupby(
            [
                "elemento",
                "centro",
            ],
            as_index=False
        )
        .agg(
            unidades=("cantidad", "sum")
        )
    )

    if agrupado.empty:
        st.info(
            "No hay datos para mostrar."
        )
        return

    tabla = agrupado.pivot_table(
        index="elemento",
        columns="centro",
        values="unidades",
        aggfunc="sum",
        fill_value=0
    )

    tabla["Total"] = tabla.sum(
        axis=1
    )

    tabla = tabla.sort_values(
        "Total",
        ascending=False
    )

    st.dataframe(
        tabla,
        use_container_width=True
    )


def _mostrar_estado_activos(df):
    st.markdown("### 🚦 Estado de los elementos")

    estado = (
        df.assign(
            estado_limpio=df["estado"].replace(
                "",
                "Sin estado"
            )
        )
        .groupby(
            "estado_limpio"
        )["cantidad"]
        .sum()
        .sort_values(
            ascending=False
        )
        .to_frame(
            "Unidades"
        )
    )

    if estado.empty:
        st.info(
            "No hay estados registrados."
        )
        return

    st.bar_chart(
        estado,
        use_container_width=True
    )

    problemas = df[
        df["estado"].isin(
            [
                "Regular",
                "Dañado",
                "Falta",
                "Retirar",
            ]
        )
    ].copy()

    if problemas.empty:
        st.success(
            "No hay elementos registrados con estado problemático "
            "en los filtros actuales."
        )
        return

    st.markdown(
        "#### ⚠️ Elementos que requieren atención"
    )

    columnas = [
        "centro",
        "edificio",
        "espacio",
        "elemento",
        "cantidad",
        "cantidad_afectada",
        "estado",
        "numero_ot_correctiva",
    ]

    st.dataframe(
        problemas[
            columnas
        ].rename(
            columns={
                "centro": "Centro",
                "edificio": "Edificio",
                "espacio": "Espacio",
                "elemento": "Elemento",
                "cantidad": "Cantidad",
                "cantidad_afectada": "Afectadas",
                "estado": "Estado",
                "numero_ot_correctiva": "OT correctiva",
            }
        ),
        use_container_width=True,
        hide_index=True
    )


def pantalla_activos_colegio():
    st.subheader(
        "🏫 Activos del colegio"
    )

    st.caption(
        "Censo automático a partir del inventario de espacios. "
        "No duplica datos ni modifica el inventario."
    )

    df = _preparar_datos(
        _leer_activos_colegio()
    )

    if df.empty:
        st.info(
            "Todavía no hay elementos registrados en el "
            "inventario de espacios."
        )
        return

    df = _aplicar_filtros(
        df
    )

    if df.empty:
        st.info(
            "No hay resultados con los filtros seleccionados."
        )
        return

    _mostrar_metricas(
        df
    )

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(
        [
            "📊 Resumen",
            "🏢 Por centro",
            "🚦 Estado",
        ]
    )

    with tab1:
        _mostrar_resumen(
            df
        )

    with tab2:
        _mostrar_por_centro(
            df
        )

    with tab3:
        _mostrar_estado_activos(
            df
        )
