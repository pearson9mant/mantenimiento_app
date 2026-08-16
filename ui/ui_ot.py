import streamlit as st
from pathlib import Path

from modules.ordenes import (
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    obtener_fotos_ot,
    crear_correctiva_desde_ot,
)

from modules.inventario import (
    obtener_material_por_codigo,
    registrar_movimiento_inventario,
)

from modules.preventivo import checklist_preventivo_completo

from ui.ui_legionella import obtener_checklist_correctivo_legionella

from ui.ui_ot_controles import (
    mostrar_checklist_preventivo_operario,
    mostrar_ejecucion_legionella_operario,
    mostrar_checklist_correctivo_legionella_operario,
)

from database.db import conectar, _sql

from modules.espacios import (
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)


def normalizar_txt(valor):
    return str(valor or "").strip().lower()


def normalizar_operario_nombre(nombre):
    texto = normalizar_txt(nombre)
    limpio = texto.replace(".", "").replace(" ", "").replace("-", "").replace("_", "")

    if limpio in ["jaalmeda", "jalmeda", "juanantonio", "juanantonioalmeda"]:
        return "j.a. almeda"

    if limpio in ["luislozano", "llozano", "luis"]:
        return "luis lozano"

    if limpio in ["abelvasquez", "abel", "avasquez"]:
        return "abel vasquez"

    return texto


def rol_actual():
    return str(st.session_state.get("rol", "")).strip().lower()


def es_operario():
    return rol_actual() == "operario"


def nombre_operario_actual():
    return str(
        st.session_state.get("operario_activo")
        or st.session_state.get("nombre")
        or st.session_state.get("usuario")
        or ""
    ).strip()


def es_ot_preventiva(origen, descripcion, numero_ot=""):
    origen_txt = str(origen or "").strip().upper()
    desc_txt = str(descripcion or "").strip().upper()
    numero_txt = str(numero_ot or "").strip().upper()

    # Regla principal:
    # una OT preventiva real lleva numeración PREV.
    if numero_txt.startswith("PREV-"):
        return True

    # Una INC creada desde un preventivo conserva origen PREVENTIVO
    # para trazabilidad, pero sigue siendo una correctiva.
    if numero_txt.startswith("INC-"):
        return False

    # Compatibilidad con OT antiguas.
    return (
        origen_txt == "PREVENTIVO"
        or desc_txt.startswith("[PREVENTIVO]")
    )


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


def descomponer_orden_operario(fila):
    observaciones_estado = ""

    if len(fila) >= 26:
        (
            id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
            area, prioridad, operario, origen, solicitante, fecha_origen,
            foto, tipo_solicitante, tipo_orden, empresa_externa,
            contacto_empresa, telefono_empresa, email_empresa,
            fecha_programada, fecha_realizacion, coste_estimado,
            coste_final, observaciones_estado,
        ) = fila[:26]

    elif len(fila) >= 16:
        (
            id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
            area, prioridad, operario, origen, solicitante, fecha_origen,
            foto, tipo_solicitante,
        ) = fila[:16]

    elif len(fila) == 15:
        (
            id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
            area, prioridad, operario, origen, solicitante, fecha_origen, foto,
        ) = fila
        tipo_solicitante = "Operarios"

    else:
        (
            id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
            area, prioridad, operario, origen
        ) = fila[:12]
        solicitante = ""
        fecha_origen = ""
        foto = ""
        tipo_solicitante = "Operarios"

    return (
        id_orden, num_ot, desc, est, fecha, centro, edificio, espacio,
        area, prioridad, operario, origen, solicitante, fecha_origen,
        foto, tipo_solicitante, observaciones_estado,
    )


def puede_finalizar_preventivo(num_ot, origen, desc):
    if es_ot_preventiva(origen, desc, num_ot):
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
def puede_corregir_ubicacion():
    return rol_actual() in [
        "admin",
        "administrador",
        "administracion",
        "administración",
    ]


def obtener_ubicacion_ot(id_orden):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT centro, edificio, planta, espacio
            FROM ordenes_trabajo
            WHERE id = ?
        """), (id_orden,))

        fila = cur.fetchone()

        if not fila:
            return "", "", "", ""

        return (
            str(fila[0] or "").strip(),
            str(fila[1] or "").strip(),
            str(fila[2] or "").strip(),
            str(fila[3] or "").strip(),
        )

    except Exception:
        return "", "", "", ""

    finally:
        conn.close()


def guardar_ubicacion_ot(
    id_orden,
    centro,
    edificio,
    planta,
    espacio,
):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE ordenes_trabajo
            SET centro = ?,
                edificio = ?,
                planta = ?,
                espacio = ?
            WHERE id = ?
        """), (
            centro,
            edificio,
            planta,
            espacio,
            id_orden,
        ))

        conn.commit()
        return True, "Ubicación corregida correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo corregir la ubicación: {e}"

    finally:
        conn.close()


