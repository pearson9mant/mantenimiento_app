import streamlit as st


def pantalla_incidencias_profesores():
    st.markdown("""
    <style>
    .inc-card {
        background: #f7f7f7;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #ddd;
        margin-bottom: 12px;
    }

    div.stButton > button {
        width: 100%;
        height: 58px;
        border-radius: 12px;
        font-size: 18px;
        font-weight: 600;
    }

    textarea {
        font-size: 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 📩 Comunicar incidencia")
    st.caption("Formulario de prueba para incidencias desde QR")

    st.markdown('<div class="inc-card">', unsafe_allow_html=True)

    centro = st.selectbox(
        "Centro",
        ["Pearson 22", "Pearson 9"]
    )

    if centro == "Pearson 22":
        edificios = ["Infantil/Primaria", "Llar"]
    else:
        edificios = ["Edif. A", "Edif. B", "Edif. C"]

    edificio = st.selectbox("Edificio", edificios)

    espacio = st.text_input(
        "Espacio / Aula",
        placeholder="Ejemplo: 3A, comedor, patio..."
    )

    descripcion = st.text_area(
        "¿Qué ocurre?",
        placeholder="Describe brevemente la incidencia",
        height=120
    )

    prioridad = st.radio(
        "Prioridad",
        ["Baja", "Media", "Alta"],
        horizontal=True
    )

    tipo_solicitante = st.radio(
        "Quién envía",
        ["Profesor", "Administración", "Dirección"],
        horizontal=True
    )

    nombre_solicitante = st.text_input(
        "Nombre",
        placeholder="Nombre de quien envía"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("📨 Enviar incidencia"):
        if not descripcion.strip():
            st.warning("Falta describir la incidencia.")
            return

        if not nombre_solicitante.strip():
            st.warning("Falta poner el nombre de quien envía.")
            return

        if centro == "Pearson 9":
            operario = "Luis Lozano"
        else:
            operario = "J.A. Almeda"

        st.success("✅ Prueba correcta. Todavía no se ha guardado en la base de datos.")

        st.info(f"""
        **Resumen de la incidencia:**

        **Centro:** {centro}  
        **Edificio:** {edificio}  
        **Espacio:** {espacio}  
        **Prioridad:** {prioridad}  
        **Solicitante:** {nombre_solicitante}  
        **Tipo:** {tipo_solicitante}  
        **Asignado a:** {operario}  

        **Descripción:**  
        {descripcion}
        """)
