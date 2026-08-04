import html

import streamlit as st

from modules.colegio_vivo import obtener_colegio_vivo

from ui.ui_edificio_vivo import (
    css_edificio_vivo,
    normalizar_centro,
    normalizar_edificio,
    normalizar_planta,
    pintar_campus_operario,
)


ORDEN_PRIORIDAD = {
    "urgente": 0,
    "alta": 1,
    "media": 2,
    "baja": 3,
}


MAPA_OPERARIO_CENTRO = {
    "J.A. Almeda": "Pearson 22",
    "Luis Lozano": "Pearson 9",
    "Abel Vasquez": "Pearson 22",
}


def _todas_las_ordenes(colegio):
    ordenes = []

    for centro_datos in colegio:
        nombre_centro = centro_datos.get("centro", "")

        for edificio_datos in centro_datos.get("edificios", []):
            nombre_edificio = edificio_datos.get("nombre", "")

            for planta_datos in edificio_datos.get("plantas", []):
                nombre_planta = planta_datos.get("nombre", "")

                # La misión solo usa órdenes ejecutables.
                ordenes_planta = planta_datos.get(
                    "ordenes_ejecutables",
                    planta_datos.get("ordenes", []),
                )

                for ot in ordenes_planta:
                    fila = dict(ot)

                    fila["_centro_vivo"] = nombre_centro
                    fila["_edificio_vivo"] = nombre_edificio
                    fila["_planta_vivo"] = nombre_planta

                    ordenes.append(fila)

    return ordenes


def _ordenar_misiones(ordenes):
    def clave(ot):
        prioridad = str(
            ot.get("prioridad") or ""
        ).strip().lower()

        en_curso = bool(
            ot.get("_en_curso", False)
        )

        fecha = str(
            ot.get("fecha_creacion")
            or ot.get("fecha")
            or ot.get("fecha_alta")
            or ""
        ).strip()

        identificador = ot.get("id") or 0

        return (
            0 if en_curso else 1,
            ORDEN_PRIORIDAD.get(prioridad, 9),
            fecha,
            identificador,
        )

    return sorted(
        ordenes,
        key=clave,
    )


def _texto_averia(ot):
    return str(
        ot.get("descripcion")
        or ot.get("titulo")
        or ot.get("incidencia")
        or ot.get("trabajo")
        or "Orden de trabajo"
    ).strip()


def _centro_del_operario(operario, colegio):
    centro_configurado = MAPA_OPERARIO_CENTRO.get(
        operario
    )

    if centro_configurado:
        return centro_configurado

    if colegio:
        return normalizar_centro(
            colegio[0].get("centro", "")
        )

    return ""


def _planta_respaldo(centro, edificio):
    if centro == "Pearson 22":
        if edificio == "Llar":
            return "Planta 0"

        return "Planta 1"

    if centro == "Pearson 9":
        return "Planta 0"

    return ""


