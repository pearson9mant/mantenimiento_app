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

    with tab1:
        pantalla_inventario_aulas()

    with tab2:
        pantalla_preventivo_aulas()

    with tab3:
        st.info(
            "Próximamente se mostrarán aquí las correctivas generadas desde las inspecciones de espacios."
        )

    with tab4:
        st.info(
            "Próximamente se mostrará aquí el histórico completo de inspecciones por espacio."
        )
