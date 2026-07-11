import streamlit as st
from datetime import date
from pathlib import Path
from ui.ui_trabajar_ot import pantalla_trabajar_ot

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


def cargar_ordenes_activas_operario(operario_sel):
    """
    Consulta únicamente las órdenes del operario y devuelve las activas.
    No carga fotos, materiales, checklists ni controles asociados.
    """
    ordenes_operario = obtener_ordenes_operario(operario_sel)

    ordenes_operario = filtrar_seguridad_operario(
        ordenes_operario,
        operario_sel
    )

    return [
        o for o in ordenes_operario
        if len(o) > 3
        and str(o[3] or "").strip()
        in [
            "Abierta",
            "En curso",
            "Pendiente material"
        ]
    ]


def buscar_ot_operario_por_id(ordenes, id_ot):
    """Localiza una única OT por su ID dentro de las órdenes permitidas."""
    if id_ot is None:
        return None

    for fila in ordenes or []:
        try:
            if int(fila[0]) == int(id_ot):
                return fila
        except (TypeError, ValueError, IndexError):
            continue

    return None


def filtrar_ordenes_activas_operario(ordenes_activas, filtro):
    """Aplica los filtros del listado sin cargar el detalle de las OT."""
    if filtro == "Preventivo":
        return [
            o for o in ordenes_activas
            if len(o) > 11
            and str(o[11] or "").strip().upper() == "PREVENTIVO"
        ]

    if filtro == "Legionella":
        return [
            o for o in ordenes_activas
            if len(o) > 11
            and str(o[11] or "").strip().upper() == "LEGIONELLA"
        ]

    if filtro == "☀️ Verano":
        return [
            o for o in ordenes_activas
            if len(o) > 11
            and str(o[11] or "").strip().upper() == "VERANO"
        ]

    if filtro == "Incidencias":
        return [
            o for o in ordenes_activas
            if len(o) > 11
            and str(o[11] or "").strip().upper()
            in [
                "APP",
                "OUTLOOK",
                "PROFESORES"
            ]
        ]

    return ordenes_activas


def mostrar_resumen_ot_operario(fila):
    """
    Muestra una fila ligera de la OT.
    No llama a mostrar_tarjeta_ot ni prepara controles internos.
    """
    try:
        id_ot = fila[0]
        numero_ot = fila[1]
        descripcion = fila[2]
        estado = fila[3]
        centro_ot = fila[5]
        edificio_ot = fila[6]
        espacio_ot = fila[7]
        prioridad_ot = fila[9]
        origen_ot = fila[11] if len(fila) > 11 else ""
    except (TypeError, IndexError):
        return

    estado_txt = str(estado or "").strip()
    prioridad_txt = str(prioridad_ot or "").strip()
    origen_txt = str(origen_ot or "").strip()

    icono_estado = {
        "Abierta": "🔴",
        "En curso": "🟠",
        "Pendiente material": "📦",
    }.get(estado_txt, "⚪")

    icono_prioridad = {
        "Urgente": "🚨",
        "Alta": "🔴",
        "Media": "🟠",
        "Baja": "🟢",
    }.get(prioridad_txt, "⚪")

    descripcion_corta = (
        str(descripcion or "")
        .replace("\n", " ")
        .strip()
    )

    if len(descripcion_corta) > 120:
        descripcion_corta = descripcion_corta[:120].rstrip() + "..."

    with st.container(border=True):
        st.markdown(
            f"### {icono_estado} {numero_ot or '-'}"
        )

        st.markdown(
            f"{icono_prioridad} **{prioridad_txt or '-'}** · "
            f"{estado_txt or '-'}"
        )

        st.caption(
            f"🏢 {centro_ot or '-'} · "
            f"{edificio_ot or '-'} · "
            f"{espacio_ot or '-'}"
        )

        if origen_txt:
            st.caption(f"Origen: {origen_txt}")

        st.markdown(descripcion_corta or "Sin descripción.")

        if st.button(
            "🔎 Abrir y trabajar esta OT",
            key=f"abrir_ot_operario_{id_ot}",
            use_container_width=True
        ):
            try:
                st.session_state["operario_ot_abierta_id"] = int(id_ot)
            except (TypeError, ValueError):
                st.error("No se ha podido abrir esta orden.")
            else:
                st.rerun()


