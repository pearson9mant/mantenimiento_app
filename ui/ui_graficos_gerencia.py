import pandas as pd
import streamlit as st

try:
    import altair as alt
except Exception:
    alt = None


# =========================================================
# UTILIDADES
# =========================================================

COLUMNAS_EVOLUCION = [
    "mes",
    "Preventivos realizados",
    "Incidencias creadas",
]


def _preparar_evolucion(evolucion):
    """
    Recibe el DataFrame mensual ya calculado por Gerencia y prepara
    únicamente los meses que tienen datos reales.

    No calcula OT, no consulta base de datos y no modifica criterios.
    """
    if evolucion is None or getattr(evolucion, "empty", True):
        return pd.DataFrame(columns=COLUMNAS_EVOLUCION)

    datos = evolucion.copy()

    for columna in COLUMNAS_EVOLUCION:
        if columna not in datos.columns:
            if columna == "mes":
                datos[columna] = ""
            else:
                datos[columna] = 0

    datos["Preventivos realizados"] = pd.to_numeric(
        datos["Preventivos realizados"],
        errors="coerce",
    ).fillna(0).astype(int)

    datos["Incidencias creadas"] = pd.to_numeric(
        datos["Incidencias creadas"],
        errors="coerce",
    ).fillna(0).astype(int)

    # Orden cronológico: se conserva el orden que ya trae Gerencia.
    datos["_orden"] = range(len(datos))

    con_datos = datos[
        (datos["Preventivos realizados"] > 0)
        | (datos["Incidencias creadas"] > 0)
    ].copy()

    return con_datos.sort_values("_orden").drop(columns=["_orden"])


def _ultimo_mes(datos):
    if datos.empty:
        return {
            "mes": "Sin datos",
            "Preventivos realizados": 0,
            "Incidencias creadas": 0,
        }

    fila = datos.iloc[-1]

    return {
        "mes": str(fila.get("mes") or "Sin datos"),
        "Preventivos realizados": int(
            fila.get("Preventivos realizados") or 0
        ),
        "Incidencias creadas": int(
            fila.get("Incidencias creadas") or 0
        ),
    }


def _datos_largos(datos):
    if datos.empty:
        return pd.DataFrame(
            columns=["mes", "Tipo", "Cantidad"]
        )

    largos = datos.melt(
        id_vars=["mes"],
        value_vars=[
            "Incidencias creadas",
            "Preventivos realizados",
        ],
        var_name="Tipo",
        value_name="Cantidad",
    )

    largos["Tipo"] = largos["Tipo"].replace({
        "Incidencias creadas": "Incidencias correctivas",
        "Preventivos realizados": "Preventivos realizados",
    })

    return largos


def _aviso_historico(datos):
    if len(datos) < 3:
        st.info(
            "Todavía estamos acumulando histórico. "
            "Cuando existan varios meses consecutivos podremos comparar "
            "la actividad preventiva con la evolución de las incidencias."
        )


# =========================================================
# MODELO A · BARRAS VERTICALES AGRUPADAS COMPACTAS
# =========================================================

def grafico_preventivo_incidencias_vertical(evolucion):
    """
    Dos barras verticales por mes.
    Barras estrechas, agrupadas y con valor visible.
    """
    datos = _preparar_evolucion(evolucion)

    st.markdown("#### A · Barras verticales agrupadas")

    if datos.empty:
        st.info("Todavía no hay datos para representar.")
        return

    if alt is None:
        st.bar_chart(
            datos.set_index("mes")[
                ["Incidencias creadas", "Preventivos realizados"]
            ],
            use_container_width=True,
            height=300,
        )
        return

    largos = _datos_largos(datos)
    orden_meses = datos["mes"].tolist()

    barras = (
        alt.Chart(largos)
        .mark_bar(size=28)
        .encode(
            x=alt.X(
                "mes:N",
                sort=orden_meses,
                title=None,
                axis=alt.Axis(labelAngle=0),
            ),
            xOffset=alt.XOffset("Tipo:N"),
            y=alt.Y(
                "Cantidad:Q",
                title="Actuaciones",
                scale=alt.Scale(zero=True),
            ),
            color=alt.Color(
                "Tipo:N",
                title=None,
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("mes:N", title="Mes"),
                alt.Tooltip("Tipo:N", title="Tipo"),
                alt.Tooltip("Cantidad:Q", title="Cantidad"),
            ],
        )
    )

    etiquetas = (
        alt.Chart(largos)
        .mark_text(dy=-8, fontSize=12, fontWeight="bold")
        .encode(
            x=alt.X("mes:N", sort=orden_meses),
            xOffset=alt.XOffset("Tipo:N"),
            y=alt.Y("Cantidad:Q"),
            text=alt.Text("Cantidad:Q"),
        )
    )

    st.altair_chart(
        (barras + etiquetas).properties(height=280),
        use_container_width=True,
    )

    _aviso_historico(datos)


