import streamlit as st

from modules.espacios import obtener_arbol_espacios, icono_tipo_espacio
from modules.colegio import obtener_estado_espacio, icono_estado_espacio


def mostrar_arbol_colegio():
    st.markdown("#### 🌳 Árbol del colegio")

    arbol = obtener_arbol_espacios()

    for centro, edificios in arbol.items():
        with st.expander(f"🏢 {centro}", expanded=True):
            for edificio, plantas in edificios.items():
                with st.expander(f"🏫 {edificio}", expanded=False):
                    for planta, espacios in plantas.items():
                        with st.expander(f"📍 {planta}", expanded=False):
                            if not espacios:
                                st.caption("Sin espacios registrados.")
                            else:
                                for item_espacio in espacios:
                                    nombre_espacio = item_espacio.get("espacio", "")
                                    tipo_espacio = item_espacio.get("tipo", "")

                                    icono_tipo = icono_tipo_espacio(tipo_espacio)

                                    estado_espacio = obtener_estado_espacio(
                                        centro=centro,
                                        edificio=edificio,
                                        espacio=nombre_espacio
                                    )

                                    icono_estado = icono_estado_espacio(estado_espacio)

                                    with st.expander(
                                        f"{icono_estado} {icono_tipo} {nombre_espacio}",
                                        expanded=False
                                    ):
                                        from ui.ui_colegio import ficha_espacio_basica

                                        ficha_espacio_basica(
                                            centro=centro,
                                            edificio=edificio,
                                            planta=planta,
                                            espacio=nombre_espacio
                                        )
