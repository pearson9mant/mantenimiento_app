import streamlit as st
import pandas as pd

from modules.inteligencia_preventiva import (
    analizar_inteligencia_preventiva,
)


ACCIONES_PRIORITARIAS = {
    "Crear preventivo",
    "Revisar frecuencia",
}

ACCIONES_CONTROL = {
    "Vigilar preventivo existente",
}

ACCIONES_OBSERVACION = {
    "Seguir observando",
}


def _icono_nivel(nivel):
    if nivel == "Alta":
        return "🔴"

    if nivel == "Media":
        return "🟠"

    return "🟡"


def _limpiar_texto(valor, defecto="-"):
    texto = str(valor or "").strip()

    if not texto or texto.lower() in {
        "nan",
        "none",
        "null",
    }:
        return defecto

    return texto


def _resumen_decisiones(recomendaciones):
    resultado = {
        "crear": 0,
        "revisar": 0,
        "vigilar": 0,
        "observar": 0,
        "con_preventivo": 0,
        "con_patron": 0,
    }

    for item in recomendaciones:
        accion = str(
            item.get("accion") or ""
        ).strip()

        if accion == "Crear preventivo":
            resultado["crear"] += 1

        elif accion == "Revisar frecuencia":
            resultado["revisar"] += 1

        elif accion == "Vigilar preventivo existente":
            resultado["vigilar"] += 1

        elif accion == "Seguir observando":
            resultado["observar"] += 1

        if str(
            item.get("frecuencia_actual") or ""
        ).strip():
            resultado["con_preventivo"] += 1

        if str(
            item.get("patron_detectado") or ""
        ).strip():
            resultado["con_patron"] += 1

    return resultado


def _lectura_general(resultado, recomendaciones):
    if not recomendaciones:
        return {
            "estado": "estable",
            "titulo": "🟢 Sin señales suficientes para proponer cambios",
            "texto": (
                "En el periodo analizado no aparecen recurrencias "
                "con evidencia suficiente para recomendar nuevos preventivos."
            ),
        }

    resumen = _resumen_decisiones(
        recomendaciones
    )

    propuestas = (
        resumen["crear"]
        + resumen["revisar"]
    )

    if propuestas >= 3:
        return {
            "estado": "atencion",
            "titulo": "🔴 Hay margen claro de mejora preventiva",
            "texto": (
                f"Se detectan {propuestas} casos donde conviene valorar "
                "crear un preventivo o revisar su frecuencia. "
                "La prioridad debe centrarse en los patrones más repetidos "
                "y con intervalos de fallo más cortos."
            ),
        }

    if propuestas >= 1:
        return {
            "estado": "seguimiento",
            "titulo": "🟠 Hay puntos concretos que merece la pena revisar",
            "texto": (
                f"Se detectan {propuestas} caso(s) con propuesta preventiva "
                "concreta. No se recomienda ampliar preventivos de forma general, "
                "solo actuar donde el patrón técnico está confirmado."
            ),
        }

    return {
        "estado": "estable",
        "titulo": "🟢 La mayor parte de los casos aconseja observar",
        "texto": (
            "Hay actividad correctiva, pero todavía no se observa suficiente "
            "evidencia técnica para crear nuevos preventivos de forma general."
        ),
    }


def _principal_foco(recomendaciones):
    candidatos = [
        item
        for item in recomendaciones
        if str(
            item.get("patron_detectado") or ""
        ).strip()
    ]

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda item: (
            int(item.get("score", 0) or 0),
            int(item.get("cantidad", 0) or 0),
        ),
        reverse=True,
    )

    return candidatos[0]


def _mostrar_esquema_decisiones(recomendaciones):
    resumen = _resumen_decisiones(
        recomendaciones
    )

    datos = pd.DataFrame(
        {
            "Decisión": [
                "Crear preventivo",
                "Revisar frecuencia",
                "Vigilar existente",
                "Seguir observando",
            ],
            "Casos": [
                resumen["crear"],
                resumen["revisar"],
                resumen["vigilar"],
                resumen["observar"],
            ],
        }
    ).set_index("Decisión")

    st.markdown(
        "### 📊 Esquema de decisiones"
    )

    st.caption(
        "Resume únicamente los casos que han superado "
        "la primera criba de recurrencia."
    )

    st.bar_chart(
        datos,
        y="Casos",
        use_container_width=True,
    )


