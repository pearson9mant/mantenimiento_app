import streamlit as st

from modules.espacios import obtener_arbol_espacios, icono_tipo_espacio
from modules.colegio import obtener_estado_espacio, icono_estado_espacio


def combinar_estados(estados):
    """
    Prioridad:
    rojo > amarillo > verde
    """
    if "rojo" in estados:
        return "rojo"

    if "amarillo" in estados:
        return "amarillo"

    return "verde"


def obtener_estado_planta(centro, edificio, espacios):
    estados = []

    for item_espacio in espacios:
        nombre_espacio = item_espacio.get("espacio", "")

        estado = obtener_estado_espacio(
            centro=centro,
            edificio=edificio,
            espacio=nombre_espacio
        )

        estados.append(estado)

    return combinar_estados(estados)


def obtener_estado_edificio(centro, edificio, plantas):
    estados = []

    for planta, espacios in plantas.items():
        estado_planta = obtener_estado_planta(
            centro=centro,
            edificio=edificio,
            espacios=espacios
        )

        estados.append(estado_planta)

    return combinar_estados(estados)


def obtener_estado_centro(centro, edificios):
    estados = []

    for edificio, plantas in edificios.items():
        estado_edificio = obtener_estado_edificio(
            centro=centro,
            edificio=edificio,
            plantas=plantas
        )

        estados.append(estado_edificio)

    return combinar_estados(estados)


def contar_incidencias_espacios(centro, edificio, espacios):
    total = 0

    for item_espacio in espacios:
        nombre_espacio = item_espacio.get("espacio", "")

        estado = obtener_estado_espacio(
            centro=centro,
            edificio=edificio,
            espacio=nombre_espacio
        )

        if estado == "rojo":
            total += 1

    return total


def contar_incidencias_planta(centro, edificio, plantas):
    total = 0

    for planta, espacios in plantas.items():
        total += contar_incidencias_espacios(
            centro=centro,
            edificio=edificio,
            espacios=espacios
        )

    return total


def contar_incidencias_centro(centro, edificios):
    total = 0

    for edificio, plantas in edificios.items():
        total += contar_incidencias_planta(
            centro=centro,
            edificio=edificio,
            plantas=plantas
        )

    return total


def texto_contador(total):
    if total > 0:
        return f" ({total})"

    return ""


def mostrar_arbol_colegio():
    st.markdown("#### 🌳 Árbol del colegio")

    arbol = obtener_arbol_espacios()

    for centro, edificios in arbol.items():
        estado_centro = obtener_estado_centro(
            centro=centro,
            edificios=edificios
        )

        icono_centro = icono_estado_espacio(estado_centro)

        total_centro = contar_incidencias_centro(
            centro=centro,
            edificios=edificios
        )

        with st.expander(
            f"{icono_centro} 🏢 {centro}{texto_contador(total_centro)}",
            expanded=True
        ):
            for edificio, plantas in edificios.items():
                estado_edificio = obtener_estado_edificio(
                    centro=centro,
                    edificio=edificio,
                    plantas=plantas
                )

                icono_edificio = icono_estado_espacio(estado_edificio)

                total_edificio = contar_incidencias_planta(
                    centro=centro,
                    edificio=edificio,
                    plantas=plantas
                )

                with st.expander(
                    f"{icono_edificio} 🏫 {edificio}{texto_contador(total_edificio)}",
                    expanded=False
                ):
                    for planta, espacios in plantas.items():

                        estado_planta = obtener_estado_planta(
                            centro=centro,
                            edificio=edificio,
                            espacios=espacios
                        )

                        icono_planta = icono_estado_espacio(estado_planta)

                        total_planta = contar_incidencias_espacios(
                            centro=centro,
                            edificio=edificio,
                            espacios=espacios
                        )

                        with st.expander(
                            f"{icono_planta} 📍 {planta}{texto_contador(total_planta)}",
                            expanded=False
                        ):
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
