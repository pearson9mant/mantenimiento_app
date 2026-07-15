import streamlit as st

from ui.ui_qr_aulas import pantalla_qr_aulas


def pantalla_placas_qr():
    st.markdown("## 📄 Placas QR")

    st.info(
        "Generación y gestión de placas QR del "
        "Sistema Integral de Mantenimiento."
    )

    tab1, tab2, tab3 = st.tabs([
        "🏫 Espacios",
        "🌍 General",
        "⚙️ Configuración",
    ])

    with tab1:
        pantalla_qr_aulas()

    with tab2:
        st.markdown("### 🌍 Placa general")
        st.caption(
            "Aquí generaremos la placa general para recepción, "
            "secretaría, sala de profesores y zonas comunes."
        )

    with tab3:
        st.markdown("### ⚙️ Configuración")
        st.caption(
            "Aquí configuraremos el tamaño, formato y acabado "
            "de las placas sin modificar código."
        )
