import streamlit as st
from pathlib import Path

from config import CENTROS, OPERARIOS
from modules.espacios import (
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)
from modules.preventivo_aulas import (
    crear_tablas_preventivo_aulas,
    crear_revision_aula,
    obtener_revisiones_aulas,
    obtener_items_revision_aula,
    guardar_item_revision_y_sincronizar,
    cerrar_revision_aula,
    crear_correctivos_desde_revision,
    resumen_revision_aula,
    obtener_estado_revision_general_aula,
    marcar_revision_general_aula_completada,
    crear_incidencia_desde_revision_aula,
    guardar_inventario_revision_aula,
    ESTADOS_REVISION_AULA,
)


def limpiar_nombre_archivo(texto):
    texto = str(texto or "")
    caracteres_malos = [
        "/", "\\", ":", "*", "?",
        '"', "<", ">", "|",
    ]

    for c in caracteres_malos:
        texto = texto.replace(c, "_")

    return texto.replace(" ", "_")


def guardar_foto_revision_aula(
    foto,
    revision_id,
    item_id,
    elemento,
):
    if foto is None:
        return ""

    carpeta = Path(
        "uploads/preventivo_aulas"
    )
    carpeta.mkdir(
        parents=True,
        exist_ok=True,
    )

    extension = (
        foto.name.split(".")[-1].lower()
    )

    nombre = limpiar_nombre_archivo(
        f"revision_{revision_id}_"
        f"item_{item_id}_"
        f"{elemento}.{extension}"
    )

    ruta = carpeta / nombre

    with open(ruta, "wb") as f:
        f.write(
            foto.getvalue()
        )

    return str(ruta)


def operario_por_centro(centro):
    if centro == "Pearson 9":
        return "Luis Lozano"

    if centro == "Pearson 22":
        return "J.A. Almeda"

    return (
        OPERARIOS[0]
        if OPERARIOS
        else ""
    )


def _es_item_inventariable(item):
    try:
        return (
            str(item[9] or "").strip()
            == "Elemento inventariable"
        )
    except Exception:
        return False


def _validar_cantidades(
    elemento,
    total,
    correctas,
    afectadas,
):
    total = int(total or 0)
    correctas = int(correctas or 0)
    afectadas = int(afectadas or 0)

    if total < 0 or correctas < 0 or afectadas < 0:
        return False, (
            f"{elemento}: las cantidades "
            "no pueden ser negativas."
        )

    if correctas + afectadas != total:
        return False, (
            f"{elemento}: Total ({total}) debe ser igual a "
            f"Correctas ({correctas}) + "
            f"Con incidencia ({afectadas})."
        )

    return True, ""


