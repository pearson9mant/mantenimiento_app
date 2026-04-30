import streamlit as st

from modules.ubicaciones import (
    CENTROS,
    obtener_edificios,
    obtener_ubicaciones_personalizadas,
    crear_espacio_personalizado,
    activar_desactivar_espacio
)


def pantalla_configuracion():
    st.subheader("⚙️ Configuración")

    tab1, tab2 = st.tabs(["➕ Añadir espacio", "📋 Espacios creados"])

    with tab1:
        st.markdown("### Añadir nuevo espacio")

        centro = st.selectbox("Centro", CENTROS, key="cfg_centro")

        edificios = obtener_edificios(centro)

        edificio = st.selectbox("Edificio", edificios, key="cfg_edificio")

        espacio = st.text_input(
            "Nuevo espacio",
            placeholder="Ejemplo: Sala psicomotricidad, Almacén, Despacho..."
        )

        if st.button("➕ Crear espacio", use_container_width=True):
            ok, mensaje = crear_espacio_personalizado(
                centro=centro,
                edificio=edificio,
                espacio=espacio
            )

            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.warning(mensaje)

    with tab2:
        st.markdown("### Espacios personalizados")

        ubicaciones = obtener_ubicaciones_personalizadas()

        if not ubicaciones:
            st.info("Todavía no hay espacios personalizados.")
            return

        for id_ubicacion, centro, edificio, espacio, activo in ubicaciones:
            icono = "✅" if activo else "⛔"
            titulo = f"{icono} {centro} · {edificio} · {espacio}"

            with st.expander(titulo, expanded=False):
                st.markdown(f"**Centro:** {centro}")
                st.markdown(f"**Edificio:** {edificio}")
                st.markdown(f"**Espacio:** {espacio}")
                st.markdown(f"**Estado:** {'Activo' if activo else 'Desactivado'}")

                if activo:
                    if st.button(
                        f"⛔ Desactivar {espacio}",
                        key=f"desactivar_espacio_{id_ubicacion}",
                        use_container_width=True
                    ):
                        activar_desactivar_espacio(id_ubicacion, 0)
                        st.rerun()
                else:
                    if st.button(
                        f"✅ Activar {espacio}",
                        key=f"activar_espacio_{id_ubicacion}",
                        use_container_width=True
                    ):
                        activar_desactivar_espacio(id_ubicacion, 1)
                        st.rerun()
