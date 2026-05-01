import streamlit as st
from modules.ordenes import obtener_ordenes, obtener_historico


def obtener_tipo_solicitante_activa(o):
    if len(o) >= 16:
        return o[15] or "Operarios"
    return "Operarios"


def obtener_tipo_solicitante_historico(h):
    if len(h) >= 18:
        return h[17] or "Operarios"
    return "Operarios"


def pantalla_ordenes_lectura():
    st.subheader("📋 Órdenes")

    tab1, tab2 = st.tabs(["Activas", "Histórico"])

    with tab1:
        ordenes = obtener_ordenes()

        if not ordenes:
            st.info("No hay órdenes activas")
        else:
            for o in ordenes:
                (
                    _,
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
                    *resto
                ) = o

                tipo_solicitante = obtener_tipo_solicitante_activa(o)

                st.markdown(
                    f"**{numero_ot}** | {prioridad} | {area or '-'} | **{estado}**  \n"
                    f"{descripcion}  \n"
                    f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                    f"📌 Solicitante: **{tipo_solicitante}**  \n"
                    f"👷 Asignado a: {operario or '-'}"
                )
                st.markdown("---")

    with tab2:
        historico = obtener_historico()

        if not historico:
            st.info("No hay órdenes finalizadas")
        else:
            for h in historico:
                (
                    _,
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
                    *resto
                ) = h

                fecha_cierre = h[14] if len(h) > 14 else "-"
                observaciones_cierre = h[15] if len(h) > 15 else ""
                tipo_solicitante = obtener_tipo_solicitante_historico(h)

                st.markdown(
                    f"**{numero_ot}** | {prioridad} | {area or '-'} | **{estado}**  \n"
                    f"{descripcion}  \n"
                    f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                    f"📌 Solicitante: **{tipo_solicitante}**  \n"
                    f"👷 Asignado a: {operario or '-'} | Cierre: {fecha_cierre or '-'}"
                )

                if observaciones_cierre:
                    st.caption(f"📝 {observaciones_cierre}")

                st.markdown("---")
