import streamlit as st
from datetime import date
from pathlib import Path
from ui.ui_ot import mostrar_tarjeta_ot

from modules.ordenes import (
    obtener_ordenes_operario,
    obtener_historico,
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    obtener_fotos_ot,
    guardar_foto_ot,
    crear_correctiva_desde_ot
)

from modules.inventario import (
    obtener_materiales_para_select,
    obtener_material_por_codigo,
    registrar_movimiento_inventario
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
    crear_checklist_preventivo,
)

from ui.ui_ot_controles import (
    mostrar_ejecucion_legionella_operario,
    mostrar_checklist_preventivo_operario,
    mostrar_checklist_correctivo_legionella_operario,
)

from ui.ui_legionella import obtener_checklist_correctivo_legionella


def rol_actual():
    return str(st.session_state.get("rol", "")).strip().lower()


def usuario_actual():
    return str(st.session_state.get("usuario", "")).strip()


def nombre_operario_actual():
    return str(
        st.session_state.get("operario_activo")
        or st.session_state.get("nombre")
        or usuario_actual()
    ).strip()


def es_admin():
    return rol_actual() == "admin"


def es_gerencia():
    return rol_actual() == "gerencia"


def es_operario():
    return rol_actual() == "operario"


def normalizar_txt(valor):
    return str(valor or "").strip().lower()


