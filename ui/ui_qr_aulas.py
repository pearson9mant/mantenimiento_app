import io

import qrcode
import streamlit as st

from modules.espacios import obtener_aulas_para_qr


URL_BASE_APP = "https://mantenimiento-app-1.onrender.com"


def generar_qr(url):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
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

    return buffer


def pantalla_qr_aulas():
    st.markdown("## 📱 QR de aulas")

    st.info(
        "Aquí aparecen las aulas registradas en el catálogo central. "
        "Puedes abrir el formulario público de cada aula para comprobarlo."
    )

    aulas = obtener_aulas_para_qr()

    if not aulas:
        st.warning("No hay aulas registradas.")
        return

    # La función devuelve:
    # codigo, centro, edificio, planta, espacio

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

        enlace = (
            f"{URL_BASE_APP}/"
            f"?qr=1&codigo={codigo}"
        )

        qr_buffer = generar_qr(enlace)
        qr_bytes = qr_buffer.getvalue()

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

            

            