def pantalla_preventivo_aulas():
    crear_tablas_preventivo_aulas()

    st.subheader("🏫 Preventivo de aulas")

    st.caption(
        "Inventario vivo del aula + revisión visual y funcional general. "
        "Las anomalías generan incidencias normales."
    )

    tab1, tab2 = st.tabs([
        "➕ Nueva revisión",
        "📋 Revisiones",
    ])

    with tab1:
        centros_catalogo = obtener_centros_espacios() or []
        centros_disponibles = centros_catalogo or CENTROS

        centro = st.selectbox(
            "Centro",
            centros_disponibles,
            key="prev_aula_centro",
        )

        edificios_disponibles = (
            obtener_edificios_espacios(centro) or []
        )

        if not edificios_disponibles:
            st.warning(
                "No hay edificios registrados en el catálogo de espacios "
                "para este centro."
            )
            edificio = ""
            planta = ""
            espacio = ""
        else:
            edificio = st.selectbox(
                "Edificio",
                edificios_disponibles,
                key=f"prev_aula_edificio_{centro}",
            )

            plantas_disponibles = (
                obtener_plantas_espacios(
                    centro,
                    edificio,
                )
                or []
            )

            if not plantas_disponibles:
                st.warning(
                    "Este edificio no tiene plantas registradas en el "
                    "catálogo de espacios."
                )
                planta = ""
                espacio = ""
            else:
                planta = st.selectbox(
                    "Planta",
                    plantas_disponibles,
                    key=f"prev_aula_planta_{centro}_{edificio}",
                )

                espacios_encontrados = (
                    obtener_espacios_por_planta(
                        centro,
                        edificio,
                        planta,
                    )
                    or []
                )

                espacios_disponibles = [
                    fila[0]
                    for fila in espacios_encontrados
                    if fila and fila[0]
                ]

                if espacios_disponibles:
                    espacio_sel = st.selectbox(
                        "Aula / espacio",
                        espacios_disponibles + ["Otro"],
                        key=(
                            f"prev_aula_espacio_{centro}_"
                            f"{edificio}_{planta}"
                        ),
                    )

                    if espacio_sel == "Otro":
                        espacio = st.text_input(
                            "Especificar aula / espacio",
                            key=(
                                "prev_aula_espacio_otro_"
                                f"{centro}_{edificio}_{planta}"
                            ),
                        )
                    else:
                        espacio = espacio_sel
                else:
                    st.warning(
                        "No hay aulas o espacios registrados en esta planta."
                    )
                    espacio = ""

        operario_auto = operario_por_centro(centro)

        if operario_auto in OPERARIOS:
            indice_operario = OPERARIOS.index(operario_auto)
        else:
            indice_operario = 0

        operario_sel = st.selectbox(
            "Operario",
            OPERARIOS,
            index=indice_operario,
            key=f"prev_aula_operario_{centro}",
        )

        if operario_sel == "Otro":
            operario = st.text_input(
                "Nombre operario",
                key="prev_aula_operario_otro",
            )
        else:
            operario = operario_sel

        observaciones = st.text_area(
            "Observaciones iniciales",
            key="prev_aula_obs_iniciales",
        )

        if st.button(
            "✅ Crear revisión de aula",
            use_container_width=True,
        ):
            if not str(edificio).strip():
                st.warning(
                    "Indica un edificio válido del catálogo."
                )
            elif not str(planta).strip():
                st.warning(
                    "Indica una planta válida del catálogo."
                )
            elif not str(espacio).strip():
                st.warning(
                    "Indica un aula o espacio."
                )
            elif not str(operario).strip():
                st.warning(
                    "Indica un operario."
                )
            else:
                try:
                    revision_id = crear_revision_aula(
                        centro=centro,
                        edificio=edificio,
                        espacio=espacio,
                        operario=operario,
                        observaciones=observaciones,
                        planta=planta,
                    )
                except Exception as e:
                    st.error(
                        "No se ha podido crear la revisión de aula."
                    )
                    st.caption(str(e))
                else:
                    st.session_state[
                        "revision_aula_activa"
                    ] = revision_id
                    st.success(
                        "Revisión de aula creada correctamente."
                    )
                    st.rerun()

    with tab2:
        revisiones = obtener_revisiones_aulas(100)

        if not revisiones:
            st.info("No hay revisiones de aula.")
            return

        for rev in revisiones:
            (
                revision_id,
                fecha,
                centro,
                edificio,
                espacio,
                operario,
                estado,
                observaciones,
                numero_ot_preventiva,
                planta,
            ) = rev

            resumen = resumen_revision_aula(
                revision_id
            )

            incidencias_revision = list(
                resumen.get(
                    "incidencias_revision",
                    [],
                )
                or []
            )

            titulo = (
                f"{fecha or '-'} | "
                f"{centro} · {edificio} · {planta or '-'} · {espacio} | "
                f"{estado} | INC: {len(incidencias_revision)}"
            )

            with st.expander(titulo):
                st.markdown(
                    f"""
🏢 **Centro:** {centro}  
🏫 **Edificio:** {edificio}  
🧱 **Planta:** {planta or '-'}  
🚪 **Aula / espacio:** {espacio}  
👷 **Operario:** {operario or '-'}  
📌 **Estado:** {estado or '-'}  
🧾 **OT preventiva origen:** {numero_ot_preventiva or '-'}
"""
                )

                if observaciones:
                    st.markdown(
                        "**Observaciones iniciales:**"
                    )
                    st.write(observaciones)

                items = obtener_items_revision_aula(
                    revision_id
                )

                inventariables = [
                    item
                    for item in items
                    if _es_item_inventariable(item)
                ]

                st.markdown("### 📦 Inventario del aula")

                st.caption(
                    "El inventario se mantiene vivo. Aquí actualizas sus "
                    "cantidades; las anomalías se registran después como INC."
                )

                if not inventariables:
                    st.info(
                        "Esta revisión no tiene elementos inventariables."
                    )
                else:
                    categoria_anterior = None

                    for item in inventariables:
                        (
                            item_id,
                            _revision_id,
                            elemento,
                            estado_item,
                            obs_item,
                            foto,
                            crear_correctivo,
                            numero_ot_correctiva,
                            categoria,
                            tipo_linea,
                            pide_cantidad,
                            cantidad_total,
                            cantidad_correcta,
                            cantidad_afectada,
                            modelo_id,
                        ) = item

                        categoria = str(
                            categoria or "General"
                        ).strip()

                        if categoria != categoria_anterior:
                            st.markdown(
                                f"#### {categoria}"
                            )
                            categoria_anterior = categoria

                        st.markdown(
                            f"**📦 {elemento}**"
                        )

                        q1, q2, q3 = st.columns(3)

                        with q1:
                            st.number_input(
                                "Cantidad total",
                                min_value=0,
                                step=1,
                                value=int(cantidad_total or 0),
                                key=f"total_aula_{item_id}",
                            )

                        with q2:
                            st.number_input(
                                "Correctas",
                                min_value=0,
                                step=1,
                                value=int(cantidad_correcta or 0),
                                key=f"correctas_aula_{item_id}",
                            )

                        with q3:
                            st.number_input(
                                "Con incidencia",
                                min_value=0,
                                step=1,
                                value=int(cantidad_afectada or 0),
                                key=f"afectadas_aula_{item_id}",
                            )

                    if st.button(
                        "💾 Guardar inventario del aula",
                        key=f"guardar_inventario_aula_{revision_id}",
                        use_container_width=True,
                    ):
                        cantidades = {}
                        errores = []

                        for item in inventariables:
                            item_id = int(item[0])
                            elemento = str(item[2] or "")

                            total_nuevo = int(
                                st.session_state.get(
                                    f"total_aula_{item_id}",
                                    item[11] or 0,
                                )
                                or 0
                            )
                            correctas_nuevo = int(
                                st.session_state.get(
                                    f"correctas_aula_{item_id}",
                                    item[12] or 0,
                                )
                                or 0
                            )
                            afectadas_nuevo = int(
                                st.session_state.get(
                                    f"afectadas_aula_{item_id}",
                                    item[13] or 0,
                                )
                                or 0
                            )

                            ok, mensaje = _validar_cantidades(
                                elemento,
                                total_nuevo,
                                correctas_nuevo,
                                afectadas_nuevo,
                            )

                            if not ok:
                                errores.append(mensaje)
                            else:
                                cantidades[item_id] = (
                                    total_nuevo,
                                    correctas_nuevo,
                                    afectadas_nuevo,
                                )

                        if errores:
                            st.error(
                                "No se ha guardado el inventario porque "
                                "hay cantidades incoherentes."
                            )
                            for error in errores:
                                st.warning(error)
                        else:
                            try:
                                guardar_inventario_revision_aula(
                                    revision_id,
                                    cantidades,
                                )
                            except Exception as e:
                                st.error(
                                    "No se ha podido guardar el inventario del aula."
                                )
                                st.caption(str(e))
                            else:
                                st.success(
                                    "Inventario vivo actualizado."
                                )
                                st.rerun()

                st.markdown("---")
                st.markdown(
                    "### 👀 Revisión preventiva del aula"
                )

                st.info(
                    "Haz una revisión visual y funcional general del aula: "
                    "iluminación, mecanismos, mobiliario, puertas, ventanas, "
                    "climatización y cualquier otra anomalía visible."
                )

                estado_general = obtener_estado_revision_general_aula(
                    revision_id
                )

                incidencias_creadas = list(
                    estado_general.get(
                        "incidencias",
                        [],
                    )
                    or []
                )

                if incidencias_creadas:
                    st.success(
                        "Incidencias creadas: "
                        + ", ".join(incidencias_creadas)
                    )

                if estado_general.get("completada"):
                    st.success(
                        "✅ Revisión preventiva registrada. "
                        "Esta revisión ya está lista para cerrar."
                    )
                elif str(estado or "").lower() != "cerrada":
                    respuesta = st.radio(
                        "¿Has detectado alguna anomalía?",
                        ["No", "Sí"],
                        index=None,
                        horizontal=True,
                        key=f"prev_aula_anomalia_{revision_id}",
                    )

                    if respuesta == "No":
                        if st.button(
                            "✅ Guardar revisión sin anomalías",
                            key=f"prev_aula_sin_anomalias_{revision_id}",
                            use_container_width=True,
                            type="primary",
                        ):
                            marcar_revision_general_aula_completada(
                                revision_id,
                                True,
                            )
                            st.success(
                                "Revisión preventiva guardada."
                            )
                            st.rerun()

                    elif respuesta == "Sí":
                        st.markdown(
                            "#### 🔧 Anomalía detectada"
                        )
                        st.caption(
                            "Se creará una incidencia normal, como las del QR, "
                            "con el aula ya asignada."
                        )

                        contador = int(
                            st.session_state.get(
                                f"prev_aula_contador_{revision_id}",
                                1,
                            )
                            or 1
                        )

                        descripcion_anomalia = st.text_area(
                            "¿Qué ocurre en este espacio?",
                            placeholder=(
                                "Ej.: downlight fundido, puerta no cierra, "
                                "persiana averiada..."
                            ),
                            height=120,
                            key=(
                                f"prev_aula_desc_{revision_id}_{contador}"
                            ),
                        )

                        fotos = st.file_uploader(
                            "Añadir fotografías (opcional)",
                            type=["jpg", "jpeg", "png"],
                            accept_multiple_files=True,
                            key=(
                                f"prev_aula_fotos_{revision_id}_{contador}"
                            ),
                        )

                        if st.button(
                            "➕ Crear incidencia",
                            key=(
                                f"prev_aula_crear_inc_{revision_id}_{contador}"
                            ),
                            use_container_width=True,
                            type="primary",
                        ):
                            ok, mensaje, numero_inc = (
                                crear_incidencia_desde_revision_aula(
                                    revision_id=revision_id,
                                    descripcion=descripcion_anomalia,
                                    fotos=fotos,
                                )
                            )

                            if not ok:
                                st.error(mensaje)
                            else:
                                st.session_state[
                                    f"prev_aula_contador_{revision_id}"
                                ] = contador + 1
                                st.success(mensaje)
                                st.rerun()

                        if incidencias_creadas:
                            st.markdown("---")
                            st.caption(
                                "Puedes crear otra incidencia. Cuando no "
                                "queden más anomalías por registrar, termina "
                                "la revisión."
                            )

                            if st.button(
                                "✅ Terminar revisión preventiva",
                                key=f"prev_aula_terminar_{revision_id}",
                                use_container_width=True,
                            ):
                                marcar_revision_general_aula_completada(
                                    revision_id,
                                    True,
                                )
                                st.success(
                                    "Revisión preventiva terminada."
                                )
                                st.rerun()

                st.markdown("---")
                st.markdown("### Cierre de revisión")

                resumen = resumen_revision_aula(
                    revision_id
                )

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "📦 Unidades censadas",
                    resumen.get("unidades_total", 0),
                )
                c2.metric(
                    "✅ Unidades correctas",
                    resumen.get("unidades_correctas", 0),
                )
                c3.metric(
                    "🔧 INC creadas",
                    resumen.get(
                        "incidencias_revision_total",
                        0,
                    ),
                )

                observaciones_cierre = st.text_area(
                    "Observaciones de cierre",
                    value=observaciones or "",
                    key=f"obs_cierre_revision_aula_{revision_id}",
                )

                if str(estado or "").lower() == "cerrada":
                    st.success("✅ Revisión cerrada.")
                elif not resumen.get(
                    "revision_general_completada",
                    False,
                ):
                    st.info(
                        "Completa primero la revisión general del aula."
                    )
                else:
                    if st.button(
                        "✅ Cerrar revisión",
                        key=f"cerrar_revision_aula_{revision_id}",
                        use_container_width=True,
                    ):
                        cerrar_revision_aula(
                            revision_id=revision_id,
                            observaciones=observaciones_cierre,
                        )
                        st.success("Revisión cerrada.")
                        st.rerun()

