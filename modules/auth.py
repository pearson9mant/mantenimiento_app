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
    },

    "comunicacion": {
        "password": "com2026",
        "perfil": "comunicacion",
        "nombre": "Comunicación"
    },

    "direccion": {
        "password": "dir2026",
        "perfil": "comunicacion",
        "nombre": "Dirección de Servicios"
    }
}


def login():
    if st.session_state.get("login_ok", False):
        return

    usuario = st.text_input("Usuario", key="login_usuario")
    password = st.text_input(
        "Contraseña",
        type="password",
        key="login_password"
    )

    if st.button(
        "Entrar",
        use_container_width=True,
        key="login_entrar"
    ):
        usuario = usuario.strip().lower()
        password = password.strip()

        if (
            usuario in USUARIOS
            and password == USUARIOS[usuario]["password"]
        ):
            datos = USUARIOS[usuario]

            st.session_state["login_ok"] = True
            st.session_state["usuario_autenticado"] = True

            # Usuario de acceso (login)
            st.session_state["usuario"] = usuario

            # Nombre visible del usuario/departamento
            st.session_state["nombre"] = datos["nombre"]

            st.session_state["perfil"] = datos["perfil"]
            st.session_state["rol"] = datos["perfil"]

            # Se mantiene para no romper el resto de la aplicación
            st.session_state["operario_activo"] = datos["nombre"]

            st.session_state["entrada_app"] = False
            st.session_state["seccion_actual"] = None
            st.session_state["vista_operario"] = False

            st.rerun()

        else:
            st.error("Usuario o contraseña incorrectos")

    st.stop()


def barra_sesion():
    nombre = st.session_state.get("nombre") or st.session_state.get("operario_activo", "")
    perfil = st.session_state.get("perfil", "")

    if nombre:
        st.caption(f"Sesión: {nombre} · {perfil}")

    if st.button(
        "Cerrar sesión",
        use_container_width=True,
        key="cerrar_sesion_app"
    ):
        claves = [
            "login_ok",
            "usuario_autenticado",
            "usuario",
            "nombre",
            "perfil",
            "rol",
            "operario_activo",
            "entrada_app",
            "seccion_actual",
            "vista_operario"
        ]

        for clave in claves:
            st.session_state.pop(clave, None)

        st.rerun()

