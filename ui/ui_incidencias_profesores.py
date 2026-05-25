import streamlit as st
from datetime import datetime
from pathlib import Path

from modules.ordenes import crear_orden, obtener_siguiente_numero_ot


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


def limpiar_nombre_archivo(texto):
    texto = str(texto or "")
    caracteres_malos = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for c in caracteres_malos:
        texto = texto.replace(c, "_")
    return texto.replace(" ", "_")


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

    fotos = st.file_uploader(
        "Añadir fotos (opcional, máximo 5)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="fotos_incidencia_profesor"
    )

    fotos_validas = []
    fotos_error = False

    if fotos:
        if len(fotos) > 5:
            st.warning("Máximo 5 fotos por incidencia.")
            fotos_error = True
        else:
            cols = st.columns(3)

            for i, foto in enumerate(fotos):
                if foto.size > 5 * 1024 * 1024:
                    st.warning(f"La foto {foto.name} supera 5 MB.")
                    fotos_error = True
                    continue

                foto_bytes = foto.getvalue()
                fotos_validas.append((foto, foto_bytes))

                with cols[i % 3]:
                    st.image(
                        foto_bytes,
                        caption=f"Foto {i + 1}",
                        use_container_width=True
                    )

    prioridad = st.radio(
        "Prioridad",
        ["🟢 Baja", "🟡 Normal", "🔴 Alta"],
        horizontal=True
    )

    tipo_solicitante = st.radio(
        "Quién envía",
        ["Profesores", "Cap de estudio", "Dirección", "Operarios"],
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

        if fotos_error:
            st.error("Revisa las fotos. Máximo 5 fotos y máximo 5 MB por foto.")
            return

        if centro == "Pearson 9":
            operario = "Luis Lozano"
        else:
            operario = "J.A. Almeda"

        numero_ot = obtener_siguiente_numero_ot(centro, "INC")
        fecha_origen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rutas_fotos = []

        if fotos_validas:
            try:
                carpeta = Path("uploads/incidencias")
                carpeta.mkdir(parents=True, exist_ok=True)

                for i, (foto, foto_bytes) in enumerate(fotos_validas, start=1):
                    extension = foto.name.split(".")[-1].lower()
                    nombre_original = limpiar_nombre_archivo(foto.name)

                    nombre_foto = limpiar_nombre_archivo(
                        f"{numero_ot}_{i}_{centro}_{edificio}_{espacio}_{nombre_original}"
                    )

                    if not nombre_foto.lower().endswith(f".{extension}"):
                        nombre_foto = f"{nombre_foto}.{extension}"

                    ruta_foto = str(carpeta / nombre_foto)

                    with open(ruta_foto, "wb") as f:
                        f.write(foto_bytes)

                    rutas_fotos.append(ruta_foto)

            except Exception as e:
                st.error(f"No se pudieron guardar las fotos: {e}")
                return

        ruta_foto = "|".join(rutas_fotos)

        prioridad_limpia = prioridad.replace("🟢 ", "").replace("🟡 ", "").replace("🔴 ", "")

        datos = (
            numero_ot,
            descripcion.strip(),
            "Abierta",
            centro,
            edificio,
            str(espacio).strip(),
            "Otros",
            prioridad_limpia,
            operario,
            "APP",
            nombre_solicitante.strip(),
            fecha_origen,
            ruta_foto,
            tipo_solicitante
        )

        crear_orden(datos)

        st.success(f"✅ Incidencia guardada correctamente. Nº OT: {numero_ot}")

        if rutas_fotos:
            st.info(f"📷 Fotos adjuntas: {len(rutas_fotos)}")

        st.info(f"""
        **Resumen de la incidencia:**

        **Nº OT:** {numero_ot}  
        **Centro:** {centro}  
        **Edificio:** {edificio}  
        **Espacio:** {espacio}  
        **Prioridad:** {prioridad_limpia}  
        **Solicitante:** {nombre_solicitante}  
        **Tipo:** {tipo_solicitante}  
        **Asignado a:** {operario}  

        **Descripción:**  
        {descripcion}
        """)
