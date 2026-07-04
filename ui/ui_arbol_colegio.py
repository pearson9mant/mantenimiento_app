import streamlit as st

from database.db import conectar, _sql

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


def texto_contador(total):
    return f" ({total})" if total > 0 else ""


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

        estados.append(estado)
        total += cantidad

    return combinar_estados(estados), total


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

                                if total_espacio == 0:
                                    continue

                                estado_espacio = obtener_estado_espacio_rapido(
                                    centro=centro,
                                    espacio=nombre_espacio,
                                    ots_abiertas=ots_abiertas
                                )

                                icono_estado = icono_estado_espacio(estado_espacio)
                                icono_tipo = icono_tipo_espacio(tipo_espacio)

                                if st.button(
                                    f"{icono_estado} {icono_tipo} {nombre_espacio}{texto_contador(total_espacio)}",
                                    key=f"abrir_ficha_{centro}_{edificio}_{planta}_{nombre_espacio}",
                                    use_container_width=True
                                ):
                                    st.session_state["colegio_ficha_seleccionada"] = {
                                        "centro": centro,
                                        "edificio": edificio,
                                        "planta": planta,
                                        "espacio": nombre_espacio,
                                    }
                                    st.rerun()

    if not hay_incidencias:
        st.success("No hay incidencias abiertas en tus centros.")


# =====================================================
# GERENCIA · SOLO LECTURA
# =====================================================

def _normalizar_arbol(texto):
    return (
        str(texto or "")
        .lower()
        .replace("edif.", "")
        .replace("edificio", "")
        .replace("infantil/primaria", "infantilprimaria")
        .replace("infantil / primaria", "infantilprimaria")
        .replace("llar(anexo)", "llar")
        .replace(" ", "")
        .replace("·", "")
        .replace("/", "")
        .replace("\\", "")
        .strip()
    )


def _leer_ots_abiertas_gerencia():
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                numero_ot,
                descripcion,
                estado,
                prioridad,
                centro,
                edificio,
                espacio,
                area,
                operario,
                fecha_creacion
            FROM ordenes_trabajo
            WHERE TRIM(LOWER(COALESCE(estado, ''))) NOT IN (
                'finalizada',
                'finalizado',
                'cerrado',
                'cerrada',
                'cancelada',
                'cancelado'
            )
            ORDER BY centro, edificio, espacio, id DESC
        """))

        filas = cur.fetchall()

    except Exception:
        filas = []

    conn.close()

    datos = []

    for fila in filas:
        try:
            (
                numero_ot,
                descripcion,
                estado,
                prioridad,
                centro,
                edificio,
                espacio,
                area,
                operario,
                fecha_creacion,
            ) = fila
        except Exception:
            continue

        datos.append({
            "numero_ot": str(numero_ot or "-"),
            "descripcion": str(descripcion or "-"),
            "estado": str(estado or "-"),
            "prioridad": str(prioridad or "-"),
            "centro": str(centro or ""),
            "edificio": str(edificio or ""),
            "espacio": str(espacio or ""),
            "area": str(area or "-"),
            "operario": str(operario or "-"),
            "fecha_creacion": str(fecha_creacion or "-"),
        })

    return datos


def _ots_del_espacio(ots, centro, edificio, espacio):
    centro_obj = _normalizar_arbol(centro)
    edificio_obj = _normalizar_arbol(edificio)
    espacio_obj = _normalizar_arbol(espacio)

    resultado = []

    for ot in ots:
        if _normalizar_arbol(ot.get("centro")) != centro_obj:
            continue

        edificio_ot = _normalizar_arbol(ot.get("edificio"))
        espacio_ot = _normalizar_arbol(ot.get("espacio"))

        if edificio_ot and edificio_ot != edificio_obj:
            continue

        if espacio_ot != espacio_obj:
            continue

        resultado.append(ot)

    return resultado


def _total_ots_planta(ots, centro, edificio, espacios):
    total = 0

    for item_espacio in espacios:
        total += len(
            _ots_del_espacio(
                ots=ots,
                centro=centro,
                edificio=edificio,
                espacio=item_espacio.get("espacio", "")
            )
        )

    return total


def _total_ots_edificio(ots, centro, edificio, plantas):
    total = 0

    for planta, espacios in plantas.items():
        total += _total_ots_planta(
            ots=ots,
            centro=centro,
            edificio=edificio,
            espacios=espacios
        )

    return total


def _total_ots_centro(ots, centro, edificios):
    total = 0

    for edificio, plantas in edificios.items():
        total += _total_ots_edificio(
            ots=ots,
            centro=centro,
            edificio=edificio,
            plantas=plantas
        )

    return total


def _pintar_ot_gerencia(ot):
    prioridad = str(ot.get("prioridad") or "-")
    numero = str(ot.get("numero_ot") or "-")
    descripcion = str(ot.get("descripcion") or "-")
    area = str(ot.get("area") or "-")

    icono = "🟠"

    if prioridad.lower() in ["alta", "urgente"]:
        icono = "🔴"
    elif prioridad.lower() in ["baja"]:
        icono = "🟡"

    st.markdown(
        f"{icono} `{numero}` · **{prioridad}** · {area}  \n"
        f"{descripcion}"
    )


def mostrar_arbol_gerencia():
    st.markdown("#### 📍 Incidencias por ubicación")

    arbol = obtener_arbol_espacios()
    ots = _leer_ots_abiertas_gerencia()

    if not ots:
        st.success("No hay incidencias abiertas.")
        return

    hay_incidencias = False

    for centro, edificios in arbol.items():
        total_centro = _total_ots_centro(
            ots=ots,
            centro=centro,
            edificios=edificios
        )

        if total_centro == 0:
            continue

        hay_incidencias = True

        with st.expander(
            f"🔴 🏢 {centro}{texto_contador(total_centro)}",
            expanded=True
        ):
            for edificio, plantas in edificios.items():
                total_edificio = _total_ots_edificio(
                    ots=ots,
                    centro=centro,
                    edificio=edificio,
                    plantas=plantas
                )

                if total_edificio == 0:
                    continue

                with st.expander(
                    f"🔴 🏫 {edificio}{texto_contador(total_edificio)}",
                    expanded=False
                ):
                    for planta, espacios in plantas.items():
                        if not espacios:
                            continue

                        total_planta = _total_ots_planta(
                            ots=ots,
                            centro=centro,
                            edificio=edificio,
                            espacios=espacios
                        )

                        if total_planta == 0:
                            continue

                        with st.expander(
                            f"🔴 📍 {planta}{texto_contador(total_planta)}",
                            expanded=False
                        ):
                            for item_espacio in espacios:
                                nombre_espacio = item_espacio.get("espacio", "")
                                tipo_espacio = item_espacio.get("tipo", "")

                                incidencias = _ots_del_espacio(
                                    ots=ots,
                                    centro=centro,
                                    edificio=edificio,
                                    espacio=nombre_espacio
                                )

                                if not incidencias:
                                    continue

                                icono_tipo = icono_tipo_espacio(tipo_espacio)

                                st.markdown(
                                    f"**{icono_tipo} {nombre_espacio}{texto_contador(len(incidencias))}**"
                                )

                                for ot in incidencias:
                                    _pintar_ot_gerencia(ot)

                                st.markdown("---")

    if not hay_incidencias:
        st.success("No hay incidencias abiertas vinculadas al árbol de espacios.")
