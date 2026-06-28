import streamlit as st

from modules.espacios import (
    crear_tabla_espacios,
    crear_espacio,
    obtener_espacios,
    desactivar_espacio,
    PLANTAS_BASE,
)


TIPOS_ESPACIO = [
    "Aula",
    "WC",
    "Biblioteca",
    "Cocina",
    "Comedor",
    "Despacho",
    "Sala técnica",
    "Pasillo",
    "Patio",
    "Terrado",
    "Almacén",
    "Laboratorio",
    "Gimnasio",
    "Otro",
]


def pantalla_admin_espacios():
    crear_tabla_espacios()

    st.subheader("🏫 Administrador de espacios")

    st.caption(
        "Alta y mantenimiento de espacios reales del colegio. "
        "Las plantas no se crean aquí como espacios; solo aulas, WC, salas, despachos, etc."
    )

    with st.expander("➕ Crear nuevo espacio", expanded=True):

        centros = list(PLANTAS_BASE.keys())

        centro = st.selectbox(
            "Centro",
            centros,
            key="admin_esp_centro"
        )

        edificios = list(PLANTAS_BASE.get(centro, {}).keys())

        edificio = st.selectbox(
            "Edificio",
            edificios,
            key="admin_esp_edificio"
        )

        plantas = PLANTAS_BASE.get(centro, {}).get(edificio, [])

        planta = st.selectbox(
            "Planta",
            plantas,
            key="admin_esp_planta"
        )

        tipo = st.selectbox(
            "Tipo de espacio",
            TIPOS_ESPACIO,
            key="admin_esp_tipo"
        )

        espacio = st.text_input(
            "Nombre del espacio",
            placeholder="Ejemplo: Aula 6C, WC chicos, Biblioteca, Sala calderas...",
            key="admin_esp_nombre"
        )

        if tipo == "Otro":
            tipo = st.text_input(
                "Especificar tipo",
                placeholder="Ejemplo: Sala orientación, Enfermería...",
                key="admin_esp_tipo_otro"
            )

        if st.button("💾 Guardar espacio", use_container_width=True, key="admin_esp_guardar"):
            if not espacio:
                st.warning("Indica el nombre del espacio.")
            elif espacio == planta:
                st.error("La planta no puede guardarse como espacio.")
            else:
                ok = crear_espacio(
                    centro=centro,
                    edificio=edificio,
                    planta=planta,
                    espacio=espacio,
                    tipo=tipo
                )

                if ok:
                    st.success("Espacio guardado correctamente.")
                    st.rerun()
                else:
                    st.error("No se pudo guardar el espacio.")

    st.markdown("---")
    st.markdown("### Espacios registrados")

    espacios = obtener_espacios(activos=True)

    if not espacios:
        st.info("Todavía no hay espacios registrados.")
        return

    filtro_centro = st.selectbox(
        "Filtrar centro",
        ["Todos"] + sorted(list(set([str(e[1]) for e in espacios if e[1]]))),
        key="admin_esp_filtro_centro"
    )

    espacios_filtrados = espacios

    if filtro_centro != "Todos":
        espacios_filtrados = [
            e for e in espacios_filtrados
            if str(e[1]) == filtro_centro
        ]

    for e in espacios_filtrados:
        (
            id_espacio,
            centro,
            edificio,
            planta,
            espacio,
            tipo,
            activo
        ) = e

        with st.expander(
            f"🏫 {centro} · {edificio} · {planta} · {espacio} · {tipo}",
            expanded=False
        ):
            st.markdown(f"**Centro:** {centro}")
            st.markdown(f"**Edificio:** {edificio}")
            st.markdown(f"**Planta:** {planta}")
            st.markdown(f"**Espacio:** {espacio}")
            st.markdown(f"**Tipo:** {tipo}")

            confirmar = st.checkbox(
                "Confirmo desactivar este espacio",
                key=f"confirmar_desactivar_espacio_{id_espacio}"
            )

            if st.button(
                "🗑️ Desactivar espacio",
                key=f"desactivar_espacio_{id_espacio}",
                use_container_width=True
            ):
                if not confirmar:
                    st.error("Marca primero la confirmación.")
                else:
                    desactivar_espacio(id_espacio)
                    st.warning("Espacio desactivado.")
                    st.rerun()