def _mostrar_esquema_areas(recomendaciones):
    if not recomendaciones:
        return

    filas = []

    for item in recomendaciones:
        filas.append(
            {
                "Área": _limpiar_texto(
                    item.get("area"),
                    "Sin área",
                ),
                "Incidencias": int(
                    item.get("cantidad", 0)
                    or 0
                ),
            }
        )

    df = pd.DataFrame(filas)

    if df.empty:
        return

    resumen = (
        df.groupby(
            "Área",
            as_index=False,
        )["Incidencias"]
        .sum()
        .sort_values(
            "Incidencias",
            ascending=False,
        )
        .head(8)
        .set_index("Área")
    )

    st.markdown(
        "### 🧭 Áreas con mayor recurrencia analizada"
    )

    st.caption(
        "No representa todas las incidencias del centro: "
        "solo los grupos que han entrado en el análisis preventivo."
    )

    st.bar_chart(
        resumen,
        y="Incidencias",
        use_container_width=True,
    )


def _mostrar_mapa_resumen(recomendaciones):
    if not recomendaciones:
        return

    filas = []

    for item in recomendaciones:
        edificio = _limpiar_texto(
            item.get("edificio"),
            "Sin edificio",
        )

        planta = _limpiar_texto(
            item.get("planta"),
            "",
        )

        espacio = _limpiar_texto(
            item.get("espacio"),
            "Sin espacio",
        )

        ubicacion = edificio

        if planta:
            ubicacion += f" · {planta}"

        ubicacion += f" · {espacio}"

        intervalo = item.get(
            "intervalo_medio"
        )

        filas.append(
            {
                "Ubicación": ubicacion,
                "Área": _limpiar_texto(
                    item.get("area")
                ),
                "Patrón": _limpiar_texto(
                    item.get(
                        "patron_detectado"
                    ),
                    "Sin patrón confirmado",
                ),
                "Incidencias": int(
                    item.get("cantidad", 0)
                    or 0
                ),
                "Intervalo": (
                    f"{intervalo} días"
                    if intervalo is not None
                    else "-"
                ),
                "Preventivo actual": _limpiar_texto(
                    item.get(
                        "frecuencia_actual"
                    )
                ),
                "Decisión": _limpiar_texto(
                    item.get("accion")
                ),
                "Índice": int(
                    item.get("score", 0)
                    or 0
                ),
            }
        )

    df = pd.DataFrame(
        filas
    )

    st.markdown(
        "### 🗺️ Mapa de análisis"
    )

    st.caption(
        "Vista rápida para localizar dónde existe patrón, "
        "qué preventivo hay y qué recomienda la inteligencia."
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
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

    icono = _icono_nivel(
        nivel
    )

    with st.container(
        border=True
    ):
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

        c1, c2, c3 = st.columns(
            3
        )

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

        if patron_detectado:
            st.markdown(
                f"**🔎 Patrón técnico:** "
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

        st.markdown(
            f"**🧠 Decisión:** "
            f"{accion}"
        )

        if accion in ACCIONES_PRIORITARIAS:
            st.warning(
                motivo
            )

        elif accion in ACCIONES_CONTROL:
            st.info(
                motivo
            )

        else:
            st.info(
                motivo
            )

        if intervalo is not None:
            st.caption(
                f"Intervalo medio observado "
                f"entre incidencias: "
                f"{intervalo} días."
            )

        if frecuencia_actual:
            st.markdown(
                f"**Preventivo actual:** "
                f"{frecuencia_actual}"
            )

        if (
            frecuencia_sugerida
            and patron_detectado
            and accion
            != "Seguir observando"
        ):
            st.markdown(
                f"**Frecuencia que conviene valorar:** "
                f"{frecuencia_sugerida}"
            )

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
        "### ⚖️ Análisis Incidencias - Preventivo"
    )

    st.caption(
        "Compara el mantenimiento correctivo con los preventivos existentes "
        "y busca patrones técnicos que merezcan una actuación preventiva."
    )

    st.info(
        "El análisis se ejecuta solo al pulsar Analizar. "
        "No modifica órdenes, frecuencias ni preventivos."
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
            "Analizando incidencias, patrones y preventivos..."
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
            "Pulsa Analizar para iniciar el diagnóstico."
        )
        return

    if (
        resultado.get("centro")
        != centro
        or int(
            resultado.get(
                "dias",
                periodo,
            )
            or periodo
        )
        != int(periodo)
    ):
        st.caption(
            f"Pulsa Analizar {centro} para actualizar "
            f"el diagnóstico de {periodo} días."
        )
        return

    recomendaciones = resultado.get(
        "recomendaciones",
        [],
    )

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

    resumen_decisiones = (
        _resumen_decisiones(
            recomendaciones
        )
    )

    altas = len(
        [
            r
            for r in patrones_confirmados
            if r.get("nivel") == "Alta"
        ]
    )

    st.markdown("---")

    # ==================================================
    # LECTURA GENERAL
    # ==================================================
    lectura = _lectura_general(
        resultado,
        recomendaciones,
    )

    st.markdown(
        "## 🧠 Lectura rápida"
    )

    if lectura["estado"] == "atencion":
        st.error(
            f"**{lectura['titulo']}**\n\n"
            f"{lectura['texto']}"
        )

    elif lectura["estado"] == "seguimiento":
        st.warning(
            f"**{lectura['titulo']}**\n\n"
            f"{lectura['texto']}"
        )

    else:
        st.success(
            f"**{lectura['titulo']}**\n\n"
            f"{lectura['texto']}"
        )

    # ==================================================
    # KPIs
    # ==================================================
    c1, c2, c3, c4 = st.columns(
        4
    )

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
        "Crear / ajustar preventivo",
        (
            resumen_decisiones["crear"]
            + resumen_decisiones["revisar"]
        ),
    )

    c4.metric(
        "Atención alta",
        altas,
    )

    # ==================================================
    # FOCO PRINCIPAL
    # ==================================================
    foco = _principal_foco(
        recomendaciones
    )

    if foco:
        st.markdown(
            "### 🎯 Principal foco preventivo"
        )

        ubicacion = " · ".join(
            [
                valor
                for valor in [
                    _limpiar_texto(
                        foco.get("edificio"),
                        "",
                    ),
                    _limpiar_texto(
                        foco.get("planta"),
                        "",
                    ),
                    _limpiar_texto(
                        foco.get("espacio"),
                        "",
                    ),
                ]
                if valor
            ]
        )

        st.warning(
            f"**{ubicacion or 'Ubicación pendiente'}**  \n"
            f"Patrón: **{_limpiar_texto(foco.get('patron_detectado'))}** · "
            f"{int(foco.get('repeticiones_patron', 0) or 0)} repeticiones · "
            f"Índice {int(foco.get('score', 0) or 0)}/100.  \n"
            f"**Propuesta:** {_limpiar_texto(foco.get('accion'))}."
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

    if not patrones_confirmados:
        st.info(
            "Se han detectado espacios con varias incidencias, "
            "pero todavía no existe un patrón técnico repetido "
            "suficientemente claro para recomendar un nuevo preventivo."
        )

    # ==================================================
    # ESQUEMAS
    # ==================================================
    col_a, col_b = st.columns(
        2
    )

    with col_a:
        _mostrar_esquema_decisiones(
            recomendaciones
        )

    with col_b:
        _mostrar_esquema_areas(
            recomendaciones
        )

    _mostrar_mapa_resumen(
        recomendaciones
    )

    # ==================================================
    # RECOMENDACIONES DETALLADAS
    # ==================================================
    st.markdown(
        "## 🔧 Recomendaciones técnicas"
    )

    st.caption(
        "Ordenadas por recurrencia, riesgo, prioridad y recencia."
    )

    filtro = st.selectbox(
        "Mostrar",
        [
            "Todas",
            "Crear preventivo",
            "Revisar frecuencia",
            "Vigilar preventivo existente",
            "Seguir observando",
            "Alta",
            "Media",
            "Observación",
        ],
        key="int_prev_filtro",
    )

    visibles = recomendaciones

    if filtro in {
        "Alta",
        "Media",
        "Observación",
    }:
        visibles = [
            r
            for r in recomendaciones
            if r.get("nivel") == filtro
        ]

    elif filtro != "Todas":
        visibles = [
            r
            for r in recomendaciones
            if str(
                r.get("accion") or ""
            ).strip() == filtro
        ]

    if not visibles:
        st.info(
            "No hay recomendaciones con este filtro."
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
