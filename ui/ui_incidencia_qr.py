import streamlit as st
from datetime import datetime

from modules.espacios import (
    obtener_espacio_por_codigo,
)
from modules.ordenes import (
    crear_orden,
    obtener_siguiente_numero_ot,
    guardar_foto_ot,
)


MAX_FOTOS = 5
MAX_MB_FOTO = 5


def limpiar_nombre_archivo(texto):
    texto = str(texto or "")

    for caracter in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]:
        texto = texto.replace(caracter, "_")

    return texto.replace(" ", "_")


def operario_por_centro(centro):
    if str(centro or "").strip() == "Pearson 9":
        return "Luis Lozano"

    if str(centro or "").strip() == "Pearson 22":
        return "J.A. Almeda"

    return ""


def obtener_id_espacio_qr():
    params = st.query_params

    valor = (
        params.get("espacio_id")
        or params.get("id_espacio")
        or params.get("id")
        or ""
    )

    try:
        return int(valor)
    except Exception:
        return None


def mostrar_estilo_formulario_qr():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 680px !important;
            padding-top: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        .qr-cabecera {
            background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
            color: white;
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 18px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
            text-align: center;
        }

        .qr-titulo {
            font-size: 28px;
            font-weight: 900;
            margin-bottom: 5px;
        }

        .qr-subtitulo {
            font-size: 15px;
            opacity: 0.92;
            font-weight: 600;
        }

        .qr-espacio {
            background: #f8fafc;
            border: 1px solid #dbeafe;
            border-radius: 20px;
            padding: 18px;
            margin-bottom: 18px;
            text-align: center;
        }

        .qr-espacio-nombre {
            font-size: 25px;
            font-weight: 900;
            color: #0f172a;
            margin-bottom: 5px;
        }

        .qr-ubicacion {
            color: #475569;
            font-size: 14px;
            font-weight: 700;
        }

        .qr-confirmacion {
            background: #ecfdf5;
            border: 1px solid #86efac;
            border-radius: 22px;
            padding: 24px;
            text-align: center;
            margin-top: 18px;
        }

        .qr-confirmacion-titulo {
            font-size: 25px;
            font-weight: 900;
            color: #166534;
            margin-bottom: 8px;
        }

        div.stButton > button {
            min-height: 58px !important;
            border-radius: 16px !important;
            font-size: 18px !important;
            font-weight: 900 !important;
        }

        textarea {
            font-size: 17px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pantalla_incidencia_qr():
    mostrar_estilo_formulario_qr()

    id_espacio = obtener_id_espacio_qr()

    if not id_espacio:
        st.error("El código QR no contiene un espacio válido.")
        return

    espacio_db = obtener_espacio_por_id(id_espacio)

    if not espacio_db:
        st.error(
            "Este espacio no existe o ya no está disponible. "
            "Comunícalo al departamento de mantenimiento."
        )
        return

    (
        id_espacio_db,
        codigo_espacio,
        centro,
        edificio,
        planta,
        espacio,
        tipo,
        activo,
    ) = espacio_db

    if int(activo or 0) != 1:
        st.error("Este espacio está desactivado.")
        return

    tipo_normalizado = str(tipo or "").strip().lower()

    if "aula" not in tipo_normalizado:
        st.warning(
            "Este formulario QR está habilitado actualmente solo para aulas."
        )
        return

    st.markdown(
        """
        <div class="qr-cabecera">
            <div class="qr-titulo">🛠️ Comunicar incidencia</div>
            <div class="qr-subtitulo">
                Colegio Abat Oliba Loreto
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="qr-espacio">
            <div class="qr-espacio-nombre">📍 {espacio}</div>
            <div class="qr-ubicacion">
                {centro} · {edificio} · {planta}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    incidencia_enviada = st.session_state.get(
        f"incidencia_qr_enviada_{id_espacio}",
        ""
    )

    if incidencia_enviada:
        st.markdown(
            f"""
            <div class="qr-confirmacion">
                <div class="qr-confirmacion-titulo">
                    ✅ Incidencia enviada
                </div>
                <div>
                    Referencia: <b>{incidencia_enviada}</b>
                </div>
                <div style="margin-top:10px;">
                    Mantenimiento ha recibido el aviso.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    descripcion = st.text_area(
        "¿Qué ocurre?",
        placeholder=(
            "Describe brevemente la incidencia. "
            "Ejemplo: la persiana no sube."
        ),
        height=150,
        key=f"qr_descripcion_{id_espacio}",
    )

    fotos = st.file_uploader(
        "Añadir fotografías (opcional)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"qr_fotos_{id_espacio}",
    )

    fotos_validas = []
    error_fotos = False

    if fotos:
        if len(fotos) > MAX_FOTOS:
            st.warning(f"Puedes añadir un máximo de {MAX_FOTOS} fotografías.")
            error_fotos = True

        else:
            columnas = st.columns(2)

            for indice, foto in enumerate(fotos):
                if foto.size > MAX_MB_FOTO * 1024 * 1024:
                    st.warning(
                        f"La fotografía {foto.name} supera {MAX_MB_FOTO} MB."
                    )
                    error_fotos = True
                    continue

                contenido = foto.getvalue()
                fotos_validas.append((foto.name, contenido))

                with columnas[indice % 2]:
                    st.image(
                        contenido,
                        caption=f"Foto {indice + 1}",
                        use_container_width=True,
                    )

    if st.button(
        "📨 Enviar incidencia",
        key=f"qr_enviar_{id_espacio}",
        use_container_width=True,
        type="primary",
    ):
        descripcion_limpia = str(descripcion or "").strip()

        if not descripcion_limpia:
            st.warning("Describe brevemente qué ocurre.")
            return

        if error_fotos:
            st.error("Revisa las fotografías antes de enviar.")
            return

        operario = operario_por_centro(centro)
        numero_ot = obtener_siguiente_numero_ot(centro, "INC")
        fecha_origen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        nombres_fotos = []

        try:
            for indice, (nombre_original, contenido) in enumerate(
                fotos_validas,
                start=1,
            ):
                nombre_foto = limpiar_nombre_archivo(
                    f"{numero_ot}_{indice}_{nombre_original}"
                )

                guardar_foto_ot(
                    numero_ot=numero_ot,
                    nombre_foto=nombre_foto,
                    foto_data=contenido,
                )

                nombres_fotos.append(nombre_foto)

        except Exception as error:
            st.error(f"No se pudieron guardar las fotografías: {error}")
            return

        ruta_foto = "|".join(nombres_fotos)

        observaciones_origen = (
            f"Incidencia comunicada mediante QR del aula.\n"
            f"Código de espacio: {codigo_espacio or id_espacio_db}\n"
            f"Planta: {planta or '-'}"
        )

        datos_orden = (
            numero_ot,
            descripcion_limpia,
            "Abierta",
            centro,
            edificio,
            espacio,
            "Otros",
            "Normal",
            operario,
            "APP",
            observaciones_origen,
            fecha_origen,
            ruta_foto,
            "Formulario QR",
        )

        try:
            crear_orden(datos_orden)

        except Exception as error:
            st.error(f"No se ha podido crear la incidencia: {error}")
            return

        st.session_state[
            f"incidencia_qr_enviada_{id_espacio}"
        ] = numero_ot

        st.rerun()
