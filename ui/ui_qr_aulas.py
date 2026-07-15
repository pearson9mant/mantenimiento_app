import io
import re
from urllib.parse import quote

import qrcode
import streamlit as st
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from modules.espacios import obtener_aulas_para_qr


URL_BASE_APP = "https://mantenimiento-app-1.onrender.com"

AZUL_OSCURO = HexColor("#0f2a5f")
AZUL = HexColor("#1d4ed8")
GRIS = HexColor("#475569")


def obtener_configuracion_placas():
    return {
        "titulo": str(
            st.session_state.get(
                "placas_titulo_principal",
                "LORETO MANTENIMIENTO",
            )
            or "LORETO MANTENIMIENTO"
        ).strip(),
        "subtitulo": str(
            st.session_state.get(
                "placas_subtitulo",
                "Sistema Integral de Mantenimiento",
            )
            or "Sistema Integral de Mantenimiento"
        ).strip(),
        "texto_accion": str(
            st.session_state.get(
                "placas_texto_accion",
                "Comunicar una incidencia",
            )
            or "Comunicar una incidencia"
        ).strip(),
        "tamano": str(
            st.session_state.get(
                "placas_tamano",
                "90 × 120 mm",
            )
            or "90 × 120 mm"
        ).strip(),
        "por_pagina": int(
            st.session_state.get(
                "placas_por_pagina",
                6,
            )
            or 6
        ),
        "mostrar_codigo": bool(
            st.session_state.get(
                "placas_mostrar_codigo",
                True,
            )
        ),
        "mostrar_ubicacion": bool(
            st.session_state.get(
                "placas_mostrar_ubicacion",
                True,
            )
        ),
        "mostrar_ayuda": bool(
            st.session_state.get(
                "placas_mostrar_ayuda",
                True,
            )
        ),
        "mostrar_mensaje_final": bool(
            st.session_state.get(
                "placas_mostrar_mensaje_final",
                True,
            )
        ),
    }

    "marcas_corte": bool(
        st.session_state.get(
            "placas_marcas_corte",
            True,
        )
    ),


def limpiar_nombre_archivo(texto):
    texto = str(texto or "").strip()
    texto = re.sub(r"[^a-zA-Z0-9_-]+", "_", texto)
    return texto.strip("_") or "qr_aulas"


def construir_enlace_qr(codigo):
    codigo = quote(str(codigo or "").strip())
    return f"{URL_BASE_APP}/?qr=1&codigo={codigo}"


def generar_qr_png(url, box_size=10, border=2):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )

    qr.add_data(url)
    qr.make(fit=True)

    imagen = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()


def dibujar_texto_centrado(
    pdf,
    texto,
    x_centro,
    y,
    fuente="Helvetica",
    tamano=9,
    color=black,
):
    pdf.setFont(fuente, tamano)
    pdf.setFillColor(color)
    pdf.drawCentredString(
        x_centro,
        y,
        str(texto or ""),
    )


