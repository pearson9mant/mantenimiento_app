import streamlit as st
from datetime import datetime

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
from ui.ui_preventivo import pantalla_preventivo
from ui.ui_operarios_admin import pantalla_operarios_admin
from ui.ui_inventario_aulas import pantalla_inventario_aulas
from ui.ui_incidencias_profesores import pantalla_incidencias_profesores
from ui.ui_configuracion import pantalla_configuracion
from ui.ui_gerencia import pantalla_gerencia
from modules.preventivo import generar_ots_preventivo_si_toca


APP_VERSION = "v1.0 PRO"
APP_NAME = "Sistema Integral de Mantenimiento"
COLEGIO = "Loreto Abat Oliba"


st.set_page_config(
    page_title="Mantenimiento PRO",
    page_icon="🛠️",
    layout="wide"
)


st.markdown("""
<meta name="google" content="notranslate">

<style>

html, body, [class*="css"] {
    font-size: 14px !important;
}

body {
    background-color: #f4f6f9;
}


/* =========================================
   QUITAR CABECERA BLANCA STREAMLIT
========================================= */
[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stStatusWidget"] {
    display: none !important;
}

div[data-testid="stToolbar"] {
    display: none !important;
}

header[data-testid="stHeader"] {
    display: none !important;
}

section.main > div {
    padding-top: 0rem !important;
}

.block-container {
    padding-top: 0rem !important;
}


/* =========================================
   CONTENEDOR GENERAL
========================================= */

.block-container {
    padding-top: 0.4rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
    max-width: 1400px;
}


/* =========================================
   BOTONES
========================================= */

.stButton > button {
    width: 100%;
    height: 82px !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    border-radius: 18px !important;
    white-space: pre-line !important;

    border: 1px solid #d8dee9 !important;

    background: linear-gradient(
        180deg,
        #ffffff 0%,
        #f8fafc 100%
    ) !important;

    color: #1f2937 !important;

    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08) !important;

    transition: all 0.15s ease-in-out !important;
}

.stButton > button:hover {
    transform: translateY(-2px);

    border-color: #1d4ed8 !important;

    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14) !important;
}


/* =========================================
   MÉTRICAS
========================================= */

[data-testid="stMetricValue"] {
    font-size: 34px !important;
}


/* =========================================
   TARJETAS
========================================= */

.pro-card {
    background: #ffffff;

    border: 1px solid #e5e7eb;

    border-radius: 22px;

    padding: 22px;

    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);

    margin-bottom: 18px;
}


/* =========================================
   CABECERA
========================================= */

.pro-header {
    background: linear-gradient(
        135deg,
        #0f172a 0%,
        #1d4ed8 100%
    );

    color: white;

    border-radius: 24px;

    padding: 26px 28px;

    margin-bottom: 22px;

    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.20);
}

.pro-header-title {
    font-size: 30px;
    font-weight: 900;
    margin-bottom: 4px;
}

.pro-header-subtitle {
    font-size: 17px;
    font-weight: 600;
    opacity: 0.92;
}

.pro-header-meta {
    text-align: right;
    font-size: 13px;
    line-height: 1.7;
    opacity: 0.95;
}


/* =========================================
   PORTADA
========================================= */

.portada-box {
    background: #ffffff;

    border: 1px solid #e5e7eb;

    border-radius: 28px;

    padding: 34px;

    box-shadow: 0 12px 34px rgba(15, 23, 42, 0.10);

    margin-top: 0px;

    text-align: center;
}

.titulo-portada {
    text-align: center;

    font-size: 34px;

    font-weight: 900;

    color: #0f172a;

    margin-top: 12px;

    margin-bottom: 4px;
}

.subtitulo-portada {
    text-align: center;

    font-size: 21px;

    font-weight: 700;

    color: #1d4ed8;

    margin-bottom: 8px;
}

.version-portada {
    display: inline-block;

    background: #e0ecff;

    color: #1d4ed8;

    border-radius: 999px;

    padding: 6px 14px;

    font-weight: 800;

    font-size: 13px;

    margin-top: 8px;

    margin-bottom: 20px;
}


/* =========================================
   INFO USUARIO
========================================= */

.info-user {
    background: #f8fafc;

    border: 1px solid #e5e7eb;

    border-radius: 18px;

    padding: 14px;

    margin-top: 12px;

    margin-bottom: 20px;

    color: #334155;

    font-weight: 700;
}


/* =========================================
   TÍTULOS
========================================= */

.section-title {
    font-size: 22px;

    font-weight: 900;

    color: #0f172a;

    margin-bottom: 12px;
}


/* =========================================
   FOOTER
========================================= */

.footer-pro {
    text-align: center;

    color: #64748b;

    font-size: 12px;

    margin-top: 35px;

    padding-top: 18px;

    border-top: 1px solid #e5e7eb;
}


/* =========================================
   STATUS
========================================= */

.status-pill {
    display: inline-block;

    background: #dcfce7;

    color: #166534;

    padding: 6px 12px;

    border-radius: 999px;

    font-weight: 800;

    font-size: 12px;
}


/* =========================================
   RESPONSIVE MÓVIL
========================================= */

@media (max-width: 768px) {

    .pro-header {
        padding: 22px 18px;
        border-radius: 20px;
    }

    .pro-header-title {
        font-size: 23px;
    }

    .pro-header-subtitle {
        font-size: 15px;
    }

    .pro-header-meta {
        text-align: left;
        margin-top: 15px;
    }

    .titulo-portada {
        font-size: 27px;
    }

    .subtitulo-portada {
        font-size: 18px;
    }

    .portada-box {
        padding: 24px 16px;
    }

    .stButton > button {
        height: 78px !important;
        font-size: 15px !important;
    }
}

</style>
""", unsafe_allow_html=True)


