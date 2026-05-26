import streamlit as st
from datetime import datetime

from modules.auth import barra_sesion, USUARIOS
from database.db import inicializar_db
from ui.ui_planos_legionella import pantalla_planos_legionella

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
from ui.ui_legionella import generar_ots_legionella_si_toca
from ui.ui_plan_verano import pantalla_plan_verano
from ui.ui_empresas_externas import pantalla_empresas_externas
from modules.alertas_empresas import obtener_alertas_empresas_externas, crear_ots_empresas_externas_si_toca
from ui.ui_estado_aulas import ui_estado_aulas
from ui.ui_recordatorios import pantalla_recordatorios
from ui.ui_recordatorios import (
    pantalla_recordatorios,
    obtener_resumen_recordatorios
)
from ui.ui_pedidos_material import ui_pedidos_material

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
:root {
    --app-teal: #16b8b5;
    --app-teal-dark: #079693;
    --app-navy: #0f172a;
    --app-blue: #1d4ed8;
    --app-bg: #f7f9fc;
    --app-border: #e2e8f0;
}

html, body, [class*="css"] {
    font-size: 14px !important;
}

body {
    background-color: var(--app-bg);
}

[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
div[data-testid="stToolbar"],
header[data-testid="stHeader"] {
    display: none !important;
}

section.main > div {
    padding-top: 0rem !important;
}

.block-container {
    padding-top: 0.4rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
    max-width: 1400px;
}

/* BOTONES GENERALES */
.stButton > button {
    width: 100%;
    min-height: 82px !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    border-radius: 22px !important;
    white-space: pre-line !important;
    border: 1px solid var(--app-border) !important;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
    color: #1f2937 !important;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08) !important;
    transition: all 0.15s ease-in-out !important;
}

.stButton > button:hover {
    transform: translateY(-2px);
    border-color: var(--app-teal) !important;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.15) !important;
    color: var(--app-teal-dark) !important;
}

/* CABECERA INTERIOR */
.pro-header {
    background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
    color: white;
    border-radius: 26px;
    padding: 26px 28px;
    margin-bottom: 22px;
    box-shadow: 0 12px 34px rgba(15, 23, 42, 0.22);
}

