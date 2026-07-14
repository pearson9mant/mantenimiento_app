import streamlit as st

from modules.espacios import (
    obtener_aulas_para_qr,
    obtener_espacios_llar_debug,
)


URL_BASE_APP = "https://mantenimiento-app-1.onrender.com"


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
        key="qr_aulas_filtro_centro"
    )

    buscar = st.text_input(
        "Buscar aula",
        placeholder="Ejemplo: I4A, 3A, ESO 1A...",
        key="qr_aulas_buscar"
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

        if centro_filtro != "Todos" and str(centro) != centro_filtro:
            continue

        texto_busqueda = (
            f"{codigo} {centro} {edificio} {planta} {espacio}"
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

        enlace = (
            "https://mantenimiento-app-1.onrender.com/"
            f"?qr=1&codigo={codigo}"
        )

        with st.container(border=True):
            st.markdown(f"### 🏫 {espacio}")

            st.caption(
                f"📍 {centro} · {edificio} · {planta}"
            )

            st.code(codigo)

            st.link_button(
                "🔎 Probar formulario de esta aula",
                enlace,
                use_container_width=True
            )
