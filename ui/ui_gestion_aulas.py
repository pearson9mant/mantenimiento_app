import streamlit as st

from ui.ui_inventario_aulas import pantalla_inventario_aulas
from ui.preventivo_aulas import pantalla_preventivo_aulas


def pantalla_gestion_aulas():

    st.subheader("🏫 Gestión de espacios")

    st.caption(
        "Inventario, inspecciones, correctivos e histórico de todos los espacios del centro."
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Inventario",
        "🔎 Inspecciones",
        "🔧 Correctivos",
        "📋 Histórico",
    ])

    # ----------------------------------
    # INVENTARIO
    # ----------------------------------
    with tab1:
        pantalla_inventario_aulas()

    # ----------------------------------
    # INSPECCIONES
    # ----------------------------------
    with tab2:
        pantalla_preventivo_aulas()

    # ----------------------------------
    # CORRECTIVOS
    # ----------------------------------
    with tab3:
        st.info("Próximamente se mostrarán aquí todas las averías detectadas en los espacios y su estado.")

    # ----------------------------------
    # HISTÓRICO
    # ----------------------------------
    with tab4:
        st.info("Próximamente se mostrará el histórico completo de inspecciones.")
