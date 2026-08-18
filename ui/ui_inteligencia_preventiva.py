import streamlit as st

from modules.inteligencia_preventiva import (
    analizar_inteligencia_preventiva,
)


def _mostrar_recomendacion(
    recomendacion,
    indice,
):
    nivel = recomendacion.get(
        "nivel",
        "Observación",
    )

    score = recomendacion.get(
        "score",
        0,
    )

    edificio = recomendacion.get(
        "edificio",
        "-",
    )

    planta = recomendacion.get(
        "planta",
        "",
    )

    espacio = recomendacion.get(
        "espacio",
        "-",
    )

    area = recomendacion.get(
        "area",
        "-",
    )

    cantidad = recomendacion.get(
        "cantidad",
        0,
    )

    abiertas = recomendacion.get(
        "abiertas",
        0,
    )

    accion = recomendacion.get(
        "accion",
        "",
    )

    motivo = recomendacion.get(
        "motivo",
        "",
    )

    frecuencia_actual = (
        recomendacion.get(
            "frecuencia_actual",
            "",
        )
    )

    frecuencia_sugerida = (
        recomendacion.get(
            "frecuencia_sugerida",
            "",
        )
    )

    intervalo = recomendacion.get(
        "intervalo_medio"
    )

    ultima_fecha = recomendacion.get(
        "ultima_fecha",
        "",
    )

    descripcion = recomendacion.get(
        "descripcion",
        "",
    )

    patron_detectado = recomendacion.get(
        "patron_detectado",
        "",
    )

    repeticiones_patron = recomendacion.get(
        "repeticiones_patron",
        0,
    )

    confianza_patron = recomendacion.get(
        "confianza_patron",
        "",
    )

    porcentaje_patron = recomendacion.get(
        "porcentaje_patron",
        0,
    )

    if nivel == "Alta":
        icono = "🔴"

    elif nivel == "Media":
        icono = "🟠"

    else:
        icono = "🟡"

    with st.container(border=True):

        c1, c2 = st.columns(
            [5, 1]
        )

        with c1:

            st.markdown(
                f"### {icono} "
                f"{espacio} · {area}"
            )

            ubicacion = edificio

            if planta:
                ubicacion += (
                    f" · {planta}"
                )

            st.caption(
                ubicacion
            )

        with c2:

            st.metric(
                "Índice",
                score,
            )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Incidencias",
            cantidad,
        )

        c2.metric(
            "Abiertas ahora",
            abiertas,
        )

        c3.metric(
            "Última",
            ultima_fecha or "-",
        )

        # ==================================================
        # PATRÓN TÉCNICO
        # ==================================================

        if patron_detectado:

            st.markdown(
                f"**🔎 Patrón detectado:** "
                f"{patron_detectado}"
            )

            detalle_patron = (
                f"{repeticiones_patron} de "
                f"{cantidad} incidencias"
            )

            if porcentaje_patron:
                detalle_patron += (
                    f" · {porcentaje_patron}%"
                )

            if confianza_patron:
                detalle_patron += (
                    f" · Confianza: "
                    f"{confianza_patron}"
                )

            st.caption(
                detalle_patron
            )

        else:

            st.caption(
                "🔎 No se ha confirmado todavía "
                "un patrón técnico repetido."
            )

        # ==================================================
        # RECOMENDACIÓN
        # ==================================================

        st.markdown(
            f"**🧠 Recomendación:** "
            f"{accion}"
        )

        st.info(
            motivo
        )

        # ==================================================
        # INTERVALO
        # ==================================================

        if intervalo is not None:

            st.caption(
                f"Intervalo medio observado "
                f"entre incidencias: "
                f"{intervalo} días."
            )

        # ==================================================
        # PREVENTIVO EXISTENTE
        # ==================================================

        if frecuencia_actual:

            st.markdown(
                f"**Preventivo actual:** "
                f"{frecuencia_actual}"
            )

        # ==================================================
        # FRECUENCIA SUGERIDA
        #
        # Solo tiene sentido si existe patrón confirmado.
        # Nunca se propone frecuencia cuando la decisión es
        # simplemente seguir observando.
        # ==================================================

        if (
            frecuencia_sugerida
            and patron_detectado
            and accion != "Seguir observando"
        ):

            st.markdown(
                f"**Frecuencia que conviene valorar:** "
                f"{frecuencia_sugerida}"
            )

        # ==================================================
        # ÚLTIMA INCIDENCIA
        # ==================================================

        if descripcion:

            with st.expander(
                "Ver última incidencia relacionada",
                expanded=False,
            ):

                st.write(
                    descripcion
                )

        st.caption(
            "La inteligencia solo recomienda. "
            "No se ha creado ni modificado "
            "ningún preventivo."
        )


