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


def pantalla_operario():
    st.subheader("👷 Vista operario")

    if st.session_state.get("vista_operario", False):
        if st.button("🔙 Volver a administración"):
            st.session_state["vista_operario"] = False
            st.rerun()

    operario_sel = st.session_state.get("operario_activo", "")

    if not operario_sel:
        st.warning("No hay operario seleccionado.")
        return

    st.info(f"Operario: {operario_sel}")

    ordenes_operario = obtener_ordenes_operario(operario_sel.strip())
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
            origen
        ) = fila

        st.markdown("---")

        estado_icono = {
            "Abierta": "🔴",
            "En curso": "🟠",
            "Pendiente material": "📦"
        }.get(est, "⚪")

        st.markdown(f"### {estado_icono} {num_ot}")
        st.markdown(f"**{prioridad}** | {area or '-'}")
        st.markdown(f"{desc}")
        st.caption(f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}")
        st.caption(f"Estado actual: {est}")

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
