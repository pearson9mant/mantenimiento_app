import io

import qrcode
import streamlit as st

from ui.ui_qr_aulas import pantalla_qr_aulas
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
    pdf = canvas.Canvas(buffer, pagesize=A4)

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
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(
        x_centro,
        y + alto_placa - 9 * mm,
        "LORETO",
    )

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(
        x_centro,
        y + alto_placa - 15 * mm,
        "MANTENIMIENTO",
    )

    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(
        x_centro,
        y + alto_placa - 19 * mm,
        "Sistema Integral de Mantenimiento",
    )

    # Título central
    pdf.setFillColor(AZUL_OSCURO)
    pdf.setFont("Helvetica-Bold", 15)

    pdf.drawCentredString(
        x_centro,
        y + alto_placa - 34 * mm,
        "¿HAS DETECTADO",
    )

    pdf.drawCentredString(
        x_centro,
        y + alto_placa - 41 * mm,
        "UNA INCIDENCIA?",
    )

    # QR
    qr_reader = ImageReader(
        io.BytesIO(qr_general)
    )

    tamano_qr = 48 * mm
    x_qr = x + (ancho_placa - tamano_qr) / 2
    y_qr = y + 37 * mm

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

    pdf.setFont("Helvetica-Bold", 7)
    pdf.setFillColor(HexColor("#64748b"))

    pdf.drawCentredString(
        x_centro,
        y_qr + tamano_qr + 5 * mm,
        "ESCANEA AQUÍ",
    )

    # Botón azul
    y_accion = y + 24 * mm
    alto_accion = 10 * mm

    pdf.setFillColor(AZUL_OSCURO)

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
    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawCentredString(
        x_centro,
        y_accion + 3.4 * mm,
        "Comunicar una incidencia",
    )

    # Instrucciones
    pdf.setFillColor(AZUL_OSCURO)
    pdf.setFont("Helvetica-Bold", 7)

    pdf.drawCentredString(
        x_centro,
        y + 17 * mm,
        "Escanea con la cámara del móvil",
    )

    pdf.setFillColor(AZUL)
    pdf.setFont("Helvetica", 6.5)

    pdf.drawCentredString(
        x_centro,
        y + 13 * mm,
        "No necesitas ninguna aplicación",
    )

    # Pie
    pdf.setFillColor(GRIS)
    pdf.setFont("Helvetica-Oblique", 6.2)

    pdf.drawCentredString(
        x_centro,
        y + 7 * mm,
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

        marcas_corte = st.checkbox(
            "Mostrar marcas de corte en el PDF",
            value=True,
            key="placas_marcas_corte",
        )

        st.markdown("#### Vista previa")

        enlace_previa, qr_previa = generar_qr_general()
        
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="
                    max-width:520px;
                    margin:0 auto;
                    border:2px solid #0f2a5f;
                    border-radius:24px;
                    background:white;
                    overflow:hidden;
                    box-shadow:0 10px 28px rgba(15,42,95,0.10);
                ">
                    <div style="
                        text-align:center;
                        background:linear-gradient(135deg,#0f172a,#1d4ed8);
                        color:white;
                        padding:20px 16px 16px 16px;
                    ">
                        <div style="
                            font-size:25px;
                            font-weight:900;
                            line-height:1.15;
                        ">
                            {titulo_placa}
                        </div>
        
                        <div style="
                            font-size:13px;
                            font-weight:700;
                            margin-top:7px;
                        ">
                            {subtitulo_placa}
                        </div>
                    </div>
        
                    <div style="
                        padding:18px 22px 22px 22px;
                        text-align:center;
                    ">
                        <div style="
                            color:#1d4ed8;
                            font-size:12px;
                            font-weight:900;
                            letter-spacing:1px;
                        ">
                            AULA
                        </div>
        
                        <div style="
                            font-size:38px;
                            font-weight:900;
                            color:#0f172a;
                            margin-top:2px;
                        ">
                            I4A
                        </div>
                """,
                unsafe_allow_html=True,
            )
        
            if mostrar_ubicacion:
                st.markdown(
                    """
                    <div style="
                        text-align:center;
                        color:#475569;
                        font-size:13px;
                        font-weight:700;
                        line-height:1.5;
                        margin-top:4px;
                    ">
                        Pearson 22 · Infantil / Primaria<br>
                        Planta 1
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        
            st.markdown(
                """
                <div style="
                    text-align:center;
                    margin-top:14px;
                    color:#64748b;
                    font-size:11px;
                    font-weight:900;
                    letter-spacing:1px;
                ">
                    ESCANEA AQUÍ
                </div>
                """,
                unsafe_allow_html=True,
            )
        
            st.image(
                qr_previa,
                width=220,
            )
        
            st.markdown(
                f"""
                <div style="
                    max-width:390px;
                    margin:10px auto 0 auto;
                    text-align:center;
                    background:#0f2a5f;
                    color:white;
                    border-radius:13px;
                    padding:11px 14px;
                    font-size:17px;
                    font-weight:900;
                ">
                    {texto_accion}
                </div>
                """,
                unsafe_allow_html=True,
            )
        
            if mostrar_ayuda:
                st.markdown(
                    """
                    <div style="
                        text-align:center;
                        margin-top:11px;
                        color:#0f2a5f;
                        font-size:12px;
                        font-weight:800;
                    ">
                        Escanea con la cámara del móvil
                    </div>
        
                    <div style="
                        text-align:center;
                        color:#1d4ed8;
                        font-size:11px;
                        margin-top:2px;
                    ">
                        No necesitas ninguna aplicación
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        
            if mostrar_mensaje_final:
                st.markdown(
                    """
                    <div style="
                        text-align:center;
                        color:#475569;
                        font-size:11px;
                        font-style:italic;
                        margin-top:10px;
                    ">
                        Gracias por ayudarnos a cuidar nuestro colegio.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        
            if mostrar_codigo:
                st.markdown(
                    """
                    <div style="
                        text-align:right;
                        color:#94a3b8;
                        font-size:9px;
                        margin-top:8px;
                    ">
                        ESP-000023
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        
            st.markdown(
                """
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
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
