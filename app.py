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
    height: 80px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    border-radius: 16px !important;
    white-space: pre-line !important;
}

[data-testid="stMetricValue"] {
    font-size: 34px !important;
}

.logo-portada {
    text-align: center;
    margin-top: 20px;
    margin-bottom: 10px;
}

.titulo-portada {
    text-align: center;
    font-size: 26px;
    font-weight: 800;
    margin-bottom: 0;
}

.subtitulo-portada {
    text-align: center;
    font-size: 18px;
    font-weight: 600;
    color: #555;
    margin-top: 0;
    margin-bottom: 25px;
}
</style>
""", unsafe_allow_html=True)


def volver_menu():
    st.session_state["seccion_actual"] = None
    st.rerun()


def volver_portada():
    st.session_state["entrada_app"] = False
    st.session_state["seccion_actual"] = None
    st.rerun()


def mostrar_portada(perfil, operario_activo):
    st.markdown("<br>", unsafe_allow_html=True)

    # Si tu logo está en otra ruta, cambia esta línea.
    try:
        st.image("logo cole.jpg", width=220)
    except Exception:
        st.markdown(
            "<div class='logo-portada'>🏫</div>",
            unsafe_allow_html=True
        )

    st.markdown("<div class='titulo-portada'>Mantenimiento</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitulo-portada'>Loreto Abat Oliba</div>", unsafe_allow_html=True)

    st.markdown("---")

    if perfil == "admin":
        texto_boton = "🔐\nEntrar en administración"

    elif perfil == "gerencia":
        texto_boton = "📊\nEntrar a gerencia"

    else:
        if operario_activo:
            st.caption(f"Operario: {operario_activo}")
        texto_boton = "👷\nEntrar a mi zona"

    if st.button(texto_boton, key="btn_entrada_app", use_container_width=True):
        st.session_state["entrada_app"] = True
        st.session_state["seccion_actual"] = None
        st.rerun()

    st.stop()


def mostrar_menu_admin():
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊\nPanel", key="btn_panel", use_container_width=True):
            st.session_state["seccion_actual"] = "Panel"
            st.rerun()

        if st.button("📦\nInventario", key="btn_inv", use_container_width=True):
            st.session_state["seccion_actual"] = "Inventario"
            st.rerun()

        if st.button("👷\nOperario", key="btn_op", use_container_width=True):
            st.session_state["seccion_actual"] = "Operario"
            st.rerun()

    with col2:
        if st.button("🛠\nÓrdenes", key="btn_ot", use_container_width=True):
            st.session_state["seccion_actual"] = "Órdenes"
            st.rerun()

        if st.button("💧\nLegionella", key="btn_leg", use_container_width=True):
            st.session_state["seccion_actual"] = "Legionella"
            st.rerun()

        if st.button("⚙️\nOperarios", key="btn_ops", use_container_width=True):
            st.session_state["seccion_actual"] = "Operarios"
            st.rerun()


def mostrar_menu_gerencia():
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊\nPanel", key="btn_panel_gerencia", use_container_width=True):
            st.session_state["seccion_actual"] = "Panel"
            st.rerun()

        if st.button("📦\nInventario", key="btn_inv_gerencia", use_container_width=True):
            st.session_state["seccion_actual"] = "Inventario"
            st.rerun()

    with col2:
        if st.button("🛠\nÓrdenes", key="btn_ot_gerencia", use_container_width=True):
            st.session_state["seccion_actual"] = "Órdenes"
            st.rerun()


def mostrar_menu_operario():
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📋\nResumen", key="btn_resumen_operario", use_container_width=True):
            st.session_state["seccion_actual"] = "Resumen"
            st.rerun()

        if st.button("📦\nInventario", key="btn_inv_operario", use_container_width=True):
            st.session_state["seccion_actual"] = "Inventario"
            st.rerun()

    with col2:
        if st.button("🛠\nÓrdenes", key="btn_ot_operario", use_container_width=True):
            st.session_state["seccion_actual"] = "Órdenes"
            st.rerun()


inicializar_db()
login()

perfil = st.session_state.get("perfil", "")
operario_activo = st.session_state.get("operario_activo", "")

if "seccion_actual" not in st.session_state:
    st.session_state["seccion_actual"] = None

if "entrada_app" not in st.session_state:
    st.session_state["entrada_app"] = False


# -------------------------------
# PORTADA DE ENTRADA
# -------------------------------
if not st.session_state["entrada_app"]:
    mostrar_portada(perfil, operario_activo)


st.markdown("### Mantenimiento")
barra_sesion()


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

    if st.button("⬅\nVolver a portada", key="volver_portada_desde_menu", use_container_width=True):
        volver_portada()

    st.markdown("---")

    if perfil == "admin":
        mostrar_menu_admin()

    elif perfil == "gerencia":
        mostrar_menu_gerencia()

    else:
        st.caption(f"{operario_activo}")
        mostrar_menu_operario()

    st.stop()


# -------------------------------
# BOTONES VOLVER
# -------------------------------
col_volver1, col_volver2 = st.columns(2)

with col_volver1:
    if st.button("⬅\nVolver al menú", key="volver_menu_general", use_container_width=True):
        volver_menu()

with col_volver2:
    if st.button("🏠\nPortada", key="volver_portada_general", use_container_width=True):
        volver_portada()

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
