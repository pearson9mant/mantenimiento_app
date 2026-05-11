import streamlit as st
from config import CENTROS, EDIFICIOS, AREAS, OPERARIOS, ESPACIOS
from modules.ubicaciones import obtener_ubicaciones_personalizadas
from config_gerencia import TIPOS_SOLICITANTE

from modules.ordenes import (
    crear_orden,
    obtener_ordenes,
    finalizar_orden,
    obtener_siguiente_numero_ot,
    actualizar_estado,
    actualizar_observaciones_estado,
    obtener_historico,
    borrar_orden,
    borrar_orden_historico,
    finalizar_trabajo_externo,
    obtener_detalle_orden_externa,
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
)


# =====================================================
# CACHE STREAMLIT
# =====================================================

def limpiar_cache_streamlit():
    try:
        st.cache_data.clear()
    except Exception:
        pass

    try:
        st.cache_resource.clear()
    except Exception:
        pass


# =====================================================
# PERMISOS / FILTRO OBLIGATORIO POR OPERARIO
# =====================================================

def rol_actual():
    return str(
        st.session_state.get("rol")
        or st.session_state.get("tipo_usuario")
        or st.session_state.get("perfil")
        or st.session_state.get("modo")
        or ""
    ).strip().lower()


def usuario_actual():
    return str(
        st.session_state.get("usuario")
        or st.session_state.get("user")
        or st.session_state.get("nombre")
        or ""
    ).strip()


def es_admin():
    rol = rol_actual()
    return rol in [
        "admin",
        "administrador",
        "administracion",
        "administración",
        "adminitracion",
        "adminitración",
        "responsable",
    ]


def es_gerencia():
    rol = rol_actual()
    return rol in [
        "gerencia",
        "gerente",
        "direccion",
        "dirección",
        "direccio",
        "direcció",
    ]


def es_operario():
    rol = rol_actual()
    return rol in [
        "operario",
        "operarios",
        "mantenimiento",
        "tecnico",
        "técnico",
    ]


def normalizar_txt(valor):
    return str(valor or "").strip().lower()


def obtener_operario_de_fila(fila):
    try:
        return fila[10]
    except Exception:
        return ""


def obtener_tipos_solicitante_lista():
    if isinstance(TIPOS_SOLICITANTE, dict):
        return list(TIPOS_SOLICITANTE.keys())
    return list(TIPOS_SOLICITANTE)


def centro_del_usuario_operario():
    usuario = normalizar_txt(usuario_actual())

    if usuario in [
        "j.a. almeda",
        "ja almeda",
        "juan antonio",
        "juan antonio almeda",
        "jalmeda",
        "j.a.almeda",
    ]:
        return "Pearson 22"

    if usuario in [
        "luis lozano",
        "luis",
    ]:
        return "Pearson 9"

    return ""


def filtrar_por_operario_obligatorio(filas):
    if not filas:
        return []

    if es_admin() or es_gerencia():
        return filas

    if es_operario():
        usuario = normalizar_txt(usuario_actual())
        centro_usuario = centro_del_usuario_operario()

        filtradas = []

        for f in filas:
            operario_fila = normalizar_txt(obtener_operario_de_fila(f))
            centro_fila = f[5] if len(f) > 5 else ""
            tipo_orden_fila = f[16] if len(f) > 16 else "Interna"

            if operario_fila == usuario:
                filtradas.append(f)
            elif tipo_orden_fila == "Externa" and centro_usuario and centro_fila == centro_usuario:
                filtradas.append(f)

        return filtradas

    return filas


def operario_forzado_si_toca(centro):
    if es_operario():
        return usuario_actual()

    return operario_por_centro(centro)


# =====================================================
# FUNCIONES EXISTENTES
# =====================================================

def obtener_origen_ot(origen):
    origen_txt = (origen or "").strip().upper()

    if origen_txt == "LEGIONELLA":
        return "Legionella"
    if origen_txt == "OUTLOOK":
        return "Profesor"
    if origen_txt == "PREVENTIVO":
        return "Preventivo"
    if origen_txt == "APP":
        return "App"
    if origen_txt == "EXTERNA":
        return "Externa"
    if origen_txt.startswith("PROFESORES"):
        return "Profesor"
    return "General"


