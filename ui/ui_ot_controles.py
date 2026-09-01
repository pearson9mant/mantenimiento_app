import streamlit as st
from datetime import date, datetime

from modules.ordenes import (
    obtener_vinculacion_ot,
    crear_orden,
    obtener_siguiente_numero_ot,
    guardar_foto_ot,
)

from database.db import conectar, _sql

from ui.procedimientos_legionella import (
    mostrar_control_sala_acs,
    mostrar_temperatura_simple,
    mostrar_cloro_residual,
    mostrar_control_afs,
    mostrar_control_acs_terminal,
    mostrar_control_terminal_completo,
    mostrar_control_depositos_solares,
    mostrar_revision_trimestral_acumulador_acs,
    mostrar_revision_visual,
    mostrar_purga,
    mostrar_ruta_semanal_purgas_p9,
    mostrar_puesta_en_servicio_acumulador_acs,
    mostrar_procedimiento_choque_termico,
    mostrar_limpieza_desinfeccion,
    mostrar_control_generico,
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    obtener_checklist_preventivo_detallado,
    actualizar_item_checklist_preventivo,
    guardar_checklist_preventivo_completo,
    crear_checklist_preventivo,
    crear_correctivas_checklist_preventivo,
    resumen_checklist_preventivo,
)

from ui.ui_legionella import (
    registrar_control,
    leer_df,
    obtener_checklist_correctivo_legionella,
    guardar_checklist_correctivo_legionella,
    borrar_checklist_correctivo_legionella,
)


def nombre_operario_actual():
    return str(
        st.session_state.get("operario_activo")
        or st.session_state.get("usuario")
        or ""
    ).strip()


def limpiar_tarea_preventiva(texto):
    return str(texto or "").strip()


def extraer_datos_ot_legionella(descripcion, espacio):
    texto = str(descripcion or "").strip()
    partes = [p.strip() for p in texto.split(" - ")]

    tarea = ""
    punto = str(espacio or "").strip()

    if texto.upper().startswith("CORRECTIVO LEGIONELLA"):
        if len(partes) >= 2:
            tarea = partes[1].strip()
        if len(partes) >= 4:
            punto = partes[-1].strip()
        return tarea, punto

    if len(partes) >= 3:
        tarea = partes[1].strip()
        punto = partes[2].strip()
    elif len(partes) == 2:
        tarea = partes[1].strip()

    return tarea, punto


