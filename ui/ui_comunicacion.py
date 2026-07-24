import mimetypes
from datetime import date, datetime

import streamlit as st

from modules.espacios import obtener_espacios
from modules.ordenes import (
    crear_orden,
    guardar_foto_ot,
    obtener_ordenes,
    obtener_historico,
    obtener_fotos_ot,
)


# =====================================================
# CONFIGURACIÓN
# =====================================================

OPERARIO_POR_CENTRO = {
    "Pearson 22": "J.A. Almeda",
    "Pearson 9": "Luis Lozano",
}
SOLICITANTE_POR_USUARIO = {
    "comunicacion": "Comunicación",
    "direccion_servicios": "Dirección de Servicios",
    "direccionservicios": "Dirección de Servicios",
}


def _usuario_actual():
    """
    Obtiene el usuario que ha iniciado sesión.
    Revisa varias claves para adaptarse al sistema actual de login.
    """
    for clave in [
        "usuario",
        "username",
        "nombre_usuario",
        "email",
        "user",
    ]:
        valor = st.session_state.get(clave)

        if valor:
            return str(valor).strip()

    return ""


def _solicitante_actual():
    usuario = _usuario_actual()
    usuario_normalizado = usuario.lower().strip()

    solicitante = SOLICITANTE_POR_USUARIO.get(usuario_normalizado)

    if solicitante:
        return solicitante

    # Alternativa por si el nombre del departamento
    # ya está guardado en la sesión.
    departamento = str(
        st.session_state.get("departamento")
        or st.session_state.get("nombre")
        or ""
    ).strip()

    if departamento:
        return departamento

    return usuario or "Comunicación"


def _es_administracion():
    rol = str(
        st.session_state.get("rol")
        or st.session_state.get("tipo_usuario")
        or st.session_state.get("perfil")
        or ""
    ).strip().lower()

    return rol in [
        "admin",
        "administrador",
        "administracion",
        "administración",
    ]

# =====================================================
# UTILIDADES
# =====================================================

def _texto(valor):
    return str(valor or "").strip()


def _formatear_fecha(valor):
    texto = _texto(valor)

    if not texto:
        return "-"

    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ]

    for formato in formatos:
        try:
            fecha = datetime.strptime(texto[:19], formato)
            return fecha.strftime("%d/%m/%Y")
        except Exception:
            pass

    return texto


def _separar_titulo_descripcion(descripcion_ot):
    texto = _texto(descripcion_ot)

    if not texto:
        return "Solicitud de mantenimiento", ""

    partes = texto.splitlines()

    titulo = partes[0].strip()
    detalle = "\n".join(partes[1:]).strip()

    return titulo, detalle


def _icono_estado(estado):
    estado_txt = _texto(estado).lower()

    if estado_txt in ["finalizada", "cerrado"]:
        return "🟢"

    if estado_txt in [
        "en curso",
        "en ejecución",
        "pendiente material",
        "pendiente proveedor",
        "avisado",
        "pendiente presupuesto",
    ]:
        return "🟡"

    return "🔴"