def operario_por_centro(centro):
    if centro == "Pearson 9":
        return "Luis Lozano"
    if centro == "Pearson 22":
        return "J.A. Almeda"
    return OPERARIOS[0] if OPERARIOS else ""


def mostrar_checklist_preventivo(numero_ot, operario):
    st.markdown("### ✅ Checklist preventivo")

    checks = obtener_checklist_preventivo(numero_ot)

    if not checks:
        st.info("Esta OT preventiva no tiene checklist asociado.")
        return False

    hechos = 0

    for check in checks:
        (
            id_check,
            check_numero_ot,
            tarea_id,
            item,
            hecho,
            fecha_hecho,
            operario_check,
            observaciones_check
        ) = check

        valor_actual = bool(hecho)

        nuevo_valor = st.checkbox(
            item,
            value=valor_actual,
            key=f"check_prev_{numero_ot}_{id_check}"
        )

        if nuevo_valor != valor_actual:
            actualizar_checklist_preventivo(
                id_check,
                nuevo_valor,
                usuario_actual() or operario
            )
            limpiar_cache_streamlit()
            st.rerun()

        if nuevo_valor:
            hechos += 1

    total_checks = len(checks)
    st.caption(f"Checklist: {hechos}/{total_checks} completado")

    if hechos == total_checks:
        st.success("Checklist preventivo completado.")
        return True

    st.warning("Faltan puntos del checklist por marcar.")
    return False


# =====================================================
# PANTALLA
# =====================================================

