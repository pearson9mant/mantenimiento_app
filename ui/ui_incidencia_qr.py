import streamlit as st
from datetime import datetime

from modules.espacios import obtener_espacio_por_codigo
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
    centro = str(centro or "").strip()

    if centro == "Pearson 9":
        return "Luis Lozano"

    if centro == "Pearson 22":
        return "J.A. Almeda"

    return ""


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

    codigo = str(
        st.query_params.get("codigo") or ""
    ).strip()

    if not codigo:
        st.error("El código QR no contiene un espacio válido.")
        return

    espacio_db = obtener_espacio_por_codigo(codigo)

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

    clave_envio = f"incidencia_qr_enviada_{codigo_espacio}"

    incidencia_enviada = st.session_state.get(
        clave_envio,
        ""
    )

    # =====================================================
    # CABECERA PERSONALIZADA
    # =====================================================

    st.markdown(
        """
<div class="qr-cabecera">
    <div class="qr-titulo">Comunicar una incidencia</div>
    <div class="qr-subtitulo">
        Servicio de Mantenimiento · Colegio Abat Oliba Loreto
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="qr-espacio">
    <div style="
        color: #2563eb;
        font-size: 13px;
        font-weight: 900;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 7px;
    ">
        Aula seleccionada
    </div>

    <div class="qr-espacio-nombre">
        {espacio}
    </div>

    <div class="qr-ubicacion">
        {centro} · {edificio}<br>
        {planta}
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # CONFIRMACIÓN FINAL
    # =====================================================

    if incidencia_enviada:
        st.markdown(
            f"""
<div style="
    background: linear-gradient(145deg, #ecfdf5 0%, #f0fdf4 100%);
    border: 2px solid #86efac;
    border-radius: 26px;
    padding: 34px 26px;
    text-align: center;
    box-shadow: 0 14px 34px rgba(22, 101, 52, 0.12);
    margin-top: 10px;
">
    <div style="
        width: 74px;
        height: 74px;
        line-height: 74px;
        margin: 0 auto 18px auto;
        border-radius: 50%;
        background: #22c55e;
        color: white;
        font-size: 40px;
        font-weight: 900;
        box-shadow: 0 8px 20px rgba(34, 197, 94, 0.28);
    ">
        ✓
    </div>

    <div style="
        font-size: 27px;
        font-weight: 950;
        color: #14532d;
        margin-bottom: 12px;
    ">
        Aviso enviado correctamente
    </div>

    <div style="
        color: #166534;
        font-size: 17px;
        font-weight: 800;
        margin-bottom: 10px;
    ">
        Gracias por comunicar la incidencia.
    </div>

    <div style="
        color: #334155;
        font-size: 15px;
        line-height: 1.6;
        max-width: 470px;
        margin: 0 auto;
    ">
        El departamento de mantenimiento ha recibido el aviso
        y lo revisará lo antes posible.
    </div>

    <div style="
        margin: 26px auto 0 auto;
        padding: 16px 20px;
        max-width: 350px;
        background: white;
        border: 1px solid #bbf7d0;
        border-radius: 16px;
    ">
        <div style="
            color: #64748b;
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 5px;
        ">
            Número de referencia
        </div>

        <div style="
            color: #0f172a;
            font-size: 24px;
            font-weight: 950;
        ">
            {incidencia_enviada}
        </div>
    </div>

    <div style="
        margin-top: 20px;
        color: #64748b;
        font-size: 13px;
        line-height: 1.5;
    ">
        No es necesario volver a enviar el mismo aviso.
    </div>
</div>

<div style="
    text-align: center;
    margin-top: 22px;
    color: #64748b;
    font-size: 12px;
    line-height: 1.6;
">
    Colegio Abat Oliba Loreto<br>
    Sistema Integral de Mantenimiento
</div>
            """,
            unsafe_allow_html=True,
        )
        return

    # =====================================================
    # FORMULARIO
    # =====================================================

    descripcion = st.text_area(
        "¿Qué ocurre en este espacio?",
        placeholder="Describe brevemente el problema observado.",
        height=150,
        key=f"qr_descripcion_{codigo_espacio}",
    )

    fotos = st.file_uploader(
        "Añadir fotografías (opcional)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"qr_fotos_{codigo_espacio}",
    )

    fotos_validas = []
    error_fotos = False

    if fotos:
        if len(fotos) > MAX_FOTOS:
            st.warning(
                f"Puedes añadir un máximo de {MAX_FOTOS} fotografías."
            )
            error_fotos = True

        else:
            columnas = st.columns(2)

            for indice, foto in enumerate(fotos):
                if foto.size > MAX_MB_FOTO * 1024 * 1024:
                    st.warning(
                        f"La fotografía {foto.name} supera "
                        f"{MAX_MB_FOTO} MB."
                    )
                    error_fotos = True
                    continue

                contenido = foto.getvalue()
                fotos_validas.append(
                    (foto.name, contenido)
                )

                with columnas[indice % 2]:
                    st.image(
                        contenido,
                        caption=f"Foto {indice + 1}",
                        use_container_width=True,
                    )

    if st.button(
        "Enviar aviso",
        key=f"qr_enviar_{codigo_espacio}",
        use_container_width=True,
        type="primary",
    ):
        descripcion_limpia = str(
            descripcion or ""
        ).strip()

        if not descripcion_limpia:
            st.warning(
                "Describe brevemente qué ocurre."
            )
            return

        if error_fotos:
            st.error(
                "Revisa las fotografías antes de enviar."
            )
            return

        operario = operario_por_centro(centro)
        numero_ot = obtener_siguiente_numero_ot(
            centro,
            "INC"
        )

        fecha_origen = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        nombres_fotos = []

        try:
            for indice, (
                nombre_original,
                contenido,
            ) in enumerate(
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
            st.error(
                "No se pudieron guardar las fotografías: "
                f"{error}"
            )
            return

        ruta_foto = "|".join(nombres_fotos)

        observaciones_origen = (
            "Incidencia comunicada mediante QR del aula.\n"
            f"Código de espacio: "
            f"{codigo_espacio or id_espacio_db}\n"
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
            with st.spinner("Enviando aviso..."):
                crear_orden(datos_orden)

        except Exception as error:
            st.error(
                "No se ha podido crear la incidencia: "
                f"{error}"
            )
            return

        st.session_state[clave_envio] = numero_ot
        st.rerun()
