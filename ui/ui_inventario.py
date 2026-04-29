import streamlit as st
from pathlib import Path

from modules.inventario import (
    generar_codigo_material,
    crear_material_inventario,
    obtener_materiales_inventario,
    registrar_movimiento_inventario,
    obtener_movimientos_por_material
)

from modules.ubicaciones import CENTROS, obtener_edificios, obtener_espacios


def pantalla_inventario():
    st.subheader("📦 Inventario mantenimiento")

    operario = st.session_state.get("operario_activo", "")

    # -------------------------
    # CREAR MATERIAL NUEVO
    # -------------------------
    if operario == "Abel Vasquez":
        with st.expander("➕ Crear material nuevo"):

            material = st.text_input("Nombre material")

            categoria = st.selectbox(
                "Categoría",
                [
                    "Electricidad",
                    "Fontanería",
                    "Climatización",
                    "Ferretería",
                    "Pintura",
                    "Limpieza",
                    "Otros"
                ],
                key="crear_categoria_material"
            )

            unidad = st.text_input("Unidad", value="uds")
            stock_actual = st.number_input("Stock inicial", min_value=0.0, step=1.0)
            stock_minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0)

            centro = st.selectbox(
                "Centro",
                CENTROS,
                key="inv_mat_centro"
            )

            edificios = obtener_edificios(centro)

            edificio = st.selectbox(
                "Edificio",
                edificios,
                key="inv_mat_edificio"
            )

            espacios = obtener_espacios(edificio)

            ubicacion = st.selectbox(
                "Aula / Espacio / Ubicación",
                espacios,
                key="inv_mat_ubicacion"
            )

            proveedor = st.text_input("Proveedor")
            observaciones = st.text_area("Observaciones")

            foto_subida = st.file_uploader(
                "Foto del material",
                type=["jpg", "jpeg", "png"],
                key="foto_material_mantenimiento"
            )

            ruta_foto = ""

            if foto_subida is not None:
                carpeta = Path("data/fotos_inventario")
                carpeta.mkdir(parents=True, exist_ok=True)

                nombre_foto = f"{centro}_{edificio}_{ubicacion}_{material}_{foto_subida.name}".replace(" ", "_")
                ruta_foto = str(carpeta / nombre_foto)

                with open(ruta_foto, "wb") as f:
                    f.write(foto_subida.getbuffer())

                st.image(ruta_foto, width=250)

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
                        observaciones=observaciones,
                        foto=ruta_foto
                    )

                    st.success(f"Material creado correctamente: {codigo}")
                    st.rerun()

    # -------------------------
    # BUSCADOR / FILTROS
    # -------------------------
    st.markdown("### 🔎 Buscar material")

    filtro_texto = st.text_input(
        "Buscar por código, material, ubicación o proveedor",
        key="filtro_texto_inventario"
    )

    f1, f2 = st.columns(2)

    with f1:
        filtro_centro = st.selectbox(
            "Centro",
            ["Todos"] + CENTROS,
            key="filtro_centro_inventario"
        )

    with f2:
        if filtro_centro != "Todos":
            edificios_filtro = obtener_edificios(filtro_centro)
        else:
            edificios_filtro = []

        filtro_edificio = st.selectbox(
            "Edificio",
            ["Todos"] + edificios_filtro,
            key="filtro_edificio_inventario"
        )

    filtro_categoria = st.selectbox(
        "Categoría",
        [
            "Todas",
            "Electricidad",
            "Fontanería",
            "Climatización",
            "Ferretería",
            "Pintura",
            "Limpieza",
            "Otros"
        ],
        key="filtro_categoria_inventario"
    )

    materiales = obtener_materiales_inventario(
        filtro_texto=filtro_texto,
        filtro_categoria=filtro_categoria,
        filtro_centro=filtro_centro,
        filtro_edificio=filtro_edificio
    )

    if not materiales:
        st.info("No hay materiales con esos filtros.")
        return

    st.markdown(f"### 📋 Stock actual ({len(materiales)})")

    for m in materiales:
        try:
            (
                id_mat,
                codigo,
                material,
                categoria,
                unidad,
                stock_actual,
                stock_minimo,
                centro,
                edificio,
                ubicacion,
                proveedor,
                observaciones,
                fecha_alta,
                foto
            ) = m
        except ValueError:
            (
                id_mat,
                codigo,
                material,
                categoria,
                unidad,
                stock_actual,
                stock_minimo,
                centro,
                edificio,
                ubicacion,
                proveedor,
                observaciones,
                fecha_alta
            ) = m
            foto = ""

        st.markdown("---")

        if stock_actual <= stock_minimo:
            st.warning(f"⚠️ Stock bajo: {material} ({stock_actual} {unidad})")

        st.markdown(f"### **{codigo}** · {material}")
        st.markdown(f"**Categoría:** {categoria or '-'}")
        st.markdown(f"**Stock:** {stock_actual} {unidad} · **Mínimo:** {stock_minimo} {unidad}")
        st.caption(f"🏢 {centro or '-'} · {edificio or '-'} · {ubicacion or '-'}")

        if proveedor:
            st.caption(f"Proveedor: {proveedor}")

        if observaciones:
            st.info(observaciones)

        if foto:
            try:
                st.image(foto, width=220)
            except Exception:
                st.caption("Foto no disponible.")

        # -------------------------
        # HISTORIAL POR MATERIAL
        # -------------------------
        with st.expander(f"📊 Historial {codigo}"):

            movimientos = obtener_movimientos_por_material(codigo)

            if not movimientos:
                st.info("Sin movimientos.")
            else:
                for mov in movimientos[:20]:
                    tipo, cantidad, motivo, ot, operario_mov, fecha = mov

                    icono = "➕" if tipo == "Entrada" else "➖"

                    st.markdown(
                        f"{icono} **{tipo}** · {cantidad}  \n"
                        f"📅 {fecha} · 👷 {operario_mov or '-'}  \n"
                        f"🛠 OT: {ot or '-'}  \n"
                        f"📝 {motivo or '-'}"
                    )
                    st.markdown("---")

        # -------------------------
        # ENTRADAS / SALIDAS
        # -------------------------
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
