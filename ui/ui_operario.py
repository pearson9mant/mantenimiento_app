import streamlit as st

from modules.ordenes import (
    obtener_ordenes_operario,
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    crear_correctiva_desde_ot
)

from modules.inventario import (
    obtener_materiales_para_select,
    registrar_movimiento_inventario
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
    crear_checklist_preventivo,
)


def rol_actual():
    return str(st.session_state.get("rol", "")).strip().lower()


def usuario_actual():
    return str(st.session_state.get("usuario", "")).strip()


def nombre_operario_actual():
    return str(
        st.session_state.get("operario_activo")
        or st.session_state.get("nombre")
        or usuario_actual()
    ).strip()


def es_admin():
    return rol_actual() == "admin"


def es_gerencia():
    return rol_actual() == "gerencia"


def es_operario():
    return rol_actual() == "operario"


def normalizar_txt(valor):
    return str(valor or "").strip().lower()


def puede_ver_legionella_operario(operario):
    operario_txt = normalizar_txt(operario)
    operario_txt = operario_txt.replace(".", "")
    operario_txt = operario_txt.replace(" ", "")
    operario_txt = operario_txt.replace("-", "")
    operario_txt = operario_txt.replace("_", "")

    return (
        "almeda" in operario_txt
        or operario_txt in ["ja", "jalmeda", "jaalmeda", "juanantonio"]
    )


def obtener_operario_fila(fila):
    try:
        return fila[10]
    except Exception:
        return ""


def es_ot_preventiva(origen, descripcion):
    origen_txt = str(origen or "").strip().upper()
    desc_txt = str(descripcion or "").strip().upper()
    return origen_txt == "PREVENTIVO" or desc_txt.startswith("[PREVENTIVO]")


def es_ot_legionella(area, origen, descripcion):
    area_txt = normalizar_txt(area)
    origen_txt = normalizar_txt(origen)
    desc_txt = normalizar_txt(descripcion)

    return (
        area_txt == "legionella"
        or origen_txt == "legionella"
        or desc_txt.startswith("control legionella")
    )


def limpiar_tarea_preventiva(descripcion):
    texto = str(descripcion or "").strip()
    return texto.replace("[PREVENTIVO]", "").strip()


