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

                for ot in planta_datos.get(
                    "ordenes_ejecutables",
                    planta_datos.get("ordenes", []),
                ):
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

        fecha = str(
            ot.get("fecha_creacion")
            or ot.get("fecha")
            or ot.get("fecha_alta")
            or ""
        ).strip()

        identificador = ot.get("id") or 0

        return (
            ORDEN_PRIORIDAD.get(prioridad, 9),
            fecha,
            identificador,
        )

    return sorted(ordenes, key=clave)


def _texto_averia(ot):
    return str(
        ot.get("descripcion")
        or ot.get("titulo")
        or ot.get("incidencia")
        or ot.get("trabajo")
        or "Orden de trabajo"
    ).strip()


def _centro_del_operario(operario, colegio):
    centro_configurado = MAPA_OPERARIO_CENTRO.get(operario)

    if centro_configurado:
        return centro_configurado

    if colegio:
        return normalizar_centro(
            colegio[0].get("centro", "")
        )

    return ""


def _crear_resumen_edificios(colegio):
    """
    Genera un único resumen por:
    centro + edificio normalizado + planta normalizada.

    Esto evita duplicados como:
    - Edif. Infantil/Primaria
    - Infantil / Primaria
    - Infantil/Primaria
    """
    resumen = {}

    for centro_datos in colegio:
        centro = normalizar_centro(
            centro_datos.get("centro", "")
        )

        for edificio_datos in centro_datos.get("edificios", []):
            edificio = normalizar_edificio(
                edificio_datos.get("nombre", ""),
                centro,
            )

            for planta_datos in edificio_datos.get("plantas", []):
                planta_original = planta_datos.get("nombre", "")

                planta = normalizar_planta(planta_original)

                # Las OT sin planta no se colocan en una planta incorrecta.
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
                        "urgentes": 0,
                        "altas": 0,
                        "ordenes": [],
                    }

                resumen[clave]["total"] += int(
                    planta_datos.get("total") or 0
                )

                resumen[clave]["urgentes"] += int(
                    planta_datos.get("urgentes") or 0
                )

                resumen[clave]["altas"] += int(
                    planta_datos.get("altas") or 0
                )

                resumen[clave]["ordenes"].extend(
                    planta_datos.get("ordenes", [])
                )

    return resumen


def _guardar_ot_recomendada(ot):
    st.session_state["colegio_vivo_ot"] = ot
    st.session_state["colegio_vivo_ot_id"] = ot.get("id")


def _ubicacion_mision(ot):
    centro = normalizar_centro(
        ot.get("_centro_vivo")
        or ot.get("centro")
        or ""
    )

    edificio = normalizar_edificio(
        ot.get("_edificio_vivo")
        or ot.get("edificio")
        or "",
        centro,
    )

    planta = normalizar_planta(
        ot.get("_planta_vivo")
        or ot.get("planta")
        or ot.get("espacio")
        or ""
    )

    if not planta:
        planta = "Pendiente de ubicar"

    return centro, edificio, planta


def _css_pantalla_operario():
    st.markdown(
        """
        <style>
        /* ================================================
           PANTALLA PRINCIPAL DEL OPERARIO
        ================================================= */

        .block-container {
            padding-top: 0.10rem !important;
            padding-left: 0.50rem !important;
            padding-right: 0.50rem !important;
            padding-bottom: 0.50rem !important;
            max-width: 1500px !important;
        }

        .cv-mission {
            background:
                linear-gradient(
                    135deg,
                    #0f2747 0%,
                    #164f91 100%
                );
            color: #ffffff;
            border-radius: 14px;
            padding: 10px 13px;
            margin: 0 0 4px 0;
            box-shadow:
                0 6px 16px rgba(15, 39, 71, 0.18);
        }

        .cv-mission-top {
            font-size: 12px;
            line-height: 1.1;
            font-weight: 950;
            margin-bottom: 3px;
        }

        .cv-mission-place {
            font-size: 15px;
            line-height: 1.15;
            font-weight: 950;
        }

        .cv-mission-description {
            font-size: 12px;
            line-height: 1.2;
            margin-top: 4px;
            opacity: 0.95;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .cv-school-title {
            font-size: 16px;
            line-height: 1.1;
            font-weight: 950;
            color: #0f2747;
            margin: 6px 0 1px 2px;
        }

        .cv-no-work {
            border: 1px solid #bbf7d0;
            background: #f0fdf4;
            color: #166534;
            border-radius: 12px;
            padding: 9px 12px;
            font-size: 13px;
            font-weight: 900;
            margin-bottom: 5px;
        }

        /* Botón principal de misión */
        div[data-testid="stButton"] button[kind="primary"] {
            min-height: 36px !important;
            height: 36px !important;
            border-radius: 10px !important;
            padding: 2px 10px !important;
            font-size: 12px !important;
            font-weight: 950 !important;
            margin: 0 !important;
        }

        div[data-testid="stButton"] {
            margin-bottom: 0 !important;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.18rem !important;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 0.40rem !important;
        }

        hr {
            margin: 4px 0 !important;
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 0.28rem !important;
                padding-right: 0.28rem !important;
            }

            .cv-mission {
                padding: 8px 9px;
                border-radius: 11px;
            }

            .cv-mission-top {
                font-size: 10px;
            }

            .cv-mission-place {
                font-size: 12px;
            }

            .cv-mission-description {
                font-size: 10px;
            }

            .cv-school-title {
                font-size: 13px;
                margin-top: 4px;
            }

            div[data-testid="stButton"]
            button[kind="primary"] {
                min-height: 33px !important;
                height: 33px !important;
                font-size: 11px !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.20rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pantalla_colegio_vivo_operario():
    _css_pantalla_operario()
    css_edificio_vivo()

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

    resumen = _crear_resumen_edificios(colegio)

    ordenes = _ordenar_misiones(
        _todas_las_ordenes(colegio)
    )

    # =====================================================
    # MISIÓN RECOMENDADA
    # Siempre aparece en primera línea.
    # =====================================================
    if ordenes:
        mision = ordenes[0]

        centro, edificio, planta = _ubicacion_mision(mision)

        prioridad = str(
            mision.get("prioridad")
            or "Media"
        ).strip()

        descripcion = _texto_averia(mision)

        st.markdown(
            f"""
            <div class="cv-mission">
                <div class="cv-mission-top">
                    ❤️ MI MISIÓN ·
                    {html.escape(prioridad.upper())}
                </div>

                <div class="cv-mission-place">
                    {html.escape(centro)}
                    ·
                    {html.escape(edificio)}
                    ·
                    {html.escape(planta)}
                </div>

                <div class="cv-mission-description">
                    {html.escape(descripcion)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "▶ EMPEZAR AHORA",
            key=(
                f"cv_empezar_"
                f"{mision.get('id', 'primera')}"
            ),
            type="primary",
            use_container_width=True,
        ):
            _guardar_ot_recomendada(mision)
            st.rerun()

    else:
        st.markdown(
            """
            <div class="cv-no-work">
                ✅ No tienes órdenes ejecutables.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =====================================================
    # COLEGIO VIVO
    # =====================================================
    st.markdown(
        """
        <div class="cv-school-title">
            🏫 COLEGIO VIVO
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not centro_operario:
        st.info("No hay un centro asignado a este operario.")
        return

    pintar_campus_operario(
        centro=centro_operario,
        resumen=resumen,
    )
