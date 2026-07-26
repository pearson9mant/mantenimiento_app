import streamlit as st

from modules.colegio import (
    obtener_estado_espacio,
    icono_estado_espacio,
    obtener_centros_visibles_usuario,
)

from ui.ui_arbol_colegio_v2 import mostrar_arbol_colegio
from ui.ui_ot import mostrar_tarjeta_ot
from ui.ui_inventario_espacio import mostrar_inventario_espacio

from modules.inventario import obtener_materiales_para_select

from modules.inteligencia import (
    diagnosticar_espacio,
    obtener_mapa_actividad,
)

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


def _abrir_ficha_desde_colegio(
    centro,
    edificio,
    planta,
    espacio,
    bloque="resumen"
):
    st.session_state["colegio_ficha_seleccionada"] = {
        "centro": centro,
        "edificio": edificio,
        "planta": planta,
        "espacio": espacio,
    }

    clave = _clave_ficha(
        centro,
        edificio,
        planta,
        espacio
    )

    st.session_state[f"bloque_ficha_{clave}"] = (
        bloque or "resumen"
    )

    st.rerun()


def _obtener_centros_visibles():
    try:
        centros = obtener_centros_espacios()
    except Exception:
        centros = []

    try:
        centros_visibles = obtener_centros_visibles_usuario()
    except Exception:
        centros_visibles = []

    return [
        centro
        for centro in centros
        if centro in centros_visibles
    ]


def _mostrar_selector_rapido(
    centros,
    modo,
    permitir_abrir_ficha=True,
    mostrar_inventario_directo=True,
):
    """
    Selector secundario para localizar directamente un espacio.

    En la vista Explorar colegio se muestra dentro de un expander,
    por lo que no compite visualmente con el árbol.
    """
    centro = st.selectbox(
        "🏢 Centro",
        centros,
        key=f"colegio_rapido_centro_{modo}"
    )

    try:
        edificios = obtener_edificios_espacios(centro)
    except Exception:
        edificios = []

    if not edificios:
        st.info(
            "No hay edificios configurados para este centro."
        )
        return None

    edificio = st.selectbox(
        "🏫 Edificio",
        edificios,
        key=f"colegio_rapido_edificio_{modo}_{centro}"
    )

    try:
        plantas = obtener_plantas_espacios(
            centro,
            edificio
        )
    except Exception:
        plantas = []

    if not plantas:
        st.info(
            "No hay plantas en este edificio."
        )
        return None

    planta = st.selectbox(
        "📍 Planta",
        plantas,
        key=(
            f"colegio_rapido_planta_"
            f"{modo}_{centro}_{edificio}"
        )
    )

    try:
        espacios_datos = obtener_espacios_por_planta(
            centro,
            edificio,
            planta
        )
    except Exception:
        espacios_datos = []

    espacios = [
        fila[0]
        for fila in espacios_datos
        if fila and fila[0]
    ]

    if not espacios:
        st.info(
            "No hay espacios en esta planta."
        )
        return None

    espacio = st.selectbox(
        "🚪 Espacio",
        espacios,
        key=(
            f"colegio_rapido_espacio_"
            f"{modo}_{centro}_{edificio}_{planta}"
        )
    )

    seleccion = {
        "centro": centro,
        "edificio": edificio,
        "planta": planta,
        "espacio": espacio,
    }

    if not permitir_abrir_ficha:
        return seleccion

    columnas = 2 if mostrar_inventario_directo else 1
    botones = st.columns(columnas)

    with botones[0]:
        if st.button(
            "🔵 Abrir ficha del espacio",
            use_container_width=True,
            key=(
                f"abrir_ficha_espacio_"
                f"{centro}_{edificio}_{planta}_{espacio}"
            )
        ):
            _abrir_ficha_desde_colegio(
                centro,
                edificio,
                planta,
                espacio,
                "resumen"
            )

    if mostrar_inventario_directo:
        with botones[1]:
            if st.button(
                "📦 Inventario directo",
                use_container_width=True,
                key=(
                    f"inventario_directo_"
                    f"{centro}_{edificio}_{planta}_{espacio}"
                )
            ):
                _abrir_ficha_desde_colegio(
                    centro,
                    edificio,
                    planta,
                    espacio,
                    "inventario"
                )

    return seleccion


