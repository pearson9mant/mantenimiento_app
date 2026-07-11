import streamlit as st

from modules.inventario import obtener_materiales_para_select
from ui.ui_ot import mostrar_tarjeta_ot


def pantalla_trabajar_ot(
    fila,
    operario_sel="",
    modo="operario",
    clave_ot_abierta=None,
    texto_volver="⬅ Volver",
    key_boton_volver="volver_desde_trabajar_ot",
    titulo=None,
):
    """
    Pantalla única para trabajar una sola OT.

    Centraliza la carga pesada de materiales y la llamada a
    mostrar_tarjeta_ot(). El listado que abre esta pantalla continúa
    siendo ligero y solo debe guardar la OT seleccionada en session_state.
    """
    if not fila:
        st.error("No se ha encontrado la OT seleccionada.")
        return False

    try:
        numero_ot = fila[1]
    except Exception:
        numero_ot = ""

    if titulo is None:
        titulo = f"## 🛠️ Trabajar OT {numero_ot or ''}"

    st.markdown(titulo)

    if clave_ot_abierta:
        if st.button(
            texto_volver,
            key=key_boton_volver,
            use_container_width=True,
        ):
            st.session_state.pop(clave_ot_abierta, None)
            st.rerun()

    # La consulta de materiales solo se realiza al abrir una OT.
    try:
        materiales_select = obtener_materiales_para_select()
    except Exception as e:
        materiales_select = []
        st.caption(f"No se pudo cargar el selector de materiales: {e}")

    mostrar_tarjeta_ot(
        fila=fila,
        materiales_select=materiales_select,
        operario_sel=operario_sel,
        modo=modo,
    )

    return True
