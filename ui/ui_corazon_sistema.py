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


def mostrar_prioridad_visual(prioridad):
    prioridad_normalizada = str(
        prioridad or ""
    ).strip().lower()

    if "urgente" in prioridad_normalizada:
        return "🔴 Urgente"

    if "alta" in prioridad_normalizada:
        return "🟠 Alta"

    if "media" in prioridad_normalizada:
        return "🟡 Media"

    if "baja" in prioridad_normalizada:
        return "🟢 Baja"

    if "normal" in prioridad_normalizada:
        return "🟢 Normal"

    return str(prioridad or "-").strip() or "-"




def icono_recurrencia(nivel):
    nivel_normalizado = str(nivel or "").strip().lower()

    if nivel_normalizado == "muy alta":
        return "🔴"
    if nivel_normalizado == "alta":
        return "🟠"
    if nivel_normalizado == "media":
        return "🟡"
    if nivel_normalizado == "baja":
        return "🟢"

    return "⚪"


def mostrar_historial_espacio(datos, titulo="📚 Historial del espacio"):
    if not datos:
        return

    historial = datos.get("historial_espacio", {}) or {}
    total = int(historial.get("total", 0) or 0)
    misma_area = int(historial.get("misma_area", 0) or 0)
    nivel = str(
        historial.get("nivel_recurrencia", "Sin datos") or "Sin datos"
    ).strip()
    mensaje = str(
        historial.get("mensaje_recurrencia", "") or ""
    ).strip()

    st.markdown(f"#### {titulo}")

    if total <= 0:
        st.info(
            "📭 No constan actuaciones anteriores en este espacio. "
            "No se detecta recurrencia."
        )
        return

    h1, h2, h3 = st.columns(3)

    h1.metric(
        "Actuaciones anteriores",
        total
    )

    h2.metric(
        "Misma área",
        misma_area
    )

    h3.metric(
        "Recurrencia",
        f"{icono_recurrencia(nivel)} {nivel}"
    )

    if historial.get("es_recurrente"):
        st.warning(
            "⚠️ Este espacio presenta averías repetidas. "
            "Conviene valorar una revisión completa de la instalación "
            "o del elemento afectado, además de resolver esta OT."
        )
    elif mensaje:
        st.caption(f"🧠 {mensaje}")

    ultimas = historial.get("ultimas", []) or []

    if ultimas:
        with st.expander("📅 Ver últimas actuaciones del espacio"):
            for i, actuacion in enumerate(ultimas, start=1):
                numero_ot = str(
                    actuacion.get("numero_ot", "") or ""
                ).strip()
                fecha = str(
                    actuacion.get("fecha", "") or ""
                ).strip()
                area = str(
                    actuacion.get("area", "") or ""
                ).strip()
                descripcion = str(
                    actuacion.get("descripcion", "") or ""
                ).strip()
                tipo = str(
                    actuacion.get("tipo", "") or ""
                ).strip()

                cabecera = " · ".join(
                    [
                        valor
                        for valor in [
                            fecha,
                            numero_ot,
                            area,
                            tipo,
                        ]
                        if valor
                    ]
                )

                if cabecera:
                    st.markdown(f"**{cabecera}**")

                if descripcion:
                    st.caption(descripcion)

                if i < len(ultimas):
                    st.markdown("---")


def mostrar_impacto_esperado(datos):
    if not datos:
        return

    impactos = []
    historial = datos.get("historial_espacio", {}) or {}
    motivos = [
        str(motivo or "").lower()
        for motivo in datos.get("motivos", []) or []
    ]

    if any(
        palabra in " ".join(motivos)
        for palabra in ["agua", "fuga", "pérdida", "perdida"]
    ):
        impactos.append("Reduce el riesgo de daños provocados por agua.")

    if any(
        palabra in " ".join(motivos)
        for palabra in ["eléctr", "electric"]
    ):
        impactos.append("Reduce un posible riesgo eléctrico.")

    if any(
        palabra in " ".join(motivos)
        for palabra in ["legionella", "sanitario"]
    ):
        impactos.append("Reduce el principal riesgo sanitario pendiente.")

    if historial.get("es_recurrente"):
        impactos.append(
            "Puede evitar nuevas intervenciones repetidas en el mismo espacio."
        )

    if int(historial.get("misma_area", 0) or 0) >= 2:
        impactos.append(
            "Permite atacar un problema repetido de la misma especialidad."
        )

    if datos.get("dias_abierta") is not None:
        try:
            if int(datos.get("dias_abierta")) >= 30:
                impactos.append(
                    "Reduce carga antigua acumulada en el sistema."
                )
        except (TypeError, ValueError):
            pass

    if not impactos:
        impactos.append(
            "Reduce la carga prioritaria del centro y mejora el estado operativo."
        )

    st.markdown("#### 🎯 Impacto esperado")

    texto_impacto = "\n".join(
        f"✓ {impacto}"
        for impacto in impactos[:4]
    )

    st.success(texto_impacto)



