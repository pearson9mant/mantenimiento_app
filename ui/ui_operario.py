import streamlit as st
from datetime import date
from pathlib import Path

from modules.ordenes import (
    obtener_ordenes_operario,
    obtener_historico,
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    obtener_fotos_ot,
    guardar_foto_ot,
    crear_correctiva_desde_ot
)

from modules.inventario import (
    obtener_materiales_para_select,
    obtener_material_por_codigo,
    registrar_movimiento_inventario
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
    crear_checklist_preventivo,
)

from ui.ui_legionella import (
    obtener_checklist_correctivo_legionella,
    guardar_checklist_correctivo_legionella,
    borrar_checklist_correctivo_legionella,
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


def normalizar_operario_nombre(nombre):
    texto = normalizar_txt(nombre)
    limpio = (
        texto.replace(".", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )

    if limpio in [
        "jaalmeda",
        "jalmeda",
        "juanantonio",
        "juanantonioalmeda",
        "jalmedac",
        "jalmedaabatolibaedu"
    ]:
        return "j.a. almeda"

    if limpio in [
        "luislozano",
        "llozano",
        "luis"
    ]:
        return "luis lozano"

    if limpio in [
        "abelvasquez",
        "abel",
        "avasquez"
    ]:
        return "abel vasquez"

    return texto


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
        or desc_txt.startswith("correctivo legionella")
        or "correctivo legionella" in desc_txt
    )


def limpiar_tarea_preventiva(descripcion):
    texto = str(descripcion or "").strip()
    return texto.replace("[PREVENTIVO]", "").strip()


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

    tarea_txt = str(tarea or "").strip()

    if tarea_txt.lower() in ["sala acs completa", "control sala acs"]:
        tarea = "Control sala ACS"

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

    terminales = int(punto.get("numero_terminales", 1) or 1)

    if terminales > 1:
        st.info(f"🚿 Terminales incluidos en este punto: {terminales}")

    valor = None
    valor_2 = None
    valor_3 = None
    unidad = ""
    tipo_control = tarea

    purga_realizada = False
    aireador_limpio = False
    revision_visual_ok = False
    terminales_revisados = terminales

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

    elif tarea == "Control sala ACS":
        tipo_control = "Control sala ACS"
        unidad = "ºC"

        st.info("Control conjunto de sala ACS: acumulador, impulsión y retorno.")

        valor = st.number_input(
            "Temperatura acumulador ºC",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=0.1,
            key=f"leg_acum_{id_orden}"
        )

        valor_2 = st.number_input(
            "Temperatura impulsión ACS ºC",
            min_value=0.0,
            max_value=100.0,
            value=50.0,
            step=0.1,
            key=f"leg_impulsion_{id_orden}"
        )

        valor_3 = st.number_input(
            "Temperatura retorno ACS ºC",
            min_value=0.0,
            max_value=100.0,
            value=50.0,
            step=0.1,
            key=f"leg_retorno_{id_orden}"
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

    elif tarea == "Control AFS":
        tipo_control = "Control AFS"
        unidad = "ºC / mg/L"

        valor = st.number_input(
            "Temperatura AFS ºC",
            min_value=0.0,
            max_value=50.0,
            value=18.0,
            step=0.1,
            key=f"leg_temp_afs_{id_orden}"
        )

        valor_2 = st.number_input(
            "Cloro residual libre mg/L",
            min_value=0.0,
            max_value=5.0,
            value=0.5,
            step=0.01,
            key=f"leg_cloro_afs_{id_orden}"
        )

        purga_realizada = st.checkbox(
            "Purga realizada",
            key=f"leg_purga_afs_{id_orden}"
        )

        aireador_limpio = st.checkbox(
            "Aireador limpio/desinfectado",
            key=f"leg_aireador_afs_{id_orden}"
        )

        revision_visual_ok = st.checkbox(
            "Revisión visual correcta",
            key=f"leg_revision_afs_{id_orden}"
        )

        terminales_revisados = st.number_input(
            "Terminales revisados",
            min_value=0,
            max_value=terminales,
            value=terminales,
            step=1,
            key=f"terminales_rev_afs_{id_orden}"
        )

        if terminales_revisados < terminales:
            st.warning(
                f"Solo se han revisado {terminales_revisados} de {terminales} terminales"
            )

    elif tarea == "Control ACS terminal":
        tipo_control = "Control ACS terminal"
        unidad = "ºC"

        valor = st.number_input(
            "Temperatura ACS terminal ºC",
            min_value=0.0,
            max_value=100.0,
            value=50.0,
            step=0.1,
            key=f"leg_temp_acs_{id_orden}"
        )

        purga_realizada = st.checkbox(
            "Purga realizada",
            key=f"leg_purga_acs_{id_orden}"
        )

        aireador_limpio = st.checkbox(
            "Aireador limpio/desinfectado",
            key=f"leg_aireador_acs_{id_orden}"
        )

        revision_visual_ok = st.checkbox(
            "Revisión visual correcta",
            key=f"leg_revision_acs_{id_orden}"
        )

        terminales_revisados = st.number_input(
            "Terminales revisados",
            min_value=0,
            max_value=terminales,
            value=terminales,
            step=1,
            key=f"terminales_rev_acs_{id_orden}"
        )

        if terminales_revisados < terminales:
            st.warning(
                f"Solo se han revisado {terminales_revisados} de {terminales} terminales"
            )

    elif tarea == "Control punto terminal completo":
        tipo_control = "Control punto terminal completo"
        unidad = "Control completo"

        valor = st.number_input(
            "Temperatura AFS ºC",
            min_value=0.0,
            max_value=50.0,
            value=18.0,
            step=0.1,
            key=f"leg_temp_afs_completo_{id_orden}"
        )

        valor_2 = st.number_input(
            "Cloro residual libre mg/L",
            min_value=0.0,
            max_value=5.0,
            value=0.5,
            step=0.01,
            key=f"leg_cloro_completo_{id_orden}"
        )

        valor_3 = st.number_input(
            "Temperatura ACS terminal ºC",
            min_value=0.0,
            max_value=100.0,
            value=50.0,
            step=0.1,
            key=f"leg_temp_acs_completo_{id_orden}"
        )

        purga_realizada = st.checkbox(
            "Purga realizada",
            key=f"leg_purga_completo_{id_orden}"
        )

        aireador_limpio = st.checkbox(
            "Aireador limpio/desinfectado",
            key=f"leg_aireador_completo_{id_orden}"
        )

        revision_visual_ok = st.checkbox(
            "Revisión visual correcta",
            key=f"leg_revision_completo_{id_orden}"
        )

        terminales_revisados = st.number_input(
            "Terminales revisados",
            min_value=0,
            max_value=terminales,
            value=terminales,
            step=1,
            key=f"terminales_rev_completo_{id_orden}"
        )

        if terminales_revisados < terminales:
            st.warning(
                f"Solo se han revisado {terminales_revisados} de {terminales} terminales"
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

        if tarea == "Control sala ACS":
            observaciones_finales = (
                observaciones_finales
                + f"\nControl sala ACS: "
                + f"Acumulador: {valor} ºC | "
                + f"Impulsión: {valor_2} ºC | "
                + f"Retorno: {valor_3} ºC"
            ).strip()

        if tarea in [
            "Control AFS",
            "Control ACS terminal",
            "Control punto terminal completo"
        ]:
            checklist = []

            checklist.append(
                "Purga realizada: Sí" if purga_realizada else "Purga realizada: No"
            )

            checklist.append(
                "Aireador limpio/desinfectado: Sí"
                if aireador_limpio
                else "Aireador limpio/desinfectado: No"
            )

            checklist.append(
                "Revisión visual correcta: Sí"
                if revision_visual_ok
                else "Revisión visual correcta: No"
            )

            checklist.append(
                f"Terminales revisados: {terminales_revisados}/{terminales}"
            )

            observaciones_finales = (
                observaciones_finales
                + "\nChecklist: "
                + " | ".join(checklist)
            ).strip()

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
            

        if nuevo_valor:
            hechos += 1

    total = len(checks)
    st.caption(f"Checklist: {hechos}/{total} completado")

    if hechos == total:
        st.success("Checklist completado. Ya puedes finalizar la OT.")
        return True

    st.warning("Faltan puntos del checklist por marcar.")
    return False

def mostrar_checklist_correctivo_legionella_operario(num_ot, centro, edificio, espacio, desc):
    if "CORRECTIVO LEGIONELLA" not in str(desc or "").upper():
        return False

    st.markdown("### 🧪 Checklist correctivo Legionella")

    checklist = obtener_checklist_correctivo_legionella(num_ot)

    revisar_consigna = st.checkbox("Revisar consigna acumulador", value=bool(checklist.get("revisar_consigna", 0)) if checklist else False, key=f"leg_consigna_op_{num_ot}")
    revisar_termostato = st.checkbox("Revisar termostato", value=bool(checklist.get("revisar_termostato", 0)) if checklist else False, key=f"leg_termostato_op_{num_ot}")
    revisar_caldera = st.checkbox("Revisar caldera", value=bool(checklist.get("revisar_caldera", 0)) if checklist else False, key=f"leg_caldera_op_{num_ot}")
    revisar_resistencia = st.checkbox("Revisar resistencia eléctrica", value=bool(checklist.get("revisar_resistencia", 0)) if checklist else False, key=f"leg_resistencia_op_{num_ot}")
    revisar_recirculacion = st.checkbox("Revisar recirculación", value=bool(checklist.get("revisar_recirculacion", 0)) if checklist else False, key=f"leg_recirculacion_op_{num_ot}")
    revisar_bomba = st.checkbox("Revisar bomba retorno", value=bool(checklist.get("revisar_bomba", 0)) if checklist else False, key=f"leg_bomba_op_{num_ot}")
    purgar_aire = st.checkbox("Purgar aire circuito", value=bool(checklist.get("purgar_aire", 0)) if checklist else False, key=f"leg_aire_op_{num_ot}")
    esperar_recuperacion = st.checkbox("Esperar recuperación térmica", value=bool(checklist.get("esperar_recuperacion", 0)) if checklist else False, key=f"leg_recuperacion_op_{num_ot}")
    nueva_medicion = st.checkbox("Realizar nueva medición", value=bool(checklist.get("nueva_medicion", 0)) if checklist else False, key=f"leg_medicion_op_{num_ot}")

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

    causa_guardada = str(checklist.get("causa_detectada", "") if checklist else "")

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
        value=float(checklist.get("temperatura_final", 0) or 0) if checklist else 0.0,
        step=0.1,
        key=f"leg_temp_op_{num_ot}"
    )

    empresa_externa_leg = st.text_input(
        "Empresa externa / técnico",
        value=str(checklist.get("empresa_externa", "") if checklist else ""),
        key=f"leg_empresa_op_{num_ot}"
    )

    observaciones_leg = st.text_area(
        "Observaciones correctivo",
        value=str(checklist.get("observaciones", "") if checklist else ""),
        key=f"leg_obs_op_{num_ot}"
    )

    col_leg1, col_leg2 = st.columns(2)

    with col_leg1:
        if st.button(f"💾 Guardar checklist {num_ot}", key=f"guardar_leg_op_{num_ot}", use_container_width=True):
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
                }
            )
            st.success("Checklist Legionella guardado.")
            st.rerun()

    with col_leg2:
        if st.button(f"🗑️ Reset checklist {num_ot}", key=f"reset_leg_op_{num_ot}", use_container_width=True):
            borrar_checklist_correctivo_legionella(num_ot)
            st.warning("Checklist reiniciado.")
            st.rerun()

    return True

