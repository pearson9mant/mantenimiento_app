import streamlit as st
from database.db import conectar, _sql
from config import CENTROS, EDIFICIOS, AREAS, OPERARIOS, ESPACIOS
from modules.ubicaciones import obtener_espacios
from modules.espacios import (
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)
from config_gerencia import TIPOS_SOLICITANTE
from ui.ui_legionella import obtener_checklist_correctivo_legionella

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
    guardar_foto_ot,
    obtener_fotos_ot,
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
)
from ui.ui_legionella import (
    guardar_checklist_correctivo_legionella,
    borrar_checklist_correctivo_legionella,
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


def obtener_espacios_completos(centro, edificio):
    espacios_base = ESPACIOS.get(edificio, [])

    try:
        espacios_custom = obtener_ubicaciones_personalizadas()
    except Exception:
        espacios_custom = []

    espacios_filtrados = []

    for esp in espacios_custom:
        try:
            centro_esp = str(esp[1] or "").strip()
            edificio_esp = str(esp[2] or "").strip()
            nombre_esp = str(esp[3] or "").strip()

            if nombre_esp:
                if centro_esp == centro and edificio_esp == edificio:
                    espacios_filtrados.append(nombre_esp)
                elif nombre_esp.lower() == "calderas":
                    espacios_filtrados.append(nombre_esp)

        except Exception:
            pass

    return list(
        dict.fromkeys(
            espacios_base + espacios_filtrados + ["General", "Otro"]
        )
    )


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
# CORRECCIÓN DE UBICACIÓN DE OT
# =====================================================

def indice_seguro(opciones, valor_actual):
    if not opciones:
        return 0

    valor_actual = str(valor_actual or "").strip()

    if valor_actual in opciones:
        return opciones.index(valor_actual)

    return 0


def extraer_nombre_espacio(fila):
    if isinstance(fila, dict):
        return str(
            fila.get("espacio")
            or fila.get("nombre")
            or ""
        ).strip()

    if isinstance(fila, (list, tuple)):
        if not fila:
            return ""

        return str(fila[0] or "").strip()

    return str(fila or "").strip()


def obtener_planta_catalogo(
    centro,
    edificio,
    espacio,
):
    centro = str(centro or "").strip()
    edificio = str(edificio or "").strip()
    espacio = str(espacio or "").strip()

    if not centro or not edificio or not espacio:
        return ""

    plantas = obtener_plantas_espacios(
        centro,
        edificio,
    )

    for planta in plantas:
        filas_espacios = obtener_espacios_por_planta(
            centro,
            edificio,
            planta,
        )

        for fila_espacio in filas_espacios:
            nombre_espacio = extraer_nombre_espacio(
                fila_espacio
            )

            if nombre_espacio == espacio:
                return str(planta or "").strip()

    return ""


def actualizar_ubicacion_ot(
    id_orden,
    centro,
    edificio,
    espacio,
):
    centro = str(centro or "").strip()
    edificio = str(edificio or "").strip()
    espacio = str(espacio or "").strip()

    if not centro:
        return False, "Selecciona el centro."

    if not edificio:
        return False, "Selecciona el edificio."

    if not espacio:
        return False, "Selecciona el espacio."

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE ordenes_trabajo
            SET centro = ?,
                edificio = ?,
                espacio = ?
            WHERE id = ?
        """), (
            centro,
            edificio,
            espacio,
            id_orden,
        ))

        conn.commit()

        return True, "Ubicación actualizada correctamente."

    except Exception as e:
        conn.rollback()

        return False, (
            f"No se pudo actualizar la ubicación: {e}"
        )

    finally:
        conn.close()


def mostrar_editor_ubicacion_ot_admin(
    id_orden,
    numero_ot,
    centro_actual,
    edificio_actual,
    espacio_actual,
):
    if not (es_admin() or es_gerencia()):
        return

    st.markdown(
        f"### ✏️ Corregir ubicación {numero_ot}"
    )

    st.caption(
        "La planta se obtiene automáticamente del catálogo. "
        "La OT solo guarda centro, edificio y espacio."
    )

    centros = obtener_centros_espacios()

    if not centros:
        st.warning(
            "No hay centros registrados en el catálogo."
        )
        return

    centro_sel = st.selectbox(
        "Centro",
        centros,
        index=indice_seguro(
            centros,
            centro_actual,
        ),
        key=f"corregir_centro_ot_{id_orden}",
    )

    edificios = obtener_edificios_espacios(
        centro_sel
    )

    if not edificios:
        st.warning(
            "No hay edificios registrados para este centro."
        )
        return

    edificio_sel = st.selectbox(
        "Edificio",
        edificios,
        index=indice_seguro(
            edificios,
            edificio_actual,
        ),
        key=f"corregir_edificio_ot_{id_orden}",
    )

    plantas = obtener_plantas_espacios(
        centro_sel,
        edificio_sel,
    )

    if not plantas:
        st.warning(
            "No hay plantas registradas para este edificio."
        )
        return

    planta_actual = obtener_planta_catalogo(
        centro_actual,
        edificio_actual,
        espacio_actual,
    )

    planta_sel = st.selectbox(
        "Planta",
        plantas,
        index=indice_seguro(
            plantas,
            planta_actual,
        ),
        key=f"corregir_planta_ot_{id_orden}",
    )

    filas_espacios = obtener_espacios_por_planta(
        centro_sel,
        edificio_sel,
        planta_sel,
    )

    espacios = []

    for fila_espacio in filas_espacios:
        nombre_espacio = extraer_nombre_espacio(
            fila_espacio
        )

        if (
            nombre_espacio
            and nombre_espacio not in espacios
        ):
            espacios.append(nombre_espacio)

    if not espacios:
        st.warning(
            "No hay espacios registrados en esta planta."
        )
        return

    espacio_sel = st.selectbox(
        "Espacio",
        espacios,
        index=indice_seguro(
            espacios,
            espacio_actual,
        ),
        key=f"corregir_espacio_ot_{id_orden}",
    )

    st.info(
        f"📍 Nueva ubicación: "
        f"{centro_sel} · {edificio_sel} · "
        f"{planta_sel} · {espacio_sel}"
    )

    confirmar_ubicacion = st.checkbox(
        "Confirmo el cambio de ubicación",
        key=f"confirmar_cambio_ubicacion_{id_orden}",
    )

    if st.button(
        f"💾 Guardar ubicación {numero_ot}",
        key=f"guardar_ubicacion_ot_{id_orden}",
        use_container_width=True,
        type="primary",
    ):
        if not confirmar_ubicacion:
            st.error(
                "Marca primero la confirmación."
            )
            return

        ok, mensaje = actualizar_ubicacion_ot(
            id_orden=id_orden,
            centro=centro_sel,
            edificio=edificio_sel,
            espacio=espacio_sel,
        )

        if ok:
            st.session_state.pop(
                "ot_editor_ubicacion_activa",
                None,
            )

            limpiar_cache_streamlit()
            st.success(mensaje)
            st.rerun()

        else:
            st.error(mensaje)

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

                espacios_disponibles = obtener_espacios(edificio, centro)

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

                    descripcion = st.text_area(
                        "Descripción",
                        key="orden_int_descripcion"
                    )
                
                    area = st.selectbox(
                        "Área",
                        AREAS,
                        key="orden_int_area"
                    )
                
                    tipo_ot_manual = st.selectbox(
                        "Tipo OT",
                        ["Normal", "☀️ Verano"],
                        key="tipo_ot_manual"
                    )
                
                    if tipo_ot_manual == "☀️ Verano":
                        st.session_state["origen_ot_manual"] = "VERANO"
                    else:
                        st.session_state["origen_ot_manual"] = "APP"
                
                    prioridad = st.selectbox(
                        "Prioridad",
                        ["Baja", "Media", "Alta"],
                        key="orden_int_prioridad"
                    )
                    fotos_ot = st.file_uploader(
                        "📷 Fotos incidencia",
                        type=["jpg", "jpeg", "png"],
                        accept_multiple_files=True,
                        key="orden_int_fotos"
                    )
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
                                st.session_state.get("origen_ot_manual", "APP"),
                                "",
                                "",
                                "postgres_fotos",
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
                            if fotos_ot:

                                try:
                            
                                    for i, foto in enumerate(fotos_ot, start=1):
                            
                                        foto_bytes = foto.read()
                            
                                        nombre_foto = f"{numero}_{i}_{foto.name}"
                            
                                        guardar_foto_ot(
                                            numero_ot=numero,
                                            nombre_foto=nombre_foto,
                                            foto_data=foto_bytes
                                        )
                            
                                except Exception as e:
                                    st.error(f"Error guardando fotos: {e}")
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

                espacios_disponibles_ext = obtener_espacios(edificio_ext, centro_ext)

                espacio_sel_ext = st.selectbox(
                    "Espacio",
                    espacios_disponibles_ext,
                    key=f"orden_ext_espacio_{edificio_ext}"
                )

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
                    [
                        "Todos",
                        "LEGIONELLA",
                        "OUTLOOK",
                        "APP",
                        "EXTERNA",
                        "PREVENTIVO",
                        "PROFESORES",
                        "VERANO"
                    ],
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
                        
                    # =====================================================
                    # CHECKLIST CORRECTIVO LEGIONELLA
                    # =====================================================
                    
                    if "CORRECTIVO LEGIONELLA" in str(descripcion or "").upper():
                    
                        st.markdown("### 🧪 Checklist correctivo Legionella")
                    
                        checklist = obtener_checklist_correctivo_legionella(numero_ot)
                    
                        revisar_consigna = st.checkbox(
                            "Revisar consigna acumulador",
                            value=bool(checklist.get("revisar_consigna", 0)) if checklist else False,
                            key=f"leg_consigna_{numero_ot}"
                        )
                    
                        revisar_termostato = st.checkbox(
                            "Revisar termostato",
                            value=bool(checklist.get("revisar_termostato", 0)) if checklist else False,
                            key=f"leg_termostato_{numero_ot}"
                        )
                    
                        revisar_caldera = st.checkbox(
                            "Revisar caldera",
                            value=bool(checklist.get("revisar_caldera", 0)) if checklist else False,
                            key=f"leg_caldera_{numero_ot}"
                        )
                    
                        revisar_resistencia = st.checkbox(
                            "Revisar resistencia eléctrica",
                            value=bool(checklist.get("revisar_resistencia", 0)) if checklist else False,
                            key=f"leg_resistencia_{numero_ot}"
                        )
                    
                        revisar_recirculacion = st.checkbox(
                            "Revisar recirculación",
                            value=bool(checklist.get("revisar_recirculacion", 0)) if checklist else False,
                            key=f"leg_recirculacion_{numero_ot}"
                        )
                    
                        revisar_bomba = st.checkbox(
                            "Revisar bomba retorno",
                            value=bool(checklist.get("revisar_bomba", 0)) if checklist else False,
                            key=f"leg_bomba_{numero_ot}"
                        )
                    
                        purgar_aire = st.checkbox(
                            "Purgar aire circuito",
                            value=bool(checklist.get("purgar_aire", 0)) if checklist else False,
                            key=f"leg_aire_{numero_ot}"
                        )
                    
                        esperar_recuperacion = st.checkbox(
                            "Esperar recuperación térmica",
                            value=bool(checklist.get("esperar_recuperacion", 0)) if checklist else False,
                            key=f"leg_recuperacion_{numero_ot}"
                        )
                    
                        nueva_medicion = st.checkbox(
                            "Realizar nueva medición",
                            value=bool(checklist.get("nueva_medicion", 0)) if checklist else False,
                            key=f"leg_medicion_{numero_ot}"
                        )
                    
                        causa_detectada = st.selectbox(
                            "Causa detectada",
                            [
                                "",
                                "Consigna incorrecta",
                                "Termostato",
                                "Caldera",
                                "Resistencia",
                                "Recirculación / bomba",
                                "Aire en circuito",
                                "Empresa externa pendiente",
                                "Otra"
                            ],
                            key=f"leg_causa_{numero_ot}"
                        )
                    
                        temperatura_final = st.number_input(
                            "Temperatura final ºC",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(checklist.get("temperatura_final", 0) or 0) if checklist else 0.0,
                            step=0.1,
                            key=f"leg_temp_{numero_ot}"
                        )
                    
                        empresa_externa_leg = st.text_input(
                            "Empresa externa / técnico",
                            value=str(checklist.get("empresa_externa", "") if checklist else ""),
                            key=f"leg_empresa_{numero_ot}"
                        )
                    
                        observaciones_leg = st.text_area(
                            "Observaciones correctivo",
                            value=str(checklist.get("observaciones", "") if checklist else ""),
                            key=f"leg_obs_{numero_ot}"
                        )
                    
                        col_leg1, col_leg2 = st.columns(2)
                    
                        with col_leg1:
                            if st.button(f"💾 Guardar checklist {numero_ot}", key=f"guardar_leg_{numero_ot}"):
                    
                                guardar_checklist_correctivo_legionella(
                                    numero_ot,
                                    centro,
                                    edificio,
                                    espacio,
                                    descripcion,
                                    {
                                        "revisar_consigna": 1 if revisar_consigna else 0,
                                        "revisar_termostato": 1 if revisar_termostato else 0,
                                        "revisar_caldera": 1 if revisar_caldera else 0,
                                        "revisar_resistencia": 1 if revisar_resistencia else 0,
                                        "revisar_recirculacion": 1 if revisar_recirculacion else 0,
                                        "revisar_bomba": 1 if revisar_bomba else 0,
                                        "purgar_aire": 1 if purgar_aire else 0,
                                        "esperar_recuperacion": 1 if esperar_recuperacion else 0,
                                        "nueva_medicion": 1 if nueva_medicion else 0,
                                        "causa_detectada": causa_detectada,
                                        "temperatura_final": temperatura_final,
                                        "empresa_externa": empresa_externa_leg,
                                        "observaciones": observaciones_leg,
                                    }
                                )
                    
                                st.success("Checklist Legionella guardado")

                        with col_leg2:
                            if st.button(f"🗑️ Reset checklist {numero_ot}", key=f"reset_leg_{numero_ot}"):
                        
                                borrar_checklist_correctivo_legionella(numero_ot)
                        
                                st.warning("Checklist reiniciado")
                                st.rerun()               

                    if solicitante:
                        st.caption(f"Solicitante: {solicitante}")

                    if fecha_origen:
                        st.caption(f"Fecha origen: {fecha_origen}")
                    clave_editor_ubicacion = (
                        "ot_editor_ubicacion_activa"
                    )

                    if (
                        st.session_state.get(
                            clave_editor_ubicacion
                        )
                        == id_orden
                    ):
                        if st.button(
                            "❌ Cerrar corrección",
                            key=f"cerrar_editor_ubicacion_{id_orden}",
                        ):
                            st.session_state.pop(
                                clave_editor_ubicacion,
                                None,
                            )
                            st.rerun()

                        mostrar_editor_ubicacion_ot_admin(
                            id_orden=id_orden,
                            numero_ot=numero_ot,
                            centro_actual=centro,
                            edificio_actual=edificio,
                            espacio_actual=espacio,
                        )

                    else:
                        if st.button(
                            "✏️ Corregir ubicación",
                            key=f"abrir_editor_ubicacion_{id_orden}",
                        ):
                            st.session_state[
                                clave_editor_ubicacion
                            ] = id_orden

                            st.rerun()
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
                                    descripcion_txt = str(descripcion or "")
                                
                                    if "CORRECTIVO LEGIONELLA" in descripcion_txt.upper():
                                        checklist_leg = obtener_checklist_correctivo_legionella(numero_ot)
                                
                                        if checklist_leg is None:
                                            st.error("No puedes finalizar esta OT correctiva de Legionella hasta completar y guardar el checklist.")
                                            st.stop()
                                
                                        tiene_revision = any([
                                            int(checklist_leg.get("revisar_consigna") or 0) == 1,
                                            int(checklist_leg.get("revisar_termostato") or 0) == 1,
                                            int(checklist_leg.get("revisar_caldera") or 0) == 1,
                                            int(checklist_leg.get("revisar_resistencia") or 0) == 1,
                                            int(checklist_leg.get("revisar_recirculacion") or 0) == 1,
                                            int(checklist_leg.get("revisar_bomba") or 0) == 1,
                                            int(checklist_leg.get("purgar_aire") or 0) == 1,
                                            int(checklist_leg.get("esperar_recuperacion") or 0) == 1,
                                        ])
                                
                                        causa = str(checklist_leg.get("causa_detectada") or "").strip()
                                        nueva_medicion = int(checklist_leg.get("nueva_medicion") or 0) == 1
                                        temperatura_final = float(checklist_leg.get("temperatura_final") or 0)
                                
                                        if not tiene_revision:
                                            st.error("Marca al menos una revisión realizada antes de finalizar.")
                                            st.stop()
                                
                                        if not causa:
                                            st.error("Indica la causa detectada antes de finalizar.")
                                            st.stop()
                                
                                        if not nueva_medicion:
                                            st.error("Debes marcar 'Realizar nueva medición' antes de finalizar.")
                                            st.stop()
                                
                                        if temperatura_final < 50:
                                            st.error("No puedes finalizar. La temperatura final sigue siendo inferior a 50 ºC.")
                                            st.stop()
                                
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
        st.markdown("### 🔎 Buscar en histórico")

        busqueda_historico = st.text_input(
            "Buscar por nº OT, descripción, centro, edificio, espacio, operario, origen o solicitante",
            key="buscar_historico_ot"
        )

        if busqueda_historico:
            texto = busqueda_historico.strip().lower()

            historico = [
                h for h in historico
                if texto in " ".join([str(campo or "") for campo in h]).lower()
            ]

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

                        
                        try:

                            fotos_db = obtener_fotos_ot(numero_ot)
                        
                            if fotos_db:
                        
                                with st.expander("📷 Ver fotos"):
                        
                                    cols_fotos = st.columns(3)
                        
                                    for i, (nombre_foto, foto_data) in enumerate(fotos_db):
                        
                                        with cols_fotos[i % 3]:
                        
                                            try:
                                                st.image(
                                                    bytes(foto_data),
                                                    caption=f"Foto {i + 1}",
                                                    use_container_width=True
                                                )
                        
                                            except Exception:
                                                st.caption("📷 Foto no disponible")
                        
                            elif foto:
                        
                                with st.expander("📷 Ver foto"):
                                    st.image(foto, use_container_width=True)
                        
                        except Exception as e:
                            st.caption(f"📷 Error fotos histórico: {e}")

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
