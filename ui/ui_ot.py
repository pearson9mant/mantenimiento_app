import streamlit as st

try:
    from st_keyup import st_keyup
except Exception:
    st_keyup = None
from modules.ordenes import (
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    obtener_fotos_ot,
    guardar_foto_ot,
    crear_correctiva_desde_ot,
)

from modules.inventario import (
    obtener_material_por_codigo,
    registrar_movimiento_inventario,
)

from modules.preventivo import checklist_preventivo_completo
from modules.ficha_espacio import obtener_inventario_espacio

from modules.cuadros_electricos import (
    COMPROBACIONES_PREVENTIVO_CUADRO,
    obtener_revision_preventiva_cuadro,
    obtener_mecanismos_cuadro,
    guardar_comprobaciones_revision_cuadro,
    comprobaciones_revision_cuadro_completas,
    obtener_puntos_anomalia_revision_cuadro,
    obtener_incidencia_existente_para_punto,
    marcar_revision_cuadro_completada,
    revision_cuadro_lista_para_cerrar,
    crear_incidencia_desde_revision_cuadro,
)

from modules.preventivo_aulas import (
    obtener_revision_aula_por_ot,
    obtener_contexto_revision_aula_por_ot,
    obtener_items_revision_aula,
    guardar_item_revision_y_sincronizar,
    crear_correctivos_desde_revision,
    revision_aula_lista_para_cerrar,
    resumen_revision_aula,
    ESTADOS_REVISION_AULA,
    obtener_estado_revision_general_aula,
    guardar_inventario_inicial_revision_aula,
    guardar_inventario_inicial_flexible_revision_aula,
    marcar_revision_general_aula_completada,
    crear_incidencia_desde_revision_aula,
)

from ui.ui_legionella import obtener_checklist_correctivo_legionella

from ui.ui_ot_controles import (
    mostrar_checklist_preventivo_operario,
    mostrar_ejecucion_legionella_operario,
    mostrar_checklist_correctivo_legionella_operario,
)

from database.db import conectar, _sql

from modules.espacios import (
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)

from ui.ui_pedido_ot import mostrar_pedido_material_desde_ot


MAX_FOTOS_CIERRE_OT = 5
MAX_MB_FOTO_OT = 5


def codigo_ot_no_traducible(numero_ot):
    """
    Evita que la traducción automática del navegador modifique
    identificadores técnicos como LEG, INC, PREV o PED-MAT.
    """
    import html

    codigo = html.escape(
        str(numero_ot or "").strip()
    )

    return (
        '<span translate="no" class="notranslate">'
        f'{codigo}'
        '</span>'
    )


def preparar_nueva_captura_foto_ot(clave_version):
    """
    Prepara una instancia limpia de cámara/subida para la siguiente foto.

    Se usa como callback para que el cambio de clave ocurra antes del
    rerun automático de Streamlit, evitando encadenar un segundo rerun
    justo después de capturar/guardar una fotografía.
    """
    version_actual = int(
        st.session_state.get(
            clave_version,
            0,
        )
        or 0
    )

    st.session_state[
        clave_version
    ] = version_actual + 1


def limpiar_nombre_archivo(texto):
    texto = str(texto or "")

    for caracter in [
        "/",
        "\\",
        ":",
        "*",
        "?",
        '"',
        "<",
        ">",
        "|",
    ]:
        texto = texto.replace(
            caracter,
            "_",
        )

    return texto.replace(
        " ",
        "_",
    )


def validar_fotos_cierre_ot(fotos):
    fotos = list(
        fotos or []
    )

    errores = []

    if len(fotos) > MAX_FOTOS_CIERRE_OT:
        errores.append(
            f"Máximo {MAX_FOTOS_CIERRE_OT} fotos por cierre."
        )

    for foto in fotos[:MAX_FOTOS_CIERRE_OT]:
        try:
            tamano = int(
                getattr(
                    foto,
                    "size",
                    0,
                )
                or 0
            )
        except Exception:
            tamano = 0

        if tamano > MAX_MB_FOTO_OT * 1024 * 1024:
            errores.append(
                f"{getattr(foto, 'name', 'Foto')}: "
                f"supera {MAX_MB_FOTO_OT} MB."
            )

    return errores


