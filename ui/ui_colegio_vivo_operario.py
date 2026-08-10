import html

import streamlit as st

from modules.colegio_vivo import obtener_colegio_vivo

from ui.ui_edificio_vivo import (
    css_edificio_vivo,
    normalizar_centro,
    normalizar_edificio,
    normalizar_planta,
    pintar_campus_operario,
    volver_colegio_vivo,
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
        nombre_centro = centro_datos.get(
            "centro",
            "",
        )

        for edificio_datos in centro_datos.get(
            "edificios",
            [],
        ):
            nombre_edificio = edificio_datos.get(
                "nombre",
                "",
            )

            for planta_datos in edificio_datos.get(
                "plantas",
                [],
            ):
                nombre_planta = planta_datos.get(
                    "nombre",
                    "",
                )

                ordenes_planta = planta_datos.get(
                    "ordenes_ejecutables",
                    [],
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
        or "Orden de trabajo"
    ).strip()


def _centro_del_operario(
    operario,
    colegio,
):
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


def _planta_respaldo(
    centro,
    edificio,
):
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

                for campo in [
                    "total",
                    "ejecutables",
                    "bloqueadas",
                    "en_curso",
                    "sin_ubicar",
                    "urgentes",
                    "altas",
                ]:
                    destino[campo] += int(
                        planta_datos.get(campo) or 0
                    )

                destino["ordenes"].extend(
                    planta_datos.get(
                        "ordenes",
                        [],
                    )
                )

                destino["ordenes_ejecutables"].extend(
                    planta_datos.get(
                        "ordenes_ejecutables",
                        [],
                    )
                )

                destino["ordenes_bloqueadas"].extend(
                    planta_datos.get(
                        "ordenes_bloqueadas",
                        [],
                    )
                )

    return resumen


def _guardar_ot_recomendada(ot):
    """
    Abre una OT utilizando la única clave que entiende ui_operario.py.
    """
    id_ot = ot.get("id")

    if id_ot is None:
        return False

    try:
        id_ot = int(id_ot)
    except (TypeError, ValueError):
        return False

    st.session_state["operario_ot_abierta_id"] = id_ot

    for clave in [
        "colegio_vivo_ot",
        "colegio_vivo_ot_id",
        "ot_seleccionada",
        "ot_seleccionada_id",
        "orden_abierta",
        "orden_abierta_id",
    ]:
        st.session_state.pop(clave, None)

    return True


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


def _texto_aula(ot):
    aula = str(
        ot.get("espacio")
        or ot.get("aula")
        or ot.get("ubicacion")
        or ""
    ).strip()

    return aula or "Espacio pendiente"


def _abrir_ot_para_trabajar(ot, origen="mision"):
    """
    Abre directamente la OT seleccionada sin pasar por el listado general.
    """
    if not _guardar_ot_recomendada(ot):
        return

    st.session_state["colegio_vivo_origen_ot"] = origen

    if origen != "planta":
        st.session_state["colegio_vivo_vista"] = "mapa"

    st.session_state["seccion_actual"] = "Órdenes"


def _volver_edificio_desde_planta():
    """
    Vuelve al edificio sin lanzar un rerun manual adicional.
    """
    volver_colegio_vivo()


def _mostrar_planta_seleccionada():
    """
    Vista de planta estable y nativa de Streamlit.

    No usa HTML personalizado en las tarjetas de OT para evitar
    inconsistencias del DOM en navegadores móviles.
    """
    if st.session_state.get("colegio_vivo_vista") != "planta":
        return False

    centro = st.session_state.get("colegio_vivo_centro", "")
    edificio = st.session_state.get("colegio_vivo_edificio", "")
    planta = st.session_state.get("colegio_vivo_planta", "")
    ordenes = st.session_state.get("colegio_vivo_ordenes_planta", [])

    st.button(
        "← VOLVER AL EDIFICIO",
        key="cv_volver_edificio",
        use_container_width=True,
        on_click=_volver_edificio_desde_planta,
    )

    st.markdown(
        f"### 📍 {centro} · {edificio} · {planta}"
    )
    st.caption(
        f"{len(ordenes)} OT activas"
    )

    if not ordenes:
        st.success(
            "✅ No hay órdenes activas en esta planta."
        )
        return True

    for ot in ordenes:
        numero_ot = str(
            ot.get("numero_ot")
            or ot.get("id")
            or "OT"
        ).strip()

        aula = _texto_aula(ot)

        descripcion = _texto_averia(ot)

        estado = str(
            ot.get("estado")
            or "Abierta"
        ).strip()

        prioridad = str(
            ot.get("prioridad")
            or "Media"
        ).strip()

        es_ejecutable = bool(
            ot.get("_ejecutable", False)
        )

        with st.container(border=True):
            st.markdown(
                f"**{numero_ot} · {aula}**"
            )

            st.markdown(
                descripcion or "Sin descripción."
            )

            st.caption(
                f"{prioridad} · {estado}"
            )

            if es_ejecutable:
                st.button(
                    f"▶ EMPEZAR {numero_ot}",
                    key=f"cv_empezar_planta_{ot.get('id')}",
                    use_container_width=True,
                    on_click=_abrir_ot_para_trabajar,
                    args=(ot, "planta"),
                )

    return True



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
            background:linear-gradient(
                135deg,
                #0f2747,
                #164f91
            );
            color:#fff;
            border-radius:15px;
            padding:17px 20px 15px;
            margin:0 auto 3px;
            width:min(100%,1180px);
            box-shadow:
                0 4px 12px rgba(15,39,71,.16);
        }

        .cv-mission-top{
            font-size:16px;
            line-height:1;
            font-weight:950;
            margin-bottom:9px;
        }

        .cv-mission-place{
            font-size:22px;
            line-height:1.15;
            font-weight:950;
        }

        .cv-mission-description{
            margin-top:10px;
            overflow:hidden;
            color:rgba(255,255,255,.94);
            font-size:15px;
            line-height:1.35;
            white-space:normal;
            display:-webkit-box;
            -webkit-line-clamp:2;
            -webkit-box-orient:vertical;
        }

        .cv-school-title{
            width:min(100%,1180px);
            margin:5px auto 1px;
            color:#0f2747;
            font-size:20px;
            line-height:1;
            font-weight:950;
        }

        .cv-no-work{
            width:min(100%,1180px);
            margin:0 auto 3px;
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
            display:block !important;
            width:min(100%,1180px) !important;
            min-height:50px !important;
            height:50px !important;
            margin:0 auto !important;
            padding:1px 8px !important;
            border-radius:8px !important;
            font-size:17px !important;
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
                padding-left:.14rem !important;
                padding-right:.14rem !important;
            }

            .cv-mission{
                width:100%;
                padding:11px 12px 10px;
                border-radius:11px;
            }

            .cv-mission-top{
                font-size:11px;
            }

            .cv-mission-place{
                font-size:14px;
            }

            .cv-mission-description{
                font-size:10px;
            }

            .cv-school-title{
                width:100%;
                font-size:11px;
            }

            div[data-testid="stButton"]
            button[kind="primary"]{
                width:100% !important;
                min-height:37px !important;
                height:37px !important;
                font-size:12px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pantalla_colegio_vivo_operario():
    _css_pantalla_operario()
    css_edificio_vivo()

    if _mostrar_planta_seleccionada():
        return

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
    # MI MISIÓN
    # =====================================================
    if ordenes:
        mision = ordenes[0]

        centro, edificio, planta = _ubicacion_mision(
            mision
        )

        aula = _texto_aula(
            mision
        )

        prioridad = str(
            mision.get("prioridad")
            or "Media"
        ).strip()

        descripcion = _texto_averia(
            mision
        )

        html_mision = (
            '<div class="cv-mission">'
            f'<div class="cv-mission-top">'
            f'❤️ MI MISIÓN · '
            f'{html.escape(prioridad.upper())}'
            f'</div>'
            f'<div class="cv-mission-place">'
            f'{html.escape(centro)} · '
            f'{html.escape(edificio)} · '
            f'{html.escape(planta)} · '
            f'{html.escape(aula)}'
            f'</div>'
            f'<div class="cv-mission-description">'
            f'{html.escape(descripcion)}'
            f'</div>'
            '</div>'
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

        st.button(
            texto_boton,
            key=(
                f"cv_empezar_"
                f"{mision.get('id', 'primera')}"
            ),
            type="primary",
            use_container_width=True,
            on_click=_abrir_ot_para_trabajar,
            args=(mision, "mision"),
        )

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