def pantalla_inteligencia_preventiva():

    st.markdown(
        "### 🧠 Inteligencia preventiva"
    )

    st.caption(
        "Analiza el mantenimiento correctivo y busca "
        "patrones que puedan convertirse en "
        "mantenimiento preventivo."
    )

    st.info(
        "Este asesor no modifica órdenes ni preventivos. "
        "Solo analiza los datos y propone actuaciones."
    )

    c1, c2 = st.columns(
        [2, 1]
    )

    with c1:

        centro = st.selectbox(
            "Centro a analizar",
            [
                "Pearson 22",
                "Pearson 9",
            ],
            index=0,
            key="int_prev_centro",
        )

    with c2:

        periodo = st.selectbox(
            "Periodo",
            [
                90,
                180,
                365,
            ],
            index=1,
            format_func=lambda x: (
                f"{x} días"
            ),
            key="int_prev_periodo",
        )

    ejecutar = st.button(
        f"🧠 Analizar {centro}",
        type="primary",
        use_container_width=True,
        key="btn_analizar_inteligencia_preventiva",
    )

    if ejecutar:

        with st.spinner(
            "Analizando histórico "
            "de mantenimiento..."
        ):

            resultado = (
                analizar_inteligencia_preventiva(
                    centro=centro,
                    dias=periodo,
                )
            )

        st.session_state[
            "resultado_inteligencia_preventiva"
        ] = resultado

    resultado = st.session_state.get(
        "resultado_inteligencia_preventiva"
    )

    if not resultado:

        st.caption(
            "Pulsa Analizar para iniciar "
            "el diagnóstico."
        )

        return

    # ==================================================
    # EVITAR MOSTRAR DATOS DE OTRO CENTRO
    # ==================================================

    if (
        resultado.get("centro")
        != centro
    ):

        st.caption(
            f"Pulsa Analizar {centro} "
            f"para actualizar el diagnóstico."
        )

        return

    recomendaciones = resultado.get(
        "recomendaciones",
        [],
    )

    # ==================================================
    # PATRONES REALMENTE CONFIRMADOS
    # ==================================================

    patrones_confirmados = [
        r
        for r in recomendaciones
        if str(
            r.get(
                "patron_detectado",
                "",
            )
        ).strip()
    ]

    altas = len([
        r
        for r in patrones_confirmados
        if r.get("nivel") == "Alta"
    ])

    st.markdown("---")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Correctivos analizados",
        resultado.get(
            "total_correctivos",
            0,
        ),
    )

    c2.metric(
        "Patrones confirmados",
        len(
            patrones_confirmados
        ),
    )

    c3.metric(
        "Atención alta",
        altas,
    )

    # ==================================================
    # SIN CANDIDATOS
    # ==================================================

    if not recomendaciones:

        st.success(
            "No se han encontrado recurrencias "
            "suficientes para analizar en este periodo."
        )

        return

    # ==================================================
    # HAY CASOS, PERO NINGÚN PATRÓN CONFIRMADO
    # ==================================================

    if not patrones_confirmados:

        st.info(
            "Se han detectado espacios con varias "
            "incidencias, pero todavía no existe "
            "un patrón técnico repetido suficientemente "
            "claro para recomendar un nuevo preventivo."
        )

    st.markdown(
        "### 🎯 Recomendaciones"
    )

    st.caption(
        "Ordenadas por recurrencia, riesgo, "
        "prioridad y recencia."
    )

    filtro = st.selectbox(
        "Mostrar",
        [
            "Todas",
            "Alta",
            "Media",
            "Observación",
        ],
        key="int_prev_filtro",
    )

    visibles = recomendaciones

    if filtro != "Todas":

        visibles = [
            r
            for r in recomendaciones
            if r.get("nivel") == filtro
        ]

    if not visibles:

        st.info(
            "No hay recomendaciones "
            "con este nivel."
        )

        return

    for indice, recomendacion in enumerate(
        visibles,
        start=1,
    ):

        _mostrar_recomendacion(
            recomendacion,
            indice,
        )