def dividir_titulo(titulo):
    palabras = str(titulo or "").strip().split()

    if len(palabras) <= 1:
        return titulo, ""

    if len(palabras) == 2:
        return palabras[0], palabras[1]

    mitad = max(1, len(palabras) // 2)
    return " ".join(palabras[:mitad]), " ".join(palabras[mitad:])


def dibujar_pegatina(
    pdf,
    x,
    y,
    ancho,
    alto,
    codigo,
    centro,
    edificio,
    planta,
    espacio,
    configuracion,
):
    radio = 5 * mm
    x_centro = x + ancho / 2

    titulo_placa = configuracion["titulo"]
    subtitulo_placa = configuracion["subtitulo"]
    texto_accion = configuracion["texto_accion"]

    mostrar_codigo = configuracion["mostrar_codigo"]
    mostrar_ubicacion = configuracion["mostrar_ubicacion"]
    mostrar_ayuda = configuracion["mostrar_ayuda"]
    mostrar_mensaje_final = configuracion["mostrar_mensaje_final"]

    # Fondo y borde
    pdf.setFillColor(white)
    pdf.setStrokeColor(AZUL_OSCURO)
    pdf.setLineWidth(1.2)
    pdf.roundRect(
        x,
        y,
        ancho,
        alto,
        radio,
        stroke=1,
        fill=1,
    )

    # Cabecera
    alto_cabecera = 18 * mm

    pdf.setFillColor(AZUL_OSCURO)
    pdf.setStrokeColor(AZUL_OSCURO)

    pdf.roundRect(
        x,
        y + alto - alto_cabecera,
        ancho,
        alto_cabecera,
        radio,
        stroke=0,
        fill=1,
    )

    pdf.rect(
        x,
        y + alto - alto_cabecera,
        ancho,
        alto_cabecera - radio,
        stroke=0,
        fill=1,
    )

    titulo_1, titulo_2 = dividir_titulo(titulo_placa)

    dibujar_texto_centrado(
        pdf,
        titulo_1,
        x_centro,
        y + alto - 7.0 * mm,
        fuente="Helvetica-Bold",
        tamano=13,
        color=white,
    )

    if titulo_2:
        dibujar_texto_centrado(
            pdf,
            titulo_2,
            x_centro,
            y + alto - 12.3 * mm,
            fuente="Helvetica-Bold",
            tamano=11,
            color=white,
        )

    dibujar_texto_centrado(
        pdf,
        subtitulo_placa,
        x_centro,
        y + alto - 16.0 * mm,
        fuente="Helvetica",
        tamano=6.5,
        color=white,
    )

    # Identificación del aula
    dibujar_texto_centrado(
        pdf,
        "AULA",
        x_centro,
        y + alto - 23.5 * mm,
        fuente="Helvetica-Bold",
        tamano=8.5,
        color=AZUL_OSCURO,
    )

    nombre_espacio = str(espacio or "").strip().upper()

    if len(nombre_espacio) <= 4:
        tamano_aula = 24
    elif len(nombre_espacio) <= 7:
        tamano_aula = 20
    else:
        tamano_aula = 15

    dibujar_texto_centrado(
        pdf,
        nombre_espacio,
        x_centro,
        y + alto - 31 * mm,
        fuente="Helvetica-Bold",
        tamano=tamano_aula,
        color=AZUL_OSCURO,
    )

    if mostrar_ubicacion:
        ubicacion_principal = (
            f"{centro or '-'} · {edificio or '-'}"
        )

        dibujar_texto_centrado(
            pdf,
            ubicacion_principal,
            x_centro,
            y + alto - 35.5 * mm,
            fuente="Helvetica-Bold",
            tamano=5.8,
            color=GRIS,
        )

        dibujar_texto_centrado(
            pdf,
            planta or "-",
            x_centro,
            y + alto - 38.5 * mm,
            fuente="Helvetica-Bold",
            tamano=5.8,
            color=GRIS,
        )

    # QR
    enlace = construir_enlace_qr(codigo)
    qr_bytes = generar_qr_png(
        enlace,
        box_size=11,
        border=2,
    )
    qr_reader = ImageReader(io.BytesIO(qr_bytes))

    tamano_qr = min(
        34 * mm,
        ancho - 24 * mm,
    )

    x_qr = x + (ancho - tamano_qr) / 2
    y_qr = y + 31 * mm
    
    dibujar_texto_centrado(
        pdf,
        "ESCANEA AQUÍ",
        x_centro,
        y_qr + tamano_qr + 4 * mm,
        fuente="Helvetica-Bold",
        tamano=6.5,
        color=HexColor("#64748b"),
    )

    pdf.setFillColor(white)
    pdf.setStrokeColor(AZUL_OSCURO)
    pdf.setLineWidth(1)

    pdf.roundRect(
        x_qr - 1.5 * mm,
        y_qr - 1.5 * mm,
        tamano_qr + 3 * mm,
        tamano_qr + 3 * mm,
        2.5 * mm,
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

    # Acción principal
    alto_accion = 7.5 * mm
    y_accion = y + 8.5 * mm

    pdf.setFillColor(AZUL_OSCURO)
    pdf.setStrokeColor(AZUL_OSCURO)

    pdf.roundRect(
        x + 7 * mm,
        y_accion,
        ancho - 14 * mm,
        alto_accion,
        2.5 * mm,
        stroke=0,
        fill=1,
    )

    dibujar_texto_centrado(
        pdf,
        texto_accion,
        x_centro,
        y_accion + 2.5 * mm,
        fuente="Helvetica-Bold",
        tamano=8.2,
        color=white,
    )

    if mostrar_ayuda:
        dibujar_texto_centrado(
            pdf,
            "Escanea con la cámara del móvil",
            x_centro,
            y + 7.2 * mm,
            fuente="Helvetica-Bold",
            tamano=6.2,
            color=AZUL_OSCURO,
        )

        dibujar_texto_centrado(
            pdf,
            "No necesitas ninguna aplicación",
            x_centro,
            y + 4.8 * mm,
            fuente="Helvetica",
            tamano=5.8,
            color=AZUL,
        )

    if mostrar_mensaje_final:
        dibujar_texto_centrado(
            pdf,
            "Gracias por ayudarnos a cuidar nuestro colegio",
            x_centro,
            y + 2.2 * mm,
            fuente="Helvetica-Oblique",
            tamano=5.2,
            color=HexColor("#334155"),
        )

    if mostrar_codigo:
        pdf.setFont("Helvetica", 4.2)
        pdf.setFillColor(HexColor("#94a3b8"))
        pdf.drawRightString(
            x + ancho - 2.5 * mm,
            y + 1.2 * mm,
            str(codigo or ""),
        )


def obtener_distribucion_pagina(por_pagina):
    if por_pagina == 2:
        return 1, 2

    if por_pagina == 4:
        return 2, 2

    return 2, 3

def dibujar_marcas_corte(
    pdf,
    x,
    y,
    ancho,
    alto,
):
    largo = 4 * mm
    separacion = 1.5 * mm

    pdf.setStrokeColor(HexColor("#94a3b8"))
    pdf.setLineWidth(0.4)

    # Esquina inferior izquierda
    pdf.line(
        x - separacion - largo,
        y,
        x - separacion,
        y,
    )
    pdf.line(
        x,
        y - separacion - largo,
        x,
        y - separacion,
    )

    # Esquina inferior derecha
    pdf.line(
        x + ancho + separacion,
        y,
        x + ancho + separacion + largo,
        y,
    )
    pdf.line(
        x + ancho,
        y - separacion - largo,
        x + ancho,
        y - separacion,
    )

    # Esquina superior izquierda
    pdf.line(
        x - separacion - largo,
        y + alto,
        x - separacion,
        y + alto,
    )
    pdf.line(
        x,
        y + alto + separacion,
        x,
        y + alto + separacion + largo,
    )

    # Esquina superior derecha
    pdf.line(
        x + ancho + separacion,
        y + alto,
        x + ancho + separacion + largo,
        y + alto,
    )
    pdf.line(
        x + ancho,
        y + alto + separacion,
        x + ancho,
        y + alto + separacion + largo,
    )


def generar_pdf_pegatinas(aulas, configuracion):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    ancho_pagina, alto_pagina = A4

    margen_x = 8 * mm
    margen_y = 8 * mm
    separacion_x = 5 * mm
    separacion_y = 5 * mm

    por_pagina = configuracion["por_pagina"]
    columnas, filas = obtener_distribucion_pagina(
        por_pagina
    )

    ancho_pegatina = (
        ancho_pagina
        - (2 * margen_x)
        - ((columnas - 1) * separacion_x)
    ) / columnas

    alto_pegatina = (
        alto_pagina
        - (2 * margen_y)
        - ((filas - 1) * separacion_y)
    ) / filas

    for indice, fila in enumerate(aulas):
        if indice > 0 and indice % por_pagina == 0:
            pdf.showPage()

        posicion = indice % por_pagina
        columna = posicion % columnas
        fila_pagina = posicion // columnas

        x = margen_x + columna * (
            ancho_pegatina + separacion_x
        )

        y = (
            alto_pagina
            - margen_y
            - alto_pegatina
            - fila_pagina * (
                alto_pegatina + separacion_y
            )
        )

        (
            codigo,
            centro,
            edificio,
            planta,
            espacio,
        ) = fila

        dibujar_pegatina(
            pdf,
            x,
            y,
            ancho_pegatina,
            alto_pegatina,
            codigo,
            centro,
            edificio,
            planta,
            espacio,
            configuracion,
        )
        if configuracion.get("marcas_corte", True):
            dibujar_marcas_corte(
                pdf,
                x,
                y,
                ancho_pegatina,
                alto_pegatina,
            ) 
    pdf.save()
    buffer.seek(0)

    return buffer.getvalue()


def pantalla_qr_aulas():
    st.markdown("## 📱 QR de aulas")

    st.info(
        "Aquí aparecen las aulas registradas en el catálogo central. "
        "Puedes probar cada formulario, descargar un QR individual "
        "o generar un PDF listo para imprimir."
    )

    aulas = obtener_aulas_para_qr()

    if not aulas:
        st.warning("No hay aulas registradas.")
        return

    centros = sorted({
        str(fila[1])
        for fila in aulas
        if len(fila) >= 5 and fila[1]
    })

    centro_filtro = st.selectbox(
        "Centro",
        ["Todos"] + centros,
        key="qr_aulas_filtro_centro",
    )

    aulas_centro = [
        fila
        for fila in aulas
        if (
            centro_filtro == "Todos"
            or str(fila[1]) == centro_filtro
        )
    ]

    edificios = sorted({
        str(fila[2])
        for fila in aulas_centro
        if len(fila) >= 5 and fila[2]
    })

    edificio_filtro = st.selectbox(
        "Edificio",
        ["Todos"] + edificios,
        key="qr_aulas_filtro_edificio",
    )

    buscar = st.text_input(
        "Buscar aula",
        placeholder="Ejemplo: I4A, 3A, ESO 1A...",
        key="qr_aulas_buscar",
    ).strip().lower()

    resultados = []

    for fila in aulas:
        if len(fila) < 5:
            continue

        (
            codigo,
            centro,
            edificio,
            planta,
            espacio,
        ) = fila

        if (
            centro_filtro != "Todos"
            and str(centro) != centro_filtro
        ):
            continue

        if (
            edificio_filtro != "Todos"
            and str(edificio) != edificio_filtro
        ):
            continue

        texto_busqueda = (
            f"{codigo} {centro} {edificio} "
            f"{planta} {espacio}"
        ).lower()

        if buscar and buscar not in texto_busqueda:
            continue

        resultados.append(fila)

    st.caption(f"Aulas encontradas: {len(resultados)}")

    if not resultados:
        st.info("No hay aulas que coincidan con los filtros.")
        return

    configuracion = obtener_configuracion_placas()

    st.markdown("### 📄 Pegatinas para imprimir")

    st.caption(
        f"El PDF incluye {configuracion['por_pagina']} placas "
        "por página A4, listas para imprimir, recortar "
        "y plastificar."
    )

    nombre_partes = ["QR_Aulas"]

    if centro_filtro != "Todos":
        nombre_partes.append(centro_filtro)

    if edificio_filtro != "Todos":
        nombre_partes.append(edificio_filtro)

    nombre_pdf = (
        limpiar_nombre_archivo("_".join(nombre_partes))
        + ".pdf"
    )

    pdf_bytes = generar_pdf_pegatinas(
        resultados,
        configuracion,
    )

    st.download_button(
        "📄 Descargar PDF de pegatinas",
        data=pdf_bytes,
        file_name=nombre_pdf,
        mime="application/pdf",
        use_container_width=True,
        key="descargar_pdf_qr_aulas",
    )

    st.markdown("---")

    with st.expander(
        "🔎 Ver y comprobar placas individuales",
        expanded=False,
    ):
        st.caption(
            "Desde aquí puedes probar el formulario de cada aula "
            "o descargar un QR individual."
        )

        for fila in resultados:
            (
                codigo,
                centro,
                edificio,
                planta,
                espacio,
            ) = fila

            codigo = str(codigo or "").strip()

            if not codigo:
                continue

            enlace = construir_enlace_qr(codigo)

            qr_bytes = generar_qr_png(
                enlace,
                box_size=8,
                border=2,
            )

            with st.container(border=True):
                st.markdown(f"### 🏫 {espacio}")

                st.caption(
                    f"📍 {centro} · {edificio} · {planta}"
                )

                col1, col2 = st.columns([1, 2])

                with col1:
                    st.image(
                        qr_bytes,
                        width=150,
                    )

                with col2:
                    st.code(codigo)

                    st.link_button(
                        "🔎 Probar formulario",
                        enlace,
                        use_container_width=True,
                    )

                    st.download_button(
                        "⬇️ Descargar QR",
                        data=qr_bytes,
                        file_name=f"{codigo}.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"descargar_qr_{codigo}",
                    )

            

            