def normalizar_operario_nombre(nombre):
    texto = normalizar_txt(nombre)
    limpio = (
        texto.replace(".", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )

    if limpio in [
        "jaalmeda",
        "jalmeda",
        "juanantonio",
        "juanantonioalmeda",
        "jalmedac",
        "jalmedaabatolibaedu"
    ]:
        return "j.a. almeda"

    if limpio in [
        "luislozano",
        "llozano",
        "luis"
    ]:
        return "luis lozano"

    if limpio in [
        "abelvasquez",
        "abel",
        "avasquez"
    ]:
        return "abel vasquez"

    return texto


def puede_ver_legionella_operario(operario):
    operario_txt = normalizar_txt(operario)
    operario_txt = operario_txt.replace(".", "")
    operario_txt = operario_txt.replace(" ", "")
    operario_txt = operario_txt.replace("-", "")
    operario_txt = operario_txt.replace("_", "")

    return (
        "almeda" in operario_txt
        or operario_txt in ["ja", "jalmeda", "jaalmeda", "juanantonio"]
    )


def obtener_operario_fila(fila):
    try:
        return fila[10]
    except Exception:
        return ""


def es_ot_preventiva(origen, descripcion):
    origen_txt = str(origen or "").strip().upper()
    desc_txt = str(descripcion or "").strip().upper()
    return origen_txt == "PREVENTIVO" or desc_txt.startswith("[PREVENTIVO]")


def es_ot_legionella(area, origen, descripcion):
    area_txt = normalizar_txt(area)
    origen_txt = normalizar_txt(origen)
    desc_txt = normalizar_txt(descripcion)

    return (
        area_txt == "legionella"
        or origen_txt == "legionella"
        or desc_txt.startswith("control legionella")
        or desc_txt.startswith("correctivo legionella")
        or "correctivo legionella" in desc_txt
    )


def limpiar_tarea_preventiva(descripcion):
    texto = str(descripcion or "").strip()
    return texto.replace("[PREVENTIVO]", "").strip()


def normalizar_estado_operario(estado):
    estado = str(estado or "").strip().lower()

    if estado in ["finalizada", "finalizado", "cerrada", "cerrado"]:
        return "Hechas"

    if estado in ["en curso", "en proceso"]:
        return "En proceso"

    if estado in ["abierta", "pendiente", "pendiente material", "esperando material"]:
        return "Faltan"

    return "Faltan"


def fecha_es_hoy(valor):
    hoy = date.today().strftime("%Y-%m-%d")
    texto = str(valor or "").strip()
    return texto[:10] == hoy


def calcular_kpis_operario(ordenes, historico=None, operario_sel=""):
    historico = historico or []

    total = len(ordenes)

    en_proceso = len([
        o for o in ordenes
        if len(o) > 3 and str(o[3] or "").strip() == "En curso"
    ])

    faltan = len([
        o for o in ordenes
        if len(o) > 3 and str(o[3] or "").strip() in ["Abierta", "Pendiente material"]
    ])

    hechas_hoy = 0
    operario_objetivo = normalizar_operario_nombre(operario_sel)

    for h in historico:
        try:
            fecha_cierre_hist = h[14]
            operario_hist = h[10]
        except Exception:
            continue

        if normalizar_operario_nombre(operario_hist) != operario_objetivo:
            continue

        if fecha_es_hoy(fecha_cierre_hist):
            hechas_hoy += 1

    base_rendimiento = hechas_hoy + en_proceso + faltan
    rendimiento = round((hechas_hoy / base_rendimiento) * 100, 1) if base_rendimiento else 0

    return {
        "total": total,
        "hechas": hechas_hoy,
        "en_proceso": en_proceso,
        "faltan": faltan,
        "rendimiento": rendimiento,
    }


def descomponer_orden_operario(fila):
    observaciones_estado = ""

    if len(fila) >= 26:
        (
            id_orden,
            num_ot,
            desc,
            est,
            fecha,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            fecha_origen,
            foto,
            tipo_solicitante,
            tipo_orden,
            empresa_externa,
            contacto_empresa,
            telefono_empresa,
            email_empresa,
            fecha_programada,
            fecha_realizacion,
            coste_estimado,
            coste_final,
            observaciones_estado,
        ) = fila[:26]

    elif len(fila) >= 16:
        (
            id_orden,
            num_ot,
            desc,
            est,
            fecha,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            fecha_origen,
            foto,
            tipo_solicitante,
        ) = fila[:16]

    elif len(fila) == 15:
        (
            id_orden,
            num_ot,
            desc,
            est,
            fecha,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            fecha_origen,
            foto,
        ) = fila
        tipo_solicitante = "Operarios"

    else:
        (
            id_orden,
            num_ot,
            desc,
            est,
            fecha,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen
        ) = fila[:12]
        solicitante = ""
        fecha_origen = ""
        foto = ""
        tipo_solicitante = "Operarios"

    return (
        id_orden,
        num_ot,
        desc,
        est,
        fecha,
        centro,
        edificio,
        espacio,
        area,
        prioridad,
        operario,
        origen,
        solicitante,
        fecha_origen,
        foto,
        tipo_solicitante,
        observaciones_estado,
    )


def puede_finalizar_preventivo(num_ot, origen, desc):
    if es_ot_preventiva(origen, desc):
        return checklist_preventivo_completo(num_ot)
    return True


def puede_finalizar_legionella(id_orden, area, origen, desc, num_ot=None):
    desc_txt = str(desc or "").upper()

    if "CORRECTIVO LEGIONELLA" in desc_txt:
        checklist = obtener_checklist_correctivo_legionella(num_ot)

        if not checklist:
            return False

        causa = str(checklist.get("causa_detectada") or "").strip()

        return (
            causa != ""
            and bool(checklist.get("nueva_medicion", 0))
            and float(checklist.get("temperatura_final", 0) or 0) >= 50
        )

    if es_ot_legionella(area, origen, desc):
        return st.session_state.get(f"legionella_guardada_{id_orden}", False)

    return True


def mostrar_crear_correctiva_desde_revision(
    id_orden,
    num_ot,
    centro,
    edificio,
    espacio,
    area,
    prioridad,
    operario,
    origen_base
):
    st.markdown("### 🛠️ Crear correctivas si hay defectos")

    st.info(
        "Escribe un defecto por línea. "
        "Se creará una OT correctiva independiente por cada línea."
    )

    defectos_texto = st.text_area(
        "Defectos encontrados",
        placeholder=(
            "Ejemplo:\n"
            "P0/ACS01 - Grifo cocina pierde agua\n"
            "P0/ACS02 - Grifo cocina sin caudal\n"
            "Luz emergencia pasillo sin batería"
        ),
        key=f"defectos_correctivas_{id_orden}",
        height=150
    )

    crear_correctivas = st.checkbox(
        "Crear OT correctivas automáticas",
        key=f"crear_correctivas_auto_{id_orden}"
    )

    if st.button(
        "➕ Crear correctivas",
        key=f"btn_crear_correctivas_{id_orden}",
        use_container_width=True
    ):
        if not crear_correctivas:
            st.warning("Marca la casilla para crear las OT correctivas.")
            return False

        defectos = [
            d.strip()
            for d in str(defectos_texto or "").splitlines()
            if d.strip()
        ]

        if not defectos:
            st.warning("Escribe al menos un defecto.")
            return False

        creadas = 0
        errores = []

        for defecto in defectos:
            ok, mensaje = crear_correctiva_desde_ot(
                centro=centro,
                edificio=edificio,
                espacio=espacio,
                area=area,
                prioridad=prioridad,
                operario=operario,
                descripcion_defecto=defecto,
                numero_ot_origen=num_ot,
                origen=origen_base,
                solicitante="Operarios",
            )

            if ok:
                creadas += 1
            else:
                errores.append(mensaje)

        if creadas > 0:
            st.success(f"Se han creado {creadas} OT correctivas independientes.")
            st.session_state[f"correctiva_creada_{id_orden}"] = True

        if errores:
            for error in errores:
                st.warning(error)

        st.rerun()

    if st.session_state.get(f"correctiva_creada_{id_orden}", False):
        st.success("Ya se han creado correctivas desde esta revisión.")

    return st.session_state.get(f"correctiva_creada_{id_orden}", False)


def filtrar_seguridad_operario(ordenes, operario_sel):
    if not ordenes:
        return []

    operario_objetivo = normalizar_operario_nombre(operario_sel)

    return [
        o for o in ordenes
        if len(o) > 10
        and normalizar_operario_nombre(o[10]) == operario_objetivo
    ]


def pantalla_operario():
    st.title("👷 Operario")

    if st.session_state.get("vista_operario", False):
        if st.button("🔙 Volver a administración"):
            st.session_state["vista_operario"] = False
            st.rerun()

    operario_sel = st.session_state.get("operario_activo", "")

    if es_operario():
        operario_sel = nombre_operario_actual()
        st.session_state["operario_activo"] = operario_sel

    if not operario_sel:
        st.warning("No hay operario seleccionado.")
        return

    st.info(f"Operario: {operario_sel}")

    if puede_ver_legionella_operario(operario_sel):
        zona_operario = st.radio(
            "Zona de trabajo",
            ["📋 Mis órdenes", "💧 Control Legionella"],
            horizontal=True,
            key="zona_operario_legionella"
        )

        if zona_operario == "💧 Control Legionella":
            try:
                from ui.ui_legionella import pantalla_legionella
                pantalla_legionella()
            except Exception as e:
                st.error("No se ha podido abrir el módulo de Legionella.")
                st.exception(e)
            return

    ordenes_operario = obtener_ordenes_operario(operario_sel.strip())
    ordenes_operario = filtrar_seguridad_operario(ordenes_operario, operario_sel)

    try:
        historico = obtener_historico()
    except Exception:
        historico = []

    kpis = calcular_kpis_operario(
        ordenes_operario,
        historico=historico,
        operario_sel=operario_sel
    )

    materiales_select = obtener_materiales_para_select()

    ordenes_operario = [
        o for o in ordenes_operario
        if o[3] in ["Abierta", "En curso", "Pendiente material"]
    ]
    
    st.markdown("## 📋 Mis órdenes")
    
    filtro_origen_operario = st.radio(
        "",
        ["Todas", "Incidencias", "Preventivo", "Legionella", "☀️ Verano"],
        horizontal=True,
        key="filtro_origen_operario"
    )

    if filtro_origen_operario == "Preventivo":
        ordenes_operario = [
            o for o in ordenes_operario
            if len(o) > 11 and str(o[11] or "").strip().upper() == "PREVENTIVO"
        ]

    elif filtro_origen_operario == "Legionella":
        ordenes_operario = [
            o for o in ordenes_operario
            if len(o) > 11 and str(o[11] or "").strip().upper() == "LEGIONELLA"
        ]

    elif filtro_origen_operario == "☀️ Verano":
        ordenes_operario = [
            o for o in ordenes_operario
            if len(o) > 11 and str(o[11] or "").strip().upper() == "VERANO"
        ]

    elif filtro_origen_operario == "Incidencias":
        ordenes_operario = [
            o for o in ordenes_operario
            if len(o) > 11 and str(o[11] or "").strip().upper() in ["APP", "OUTLOOK", "PROFESORES"]
        ]

    if not ordenes_operario:
        st.success("No tienes órdenes pendientes.")

    else:
        st.markdown("## 📋 Mis órdenes")

        for fila in ordenes_operario:
            mostrar_tarjeta_ot(
                fila=fila,
                materiales_select=materiales_select,
                operario_sel=operario_sel,
                modo="operario"
            )

    historico_operario = [
        h for h in historico
        if normalizar_operario_nombre(h[10])
        == normalizar_operario_nombre(operario_sel)
    ]

    st.markdown("---")

    with st.expander("📁 Mi histórico", expanded=False):

        if not historico_operario:
            st.info("No hay trabajos finalizados todavía.")

        else:
            for h in reversed(historico_operario[-50:]):

                try:
                    (
                        id_hist,
                        num_ot_hist,
                        desc_hist,
                        estado_hist,
                        fecha_hist,
                        centro_hist,
                        edificio_hist,
                        espacio_hist,
                        area_hist,
                        prioridad_hist,
                        operario_hist,
                        origen_hist,
                        solicitante_hist,
                        fecha_origen_hist,
                        fecha_cierre_hist,
                        observaciones_cierre_hist,
                        foto_hist,
                        *resto
                    ) = h

                except Exception:
                    continue

                titulo_hist = (
                    f"✅ {num_ot_hist} | "
                    f"{centro_hist or '-'} · {espacio_hist or '-'}"
                )

                with st.expander(titulo_hist, expanded=False):

                    st.markdown(f"### ✅ {num_ot_hist}")
                    st.markdown(desc_hist)

                    st.caption(
                        f"🏢 {centro_hist or '-'} · "
                        f"{edificio_hist or '-'} · "
                        f"{espacio_hist or '-'}"
                    )

                    st.caption(f"📅 Cierre: {fecha_cierre_hist or '-'}")

                    if observaciones_cierre_hist:
                        st.info(f"📝 {observaciones_cierre_hist}")

                    try:
                        fotos_db = obtener_fotos_ot(num_ot_hist)

                        if fotos_db:
                            cols_fotos = st.columns(3)

                            for i, (nombre_foto, foto_data) in enumerate(fotos_db):
                                with cols_fotos[i % 3]:
                                    st.image(
                                        bytes(foto_data),
                                        caption=f"Foto {i + 1}",
                                        use_container_width=True
                                    )

                        elif foto_hist:
                            fotos = str(foto_hist).split("|")
                            cols_fotos = st.columns(3)

                            for i, ruta_foto in enumerate(fotos):
                                ruta_foto = str(ruta_foto).strip()

                                if not ruta_foto:
                                    continue

                                with cols_fotos[i % 3]:
                                    try:
                                        st.image(
                                            ruta_foto,
                                            caption=f"Foto {i + 1}",
                                            use_container_width=True
                                        )

                                    except Exception as e:
                                        st.caption(f"📷 Foto no disponible: {e}")

                    except Exception as e:
                        st.caption(f"📷 Error fotos histórico: {e}")
