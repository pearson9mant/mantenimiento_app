import streamlit as st
from modules.ordenes import obtener_ordenes, obtener_historico

def pantalla_ordenes_lectura():
    st.subheader("📋 Órdenes")

    tab1, tab2 = st.tabs(["Activas", "Histórico"])

    with tab1:
        ordenes = obtener_ordenes()

        if not ordenes:
            st.info("No hay órdenes activas")
        else:
            for o in ordenes:
                _, numero_ot, descripcion, estado, fecha, centro, edificio, espacio, area, prioridad, operario, origen, *resto = o

                st.markdown(
                    f"**{numero_ot}** | {prioridad} | {area or '-'} | **{estado}**  \n"
                    f"{descripcion}  \n"
                    f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                    f"👷 {operario or '-'}"
                )
                st.markdown("---")

    with tab2:
        historico = obtener_historico()

        if not historico:
            st.info("No hay órdenes finalizadas")
        else:
            for h in historico:
                _, numero_ot, descripcion, estado, fecha, centro, edificio, espacio, area, prioridad, operario, origen, fecha_cierre, observaciones_cierre = h

                st.markdown(
                    f"**{numero_ot}** | {prioridad} | {area or '-'}  \n"
                    f"{descripcion}  \n"
                    f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                    f"👷 {operario or '-'} | Cierre: {fecha_cierre or '-'}"
                )

                if observaciones_cierre:
                    st.caption(f"📝 {observaciones_cierre}")

                st.markdown("---")
