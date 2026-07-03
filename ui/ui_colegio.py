import streamlit as st

from modules.colegio import obtener_estado_espacio, icono_estado_espacio
from modules.colegio import obtener_centros_visibles_usuario
from ui.ui_arbol_colegio import mostrar_arbol_colegio
from ui.ui_ot import mostrar_tarjeta_ot
from ui.ui_inventario_espacio import mostrar_inventario_espacio
from modules.inventario import obtener_materiales_para_select
from modules.inteligencia import diagnosticar_espacio

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


def _preventivos_pendientes(preventivos):
    pendientes = []

    for p in preventivos:
        try:
            estado = str(p[3] or "").strip().lower()
        except Exception:
            estado = ""

        if estado not in [
            "finalizado",
            "finalizada",
            "cerrado",
            "cerrada",
            "completado",
            "completada",
            "ok",
        ]:
            pendientes.append(p)

    return pendientes


def _obtener_resumen_legionella_seguro(centro, edificio, espacio):
    try:
        from ui.ui_legionella import obtener_resumen_legionella_espacio

        return obtener_resumen_legionella_espacio(
            centro,
            edificio,
            espacio
        )
    except Exception:
        return {
            "aplica": False,
            "estado": "No aplica",
            "color": "gris",
            "puntos": 0,
            "tareas": 0,
            "incidencias_abiertas": 0,
            "ultimo_control": "",
            "proximo_control": "",
            "diagnostico": [],
            "recomendaciones": [],
        }


def _legionella_relevante(resumen_legionella):
    if not resumen_legionella:
        return False

    if not resumen_legionella.get("aplica"):
        return False

    if int(resumen_legionella.get("incidencias_abiertas") or 0) > 0:
        return True

    color = str(resumen_legionella.get("color") or "").lower()

    if color in ["rojo", "amarillo"]:
        return True

    return False


def _obtener_actividad_espacio(centro, edificio, planta, espacio):
    actuaciones = obtener_actuaciones_espacio(
        centro,
        edificio,
        espacio
    )

    preventivos = obtener_preventivos_espacio(
        centro,
        edificio,
        espacio
    )

    preventivos_pend = _preventivos_pendientes(preventivos)

    legionella = _obtener_resumen_legionella_seguro(
        centro,
        edificio,
        espacio
    )

    tiene_legionella = _legionella_relevante(legionella)

    tiene_actividad = (
        len(actuaciones) > 0
        or len(preventivos_pend) > 0
        or tiene_legionella
    )

    return {
        "centro": centro,
        "edificio": edificio,
        "planta": planta,
        "espacio": espacio,
        "actuaciones": actuaciones,
        "preventivos": preventivos,
        "preventivos_pendientes": preventivos_pend,
        "legionella": legionella,
        "tiene_legionella": tiene_legionella,
        "tiene_actividad": tiene_actividad,
    }


def _obtener_actividad_edificio(centro, edificio):
    actividad = []

    for planta in obtener_plantas_espacios(centro, edificio):
        for espacio, tipo in obtener_espacios_por_planta(
            centro,
            edificio,
            planta
        ):
            item = _obtener_actividad_espacio(
                centro,
                edificio,
                planta,
                espacio
            )

            if item["tiene_actividad"]:
                actividad.append(item)

    return actividad


def _edificio_tiene_actividad(centro, edificio):
    return len(_obtener_actividad_edificio(centro, edificio)) > 0


def _centro_tiene_actividad(centro):
    for edificio in obtener_edificios_espacios(centro):
        if _edificio_tiene_actividad(centro, edificio):
            return True

    return False


