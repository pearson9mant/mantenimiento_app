import streamlit as st
from config import CENTROS, EDIFICIOS, AREAS, OPERARIOS, ESPACIOS
from modules.ordenes import (
    crear_orden,
    obtener_ordenes,
    finalizar_orden,
    obtener_siguiente_numero_ot,
    actualizar_estado,
    obtener_historico,
    borrar_orden,
    borrar_orden_historico,
)


def obtener_origen_ot(origen):
    origen_txt = (origen or "").strip().upper()

    if origen_txt == "LEGIONELLA":
        return "Legionella"
    if origen_txt == "OUTLOOK":
        return "Profesor"
    if origen_txt == "PREVENTIVO":
        return "Preventivo"
    if origen_txt == "APP":
        return "App"
    return "General"


def pantalla_ordenes():
    st.subheader("📋 Órdenes de trabajo")

    tab1, tab2, tab3 = st.tabs(["➕ Nueva orden", "📄 Activas", "🗂️ Histórico"])

    # ----------------------
    # TAB 1 - NUEVA ORDEN
    # ----------------------
    with tab1:
        c1, c2 = st.columns(2)

        with c1:
            centro = st.selectbox("Centro", CENTROS, key="orden_centro")

            st.info("Número de OT: se asignará al crear la orden")

            edificios_disponibles = EDIFICIOS.get(centro, [])
            edificio = st.selectbox(
                "Edificio",
                edificios_disponibles,
                key=f"orden_edificio_{centro}"
            )

            espacios_disponibles = ESPACIOS.get(edificio, ["General", "Otro"])
            espacio_sel = st.selectbox(
                "Espacio",
                espacios_disponibles,
                key=f"orden_espacio_{edificio}"
            )

            if espacio_sel == "Otro":
                espacio = st.text_input("Especificar espacio nuevo", key="orden_espacio_otro")
            else:
                espacio = espacio_sel

        with c2:
            with st.form("form_nueva_orden", clear_on_submit=True):
                descripcion = st.text_area("Descripción", key="orden_descripcion")
                area = st.selectbox("Área", AREAS, key="orden_area")
                prioridad = st.selectbox("Prioridad", ["Baja", "Media", "Alta"], key="orden_prioridad")
                operario_sel = st.selectbox("Operario", OPERARIOS, key="orden_operario")

                if operario_sel == "Otro":
                    operario = st.text_input("Nombre operario", key="orden_operario_otro")
                else:
                    operario = operario_sel

                boton_crear = st.form_submit_button("✅ Crear orden", use_container_width=True)

                if boton_crear:
                    if not descripcion.strip():
                        st.warning("La descripción es obligatoria")
                    elif not operario.strip():
                        st.warning("Indica un operario")
                    elif not str(espacio).strip():
                        st.warning("Indica un espacio")
                    else:
                        numero = obtener_siguiente_numero_ot(centro, "INC")

                        crear_orden((
                            numero,
                            descripcion,
                            "Abierta",
                            centro,
                            edificio,
                            espacio,
                            area,
                            prioridad,
                            operario,
                            "APP"
                        ))

                        st.success(f"Orden creada correctamente: {numero}")
                        st.rerun()

    # ----------------------
    # TAB 2 - ACTIVAS
    # ----------------------
    with tab2:
        ordenes = obtener_ordenes()

        if ordenes:
            f1, f2 = st.columns(2)

            with f1:
                filtro_estado = st.selectbox(
                    "Estado",
                    ["Todas", "Abierta", "En curso", "Pendiente material", "Incidencias"],
                    key="filtro_estado_admin_ot"
                )

            with f2:
                filtro_origen = st.selectbox(
                    "Origen",
                    ["Todos", "LEGIONELLA", "OUTLOOK", "APP", "PREVENTIVO"],
                    key="filtro_origen_admin_ot"
                )

            if filtro_origen != "Todos":
                ordenes = [
                    o for o in ordenes
                    if (o[11] or "").strip().upper() == filtro_origen
                ]

            total_abiertas = len([o for o in ordenes if o[3] == "Abierta"])
            total_curso = len([o for o in ordenes if o[3] == "En curso"])
            total_material = len([o for o in ordenes if o[3] == "Pendiente material"])
            total_incidencias = len([
                o for o in ordenes
                if (o[11] or "").strip().upper() == "LEGIONELLA"
            ])

            if filtro_estado == "Incidencias":
                ordenes = [
                    o for o in ordenes
                    if (o[11] or "").strip().upper() == "LEGIONELLA"
                ]
            elif filtro_estado != "Todas":
                ordenes = [o for o in ordenes if o[3] == filtro_estado]

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Abiertas", total_abiertas)
            k2.metric("En curso", total_curso)
            k3.metric("Material", total_material)
            k4.metric("Incidencias", total_incidencias)

            st.markdown("---")

        if not ordenes:
            st.info("No hay órdenes activas")
        else:
            for o in ordenes:
                if len(o) == 14:
                    (
                        id_orden,
                        numero_ot,
                        descripcion,
                        estado,
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
                    ) = o
                else:
                    (
                        id_orden,
                        numero_ot,
                        descripcion,
                        estado,
                        fecha,
                        centro,
                        edificio,
                        espacio,
                        area,
                        prioridad,
                        operario,
                        origen,
                    ) = o
                    solicitante = ""
                    fecha_origen = ""

                origen_label = obtener_origen_ot(origen)

                with st.container():
                    c1, c2, c3, c4 = st.columns([5, 2, 2, 2])

                    with c1:
                        st.markdown(
                            f"**{numero_ot}** | {prioridad} | {area or '-'} | {origen_label}  \n"
                            f"{descripcion}  \n"
                            f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                            f"👷 {operario or '-'} | Estado: **{estado}**"
                        )

                        if solicitante:
                            st.caption(f"Solicitante: {solicitante}")

                        if fecha_origen:
                            st.caption(f"Fecha origen: {fecha_origen}")

                    with c2:
                        estados = ["Abierta", "En curso", "Pendiente material", "Finalizada"]

                        nuevo_estado = st.selectbox(
                            f"Estado {numero_ot}",
                            estados,
                            index=estados.index(estado) if estado in estados else 0,
                            key=f"estado_admin_{id_orden}"
                        )

                        if nuevo_estado != estado and nuevo_estado != "Finalizada":
                            if st.button(f"Actualizar {numero_ot}", key=f"act_admin_{id_orden}"):
                                actualizar_estado(id_orden, nuevo_estado)
                                st.rerun()

                    with c3:
                        if st.button(f"Finalizar {numero_ot}", key=f"fin_admin_{id_orden}"):
                            finalizar_orden(id_orden)
                            st.success(f"{numero_ot} finalizada")
                            st.rerun()

                    with c4:
                        confirmar_activa = st.checkbox(
                            "Confirmar",
                            key=f"conf_admin_activas_{id_orden}"
                        )

                        if st.button(
                            f"🗑️ Borrar {numero_ot}",
                            key=f"del_admin_activas_{id_orden}"
                        ):
                            if confirmar_activa:
                                borrar_orden(id_orden)
                                st.warning(f"{numero_ot} eliminada")
                                st.rerun()
                            else:
                                st.error("Debes marcar la confirmación antes de borrar")

                    st.markdown("---")

    # ----------------------
    # TAB 3 - HISTÓRICO
    # ----------------------
    with tab3:
        historico = obtener_historico()

        if not historico:
            st.info("No hay órdenes finalizadas")
        else:
            for h in historico:
                if len(h) == 16:
                    (
                        id_orden,
                        numero_ot,
                        descripcion,
                        estado,
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
                        fecha_cierre,
                        observaciones_cierre,
                    ) = h
                else:
                    (
                        id_orden,
                        numero_ot,
                        descripcion,
                        estado,
                        fecha,
                        centro,
                        edificio,
                        espacio,
                        area,
                        prioridad,
                        operario,
                        origen,
                        fecha_cierre,
                        observaciones_cierre,
                    ) = h
                    solicitante = ""
                    fecha_origen = ""

                origen_label = obtener_origen_ot(origen)

                with st.container():
                    c1, c2 = st.columns([6, 2])

                    with c1:
                        st.markdown(
                            f"**{numero_ot}** | {prioridad} | {area or '-'} | {origen_label}  \n"
                            f"{descripcion}  \n"
                            f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                            f"👷 {operario or '-'} | Cierre: {fecha_cierre or '-'}"
                        )

                        if solicitante:
                            st.caption(f"Solicitante: {solicitante}")

                        if fecha_origen:
                            st.caption(f"Fecha origen: {fecha_origen}")

                        if observaciones_cierre:
                            st.caption(f"📝 {observaciones_cierre}")

                    with c2:
                        confirmar_hist = st.checkbox(
                            "Confirmar",
                            key=f"conf_admin_hist_{id_orden}"
                        )

                        if st.button(
                            f"🗑️ Borrar {numero_ot}",
                            key=f"del_admin_hist_{id_orden}"
                        ):
                            if confirmar_hist:
                                borrar_orden_historico(id_orden)
                                st.warning(f"{numero_ot} eliminada del histórico")
                                st.rerun()
                            else:
                                st.error("Debes marcar la confirmación antes de borrar")

                    st.markdown("---")