def extraer_datos_ot_legionella(descripcion, espacio):
    texto = str(descripcion or "").strip()
    partes = [p.strip() for p in texto.split(" - ")]

    tarea = ""
    punto = str(espacio or "").strip()

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
    operario
):
    st.markdown("### 💧 Ejecutar control Legionella")

    try:
        from ui.ui_legionella import registrar_control, leer_df
    except Exception as e:
        st.error("No se ha podido cargar el módulo de Legionella.")
        st.exception(e)
        return False

    tarea, punto_nombre = extraer_datos_ot_legionella(desc, espacio)

    if not tarea:
        st.warning("No se ha podido identificar la tarea de Legionella desde la OT.")
        return False

    puntos_df = leer_df(
        """
        SELECT *
        FROM legionella_puntos
        WHERE centro = ?
          AND edificio = ?
          AND nombre_punto = ?
          AND activo = 1
        ORDER BY id DESC
        """,
        (centro, edificio, punto_nombre),
    )

    if puntos_df.empty:
        st.warning(
            "No se ha encontrado el punto de Legionella asociado a esta OT. "
            "Puedes revisar el punto en el módulo Legionella."
        )
        return False

    punto = puntos_df.iloc[0].to_dict()

    st.caption(f"📍 {centro} · {edificio} · {punto_nombre}")
    st.caption(f"🧪 Tarea: {tarea}")

    valor = None
    valor_2 = None
    unidad = ""

    if tarea == "Temperatura acumulador":
        tipo_control = "Temperatura acumulador"
        unidad = "ºC"
        valor = st.number_input(
            "Temperatura acumulador ºC",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=0.1,
            key=f"leg_valor_{id_orden}"
        )

    elif tarea == "Temperatura retorno":
        tipo_control = "Temperatura retorno"
        unidad = "ºC"
        valor = st.number_input(
            "Temperatura retorno ºC",
            min_value=0.0,
            max_value=100.0,
            value=50.0,
            step=0.1,
            key=f"leg_valor_{id_orden}"
        )

    elif tarea == "Temperatura punto terminal":
        tipo_control = "Temperatura punto terminal"
        unidad = "ºC"
        valor = st.number_input(
            "Temperatura punto terminal ºC",
            min_value=0.0,
            max_value=100.0,
            value=45.0,
            step=0.1,
            key=f"leg_valor_{id_orden}"
        )

    elif tarea == "Cloro residual":
        tipo_control = "Cloro residual"
        unidad = "mg/L"
        valor = st.number_input(
            "Cloro residual libre mg/L",
            min_value=0.0,
            max_value=5.0,
            value=0.5,
            step=0.01,
            key=f"leg_valor_{id_orden}"
        )

    elif tarea == "Revisión visual":
        tipo_control = "Revisión visual"
        unidad = "OK/KO"
        correcto = st.radio(
            "Resultado revisión visual",
            ["Correcto", "Deficiente"],
            horizontal=True,
            key=f"leg_revision_{id_orden}"
        )
        valor = 1 if correcto == "Correcto" else 0

    elif tarea == "Purga":
        tipo_control = "Purga"
        unidad = "Sí/No"
        purga = st.radio(
            "Purga realizada",
            ["Sí", "No"],
            horizontal=True,
            key=f"leg_purga_{id_orden}"
        )
        valor = 1 if purga == "Sí" else 0

    else:
        tipo_control = tarea
        unidad = ""
        valor = st.number_input(
            "Valor del control",
            min_value=0.0,
            max_value=999.0,
            value=0.0,
            step=0.1,
            key=f"leg_valor_{id_orden}"
        )

    fecha_control = st.date_input(
        "Fecha del control",
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
        estado, resultado = registrar_control(
            fecha_control.strftime("%Y-%m-%d"),
            punto,
            tarea,
            tipo_control,
            valor,
            valor_2,
            unidad,
            operario,
            observaciones_leg,
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


def mostrar_checklist_preventivo_operario(num_ot, desc, operario):
    st.markdown("### ✅ Checklist preventivo")

    checks = obtener_checklist_preventivo(num_ot)

    if not checks:
        crear_checklist_preventivo(
            num_ot,
            0,
            limpiar_tarea_preventiva(desc),
            operario
        )
        checks = obtener_checklist_preventivo(num_ot)

    if not checks:
        st.warning("No se ha podido crear el checklist preventivo.")
        return False

    hechos = 0

    for check in checks:
        (
            id_check,
            check_numero_ot,
            tarea_id,
            item,
            hecho,
            fecha_hecho,
            operario_check,
            observaciones_check
        ) = check

        valor_actual = bool(hecho)

        nuevo_valor = st.checkbox(
            item,
            value=valor_actual,
            key=f"check_operario_prev_{num_ot}_{id_check}"
        )

        if nuevo_valor != valor_actual:
            actualizar_checklist_preventivo(
                id_check,
                nuevo_valor,
                nombre_operario_actual() or operario
            )
            st.rerun()

        if nuevo_valor:
            hechos += 1

    total = len(checks)
    st.caption(f"Checklist: {hechos}/{total} completado")

    if hechos == total:
        st.success("Checklist completado. Ya puedes finalizar la OT.")
        return True

    st.warning("Faltan puntos del checklist por marcar.")
    return False


def normalizar_estado_operario(estado):
    estado = str(estado or "").strip().lower()

    if estado in ["finalizada", "finalizado", "cerrada", "cerrado"]:
        return "Hechas"

    if estado in ["en curso", "en proceso"]:
        return "En proceso"

    if estado in ["abierta", "pendiente", "pendiente material", "esperando material"]:
        return "Faltan"

    return "Faltan"


def calcular_kpis_operario(ordenes):
    total = len(ordenes)

    hechas = len([
        o for o in ordenes
        if normalizar_estado_operario(o[3]) == "Hechas"
    ])

    en_proceso = len([
        o for o in ordenes
        if normalizar_estado_operario(o[3]) == "En proceso"
    ])

    faltan = len([
        o for o in ordenes
        if normalizar_estado_operario(o[3]) == "Faltan"
    ])

    rendimiento = round((hechas / total) * 100, 1) if total else 0

    return {
        "total": total,
        "hechas": hechas,
        "en_proceso": en_proceso,
        "faltan": faltan,
        "rendimiento": rendimiento,
    }


def filtrar_seguridad_operario(ordenes, operario_sel):
    if not ordenes:
        return []

    if es_operario():
        usuario = normalizar_txt(nombre_operario_actual())

        return [
            o for o in ordenes
            if normalizar_txt(obtener_operario_fila(o)) == usuario
        ]

    return [
        o for o in ordenes
        if normalizar_txt(obtener_operario_fila(o)) == normalizar_txt(operario_sel)
    ]


def descomponer_orden_operario(fila):
    observaciones_estado = ""

    if len(fila) >= 26:
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
            tipo_orden,
            empresa_externa,
            contacto_empresa,
            telefono_empresa,
            email_empresa,
            fecha_programada,
            fecha_realizacion,
            coste_estimado,
            coste_final,
            observaciones_estado,
        ) = fila[:26]

    elif len(fila) >= 16:
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
        ) = fila[:16]

    elif len(fila) == 15:
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
        ) = fila
        tipo_solicitante = "Operarios"

    else:
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
            origen
        ) = fila[:12]
        solicitante = ""
        fecha_origen = ""
        foto = ""
        tipo_solicitante = "Operarios"

    return (
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
    )


