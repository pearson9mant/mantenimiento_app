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
        "password": "1234",
        "perfil": "operario",
        "nombre": "Luis Lozano"
    }
}


def login():

    if st.session_state.get("login_ok", False):
        return

    st.title("🔐 Acceso mantenimiento")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):

        usuario = usuario.strip().lower()
        password = password.strip()

        if usuario in USUARIOS:

            if password == USUARIOS[usuario]["password"]:

                st.session_state["login_ok"] = True
                st.session_state["usuario"] = usuario
                st.session_state["perfil"] = USUARIOS[usuario]["perfil"]
                st.session_state["operario_activo"] = USUARIOS[usuario]["nombre"]

                st.rerun()

        st.error("Usuario o contraseña incorrectos")

    st.stop()


def barra_sesion():

    nombre = st.session_state.get("operario_activo", "")
    perfil = st.session_state.get("perfil", "")

    st.sidebar.success(f"{nombre} ({perfil})")

    if st.sidebar.button("Cerrar sesión"):

        for clave in [
            "login_ok",
            "usuario",
            "perfil",
            "operario_activo"
        ]:

            if clave in st.session_state:
                del st.session_state[clave]

        st.rerun()
