import streamlit as st

from modules.espacios import (
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)

from modules.cuadros_electricos import (
    asegurar_tablas_cuadros_electricos,
    crear_cuadro_electrico,
    obtener_cuadros_electricos,
    actualizar_cuadro_electrico,
    activar_desactivar_cuadro,
    obtener_mecanismos_cuadro,
    crear_mecanismo_cuadro,
    actualizar_mecanismo_cuadro,
    eliminar_mecanismo_cuadro,
)


MECANISMOS_SUGERIDOS = [
    "Magnetotérmico",
    "Diferencial",
    "Contactor",
    "Relé",
    "Temporizador",
    "Protector sobretensiones",
    "Fuente de alimentación",
    "Transformador",
    "Interruptor-seccionador",
    "Guardamotor",
    "Otro",
]


def _indice(opciones, valor):
    valor = str(valor or "").strip()

    if valor in opciones:
        return opciones.index(valor)

    return 0


def _obtener_nombres_espacios(
    centro,
    edificio,
    planta,
):
    datos = obtener_espacios_por_planta(
        centro,
        edificio,
        planta,
    )

    espacios = []

    for fila in datos:
        if isinstance(fila, dict):
            nombre = str(
                fila.get("espacio")
                or fila.get("nombre")
                or ""
            ).strip()
        elif isinstance(fila, (tuple, list)):
            nombre = str(
                fila[0] if fila else ""
            ).strip()
        else:
            nombre = str(
                fila or ""
            ).strip()

        if nombre and nombre not in espacios:
            espacios.append(nombre)

    return espacios


def _selector_ubicacion(
    prefijo,
    centro_actual="",
    edificio_actual="",
    planta_actual="",
    espacio_actual="",
):
    centros = obtener_centros_espacios()

    if not centros:
        st.warning(
            "No hay centros disponibles en el catálogo de espacios."
        )
        return None

    centro = st.selectbox(
        "Centro",
        centros,
        index=_indice(
            centros,
            centro_actual,
        ),
        key=f"{prefijo}_centro",
    )

    edificios = obtener_edificios_espacios(
        centro
    )

    if not edificios:
        st.warning(
            "No hay edificios configurados para este centro."
        )
        return None

    edificio = st.selectbox(
        "Edificio",
        edificios,
        index=_indice(
            edificios,
            edificio_actual,
        ),
        key=f"{prefijo}_edificio",
    )

    plantas = obtener_plantas_espacios(
        centro,
        edificio,
    )

    if (
        planta_actual
        and planta_actual not in plantas
    ):
        plantas.append(
            planta_actual
        )

    if not plantas:
        st.warning(
            "No hay plantas configuradas para este edificio."
        )
        return None

    planta = st.selectbox(
        "Planta",
        plantas,
        index=_indice(
            plantas,
            planta_actual,
        ),
        key=f"{prefijo}_planta",
    )

    espacios = _obtener_nombres_espacios(
        centro,
        edificio,
        planta,
    )

    if (
        espacio_actual
        and espacio_actual not in espacios
    ):
        espacios.append(
            espacio_actual
        )

    if not espacios:
        espacios = [
            "Sala técnica / Instalaciones"
        ]

    espacio = st.selectbox(
        "Ubicación / espacio",
        espacios,
        index=_indice(
            espacios,
            espacio_actual,
        ),
        key=f"{prefijo}_espacio",
    )

    return (
        centro,
        edificio,
        planta,
        espacio,
    )