def pantalla_listado_ordenes_operario(operario_sel, ordenes_activas):
    """Pantalla ligera: filtros, paginación y resúmenes de OT."""
    st.markdown("## 📋 Mis órdenes")

    filtro_origen_operario = st.radio(
        "",
        [
            "Todas",
            "Incidencias",
            "Preventivo",
            "Legionella",
            "☀️ Verano"
        ],
        horizontal=True,
        key="filtro_origen_operario"
    )

    ordenes_filtradas = filtrar_ordenes_activas_operario(
        ordenes_activas,
        filtro_origen_operario
    )

    if not ordenes_filtradas:
        st.success("No tienes órdenes pendientes en este filtro.")
        return

    elementos_por_pagina = 15
    total_ordenes = len(ordenes_filtradas)

    total_paginas = max(
        1,
        (total_ordenes + elementos_por_pagina - 1)
        // elementos_por_pagina
    )

    pagina_guardada = int(
        st.session_state.get("pagina_ordenes_operario", 1) or 1
    )

    if pagina_guardada > total_paginas:
        st.session_state["pagina_ordenes_operario"] = total_paginas

    if total_paginas > 1:
        pagina = st.number_input(
            "Página de órdenes",
            min_value=1,
            max_value=total_paginas,
            value=min(pagina_guardada, total_paginas),
            step=1,
            key="pagina_ordenes_operario"
        )
    else:
        pagina = 1

    inicio = (int(pagina) - 1) * elementos_por_pagina
    fin = inicio + elementos_por_pagina
    ordenes_pagina = ordenes_filtradas[inicio:fin]

    st.caption(
        f"Mostrando {inicio + 1}–"
        f"{min(fin, total_ordenes)} "
        f"de {total_ordenes} órdenes."
    )

    for fila in ordenes_pagina:
        mostrar_resumen_ot_operario(fila)


def pantalla_trabajar_ot_operario(operario_sel, ordenes_activas):
    """
    Pantalla de detalle: carga y construye una sola OT completa.
    Toda la lógica existente continúa dentro de mostrar_tarjeta_ot().
    """
    id_ot_abierta = st.session_state.get("operario_ot_abierta_id")

    fila_abierta = buscar_ot_operario_por_id(
        ordenes_activas,
        id_ot_abierta
    )

    if fila_abierta is None:
        st.session_state.pop("operario_ot_abierta_id", None)
        st.warning(
            "La OT seleccionada ya no está disponible o ya ha sido finalizada."
        )

        if st.button(
            "⬅ Volver al listado de órdenes",
            key="volver_listado_ot_no_disponible",
            use_container_width=True
        ):
            st.rerun()

        return

    try:
        numero_ot = fila_abierta[1]
    except Exception:
        numero_ot = ""

    pantalla_trabajar_ot(
        fila=fila_abierta,
        operario_sel=operario_sel,
        modo="operario",
        clave_ot_abierta="operario_ot_abierta_id",
        texto_volver="⬅ Volver al listado de órdenes",
        key_boton_volver="volver_listado_ordenes_operario",
        titulo=f"## 🛠️ Trabajar OT {numero_ot or ''}",
    )


