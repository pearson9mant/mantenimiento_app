import streamlit as st
from pathlib import Path
from streamlit_image_coordinates import streamlit_image_coordinates


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

    st.info("Haz clic sobre el plano para obtener coordenadas.")

    coordenadas = streamlit_image_coordinates(
        str(plano),
        use_column_width=True,
        key="planos_legionella"
    )

    if coordenadas:
        st.success(
            f"X: {coordenadas['x']} | Y: {coordenadas['y']}"
        )
