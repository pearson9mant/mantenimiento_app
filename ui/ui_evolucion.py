import streamlit as st
import pandas as pd
from datetime import date, timedelta

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



def _correctivas(df):
    if df.empty:
        return df

    return df[
        df["tipo_evolucion"].isin(
            [
                "Incidencias / correctivas",
                "OT correctivas",
            ]
        )
    ].copy()


def _preventivas(df):
    if df.empty:
        return df

    return df[
        df["tipo_evolucion"] == "Preventivas"
    ].copy()


def _dividir_periodo_comparable(df):
    """
    Divide el periodo seleccionado en dos mitades iguales:
    - periodo anterior
    - periodo reciente

    Así la lectura siempre compara tiempos equivalentes y respeta
    los filtros Desde / Hasta seleccionados por el usuario.
    """
    if df.empty:
        return df.copy(), df.copy(), None

    desde = st.session_state.get("evol_desde")
    hasta = st.session_state.get("evol_hasta")

    if not desde or not hasta:
        fechas = df["fecha"].dropna()

        if fechas.empty:
            return df.copy(), df.copy(), None

        desde = fechas.min().date()
        hasta = fechas.max().date()

    if hasta < desde:
        desde, hasta = hasta, desde

    dias_totales = (hasta - desde).days + 1

    if dias_totales < 2:
        return df.iloc[0:0].copy(), df.copy(), {
            "desde_anterior": desde,
            "hasta_anterior": desde,
            "desde_reciente": desde,
            "hasta_reciente": hasta,
        }

    dias_anterior = dias_totales // 2
    corte = desde + timedelta(days=dias_anterior)

    anterior = df[
        (df["fecha"].dt.date >= desde)
        & (df["fecha"].dt.date < corte)
    ].copy()

    reciente = df[
        (df["fecha"].dt.date >= corte)
        & (df["fecha"].dt.date <= hasta)
    ].copy()

    meta = {
        "desde_anterior": desde,
        "hasta_anterior": corte - timedelta(days=1),
        "desde_reciente": corte,
        "hasta_reciente": hasta,
    }

    return anterior, reciente, meta


def _variacion_porcentaje(actual, anterior):
    if anterior == 0:
        return None

    return ((actual - anterior) / anterior) * 100.0


def _texto_variacion(actual, anterior):
    variacion = _variacion_porcentaje(
        actual,
        anterior
    )

    if variacion is None:
        if actual == 0:
            return "sin actividad en ninguno de los dos periodos"

        return (
            f"{actual} en el periodo reciente "
            "sin registros comparables en el periodo anterior"
        )

    signo = "+" if variacion > 0 else ""

    return (
        f"{actual} frente a {anterior} "
        f"({signo}{variacion:.0f}%)"
    )


