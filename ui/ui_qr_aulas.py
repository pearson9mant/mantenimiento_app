import io
import re
import zipfile
from urllib.parse import quote

import pandas as pd
import qrcode
import streamlit as st
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from modules.espacios import (
    obtener_espacios_para_qr,
    obtener_espacios,
    actualizar_qr_habilitado_espacio,
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
    obtener_codigo_espacio,
)


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
                "Comunicar incidencia",
            )
            or "Comunicar incidencia"
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

        "marcas_corte": bool(
            st.session_state.get(
                "placas_marcas_corte",
                True,
            )
        ),

        "mostrar_aula": bool(
            st.session_state.get(
                "placas_mostrar_aula",
                True,
            )
        ),

        "tamano_texto_aula": int(
            st.session_state.get(
                "placas_tamano_aula",
                9,
            )
            or 9
        ),

        "tamano_nombre_espacio": int(
            st.session_state.get(
                "placas_tamano_nombre",
                20,
            )
            or 20
        ),

        "tamano_qr": int(
            st.session_state.get(
                "placas_tamano_qr",
                32,
            )
            or 32
        ),

        "separacion_superior": float(
            st.session_state.get(
                "placas_posicion_aula",
                22.0,
            )
            or 22.0
        ),

        "separacion_nombre": float(
            st.session_state.get(
                "placas_posicion_nombre",
                27.5,
            )
            or 27.5
        ),
    }


def sincronizar_qr_espacios(filas_filtradas, ids_seleccionados):
    """
    Sincroniza exactamente el estado QR del filtro:

    - seleccionado   -> QR habilitado
    - no seleccionado -> QR deshabilitado

    Así el PDF posterior refleja exactamente la selección realizada.
    """
    habilitados = 0
    deshabilitados = 0
    errores = []

    ids_seleccionados = {
        int(valor)
        for valor in ids_seleccionados
    }

    for fila in filas_filtradas:
        try:
            id_espacio = int(fila[0])
            habilitar = id_espacio in ids_seleccionados

            ok = actualizar_qr_habilitado_espacio(
                id_espacio,
                habilitar,
            )

            if ok:
                if habilitar:
                    habilitados += 1
                else:
                    deshabilitados += 1
            else:
                errores.append(
                    f"{fila[1]} · {fila[2]} · {fila[3]} · {fila[4]}"
                )

        except Exception as e:
            errores.append(
                f"{fila}: {e}"
            )

    return habilitados, deshabilitados, errores


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