def obtener_nombres_fotos_ot(numero_ot):
    """
    Consulta únicamente los nombres de fotos ya guardadas.
    Evita descargar los binarios para comprobar duplicados.
    """
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT nombre_foto
            FROM ordenes_fotos
            WHERE numero_ot = ?
        """), (
            numero_ot,
        ))

        return {
            str(fila[0] or "").strip()
            for fila in cur.fetchall()
            if fila and fila[0]
        }

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

        return set()

    finally:
        conn.close()


def guardar_fotos_cierre_ot(
    numero_ot,
    id_orden,
    fotos,
):
    """
    Guarda las fotos de trabajo realizado.

    Los nombres son deterministas para que un segundo intento
    de cierre no duplique las mismas fotografías.
    """
    fotos = list(
        fotos or []
    )[:MAX_FOTOS_CIERRE_OT]

    if not fotos:
        return (
            True,
            0,
            "",
        )

    errores = validar_fotos_cierre_ot(
        fotos
    )

    if errores:
        return (
            False,
            0,
            " | ".join(
                errores
            ),
        )

    nombres_existentes = obtener_nombres_fotos_ot(
        numero_ot
    )

    guardadas = 0

    try:
        for indice, foto in enumerate(
            fotos,
            start=1,
        ):
            nombre_original = limpiar_nombre_archivo(
                getattr(
                    foto,
                    "name",
                    f"foto_{indice}.jpg",
                )
            )

            nombre_foto = limpiar_nombre_archivo(
                f"{numero_ot}_CIERRE_{id_orden}_"
                f"{indice}_{nombre_original}"
            )

            if nombre_foto in nombres_existentes:
                continue

            contenido = foto.getvalue()

            if len(contenido) > MAX_MB_FOTO_OT * 1024 * 1024:
                return (
                    False,
                    guardadas,
                    (
                        f"{nombre_original}: "
                        f"supera {MAX_MB_FOTO_OT} MB."
                    ),
                )

            guardar_foto_ot(
                numero_ot=numero_ot,
                nombre_foto=nombre_foto,
                foto_data=contenido,
            )

            nombres_existentes.add(
                nombre_foto
            )

            guardadas += 1

        return (
            True,
            guardadas,
            "",
        )

    except Exception as error:
        return (
            False,
            guardadas,
            str(error),
        )


def normalizar_txt(valor):
    import unicodedata

    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)

    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )


def normalizar_operario_nombre(nombre):
    texto = normalizar_txt(nombre)
    limpio = texto.replace(".", "").replace(" ", "").replace("-", "").replace("_", "")

    if limpio in ["jaalmeda", "jalmeda", "juanantonio", "juanantonioalmeda"]:
        return "j.a. almeda"

    if limpio in ["luislozano", "llozano", "luis"]:
        return "luis lozano"

    if limpio in ["abelvasquez", "abel", "avasquez"]:
        return "abel vasquez"

    return texto


def rol_actual():
    return str(st.session_state.get("rol", "")).strip().lower()


def es_operario():
    return rol_actual() == "operario"


def nombre_operario_actual():
    return str(
        st.session_state.get("operario_activo")
        or st.session_state.get("nombre")
        or st.session_state.get("usuario")
        or ""
    ).strip()


def es_ot_preventiva(origen, descripcion, numero_ot=""):
    origen_txt = str(origen or "").strip().upper()
    desc_txt = str(descripcion or "").strip().upper()
    numero_txt = str(numero_ot or "").strip().upper()

    # Regla principal:
    # una OT preventiva real lleva numeración PREV.
    if numero_txt.startswith("PREV-"):
        return True

    # Una INC creada desde un preventivo conserva origen PREVENTIVO
    # para trazabilidad, pero sigue siendo una correctiva.
    if numero_txt.startswith("INC-"):
        return False

    # Compatibilidad con OT antiguas.
    return (
        origen_txt == "PREVENTIVO"
        or desc_txt.startswith("[PREVENTIVO]")
    )


def es_ot_legionella(area, origen, descripcion):
    area_txt = normalizar_txt(area)
    origen_txt = normalizar_txt(origen)
    desc_txt = normalizar_txt(descripcion)

    return (
        area_txt == "legionella"
        or origen_txt == "legionella"
        or desc_txt.startswith("control legionella")
        or desc_txt.startswith("correctivo legionella")
        or "correctivo legionella" in desc_txt
    )


def descomponer_orden_operario(fila):
    observaciones_estado = ""

    if len(fila) >= 26:
        (
            id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
            area, prioridad, operario, origen, solicitante, fecha_origen,
            foto, tipo_solicitante, tipo_orden, empresa_externa,
            contacto_empresa, telefono_empresa, email_empresa,
            fecha_programada, fecha_realizacion, coste_estimado,
            coste_final, observaciones_estado,
        ) = fila[:26]

    elif len(fila) >= 16:
        (
            id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
            area, prioridad, operario, origen, solicitante, fecha_origen,
            foto, tipo_solicitante,
        ) = fila[:16]

    elif len(fila) == 15:
        (
            id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
            area, prioridad, operario, origen, solicitante, fecha_origen, foto,
        ) = fila
        tipo_solicitante = "Operarios"

    else:
        (
            id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
            area, prioridad, operario, origen
        ) = fila[:12]
        solicitante = ""
        fecha_origen = ""
        foto = ""
        tipo_solicitante = "Operarios"

    return (
        id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
        area, prioridad, operario, origen, solicitante, fecha_origen,
        foto, tipo_solicitante, observaciones_estado,
    )



def es_preventivo_cuadro_ot(area, descripcion, numero_ot=""):
    numero_txt = str(
        numero_ot or ""
    ).strip().upper()

    if not numero_txt.startswith(
        "PREV-"
    ):
        return False

    desc_txt = normalizar_txt(
        descripcion
    )

    return (
        "preventivo cuadro" in desc_txt
    )


def mostrar_preventivo_cuadro_operario(
    num_ot,
    operario,
):
    revision = obtener_revision_preventiva_cuadro(
        num_ot
    )

    st.markdown(
        "### ⚡ Revisión preventiva del cuadro"
    )

    if not revision:
        st.error(
            "Esta OT está marcada como preventivo de cuadro eléctrico, "
            "pero no se encuentra su revisión vinculada."
        )
        return

    st.caption(
        f"📍 {revision['centro'] or '-'} · "
        f"{revision['edificio'] or '-'} · "
        f"{revision['planta'] or '-'} · "
        f"{revision['espacio'] or '-'}"
    )

    st.markdown(
        f"#### ⚡ {revision['codigo']} · {revision['nombre']}"
    )

    # -----------------------------------------------------
    # INVENTARIO TÉCNICO VIVO
    # -----------------------------------------------------
    st.markdown(
        "### 📦 Inventario técnico actual"
    )

    mecanismos = obtener_mecanismos_cuadro(
        revision["cuadro_id"],
        solo_activos=True,
    )

    if not mecanismos:
        st.warning(
            "Este cuadro todavía no tiene mecanismos inventariados. "
            "Completa primero su inventario en "
            "Configuración → Cuadros eléctricos."
        )
    else:
        lineas = []

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

            partes = []

            if identificador:
                partes.append(
                    str(identificador)
                )

            partes.append(
                str(mecanismo or "-")
            )

            if caracteristicas:
                partes.append(
                    str(caracteristicas)
                )

            texto = " · ".join(
                partes
            )

            if circuito:
                texto += (
                    f" · **{circuito}**"
                )

            texto += (
                f" · {int(cantidad or 0)} ud"
                f"{'s' if int(cantidad or 0) != 1 else ''}"
            )

            lineas.append(
                f"- {texto}"
            )

        st.markdown(
            "\n".join(
                lineas
            )
        )

    # -----------------------------------------------------
    # CHECKLIST TÉCNICO BREVE
    # -----------------------------------------------------
    st.markdown(
        "---"
    )
    st.markdown(
        "### 👀 Revisión técnica"
    )

    st.info(
        "Revisión visual y funcional básica del cuadro. "
        "No sustituye mediciones reglamentarias ni trabajos que "
        "requieran procedimientos eléctricos específicos."
    )

    comprobaciones_guardadas = dict(
        revision.get(
            "comprobaciones",
            {},
        )
        or {}
    )

    comprobaciones_nuevas = {}

    opciones_estado_revision = [
        "Pendiente",
        "✅ Correcto",
        "⚠️ Anomalía",
        "➖ No aplica",
    ]

    mapa_valor_a_opcion = {
        "": "Pendiente",
        "correcto": "✅ Correcto",
        "anomalia": "⚠️ Anomalía",
        "no_aplica": "➖ No aplica",
    }

    mapa_opcion_a_valor = {
        "Pendiente": "",
        "✅ Correcto": "correcto",
        "⚠️ Anomalía": "anomalia",
        "➖ No aplica": "no_aplica",
    }

    for indice, punto in enumerate(
        COMPROBACIONES_PREVENTIVO_CUADRO,
        start=1,
    ):
        valor_guardado = str(
            comprobaciones_guardadas.get(
                punto,
                "",
            )
            or ""
        ).strip().lower()

        opcion_actual = mapa_valor_a_opcion.get(
            valor_guardado,
            "Pendiente",
        )

        seleccion = st.radio(
            punto,
            opciones_estado_revision,
            index=opciones_estado_revision.index(
                opcion_actual
            ),
            horizontal=True,
            key=(
                f"prev_cuadro_check_"
                f"{num_ot}_{indice}"
            ),
        )

        comprobaciones_nuevas[punto] = (
            mapa_opcion_a_valor[
                seleccion
            ]
        )

    observaciones_revision = st.text_area(
        "Observaciones de la revisión",
        value=str(
            revision.get(
                "observaciones",
                "",
            )
            or ""
        ),
        key=f"prev_cuadro_obs_{num_ot}",
    )

    if st.button(
        "💾 Guardar revisión técnica",
        key=f"prev_cuadro_guardar_check_{num_ot}",
        use_container_width=True,
    ):
        if guardar_comprobaciones_revision_cuadro(
            numero_ot=num_ot,
            comprobaciones=comprobaciones_nuevas,
            observaciones=observaciones_revision,
        ):
            st.success(
                "Revisión técnica guardada."
            )
            st.rerun()
        else:
            st.error(
                "No se ha podido guardar la revisión técnica."
            )

    checks_completos = all(
        str(
            comprobaciones_nuevas.get(
                punto,
                "",
            )
            or ""
        ).strip().lower()
        in [
            "correcto",
            "anomalia",
            "no_aplica",
        ]
        for punto in COMPROBACIONES_PREVENTIVO_CUADRO
    )

    if not checks_completos:
        st.warning(
            "Indica el resultado de todos los puntos: "
            "Correcto, Anomalía o No aplica."
        )
        return

    puntos_anomalia_actuales = [
        punto
        for punto in COMPROBACIONES_PREVENTIVO_CUADRO
        if str(
            comprobaciones_nuevas.get(
                punto,
                "",
            )
            or ""
        ).strip().lower() == "anomalia"
    ]

    if puntos_anomalia_actuales:
        st.warning(
            "⚠️ Puntos con anomalía:\n\n"
            + "\n".join(
                f"- {punto}"
                for punto in puntos_anomalia_actuales
            )
        )

    # -----------------------------------------------------
    # ANOMALÍAS → INC NORMALES
    # -----------------------------------------------------
    st.markdown(
        "---"
    )
    st.markdown(
        "### 🚨 Resultado"
    )

    incidencias_creadas = list(
        revision.get(
            "incidencias",
            [],
        )
        or []
    )

    if incidencias_creadas:
        st.success(
            "🔧 Incidencias creadas: "
            + ", ".join(
                incidencias_creadas
            )
        )

    if revision.get(
        "completada"
    ):
        st.success(
            "✅ Revisión preventiva terminada. "
            "La OT ya puede finalizarse."
        )
        return

    if not puntos_anomalia_actuales:
        if st.button(
            "✅ Terminar revisión sin anomalías",
            key=f"prev_cuadro_sin_anomalias_{num_ot}",
            use_container_width=True,
            type="primary",
        ):
            guardar_comprobaciones_revision_cuadro(
                numero_ot=num_ot,
                comprobaciones=comprobaciones_nuevas,
                observaciones=observaciones_revision,
            )

            if marcar_revision_cuadro_completada(
                num_ot,
                True,
            ):
                st.success(
                    "Revisión preventiva registrada."
                )
                st.rerun()
            else:
                st.error(
                    "No se ha podido completar la revisión."
                )

    else:
        st.markdown(
            "#### 🔧 Registrar anomalía"
        )

        st.caption(
            "Los puntos marcados como ⚠️ Anomalía deben quedar "
            "trazados mediante una incidencia normal de Electricidad. "
            "Puedes agrupar en una INC los defectos que formen parte "
            "de la misma actuación, o crear varias."
        )

        contador = int(
            st.session_state.get(
                f"prev_cuadro_contador_inc_{num_ot}",
                1,
            )
            or 1
        )

        opciones_anomalia = list(
            puntos_anomalia_actuales
        )

        punto_asociado = st.selectbox(
            "Punto de revisión asociado",
            opciones_anomalia,
            key=(
                f"prev_cuadro_punto_inc_"
                f"{num_ot}_{contador}"
            ),
        )

        incidencia_existente_punto = (
            obtener_incidencia_existente_para_punto(
                numero_ot_preventiva=num_ot,
                punto_revision=punto_asociado,
            )
        )

        if incidencia_existente_punto:
            st.success(
                "✅ Este punto ya está registrado en "
                f"{incidencia_existente_punto}. "
                "No se creará otra incidencia igual."
            )

        descripcion = st.text_area(
            "¿Qué ocurre?",
            value=f"{punto_asociado}: ",
            placeholder=(
                "Ej.: Q1 presenta signos de calentamiento "
                "en el borne de salida."
            ),
            height=110,
            key=(
                f"prev_cuadro_desc_inc_"
                f"{num_ot}_{contador}"
            ),
        )

        fotos = st.file_uploader(
            "📷 Fotografías de la anomalía (opcional)",
            type=[
                "jpg",
                "jpeg",
                "png",
            ],
            accept_multiple_files=True,
            key=(
                f"prev_cuadro_fotos_inc_"
                f"{num_ot}_{contador}"
            ),
            help=(
                "Máximo 5 fotografías y 5 MB por foto."
            ),
        )

        if st.button(
            "➕ Crear incidencia",
            key=(
                f"prev_cuadro_crear_inc_"
                f"{num_ot}_{contador}"
            ),
            use_container_width=True,
            type="primary",
            disabled=bool(
                incidencia_existente_punto
            ),
        ):
            guardar_comprobaciones_revision_cuadro(
                numero_ot=num_ot,
                comprobaciones=comprobaciones_nuevas,
                observaciones=observaciones_revision,
            )

            ok, mensaje, numero_inc = (
                crear_incidencia_desde_revision_cuadro(
                    numero_ot_preventiva=num_ot,
                    descripcion=descripcion,
                    fotos=fotos,
                    punto_revision=punto_asociado,
                )
            )

            if not ok:
                st.error(
                    mensaje
                )
            else:
                st.session_state[
                    f"prev_cuadro_contador_inc_{num_ot}"
                ] = contador + 1

                st.success(
                    mensaje
                )
                st.rerun()

        if incidencias_creadas:
            st.success(
                "Ya existe al menos una INC vinculada a esta revisión."
            )

            if st.button(
                "✅ Terminar revisión preventiva",
                key=f"prev_cuadro_terminar_{num_ot}",
                use_container_width=True,
            ):
                guardar_comprobaciones_revision_cuadro(
                    numero_ot=num_ot,
                    comprobaciones=comprobaciones_nuevas,
                    observaciones=observaciones_revision,
                )

                if marcar_revision_cuadro_completada(
                    num_ot,
                    True,
                ):
                    st.success(
                        "Revisión preventiva terminada."
                    )
                    st.rerun()
                else:
                    st.error(
                        "No se ha podido completar la revisión. "
                        "Comprueba que exista una INC para las anomalías."
                    )



def es_preventivo_aulas_ot(area, descripcion, numero_ot=""):
    """
    Reconoce el flujo integral de revisión de espacios sin consultar la BD.

    Compatibilidad:
    - mantiene los antiguos Preventivo aulas;
    - reconoce las nuevas OT marcadas como PREVENTIVO ESPACIO.

    La validación real de la revisión vinculada se mantiene al abrir la OT,
    evitando una consulta remota adicional por cada tarjeta del listado.
    """
    desc_txt = normalizar_txt(
        descripcion
    )

    numero_txt = str(
        numero_ot or ""
    ).strip().upper()

    if not numero_txt.startswith(
        "PREV-"
    ):
        return False

    return (
        "preventivo espacio" in desc_txt
        or "preventivo aulas" in desc_txt
        or "preventivo aula" in desc_txt
    )


def _es_item_aula_inventariable(item):
    try:
        return (
            str(item[9] or "").strip()
            == "Elemento inventariable"
        )
    except Exception:
        return False


def _validar_cantidades_item_aula(
    elemento,
    total,
    correctas,
    afectadas,
):
    total = int(
        total or 0
    )
    correctas = int(
        correctas or 0
    )
    afectadas = int(
        afectadas or 0
    )

    if (
        total < 0
        or correctas < 0
        or afectadas < 0
    ):
        return (
            False,
            f"{elemento}: las cantidades no pueden ser negativas.",
        )

    if correctas + afectadas != total:
        return (
            False,
            (
                f"{elemento}: Total ({total}) debe ser igual a "
                f"Correctas ({correctas}) + "
                f"Con incidencia ({afectadas})."
            ),
        )

    return True, ""


def mostrar_preventivo_aula_operario_legacy(
    num_ot,
    operario,
):
    """
    Ejecuta dentro de la OT la revisión integral de aula.

    Esta pantalla reutiliza la revisión ya creada por modules.preventivo
    cuando generó la OT. No crea una nueva revisión ni una segunda OT.
    """
    (
        revision,
        items,
        estado_general,
    ) = obtener_contexto_revision_aula_por_ot(
        num_ot
    )

    st.markdown(
        "### 🏫 Preventivo integral del aula"
    )

    if not revision:
        st.error(
            "Esta OT está marcada como Preventivo aulas, "
            "pero no se encuentra su revisión vinculada."
        )
        return

    (
        revision_id,
        fecha_revision,
        centro_revision,
        edificio_revision,
        espacio_revision,
        operario_revision,
        estado_revision,
        observaciones_revision,
        numero_ot_revision,
        planta_revision,
    ) = revision

    st.caption(
        f"📍 {centro_revision or '-'} · "
        f"{edificio_revision or '-'} · "
        f"{planta_revision or '-'} · "
        f"{espacio_revision or '-'}"
    )

    st.info(
        "Los 📦 elementos mantienen actualizado el inventario vivo. "
        "En ellos debe cumplirse: "
        "**Total = Correctas + Con incidencia**."
    )

    items = obtener_items_revision_aula(
        revision_id
    )

    if not items:
        st.warning(
            "La revisión no contiene elementos. "
            "Revisa Configuración → Modelo aulas."
        )
        return

    categoria_anterior = None

    for item in items:
        (
            item_id,
            _revision_id,
            elemento,
            estado_item,
            observaciones_item,
            foto_item,
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
            st.markdown("---")
            st.markdown(
                f"#### {categoria}"
            )
            categoria_anterior = categoria

        inventariable = _es_item_aula_inventariable(
            item
        )

        icono = (
            "📦"
            if inventariable
            else "🔧"
        )

        with st.container(border=True):
            st.markdown(
                f"**{icono} {elemento}**"
            )

            if inventariable:
                c1, c2, c3 = st.columns(3)

                with c1:
                    total_nuevo = st.number_input(
                        "Cantidad total",
                        min_value=0,
                        step=1,
                        value=int(
                            cantidad_total or 0
                        ),
                        key=(
                            f"ot_aula_total_"
                            f"{num_ot}_{item_id}"
                        ),
                    )

                with c2:
                    correctas_nuevo = st.number_input(
                        "Correctas",
                        min_value=0,
                        step=1,
                        value=int(
                            cantidad_correcta or 0
                        ),
                        key=(
                            f"ot_aula_correctas_"
                            f"{num_ot}_{item_id}"
                        ),
                    )

                with c3:
                    afectadas_nuevo = st.number_input(
                        "Con incidencia",
                        min_value=0,
                        step=1,
                        value=int(
                            cantidad_afectada or 0
                        ),
                        key=(
                            f"ot_aula_afectadas_"
                            f"{num_ot}_{item_id}"
                        ),
                    )

                if (
                    int(correctas_nuevo)
                    + int(afectadas_nuevo)
                    != int(total_nuevo)
                ):
                    st.warning(
                        f"{int(correctas_nuevo)} + "
                        f"{int(afectadas_nuevo)} ≠ "
                        f"{int(total_nuevo)}"
                    )

            else:
                total_nuevo = 0
                correctas_nuevo = 0
                afectadas_nuevo = 0

            estado_actual = (
                estado_item
                if estado_item
                in ESTADOS_REVISION_AULA
                else "Correcto"
            )

            estado_nuevo = st.radio(
                "Estado",
                ESTADOS_REVISION_AULA,
                index=(
                    ESTADOS_REVISION_AULA.index(
                        estado_actual
                    )
                ),
                horizontal=True,
                key=(
                    f"ot_aula_estado_"
                    f"{num_ot}_{item_id}"
                ),
            )

            observacion_nueva = st.text_area(
                "Observación",
                value=str(
                    observaciones_item
                    or ""
                ),
                key=(
                    f"ot_aula_obs_"
                    f"{num_ot}_{item_id}"
                ),
            )

            if numero_ot_correctiva:
                st.success(
                    f"🔧 Correctiva vinculada: "
                    f"{numero_ot_correctiva}"
                )

            crear_corr = False

            if estado_nuevo == "Avería":
                crear_corr = st.checkbox(
                    "Crear OT correctiva",
                    value=(
                        bool(crear_correctivo)
                        if not numero_ot_correctiva
                        else False
                    ),
                    disabled=bool(
                        numero_ot_correctiva
                    ),
                    key=(
                        f"ot_aula_corr_"
                        f"{num_ot}_{item_id}"
                    ),
                )

            if st.button(
                "💾 Guardar punto",
                key=(
                    f"ot_aula_guardar_"
                    f"{num_ot}_{item_id}"
                ),
                use_container_width=True,
            ):
                if (
                    estado_nuevo
                    in [
                        "Ajustado",
                        "Revisar",
                        "Avería",
                    ]
                    and not str(
                        observacion_nueva
                        or ""
                    ).strip()
                ):
                    st.warning(
                        "Este estado necesita una observación."
                    )
                else:
                    if inventariable:
                        ok_cant, mensaje_cant = (
                            _validar_cantidades_item_aula(
                                elemento,
                                total_nuevo,
                                correctas_nuevo,
                                afectadas_nuevo,
                            )
                        )
                    else:
                        ok_cant = True
                        mensaje_cant = ""

                    if not ok_cant:
                        st.warning(
                            mensaje_cant
                        )
                    else:
                        ok = guardar_item_revision_y_sincronizar(
                            revision_id=revision_id,
                            item_id=item_id,
                            estado=estado_nuevo,
                            observaciones=observacion_nueva,
                            foto=foto_item or "",
                            crear_correctivo=crear_corr,
                            cantidad_total=total_nuevo,
                            cantidad_correcta=correctas_nuevo,
                            cantidad_afectada=afectadas_nuevo,
                        )

                        if ok:
                            creadas = 0

                            if (
                                estado_nuevo == "Avería"
                                and crear_corr
                            ):
                                creadas = (
                                    crear_correctivos_desde_revision(
                                        revision_id
                                    )
                                )

                            if creadas > 0:
                                st.success(
                                    "Guardado. "
                                    f"Se han creado {creadas} "
                                    "OT correctiva(s)."
                                )
                            else:
                                st.success(
                                    "Punto guardado e inventario actualizado."
                                )

                            st.rerun()

                        else:
                            st.error(
                                "No se ha podido guardar este punto."
                            )

    st.markdown("---")
    st.markdown("### 📊 Resultado de la revisión")

    resumen = resumen_revision_aula(
        revision_id
    )

    unidades_total = int(
        resumen.get("unidades_total", 0) or 0
    )
    unidades_correctas = int(
        resumen.get("unidades_correctas", 0) or 0
    )
    unidades_afectadas = int(
        resumen.get("unidades_afectadas", 0) or 0
    )

    total_lineas = int(
        resumen.get("total", 0) or 0
    )
    correctos = int(
        resumen.get("correctos", 0) or 0
    )
    ajustados = int(
        resumen.get("ajustados", 0) or 0
    )
    revisar = int(
        resumen.get("revisar", 0) or 0
    )
    averias = int(
        resumen.get("averias_detectadas", 0) or 0
    )
    averias_pendientes = int(
        resumen.get("averias_pendientes", 0) or 0
    )
    averias_resueltas = int(
        resumen.get("averias_resueltas", 0) or 0
    )

    # Las comprobaciones técnicas son las líneas no inventariables.
    total_inventariables = sum(
        1
        for item in items
        if _es_item_aula_inventariable(item)
    )
    total_comprobaciones = max(
        0,
        total_lineas - total_inventariables,
    )

    comprobaciones_correctas = sum(
        1
        for item in items
        if (
            not _es_item_aula_inventariable(item)
            and str(item[3] or "") == "Correcto"
        )
    )
    comprobaciones_ajustadas = sum(
        1
        for item in items
        if (
            not _es_item_aula_inventariable(item)
            and str(item[3] or "") == "Ajustado"
        )
    )
    comprobaciones_revisar = sum(
        1
        for item in items
        if (
            not _es_item_aula_inventariable(item)
            and str(item[3] or "") == "Revisar"
        )
    )
    comprobaciones_averia = sum(
        1
        for item in items
        if (
            not _es_item_aula_inventariable(item)
            and str(item[3] or "") == "Avería"
        )
    )

    r1, r2, r3 = st.columns(3)

    with r1:
        st.metric(
            "📦 Unidades inventariadas",
            unidades_total,
        )
        st.caption(
            f"✅ {unidades_correctas} correctas · "
            f"⚠️ {unidades_afectadas} afectadas"
        )

    with r2:
        st.metric(
            "🔧 Comprobaciones técnicas",
            total_comprobaciones,
        )
        st.caption(
            f"✅ {comprobaciones_correctas} correctas · "
            f"🛠️ {comprobaciones_ajustadas} ajustadas · "
            f"👀 {comprobaciones_revisar} revisar · "
            f"🚨 {comprobaciones_averia} avería"
        )

    with r3:
        st.metric(
            "🚨 Averías detectadas",
            averias,
        )
        st.caption(
            f"⏳ {averias_pendientes} pendientes · "
            f"✅ {averias_resueltas} resueltas"
        )

    # Estado automático del aula a partir de la revisión real.
    if averias > 0 or unidades_afectadas > 0:
        estado_resultante = "🔴 Requiere actuación"
    elif revisar > 0:
        estado_resultante = "🟡 Requiere seguimiento"
    elif ajustados > 0:
        estado_resultante = "🟢 Correcta · con ajustes realizados"
    else:
        estado_resultante = "🟢 Correcta"

    st.info(
        f"**Estado resultante del aula:** {estado_resultante}"
    )

    if revision_aula_lista_para_cerrar(
        num_ot
    ):
        st.success(
            "✅ Preventivo de aula completo. "
            "La OT ya puede finalizarse."
        )
    else:
        st.warning(
            "Completa los estados, observaciones necesarias "
            "y cantidades antes de finalizar la OT."
        )



def mostrar_preventivo_aula_operario(
    num_ot,
    operario,
):
    """
    Flujo actual de revisión preventiva integral de espacios.

    El flujo anterior se conserva íntegro en
    mostrar_preventivo_aula_operario_legacy() por seguridad.

    - Primer preventivo del espacio: censo inicial una sola vez.
    - Preventivos posteriores: solo lectura de cantidades.
    - Revisión visual/funcional general.
    - Cada anomalía genera una INC normal.
    """
    (
        revision,
        items,
        estado_general,
    ) = obtener_contexto_revision_aula_por_ot(
        num_ot
    )

    st.markdown(
        "### 🏫 Revisión preventiva del espacio"
    )

    if not revision:
        st.error(
            "Esta OT está marcada como revisión general de espacio, "
            "pero no se encuentra su revisión vinculada."
        )
        return

    (
        revision_id,
        fecha_revision,
        centro_revision,
        edificio_revision,
        espacio_revision,
        operario_revision,
        estado_revision,
        observaciones_revision,
        numero_ot_revision,
        planta_revision,
    ) = revision

    st.caption(
        f"📍 {centro_revision or '-'} · "
        f"{edificio_revision or '-'} · "
        f"{planta_revision or '-'} · "
        f"{espacio_revision or '-'}"
    )

    if not items:
        st.warning(
            "La revisión no contiene elementos. "
            "No se ha podido preparar el inventario de este espacio."
        )
        return

    inventariables = [
        item
        for item in items
        if _es_item_aula_inventariable(
            item
        )
    ]

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

    # =====================================================
    # INVENTARIO
    # =====================================================
    st.markdown(
        "### 📦 Inventario del espacio"
    )

    if (
        inventario_requerido
        and not inventario_completado
    ):
        st.info(
            "Es el primer preventivo de este espacio. "
            "Haz ahora el inventario inicial una sola vez. "
            "En los próximos preventivos solo verás las cantidades."
        )

        st.caption(
            "La plantilla es solo una ayuda. Puedes cambiar nombres, "
            "eliminar filas y añadir todos los elementos que realmente "
            "existan en este espacio."
        )

        lineas_propuestas = [
            {
                "categoria": str(item[8] or "General").strip(),
                "elemento": str(item[2] or "").strip(),
                "cantidad": int(item[11] or 0),
            }
            for item in inventariables
        ]

        inventario_editado = st.data_editor(
            lineas_propuestas,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_order=[
                "categoria",
                "elemento",
                "cantidad",
            ],
            column_config={
                "categoria": st.column_config.TextColumn(
                    "Categoría",
                    help=(
                        "Ej.: Electricidad, Fontanería, "
                        "Carpintería, Mobiliario..."
                    ),
                ),
                "elemento": st.column_config.TextColumn(
                    "Elemento real",
                    help=(
                        "Concreta el tipo real: Downlight, "
                        "Ojo de buey, Puerta de aluminio..."
                    ),
                    required=True,
                ),
                "cantidad": st.column_config.NumberColumn(
                    "Cantidad",
                    min_value=0,
                    step=1,
                    format="%d",
                    required=True,
                ),
            },
            key=f"ot_espacio_censo_flexible_{num_ot}",
        )

        st.caption(
            "Ejemplo: puedes borrar ‘Luminarias’ y crear "
            "‘Downlight · 3’ + ‘Ojo de buey · 3’; o sustituir "
            "‘Puerta’ por ‘Puerta de aluminio · 1’ y "
            "‘Puerta de madera · 2’."
        )

        if st.button(
            "💾 Guardar inventario inicial",
            key=(
                f"ot_aula_guardar_censo_"
                f"{num_ot}"
            ),
            use_container_width=True,
            type="primary",
        ):
            try:
                if hasattr(inventario_editado, "to_dict"):
                    lineas_guardar = inventario_editado.to_dict(
                        orient="records"
                    )
                else:
                    lineas_guardar = list(
                        inventario_editado or []
                    )

                guardar_inventario_inicial_flexible_revision_aula(
                    revision_id=revision_id,
                    lineas_inventario=lineas_guardar,
                )

            except Exception as error:
                st.error(
                    "No se ha podido guardar "
                    "el inventario inicial."
                )
                st.caption(
                    str(error)
                )

            else:
                st.success(
                    "Inventario inicial real guardado. "
                    "A partir de ahora este será el inventario vivo "
                    "del espacio."
                )
                st.rerun()

        st.info(
            "Guarda primero el inventario inicial "
            "para continuar con la revisión preventiva."
        )
        return

    st.caption(
        "Inventario ya censado. "
        "En esta revisión se consulta "
        "el inventario vivo actual del espacio."
    )

    try:
        inventario_vivo = obtener_inventario_espacio(
            centro=centro_revision,
            edificio=edificio_revision,
            espacio=espacio_revision,
        )
    except Exception as error:
        inventario_vivo = []
        st.caption(
            "No se ha podido consultar el inventario vivo: "
            f"{error}"
        )

    if not inventario_vivo:
        st.info(
            "No hay elementos registrados actualmente "
            "en el inventario vivo de este espacio."
        )

    else:
        st.markdown(
            "**Inventario existente**"
        )

        lineas_inventario_vivo = []

        for item_inv in inventario_vivo:
            try:
                elemento_inv = str(
                    item_inv[2] or ""
                ).strip()
                cantidad_inv = int(
                    item_inv[3] or 0
                )
            except Exception:
                continue

            if not elemento_inv:
                continue

            lineas_inventario_vivo.append(
                (elemento_inv, cantidad_inv)
            )

        lineas_inventario_vivo.sort(
            key=lambda linea: normalizar_txt(
                linea[0]
            )
        )

        st.markdown(
            "\n".join(
                f"- {elemento}: **{cantidad}**"
                for elemento, cantidad in lineas_inventario_vivo
            )
        )

    # =====================================================
    # REVISIÓN GENERAL
    # =====================================================
    st.markdown(
        "---"
    )
    st.markdown(
        "### 👀 Revisión preventiva del espacio"
    )

    st.info(
        "Revisa visual y funcionalmente el espacio completo: "
        "iluminación, mecanismos, mobiliario, puertas, ventanas, "
        "climatización y cualquier otra anomalía visible."
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
            "🔧 Incidencias creadas: "
            + ", ".join(
                incidencias_creadas
            )
        )

    if estado_general.get(
        "completada"
    ):
        st.success(
            "✅ Revisión preventiva terminada. "
            "La OT ya puede finalizarse."
        )

    else:
        respuesta = st.radio(
            "¿Has detectado alguna anomalía?",
            [
                "No",
                "Sí",
            ],
            index=None,
            horizontal=True,
            key=(
                f"ot_aula_anomalia_"
                f"{num_ot}"
            ),
        )

        if respuesta == "No":
            if st.button(
                "✅ Guardar revisión sin anomalías",
                key=(
                    f"ot_aula_sin_anomalias_"
                    f"{num_ot}"
                ),
                use_container_width=True,
                type="primary",
            ):
                marcar_revision_general_aula_completada(
                    revision_id,
                    True,
                )

                st.success(
                    "Revisión preventiva registrada."
                )
                st.rerun()

        elif respuesta == "Sí":
            st.markdown(
                "#### 🔧 Anomalía detectada"
            )

            st.caption(
                "Se creará una incidencia normal, "
                "como las del QR. "
                "La ubicación del espacio ya viene asignada."
            )

            contador = int(
                st.session_state.get(
                    f"ot_aula_contador_inc_"
                    f"{num_ot}",
                    1,
                )
                or 1
            )

            descripcion_anomalia = (
                st.text_area(
                    "¿Qué ocurre?",
                    placeholder=(
                        "Ej.: downlight fundido, "
                        "puerta no cierra, "
                        "persiana averiada..."
                    ),
                    height=110,
                    key=(
                        f"ot_aula_desc_inc_"
                        f"{num_ot}_{contador}"
                    ),
                )
            )

            fotos_anomalia = (
                st.file_uploader(
                    "📷 Fotografías de la anomalía (opcional)",
                    type=[
                        "jpg",
                        "jpeg",
                        "png",
                    ],
                    accept_multiple_files=True,
                    key=(
                        f"ot_aula_fotos_inc_"
                        f"{num_ot}_{contador}"
                    ),
                    help=(
                        "Máximo 5 fotografías "
                        "y 5 MB por foto."
                    ),
                )
            )

            if st.button(
                "➕ Crear incidencia",
                key=(
                    f"ot_aula_crear_inc_"
                    f"{num_ot}_{contador}"
                ),
                use_container_width=True,
                type="primary",
            ):
                (
                    ok,
                    mensaje,
                    numero_inc,
                ) = (
                    crear_incidencia_desde_revision_aula(
                        revision_id=revision_id,
                        descripcion=descripcion_anomalia,
                        fotos=fotos_anomalia,
                    )
                )

                if not ok:
                    st.error(
                        mensaje
                    )

                else:
                    st.session_state[
                        f"ot_aula_contador_inc_"
                        f"{num_ot}"
                    ] = contador + 1

                    st.success(
                        mensaje
                    )
                    st.rerun()

            if incidencias_creadas:
                st.caption(
                    "Puedes crear otra incidencia. "
                    "Cuando estén todas registradas, "
                    "termina la revisión."
                )

                if st.button(
                    "✅ Terminar revisión preventiva",
                    key=(
                        f"ot_aula_terminar_revision_"
                        f"{num_ot}"
                    ),
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

    # =====================================================
    # RESULTADO
    # =====================================================
    st.markdown(
        "---"
    )
    st.markdown(
        "### 📊 Resultado de la revisión"
    )

    # Ya tenemos items y estado_general cargados en esta misma pantalla.
    # No repetimos consultas a base de datos solo para mostrar el resumen.
    if inventario_completado and inventario_vivo:
        unidades_total = sum(
            int(item_inv[3] or 0)
            for item_inv in inventario_vivo
            if len(item_inv) > 3
        )
    else:
        unidades_total = sum(
            int(item[11] or 0)
            for item in inventariables
        )

    incidencias_total = len(
        incidencias_creadas
    )

    revision_completada = bool(
        estado_general.get(
            "completada",
            False,
        )
    )

    r1, r2, r3 = st.columns(
        3
    )

    r1.metric(
        "📦 Unidades inventariadas",
        unidades_total,
    )

    r2.metric(
        "🔧 INC creadas",
        incidencias_total,
    )

    r3.metric(
        "👀 Revisión",
        (
            "Completa"
            if revision_completada
            else "Pendiente"
        ),
    )

    if revision_completada:
        st.success(
            "✅ Preventivo del espacio completo. "
            "La OT ya puede finalizarse."
        )
    else:
        st.warning(
            "La OT no puede finalizarse "
            "hasta terminar la revisión preventiva."
        )

def puede_finalizar_preventivo(num_ot, origen, desc, area=''):
    if es_preventivo_cuadro_ot(
        area,
        desc,
        num_ot
    ):
        return revision_cuadro_lista_para_cerrar(
            num_ot
        )

    if es_preventivo_aulas_ot(
        area,
        desc,
        num_ot
    ):
        return revision_aula_lista_para_cerrar(
            num_ot
        )

    if es_ot_preventiva(
        origen,
        desc,
        num_ot
    ):
        return checklist_preventivo_completo(
            num_ot
        )

    return True


def puede_finalizar_legionella(id_orden, area, origen, desc, num_ot=None):
    desc_txt = str(desc or "").upper()

    if "CORRECTIVO LEGIONELLA" in desc_txt:
        checklist = obtener_checklist_correctivo_legionella(num_ot)

        if not checklist:
            return False

        causa = str(checklist.get("causa_detectada") or "").strip()

        return (
            causa != ""
            and bool(checklist.get("nueva_medicion", 0))
            and float(checklist.get("temperatura_final", 0) or 0) >= 50
        )

    if es_ot_legionella(area, origen, desc):
        return st.session_state.get(f"legionella_guardada_{id_orden}", False)

    return True
def puede_corregir_ubicacion():
    return rol_actual() in [
        "admin",
        "administrador",
        "administracion",
        "administración",
    ]


def obtener_ubicacion_ot(id_orden):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT centro, edificio, planta, espacio
            FROM ordenes_trabajo
            WHERE id = ?
        """), (id_orden,))

        fila = cur.fetchone()

        if not fila:
            return "", "", "", ""

        return (
            str(fila[0] or "").strip(),
            str(fila[1] or "").strip(),
            str(fila[2] or "").strip(),
            str(fila[3] or "").strip(),
        )

    except Exception:
        return "", "", "", ""

    finally:
        conn.close()