def _mostrar_hoy(centros, modo):
    """
    Vista de trabajo diario.

    Los selectores de centro y edificio se mantienen visibles porque
    delimitan el panel de actividad que se consulta.
    """
    centro = st.selectbox(
        "🏢 Centro",
        centros,
        key=f"colegio_hoy_centro_{modo}"
    )

    try:
        edificios = obtener_edificios_espacios(centro)
    except Exception:
        edificios = []

    if not edificios:
        st.info(
            "No hay edificios configurados para este centro."
        )
        return

    edificio = st.selectbox(
        "🏫 Edificio",
        edificios,
        key=f"colegio_hoy_edificio_{modo}_{centro}"
    )

    try:
        mapa_actividad = obtener_mapa_actividad(
            centro=centro,
            edificio=edificio
        )
    except Exception as error:
        st.error(
            "No se ha podido cargar la actividad del edificio."
        )
        st.exception(error)
        return

    st.markdown("### 📌 Lo importante hoy")

    st.caption(
        "Trabajos, preventivos y controles que requieren atención."
    )

    if not mapa_actividad:
        st.success(
            "🟢 No hay actividad pendiente en este edificio."
        )
        return

    total_trabajos = 0
    total_preventivos = 0
    total_legionella = 0
    total_espacios = 0

    for items in mapa_actividad.values():
        for item in items:
            actuaciones = item.get("actuaciones", []) or []
            preventivos = (
                item.get("preventivos_pendientes", [])
                or []
            )
            tiene_legionella = bool(
                item.get("tiene_legionella", False)
            )

            total_trabajos += len(actuaciones)
            total_preventivos += len(preventivos)

            if tiene_legionella:
                total_legionella += 1

            if actuaciones or preventivos or tiene_legionella:
                total_espacios += 1

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Espacios", total_espacios)
    c2.metric("Trabajos", total_trabajos)
    c3.metric("Preventivos", total_preventivos)
    c4.metric("Legionella", total_legionella)

    st.markdown("---")

    for planta, items in mapa_actividad.items():
        st.markdown(f"#### 📍 {planta}")

        for item in items:
            espacio = item.get("espacio", "")
            actuaciones = item.get("actuaciones", []) or []

            preventivos_pend = (
                item.get("preventivos_pendientes", [])
                or []
            )

            legionella = item.get("legionella", {}) or {}

            tiene_legionella = bool(
                item.get("tiene_legionella", False)
            )

            # -----------------------------------------
            # OT ABIERTAS
            # -----------------------------------------
            for a in actuaciones:
                try:
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
                except Exception:
                    continue

                c_info, c_btn = st.columns([5, 1])

                with c_info:
                    st.markdown(
                        f"🔴 **{espacio}**  \n"
                        f"`{numero_ot or '-'}` · "
                        f"{prioridad or '-'} · "
                        f"{area or '-'}  \n"
                        f"{descripcion or '-'}"
                    )

                with c_btn:
                    if st.button(
                        "Abrir",
                        key=(
                            f"abrir_ot_colegio_"
                            f"{id_ot}_{numero_ot}_"
                            f"{planta}_{espacio}"
                        ),
                        use_container_width=True
                    ):
                        _abrir_ficha_desde_colegio(
                            centro,
                            edificio,
                            planta,
                            espacio,
                            "actuaciones"
                        )

            # -----------------------------------------
            # PREVENTIVOS
            # -----------------------------------------
            for p in preventivos_pend:
                try:
                    (
                        id_prev,
                        fecha_prev,
                        operario_prev,
                        estado_prev,
                        obs_prev,
                        num_prev
                    ) = p
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
                        f"🛠️ **{espacio}**  \n"
                        f"`{num_prev or '-'}` · "
                        f"{estado_prev or '-'} · "
                        f"{operario_prev or '-'}  \n"
                        f"{obs_prev or 'Preventivo pendiente'}"
                    )

                with c_btn:
                    if st.button(
                        "Abrir",
                        key=(
                            f"abrir_prev_colegio_"
                            f"{id_prev}_{planta}_{espacio}"
                        ),
                        use_container_width=True
                    ):
                        _abrir_ficha_desde_colegio(
                            centro,
                            edificio,
                            planta,
                            espacio,
                            "preventivos"
                        )

            # -----------------------------------------
            # LEGIONELLA
            # -----------------------------------------
            if tiene_legionella:
                color_leg = str(
                    legionella.get("color") or ""
                ).lower()

                estado_leg = (
                    legionella.get("estado")
                    or "Legionella"
                )

                puntos = legionella.get("puntos") or 0
                tareas = legionella.get("tareas") or 0

                inc_leg = (
                    legionella.get("incidencias_abiertas")
                    or 0
                )

                icono_leg = "🦠"

                if color_leg == "rojo":
                    icono_leg = "🔴🦠"
                elif color_leg in ["amarillo", "naranja"]:
                    icono_leg = "🟠🦠"

                c_info, c_btn = st.columns([5, 1])

                with c_info:
                    st.markdown(
                        f"{icono_leg} **{espacio}**  \n"
                        f"{estado_leg} · "
                        f"{puntos} puntos · "
                        f"{tareas} tareas · "
                        f"{inc_leg} incidencias"
                    )

                with c_btn:
                    if st.button(
                        "Abrir",
                        key=(
                            f"abrir_leg_colegio_"
                            f"{planta}_{espacio}"
                        ),
                        use_container_width=True
                    ):
                        _abrir_ficha_desde_colegio(
                            centro,
                            edificio,
                            planta,
                            espacio,
                            "legionella"
                        )


