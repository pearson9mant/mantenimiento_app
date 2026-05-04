def pantalla_gerencia():
    st.title("📊 Panel Gerencia")

    df = preparar_dataframe_ordenes()

    if df.empty:
        st.warning("No hay órdenes registradas todavía.")
        return

    df = aplicar_filtros(df)

    if df.empty:
        st.warning("No hay datos con estos filtros.")
        return

    st.markdown("---")

    # =============================
    # MÉTRICAS PRINCIPALES
    # =============================
    pintar_metricas_generales(df)

    st.markdown("---")

    # =============================
    # ALERTAS
    # =============================
    pintar_alertas(df)

    st.markdown("---")

    # =============================
    # DASHBOARD EN BLOQUES
    # =============================

    col1, col2 = st.columns(2)

    # -------------------------
    # SOLICITANTES
    # -------------------------
    with col1:
        st.markdown("### 📌 Solicitante")

        tabla = tabla_resumen(df, "tipo_solicitante", TIPOS_SOLICITANTE)
        if not tabla.empty:
            tabla_chart = tabla.set_index("tipo_solicitante")
            st.bar_chart(tabla_chart[["Hechas", "En proceso", "Faltan"]])

    # -------------------------
    # OPERARIOS
    # -------------------------
    with col2:
        st.markdown("### 👷 Operarios")

        tabla = tabla_resumen(df, "operario")
        if not tabla.empty:
            tabla_chart = tabla.set_index("operario")
            st.bar_chart(tabla_chart[["Hechas", "En proceso", "Faltan"]])

    st.markdown("---")

    col3, col4 = st.columns(2)

    # -------------------------
    # ÁREAS
    # -------------------------
    with col3:
        st.markdown("### 🔧 Áreas")

        tabla = tabla_resumen(df, "area")
        if not tabla.empty:
            tabla_chart = tabla.set_index("area")
            st.bar_chart(tabla_chart[["Hechas", "En proceso", "Faltan"]])

    # -------------------------
    # CENTROS
    # -------------------------
    with col4:
        if MOSTRAR_CENTROS:
            st.markdown("### 🏫 Centros")

            tabla = tabla_resumen(df, "centro")
            if not tabla.empty:
                tabla_chart = tabla.set_index("centro")
                st.bar_chart(tabla_chart[["Hechas", "En proceso", "Faltan"]])

    st.markdown("---")

    # -------------------------
    # MESES (ANCHO COMPLETO)
    # -------------------------
    if MOSTRAR_MESES:
        st.markdown("### 📅 Evolución mensual")

        tabla = tabla_resumen(df, "mes")
        if not tabla.empty:
            tabla_chart = tabla.set_index("mes")
            st.bar_chart(tabla_chart[["Hechas", "En proceso", "Faltan"]])

    st.markdown("---")

    # =============================
    # ÓRDENES PROBLEMÁTICAS
    # =============================
    st.markdown("### ⚠️ Órdenes +7 días")

    antiguas = df[
        (df["estado_resumen"] != "Hechas") &
        (df["dias_abierta"] >= 7)
    ]

    if antiguas.empty:
        st.success("Todo al día 👍")
    else:
        st.dataframe(
            antiguas[[
                "numero_ot", "descripcion", "estado",
                "centro", "espacio", "operario", "dias_abierta"
            ]],
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # =============================
    # INVENTARIOS (COMPLETOS)
    # =============================
    if MOSTRAR_INVENTARIO:

        st.markdown("## 📦 Inventario mantenimiento")
        pantalla_inventario()

        st.markdown("---")

        st.markdown("## 🏫 Inventario aulas")
        pantalla_inventario_aulas()
