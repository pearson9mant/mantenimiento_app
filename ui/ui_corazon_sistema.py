import streamlit as st

from modules.corazon_sistema import diagnosticar_corazon_sistema


def mostrar_corazon_sistema():

    st.title("❤️ Corazón del Sistema")

    panel = diagnosticar_corazon_sistema()

    color = panel.get("color", "verde")
    score = panel.get("score_global", 0)

    if color == "verde":
        st.success(f"Estado global: {score}%")
    elif color == "amarillo":
        st.warning(f"Estado global: {score}%")
    else:
        st.error(f"Estado global: {score}%")

    st.markdown(panel.get("mensaje", ""))

    st.divider()

    st.subheader("📊 Indicadores principales")

    c1, c2, c3, c4, c5 = st.columns(5)

    kpis = panel.get("kpis", {})

    with c1:
        st.metric("OT", kpis.get("ot", 0))

    with c2:
        st.metric("Incidencias", kpis.get("incidencias", 0))

    with c3:
        st.metric("Preventivos", kpis.get("preventivos", 0))

    with c4:
        st.metric("Legionella", kpis.get("legionella", 0))

    with c5:
        st.metric("Urgentes", kpis.get("urgentes", 0))

    st.divider()

    prioridad = panel.get("prioridad_hoy")

    st.subheader("🎯 Si hoy solo hicieras una cosa...")

    if prioridad:

        with st.container(border=True):

            st.markdown(f"### ⭐ {prioridad.get('numero_ot','')}")

            st.markdown(
                f"## {prioridad.get('titulo','Sin prioridad')}"
            )

            st.caption(
                f"{prioridad.get('centro','')} · "
                f"{prioridad.get('edificio','')} · "
                f"{prioridad.get('espacio','')}"
            )

            st.markdown(
                f"**Origen:** {prioridad.get('origen','')}"
            )

            st.markdown(
                f"**Área:** {prioridad.get('area','')}"
            )

            st.markdown(
                f"**Prioridad:** {prioridad.get('prioridad','')}"
            )
            st.markdown(
                f"**Tipo de prioridad:** {prioridad.get('tipo_prioridad','-')}"
            )

            st.markdown(
                f"**Puntuación IA:** {prioridad.get('score',0)}/100"
            )

            st.info(
                prioridad.get(
                    "accion",
                    "Realizar actuación."
                )
            )

            st.markdown("### 🧠 Motivos de la decisión")

            motivos = prioridad.get("motivos", [])
            
            if motivos:
                for m in motivos:
                    st.markdown(f"• {m}")
            else:
                st.write(prioridad.get("motivo", ""))

    else:

        st.success(
            "No existen actuaciones prioritarias."
        )

    st.divider()

    st.subheader("🚦 Ranking general")

    prioridades = panel.get("prioridades", [])

    if prioridades:

        for p in prioridades:

            with st.expander(
                f"{p.get('score',0)}/100 · "
                f"{p.get('tipo_prioridad','-')} · "
                f"{p.get('numero_ot','')} · "
                f"{p.get('titulo','')}"
            ):

                st.write(
                    f"Origen: {p.get('origen','')}"
                )

                st.write(
                    f"Centro: {p.get('centro','')}"
                )

                st.write(
                    f"Área: {p.get('area','')}"
                )

                st.write(
                    f"Estado: {p.get('estado','')}"
                )

                st.info(
                    p.get(
                        "accion",
                        ""
                    )
                )

                motivos = p.get("motivos", [])

                if motivos:
                    st.markdown("#### 🧠 Motivos")
                    for m in motivos:
                        st.markdown(f"• {m}")
                else:
                    st.caption(p.get("motivo", ""))

    else:

        st.success(
            "No existen prioridades."
        )
