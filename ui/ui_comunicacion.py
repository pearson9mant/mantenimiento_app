import streamlit as st
from datetime import date

from modules.espacios import obtener_espacios
from modules.ordenes import crear_orden, guardar_foto_ot


# =====================================================
# CONFIGURACIÓN
# =====================================================

OPERARIO_POR_CENTRO = {
    "Pearson 22": "J.A. Almeda",
    "Pearson 9": "Luis Lozano",
}


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
        "Espacio *",
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
# CREACIÓN DE LA OT
# =====================================================

def _crear_ot_comunicacion(
    titulo,
    descripcion,
    espacio_seleccionado,
    fecha_necesaria,
    archivo=None,
):
    titulo_limpio = str(titulo or "").strip()
    descripcion_limpia = str(descripcion or "").strip()

    centro = espacio_seleccionado["centro"]
    edificio = espacio_seleccionado["edificio"]
    espacio = espacio_seleccionado["espacio"]

    operario = OPERARIO_POR_CENTRO.get(centro, "")

    descripcion_ot = titulo_limpio

    if descripcion_limpia:
        descripcion_ot += f"\n\n{descripcion_limpia}"

    fecha_solicitud = date.today().isoformat()
    fecha_programada = fecha_necesaria.isoformat()

    numero_ot = crear_orden((
        "",                         # numero_ot
        descripcion_ot,
        "Abierta",
        centro,
        edificio,
        espacio,
        "",                         # area
        "Alta",
        operario,
        "COMUNICACION",
        "Comunicación",
        fecha_solicitud,
        "",
        "Comunicación",
        "Interna",
        "",                         # empresa
        "",                         # contacto
        "",                         # telefono
        "",                         # email
        fecha_programada,           # fecha_programada
        "",                         # fecha_aviso_empresa
        "",                         # fecha_realizacion
        "",                         # trabajo_a_realizar
        "",                         # trabajo_realizado
        "",                         # firma_operario
        "",                         # fecha_firma_operario
        0,                          # coste_estimado
        0,                          # coste_final
        ""                          # observaciones_estado
    ))

    if archivo is not None and numero_ot:
        guardar_foto_ot(
            numero_ot=numero_ot,
            nombre_foto=archivo.name,
            foto_data=archivo.getvalue(),
        )

    return numero_ot


# =====================================================
# PANTALLA
# =====================================================

def pantalla_comunicacion(modo="nuevo"):

    if modo == "historico":
        st.title("📋 Mis solicitudes")
        st.info("El histórico de solicitudes se conectará en el siguiente paso.")
        return

    st.title("📣 Comunicación")
    st.markdown("### Nueva solicitud")

    st.caption(
        "Indica el trabajo necesario. Mantenimiento recibirá automáticamente "
        "una orden con prioridad alta."
    )

    titulo = st.text_input(
        "Título *",
        placeholder="Ej.: Pérdida de agua",
        key="comunicacion_titulo"
    )

    espacio_seleccionado = _seleccionar_espacio()

    fecha_necesaria = st.date_input(
        "Fecha necesaria",
        value=date.today(),
        min_value=date.today(),
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

    if espacio_seleccionado:
        st.caption(
            f"📍 {espacio_seleccionado['centro']} · "
            f"{espacio_seleccionado['edificio']} · "
            f"{espacio_seleccionado['planta']} · "
            f"{espacio_seleccionado['espacio']}"
        )

    if st.button(
        "📣 Enviar solicitud",
        key="comunicacion_enviar",
        use_container_width=True,
        type="primary"
    ):
        titulo_limpio = str(titulo or "").strip()

        if not titulo_limpio:
            st.warning("Escribe el título de la solicitud.")
            return

        if not espacio_seleccionado:
            st.warning("Selecciona un espacio.")
            return

        try:
            with st.spinner("Creando la orden de trabajo..."):
                numero_ot = _crear_ot_comunicacion(
                    titulo=titulo_limpio,
                    descripcion=descripcion,
                    espacio_seleccionado=espacio_seleccionado,
                    fecha_necesaria=fecha_necesaria,
                    archivo=archivo,
                )

            if not numero_ot:
                st.error("No se pudo generar la orden de trabajo.")
                return

            st.success(
                f"✅ Solicitud enviada correctamente. OT: {numero_ot}"
            )

            st.info(
                f"📍 {espacio_seleccionado['espacio']} · "
                f"📅 Fecha necesaria: "
                f"{fecha_necesaria.strftime('%d/%m/%Y')}"
            )

        except Exception as e:
            st.error(
                "No se pudo crear la solicitud. "
                f"Detalle técnico: {e}"
            )
