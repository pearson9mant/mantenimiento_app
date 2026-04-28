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
# ESTILO MÓVIL
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

.stButton > button {
    width: 100%;
    min-height: 44px;
    font-size: 14px !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    padding: 0.4rem 0.5rem !important;
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
# FUNCIONES MENÚ
# -------------------------------
def boton_menu(nombre, clave, destino):
    if st.button(nombre, key=clave):
        st.session_state["menu_actual"] = destino
        st.rerun()


def menu_admin():
    if "menu_actual" not in st.session_state:
        st.session_state["menu_actual"] = "Panel"

    col1, col2, col3 = st.columns(3)
    with col1:
        boton_menu("📊 Panel", "btn_panel_admin", "Panel")
    with col2:
        boton_menu("🛠 Órdenes", "btn_ordenes_admin", "Ordenes")
    with col3:
        boton_menu("📦 Inventario", "btn_inventario_admin", "Inventario")

    col4, col5, col6 = st.columns(3)
    with col4:
        boton_menu("💧 Legionella", "btn_legionella_admin", "Legionella")
    with col5:
        boton_menu("👷 Operario", "btn_operario_admin", "Operario")
    with col6:
        boton_menu("⚙️ Operarios", "btn_operarios_admin", "Operarios")


def menu_gerencia():
    if "menu_actual" not in st.session_state:
        st.session_state["menu_actual"] = "Panel"

    col1, col2, col3 = st.columns(3)
    with col1:
        boton_menu("📊 Panel", "btn_panel_gerencia", "Panel")
    with col2:
        boton_menu("🛠 Órdenes", "btn_ordenes_gerencia", "Ordenes")
    with col3:
        boton_menu("📦 Inventario", "btn_inventario_gerencia", "Inventario")


def menu_operario():
    if "menu_actual" not in st.session_state:
        st.session_state["menu_actual"] = "Resumen"

    col1, col2, col3 = st.columns(3)
    with col1:
        boton_menu("📋 Resumen", "btn_resumen_operario", "Resumen")
    with col2:
        boton_menu("🛠 Órdenes", "btn_ordenes_operario", "Ordenes")
    with col3:
        boton_menu("📦 Inventario", "btn_inventario_operario", "Inventario")


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

    menu_admin()
    st.markdown("---")

    menu = st.session_state.get("menu_actual", "Panel")

    if menu == "Panel":
        pantalla_panel()

    elif menu == "Ordenes":
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

    menu_gerencia()
    st.markdown("---")

    menu = st.session_state.get("menu_actual", "Panel")

    if menu == "Panel":
        pantalla_panel()

    elif menu == "Ordenes":
        pantalla_ordenes_lectura()

    elif menu == "Inventario":
        pantalla_inventario_lectura()


# -------------------------------
# OPERARIO
# -------------------------------
else:

    st.caption(f"{operario_activo}")

    menu_operario()
    st.markdown("---")

    menu = st.session_state.get("menu_actual", "Resumen")

    if menu == "Resumen":
        pantalla_resumen_operario()

    elif menu == "Ordenes":
        pantalla_operario()

    elif menu == "Inventario":
        pantalla_inventario()
