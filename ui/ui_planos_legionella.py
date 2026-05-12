import streamlit as st
from pathlib import Path


def pantalla_planos_legionella():

    st.title("🗺️ Planos Legionella")

    carpeta = Path("assets/planos_legionella")

    extensiones_validas = ["*.png", "*.jpg", "*.jpeg"]

    planos = []

    for extension in extensiones_validas:
        planos.extend(carpeta.glob(extension))

    planos = sorted(planos, key=lambda p: p.name.lower())

    if not planos:
        st.error("No encuentro planos PNG/JPG dentro de assets/planos_legionella")
        return

    plano = st.selectbox(
        "Selecciona plano",
        planos,
        format_func=lambda p: p.name
    )

    st.image(str(plano), use_container_width=True)
