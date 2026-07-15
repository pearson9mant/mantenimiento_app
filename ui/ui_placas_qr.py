import io

import qrcode
import streamlit as st

from ui.ui_qr_aulas import pantalla_qr_aulas


URL_BASE_APP = "https://mantenimiento-app-1.onrender.com"


def generar_qr_general():
    enlace = f"{URL_BASE_APP}/?modo=incidencias"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )

    qr.add_data(enlace)
    qr.make(fit=True)

    imagen = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)

    return enlace, buffer.getvalue()


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

        st.info(
            "Esta placa permite comunicar una incidencia cuando no existe "
            "un QR específico para el espacio."
        )

        enlace_general, qr_general = generar_qr_general()

        with st.container(border=True):
            st.markdown(
                """
                <div style="
                    text-align:center;
                    background:linear-gradient(135deg,#0f172a,#1d4ed8);
                    color:white;
                    border-radius:20px;
                    padding:22px;
                    margin-bottom:16px;
                    font-size:27px;
                    font-weight:900;
                    line-height:1.35;
                ">
                    LORETO MANTENIMIENTO
                    <br>
                    <span style="
                        font-size:14px;
                        font-weight:700;
                    ">
                        Sistema Integral de Mantenimiento
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div style="
                    text-align:center;
                    font-size:24px;
                    font-weight:900;
                    color:#0f172a;
                    margin-bottom:12px;
                ">
                    ¿Has detectado una incidencia?
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns([1, 2])

            with col1:
                st.image(
                    qr_general,
                    width=190,
                )

            with col2:
                st.markdown(
                    "**Comunica cualquier incidencia del colegio**"
                )

                st.write(
                    "Escanea el código con la cámara del móvil."
                )

                st.write(
                    "No necesitas instalar ninguna aplicación."
                )

                st.link_button(
                    "🔎 Probar formulario general",
                    enlace_general,
                    use_container_width=True,
                )

                st.download_button(
                    "⬇️ Descargar QR general",
                    data=qr_general,
                    file_name="QR_GENERAL_LORETO_MANTENIMIENTO.png",
                    mime="image/png",
                    use_container_width=True,
                    key="descargar_qr_general",
                )

        st.caption(
            "Pensada para recepción, secretaría, sala de profesores "
            "y otras zonas comunes."
        )

    with tab3:
        st.markdown("### ⚙️ Configuración")

        st.info(
            "Ajustes visuales y de impresión para las placas QR. "
            "Estos cambios no modifican los enlaces ni los códigos QR."
        )

        col1, col2 = st.columns(2)

        with col1:
            titulo_placa = st.text_input(
                "Título principal",
                value="LORETO MANTENIMIENTO",
                key="placas_titulo_principal",
            )

            subtitulo_placa = st.text_input(
                "Subtítulo",
                value="Sistema Integral de Mantenimiento",
                key="placas_subtitulo",
            )

            texto_accion = st.text_input(
                "Texto de acción",
                value="Comunicar una incidencia",
                key="placas_texto_accion",
            )

        with col2:
            tamano_placa = st.selectbox(
                "Tamaño recomendado",
                [
                    "90 × 120 mm",
                    "80 × 110 mm",
                    "70 × 100 mm",
                ],
                index=0,
                key="placas_tamano",
            )

            placas_por_pagina = st.selectbox(
                "Placas por página A4",
                [6, 4, 2],
                index=0,
                key="placas_por_pagina",
            )

            acabado = st.selectbox(
                "Acabado recomendado",
                [
                    "Vinilo adhesivo mate + laminado transparente",
                    "Vinilo adhesivo brillo + laminado transparente",
                    "Papel adhesivo plastificado",
                ],
                index=0,
                key="placas_acabado",
            )

        st.markdown("#### Contenido visible")

        mostrar_codigo = st.checkbox(
            "Mostrar código técnico del espacio",
            value=True,
            key="placas_mostrar_codigo",
        )

        mostrar_ubicacion = st.checkbox(
            "Mostrar centro, edificio y planta",
            value=True,
            key="placas_mostrar_ubicacion",
        )

        mostrar_ayuda = st.checkbox(
            "Mostrar instrucciones para escanear",
            value=True,
            key="placas_mostrar_ayuda",
        )

        mostrar_mensaje_final = st.checkbox(
            "Mostrar mensaje de colaboración",
            value=True,
            key="placas_mostrar_mensaje_final",
        )

        st.markdown("#### Vista previa")

        with st.container(border=True):
            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    background:linear-gradient(135deg,#0f172a,#1d4ed8);
                    color:white;
                    border-radius:18px;
                    padding:20px;
                    font-size:26px;
                    font-weight:900;
                ">
                    {titulo_placa}
                    <br>
                    <span style="
                        font-size:14px;
                        font-weight:700;
                    ">
                        {subtitulo_placa}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div style="
                    text-align:center;
                    margin-top:18px;
                    font-size:13px;
                    font-weight:900;
                    color:#1d4ed8;
                    letter-spacing:1px;
                ">
                    AULA
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div style="
                    text-align:center;
                    font-size:34px;
                    font-weight:900;
                    color:#0f172a;
                    margin-top:4px;
                ">
                    I4A
                </div>
                """,
                unsafe_allow_html=True,
            )

            if mostrar_ubicacion:
                st.caption(
                    "Pearson 22 · Infantil / Primaria · Planta 1"
                )

            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    background:#0f2a5f;
                    color:white;
                    border-radius:14px;
                    padding:12px;
                    margin-top:16px;
                    font-size:18px;
                    font-weight:900;
                ">
                    {texto_accion}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if mostrar_ayuda:
                st.caption(
                    "Escanea con la cámara del móvil. "
                    "No necesitas ninguna aplicación."
                )

            if mostrar_mensaje_final:
                st.caption(
                    "Gracias por ayudarnos a cuidar nuestro colegio."
                )

            if mostrar_codigo:
                st.caption("ESP-000023")

        st.markdown("#### Resumen de impresión")

        st.write(f"**Tamaño:** {tamano_placa}")
        st.write(f"**Placas por página:** {placas_por_pagina}")
        st.write(f"**Acabado:** {acabado}")

        st.success(
            "Configuración preparada. En el siguiente paso conectaremos "
            "estos ajustes con el PDF para que puedas generar las placas "
            "sin volver a tocar código."
        )