def _estado_visible(estado):
    estado_txt = _texto(estado)

    if estado_txt == "Cerrado":
        return "Finalizada"

    return estado_txt or "Abierta"


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
            "centro": _texto(centro),
            "edificio": _texto(edificio),
            "planta": _texto(planta),
            "espacio": _texto(espacio),
            "tipo": _texto(tipo),
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
        key="comunicacion_espacio",
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
    titulo_limpio = _texto(titulo)
    descripcion_limpia = _texto(descripcion)

    centro = espacio_seleccionado["centro"]
    edificio = espacio_seleccionado["edificio"]
    espacio = espacio_seleccionado["espacio"]

    operario = OPERARIO_POR_CENTRO.get(centro, "")
    solicitante = _solicitante_actual()

    descripcion_ot = titulo_limpio

    if descripcion_limpia:
        descripcion_ot += f"\n\n{descripcion_limpia}"

    fecha_solicitud = date.today().isoformat()
    fecha_programada = fecha_necesaria.isoformat()

    numero_ot = crear_orden((
        "",                         # 0 numero_ot
        descripcion_ot,             # 1 descripcion
        "Abierta",                  # 2 estado
        centro,                     # 3 centro
        edificio,                   # 4 edificio
        espacio,                    # 5 espacio
        "",                         # 6 area automática
        "Alta",                     # 7 prioridad
        operario,                   # 8 operario
        "COMUNICACION",             # 9 origen
        solicitante,                # 10 solicitante real
        fecha_solicitud,            # 11 fecha_origen
        "",                         # 12 foto antigua
        "Comunicación",             # 13 tipo_solicitante
        "Interna",                  # 14 tipo_orden
        "",                         # 15 empresa_externa
        "",                         # 16 contacto_empresa
        "",                         # 17 telefono_empresa
        "",                         # 18 email_empresa
        fecha_programada,           # 19 fecha programada
        "",                         # 20 fecha_realizacion
        "",                         # 21 trabajo_a_realizar
        "",                         # 22 trabajo_realizado
        "",                         # 23 firma_operario
        "",                         # 24 fecha_firma_operario
        0,                          # 25 coste_estimado
        0,                          # 26 coste_final
        "",                         # 27 observaciones_estado
    ))

    if archivo is not None and numero_ot:
        guardar_foto_ot(
            numero_ot=numero_ot,
            nombre_foto=archivo.name,
            foto_data=archivo.getvalue(),
        )

    return numero_ot


# =====================================================
# SOLICITUDES DE COMUNICACIÓN
# =====================================================

def _normalizar_ot_activa(fila):
    return {
        "id": fila[0],
        "numero_ot": _texto(fila[1]),
        "descripcion": _texto(fila[2]),
        "estado": _texto(fila[3]),
        "fecha_creacion": fila[4],
        "centro": _texto(fila[5]),
        "edificio": _texto(fila[6]),
        "espacio": _texto(fila[7]),
        "area": _texto(fila[8]),
        "prioridad": _texto(fila[9]),
        "operario": _texto(fila[10]),
        "origen": _texto(fila[11]),
        "solicitante": _texto(fila[12]),
        "fecha_origen": fila[13],
        "fecha_programada": fila[21],
        "fecha_realizacion": fila[22],
        "observaciones_estado": _texto(fila[25]),
        "observaciones_cierre": "",
        "finalizada": False,
    }


def _normalizar_ot_historica(fila):
    return {
        "id": fila[0],
        "numero_ot": _texto(fila[1]),
        "descripcion": _texto(fila[2]),
        "estado": _texto(fila[3]),
        "fecha_creacion": fila[4],
        "centro": _texto(fila[5]),
        "edificio": _texto(fila[6]),
        "espacio": _texto(fila[7]),
        "area": _texto(fila[8]),
        "prioridad": _texto(fila[9]),
        "operario": _texto(fila[10]),
        "origen": _texto(fila[11]),
        "solicitante": _texto(fila[12]),
        "fecha_origen": fila[13],
        "fecha_cierre": fila[14],
        "observaciones_cierre": _texto(fila[15]),
        "fecha_programada": fila[23],
        "fecha_realizacion": fila[24],
        "observaciones_estado": _texto(fila[27]),
        "finalizada": True,
    }


def _obtener_solicitudes_comunicacion():
    solicitudes = []

    solicitante_actual = _solicitante_actual()
    es_admin = _es_administracion()

    for fila in obtener_ordenes():
        solicitud = _normalizar_ot_activa(fila)

        if solicitud["origen"].upper() != "COMUNICACION":
            continue

        if (
            not es_admin
            and solicitud["solicitante"].strip().lower()
            != solicitante_actual.strip().lower()
        ):
            continue

        solicitudes.append(solicitud)

    for fila in obtener_historico():
        solicitud = _normalizar_ot_historica(fila)

        if solicitud["origen"].upper() != "COMUNICACION":
            continue

        if (
            not es_admin
            and solicitud["solicitante"].strip().lower()
            != solicitante_actual.strip().lower()
        ):
            continue

        solicitudes.append(solicitud)

    solicitudes.sort(
        key=lambda item: _texto(
            item.get("fecha_creacion")
            or item.get("fecha_origen")
        ),
        reverse=True,
    )

    return solicitudes