def indice_opcion(opciones, valor):
    valor = str(valor or "").strip()

    if valor in opciones:
        return opciones.index(valor)

    return 0


def mostrar_correccion_ubicacion_ot(id_orden, modo):
    if not puede_corregir_ubicacion():
        return

    centro_actual, edificio_actual, planta_actual, espacio_actual = (
        obtener_ubicacion_ot(id_orden)
    )

    with st.expander("✏️ Corregir ubicación", expanded=False):
        st.caption(
            "Solo cambia la ubicación de esta OT. "
            "No modifica el estado, fotos, observaciones ni materiales."
        )

        centros = obtener_centros_espacios()

        if not centros:
            st.warning("No hay centros en el catálogo de espacios.")
            return

        centro_sel = st.selectbox(
            "Centro",
            centros,
            index=indice_opcion(centros, centro_actual),
            key=f"{modo}_corregir_centro_{id_orden}",
        )

        edificios = obtener_edificios_espacios(centro_sel)

        if not edificios:
            st.warning("No hay edificios para este centro.")
            return

        edificio_sel = st.selectbox(
            "Edificio",
            edificios,
            index=indice_opcion(edificios, edificio_actual),
            key=f"{modo}_corregir_edificio_{id_orden}",
        )

        plantas = obtener_plantas_espacios(
            centro_sel,
            edificio_sel,
        )

        if not plantas:
            st.warning("No hay plantas para este edificio.")
            return

        planta_sel = st.selectbox(
            "Planta",
            plantas,
            index=indice_opcion(plantas, planta_actual),
            key=f"{modo}_corregir_planta_{id_orden}",
        )

        espacios_filas = obtener_espacios_por_planta(
            centro_sel,
            edificio_sel,
            planta_sel,
        )

        espacios = []

        for fila_espacio in espacios_filas:
            if isinstance(fila_espacio, dict):
                nombre = str(
                    fila_espacio.get("espacio")
                    or fila_espacio.get("nombre")
                    or ""
                ).strip()
            elif isinstance(fila_espacio, (list, tuple)):
                nombre = str(
                    fila_espacio[0] if fila_espacio else ""
                ).strip()
            else:
                nombre = str(fila_espacio or "").strip()

            if nombre and nombre not in espacios:
                espacios.append(nombre)

        if not espacios:
            st.warning("No hay espacios para esta planta.")
            return

        espacio_sel = st.selectbox(
            "Espacio",
            espacios,
            index=indice_opcion(espacios, espacio_actual),
            key=f"{modo}_corregir_espacio_{id_orden}",
        )

        st.info(
            f"📍 {centro_sel} · {edificio_sel} · "
            f"{planta_sel} · {espacio_sel}"
        )

        confirmar = st.checkbox(
            "Confirmo que quiero modificar la ubicación",
            key=f"{modo}_confirmirma_ubicacion_{id_orden}",
        )

        if st.button(
            "💾 Guardar ubicación",
            key=f"{modo}_guardar_ubicacion_{id_orden}",
            use_container_width=True,
            type="primary",
        ):
            if not confirmar:
                st.warning("Marca primero la confirmación.")
                return

            ok, mensaje = guardar_ubicacion_ot(
                id_orden=id_orden,
                centro=centro_sel,
                edificio=edificio_sel,
                planta=planta_sel,
                espacio=espacio_sel,
            )

            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)

# =====================================================
# SELECTOR INTELIGENTE DE MATERIALES
# =====================================================

CATEGORIAS_MATERIAL_POR_PREFIJO = {
    "FON": "Fontanería",
    "ELE": "Electricidad",
    "FER": "Ferretería",
    "CLI": "Climatización",
    "PIN": "Pintura",
    "LIM": "Limpieza",
    "SEG": "Seguridad",
    "JAR": "Jardinería",
    "INF": "Informática",
    "ACS": "ACS",
    "LEG": "Legionella",
    "EQU": "Equipamiento",
    "OTR": "Otros",
}


