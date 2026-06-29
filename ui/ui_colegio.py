import streamlit as st

from modules.colegio import obtener_estado_espacio, icono_estado_espacio
from ui.ui_arbol_colegio import mostrar_arbol_colegio

from modules.ficha_espacio import (
    obtener_resumen_ficha_espacio,
    obtener_actuaciones_espacio,
    obtener_inventario_espacio,
    obtener_preventivos_espacio,
    obtener_historial_tecnico_espacio,
)


def pantalla_colegio():
    st.markdown("## 🏫 Colegio")
    st.caption(
        "Navegación por centro, edificio, planta y espacio. "
        "Todo pensado para móvil y trabajo diario."
    )

    mostrar_arbol_colegio()


def ficha_espacio_basica(centro, edificio, planta, espacio):
    estado = obtener_estado_espacio(centro, edificio, espacio)
    icono = icono_estado_espacio(estado)

    resumen = obtener_resumen_ficha_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio
    )

    st.markdown(f"### {icono} {espacio}")
    st.caption(f"{centro} · {edificio} · {planta}")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Actuaciones", resumen["actuaciones_abiertas"])
    c2.metric("Inventario", resumen["inventario"])
    c3.metric("Preventivos", resumen["preventivos"])
    c4.metric("Historial", resumen["historial"])

    st.markdown("---")

    with st.expander(f"📌 Actuaciones ({resumen['actuaciones_abiertas']})", expanded=False):
        actuaciones = obtener_actuaciones_espacio(centro, edificio, espacio)

        if not actuaciones:
            st.info("No hay actuaciones abiertas en este espacio.")
        else:
            for a in actuaciones:
                id_ot, numero_ot, descripcion, estado_ot, prioridad, operario, origen, area, fecha = a

                st.markdown(
                    f"**{numero_ot or '-'}** · {estado_ot or '-'} · "
                    f"{prioridad or '-'} · {area or '-'}"
                )
                st.caption(descripcion or "")

    with st.expander(f"📦 Inventario ({resumen['inventario']})", expanded=False):
        inventario = obtener_inventario_espacio(centro, edificio, espacio)

        if not inventario:
            st.info("No hay inventario registrado en este espacio.")
        else:
            for i in inventario:
                (
                    id_inv,
                    fecha_revision,
                    elemento,
                    cantidad,
                    estado_inv,
                    ancho,
                    alto,
                    fondo,
                    unidad,
                    observaciones,
                    foto,
                    operario
                ) = i

                st.markdown(
                    f"• **{elemento or '-'}** · "
                    f"Cantidad: {cantidad or 0} · "
                    f"{estado_inv or '-'}"
                )

    with st.expander(f"📅 Preventivos ({resumen['preventivos']})", expanded=False):
        preventivos = obtener_preventivos_espacio(centro, edificio, espacio)

        if not preventivos:
            st.info("No hay preventivos registrados en este espacio.")
        else:
            for p in preventivos:
                id_prev, fecha, operario, estado_prev, observaciones, numero_ot_preventiva = p

                st.markdown(
                    f"**{fecha or '-'}** · {estado_prev or '-'} · "
                    f"{operario or '-'}"
                )

                if observaciones:
                    st.caption(observaciones)

    with st.expander(f"📋 Historial ({resumen['historial']})", expanded=False):
        historial = obtener_historial_tecnico_espacio(centro, edificio, espacio)

        if not historial:
            st.info("No hay historial técnico registrado en este espacio.")
        else:
            for h in historial[:10]:
                (
                    id_hist,
                    fecha,
                    elemento,
                    tipo,
                    numero_ot,
                    descripcion,
                    area,
                    estado_hist,
                    operario,
                    observaciones,
                    origen,
                    tipo_orden,
                    coste,
                    foto,
                    fecha_reparacion
                ) = h

                st.markdown(
                    f"**{fecha or '-'}** · "
                    f"{tipo or '-'} · "
                    f"{area or '-'} · "
                    f"OT `{numero_ot or '-'}`"
                )

                st.caption(descripcion or "")

    with st.expander("📸 Fotografías", expanded=False):
        st.info("Aquí mostraremos las fotos asociadas al espacio.")


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
