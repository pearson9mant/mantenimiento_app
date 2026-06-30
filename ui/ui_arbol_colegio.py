import streamlit as st

from modules.espacios import obtener_arbol_espacios, icono_tipo_espacio
from modules.colegio import (
    icono_estado_espacio,
    obtener_centros_visibles_usuario,
    obtener_ots_abiertas_por_centro,
    obtener_estado_espacio_rapido,
    contar_ots_espacio_rapido,
)


def combinar_estados(estados):
    if "rojo" in estados:
        return "rojo"
    if "amarillo" in estados:
        return "amarillo"
    return "verde"


def estado_y_total_planta(centro, espacios, ots_abiertas):
    estados = []
    total = 0

    for item_espacio in espacios:
        nombre_espacio = item_espacio.get("espacio", "")

        estado = obtener_estado_espacio_rapido(
            centro=centro,
            espacio=nombre_espacio,
            ots_abiertas=ots_abiertas
        )

        cantidad = contar_ots_espacio_rapido(
            centro=centro,
            espacio=nombre_espacio,
            ots_abiertas=ots_abiertas
        )

        estados.append(estado)
        total += cantidad

    return combinar_estados(estados), total


def estado_y_total_edificio(centro, plantas, ots_abiertas):
    estados = []
    total = 0

    for planta, espacios in plantas.items():
        if not espacios:
            continue

        estado, cantidad = estado_y_total_planta(
            centro=centro,
            espacios=espacios,
            ots_abiertas=ots_abiertas
        )

        estados.append(estado)
        total += cantidad

    return combinar_estados(estados), total


def estado_y_total_centro(centro, edificios, ots_abiertas):
    estados = []
    total = 0

    for edificio, plantas in edificios.items():
        estado, cantidad = estado_y_total_edificio(
            centro=centro,
            plantas=plantas,
            ots_abiertas=ots_abiertas
        )

        states = estado
        estados.append(states)
        total += cantidad

    return combinar_estados(estados), total


def texto_contador(total):
    return f" ({total})" if total > 0 else ""


def mostrar_arbol_colegio():
    st.markdown("#### 🌳 Árbol del colegio")

    arbol = obtener_arbol_espacios()
    centros_visibles = obtener_centros_visibles_usuario()

    arbol = {
        centro: datos
        for centro, datos in arbol.items()
        if centro in centros_visibles
    }

    ots_abiertas = obtener_ots_abiertas_por_centro()

    hay_incidencias = False

    for centro, edificios in arbol.items():
        estado_centro, total_centro = estado_y_total_centro(
            centro=centro,
            edificios=edificios,
            ots_abiertas=ots_abiertas
        )

        # No pintamos centros sin incidencias
        if total_centro == 0:
            continue

        hay_incidencias = True
        icono_centro = icono_estado_espacio(estado_centro)

        with st.expander(
            f"{icono_centro} 🏢 {centro}{texto_contador(total_centro)}",
            expanded=True
        ):
            for edificio, plantas in edificios.items():
                estado_edificio, total_edificio = estado_y_total_edificio(
                    centro=centro,
                    plantas=plantas,
                    ots_abiertas=ots_abiertas
                )

                # No pintamos edificios sin incidencias
                if total_edificio == 0:
                    continue

                icono_edificio = icono_estado_espacio(estado_edificio)

                with st.expander(
                    f"{icono_edificio} 🏫 {edificio}{texto_contador(total_edificio)}",
                    expanded=False
                ):
                    for planta, espacios in plantas.items():
                        if not espacios:
                            continue

                        estado_planta, total_planta = estado_y_total_planta(
                            centro=centro,
                            espacios=espacios,
                            ots_abiertas=ots_abiertas
                        )

                        # No pintamos plantas sin incidencias
                        if total_planta == 0:
                            continue

                        icono_planta = icono_estado_espacio(estado_planta)

                        with st.expander(
                            f"{icono_planta} 📍 {planta}{texto_contador(total_planta)}",
                            expanded=False
                        ):
                            for item_espacio in espacios:
                                nombre_espacio = item_espacio.get("espacio", "")
                                tipo_espacio = item_espacio.get("tipo", "")

                                total_espacio = contar_ots_espacio_rapido(
                                    centro=centro,
                                    espacio=nombre_espacio,
                                    ots_abiertas=ots_abiertas
                                )

                                # No pintamos espacios sin incidencias
                                if total_espacio == 0:
                                    continue

                                estado_espacio = obtener_estado_espacio_rapido(
                                    centro=centro,
                                    espacio=nombre_espacio,
                                    ots_abiertas=ots_abiertas
                                )

                                icono_estado = icono_estado_espacio(estado_espacio)
                                icono_tipo = icono_tipo_espacio(tipo_espacio)

                                with st.expander(
                                    f"{icono_estado} {icono_tipo} {nombre_espacio}{texto_contador(total_espacio)}",
                                    expanded=False
                                ):
                                    from ui.ui_colegio import ficha_espacio_basica

                                    ficha_espacio_basica(
                                        centro=centro,
                                        edificio=edificio,
                                        planta=planta,
                                        espacio=nombre_espacio
                                    )

    if not hay_incidencias:
        st.success("No hay incidencias abiertas en tus centros.")
