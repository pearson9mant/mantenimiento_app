import streamlit as st

from modules.ordenes import (
    obtener_ordenes_operario,
    actualizar_estado,
    finalizar_orden
)

from modules.inventario import (
    obtener_materiales_para_select,
    registrar_movimiento_inventario
)


def rol_actual():
    return str(st.session_state.get("rol", "")).strip().lower()


def usuario_actual():
    return str(st.session_state.get("usuario", "")).strip()


def es_admin():
    return rol_actual() == "admin"


def es_gerencia():
    return rol_actual() == "gerencia"


def es_operario():
    return rol_actual() == "operario"


def normalizar_txt(valor):
    return str(valor or "").strip().lower()


def obtener_operario_fila(fila):
    try:
        return fila[10]
    except Exception:
        return ""


# =====================================================
# KPIs OPERARIO - SEGURO, SIN TOCAR FLUJO ACTUAL
# =====================================================

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
    """
    Si es operario real: solo puede ver sus propias órdenes.
    Si es admin/gerencia en vista operario: respeta operario_activo.
    """
    if not ordenes:
        return []

    if es_operario():
        usuario = normalizar_txt(usuario_actual())
        return [
            o for o in ordenes
            if normalizar_txt(obtener_operario_fila(o)) == usuario
        ]

    return [
        o for o in ordenes
        if normalizar_txt(obtener_operario_fila(o)) == normalizar_txt(operario_sel)
    ]


def descomponer_orden_operario(fila):
    if len(fila) >= 16:
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
    )


def pantalla_operario():
    st.subheader("👷 Vista operario")

    if st.session_state.get("vista_operario", False):
        if st.button("🔙 Volver a administración"):
            st.session_state["vista_operario"] = False
            st.rerun()

    operario_sel = st.session_state.get("operario_activo", "")

    # Seguridad PRO:
    # Si entra un operario real, se fuerza siempre su usuario de sesión.
    if es_operario():
        operario_sel = usuario_actual()
        st.session_state["operario_activo"] = operario_sel

    if not operario_sel:
        st.warning("No hay operario seleccionado.")
        return

    st.info(f"Operario: {operario_sel}")

    ordenes_operario = obtener_ordenes_operario(operario_sel.strip())
    ordenes_operario = filtrar_seguridad_operario(ordenes_operario, operario_sel)

    # -------------------------------
    # KPIs DEL OPERARIO
    # -------------------------------
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
        ) = descomponer_orden_operario(fila)

        # Segunda seguridad: si por cualquier motivo entra una fila incorrecta, no se muestra.
        if es_operario() and normalizar_txt(operario) != normalizar_txt(usuario_actual()):
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

            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button("▶\nEn curso", key=f"curso_rapido_{id_orden}", use_container_width=True):
                    actualizar_estado(id_orden, "En curso")
                    st.rerun()

            with b2:
                if st.button("📦\nMaterial", key=f"mat_rapido_{id_orden}", use_container_width=True):
                    actualizar_estado(id_orden, "Pendiente material")
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
                        finalizar_orden(id_orden, "")
                        st.session_state[f"confirmar_fin_rapido_{id_orden}"] = False
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

                            if usar_material and materiales_select:

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
                                        finalizar_orden(id_orden, observaciones_fin)
                                        st.session_state[f"confirmar_fin_completo_{id_orden}"] = False
                                        st.session_state.pop(f"materiales_confirmados_{id_orden}", None)
                                        st.success(f"{num_ot} finalizada y materiales descontados correctamente.")
                                        st.rerun()

                            else:
                                finalizar_orden(id_orden, observaciones_fin)
                                st.session_state[f"confirmar_fin_completo_{id_orden}"] = False
                                st.session_state.pop(f"materiales_confirmados_{id_orden}", None)
                                st.success(f"{num_ot} finalizada correctamente.")
                                st.rerun()

                    with c2:
                        if st.button("❌\nCancelar", key=f"no_fin_completo_{id_orden}", use_container_width=True):
                            st.session_state[f"confirmar_fin_completo_{id_orden}"] = False
                            st.session_state.pop(f"materiales_confirmados_{id_orden}", None)
                            st.rerun()
