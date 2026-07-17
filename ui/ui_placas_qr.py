import io

import qrcode
import streamlit as st

from ui.ui_qr_aulas import (
    pantalla_qr_aulas,
    generar_pdf_vista_previa,
    obtener_configuracion_placas,
)


from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


URL_BASE_APP = "https://mantenimiento-app-1.onrender.com"
AZUL_OSCURO = HexColor("#0f2a5f")
AZUL = HexColor("#1d4ed8")
GRIS = HexColor("#475569")


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


def generar_pdf_placa_general():
    enlace_general, qr_general = generar_qr_general()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    ancho_pagina, alto_pagina = A4

    ancho_placa = 90 * mm
    alto_placa = 120 * mm

    x = (ancho_pagina - ancho_placa) / 2
    y = (alto_pagina - alto_placa) / 2

    radio = 5 * mm
    x_centro = x + ancho_placa / 2

    # Fondo y borde
    pdf.setFillColor(white)
    pdf.setStrokeColor(AZUL_OSCURO)
    pdf.setLineWidth(1.2)

    pdf.roundRect(
        x,
        y,
        ancho_placa,
        alto_placa,
        radio,
        stroke=1,
        fill=1,
    )

    # Cabecera
    alto_cabecera = 22 * mm

    pdf.setFillColor(AZUL_OSCURO)
    pdf.setStrokeColor(AZUL_OSCURO)

    pdf.roundRect(
        x,
        y + alto_placa - alto_cabecera,
        ancho_placa,
        alto_cabecera,
        radio,
        stroke=0,
        fill=1,
    )

    pdf.rect(
        x,
        y + alto_placa - alto_cabecera,
        ancho_placa,
        alto_cabecera - radio,
        stroke=0,
        fill=1,
    )

    pdf.setFillColor(white)

    pdf.setFont(
        "Helvetica-Bold",
        15,
    )
    pdf.drawCentredString(
        x_centro,
        y + alto_placa - 9 * mm,
        "LORETO",
    )

    pdf.setFont(
        "Helvetica-Bold",
        13,
    )
    pdf.drawCentredString(
        x_centro,
        y + alto_placa - 15 * mm,
        "MANTENIMIENTO",
    )

    pdf.setFont(
        "Helvetica",
        7,
    )
    pdf.drawCentredString(
        x_centro,
        y + alto_placa - 19 * mm,
        "Sistema Integral de Mantenimiento",
    )

    # QR
    qr_reader = ImageReader(
        io.BytesIO(qr_general)
    )

    tamano_qr = 38 * mm
    x_qr = x + (ancho_placa - tamano_qr) / 2
    y_qr = y + 32 * mm

    pdf.setFillColor(white)
    pdf.setStrokeColor(AZUL_OSCURO)
    pdf.setLineWidth(1)

    pdf.roundRect(
        x_qr - 2 * mm,
        y_qr - 2 * mm,
        tamano_qr + 4 * mm,
        tamano_qr + 4 * mm,
        3 * mm,
        stroke=1,
        fill=1,
    )

    pdf.drawImage(
        qr_reader,
        x_qr,
        y_qr,
        width=tamano_qr,
        height=tamano_qr,
        preserveAspectRatio=True,
        mask="auto",
    )

    # Acción
    y_accion = y + 19 * mm
    alto_accion = 9 * mm

    pdf.setFillColor(AZUL_OSCURO)
    pdf.setStrokeColor(AZUL_OSCURO)

    pdf.roundRect(
        x + 9 * mm,
        y_accion,
        ancho_placa - 18 * mm,
        alto_accion,
        3 * mm,
        stroke=0,
        fill=1,
    )

    pdf.setFillColor(white)
    pdf.setFont(
        "Helvetica-Bold",
        10,
    )

    pdf.drawCentredString(
        x_centro,
        y_accion + 3.1 * mm,
        "Comunicar incidencia",
    )

    # Instrucciones
    pdf.setFillColor(AZUL_OSCURO)
    pdf.setFont(
        "Helvetica-Bold",
        7,
    )

    pdf.drawCentredString(
        x_centro,
        y + 16 * mm,
        "Escanea con la cámara del móvil",
    )

    pdf.setFillColor(AZUL)
    pdf.setFont(
        "Helvetica",
        6.5,
    )

    pdf.drawCentredString(
        x_centro,
        y + 12 * mm,
        "No necesitas ninguna aplicación",
    )

    # Pie
    pdf.setFillColor(GRIS)
    pdf.setFont(
        "Helvetica-Oblique",
        6.2,
    )

    pdf.drawCentredString(
        x_centro,
        y + 6 * mm,
        "Gracias por ayudarnos a cuidar nuestro colegio",
    )

    pdf.save()
    buffer.seek(0)

    return buffer.getvalue()


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
                pdf_general = generar_pdf_placa_general()

                st.download_button(
                    "📄 Descargar placa general en PDF",
                    data=pdf_general,
                    file_name="PLACA_GENERAL_LORETO_MANTENIMIENTO.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="descargar_pdf_placa_general",
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
                value="Comunicar incidencia",
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

        marcas_corte = st.checkbox(
            "Mostrar marcas de corte en el PDF",
            value=True,
            key="placas_marcas_corte",
        )

        st.markdown("#### Vista previa real de impresión")

        configuracion_previa = obtener_configuracion_placas()

        pdf_previa = generar_pdf_vista_previa(
            configuracion_previa
        )

        st.download_button(
            "📄 Descargar vista previa real",
            data=pdf_previa,
            file_name="VISTA_PREVIA_PLACA_QR.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="descargar_vista_previa_placa",
        )

        st.caption(
            "La vista previa utiliza el mismo diseño que el PDF "
            "destinado a impresión."
        )

        st.markdown("#### Resumen de impresión")

        st.write(f"**Tamaño:** {tamano_placa}")
        st.write(f"**Placas por página:** {placas_por_pagina}")
        st.write(f"**Acabado:** {acabado}")

        st.success(
            "Configuración preparada. En el siguiente paso conectaremos "
            "estos ajustes con el PDF para que puedas generar las placas "
            "sin volver a tocar código."
        )

        st.markdown("#### Diseño")

        mostrar_aula = st.checkbox(
            'Mostrar texto "AULA"',
            value=True,
            key="placas_mostrar_aula",
        )
        
        tamano_texto_aula = st.slider(
            "Tamaño texto AULA",
            6,
            16,
            9,
            key="placas_tamano_aula",
        )
        
        tamano_nombre_espacio = st.slider(
            "Tamaño nombre del espacio",
            14,
            28,
            20,
            key="placas_tamano_nombre",
        )
        
        tamano_qr = st.slider(
            "Tamaño del QR (mm)",
            25,
            40,
            32,
            key="placas_tamano_qr",
        )
        st.markdown("#### Posiciones")

        separacion_superior = st.slider(
            "Separación cabecera",
            18.0,
            26.0,
            22.0,
            0.5,
            key="placas_posicion_aula",
        )
        
        separacion_nombre = st.slider(
            "Separación nombre",
            22.0,
            32.0,
            27.5,
            0.5,
            key="placas_posicion_nombre",
        )