def _mostrar_explorador_colegio(centros, modo):
    """
    El árbol es el navegador principal.

    Si existe una ficha seleccionada, se muestra únicamente la ficha.
    Al volver, Streamlit conserva el estado de los expanders del árbol
    mediante sus claves de session_state.
    """
    ficha = st.session_state.get(
        "colegio_ficha_seleccionada"
    )

    if ficha:
        ficha_espacio_basica(
            centro=ficha["centro"],
            edificio=ficha["edificio"],
            planta=ficha["planta"],
            espacio=ficha["espacio"],
        )
        return

    st.markdown("### 🌳 Explorar colegio")

    st.caption(
        "Navega por centro, edificio, planta y espacio."
    )

    mostrar_arbol_colegio()

    st.markdown("---")

    with st.expander(
        "🔎 Ir directamente a un espacio",
        expanded=False
    ):
        st.caption(
            "Usa esta selección solamente cuando quieras "
            "localizar un espacio sin recorrer el árbol."
        )

        _mostrar_selector_rapido(
            centros=centros,
            modo=f"explorar_{modo}",
            permitir_abrir_ficha=True,
            mostrar_inventario_directo=True,
        )


def _mostrar_inventario_espacios(centros, modo):
    seleccion = _mostrar_selector_rapido(
        centros=centros,
        modo=modo,
        permitir_abrir_ficha=False,
        mostrar_inventario_directo=False,
    )

    if not seleccion:
        return

    centro = seleccion["centro"]
    edificio = seleccion["edificio"]
    planta = seleccion["planta"]
    espacio = seleccion["espacio"]

    st.markdown("---")
    st.markdown(f"### 📦 {espacio}")
    st.caption(f"{centro} · {edificio} · {planta}")

    try:
        mostrar_inventario_espacio(
            centro=centro,
            edificio=edificio,
            planta=planta,
            espacio=espacio
        )
    except Exception as error:
        st.error(
            "No se ha podido cargar el inventario "
            "de este espacio."
        )
        st.exception(error)


