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

        st.caption(
            "Aquí configuraremos el tamaño, formato y acabado "
            "de las placas sin modificar código."
        )
