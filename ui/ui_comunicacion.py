import streamlit as st
from datetime import date


def pantalla_comunicacion(modo="nuevo"):

    if modo == "historico":
        st.title("📋 Mis solicitudes")
        st.info("Todavía no hay solicitudes para mostrar.")
        return

    st.title("📣 Comunicación")

    st.markdown("### Nueva solicitud")

    titulo = st.text_input(
        "Título",
        key="comunicacion_titulo"
    )

    espacio = st.text_input(
        "Espacio o lugar",
        key="comunicacion_espacio"
    )

    fecha_necesaria = st.date_input(
        "Fecha necesaria",
        value=date.today(),
        key="comunicacion_fecha"
    )

    descripcion = st.text_area(
        "Descripción",
        height=180,
        key="comunicacion_descripcion"
    )

    archivo = st.file_uploader(
        "Adjuntar archivo (opcional)",
        type=["pdf", "jpg", "jpeg", "png", "doc", "docx"],
        key="comunicacion_archivo"
    )

    if st.button(
        "📣 Enviar solicitud",
        key="comunicacion_enviar",
        use_container_width=True
    ):
        if not titulo.strip():
            st.warning("Escribe el título de la solicitud.")
            return

        if not espacio.strip():
            st.warning("Indica el espacio o lugar.")
            return

        if not descripcion.strip():
            st.warning("Escribe la descripción del trabajo.")
            return

        st.success("Formulario preparado correctamente. En el siguiente paso lo conectaremos con las órdenes de trabajo.")
