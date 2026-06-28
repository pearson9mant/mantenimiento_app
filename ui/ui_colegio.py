import streamlit as st

from modules.espacios import obtener_arbol_espacios
from modules.colegio import obtener_estado_espacio, icono_estado_espacio


def ficha_espacio_basica(centro, edificio, planta, espacio):
    estado = obtener_estado_espacio(centro, edificio, espacio)
    icono = icono_estado_espacio(estado)

    st.markdown(f"### {icono} {espacio}")
    st.caption(f"{centro} · {edificio} · {planta}")

    st.markdown("---")

    with st.expander("📌 Actuaciones", expanded=False):
        st.info("Aquí aparecerán las actuaciones pendientes y finalizadas de este espacio.")

    with st.expander("📦 Inventario", expanded=False):
        st.info("Aquí aparecerá el inventario del espacio.")

    with st.expander("📅 Preventivos", expanded=False):
        st.info("Aquí aparecerán los preventivos asociados al espacio.")

    with st.expander("📋 Historial", expanded=False):
        st.info("Aquí aparecerá el historial técnico del espacio.")

    with st.expander("📸 Fotografías", expanded=False):
        st.info("Aquí aparecerán las fotografías del espacio.")


def pantalla_colegio():
    st.markdown("## 🏫 Colegio")

    st.caption(
        "Navegación por centro, edificio, planta y espacio. "
        "Todo pensado para móvil y trabajo diario."
    )

    arbol = obtener_arbol_espacios()

    if not arbol:
        st.warning("No hay espacios configurados todavía.")
        return

    for centro, edificios in arbol.items():
        with st.expander(f"🏢 {centro}", expanded=True):

            for edificio, plantas in edificios.items():
                with st.expander(f"🏫 {edificio}", expanded=False):

                    for planta, espacios in plantas.items():
                        with st.expander(f"📍 {planta}", expanded=False):

                            if not espacios:
                                st.caption("Sin espacios registrados.")
                                continue

                            for espacio in espacios:
                                estado = obtener_estado_espacio(
                                    centro,
                                    edificio,
                                    espacio
                                )
                                icono = icono_estado_espacio(estado)

                                with st.expander(
                                    f"{icono} {espacio}",
                                    expanded=False
                                ):
                                    ficha_espacio_basica(
                                        centro,
                                        edificio,
                                        planta,
                                        espacio
                                    )
