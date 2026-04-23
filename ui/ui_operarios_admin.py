import streamlit as st
from config import OPERARIOS

def pantalla_operarios_admin():

    st.subheader("👷 Operarios")
    st.info("Selecciona un operario para ver su panel")

    for op in OPERARIOS:
        if st.button(f"👷 {op}", use_container_width=True):

            st.session_state["vista_operario"] = True
            st.session_state["operario_activo"] = op

            st.rerun()