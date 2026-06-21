import streamlit as st


def tarjeta_kpi(titulo, valor, icono):

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border-radius:18px;
            padding:18px;
            text-align:center;
            box-shadow:0 3px 10px rgba(0,0,0,0.08);
            border:1px solid #e5e7eb;
        ">
            <div style="font-size:32px;">{icono}</div>
            <div style="font-size:14px;color:#64748b;">
                {titulo}
            </div>
            <div style="
                font-size:32px;
                font-weight:800;
                color:#0f172a;
            ">
                {valor}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def pantalla_panel_legionella():

    st.markdown(
        """
        <div style="
            background:linear-gradient(135deg,#0f172a,#1d4ed8);
            padding:25px;
            border-radius:20px;
            color:white;
            margin-bottom:20px;
        ">
            <h1 style="margin:0;">
                🛡️ Centro de Control Legionella
            </h1>
            <p style="margin-top:8px;">
                Colegio Abat Oliba Loreto
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.success(
        "🟢 Instalación controlada"
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        tarjeta_kpi("Puntos", "42", "💧")

    with c2:
        tarjeta_kpi("Controles", "1248", "📋")

    with c3:
        tarjeta_kpi("OT Legionella", "37", "🛠️")

    with c4:
        tarjeta_kpi("Incidencias", "2", "⚠️")

    with c5:
        tarjeta_kpi("Próximos", "8", "📅")

    with c6:
        tarjeta_kpi("Cumplimiento", "98,7%", "🏆")

    st.markdown("<br>", unsafe_allow_html=True)

    st.info(
        "🚧 Fase 1 completada. Próximo paso: tarjetas ACS, AFCH, Duchas, VTM, Solar y Retornos."
    )
