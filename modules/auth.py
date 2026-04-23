import streamlit as st
from config import CLAVE_ADMIN

def login():
    if "perfil" not in st.session_state:
        st.session_state.perfil = None

    if "operario_activo" not in st.session_state:
        st.session_state.operario_activo = None

    if st.session_state.perfil is None:
        st.title("🛠️ Acceso Mantenimiento")

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            if st.button("Abel Vasquez", key="login_abel"):
                st.session_state.perfil = "operario"
                st.session_state.operario_activo = "Abel Vasquez"
                st.rerun()

        with c2:
            if st.button("Luis Lozano", key="login_luis"):
                st.session_state.perfil = "operario"
                st.session_state.operario_activo = "Luis Lozano"
                st.rerun()

        with c3:
            if st.button("J.A. Almeda", key="login_ja"):
                st.session_state.perfil = "operario"
                st.session_state.operario_activo = "J.A. Almeda"
                st.rerun()

        with c4:
            if st.button("Gerencia", key="login_gerencia"):
                st.session_state.perfil = "gerencia"
                st.session_state.operario_activo = "Gerencia"
                st.rerun()

        with c5:
            clave = st.text_input("Clave admin", type="password", key="clave_admin")
            if st.button("Entrar admin", key="login_admin"):
                if clave == CLAVE_ADMIN:
                    st.session_state.perfil = "admin"
                    st.session_state.operario_activo = "Administrador"
                    st.rerun()
                else:
                    st.error("Clave incorrecta")

        st.stop()

def barra_sesion():
    c1, c2 = st.columns([6, 1])

    with c1:
        perfil = st.session_state.get("perfil", "")
        activo = st.session_state.get("operario_activo", "")

        if perfil == "admin":
            st.caption("Sesión activa: Administrador")
        elif perfil == "gerencia":
            st.caption("Sesión activa: Gerencia")
        else:
            st.caption(f"Sesión activa: Operario | {activo}")

    with c2:
        if st.button("Salir", key="logout_btn"):
            st.session_state.perfil = None
            st.session_state.operario_activo = None
            st.rerun()