# =========================================================
# MODELO B · BARRAS HORIZONTALES POR MES
# =========================================================

def grafico_preventivo_incidencias_horizontal(evolucion):
    """
    Muy legible cuando hay pocos meses.
    """
    datos = _preparar_evolucion(evolucion)

    st.markdown("#### B · Barras horizontales comparativas")

    if datos.empty:
        st.info("Todavía no hay datos para representar.")
        return

    largos = _datos_largos(datos)

    if alt is None:
        ultimo = _ultimo_mes(datos)

        comparativa = pd.DataFrame(
            {
                "Cantidad": [
                    ultimo["Incidencias creadas"],
                    ultimo["Preventivos realizados"],
                ]
            },
            index=[
                "Incidencias correctivas",
                "Preventivos realizados",
            ],
        )

        st.bar_chart(
            comparativa,
            horizontal=True,
            use_container_width=True,
            height=220,
        )
        return

    orden_meses = datos["mes"].tolist()

    grafico = (
        alt.Chart(largos)
        .mark_bar(size=20)
        .encode(
            y=alt.Y(
                "Tipo:N",
                title=None,
                sort=[
                    "Incidencias correctivas",
                    "Preventivos realizados",
                ],
            ),
            x=alt.X(
                "Cantidad:Q",
                title="Actuaciones",
                scale=alt.Scale(zero=True),
            ),
            row=alt.Row(
                "mes:N",
                sort=orden_meses,
                title=None,
                header=alt.Header(
                    labelAngle=0,
                    labelFontWeight="bold",
                ),
            ),
            color=alt.Color(
                "Tipo:N",
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("mes:N", title="Mes"),
                alt.Tooltip("Tipo:N", title="Tipo"),
                alt.Tooltip("Cantidad:Q", title="Cantidad"),
            ],
        )
        .properties(height=85)
    )

    st.altair_chart(
        grafico,
        use_container_width=True,
    )

    _aviso_historico(datos)


# =========================================================
# MODELO C · TARJETAS + MINI COMPARATIVA
# =========================================================

def grafico_preventivo_incidencias_compacto(evolucion):
    """
    Pensado para Gerencia: lectura inmediata y poco espacio vertical.
    """
    datos = _preparar_evolucion(evolucion)

    st.markdown("#### C · Resumen compacto")

    if datos.empty:
        st.info("Todavía no hay datos para representar.")
        return

    ultimo = _ultimo_mes(datos)

    c1, c2, c3 = st.columns([1, 1, 1.25])

    with c1:
        st.metric(
            "Incidencias correctivas",
            ultimo["Incidencias creadas"],
        )

    with c2:
        st.metric(
            "Preventivos realizados",
            ultimo["Preventivos realizados"],
        )

    diferencia = (
        ultimo["Preventivos realizados"]
        - ultimo["Incidencias creadas"]
    )

    with c3:
        st.metric(
            f"Balance · {ultimo['mes']}",
            diferencia,
            help=(
                "Diferencia simple entre preventivos realizados "
                "e incidencias correctivas del mes. "
                "No representa todavía eficacia preventiva."
            ),
        )

    if alt is not None:
        largos = _datos_largos(
            datos.tail(6)
        )

        orden_meses = datos.tail(6)["mes"].tolist()

        mini = (
            alt.Chart(largos)
            .mark_bar(size=18)
            .encode(
                x=alt.X(
                    "mes:N",
                    sort=orden_meses,
                    title=None,
                    axis=alt.Axis(labelAngle=0),
                ),
                xOffset=alt.XOffset("Tipo:N"),
                y=alt.Y(
                    "Cantidad:Q",
                    title=None,
                    axis=alt.Axis(labels=False, ticks=False),
                ),
                color=alt.Color(
                    "Tipo:N",
                    title=None,
                    legend=alt.Legend(orient="bottom"),
                ),
                tooltip=[
                    "mes:N",
                    "Tipo:N",
                    "Cantidad:Q",
                ],
            )
            .properties(height=150)
        )

        st.altair_chart(
            mini,
            use_container_width=True,
        )

    _aviso_historico(datos)


