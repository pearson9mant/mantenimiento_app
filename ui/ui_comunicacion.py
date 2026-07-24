import streamlit as st
from datetime import date

from modules.espacios import obtener_espacios


# =====================================================
# ESPACIOS
# =====================================================

def _obtener_opciones_espacios():
    filas = obtener_espacios(activos=True)

    opciones = {}

    for fila in filas:
        (
            id_espacio,
            centro,
            edificio,
            planta,
            espacio,
            tipo,
            activo,
        ) = fila

        opciones[id_espacio] = {
            "id": id_espacio,
            "centro": str(centro or "").strip(),
            "edificio": str(edificio or "").strip(),
            "planta": str(planta or "").strip(),
            "espacio": str(espacio or "").strip(),
            "tipo": str(tipo or "").strip(),
        }

    return opciones


def _etiqueta_espacio(id_espacio, opciones):
    datos = opciones.get(id_espacio)

    if not datos:
        return ""

    partes = [datos["espacio"]]

    if datos["centro"]:
        partes.append(datos["centro"])

    if datos["edificio"]:
        partes.append(datos["edificio"])

    if datos["planta"]:
        partes.append(datos["planta"])

    return " · ".join(partes)


def _seleccionar_espacio():
    opciones = _obtener_opciones_espacios()

    if not opciones:
        st.warning("No hay espacios disponibles.")
        return None

    ids_espacios = list(opciones.keys())

    id_seleccionado = st.selectbox(
        "Espacio",
        options=ids_espacios,
        index=None,
        placeholder="Escribe 3, I1, I2, Biblioteca...",
        format_func=lambda id_espacio: _etiqueta_espacio(
            id_espacio,
            opciones
        ),
        key="comunicacion_espacio"
    )

    if id_seleccionado is None:
        return None

    return opciones.get(id_seleccionado)


# =====================================================
# PANTALLA
# =====================================================

def pantalla_comunicacion(modo="nuevo"):

    if modo == "historico":
        st.title("📋 Mis solicitudes")
        st.info("Todavía no hay solicitudes para mostrar.")
        return

    st.title("📣 Comunicación")
    st.markdown("### Nueva solicitud")

    titulo = st.text_input(
        "Título",
        placeholder="Ej.: Pérdida de agua",
        key="comunicacion_titulo"
    )

    espacio_seleccionado = _seleccionar_espacio()

    fecha_necesaria = st.date_input(
        "Fecha necesaria",
        value=date.today(),
        key="comunicacion_fecha"
    )

    descripcion = st.text_area(
        "Descripción (opcional)",
        placeholder="Añade información solamente si es necesaria.",
        height=130,
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
        titulo_limpio = str(titulo or "").strip()

        if not titulo_limpio:
            st.warning("Escribe el título de la solicitud.")
            return

        if not espacio_seleccionado:
            st.warning("Selecciona un espacio.")
            return

        st.success(
            f"Solicitud preparada: {titulo_limpio} · "
            f"{espacio_seleccionado['espacio']}"
        )
