import streamlit as st
from datetime import date
from modules.ordenes import obtener_vinculacion_ot
from ui.procedimientos_legionella import (
    mostrar_control_sala_acs,
    mostrar_temperatura_simple,
    mostrar_cloro_residual,
    mostrar_control_afs,
    mostrar_control_acs_terminal,
    mostrar_control_terminal_completo,
    mostrar_revision_visual,
    mostrar_purga,
    mostrar_procedimiento_choque_termico,
    mostrar_limpieza_desinfeccion,
    mostrar_control_generico,
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
    crear_checklist_preventivo,
)

from ui.ui_legionella import (
    registrar_control,
    leer_df,
    obtener_checklist_correctivo_legionella,
    guardar_checklist_correctivo_legionella,
    borrar_checklist_correctivo_legionella,
)
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

    # -------------------------------------------------
    # Buscar punto Legionella de forma segura
    # 1) Primero por id_punto_legionella
    # 2) Si no existe, por nombre de punto como respaldo
    # -------------------------------------------------

    punto = None

    try:
        vinculacion = obtener_vinculacion_ot(
            numero_ot=num_ot,
            id_orden=id_orden
        )

        id_punto_legionella = vinculacion.get("id_punto_legionella")

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

    except Exception:
        punto = None

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

    st.caption(f"📍 {centro} · {edificio} · {punto_nombre}")
    st.caption(f"🧪 Tarea: {tarea}")

    terminales = int(punto.get("numero_terminales", 1) or 1)

    if terminales > 1:
        st.info(f"🚿 Terminales incluidos en este punto: {terminales}")

        resultado_procedimiento = None

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
    
        elif tarea == "Choque térmico":
            resultado_procedimiento = mostrar_procedimiento_choque_termico(id_orden, terminales)
    
        elif tarea == "Revisión visual":
            resultado_procedimiento = mostrar_revision_visual(id_orden)
    
        elif tarea == "Purga":
            resultado_procedimiento = mostrar_purga(id_orden)
    
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

        if tarea == "Choque térmico":
            observaciones_finales = (
                observaciones_finales
                + "\nProcedimiento choque térmico: "
                + " | ".join(checklist_choque)
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

        if tarea == "Choque térmico":

            if not resultado_procedimiento["valido"]:
                for error in resultado_procedimiento["errores"]:
                    st.error(error)
                return False
        
            observaciones_finales = (
                observaciones_finales
                + "\n"
                + resultado_procedimiento["observaciones_extra"]
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