# =====================================================
# ADJUNTOS
# =====================================================

def _mostrar_adjuntos(numero_ot):
    fotos = obtener_fotos_ot(numero_ot)

    if not fotos:
        return

    st.markdown("### 📎 Archivos adjuntos")

    for indice, foto in enumerate(fotos):
        nombre_foto = _texto(foto[0]) or f"archivo_{indice + 1}"
        foto_data = foto[1]

        mime, _ = mimetypes.guess_type(nombre_foto)
        mime = mime or "application/octet-stream"

        if mime.startswith("image/"):
            st.image(
                foto_data,
                caption=nombre_foto,
                use_container_width=True,
            )

        st.download_button(
            label=f"⬇️ Descargar {nombre_foto}",
            data=foto_data,
            file_name=nombre_foto,
            mime=mime,
            key=f"comunicacion_descargar_{numero_ot}_{indice}",
        )


# =====================================================
# DETALLE DE SOLICITUD
# =====================================================

def _mostrar_detalle_solicitud(solicitud):
    if st.button(
        "← Volver a mis solicitudes",
        key="comunicacion_volver_historico",
    ):
        st.session_state.pop("comunicacion_ot_abierta", None)
        st.rerun()

    titulo, descripcion = _separar_titulo_descripcion(
        solicitud["descripcion"]
    )

    estado = _estado_visible(solicitud["estado"])
    icono = _icono_estado(estado)

    st.title("📣 Solicitud")
    st.markdown(f"## {titulo}")

    if solicitud["finalizada"]:
        st.success("✅ Trabajo finalizado")
    else:
        st.info(f"{icono} Estado actual: **{estado}**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Estado", estado)

    with col2:
        st.metric("Prioridad", solicitud["prioridad"] or "Alta")

    with col3:
        st.metric("Área", solicitud["area"] or "Pendiente de clasificar")

    st.markdown("### 📍 Ubicación")

    st.write(
        f"**Centro:** {solicitud['centro'] or '-'}  \n"
        f"**Edificio:** {solicitud['edificio'] or '-'}  \n"
        f"**Espacio:** {solicitud['espacio'] or '-'}"
    )

    st.markdown("### 📋 Seguimiento")

    st.write(
        f"**OT:** {solicitud['numero_ot']}  \n"
        f"**Operario asignado:** {solicitud['operario'] or 'Pendiente'}  \n"
        f"**Fecha de solicitud:** "
        f"{_formatear_fecha(solicitud['fecha_origen'])}  \n"
        f"**Fecha necesaria:** "
        f"{_formatear_fecha(solicitud['fecha_programada'])}"
    )

    if descripcion:
        st.markdown("### 📝 Descripción")
        st.write(descripcion)

    if solicitud["observaciones_estado"]:
        st.markdown("### 🔧 Información de mantenimiento")
        st.info(solicitud["observaciones_estado"])

    if solicitud["finalizada"]:
        observaciones_finales = solicitud["observaciones_cierre"]

        st.markdown("### ✅ Trabajo realizado")

        if observaciones_finales:
            st.success(observaciones_finales)
        else:
            st.success("La orden de trabajo ha sido finalizada.")

        fecha_final = (
            solicitud.get("fecha_realizacion")
            or solicitud.get("fecha_cierre")
        )

        st.write(
            f"**Fecha de finalización:** "
            f"{_formatear_fecha(fecha_final)}  \n"
            f"**Operario:** {solicitud['operario'] or '-'}"
        )

    _mostrar_adjuntos(solicitud["numero_ot"])


# =====================================================
# HISTÓRICO
# =====================================================

