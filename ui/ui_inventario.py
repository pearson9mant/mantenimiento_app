import streamlit as st

from modules.inventario import (
    obtener_materiales,
    registrar_movimiento_inventario,
    crear_material
)


def pantalla_inventario():
    st.subheader("📦 Inventario mantenimiento")

    operario = st.session_state.get("operario_activo", "")

    # -------------------------
    # NUEVO MATERIAL (solo Abel)
    # -------------------------
    if operario == "Abel Vasquez":
        with st.expander("➕ Crear nuevo material"):
            codigo = st.text_input("Código")
            nombre = st.text_input("Material")
            unidad = st.text_input("Unidad (uds, m, kg...)")

            if st.button("Crear material"):
                if codigo and nombre:
                    crear_material(codigo, nombre, unidad)
                    st.success("Material creado.")
                    st.rerun()
                else:
                    st.warning("Completa código y nombre.")

    # -------------------------
    # LISTADO
    # -------------------------
    materiales = obtener_materiales()

    if not materiales:
        st.info("No hay materiales en inventario.")
        return

    st.markdown("### 📋 Stock actual")

    for m in materiales:
        try:
            codigo, nombre, stock, unidad = m

            st.markdown("---")
            st.markdown(f"**{codigo}** · {nombre}")
            st.markdown(f"Stock: **{stock} {unidad}**")

            # -------------------------
            # MOVIMIENTO RÁPIDO
            # -------------------------
            c1, c2 = st.columns(2)

            with c1:
                entrada = st.number_input(
                    f"Entrada {codigo}",
                    min_value=0.0,
                    step=1.0,
                    key=f"ent_{codigo}"
                )

                if st.button(f"➕ Añadir {codigo}"):
                    if entrada > 0:
                        registrar_movimiento_inventario(
                            codigo_material=codigo,
                            tipo_movimiento="Entrada",
                            cantidad=entrada,
                            motivo="Entrada manual",
                            numero_ot="",
                            operario=operario
                        )
                        st.rerun()

            with c2:
                salida = st.number_input(
                    f"Salida {codigo}",
                    min_value=0.0,
                    step=1.0,
                    key=f"sal_{codigo}"
                )

                if st.button(f"➖ Quitar {codigo}"):
                    if salida > 0:
                        registrar_movimiento_inventario(
                            codigo_material=codigo,
                            tipo_movimiento="Salida",
                            cantidad=salida,
                            motivo="Salida manual",
                            numero_ot="",
                            operario=operario
                        )
                        st.rerun()

        except Exception:
            pass
