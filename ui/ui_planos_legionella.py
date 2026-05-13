import streamlit as st
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates


def cargar_fuente(tamano=24):
    try:
        return ImageFont.truetype("arial.ttf", tamano)
    except Exception:
        return ImageFont.load_default()


def dibujar_puntos(imagen_path, puntos):

    imagen = Image.open(imagen_path).convert("RGB")
    draw = ImageDraw.Draw(imagen)
    font = cargar_fuente(34)

    colores = {
        "ACS": "#ff0000",
        "AFCH": "#0066ff",
        "Retorno": "#ff8800",
        "Acumulador": "#9900ff",
        "Grifo": "#00aa00",
        "Ducha": "#00bbbb",
    }

    for punto in puntos:

        x = int(punto["x"])
        y = int(punto["y"])

        tipo = punto.get("tipo", "Grifo")
        nombre = punto.get("nombre", "")

        color = colores.get(tipo, "#ff0000")

        radio = 10

        draw.ellipse(
            (x - radio, y - radio, x + radio, y + radio),
            fill=color,
            outline="white",
            width=3
        )

        texto_x = x + 16
        texto_y = y - 18

        bbox = draw.textbbox((texto_x, texto_y), nombre, font=font)

        draw.rectangle(
            (
                bbox[0] - 5,
                bbox[1] - 3,
                bbox[2] + 5,
                bbox[3] + 3
            ),
            fill="white"
        )

        draw.text(
            (texto_x, texto_y),
            nombre,
            fill=color,
            font=font
        )

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
            nombre = st.text_input("Nombre del punto", placeholder="Ej: P0/ACS01 - Grifo cocina")

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
