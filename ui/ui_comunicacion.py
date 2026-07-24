import streamlit as st
from datetime import date

from modules.espacios import buscar_espacios_texto


def _limpiar_seleccion_espacio():
    st.session_state.pop("comunicacion_espacio_seleccionado", None)
    st.session_state.pop("comunicacion_espacio_busqueda", None)


def _mostrar_buscador_espacio():
    seleccionado = st.session_state.get(
        "comunicacion_espacio_seleccionado"
    )

    if seleccionado:
        st.success(
            f"📍 {seleccionado['espacio']} · "
            f"{seleccionado['centro']} · "
            f"{seleccionado['edificio']} · "
            f"{seleccionado['planta']}"
        )

        if st.button(
            "Cambiar espacio",
            key="comunicacion_cambiar_espacio"
        ):
            _limpiar_seleccion_espacio()
            st.rerun()

        return seleccionado

    texto = st.text_input(
        "Espacio",
        placeholder="Escribe 3, I2, Biblioteca, Teatro...",
        key="comunicacion_espacio_busqueda"
    )

    texto = str(texto or "").strip()

    if not texto:
        return None

    resultados = buscar_espacios_texto(
        texto,
        limite=25
    )

    if not resultados:
        st.warning("No se han encontrado espacios.")
        return None

    st.caption(f"{len(resultados)} espacios encontrados")

    for resultado in resultados:
        etiqueta = resultado["espacio"]

        if resultado["centro"]:
            etiqueta += f" · {resultado['centro']}"

        if resultado["edificio"]:
            etiqueta += f" · {resultado['edificio']}"

        if resultado["planta"]:
            etiqueta += f" · {resultado['planta']}"

        if st.button(
            etiqueta,
            key=f"comunicacion_espacio_{resultado['id']}",
            use_container_width=True
        ):
            st.session_state[
                "comunicacion_espacio_seleccionado"
            ] = resultado

            st.rerun()

    return None


def pantalla_comunicacion(modo="nuevo"):

    if modo == "historico":
        st.title("📋 Mis solicitudes")
        st.info("Todavía no hay solicitudes para mostrar.")
        return

    st.title("📣 Comunicación")
    st.markdown("### Nueva solicitud")

    titulo = st.text_input(
        "Título",
        placeholder="Ej.: Pérdida de agua en aula",
        key="comunicacion_titulo"
    )

    espacio_seleccionado = _mostrar_buscador_espacio()

    fecha_necesaria = st.date_input(
        "Fecha necesaria",
        value=date.today(),
        key="comunicacion_fecha"
    )

    descripcion = st.text_area(
        "Descripción",
        height=180,
        key="comunicacion_descripcion"
    )

    archivo = st.file_uploader(
        "Adjuntar archivo (opcional)",
        type=[
            "pdf",
            "jpg",
            "jpeg",
            "png",
            "doc",
            "docx",
        ],
        key="comunicacion_archivo"
    )

    if st.button(
        "📣 Enviar solicitud",
        key="comunicacion_enviar",
        use_container_width=True
    ):
        if not titulo.strip():
            st.warning("Escribe el título de la solicitud.")
            return

        if not espacio_seleccionado:
            st.warning("Selecciona un espacio de la lista.")
            return

        if not descripcion.strip():
            st.warning("Escribe la descripción del trabajo.")
            return

        st.success(
            "Solicitud preparada correctamente. "
            "El siguiente paso será crear la OT."
        )
