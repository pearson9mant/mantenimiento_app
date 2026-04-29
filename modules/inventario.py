import streamlit as st

from modules.inventario import (
    generar_codigo_material,
    crear_material_inventario,
    obtener_materiales_para_select,
    registrar_movimiento_inventario
)


def pantalla_inventario():
    st.subheader("📦 Inventario mantenimiento")

    operario = st.session_state.get("operario_activo", "")

    # -------------------------
    # ➕ CREAR MATERIAL
    # -------------------------
    if operario == "Abel Vasquez":
        with st.expander("➕ Crear material nuevo"):
            material = st.text_input("Nombre material")
            categoria = st.selectbox(
                "Categoría",
                ["Electricidad", "Fontanería", "Climatización", "Ferretería", "Pintura", "Limpieza", "Otros"]
            )
            unidad = st.text_input("Unidad", value="uds")
            stock_actual = st.number_input("Stock inicial", min_value=0.0, step=1.0)
            stock_minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0)

            centro = st.selectbox("Centro", ["Pearson 22", "Pearson 9"])
            edificio = st.text_input("Edificio")
            ubicacion = st.text_input("Ubicación")
            proveedor = st.text_input("Proveedor")
            observaciones = st.text_area("Observaciones")

            if st.button("Crear material", use_container_width=True):
                if not material.strip():
                    st.warning("Indica el nombre del material.")
                else:
                    codigo = generar_codigo_material(material, categoria)

                    crear_material_inventario(
                        codigo=codigo,
                        material=material,
                        categoria=categoria,
                        unidad=unidad,
                        stock_actual=stock_actual,
                        stock_minimo=stock_minimo,
                        centro=centro,
                        edificio=edificio,
                        ubicacion=ubicacion,
                        proveedor=proveedor,
                        observaciones=observaciones
                    )

                    st.success(f"Material creado correctamente: {codigo}")
                    st.rerun()

    # -------------------------
    # 📦 LISTADO
    # -------------------------
    materiales = obtener_materiales_para_select()

    if not materiales:
        st.info("No hay materiales en inventario.")
        return

    st.markdown("### 📋 Stock actual")

    for codigo, material, stock_actual, unidad in materiales:

        st.markdown("---")
        st.markdown(f"**{codigo}** · {material}")
        st.markdown(f"Stock: **{stock_actual} {unidad}**")

        c1, c2 = st.columns(2)

        with c1:
            entrada = st.number_input(
                f"Entrada {codigo}",
                min_value=0.0,
                step=1.0,
                key=f"entrada_{codigo}"
            )

            if st.button(f"➕ Añadir {codigo}", key=f"btn_entrada_{codigo}"):
                if entrada > 0:
                    ok, mensaje = registrar_movimiento_inventario(
                        codigo_material=codigo,
                        tipo_movimiento="Entrada",
                        cantidad=entrada,
                        motivo="Entrada manual",
                        numero_ot="",
                        operario=operario
                    )

                    if ok:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)

        with c2:
            salida = st.number_input(
                f"Salida {codigo}",
                min_value=0.0,
                step=1.0,
                key=f"salida_{codigo}"
            )

            if st.button(f"➖ Quitar {codigo}", key=f"btn_salida_{codigo}"):
                if salida > 0:
                    ok, mensaje = registrar_movimiento_inventario(
                        codigo_material=codigo,
                        tipo_movimiento="Salida",
                        cantidad=salida,
                        motivo="Salida manual",
                        numero_ot="",
                        operario=operario
                    )

                    if ok:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)