def normalizar_estado_operario(estado):
    estado = str(estado or "").strip().lower()

    if estado in ["finalizada", "finalizado", "cerrada", "cerrado"]:
        return "Hechas"

    if estado in ["en curso", "en proceso"]:
        return "En proceso"

    if estado in ["abierta", "pendiente", "pendiente material", "esperando material"]:
        return "Faltan"

    return "Faltan"


def fecha_es_hoy(valor):
    hoy = date.today().strftime("%Y-%m-%d")
    texto = str(valor or "").strip()
    return texto[:10] == hoy


def calcular_kpis_operario(ordenes, historico=None, operario_sel=""):
    historico = historico or []

    total = len(ordenes)

    en_proceso = len([
        o for o in ordenes
        if len(o) > 3 and str(o[3] or "").strip() == "En curso"
    ])

    faltan = len([
        o for o in ordenes
        if len(o) > 3 and str(o[3] or "").strip() in ["Abierta", "Pendiente material"]
    ])

    hechas_hoy = 0
    operario_objetivo = normalizar_operario_nombre(operario_sel)

    for h in historico:
        try:
            fecha_cierre_hist = h[14]
            operario_hist = h[10]
        except Exception:
            continue

        if normalizar_operario_nombre(operario_hist) != operario_objetivo:
            continue

        if fecha_es_hoy(fecha_cierre_hist):
            hechas_hoy += 1

    base_rendimiento = hechas_hoy + en_proceso + faltan
    rendimiento = round((hechas_hoy / base_rendimiento) * 100, 1) if base_rendimiento else 0

    return {
        "total": total,
        "hechas": hechas_hoy,
        "en_proceso": en_proceso,
        "faltan": faltan,
        "rendimiento": rendimiento,
    }


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
    
