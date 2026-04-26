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
# CONFIG
# -------------------------------
st.set_page_config(page_title="Mantenimiento", layout="wide")

inicializar_db()
login()

# -------------------------------
# ESTILO MÓVIL / MENÚ
# -------------------------------
st.markdown("""
<style>
div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    justify-content: center !important;
    gap: 0.35rem;
    flex-wrap: wrap;
}
div[role="radiogroup"] label {
    margin: 0 !important;
    padding: 0.4rem 0.6rem !important;
}
div[role="radiogroup"] label {
    font-size: 20px !important;
    font-weight: bold;
    padding: 8px 12px;
}
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# HEADER COMPACTO
# -------------------------------
st.markdown("### 🛠 Mantenimiento")
barra_sesion()

perfil = st.session_state.get("perfil", "")
operario_activo = st.session_state.get("operario_activo", "")

# -------------------------------
# MODO VISTA OPERARIO DESDE ADMIN
# -------------------------------
if perfil == "admin" and st.session_state.get("vista_operario", False):
    pantalla_operario()

    st.markdown("---")
    if st.button("🔙 Volver a administración", key="volver_admin_desde_vista_operario"):
        st.session_state["vista_operario"] = False
        st.rerun()

    st.stop()

# -------------------------
# ADMIN
# -------------------------
if perfil == "admin":

    menu = st.radio(
        "",
        ["Panel", "OT", "Inv.", " Leg.", " Op.", " Operarios"],
        horizontal=True,
        key="menu_admin_radio"
    )

    st.markdown("---")

    if menu == " Panel":
        pantalla_panel()

    elif menu == " OT":
        pantalla_ordenes()

    elif menu == " Inv.":
        pantalla_inventario()

    elif menu == " Leg.":
        pantalla_legionella()

    elif menu == " Op.":
        pantalla_operario()

    elif menu == " Operarios":
        pantalla_operarios_admin()

# -------------------------
# GERENCIA
# -------------------------
elif perfil == "gerencia":

    menu = st.radio(
        "",
        ["📊 Panel", "📋 OT", "📦 Inv."],
        horizontal=True,
        key="menu_gerencia_radio"
    )

    st.markdown("---")

    if menu == "📊 Panel":
        pantalla_panel()

    elif menu == "📋 OT":
        pantalla_ordenes_lectura()

    elif menu == "📦 Inv.":
        pantalla_inventario_lectura()

# -------------------------
# OPERARIO
# -------------------------
else:
    st.caption(f"👷 {operario_activo}")

    menu = st.radio(
        "",
        ["👷 Res.", "📋 OT", "📦 Inv."],
        horizontal=True,
        key="menu_operario_radio"
    )

    st.markdown("---")

    if menu == "👷 Res.":
        pantalla_resumen_operario()

    elif menu == "📋 OT":
        pantalla_operario()

    elif menu == "📦 Inv.":
        pantalla_inventario()