def mostrar_oportunidad_misma_zona(prioridad, prioridades):
    """
    Muestra únicamente otras OT de la misma planta.

    Mantiene el resto del flujo sin cambios y evita agrupar trabajos
    que estén en plantas diferentes aunque pertenezcan al mismo edificio.
    """
    if not prioridad or not prioridades:
        return

    numero_actual = str(
        prioridad.get("numero_ot", "") or ""
    ).strip()

    centro_actual = str(
        prioridad.get("centro", "") or ""
    ).strip()

    edificio_actual = str(
        prioridad.get("edificio", "") or ""
    ).strip()

    planta_actual = str(
        prioridad.get("planta", "") or ""
    ).strip()

    # Sin planta informada no se puede garantizar que las OT
    # pertenezcan realmente a la misma zona de trabajo.
    if not planta_actual or planta_actual.lower() in [
        "nan",
        "none",
        "null",
        "-",
        "sin planta",
    ]:
        return

    trabajos_planta = []

    for trabajo in prioridades:
        numero = str(
            trabajo.get("numero_ot", "") or ""
        ).strip()

        if numero == numero_actual:
            continue

        if str(trabajo.get("centro", "") or "").strip() != centro_actual:
            continue

        if str(trabajo.get("edificio", "") or "").strip() != edificio_actual:
            continue

        planta_trabajo = str(
            trabajo.get("planta", "") or ""
        ).strip()

        if planta_trabajo != planta_actual:
            continue

        trabajos_planta.append(trabajo)

    if not trabajos_planta:
        return

    st.markdown("#### 🧭 Aprovechar el desplazamiento")

    st.info(
        f"En esta misma planta ({planta_actual}) hay "
        f"{len(trabajos_planta)} actuaciones adicionales. "
        "Conviene revisarlas antes de cambiar de planta."
    )

    with st.expander(
        f"Ver actuaciones de la misma planta ({len(trabajos_planta)})"
    ):
        for i, trabajo in enumerate(trabajos_planta[:6], start=1):
            st.markdown(
                f"**{trabajo.get('numero_ot', '')}** · "
                f"{trabajo.get('titulo', '')}"
            )

            st.caption(
                " · ".join(
                    [
                        valor
                        for valor in [
                            str(trabajo.get("espacio", "") or "").strip(),
                            str(trabajo.get("area", "") or "").strip(),
                            f"{trabajo.get('score', 0)}/100",
                        ]
                        if valor
                    ]
                )
            )

            boton_abrir_ot(
                trabajo.get("numero_ot", ""),
                key_extra=f"misma_planta_{i}",
                texto="🔎 Abrir esta OT"
            )



