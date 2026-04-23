import streamlit as st
from modules.ordenes import obtener_ordenes, obtener_historico
from modules.outlook import importar_y_crear_ots_automaticamente


def pantalla_panel():
    st.subheader("📊 Panel general")

    st.markdown("---")
    st.subheader("📩 Incidencias Outlook")

    if st.button("🔄 Importar incidencias y crear OT"):
        ok, mensaje = importar_y_crear_ots_automaticamente()

        if ok:
            st.success(mensaje)
        else:
            st.error(mensaje)

    ordenes = obtener_ordenes()
    historico = obtener_historico()

    abiertas = len([o for o in ordenes if o[3] == "Abierta"])
    en_curso = len([o for o in ordenes if o[3] == "En curso"])
    pendiente_material = len([o for o in ordenes if o[3] == "Pendiente material"])
    finalizadas = len(historico)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Abiertas", abiertas)
    c2.metric("En curso", en_curso)
    c3.metric("Pend. material", pendiente_material)
    c4.metric("Finalizadas", finalizadas)

    st.info("Panel general base. Luego meteremos aquí Outlook y métricas más finas.")