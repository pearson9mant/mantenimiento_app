import streamlit as st
from datetime import date
from pathlib import Path

from config import CENTROS, OPERARIOS
from database.db import conectar, _sql
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
    guardar_inventario_inicial_revision_aula,
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



def crear_planificacion_preventivo_aula(
    centro,
    edificio,
    planta,
    espacio,
    operario,
    frecuencia_dias,
    proxima_fecha,
    observaciones="",
):
    """
    Programa el Preventivo de aulas en preventivo_tareas.

    No crea una revisión ni una OT directamente. El motor general de
    Preventivo generará la PREV cuando llegue la fecha y entonces
    modules.preventivo creará la revisión de aula vinculada.
    """
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT COUNT(*)
            FROM preventivo_tareas
            WHERE centro = ?
              AND edificio = ?
              AND COALESCE(planta, '') = ?
              AND espacio = ?
              AND area = ?
              AND tarea = ?
              AND activo = 1
        """), (
            centro,
            edificio,
            str(planta or ""),
            espacio,
            "Mantenimiento general aulas",
            "Preventivo aulas",
        ))

        if int(cur.fetchone()[0] or 0) > 0:
            return (
                False,
                "Ya existe un Preventivo de aulas activo para este espacio.",
            )

        cur.execute(_sql("""
            INSERT INTO preventivo_tareas
            (
                centro, edificio, planta, espacio, area,
                tarea, frecuencia,
                ultima_fecha, proxima_fecha,
                operario, activo, observaciones, foto,
                tipo, prioridad, duracion_prevista,
                material_necesario, empresa_externa, fecha_limite
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (
            centro,
            edificio,
            str(planta or ""),
            espacio,
            "Mantenimiento general aulas",
            "Preventivo aulas",
            str(int(frecuencia_dias)),
            "",
            str(proxima_fecha),
            operario,
            1,
            observaciones,
            "",
            "Preventivo",
            "Media",
            "30 min",
            "",
            "",
            str(proxima_fecha),
        ))

        conn.commit()

        return (
            True,
            "Preventivo de aula añadido a Planificación.",
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


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

        frecuencia_dias = st.number_input(
            "Frecuencia en días",
            min_value=1,
            max_value=3650,
            value=180,
            step=1,
            key="prev_aula_frecuencia_dias",
        )

        proxima_fecha = st.date_input(
            "Próxima fecha",
            value=date.today(),
            key="prev_aula_proxima_fecha",
        )

        observaciones = st.text_area(
            "Observaciones",
            key="prev_aula_obs_iniciales",
        )

        st.caption(
            "Al crearla se añadirá a 📅 Planificación. "
            "La OT preventiva se generará cuando llegue la fecha."
        )

        if st.button(
            "✅ Crear tarea preventiva de aula",
            use_container_width=True,
            type="primary",
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
                    ok, mensaje = crear_planificacion_preventivo_aula(
                        centro=centro,
                        edificio=edificio,
                        planta=planta,
                        espacio=espacio,
                        operario=operario,
                        frecuencia_dias=int(frecuencia_dias),
                        proxima_fecha=str(proxima_fecha),
                        observaciones=observaciones,
                    )
                except Exception as e:
                    st.error(
                        "No se ha podido crear la planificación preventiva."
                    )
                    st.caption(str(e))
                else:
                    if ok:
                        st.success(mensaje)
                        st.info(
                            "Ya puedes verla y editarla en la pestaña "
                            "📅 Planificación."
                        )
                        st.rerun()
                    else:
                        st.warning(mensaje)

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

                estado_general = obtener_estado_revision_general_aula(
                    revision_id
                )

                inventario_requerido = bool(
                    estado_general.get(
                        "inventario_inicial_requerido",
                        False,
                    )
                )
                inventario_completado = bool(
                    estado_general.get(
                        "inventario_inicial_completado",
                        False,
                    )
                )

                if inventario_requerido and not inventario_completado:
                    st.info(
                        "Primer censo del aula. Este inventario se hace "
                        "una sola vez."
                    )

                    cantidades = {}
                    categoria_anterior = None

                    for item in inventariables:
                        item_id = int(item[0])
                        elemento = str(item[2] or "")
                        categoria = str(item[8] or "General").strip()

                        if categoria != categoria_anterior:
                            st.markdown(f"#### {categoria}")
                            categoria_anterior = categoria

                        cantidades[item_id] = int(
                            st.number_input(
                                elemento,
                                min_value=0,
                                step=1,
                                value=int(item[11] or 0),
                                key=(
                                    f"admin_aula_censo_"
                                    f"{revision_id}_{item_id}"
                                ),
                            )
                        )

                    if st.button(
                        "💾 Guardar inventario inicial",
                        key=f"admin_guardar_censo_{revision_id}",
                        use_container_width=True,
                    ):
                        try:
                            guardar_inventario_inicial_revision_aula(
                                revision_id,
                                cantidades,
                            )
                        except Exception as e:
                            st.error(
                                "No se ha podido guardar el inventario inicial."
                            )
                            st.caption(str(e))
                        else:
                            st.success(
                                "Inventario inicial guardado."
                            )
                            st.rerun()
                else:
                    st.caption(
                        "Inventario ya censado. Las revisiones posteriores "
                        "solo muestran las cantidades existentes."
                    )

                    categoria_anterior = None

                    for item in inventariables:
                        elemento = str(item[2] or "")
                        categoria = str(item[8] or "General").strip()
                        cantidad = int(item[11] or 0)

                        if categoria != categoria_anterior:
                            st.markdown(f"#### {categoria}")
                            categoria_anterior = categoria

                        st.markdown(
                            f"• **{elemento}:** {cantidad} ud"
                        )

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

