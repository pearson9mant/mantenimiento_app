import streamlit as st


USUARIOS = {
    "juan": {
        "password": "1234",
        "perfil": "admin",
        "nombre": "Juan Antonio"
    },
    "luis": {
        "password": "1234",
        "perfil": "operario",
        "nombre": "Luis Lozano"
    },
    "abel": {
        "password": "1234",
        "perfil": "operario",
        "nombre": "Abel Vasquez"
    },
    "gerencia": {
        "password": "1234",
        "perfil": "gerencia",
        "nombre": "Gerencia"
    }
}


def login():
    if st.session_state.get("login_ok", False):
        return

    st.markdown("## Acceso mantenimiento")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar", use_container_width=True):
        usuario = usuario.strip().lower()

        if usuario in USUARIOS and password == USUARIOS[usuario]["password"]:
            datos = USUARIOS[usuario]

            st.session_state["login_ok"] = True
            st.session_state["usuario"] = usuario
            st.session_state["perfil"] = datos["perfil"]
            st.session_state["operario_activo"] = datos["nombre"]
            st.session_state["entrada_app"] = False
            st.session_state["seccion_actual"] = None

            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

    st.stop()


def barra_sesion():
    nombre = st.session_state.get("operario_activo", "")
    perfil = st.session_state.get("perfil", "")

    if nombre:
        st.caption(f"Sesión: {nombre} · {perfil}")

    if st.button("Cerrar sesión", use_container_width=True):
        claves = [
            "login_ok",
            "usuario",
            "perfil",
            "operario_activo",
            "entrada_app",
            "seccion_actual",
            "vista_operario"
        ]

        for clave in claves:
            if clave in st.session_state:
                del st.session_state[clave]

        st.rerun()