def _mostrar_lectura_evolucion(df):
    """
    Interpreta tendencias con reglas matemáticas simples y explicables.
    No usa IA externa ni modifica ningún dato.
    """
    anterior, reciente, meta = _dividir_periodo_comparable(
        df
    )

    if meta is None:
        return

    st.markdown("### 🧠 Lectura de la evolución")

    st.caption(
        "Comparación automática entre dos periodos equivalentes: "
        f"{meta['desde_anterior'].strftime('%d/%m/%Y')}–"
        f"{meta['hasta_anterior'].strftime('%d/%m/%Y')} frente a "
        f"{meta['desde_reciente'].strftime('%d/%m/%Y')}–"
        f"{meta['hasta_reciente'].strftime('%d/%m/%Y')}."
    )

    corr_ant = _correctivas(anterior)
    corr_rec = _correctivas(reciente)

    prev_ant = _preventivas(anterior)
    prev_rec = _preventivas(reciente)

    n_corr_ant = len(corr_ant)
    n_corr_rec = len(corr_rec)
    n_prev_ant = len(prev_ant)
    n_prev_rec = len(prev_rec)

    variacion_corr = _variacion_porcentaje(
        n_corr_rec,
        n_corr_ant
    )

    if variacion_corr is None:
        if n_corr_ant == 0 and n_corr_rec == 0:
            st.success(
                "🟢 **Correctivas:** no hay correctivas en ninguno "
                "de los dos periodos comparados."
            )
        else:
            st.info(
                "🔵 **Correctivas:** "
                + _texto_variacion(
                    n_corr_rec,
                    n_corr_ant
                )
                + "."
            )

    elif variacion_corr <= -10:
        st.success(
            "🟢 **Las correctivas disminuyen:** "
            + _texto_variacion(
                n_corr_rec,
                n_corr_ant
            )
            + ". La evolución operativa es favorable."
        )

    elif variacion_corr >= 10:
        st.warning(
            "🟠 **Las correctivas aumentan:** "
            + _texto_variacion(
                n_corr_rec,
                n_corr_ant
            )
            + ". Conviene revisar dónde se concentra el incremento."
        )

    else:
        st.info(
            "🔵 **Correctivas estables:** "
            + _texto_variacion(
                n_corr_rec,
                n_corr_ant
            )
            + "."
        )

    variacion_prev = _variacion_porcentaje(
        n_prev_rec,
        n_prev_ant
    )

    if variacion_prev is None:
        st.info(
            "🔧 **Preventivas:** "
            + _texto_variacion(
                n_prev_rec,
                n_prev_ant
            )
            + "."
        )
    elif variacion_prev >= 10:
        st.success(
            "🟢 **Actividad preventiva al alza:** "
            + _texto_variacion(
                n_prev_rec,
                n_prev_ant
            )
            + "."
        )
    elif variacion_prev <= -10:
        st.warning(
            "🟠 **Actividad preventiva a la baja:** "
            + _texto_variacion(
                n_prev_rec,
                n_prev_ant
            )
            + ". Conviene comprobar si responde a planificación "
            "o a preventivos pendientes."
        )
    else:
        st.info(
            "🔵 **Preventivas estables:** "
            + _texto_variacion(
                n_prev_rec,
                n_prev_ant
            )
            + "."
        )

    # Relación preventivo / correctivo.
    if n_corr_rec > 0:
        ratio_rec = n_prev_rec / n_corr_rec
        st.info(
            f"⚖️ **Relación preventivo/correctivo:** "
            f"{ratio_rec:.2f} preventivas por cada correctiva "
            "en el periodo reciente."
        )
    elif n_prev_rec > 0:
        st.success(
            "⚖️ **Relación preventivo/correctivo:** hay actividad "
            "preventiva y ninguna correctiva en el periodo reciente."
        )

    # Reincidencias: mismo centro + edificio + espacio + área.
    if not corr_rec.empty:
        agrupacion = (
            corr_rec.assign(
                centro_r=corr_rec["centro"].fillna("").astype(str),
                edificio_r=corr_rec["edificio"].fillna("").astype(str),
                espacio_r=corr_rec["espacio"].fillna("").astype(str),
                area_r=corr_rec["area"].fillna("").astype(str),
            )
            .groupby(
                [
                    "centro_r",
                    "edificio_r",
                    "espacio_r",
                    "area_r",
                ],
                dropna=False,
            )
            .size()
            .sort_values(ascending=False)
        )

        reincidentes = agrupacion[
            agrupacion >= 2
        ]

        if not reincidentes.empty:
            clave = reincidentes.index[0]
            repeticiones = int(
                reincidentes.iloc[0]
            )

            centro_r, edificio_r, espacio_r, area_r = clave

            st.warning(
                "🔁 **Reincidencia detectada:** "
                f"{centro_r or '-'} · {edificio_r or '-'} · "
                f"{espacio_r or '-'} · {area_r or '-'} "
                f"acumula {repeticiones} correctivas en el periodo reciente."
            )

    # Área que más empeora en correctivas.
    if not corr_rec.empty:
        areas_ant = (
            corr_ant.assign(
                area_limpia=corr_ant["area"]
                .fillna("Sin área")
                .astype(str)
                .replace("", "Sin área")
            )
            .groupby("area_limpia")
            .size()
        )

        areas_rec = (
            corr_rec.assign(
                area_limpia=corr_rec["area"]
                .fillna("Sin área")
                .astype(str)
                .replace("", "Sin área")
            )
            .groupby("area_limpia")
            .size()
        )

        todas_areas = sorted(
            set(areas_ant.index)
            | set(areas_rec.index)
        )

        cambios = []

        for area in todas_areas:
            ant = int(
                areas_ant.get(area, 0)
            )
            rec = int(
                areas_rec.get(area, 0)
            )

            cambios.append(
                (
                    rec - ant,
                    rec,
                    ant,
                    area,
                )
            )

        cambios.sort(reverse=True)

        if cambios and cambios[0][0] > 0:
            incremento, rec, ant, area = cambios[0]

            st.warning(
                f"📍 **Área a vigilar:** {area} es la que más aumenta "
                f"en correctivas ({rec} frente a {ant}, "
                f"+{incremento})."
            )

            _mostrar_detalle_area_correctivas(
                reciente,
                area_objetivo=area,
                titulo="OT que explican el aumento"
            )