def _mostrar_inventario_mecanismos(
    id_cuadro,
    codigo,
):
    st.markdown(
        "#### 📦 Inventario técnico de mecanismos"
    )

    mecanismos = obtener_mecanismos_cuadro(
        id_cuadro
    )

    if not mecanismos:
        st.info(
            "Este cuadro todavía no tiene mecanismos inventariados."
        )

    else:
        total_unidades = sum(
            int(fila[4] or 0)
            for fila in mecanismos
        )

        c1, c2 = st.columns(2)

        c1.metric(
            "Tipos / líneas",
            len(mecanismos),
        )

        c2.metric(
            "Unidades",
            total_unidades,
        )

        for fila in mecanismos:
            (
                id_mecanismo,
                cuadro_id,
                mecanismo,
                caracteristicas,
                cantidad,
                circuito,
                fabricante,
                modelo,
                observaciones,
                activo,
                fecha_creacion,
                fecha_actualizacion,
                identificador,
            ) = fila

            detalle = str(
                caracteristicas or ""
            ).strip()

            identificador_txt = str(
                identificador or ""
            ).strip()

            titulo = (
                f"⚡ "
                f"{identificador_txt + ' · ' if identificador_txt else ''}"
                f"{mecanismo or '-'}"
                f"{' · ' + detalle if detalle else ''}"
                f" · {int(cantidad or 0)} uds"
            )

            with st.expander(
                titulo,
                expanded=False,
            ):
                identificador_nuevo = st.text_input(
                    "Identificador / posición",
                    value=str(
                        identificador or ""
                    ),
                    placeholder="Ej.: Q1, Q2, ID1, KM1...",
                    key=(
                        f"cfg_cuadro_mec_id_"
                        f"{id_mecanismo}"
                    ),
                    help=(
                        "Referencia visible o lógica dentro del cuadro. "
                        "Puede dejarse vacía si todavía no está identificada."
                    ),
                )

                mecanismo_nuevo = st.text_input(
                    "Mecanismo",
                    value=str(
                        mecanismo or ""
                    ),
                    key=(
                        f"cfg_cuadro_mec_nombre_"
                        f"{id_mecanismo}"
                    ),
                )

                caracteristicas_nuevas = st.text_input(
                    "Características",
                    value=str(
                        caracteristicas or ""
                    ),
                    placeholder=(
                        "Ej.: 16 A · curva C · 1P+N"
                    ),
                    key=(
                        f"cfg_cuadro_mec_carac_"
                        f"{id_mecanismo}"
                    ),
                )

                cantidad_nueva = st.number_input(
                    "Cantidad",
                    min_value=1,
                    step=1,
                    value=max(
                        1,
                        int(cantidad or 1),
                    ),
                    key=(
                        f"cfg_cuadro_mec_cantidad_"
                        f"{id_mecanismo}"
                    ),
                )

                circuito_nuevo = st.text_input(
                    "Circuito / qué alimenta",
                    value=str(
                        circuito or ""
                    ),
                    placeholder=(
                        "Ej.: Alumbrado planta 2"
                    ),
                    key=(
                        f"cfg_cuadro_mec_circuito_"
                        f"{id_mecanismo}"
                    ),
                )

                mc1, mc2 = st.columns(2)

                with mc1:
                    fabricante_nuevo = st.text_input(
                        "Fabricante",
                        value=str(
                            fabricante or ""
                        ),
                        key=(
                            f"cfg_cuadro_mec_fab_"
                            f"{id_mecanismo}"
                        ),
                    )

                with mc2:
                    modelo_nuevo = st.text_input(
                        "Modelo",
                        value=str(
                            modelo or ""
                        ),
                        key=(
                            f"cfg_cuadro_mec_modelo_"
                            f"{id_mecanismo}"
                        ),
                    )

                observaciones_nuevas = st.text_area(
                    "Observaciones",
                    value=str(
                        observaciones or ""
                    ),
                    key=(
                        f"cfg_cuadro_mec_obs_"
                        f"{id_mecanismo}"
                    ),
                )

                b1, b2 = st.columns(2)

                with b1:
                    if st.button(
                        "💾 Guardar mecanismo",
                        key=(
                            f"cfg_cuadro_mec_guardar_"
                            f"{id_mecanismo}"
                        ),
                        use_container_width=True,
                    ):
                        ok, mensaje = (
                            actualizar_mecanismo_cuadro(
                                id_mecanismo=id_mecanismo,
                                mecanismo=mecanismo_nuevo,
                                caracteristicas=(
                                    caracteristicas_nuevas
                                ),
                                cantidad=cantidad_nueva,
                                circuito=circuito_nuevo,
                                fabricante=(
                                    fabricante_nuevo
                                ),
                                modelo=modelo_nuevo,
                                observaciones=(
                                    observaciones_nuevas
                                ),
                                identificador=(
                                    identificador_nuevo
                                ),
                            )
                        )

                        if ok:
                            st.success(
                                mensaje
                            )
                            st.rerun()
                        else:
                            st.warning(
                                mensaje
                            )

                with b2:
                    confirmar_borrado = st.checkbox(
                        "Confirmar baja",
                        key=(
                            f"cfg_cuadro_mec_confirmar_"
                            f"{id_mecanismo}"
                        ),
                    )

                    if st.button(
                        "🗑️ Retirar del inventario",
                        key=(
                            f"cfg_cuadro_mec_borrar_"
                            f"{id_mecanismo}"
                        ),
                        use_container_width=True,
                    ):
                        if not confirmar_borrado:
                            st.warning(
                                "Marca primero la confirmación."
                            )
                        elif eliminar_mecanismo_cuadro(
                            id_mecanismo
                        ):
                            st.success(
                                "Mecanismo retirado del inventario."
                            )
                            st.rerun()
                        else:
                            st.error(
                                "No se pudo retirar el mecanismo."
                            )

    st.markdown("---")
    st.markdown(
        "#### ➕ Añadir mecanismo"
    )

    identificador_nuevo = st.text_input(
        "Identificador / posición",
        placeholder="Ej.: Q1, Q2, ID1, KM1...",
        key=f"cfg_cuadro_add_id_{id_cuadro}",
        help=(
            "Referencia del mecanismo dentro del cuadro. "
            "Es opcional y puede completarse más adelante."
        ),
    )

    mecanismo_sugerido = st.selectbox(
        "Tipo sugerido",
        MECANISMOS_SUGERIDOS,
        key=f"cfg_cuadro_add_tipo_{id_cuadro}",
    )

    mecanismo_nuevo = mecanismo_sugerido

    if mecanismo_sugerido == "Otro":
        mecanismo_nuevo = st.text_input(
            "Especificar mecanismo",
            key=f"cfg_cuadro_add_otro_{id_cuadro}",
        )

    caracteristicas = st.text_input(
        "Características",
        placeholder=(
            "Ej.: 16 A · curva C · 1P+N"
        ),
        key=f"cfg_cuadro_add_carac_{id_cuadro}",
    )

    cantidad = st.number_input(
        "Cantidad",
        min_value=1,
        step=1,
        value=1,
        key=f"cfg_cuadro_add_cantidad_{id_cuadro}",
    )

    circuito = st.text_input(
        "Circuito / qué alimenta",
        placeholder=(
            "Ej.: Alumbrado aulas planta 2"
        ),
        key=f"cfg_cuadro_add_circuito_{id_cuadro}",
    )

    ac1, ac2 = st.columns(2)

    with ac1:
        fabricante = st.text_input(
            "Fabricante",
            key=f"cfg_cuadro_add_fab_{id_cuadro}",
        )

    with ac2:
        modelo = st.text_input(
            "Modelo",
            key=f"cfg_cuadro_add_modelo_{id_cuadro}",
        )

    observaciones = st.text_area(
        "Observaciones",
        key=f"cfg_cuadro_add_obs_{id_cuadro}",
    )

    if st.button(
        "➕ Añadir al cuadro",
        key=f"cfg_cuadro_add_guardar_{id_cuadro}",
        use_container_width=True,
        type="primary",
    ):
        ok, mensaje = crear_mecanismo_cuadro(
            cuadro_id=id_cuadro,
            mecanismo=mecanismo_nuevo,
            caracteristicas=caracteristicas,
            cantidad=cantidad,
            circuito=circuito,
            fabricante=fabricante,
            modelo=modelo,
            observaciones=observaciones,
            identificador=identificador_nuevo,
        )

        if ok:
            st.success(
                mensaje
            )
            st.rerun()
        else:
            st.warning(
                mensaje
            )