def _crear_resumen_edificios(colegio):
    resumen = {}

    for centro_datos in colegio:
        centro = normalizar_centro(
            centro_datos.get("centro", "")
        )

        for edificio_datos in centro_datos.get(
            "edificios",
            [],
        ):
            edificio = normalizar_edificio(
                edificio_datos.get("nombre", ""),
                centro,
            )

            for planta_datos in edificio_datos.get(
                "plantas",
                [],
            ):
                planta = normalizar_planta(
                    planta_datos.get("nombre", "")
                )

                if not planta:
                    planta = _planta_respaldo(
                        centro,
                        edificio,
                    )

                if not planta:
                    continue

                clave = (
                    centro,
                    edificio,
                    planta,
                )

                if clave not in resumen:
                    resumen[clave] = {
                        "total": 0,
                        "ejecutables": 0,
                        "bloqueadas": 0,
                        "en_curso": 0,
                        "sin_ubicar": 0,
                        "urgentes": 0,
                        "altas": 0,
                        "ordenes": [],
                        "ordenes_ejecutables": [],
                        "ordenes_bloqueadas": [],
                    }

                destino = resumen[clave]

                destino["total"] += int(
                    planta_datos.get("total") or 0
                )

                destino["ejecutables"] += int(
                    planta_datos.get("ejecutables")
                    or 0
                )

                destino["bloqueadas"] += int(
                    planta_datos.get("bloqueadas")
                    or 0
                )

                destino["en_curso"] += int(
                    planta_datos.get("en_curso")
                    or 0
                )

                destino["sin_ubicar"] += int(
                    planta_datos.get("sin_ubicar")
                    or 0
                )

                destino["urgentes"] += int(
                    planta_datos.get("urgentes")
                    or 0
                )

                destino["altas"] += int(
                    planta_datos.get("altas")
                    or 0
                )

                destino["ordenes"].extend(
                    planta_datos.get(
                        "ordenes",
                        [],
                    )
                )

                destino[
                    "ordenes_ejecutables"
                ].extend(
                    planta_datos.get(
                        "ordenes_ejecutables",
                        [],
                    )
                )

                destino[
                    "ordenes_bloqueadas"
                ].extend(
                    planta_datos.get(
                        "ordenes_bloqueadas",
                        [],
                    )
                )

    return resumen


def _guardar_ot_recomendada(ot):
    st.session_state["colegio_vivo_ot"] = ot
    st.session_state["colegio_vivo_ot_id"] = ot.get("id")


def _ubicacion_mision(ot):
    centro = normalizar_centro(
        ot.get("_centro_normalizado")
        or ot.get("_centro_vivo")
        or ot.get("centro")
        or ""
    )

    edificio = normalizar_edificio(
        ot.get("_edificio_normalizado")
        or ot.get("_edificio_vivo")
        or ot.get("edificio")
        or "",
        centro,
    )

    planta = normalizar_planta(
        ot.get("_planta_normalizada")
        or ot.get("_planta_vivo")
        or ot.get("planta")
        or ot.get("espacio")
        or ""
    )

    if not planta:
        planta = _planta_respaldo(
            centro,
            edificio,
        )

    return centro, edificio, planta


def _recoger_planta_query():
    params = st.query_params

    if params.get("cv_accion") != "planta":
        return

    centro = str(
        params.get("cv_centro") or ""
    ).strip()

    edificio = str(
        params.get("cv_edificio") or ""
    ).strip()

    planta = str(
        params.get("cv_planta") or ""
    ).strip()

    if not centro or not edificio or not planta:
        return

    st.session_state["colegio_vivo_centro"] = centro
    st.session_state["colegio_vivo_edificio"] = edificio
    st.session_state["colegio_vivo_planta"] = planta


