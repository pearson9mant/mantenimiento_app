import streamlit as st


def usuario_actual():
    return st.session_state.get("usuario", "")


def rol_actual():
    return st.session_state.get("rol", "")


def es_admin():
    return rol_actual() == "admin"


def es_gerencia():
    return rol_actual() == "gerencia"


def es_operario():
    return rol_actual() == "operario"


def filtrar_ordenes_por_permiso(ordenes):
    """
    Admin y gerencia ven todo.
    Operario solo ve sus órdenes.
    """
    if not ordenes:
        return []

    if es_admin() or es_gerencia():
        return ordenes

    if es_operario():
        user = usuario_actual()
        return [
            o for o in ordenes
            if str(o.get("operario", "")).strip() == str(user).strip()
        ]

    return []
