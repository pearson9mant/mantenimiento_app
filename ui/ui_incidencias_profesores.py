import streamlit as st
from datetime import datetime

from modules.ordenes import crear_orden, obtener_siguiente_numero_ot
from pathlib import Path


ESPACIOS_POR_EDIFICIO = {
    "Infantil/Primaria": [
        "I3A", "I3B", "I3C",
        "I4A", "I4B", "I4C",
        "I5A", "I5B", "I5C",
        "1A", "1B", "1C",
        "2A", "2B", "2C",
        "3A", "3B", "3C",
        "4A", "4B", "4C",
        "5A", "5B", "5C",
        "6A", "6B", "6C",
        "Comedor niños",
        "Comedor profesores",
        "Patio cuadrado",
        "Patio fútbol",
        "Patio patines",
        "Capilla",
        "Secretaría",
        "Sala profesores",
        "Teatro",
        "Pasillos",
        "WC",
        "General",
        "Otro"
    ],
    "Llar": [
        "I1A", "I1B", "I1C",
        "I2A", "I2B", "I2C",
        "Sala polivalente",
        "Sala profesores",
        "Pasillo",
        "Almacén",
        "Despacho gym",
        "Vestuario femenino",
        "Vestuario masculino",
        "Patio",
        "WC",
        "Secretaría",
        "General",
        "Otro"
    ],
    "Edif. A": [
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillo",
        "WC",
        "General",
        "Otro"
    ],
    "Edif. B": [
        "General",
        "Laboratorio",
        "Aula música",
        "Aula informática",
        "Pasillo",
        "WC",
        "Otro"
    ],
    "Edif. C": [
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillo",
        "WC",
        "General",
        "Otro"
    ],
}


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

    espacios = ESPACIOS_POR_EDIFICIO.get(edificio, ["General", "Otro"])

    espacio_seleccionado = st.selectbox(
        "Espacio / Aula",
        espacios
    )

    if espacio_seleccionado == "Otro":
        espacio = st.text_input(
            "Escribe el espacio",
            placeholder="Ejemplo: despacho, almacén, aula..."
        )
    else:
        espacio = espacio_seleccionado

    descripcion = st.text_area(
        "¿Qué ocurre?",
        placeholder="Describe brevemente la incidencia",
        height=120
    )

    foto = st.file_uploader(
        "Añadir foto (opcional)",
        type=["jpg", "jpeg", "png"]
    )
    foto_bytes = None

    if foto is not None:
        foto_bytes = foto.getvalue()
        st.image(foto_bytes, caption="Foto adjunta", use_container_width=True)

    prioridad = st.radio(
        "Prioridad",
        ["🟢 Baja", "🟡 Normal", "🔴 Alta"],
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

        if not str(espacio).strip():
            st.warning("Falta indicar el espacio.")
            return

        if centro == "Pearson 9":
            operario = "Luis Lozano"
        else:
            operario = "J.A. Almeda"

        numero_ot = obtener_siguiente_numero_ot(centro, "INC")
        fecha_origen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ruta_foto = ""

        if foto_bytes is not None:
            carpeta = Path("uploads/incidencias")
            carpeta.mkdir(parents=True, exist_ok=True)

            extension = foto.name.split(".")[-1].lower()
            nombre_foto = f"{numero_ot}.{extension}"
            ruta_foto = str(carpeta / nombre_foto)

            with open(ruta_foto, "wb") as f:
                f.write(foto_bytes)

        prioridad = prioridad.replace("🟢 ", "").replace("🟡 ", "").replace("🔴 ", "")

        datos = (
            numero_ot,
            descripcion.strip(),
            "Abierta",
            centro,
            edificio,
            str(espacio).strip(),
            "Otros",
            prioridad,
            operario,
            f"Profesores - {tipo_solicitante}",
            nombre_solicitante.strip(),
            fecha_origen,
            ruta_foto
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
