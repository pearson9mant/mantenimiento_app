 with st.expander("📦 Inventario del espacio", expanded=False):
        inventario = obtener_inventario_espacio(centro, edificio, espacio)

        st.markdown("### 📋 Inventario actual")
        perfil = str(st.session_state.get("perfil", "")).lower()

        if perfil in ["admin", "administracion", "administración"]:
        
            st.markdown("---")
            st.markdown("### ⚙️ Administración")
        
            if not st.session_state.get(
                f"confirmar_borrar_inv_{centro}_{edificio}_{espacio}",
                False
            ):
        
                if st.button(
                    "🗑️ Reiniciar inventario del espacio",
                    key=f"reiniciar_inv_{centro}_{edificio}_{espacio}",
                    use_container_width=True
                ):
                    st.session_state[
                        f"confirmar_borrar_inv_{centro}_{edificio}_{espacio}"
                    ] = True
        
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
                        key=f"si_reiniciar_inv_{centro}_{edificio}_{espacio}",
                        use_container_width=True
                    ):
        
                        ok = eliminar_inventario_espacio(
                            centro,
                            edificio,
                            espacio
                        )
        
                        st.session_state[
                            f"confirmar_borrar_inv_{centro}_{edificio}_{espacio}"
                        ] = False
        
                        if ok:
                            st.success("Inventario eliminado correctamente.")
                        else:
                            st.error("No se pudo eliminar el inventario.")
        
                        st.rerun()
        
                with c2:
        
                    if st.button(
                        "Cancelar",
                        key=f"cancelar_reiniciar_inv_{centro}_{edificio}_{espacio}",
                        use_container_width=True
                    ):
        
                        st.session_state[
                            f"confirmar_borrar_inv_{centro}_{edificio}_{espacio}"
                        ] = False
        
                        st.rerun()

        if not inventario:
            st.info("Este espacio todavía no tiene inventario. Usa la carga rápida inicial.")
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

        st.markdown("---")
        st.markdown("### ➕ Carga rápida inicial")

        num_elementos = st.number_input(
            "Número de elementos a introducir",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
            key=f"colegio_inv_num_elementos_{centro}_{edificio}_{espacio}"
        )

        opciones_base = list(obtener_elementos_catalogo_aulas())

        if "Otro" not in opciones_base:
            opciones_base.append("Otro")

        registros_a_guardar = []

        for i in range(int(num_elementos)):
            st.markdown(f"#### Elemento {i + 1}")

            c1, c2, c3 = st.columns([2, 1, 1])

            with c1:
                elemento = st.selectbox(
                    "Elemento",
                    opciones_base,
                    key=f"colegio_inv_rapido_elemento_{centro}_{edificio}_{espacio}_{i}"
                )

                if elemento == "Otro":
                    elemento = st.text_input(
                        "Especificar elemento",
                        key=f"colegio_inv_rapido_otro_{centro}_{edificio}_{espacio}_{i}"
                    )

            with c2:
                cantidad = st.number_input(
                    "Cantidad",
                    min_value=0,
                    step=1,
                    key=f"colegio_inv_rapido_cantidad_{centro}_{edificio}_{espacio}_{i}"
                )

            with c3:
                estado_item = st.selectbox(
                    "Estado",
                    ["Correcto", "Regular", "Dañado", "Falta", "Retirar"],
                    key=f"colegio_inv_rapido_estado_{centro}_{edificio}_{espacio}_{i}"
                )

            observaciones_inv = st.text_input(
                "Observaciones",
                key=f"colegio_inv_rapido_obs_{centro}_{edificio}_{espacio}_{i}"
            )

            foto_inv = st.file_uploader(
                "Foto",
                type=["jpg", "jpeg", "png"],
                key=f"colegio_inv_rapido_foto_{centro}_{edificio}_{espacio}_{i}"
            )

            if foto_inv is not None:
                st.image(foto_inv, width=180)

            registros_a_guardar.append(
                (elemento, cantidad, estado_item, observaciones_inv, foto_inv)
            )

            st.markdown("---")

        if st.button(
            "💾 Guardar inventario del espacio",
            key=f"colegio_guardar_inv_multiple_{centro}_{edificio}_{espacio}",
            use_container_width=True
        ):
            guardados = 0

            for elemento, cantidad, estado_item, observaciones_inv, foto_inv in registros_a_guardar:
                elemento = str(elemento or "").strip()

                if not elemento or cantidad <= 0:
                    continue

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
                    guardados += 1

            if guardados > 0:
                st.success(f"Inventario actualizado. Elementos guardados: {guardados}")
                st.rerun()
            else:
                st.warning("No hay elementos con cantidad para guardar.")
