import streamlit as st


USUARIOS = {
    "juan": {
        "password": "1234",
        "perfil": "admin",
        "nombre": "Juan Antonio"
    },

    "almeda": {
        "password": "1234",
        "perfil": "operario",
        "nombre": "J.A. Almeda"
    },

    "luis": {
        "password": "luis2026",
        "perfil": "operario",
        "nombre": "Luis Lozano"
    },

    "abel": {
        "password": "abel2026",
        "perfil": "inventario",
        "nombre": "Abel Vasquez"
    },

    "gerencia": {
        "password": "gerencia2026",
        "perfil": "gerencia",
        "nombre": "Gerencia"
    }
}


def login():
    if st.session_state.get("login_ok", False):
        return

    st.markdown(
        """
        <div style="
            max-width: 420px;
            margin: 70px auto 0 auto;
            padding: 28px;
            border-radius: 24px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.10);
        ">
            <div style="
                text-align: center;
                font-size: 28px;
                font-weight: 900;
                color: #0f172a;
                margin-bottom: 6px;
            ">
                🔐 Acceso
            </div>
            <div style="
                text-align: center;
                font-size: 14px;
                font-weight: 700;
                color: #64748b;
                margin-bottom: 22px;
            ">
                Sistema Integral de Mantenimiento
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.container():
        usuario = st.text_input("Usuario", key="login_usuario")
        password = st.text_input("Contraseña", type="password", key="login_password")

        if st.button("Entrar", use_container_width=True, key="login_boton_entrar"):
            usuario = usuario.strip().lower()
            password = password.strip()

            if usuario in USUARIOS and password == USUARIOS[usuario]["password"]:
                datos = USUARIOS[usuario]

                st.session_state["login_ok"] = True
                st.session_state["usuario"] = usuario
                st.session_state["perfil"] = datos["perfil"]
                st.session_state["rol"] = datos["perfil"]
                st.session_state["operario_activo"] = datos["nombre"]
                st.session_state["entrada_app"] = False
                st.session_state["seccion_actual"] = None
                st.session_state["vista_operario"] = False

                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

    st.stop()


def barra_sesion():
    nombre = st.session_state.get("operario_activo", "")
    perfil = st.session_state.get("perfil", "")

    if nombre:
        st.caption(f"Sesión: {nombre} · {perfil}")

    if st.button("Cerrar sesión", use_container_width=True, key="cerrar_sesion_app"):
        claves = [
            "login_ok",
            "usuario",
            "perfil",
            "rol",
            "operario_activo",
            "entrada_app",
            "seccion_actual",
            "vista_operario"
        ]

        for clave in claves:
            if clave in st.session_state:
                del st.session_state[clave]

        st.rerun()
