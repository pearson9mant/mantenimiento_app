import streamlit as st
from pathlib import Path

from modules.inventario import (
    generar_codigo_material,
    crear_material_inventario,
    obtener_materiales_para_select,
    registrar_movimiento_inventario,
    obtener_material_por_codigo
)

from modules.ubicaciones import CENTROS, obtener_edificios, obtener_espacios


def pantalla_inventario():
    st.subheader("📦 Inventario mantenimiento")

    operario = st.session_state.get("operario_activo", "")

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
                ]
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

    materiales = obtener_materiales_para_select()

    if not materiales:
        st.info("No hay materiales en inventario.")
        return

    st.markdown("### 📋 Stock actual")

    for codigo, material, stock_actual, unidad in materiales:

        st.markdown("---")
        st.markdown(f"**{codigo}** · {material}")
        st.markdown(f"Stock: **{stock_actual} {unidad}**")

        datos_material = obtener_material_por_codigo(codigo)

        if datos_material:
            try:
                foto = datos_material[-1]

                if foto:
                    st.image(foto, width=220)

            except Exception:
                st.caption("Foto no disponible.")

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
