import streamlit as st
from modules.auth import login, barra_sesion
from database.db import inicializar_db

from ui.ui_panel import pantalla_panel
from ui.ui_ordenes import pantalla_ordenes
from ui.ui_ordenes_lectura import pantalla_ordenes_lectura
from ui.ui_inventario import pantalla_inventario
from ui.ui_inventario_lectura import pantalla_inventario_lectura
from ui.ui_operario import pantalla_operario
from ui.ui_outlook import pantalla_outlook
from ui.ui_outlook_lectura import pantalla_outlook_lectura
from ui.ui_resumen_operario import pantalla_resumen_operario

st.set_page_config(page_title="Mantenimiento", layout="wide")

inicializar_db()
login()

st.title("🛠️ Gestión de Mantenimiento")
barra_sesion()

perfil = st.session_state.get("perfil", "")
operario_activo = st.session_state.get("operario_activo", "")

# -------------------------
# NAVEGACIÓN ADMIN
# -------------------------
if perfil == "admin":
    menu_admin = st.sidebar.radio(
        "Navegación",
        [
            "📊 Panel",
            "📋 Órdenes",
            "📦 Inventario",
            "👷 Operario",
            "📥 Outlook",
            "🧪 Legionella"
        ],
        key="menu_admin"
    )

    if menu_admin == "📊 Panel":
        pantalla_panel()

    elif menu_admin == "📋 Órdenes":
        pantalla_ordenes()

    elif menu_admin == "📦 Inventario":
        pantalla_inventario()

    elif menu_admin == "👷 Operario":
        pantalla_operario()

    elif menu_admin == "📥 Outlook":
        pantalla_outlook()

    elif menu_admin == "🧪 Legionella":
        st.subheader("🧪 Legionella")
        st.info("Módulo reservado para integrar Legionella PRO en el siguiente paso.")

# -------------------------
# NAVEGACIÓN GERENCIA
# -------------------------
elif perfil == "gerencia":
    menu_gerencia = st.sidebar.radio(
        "Navegación",
        [
            "📊 Panel",
            "📋 Órdenes",
            "📦 Inventario",
            "📥 Outlook",
            "🧪 Legionella"
        ],
        key="menu_gerencia"
    )

    if menu_gerencia == "📊 Panel":
        pantalla_panel()

    elif menu_gerencia == "📋 Órdenes":
        pantalla_ordenes_lectura()

    elif menu_gerencia == "📦 Inventario":
        pantalla_inventario_lectura()

    elif menu_gerencia == "📥 Outlook":
        pantalla_outlook_lectura()

    elif menu_gerencia == "🧪 Legionella":
        st.subheader("🧪 Legionella")
        st.info("Vista gerencia reservada para paneles e informes de Legionella.")

# -------------------------
# NAVEGACIÓN OPERARIO
# -------------------------
else:
    st.sidebar.caption(f"Operario activo: {operario_activo}")

    menu_operario = st.sidebar.radio(
        "Navegación",
        [
            "👷 Mi resumen",
            "📋 Mis órdenes",
            "📦 Inventario"
        ],
        key="menu_operario"
    )

    if menu_operario == "👷 Mi resumen":
        pantalla_resumen_operario()

    elif menu_operario == "📋 Mis órdenes":
        pantalla_operario()

    elif menu_operario == "📦 Inventario":
        pantalla_inventario()