.pro-header-title {
    font-size: 30px;
    font-weight: 900;
    margin-bottom: 8px;
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

/* PORTADA LOGIN */
.portada-wrap {
    max-width: 520px;
    margin: 0 auto;
    padding-top: 18px;
    padding-bottom: 20px;
    text-align: center;
}

.portada-logo-text {
    font-size: 42px;
    line-height: 1;
    font-weight: 950;
    letter-spacing: -1px;
    color: #111827;
    margin-top: 6px;
}

.portada-logo-sub {
    font-size: 11px;
    font-weight: 900;
    letter-spacing: 12px;
    color: #334155;
    margin-left: 12px;
    margin-bottom: 4px;
}

.portada-logo-o {
    display: inline-block;
    color: var(--app-teal);
}

.portada-colegio {
    font-size: 15px;
    font-weight: 800;
    color: #64748b;
    margin-top: 10px;
}

.portada-selecciona {
    font-size: 18px;
    font-weight: 800;
    color: var(--app-teal-dark);
    margin-top: 28px;
    margin-bottom: 22px;
}

.portada-version {
    display: inline-block;
    background: #ccfbf1;
    color: #0f766e;
    border-radius: 999px;
    padding: 7px 16px;
    font-weight: 900;
    font-size: 12px;
    margin-top: 6px;
}

.login-card {
    max-width: 420px;
    margin: 0 auto;
    background: #ffffff;
    border: 1px solid var(--app-border);
    border-radius: 24px;
    padding: 22px 24px 26px 24px;
    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
    text-align: left;
}

.login-card-title {
    text-align: center;
    font-size: 20px;
    font-weight: 950;
    color: var(--app-navy);
    margin-bottom: 14px;
}

/* TEXTOS */
.info-user {
    background: #f8fafc;
    border: 1px solid var(--app-border);
    border-radius: 18px;
    padding: 14px;
    margin-top: 12px;
    margin-bottom: 20px;
    color: #334155;
    font-weight: 700;
}

.section-title {
    font-size: 22px;
    font-weight: 900;
    color: var(--app-navy);
    margin-bottom: 12px;
}

.footer-pro {
    text-align: center;
    color: #64748b;
    font-size: 12px;
    margin-top: 35px;
    padding-top: 18px;
    border-top: 1px solid #e5e7eb;
}

[data-testid="stMetricValue"] {
    font-size: 34px !important;
}

@media (max-width: 768px) {
    .block-container {
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }

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

    .portada-wrap {
        max-width: 100%;
        padding-top: 6px;
    }

    .portada-logo-text {
        font-size: 48px;
    }

    .portada-selecciona {
        margin-top: 24px;
        font-size: 17px;
    }

    .stButton > button {
        min-height: 78px !important;
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
        st.markdown(
            f'<div class="pro-header">'
            f'<div class="pro-header-title">{APP_NAME}</div>'
            f'<div class="pro-header-subtitle">{COLEGIO}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f'<div class="pro-header">'
            f'<div class="pro-header-meta">'
            f'<b>{APP_VERSION}</b><br>'
            f'{fecha}<br>'
            f'{usuario}<br>'
            f'{etiqueta_perfil(perfil)}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )


def pintar_footer():
    st.markdown(
        f'<div class="footer-pro">{APP_NAME} · {COLEGIO} · {APP_VERSION} · © 2026</div>',
        unsafe_allow_html=True
    )


def volver_menu():
    st.session_state["seccion_actual"] = None
    st.rerun()


def volver_portada():
    st.session_state["entrada_app"] = False
    st.session_state["seccion_actual"] = None
    st.rerun()


def login_portada():
    if st.session_state.get("login_ok", False):
        return

    st.markdown("<div class='portada-wrap'>", unsafe_allow_html=True)

    try:
        st.image("logo cole.jpg", width=150)
    except Exception:
        st.markdown(
            """
            <div class="portada-logo-sub">GRUPO</div>
            <div class="portada-logo-text">m<span class="portada-logo-o">o</span>ria</div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        f"""
        <div class="portada-colegio">{COLEGIO}</div>
        <div class="portada-version">{APP_VERSION}</div>
        <div class="portada-selecciona">Acceso al sistema</div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='login-card'>", unsafe_allow_html=True)
    st.markdown("<div class='login-card-title'>🔐 Identificación</div>", unsafe_allow_html=True)

    usuario = st.text_input("Usuario", key="login_usuario")
    password = st.text_input("Contraseña", type="password", key="login_password")

    if st.button("Entrar", use_container_width=True, key="login_entrar"):
        usuario = usuario.strip().lower()
        password = password.strip()

        if usuario in USUARIOS and password == USUARIOS[usuario]["password"]:
            datos = USUARIOS[usuario]

            st.session_state["login_ok"] = True
            st.session_state["usuario"] = usuario
            st.session_state["perfil"] = datos["perfil"]
            st.session_state["rol"] = datos["perfil"]
            st.session_state["operario_activo"] = datos["nombre"]
            st.session_state["entrada_app"] = True
            st.session_state["seccion_actual"] = None
            st.session_state["vista_operario"] = False

            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    pintar_footer()
    st.stop()


def mostrar_menu_admin():
    st.markdown(
        "<div class='section-title'>Menú principal</div>",
        unsafe_allow_html=True
    )
    try:

        resumen_recordatorios = obtener_resumen_recordatorios()

        if resumen_recordatorios["vencidos"]:

            st.error("🔴 Recordatorios vencidos")

            for item in resumen_recordatorios["vencidos"]:
                st.markdown(f"- {item}")

        if resumen_recordatorios["hoy"]:

            st.warning("🟠 Recordatorios para hoy")

            for item in resumen_recordatorios["hoy"]:
                st.markdown(f"- {item}")

        if resumen_recordatorios["mañana"]:

            st.info("🔔 Recordatorios para mañana")

            for item in resumen_recordatorios["mañana"]:
                st.markdown(f"- {item}")

    except Exception as e:
        st.warning(f"Error recordatorios: {e}")

    # =====================================================
    # ALERTAS EMPRESAS / LEGIONELLA
    # =====================================================

    try:

        alertas = obtener_alertas_empresas_externas()

        toca = alertas["toca"]
        proximo = alertas["proximo"]

        if toca:

            st.error(
                f"🔴 Hay {len(toca)} actuaciones externas vencidas"
            )

            for item in toca:

                st.markdown(
                    f"- {item['tipo']} · "
                    f"{item['empresa']} · "
                    f"{item['centro']} · "
                    f"{item['fecha']}"
                )

        if proximo:

            st.warning(
                f"🟠 Hay {len(proximo)} actuaciones próximas"
            )

            for item in proximo:

                st.markdown(
                    f"- {item['tipo']} · "
                    f"{item['empresa']} · "
                    f"{item['centro']} · "
                    f"{item['fecha']}"
                )

    except Exception as e:

        st.warning(f"Alertas empresas externas: {e}")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊\nPanel general", key="btn_panel", use_container_width=True):
            st.session_state["seccion_actual"] = "Panel"
            st.rerun()

        if st.button("📦\nInventario", key="btn_inv", use_container_width=True):
            st.session_state["seccion_actual"] = "Inventario"
            st.rerun()

        if st.button("👷\nVista operario", key="btn_op", use_container_width=True):
            st.session_state["seccion_actual"] = "Operario"
            st.rerun()

    with col2:
        if st.button("🛠\nÓrdenes de trabajo", key="btn_ot", use_container_width=True):
            st.session_state["seccion_actual"] = "Órdenes"
            st.rerun()

        if st.button("💧\nLegionella", key="btn_leg", use_container_width=True):
            st.session_state["seccion_actual"] = "Legionella"
            st.rerun()

        if st.button("🔧\nPreventivo", key="btn_preventivo", use_container_width=True):
            st.session_state["seccion_actual"] = "Preventivo"
            st.rerun()

    with col3:
        if st.button("📊\nGerencia", key="btn_gerencia_admin", use_container_width=True):
            st.session_state["seccion_actual"] = "Gerencia"
            st.rerun()

        if st.button("⚙️\nOperarios", key="btn_ops", use_container_width=True):
            st.session_state["seccion_actual"] = "Operarios"
            st.rerun()

        if st.button("📩\nIncidencias", key="btn_incidencias", use_container_width=True):
            st.session_state["seccion_actual"] = "Incidencias"
            st.rerun()
        if st.button("📩\nPedidos material", key="btn_pedidos_admin", use_container_width=True):
            st.session_state["seccion_actual"] = "Pedidos material"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)

    with col4:
        if st.button("🗺️\nPlanos Legionella", key="btn_planos_legionella", use_container_width=True):
            st.session_state["seccion_actual"] = "Planos Legionella"
            st.rerun()
        if st.button("🏢\nEmpresas externas", key="btn_empresas_externas", use_container_width=True):
            st.session_state["seccion_actual"] = "Empresas externas"
            st.rerun()
    

    with col5:
        if st.button("☀️\nPlan verano", key="btn_plan_verano_admin", use_container_width=True):
            st.session_state["seccion_actual"] = "Plan verano"
            st.rerun()

        if st.button("🏫\nEstado aulas", key="btn_estado_aulas", use_container_width=True):
            st.session_state["seccion_actual"] = "Estado aulas"
            st.rerun() 

        if st.button("🔔\nRecordatorios", key="btn_recordatorios", use_container_width=True):
            st.session_state["seccion_actual"] = "Recordatorios"
            st.rerun()

        if st.button("⚙️\nConfiguración", key="btn_config", use_container_width=True):
            st.session_state["seccion_actual"] = "Configuración"
            st.rerun()


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
            if st.button("📦\nInventario mantenimiento", key="btn_inv_inventario", use_container_width=True):
                st.session_state["seccion_actual"] = "Inventario"
                st.rerun()

        with col2:
            if st.button("🏫\nInventario aulas", key="btn_inv_aulas_inventario", use_container_width=True):
                st.session_state["seccion_actual"] = "Inventario aulas"
                st.rerun()

        return

    st.markdown(
        f"<div class='info-user'>Operario: {operario}</div>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📋\nResumen", key="btn_resumen_operario", use_container_width=True):
            st.session_state["seccion_actual"] = "Resumen"
            st.rerun()

    with col2:
        if st.button("🛠\nMis órdenes", key="btn_ot_operario", use_container_width=True):
            st.session_state["seccion_actual"] = "Órdenes"
            st.rerun()

    with col3:
        if st.button("📦\nInventario", key="btn_inv_operario", use_container_width=True):
            st.session_state["seccion_actual"] = "Inventario"
            st.rerun()
        if st.button("📩\nPedidos material", key="btn_pedidos_material", use_container_width=True):
            st.session_state["seccion_actual"] = "Pedidos material"
            st.rerun()  


# =====================================================
# INICIO APP
# =====================================================

inicializar_db()

try:
    if "preventivos_auto_revisados" not in st.session_state:
        generar_ots_preventivo_si_toca()
        st.session_state["preventivos_auto_revisados"] = True

except Exception:
    pass


try:
    if "legionella_auto_revisada" not in st.session_state:
        generar_ots_legionella_si_toca()
        st.session_state["legionella_auto_revisada"] = True

except Exception:
    pass

try:
    if "externas_auto_revisadas" not in st.session_state:
        crear_ots_empresas_externas_si_toca()
        st.session_state["externas_auto_revisadas"] = True

except Exception:
    pass


params = st.query_params
modo = params.get("modo")

if modo == "incidencias":
    pantalla_incidencias_profesores()
    st.stop()


if "seccion_actual" not in st.session_state:
    st.session_state["seccion_actual"] = None

if "entrada_app" not in st.session_state:
    st.session_state["entrada_app"] = True


login_portada()


perfil = st.session_state.get("perfil", "")
operario_activo = st.session_state.get("operario_activo", "")


pintar_cabecera()
barra_sesion()


if perfil == "admin" and st.session_state.get("vista_operario", False):
    pantalla_operario()

    st.markdown("---")

    if st.button(
        "⬅ Volver a administración",
        key="volver_admin_desde_vista_operario"
    ):
        st.session_state["vista_operario"] = False
        st.session_state["seccion_actual"] = None
        st.rerun()

    st.stop()


if perfil == "gerencia":
    if st.session_state["seccion_actual"] is None:
        st.markdown(
            "<div class='section-title'>Menú Gerencia</div>",
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊\nPanel gerencia", key="btn_gerencia_panel", use_container_width=True):
                st.session_state["seccion_actual"] = "Gerencia"
                st.rerun()

        with col2:
            if st.button("☀️\nPlan verano", key="btn_plan_verano_gerencia", use_container_width=True):
                st.session_state["seccion_actual"] = "Plan verano"
                st.rerun()

        pintar_footer()
        st.stop()


if st.session_state["seccion_actual"] is None:
    if perfil == "admin":
        mostrar_menu_admin()
    else:
        mostrar_menu_operario()

    pintar_footer()
    st.stop()


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
        "🏠\nInicio",
        key="volver_inicio_general",
        use_container_width=True
    ):
        volver_menu()


st.markdown("---")

seccion = st.session_state["seccion_actual"]

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

    elif seccion == "Planos Legionella":
        pantalla_planos_legionella()

    elif seccion == "Plan verano":
        pantalla_plan_verano()

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

    elif seccion == "Empresas externas":
        pantalla_empresas_externas()

    elif seccion == "Estado aulas":
        ui_estado_aulas()

    elif seccion == "Recordatorios":
        pantalla_recordatorios()


elif perfil == "gerencia":

    if seccion == "Gerencia":
        pantalla_gerencia()

    elif seccion == "Plan verano":
        pantalla_plan_verano()


else:
    st.caption(f"{operario_activo}")

    if perfil == "inventario" and seccion not in [
        "Inventario",
        "Inventario aulas"
        "Pedidos material"
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
        
    elif seccion == "Pedidos material":
        ui_pedidos_material()


pintar_footer()
