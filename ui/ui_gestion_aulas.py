import streamlit as st

from database.db import conectar, _sql

from ui.ui_inventario_aulas import pantalla_inventario_aulas
from ui.preventivo_aulas import pantalla_preventivo_aulas
from modules.espacios_historial import obtener_historial_espacios
from modules.preventivo_aulas import (
    obtener_estado_ot,
    resumen_revision_aula,
    obtener_items_revision_aula,
)


def es_ot_resuelta(estado_ot):
    return str(estado_ot or "").lower() in [
        "finalizada",
        "cerrado",
        "cerrada",
        "cancelada"
    ]


def obtener_correctivos_espacios():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT
            r.fecha,
            r.centro,
            r.edificio,
            r.espacio,
            r.operario,
            i.elemento,
            i.estado,
            i.observaciones,
            i.numero_ot_correctiva
        FROM preventivo_aulas_items i
        INNER JOIN preventivo_aulas r
            ON i.revision_id = r.id
        WHERE i.estado = ?
          AND i.numero_ot_correctiva IS NOT NULL
          AND i.numero_ot_correctiva <> ''
        ORDER BY r.fecha DESC, r.id DESC
    """), ("Avería",))

    datos = cur.fetchall()
    conn.close()
    return datos


def obtener_historico_inspecciones_espacios():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT
            id,
            fecha,
            centro,
            edificio,
            espacio,
            operario,
            estado,
            observaciones,
            numero_ot_preventiva
        FROM preventivo_aulas
        ORDER BY id DESC
    """))

    datos = cur.fetchall()
    conn.close()
    return datos


def icono_estado_item(estado):
    estado = str(estado or "")

    if estado == "Avería":
        return "🔴"

    if estado == "Revisar":
        return "🟡"

    return "✅"


def pantalla_correctivos_espacios():
    st.subheader("🔧 Correctivos de espacios")

    correctivos = obtener_correctivos_espacios()

    if not correctivos:
        st.info("No hay correctivos generados desde inspecciones de espacios.")
        return

    enriquecidos = []

    for c in correctivos:
        (
            fecha,
            centro,
            edificio,
            espacio,
            operario,
            elemento,
            estado_item,
            observaciones,
            numero_ot
        ) = c

        estado_ot = obtener_estado_ot(numero_ot)
        resuelta = es_ot_resuelta(estado_ot)

        enriquecidos.append({
            "fecha": fecha,
            "centro": centro,
            "edificio": edificio,
            "espacio": espacio,
            "operario": operario,
            "elemento": elemento,
            "estado_item": estado_item,
            "observaciones": observaciones,
            "numero_ot": numero_ot,
            "estado_ot": estado_ot,
            "resuelta": resuelta,
        })

    total = len(enriquecidos)
    pendientes_total = len([x for x in enriquecidos if not x["resuelta"]])
    resueltas_total = len([x for x in enriquecidos if x["resuelta"]])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total correctivos", total)
    c2.metric("Pendientes", pendientes_total)
    c3.metric("Resueltos", resueltas_total)

    centros = sorted(list(set([str(x["centro"]) for x in enriquecidos if x["centro"]])))
    espacios = sorted(list(set([str(x["espacio"]) for x in enriquecidos if x["espacio"]])))

    f1, f2, f3 = st.columns(3)

    with f1:
        filtro_estado = st.selectbox(
            "Filtrar estado",
            ["Todos", "Pendientes", "Resueltos"],
            key="filtro_correctivos_espacios_estado"
        )

    with f2:
        filtro_centro = st.selectbox(
            "Filtrar centro",
            ["Todos"] + centros,
            key="filtro_correctivos_espacios_centro"
        )

    with f3:
        filtro_espacio = st.selectbox(
            "Filtrar espacio",
            ["Todos"] + espacios,
            key="filtro_correctivos_espacios_espacio"
        )

    mostrados = 0

    for x in enriquecidos:

        if filtro_estado == "Pendientes" and x["resuelta"]:
            continue

        if filtro_estado == "Resueltos" and not x["resuelta"]:
            continue

        if filtro_centro != "Todos" and str(x["centro"]) != filtro_centro:
            continue

        if filtro_espacio != "Todos" and str(x["espacio"]) != filtro_espacio:
            continue

        mostrados += 1

        icono = "🟢" if x["resuelta"] else "🔴"
        estado_visible = "Resuelta" if x["resuelta"] else (x["estado_ot"] or "Pendiente")

        with st.expander(
            f"{icono} {x['espacio']} · {x['elemento']} · OT {x['numero_ot']} · {estado_visible}",
            expanded=False
        ):
            st.markdown(f"**Fecha inspección:** {x['fecha'] or '-'}")
            st.markdown(f"**Centro:** {x['centro'] or '-'}")
            st.markdown(f"**Edificio:** {x['edificio'] or '-'}")
            st.markdown(f"**Espacio:** {x['espacio'] or '-'}")
            st.markdown(f"**Elemento:** {x['elemento'] or '-'}")
            st.markdown(f"**OT correctiva:** {x['numero_ot'] or '-'}")
            st.markdown(f"**Estado OT:** {estado_visible}")
            st.markdown(f"**Operario:** {x['operario'] or '-'}")

            if x["observaciones"]:
                st.info(x["observaciones"])

    if mostrados == 0:
        st.info("No hay correctivos con esos filtros.")