def pantalla_colegio(modo="completo"):
    solo_inventario = (
        str(modo or "").strip().lower()
        == "inventario"
    )

    centros = _obtener_centros_visibles()

    if not centros:
        st.info(
            "No hay centros visibles para este usuario."
        )
        return

    # =====================================================
    # MODO INVENTARIO DE ESPACIOS
    # =====================================================
    if solo_inventario:
        st.markdown("## 🧾 Inventario de espacios")

        st.caption(
            "Selecciona un espacio para revisar, añadir, editar "
            "o eliminar elementos de su inventario."
        )

        _mostrar_inventario_espacios(
            centros=centros,
            modo=modo
        )
        return

    # =====================================================
    # MODO COMPLETO DEL COLEGIO
    # =====================================================
    st.markdown("## 🏫 Colegio")

    st.caption(
        "Qué necesita hoy el colegio y dónde se encuentra."
    )

    vista_colegio = st.radio(
        "Vista",
        options=[
            "📌 Hoy",
            "🌳 Explorar colegio",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="colegio_vista_principal"
    )

    if vista_colegio == "📌 Hoy":
        # Si se abrió una ficha desde Hoy, la mostramos sin cargar
        # de nuevo el mapa de actividad.
        ficha = st.session_state.get(
            "colegio_ficha_seleccionada"
        )

        if ficha:
            ficha_espacio_basica(
                centro=ficha["centro"],
                edificio=ficha["edificio"],
                planta=ficha["planta"],
                espacio=ficha["espacio"],
            )
            return

        _mostrar_hoy(
            centros=centros,
            modo=modo
        )
        return

    _mostrar_explorador_colegio(
        centros=centros,
        modo=modo
    )




def ficha_espacio_basica(
    centro,
    edificio,
    planta,
    espacio
):
    clave = _clave_ficha(
        centro,
        edificio,
        planta,
        espacio
    )

    # =====================================================
    # CABECERA LIGERA
    # =====================================================
    estado = obtener_estado_espacio(
        centro,
        edificio,
        espacio
    )

    icono = icono_estado_espacio(estado)

    cabecera, cerrar = st.columns([6, 1])

    with cabecera:
        st.markdown(
            f"## {icono} {espacio}"
        )

        st.caption(
            f"🏢 {centro} · 🏫 {edificio} · 📍 {planta}"
        )

    with cerrar:
        if st.button(
            "← Volver",
            key=f"cerrar_ficha_superior_{clave}",
            use_container_width=True
        ):
            st.session_state[
                "colegio_ficha_seleccionada"
            ] = None

            st.session_state[
                f"bloque_ficha_{clave}"
            ] = "resumen"

            st.rerun()

    # =====================================================
    # BLOQUE ACTIVO
    # =====================================================
    clave_bloque = f"bloque_ficha_{clave}"

    bloque_actual = st.session_state.get(
        clave_bloque,
        "resumen"
    )

    if not bloque_actual:
        bloque_actual = "resumen"

    opciones = {
        "📊 Resumen": "resumen",
        "🔧 Actuaciones": "actuaciones",
        "📦 Inventario": "inventario",
        "📅 Preventivos": "preventivos",
        "🦠 Legionella": "legionella",
        "📚 Historial": "historial",
    }

    etiqueta_actual = next(
        (
            etiqueta
            for etiqueta, valor in opciones.items()
            if valor == bloque_actual
        ),
        "📊 Resumen"
    )

    # Navegación horizontal con apariencia de pestañas.
    # Solo se ejecutará el bloque seleccionado.
    etiqueta_seleccionada = st.radio(
        "Secciones de la ficha",
        options=list(opciones.keys()),
        index=list(opciones.keys()).index(
            etiqueta_actual
        ),
        horizontal=True,
        label_visibility="collapsed",
        key=f"navegacion_ficha_{clave}"
    )

    bloque_seleccionado = opciones[
        etiqueta_seleccionada
    ]

    if bloque_seleccionado != bloque_actual:
        st.session_state[
            clave_bloque
        ] = bloque_seleccionado

        st.rerun()

    bloque = bloque_seleccionado

    st.markdown("---")

    # =====================================================
    # RESUMEN
    # Es el único bloque que se carga inicialmente.
    # =====================================================
    if bloque == "resumen":
        try:
            info = diagnosticar_espacio(
                centro=centro,
                edificio=edificio,
                espacio=espacio
            )

        except Exception as error:
            st.error(
                "No se ha podido calcular el estado "
                "del espacio."
            )

            st.exception(error)
            info = {}

        color = str(
            info.get("color") or estado or "verde"
        ).strip().lower()

        estado_texto = str(
            info.get("estado")
            or "Estado sin determinar"
        )

        if color == "verde":
            st.success(
                f"🟢 {estado_texto}"
            )

        elif color in ["amarillo", "naranja"]:
            st.warning(
                f"🟠 {estado_texto}"
            )

        else:
            st.error(
                f"🔴 {estado_texto}"
            )

        # ---------------------------------------------
        # INDICADORES PRINCIPALES
        # ---------------------------------------------
        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Trabajos",
            info.get("trabajos", 0)
        )

        c2.metric(
            "Activos",
            info.get("activos", 0)
        )

        c3.metric(
            "Dañados",
            info.get("danados", 0)
        )

        c4.metric(
            "Correctivos",
            info.get("correctivos", 0)
        )

        st.markdown("### 🧠 Situación del espacio")

        diagnostico = info.get(
            "diagnostico",
            []
        ) or []

        if diagnostico:
            for linea in diagnostico:
                st.markdown(
                    f"• {linea}"
                )

        else:
            st.info(
                "Todavía no hay suficiente información "
                "para elaborar un diagnóstico detallado."
            )

        st.markdown(
            "### 🎯 Siguiente actuación recomendada"
        )

        recomendacion = info.get(
            "recomendacion",
            "No es necesaria ninguna actuación inmediata."
        )

        st.info(recomendacion)

        legionella = info.get(
            "legionella",
            {}
        ) or {}

        if legionella.get("aplica"):
            st.markdown(
                "### 🦠 Control sanitario"
            )

            color_leg = str(
                legionella.get("color") or ""
            ).lower()

            estado_leg = (
                legionella.get("estado")
                or "Estado sin determinar"
            )

            if color_leg == "rojo":
                st.error(
                    f"🔴 {estado_leg}"
                )

            elif color_leg in ["amarillo", "naranja"]:
                st.warning(
                    f"🟠 {estado_leg}"
                )

            else:
                st.success(
                    f"🟢 {estado_leg}"
                )

    # =====================================================
    # ACTUACIONES
    # Solo carga las OT cuando se abre esta sección.
    # =====================================================
    elif bloque == "actuaciones":
        st.markdown(
            "### 🔧 Actuaciones abiertas"
        )

        try:
            actuaciones = obtener_actuaciones_espacio(
                centro,
                edificio,
                espacio
            )

        except Exception as error:
            actuaciones = []

            st.error(
                "No se han podido cargar las actuaciones."
            )

            st.exception(error)

        if not actuaciones:
            st.success(
                "No hay trabajos abiertos en este espacio."
            )

        else:
            st.caption(
                f"{len(actuaciones)} trabajo(s) abierto(s)."
            )

            try:
                materiales_select = (
                    obtener_materiales_para_select()
                )

            except Exception:
                materiales_select = []

            for a in actuaciones:
                try:
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

                except Exception:
                    continue

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

    # =====================================================
    # INVENTARIO
    # Solo carga al entrar en esta sección.
    # =====================================================
    elif bloque == "inventario":
        st.markdown(
            "### 📦 Inventario del espacio"
        )

        try:
            mostrar_inventario_espacio(
                centro=centro,
                edificio=edificio,
                planta=planta,
                espacio=espacio
            )

        except Exception as error:
            st.error(
                "No se ha podido cargar el inventario "
                "de este espacio."
            )

            st.exception(error)

    # =====================================================
    # PREVENTIVOS
    # =====================================================
    elif bloque == "preventivos":
        st.markdown(
            "### 📅 Mantenimiento preventivo"
        )

        try:
            preventivos = obtener_preventivos_espacio(
                centro,
                edificio,
                espacio
            )

        except Exception as error:
            preventivos = []

            st.error(
                "No se han podido cargar los preventivos."
            )

            st.exception(error)

        if not preventivos:
            st.info(
                "No hay preventivos registrados "
                "en este espacio."
            )

        else:
            st.caption(
                f"{len(preventivos)} preventivo(s) registrado(s)."
            )

            for p in preventivos:
                try:
                    (
                        id_prev,
                        fecha,
                        operario,
                        estado_prev,
                        observaciones,
                        numero_ot_preventiva
                    ) = p

                except Exception:
                    continue

                estado_normalizado = str(
                    estado_prev or ""
                ).strip().lower()

                if estado_normalizado in [
                    "finalizado",
                    "finalizada",
                    "cerrado",
                    "cerrada",
                    "realizado",
                    "completado",
                ]:
                    icono_prev = "🟢"

                elif estado_normalizado in [
                    "pendiente",
                    "vencido",
                    "atrasado",
                ]:
                    icono_prev = "🔴"

                else:
                    icono_prev = "🟠"

                with st.container(border=True):
                    st.markdown(
                        f"{icono_prev} "
                        f"**{fecha or 'Sin fecha'}**"
                    )

                    st.caption(
                        f"Estado: {estado_prev or '-'} · "
                        f"Operario: {operario or '-'} · "
                        f"OT: {numero_ot_preventiva or '-'}"
                    )

                    if observaciones:
                        st.write(observaciones)

    # =====================================================
    # LEGIONELLA
    # =====================================================
    elif bloque == "legionella":
        st.markdown(
            "### 🦠 Legionella"
        )

        try:
            info = diagnosticar_espacio(
                centro=centro,
                edificio=edificio,
                espacio=espacio
            )

        except Exception as error:
            st.error(
                "No se ha podido cargar la información "
                "de Legionella."
            )

            st.exception(error)
            info = {}

        legionella = info.get(
            "legionella",
            {}
        ) or {}

        if not legionella.get("aplica"):
            st.info(
                "Este espacio no tiene controles "
                "de Legionella asociados."
            )

        else:
            color = str(
                legionella.get("color") or ""
            ).lower()

            estado_leg = (
                legionella.get("estado")
                or "Legionella"
            )

            if color == "rojo":
                st.error(
                    f"🔴 {estado_leg}"
                )

            elif color in ["amarillo", "naranja"]:
                st.warning(
                    f"🟠 {estado_leg}"
                )

            else:
                st.success(
                    f"🟢 {estado_leg}"
                )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Puntos",
                legionella.get("puntos") or 0
            )

            c2.metric(
                "Tareas",
                legionella.get("tareas") or 0
            )

            c3.metric(
                "Incidencias",
                legionella.get(
                    "incidencias_abiertas"
                ) or 0
            )

            ultimo = (
                legionella.get("ultimo_control")
                or "-"
            )

            proximo = (
                legionella.get("proximo_control")
                or "-"
            )

            st.caption(
                f"Último control: {ultimo}"
            )

            st.caption(
                f"Próximo control: {proximo}"
            )

            diagnostico_leg = (
                legionella.get("diagnostico")
                or []
            )

            recomendaciones_leg = (
                legionella.get("recomendaciones")
                or []
            )

            if diagnostico_leg:
                st.markdown(
                    "#### Diagnóstico"
                )

                for linea in diagnostico_leg:
                    st.markdown(
                        f"• {linea}"
                    )

            if recomendaciones_leg:
                st.markdown(
                    "#### Recomendaciones"
                )

                for recomendacion_leg in recomendaciones_leg:
                    st.info(recomendacion_leg)

    # =====================================================
    # HISTORIAL
    # Solo muestra los últimos 10 registros.
    # =====================================================
    elif bloque == "historial":
        st.markdown(
            "### 📚 Historial técnico"
        )

        st.caption(
            "Se muestran los últimos 10 registros "
            "para mantener la ficha ligera."
        )

        try:
            historial = obtener_historial_tecnico_espacio(
                centro,
                edificio,
                espacio
            )

        except Exception as error:
            historial = []

            st.error(
                "No se ha podido cargar el historial."
            )

            st.exception(error)

        if not historial:
            st.info(
                "No hay historial técnico registrado "
                "en este espacio."
            )

        else:
            for h in historial[:10]:
                try:
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

                except Exception:
                    continue

                with st.container(border=True):
                    st.markdown(
                        f"**{fecha or '-'}** · "
                        f"{tipo or 'Actuación'}"
                    )

                    st.caption(
                        f"{area or '-'} · "
                        f"OT {numero_ot or '-'} · "
                        f"{operario or '-'}"
                    )

                    if descripcion:
                        st.write(descripcion)

                    if observaciones:
                        st.caption(
                            f"Observaciones: {observaciones}"
                        )

    # =====================================================
    # PIE DE FICHA
    # =====================================================
    st.markdown("---")

    if st.button(
        "← Volver al colegio",
        key=f"cerrar_ficha_inferior_{clave}",
        use_container_width=True
    ):
        st.session_state[
            "colegio_ficha_seleccionada"
        ] = None

        st.session_state[
            clave_bloque
        ] = "resumen"

        st.rerun()


