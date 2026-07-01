import streamlit as st

from modules.colegio import obtener_estado_espacio, icono_estado_espacio
from ui.ui_arbol_colegio import mostrar_arbol_colegio
from ui.ui_ot import mostrar_tarjeta_ot
from ui.ui_inventario_espacio import mostrar_inventario_espacio
from modules.inventario import obtener_materiales_para_select

from modules.espacios import (
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)

from modules.ficha_espacio import (
    obtener_actuaciones_espacio,
    obtener_preventivos_espacio,
    obtener_historial_tecnico_espacio,
)


def _clave_ficha(centro, edificio, planta, espacio):
    return (
        f"{centro}_{edificio}_{planta}_{espacio}"
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def pantalla_colegio():
    st.markdown("## 🏫 Colegio")
    st.caption("Entrada rápida por centro, edificio, planta y espacio.")
    solo_incidencias = st.checkbox(
        "Mostrar solo espacios con incidencias",
        value=False,
        key="colegio_solo_incidencias"
    )

    centros = obtener_centros_espacios()

    if not centros:
        st.warning("No hay espacios configurados.")
        return

    centro = st.selectbox("🏢 Centro", centros, key="colegio_rapido_centro")

    edificios = obtener_edificios_espacios(centro)

    if not edificios:
        st.warning("No hay edificios configurados para este centro.")
        return

    edificio = st.selectbox("🏫 Edificio", edificios, key="colegio_rapido_edificio")

    plantas = obtener_plantas_espacios(centro, edificio)

    if not plantas:
        st.warning("No hay plantas configuradas para este edificio.")
        return

    planta = st.selectbox("📍 Planta", plantas, key="colegio_rapido_planta")

    espacios_datos = obtener_espacios_por_planta(centro, edificio, planta)
    espacios = [e[0] for e in espacios_datos]

    if not espacios:
        st.warning("No hay espacios configurados en esta planta.")
        return

    espacio = st.selectbox("🚪 Espacio", espacios, key="colegio_rapido_espacio")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("🔵 Abrir ficha del espacio", use_container_width=True):
            st.session_state["colegio_ficha_seleccionada"] = {
                "centro": centro,
                "edificio": edificio,
                "planta": planta,
                "espacio": espacio,
            }
            st.session_state["colegio_ver_arbol"] = False
            st.rerun()

    with c2:
        if st.button("🌳 Ver árbol del colegio", use_container_width=True):
            st.session_state["colegio_ver_arbol"] = not st.session_state.get(
                "colegio_ver_arbol",
                False
            )
            st.rerun()

    if st.session_state.get("colegio_ver_arbol", False):
        st.markdown("---")
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
    clave = _clave_ficha(centro, edificio, planta, espacio)

    estado = obtener_estado_espacio(centro, edificio, espacio)
    icono = icono_estado_espacio(estado)

    st.markdown(f"### {icono} {espacio}")
    st.caption(f"{centro} · {edificio} · {planta}")

    if st.button("❌ Cerrar ficha", key=f"cerrar_ficha_{clave}", use_container_width=True):
        st.session_state["colegio_ficha_seleccionada"] = None
        st.rerun()

    st.markdown("---")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("📌 Actuaciones", key=f"ver_actuaciones_{clave}", use_container_width=True):
            st.session_state[f"bloque_ficha_{clave}"] = "actuaciones"
            st.rerun()

        if st.button("📦 Inventario", key=f"ver_inventario_{clave}", use_container_width=True):
            st.session_state[f"bloque_ficha_{clave}"] = "inventario"
            st.rerun()

    with c2:
        if st.button("📅 Preventivos", key=f"ver_preventivos_{clave}", use_container_width=True):
            st.session_state[f"bloque_ficha_{clave}"] = "preventivos"
            st.rerun()

        if st.button("📋 Historial", key=f"ver_historial_{clave}", use_container_width=True):
            st.session_state[f"bloque_ficha_{clave}"] = "historial"
            st.rerun()

    bloque = st.session_state.get(f"bloque_ficha_{clave}", "")

    st.markdown("---")

    if bloque == "actuaciones":
        st.markdown("### 📌 Actuaciones")

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

    elif bloque == "inventario":
        st.markdown("### 📦 Inventario del espacio")
        mostrar_inventario_espacio(centro, edificio, planta, espacio)

    elif bloque == "preventivos":
        st.markdown("### 📅 Preventivos")

        preventivos = obtener_preventivos_espacio(centro, edificio, espacio)

        if not preventivos:
            st.info("No hay preventivos registrados en este espacio.")
        else:
            for p in preventivos:
                id_prev, fecha, operario, estado_prev, observaciones, numero_ot_preventiva = p
                st.markdown(f"**{fecha or '-'}** · {estado_prev or '-'} · {operario or '-'}")
                if observaciones:
                    st.caption(observaciones)

    elif bloque == "historial":
        st.markdown("### 📋 Historial técnico")

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
                    fecha_reparacion,
                ) = h

                st.markdown(
                    f"**{fecha or '-'}** · {tipo or '-'} · {area or '-'} · OT `{numero_ot or '-'}`"
                )
                st.caption(descripcion or "")

    else:
        st.info("Elige qué quieres abrir de este espacio.")



