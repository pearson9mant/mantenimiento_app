import sqlite3
import pandas as pd
import streamlit as st

from config import (
    CATEGORIAS_INVENTARIO,
    UNIDADES_INVENTARIO,
    TIPOS_MOVIMIENTO,
    CENTROS,
    EDIFICIOS,
    OPERARIOS_CON_ALTA_MATERIAL,
)
from modules.inventario import (
    generar_codigo_material,
    crear_material_inventario,
    obtener_materiales_inventario,
    obtener_codigos_materiales,
    registrar_movimiento_inventario,
    obtener_movimientos_inventario,
    obtener_stock_bajo
)

def pantalla_inventario():
    st.subheader("📦 Inventario")

    perfil = st.session_state.get("perfil", "")
    operario_activo = st.session_state.get("operario_activo", "")

    puede_dar_alta = perfil == "admin" or operario_activo in OPERARIOS_CON_ALTA_MATERIAL

    tab1, tab2, tab3 = st.tabs(["Materiales", "Movimientos", "Stock bajo"])

    with tab1:
        if puede_dar_alta:
            st.markdown("### Alta de material")

            c1, c2 = st.columns(2)

            with c1:
                material = st.text_input("Material")
                categoria = st.selectbox("Categoría", CATEGORIAS_INVENTARIO)
                unidad = st.selectbox("Unidad", UNIDADES_INVENTARIO)
                stock_actual = st.number_input("Stock actual", min_value=0.0, step=1.0)
                stock_minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0)

            with c2:
                centro = st.selectbox("Centro", CENTROS, key="inv_centro_alta")
                edificios_disponibles = EDIFICIOS.get(centro, [])
                edificio = st.selectbox("Edificio", edificios_disponibles, key="inv_edificio_alta")
                ubicacion = st.text_input("Ubicación")
                proveedor = st.text_input("Proveedor")
                observaciones = st.text_area("Observaciones")

            codigo_sugerido = ""
            if material.strip():
                codigo_sugerido = generar_codigo_material(material, categoria)
                st.info(f"Código sugerido: {codigo_sugerido}")

            if st.button("Guardar material", use_container_width=True, key="btn_guardar_material"):
                if not material.strip():
                    st.warning("Escribe el nombre del material.")
                else:
                    try:
                        codigo_final = codigo_sugerido if codigo_sugerido else generar_codigo_material(material, categoria)
                        crear_material_inventario(
                            codigo_final,
                            material,
                            categoria,
                            unidad,
                            stock_actual,
                            stock_minimo,
                            centro,
                            edificio,
                            ubicacion,
                            proveedor,
                            observaciones
                        )
                        st.success(f"Material guardado con código {codigo_final}.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe un material con ese código.")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
        else:
            st.info(f"{operario_activo} no tiene permiso para dar de alta materiales.")

        st.divider()
        st.markdown("### Listado de materiales")

        f1, f2, f3, f4 = st.columns(4)

        with f1:
            filtro_txt = st.text_input("Buscar", key="filtro_txt_inv")

        with f2:
            filtro_cat = st.selectbox("Categoría", ["Todas"] + CATEGORIAS_INVENTARIO, key="filtro_cat_inv")

        with f3:
            filtro_centro = st.selectbox("Centro", ["Todos"] + CENTROS, key="filtro_centro_inv")

        with f4:
            if filtro_centro == "Todos":
                edificios_filtro = ["Todos"]
                for lista in EDIFICIOS.values():
                    for ed in lista:
                        if ed not in edificios_filtro:
                            edificios_filtro.append(ed)
            else:
                edificios_filtro = ["Todos"] + EDIFICIOS.get(filtro_centro, [])

            filtro_edificio = st.selectbox("Edificio", edificios_filtro, key="filtro_edificio_inv")

        materiales = obtener_materiales_inventario(
            filtro_texto=filtro_txt,
            filtro_categoria=filtro_cat,
            filtro_centro=filtro_centro,
            filtro_edificio=filtro_edificio
        )

        st.caption(f"Materiales mostrados: {len(materiales)}")

        if materiales:
            datos = []
            for fila in materiales:
                _, codigo, material, categoria, unidad, stock_actual, stock_minimo, centro, edificio, ubicacion, proveedor, observaciones, fecha_alta = fila

                estado_stock = "OK"
                if stock_actual <= 0:
                    estado_stock = "AGOTADO"
                elif stock_actual <= stock_minimo:
                    estado_stock = "BAJO"

                datos.append({
                    "CÓDIGO": codigo,
                    "MATERIAL": material,
                    "CATEGORÍA": categoria,
                    "UNIDAD": unidad,
                    "STOCK": stock_actual,
                    "MÍNIMO": stock_minimo,
                    "ESTADO": estado_stock,
                    "CENTRO": centro,
                    "EDIFICIO": edificio,
                    "UBICACIÓN": ubicacion,
                    "PROVEEDOR": proveedor
                })

            st.dataframe(pd.DataFrame(datos), use_container_width=True)
        else:
            st.info("No hay materiales para esos filtros.")

    with tab2:
        st.markdown("### Registrar movimiento")

        codigos = obtener_codigos_materiales()
        opciones_material = [f"{codigo} | {material}" for codigo, material in codigos]

        if opciones_material:
            c1, c2 = st.columns(2)

            with c1:
                seleccion_material = st.selectbox("Material", opciones_material, key="mov_material")
                tipo_mov = st.selectbox("Tipo de movimiento", TIPOS_MOVIMIENTO, key="mov_tipo")
                cantidad_mov = st.number_input("Cantidad", min_value=0.0, step=1.0, key="mov_cantidad")

            with c2:
                motivo_mov = st.text_input("Motivo", key="mov_motivo")
                numero_ot_mov = st.text_input("Nº OT (opcional)", key="mov_ot")

                if perfil == "admin":
                    operario_mov = st.text_input("Operario", key="mov_operario")
                else:
                    operario_mov = operario_activo

            if st.button("Guardar movimiento", use_container_width=True, key="btn_guardar_movimiento"):
                codigo_sel = seleccion_material.split(" | ")[0]

                if cantidad_mov <= 0:
                    st.warning("La cantidad debe ser mayor que 0.")
                else:
                    ok, mensaje = registrar_movimiento_inventario(
                        codigo_material=codigo_sel,
                        tipo_movimiento=tipo_mov,
                        cantidad=cantidad_mov,
                        motivo=motivo_mov,
                        numero_ot=numero_ot_mov,
                        operario=operario_mov
                    )
                    if ok:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)
        else:
            st.info("Primero debes dar de alta materiales.")

        st.divider()
        st.markdown("### Histórico de movimientos")

        movimientos = obtener_movimientos_inventario()

        if movimientos:
            datos = []
            for fila in movimientos:
                _, codigo_material, material, tipo_movimiento, cantidad, motivo, numero_ot, operario, fecha_movimiento = fila
                datos.append({
                    "FECHA": fecha_movimiento,
                    "CÓDIGO": codigo_material,
                    "MATERIAL": material,
                    "TIPO": tipo_movimiento,
                    "CANTIDAD": cantidad,
                    "MOTIVO": motivo,
                    "Nº OT": numero_ot,
                    "OPERARIO": operario
                })

            st.dataframe(pd.DataFrame(datos), use_container_width=True)
        else:
            st.info("Todavía no hay movimientos registrados.")

    with tab3:
        st.markdown("### Materiales con stock bajo")

        stock_bajo = obtener_stock_bajo()

        if stock_bajo:
            datos = []
            for fila in stock_bajo:
                _, codigo, material, categoria, unidad, stock_actual, stock_minimo, centro, edificio, ubicacion, proveedor, observaciones, fecha_alta = fila

                estado = "BAJO"
                if stock_actual <= 0:
                    estado = "AGOTADO"

                datos.append({
                    "CÓDIGO": codigo,
                    "MATERIAL": material,
                    "CATEGORÍA": categoria,
                    "STOCK": stock_actual,
                    "MÍNIMO": stock_minimo,
                    "ESTADO": estado,
                    "CENTRO": centro,
                    "EDIFICIO": edificio,
                    "UBICACIÓN": ubicacion,
                    "PROVEEDOR": proveedor
                })

            st.dataframe(pd.DataFrame(datos), use_container_width=True)
        else:
            st.success("No hay materiales por debajo del stock mínimo.")