def pantalla_colegio():
    st.markdown("## 🏫 Colegio")
    st.caption("Centro de control por centro, edificio, planta y espacio.")

    solo_actividad = st.checkbox(
        "Mostrar solo espacios con actividad pendiente",
        value=False,
        key="colegio_solo_incidencias"
    )

    centros = obtener_centros_espacios()
    centros_visibles = obtener_centros_visibles_usuario()

    centros = [
        c for c in centros
        if c in centros_visibles
    ]

    if solo_actividad:
        centros = [
            c for c in centros
            if _centro_tiene_actividad(c)
        ]

    if not centros:
        st.info("No hay espacios con actividad pendiente.")
        return

    centro = st.selectbox(
        "🏢 Centro",
        centros,
        key="colegio_rapido_centro"
    )

    edificios = obtener_edificios_espacios(centro)

    if solo_actividad:
        edificios = [
            e for e in edificios
            if _edificio_tiene_actividad(centro, e)
        ]

    if not edificios:
        st.info("No hay edificios con actividad pendiente en este centro.")
        return

    edificio = st.selectbox(
        "🏫 Edificio",
        edificios,
        key=f"colegio_rapido_edificio_{centro}"
    )

    # =====================================================
    # MODO CENTRO DE CONTROL
    # =====================================================
    if solo_actividad:
        actividad_edificio = _obtener_actividad_edificio(
            centro,
            edificio
        )

        if not actividad_edificio:
            st.info("No hay actividad pendiente en este edificio.")
            return

        st.markdown("### 📋 Actividad pendiente por planta")

        planta_actual = None

        for item in actividad_edificio:
            planta = item["planta"]
            espacio = item["espacio"]
            actuaciones = item["actuaciones"]
            preventivos_pend = item["preventivos_pendientes"]
            legionella = item["legionella"]
            tiene_legionella = item["tiene_legionella"]

            if planta != planta_actual:
                planta_actual = planta
                st.markdown(f"#### 📍 {planta_actual}")

            # -------------------------
            # OT ABIERTAS
            # -------------------------
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
                        f"🔴 **{espacio}** · "
                        f"`{numero_ot or '-'}` · "
                        f"{prioridad or '-'} · "
                        f"{descripcion or '-'}"
                    )

                with c_btn:
                    if st.button(
                        "Abrir",
                        key=f"abrir_ot_colegio_{id_ot}_{numero_ot}_{planta}_{espacio}",
                        use_container_width=True
                    ):
                        _abrir_ficha_desde_colegio(
                            centro,
                            edificio,
                            planta,
                            espacio,
                            "actuaciones"
                        )

            # -------------------------
            # PREVENTIVOS
            # -------------------------
            for p in preventivos_pend:
                try:
                    id_prev, fecha_prev, operario_prev, estado_prev, obs_prev, num_prev = p
                except Exception:
                    id_prev = ""
                    fecha_prev = ""
                    operario_prev = ""
                    estado_prev = ""
                    obs_prev = ""
                    num_prev = ""

                c_info, c_btn = st.columns([5, 1])

                with c_info:
                    st.markdown(
                        f"🟠 **{espacio}** · Preventivo "
                        f"`{num_prev or '-'}` · "
                        f"{estado_prev or '-'} · "
                        f"{obs_prev or ''}"
                    )

                with c_btn:
                    if st.button(
                        "Abrir",
                        key=f"abrir_prev_colegio_{id_prev}_{planta}_{espacio}",
                        use_container_width=True
                    ):
                        _abrir_ficha_desde_colegio(
                            centro,
                            edificio,
                            planta,
                            espacio,
                            "preventivos"
                        )

            # -------------------------
            # LEGIONELLA
            # -------------------------
            if tiene_legionella:
                color_leg = str(legionella.get("color") or "").lower()
                estado_leg = legionella.get("estado") or "Legionella"
                puntos = legionella.get("puntos") or 0
                tareas = legionella.get("tareas") or 0
                inc_leg = legionella.get("incidencias_abiertas") or 0

                icono_leg = "🦠"
                if color_leg == "rojo":
                    icono_leg = "🔴🦠"
                elif color_leg == "amarillo":
                    icono_leg = "🟠🦠"

                c_info, c_btn = st.columns([5, 1])

                with c_info:
                    st.markdown(
                        f"{icono_leg} **{espacio}** · Legionella · "
                        f"{estado_leg} · "
                        f"{puntos} punto(s) · "
                        f"{tareas} tarea(s) · "
                        f"{inc_leg} incidencia(s)"
                    )

                with c_btn:
                    if st.button(
                        "Abrir",
                        key=f"abrir_leg_colegio_{planta}_{espacio}",
                        use_container_width=True
                    ):
                        _abrir_ficha_desde_colegio(
                            centro,
                            edificio,
                            planta,
                            espacio,
                            "legionella"
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

    espacios_datos = obtener_espacios_por_planta(
        centro,
        edificio,
        planta
    )

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
    elif info["color"] == "amarillo":
        st.warning(f"🟠 {info['estado']}")
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

        if st.button(
            "🦠 Legionella",
            key=f"ver_legionella_{clave}",
            use_container_width=True
        ):
            st.session_state[f"bloque_ficha_{clave}"] = "legionella"
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

        actuaciones = obtener_actuaciones_espacio(
            centro,
            edificio,
            espacio
        )

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

        preventivos = obtener_preventivos_espacio(
            centro,
            edificio,
            espacio
        )

        if not preventivos:
            st.info("No hay preventivos registrados en este espacio.")
        else:
            for p in preventivos:
                try:
                    id_prev, fecha, operario, estado_prev, observaciones, numero_ot_preventiva = p
                except Exception:
                    continue

                st.markdown(
                    f"**{fecha or '-'}** · "
                    f"{estado_prev or '-'} · "
                    f"{operario or '-'} · "
                    f"OT `{numero_ot_preventiva or '-'}`"
                )

                if observaciones:
                    st.caption(observaciones)

    elif bloque == "legionella":
        st.markdown("### 🦠 Legionella")

        legionella = _obtener_resumen_legionella_seguro(
            centro,
            edificio,
            espacio
        )

        if not legionella.get("aplica"):
            st.info("Este espacio no tiene controles de Legionella asociados.")
        else:
            color = str(legionella.get("color") or "").lower()
            estado_leg = legionella.get("estado") or "Legionella"

            if color == "rojo":
                st.error(f"🔴 {estado_leg}")
            elif color == "amarillo":
                st.warning(f"🟠 {estado_leg}")
            else:
                st.success(f"🟢 {estado_leg}")

            c1, c2, c3 = st.columns(3)

            c1.metric("Puntos", legionella.get("puntos") or 0)
            c2.metric("Tareas", legionella.get("tareas") or 0)
            c3.metric("Incidencias", legionella.get("incidencias_abiertas") or 0)

            ultimo = legionella.get("ultimo_control") or "-"
            proximo = legionella.get("proximo_control") or "-"

            st.caption(f"Último control: {ultimo}")
            st.caption(f"Próximo control: {proximo}")

            diagnostico = legionella.get("diagnostico") or []
            recomendaciones = legionella.get("recomendaciones") or []

            if diagnostico:
                st.markdown("**Diagnóstico Legionella**")
                for d in diagnostico:
                    st.markdown(f"• {d}")

            if recomendaciones:
                st.markdown("**Recomendaciones**")
                for r in recomendaciones:
                    st.info(r)

    elif bloque == "historial":
        st.markdown("### 📋 Historial técnico")

        historial = obtener_historial_tecnico_espacio(
            centro,
            edificio,
            espacio
        )

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
                    f"**{fecha or '-'}** · "
                    f"{tipo or '-'} · "
                    f"{area or '-'} · "
                    f"OT `{numero_ot or '-'}`"
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



