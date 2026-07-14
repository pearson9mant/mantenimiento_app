import streamlit as st

from modules.espacios import obtener_aulas_para_qr


URL_BASE_APP = "https://mantenimiento-app-1.onrender.com"


def pantalla_qr_aulas():
    st.markdown("## 📱 QR de aulas")

    st.info(
        "Aquí aparecen las aulas registradas en el catálogo central. "
        "Puedes abrir el formulario público de cada aula para comprobarlo."
    )

    aulas = obtener_aulas_para_qr()

    if not aulas:
        st.warning("No hay espacios registrados.")
        return

    # La función devuelve:
    # id, codigo, centro, edificio, planta, espacio
    aulas_filtradas = []

    for fila in aulas:
        try:
            (
                id_espacio,
                codigo,
                centro,
                edificio,
                planta,
                espacio,
            ) = fila
        except Exception:
            continue

        texto_espacio = str(espacio or "").strip().lower()

        # De momento filtramos por nombres habituales de aulas.
        es_aula = (
            texto_espacio.startswith("i")
            or texto_espacio.startswith("eso")
            or texto_espacio.startswith("bach")
            or texto_espacio[:1].isdigit()
            or "aula" in texto_espacio
        )

        if not es_aula:
            continue

        aulas_filtradas.append(fila)

    if not aulas_filtradas:
        st.warning(
            "No se han reconocido aulas automáticamente. "
            "Revisa cómo están nombrados los espacios."
        )
        return

    centros = sorted({
        str(fila[2])
        for fila in aulas_filtradas
        if fila[2]
    })

    centro_filtro = st.selectbox(
        "Centro",
        ["Todos"] + centros,
        key="qr_aulas_filtro_centro"
    )

    buscar = st.text_input(
        "Buscar aula",
        placeholder="Ejemplo: I3A, ESO 1A, Bach 2B...",
        key="qr_aulas_buscar"
    ).strip().lower()

    resultados = []

    for fila in aulas_filtradas:
        (
            id_espacio,
            codigo,
            centro,
            edificio,
            planta,
            espacio,
        ) = fila

        if centro_filtro != "Todos" and str(centro) != centro_filtro:
            continue

        texto_busqueda = (
            f"{codigo} {centro} {edificio} {planta} {espacio}"
        ).lower()

        if buscar and buscar not in texto_busqueda:
            continue

        resultados.append(fila)

    st.caption(f"Aulas encontradas: {len(resultados)}")

    for fila in resultados:
        (
            id_espacio,
            codigo,
            centro,
            edificio,
            planta,
            espacio,
        ) = fila

        enlace = (
            f"{URL_BASE_APP}/"
            f"?qr=1&codigo={codigo}"
        )

        with st.container(border=True):
            st.markdown(f"### 🏫 {espacio}")

            st.caption(
                f"{centro} · {edificio} · {planta}"
            )

            st.code(codigo)

            st.link_button(
                "🔎 Probar formulario de esta aula",
                enlace,
                use_container_width=True
            )
