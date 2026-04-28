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


# -------------------------------
# CONFIGURACIÓN
# -------------------------------
st.set_page_config(page_title="Mantenimiento", layout="wide")


# -------------------------------
# ESTILO MÓVIL / MENÚ HORIZONTAL
# -------------------------------
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

div[role="radiogroup"] p {
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

h1, h2, h3 {
    margin-top: 0.4rem !important;
}

[data-testid="stMetricValue"] {
    font-size: 34px !important;
}
</style>
""", unsafe_allow_html=True)


# -------------------------------
# INICIO APP
# -------------------------------
inicializar_db()
login()

st.markdown("### Mantenimiento")
barra_sesion()

perfil = st.session_state.get("perfil", "")
operario_activo = st.session_state.get("operario_activo", "")


# -------------------------------
# VISTA OPERARIO DESDE ADMIN
# -------------------------------
if perfil == "admin" and st.session_state.get("vista_operario", False):
    pantalla_operario()

    st.markdown("---")
    if st.button("⬅ Volver a administración", key="volver_admin_desde_vista_operario"):
        st.session_state["vista_operario"] = False
        st.rerun()

    st.stop()


# -------------------------------
# ADMIN
# -------------------------------
if perfil == "admin":

    menu = st.radio(
        "",
        ["Panel", "Órdenes", "Inventario", "Legionella", "Operario", "Operarios"],
        horizontal=True,
        key="menu_admin_radio"
    )

    st.markdown("---")

    if menu == "Panel":
        pantalla_panel()

    elif menu == "Órdenes":
        pantalla_ordenes()

    elif menu == "Inventario":
        pantalla_inventario()

    elif menu == "Legionella":
        pantalla_legionella()

    elif menu == "Operario":
        pantalla_operario()

    elif menu == "Operarios":
        pantalla_operarios_admin()


# -------------------------------
# GERENCIA
# -------------------------------
elif perfil == "gerencia":

    menu = st.radio(
        "",
        ["Panel", "Órdenes", "Inventario"],
        horizontal=True,
        key="menu_gerencia_radio"
    )

    st.markdown("---")

    if menu == "Panel":
        pantalla_panel()

    elif menu == "Órdenes":
        pantalla_ordenes_lectura()

    elif menu == "Inventario":
        pantalla_inventario_lectura()


# -------------------------------
# OPERARIO
# -------------------------------
else:

    st.caption(f"{operario_activo}")

    menu = st.radio(
        "",
        ["Resumen", "Órdenes", "Inventario"],
        horizontal=True,
        key="menu_operario_radio"
    )

    st.markdown("---")

    if menu == "Resumen":
        pantalla_resumen_operario()

    elif menu == "Órdenes":
        pantalla_operario()

    elif menu == "Inventario":
        pantalla_inventario()