def filtrar_seguridad_operario(ordenes, operario_sel):
    if not ordenes:
        return []

    operario_objetivo = normalizar_operario_nombre(operario_sel)

    return [
        o for o in ordenes
        if len(o) > 10
        and normalizar_operario_nombre(o[10]) == operario_objetivo
    ]

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

    try:
        historico = obtener_historico()
    except Exception:
        historico = []
    

    kpis = calcular_kpis_operario(
        ordenes_operario,
        historico=historico,
        operario_sel=operario_sel
    )

    st.markdown("### 📈 Mi resumen")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Mis OT", kpis["total"])
    k2.metric("✅ Hechas hoy", kpis["hechas"])
    k3.metric("🔄 En curso", kpis["en_proceso"])
    k4.metric("⏳ Pendientes", kpis["faltan"])
    k5.metric("📈 Rendimiento hoy", f'{kpis["rendimiento"]}%')

    st.markdown("---")

    materiales_select = obtener_materiales_para_select()

    ordenes_operario = [
        o for o in ordenes_operario
        if o[3] in ["Abierta", "En curso", "Pendiente material"]
    ]

    filtro_origen_operario = st.radio(
        "Filtrar trabajos",
        ["Todas", "Incidencias", "Preventivo", "Legionella", "☀️ Verano"],
        horizontal=True,
        key="filtro_origen_operario"
    )
    
    if filtro_origen_operario == "Preventivo":
        ordenes_operario = [
            o for o in ordenes_operario
            if len(o) > 11 and str(o[11] or "").strip().upper() == "PREVENTIVO"
        ]
    
    elif filtro_origen_operario == "Legionella":
        ordenes_operario = [
            o for o in ordenes_operario
            if len(o) > 11 and str(o[11] or "").strip().upper() == "LEGIONELLA"
        ]
    
    elif filtro_origen_operario == "☀️ Verano":
        ordenes_operario = [
            o for o in ordenes_operario
            if len(o) > 11 and str(o[11] or "").strip().upper() == "VERANO"
        ]
    
    elif filtro_origen_operario == "Incidencias":
        ordenes_operario = [
            o for o in ordenes_operario
            if len(o) > 11 and str(o[11] or "").strip().upper() in ["APP", "OUTLOOK", "PROFESORES"]
        ]

    if not ordenes_operario:
        st.success("No tienes órdenes pendientes.")

    else:
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

            if es_operario() and normalizar_operario_nombre(operario) != normalizar_operario_nombre(nombre_operario_actual()):
                continue
    
            estado_icono = {
                "Abierta": "🔴",
                "En curso": "🟠",
                "Pendiente material": "📦"
            }.get(est, "⚪")
    
            desc_corta = str(desc or "").replace("\n", " ").strip()
    
            if len(desc_corta) > 45:
                desc_corta = desc_corta[:45] + "..."
            
            titulo = (
                f"{estado_icono} {num_ot} | {prioridad} | "
                f"{centro or '-'} · {espacio or '-'} | {desc_corta}"
            )
    
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
    
                try:
                
                    fotos_db = obtener_fotos_ot(num_ot)
                
                    if fotos_db:
                
                        cols_fotos = st.columns(3)
                
                        for i, (nombre_foto, foto_data) in enumerate(fotos_db):
                
                            with cols_fotos[i % 3]:
                
                                try:
                                    st.image(
                                        bytes(foto_data),
                                        caption=f"Foto {i + 1}",
                                        use_container_width=True
                                    )
                
                                except Exception as e:
                                    st.caption(f"📷 Foto no disponible: {e}")
                
                    elif foto:
                
                        fotos = str(foto).split("|")
                
                        cols_fotos = st.columns(3)
                
                        for i, ruta_foto in enumerate(fotos):
                
                            ruta_foto = str(ruta_foto).strip()
                
                            if not ruta_foto:
                                continue
                
                            with cols_fotos[i % 3]:
                
                                try:
                                    st.image(
                                        ruta_foto,
                                        caption=f"Foto {i + 1}",
                                        use_container_width=True
                                    )
                
                                except Exception as e:
                                    st.caption(f"📷 Foto no disponible: {e}")
                
                except Exception as e:
                    st.error(f"📷 Error mostrando fotos: {e}")
                        
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
                    

                if es_ot_legionella(area, origen, desc):

                    if str(centro).strip() == "Pearson 9":
                        pdf_puntos = Path(
                            "assets/planos_legionella/Puntos_control_legionela_Pearson_9.pdf"
                        )
                        nombre_pdf = "Puntos_control_legionela_Pearson_9.pdf"
                    else:
                        pdf_puntos = Path(
                            "assets/planos_legionella/Puntos_control_legionela.pdf"
                        )
                        nombre_pdf = "Puntos_control_legionela.pdf"
                
                    if pdf_puntos.exists():
                
                        with open(pdf_puntos, "rb") as f:
                
                            st.download_button(
                                "🗺️ Ver plano de puntos de control",
                                data=f.read(),
                                file_name=nombre_pdf,
                                mime="application/pdf",
                                use_container_width=True,
                                key=f"plano_legionella_{id_orden}"
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
                mostrar_checklist_correctivo_legionella_operario(
                    num_ot=num_ot,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    desc=desc
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
                            elif not puede_finalizar_legionella(id_orden, area, origen, desc, num_ot):
                                st.error("No puedes finalizar esta OT de Legionella hasta completar el control/checklist correspondiente.")
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
                                datos_mat = obtener_material_por_codigo(codigo_sel)
    
                                if datos_mat:
    
                                    foto_data = datos_mat.get("foto_data")
                                    foto_ruta = datos_mat.get("foto")
    
                                    if foto_data:
                                        try:
                                            st.image(bytes(foto_data), width=180)
                                        except Exception:
                                            st.caption("Foto del material no disponible.")
    
                                    elif foto_ruta:
                                        try:
                                            st.image(foto_ruta, width=180)
                                        except Exception:
                                            st.caption("Foto del material no disponible.")
    
                                    elif foto_ruta:
                                        try:
                                            st.image(foto_ruta, width=180)
                                        except Exception:
                                            st.caption("Foto del material no disponible.")
    
                                    elif foto_ruta:
                                        try:
                                            st.image(foto_ruta, width=180)
                                        except Exception:
                                            st.caption("Foto del material no disponible.")
    
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
                    fotos_cierre = st.file_uploader(
                        "📷 Fotos del trabajo realizado",
                        type=["jpg", "jpeg", "png"],
                        accept_multiple_files=True,
                        key=f"fotos_cierre_{id_orden}"
                    )
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
    
                                elif not puede_finalizar_legionella(id_orden, area, origen, desc, num_ot):
                                    st.error("No puedes finalizar esta OT de Legionella hasta completar el control/checklist correspondiente.")
    
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



    historico_operario = [
        h for h in historico
        if normalizar_operario_nombre(h[10])
        == normalizar_operario_nombre(operario_sel)
    ]

    st.markdown("---")

    with st.expander("📁 Mi histórico", expanded=False):

        if not historico_operario:

            st.info("No hay trabajos finalizados todavía.")

        else:

            for h in reversed(historico_operario[-50:]):

                try:

                    (
                        id_hist,
                        num_ot_hist,
                        desc_hist,
                        estado_hist,
                        fecha_hist,
                        centro_hist,
                        edificio_hist,
                        espacio_hist,
                        area_hist,
                        prioridad_hist,
                        operario_hist,
                        origen_hist,
                        solicitante_hist,
                        fecha_origen_hist,
                        fecha_cierre_hist,
                        observaciones_cierre_hist,
                        foto_hist,
                        *resto
                    ) = h

                except Exception:
                    continue

                titulo_hist = (
                    f"✅ {num_ot_hist} | "
                    f"{centro_hist or '-'} · {espacio_hist or '-'}"
                )

                with st.expander(titulo_hist, expanded=False):

                    st.markdown(f"### ✅ {num_ot_hist}")
                    st.markdown(desc_hist)

                    st.caption(
                        f"🏢 {centro_hist or '-'} · "
                        f"{edificio_hist or '-'} · "
                        f"{espacio_hist or '-'}"
                    )

                    st.caption(f"📅 Cierre: {fecha_cierre_hist or '-'}")

                    if observaciones_cierre_hist:
                        st.info(f"📝 {observaciones_cierre_hist}")

                    try:
                        fotos_db = obtener_fotos_ot(num_ot_hist)

                        if fotos_db:

                            cols_fotos = st.columns(3)

                            for i, (nombre_foto, foto_data) in enumerate(fotos_db):

                                with cols_fotos[i % 3]:

                                    st.image(
                                        bytes(foto_data),
                                        caption=f"Foto {i + 1}",
                                        use_container_width=True
                                    )

                        elif foto_hist:

                            fotos = str(foto_hist).split("|")
                            cols_fotos = st.columns(3)

                            for i, ruta_foto in enumerate(fotos):

                                ruta_foto = str(ruta_foto).strip()

                                if not ruta_foto:
                                    continue

                                with cols_fotos[i % 3]:

                                    try:
                                        st.image(
                                            ruta_foto,
                                            caption=f"Foto {i + 1}",
                                            use_container_width=True
                                        )

                                    except Exception as e:
                                        st.caption(f"📷 Foto no disponible: {e}")

                    except Exception as e:
                        st.caption(f"📷 Error fotos histórico: {e}")
