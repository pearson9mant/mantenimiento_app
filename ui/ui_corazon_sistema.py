import streamlit as st

from modules.corazon_sistema import diagnosticar_corazon_sistema
from database.db import conectar, _sql
from ui.ui_trabajar_ot import pantalla_trabajar_ot


def obtener_fila_ot_por_numero(numero_ot):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(
            _sql("""
                SELECT *
                FROM ordenes_trabajo
                WHERE numero_ot = ?
                LIMIT 1
            """),
            (numero_ot,)
        )
        fila = cur.fetchone()

    except Exception:
        fila = None

    finally:
        conn.close()

    return fila


def boton_abrir_ot(
    numero_ot,
    key_extra="",
    texto="🔎 Abrir OT",
    tipo="secondary"
):
    if not numero_ot:
        return

    if st.button(
        texto,
        key=f"abrir_corazon_{numero_ot}_{key_extra}",
        use_container_width=True,
        type=tipo
    ):
        st.session_state["corazon_ot_abierta"] = numero_ot
        st.rerun()


def mostrar_ubicacion_ot(datos):
    if not datos:
        return

    ubicacion = " · ".join(
        [
            str(valor).strip()
            for valor in [
                datos.get("centro", ""),
                datos.get("edificio", ""),
                datos.get("planta", ""),
                datos.get("espacio", ""),
            ]
            if str(valor or "").strip()
        ]
    )

    if ubicacion:
        st.caption(f"📍 Ubicación: {ubicacion}")


def mostrar_motivo_principal(datos):
    if not datos:
        return

    motivos = datos.get("motivos", [])

    if motivos:
        motivo_principal = str(motivos[0] or "").strip()
    else:
        motivo_principal = str(
            datos.get("motivo", "") or ""
        ).strip()

    if motivo_principal:
        st.caption(
            f"🧠 Motivo principal: {motivo_principal}"
        )


def mostrar_antiguedad_ot(datos):
    if not datos:
        return

    dias = datos.get("dias_abierta")

    if dias is None:
        return

    try:
        dias = int(dias)
    except (TypeError, ValueError):
        return

    if dias < 0:
        return

    if dias == 0:
        texto = "Creada hoy"
    elif dias == 1:
        texto = "Abierta hace 1 día"
    else:
        texto = f"Abierta hace {dias} días"

    st.caption(f"⏳ {texto}")