def _mostrar_historico_comunicacion():
    solicitudes = _obtener_solicitudes_comunicacion()

    numero_abierto = st.session_state.get("comunicacion_ot_abierta")

    if numero_abierto:
        solicitud = next(
            (
                item
                for item in solicitudes
                if item["numero_ot"] == numero_abierto
            ),
            None,
        )

        if solicitud:
            _mostrar_detalle_solicitud(solicitud)
            return

        st.session_state.pop("comunicacion_ot_abierta", None)

    st.title("📋 Mis solicitudes")

    if not _es_administracion():
        st.caption(
            f"Mostrando únicamente las solicitudes de "
            f"**{_solicitante_actual()}**"
        )

    if not solicitudes:
        st.info("Todavía no hay solicitudes enviadas.")
        return

    abiertas = sum(
        1
        for solicitud in solicitudes
        if not solicitud["finalizada"]
        and solicitud["estado"] == "Abierta"
    )

    en_seguimiento = sum(
        1
        for solicitud in solicitudes
        if not solicitud["finalizada"]
        and solicitud["estado"] != "Abierta"
    )

    finalizadas = sum(
        1
        for solicitud in solicitudes
        if solicitud["finalizada"]
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Abiertas", abiertas)

    with col2:
        st.metric("En seguimiento", en_seguimiento)

    with col3:
        st.metric("Finalizadas", finalizadas)

    filtro_estado = st.selectbox(
        "Mostrar",
        [
            "Todas",
            "Abiertas",
            "En seguimiento",
            "Finalizadas",
        ],
        key="comunicacion_filtro_estado",
    )

    solicitudes_filtradas = []

    for solicitud in solicitudes:
        if filtro_estado == "Abiertas":
            if solicitud["finalizada"]:
                continue

            if solicitud["estado"] != "Abierta":
                continue

        elif filtro_estado == "En seguimiento":
            if solicitud["finalizada"]:
                continue

            if solicitud["estado"] == "Abierta":
                continue

        elif filtro_estado == "Finalizadas":
            if not solicitud["finalizada"]:
                continue

        solicitudes_filtradas.append(solicitud)

    if not solicitudes_filtradas:
        st.info("No hay solicitudes en este estado.")
        return

    for solicitud in solicitudes_filtradas:
        titulo, _ = _separar_titulo_descripcion(
            solicitud["descripcion"]
        )

        estado = _estado_visible(solicitud["estado"])
        icono = _icono_estado(estado)

        with st.container(border=True):
            col_info, col_boton = st.columns([5, 1])

            with col_info:
                st.markdown(f"### {icono} {titulo}")

                st.caption(
                    f"{solicitud['numero_ot']} · "
                    f"{solicitud['centro']} · "
                    f"{solicitud['espacio']}"
                )

                st.write(
                    f"**Estado:** {estado}  \n"
                    f"**Fecha necesaria:** "
                    f"{_formatear_fecha(solicitud['fecha_programada'])}"
                )

            with col_boton:
                if st.button(
                    "Ver",
                    key=f"comunicacion_ver_{solicitud['numero_ot']}",
                    use_container_width=True,
                ):
                    st.session_state["comunicacion_ot_abierta"] = (
                        solicitud["numero_ot"]
                    )
                    st.rerun()


# =====================================================
# NUEVA SOLICITUD
# =====================================================

def _mostrar_nueva_solicitud():
    st.title("📣 Comunicación")

    solicitante = _solicitante_actual()

    st.caption(
        f"Solicitudes de: **{solicitante}**"
    )

    st.markdown("### Nueva solicitud")

    st.caption(
        "Indica el trabajo necesario. Mantenimiento recibirá "
        "automáticamente una orden con prioridad alta."
    )

    titulo = st.text_input(
        "Título *",
        placeholder="Ej.: Pérdida de agua",
        key="comunicacion_titulo",
    )

    espacio_seleccionado = _seleccionar_espacio()

    fecha_necesaria = st.date_input(
        "Fecha necesaria",
        value=date.today(),
        min_value=date.today(),
        key="comunicacion_fecha",
    )

    descripcion = st.text_area(
        "Descripción (opcional)",
        placeholder="Añade información solamente si es necesaria.",
        height=130,
        key="comunicacion_descripcion",
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
        key="comunicacion_archivo",
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
        type="primary",
    ):
        titulo_limpio = _texto(titulo)

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


# =====================================================
# PANTALLA PRINCIPAL
# =====================================================

def pantalla_comunicacion(modo="nuevo"):
    if modo == "historico":
        _mostrar_historico_comunicacion()
        return

    _mostrar_nueva_solicitud()
