import streamlit as st

from modules.colegio import obtener_estado_espacio, icono_estado_espacio
from ui.ui_arbol_colegio import mostrar_arbol_colegio
from ui.ui_ot import mostrar_tarjeta_ot

from modules.inventario import obtener_materiales_para_select
from modules.catalogo_aulas import obtener_elementos_catalogo_aulas

from modules.inventario_aulas import (
    guardar_o_actualizar_espacio,
    guardar_foto_espacio,
)

from modules.ficha_espacio import (
    obtener_resumen_ficha_espacio,
    obtener_actuaciones_espacio,
    obtener_inventario_espacio,
    obtener_preventivos_espacio,
    obtener_historial_tecnico_espacio,
)


def pantalla_colegio():
    st.markdown("## 🏫 Colegio")
    st.caption(
        "Navegación por centro, edificio, planta y espacio. "
        "Todo pensado para móvil y trabajo diario."
    )

    mostrar_arbol_colegio()


def ficha_espacio_basica(centro, edificio, planta, espacio):
    estado = obtener_estado_espacio(centro, edificio, espacio)
    icono = icono_estado_espacio(estado)

    resumen = obtener_resumen_ficha_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio
    )

    st.markdown(f"### {icono} {espacio}")
    st.caption(f"{centro} · {edificio} · {planta}")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Actuaciones", resumen["actuaciones_abiertas"])
    c2.metric("Inventario", resumen["inventario"])
    c3.metric("Preventivos", resumen["preventivos"])
    c4.metric("Historial", resumen["historial"])

    st.markdown("---")

    with st.expander(f"📌 Actuaciones ({resumen['actuaciones_abiertas']})", expanded=False):
        actuaciones = obtener_actuaciones_espacio(centro, edificio, espacio)

        if not actuaciones:
            st.info("No hay actuaciones abiertas en este espacio.")
        else:
            materiales_select = obtener_materiales_para_select()

            for a in actuaciones:
                id_ot, numero_ot, descripcion, estado_ot, prioridad, operario, origen, area, fecha = a

                fila_ot = (
                    id_ot,
                    numero_ot,
                    descripcion,
                    estado_ot,
                    fecha,
                    centro,
                    edificio,
                    espacio,
                    area,
                    prioridad,
                    operario,
                    origen,
                    "",
                    "",
                    "",
                    "Operarios",
                    "",
                )

                mostrar_tarjeta_ot(
                    fila=fila_ot,
                    materiales_select=materiales_select,
                    operario_sel=operario or "",
                    modo="colegio"
                )

    with st.expander("📦 Inventario del espacio", expanded=False):
        st.markdown("### 📦 Añadir / actualizar elemento")

        opciones_elementos = list(obtener_elementos_catalogo_aulas())

        if "Otro" not in opciones_elementos:
            opciones_elementos.append("Otro")

        elemento = st.selectbox(
            "Elemento",
            opciones_elementos,
            key=f"colegio_inv_elemento_{centro}_{edificio}_{espacio}"
        )

        if elemento == "Otro":
            elemento = st.text_input(
                "Especificar elemento",
                key=f"colegio_inv_elemento_otro_{centro}_{edificio}_{espacio}"
            )

        c_inv1, c_inv2 = st.columns(2)

        with c_inv1:
            cantidad = st.number_input(
                "Cantidad",
                min_value=0,
                step=1,
                key=f"colegio_inv_cantidad_{centro}_{edificio}_{espacio}"
            )

        with c_inv2:
            estado_item = st.selectbox(
                "Estado",
                ["Correcto", "Regular", "Dañado", "Falta", "Retirar"],
                key=f"colegio_inv_estado_{centro}_{edificio}_{espacio}"
            )

        observaciones_inv = st.text_input(
            "Observaciones",
            key=f"colegio_inv_obs_{centro}_{edificio}_{espacio}"
        )

        foto_inv = st.file_uploader(
            "Foto del elemento",
            type=["jpg", "jpeg", "png"],
            key=f"colegio_inv_foto_{centro}_{edificio}_{espacio}"
        )

        if foto_inv is not None:
            st.image(foto_inv, width=220)

        if st.button(
            "💾 Guardar elemento en este espacio",
            key=f"colegio_guardar_inv_{centro}_{edificio}_{espacio}",
            use_container_width=True
        ):
            elemento = str(elemento or "").strip()

            if not elemento:
                st.warning("Indica un elemento.")
            elif cantidad <= 0:
                st.warning("Indica una cantidad mayor que 0.")
            else:
                ruta_foto = guardar_foto_espacio(
                    foto_inv,
                    centro,
                    edificio,
                    espacio,
                    elemento
                )

                ok = guardar_o_actualizar_espacio(
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    elemento=elemento,
                    cantidad=cantidad,
                    estado=estado_item,
                    ancho=0,
                    alto=0,
                    fondo=0,
                    unidad="cm",
                    observaciones=observaciones_inv,
                    foto=ruta_foto,
                    operario=st.session_state.get("operario_activo", "")
                )

                if ok:
                    st.success("Inventario del espacio actualizado.")
                    st.rerun()
                else:
                    st.error("No se pudo guardar el inventario del espacio.")

        st.markdown("---")
        st.markdown("### 📋 Inventario actual")

        inventario = obtener_inventario_espacio(centro, edificio, espacio)

        if not inventario:
            st.info("No hay inventario registrado en este espacio.")
        else:
            for i in inventario:
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
                    operario
                ) = i

                icono_inv = "✅"

                if estado_inv in ["Dañado", "Falta", "Retirar"]:
                    icono_inv = "🔴"
                elif estado_inv == "Regular":
                    icono_inv = "🟡"

                with st.expander(
                    f"{icono_inv} {elemento or '-'} · {cantidad or 0} uds · {estado_inv or '-'}",
                    expanded=False
                ):
                    st.caption(f"Revisado por {operario or '-'} · {fecha_revision or '-'}")

                    if observaciones:
                        st.info(observaciones)

                    if foto:
                        try:
                            st.image(foto, width=220)
                        except Exception:
                            st.caption("Foto no disponible.")

    with st.expander(f"📅 Preventivos ({resumen['preventivos']})", expanded=False):
        preventivos = obtener_preventivos_espacio(centro, edificio, espacio)

        if not preventivos:
            st.info("No hay preventivos registrados en este espacio.")
        else:
            for p in preventivos:
                id_prev, fecha, operario, estado_prev, observaciones, numero_ot_preventiva = p

                st.markdown(
                    f"**{fecha or '-'}** · {estado_prev or '-'} · "
                    f"{operario or '-'}"
                )

                if observaciones:
                    st.caption(observaciones)

    with st.expander(f"📋 Historial ({resumen['historial']})", expanded=False):
        historial = obtener_historial_tecnico_espacio(centro, edificio, espacio)

        if not historial:
            st.info("No hay historial técnico registrado en este espacio.")
        else:
            for h in historial[:10]:
                (
                    id_hist,
                    fecha,
                    elemento,
                    tipo,
                    numero_ot,
                    descripcion,
                    area,
                    estado_hist,
                    operario,
                    observaciones,
                    origen,
                    tipo_orden,
                    coste,
                    foto,
                    fecha_reparacion
                ) = h

                st.markdown(
                    f"**{fecha or '-'}** · "
                    f"{tipo or '-'} · "
                    f"{area or '-'} · "
                    f"OT `{numero_ot or '-'}`"
                )

                st.caption(descripcion or "")

    with st.expander("📸 Fotografías", expanded=False):
        st.info("Aquí mostraremos las fotos asociadas al espacio.")



