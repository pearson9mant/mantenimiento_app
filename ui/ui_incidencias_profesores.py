import streamlit as st
from datetime import datetime

from modules.ordenes import (
    crear_orden,
    obtener_siguiente_numero_ot,
    guardar_foto_ot,
)


ESPACIOS_POR_EDIFICIO = {
    "Infantil/Primaria": [
        "I3A", "I3B", "I3C",
        "I4A", "I4B", "I4C",
        "I5A", "I5B", "I5C",
        "1A", "1B", "1C",
        "2A", "2B", "2C",
        "3A", "3B", "3C",
        "4A", "4B", "4C",
        "5A", "5B", "5C",
        "6A", "6B", "6C",
        "Comedor niños",
        "Comedor profesores",
        "Patio cuadrado",
        "Patio fútbol",
        "Patio patines",
        "Capilla",
        "Secretaría",
        "Sala profesores",
        "Teatro",
        "Pasillos",
        "WC",
        "General",
        "Otro",
    ],
    "Llar": [
        "I1A", "I1B", "I1C",
        "I2A", "I2B", "I2C",
        "Sala polivalente",
        "Sala profesores",
        "Pasillo",
        "Almacén",
        "Despacho gym",
        "Vestuario femenino",
        "Vestuario masculino",
        "Patio",
        "WC",
        "Secretaría",
        "General",
        "Otro",
    ],
    "Edif. A": [
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillo",
        "WC",
        "General",
        "Otro",
    ],
    "Edif. B": [
        "General",
        "Laboratorio",
        "Aula música",
        "Aula informática",
        "Pasillo",
        "WC",
        "Otro",
    ],
    "Edif. C": [
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillo",
        "WC",
        "General",
        "Otro",
    ],
}

MAX_FOTOS = 5
MAX_MB_FOTO = 5


def limpiar_nombre_archivo(texto):
    texto = str(texto or "")
    caracteres_malos = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]

    for caracter in caracteres_malos:
        texto = texto.replace(caracter, "_")

    return texto.replace(" ", "_")


def operario_por_centro(centro):
    if centro == "Pearson 9":
        return "Luis Lozano"

    if centro == "Pearson 22":
        return "J.A. Almeda"

    return ""


