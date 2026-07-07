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
    
    st.subheader("📍 Ruta inteligente de trabajo")
    
    ruta = panel.get("ruta", [])
    
    if not ruta:
        st.info("Todavía no hay suficientes datos para proponer una ruta inteligente.")
    else:
        for i, tramo in enumerate(ruta, start=1):
            with st.container(border=True):
                st.markdown(
                    f"### {i}. 🏫 {tramo.get('centro', '')} · {tramo.get('edificio', '')}"
                )
    
                st.metric(
                    "Actuaciones agrupadas",
                    tramo.get("cantidad", 0)
                )
    
                st.markdown(f"**Prioridad máxima:** {tramo.get('score', 0)}/100")
                st.info(tramo.get("mensaje", ""))
    
                tipos = tramo.get("tipos", {})
    
                if tipos:
                    st.markdown("#### Tipos de trabajo")
                    for tipo, cantidad in tipos.items():
                        st.markdown(f"• **{tipo}:** {cantidad}")
    
                trabajos = tramo.get("trabajos", [])
    
                with st.expander("Ver trabajos incluidos", expanded=False):
                    for t in trabajos:
                        st.markdown(
                            f"• **{t.get('numero_ot', '')}** · "
                            f"{t.get('tipo_prioridad', '')} · "
                            f"{t.get('titulo', '')}"
                        )
    st.divider()

    st.subheader("🛠 Diagnóstico IA")
    
    st.write("OT analizadas:", len(panel["prioridades"]))
    
    for p in panel["prioridades"][:30]:
        st.write(
            p["numero_ot"],
            "|",
            p["estado"],
            "|",
            p["origen"],
            "|",
            p["centro"],
            "|",
            p["edificio"],
        )

    st.divider()

    st.subheader("🏫 Carga por edificio")
    
    for e in datos.get("carga_edificios", []):
    
        if e["color"] == "verde":
            icono = "🟢"
        elif e["color"] == "amarillo":
            icono = "🟠"
        else:
            icono = "🔴"
    
        with st.container(border=True):
    
            st.markdown(
                f"### {icono} {e['centro']} · {e['edificio']}"
            )
    
            c1, c2, c3 = st.columns(3)
    
            with c1:
                st.metric("Salud", f"{e['salud']}%")
    
            with c2:
                st.metric("Actuaciones", e["total"])
    
            with c3:
                st.metric("Estado", e["estado"])
    
            st.progress(e["salud"] / 100)
    
            c1, c2, c3, c4 = st.columns(4)
    
            c1.metric("🦠 Sanitarias", e["sanitarias"])
            c2.metric("🛠 Preventivas", e["preventivas"])
            c3.metric("🚨 Urgentes", e["urgentes"])
            c4.metric("📋 Otras", e["incidencias"])
    
            if e["color"] == "verde":
                st.success("El edificio presenta una carga de trabajo estable.")
            elif e["color"] == "amarillo":
                st.warning("Conviene planificar actuaciones agrupadas.")
            else:
                st.error("Edificio con elevada carga de trabajo. Priorizar recursos.")
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
