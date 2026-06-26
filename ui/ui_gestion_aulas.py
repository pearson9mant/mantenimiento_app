import streamlit as st

from database.db import conectar, _sql

from ui.ui_inventario_aulas import pantalla_inventario_aulas
from ui.preventivo_aulas import pantalla_preventivo_aulas
from modules.preventivo_aulas import obtener_estado_ot, resumen_revision_aula


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


def pantalla_correctivos_espacios():
    st.subheader("🔧 Correctivos de espacios")

    correctivos = obtener_correctivos_espacios()

    if not correctivos:
        st.info("No hay correctivos generados desde inspecciones de espacios.")
        return

    filtro_estado = st.selectbox(
        "Filtrar estado",
        ["Todos", "Pendientes", "Resueltos"],
        key="filtro_correctivos_espacios_estado"
    )

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

        resuelta = str(estado_ot).lower() in [
            "finalizada",
            "cerrado",
            "cerrada",
            "cancelada"
        ]

        if filtro_estado == "Pendientes" and resuelta:
            continue

        if filtro_estado == "Resueltos" and not resuelta:
            continue

        icono = "🟢" if resuelta else "🔴"
        estado_visible = "Resuelta" if resuelta else (estado_ot or "Pendiente")

        with st.expander(
            f"{icono} {espacio} · {elemento} · OT {numero_ot} · {estado_visible}",
            expanded=False
        ):
            st.markdown(f"**Fecha inspección:** {fecha or '-'}")
            st.markdown(f"**Centro:** {centro or '-'}")
            st.markdown(f"**Edificio:** {edificio or '-'}")
            st.markdown(f"**Espacio:** {espacio or '-'}")
            st.markdown(f"**Elemento:** {elemento or '-'}")
            st.markdown(f"**OT correctiva:** {numero_ot or '-'}")
            st.markdown(f"**Estado OT:** {estado_visible}")
            st.markdown(f"**Operario:** {operario or '-'}")

            if observaciones:
                st.info(observaciones)


def pantalla_historico_espacios():
    st.subheader("📋 Histórico de espacios")

    historico = obtener_historico_inspecciones_espacios()

    if not historico:
        st.info("Todavía no hay inspecciones registradas.")
        return

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


def pantalla_gestion_aulas():

    st.subheader("🏫 Gestión de espacios")

    st.caption(
        "Inventario, inspecciones, correctivos e histórico de todos los espacios del centro."
    )

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
