import pandas as pd
import streamlit as st
from config import CATEGORIAS_INVENTARIO, CENTROS, EDIFICIOS
from modules.inventario import obtener_materiales_inventario, obtener_stock_bajo


def descomponer_material(fila):
    valores = list(fila) + [""] * 20

    return {
        "id": valores[0],
        "codigo": valores[1],
        "material": valores[2],
        "categoria": valores[3],
        "unidad": valores[4],
        "stock_actual": valores[5],
        "stock_minimo": valores[6],
        "centro": valores[7],
        "edificio": valores[8],
        "ubicacion": valores[9],
        "proveedor": valores[10],
        "observaciones": valores[11],
        "fecha_alta": valores[12],
        "foto": valores[13],
        "activo": valores[14],
        "precio_unitario": valores[15],
        "coste_total": valores[16],
        "fecha_compra": valores[17],
        "referencia_factura": valores[18],
        "observaciones_coste": valores[19],
    }


def pantalla_inventario_lectura():
    st.subheader("📦 Inventario")

    tab1, tab2 = st.tabs(["Listado", "Stock bajo"])

    with tab1:
        f1, f2, f3, f4 = st.columns(4)

        with f1:
            filtro_txt = st.text_input("Buscar", key="lect_txt_inv")

        with f2:
            filtro_cat = st.selectbox("Categoría", ["Todas"] + CATEGORIAS_INVENTARIO, key="lect_cat_inv")

        with f3:
            filtro_centro = st.selectbox("Centro", ["Todos"] + CENTROS, key="lect_centro_inv")

        with f4:
            if filtro_centro == "Todos":
                edificios_filtro = ["Todos"]
                for lista in EDIFICIOS.values():
                    for ed in lista:
                        if ed not in edificios_filtro:
                            edificios_filtro.append(ed)
            else:
                edificios_filtro = ["Todos"] + EDIFICIOS.get(filtro_centro, [])

            filtro_edificio = st.selectbox("Edificio", edificios_filtro, key="lect_edificio_inv")

        materiales = obtener_materiales_inventario(
            filtro_texto=filtro_txt,
            filtro_categoria=filtro_cat,
            filtro_centro=filtro_centro,
            filtro_edificio=filtro_edificio
        )

        if materiales:
            datos = []

            for fila in materiales:
                m = descomponer_material(fila)

                stock_actual = float(m["stock_actual"] or 0)
                stock_minimo = float(m["stock_minimo"] or 0)

                estado_stock = "OK"
                if stock_actual <= 0:
                    estado_stock = "AGOTADO"
                elif stock_actual <= stock_minimo:
                    estado_stock = "BAJO"

                datos.append({
                    "CÓDIGO": m["codigo"],
                    "MATERIAL": m["material"],
                    "CATEGORÍA": m["categoria"],
                    "UNIDAD": m["unidad"],
                    "STOCK": stock_actual,
                    "MÍNIMO": stock_minimo,
                    "ESTADO": estado_stock,
                    "CENTRO": m["centro"],
                    "EDIFICIO": m["edificio"],
                    "UBICACIÓN": m["ubicacion"],
                    "PROVEEDOR": m["proveedor"],
                    "PRECIO UNIT.": m["precio_unitario"],
                    "COSTE TOTAL": m["coste_total"],
                })

            st.dataframe(pd.DataFrame(datos), use_container_width=True)
        else:
            st.info("No hay materiales para esos filtros.")

    with tab2:
        stock_bajo = obtener_stock_bajo()

        if stock_bajo:
            datos = []

            for fila in stock_bajo:
                m = descomponer_material(fila)

                stock_actual = float(m["stock_actual"] or 0)
                stock_minimo = float(m["stock_minimo"] or 0)

                estado = "BAJO"
                if stock_actual <= 0:
                    estado = "AGOTADO"

                datos.append({
                    "CÓDIGO": m["codigo"],
                    "MATERIAL": m["material"],
                    "CATEGORÍA": m["categoria"],
                    "STOCK": stock_actual,
                    "MÍNIMO": stock_minimo,
                    "ESTADO": estado,
                    "CENTRO": m["centro"],
                    "EDIFICIO": m["edificio"],
                    "UBICACIÓN": m["ubicacion"],
                    "PROVEEDOR": m["proveedor"],
                    "COSTE TOTAL": m["coste_total"],
                })

            st.dataframe(pd.DataFrame(datos), use_container_width=True)
        else:
            st.success("No hay materiales por debajo del stock mínimo.")