ICONOS_CATEGORIA_MATERIAL = {
    "Todas": "📦",
    "Fontanería": "🔧",
    "Electricidad": "⚡",
    "Ferretería": "🔩",
    "Climatización": "❄️",
    "Pintura": "🎨",
    "Limpieza": "🧹",
    "Seguridad": "🦺",
    "Jardinería": "🌿",
    "Informática": "💻",
    "ACS": "🌡️",
    "Legionella": "💧",
    "Equipamiento": "🪑",
    "Otros": "📦",
}


def obtener_categoria_material_desde_codigo(codigo):
    """
    Obtiene la categoría usando el prefijo del código.

    Ejemplos:
        FON-PRPI-001 -> Fontanería
        ELE-PAEL-001 -> Electricidad
        FER-JUDE-001 -> Ferretería
    """
    codigo_txt = str(codigo or "").strip().upper()

    if not codigo_txt:
        return "Otros"

    prefijo = codigo_txt.split("-")[0]

    return CATEGORIAS_MATERIAL_POR_PREFIJO.get(
        prefijo,
        "Otros"
    )


def preparar_materiales_selector(materiales_select):
    """
    Convierte los materiales recibidos en una estructura uniforme.
    Mantiene compatibilidad con obtener_materiales_para_select().
    """
    materiales = []

    for fila in materiales_select or []:
        try:
            codigo = str(fila[0] or "").strip()
            nombre = str(fila[1] or "").strip()
            stock = float(fila[2] or 0)
            unidad = str(fila[3] or "").strip()
        except (IndexError, TypeError, ValueError):
            continue

        if not codigo:
            continue

        materiales.append({
            "codigo": codigo,
            "nombre": nombre or codigo,
            "stock": stock,
            "unidad": unidad,
            "categoria": obtener_categoria_material_desde_codigo(
                codigo
            ),
        })

    return materiales


def mostrar_ficha_material_seleccionado(material):
    """
    Muestra la información completa del material elegido.
    """
    if not material:
        return

    codigo = material["codigo"]

    try:
        datos_mat = obtener_material_por_codigo(codigo)
    except Exception as e:
        datos_mat = None
        st.caption(f"No se pudo cargar la ficha del material: {e}")

    st.markdown(f"#### {material['nombre']}")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("Código")
        st.markdown(f"**{codigo}**")

    with col2:
        st.caption("Stock disponible")
        st.markdown(
            f"**{material['stock']:g} "
            f"{material['unidad']}**"
        )

    icono_categoria = ICONOS_CATEGORIA_MATERIAL.get(
        material["categoria"],
        "📦"
    )

    st.caption(
        f"{icono_categoria} Categoría: "
        f"{material['categoria']}"
    )

    if material["stock"] <= 0:
        st.warning("Este material no tiene stock disponible.")
    elif material["stock"] <= 2:
        st.warning("Queda poco stock de este material.")

    if not datos_mat:
        return

    foto_data = datos_mat.get("foto_data")
    foto_ruta = datos_mat.get("foto")

    if foto_data:
        try:
            st.image(
                bytes(foto_data),
                width=220,
                caption=material["nombre"]
            )
        except Exception:
            st.caption("Foto del material no disponible.")

    elif foto_ruta:
        try:
            st.image(
                foto_ruta,
                width=220,
                caption=material["nombre"]
            )
        except Exception:
            st.caption("Foto del material no disponible.")

    ubicacion = str(
        datos_mat.get("ubicacion")
        or datos_mat.get("espacio")
        or ""
    ).strip()

    centro_material = str(
        datos_mat.get("centro")
        or ""
    ).strip()

    edificio_material = str(
        datos_mat.get("edificio")
        or ""
    ).strip()

    partes_ubicacion = [
        parte
        for parte in [
            centro_material,
            edificio_material,
            ubicacion,
        ]
        if parte
    ]

    if partes_ubicacion:
        st.info(
            "📍 " + " · ".join(partes_ubicacion)
        )


