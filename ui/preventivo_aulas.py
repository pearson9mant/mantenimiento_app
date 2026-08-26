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

    st.subheader(
        "🏫 Preventivo de aulas"
    )

    st.caption(
        "Una sola revisión mantiene el preventivo técnico "
        "y actualiza el inventario vivo del aula."
    )

    tab1, tab2 = st.tabs([
        "➕ Nueva revisión",
        "📋 Revisiones",
    ])

    # =====================================================
    # NUEVA REVISIÓN
    # =====================================================
    with tab1:
        centros_catalogo = (
            obtener_centros_espacios()
            or []
        )

        centros_disponibles = (
            centros_catalogo
            or CENTROS
        )

        centro = st.selectbox(
            "Centro",
            centros_disponibles,
            key="prev_aula_centro",
        )

        edificios_disponibles = (
            obtener_edificios_espacios(
                centro
            )
            or []
        )

        if not edificios_disponibles:
            st.warning(
                "No hay edificios registrados "
                "en el catálogo de espacios "
                "para este centro."
            )
            edificio = ""
            planta = ""
            espacio = ""

        else:
            edificio = st.selectbox(
                "Edificio",
                edificios_disponibles,
                key=(
                    f"prev_aula_edificio_"
                    f"{centro}"
                ),
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
                    "Este edificio no tiene "
                    "plantas registradas en el "
                    "catálogo de espacios."
                )
                planta = ""
                espacio = ""

            else:
                planta = st.selectbox(
                    "Planta",
                    plantas_disponibles,
                    key=(
                        f"prev_aula_planta_"
                        f"{centro}_{edificio}"
                    ),
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
                        (
                            espacios_disponibles
                            + ["Otro"]
                        ),
                        key=(
                            f"prev_aula_espacio_"
                            f"{centro}_"
                            f"{edificio}_"
                            f"{planta}"
                        ),
                    )

                    if espacio_sel == "Otro":
                        espacio = st.text_input(
                            "Especificar aula / espacio",
                            key=(
                                "prev_aula_espacio_otro_"
                                f"{centro}_"
                                f"{edificio}_"
                                f"{planta}"
                            ),
                        )
                    else:
                        espacio = espacio_sel

                else:
                    st.warning(
                        "No hay aulas o espacios "
                        "registrados en esta planta."
                    )
                    espacio = ""

        operario_auto = (
            operario_por_centro(
                centro
            )
        )

        if operario_auto in OPERARIOS:
            indice_operario = (
                OPERARIOS.index(
                    operario_auto
                )
            )
        else:
            indice_operario = 0

        operario_sel = st.selectbox(
            "Operario",
            OPERARIOS,
            index=indice_operario,
            key=(
                f"prev_aula_operario_"
                f"{centro}"
            ),
        )

        if operario_sel == "Otro":
            operario = st.text_input(
                "Nombre operario",
                key=(
                    "prev_aula_operario_otro"
                ),
            )
        else:
            operario = operario_sel

        observaciones = st.text_area(
            "Observaciones iniciales",
            key=(
                "prev_aula_obs_iniciales"
            ),
        )

        if st.button(
            "✅ Crear revisión de aula",
            use_container_width=True,
        ):
            if not str(
                edificio
            ).strip():
                st.warning(
                    "Indica un edificio válido "
                    "del catálogo."
                )

            elif not str(
                planta
            ).strip():
                st.warning(
                    "Indica una planta válida "
                    "del catálogo."
                )

            elif not str(
                espacio
            ).strip():
                st.warning(
                    "Indica un aula o espacio."
                )

            elif not str(
                operario
            ).strip():
                st.warning(
                    "Indica un operario."
                )

            else:
                try:
                    revision_id = (
                        crear_revision_aula(
                            centro=centro,
                            edificio=edificio,
                            espacio=espacio,
                            operario=operario,
                            observaciones=observaciones,
                            planta=planta,
                        )
                    )

                except Exception as e:
                    st.error(
                        "No se ha podido crear "
                        "la revisión de aula."
                    )
                    st.caption(
                        str(e)
                    )

                else:
                    st.session_state[
                        "revision_aula_activa"
                    ] = revision_id

                    st.success(
                        "Revisión de aula "
                        "creada correctamente."
                    )
                    st.rerun()

    # =====================================================
    # REVISIONES
    # =====================================================
    with tab2:
        revisiones = (
            obtener_revisiones_aulas(
                100
            )
        )

        if not revisiones:
            st.info(
                "No hay revisiones de aula."
            )
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

            resumen = (
                resumen_revision_aula(
                    revision_id
                )
            )

            averias_detectadas = (
                resumen.get(
                    "averias_detectadas",
                    resumen.get(
                        "averias",
                        0,
                    ),
                )
            )

            averias_pendientes = (
                resumen.get(
                    "averias_pendientes",
                    averias_detectadas,
                )
            )

            averias_resueltas = (
                resumen.get(
                    "averias_resueltas",
                    0,
                )
            )

            titulo = (
                f"{fecha or '-'} | "
                f"{centro} · "
                f"{edificio} · "
                f"{planta or '-'} · "
                f"{espacio} | "
                f"{estado} | "
                f"Detectadas: "
                f"{averias_detectadas} | "
                f"Pendientes: "
                f"{averias_pendientes} | "
                f"Resueltas: "
                f"{averias_resueltas}"
            )

            with st.expander(
                titulo
            ):
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
                    st.write(
                        observaciones
                    )

                items = (
                    obtener_items_revision_aula(
                        revision_id
                    )
                )

                st.markdown(
                    "### Revisión integral"
                )

                st.info(
                    "Los 📦 elementos actualizan el inventario vivo. "
                    "En ellos se cumple siempre: "
                    "**Total = Correctas + Con incidencia**."
                )

                categoria_anterior = None

                for item in items:
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

                    categoria = (
                        str(
                            categoria
                            or "General"
                        ).strip()
                    )

                    if (
                        categoria
                        != categoria_anterior
                    ):
                        st.markdown(
                            "---"
                        )
                        st.markdown(
                            f"### {categoria}"
                        )
                        categoria_anterior = (
                            categoria
                        )

                    inventariable = (
                        _es_item_inventariable(
                            item
                        )
                    )

                    icono_tipo = (
                        "📦"
                        if inventariable
                        else "🔧"
                    )

                    st.markdown(
                        f"#### {icono_tipo} "
                        f"{elemento}"
                    )

                    if inventariable:
                        q1, q2, q3 = (
                            st.columns(
                                3
                            )
                        )

                        with q1:
                            total_nuevo = (
                                st.number_input(
                                    "Cantidad total",
                                    min_value=0,
                                    step=1,
                                    value=int(
                                        cantidad_total
                                        or 0
                                    ),
                                    key=(
                                        "total_aula_"
                                        f"{item_id}"
                                    ),
                                )
                            )

                        with q2:
                            correctas_nuevo = (
                                st.number_input(
                                    "Correctas",
                                    min_value=0,
                                    step=1,
                                    value=int(
                                        cantidad_correcta
                                        or 0
                                    ),
                                    key=(
                                        "correctas_aula_"
                                        f"{item_id}"
                                    ),
                                )
                            )

                        with q3:
                            afectadas_nuevo = (
                                st.number_input(
                                    "Con incidencia",
                                    min_value=0,
                                    step=1,
                                    value=int(
                                        cantidad_afectada
                                        or 0
                                    ),
                                    key=(
                                        "afectadas_aula_"
                                        f"{item_id}"
                                    ),
                                )
                            )

                        if (
                            int(correctas_nuevo)
                            + int(afectadas_nuevo)
                            != int(total_nuevo)
                        ):
                            st.warning(
                                "La suma todavía no coincide: "
                                f"{int(correctas_nuevo)} "
                                f"+ {int(afectadas_nuevo)} "
                                f"≠ {int(total_nuevo)}."
                            )

                    else:
                        total_nuevo = 0
                        correctas_nuevo = 0
                        afectadas_nuevo = 0

                    col1, col2, col3 = (
                        st.columns(
                            [2, 3, 2]
                        )
                    )

                    with col1:
                        estado_nuevo = (
                            st.radio(
                                "Estado",
                                ESTADOS_REVISION_AULA,
                                index=(
                                    ESTADOS_REVISION_AULA.index(
                                        estado_item
                                    )
                                    if estado_item
                                    in ESTADOS_REVISION_AULA
                                    else 0
                                ),
                                horizontal=True,
                                key=(
                                    "estado_aula_item_"
                                    f"{item_id}"
                                ),
                            )
                        )

                        if numero_ot_correctiva:
                            st.success(
                                "OT correctiva: "
                                f"{numero_ot_correctiva}"
                            )

                    with col2:
                        st.text_area(
                            "Observaciones",
                            value=(
                                obs_item
                                or ""
                            ),
                            key=(
                                "obs_aula_item_"
                                f"{item_id}"
                            ),
                        )

                        if (
                            estado_nuevo
                            == "Revisar"
                        ):
                            st.info(
                                "Quedará registrado "
                                "como pendiente de revisar."
                            )

                        if (
                            estado_nuevo
                            == "Avería"
                        ):
                            st.checkbox(
                                "Crear OT correctiva",
                                value=(
                                    True
                                    if not numero_ot_correctiva
                                    else False
                                ),
                                disabled=(
                                    True
                                    if numero_ot_correctiva
                                    else False
                                ),
                                key=(
                                    "crear_corr_aula_item_"
                                    f"{item_id}"
                                ),
                            )
                        else:
                            st.session_state[
                                "crear_corr_aula_item_"
                                f"{item_id}"
                            ] = False

                    with col3:
                        if foto:
                            try:
                                st.image(
                                    foto,
                                    caption=(
                                        "Foto actual"
                                    ),
                                    use_container_width=True,
                                )
                            except Exception:
                                st.caption(
                                    "Foto no disponible."
                                )

                        st.file_uploader(
                            "Foto",
                            type=[
                                "jpg",
                                "jpeg",
                                "png",
                            ],
                            key=(
                                "foto_aula_item_"
                                f"{item_id}"
                            ),
                        )

                st.markdown(
                    "---"
                )

                if st.button(
                    "💾 Guardar revisión completa",
                    key=(
                        "guardar_revision_completa_"
                        f"{revision_id}"
                    ),
                    use_container_width=True,
                ):
                    errores = []

                    # Primera pasada: validar todo.
                    for item in items:
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

                        if not _es_item_inventariable(
                            item
                        ):
                            continue

                        total_nuevo = (
                            st.session_state.get(
                                "total_aula_"
                                f"{item_id}",
                                cantidad_total or 0,
                            )
                        )

                        correctas_nuevo = (
                            st.session_state.get(
                                "correctas_aula_"
                                f"{item_id}",
                                cantidad_correcta
                                or 0,
                            )
                        )

                        afectadas_nuevo = (
                            st.session_state.get(
                                "afectadas_aula_"
                                f"{item_id}",
                                cantidad_afectada
                                or 0,
                            )
                        )

                        ok, mensaje = (
                            _validar_cantidades(
                                elemento,
                                total_nuevo,
                                correctas_nuevo,
                                afectadas_nuevo,
                            )
                        )

                        if not ok:
                            errores.append(
                                mensaje
                            )

                    if errores:
                        st.error(
                            "No se ha guardado "
                            "la revisión porque hay "
                            "cantidades incoherentes."
                        )

                        for error in errores:
                            st.warning(
                                error
                            )

                    else:
                        total_guardados = 0

                        for item in items:
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

                            estado_nuevo = (
                                st.session_state.get(
                                    "estado_aula_item_"
                                    f"{item_id}",
                                    estado_item
                                    or "Correcto",
                                )
                            )

                            obs_nueva = (
                                st.session_state.get(
                                    "obs_aula_item_"
                                    f"{item_id}",
                                    obs_item
                                    or "",
                                )
                            )

                            crear_corr_nuevo = (
                                st.session_state.get(
                                    "crear_corr_aula_item_"
                                    f"{item_id}",
                                    False,
                                )
                            )

                            foto_nueva = (
                                st.session_state.get(
                                    "foto_aula_item_"
                                    f"{item_id}",
                                    None,
                                )
                            )

                            ruta_foto = (
                                foto
                                or ""
                            )

                            if (
                                foto_nueva
                                is not None
                            ):
                                if (
                                    foto_nueva.size
                                    > 5
                                    * 1024
                                    * 1024
                                ):
                                    st.error(
                                        "La foto de "
                                        f"{elemento} "
                                        "supera 5 MB."
                                    )
                                    return

                                try:
                                    ruta_foto = (
                                        guardar_foto_revision_aula(
                                            foto_nueva,
                                            revision_id,
                                            item_id,
                                            elemento,
                                        )
                                    )
                                except Exception as e:
                                    st.error(
                                        "Error guardando "
                                        "foto de "
                                        f"{elemento}: {e}"
                                    )
                                    return

                            if (
                                _es_item_inventariable(
                                    item
                                )
                            ):
                                total_nuevo = (
                                    st.session_state.get(
                                        "total_aula_"
                                        f"{item_id}",
                                        cantidad_total
                                        or 0,
                                    )
                                )
                                correctas_nuevo = (
                                    st.session_state.get(
                                        "correctas_aula_"
                                        f"{item_id}",
                                        cantidad_correcta
                                        or 0,
                                    )
                                )
                                afectadas_nuevo = (
                                    st.session_state.get(
                                        "afectadas_aula_"
                                        f"{item_id}",
                                        cantidad_afectada
                                        or 0,
                                    )
                                )
                            else:
                                total_nuevo = 0
                                correctas_nuevo = 0
                                afectadas_nuevo = 0

                            guardar_item_revision_y_sincronizar(
                                revision_id=revision_id,
                                item_id=item_id,
                                estado=estado_nuevo,
                                observaciones=obs_nueva,
                                foto=ruta_foto,
                                crear_correctivo=crear_corr_nuevo,
                                cantidad_total=total_nuevo,
                                cantidad_correcta=correctas_nuevo,
                                cantidad_afectada=afectadas_nuevo,
                            )

                            total_guardados += 1

                        creadas = (
                            crear_correctivos_desde_revision(
                                revision_id
                            )
                        )

                        if creadas > 0:
                            st.success(
                                "Revisión guardada. "
                                f"Se han creado {creadas} "
                                "OTs correctivas y se ha "
                                "actualizado el inventario vivo."
                            )
                        else:
                            st.success(
                                "Revisión guardada. "
                                f"Elementos guardados: "
                                f"{total_guardados}. "
                                "Inventario vivo actualizado."
                            )

                        st.rerun()

                st.markdown(
                    "---"
                )
                st.markdown(
                    "### Cierre de revisión"
                )

                resumen = (
                    resumen_revision_aula(
                        revision_id
                    )
                )

                c1, c2, c3, c4, c5, c6 = (
                    st.columns(
                        6
                    )
                )

                c1.metric(
                    "✅ Correctos",
                    resumen.get(
                        "correctos",
                        0,
                    ),
                )
                c2.metric(
                    "🛠 Ajustados",
                    resumen.get(
                        "ajustados",
                        0,
                    ),
                )
                c3.metric(
                    "🟡 Revisar",
                    resumen.get(
                        "revisar",
                        0,
                    ),
                )
                c4.metric(
                    "🔴 Detectadas",
                    resumen.get(
                        "averias_detectadas",
                        resumen.get(
                            "averias",
                            0,
                        ),
                    ),
                )
                c5.metric(
                    "⏳ Pendientes",
                    resumen.get(
                        "averias_pendientes",
                        resumen.get(
                            "averias",
                            0,
                        ),
                    ),
                )
                c6.metric(
                    "✅ Resueltas",
                    resumen.get(
                        "averias_resueltas",
                        0,
                    ),
                )

                u1, u2, u3 = st.columns(
                    3
                )
                u1.metric(
                    "📦 Unidades censadas",
                    resumen.get(
                        "unidades_total",
                        0,
                    ),
                )
                u2.metric(
                    "✅ Unidades correctas",
                    resumen.get(
                        "unidades_correctas",
                        0,
                    ),
                )
                u3.metric(
                    "🔴 Unidades con incidencia",
                    resumen.get(
                        "unidades_afectadas",
                        0,
                    ),
                )

                observaciones_cierre = (
                    st.text_area(
                        "Observaciones de cierre",
                        value=(
                            observaciones
                            or ""
                        ),
                        key=(
                            "obs_cierre_revision_aula_"
                            f"{revision_id}"
                        ),
                    )
                )

                col_a, col_b = st.columns(
                    2
                )

                with col_a:
                    if st.button(
                        "🔧 Crear correctivos de averías",
                        key=(
                            "crear_corr_revision_"
                            f"{revision_id}"
                        ),
                    ):
                        creadas = (
                            crear_correctivos_desde_revision(
                                revision_id
                            )
                        )

                        if creadas > 0:
                            st.success(
                                "Se han creado "
                                f"{creadas} OTs "
                                "correctivas."
                            )
                        else:
                            st.info(
                                "No hay averías "
                                "pendientes de generar OT."
                            )

                        st.rerun()

                with col_b:
                    if st.button(
                        "✅ Cerrar revisión",
                        key=(
                            "cerrar_revision_aula_"
                            f"{revision_id}"
                        ),
                    ):
                        cerrar_revision_aula(
                            revision_id=revision_id,
                            observaciones=(
                                observaciones_cierre
                            ),
                        )

                        st.success(
                            "Revisión cerrada."
                        )
                        st.rerun()

