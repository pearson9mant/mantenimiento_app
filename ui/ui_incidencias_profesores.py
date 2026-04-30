import streamlit as st
from datetime import datetime

from modules.ordenes import crear_orden, obtener_siguiente_numero_ot


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

        numero_ot = obtener_siguiente_numero_ot(centro, "INC")
        fecha_origen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        datos = (
            numero_ot,
            descripcion.strip(),
            "Abierta",
            centro,
            edificio,
            espacio.strip(),
            "Otros",
            prioridad,
            operario,
            f"Profesores - {tipo_solicitante}",
            nombre_solicitante.strip(),
            fecha_origen
        )

        crear_orden(datos)

        st.success(f"✅ Incidencia guardada correctamente. Nº OT: {numero_ot}")

        st.info(f"""
        **Resumen de la incidencia:**

        **Nº OT:** {numero_ot}  
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