def pantalla_historico_espacios():
    st.subheader("📋 Histórico de espacios")

    historico = obtener_historico_inspecciones_espacios()

    if not historico:
        st.info("Todavía no hay inspecciones registradas.")
        return

    # =====================================
    # RESUMEN GENERAL + SEMÁFORO
    # =====================================

    total_inspecciones = len(historico)
    total_pendientes = 0
    total_resueltas = 0
    total_revisar = 0

    espacios_estado = {}

    for h in historico:
        revision_id = h[0]
        espacio = str(h[4] or "")

        resumen = resumen_revision_aula(revision_id)

        pendientes = resumen.get("averias_pendientes", 0)
        resueltas = resumen.get("averias_resueltas", 0)
        revisar = resumen.get("revisar", 0)

        total_pendientes += pendientes
        total_resueltas += resueltas
        total_revisar += revisar

        if espacio:
            if pendientes > 0:
                espacios_estado[espacio] = "rojo"
            elif revisar > 0 and espacios_estado.get(espacio) != "rojo":
                espacios_estado[espacio] = "amarillo"
            elif espacio not in espacios_estado:
                espacios_estado[espacio] = "verde"

    espacios_verdes = len([x for x in espacios_estado.values() if x == "verde"])
    espacios_amarillos = len([x for x in espacios_estado.values() if x == "amarillo"])
    espacios_rojos = len([x for x in espacios_estado.values() if x == "rojo"])

    st.markdown("### 📊 Resumen general")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inspecciones", total_inspecciones)
    m2.metric("Averías pendientes", total_pendientes)
    m3.metric("Averías resueltas", total_resueltas)
    m4.metric("A revisar", total_revisar)

    st.markdown("### 🚦 Estado de espacios")

    s1, s2, s3 = st.columns(3)
    s1.metric("🟢 Correctos", espacios_verdes)
    s2.metric("🟡 Revisar", espacios_amarillos)
    s3.metric("🔴 Avería", espacios_rojos)

    st.markdown("### Semáforo por espacio")

    for espacio, estado_espacio in sorted(espacios_estado.items()):
        if estado_espacio == "rojo":
            st.error(f"🔴 {espacio} · Averías pendientes")
        elif estado_espacio == "amarillo":
            st.warning(f"🟡 {espacio} · Elementos a revisar")
        else:
            st.success(f"🟢 {espacio} · Correcto")

    st.markdown("---")

    # =====================================
    # FILTROS
    # =====================================

    centros = sorted(list(set([str(h[2]) for h in historico if h[2]])))
    espacios = sorted(list(set([str(h[4]) for h in historico if h[4]])))

    col1, col2 = st.columns(2)

    with col1:
        filtro_centro = st.selectbox(
            "Filtrar centro",
            ["Todos"] + centros,
            key="hist_espacios_filtro_centro"
        )

    with col2:
        filtro_espacio = st.selectbox(
            "Filtrar espacio",
            ["Todos"] + espacios,
            key="hist_espacios_filtro_espacio"
        )

    for h in historico:
        (
            revision_id,
            fecha,
            centro,
            edificio,
            espacio,
            operario,
            estado,
            observaciones,
            numero_ot_preventiva
        ) = h

        if filtro_centro != "Todos" and str(centro) != filtro_centro:
            continue

        if filtro_espacio != "Todos" and str(espacio) != filtro_espacio:
            continue

        resumen = resumen_revision_aula(revision_id)

        detectadas = resumen.get("averias_detectadas", resumen.get("averias", 0))
        pendientes = resumen.get("averias_pendientes", 0)
        resueltas = resumen.get("averias_resueltas", 0)

        if pendientes > 0:
            icono = "🔴"
        elif detectadas > 0 and pendientes == 0:
            icono = "🟢"
        elif resumen.get("revisar", 0) > 0:
            icono = "🟡"
        else:
            icono = "✅"

        titulo = (
            f"{icono} {fecha or '-'} · {centro} · {edificio} · {espacio} · "
            f"Correctos: {resumen.get('correctos', 0)} · "
            f"Revisar: {resumen.get('revisar', 0)} · "
            f"Averías: {detectadas} · "
            f"Pendientes: {pendientes} · "
            f"Resueltas: {resueltas}"
        )

        with st.expander(titulo, expanded=False):
            st.markdown(f"**Fecha:** {fecha or '-'}")
            st.markdown(f"**Centro:** {centro or '-'}")
            st.markdown(f"**Edificio:** {edificio or '-'}")
            st.markdown(f"**Espacio:** {espacio or '-'}")
            st.markdown(f"**Operario:** {operario or '-'}")
            st.markdown(f"**Estado revisión:** {estado or '-'}")
            st.markdown(f"**OT preventiva origen:** {numero_ot_preventiva or '-'}")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Correctos", resumen.get("correctos", 0))
            c2.metric("Revisar", resumen.get("revisar", 0))
            c3.metric("Averías", detectadas)
            c4.metric("Pendientes", pendientes)
            c5.metric("Resueltas", resueltas)

            if observaciones:
                st.info(observaciones)

            st.markdown("---")
            st.markdown("### Detalle de elementos revisados")

            items = obtener_items_revision_aula(revision_id)

            if not items:
                st.info("Esta inspección no tiene elementos registrados.")
            else:
                for item in items:
                    (
                        item_id,
                        _revision_id,
                        elemento,
                        estado_item,
                        obs_item,
                        foto,
                        crear_correctivo,
                        numero_ot_correctiva,
                    ) = item

                    icono_item = icono_estado_item(estado_item)

                    linea = f"{icono_item} **{elemento}** · {estado_item or '-'}"

                    if numero_ot_correctiva:
                        estado_ot = obtener_estado_ot(numero_ot_correctiva)
                        estado_ot_visible = estado_ot or "Pendiente"
                        linea += f" · OT: `{numero_ot_correctiva}` · {estado_ot_visible}"

                    st.markdown(linea)

                    if obs_item:
                        st.caption(obs_item)

                    if foto:
                        try:
                            st.image(foto, width=220)
                        except Exception:
                            st.caption("Foto no disponible.")

            st.markdown("---")
            st.markdown("### Historial de OTs del espacio")

            historial_ot = obtener_historial_espacios(
                centro=centro,
                edificio=edificio,
                espacio=espacio
            )

            if not historial_ot:
                st.info("Este espacio no tiene OTs finalizadas registradas.")
            else:
                for h_ot in historial_ot[:10]:
                    (
                        id_hist,
                        fecha_hist,
                        centro_hist,
                        edificio_hist,
                        espacio_hist,
                        elemento_hist,
                        tipo_hist,
                        numero_ot_hist,
                        descripcion_hist,
                        area_hist,
                        estado_hist,
                        operario_hist,
                        observaciones_hist
                    ) = h_ot

                    st.markdown(
                        f"✅ **{fecha_hist or '-'}** · "
                        f"OT `{numero_ot_hist or '-'}` · "
                        f"{area_hist or '-'} · "
                        f"{operario_hist or '-'}"
                    )

                    st.caption(descripcion_hist or "")

                    if observaciones_hist:
                        st.info(observaciones_hist)