def selector_material_inteligente(
    materiales,
    id_orden,
    indice,
    modo="operario",
):
    """
    Selector reutilizable de un material.

    Flujo:
        1. Categoría
        2. Búsqueda por nombre o código
        3. Selección del material
        4. Ficha y cantidad
    """
    if not materiales:
        st.info("No hay materiales disponibles.")
        return None

    categorias_disponibles = sorted({
        material["categoria"]
        for material in materiales
    })

    categorias = ["Todas"] + categorias_disponibles

    categoria_sel = st.selectbox(
        "Categoría",
        categorias,
        format_func=lambda categoria: (
            f"{ICONOS_CATEGORIA_MATERIAL.get(categoria, '📦')} "
            f"{categoria}"
        ),
        key=(
            f"{modo}_categoria_material_"
            f"{id_orden}_{indice}"
        ),
    )

    texto_busqueda = st.text_input(
        "Buscar por nombre o código",
        placeholder=(
            "Ejemplo: Presto, pistón, conector, FON..."
        ),
        key=(
            f"{modo}_buscar_material_"
            f"{id_orden}_{indice}"
        ),
    )

    materiales_filtrados = materiales

    if categoria_sel != "Todas":
        materiales_filtrados = [
            material
            for material in materiales_filtrados
            if material["categoria"] == categoria_sel
        ]

    buscar_txt = normalizar_txt(texto_busqueda)

    if buscar_txt:
        materiales_filtrados = [
            material
            for material in materiales_filtrados
            if (
                buscar_txt
                in normalizar_txt(material["nombre"])
                or buscar_txt
                in normalizar_txt(material["codigo"])
            )
        ]

    materiales_filtrados = sorted(
        materiales_filtrados,
        key=lambda material: (
            normalizar_txt(material["nombre"]),
            normalizar_txt(material["codigo"]),
        )
    )

    st.caption(
        f"{len(materiales_filtrados)} materiales encontrados."
    )

    if not materiales_filtrados:
        st.warning(
            "No se encontraron materiales con estos filtros."
        )
        return None

    codigos_filtrados = [
        material["codigo"]
        for material in materiales_filtrados
    ]

    materiales_por_codigo = {
        material["codigo"]: material
        for material in materiales_filtrados
    }

    codigo_sel = st.selectbox(
        "Material",
        codigos_filtrados,
        format_func=lambda codigo: (
            f"{materiales_por_codigo[codigo]['nombre']} · "
            f"Stock: "
            f"{materiales_por_codigo[codigo]['stock']:g} "
            f"{materiales_por_codigo[codigo]['unidad']}"
        ),
        key=(
            f"{modo}_material_ot_"
            f"{id_orden}_{indice}"
        ),
    )

    material_sel = materiales_por_codigo.get(codigo_sel)

    mostrar_ficha_material_seleccionado(
        material_sel
    )

    cantidad_material = st.number_input(
        "Cantidad usada",
        min_value=0.0,
        step=1.0,
        key=(
            f"{modo}_cantidad_material_ot_"
            f"{id_orden}_{indice}"
        ),
    )

    return {
        "codigo": codigo_sel,
        "cantidad": cantidad_material,
    }


def preparar_siguiente_mision_corazon(num_ot, id_orden, modo="operario"):
    """
    Libera la OT finalizada y solicita al Corazón una nueva misión.

    No calcula prioridades aquí: únicamente deja la interfaz preparada
    para que ui_operario vuelva a ejecutar latido_corazon().
    """
    if str(modo or "").strip().lower() != "operario":
        return

    st.session_state.pop("operario_ot_abierta_id", None)
    st.session_state["corazon_mision_finalizada"] = {
        "id": id_orden,
        "numero_ot": str(num_ot or "").strip(),
    }
    st.session_state["recalcular_corazon"] = True


