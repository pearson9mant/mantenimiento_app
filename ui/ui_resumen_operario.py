import streamlit as st
from modules.ordenes import obtener_ordenes_operario

def pantalla_resumen_operario():
    st.subheader("👷 Mi resumen")

    operario = st.session_state.get("operario_activo", "")

    if not operario:
        st.info("No hay operario activo.")
        return

    ordenes = obtener_ordenes_operario(operario)

    abiertas = len([o for o in ordenes if o[3] == "Abierta"])
    en_curso = len([o for o in ordenes if o[3] == "En curso"])
    pendiente_material = len([o for o in ordenes if o[3] == "Pendiente material"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Operario", operario)
    c2.metric("Abiertas", abiertas)
    c3.metric("En curso", en_curso)
    c4.metric("Pend. material", pendiente_material)

    st.caption("Resumen rápido del operario activo.")