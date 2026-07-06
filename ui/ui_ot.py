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

from ui.ui_ot_controles import (
    mostrar_ejecucion_legionella_operario,
    mostrar_checklist_preventivo_operario,
    mostrar_checklist_correctivo_legionella_operario,
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
            try:
                from ui.ui_operario import mostrar_checklist_preventivo_operario
        
                mostrar_checklist_preventivo_operario(
                    num_ot=num_ot,
                    desc=desc,
                    operario=operario
                )
        
            except Exception as e:
                st.error("No se ha podido cargar el checklist preventivo.")
                st.exception(e)
        
        elif es_ot_legionella(area, origen, desc):
            try:
                from ui.ui_operario import (
                    mostrar_ejecucion_legionella_operario,
                    mostrar_checklist_correctivo_legionella_operario,
                )
        
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
        
            except Exception as e:
                st.error("No se ha podido cargar el control de Legionella.")
                st.exception(e)

        # -----------------------------
        # CONTROLES INTELIGENTES DE OT
        # -----------------------------
        
        if es_ot_preventiva(origen, desc):
            try:
                from ui.ui_operario import mostrar_checklist_preventivo_operario
        
                mostrar_checklist_preventivo_operario(
                    num_ot=num_ot,
                    desc=desc,
                    operario=operario
                )
        
            except Exception as e:
                st.error("No se ha podido cargar el checklist preventivo.")
                st.exception(e)
        
        elif es_ot_legionella(area, origen, desc):
            try:
                from ui.ui_operario import (
                    mostrar_ejecucion_legionella_operario,
                    mostrar_checklist_correctivo_legionella_operario,
                )
        
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
        
            except Exception as e:
                st.error("No se ha podido cargar el control de Legionella.")
                st.exception(e)

        if es_ot_preventiva(origen, desc):
            mostrar_checklist_preventivo_operario(num_ot, desc, operario)
        
        elif es_ot_legionella(area, origen, desc):
            if "CORRECTIVO LEGIONELLA" in str(desc or "").upper():
                mostrar_checklist_correctivo_legionella_operario(
                    num_ot, centro, edificio, espacio, desc
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
                        st.success(f"{num_ot} finalizada correctamente.")
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
                if materiales_select:
                    opciones_material = [
                        f"{codigo} | {material} | Stock: {stock_actual} {unidad}"
                        for codigo, material, stock_actual, unidad in materiales_select
                    ]

                    num_materiales = st.number_input(
                        "Número de materiales usados",
                        min_value=1,
                        max_value=10,
                        value=1,
                        step=1,
                        key=f"{modo}_num_materiales_ot_{id_orden}"
                    )

                    st.markdown("#### Materiales usados")

                    for i in range(int(num_materiales)):
                        st.markdown(f"**Material {i + 1}**")

                        material_ot = st.selectbox(
                            "Selecciona material",
                            opciones_material,
                            key=f"{modo}_material_ot_{id_orden}_{i}"
                        )

                        codigo_sel = material_ot.split(" | ")[0]
                        datos_mat = obtener_material_por_codigo(codigo_sel)

                        if datos_mat:
                            foto_data = datos_mat.get("foto_data")
                            foto_ruta = datos_mat.get("foto")

                            if foto_data:
                                try:
                                    st.image(bytes(foto_data), width=180)
                                except Exception:
                                    st.caption("Foto del material no disponible.")

                            elif foto_ruta:
                                try:
                                    st.image(foto_ruta, width=180)
                                except Exception:
                                    st.caption("Foto del material no disponible.")

                        cantidad_material = st.number_input(
                            "Cantidad usada",
                            min_value=0.0,
                            step=1.0,
                            key=f"{modo}_cantidad_material_ot_{id_orden}_{i}"
                        )

                        materiales_ot.append({
                            "codigo": codigo_sel,
                            "cantidad": cantidad_material
                        })
                else:
                    st.info("No hay materiales dados de alta en Inventario.")

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
                                    st.success(f"{num_ot} finalizada y materiales descontados correctamente.")
                                    st.rerun()

                        else:
                            actualizar_observaciones_estado(id_orden, observacion_estado_nueva)
                            finalizar_orden(id_orden, observaciones_fin)
                            st.session_state[f"{modo}_confirmar_fin_completo_{id_orden}"] = False
                            st.session_state.pop(f"{modo}_materiales_confirmados_{id_orden}", None)
                            st.session_state.pop(f"legionella_guardada_{id_orden}", None)
                            st.success(f"{num_ot} finalizada correctamente.")
                            st.rerun()

                with c2:
                    if st.button("❌\nCancelar", key=f"{modo}_no_fin_completo_{id_orden}", use_container_width=True):
                        st.session_state[f"{modo}_confirmar_fin_completo_{id_orden}"] = False
                        st.session_state.pop(f"{modo}_materiales_confirmados_{id_orden}", None)
                        st.rerun()