# =========================================================
# MODELO D · DIFERENCIA MENSUAL
# =========================================================

def grafico_balance_mensual(evolucion):
    """
    No pretende medir eficacia.
    Solo muestra, mes a mes, cuánta actividad preventiva hubo frente
    a las incidencias creadas.
    """
    datos = _preparar_evolucion(evolucion)

    st.markdown("#### D · Balance mensual")

    if datos.empty:
        st.info("Todavía no hay datos para representar.")
        return

    balance = datos.copy()
    balance["Balance"] = (
        balance["Preventivos realizados"]
        - balance["Incidencias creadas"]
    )

    if alt is None:
        st.bar_chart(
            balance.set_index("mes")[["Balance"]],
            use_container_width=True,
            height=250,
        )
        return

    orden_meses = balance["mes"].tolist()

    base = (
        alt.Chart(balance)
        .mark_bar(size=32)
        .encode(
            x=alt.X(
                "mes:N",
                sort=orden_meses,
                title=None,
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "Balance:Q",
                title="Preventivos − incidencias",
            ),
            tooltip=[
                alt.Tooltip("mes:N", title="Mes"),
                alt.Tooltip(
                    "Preventivos realizados:Q",
                    title="Preventivos",
                ),
                alt.Tooltip(
                    "Incidencias creadas:Q",
                    title="Incidencias",
                ),
                alt.Tooltip("Balance:Q", title="Balance"),
            ],
        )
    )

    cero = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(strokeDash=[4, 4])
        .encode(y="y:Q")
    )

    st.altair_chart(
        (base + cero).properties(height=240),
        use_container_width=True,
    )

    st.caption(
        "Este balance no indica todavía eficacia preventiva. "
        "Sirve únicamente para comparar el volumen mensual de actividad."
    )


# =========================================================
# LABORATORIO
# =========================================================

def pantalla_laboratorio_preventivo_incidencias(
    evolucion,
    titulo="🧪 Laboratorio · Preventivo e incidencias",
):
    """
    Muestra cuatro propuestas con exactamente los mismos datos.
    No modifica Gerencia ni realiza consultas.
    """
    st.markdown(f"## {titulo}")

    datos = _preparar_evolucion(evolucion)
    ultimo = _ultimo_mes(datos)

    st.caption(
        f"Datos actuales · {ultimo['mes']} · "
        f"{ultimo['Incidencias creadas']} incidencias correctivas · "
        f"{ultimo['Preventivos realizados']} preventivos realizados"
    )

    tab_a, tab_b, tab_c, tab_d = st.tabs([
        "A · Vertical",
        "B · Horizontal",
        "C · Compacto",
        "D · Balance",
    ])

    with tab_a:
        grafico_preventivo_incidencias_vertical(
            evolucion
        )

    with tab_b:
        grafico_preventivo_incidencias_horizontal(
            evolucion
        )

    with tab_c:
        grafico_preventivo_incidencias_compacto(
            evolucion
        )

    with tab_d:
        grafico_balance_mensual(
            evolucion
        )


# =========================================================
# DEMO CON LOS DATOS ACTUALES
# =========================================================

def datos_demo_actuales():
    """
    Demo visual con los datos que ahora mismo estamos viendo en Gerencia:
    6 incidencias correctivas y 7 preventivos realizados.
    """
    return pd.DataFrame([
        {
            "periodo": "2026-08",
            "mes": "Ago 26",
            "Preventivos realizados": 7,
            "Incidencias creadas": 6,
        }
    ])


def pantalla_demo_graficos_gerencia():
    """
    Permite probar el laboratorio sin depender de la base de datos.
    """
    pantalla_laboratorio_preventivo_incidencias(
        datos_demo_actuales(),
        titulo="🧪 Laboratorio de gráficos · Datos actuales",
    )