def _mostrar_detalle_area_correctivas(df, area_objetivo, titulo="Detalle"):
    """
    Muestra las OT correctivas que justifican una alerta de área.
    No hace nuevas consultas: reutiliza el dataframe ya filtrado.
    """
    if df.empty or not area_objetivo:
        return

    corr = _correctivas(df)

    if corr.empty:
        return

    detalle = corr[
        corr["area"]
        .fillna("Sin área")
        .astype(str)
        .replace("", "Sin área")
        == str(area_objetivo)
    ].copy()

    if detalle.empty:
        return

    with st.expander(
        f"🔎 Ver OT de {area_objetivo} ({len(detalle)})",
        expanded=False
    ):
        columnas = [
            "fecha",
            "numero_ot",
            "centro",
            "edificio",
            "espacio",
            "area",
            "prioridad",
            "operario",
            "origen",
            "descripcion",
        ]

        disponibles = [
            c for c in columnas
            if c in detalle.columns
        ]

        mostrar = detalle[
            disponibles
        ].copy()

        if "fecha" in mostrar.columns:
            mostrar["fecha"] = (
                pd.to_datetime(
                    mostrar["fecha"],
                    errors="coerce"
                )
                .dt.strftime("%d/%m/%Y")
            )

        st.dataframe(
            mostrar.sort_values(
                by="fecha",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )


def _mostrar_espacios_mas_afectados(df):
    """
    Identifica los espacios con más correctivas dentro del periodo filtrado
    y permite desplegar las OT que justifican el dato.
    """
    corr = _correctivas(df)

    if corr.empty:
        return

    corr = corr.copy()

    corr["centro_limpio"] = (
        corr["centro"]
        .fillna("Sin centro")
        .astype(str)
        .replace("", "Sin centro")
    )

    corr["edificio_limpio"] = (
        corr["edificio"]
        .fillna("Sin edificio")
        .astype(str)
        .replace("", "Sin edificio")
    )

    corr["espacio_limpio"] = (
        corr["espacio"]
        .fillna("Sin espacio")
        .astype(str)
        .replace("", "Sin espacio")
    )

    corr["clave_espacio"] = (
        corr["centro_limpio"]
        + " · "
        + corr["edificio_limpio"]
        + " · "
        + corr["espacio_limpio"]
    )

    ranking = (
        corr.groupby("clave_espacio")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .to_frame("Correctivas")
    )

    if ranking.empty:
        return

    st.markdown("### 🏫 Espacios más afectados")

    st.bar_chart(
        ranking,
        use_container_width=True,
        horizontal=True
    )

    top_espacios = ranking.index.tolist()

    for posicion, clave in enumerate(top_espacios, start=1):
        total = int(ranking.loc[clave, "Correctivas"])

        with st.expander(
            f"{posicion}. {clave} · {total} "
            f"{'correctiva' if total == 1 else 'correctivas'}",
            expanded=False
        ):
            detalle = corr[
                corr["clave_espacio"] == clave
            ].copy()

            columnas = [
                "fecha",
                "numero_ot",
                "area",
                "prioridad",
                "operario",
                "origen",
                "descripcion",
            ]

            disponibles = [
                c for c in columnas
                if c in detalle.columns
            ]

            mostrar = detalle[
                disponibles
            ].copy()

            if "fecha" in mostrar.columns:
                mostrar["fecha"] = (
                    pd.to_datetime(
                        mostrar["fecha"],
                        errors="coerce"
                    )
                    .dt.strftime("%d/%m/%Y")
                )

            st.dataframe(
                mostrar,
                use_container_width=True,
                hide_index=True
            )

def pantalla_evolucion():
    st.subheader("📈 Evolución")

    st.caption(
        "Gráficos e interpretación automática de tendencias "
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

    _mostrar_lectura_evolucion(
        df
    )

    st.markdown("---")

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
    # GRÁFICO 1B · PREVENTIVAS VS CORRECTIVAS
    # =====================================================
    comparativa = mensual[
        mensual["tipo_evolucion"].isin(
            [
                "Preventivas",
                "Incidencias / correctivas",
                "OT correctivas",
            ]
        )
    ].copy()

    if not comparativa.empty:
        comparativa["familia"] = comparativa[
            "tipo_evolucion"
        ].replace(
            {
                "Incidencias / correctivas": "Correctivas",
                "OT correctivas": "Correctivas",
                "Preventivas": "Preventivas",
            }
        )

        prev_corr_mes = (
            comparativa.groupby(
                ["mes", "familia"]
            )
            .size()
            .unstack(fill_value=0)
            .sort_index()
        )

        st.markdown(
            "### Preventivas frente a correctivas"
        )

        st.line_chart(
            prev_corr_mes,
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
    # ESPACIOS MÁS AFECTADOS
    # =====================================================
    _mostrar_espacios_mas_afectados(
        df
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