def guardar_ubicacion_ot(
    id_orden,
    centro,
    edificio,
    planta,
    espacio,
):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE ordenes_trabajo
            SET centro = ?,
                edificio = ?,
                planta = ?,
                espacio = ?
            WHERE id = ?
        """), (
            centro,
            edificio,
            planta,
            espacio,
            id_orden,
        ))

        conn.commit()
        return True, "Ubicación corregida correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo corregir la ubicación: {e}"

    finally:
        conn.close()


def indice_opcion(opciones, valor):
    valor = str(valor or "").strip()

    if valor in opciones:
        return opciones.index(valor)

    return 0


def mostrar_correccion_ubicacion_ot(id_orden, modo):
    if not puede_corregir_ubicacion():
        return

    centro_actual, edificio_actual, planta_actual, espacio_actual = (
        obtener_ubicacion_ot(id_orden)
    )

    with st.expander("✏️ Corregir ubicación", expanded=False):
        st.caption(
            "Solo cambia la ubicación de esta OT. "
            "No modifica el estado, fotos, observaciones ni materiales."
        )

        centros = obtener_centros_espacios()

        if not centros:
            st.warning("No hay centros en el catálogo de espacios.")
            return

        centro_sel = st.selectbox(
            "Centro",
            centros,
            index=indice_opcion(centros, centro_actual),
            key=f"{modo}_corregir_centro_{id_orden}",
        )

        edificios = obtener_edificios_espacios(centro_sel)

        if not edificios:
            st.warning("No hay edificios para este centro.")
            return

        edificio_sel = st.selectbox(
            "Edificio",
            edificios,
            index=indice_opcion(edificios, edificio_actual),
            key=f"{modo}_corregir_edificio_{id_orden}",
        )

        plantas = obtener_plantas_espacios(
            centro_sel,
            edificio_sel,
        )

        if not plantas:
            st.warning("No hay plantas para este edificio.")
            return

        planta_sel = st.selectbox(
            "Planta",
            plantas,
            index=indice_opcion(plantas, planta_actual),
            key=f"{modo}_corregir_planta_{id_orden}",
        )

        espacios_filas = obtener_espacios_por_planta(
            centro_sel,
            edificio_sel,
            planta_sel,
        )

        espacios = []

        for fila_espacio in espacios_filas:
            if isinstance(fila_espacio, dict):
                nombre = str(
                    fila_espacio.get("espacio")
                    or fila_espacio.get("nombre")
                    or ""
                ).strip()
            elif isinstance(fila_espacio, (list, tuple)):
                nombre = str(
                    fila_espacio[0] if fila_espacio else ""
                ).strip()
            else:
                nombre = str(fila_espacio or "").strip()

            if nombre and nombre not in espacios:
                espacios.append(nombre)

        if not espacios:
            st.warning("No hay espacios para esta planta.")
            return

        espacio_sel = st.selectbox(
            "Espacio",
            espacios,
            index=indice_opcion(espacios, espacio_actual),
            key=f"{modo}_corregir_espacio_{id_orden}",
        )

        st.info(
            f"📍 {centro_sel} · {edificio_sel} · "
            f"{planta_sel} · {espacio_sel}"
        )

        confirmar = st.checkbox(
            "Confirmo que quiero modificar la ubicación",
            key=f"{modo}_confirmirma_ubicacion_{id_orden}",
        )

        if st.button(
            "💾 Guardar ubicación",
            key=f"{modo}_guardar_ubicacion_{id_orden}",
            use_container_width=True,
            type="primary",
        ):
            if not confirmar:
                st.warning("Marca primero la confirmación.")
                return

            ok, mensaje = guardar_ubicacion_ot(
                id_orden=id_orden,
                centro=centro_sel,
                edificio=edificio_sel,
                planta=planta_sel,
                espacio=espacio_sel,
            )

            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)

# =====================================================
# SELECTOR INTELIGENTE DE MATERIALES
# =====================================================

CATEGORIAS_MATERIAL_POR_PREFIJO = {
    # Códigos antiguos
    "FON": "Fontanería",
    "ELE": "Electricidad",
    "FER": "Ferretería",
    "CLI": "Climatización",
    "PIN": "Pintura",
    "LIM": "Limpieza",
    "SEG": "Seguridad",
    "JAR": "Jardinería",
    "INF": "Informática",
    "ACS": "ACS",
    "LEG": "Legionella",
    "EQU": "Equipamiento",
    "OTR": "Otros",

    # Códigos nuevos legibles
    "FONTANERIA": "Fontanería",
    "ELECTRICIDAD": "Electricidad",
    "FERRETERIA": "Ferretería",
    "CLIMATIZACION": "Climatización",
    "PINTURA": "Pintura",
    "LIMPIEZA": "Limpieza",
    "SEGURIDAD": "Seguridad",
    "JARDINERIA": "Jardinería",
    "LEGIONELLA": "Legionella",
    "CERRAJERIA": "Cerrajería",
    "MOBILIARIO": "Mobiliario",
    "ALBANILERIA": "Albañilería",
    "OTROS": "Otros",
}


ICONOS_CATEGORIA_MATERIAL = {
    "Todas": "📦",
    "Fontanería": "🔧",
    "Electricidad": "⚡",
    "Ferretería": "🔩",
    "Climatización": "❄️",
    "Pintura": "🎨",
    "Limpieza": "🧹",
    "Seguridad": "🦺",
    "Jardinería": "🌿",
    "Informática": "💻",
    "ACS": "🌡️",
    "Legionella": "💧",
    "Equipamiento": "🪑",
    "Cerrajería": "🔐",
    "Mobiliario": "🪑",
    "Albañilería": "🧱",
    "Otros": "📦",
}


def obtener_categoria_material_desde_codigo(codigo):
    """
    Obtiene la categoría usando el prefijo del código.

    Ejemplos:
        FON-PRPI-001 -> Fontanería
        ELE-PAEL-001 -> Electricidad
        FER-JUDE-001 -> Ferretería
    """
    codigo_txt = str(codigo or "").strip().upper()

    if not codigo_txt:
        return "Otros"

    prefijo = codigo_txt.split("-")[0]

    return CATEGORIAS_MATERIAL_POR_PREFIJO.get(
        prefijo,
        "Otros"
    )


def preparar_materiales_selector(materiales_select):
    """
    Convierte los materiales recibidos en una estructura uniforme.
    Mantiene compatibilidad con obtener_materiales_para_select().
    """
    materiales = []

    for fila in materiales_select or []:
        try:
            codigo = str(fila[0] or "").strip()
            nombre = str(fila[1] or "").strip()
            stock = float(fila[2] or 0)
            unidad = str(fila[3] or "").strip()
        except (IndexError, TypeError, ValueError):
            continue

        if not codigo:
            continue

        materiales.append({
            "codigo": codigo,
            "nombre": nombre or codigo,
            "stock": stock,
            "unidad": unidad,
            "categoria": obtener_categoria_material_desde_codigo(
                codigo
            ),
        })

    return materiales


def mostrar_ficha_material_seleccionado(material):
    """
    Muestra la información completa del material elegido.
    """
    if not material:
        return

    codigo = material["codigo"]

    try:
        datos_mat = obtener_material_por_codigo(codigo)
    except Exception as e:
        datos_mat = None
        st.caption(f"No se pudo cargar la ficha del material: {e}")

    st.markdown(f"#### {material['nombre']}")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("Código")
        st.markdown(f"**{codigo}**")

    with col2:
        st.caption("Stock disponible")
        st.markdown(
            f"**{material['stock']:g} "
            f"{material['unidad']}**"
        )

    icono_categoria = ICONOS_CATEGORIA_MATERIAL.get(
        material["categoria"],
        "📦"
    )

    st.caption(
        f"{icono_categoria} Categoría: "
        f"{material['categoria']}"
    )

    if material["stock"] <= 0:
        st.warning("Este material no tiene stock disponible.")
    elif material["stock"] <= 2:
        st.warning("Queda poco stock de este material.")

    if not datos_mat:
        return

    foto_data = datos_mat.get("foto_data")
    foto_ruta = datos_mat.get("foto")

    if foto_data:
        try:
            st.image(
                bytes(foto_data),
                width=220,
                caption=material["nombre"]
            )
        except Exception:
            st.caption("Foto del material no disponible.")

    elif foto_ruta:
        try:
            st.image(
                foto_ruta,
                width=220,
                caption=material["nombre"]
            )
        except Exception:
            st.caption("Foto del material no disponible.")

    ubicacion = str(
        datos_mat.get("ubicacion")
        or datos_mat.get("espacio")
        or ""
    ).strip()

    centro_material = str(
        datos_mat.get("centro")
        or ""
    ).strip()

    edificio_material = str(
        datos_mat.get("edificio")
        or ""
    ).strip()

    partes_ubicacion = [
        parte
        for parte in [
            centro_material,
            edificio_material,
            ubicacion,
        ]
        if parte
    ]

    if partes_ubicacion:
        st.info(
            "📍 " + " · ".join(partes_ubicacion)
        )


def selector_material_inteligente(
    materiales,
    id_orden,
    indice,
    modo="operario",
):
    """
    Selector de recambios/materiales para la OT.

    - Busca mientras se escribe, sin Enter, si streamlit-keyup está instalado.
    - Admite fragmentos y varias palabras: "cerr taq", "rac 25", "sil neg".
    - Ignora mayúsculas/minúsculas y acentos.
    - Busca en nombre, código, categoría y unidad.
    - La búsqueda escrita tiene prioridad sobre una categoría que haya quedado
      seleccionada previamente.
    - Muestra primero materiales con stock disponible.
    """
    if not materiales:
        st.info("No hay materiales disponibles.")
        return None

    categorias_disponibles = sorted({
        material["categoria"]
        for material in materiales
    })

    categorias = ["Todas"] + categorias_disponibles

    categoria_sel = st.selectbox(
        "Categoría",
        categorias,
        format_func=lambda categoria: (
            f"{ICONOS_CATEGORIA_MATERIAL.get(categoria, '📦')} "
            f"{categoria}"
        ),
        key=(
            f"{modo}_categoria_material_"
            f"{id_orden}_{indice}"
        ),
    )

    clave_busqueda = (
        f"{modo}_buscar_material_"
        f"{id_orden}_{indice}"
    )

    if st_keyup is not None:
        texto_busqueda = st_keyup(
            "🔎 Buscar recambio",
            key=clave_busqueda,
            placeholder=(
                "Ej.: gri · cerr taq · rac 25 · sil neg · down..."
            ),
            debounce=350,
        )
    else:
        texto_busqueda = st.text_input(
            "🔎 Buscar recambio",
            key=clave_busqueda,
            placeholder=(
                "Ej.: gri · cerr taq · rac 25 · sil neg · down..."
            ),
        )

    buscar_txt = normalizar_txt(texto_busqueda)
    terminos = [
        termino
        for termino in buscar_txt.split()
        if termino
    ]

    materiales_filtrados = list(materiales)

    # Si el operario está escribiendo, la búsqueda manda.
    # Así una categoría olvidada no oculta un recambio válido.
    if not terminos and categoria_sel != "Todas":
        materiales_filtrados = [
            material
            for material in materiales_filtrados
            if material["categoria"] == categoria_sel
        ]

    if terminos:
        encontrados = []

        for material in materiales_filtrados:
            texto_material = normalizar_txt(
                " ".join([
                    str(material.get("nombre") or ""),
                    str(material.get("codigo") or ""),
                    str(material.get("categoria") or ""),
                    str(material.get("unidad") or ""),
                ])
            )

            if all(
                termino in texto_material
                for termino in terminos
            ):
                encontrados.append(material)

        materiales_filtrados = encontrados

    # Primero lo que realmente se puede usar; después orden alfabético.
    materiales_filtrados = sorted(
        materiales_filtrados,
        key=lambda material: (
            0 if float(material.get("stock") or 0) > 0 else 1,
            normalizar_txt(material["nombre"]),
            normalizar_txt(material["codigo"]),
        )
    )

    if terminos:
        st.caption(
            f"🔎 {len(materiales_filtrados)} coincidencia(s). "
            "La búsqueda está mirando todos los materiales."
        )
    else:
        st.caption(
            f"{len(materiales_filtrados)} materiales disponibles con estos filtros."
        )

    if not materiales_filtrados:
        st.warning(
            "No se encontraron recambios/materiales con esa búsqueda."
        )
        return None

    codigos_filtrados = [
        material["codigo"]
        for material in materiales_filtrados
    ]

    materiales_por_codigo = {
        material["codigo"]: material
        for material in materiales_filtrados
    }

    codigo_sel = st.selectbox(
        "Material",
        codigos_filtrados,
        format_func=lambda codigo: (
            f"{'✅' if materiales_por_codigo[codigo]['stock'] > 0 else '⚠️'} "
            f"{materiales_por_codigo[codigo]['nombre']} · "
            f"{materiales_por_codigo[codigo]['categoria']} · "
            f"Stock: {materiales_por_codigo[codigo]['stock']:g} "
            f"{materiales_por_codigo[codigo]['unidad']}"
        ),
        key=(
            f"{modo}_material_ot_"
            f"{id_orden}_{indice}"
        ),
    )

    material_sel = materiales_por_codigo.get(codigo_sel)

    mostrar_ficha_material_seleccionado(
        material_sel
    )

    stock_disponible = float(
        material_sel.get("stock") or 0
    ) if material_sel else 0.0

    cantidad_material = st.number_input(
        "Cantidad usada",
        min_value=0.0,
        max_value=max(stock_disponible, 0.0) if stock_disponible > 0 else 0.0,
        step=1.0,
        disabled=stock_disponible <= 0,
        key=(
            f"{modo}_cantidad_material_ot_"
            f"{id_orden}_{indice}"
        ),
    )

    if stock_disponible <= 0:
        st.caption(
            "⛔ Sin stock: no se puede descontar este material."
        )

    return {
        "codigo": codigo_sel,
        "cantidad": cantidad_material,
    }



def preparar_siguiente_mision_corazon(num_ot, id_orden, modo="operario"):
    """
    Libera la OT finalizada y solicita al Corazón una nueva misión.

    No calcula prioridades aquí: únicamente deja la interfaz preparada
    para que ui_operario vuelva a ejecutar latido_corazon().
    """
    if str(modo or "").strip().lower() != "operario":
        return

    st.session_state.pop("operario_ot_abierta_id", None)
    st.session_state["corazon_mision_finalizada"] = {
        "id": id_orden,
        "numero_ot": str(num_ot or "").strip(),
    }
    st.session_state["recalcular_corazon"] = True


def mostrar_tarjeta_ot(
    fila,
    materiales_select,
    operario_sel,
    modo="operario"
):
    (
        id_orden,
        num_ot,
        desc,
        est,
        fecha,
        centro,
        edificio,
        espacio,
        area,
        prioridad,
        operario,
        origen,
        solicitante,
        fecha_origen,
        foto,
        tipo_solicitante,
        observaciones_estado,
    ) = descomponer_orden_operario(fila)

    if es_operario() and normalizar_operario_nombre(operario) != normalizar_operario_nombre(nombre_operario_actual()):
        return

    # La fila ligera histórica no incluye siempre planta.
    # Al abrir una única OT podemos consultar su ubicación real.
    (
        centro_real,
        edificio_real,
        planta_real,
        espacio_real,
    ) = obtener_ubicacion_ot(
        id_orden
    )

    centro_mostrar = (
        centro_real
        or centro
        or "-"
    )

    edificio_mostrar = (
        edificio_real
        or edificio
        or "-"
    )

    planta_mostrar = (
        planta_real
        or "-"
    )

    espacio_mostrar = (
        espacio_real
        or espacio
        or "-"
    )

    estado_icono = {
        "Abierta": "🔴",
        "En curso": "🟠",
        "Pendiente material": "📦"
    }.get(est, "⚪")

    desc_corta = str(desc or "").replace("\n", " ").strip()

    if len(desc_corta) > 45:
        desc_corta = desc_corta[:45] + "..."

    titulo = (
        f"{estado_icono} `{num_ot}` | {prioridad} | "
        f"{centro or '-'} · {espacio or '-'} | {desc_corta}"
    )

    with st.expander(titulo, expanded=True):
        st.markdown(
            f"### {estado_icono} "
            f"{codigo_ot_no_traducible(num_ot)}",
            unsafe_allow_html=True,
        )
        st.markdown(f"**{prioridad}** | {area or '-'}")
        st.markdown(f"{desc}")
        st.caption(
            f"🏢 {centro_mostrar} · "
            f"{edificio_mostrar} · "
            f"{planta_mostrar} · "
            f"{espacio_mostrar}"
        )
        st.caption(f"Estado actual: {est}")

        if observaciones_estado:
            st.info(f"📝 Observación estado: {observaciones_estado}")

        st.caption(f"👷 Operario: {operario or '-'}")
        st.caption(f"📌 Solicitante: {tipo_solicitante or 'Operarios'}")

        if solicitante:
            st.caption(f"Nombre solicitante: {solicitante}")

        if fecha_origen:
            st.caption(f"Fecha origen: {fecha_origen}")
        mostrar_correccion_ubicacion_ot(
            id_orden=id_orden,
            modo=modo,
        )
        # -------------------------------------------------
        # FOTOS DE LA OT · CARGA BAJO DEMANDA
        # -------------------------------------------------
        clave_fotos_ot = (
            f"{modo}_mostrar_fotos_ot_{id_orden}"
        )

        mostrar_fotos_ot = bool(
            st.session_state.get(
                clave_fotos_ot,
                False,
            )
        )

        if not mostrar_fotos_ot:
            if st.button(
                "📷 Ver fotos de la OT",
                key=f"{modo}_ver_fotos_ot_{id_orden}",
                use_container_width=True,
            ):
                st.session_state[
                    clave_fotos_ot
                ] = True
                st.rerun()

        else:
            if st.button(
                "🙈 Ocultar fotos de la OT",
                key=f"{modo}_ocultar_fotos_ot_{id_orden}",
                use_container_width=True,
            ):
                st.session_state[
                    clave_fotos_ot
                ] = False
                st.rerun()

            try:
                fotos_db = obtener_fotos_ot(
                    num_ot
                )

                if fotos_db:
                    cols_fotos = st.columns(3)

                    for i, (
                        nombre_foto,
                        foto_data,
                    ) in enumerate(
                        fotos_db
                    ):
                        with cols_fotos[
                            i % 3
                        ]:
                            try:
                                st.image(
                                    bytes(
                                        foto_data
                                    ),
                                    caption=(
                                        nombre_foto
                                        or f"Foto {i + 1}"
                                    ),
                                    use_container_width=True,
                                )
                            except Exception as error:
                                st.caption(
                                    "📷 Foto no disponible: "
                                    f"{error}"
                                )

                elif (
                    foto
                    and str(
                        foto
                    ).strip().lower()
                    != "postgres_fotos"
                ):
                    fotos_legacy = [
                        ruta.strip()
                        for ruta in str(
                            foto
                        ).split("|")
                        if ruta.strip()
                    ]

                    if fotos_legacy:
                        cols_fotos = st.columns(3)

                        for i, ruta_foto in enumerate(
                            fotos_legacy
                        ):
                            with cols_fotos[
                                i % 3
                            ]:
                                try:
                                    st.image(
                                        ruta_foto,
                                        caption=f"Foto {i + 1}",
                                        use_container_width=True,
                                    )
                                except Exception:
                                    st.caption(
                                        "📷 Foto no disponible."
                                    )
                    else:
                        st.info(
                            "Esta OT no tiene fotos."
                        )

                else:
                    st.info(
                        "Esta OT no tiene fotos."
                    )

            except Exception as error:
                st.caption(
                    "📷 No se pudieron cargar las fotos: "
                    f"{error}"
                )

        # -------------------------------------------------
        # AÑADIR FOTO A LA OT · SIN FINALIZARLA
        # -------------------------------------------------
        with st.expander(
            "📸 Añadir foto a esta OT",
            expanded=False,
        ):
            st.caption(
                "La fotografía se guarda directamente en esta OT. "
                "No cambia su estado ni la finaliza."
            )

            clave_version_foto_ot = (
                f"{modo}_version_foto_ot_{id_orden}"
            )

            version_foto_ot = int(
                st.session_state.get(
                    clave_version_foto_ot,
                    0,
                )
                or 0
            )

            clave_version_guardada = (
                f"{modo}_version_foto_guardada_ot_{id_orden}"
            )

            version_guardada = st.session_state.get(
                clave_version_guardada
            )

            foto_camara = st.camera_input(
                "📸 Hacer foto ahora",
                key=(
                    f"{modo}_camara_ot_{id_orden}_"
                    f"{version_foto_ot}"
                ),
            )

            foto_archivo = st.file_uploader(
                "🖼️ O elegir una foto del dispositivo",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=False,
                key=(
                    f"{modo}_anadir_foto_ot_{id_orden}_"
                    f"{version_foto_ot}"
                ),
                help=f"Máximo {MAX_MB_FOTO_OT} MB.",
            )

            foto_nueva = foto_camara or foto_archivo

            error_foto_nueva = ""

            if foto_nueva is not None:
                try:
                    tamano_foto_nueva = int(
                        getattr(
                            foto_nueva,
                            "size",
                            0,
                        )
                        or 0
                    )
                except Exception:
                    tamano_foto_nueva = 0

                if tamano_foto_nueva > MAX_MB_FOTO_OT * 1024 * 1024:
                    error_foto_nueva = (
                        f"La fotografía supera {MAX_MB_FOTO_OT} MB."
                    )
                    st.error(
                        error_foto_nueva
                    )

            foto_actual_guardada = (
                foto_nueva is not None
                and version_guardada == version_foto_ot
            )

            if foto_actual_guardada:
                st.success(
                    "Fotografía guardada en la OT. "
                    "Puedes preparar otra captura."
                )

            if st.button(
                "💾 Guardar foto en la OT",
                key=(
                    f"{modo}_guardar_foto_ot_{id_orden}_"
                    f"{version_foto_ot}"
                ),
                use_container_width=True,
                type="primary",
                disabled=(
                    foto_nueva is None
                    or bool(error_foto_nueva)
                    or foto_actual_guardada
                ),
            ):
                try:
                    contenido_foto = foto_nueva.getvalue()

                    if len(contenido_foto) > MAX_MB_FOTO_OT * 1024 * 1024:
                        st.error(
                            f"La fotografía supera {MAX_MB_FOTO_OT} MB."
                        )
                    else:
                        nombres_existentes = obtener_nombres_fotos_ot(
                            num_ot
                        )

                        secuencia = len(
                            nombres_existentes
                        ) + 1

                        nombre_original = limpiar_nombre_archivo(
                            getattr(
                                foto_nueva,
                                "name",
                                "foto.jpg",
                            )
                        )

                        nombre_foto_nueva = limpiar_nombre_archivo(
                            f"{num_ot}_OT_{id_orden}_"
                            f"{secuencia}_{nombre_original}"
                        )

                        while nombre_foto_nueva in nombres_existentes:
                            secuencia += 1
                            nombre_foto_nueva = limpiar_nombre_archivo(
                                f"{num_ot}_OT_{id_orden}_"
                                f"{secuencia}_{nombre_original}"
                            )

                        guardar_foto_ot(
                            numero_ot=num_ot,
                            nombre_foto=nombre_foto_nueva,
                            foto_data=contenido_foto,
                        )

                        st.session_state[
                            clave_fotos_ot
                        ] = True

                        st.session_state[
                            clave_version_guardada
                        ] = version_foto_ot

                        st.success(
                            "Fotografía guardada en la OT."
                        )

                except Exception as error:
                    st.error(
                        "No se ha podido guardar la fotografía: "
                        f"{error}"
                    )

            if (
                st.session_state.get(
                    clave_version_guardada
                ) == version_foto_ot
            ):
                st.button(
                    "📸 Preparar otra foto",
                    key=(
                        f"{modo}_otra_foto_ot_{id_orden}_"
                        f"{version_foto_ot}"
                    ),
                    use_container_width=True,
                    on_click=preparar_nueva_captura_foto_ot,
                    args=(
                        clave_version_foto_ot,
                    ),
                )

        # -----------------------------
        # CONTROLES INTELIGENTES DE OT
        # -----------------------------
        if es_preventivo_cuadro_ot(
            area,
            desc,
            num_ot
        ):
            mostrar_preventivo_cuadro_operario(
                num_ot=num_ot,
                operario=operario,
            )

        elif es_preventivo_aulas_ot(
            area,
            desc,
            num_ot
        ):
            mostrar_preventivo_aula_operario(
                num_ot=num_ot,
                operario=operario,
            )

        elif es_ot_preventiva(origen, desc, num_ot):
            mostrar_checklist_preventivo_operario(
                num_ot=num_ot,
                desc=desc,
                operario=operario
            )

        elif es_ot_legionella(area, origen, desc):
            if "CORRECTIVO LEGIONELLA" in str(desc or "").upper():
                mostrar_checklist_correctivo_legionella_operario(
                    num_ot=num_ot,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    desc=desc,
                    planta=planta_mostrar,
                )
            else:
                mostrar_ejecucion_legionella_operario(
                    id_orden=id_orden,
                    num_ot=num_ot,
                    desc=desc,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    operario=operario,
                    planta=planta_mostrar,
                )

        # -------------------------------------------------
        # PEDIDO DE MATERIAL VINCULADO A ESTA OT
        # -------------------------------------------------
        if es_operario():
            mostrar_pedido_material_desde_ot(
                id_orden=id_orden,
                numero_ot=num_ot,
                descripcion_ot=desc,
                centro=centro_mostrar,
                edificio=edificio_mostrar,
                planta=planta_mostrar,
                espacio=espacio_mostrar,
                operario=operario,
                prioridad=prioridad or "Media",
            )

        # -------------------------------------------------
        # PENDIENTE MATERIAL · REAPERTURA POR EL OPERARIO
        # -------------------------------------------------
        estado_normalizado = normalizar_txt(est)

        if (
            es_operario()
            and estado_normalizado == "pendiente material"
        ):
            st.markdown("### 📦 Material pendiente")
            st.info(
                "Esta OT está pendiente de material. "
                "Si el material ya ha llegado, puedes reabrirla "
                "y continuar el trabajo sin esperar a Administración."
            )

            if st.button(
                "📦 Material recibido · Reabrir OT",
                key=f"{modo}_material_recibido_reabrir_{id_orden}",
                use_container_width=True,
                type="primary",
            ):
                actualizar_estado(
                    id_orden,
                    "Abierta",
                    "Material recibido. OT reabierta por el operario.",
                )

                st.session_state["recalcular_corazon"] = True
                st.rerun()

        st.markdown("### 📝 Estado y observaciones")

        observacion_estado_nueva = st.text_area(
            "Observación del estado",
            value=str(observaciones_estado or ""),
            placeholder="Ejemplo: En curso porque falta acceder al aula, pendiente de pieza, esperando proveedor...",
            key=f"{modo}_observacion_estado_{id_orden}"
        )

        b1, b2, b3 = st.columns(3)

        with b1:
            if st.button("▶\nEn curso", key=f"{modo}_curso_rapido_{id_orden}", use_container_width=True):
                actualizar_estado(id_orden, "En curso", observacion_estado_nueva)
                st.rerun()

        with b2:
            if st.button("📦\nMaterial", key=f"{modo}_mat_rapido_{id_orden}", use_container_width=True):
                actualizar_estado(id_orden, "Pendiente material", observacion_estado_nueva)
                st.rerun()

        with b3:
            if st.button("✔\nFinalizar", key=f"{modo}_fin_rapido_{id_orden}", use_container_width=True):
                st.session_state[f"{modo}_confirmar_fin_rapido_{id_orden}"] = True
                st.rerun()

        if st.session_state.get(f"{modo}_confirmar_fin_rapido_{id_orden}", False):
            st.warning(f"¿Seguro que quieres finalizar {num_ot}?")

            c1, c2 = st.columns(2)

            with c1:
                if st.button("✔\nSí, finalizar", key=f"{modo}_si_fin_rapido_{id_orden}", use_container_width=True):
                    if not puede_finalizar_preventivo(num_ot, origen, desc, area):
                        st.error("No puedes finalizar esta preventiva hasta completar su revisión.")
                    elif not puede_finalizar_legionella(id_orden, area, origen, desc, num_ot):
                        st.error("No puedes finalizar esta OT de Legionella hasta completar el control/checklist correspondiente.")
                    else:
                        actualizar_observaciones_estado(id_orden, observacion_estado_nueva)
                        finalizar_orden(id_orden, "")
                        st.session_state[f"{modo}_confirmar_fin_rapido_{id_orden}"] = False
                        st.session_state.pop(f"legionella_guardada_{id_orden}", None)
                        preparar_siguiente_mision_corazon(num_ot, id_orden, modo)
                        st.rerun()

            with c2:
                if st.button("❌\nCancelar", key=f"{modo}_no_fin_rapido_{id_orden}", use_container_width=True):
                    st.session_state[f"{modo}_confirmar_fin_rapido_{id_orden}"] = False
                    st.rerun()

        with st.expander(f"Más opciones {num_ot}"):
            observaciones_fin = st.text_area(
                "Observaciones de cierre",
                key=f"{modo}_obs_operario_{id_orden}"
            )

            usar_material = st.checkbox(
                "Descontar material del inventario al cerrar",
                key=f"{modo}_usar_material_{id_orden}"
            )

            materiales_ot = []

            if usar_material:
                materiales_preparados = preparar_materiales_selector(
                    materiales_select
                )

                if materiales_preparados:
                    num_materiales = st.number_input(
                        "Número de materiales usados",
                        min_value=1,
                        max_value=10,
                        value=1,
                        step=1,
                        key=(
                            f"{modo}_num_materiales_ot_"
                            f"{id_orden}"
                        ),
                    )

                    st.markdown("### 📦 Materiales usados")

                    for i in range(int(num_materiales)):
                        with st.container(border=True):
                            st.markdown(
                                f"### Material {i + 1}"
                            )

                            material_usado = (
                                selector_material_inteligente(
                                    materiales=materiales_preparados,
                                    id_orden=id_orden,
                                    indice=i,
                                    modo=modo,
                                )
                            )

                            if material_usado:
                                materiales_ot.append(
                                    material_usado
                                )

                else:
                    st.info(
                        "No hay materiales dados de alta "
                        "en Inventario."
                    )

            fotos_cierre = st.file_uploader(
                "📷 Fotos del trabajo realizado",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=f"{modo}_fotos_cierre_{id_orden}",
                help=(
                    f"Máximo {MAX_FOTOS_CIERRE_OT} fotos "
                    f"y {MAX_MB_FOTO_OT} MB por foto."
                ),
            )

            errores_fotos_cierre = validar_fotos_cierre_ot(
                fotos_cierre
            )

            if errores_fotos_cierre:
                for error_foto in errores_fotos_cierre:
                    st.error(
                        error_foto
                    )

            elif fotos_cierre:
                st.caption(
                    f"📷 {len(fotos_cierre)} "
                    "foto(s) preparada(s) para guardar al cerrar."
                )

            if st.button(
                f"Finalizar con observaciones/material {num_ot}",
                key=f"{modo}_fin_completo_operario_{id_orden}",
                use_container_width=True
            ):
                if errores_fotos_cierre:
                    st.error(
                        "Corrige las fotografías antes de continuar."
                    )
                else:
                    st.session_state[
                        f"{modo}_materiales_confirmados_{id_orden}"
                    ] = materiales_ot.copy()

                    st.session_state[
                        f"{modo}_confirmar_fin_completo_{id_orden}"
                    ] = True

                    st.rerun()

            if st.session_state.get(f"{modo}_confirmar_fin_completo_{id_orden}", False):
                st.warning(f"¿Seguro que quieres finalizar {num_ot} con estas observaciones/material?")

                c1, c2 = st.columns(2)

                with c1:
                    if st.button("✔\nSí, finalizar", key=f"{modo}_si_fin_completo_{id_orden}", use_container_width=True):

                        if not puede_finalizar_preventivo(num_ot, origen, desc, area):
                            st.error("No puedes finalizar esta preventiva hasta completar su revisión.")

                        elif not puede_finalizar_legionella(id_orden, area, origen, desc, num_ot):
                            st.error("No puedes finalizar esta OT de Legionella hasta completar el control/checklist correspondiente.")

                        elif usar_material and materiales_select:
                            materiales_confirmados = st.session_state.get(
                                f"{modo}_materiales_confirmados_{id_orden}",
                                materiales_ot
                            )

                            materiales_validos = [
                                m for m in materiales_confirmados
                                if m["cantidad"] > 0
                            ]

                            if not materiales_validos:
                                st.warning("Indica al menos un material con cantidad mayor que 0.")
                            else:
                                errores = []

                                for m in materiales_validos:
                                    ok, mensaje = registrar_movimiento_inventario(
                                        codigo_material=m["codigo"],
                                        tipo_movimiento="Salida",
                                        cantidad=m["cantidad"],
                                        motivo=f"Consumo en OT {num_ot}",
                                        numero_ot=num_ot,
                                        operario=operario_sel
                                    )

                                    if not ok:
                                        errores.append(f"{m['codigo']}: {mensaje}")

                                if errores:
                                    for error in errores:
                                        st.error(error)
                                else:
                                    (
                                        fotos_ok,
                                        fotos_guardadas,
                                        error_fotos,
                                    ) = guardar_fotos_cierre_ot(
                                        numero_ot=num_ot,
                                        id_orden=id_orden,
                                        fotos=fotos_cierre,
                                    )

                                    if not fotos_ok:
                                        st.error(
                                            "No se han podido guardar "
                                            "las fotos de cierre: "
                                            f"{error_fotos}"
                                        )
                                    else:
                                        actualizar_observaciones_estado(
                                            id_orden,
                                            observacion_estado_nueva,
                                        )

                                        finalizar_orden(
                                            id_orden,
                                            observaciones_fin,
                                        )

                                        st.session_state[
                                            f"{modo}_confirmar_fin_completo_{id_orden}"
                                        ] = False

                                        st.session_state.pop(
                                            f"{modo}_materiales_confirmados_{id_orden}",
                                            None,
                                        )

                                        st.session_state.pop(
                                            f"legionella_guardada_{id_orden}",
                                            None,
                                        )

                                        preparar_siguiente_mision_corazon(
                                            num_ot,
                                            id_orden,
                                            modo,
                                        )

                                        st.rerun()

                        else:
                            (
                                fotos_ok,
                                fotos_guardadas,
                                error_fotos,
                            ) = guardar_fotos_cierre_ot(
                                numero_ot=num_ot,
                                id_orden=id_orden,
                                fotos=fotos_cierre,
                            )

                            if not fotos_ok:
                                st.error(
                                    "No se han podido guardar "
                                    "las fotos de cierre: "
                                    f"{error_fotos}"
                                )
                            else:
                                actualizar_observaciones_estado(
                                    id_orden,
                                    observacion_estado_nueva,
                                )

                                finalizar_orden(
                                    id_orden,
                                    observaciones_fin,
                                )

                                st.session_state[
                                    f"{modo}_confirmar_fin_completo_{id_orden}"
                                ] = False

                                st.session_state.pop(
                                    f"{modo}_materiales_confirmados_{id_orden}",
                                    None,
                                )

                                st.session_state.pop(
                                    f"legionella_guardada_{id_orden}",
                                    None,
                                )

                                preparar_siguiente_mision_corazon(
                                    num_ot,
                                    id_orden,
                                    modo,
                                )

                                st.rerun()

                with c2:
                    if st.button("❌\nCancelar", key=f"{modo}_no_fin_completo_{id_orden}", use_container_width=True):
                        st.session_state[f"{modo}_confirmar_fin_completo_{id_orden}"] = False
                        st.session_state.pop(f"{modo}_materiales_confirmados_{id_orden}", None)
                        st.rerun()
