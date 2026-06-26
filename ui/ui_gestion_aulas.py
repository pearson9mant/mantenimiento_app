import streamlit as st

from ui.ui_inventario_aulas import pantalla_inventario_aulas
from ui.preventivo_aulas import pantalla_preventivo_aulas


def pantalla_gestion_aulas():
    st.subheader("🏫 Gestión de aulas")

    st.info(
        "Desde aquí se gestionará el aula completa: inventario, inspecciones, "
        "correctivos e histórico."
    )

    tab1, tab2 = st.tabs([
        "📦 Inventario",
        "🔎 Inspecciones",
    ])

    with tab1:
        pantalla_inventario_aulas()

    with tab2:
        pantalla_preventivo_aulas()
