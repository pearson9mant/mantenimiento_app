def mostrar_detalle_inventario_total(centro):
    inventario = preparar_inventario()
    datos = filtrar_inventario_por_centro(inventario, centro)

    if datos.empty:
        st.info("No hay inventario registrado para mostrar.")
        return

    st.metric("💰 Total inventario", euros(datos["valor_total"].sum()))

    datos = buscador_dataframe(
        datos,
        key=f"buscador_inv_gerencia_{centro}",
        placeholder="Buscar material, código, ubicación o proveedor..."
    )

    for _, row in datos.iterrows():

        id_material = row.get("id", None)
        codigo = row.get("codigo", "")
        material = row.get("material_mostrar", "")
        categoria = row.get("categoria", "")
        stock = row.get("stock_num", 0)

        precio = row.get("precio_num", 0)
        valor = row.get("valor_total", 0)

        ubicacion = row.get("ubicacion", "")
        fecha_compra = row.get("fecha_compra", "")

        foto = row.get("foto", "")
        foto_data = obtener_foto_inventario_por_id(id_material)

        with st.expander(
            f"📦 {codigo} · {material} · Stock: {stock}",
            expanded=False
        ):

            st.markdown(f"### {material}")

            st.caption(
                f"🏷️ {categoria or '-'} · "
                f"📍 {ubicacion or '-'}"
            )

            st.markdown(f"**Precio unitario:** {euros(precio)}")
            st.markdown(f"**Valor inventario:** {euros(valor)}")

            if fecha_compra:
                st.caption(f"📅 {fecha_compra}")

            if foto_data:
                try:
                    st.image(bytes(foto_data), width=220)
                except Exception:
                    st.caption("Foto no disponible.")

            elif foto:
                try:
                    st.image(foto, width=220)
                except Exception:
                    st.caption("Foto no disponible.")