def etiqueta_perfil(perfil):
    perfil = str(perfil or "").strip().lower()

    if perfil == "admin":
        return "Administración"

    if perfil == "gerencia":
        return "Gerencia"

    if perfil == "inventario":
        return "Inventario"

    return "Operario"


def usuario_visible():
    usuario = st.session_state.get("usuario", "")
    operario = st.session_state.get("operario_activo", "")

    if operario:
        return operario

    if usuario:
        return usuario

    return "Usuario"


def pintar_cabecera():

    perfil = st.session_state.get("perfil", "")
    usuario = usuario_visible()

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"""
        <div class="pro-header">
            <div class="pro-header-title">
                {APP_NAME}
            </div>

            <div class="pro-header-subtitle">
                {COLEGIO}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="pro-header">

            <div class="pro-header-meta">
                <b>{APP_VERSION}</b><br>
                {fecha}<br>
                {usuario}<br>
                {etiqueta_perfil(perfil)}
            </div>

        </div>
        """, unsafe_allow_html=True)


def pintar_footer():
    st.markdown(f"""
    <div class="footer-pro">
        {APP_NAME} · {COLEGIO} · {APP_VERSION} · © 2026
    </div>
    """, unsafe_allow_html=True)


def volver_menu():
    st.session_state["seccion_actual"] = None
    st.rerun()


def volver_portada():
    st.session_state["entrada_app"] = False
    st.session_state["seccion_actual"] = None
    st.rerun()