def mostrar_ejecucion_legionella_operario(
    id_orden,
    num_ot,
    desc,
    centro,
    edificio,
    espacio,
    operario,
    planta="",
):
    st.markdown("### 💧 Ejecutar control Legionella")

    # -------------------------------------------------
    # VINCULACIÓN SEGURA DE TAREA LEGIONELLA
    #
    # 1. Si la OT tiene id_tarea_legionella, usamos esa fila exacta.
    # 2. Si es una OT antigua sin vínculo, mantenemos compatibilidad
    #    leyendo la tarea desde la descripción como hasta ahora.
    # -------------------------------------------------
    tarea_desc, punto_nombre_desc = extraer_datos_ot_legionella(
        desc,
        espacio,
    )

    tarea = str(tarea_desc or "").strip()
    punto_nombre = str(
        punto_nombre_desc
        or espacio
        or ""
    ).strip()

    punto = None

    try:
        vinculacion = obtener_vinculacion_ot(
            numero_ot=num_ot,
            id_orden=id_orden,
        )

        id_punto_legionella = vinculacion.get(
            "id_punto_legionella"
        )

        id_tarea_legionella = vinculacion.get(
            "id_tarea_legionella"
        )

        # -------------------------------------------------
        # TAREA EXACTA DE PLANIFICACIÓN
        # -------------------------------------------------
        if id_tarea_legionella:
            df_tarea_vinculada = leer_df(
                """
                SELECT id,
                       punto_id,
                       centro,
                       edificio,
                       planta,
                       punto,
                       tarea,
                       tipo_control,
                       activo
                FROM legionella_tareas
                WHERE id = ?
                LIMIT 1
                """,
                (int(id_tarea_legionella),),
            )

            if not df_tarea_vinculada.empty:
                fila_tarea = df_tarea_vinculada.iloc[0]

                tarea_vinculada = str(
                    fila_tarea.get("tarea")
                    or ""
                ).strip()

                punto_vinculado = str(
                    fila_tarea.get("punto")
                    or ""
                ).strip()

                if tarea_vinculada:
                    tarea = tarea_vinculada

                if punto_vinculado:
                    punto_nombre = punto_vinculado

                if not str(planta or "").strip():
                    planta = str(
                        fila_tarea.get("planta")
                        or ""
                    ).strip()

                # Si por algún motivo la OT antigua no conserva punto_id,
                # recuperamos también el punto desde la tarea vinculada.
                if not id_punto_legionella:
                    try:
                        id_punto_legionella = int(
                            fila_tarea.get("punto_id")
                        )
                    except Exception:
                        id_punto_legionella = None

        # -------------------------------------------------
        # PUNTO EXACTO DE LEGIONELLA
        # -------------------------------------------------
        if id_punto_legionella:
            puntos_df = leer_df(
                """
                SELECT *
                FROM legionella_puntos
                WHERE id = ?
                  AND activo = 1
                ORDER BY id DESC
                """,
                (int(id_punto_legionella),),
            )

            if not puntos_df.empty:
                punto = puntos_df.iloc[0].to_dict()

                nombre_punto_real = str(
                    punto.get("nombre_punto")
                    or ""
                ).strip()

                if nombre_punto_real:
                    punto_nombre = nombre_punto_real

                if not str(planta or "").strip():
                    planta = str(
                        punto.get("planta")
                        or ""
                    ).strip()

    except Exception:
        punto = None

    if not tarea:
        st.warning(
            "No se ha podido identificar la tarea de Legionella "
            "desde la vinculación ni desde la OT."
        )
        return False

    tarea_txt = str(tarea or "").strip()

    if tarea_txt.lower() in [
        "sala acs completa",
        "control sala acs",
    ]:
        tarea = "Control sala ACS"

    if punto is None:
        puntos_df = leer_df(
            """
            SELECT *
            FROM legionella_puntos
            WHERE centro = ?
              AND activo = 1
            ORDER BY id DESC
            """,
            (centro,),
        )

        if not puntos_df.empty:
            puntos_df = puntos_df[
                puntos_df["nombre_punto"]
                .fillna("")
                .str.lower()
                .str.strip()
                == str(punto_nombre).lower().strip()
            ]

        if puntos_df.empty:
            st.warning(
                f"No se ha encontrado el punto '{punto_nombre}'. "
                "Revisa que esta OT esté vinculada al punto Legionella."
            )
            return False

        punto = puntos_df.iloc[0].to_dict()

        if not str(planta or "").strip():
            planta = str(
                punto.get("planta")
                or ""
            ).strip()

    st.caption(
        f"📍 {centro} · {edificio} · "
        f"{planta or '-'} · {punto_nombre}"
    )
    st.caption(f"🧪 Tarea: {tarea}")

    terminales = int(punto.get("numero_terminales", 1) or 1)

    if terminales > 1:
        st.info(f"🚿 Terminales incluidos en este punto: {terminales}")

    if tarea == "Control sala ACS":
        resultado_procedimiento = mostrar_control_sala_acs(id_orden)

    elif tarea in [
        "Temperatura acumulador",
        "Temperatura retorno",
        "Temperatura punto terminal",
        "Temperatura impulsión ACS",
    ]:
        resultado_procedimiento = mostrar_temperatura_simple(id_orden, tarea)

    elif tarea == "Cloro residual":
        resultado_procedimiento = mostrar_cloro_residual(id_orden)

    elif tarea == "Control AFS":
        resultado_procedimiento = mostrar_control_afs(id_orden, terminales)

    elif tarea == "Control ACS terminal":
        resultado_procedimiento = mostrar_control_acs_terminal(id_orden, terminales)

    elif tarea == "Control punto terminal completo":
        resultado_procedimiento = mostrar_control_terminal_completo(id_orden, terminales)

    elif tarea == "Control depósitos solares":
        resultado_procedimiento = mostrar_control_depositos_solares(
            id_orden
        )
        
    elif tarea == "Choque térmico":
        resultado_procedimiento = mostrar_procedimiento_choque_termico(id_orden, terminales)

    elif tarea == "Revisión trimestral acumulador ACS":
        resultado_procedimiento = mostrar_revision_trimestral_acumulador_acs(
            id_orden
        )

    elif tarea == "Revisión visual":
        resultado_procedimiento = mostrar_revision_visual(id_orden)

    elif tarea == "Purga":
        resultado_procedimiento = mostrar_purga(
            id_orden,
            punto
        )

    elif tarea == "Ruta semanal purgas P9":
        resultado_procedimiento = mostrar_ruta_semanal_purgas_p9(
            id_orden
        )

    elif tarea == "Puesta en servicio acumulador ACS":
        resultado_procedimiento = (
            mostrar_puesta_en_servicio_acumulador_acs(
                id_orden
            )
        )

    elif tarea in [
        "Limpieza y desinfección acumulador",
        "Limpieza y desinfección depósito AFCH",
    ]:
        resultado_procedimiento = mostrar_limpieza_desinfeccion(id_orden, tarea)

    else:
        resultado_procedimiento = mostrar_control_generico(id_orden, tarea)

    tipo_control = resultado_procedimiento["tipo_control"]
    unidad = resultado_procedimiento["unidad"]
    valor = resultado_procedimiento["valor"]
    valor_2 = resultado_procedimiento["valor_2"]
    valor_3 = resultado_procedimiento["valor_3"]

    fecha_control = st.date_input(
        "Fecha del control",
        value=date.today(),
        key=f"leg_fecha_{id_orden}"
    )

    observaciones_leg = st.text_area(
        "Observaciones Legionella",
        key=f"leg_obs_{id_orden}"
    )

    ya_guardado = st.session_state.get(f"legionella_guardada_{id_orden}", False)

    if ya_guardado:
        st.success("Control de Legionella guardado para esta OT.")
        return True

    if st.button(
        f"💾 Guardar control Legionella {num_ot}",
        key=f"guardar_legionella_ot_{id_orden}",
        use_container_width=True
    ):
        observaciones_finales = observaciones_leg or ""

        if not resultado_procedimiento.get("valido", True):
            for error in resultado_procedimiento.get("errores", []):
                st.error(error)
            return False

        obs_extra = resultado_procedimiento.get("observaciones_extra", "")

        if obs_extra:
            observaciones_finales = (
                observaciones_finales
                + "\n"
                + obs_extra
            ).strip()

        if tarea == "Ruta semanal purgas P9":
            puntos_ruta_df = leer_df(
                """
                SELECT *
                FROM legionella_puntos
                WHERE centro = ?
                  AND activo = 1
                  AND (
                        LOWER(COALESCE(nombre_punto, '')) LIKE ?
                        OR LOWER(COALESCE(nombre_punto, '')) LIKE ?
                  )
                ORDER BY id ASC
                """,
                (
                    "Pearson 9",
                    "%afs-04%",
                    "%afs-08%",
                ),
            )

            if puntos_ruta_df.empty or len(puntos_ruta_df) < 2:
                st.error(
                    "No se han encontrado AFS-04 y AFS-08 en el catálogo "
                    "de puntos Legionella."
                )
                return False

            estados_ruta = []

            for _, fila_punto in puntos_ruta_df.iterrows():
                punto_real = fila_punto.to_dict()

                estado_punto, resultado_punto = registrar_control(
                    fecha_control.strftime("%Y-%m-%d"),
                    punto_real,
                    "Purga",
                    "Purga",
                    1,
                    None,
                    None,
                    "Sí/No",
                    operario,
                    observaciones_finales,
                )

                estados_ruta.append(
                    (estado_punto, resultado_punto)
                )

            errores_ruta = [
                resultado_punto
                for estado_punto, resultado_punto in estados_ruta
                if estado_punto == "ERROR"
            ]

            if errores_ruta:
                for error in errores_ruta:
                    st.error(error)
                return False

            estado = (
                "RIESGO"
                if any(
                    estado_punto == "RIESGO"
                    for estado_punto, _ in estados_ruta
                )
                else (
                    "INCIDENCIA"
                    if any(
                        estado_punto == "INCIDENCIA"
                        for estado_punto, _ in estados_ruta
                    )
                    else "OK"
                )
            )

            resultado = (
                "Ruta semanal completada y registrada en AFS-04 y AFS-08."
            )

        else:
            estado, resultado = registrar_control(
                fecha_control.strftime("%Y-%m-%d"),
                punto,
                tarea,
                tipo_control,
                valor,
                valor_2,
                valor_3,
                unidad,
                operario,
                observaciones_finales,
            )

            if estado == "ERROR":
                st.error(resultado)
                return False

        st.session_state[f"legionella_guardada_{id_orden}"] = True

        if estado == "OK":
            st.success(f"Control guardado correctamente: {resultado}")
        elif estado == "RIESGO":
            st.error(f"Control guardado con RIESGO: {resultado}")
        else:
            st.warning(f"Control guardado con incidencia: {resultado}")

        st.rerun()

    st.info("Guarda el control de Legionella antes de finalizar esta OT.")
    return False