def pantalla_ordenes():
    st.subheader("📋 Órdenes de trabajo")

    tipos_solicitante_lista = obtener_tipos_solicitante_lista()

    tab1, tab2, tab3 = st.tabs(["➕ Nueva orden", "📄 Activas", "🗂️ Histórico"])

    # =====================================================
    # NUEVA ORDEN
    # =====================================================

    with tab1:
        tab_interna, tab_externa = st.tabs(["🔧 Interna", "🏢 Externa"])

        # =====================================================
        # NUEVA ORDEN INTERNA
        # =====================================================

        with tab_interna:
            c1, c2 = st.columns(2)

            with c1:
                centro = st.selectbox("Centro", CENTROS, key="orden_int_centro")
                st.info("Número de OT interna: se asignará al crear la orden")

                edificios_disponibles = EDIFICIOS.get(centro, [])
                edificio = st.selectbox("Edificio", edificios_disponibles, key=f"orden_int_edificio_{centro}")

                espacios_base = ESPACIOS.get(edificio, [])

                espacios_custom = obtener_ubicaciones_personalizadas(
                    centro,
                    edificio
                )

                espacios_disponibles = list(
                    dict.fromkeys(
                    espacios_base + espacios_custom + ["General", "Otro"]
                    )
                )

                espacio_sel = st.selectbox(
                    "Espacio",
                    espacios_disponibles,
                    key=f"orden_int_espacio_{edificio}"
                )

                if espacio_sel == "Otro":
                    espacio = st.text_input("Especificar espacio nuevo", key="orden_int_espacio_otro")
                else:
                    espacio = espacio_sel

            with c2:
                tipo_solicitante = st.selectbox(
                    "Tipo solicitante",
                    tipos_solicitante_lista,
                    index=tipos_solicitante_lista.index("Operarios") if "Operarios" in tipos_solicitante_lista else 0,
                    key="orden_int_tipo_solicitante"
                )

                with st.form("form_nueva_orden_interna", clear_on_submit=True):
                    descripcion = st.text_area("Descripción", key="orden_int_descripcion")
                    area = st.selectbox("Área", AREAS, key="orden_int_area")
                    prioridad = st.selectbox("Prioridad", ["Baja", "Media", "Alta"], key="orden_int_prioridad")

                    operario_auto = operario_forzado_si_toca(centro)

                    if es_operario():
                        operario = operario_auto
                        st.info(f"👷 Operario asignado automáticamente: {operario}")
                    else:
                        indice_operario = OPERARIOS.index(operario_auto) if operario_auto in OPERARIOS else 0

                        operario_sel = st.selectbox(
                            "Operario",
                            OPERARIOS,
                            index=indice_operario,
                            key=f"orden_int_operario_{centro}"
                        )

                        if operario_sel == "Otro":
                            operario = st.text_input("Nombre operario", key="orden_int_operario_otro")
                        else:
                            operario = operario_sel

                    boton_crear_interna = st.form_submit_button("✅ Crear orden interna", use_container_width=True)

                    if boton_crear_interna:
                        tipo_solicitante_guardar = str(tipo_solicitante or "Operarios").strip()

                        if tipo_solicitante_guardar not in tipos_solicitante_lista:
                            tipo_solicitante_guardar = "Operarios"

                        if es_operario():
                            tipo_solicitante_guardar = "Operarios"
                            operario = usuario_actual()

                        if not descripcion.strip():
                            st.warning("La descripción es obligatoria")
                        elif not str(espacio).strip():
                            st.warning("Indica un espacio")
                        elif not operario.strip():
                            st.warning("Indica un operario")
                        else:
                            numero = obtener_siguiente_numero_ot(centro, "INC")

                            datos_orden = (
                                numero,
                                descripcion,
                                "Abierta",
                                centro,
                                edificio,
                                espacio,
                                area,
                                prioridad,
                                operario,
                                "APP",
                                "",
                                "",
                                "",
                                tipo_solicitante_guardar,
                                "Interna",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                0,
                                0,
                                ""
                            )

                            crear_orden(datos_orden)
                            limpiar_cache_streamlit()

                            st.success(f"Orden interna creada correctamente: {numero}")
                            st.rerun()

        # =====================================================
        # NUEVA ORDEN EXTERNA
        # =====================================================

        with tab_externa:
            c1, c2 = st.columns(2)

            with c1:
                centro_ext = st.selectbox("Centro", CENTROS, key="orden_ext_centro")
                st.info("Número de OT externa: se asignará al crear la orden")

                edificios_disponibles_ext = EDIFICIOS.get(centro_ext, [])
                edificio_ext = st.selectbox("Edificio", edificios_disponibles_ext, key=f"orden_ext_edificio_{centro_ext}")

                espacios_disponibles_ext = ESPACIOS.get(edificio_ext, ["General", "Otro"])
                espacio_sel_ext = st.selectbox("Espacio", espacios_disponibles_ext, key=f"orden_ext_espacio_{edificio_ext}")

                if espacio_sel_ext == "Otro":
                    espacio_ext = st.text_input("Especificar espacio nuevo", key="orden_ext_espacio_otro")
                else:
                    espacio_ext = espacio_sel_ext

            with c2:
                tipo_solicitante_ext = st.selectbox(
                    "Tipo solicitante",
                    tipos_solicitante_lista,
                    index=tipos_solicitante_lista.index("Operarios") if "Operarios" in tipos_solicitante_lista else 0,
                    key="orden_ext_tipo_solicitante"
                )

                with st.form("form_nueva_orden_externa", clear_on_submit=True):
                    descripcion_ext = st.text_area("Descripción / incidencia", key="orden_ext_descripcion")
                    area_ext = st.selectbox("Área", AREAS, key="orden_ext_area")
                    prioridad_ext = st.selectbox("Prioridad", ["Baja", "Media", "Alta"], key="orden_ext_prioridad")


                    st.markdown("### 🏢 Empresa externa")

                    empresa_externa = st.text_input(
                        "Empresa externa",
                        key="orden_ext_empresa"
                    )

                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""

                    fecha_aviso_empresa = st.date_input(
                        "Fecha de aviso a la empresa",
                        key="orden_ext_fecha_aviso"
                    )

                    trabajo_a_realizar = st.text_area(
                        "Trabajo a realizar",
                        placeholder="Opcional. Ejemplo: revisar equipo, reparar fuga, sustituir pieza...",
                        key="orden_ext_trabajo_a_realizar"
                    )

                    coste_estimado = st.number_input(
                        "Coste estimado €",
                        min_value=0.0,
                        step=10.0,
                        key="orden_ext_coste_estimado"
                    )

                    boton_crear_externa = st.form_submit_button("✅ Crear orden externa", use_container_width=True)

                    if boton_crear_externa:
                        tipo_solicitante_guardar_ext = str(tipo_solicitante_ext or "Operarios").strip()

                        if tipo_solicitante_guardar_ext not in tipos_solicitante_lista:
                            tipo_solicitante_guardar_ext = "Operarios"

                        if not descripcion_ext.strip():
                            st.warning("La descripción es obligatoria")
                        elif not str(espacio_ext).strip():
                            st.warning("Indica un espacio")
                        elif not empresa_externa.strip():
                            st.warning("Indica la empresa externa")
                        else:
                            numero_ext = obtener_siguiente_numero_ot(centro_ext, "EXT")

                            datos_orden_ext = (
                                numero_ext,
                                descripcion_ext,
                                "Pendiente proveedor",
                                centro_ext,
                                edificio_ext,
                                espacio_ext,
                                area_ext,
                                prioridad_ext,
                                "Proveedor externo",
                                "EXTERNA",
                                "",
                                "",
                                "",
                                tipo_solicitante_guardar_ext,
                                "Externa",
                                empresa_externa,
                                contacto_empresa,
                                telefono_empresa,
                                email_empresa,
                                str(fecha_aviso_empresa) if fecha_aviso_empresa else "",
                                "",
                                trabajo_a_realizar,
                                "",
                                "",
                                "",
                                coste_estimado,
                                0,
                                ""
                            )

                            crear_orden(datos_orden_ext)
                            limpiar_cache_streamlit()

                            st.success(f"Orden externa creada correctamente: {numero_ext}")
                            st.rerun()

    # =====================================================
    # ÓRDENES ACTIVAS
    # =====================================================

    with tab2:
        ordenes = obtener_ordenes()
        ordenes = filtrar_por_operario_obligatorio(ordenes)

        if ordenes:
            f1, f2, f3 = st.columns(3)

            with f1:
                filtro_estado = st.selectbox(
                    "Estado",
                    [
                        "Todas",
                        "Abierta",
                        "En curso",
                        "Pendiente material",
                        "Pendiente proveedor",
                        "Avisado",
                        "En ejecución",
                        "Cerrado",
                        "Incidencias",
                    ],
                    key="filtro_estado_admin_ot"
                )

            with f2:
                filtro_origen = st.selectbox(
                    "Origen",
                    ["Todos", "LEGIONELLA", "OUTLOOK", "APP", "EXTERNA", "PREVENTIVO", "PROFESORES"],
                    key="filtro_origen_admin_ot"
                )

            with f3:
                filtro_tipo_orden = st.selectbox(
                    "Tipo orden",
                    ["Todas", "Interna", "Externa"],
                    key="filtro_tipo_orden_admin_ot"
                )

            if filtro_origen != "Todos":
                if filtro_origen == "PROFESORES":
                    ordenes = [
                        o for o in ordenes
                        if (o[11] or "").strip().upper().startswith("PROFESORES")
                    ]
                else:
                    ordenes = [
                        o for o in ordenes
                        if (o[11] or "").strip().upper() == filtro_origen
                    ]

            if filtro_tipo_orden != "Todas":
                ordenes = [
                    o for o in ordenes
                    if len(o) > 16 and (o[16] or "Interna") == filtro_tipo_orden
                ]

            total_abiertas = len([o for o in ordenes if o[3] == "Abierta"])
            total_curso = len([o for o in ordenes if o[3] == "En curso"])
            total_material = len([o for o in ordenes if o[3] == "Pendiente material"])
            total_externas = len([
                o for o in ordenes
                if len(o) > 16 and (o[16] or "Interna") == "Externa"
            ])
            total_incidencias = len([
                o for o in ordenes
                if (o[11] or "").strip().upper() in ["LEGIONELLA", "EXTERNA"]
            ])

            if filtro_estado == "Incidencias":
                ordenes = [
                    o for o in ordenes
                    if (o[11] or "").strip().upper() in ["LEGIONELLA", "EXTERNA"]
                ]
            elif filtro_estado != "Todas":
                ordenes = [o for o in ordenes if o[3] == filtro_estado]

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Abiertas", total_abiertas)
            k2.metric("En curso", total_curso)
            k3.metric("Material", total_material)
            k4.metric("Externas", total_externas)
            k5.metric("Incidencias", total_incidencias)

            st.markdown("---")

        if not ordenes:
            if es_operario():
                st.info("No tienes órdenes activas asignadas")
            else:
                st.info("No hay órdenes activas")
        else:
            for o in ordenes:
                observaciones_estado = ""

                if len(o) >= 26:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, foto, tipo_solicitante,
                        tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
                        email_empresa, fecha_programada, fecha_realizacion,
                        coste_estimado, coste_final, observaciones_estado
                    ) = o
                elif len(o) == 25:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, foto, tipo_solicitante,
                        tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
                        email_empresa, fecha_programada, fecha_realizacion,
                        coste_estimado, coste_final
                    ) = o
                elif len(o) == 16:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, foto, tipo_solicitante
                    ) = o
                    tipo_orden = "Interna"
                    empresa_externa = ""
                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""
                    fecha_programada = ""
                    fecha_realizacion = ""
                    coste_estimado = 0
                    coste_final = 0
                elif len(o) == 15:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, foto
                    ) = o
                    tipo_solicitante = "Operarios"
                    tipo_orden = "Interna"
                    empresa_externa = ""
                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""
                    fecha_programada = ""
                    fecha_realizacion = ""
                    coste_estimado = 0
                    coste_final = 0
                elif len(o) == 14:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen
                    ) = o
                    foto = ""
                    tipo_solicitante = "Operarios"
                    tipo_orden = "Interna"
                    empresa_externa = ""
                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""
                    fecha_programada = ""
                    fecha_realizacion = ""
                    coste_estimado = 0
                    coste_final = 0
                else:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario, origen
                    ) = o
                    solicitante = ""
                    fecha_origen = ""
                    foto = ""
                    tipo_solicitante = "Operarios"
                    tipo_orden = "Interna"
                    empresa_externa = ""
                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""
                    fecha_programada = ""
                    fecha_realizacion = ""
                    coste_estimado = 0
                    coste_final = 0

                origen_label = obtener_origen_ot(origen)

                icono_estado = "🔴"
                if estado == "En curso":
                    icono_estado = "🟡"
                elif estado == "Pendiente material":
                    icono_estado = "📦"
                elif estado in ["Pendiente proveedor", "Avisado", "En ejecución", "Cerrado"]:
                    icono_estado = "🏢"

                if tipo_orden == "Externa":
                    titulo = f"{icono_estado} {numero_ot} | EXTERNA | {empresa_externa or '-'} | {centro or '-'} · {espacio or '-'}"
                else:
                    titulo = f"{icono_estado} {numero_ot} | {prioridad} | {centro or '-'} · {espacio or '-'}"

                with st.expander(titulo, expanded=False):
                    st.markdown(
                        f"**{numero_ot}** | {prioridad} | {area or '-'} | {origen_label}  \n"
                        f"{descripcion}  \n"
                        f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                        f"👷 {operario or '-'} | Estado: **{estado}**  \n"
                        f"📌 Tipo solicitante: **{tipo_solicitante or '-'}**  \n"
                        f"🔧 Tipo orden: **{tipo_orden or 'Interna'}**"
                    )

                    if observaciones_estado:
                        st.info(f"📝 Observación estado: {observaciones_estado}")

                    detalle_externa = {
                        "fecha_aviso_empresa": "",
                        "trabajo_a_realizar": "",
                        "trabajo_realizado": "",
                        "firma_operario": "",
                        "fecha_firma_operario": "",
                    }

                    if tipo_orden == "Externa":
                        detalle_externa = obtener_detalle_orden_externa(id_orden)

                        fecha_aviso_empresa = (
                            detalle_externa.get("fecha_aviso_empresa")
                            or fecha_programada
                            or ""
                        )

                        trabajo_a_realizar = detalle_externa.get("trabajo_a_realizar", "")
                        trabajo_realizado_guardado = detalle_externa.get("trabajo_realizado", "")
                        firma_guardada = detalle_externa.get("firma_operario", "")
                        fecha_firma_guardada = detalle_externa.get("fecha_firma_operario", "")

                        st.info(
                            f"🏢 Empresa: **{empresa_externa or '-'}**  \n"
                            f"👤 Contacto: {contacto_empresa or '-'}  \n"
                            f"☎️ Teléfono: {telefono_empresa or '-'}  \n"
                            f"✉️ Email: {email_empresa or '-'}  \n"
                            f"📅 Fecha aviso empresa: {fecha_aviso_empresa or '-'}  \n"
                            f"💰 Coste estimado: {coste_estimado or 0} €"
                        )

                        if trabajo_a_realizar:
                            st.warning(f"🛠️ Trabajo a realizar:\n\n{trabajo_a_realizar}")

                        if trabajo_realizado_guardado:
                            st.success(f"✅ Trabajo realizado:\n\n{trabajo_realizado_guardado}")

                        if firma_guardada:
                            st.caption(f"✍️ Confirmado por: {firma_guardada} | {fecha_firma_guardada or '-'}")

                    if (origen or "").strip().upper() == "PREVENTIVO":
                        mostrar_checklist_preventivo(numero_ot, operario)

                    if solicitante:
                        st.caption(f"Solicitante: {solicitante}")

                    if fecha_origen:
                        st.caption(f"Fecha origen: {fecha_origen}")

                    if foto:
                        try:
                            with st.expander("📷 Ver foto"):
                                st.image(foto, use_container_width=True)
                        except Exception:
                            st.caption("📷 Foto no disponible")

                    c2, c3, c4 = st.columns([2, 2, 2])

                    with c2:
                        if tipo_orden == "Externa":
                            estados = [
                                "Pendiente proveedor",
                                "Avisado",
                                "En ejecución",
                                "Cerrado",
                                "Finalizada",
                            ]
                        else:
                            estados = ["Abierta", "En curso", "Pendiente material", "Finalizada"]

                        nuevo_estado = st.selectbox(
                            f"Estado {numero_ot}",
                            estados,
                            index=estados.index(estado) if estado in estados else 0,
                            key=f"estado_admin_{id_orden}"
                        )

                        observaciones_estado_nueva = st.text_area(
                            "Observación del estado",
                            value=str(observaciones_estado or ""),
                            placeholder="Motivo del estado actual: en curso, material, proveedor...",
                            key=f"obs_estado_admin_{id_orden}"
                        )

                        if nuevo_estado != estado and nuevo_estado != "Finalizada":
                            if st.button(f"Actualizar {numero_ot}", key=f"act_admin_{id_orden}"):
                                actualizar_estado(id_orden, nuevo_estado, observaciones_estado_nueva)
                                limpiar_cache_streamlit()
                                st.rerun()
                        else:
                            if st.button(f"Guardar observación {numero_ot}", key=f"obs_admin_{id_orden}"):
                                actualizar_observaciones_estado(id_orden, observaciones_estado_nueva)
                                limpiar_cache_streamlit()
                                st.success("Observación guardada.")
                                st.rerun()

                    with c3:
                        if tipo_orden == "Externa":
                            with st.form(f"form_fin_ext_{id_orden}", clear_on_submit=False):
                                st.markdown("#### ✅ Cierre empresa externa")

                                trabajo_realizado = st.text_area(
                                    "Trabajo realizado por la empresa",
                                    value=str(detalle_externa.get("trabajo_realizado", "") or ""),
                                    placeholder="Ejemplo: se sustituye pieza, se repara fuga, se comprueba funcionamiento...",
                                    key=f"trabajo_realizado_ext_{id_orden}"
                                )

                                coste_final_nuevo = st.number_input(
                                    "Coste final €",
                                    min_value=0.0,
                                    step=10.0,
                                    value=float(coste_final or 0),
                                    key=f"coste_final_ext_{id_orden}"
                                )

                                firma_nombre = usuario_actual() or "Operario mantenimiento"

                                confirmar_realizado = st.checkbox(
                                    f"Confirmo que el trabajo externo está realizado. Firma: {firma_nombre}",
                                    key=f"firma_ext_{id_orden}"
                                )

                                finalizar_ext = st.form_submit_button(
                                    f"✅ Finalizar externa {numero_ot}",
                                    use_container_width=True
                                )

                                if finalizar_ext:
                                    if not trabajo_realizado.strip():
                                        st.error("Indica el trabajo realizado por la empresa.")
                                    elif not confirmar_realizado:
                                        st.error("Debes confirmar la firma del operario.")
                                    else:
                                        finalizar_trabajo_externo(
                                            id_orden,
                                            trabajo_realizado=trabajo_realizado,
                                            firma_operario=firma_nombre,
                                            coste_final=coste_final_nuevo,
                                            observaciones_estado=observaciones_estado_nueva
                                        )

                                        finalizar_orden(
                                            id_orden,
                                            observaciones=f"Trabajo externo confirmado por {firma_nombre}"
                                        )

                                        limpiar_cache_streamlit()
                                        st.success(f"{numero_ot} externa finalizada y enviada al histórico")
                                        st.rerun()

                        else:
                            if st.button(f"Finalizar {numero_ot}", key=f"fin_admin_{id_orden}"):

                                if (origen or "").strip().upper() == "PREVENTIVO":
                                    if not checklist_preventivo_completo(numero_ot):
                                        st.error("No puedes finalizar esta preventiva hasta completar todo el checklist.")
                                    else:
                                        actualizar_observaciones_estado(id_orden, observaciones_estado)
                                        finalizar_orden(id_orden)
                                        limpiar_cache_streamlit()
                                        st.success(f"{numero_ot} finalizada")
                                        st.rerun()
                                else:
                                    actualizar_observaciones_estado(id_orden, observaciones_estado)
                                    finalizar_orden(id_orden)
                                    limpiar_cache_streamlit()
                                    st.success(f"{numero_ot} finalizada")
                                    st.rerun()

                    with c4:
                        if es_admin() or es_gerencia():
                            confirmar_activa = st.checkbox("Confirmar", key=f"conf_admin_activas_{id_orden}")

                            if st.button(f"🗑️ Borrar {numero_ot}", key=f"del_admin_activas_{id_orden}"):
                                if confirmar_activa:
                                    borrar_orden(id_orden)
                                    limpiar_cache_streamlit()
                                    st.warning(f"{numero_ot} eliminada")
                                    st.rerun()
                                else:
                                    st.error("Debes marcar la confirmación antes de borrar")

    # =====================================================
    # HISTÓRICO
    # =====================================================

    with tab3:
        historico = obtener_historico()
        historico = filtrar_por_operario_obligatorio(historico)

        if not historico:
            if es_operario():
                st.info("No tienes órdenes finalizadas")
            else:
                st.info("No hay órdenes finalizadas")
        else:
            for h in historico:
                observaciones_estado = ""

                if len(h) >= 28:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, fecha_cierre,
                        observaciones_cierre, foto, tipo_solicitante,
                        tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
                        email_empresa, fecha_programada, fecha_realizacion,
                        coste_estimado, coste_final, observaciones_estado
                    ) = h
                elif len(h) == 27:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, fecha_cierre,
                        observaciones_cierre, foto, tipo_solicitante,
                        tipo_orden, empresa_externa, contacto_empresa, telefono_empresa,
                        email_empresa, fecha_programada, fecha_realizacion,
                        coste_estimado, coste_final
                    ) = h
                elif len(h) == 18:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, fecha_cierre,
                        observaciones_cierre, foto, tipo_solicitante
                    ) = h
                    tipo_orden = "Interna"
                    empresa_externa = ""
                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""
                    fecha_programada = ""
                    fecha_realizacion = ""
                    coste_estimado = 0
                    coste_final = 0
                elif len(h) == 17:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, fecha_cierre,
                        observaciones_cierre, foto
                    ) = h
                    tipo_solicitante = "Operarios"
                    tipo_orden = "Interna"
                    empresa_externa = ""
                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""
                    fecha_programada = ""
                    fecha_realizacion = ""
                    coste_estimado = 0
                    coste_final = 0
                elif len(h) == 16:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, solicitante, fecha_origen, fecha_cierre,
                        observaciones_cierre
                    ) = h
                    foto = ""
                    tipo_solicitante = "Operarios"
                    tipo_orden = "Interna"
                    empresa_externa = ""
                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""
                    fecha_programada = ""
                    fecha_realizacion = ""
                    coste_estimado = 0
                    coste_final = 0
                else:
                    (
                        id_orden, numero_ot, descripcion, estado, fecha,
                        centro, edificio, espacio, area, prioridad, operario,
                        origen, fecha_cierre, observaciones_cierre
                    ) = h
                    solicitante = ""
                    fecha_origen = ""
                    foto = ""
                    tipo_solicitante = "Operarios"
                    tipo_orden = "Interna"
                    empresa_externa = ""
                    contacto_empresa = ""
                    telefono_empresa = ""
                    email_empresa = ""
                    fecha_programada = ""
                    fecha_realizacion = ""
                    coste_estimado = 0
                    coste_final = 0

                origen_label = obtener_origen_ot(origen)

                with st.container():
                    c1, c2 = st.columns([6, 2])

                    with c1:
                        st.markdown(
                            f"**{numero_ot}** | {prioridad} | {area or '-'} | {origen_label}  \n"
                            f"{descripcion}  \n"
                            f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                            f"👷 {operario or '-'} | Cierre: {fecha_cierre or '-'}  \n"
                            f"📌 Tipo solicitante: **{tipo_solicitante or '-'}**  \n"
                            f"🔧 Tipo orden: **{tipo_orden or 'Interna'}**"
                        )

                        if tipo_orden == "Externa":
                            st.info(
                                f"🏢 Empresa: **{empresa_externa or '-'}**  \n"
                                f"👤 Contacto: {contacto_empresa or '-'}  \n"
                                f"☎️ Teléfono: {telefono_empresa or '-'}  \n"
                                f"✉️ Email: {email_empresa or '-'}  \n"
                                f"📅 Fecha aviso/programada: {fecha_programada or '-'}  \n"
                                f"📅 Fecha realización: {fecha_realizacion or '-'}  \n"
                                f"💰 Coste estimado: {coste_estimado or 0} €  \n"
                                f"💶 Coste final: {coste_final or 0} €"
                            )

                        if solicitante:
                            st.caption(f"Solicitante: {solicitante}")

                        if fecha_origen:
                            st.caption(f"Fecha origen: {fecha_origen}")

                        if observaciones_cierre:
                            st.caption(f"📝 {observaciones_cierre}")

                        if observaciones_estado:
                            st.info(f"📝 Observación durante el estado: {observaciones_estado}")

                        if foto:
                            try:
                                with st.expander("📷 Ver foto"):
                                    st.image(foto, use_container_width=True)
                            except Exception:
                                st.caption("📷 Foto no disponible")

                    with c2:
                        if es_admin() or es_gerencia():
                            confirmar_hist = st.checkbox("Confirmar", key=f"conf_admin_hist_{id_orden}")

                            if st.button(f"🗑️ Borrar {numero_ot}", key=f"del_admin_hist_{id_orden}"):
                                if confirmar_hist:
                                    borrar_orden_historico(id_orden)
                                    limpiar_cache_streamlit()
                                    st.warning(f"{numero_ot} eliminada del histórico")
                                    st.rerun()
                                else:
                                    st.error("Debes marcar la confirmación antes de borrar")

                    st.markdown("---")