def puede_finalizar_preventivo(num_ot, origen, desc):
    if es_ot_preventiva(origen, desc):
        return checklist_preventivo_completo(num_ot)
    return True


def puede_finalizar_legionella(id_orden, area, origen, desc):
    if es_ot_legionella(area, origen, desc):
        return st.session_state.get(f"legionella_guardada_{id_orden}", False)
    return True


def mostrar_crear_correctiva_desde_revision(
    id_orden,
    num_ot,
    centro,
    edificio,
    espacio,
    area,
    prioridad,
    operario,
    origen_base
):
    st.markdown("### 🛠️ Crear correctivas si hay defectos")

    st.info(
        "Escribe un defecto por línea. "
        "Se creará una OT correctiva independiente por cada línea."
    )

    defectos_texto = st.text_area(
        "Defectos encontrados",
        placeholder=(
            "Ejemplo:\n"
            "P0/ACS01 - Grifo cocina pierde agua\n"
            "P0/ACS02 - Grifo cocina sin caudal\n"
            "Luz emergencia pasillo sin batería"
        ),
        key=f"defectos_correctivas_{id_orden}",
        height=150
    )

    crear_correctivas = st.checkbox(
        "Crear OT correctivas automáticas",
        key=f"crear_correctivas_auto_{id_orden}"
    )

    if st.button(
        "➕ Crear correctivas",
        key=f"btn_crear_correctivas_{id_orden}",
        use_container_width=True
    ):
        if not crear_correctivas:
            st.warning("Marca la casilla para crear las OT correctivas.")
            return False

        defectos = [
            d.strip()
            for d in str(defectos_texto or "").splitlines()
            if d.strip()
        ]

        if not defectos:
            st.warning("Escribe al menos un defecto.")
            return False

        creadas = 0
        errores = []

        for defecto in defectos:
            ok, mensaje = crear_correctiva_desde_ot(
                centro=centro,
                edificio=edificio,
                espacio=espacio,
                area=area,
                prioridad=prioridad,
                operario=operario,
                descripcion_defecto=defecto,
                numero_ot_origen=num_ot,
                origen=origen_base,
                solicitante="Operarios",
            )

            if ok:
                creadas += 1
            else:
                errores.append(mensaje)

        if creadas > 0:
            st.success(f"Se han creado {creadas} OT correctivas independientes.")
            st.session_state[f"correctiva_creada_{id_orden}"] = True

        if errores:
            for error in errores:
                st.warning(error)

        st.rerun()

    if st.session_state.get(f"correctiva_creada_{id_orden}", False):
        st.success("Ya se han creado correctivas desde esta revisión.")

    return st.session_state.get(f"correctiva_creada_{id_orden}", False)


