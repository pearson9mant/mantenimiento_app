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

    # 🔙 Volver a administración SOLO si vienes desde vista admin
    if st.session_state.get("vista_operario", False):
        if st.button("🔙 Volver a administración"):
            st.session_state["vista_operario"] = False
            st.rerun()

    # ✅ Operario desde sesión (NO editable)
    operario_sel = st.session_state.get("operario_activo", "")

    if not operario_sel:
        st.warning("No hay operario seleccionado.")
        return

    st.info(f"Operario: {operario_sel}")

    ordenes_operario = obtener_ordenes_operario(operario_sel.strip())
    materiales_select = obtener_materiales_para_select()

    # -------------------
    # FILTROS
    # -------------------
    f1, f2 = st.columns(2)

    with f1:
        filtro_area = st.text_input("Filtrar por área")

    with f2:
        filtro_estado = st.selectbox(
            "Filtrar por estado",
            ["Todas", "Abierta", "En curso", "Pendiente material"]
        )

    if filtro_area.strip():
        ordenes_operario = [
            o for o in ordenes_operario
            if (o[8] or "").lower() == filtro_area.strip().lower()
        ]

    if filtro_estado != "Todas":
        ordenes_operario = [o for o in ordenes_operario if o[3] == filtro_estado]

    # -------------------
    # KPIs
    # -------------------
    total_abiertas = len([o for o in ordenes_operario if o[3] == "Abierta"])
    total_curso = len([o for o in ordenes_operario if o[3] == "En curso"])
    total_material = len([o for o in ordenes_operario if o[3] == "Pendiente material"])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total", len(ordenes_operario))
    k2.metric("Abiertas", total_abiertas)
    k3.metric("En curso", total_curso)
    k4.metric("Pend. material", total_material)

    if not ordenes_operario:
        st.info("No hay órdenes para este operario con esos filtros.")
        return

    # -------------------
    # LISTADO OT
    # -------------------
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

        with st.container():
            st.markdown("---")

            c1, c2 = st.columns([3.5, 2])

            with c1:
                st.markdown(
                    f"**{num_ot}** | {prioridad} | {area or '-'}  \n"
                    f"{desc}  \n"
                    f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                    f"👷 {operario or '-'} | Estado actual: **{est}**"
                )

            with c2:
                nuevo_estado = st.selectbox(
                    f"Estado {num_ot}",
                    ["Abierta", "En curso", "Pendiente material", "Finalizada"],
                    index=["Abierta", "En curso", "Pendiente material", "Finalizada"].index(est)
                    if est in ["Abierta", "En curso", "Pendiente material", "Finalizada"] else 0,
                    key=f"estado_operario_{id_orden}"
                )

                if nuevo_estado != est and nuevo_estado != "Finalizada":
                    if st.button(f"Actualizar {num_ot}", key=f"act_operario_{id_orden}"):
                        actualizar_estado(id_orden, nuevo_estado)
                        st.success(f"{num_ot} actualizada a {nuevo_estado}.")
                        st.rerun()

            # -------------------
            # TRABAJO OT
            # -------------------
            with st.expander(f"Trabajar OT {num_ot}"):

                observaciones_fin = st.text_area(
                    "Observaciones de cierre",
                    key=f"obs_operario_{id_orden}"
                )

                st.markdown("#### Material usado en esta OT")

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

                b1, b2, b3 = st.columns(3)

                with b1:
                    if st.button(f"A En curso {num_ot}", key=f"curso_operario_{id_orden}"):
                        actualizar_estado(id_orden, "En curso")
                        st.success(f"{num_ot} pasada a En curso.")
                        st.rerun()

                with b2:
                    if st.button(f"A Pend. material {num_ot}", key=f"mat_operario_{id_orden}"):
                        actualizar_estado(id_orden, "Pendiente material")
                        st.success(f"{num_ot} pasada a Pendiente material.")
                        st.rerun()

                with b3:
                    if st.button(f"Finalizar {num_ot}", key=f"fin_operario_{id_orden}"):

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