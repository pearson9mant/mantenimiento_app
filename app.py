import streamlit as st
from modules.auth import login, barra_sesion
from database.db import inicializar_db

from ui.ui_panel import pantalla_panel
from ui.ui_ordenes import pantalla_ordenes
from ui.ui_ordenes_lectura import pantalla_ordenes_lectura
from ui.ui_inventario import pantalla_inventario
from ui.ui_inventario_lectura import pantalla_inventario_lectura
from ui.ui_operario import pantalla_operario
from ui.ui_resumen_operario import pantalla_resumen_operario
from ui.ui_legionella import pantalla_legionella
from ui.ui_operarios_admin import pantalla_operarios_admin


st.set_page_config(page_title="Mantenimiento", layout="wide")


st.markdown("""
<meta name="google" content="notranslate">

<style>
html, body {
    font-size: 14px !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    gap: 10px !important;
    align-items: center !important;
}

div[role="radiogroup"] label {
    white-space: nowrap !important;
    min-width: fit-content !important;
    padding: 8px 10px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
}

.stButton > button {
    width: 100%;
    min-height: 42px;
    font-size: 14px !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
}

[data-testid="stMetricValue"] {
    font-size: 34px !important;
}
</style>
""", unsafe_allow_html=True)


def volver_menu():
    st.session_state["seccion_actual"] = None
    for key in ["menu_admin_radio", "menu_gerencia_radio", "menu_operario_radio"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def mostrar_menu_admin():
    opciones = [
        "Selecciona",
        "Panel",
        "Órdenes",
        "Inventario",
        "Legionella",
        "Operario",
        "Operarios"
    ]

    menu = st.radio(
        "",
        opciones,
        horizontal=True,
        key="menu_admin_radio"
    )

    if menu != "Selecciona":
        st.session_state["seccion_actual"] = menu
        st.rerun()


def mostrar_menu_gerencia():
    opciones = [
        "Selecciona",
        "Panel",
        "Órdenes",
        "Inventario"
    ]

    menu = st.radio(
        "",
        opciones,
        horizontal=True,
        key="menu_gerencia_radio"
    )

    if menu != "Selecciona":
        st.session_state["seccion_actual"] = menu
        st.rerun()


def mostrar_menu_operario():
    opciones = [
        "Selecciona",
        "Resumen",
        "Órdenes",
        "Inventario"
    ]

    menu = st.radio(
        "",
        opciones,
        horizontal=True,
        key="menu_operario_radio"
    )

    if menu != "Selecciona":
        st.session_state["seccion_actual"] = menu
        st.rerun()


inicializar_db()
login()

st.markdown("### Mantenimiento")
barra_sesion()

perfil = st.session_state.get("perfil", "")
operario_activo = st.session_state.get("operario_activo", "")

if "seccion_actual" not in st.session_state:
    st.session_state["seccion_actual"] = None


if perfil == "admin" and st.session_state.get("vista_operario", False):
    pantalla_operario()

    st.markdown("---")
    if st.button("⬅ Volver a administración", key="volver_admin_desde_vista_operario"):
        st.session_state["vista_operario"] = False
        st.rerun()

    st.stop()


# -------------------------------
# MENÚ GENERAL
# -------------------------------
if st.session_state["seccion_actual"] is None:

    if perfil == "admin":
        mostrar_menu_admin()

    elif perfil == "gerencia":
        mostrar_menu_gerencia()

    else:
        st.caption(f"{operario_activo}")
        mostrar_menu_operario()

    st.stop()


# -------------------------------
# BOTÓN VOLVER
# -------------------------------
if st.button("⬅ Volver al menú", key="volver_menu_general"):
    volver_menu()

st.markdown("---")

seccion = st.session_state["seccion_actual"]


# -------------------------------
# ADMIN
# -------------------------------
if perfil == "admin":

    if seccion == "Panel":
        pantalla_panel()

    elif seccion == "Órdenes":
        pantalla_ordenes()

    elif seccion == "Inventario":
        pantalla_inventario()

    elif seccion == "Legionella":
        pantalla_legionella()

    elif seccion == "Operario":
        pantalla_operario()

    elif seccion == "Operarios":
        pantalla_operarios_admin()


# -------------------------------
# GERENCIA
# -------------------------------
elif perfil == "gerencia":

    if seccion == "Panel":
        pantalla_panel()

    elif seccion == "Órdenes":
        pantalla_ordenes_lectura()

    elif seccion == "Inventario":
        pantalla_inventario_lectura()


# -------------------------------
# OPERARIO
# -------------------------------
else:

    st.caption(f"{operario_activo}")

    if seccion == "Resumen":
        pantalla_resumen_operario()

    elif seccion == "Órdenes":
        pantalla_operario()

    elif seccion == "Inventario":
        pantalla_inventario()