def pantalla_operario(modo="ordenes"):
    solo_historico = str(modo or "").strip().lower() == "historico"

    # Al entrar en histórico nunca se conserva una OT abierta.
    if solo_historico:
        st.session_state.pop("operario_ot_abierta_id", None)
        st.title("📁 Mi histórico")
    else:
        st.title("👷 Operario")

    # =====================================================
    # VOLVER A ADMINISTRACIÓN
    # =====================================================
    if st.session_state.get("vista_operario", False):
        if st.button(
            "🔙 Volver a administración",
            key="volver_admin_pantalla_operario"
        ):
            st.session_state["vista_operario"] = False
            st.session_state.pop("operario_ot_abierta_id", None)
            st.rerun()

    # =====================================================
    # OPERARIO ACTUAL
    # =====================================================
    operario_sel = str(
        st.session_state.get("operario_activo", "")
        or ""
    ).strip()

    if es_operario():
        operario_sel = str(
            nombre_operario_actual()
            or ""
        ).strip()

        st.session_state["operario_activo"] = operario_sel

    if not operario_sel:
        st.warning("No hay operario seleccionado.")
        return

    st.info(f"Operario: {operario_sel}")

    # =====================================================
    # MODO ÓRDENES
    # Listado ligero o una única OT abierta
    # =====================================================
    if not solo_historico:
        id_ot_abierta = st.session_state.get(
            "operario_ot_abierta_id"
        )

        # Legionella se ofrece únicamente desde el listado.
        # Al trabajar una OT no se construyen otras pantallas.
        if (
            id_ot_abierta is None
            and puede_ver_legionella_operario(operario_sel)
        ):
            zona_operario = st.radio(
                "Zona de trabajo",
                [
                    "📋 Mis órdenes",
                    "💧 Control Legionella"
                ],
                horizontal=True,
                key="zona_operario_legionella"
            )

            if zona_operario == "💧 Control Legionella":
                try:
                    from ui.ui_legionella import pantalla_legionella
                    pantalla_legionella()

                except Exception as e:
                    st.error(
                        "No se ha podido abrir el módulo de Legionella."
                    )
                    st.exception(e)

                return

        try:
            ordenes_activas = cargar_ordenes_activas_operario(
                operario_sel
            )
        except Exception as e:
            st.error(
                "No se han podido cargar las órdenes del operario."
            )
            st.caption(str(e))
            return

        if id_ot_abierta is not None:
            pantalla_trabajar_ot_operario(
                operario_sel,
                ordenes_activas
            )
            return

        pantalla_listado_ordenes_operario(
            operario_sel,
            ordenes_activas
        )
        return

    # =====================================================
    # MODO HISTÓRICO
    # No consulta ni renderiza órdenes activas
    # =====================================================
    try:
        historico = obtener_historico()
    except Exception as e:
        st.error(
            "No se ha podido cargar el histórico."
        )
        st.caption(str(e))
        return

    operario_normalizado = normalizar_operario_nombre(
        operario_sel
    )

    historico_operario = [
        h for h in historico
        if len(h) > 10
        and normalizar_operario_nombre(h[10])
        == operario_normalizado
    ]

    if not historico_operario:
        st.info("No hay trabajos finalizados todavía.")
        return

    # Orden más reciente primero
    historico_operario = list(
        reversed(historico_operario)
    )

    # =====================================================
    # PAGINACIÓN DEL HISTÓRICO
    # =====================================================
    historicos_por_pagina = 15
    total_historicos = len(historico_operario)

    total_paginas_hist = max(
        1,
        (
            total_historicos
            + historicos_por_pagina
            - 1
        ) // historicos_por_pagina
    )

    if total_paginas_hist > 1:
        pagina_hist = st.number_input(
            "Página del histórico",
            min_value=1,
            max_value=total_paginas_hist,
            value=1,
            step=1,
            key="pagina_historico_operario"
        )
    else:
        pagina_hist = 1

    inicio_hist = (
        int(pagina_hist) - 1
    ) * historicos_por_pagina

    fin_hist = inicio_hist + historicos_por_pagina

    historico_pagina = historico_operario[
        inicio_hist:fin_hist
    ]

    st.caption(
        f"Mostrando {inicio_hist + 1}–"
        f"{min(fin_hist, total_historicos)} "
        f"de {total_historicos} trabajos finalizados."
    )

    # =====================================================
    # LISTADO DEL HISTÓRICO
    # =====================================================
    for h in historico_pagina:
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
            f"✅ {num_ot_hist or '-'} | "
            f"{centro_hist or '-'} · "
            f"{espacio_hist or '-'}"
        )

        with st.expander(
            titulo_hist,
            expanded=False
        ):
            st.markdown(
                f"### ✅ {num_ot_hist or '-'}"
            )

            st.markdown(
                desc_hist or "Sin descripción."
            )

            st.caption(
                f"🏢 {centro_hist or '-'} · "
                f"{edificio_hist or '-'} · "
                f"{espacio_hist or '-'}"
            )

            st.caption(
                f"📅 Cierre: "
                f"{fecha_cierre_hist or fecha_hist or '-'}"
            )

            if observaciones_cierre_hist:
                st.info(
                    f"📝 {observaciones_cierre_hist}"
                )

            # ---------------------------------------------
            # LAS FOTOS NO SE CONSULTAN AUTOMÁTICAMENTE
            # Solo al pulsar el botón
            # ---------------------------------------------
            key_fotos = (
                f"mostrar_fotos_hist_"
                f"{id_hist}_{num_ot_hist}"
            )

            if not st.session_state.get(
                key_fotos,
                False
            ):
                if st.button(
                    "📷 Ver fotos",
                    key=(
                        f"btn_ver_fotos_hist_"
                        f"{id_hist}_{num_ot_hist}"
                    ),
                    use_container_width=True
                ):
                    st.session_state[key_fotos] = True
                    st.rerun()

            else:
                if st.button(
                    "🙈 Ocultar fotos",
                    key=(
                        f"btn_ocultar_fotos_hist_"
                        f"{id_hist}_{num_ot_hist}"
                    ),
                    use_container_width=True
                ):
                    st.session_state[key_fotos] = False
                    st.rerun()

                try:
                    fotos_db = obtener_fotos_ot(
                        num_ot_hist
                    )

                    if fotos_db:
                        cols_fotos = st.columns(3)

                        for i, (
                            nombre_foto,
                            foto_data
                        ) in enumerate(fotos_db):

                            with cols_fotos[i % 3]:
                                st.image(
                                    bytes(foto_data),
                                    caption=(
                                        nombre_foto
                                        or f"Foto {i + 1}"
                                    ),
                                    use_container_width=True
                                )

                    elif foto_hist:
                        fotos = [
                            ruta.strip()
                            for ruta in str(
                                foto_hist
                            ).split("|")
                            if ruta.strip()
                        ]

                        if fotos:
                            cols_fotos = st.columns(3)

                            for i, ruta_foto in enumerate(
                                fotos
                            ):
                                with cols_fotos[i % 3]:
                                    try:
                                        st.image(
                                            ruta_foto,
                                            caption=(
                                                f"Foto {i + 1}"
                                            ),
                                            use_container_width=True
                                        )

                                    except Exception:
                                        st.caption(
                                            "📷 Foto no disponible."
                                        )

                        else:
                            st.info(
                                "Esta OT no tiene fotos."
                            )

                    else:
                        st.info(
                            "Esta OT no tiene fotos."
                        )

                except Exception as e:
                    st.caption(
                        f"📷 No se pudieron cargar "
                        f"las fotos: {e}"
                    )

# =====================================================
# COMPATIBILIDAD CON APP.PY
# Mantiene el nombre anterior esperado por la aplicación
# =====================================================
def pantalla_operario_prueba(modo="ordenes"):
    return pantalla_operario(modo=modo)