def pantalla_cuadros_electricos():
    asegurar_tablas_cuadros_electricos()

    st.markdown(
        "### ⚡ Cuadros eléctricos"
    )

    st.info(
        "Cada cuadro tiene su propia ficha y su inventario técnico "
        "de mecanismos. Aquí solo construimos la base técnica; "
        "el preventivo se conectará después."
    )

    seccion = st.radio(
        "Gestión de cuadros",
        [
            "➕ Crear cuadro",
            "📋 Cuadros existentes",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="cfg_cuadros_seccion",
    )

    if seccion == "➕ Crear cuadro":
        st.markdown(
            "#### ➕ Alta de cuadro eléctrico"
        )

        ubicacion = _selector_ubicacion(
            "cfg_cuadro_nuevo"
        )

        if not ubicacion:
            return

        (
            centro,
            edificio,
            planta,
            espacio,
        ) = ubicacion

        c1, c2 = st.columns(2)

        with c1:
            codigo = st.text_input(
                "Referencia / código",
                placeholder=(
                    "Ej.: QGBT-01, QS-P5-01"
                ),
                key="cfg_cuadro_nuevo_codigo",
            )

        with c2:
            nombre = st.text_input(
                "Nombre",
                placeholder=(
                    "Ej.: Cuadro general planta 5"
                ),
                key="cfg_cuadro_nuevo_nombre",
            )

        c3, c4 = st.columns(2)

        with c3:
            fabricante = st.text_input(
                "Fabricante",
                key="cfg_cuadro_nuevo_fabricante",
            )

        with c4:
            modelo = st.text_input(
                "Modelo",
                key="cfg_cuadro_nuevo_modelo",
            )

        observaciones = st.text_area(
            "Observaciones",
            key="cfg_cuadro_nuevo_observaciones",
        )

        if st.button(
            "💾 Crear cuadro eléctrico",
            key="cfg_cuadro_nuevo_guardar",
            use_container_width=True,
            type="primary",
        ):
            ok, mensaje = crear_cuadro_electrico(
                codigo=codigo,
                nombre=nombre,
                centro=centro,
                edificio=edificio,
                planta=planta,
                espacio=espacio,
                fabricante=fabricante,
                modelo=modelo,
                observaciones=observaciones,
            )

            if ok:
                st.success(
                    mensaje
                )
                st.rerun()
            else:
                st.warning(
                    mensaje
                )

        return

    cuadros = obtener_cuadros_electricos(
        solo_activos=False
    )

    if not cuadros:
        st.info(
            "Todavía no hay cuadros eléctricos registrados."
        )
        return

    activos = sum(
        1
        for fila in cuadros
        if bool(fila[10])
    )

    m1, m2 = st.columns(2)

    m1.metric(
        "Cuadros registrados",
        len(cuadros),
    )

    m2.metric(
        "Activos",
        activos,
    )

    buscar = st.text_input(
        "🔎 Buscar cuadro",
        placeholder=(
            "Referencia, nombre, planta, espacio..."
        ),
        key="cfg_cuadros_buscar",
    ).strip().lower()

    for fila in cuadros:
        (
            id_cuadro,
            codigo,
            nombre,
            centro,
            edificio,
            planta,
            espacio,
            fabricante,
            modelo,
            observaciones,
            activo,
            fecha_creacion,
            fecha_actualizacion,
        ) = fila

        texto_busqueda = (
            f"{codigo} {nombre} {centro} {edificio} "
            f"{planta} {espacio} {fabricante} {modelo}"
        ).lower()

        if (
            buscar
            and buscar not in texto_busqueda
        ):
            continue

        icono = "✅" if activo else "⛔"

        with st.expander(
            (
                f"{icono} ⚡ {codigo} · {nombre} · "
                f"{centro} · {planta} · {espacio}"
            ),
            expanded=False,
        ):
            ubicacion = _selector_ubicacion(
                f"cfg_cuadro_edit_{id_cuadro}",
                centro_actual=centro,
                edificio_actual=edificio,
                planta_actual=planta,
                espacio_actual=espacio,
            )

            if not ubicacion:
                continue

            (
                centro_nuevo,
                edificio_nuevo,
                planta_nueva,
                espacio_nuevo,
            ) = ubicacion

            e1, e2 = st.columns(2)

            with e1:
                codigo_nuevo = st.text_input(
                    "Referencia / código",
                    value=str(
                        codigo or ""
                    ),
                    key=(
                        f"cfg_cuadro_edit_codigo_"
                        f"{id_cuadro}"
                    ),
                )

            with e2:
                nombre_nuevo = st.text_input(
                    "Nombre",
                    value=str(
                        nombre or ""
                    ),
                    key=(
                        f"cfg_cuadro_edit_nombre_"
                        f"{id_cuadro}"
                    ),
                )

            e3, e4 = st.columns(2)

            with e3:
                fabricante_nuevo = st.text_input(
                    "Fabricante",
                    value=str(
                        fabricante or ""
                    ),
                    key=(
                        f"cfg_cuadro_edit_fab_"
                        f"{id_cuadro}"
                    ),
                )

            with e4:
                modelo_nuevo = st.text_input(
                    "Modelo",
                    value=str(
                        modelo or ""
                    ),
                    key=(
                        f"cfg_cuadro_edit_modelo_"
                        f"{id_cuadro}"
                    ),
                )

            observaciones_nuevas = st.text_area(
                "Observaciones",
                value=str(
                    observaciones or ""
                ),
                key=(
                    f"cfg_cuadro_edit_obs_"
                    f"{id_cuadro}"
                ),
            )

            g1, g2 = st.columns(2)

            with g1:
                if st.button(
                    "💾 Guardar ficha",
                    key=(
                        f"cfg_cuadro_guardar_"
                        f"{id_cuadro}"
                    ),
                    use_container_width=True,
                ):
                    ok, mensaje = (
                        actualizar_cuadro_electrico(
                            id_cuadro=id_cuadro,
                            codigo=codigo_nuevo,
                            nombre=nombre_nuevo,
                            centro=centro_nuevo,
                            edificio=edificio_nuevo,
                            planta=planta_nueva,
                            espacio=espacio_nuevo,
                            fabricante=fabricante_nuevo,
                            modelo=modelo_nuevo,
                            observaciones=(
                                observaciones_nuevas
                            ),
                        )
                    )

                    if ok:
                        st.success(
                            mensaje
                        )
                        st.rerun()
                    else:
                        st.warning(
                            mensaje
                        )

            with g2:
                if activo:
                    texto_estado = "⛔ Desactivar cuadro"
                    nuevo_estado = 0
                else:
                    texto_estado = "✅ Activar cuadro"
                    nuevo_estado = 1

                if st.button(
                    texto_estado,
                    key=(
                        f"cfg_cuadro_estado_"
                        f"{id_cuadro}"
                    ),
                    use_container_width=True,
                ):
                    if activar_desactivar_cuadro(
                        id_cuadro,
                        nuevo_estado,
                    ):
                        st.rerun()

            st.markdown("---")

            _mostrar_inventario_mecanismos(
                id_cuadro=id_cuadro,
                codigo=codigo,
            )
