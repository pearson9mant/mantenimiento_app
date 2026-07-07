import streamlit as st

from modules.corazon_sistema import diagnosticar_corazon_sistema


def mostrar_corazon_sistema():
    st.title("❤️ Corazón del Sistema")

    centro_sel = st.selectbox(
        "Centro",
        ["Todos", "Pearson 22", "Pearson 9"],
        key="corazon_centro"
    )

    centro_motor = None if centro_sel == "Todos" else centro_sel
    panel = diagnosticar_corazon_sistema(centro=centro_motor)

    color = panel.get("color", "verde")
    score = panel.get("score_global", 0)

    if color == "rojo":
        st.error(f"🔴 Estado global · {score}% · {panel.get('estado', '')}")
    elif color == "amarillo":
        st.warning(f"🟠 Estado global · {score}% · {panel.get('estado', '')}")
    else:
        st.success(f"🟢 Estado global · {score}% · {panel.get('estado', '')}")

    st.markdown(f"**{panel.get('mensaje', '')}**")

    st.divider()

    st.subheader("📊 Indicadores principales")

    kpis = panel.get("kpis", {})

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("OT abiertas", kpis.get("abiertas", 0))
    c2.metric("Incidencias", kpis.get("incidencias", 0))
    c3.metric("Preventivos", kpis.get("preventivos", 0))
    c4.metric("Legionella", kpis.get("legionella", 0))
    c5.metric("Alta/Urgente", kpis.get("urgentes", 0))

    st.subheader("🧠 Índices principales")

    i1, i2, i3 = st.columns(3)
    i1.metric("Operativo", f"{panel.get('score_operativo', 0)}%")
    i2.metric("Preventivo", f"{panel.get('score_preventivo', 0)}%")
    i3.metric("Sanitario", f"{panel.get('score_legionella', 0)}%")

    st.divider()

    st.subheader("🎯 Si hoy solo hicieras una cosa...")

    prioridad = panel.get("prioridad_hoy")

    with st.container(border=True):
        if prioridad:
            st.markdown(f"### ⭐ {prioridad.get('numero_ot', '')}")
            st.markdown(f"## {prioridad.get('titulo', 'Sin prioridad')}")

            st.caption(
                f"{prioridad.get('centro', '')} · "
                f"{prioridad.get('edificio', '')} · "
                f"{prioridad.get('espacio', '')}"
            )

            st.markdown(f"**Origen:** {prioridad.get('origen', '-')}")
            st.markdown(f"**Área:** {prioridad.get('area', '-')}")
            st.markdown(f"**Prioridad:** {prioridad.get('prioridad', '-')}")
            st.markdown(f"**Tipo de prioridad:** {prioridad.get('tipo_prioridad', '-')}")
            st.markdown(f"**Puntuación IA:** {prioridad.get('score', 0)}/100")

            st.info(prioridad.get("accion", "Realizar actuación."))

            st.markdown("### 🧠 Motivos de la decisión")

            motivos = prioridad.get("motivos", [])

            if motivos:
                for m in motivos:
                    st.markdown(f"• {m}")
            else:
                st.write(prioridad.get("motivo", ""))

        else:
            st.success("No existen actuaciones prioritarias.")

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

                st.metric("Actuaciones agrupadas", tramo.get("cantidad", 0))
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

    st.subheader("🏫 Carga por edificio")

    carga_edificios = panel.get("carga_edificios", [])

    if not carga_edificios:
        st.info("No hay carga por edificio disponible.")
    else:
        for e in carga_edificios:
            color_edificio = e.get("color", "verde")

            if color_edificio == "rojo":
                icono = "🔴"
            elif color_edificio == "amarillo":
                icono = "🟠"
            else:
                icono = "🟢"

            with st.container(border=True):
                st.markdown(
                    f"### {icono} {e.get('centro', '')} · {e.get('edificio', '')}"
                )

                c1, c2, c3 = st.columns(3)
                c1.metric("Salud", f"{e.get('salud', 0)}%")
                c2.metric("Actuaciones", e.get("total", 0))
                c3.metric("Estado", e.get("estado", "-"))

                st.progress(e.get("salud", 0) / 100)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("🦠 Sanitarias", e.get("sanitarias", 0))
                c2.metric("🛠 Preventivas", e.get("preventivas", 0))
                c3.metric("🚨 Urgentes", e.get("urgentes", 0))
                c4.metric("📋 Otras", e.get("incidencias", 0))

                if color_edificio == "verde":
                    st.success("El edificio presenta una carga de trabajo estable.")
                elif color_edificio == "amarillo":
                    st.warning("Conviene planificar actuaciones agrupadas.")
                else:
                    st.error("Edificio con elevada carga de trabajo. Priorizar recursos.")

    st.divider()

    datos_incompletos = panel.get("datos_incompletos", [])

    if datos_incompletos:
        with st.expander("⚠️ Datos incompletos detectados", expanded=False):
            st.warning(
                "Hay OT con edificio o espacio incompleto. Conviene corregirlas para que el Corazón agrupe mejor."
            )

            for aviso in datos_incompletos[:30]:
                st.markdown(
                    f"• **{aviso.get('numero_ot', '')}** · "
                    f"{aviso.get('campo', '')} · "
                    f"{aviso.get('mensaje', '')}"
                )
                st.caption(
                    f"{aviso.get('centro', '')} · {aviso.get('titulo', '')}"
                )

    st.subheader("🚦 Ranking general")

    prioridades = panel.get("prioridades", [])

    if not prioridades:
        st.success("No existen prioridades.")
    else:
        for p in prioridades:
            with st.expander(
                f"{p.get('score', 0)}/100 · "
                f"{p.get('tipo_prioridad', '-')} · "
                f"{p.get('numero_ot', '')} · "
                f"{p.get('titulo', '')}",
                expanded=False
            ):
                st.markdown(f"### {p.get('titulo', '')}")

                st.caption(
                    f"{p.get('centro', '')} · "
                    f"{p.get('edificio', '')} · "
                    f"{p.get('espacio', '')}"
                )

                st.markdown(f"**Origen:** {p.get('origen', '-')}")
                st.markdown(f"**Área:** {p.get('area', '-')}")
                st.markdown(f"**Estado:** {p.get('estado', '-')}")
                st.markdown(f"**Prioridad:** {p.get('prioridad', '-')}")
                st.markdown(f"**Operario:** {p.get('operario', '-')}")
                st.info(p.get("accion", ""))

                motivos = p.get("motivos", [])

                if motivos:
                    st.markdown("#### 🧠 Motivos")
                    for m in motivos:
                        st.markdown(f"• {m}")
                else:
                    st.caption(p.get("motivo", ""))

    st.markdown("---")
