import streamlit as st

from modules.colegio import obtener_estado_espacio, icono_estado_espacio
from ui.ui_arbol_colegio import mostrar_arbol_colegio
from ui.ui_ot import mostrar_tarjeta_ot
from ui.ui_inventario_espacio import mostrar_inventario_espacio
from modules.inventario import obtener_materiales_para_select

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

    ficha = st.session_state.get("colegio_ficha_seleccionada")

    if ficha:
        st.markdown("---")

        ficha_espacio_basica(
            centro=ficha["centro"],
            edificio=ficha["edificio"],
            planta=ficha["planta"],
            espacio=ficha["espacio"],
        )


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
            materiales_select = obtener_materiales_para_select()

            for a in actuaciones:
                id_ot, numero_ot, descripcion, estado_ot, prioridad, operario, origen, area, fecha = a

                fila_ot = (
                    id_ot,
                    numero_ot,
                    descripcion,
                    estado_ot,
                    fecha,
                    centro,
                    edificio,
                    espacio,
                    area,
                    prioridad,
                    operario,
                    origen,
                    "",
                    "",
                    "",
                    "Operarios",
                    "",
                )

                mostrar_tarjeta_ot(
                    fila=fila_ot,
                    materiales_select=materiales_select,
                    operario_sel=operario or "",
                    modo="colegio"
                )

    with st.expander("📦 Inventario del espacio", expanded=False):
        mostrar_inventario_espacio(
            centro=centro,
            edificio=edificio,
            planta=planta,
            espacio=espacio
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