def etiqueta_motivo_principal(datos):
    if not datos:
        return "📋 Prioritaria"

    texto = " ".join(
        [
            str(datos.get("area", "") or ""),
            str(datos.get("origen", "") or ""),
            str(datos.get("titulo", "") or ""),
            " ".join(
                str(motivo or "")
                for motivo in datos.get("motivos", []) or []
            ),
        ]
    ).lower()

    historial = datos.get("historial_espacio", {}) or {}

    if "legionella" in texto:
        return "🦠 Sanitaria"

    if any(palabra in texto for palabra in ["fuga", "agua", "perdida", "pérdida"]):
        return "💧 Agua"

    if any(palabra in texto for palabra in ["eléctr", "electric"]):
        return "⚡ Electricidad"

    if historial.get("es_recurrente"):
        return "🔁 Recurrente"

    try:
        if int(datos.get("dias_abierta")) >= 60:
            return "📅 Muy antigua"
    except (TypeError, ValueError):
        pass

    prioridad = str(datos.get("prioridad", "") or "").lower()

    if "urgente" in prioridad:
        return "🚨 Urgente"

    if "alta" in prioridad:
        return "🟠 Alta"

    return "📋 Prioritaria"


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
            st.success("🏆 Recomendación nº 1 del Corazón")

            st.caption(
                f"⭐ OT {prioridad.get('numero_ot', '')}"
            )

            st.markdown(
                f"## "
                f"{prioridad.get('titulo', 'Sin prioridad')}"
            )

            st.caption(
                "🎯 Recomendación generada automáticamente según "
                "riesgo, prioridad, antigüedad y agrupación de trabajos."
            )

            mostrar_ubicacion_ot(prioridad)
            mostrar_antiguedad_ot(prioridad)

            st.markdown("#### 🧠 ¿Por qué la recomienda?")

            motivos_resumen = prioridad.get("motivos", []) or []

            if motivos_resumen:
                for motivo in motivos_resumen[:4]:
                    st.markdown(f"✓ {motivo}")
            else:
                st.caption(
                    prioridad.get(
                        "motivo",
                        "Actuación prioritaria según el Corazón del Sistema."
                    )
                )

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Área",
                prioridad.get(
                    "area",
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
                "Confianza",
                f"{prioridad.get('score', 0)}/100"
            )

            c4.metric(
                "Prioridad",
                mostrar_prioridad_visual(
                    prioridad.get(
                        "prioridad",
                        "-"
                    )
                )
            )

            st.info(
                "🎯 Actuación recomendada por el Corazón del Sistema."
            )

            mostrar_historial_espacio(prioridad)
            mostrar_impacto_esperado(prioridad)
            mostrar_oportunidad_misma_zona(
                prioridad,
                panel.get("prioridades", [])
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
            "📍 Ruta inteligente por plantas"
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
                planta = str(
                    tramo.get("planta", "") or "Sin planta"
                ).strip()

                titulo_tramo = (
                    f"{i}. "
                    f"{tramo.get('centro', '')} · "
                    f"{tramo.get('edificio', '')} · "
                    f"{planta} · "
                    f"{tramo.get('cantidad', 0)} actuaciones"
                )

                with st.expander(
                    titulo_tramo,
                    expanded=i == 1
                ):
                    c1, c2, c3 = st.columns(3)

                    c1.metric(
                        "Prioridad máxima",
                        f"{tramo.get('score', 0)}/100"
                    )

                    c2.metric(
                        "Actuaciones",
                        tramo.get(
                            "cantidad",
                            0
                        )
                    )

                    c3.metric(
                        "Planta",
                        planta
                    )

                    mensaje_tramo = str(
                        tramo.get("mensaje", "") or ""
                    ).strip()

                    if planta == "Sin planta":
                        st.warning(
                            mensaje_tramo
                            or (
                                "Hay actuaciones sin planta informada. "
                                "Conviene completar este dato."
                            )
                        )
                    else:
                        st.info(
                            mensaje_tramo
                        )

                    tipos = tramo.get(
                        "tipos",
                        {}
                    )

                    if tipos:
                        st.markdown(
                            "#### 🧰 Tipos de trabajo"
                        )

                        columnas_tipos = st.columns(
                            min(4, len(tipos))
                        )

                        for indice_tipo, (
                            tipo,
                            cantidad
                        ) in enumerate(
                            tipos.items()
                        ):
                            columnas_tipos[
                                indice_tipo % len(columnas_tipos)
                            ].metric(
                                tipo,
                                cantidad
                            )

                    primera_ot = tramo.get(
                        "primera_ot"
                    ) or {}

                    numero_ot_recomendada = str(
                        tramo.get(
                            "numero_ot_recomendada",
                            ""
                        )
                        or primera_ot.get(
                            "numero_ot",
                            ""
                        )
                        or ""
                    ).strip()

                    titulo_ot_recomendada = str(
                        tramo.get(
                            "titulo_ot_recomendada",
                            ""
                        )
                        or primera_ot.get(
                            "titulo",
                            ""
                        )
                        or ""
                    ).strip()

                    if numero_ot_recomendada:
                        st.markdown(
                            "#### 🎯 Primera actuación recomendada"
                        )

                        with st.container(border=True):
                            st.markdown(
                                f"**{numero_ot_recomendada}**"
                            )

                            if titulo_ot_recomendada:
                                st.markdown(
                                    titulo_ot_recomendada
                                )

                            mostrar_ubicacion_ot(
                                primera_ot
                            )
                            mostrar_antiguedad_ot(
                                primera_ot
                            )

                            boton_abrir_ot(
                                numero_ot_recomendada,
                                key_extra=f"ruta_principal_{i}",
                                texto="▶ Empezar esta planta",
                                tipo="primary"
                            )

                    trabajos = tramo.get(
                        "trabajos",
                        []
                    )

                    with st.expander(
                        f"Ver trabajos de esta planta ({len(trabajos)})"
                    ):
                        if not trabajos:
                            st.caption(
                                "No hay trabajos disponibles "
                                "en este tramo."
                            )

                        for j, trabajo in enumerate(
                            trabajos,
                            start=1
                        ):
                            st.markdown(
                                f"**{trabajo.get('numero_ot', '')}** · "
                                f"{trabajo.get('tipo_prioridad', '')} · "
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

                            if j < len(trabajos):
                                st.markdown("---")

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
                etiqueta = etiqueta_motivo_principal(
                    prioridad_ranking
                )

                titulo_ranking = (
                    f"{prioridad_ranking.get('score', 0)}/100 · "
                    f"{etiqueta} · "
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

                    mostrar_historial_espacio(
                        prioridad_ranking,
                        titulo="📚 Historial del espacio"
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