def pantalla_operario():
    st.subheader("👷 Vista operario")

    if st.session_state.get("vista_operario", False):
        if st.button("🔙 Volver a administración"):
            st.session_state["vista_operario"] = False
            st.rerun()

    operario_sel = st.session_state.get("operario_activo", "")

    if es_operario():
        operario_sel = nombre_operario_actual()
        st.session_state["operario_activo"] = operario_sel

    if not operario_sel:
        st.warning("No hay operario seleccionado.")
        return

    st.info(f"Operario: {operario_sel}")

    if puede_ver_legionella_operario(operario_sel):
        zona_operario = st.radio(
            "Zona de trabajo",
            ["📋 Mis órdenes", "💧 Control Legionella"],
            horizontal=True,
            key="zona_operario_legionella"
        )

        if zona_operario == "💧 Control Legionella":
            try:
                from ui.ui_legionella import pantalla_legionella
                pantalla_legionella()
            except Exception as e:
                st.error("No se ha podido abrir el módulo de Legionella.")
                st.exception(e)
            return

    ordenes_operario = obtener_ordenes_operario(operario_sel.strip())
    ordenes_operario = filtrar_seguridad_operario(ordenes_operario, operario_sel)

    kpis = calcular_kpis_operario(ordenes_operario)

    st.markdown("### 📈 Mi resumen")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Mis OT", kpis["total"])
    k2.metric("✅ Hechas", kpis["hechas"])
    k3.metric("🔄 En curso", kpis["en_proceso"])
    k4.metric("⏳ Pendientes", kpis["faltan"])
    k5.metric("📈 Rendimiento", f'{kpis["rendimiento"]}%')

    st.markdown("---")

    materiales_select = obtener_materiales_para_select()

    ordenes_operario = [
        o for o in ordenes_operario
        if o[3] in ["Abierta", "En curso", "Pendiente material"]
    ]

    if not ordenes_operario:
        st.success("No tienes órdenes pendientes.")
        return

    st.markdown("## ⚡ Trabajo rápido")

    for fila in ordenes_operario:

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

        if es_operario() and normalizar_txt(operario) != normalizar_txt(nombre_operario_actual()):
            continue

        estado_icono = {
            "Abierta": "🔴",
            "En curso": "🟠",
            "Pendiente material": "📦"
        }.get(est, "⚪")

        titulo = f"{estado_icono} {num_ot} | {prioridad} | {centro or '-'} · {espacio or '-'}"

        with st.expander(titulo, expanded=False):

            st.markdown(f"### {estado_icono} {num_ot}")
            st.markdown(f"**{prioridad}** | {area or '-'}")
            st.markdown(f"{desc}")
            st.caption(f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}")
            st.caption(f"Estado actual: {est}")

            if observaciones_estado:
                st.info(f"📝 Observación estado: {observaciones_estado}")

            st.caption(f"👷 Operario: {operario or '-'}")
            st.caption(f"📌 Solicitante: {tipo_solicitante or 'Operarios'}")

            if solicitante:
                st.caption(f"Nombre solicitante: {solicitante}")

            if fecha_origen:
                st.caption(f"Fecha origen: {fecha_origen}")

            if foto:
                try:
                    st.image(foto, caption="Foto incidencia", use_container_width=True)
                except Exception:
                    st.caption("📷 Foto no disponible")

            if es_ot_preventiva(origen, desc):
                mostrar_checklist_preventivo_operario(num_ot, desc, operario)

            if es_ot_legionella(area, origen, desc):
                mostrar_ejecucion_legionella_operario(
                    id_orden,
                    num_ot,
                    desc,
                    centro,
                    edificio,
                    espacio,
                    operario
                )

            if es_ot_preventiva(origen, desc):
                mostrar_crear_correctiva_desde_revision(
                    id_orden=id_orden,
                    num_ot=num_ot,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    area=area,
                    prioridad="Media",
                    operario=operario,
                    origen_base="Preventivo"
                )

            if es_ot_legionella(area, origen, desc):
                mostrar_crear_correctiva_desde_revision(
                    id_orden=id_orden,
                    num_ot=num_ot,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    area="Legionella",
                    prioridad="Alta",
                    operario=operario,
                    origen_base="Legionella"
                )

            st.markdown("### 📝 Estado y observaciones")

            observacion_estado_nueva = st.text_area(
                "Observación del estado",
                value=str(observaciones_estado or ""),
                placeholder="Ejemplo: En curso porque falta acceder al aula, pendiente de pieza, esperando proveedor...",
                key=f"observacion_estado_{id_orden}"
            )

            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button("▶\nEn curso", key=f"curso_rapido_{id_orden}", use_container_width=True):
                    actualizar_estado(id_orden, "En curso", observacion_estado_nueva)
                    st.rerun()

            with b2:
                if st.button("📦\nMaterial", key=f"mat_rapido_{id_orden}", use_container_width=True):
                    actualizar_estado(id_orden, "Pendiente material", observacion_estado_nueva)
                    st.rerun()

            with b3:
                if st.button("✔\nFinalizar", key=f"fin_rapido_{id_orden}", use_container_width=True):
                    st.session_state[f"confirmar_fin_rapido_{id_orden}"] = True
                    st.rerun()

            if st.session_state.get(f"confirmar_fin_rapido_{id_orden}", False):
                st.warning(f"¿Seguro que quieres finalizar {num_ot}?")

                c1, c2 = st.columns(2)

                with c1:
                    if st.button("✔\nSí, finalizar", key=f"si_fin_rapido_{id_orden}", use_container_width=True):
                        if not puede_finalizar_preventivo(num_ot, origen, desc):
                            st.error("No puedes finalizar esta preventiva hasta completar todo el checklist.")
                        elif not puede_finalizar_legionella(id_orden, area, origen, desc):
                            st.error("No puedes finalizar esta OT de Legionella hasta guardar el control.")
                        else:
                            actualizar_observaciones_estado(id_orden, observacion_estado_nueva)
                            finalizar_orden(id_orden, "")
                            st.session_state[f"confirmar_fin_rapido_{id_orden}"] = False
                            st.session_state.pop(f"legionella_guardada_{id_orden}", None)
                            st.success(f"{num_ot} finalizada correctamente.")
                            st.rerun()

                with c2:
                    if st.button("❌\nCancelar", key=f"no_fin_rapido_{id_orden}", use_container_width=True):
                        st.session_state[f"confirmar_fin_rapido_{id_orden}"] = False
                        st.rerun()

            with st.expander(f"Más opciones {num_ot}"):

                observaciones_fin = st.text_area(
                    "Observaciones de cierre",
                    key=f"obs_operario_{id_orden}"
                )

                usar_material = st.checkbox(
                    "Descontar material del inventario al cerrar",
                    key=f"usar_material_{id_orden}"
                )

                materiales_ot = []

                if usar_material:
                    if materiales_select:
                        opciones_material = [
                            f"{codigo} | {material} | Stock: {stock_actual} {unidad}"
                            for codigo, material, stock_actual, unidad in materiales_select
                        ]

                        num_materiales = st.number_input(
                            "Número de materiales usados",
                            min_value=1,
                            max_value=10,
                            value=1,
                            step=1,
                            key=f"num_materiales_ot_{id_orden}"
                        )

                        st.markdown("#### Materiales usados")

                        for i in range(int(num_materiales)):
                            st.markdown(f"**Material {i + 1}**")

                            material_ot = st.selectbox(
                                "Selecciona material",
                                opciones_material,
                                key=f"material_ot_{id_orden}_{i}"
                            )

                            codigo_sel = material_ot.split(" | ")[0]

                            cantidad_material = st.number_input(
                                "Cantidad usada",
                                min_value=0.0,
                                step=1.0,
                                key=f"cantidad_material_ot_{id_orden}_{i}"
                            )

                            materiales_ot.append({
                                "codigo": codigo_sel,
                                "cantidad": cantidad_material
                            })
                    else:
                        st.info("No hay materiales dados de alta en Inventario.")

                if st.button(
                    f"Finalizar con observaciones/material {num_ot}",
                    key=f"fin_completo_operario_{id_orden}",
                    use_container_width=True
                ):
                    st.session_state[f"materiales_confirmados_{id_orden}"] = materiales_ot.copy()
                    st.session_state[f"confirmar_fin_completo_{id_orden}"] = True
                    st.rerun()

                if st.session_state.get(f"confirmar_fin_completo_{id_orden}", False):
                    st.warning(f"¿Seguro que quieres finalizar {num_ot} con estas observaciones/material?")

                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button("✔\nSí, finalizar", key=f"si_fin_completo_{id_orden}", use_container_width=True):

                            if not puede_finalizar_preventivo(num_ot, origen, desc):
                                st.error("No puedes finalizar esta preventiva hasta completar todo el checklist.")

                            elif not puede_finalizar_legionella(id_orden, area, origen, desc):
                                st.error("No puedes finalizar esta OT de Legionella hasta guardar el control.")

                            elif usar_material and materiales_select:

                                materiales_confirmados = st.session_state.get(
                                    f"materiales_confirmados_{id_orden}",
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
                                        actualizar_observaciones_estado(id_orden, observacion_estado_nueva)
                                        finalizar_orden(id_orden, observaciones_fin)
                                        st.session_state[f"confirmar_fin_completo_{id_orden}"] = False
                                        st.session_state.pop(f"materiales_confirmados_{id_orden}", None)
                                        st.session_state.pop(f"legionella_guardada_{id_orden}", None)
                                        st.success(f"{num_ot} finalizada y materiales descontados correctamente.")
                                        st.rerun()

                            else:
                                actualizar_observaciones_estado(id_orden, observacion_estado_nueva)
                                finalizar_orden(id_orden, observaciones_fin)
                                st.session_state[f"confirmar_fin_completo_{id_orden}"] = False
                                st.session_state.pop(f"materiales_confirmados_{id_orden}", None)
                                st.session_state.pop(f"legionella_guardada_{id_orden}", None)
                                st.success(f"{num_ot} finalizada correctamente.")
                                st.rerun()

                    with c2:
                        if st.button("❌\nCancelar", key=f"no_fin_completo_{id_orden}", use_container_width=True):
                            st.session_state[f"confirmar_fin_completo_{id_orden}"] = False
                            st.session_state.pop(f"materiales_confirmados_{id_orden}", None)
                            st.rerun()
