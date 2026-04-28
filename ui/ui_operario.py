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

    total_abiertas = len([o for o in ordenes_operario if o[3] == "Abierta"])
    total_curso = len([o for o in ordenes_operario if o[3] == "En curso"])
    total_material = len([o for o in ordenes_operario if o[3] == "Pendiente material"])

    k1, k2, k3 = st.columns(3)
    k1.metric("Abiertas", total_abiertas)
    k2.metric("En curso", total_curso)
    k3.metric("Material", total_material)

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
                finalizar_orden(id_orden, "")
                st.success(f"{num_ot} finalizada correctamente.")
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

            codigo_sel = ""
            cantidad_material = 0.0

            if usar_material:
                if materiales_select:
                    opciones_material = [
                        f"{codigo} | {material} | Stock: {stock_actual} {unidad}"
                        for codigo, material, stock_actual, unidad in materiales_select
                    ]

                    material_ot = st.selectbox(
                        "Selecciona material",
                        opciones_material,
                        key=f"material_ot_{id_orden}"
                    )

                    codigo_sel = material_ot.split(" | ")[0]

                    cantidad_material = st.number_input(
                        "Cantidad usada",
                        min_value=0.0,
                        step=1.0,
                        key=f"cantidad_material_ot_{id_orden}"
                    )
                else:
                    st.info("No hay materiales dados de alta en Inventario.")

            if st.button(
                f"Finalizar con observaciones/material {num_ot}",
                key=f"fin_completo_operario_{id_orden}",
                use_container_width=True
            ):
                if usar_material and materiales_select:
                    if cantidad_material <= 0:
                        st.warning("Indica una cantidad de material mayor que 0.")
                    else:
                        ok, mensaje = registrar_movimiento_inventario(
                            codigo_material=codigo_sel,
                            tipo_movimiento="Salida",
                            cantidad=cantidad_material,
                            motivo=f"Consumo en OT {num_ot}",
                            numero_ot=num_ot,
                            operario=operario_sel
                        )

                        if not ok:
                            st.error(mensaje)
                        else:
                            finalizar_orden(id_orden, observaciones_fin)
                            st.success(f"{num_ot} finalizada y material descontado correctamente.")
                            st.rerun()
                else:
                    finalizar_orden(id_orden, observaciones_fin)
                    st.success(f"{num_ot} finalizada correctamente.")
                    st.rerun()