def mostrar_portada(perfil, operario_activo):

    st.markdown("<div class='portada-box'>", unsafe_allow_html=True)

    try:
        col_logo1, col_logo2, col_logo3 = st.columns([1, 1, 1])

        with col_logo2:
            st.image("logo cole.jpg", width=230)

    except Exception:
        st.markdown(
            "<div style='font-size:64px;'>🏫</div>",
            unsafe_allow_html=True
        )

    st.markdown(
        f"<div class='titulo-portada'>{APP_NAME}</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<div class='subtitulo-portada'>{COLEGIO}</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<div class='version-portada'>{APP_VERSION}</div>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if perfil == "admin":

        texto_boton = "🔐\nEntrar en administración"

        descripcion = "Acceso completo al sistema"

    elif perfil == "gerencia":

        texto_boton = "📊\nEntrar a gerencia"

        descripcion = "Panel de control y seguimiento"

    elif perfil == "inventario":

        texto_boton = "📦\nEntrar a inventario"

        descripcion = "Gestión de materiales e inventario"

    else:

        texto_boton = "👷\nEntrar a mi zona"

        descripcion = (
            f"Operario: {operario_activo}"
            if operario_activo
            else "Zona de operario"
        )

    st.markdown(
        f"<div class='info-user'>{descripcion}</div>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:

        if st.button(
            texto_boton,
            key="btn_entrada_app",
            use_container_width=True
        ):
            st.session_state["entrada_app"] = True
            st.session_state["seccion_actual"] = None
            st.rerun()

    st.markdown(
        "<br><span class='status-pill'>● Sistema operativo</span>",
        unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

    pintar_footer()

    st.stop()


# =====================================================
# MENÚ ADMIN
# =====================================================

def mostrar_menu_admin():

    st.markdown(
        "<div class='section-title'>Menú principal</div>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        if st.button(
            "📊\nPanel general",
            key="btn_panel",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Panel"
            st.rerun()

        if st.button(
            "📦\nInventario",
            key="btn_inv",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Inventario"
            st.rerun()

        if st.button(
            "👷\nVista operario",
            key="btn_op",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Operario"
            st.rerun()

    with col2:

        if st.button(
            "🛠\nÓrdenes de trabajo",
            key="btn_ot",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Órdenes"
            st.rerun()

        if st.button(
            "💧\nLegionella",
            key="btn_leg",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Legionella"
            st.rerun()

        if st.button(
            "🔧\nPreventivo",
            key="btn_preventivo",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Preventivo"
            st.rerun()

    with col3:

        if st.button(
            "📊\nGerencia",
            key="btn_gerencia_admin",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Gerencia"
            st.rerun()

        if st.button(
            "⚙️\nOperarios",
            key="btn_ops",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Operarios"
            st.rerun()

        if st.button(
            "📩\nIncidencias",
            key="btn_incidencias",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Incidencias"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)

    with col5:

        if st.button(
            "⚙️\nConfiguración",
            key="btn_config",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Configuración"
            st.rerun()


# =====================================================
# MENÚ OPERARIO
# =====================================================

def mostrar_menu_operario():

    perfil = st.session_state.get("perfil", "")
    operario = st.session_state.get("operario_activo", "")

    st.markdown(
        "<div class='section-title'>Menú de trabajo</div>",
        unsafe_allow_html=True
    )

    if perfil == "inventario":

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "📦\nInventario mantenimiento",
                key="btn_inv_inventario",
                use_container_width=True
            ):
                st.session_state["seccion_actual"] = "Inventario"
                st.rerun()

        with col2:

            if st.button(
                "🏫\nInventario aulas",
                key="btn_inv_aulas_inventario",
                use_container_width=True
            ):
                st.session_state["seccion_actual"] = "Inventario aulas"
                st.rerun()

        return

    st.markdown(
        f"<div class='info-user'>Operario: {operario}</div>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        if st.button(
            "📋\nResumen",
            key="btn_resumen_operario",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Resumen"
            st.rerun()

    with col2:

        if st.button(
            "🛠\nMis órdenes",
            key="btn_ot_operario",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Órdenes"
            st.rerun()

    with col3:

        if st.button(
            "📦\nInventario",
            key="btn_inv_operario",
            use_container_width=True
        ):
            st.session_state["seccion_actual"] = "Inventario"
            st.rerun()


# =====================================================
# INICIO
# =====================================================

inicializar_db()


try:

    if "preventivos_auto_revisados" not in st.session_state:

        generar_ots_preventivo_si_toca()

        st.session_state["preventivos_auto_revisados"] = True

except Exception:
    pass


params = st.query_params
modo = params.get("modo")

if modo == "incidencias":
    pantalla_incidencias_profesores()
    st.stop()


login()

perfil = st.session_state.get("perfil", "")
operario_activo = st.session_state.get("operario_activo", "")

if "seccion_actual" not in st.session_state:
    st.session_state["seccion_actual"] = None

if "entrada_app" not in st.session_state:
    st.session_state["entrada_app"] = False


if not st.session_state["entrada_app"]:
    mostrar_portada(perfil, operario_activo)


pintar_cabecera()

barra_sesion()


# =====================================================
# VISTA OPERARIO DESDE ADMIN
# =====================================================

if perfil == "admin" and st.session_state.get("vista_operario", False):

    pantalla_operario()

    st.markdown("---")

    if st.button(
        "⬅ Volver a administración",
        key="volver_admin_desde_vista_operario"
    ):
        st.session_state["vista_operario"] = False
        st.rerun()

    st.stop()


# =====================================================
# GERENCIA
# =====================================================

if perfil == "gerencia":

    st.markdown("---")

    if st.button(
        "🏠\nPortada",
        key="volver_portada_gerencia",
        use_container_width=True
    ):
        volver_portada()

    st.markdown("---")

    pantalla_gerencia()

    pintar_footer()

    st.stop()


# =====================================================
# MENÚ PRINCIPAL
# =====================================================

if st.session_state["seccion_actual"] is None:

    if st.button(
        "⬅\nVolver a portada",
        key="volver_portada_desde_menu",
        use_container_width=True
    ):
        volver_portada()

    st.markdown("---")

    if perfil == "admin":
        mostrar_menu_admin()

    else:
        mostrar_menu_operario()

    pintar_footer()

    st.stop()


# =====================================================
# BOTONES SUPERIORES
# =====================================================

col_volver1, col_volver2 = st.columns(2)

with col_volver1:

    if st.button(
        "⬅\nVolver al menú",
        key="volver_menu_general",
        use_container_width=True
    ):
        volver_menu()

with col_volver2:

    if st.button(
        "🏠\nPortada",
        key="volver_portada_general",
        use_container_width=True
    ):
        volver_portada()


st.markdown("---")

seccion = st.session_state["seccion_actual"]


# =====================================================
# ADMIN
# =====================================================

if perfil == "admin":

    if seccion == "Panel":
        pantalla_panel()

    elif seccion == "Gerencia":
        pantalla_gerencia()

    elif seccion == "Órdenes":
        pantalla_ordenes()

    elif seccion == "Inventario":
        pantalla_inventario()

    elif seccion == "Inventario aulas":
        pantalla_inventario_aulas()

    elif seccion == "Legionella":
        pantalla_legionella()

    elif seccion == "Preventivo":
        pantalla_preventivo()

    elif seccion == "Operario":
        pantalla_operario()

    elif seccion == "Operarios":
        pantalla_operarios_admin()

    elif seccion == "Incidencias":
        pantalla_incidencias_profesores()

    elif seccion == "Configuración":
        pantalla_configuracion()


# =====================================================
# OPERARIOS
# =====================================================

else:

    st.caption(f"{operario_activo}")

    if perfil == "inventario" and seccion not in [
        "Inventario",
        "Inventario aulas"
    ]:
        st.warning("Este usuario solo tiene acceso a Inventario.")
        st.stop()

    if seccion == "Resumen":
        pantalla_resumen_operario()

    elif seccion == "Órdenes":
        pantalla_operario()

    elif seccion == "Inventario":
        pantalla_inventario()

    elif seccion == "Inventario aulas":
        pantalla_inventario_aulas()


pintar_footer()
