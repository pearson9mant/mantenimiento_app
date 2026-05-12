import streamlit as st
from pathlib import Path


def pantalla_planos_legionella():

    st.title("🗺️ Planos Legionella")

    carpeta = Path("assets/planos_legionella")

    st.write("Buscando planos en:", carpeta.resolve())

    planos = list(carpeta.glob("*"))

    if not planos:
        st.error("No encuentro ningún archivo dentro de assets/planos_legionella")
        return

    plano = st.selectbox(
        "Selecciona plano",
        planos,
        format_func=lambda p: p.name
    )

    st.image(str(plano), use_container_width=True)