def mostrar_corazon_sistema():
    perfil = str(
        st.session_state.get("perfil", "") or ""
    ).strip().lower()

    operario = str(
        st.session_state.get("operario_activo")
        or st.session_state.get("usuario")
        or ""
    ).strip()

    st.title("🎯 Prioridades")

    if perfil == "operario":
        operario_normalizado = (
            operario.lower()
            .replace(".", "")
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
        )

        if (
            "luis" in operario_normalizado
            or "lozano" in operario_normalizado
        ):
            centro_motor = "Pearson 9"
            st.caption("📍 Centro asignado: Pearson 9")

        elif (
            "almeda" in operario_normalizado
            or "juanantonio" in operario_normalizado
        ):
            centro_motor = "Pearson 22"
            st.caption("📍 Centro asignado: Pearson 22")

        else:
            st.error(
                "No se ha podido determinar el centro asignado "
                "a este operario."
            )
            return

    else:
        centro_sel = st.selectbox(
            "Centro",
            ["Todos", "Pearson 22", "Pearson 9"],
            key="corazon_centro"
        )

        centro_motor = (
            None
            if centro_sel == "Todos"
            else centro_sel
        )

    panel = diagnosticar_corazon_sistema(
        centro=centro_motor
    )

    ot_abierta = st.session_state.get(
        "corazon_ot_abierta"
    )

    if ot_abierta:
        fila_ot = obtener_fila_ot_por_numero(
            ot_abierta
        )

        if not fila_ot:
            st.session_state.pop(
                "corazon_ot_abierta",
                None
            )
            st.rerun()

        pantalla_trabajar_ot(
            fila=fila_ot,
            operario_sel=str(fila_ot[10] or ""),
            modo="corazon",
            clave_ot_abierta="corazon_ot_abierta",
            texto_volver="⬅ Volver a Prioridades",
            key_boton_volver="volver_corazon_desde_ot",
            titulo="## 🛠 Trabajar OT desde Prioridades",
        )

        st.stop()

    color = panel.get("color", "verde")
    score = panel.get("score_global", 0)

    if color == "rojo":
        st.error(
            f"🔴 Estado global · "
            f"{score}% · "
            f"{panel.get('estado', '')}"
        )

    elif color == "amarillo":
        st.warning(
            f"🟠 Estado global · "
            f"{score}% · "
            f"{panel.get('estado', '')}"
        )

    else:
        st.success(
            f"🟢 Estado global · "
            f"{score}% · "
            f"{panel.get('estado', '')}"
        )

    st.caption(
        panel.get("mensaje", "")
    )

    kpis = panel.get("kpis", {})

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "OT",
        kpis.get("abiertas", 0)
    )

    c2.metric(
        "Incidencias",
        kpis.get("incidencias", 0)
    )

    c3.metric(
        "Preventivos",
        kpis.get("preventivos", 0)
    )

    c4.metric(
        "Legionella",
        kpis.get("legionella", 0)
    )

    c5.metric(
        "Alta/Urgente",
        kpis.get("urgentes", 0)
    )

    i1, i2, i3 = st.columns(3)

    i1.metric(
        "Operativo",
        f"{panel.get('score_operativo', 0)}%"
    )

    i2.metric(
        "Preventivo",
        f"{panel.get('score_preventivo', 0)}%"
    )

    i3.metric(
        "Sanitario",
        f"{panel.get('score_legionella', 0)}%"
    )

    st.markdown(
        "### 🎯 Si hoy solo hicieras una cosa..."
    )

    prioridad = panel.get("prioridad_hoy")

    with st.container(border=True):
        if prioridad:
            st.markdown(
                f"#### ⭐ "
                f"{prioridad.get('numero_ot', '')}"
            )

            st.markdown(
                f"### "
                f"{prioridad.get('titulo', 'Sin prioridad')}"
            )

            mostrar_ubicacion_ot(prioridad)
            mostrar_motivo_principal(prioridad)
            mostrar_antiguedad_ot(prioridad)

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Tipo",
                prioridad.get(
                    "tipo_prioridad",
                    "-"
                )
            )

            c2.metric(
                "Estado",
                prioridad.get(
                    "estado",
                    "-"
                )
            )

            c3.metric(
                "Puntuación",
                f"{prioridad.get('score', 0)}/100"
            )

            c4.metric(
                "Prioridad",
                prioridad.get(
                    "prioridad",
                    "-"
                )
            )

            st.info(
                prioridad.get(
                    "accion",
                    "Realizar actuación."
                )
            )

            with st.expander(
                "🧠 Ver todos los motivos"
            ):
                motivos = prioridad.get(
                    "motivos",
                    []
                )

                if motivos:
                    for motivo in motivos:
                        st.markdown(
                            f"• {motivo}"
                        )

                else:
                    st.caption(
                        prioridad.get(
                            "motivo",
                            ""
                        )
                    )

            boton_abrir_ot(
                prioridad.get("numero_ot", ""),
                key_extra="prioridad_hoy",
                texto="▶ Empezar esta actuación",
                tipo="primary"
            )

        else:
            st.success(
                "No existen actuaciones prioritarias."
            )

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📍 Ruta",
            "🏫 Edificios",
            "🚦 Ranking",
            "⚠️ Datos"
        ]
    )

    with tab1:
        st.subheader(
            "📍 Ruta inteligente de trabajo"
        )

        ruta = panel.get("ruta", [])

        if not ruta:
            st.info(
                "Todavía no hay suficientes datos "
                "para proponer una ruta inteligente."
            )

        else:
            for i, tramo in enumerate(
                ruta,
                start=1
            ):
                titulo_tramo = (
                    f"{i}. "
                    f"{tramo.get('centro', '')} · "
                    f"{tramo.get('edificio', '')} · "
                    f"{tramo.get('cantidad', 0)} actuaciones"
                )

                with st.expander(
                    titulo_tramo,
                    expanded=i == 1
                ):
                    st.metric(
                        "Prioridad máxima",
                        f"{tramo.get('score', 0)}/100"
                    )

                    st.info(
                        tramo.get(
                            "mensaje",
                            ""
                        )
                    )

                    tipos = tramo.get(
                        "tipos",
                        {}
                    )

                    if tipos:
                        st.markdown(
                            "**Tipos de trabajo**"
                        )

                        for tipo, cantidad in tipos.items():
                            st.markdown(
                                f"• **{tipo}:** "
                                f"{cantidad}"
                            )

                    with st.expander(
                        "Ver trabajos incluidos"
                    ):
                        trabajos = tramo.get(
                            "trabajos",
                            []
                        )

                        for j, trabajo in enumerate(
                            trabajos,
                            start=1
                        ):
                            st.markdown(
                                f"• **"
                                f"{trabajo.get('numero_ot', '')}"
                                f"** · "
                                f"{trabajo.get('tipo_prioridad', '')}"
                                f" · "
                                f"{trabajo.get('titulo', '')}"
                            )

                            mostrar_ubicacion_ot(
                                trabajo
                            )
                            mostrar_antiguedad_ot(
                                trabajo
                            )

                            boton_abrir_ot(
                                trabajo.get("numero_ot", ""),
                                key_extra=f"ruta_{i}_{j}",
                                texto="🔎 Abrir OT"
                            )

    with tab2:
        st.subheader(
            "🏫 Carga por edificio"
        )

        carga_edificios = panel.get(
            "carga_edificios",
            []
        )

        if not carga_edificios:
            st.info(
                "No hay carga por edificio disponible."
            )

        else:
            for edificio in carga_edificios:
                icono = {
                    "rojo": "🔴",
                    "amarillo": "🟠",
                    "verde": "🟢"
                }.get(
                    edificio.get(
                        "color",
                        "verde"
                    ),
                    "🟢"
                )

                titulo_edificio = (
                    f"{icono} "
                    f"{edificio.get('centro', '')} · "
                    f"{edificio.get('edificio', '')} · "
                    f"{edificio.get('total', 0)} actuaciones"
                )

                with st.expander(
                    titulo_edificio,
                    expanded=False
                ):
                    c1, c2, c3 = st.columns(3)

                    c1.metric(
                        "Salud",
                        f"{edificio.get('salud', 0)}%"
                    )

                    c2.metric(
                        "Actuaciones",
                        edificio.get(
                            "total",
                            0
                        )
                    )

                    c3.metric(
                        "Estado",
                        edificio.get(
                            "estado",
                            "-"
                        )
                    )

                    salud = edificio.get(
                        "salud",
                        0
                    )

                    salud = max(
                        0,
                        min(100, salud)
                    )

                    st.progress(
                        salud / 100
                    )

                    c1, c2, c3, c4 = st.columns(4)

                    c1.metric(
                        "🦠 Sanitarias",
                        edificio.get(
                            "sanitarias",
                            0
                        )
                    )

                    c2.metric(
                        "🛠 Preventivas",
                        edificio.get(
                            "preventivas",
                            0
                        )
                    )

                    c3.metric(
                        "🚨 Urgentes",
                        edificio.get(
                            "urgentes",
                            0
                        )
                    )

                    c4.metric(
                        "📋 Otras",
                        edificio.get(
                            "incidencias",
                            0
                        )
                    )

    with tab3:
        st.subheader(
            "🚦 Ranking general"
        )

        prioridades = panel.get(
            "prioridades",
            []
        )

        if not prioridades:
            st.success(
                "No existen prioridades."
            )

        else:
            for i, prioridad_ranking in enumerate(
                prioridades,
                start=1
            ):
                titulo_ranking = (
                    f"{prioridad_ranking.get('score', 0)}/100 · "
                    f"{prioridad_ranking.get('tipo_prioridad', '-')} · "
                    f"{prioridad_ranking.get('numero_ot', '')} · "
                    f"{prioridad_ranking.get('titulo', '')}"
                )

                with st.expander(
                    titulo_ranking,
                    expanded=False
                ):
                    mostrar_ubicacion_ot(
                        prioridad_ranking
                    )
                    mostrar_antiguedad_ot(
                        prioridad_ranking
                    )

                    st.markdown(
                        f"**Origen:** "
                        f"{prioridad_ranking.get('origen', '-')}"
                    )

                    st.markdown(
                        f"**Área:** "
                        f"{prioridad_ranking.get('area', '-')}"
                    )

                    st.markdown(
                        f"**Estado:** "
                        f"{prioridad_ranking.get('estado', '-')}"
                    )

                    st.markdown(
                        f"**Prioridad:** "
                        f"{prioridad_ranking.get('prioridad', '-')}"
                    )

                    st.markdown(
                        f"**Operario:** "
                        f"{prioridad_ranking.get('operario', '-')}"
                    )

                    st.info(
                        prioridad_ranking.get(
                            "accion",
                            ""
                        )
                    )

                    motivos = prioridad_ranking.get(
                        "motivos",
                        []
                    )

                    if motivos:
                        st.markdown(
                            "#### 🧠 Motivos"
                        )

                        for motivo in motivos:
                            st.markdown(
                                f"• {motivo}"
                            )

                    boton_abrir_ot(
                        prioridad_ranking.get("numero_ot", ""),
                        key_extra=f"ranking_{i}",
                        texto="🔎 Abrir OT"
                    )

    with tab4:
        st.subheader(
            "⚠️ Datos incompletos"
        )

        datos_incompletos = panel.get(
            "datos_incompletos",
            []
        )

        if not datos_incompletos:
            st.success(
                "No se han detectado datos "
                "incompletos relevantes."
            )

        else:
            st.warning(
                "Hay OT con edificio o espacio incompleto. "
                "Conviene corregirlas para que el Corazón "
                "agrupe mejor."
            )

            for aviso in datos_incompletos[:50]:
                titulo_aviso = (
                    f"{aviso.get('numero_ot', '')} · "
                    f"{aviso.get('campo', '')}"
                )

                with st.expander(
                    titulo_aviso,
                    expanded=False
                ):
                    st.markdown(
                        aviso.get(
                            "mensaje",
                            ""
                        )
                    )

                    st.caption(
                        f"{aviso.get('centro', '')} · "
                        f"{aviso.get('titulo', '')}"
                    )

    st.markdown("---")