def _limpiar_nombre_foto_preventivo(texto):
    texto = str(texto or "")

    for caracter in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]:
        texto = texto.replace(caracter, "_")

    return texto.replace(" ", "_")


def _operario_incidencia_por_centro(centro, operario_actual=""):
    centro = str(centro or "").strip()

    if centro == "Pearson 9":
        return "Luis Lozano"

    if centro == "Pearson 22":
        return "J.A. Almeda"

    return str(operario_actual or "").strip()


def _obtener_ubicacion_preventiva(numero_ot):
    """Obtiene la ubicación real de la OT preventiva sin pedirla al operario."""
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT centro, edificio, planta, espacio
            FROM ordenes_trabajo
            WHERE numero_ot = ?
            LIMIT 1
        """), (numero_ot,))

        fila = cur.fetchone()

        if not fila:
            return "", "", "", ""

        return tuple(str(valor or "").strip() for valor in fila[:4])

    except Exception:
        return "", "", "", ""

    finally:
        conn.close()


def _guardar_revision_general_preventiva(
    num_ot,
    desc,
    operario,
    numeros_incidencia=None,
):
    """
    Mantiene compatible la tabla de checklist existente.

    La interfaz deja de obligar a revisar tarjetas una a una, pero guardamos
    la revisión general sobre las filas ya existentes para que el cierre,
    histórico y preventivos antiguos sigan funcionando sin migrar tablas.
    """
    numeros_incidencia = [
        str(numero or "").strip()
        for numero in (numeros_incidencia or [])
        if str(numero or "").strip()
    ]

    checks = obtener_checklist_preventivo_detallado(num_ot)

    if not checks:
        crear_checklist_preventivo(
            num_ot,
            0,
            limpiar_tarea_preventiva(desc),
            operario,
        )
        checks = obtener_checklist_preventivo_detallado(num_ot)

    if not checks:
        return False

    hay_anomalias = bool(numeros_incidencia)
    referencias = ", ".join(numeros_incidencia)

    items = []

    for indice, check in enumerate(checks):
        id_check = check[0]

        if indice == 0:
            if hay_anomalias:
                estado = "Revisar"
                observacion = (
                    "Revisión visual y funcional general realizada. "
                    "Se detectaron anomalías y se generaron las siguientes "
                    f"incidencias: {referencias}."
                )
            else:
                estado = "Correcto"
                observacion = (
                    "Revisión visual y funcional general realizada sin "
                    "anomalías detectadas."
                )
        else:
            estado = "Correcto"
            observacion = "Revisado dentro de la inspección general del espacio."

        items.append({
            "id_check": id_check,
            "estado_revision": estado,
            "observaciones_revision": observacion,
            "crear_correctivo": False,
        })

    return bool(
        guardar_checklist_preventivo_completo(
            items=items,
            operario=nombre_operario_actual() or operario,
        )
    )


def _crear_incidencia_desde_revision_preventiva(
    num_ot_preventiva,
    centro,
    edificio,
    planta,
    espacio,
    operario,
    descripcion,
    fotos,
):
    """Crea una INC con la misma estructura base que el formulario QR."""
    descripcion_limpia = str(descripcion or "").strip()

    if not descripcion_limpia:
        return False, "Describe brevemente la anomalía detectada.", ""

    fotos = list(fotos or [])

    if len(fotos) > 5:
        return False, "Puedes añadir un máximo de 5 fotografías.", ""

    fotos_validas = []

    for foto in fotos:
        try:
            tamano = int(getattr(foto, "size", 0) or 0)
        except Exception:
            tamano = 0

        if tamano > 5 * 1024 * 1024:
            return (
                False,
                f"La fotografía {getattr(foto, 'name', 'seleccionada')} supera 5 MB.",
                "",
            )

        fotos_validas.append(
            (
                str(getattr(foto, "name", "foto.jpg") or "foto.jpg"),
                foto.getvalue(),
            )
        )

    numero_ot = obtener_siguiente_numero_ot(centro, "INC")
    operario_destino = _operario_incidencia_por_centro(
        centro,
        operario,
    )
    fecha_origen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    observaciones_origen = (
        "Incidencia detectada durante una revisión preventiva del espacio.\n"
        f"OT preventiva origen: {num_ot_preventiva}\n"
        f"Planta: {planta or '-'}"
    )

    datos_orden = (
        numero_ot,
        descripcion_limpia,
        "Abierta",
        centro,
        edificio,
        espacio,
        "Otros",
        "Media",
        operario_destino,
        "PREVENTIVO",
        observaciones_origen,
        fecha_origen,
        "postgres_fotos" if fotos_validas else "",
        "Revisión preventiva",
        "Interna",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        0,
        0,
        "",
        planta,
    )

    try:
        crear_orden(datos_orden)
    except Exception as error:
        return False, f"No se ha podido crear la incidencia: {error}", ""

    error_fotos = ""

    if fotos_validas:
        try:
            for indice, (nombre_original, contenido) in enumerate(
                fotos_validas,
                start=1,
            ):
                nombre_foto = _limpiar_nombre_foto_preventivo(
                    f"{numero_ot}_{indice}_{nombre_original}"
                )

                guardar_foto_ot(
                    numero_ot=numero_ot,
                    nombre_foto=nombre_foto,
                    foto_data=contenido,
                )
        except Exception as error:
            error_fotos = str(error)

    if error_fotos:
        mensaje = (
            f"Incidencia {numero_ot} creada, pero alguna fotografía "
            "no se pudo guardar."
        )
    else:
        mensaje = f"Incidencia {numero_ot} creada correctamente."

    return True, mensaje, numero_ot


def mostrar_checklist_preventivo_operario(num_ot, desc, operario):
    """
    Nueva revisión preventiva de espacios.

    Filosofía:
    - revisar el espacio de forma visual y funcional;
    - una sola decisión: si existe alguna anomalía;
    - si existe, crear una o varias INC normales con la ubicación heredada;
    - conservar el checklist antiguo únicamente como soporte de trazabilidad y
      compatibilidad con el cierre, sin mostrar sus tarjetas al operario.
    """
    st.markdown("### 👀 Revisión preventiva del espacio")

    checks = obtener_checklist_preventivo_detallado(num_ot)

    if not checks:
        crear_checklist_preventivo(
            num_ot,
            0,
            limpiar_tarea_preventiva(desc),
            operario,
        )
        checks = obtener_checklist_preventivo_detallado(num_ot)

    if not checks:
        st.warning("No se ha podido preparar la revisión preventiva.")
        return False

    centro, edificio, planta, espacio = _obtener_ubicacion_preventiva(num_ot)

    if not any([centro, edificio, espacio]):
        st.warning(
            "No se ha podido recuperar la ubicación de esta preventiva. "
            "No se crearán incidencias hasta disponer de una ubicación válida."
        )

    st.caption(
        f"📍 {centro or '-'} · {edificio or '-'} · "
        f"{planta or '-'} · {espacio or '-'}"
    )

    st.info(
        "Realiza una comprobación visual y funcional general del espacio: "
        "agua, iluminación, mecanismos, mobiliario, puertas, climatización "
        "y cualquier otra anomalía visible o comunicada."
    )

    resumen_guardado = resumen_checklist_preventivo(num_ot)

    if resumen_guardado.get("listo_para_cerrar"):
        st.success(
            "✅ Revisión preventiva registrada. Esta OT ya puede finalizarse."
        )
        return True

    clave_incidencias = f"prev_incidencias_creadas_{num_ot}"
    incidencias_creadas = list(
        st.session_state.get(clave_incidencias, []) or []
    )

    if incidencias_creadas:
        st.success(
            "Incidencias creadas durante esta revisión: "
            + ", ".join(incidencias_creadas)
        )

    respuesta = st.radio(
        "¿Has detectado alguna anomalía?",
        ["No", "Sí"],
        index=None,
        horizontal=True,
        key=f"prev_anomalia_general_{num_ot}",
    )

    if respuesta == "No":
        st.caption(
            "Si todo está correcto, guarda la revisión y después podrás "
            "finalizar la OT preventiva."
        )

        if st.button(
            "✅ Guardar revisión sin anomalías",
            key=f"prev_guardar_sin_anomalias_{num_ot}",
            use_container_width=True,
            type="primary",
        ):
            if _guardar_revision_general_preventiva(
                num_ot=num_ot,
                desc=desc,
                operario=operario,
                numeros_incidencia=[],
            ):
                st.success("Revisión preventiva guardada correctamente.")
                st.rerun()
            else:
                st.error("No se ha podido guardar la revisión preventiva.")

        return False

    if respuesta != "Sí":
        st.info("Indica si has detectado alguna anomalía para continuar.")
        return False

    st.markdown("#### 🔧 Anomalía detectada")
    st.caption(
        "Se creará una incidencia normal, como las del QR, con este espacio "
        "ya asignado automáticamente."
    )

    contador = int(
        st.session_state.get(
            f"prev_contador_anomalia_{num_ot}",
            1,
        )
        or 1
    )

    descripcion_anomalia = st.text_area(
        "¿Qué ocurre en este espacio?",
        placeholder="Ej.: WC pierde agua, downlight fundido, puerta no cierra...",
        height=120,
        key=f"prev_desc_anomalia_{num_ot}_{contador}",
    )

    fotos = st.file_uploader(
        "Añadir fotografías (opcional)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"prev_fotos_anomalia_{num_ot}_{contador}",
    )

    if st.button(
        "➕ Crear incidencia",
        key=f"prev_crear_incidencia_{num_ot}_{contador}",
        use_container_width=True,
        type="primary",
        disabled=not bool(centro and edificio and espacio),
    ):
        ok, mensaje, numero_incidencia = _crear_incidencia_desde_revision_preventiva(
            num_ot_preventiva=num_ot,
            centro=centro,
            edificio=edificio,
            planta=planta,
            espacio=espacio,
            operario=operario,
            descripcion=descripcion_anomalia,
            fotos=fotos,
        )

        if not ok:
            st.error(mensaje)
            return False

        incidencias_creadas.append(numero_incidencia)
        st.session_state[clave_incidencias] = incidencias_creadas
        st.session_state[f"prev_contador_anomalia_{num_ot}"] = contador + 1
        st.session_state["recalcular_corazon"] = True
        st.success(mensaje)
        st.rerun()

    if incidencias_creadas:
        st.markdown("---")
        st.caption(
            "Puedes crear otra incidencia arriba. Cuando ya no haya más "
            "anomalías, cierra la revisión preventiva."
        )

        if st.button(
            "✅ Terminar revisión preventiva",
            key=f"prev_terminar_revision_{num_ot}",
            use_container_width=True,
        ):
            if _guardar_revision_general_preventiva(
                num_ot=num_ot,
                desc=desc,
                operario=operario,
                numeros_incidencia=incidencias_creadas,
            ):
                st.success(
                    "Revisión preventiva guardada y anomalías trazadas "
                    "como incidencias independientes."
                )
                st.rerun()
            else:
                st.error("No se ha podido cerrar la revisión preventiva.")

    return False

def mostrar_checklist_correctivo_legionella_operario(
    num_ot,
    centro,
    edificio,
    espacio,
    desc,
    planta="",
):
    if "CORRECTIVO LEGIONELLA" not in str(desc or "").upper():
        return False

    st.markdown("### 🧪 Checklist correctivo Legionella")

    checklist = obtener_checklist_correctivo_legionella(num_ot) or {}

    revisar_consigna = st.checkbox(
        "Revisar consigna acumulador",
        value=bool(checklist.get("revisar_consigna", 0)),
        key=f"leg_consigna_op_{num_ot}"
    )

    revisar_termostato = st.checkbox(
        "Revisar termostato",
        value=bool(checklist.get("revisar_termostato", 0)),
        key=f"leg_termostato_op_{num_ot}"
    )

    revisar_caldera = st.checkbox(
        "Revisar caldera",
        value=bool(checklist.get("revisar_caldera", 0)),
        key=f"leg_caldera_op_{num_ot}"
    )

    revisar_resistencia = st.checkbox(
        "Revisar resistencia eléctrica",
        value=bool(checklist.get("revisar_resistencia", 0)),
        key=f"leg_resistencia_op_{num_ot}"
    )

    revisar_recirculacion = st.checkbox(
        "Revisar recirculación",
        value=bool(checklist.get("revisar_recirculacion", 0)),
        key=f"leg_recirculacion_op_{num_ot}"
    )

    revisar_bomba = st.checkbox(
        "Revisar bomba retorno",
        value=bool(checklist.get("revisar_bomba", 0)),
        key=f"leg_bomba_op_{num_ot}"
    )

    purgar_aire = st.checkbox(
        "Purgar aire circuito",
        value=bool(checklist.get("purgar_aire", 0)),
        key=f"leg_aire_op_{num_ot}"
    )

    esperar_recuperacion = st.checkbox(
        "Esperar recuperación térmica",
        value=bool(checklist.get("esperar_recuperacion", 0)),
        key=f"leg_recuperacion_op_{num_ot}"
    )

    nueva_medicion = st.checkbox(
        "Realizar nueva medición",
        value=bool(checklist.get("nueva_medicion", 0)),
        key=f"leg_medicion_op_{num_ot}"
    )

    opciones_causa = [
        "",
        "Consigna incorrecta",
        "Termostato",
        "Caldera",
        "Resistencia",
        "Recirculación / bomba",
        "Aire en circuito",
        "Empresa externa pendiente",
        "Otra"
    ]

    causa_guardada = str(checklist.get("causa_detectada", ""))

    causa_detectada = st.selectbox(
        "Causa detectada",
        opciones_causa,
        index=opciones_causa.index(causa_guardada) if causa_guardada in opciones_causa else 0,
        key=f"leg_causa_op_{num_ot}"
    )

    temperatura_final = st.number_input(
        "Temperatura final ºC",
        min_value=0.0,
        max_value=100.0,
        value=float(checklist.get("temperatura_final", 0) or 0),
        step=0.1,
        key=f"leg_temp_op_{num_ot}"
    )

    empresa_externa_leg = st.text_input(
        "Empresa externa / técnico",
        value=str(checklist.get("empresa_externa", "")),
        key=f"leg_empresa_op_{num_ot}"
    )

    observaciones_leg = st.text_area(
        "Observaciones correctivo",
        value=str(checklist.get("observaciones", "")),
        key=f"leg_obs_op_{num_ot}"
    )

    col_leg1, col_leg2 = st.columns(2)

    with col_leg1:
        if st.button(
            f"💾 Guardar checklist {num_ot}",
            key=f"guardar_leg_op_{num_ot}",
            use_container_width=True
        ):
            guardar_checklist_correctivo_legionella(
                num_ot,
                centro,
                edificio,
                espacio,
                desc,
                {
                    "revisar_consigna": 1 if revisar_consigna else 0,
                    "revisar_termostato": 1 if revisar_termostato else 0,
                    "revisar_caldera": 1 if revisar_caldera else 0,
                    "revisar_resistencia": 1 if revisar_resistencia else 0,
                    "revisar_recirculacion": 1 if revisar_recirculacion else 0,
                    "revisar_bomba": 1 if revisar_bomba else 0,
                    "purgar_aire": 1 if purgar_aire else 0,
                    "esperar_recuperacion": 1 if esperar_recuperacion else 0,
                    "nueva_medicion": 1 if nueva_medicion else 0,
                    "causa_detectada": causa_detectada,
                    "temperatura_final": temperatura_final,
                    "empresa_externa": empresa_externa_leg,
                    "observaciones": observaciones_leg,
                },
                planta=planta,
            )
            st.success("Checklist Legionella guardado.")
            st.rerun()

    with col_leg2:
        if st.button(
            f"🗑️ Reset checklist {num_ot}",
            key=f"reset_leg_op_{num_ot}",
            use_container_width=True
        ):
            borrar_checklist_correctivo_legionella(num_ot)
            st.warning("Checklist reiniciado.")
            st.rerun()

    return True
