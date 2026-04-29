import streamlit as st

from modules.inventario import (
    obtener_materiales_para_select,
    registrar_movimiento_inventario
)


def pantalla_inventario():
    st.subheader("📦 Inventario mantenimiento")

    operario = st.session_state.get("operario_activo", "")

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
                    registrar_movimiento_inventario(
                        codigo_material=codigo,
                        tipo_movimiento="Entrada",
                        cantidad=entrada,
                        motivo="Entrada manual",
                        numero_ot="",
                        operario=operario
                    )
                    st.success("Entrada registrada.")
                    st.rerun()

        with c2:
            salida = st.number_input(
                f"Salida {codigo}",
                min_value=0.0,
                step=1.0,
                key=f"salida_{codigo}"
            )

            if st.button(f"➖ Quitar {codigo}", key=f"btn_salida_{codigo}"):
                if salida > 0:
                    registrar_movimiento_inventario(
                        codigo_material=codigo,
                        tipo_movimiento="Salida",
                        cantidad=salida,
                        motivo="Salida manual",
                        numero_ot="",
                        operario=operario
                    )
                    st.success("Salida registrada.")
                    st.rerun()