def mostrar_tarjeta_ot(
    fila,
    materiales_select,
    operario_sel,
    modo="operario"
):
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
        observaciones_estado,
    ) = descomponer_orden_operario(fila)

    if es_operario() and normalizar_operario_nombre(operario) != normalizar_operario_nombre(nombre_operario_actual()):
        return

    estado_icono = {
        "Abierta": "🔴",
        "En curso": "🟠",
        "Pendiente material": "📦"
    }.get(est, "⚪")

    desc_corta = str(desc or "").replace("\n", " ").strip()

    if len(desc_corta) > 45:
        desc_corta = desc_corta[:45] + "..."

    titulo = (
        f"{estado_icono} {num_ot} | {prioridad} | "
        f"{centro or '-'} · {espacio or '-'} | {desc_corta}"
    )

    with st.expander(titulo, expanded=False):
        st.markdown(f"### {estado_icono} {num_ot}")
        st.markdown(f"**{prioridad}** | {area or '-'}")
        st.markdown(f"{desc}")
        st.caption(f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}")
        st.caption(f"Estado actual: {est}")

        if observaciones_estado:
            st.info(f"📝 Observación estado: {observaciones_estado}")

        st.caption(f"👷 Operario: {operario or '-'}")
        st.caption(f"📌 Solicitante: {tipo_solicitante or 'Operarios'}")

        if solicitante:
            st.caption(f"Nombre solicitante: {solicitante}")

        if fecha_origen:
            st.caption(f"Fecha origen: {fecha_origen}")
        mostrar_correccion_ubicacion_ot(
            id_orden=id_orden,
            modo=modo,
        )
        try:
            fotos_db = obtener_fotos_ot(num_ot)

            if fotos_db:
                cols_fotos = st.columns(3)

                for i, (nombre_foto, foto_data) in enumerate(fotos_db):
                    with cols_fotos[i % 3]:
                        try:
                            st.image(
                                bytes(foto_data),
                                caption=f"Foto {i + 1}",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.caption(f"📷 Foto no disponible: {e}")

            elif foto:
                fotos = str(foto).split("|")
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
            st.error(f"📷 Error mostrando fotos: {e}")

        # -----------------------------
        # CONTROLES INTELIGENTES DE OT
        # -----------------------------
        if es_ot_preventiva(origen, desc):
            mostrar_checklist_preventivo_operario(
                num_ot=num_ot,
                desc=desc,
                operario=operario
            )

        elif es_ot_legionella(area, origen, desc):
            if "CORRECTIVO LEGIONELLA" in str(desc or "").upper():
                mostrar_checklist_correctivo_legionella_operario(
                    num_ot=num_ot,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    desc=desc
                )
            else:
                mostrar_ejecucion_legionella_operario(
                    id_orden=id_orden,
                    num_ot=num_ot,
                    desc=desc,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    operario=operario,
                )

        st.markdown("### 📝 Estado y observaciones")

        observacion_estado_nueva = st.text_area(
            "Observación del estado",
            value=str(observaciones_estado or ""),
            placeholder="Ejemplo: En curso porque falta acceder al aula, pendiente de pieza, esperando proveedor...",
            key=f"{modo}_observacion_estado_{id_orden}"
        )

        b1, b2, b3 = st.columns(3)

        with b1:
            if st.button("▶\nEn curso", key=f"{modo}_curso_rapido_{id_orden}", use_container_width=True):
                actualizar_estado(id_orden, "En curso", observacion_estado_nueva)
                st.rerun()

        with b2:
            if st.button("📦\nMaterial", key=f"{modo}_mat_rapido_{id_orden}", use_container_width=True):
                actualizar_estado(id_orden, "Pendiente material", observacion_estado_nueva)
                st.rerun()

        with b3:
            if st.button("✔\nFinalizar", key=f"{modo}_fin_rapido_{id_orden}", use_container_width=True):
                st.session_state[f"{modo}_confirmar_fin_rapido_{id_orden}"] = True
                st.rerun()

        if st.session_state.get(f"{modo}_confirmar_fin_rapido_{id_orden}", False):
            st.warning(f"¿Seguro que quieres finalizar {num_ot}?")

            c1, c2 = st.columns(2)

            with c1:
                if st.button("✔\nSí, finalizar", key=f"{modo}_si_fin_rapido_{id_orden}", use_container_width=True):
                    if not puede_finalizar_preventivo(num_ot, origen, desc):
                        st.error("No puedes finalizar esta preventiva hasta completar todo el checklist.")
                    elif not puede_finalizar_legionella(id_orden, area, origen, desc, num_ot):
                        st.error("No puedes finalizar esta OT de Legionella hasta completar el control/checklist correspondiente.")
                    else:
                        actualizar_observaciones_estado(id_orden, observacion_estado_nueva)
                        finalizar_orden(id_orden, "")
                        st.session_state[f"{modo}_confirmar_fin_rapido_{id_orden}"] = False
                        st.session_state.pop(f"legionella_guardada_{id_orden}", None)
                        preparar_siguiente_mision_corazon(num_ot, id_orden, modo)
                        st.rerun()

            with c2:
                if st.button("❌\nCancelar", key=f"{modo}_no_fin_rapido_{id_orden}", use_container_width=True):
                    st.session_state[f"{modo}_confirmar_fin_rapido_{id_orden}"] = False
                    st.rerun()

        with st.expander(f"Más opciones {num_ot}"):
            observaciones_fin = st.text_area(
                "Observaciones de cierre",
                key=f"{modo}_obs_operario_{id_orden}"
            )

            usar_material = st.checkbox(
                "Descontar material del inventario al cerrar",
                key=f"{modo}_usar_material_{id_orden}"
            )

            materiales_ot = []

            if usar_material:
                materiales_preparados = preparar_materiales_selector(
                    materiales_select
                )

                if materiales_preparados:
                    num_materiales = st.number_input(
                        "Número de materiales usados",
                        min_value=1,
                        max_value=10,
                        value=1,
                        step=1,
                        key=(
                            f"{modo}_num_materiales_ot_"
                            f"{id_orden}"
                        ),
                    )

                    st.markdown("### 📦 Materiales usados")

                    for i in range(int(num_materiales)):
                        with st.container(border=True):
                            st.markdown(
                                f"### Material {i + 1}"
                            )

                            material_usado = (
                                selector_material_inteligente(
                                    materiales=materiales_preparados,
                                    id_orden=id_orden,
                                    indice=i,
                                    modo=modo,
                                )
                            )

                            if material_usado:
                                materiales_ot.append(
                                    material_usado
                                )

                else:
                    st.info(
                        "No hay materiales dados de alta "
                        "en Inventario."
                    )

            st.file_uploader(
                "📷 Fotos del trabajo realizado",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=f"{modo}_fotos_cierre_{id_orden}"
            )

            if st.button(
                f"Finalizar con observaciones/material {num_ot}",
                key=f"{modo}_fin_completo_operario_{id_orden}",
                use_container_width=True
            ):
                st.session_state[f"{modo}_materiales_confirmados_{id_orden}"] = materiales_ot.copy()
                st.session_state[f"{modo}_confirmar_fin_completo_{id_orden}"] = True
                st.rerun()

            if st.session_state.get(f"{modo}_confirmar_fin_completo_{id_orden}", False):
                st.warning(f"¿Seguro que quieres finalizar {num_ot} con estas observaciones/material?")

                c1, c2 = st.columns(2)

                with c1:
                    if st.button("✔\nSí, finalizar", key=f"{modo}_si_fin_completo_{id_orden}", use_container_width=True):

                        if not puede_finalizar_preventivo(num_ot, origen, desc):
                            st.error("No puedes finalizar esta preventiva hasta completar todo el checklist.")

                        elif not puede_finalizar_legionella(id_orden, area, origen, desc, num_ot):
                            st.error("No puedes finalizar esta OT de Legionella hasta completar el control/checklist correspondiente.")

                        elif usar_material and materiales_select:
                            materiales_confirmados = st.session_state.get(
                                f"{modo}_materiales_confirmados_{id_orden}",
                                materiales_ot
                            )

                            materiales_validos = [
                                m for m in materiales_confirmados
                                if m["cantidad"] > 0
                            ]

                            if not materiales_validos:
                                st.warning("Indica al menos un material con cantidad mayor que 0.")
                            else:
                                errores = []

                                for m in materiales_validos:
                                    ok, mensaje = registrar_movimiento_inventario(
                                        codigo_material=m["codigo"],
                                        tipo_movimiento="Salida",
                                        cantidad=m["cantidad"],
                                        motivo=f"Consumo en OT {num_ot}",
                                        numero_ot=num_ot,
                                        operario=operario_sel
                                    )

                                    if not ok:
                                        errores.append(f"{m['codigo']}: {mensaje}")

                                if errores:
                                    for error in errores:
                                        st.error(error)
                                else:
                                    actualizar_observaciones_estado(id_orden, observacion_estado_nueva)
                                    finalizar_orden(id_orden, observaciones_fin)
                                    st.session_state[f"{modo}_confirmar_fin_completo_{id_orden}"] = False
                                    st.session_state.pop(f"{modo}_materiales_confirmados_{id_orden}", None)
                                    st.session_state.pop(f"legionella_guardada_{id_orden}", None)
                                    preparar_siguiente_mision_corazon(num_ot, id_orden, modo)
                                    st.rerun()

                        else:
                            actualizar_observaciones_estado(id_orden, observacion_estado_nueva)
                            finalizar_orden(id_orden, observaciones_fin)
                            st.session_state[f"{modo}_confirmar_fin_completo_{id_orden}"] = False
                            st.session_state.pop(f"{modo}_materiales_confirmados_{id_orden}", None)
                            st.session_state.pop(f"legionella_guardada_{id_orden}", None)
                            preparar_siguiente_mision_corazon(num_ot, id_orden, modo)
                            st.rerun()

                with c2:
                    if st.button("❌\nCancelar", key=f"{modo}_no_fin_completo_{id_orden}", use_container_width=True):
                        st.session_state[f"{modo}_confirmar_fin_completo_{id_orden}"] = False
                        st.session_state.pop(f"{modo}_materiales_confirmados_{id_orden}", None)
                        st.rerun()