def pantalla_incidencias_profesores():
    st.markdown(
        """
        <style>
        .inc-card {
            background: #f7f7f7;
            padding: 18px;
            border-radius: 14px;
            border: 1px solid #ddd;
            margin-bottom: 12px;
        }

        div.stButton > button {
            width: 100%;
            min-height: 58px;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 600;
        }

        textarea {
            font-size: 16px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## 📩 Comunicar incidencia")
    st.caption(
        "Comunica el problema observado. "
        "Mantenimiento se encargará de clasificarlo y gestionarlo."
    )

    clave_envio = "incidencia_profesores_enviada"
    incidencia_enviada = st.session_state.get(
        clave_envio,
        "",
    )

    if incidencia_enviada:
        st.success(
            f"✅ Incidencia enviada correctamente. "
            f"Nº OT: {incidencia_enviada}"
        )

        error_fotos = st.session_state.get(
            "incidencia_profesores_error_fotos",
            "",
        )

        if error_fotos:
            st.warning(error_fotos)

        st.caption(
            "No es necesario volver a enviar el mismo aviso."
        )

        if st.button(
            "➕ Comunicar otra incidencia",
            key="profesores_nueva_incidencia",
            use_container_width=True,
        ):
            st.session_state.pop(
                clave_envio,
                None,
            )
            st.session_state.pop(
                "incidencia_profesores_error_fotos",
                None,
            )
            st.rerun()

        return

    st.markdown(
        '<div class="inc-card">',
        unsafe_allow_html=True,
    )

    centro = st.selectbox(
        "Centro",
        ["Pearson 22", "Pearson 9"],
        key="prof_incidencia_centro",
    )

    if centro == "Pearson 22":
        edificios = ["Infantil/Primaria", "Llar"]
    else:
        edificios = ["Edif. A", "Edif. B", "Edif. C"]

    edificio = st.selectbox(
        "Edificio",
        edificios,
        key="prof_incidencia_edificio",
    )

    espacios = ESPACIOS_POR_EDIFICIO.get(
        edificio,
        ["General", "Otro"],
    )

    espacio_seleccionado = st.selectbox(
        "Espacio / Aula",
        espacios,
        key="prof_incidencia_espacio",
    )

    if espacio_seleccionado == "Otro":
        espacio = st.text_input(
            "Escribe el espacio",
            placeholder="Ejemplo: despacho, almacén, aula...",
            key="prof_incidencia_otro_espacio",
        )
    else:
        espacio = espacio_seleccionado

    descripcion = st.text_area(
        "¿Qué ocurre?",
        placeholder="Describe brevemente la incidencia",
        height=120,
        key="prof_incidencia_descripcion",
    )

    fotos = st.file_uploader(
        f"Añadir fotos (opcional, máximo {MAX_FOTOS})",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="fotos_incidencia_profesor",
        help=f"Máximo {MAX_FOTOS} fotos y {MAX_MB_FOTO} MB por foto.",
    )

    fotos_validas = []
    fotos_error = False

    if fotos:
        if len(fotos) > MAX_FOTOS:
            st.warning(
                f"Máximo {MAX_FOTOS} fotos por incidencia."
            )
            fotos_error = True
        else:
            cols = st.columns(3)

            for i, foto in enumerate(fotos):
                if foto.size > MAX_MB_FOTO * 1024 * 1024:
                    st.warning(
                        f"La foto {foto.name} supera "
                        f"{MAX_MB_FOTO} MB."
                    )
                    fotos_error = True
                    continue

                foto_bytes = foto.getvalue()

                fotos_validas.append(
                    (foto.name, foto_bytes)
                )

                with cols[i % 3]:
                    st.image(
                        foto_bytes,
                        caption=f"Foto {i + 1}",
                        use_container_width=True,
                    )

    prioridad = st.radio(
        "Prioridad",
        ["🟢 Baja", "🟡 Media", "🔴 Alta"],
        horizontal=True,
        key="prof_incidencia_prioridad",
    )

    tipo_solicitante = st.radio(
        "Quién envía",
        [
            "Profesores",
            "Cap de estudio",
            "Dirección",
            "Operarios",
        ],
        horizontal=True,
        key="prof_incidencia_tipo_solicitante",
    )

    nombre_solicitante = st.text_input(
        "Nombre",
        placeholder="Nombre de quien envía",
        key="prof_incidencia_nombre",
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button(
        "📨 Enviar incidencia",
        key="prof_incidencia_enviar",
        use_container_width=True,
        type="primary",
    ):
        descripcion_limpia = str(
            descripcion or ""
        ).strip()

        nombre_limpio = str(
            nombre_solicitante or ""
        ).strip()

        espacio_limpio = str(
            espacio or ""
        ).strip()

        if not descripcion_limpia:
            st.warning("Falta describir la incidencia.")
            return

        if not nombre_limpio:
            st.warning(
                "Falta poner el nombre de quien envía."
            )
            return

        if not espacio_limpio:
            st.warning("Falta indicar el espacio.")
            return

        if fotos_error:
            st.error(
                "Revisa las fotos. "
                f"Máximo {MAX_FOTOS} fotos y "
                f"{MAX_MB_FOTO} MB por foto."
            )
            return

        operario = operario_por_centro(
            centro
        )

        numero_ot = obtener_siguiente_numero_ot(
            centro,
            "INC",
        )

        fecha_origen = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        prioridad_limpia = (
            prioridad
            .replace("🟢 ", "")
            .replace("🟡 ", "")
            .replace("🔴 ", "")
        )

        datos = (
            numero_ot,
            descripcion_limpia,
            "Abierta",
            centro,
            edificio,
            espacio_limpio,
            "Otros",
            prioridad_limpia,
            operario,
            "PROFESORES",
            nombre_limpio,
            fecha_origen,
            "postgres_fotos" if fotos_validas else "",
            tipo_solicitante,
        )

        # Primero se crea la OT. Las fotos se guardan después.
        try:
            crear_orden(datos)

        except Exception as error:
            st.error(
                "No se ha podido crear la incidencia: "
                f"{error}"
            )
            return

        error_fotos_guardado = ""

        if fotos_validas:
            try:
                for i, (
                    nombre_original,
                    foto_bytes,
                ) in enumerate(
                    fotos_validas,
                    start=1,
                ):
                    nombre_foto = limpiar_nombre_archivo(
                        f"{numero_ot}_{i}_{nombre_original}"
                    )

                    guardar_foto_ot(
                        numero_ot=numero_ot,
                        nombre_foto=nombre_foto,
                        foto_data=foto_bytes,
                    )

            except Exception as error:
                error_fotos_guardado = str(error)

        st.session_state[
            clave_envio
        ] = numero_ot

        if error_fotos_guardado:
            st.session_state[
                "incidencia_profesores_error_fotos"
            ] = (
                "La incidencia se ha creado, pero alguna fotografía "
                "no pudo guardarse."
            )
        else:
            st.session_state.pop(
                "incidencia_profesores_error_fotos",
                None,
            )

        st.rerun()
