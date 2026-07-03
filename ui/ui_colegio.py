import streamlit as st

from modules.colegio import obtener_estado_espacio, icono_estado_espacio
from ui.ui_arbol_colegio import mostrar_arbol_colegio
from ui.ui_ot import mostrar_tarjeta_ot
from ui.ui_inventario_espacio import mostrar_inventario_espacio
from modules.inventario import obtener_materiales_para_select
from modules.inteligencia import diagnosticar_espacio
from modules.colegio import obtener_centros_visibles_usuario

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
    obtener_cabecera_inteligente_espacio,
)


def _clave_ficha(centro, edificio, planta, espacio):
    return (
        f"{centro}_{edificio}_{planta}_{espacio}"
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def _hay_incidencia_en_espacio(centro, espacio, ots_abiertas):
    from modules.colegio import contar_ots_espacio_rapido

    return contar_ots_espacio_rapido(
        centro=centro,
        espacio=espacio,
        ots_abiertas=ots_abiertas
    ) > 0


def _obtener_trabajos_abiertos_edificio(centro, edificio):
    trabajos = []

    for planta_tmp in obtener_plantas_espacios(centro, edificio):
        for espacio_tmp, tipo_tmp in obtener_espacios_por_planta(
            centro,
            edificio,
            planta_tmp
        ):
            actuaciones = obtener_actuaciones_espacio(
                centro,
                edificio,
                espacio_tmp
            )

            for a in actuaciones:
                trabajos.append({
                    "planta": planta_tmp,
                    "espacio": espacio_tmp,
                    "actuacion": a,
                })

    return trabajos


def _abrir_ficha_desde_colegio(centro, edificio, planta, espacio, bloque="actuaciones"):
    st.session_state["colegio_ficha_seleccionada"] = {
        "centro": centro,
        "edificio": edificio,
        "planta": planta,
        "espacio": espacio,
    }

    clave = _clave_ficha(centro, edificio, planta, espacio)
    st.session_state[f"bloque_ficha_{clave}"] = bloque
    st.session_state["colegio_ver_arbol"] = False
    st.rerun()


def pantalla_colegio():
    st.markdown("## 🏫 Colegio")
    st.caption("Entrada rápida por centro, edificio, planta y espacio.")

    solo_incidencias = st.checkbox(
        "Mostrar solo espacios con incidencias",
        value=False,
        key="colegio_solo_incidencias"
    )

    ots_abiertas = None
    centros = obtener_centros_espacios()

    if solo_incidencias:
        from modules.colegio import obtener_ots_abiertas_por_centro
        ots_abiertas = obtener_ots_abiertas_por_centro()

    centros_visibles = obtener_centros_visibles_usuario()

    centros = [
        c for c in centros
        if c in centros_visibles
    ]

    if solo_incidencias:
        centros = [
            c for c in centros
            if any(
                _hay_incidencia_en_espacio(c, espacio, ots_abiertas)
                for edificio_tmp in obtener_edificios_espacios(c)
                for planta_tmp in obtener_plantas_espacios(c, edificio_tmp)
                for espacio, tipo in obtener_espacios_por_planta(c, edificio_tmp, planta_tmp)
            )
        ]

    if not centros:
        st.info("No hay espacios con incidencias abiertas.")
        return

    centro = st.selectbox(
        "🏢 Centro",
        centros,
        key="colegio_rapido_centro"
    )

    edificios = obtener_edificios_espacios(centro)

    if solo_incidencias:
        edificios = [
            e for e in edificios
            if any(
                _hay_incidencia_en_espacio(centro, espacio, ots_abiertas)
                for planta_tmp in obtener_plantas_espacios(centro, e)
                for espacio, tipo in obtener_espacios_por_planta(centro, e, planta_tmp)
            )
        ]

    if not edificios:
        st.info("No hay edificios con incidencias en este centro.")
        return

    edificio = st.selectbox(
        "🏫 Edificio",
        edificios,
        key=f"colegio_rapido_edificio_{centro}"
    )

    # =====================================================
    # MODO INCIDENCIAS: Centro -> Edificio -> Plantas -> OT
    # =====================================================
    if solo_incidencias:
        espacios_incidencias = _obtener_espacios_con_incidencias_edificio(
            centro,
            edificio,
            ots_abiertas
        )

        if not espacios_incidencias:
            st.info("No hay espacios con incidencias en este edificio.")
            return

        st.markdown("### 📋 Incidencias abiertas por planta")

        planta_actual = None

        for item in espacios_incidencias:
            planta_tmp = item["planta"]
            espacio_tmp = item["espacio"]
            actuaciones = item.get("actuaciones") or []

            if planta_tmp != planta_actual:
                planta_actual = planta_tmp
                st.markdown(f"#### 📍 {planta_actual}")

            if actuaciones:
                for a in actuaciones:
                    (
                        id_ot,
                        numero_ot,
                        descripcion,
                        estado_ot,
                        prioridad,
                        operario,
                        origen,
                        area,
                        fecha,
                    ) = a

                    c_info, c_btn = st.columns([5, 1])

                    with c_info:
                        st.markdown(
                            f"🔴 **{espacio_tmp}** · "
                            f"`{numero_ot or '-'}` · "
                            f"{prioridad or '-'} · "
                            f"{descripcion or '-'}"
                        )

                    with c_btn:
                        if st.button(
                            "Abrir",
                            key=f"abrir_ot_colegio_{id_ot}_{numero_ot}_{planta_tmp}_{espacio_tmp}",
                            use_container_width=True
                        ):
                            _abrir_ficha_desde_colegio(
                                centro,
                                edificio,
                                planta_tmp,
                                espacio_tmp,
                                "actuaciones"
                            )

            else:
                c_info, c_btn = st.columns([5, 1])

                with c_info:
                    st.markdown(
                        f"🔴 **{espacio_tmp}** · OT abierta detectada, pendiente de enlazar"
                    )

                with c_btn:
                    if st.button(
                        "Abrir",
                        key=f"abrir_espacio_sin_ot_{centro}_{edificio}_{planta_tmp}_{espacio_tmp}_{len(actuaciones)}",
                        use_container_width=True
                    ):
                        _abrir_ficha_desde_colegio(
                            centro,
                            edificio,
                            planta_tmp,
                            espacio_tmp,
                            "actuaciones"
                        )

        st.markdown("---")

        if st.button("🌳 Ver árbol", use_container_width=True):
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

        return

    # =====================================================
    # MODO NORMAL
    # =====================================================
    plantas = obtener_plantas_espacios(centro, edificio)

    if not plantas:
        st.info("No hay plantas en este edificio.")
        return

    planta = st.selectbox(
        "📍 Planta",
        plantas,
        key=f"colegio_rapido_planta_{centro}_{edificio}"
    )

    espacios_datos = obtener_espacios_por_planta(centro, edificio, planta)
    espacios = [e[0] for e in espacios_datos]

    if not espacios:
        st.info("No hay espacios en esta planta.")
        return

    espacio = st.selectbox(
        "🚪 Espacio",
        espacios,
        key=f"colegio_rapido_espacio_{centro}_{edificio}_{planta}"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("🔵 Abrir ficha del espacio", use_container_width=True):
            _abrir_ficha_desde_colegio(
                centro,
                edificio,
                planta,
                espacio,
                ""
            )

    with c2:
        if st.button("📦 Inventario directo", use_container_width=True):
            _abrir_ficha_desde_colegio(
                centro,
                edificio,
                planta,
                espacio,
                "inventario"
            )

    with c3:
        if st.button("🌳 Ver árbol", use_container_width=True):
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

    resumen = obtener_cabecera_inteligente_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio
    )

    info = diagnosticar_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio
    )

    if info["color"] == "verde":
        st.success(f"🟢 {info['estado']}")
    else:
        st.error(f"🔴 {info['estado']}")

    st.markdown("### 🧠 Asistente técnico")

    st.markdown("**Situación actual**")

    for linea in info["diagnostico"]:
        st.markdown(f"• {linea}")

    st.markdown("**Siguiente actuación**")
    st.info(info["recomendacion"])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Trabajos", info["trabajos"])
    c2.metric("Activos", info["activos"])
    c3.metric("Dañados", info["danados"])
    c4.metric("Correctivos", info["correctivos"])

    st.markdown("---")

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "📋 Trabajos del espacio",
            key=f"ver_actuaciones_{clave}",
            use_container_width=True
        ):
            st.session_state[f"bloque_ficha_{clave}"] = "actuaciones"
            st.rerun()

        if st.button(
            "📦 Inventario",
            key=f"ver_inventario_{clave}",
            use_container_width=True
        ):
            st.session_state[f"bloque_ficha_{clave}"] = "inventario"
            st.rerun()

    with c2:
        if st.button(
            "📅 Preventivos",
            key=f"ver_preventivos_{clave}",
            use_container_width=True
        ):
            st.session_state[f"bloque_ficha_{clave}"] = "preventivos"
            st.rerun()

        if st.button(
            "📋 Historial",
            key=f"ver_historial_{clave}",
            use_container_width=True
        ):
            st.session_state[f"bloque_ficha_{clave}"] = "historial"
            st.rerun()

    bloque = st.session_state.get(f"bloque_ficha_{clave}", "")

    st.markdown("---")

    if bloque == "actuaciones":
        st.markdown("### 📋 Trabajos del espacio")

        actuaciones = obtener_actuaciones_espacio(centro, edificio, espacio)

        if not actuaciones:
            st.info("No hay trabajos abiertos en este espacio.")
        else:
            materiales_select = obtener_materiales_para_select()

            for a in actuaciones:
                (
                    id_ot,
                    numero_ot,
                    descripcion,
                    estado_ot,
                    prioridad,
                    operario,
                    origen,
                    area,
                    fecha,
                ) = a

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
        mostrar_inventario_espacio(
            centro=centro,
            edificio=edificio,
            planta=planta,
            espacio=espacio
        )

    elif bloque == "preventivos":
        st.markdown("### 📅 Preventivos")

        preventivos = obtener_preventivos_espacio(centro, edificio, espacio)

        if not preventivos:
            st.info("No hay preventivos registrados en este espacio.")
        else:
            for p in preventivos:
                id_prev, fecha, operario, estado_prev, observaciones, numero_ot_preventiva = p

                st.markdown(
                    f"**{fecha or '-'}** · {estado_prev or '-'} · {operario or '-'}"
                )

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

    st.markdown("---")

    if st.button(
        "❌ Cerrar ficha",
        key=f"cerrar_ficha_{clave}",
        use_container_width=True
    ):
        st.session_state["colegio_ficha_seleccionada"] = None
        st.session_state[f"bloque_ficha_{clave}"] = ""
        st.rerun()