def obtener_metricas_gestion_espacios():
    historico = obtener_historico_inspecciones_espacios()
    correctivos = obtener_correctivos_espacios()

    espacios = set()
    inspecciones = len(historico)
    correctivos_pendientes = 0
    espacios_con_averia = set()

    for h in historico:
        espacio = str(h[4] or "").strip()
        if espacio:
            espacios.add(espacio)

        resumen = resumen_revision_aula(h[0])
        if resumen.get("averias_pendientes", 0) > 0 and espacio:
            espacios_con_averia.add(espacio)

    for c in correctivos:
        numero_ot = c[8]
        estado_ot = obtener_estado_ot(numero_ot)

        if not es_ot_resuelta(estado_ot):
            correctivos_pendientes += 1

    return {
        "espacios": len(espacios),
        "inspecciones": inspecciones,
        "correctivos_pendientes": correctivos_pendientes,
        "espacios_con_averia": len(espacios_con_averia),
    }

def pantalla_gestion_aulas():

    st.markdown("## 🏫 Panel Gestión de Espacios")

    st.caption(
        "Control centralizado de inventario, inspecciones, correctivos e histórico de aulas y espacios."
    )

    metricas = obtener_metricas_gestion_espacios()

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("🏫 Espacios", metricas["espacios"])

    with col2:
        st.metric("🔎 Inspecciones", metricas["inspecciones"])

    with col3:
        st.metric("🔧 Correctivos", metricas["correctivos_pendientes"])

    with col4:
        st.metric("🔴 Con avería", metricas["espacios_con_averia"])

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Inventario",
        "🔎 Inspecciones",
        "🔧 Correctivos",
        "📋 Histórico",
    ])

    with tab1:
        pantalla_inventario_aulas()

    with tab2:
        pantalla_preventivo_aulas()

    with tab3:
        pantalla_correctivos_espacios()

    with tab4:
        pantalla_historico_espacios()