def generar_pdf_pegatina_individual(fila, configuracion):
    """
    Genera una sola placa a tamaño real 90 x 120 mm.
    Pensado para imprenta: una pegatina = un PDF.
    """
    ancho_pegatina = 90 * mm
    alto_pegatina = 120 * mm

    buffer = io.BytesIO()
    pdf = canvas.Canvas(
        buffer,
        pagesize=(ancho_pegatina, alto_pegatina),
    )

    (
        codigo,
        centro,
        edificio,
        planta,
        espacio,
        tipo_espacio,
    ) = fila

    configuracion_espacio = dict(configuracion)
    configuracion_espacio["tipo_espacio"] = tipo_espacio
    configuracion_espacio["marcas_corte"] = False

    # Composición específica para la placa individual real 90 x 120 mm.
    # No afecta al PDF A4 ni a la vista previa habitual.
    configuracion_espacio["tamano_qr_individual"] = 38
    configuracion_espacio["posicion_qr_y_individual"] = 33

    dibujar_pegatina_espacio(
        pdf,
        0,
        0,
        ancho_pegatina,
        alto_pegatina,
        codigo,
        centro,
        edificio,
        planta,
        espacio,
        configuracion_espacio,
    )

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def generar_zip_pegatinas_individuales(aulas, configuracion):
    """
    Devuelve un ZIP con un PDF independiente por cada placa seleccionada.
    """
    buffer_zip = io.BytesIO()

    with zipfile.ZipFile(
        buffer_zip,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archivo_zip:
        for indice, fila in enumerate(aulas, start=1):
            codigo = str(fila[0] or "").strip()
            espacio = str(fila[4] or "").strip()

            nombre_base = limpiar_nombre_archivo(
                f"{indice:03d}_{codigo}_{espacio}"
            )

            pdf_individual = generar_pdf_pegatina_individual(
                fila,
                configuracion,
            )

            archivo_zip.writestr(
                f"{nombre_base}.pdf",
                pdf_individual,
            )

    buffer_zip.seek(0)
    return buffer_zip.getvalue()


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
            tipo_espacio,
        ) = fila

        configuracion_espacio = dict(
            configuracion
        )
        configuracion_espacio[
            "tipo_espacio"
        ] = tipo_espacio

        dibujar_pegatina_espacio(
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
            configuracion_espacio,
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


def generar_pdf_vista_previa(configuracion):
    buffer = io.BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    ancho_pagina, alto_pagina = A4

    margen_x = 8 * mm
    margen_y = 8 * mm
    separacion_x = 5 * mm
    separacion_y = 5 * mm

    por_pagina = configuracion.get(
        "por_pagina",
        6,
    )

    columnas, filas = obtener_distribucion_pagina(
        por_pagina
    )

    # Mismas medidas que el PDF definitivo.
    ancho_placa = (
        ancho_pagina
        - (2 * margen_x)
        - ((columnas - 1) * separacion_x)
    ) / columnas

    alto_placa = (
        alto_pagina
        - (2 * margen_y)
        - ((filas - 1) * separacion_y)
    ) / filas

    # Pegatina centrada en la hoja.
    x = (ancho_pagina - ancho_placa) / 2
    y = (alto_pagina - alto_placa) / 2

    dibujar_pegatina_espacio(
        pdf=pdf,
        x=x,
        y=y,
        ancho=ancho_placa,
        alto=alto_placa,
        codigo=configuracion.get(
            "codigo",
            "ESP-000023",
        ),
        centro=configuracion.get(
            "centro",
            "",
        ),
        edificio=configuracion.get(
            "edificio",
            "",
        ),
        planta=configuracion.get(
            "planta",
            "",
        ),
        espacio=configuracion.get(
            "espacio",
            "4A",
        ),
        configuracion=configuracion,
    )

    if configuracion.get(
        "marcas_corte",
        True,
    ):
        dibujar_marcas_corte(
            pdf,
            x,
            y,
            ancho_placa,
            alto_placa,
        )

    pdf.save()
    buffer.seek(0)

    return buffer.getvalue()


def dibujar_pegatina_espacio(
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

    titulo_placa = configuracion.get(
        "titulo",
        "LORETO MANTENIMIENTO",
    )

    subtitulo_placa = configuracion.get(
        "subtitulo",
        "Sistema Integral de Mantenimiento",
    )

    texto_accion = configuracion.get(
        "texto_accion",
        "Comunicar incidencia",
    )

    mostrar_codigo = configuracion.get(
        "mostrar_codigo",
        True,
    )

    mostrar_ubicacion = configuracion.get(
        "mostrar_ubicacion",
        True,
    )

    mostrar_ayuda = configuracion.get(
        "mostrar_ayuda",
        True,
    )

    mostrar_mensaje_final = configuracion.get(
        "mostrar_mensaje_final",
        True,
    )

    mostrar_aula = configuracion.get(
        "mostrar_aula",
        True,
    )

    tamano_texto_aula = configuracion.get(
        "tamano_texto_aula",
        9,
    )

    tamano_nombre_config = configuracion.get(
        "tamano_nombre_espacio",
        20,
    )

    tamano_qr_config = configuracion.get(
        "tamano_qr",
        30,
    )

    separacion_superior = configuracion.get(
        "separacion_superior",
        22.0,
    )

    separacion_nombre = configuracion.get(
        "separacion_nombre",
        27.5,
    )

    tipo_espacio = str(
        configuracion.get(
            "tipo_espacio",
            "",
        )
        or ""
    ).strip()

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

    titulo_1, titulo_2 = dividir_titulo(
        titulo_placa
    )

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

    nombre_espacio = str(
        espacio or ""
    ).strip().upper()

    # Etiqueta superior según el tipo real del espacio.
    tipo_normalizado = str(tipo_espacio or "").strip()
    tipo_lower = tipo_normalizado.lower()

    if "aula" in tipo_lower:
        etiqueta_espacio = "AULA"
    elif "patio" in tipo_lower:
        etiqueta_espacio = "PATIO"
    elif tipo_lower in ["wc", "aseo", "baño", "lavabo"]:
        etiqueta_espacio = "WC"
    elif "comedor" in tipo_lower:
        etiqueta_espacio = "COMEDOR"
    elif "cocina" in tipo_lower:
        etiqueta_espacio = "COCINA"
    elif "almac" in tipo_lower:
        etiqueta_espacio = "ALMACÉN"
    elif "laboratorio" in tipo_lower:
        etiqueta_espacio = "LABORATORIO"
    elif "gimnasio" in tipo_lower:
        etiqueta_espacio = "GIMNASIO"
    elif "sala" in tipo_lower:
        etiqueta_espacio = "SALA"
    else:
        etiqueta_espacio = tipo_normalizado.upper() or "ESPACIO"

    if mostrar_aula:
        dibujar_texto_centrado(
            pdf,
            etiqueta_espacio,
            x_centro,
            y + alto - separacion_superior * mm,
            fuente="Helvetica-Bold",
            tamano=tamano_texto_aula,
            color=AZUL_OSCURO,
        )

    # Conserva el ajuste automático para nombres largos.
    if len(nombre_espacio) <= 4:
        tamano_nombre = tamano_nombre_config

    elif len(nombre_espacio) <= 7:
        tamano_nombre = min(
            tamano_nombre_config,
            17,
        )

    else:
        tamano_nombre = min(
            tamano_nombre_config,
            14,
        )

    dibujar_texto_centrado(
        pdf,
        nombre_espacio,
        x_centro,
        y + alto - separacion_nombre * mm,
        fuente="Helvetica-Bold",
        tamano=tamano_nombre,
        color=AZUL_OSCURO,
    )

    if mostrar_ubicacion:
        dibujar_texto_centrado(
            pdf,
            f"{centro or '-'} · {edificio or '-'}",
            x_centro,
            y + alto - 30.5 * mm,
            fuente="Helvetica-Bold",
            tamano=5.8,
            color=GRIS,
        )

        planta_visible = str(
            planta or "-"
        ).strip().upper()

        dibujar_texto_centrado(
            pdf,
            planta_visible,
            x_centro,
            y + alto - 33.2 * mm,
            fuente="Helvetica-Bold",
            tamano=8.2,
            color=AZUL_OSCURO,
        )

    # QR real del espacio seleccionado
    enlace = construir_enlace_qr(
        codigo
    )

    qr_bytes = generar_qr_png(
        enlace,
        box_size=11,
        border=2,
    )

    qr_reader = ImageReader(
        io.BytesIO(qr_bytes)
    )

    tamano_qr = min(
        float(
            configuracion.get(
                "tamano_qr_individual",
                tamano_qr_config,
            )
        ) * mm,
        ancho - 21 * mm,
    )

    x_qr = x + (ancho - tamano_qr) / 2
    y_qr = y + float(
        configuracion.get(
            "posicion_qr_y_individual",
            22,
        )
    ) * mm

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

    # Acción
    alto_accion = 7.5 * mm
    y_accion = y + 12.5 * mm

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

    # Instrucciones
    if mostrar_ayuda:
        dibujar_texto_centrado(
            pdf,
            "Escanea con la cámara del móvil",
            x_centro,
            y + 9.2 * mm,
            fuente="Helvetica-Bold",
            tamano=6.2,
            color=AZUL_OSCURO,
        )

        dibujar_texto_centrado(
            pdf,
            "No necesitas ninguna aplicación",
            x_centro,
            y + 6.8 * mm,
            fuente="Helvetica",
            tamano=5.8,
            color=AZUL,
        )

    # Mensaje inferior
    if mostrar_mensaje_final:
        dibujar_texto_centrado(
            pdf,
            "Gracias por ayudarnos a cuidar nuestro colegio",
            x_centro,
            y + 4.2 * mm,
            fuente="Helvetica-Oblique",
            tamano=5.2,
            color=HexColor("#334155"),
        )

    # Código técnico
    if mostrar_codigo:
        pdf.setFont(
            "Helvetica",
            4.2,
        )

        pdf.setFillColor(
            HexColor("#94a3b8")
        )

        pdf.drawRightString(
            x + ancho - 2.5 * mm,
            y + 1.2 * mm,
            str(codigo or ""),
        )


def pantalla_qr_aulas():
    st.markdown("## 📱 QR de espacios")

    st.info(
        "Aquí aparecen los espacios del catálogo que tienen "
        "activado 📱 QR habilitado. Puedes activar varios de una vez, "
        "probar el formulario, descargar un QR individual o generar el PDF de placas."
    )

    # =========================================================
    # ACTIVACIÓN MASIVA / SELECCIONABLE DESDE LA MISMA PANTALLA
    # =========================================================
    espacios_catalogo = obtener_espacios(
        activos=True
    )

    if espacios_catalogo:
        with st.expander(
            "📱 Activar QR para varios espacios",
            expanded=False,
        ):
            st.caption(
                "La tabla representa el estado final: ✅ marcado = tendrá QR · "
                "⬜ desmarcado = no tendrá QR. Al aplicar, el PDF mostrará "
                "únicamente los que queden habilitados."
            )

            centros_catalogo = sorted({
                str(fila[1])
                for fila in espacios_catalogo
                if len(fila) >= 7 and fila[1]
            })

            centro_masivo = st.selectbox(
                "Centro",
                centros_catalogo,
                index=(
                    centros_catalogo.index("Pearson 22")
                    if "Pearson 22" in centros_catalogo
                    else 0
                ),
                key="qr_masivo_centro",
            )

            filas_centro = [
                fila
                for fila in espacios_catalogo
                if str(fila[1]) == centro_masivo
            ]

            edificios_catalogo = sorted({
                str(fila[2])
                for fila in filas_centro
                if fila[2]
            })

            edificio_masivo = st.selectbox(
                "Edificio",
                ["Todos"] + edificios_catalogo,
                key="qr_masivo_edificio",
            )

            filas_edificio = [
                fila
                for fila in filas_centro
                if (
                    edificio_masivo == "Todos"
                    or str(fila[2]) == edificio_masivo
                )
            ]

            plantas_catalogo = sorted({
                str(fila[3])
                for fila in filas_edificio
                if fila[3]
            })

            planta_masiva = st.selectbox(
                "Planta / zona",
                ["Todas"] + plantas_catalogo,
                key="qr_masivo_planta",
            )

            filas_filtradas = [
                fila
                for fila in filas_edificio
                if (
                    planta_masiva == "Todas"
                    or str(fila[3]) == planta_masiva
                )
            ]

            st.metric(
                "Espacios incluidos en el filtro",
                len(filas_filtradas),
            )

            if filas_filtradas:
                # Estado QR real actual, sin hacer una consulta por cada fila.
                espacios_qr_actuales = obtener_espacios_para_qr()

                claves_qr_activas = {
                    (
                        str(fila[1] or "").strip(),
                        str(fila[2] or "").strip(),
                        str(fila[3] or "").strip(),
                        str(fila[4] or "").strip(),
                    )
                    for fila in espacios_qr_actuales
                    if len(fila) >= 6
                }

                seleccionar_todos = st.checkbox(
                    "Seleccionar todos los espacios del filtro",
                    value=False,
                    key="qr_masivo_seleccionar_todos",
                    help=(
                        "Si lo marcas, todos aparecerán seleccionados. "
                        "Si lo dejas desmarcado, la tabla refleja el estado QR actual."
                    ),
                )

                clave_filtro = (
                    f"{centro_masivo}|"
                    f"{edificio_masivo}|"
                    f"{planta_masiva}"
                )

                df_seleccion = pd.DataFrame(
                    [
                        {
                            "Seleccionar": (
                                True
                                if seleccionar_todos
                                else (
                                    (
                                        str(fila[1] or "").strip(),
                                        str(fila[2] or "").strip(),
                                        str(fila[3] or "").strip(),
                                        str(fila[4] or "").strip(),
                                    )
                                    in claves_qr_activas
                                )
                            ),
                            "ID": int(fila[0]),
                            "Edificio": fila[2],
                            "Planta / zona": fila[3],
                            "Espacio": fila[4],
                            "Tipo": fila[5],
                        }
                        for fila in filas_filtradas
                    ]
                )

                tabla_editada = st.data_editor(
                    df_seleccion,
                    use_container_width=True,
                    hide_index=True,
                    disabled=[
                        "ID",
                        "Edificio",
                        "Planta / zona",
                        "Espacio",
                        "Tipo",
                    ],
                    column_config={
                        "Seleccionar": st.column_config.CheckboxColumn(
                            "Seleccionar",
                            help="Desmarca los espacios que todavía no quieras habilitar.",
                        ),
                        "ID": None,
                    },
                    key=f"qr_masivo_editor_{clave_filtro}",
                )

                ids_seleccionados = set(
                    tabla_editada.loc[
                        tabla_editada["Seleccionar"] == True,
                        "ID",
                    ]
                    .astype(int)
                    .tolist()
                )

                filas_seleccionadas = [
                    fila
                    for fila in filas_filtradas
                    if int(fila[0]) in ids_seleccionados
                ]

                st.caption(
                    f"Seleccionados: {len(filas_seleccionadas)} de "
                    f"{len(filas_filtradas)} espacios."
                )

                no_seleccionados = (
                    len(filas_filtradas)
                    - len(filas_seleccionadas)
                )

                st.info(
                    f"Al aplicar: **{len(filas_seleccionadas)}** quedarán con QR "
                    f"y **{no_seleccionados}** quedarán sin QR dentro de este filtro."
                )

                confirmar_masivo = st.checkbox(
                    "Confirmo aplicar exactamente esta selección",
                    key="qr_masivo_confirmar",
                )

                if st.button(
                    "📱 Aplicar selección de QR",
                    key="qr_masivo_habilitar",
                    type="primary",
                    use_container_width=True,
                ):
                    if not confirmar_masivo:
                        st.error(
                            "Marca primero la casilla de confirmación."
                        )
                    else:
                        habilitados, deshabilitados, errores = (
                            sincronizar_qr_espacios(
                                filas_filtradas,
                                ids_seleccionados,
                            )
                        )

                        if not errores:
                            st.success(
                                f"Selección aplicada: "
                                f"{habilitados} con QR y "
                                f"{deshabilitados} sin QR."
                            )
                            st.rerun()
                        else:
                            st.warning(
                                f"La selección se aplicó parcialmente. "
                                f"Hubo {len(errores)} errores."
                            )

                            with st.expander(
                                "Ver errores",
                                expanded=False,
                            ):
                                for error in errores:
                                    st.write(f"• {error}")
            else:
                st.info(
                    "No hay espacios activos dentro de este filtro."
                )

    st.markdown("---")

    espacios_qr = obtener_espacios_para_qr()

    if not espacios_qr:
        st.warning(
            "No hay espacios con QR habilitado todavía."
        )
        return

    centros = sorted({
        str(fila[1])
        for fila in espacios_qr
        if len(fila) >= 6 and fila[1]
    })

    centro_filtro = st.selectbox(
        "Centro",
        ["Todos"] + centros,
        key="qr_espacios_filtro_centro",
    )

    espacios_centro = [
        fila
        for fila in espacios_qr
        if (
            centro_filtro == "Todos"
            or str(fila[1]) == centro_filtro
        )
    ]

    edificios = sorted({
        str(fila[2])
        for fila in espacios_centro
        if len(fila) >= 6 and fila[2]
    })

    edificio_filtro = st.selectbox(
        "Edificio",
        ["Todos"] + edificios,
        key="qr_espacios_filtro_edificio",
    )

    buscar = st.text_input(
        "Buscar espacio",
        placeholder="Ejemplo: Patio, Sala polivalente, I4A, WC...",
        key="qr_espacios_buscar",
    ).strip().lower()

    resultados = []

    for fila in espacios_qr:
        if len(fila) < 6:
            continue

        (
            codigo,
            centro,
            edificio,
            planta,
            espacio,
            tipo_espacio,
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
            f"{planta} {espacio} {tipo_espacio}"
        ).lower()

        if buscar and buscar not in texto_busqueda:
            continue

        resultados.append(fila)

    st.caption(
        f"Espacios con QR encontrados: {len(resultados)}"
    )

    if not resultados:
        st.info(
            "No hay espacios que coincidan con los filtros."
        )
        return

    configuracion = obtener_configuracion_placas()

    st.markdown("### 📄 Placas para imprimir")

    st.caption(
        "Marca únicamente los espacios que quieras incluir en este PDF. "
        "Esta selección no activa ni desactiva ningún QR del colegio."
    )

    df_impresion = pd.DataFrame(
        [
            {
                "Imprimir": False,
                "Código": fila[0],
                "Planta": fila[3],
                "Espacio": fila[4],
                "Tipo": fila[5],
            }
            for fila in resultados
        ]
    )

    tabla_impresion = st.data_editor(
        df_impresion,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Código",
            "Planta",
            "Espacio",
            "Tipo",
        ],
        column_config={
            "Imprimir": st.column_config.CheckboxColumn(
                "✓ Imprimir",
                help="Marca solo las placas que quieras generar ahora.",
                default=False,
            ),
        },
        key=(
            f"qr_impresion_editor_"
            f"{centro_filtro}_{edificio_filtro}"
        ),
    )

    indices_imprimir = (
        tabla_impresion.index[
            tabla_impresion["Imprimir"] == True
        ].tolist()
    )

    resultados_imprimir = [
        resultados[indice]
        for indice in indices_imprimir
        if 0 <= indice < len(resultados)
    ]

    st.caption(
        f"Seleccionadas para imprimir: "
        f"**{len(resultados_imprimir)}** de {len(resultados)}."
    )

    if not resultados_imprimir:
        st.info(
            "Marca al menos una casilla para preparar el PDF."
        )

    else:
        st.caption(
            f"El PDF incluirá únicamente estas "
            f"{len(resultados_imprimir)} placas, "
            f"con {configuracion['por_pagina']} por página A4."
        )

        nombre_partes = ["QR_Espacios"]

        if centro_filtro != "Todos":
            nombre_partes.append(
                centro_filtro
            )

        if edificio_filtro != "Todos":
            nombre_partes.append(
                edificio_filtro
            )

        nombre_partes.append(
            f"{len(resultados_imprimir)}_seleccionadas"
        )

        nombre_pdf = (
            limpiar_nombre_archivo(
                "_".join(nombre_partes)
            )
            + ".pdf"
        )

        pdf_bytes = generar_pdf_pegatinas(
            resultados_imprimir,
            configuracion,
        )

        st.download_button(
            f"📄 Descargar PDF · "
            f"{len(resultados_imprimir)} placa(s)",
            data=pdf_bytes,
            file_name=nombre_pdf,
            mime="application/pdf",
            use_container_width=True,
            key="descargar_pdf_qr_espacios",
        )

        zip_imprenta = generar_zip_pegatinas_individuales(
            resultados_imprimir,
            configuracion,
        )

        st.download_button(
            f"🏷️ Descargar para imprenta · "
            f"{len(resultados_imprimir)} PDF individuales",
            data=zip_imprenta,
            file_name=(
                limpiar_nombre_archivo(
                    "_".join(nombre_partes)
                    + "_IMPRENTA_90x120mm"
                )
                + ".zip"
            ),
            mime="application/zip",
            use_container_width=True,
            key="descargar_qr_imprenta_individual",
            help=(
                "Descarga un ZIP con una placa por archivo PDF, "
                "cada una a tamaño real 90 × 120 mm."
            ),
        )

        st.caption(
            "Para imprenta: el ZIP contiene una pegatina por PDF, "
            "a tamaño real 90 × 120 mm, sin la hoja A4 de 6 placas."
        )

    st.markdown("---")

    with st.expander(
        "🔎 Ver y comprobar placas individuales",
        expanded=False,
    ):
        for fila in resultados:
            (
                codigo,
                centro,
                edificio,
                planta,
                espacio,
                tipo_espacio,
            ) = fila

            codigo = str(
                codigo or ""
            ).strip()

            if not codigo:
                continue

            enlace = construir_enlace_qr(
                codigo
            )

            qr_bytes = generar_qr_png(
                enlace,
                box_size=8,
                border=2,
            )

            with st.container(
                border=True
            ):
                st.markdown(
                    f"### 📍 {espacio}"
                )

                st.caption(
                    f"{tipo_espacio or 'Espacio'} · "
                    f"{centro} · {edificio} · {planta}"
                )

                col1, col2 = st.columns(
                    [1, 2]
                )

                with col1:
                    st.image(
                        qr_bytes,
                        width=150,
                    )

                with col2:
                    st.code(
                        codigo
                    )

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
            

            
