import streamlit as st


def pantalla_colegio_vivo_operario():
    st.set_page_config(layout="wide")

    st.markdown(
        """
        <style>

        .titulo{
            font-size:34px;
            font-weight:700;
            color:#0f2747;
            margin-bottom:5px;
        }

        .subtitulo{
            color:#666;
            font-size:16px;
            margin-bottom:25px;
        }

        .bloque{
            background:white;
            border-radius:18px;
            padding:18px;
            margin-bottom:18px;
            border:1px solid #ececec;
            box-shadow:0 2px 8px rgba(0,0,0,.05);
        }

        .edificio{
            font-size:22px;
            font-weight:bold;
            color:#16385f;
            margin-bottom:10px;
        }

        .planta{
            background:#f8f8f8;
            border-radius:10px;
            padding:10px 14px;
            margin-bottom:8px;
            font-size:18px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="titulo">❤️ Mi misión</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitulo">Empieza a trabajar desde el colegio, no desde una lista.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="bloque">', unsafe_allow_html=True)

    st.markdown('<div class="edificio">🏫 Pearson 22</div>', unsafe_allow_html=True)

    if st.button("🔴 Planta 5      (2)", use_container_width=True):
        st.session_state["planta_seleccionada"] = "P5"

    if st.button("🟠 Planta 4      (3)", use_container_width=True):
        st.session_state["planta_seleccionada"] = "P4"

    if st.button("🟢 Planta 3", use_container_width=True):
        st.session_state["planta_seleccionada"] = "P3"

    if st.button("🟢 Planta 2", use_container_width=True):
        st.session_state["planta_seleccionada"] = "P2"

    if st.button("🟢 Planta 1", use_container_width=True):
        st.session_state["planta_seleccionada"] = "P1"

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="bloque">', unsafe_allow_html=True)

    st.markdown('<div class="edificio">🏫 Llar</div>', unsafe_allow_html=True)

    if st.button("🟢 Planta 2 ", use_container_width=True):
        st.session_state["planta_seleccionada"] = "L2"

    if st.button("🟡 Planta 1      (1)", use_container_width=True):
        st.session_state["planta_seleccionada"] = "L1"

    if st.button("🟢 Planta 0", use_container_width=True):
        st.session_state["planta_seleccionada"] = "L0"

    st.markdown("</div>", unsafe_allow_html=True)

    if "planta_seleccionada" in st.session_state:

        st.divider()

        st.subheader(f"📍 {st.session_state['planta_seleccionada']}")

        st.button(
            "▶️ Empezar primera OT",
            type="primary",
            use_container_width=True,
        )
