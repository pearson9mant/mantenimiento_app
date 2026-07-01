import streamlit as st

from modules.catalogo_aulas import obtener_elementos_catalogo_aulas
from modules.ficha_espacio import obtener_inventario_espacio
from modules.ordenes import crear_correctiva_desde_ot

from modules.inventario_aulas import (
    guardar_o_actualizar_espacio,
    guardar_foto_espacio,
    eliminar_inventario_espacio,
    guardar_correctivo_inventario,
)
from modules.activos import (
    obtener_activo_por_inventario,
    guardar_o_actualizar_activo,
)


def _clave(centro, edificio, planta, espacio):
    return (
        f"{centro}_{edificio}_{planta}_{espacio}"
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def _icono_estado(estado):
    if estado in ["Dañado", "Falta", "Retirar"]:
        return "🔴"
    if estado == "Regular":
        return "🟡"
    return "🟢"


def _opciones_elementos():
    opciones = list(obtener_elementos_catalogo_aulas())
    if "Otro" not in opciones:
        opciones.append("Otro")
    return opciones


def _mostrar_reinicio_admin(centro, edificio, espacio, inventario, clave_base):
    perfil = str(st.session_state.get("perfil", "")).lower()

    if perfil not in ["admin", "administracion", "administración"]:
        return

    if not inventario:
        return

    st.markdown("---")
    st.markdown("### ⚙️ Administración")

    key_confirmar = f"confirmar_reiniciar_inv_{clave_base}"

    if not st.session_state.get(key_confirmar, False):
        if st.button(
            "🗑️ Reiniciar inventario del espacio",
            key=f"btn_reiniciar_inv_{clave_base}",
            use_container_width=True
        ):
            st.session_state[key_confirmar] = True
            st.rerun()
    else:
        st.warning(
            "¿Seguro?\n\n"
            "Se eliminarán TODOS los elementos del inventario de este espacio."
        )

        c1, c2 = st.columns(2)

        with c1:
            if st.button(
                "✅ Sí, reiniciar",
                key=f"si_reiniciar_inv_{clave_base}",
                use_container_width=True
            ):
                ok = eliminar_inventario_espacio(centro, edificio, espacio)
                st.session_state[key_confirmar] = False

                if ok:
                    st.success("Inventario eliminado correctamente.")
                else:
                    st.error("No se pudo eliminar el inventario.")

                st.rerun()

        with c2:
            if st.button(
                "Cancelar",
                key=f"cancelar_reiniciar_inv_{clave_base}",
                use_container_width=True
            ):
                st.session_state[key_confirmar] = False
                st.rerun()


def _mostrar_inventario_actual(centro, edificio, espacio, inventario, clave_base):
    st.markdown("### 📋 Inventario actual")

    if not inventario:
        st.info("Este espacio todavía no tiene inventario.")
        return

    for item in inventario:
        (
            id_inv,
            fecha_revision,
            elemento,
            cantidad,
            estado_inv,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario,
            numero_ot_correctiva,
            fecha_correctivo,
            fabricante,
            modelo,
            numero_serie,
            fecha_instalacion,
            proveedor,
            vida_util_anios,
            coste_estimado,
        ) = item

        icono = _icono_estado(estado_inv)

        with st.expander(
            f"{icono} {elemento or '-'} · {cantidad or 0} uds · {estado_inv or '-'}",
            expanded=False
        ):
            st.caption(f"Revisado por {operario or '-'} · {fecha_revision or '-'}")

            if numero_ot_correctiva:
                st.warning(f"🟠 OT correctiva asociada: {numero_ot_correctiva}")

            opciones_estado = ["Correcto", "Regular", "Dañado", "Falta", "Retirar"]

            c1, c2 = st.columns(2)

            with c1:
                nueva_cantidad = st.number_input(
                    "Cantidad",
                    min_value=0,
                    step=1,
                    value=int(cantidad or 0),
                    key=f"edit_cantidad_{clave_base}_{id_inv}"
                )

            with c2:
                estado_actual = estado_inv if estado_inv in opciones_estado else "Correcto"

                nuevo_estado = st.selectbox(
                    "Estado",
                    opciones_estado,
                    index=opciones_estado.index(estado_actual),
                    key=f"edit_estado_{clave_base}_{id_inv}"
                )

            nuevas_obs = st.text_input(
                "Observaciones",
                value=str(observaciones or ""),
                key=f"edit_obs_{clave_base}_{id_inv}"
            )

            nueva_foto = st.file_uploader(
                "Actualizar foto",
                type=["jpg", "jpeg", "png"],
                key=f"edit_foto_{clave_base}_{id_inv}"
            )

            foto_final = foto

            if nueva_foto is not None:
                st.image(nueva_foto, width=180)
                foto_final = guardar_foto_espacio(
                    nueva_foto,
                    centro,
                    edificio,
                    espacio,
                    elemento
                )
            elif foto:
                try:
                    st.image(foto, width=220)
                except Exception:
                    st.caption("Foto no disponible.")

            if st.button(
                "💾 Guardar cambios",
                key=f"guardar_edit_inv_{clave_base}_{id_inv}",
                use_container_width=True
            ):
                ok = guardar_o_actualizar_espacio(
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    elemento=elemento,
                    cantidad=nueva_cantidad,
                    estado=nuevo_estado,
                    ancho=ancho or 0,
                    alto=alto or 0,
                    fondo=fondo or 0,
                    unidad=unidad or "cm",
                    observaciones=nuevas_obs,
                    foto=foto_final,
                    operario=st.session_state.get("operario_activo", "")
                )

                if ok:
                    st.success("Elemento actualizado.")
                    st.rerun()
                else:
                    st.error("No se pudo actualizar el elemento.")

            st.markdown("---")
            st.markdown("### 🏷️ Ficha técnica del activo")

            t1, t2 = st.columns(2)

            with t1:
                fabricante_nuevo = st.text_input(
                    "Fabricante",
                    value=str(fabricante or ""),
                    key=f"activo_fabricante_{clave_base}_{id_inv}"
                )

                modelo_nuevo = st.text_input(
                    "Modelo",
                    value=str(modelo or ""),
                    key=f"activo_modelo_{clave_base}_{id_inv}"
                )

                numero_serie_nuevo = st.text_input(
                    "Nº de serie",
                    value=str(numero_serie or ""),
                    key=f"activo_serie_{clave_base}_{id_inv}"
                )

            with t2:
                proveedor_nuevo = st.text_input(
                    "Proveedor",
                    value=str(proveedor or ""),
                    key=f"activo_proveedor_{clave_base}_{id_inv}"
                )

                fecha_instalacion_nueva = st.text_input(
                    "Fecha instalación",
                    value=str(fecha_instalacion or ""),
                    placeholder="AAAA-MM-DD",
                    key=f"activo_fecha_inst_{clave_base}_{id_inv}"
                )

                vida_util_nueva = st.number_input(
                    "Vida útil estimada (años)",
                    min_value=0,
                    step=1,
                    value=int(vida_util_anios or 0),
                    key=f"activo_vida_{clave_base}_{id_inv}"
                )

            coste_estimado_nuevo = st.number_input(
                "Coste estimado (€)",
                min_value=0.0,
                step=1.0,
                value=float(coste_estimado or 0),
                key=f"activo_coste_{clave_base}_{id_inv}"
            )

            if st.button(
                "💾 Guardar ficha técnica",
                key=f"guardar_ficha_tecnica_{clave_base}_{id_inv}",
                use_container_width=True
            ):
                ok_activo = guardar_o_actualizar_activo(
                    id_inventario=id_inv,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    elemento=elemento,
                    fabricante=fabricante_nuevo,
                    modelo=modelo_nuevo,
                    numero_serie=numero_serie_nuevo,
                    fecha_instalacion=fecha_instalacion_nueva,
                    proveedor=proveedor_nuevo,
                    vida_util_anios=vida_util_nueva,
                    coste_estimado=coste_estimado_nuevo,
                )

                if ok_activo:
                    st.success("Ficha técnica actualizada correctamente.")
                    st.rerun()
                else:
                    st.error("No se pudo guardar la ficha técnica.")

            st.markdown("---")

            if nuevo_estado in ["Dañado", "Falta", "Retirar"]:
                if numero_ot_correctiva:
                    st.warning(f"🟠 Ya existe OT correctiva asociada: {numero_ot_correctiva}")
                else:
                    st.warning("Este elemento necesita correctivo.")

                    descripcion_defecto = st.text_area(
                        "Descripción del correctivo",
                        value=f"{elemento} en estado {nuevo_estado}. {nuevas_obs}",
                        key=f"correctivo_desc_{clave_base}_{id_inv}"
                    )

                    confirmar_correctivo = st.checkbox(
                        "Crear OT correctiva para este elemento",
                        key=f"crear_correctivo_inv_{clave_base}_{id_inv}"
                    )

                    if st.button(
                        "🛠️ Crear correctivo",
                        key=f"btn_correctivo_inv_{clave_base}_{id_inv}",
                        use_container_width=True
                    ):
                        if not confirmar_correctivo:
                            st.warning("Marca primero la casilla de confirmación.")
                        else:
                            ok, mensaje = crear_correctiva_desde_ot(
                                centro=centro,
                                edificio=edificio,
                                espacio=espacio,
                                area="Mantenimiento",
                                prioridad="Media",
                                operario=st.session_state.get("operario_activo", ""),
                                descripcion_defecto=descripcion_defecto,
                                numero_ot_origen=f"INV-{id_inv}",
                                origen="INVENTARIO",
                                solicitante="Inventario espacio",
                            )

                            if ok:
                                numero_ot_generada = (
                                    str(mensaje or "")
                                    .replace("Correctiva creada correctamente:", "")
                                    .strip()
                                )

                                guardar_correctivo_inventario(
                                    id_elemento=id_inv,
                                    numero_ot=numero_ot_generada
                                )

                                st.success(f"OT correctiva creada: {numero_ot_generada}")
                                st.rerun()
                            else:
                                st.error(mensaje)


def _mostrar_asistente_inventario(centro, edificio, planta, espacio, inventario, clave_base):
    st.markdown("---")

    if not inventario:
        st.markdown("### 🚀 Crear inventario inicial")
    else:
        st.markdown("### ➕ Añadir nuevo elemento")

    key_mostrar_form = f"estado_mostrar_form_add_{clave_base}"

    if "inventario_temp" not in st.session_state:
        st.session_state["inventario_temp"] = {}

    if clave_base not in st.session_state["inventario_temp"]:
        st.session_state["inventario_temp"][clave_base] = []

    elementos_temp = st.session_state["inventario_temp"][clave_base]

    if elementos_temp:
        st.markdown("#### ✅ Elementos preparados")

        for item in elementos_temp:
            st.markdown(
                f"✅ **{item['elemento']}** · "
                f"{item['cantidad']} uds · {item['estado']}"
            )

        st.markdown("---")

    mostrar_formulario = st.session_state.get(
        key_mostrar_form,
        not elementos_temp
    )

    if not mostrar_formulario:
        if st.button(
            "➕ Añadir otro elemento",
            key=f"btn_mostrar_form_add_{clave_base}",
            use_container_width=True
        ):
            st.session_state[key_mostrar_form] = True
            st.rerun()

    if mostrar_formulario:
        st.markdown("#### Nuevo elemento")

        opciones_base = _opciones_elementos()

        elemento_nuevo = st.selectbox(
            "Elemento",
            opciones_base,
            key=f"add_elemento_{clave_base}"
        )

        if elemento_nuevo == "Otro":
            elemento_nuevo = st.text_input(
                "Especificar elemento",
                key=f"add_elemento_otro_{clave_base}"
            )

        c1, c2 = st.columns(2)

        with c1:
            cantidad_nueva = st.number_input(
                "Cantidad",
                min_value=0,
                step=1,
                key=f"add_cantidad_{clave_base}"
            )

        with c2:
            estado_nuevo = st.selectbox(
                "Estado",
                ["Correcto", "Regular", "Dañado", "Falta", "Retirar"],
                key=f"add_estado_{clave_base}"
            )

        observaciones_nuevo = st.text_input(
            "Observaciones",
            key=f"add_obs_{clave_base}"
        )

        foto_nuevo = st.file_uploader(
            "Foto",
            type=["jpg", "jpeg", "png"],
            key=f"add_foto_{clave_base}"
        )

        if foto_nuevo is not None:
            st.image(foto_nuevo, width=180)

        if st.button(
            "✅ Añadir a la lista",
            key=f"add_temp_{clave_base}",
            use_container_width=True
        ):
            elemento_nuevo = str(elemento_nuevo or "").strip()

            if not elemento_nuevo:
                st.warning("Indica un elemento.")
            elif cantidad_nueva <= 0:
                st.warning("Indica una cantidad mayor que 0.")
            else:
                existe_bd = any(
                    str(x[2] or "").strip().lower() == elemento_nuevo.lower()
                    for x in inventario
                )

                existe_temp = any(
                    str(x["elemento"]).strip().lower() == elemento_nuevo.lower()
                    for x in elementos_temp
                )

                if existe_bd or existe_temp:
                    st.warning(
                        "Este elemento ya existe en este espacio. "
                        "Modifícalo desde su ficha."
                    )
                else:
                    ruta_foto = guardar_foto_espacio(
                        foto_nuevo,
                        centro,
                        edificio,
                        espacio,
                        elemento_nuevo
                    )

                    elementos_temp.append({
                        "elemento": elemento_nuevo,
                        "cantidad": cantidad_nueva,
                        "estado": estado_nuevo,
                        "observaciones": observaciones_nuevo,
                        "foto": ruta_foto,
                    })

                    st.session_state["inventario_temp"][clave_base] = elementos_temp
                    st.session_state[key_mostrar_form] = False
                    st.success("Elemento añadido a la lista.")
                    st.rerun()

    if elementos_temp:
        st.markdown("---")

        c_final1, c_final2 = st.columns(2)

        with c_final1:
            texto_boton = (
                "💾 Crear inventario inicial"
                if not inventario
                else "💾 Guardar nuevos elementos"
            )

            if st.button(
                texto_boton,
                key=f"guardar_temp_{clave_base}",
                use_container_width=True
            ):
                guardados = 0

                for item in elementos_temp:
                    ok = guardar_o_actualizar_espacio(
                        centro=centro,
                        edificio=edificio,
                        espacio=espacio,
                        elemento=item["elemento"],
                        cantidad=item["cantidad"],
                        estado=item["estado"],
                        ancho=0,
                        alto=0,
                        fondo=0,
                        unidad="cm",
                        observaciones=item["observaciones"],
                        foto=item["foto"],
                        operario=st.session_state.get("operario_activo", "")
                    )

                    if ok:
                        guardados += 1

                if guardados > 0:
                    st.session_state["inventario_temp"][clave_base] = []
                    st.session_state[key_mostrar_form] = True
                    st.success(f"Inventario actualizado. Elementos guardados: {guardados}")
                    st.rerun()
                else:
                    st.error("No se pudo guardar el inventario.")

        with c_final2:
            if st.button(
                "🧹 Vaciar lista preparada",
                key=f"vaciar_temp_{clave_base}",
                use_container_width=True
            ):
                st.session_state["inventario_temp"][clave_base] = []
                st.session_state[key_mostrar_form] = True
                st.rerun()


def mostrar_inventario_espacio(centro, edificio, planta, espacio):
    clave_base = _clave(centro, edificio, planta, espacio)

    inventario = obtener_inventario_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio
    )

    _mostrar_inventario_actual(
        centro=centro,
        edificio=edificio,
        espacio=espacio,
        inventario=inventario,
        clave_base=clave_base
    )

    _mostrar_asistente_inventario(
        centro=centro,
        edificio=edificio,
        planta=planta,
        espacio=espacio,
        inventario=inventario,
        clave_base=clave_base
    )

    _mostrar_reinicio_admin(
        centro=centro,
        edificio=edificio,
        espacio=espacio,
        inventario=inventario,
        clave_base=clave_base
    )