def _css_pantalla_operario():
    st.markdown(
        """
        <style>
        .block-container{
            padding-top:.08rem !important;
            padding-left:.30rem !important;
            padding-right:.30rem !important;
            padding-bottom:.30rem !important;
            max-width:1500px !important;
        }

        .cv-mission{
            display:grid;
            grid-template-columns:1fr;
            background:linear-gradient(
                135deg,
                #0f2747,
                #164f91
            );
            color:#fff;
            border-radius:11px;
            padding:7px 10px;
            margin:0 0 3px;
            box-shadow:0 4px 12px rgba(15,39,71,.16);
        }

        .cv-mission-top{
            font-size:10px;
            line-height:1;
            font-weight:950;
            margin-bottom:2px;
        }

        .cv-mission-place{
            font-size:12px;
            line-height:1.1;
            font-weight:950;
        }

        .cv-mission-description{
            margin-top:2px;
            overflow:hidden;
            color:rgba(255,255,255,.93);
            font-size:10px;
            line-height:1.1;
            white-space:nowrap;
            text-overflow:ellipsis;
        }

        .cv-school-title{
            margin:4px 0 0 1px;
            color:#0f2747;
            font-size:13px;
            line-height:1;
            font-weight:950;
        }

        .cv-no-work{
            margin-bottom:3px;
            padding:7px 9px;
            border:1px solid #bbf7d0;
            border-radius:10px;
            background:#f0fdf4;
            color:#166534;
            font-size:11px;
            font-weight:900;
        }

        div[data-testid="stButton"]
        button[kind="primary"]{
            min-height:31px !important;
            height:31px !important;
            margin:0 !important;
            padding:1px 8px !important;
            border-radius:8px !important;
            font-size:10px !important;
            font-weight:950 !important;
        }

        div[data-testid="stButton"]{
            margin-bottom:0 !important;
        }

        div[data-testid="stVerticalBlock"]{
            gap:.10rem !important;
        }

        @media(max-width:760px){
            .block-container{
                padding-left:.16rem !important;
                padding-right:.16rem !important;
            }

            .cv-mission{
                padding:6px 8px;
                border-radius:9px;
            }

            .cv-mission-top{
                font-size:9px;
            }

            .cv-mission-place{
                font-size:10px;
            }

            .cv-mission-description{
                font-size:8px;
            }

            .cv-school-title{
                font-size:11px;
            }

            div[data-testid="stButton"]
            button[kind="primary"]{
                min-height:29px !important;
                height:29px !important;
                font-size:9px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pantalla_colegio_vivo_operario():
    _css_pantalla_operario()
    css_edificio_vivo()
    _recoger_planta_query()

    operario = str(
        st.session_state.get("operario_activo")
        or st.session_state.get("usuario")
        or ""
    ).strip()

    colegio = obtener_colegio_vivo(operario)

    centro_operario = _centro_del_operario(
        operario,
        colegio,
    )

    resumen = _crear_resumen_edificios(
        colegio
    )

    ordenes = _ordenar_misiones(
        _todas_las_ordenes(colegio)
    )

    # =====================================================
    # MISIÓN
    # =====================================================
    if ordenes:
        mision = ordenes[0]

        centro, edificio, planta = _ubicacion_mision(
            mision
        )

        prioridad = str(
            mision.get("prioridad")
            or "Media"
        ).strip()

        descripcion = _texto_averia(
            mision
        )

        # Sin sangrías internas para que Streamlit
        # no lo interprete como código.
        html_mision = (
            '<div class="cv-mission">'
            f'<div class="cv-mission-top">'
            f'❤️ MI MISIÓN · '
            f'{html.escape(prioridad.upper())}'
            f'</div>'
            f'<div class="cv-mission-place">'
            f'{html.escape(centro)} · '
            f'{html.escape(edificio)} · '
            f'{html.escape(planta)}'
            f'</div>'
            f'<div class="cv-mission-description">'
            f'{html.escape(descripcion)}'
            f'</div>'
            f'</div>'
        )

        st.markdown(
            html_mision,
            unsafe_allow_html=True,
        )

        texto_boton = (
            "▶ CONTINUAR AHORA"
            if mision.get("_en_curso", False)
            else "▶ EMPEZAR AHORA"
        )

        if st.button(
            texto_boton,
            key=(
                f"cv_empezar_"
                f"{mision.get('id', 'primera')}"
            ),
            type="primary",
            use_container_width=True,
        ):
            _guardar_ot_recomendada(
                mision
            )
            st.rerun()

    else:
        st.markdown(
            '<div class="cv-no-work">'
            '✅ No tienes órdenes ejecutables.'
            '</div>',
            unsafe_allow_html=True,
        )

    # =====================================================
    # COLEGIO VIVO
    # =====================================================
    st.markdown(
        '<div class="cv-school-title">'
        '🏫 COLEGIO VIVO'
        '</div>',
        unsafe_allow_html=True,
    )

    if not centro_operario:
        st.info(
            "No hay un centro asignado a este operario."
        )
        return

    pintar_campus_operario(
        centro=centro_operario,
        resumen=resumen,
    )
