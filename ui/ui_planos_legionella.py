import streamlit as st
from pathlib import Path
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates


def dibujar_puntos(imagen_path, puntos):
    imagen = Image.open(imagen_path).convert("RGB")
    draw = ImageDraw.Draw(imagen)

    colores = {
        "ACS": "red",
        "AFCH": "blue",
        "Retorno": "orange",
        "Acumulador": "purple",
        "Grifo": "green",
        "Ducha": "cyan",
    }

    for punto in puntos:
        x = int(punto["x"])
        y = int(punto["y"])
        tipo = punto.get("tipo", "Grifo")
        nombre = punto.get("nombre", "")

        color = colores.get(tipo, "black")

        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=color, outline="black")
        draw.text((x + 10, y - 10), nombre, fill="black")

    return imagen


def pantalla_planos_legionella():

    st.title("🗺️ Planos Legionella")

    carpeta = Path("assets/planos_legionella")

    planos = []
    for extension in ["*.png", "*.jpg", "*.jpeg"]:
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

    clave_puntos = f"puntos_{plano.name}"

    if clave_puntos not in st.session_state:
        st.session_state[clave_puntos] = []

    st.info("Haz clic en el plano para capturar la posición del punto.")

    imagen_con_puntos = dibujar_puntos(plano, st.session_state[clave_puntos])

    coordenadas = streamlit_image_coordinates(
        imagen_con_puntos,
        use_column_width=True,
        key=f"coords_{plano.name}"
    )

    st.markdown("---")

    st.subheader("➕ Añadir punto Legionella")

    if coordenadas:
        x = coordenadas["x"]
        y = coordenadas["y"]

        st.success(f"Coordenada seleccionada: X={x} | Y={y}")

        col1, col2 = st.columns(2)

        with col1:
            nombre = st.text_input("Nombre del punto", placeholder="Ej: Grifo baño primaria")

        with col2:
            tipo = st.selectbox(
                "Tipo de punto",
                ["ACS", "AFCH", "Retorno", "Acumulador", "Grifo", "Ducha"]
            )

        if st.button("✅ Guardar punto en el plano", use_container_width=True):
            st.session_state[clave_puntos].append({
                "nombre": nombre or tipo,
                "tipo": tipo,
                "x": x,
                "y": y
            })
            st.rerun()

    st.markdown("---")

    st.subheader("📍 Puntos marcados")

    puntos = st.session_state[clave_puntos]

    if not puntos:
        st.info("Todavía no hay puntos marcados en este plano.")
    else:
        for i, punto in enumerate(puntos):
            st.write(
                f"{i + 1}. {punto['tipo']} · {punto['nombre']} "
                f"· X={punto['x']} · Y={punto['y']}"
            )

        if st.button("🗑️ Borrar todos los puntos de este plano", use_container_width=True):
            st.session_state[clave_puntos] = []
            st.rerun()
