import streamlit as st

from modules.colegio_vivo import obtener_colegio_vivo


ORDEN_PRIORIDAD = {
    "urgente": 0,
    "alta": 1,
    "media": 2,
    "baja": 3,
}


def _todas_las_ordenes(colegio):
    ordenes = []

    for centro in colegio:
        for edificio in centro.get("edificios", []):
            for planta in edificio.get("plantas", []):
                for ot in planta.get("ordenes", []):
                    fila = dict(ot)
                    fila["_centro_vivo"] = centro.get("centro", "")
                    fila["_edificio_vivo"] = edificio.get("nombre", "")
                    fila["_planta_vivo"] = planta.get("nombre", "")
                    ordenes.append(fila)

    return ordenes


def _ordenar_misiones(ordenes):
    def clave(ot):
        prioridad = str(ot.get("prioridad") or "").strip().lower()

        fecha = str(
            ot.get("fecha")
            or ot.get("fecha_creacion")
            or ot.get("fecha_alta")
            or ""
        )

        return (
            ORDEN_PRIORIDAD.get(prioridad, 9),
            fecha,
            str(ot.get("id") or ""),
        )

    return sorted(ordenes, key=clave)


def _texto_averia(ot):
    return str(
        ot.get("titulo")
        or ot.get("incidencia")
        or ot.get("descripcion")
        or ot.get("trabajo")
        or "Orden de trabajo"
    ).strip()


def _guardar_ot_seleccionada(ot):
    """
    De momento guarda la OT recomendada.
    En el siguiente paso la conectaremos con la pantalla
    real de trabajo usando las claves exactas de ui_operario.py.
    """
    st.session_state["colegio_vivo_ot"] = ot
    st.session_state["colegio_vivo_ot_id"] = ot.get("id")


def pantalla_colegio_vivo_operario():
    st.markdown(
        """
        <style>
        /* Pantalla operario compacta */
        .block-container {
            padding-top: 0.15rem !important;
            padding-left: 0.65rem !important;
            padding-right: 0.65rem !important;
            padding-bottom: 1rem !important;
        }

        .cv-mision {
            background: linear-gradient(135deg, #0f2747 0%, #164f91 100%);
            color: white;
            border-radius: 18px;
            padding: 14px 16px 12px 16px;
            margin: 0 0 8px 0;
            box-shadow: 0 8px 20px rgba(15, 39, 71, 0.20);
        }

        .cv-mision-titulo {
            font-size: 14px;
            font-weight: 900;
            opacity: 0.90;
            margin-bottom: 4px;
        }

        .cv-mision-ubicacion {
            font-size: 17px;
            line-height: 1.25;
            font-weight: 900;
        }

        .cv-mision-texto {
            font-size: 14px;
            line-height: 1.25;
            margin-top: 4px;
            opacity: 0.96;
        }

        .cv-colegio {
            font-size: 18px;
            font-weight: 950;
            color: #0f2747;
            margin: 8px 0 4px 2px;
        }

        .cv-centro {
            font-size: 17px;
            font-weight: 950;
            color: #164f91;
            margin: 6px 0 2px 2px;
        }

        .cv-edificio {
            font-size: 15px;
            font-weight: 900;
            color: #22344d;
            margin: 5px 0 2px 3px;
        }

        /* Anula los botones gigantes definidos en app.py */
        div[data-testid="stButton"] > button {
            min-height: 42px !important;
            height: 42px !important;
            padding: 5px 11px !important;
            margin: 0 !important;
            border-radius: 12px !important;
            font-size: 14px !important;
            font-weight: 850 !important;
            box-shadow: 0 2px 7px rgba(15, 23, 42, 0.07) !important;
            white-space: nowrap !important;
        }

        div[data-testid="stButton"] {
            margin-bottom: 3px !important;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.22rem !important;
        }

        hr {
            margin: 5px 0 !important;
        }

        @media (max-width: 768px) {
            .cv-mision {
                padding: 12px 13px 10px 13px;
                border-radius: 16px;
            }

            .cv-mision-ubicacion {
                font-size: 16px;
            }

            div[data-testid="stButton"] > button {
                min-height: 40px !important;
                height: 40px !important;
                font-size: 13px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    operario = str(
        st.session_state.get("operario_activo")
        or st.session_state.get("usuario")
        or ""
    ).strip()

    colegio = obtener_colegio_vivo(operario)
    ordenes = _ordenar_misiones(_todas_las_ordenes(colegio))

    # =====================================================
    # MISIÓN: SIEMPRE LO PRIMERO
    # =====================================================
    if ordenes:
        mision = ordenes[0]

        centro = mision.get("_centro_vivo", "")
        edificio = mision.get("_edificio_vivo", "")
        planta = mision.get("_planta_vivo", "")
        averia = _texto_averia(mision)
        prioridad = str(mision.get("prioridad") or "").strip()

        st.markdown(
            f"""
            <div class="cv-mision">
                <div class="cv-mision-titulo">❤️ MI MISIÓN · {prioridad.upper()}</div>
                <div class="cv-mision-ubicacion">
                    {centro} · {edificio} · {planta}
                </div>
                <div class="cv-mision-texto">{averia}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "▶ EMPEZAR AHORA",
            key=f"cv_empezar_{mision.get('id', 'primera')}",
            type="primary",
            use_container_width=True,
        ):
            _guardar_ot_seleccionada(mision)
            st.rerun()

    else:
        st.success("✅ No tienes órdenes ejecutables.")

    # =====================================================
    # COLEGIO VIVO
    # =====================================================
    st.markdown(
        '<div class="cv-colegio">🏫 COLEGIO VIVO</div>',
        unsafe_allow_html=True,
    )

    if not colegio:
        st.info("No hay trabajo ejecutable asignado.")
        return

    for centro in colegio:
        nombre_centro = centro.get("centro", "Centro")

        st.markdown(
            f'<div class="cv-centro">{nombre_centro}</div>',
            unsafe_allow_html=True,
        )

        for edificio in centro.get("edificios", []):
            nombre_edificio = edificio.get("nombre", "Edificio")

            st.markdown(
                f'<div class="cv-edificio">{nombre_edificio}</div>',
                unsafe_allow_html=True,
            )

            plantas = edificio.get("plantas", [])

            if not plantas:
                st.caption("Sin órdenes ejecutables.")
                continue

            # Dos plantas por fila para evitar scroll
            for inicio in range(0, len(plantas), 2):
                pareja = plantas[inicio:inicio + 2]
                columnas = st.columns(2)

                for columna, planta in zip(columnas, pareja):
                    nombre_planta = planta.get("nombre", "Planta")
                    total = int(planta.get("total") or 0)
                    color = planta.get("color", "🟢")

                    texto = (
                        f"{color} {nombre_planta}"
                        if total == 0
                        else f"{color} {nombre_planta} · {total}"
                    )

                    clave = (
                        f"cv_{nombre_centro}_"
                        f"{nombre_edificio}_"
                        f"{nombre_planta}"
                    )

                    with columna:
                        if st.button(
                            texto,
                            key=clave,
                            use_container_width=True,
                        ):
                            st.session_state["colegio_vivo_planta"] = planta
                            st.session_state["colegio_vivo_centro"] = nombre_centro
                            st.session_state["colegio_vivo_edificio"] = nombre_edificio
                            st.rerun()
