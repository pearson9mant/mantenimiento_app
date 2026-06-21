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

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("## 🏢 Estado de las instalaciones")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.success("""
    🔥 ACS
    
    Acumuladores: 3
    
    🌡️ Temperaturas: 30
    🚰 Purgas: 12
    🔥 Choques térmicos: 2
    
    Cumplimiento: 98%
    """)
    
    with c2:
        st.success("""
    💧 AFCH
    
    Puntos terminales: 19
    
    🌡️ Temperaturas: 19
    🧪 Cloro residual: 19
    
    Cumplimiento: 99%
    """)
    
    with c3:
        st.success("""
    🚿 DUCHAS
    
    Puntos: 8
    
    🚿 Controles realizados: 48
    
    Cumplimiento: 97%
    """)
    
    c4, c5, c6 = st.columns(3)
    
    with c4:
        st.success("""
    🎛️ VTM
    
    Válvulas: 2
    
    🔍 Revisiones: 12
    
    Cumplimiento: 100%
    """)
    
    with c5:
        st.success("""
    ☀️ SOLAR
    
    Depósitos: 2
    
    🌡️ Lecturas realizadas: 730
    
    Cumplimiento: 100%
    """)
    
    with c6:
        st.success("""
    🔄 RETORNOS
    
    Puntos: 2
    
    🌡️ Mediciones: 365
    
    Cumplimiento: 100%
    """)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("## 🗺️ Estado de los puntos de control")
    
    puntos_html = """
    <div style="
    display:flex;
    flex-wrap:wrap;
    gap:10px;
    margin-bottom:20px;
    ">
    
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">ACS-01 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">ACS-02 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">RTC-01 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">RTC-02 🟢</div>
    
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">PT-01 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">PT-02 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">PT-03 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">PT-04 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">PT-05 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">PT-06 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">PT-07 🟢</div>
    
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">M01 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">M02 🟢</div>
    
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">VTM-01 🟢</div>
    <div style="background:#dcfce7;padding:10px 14px;border-radius:10px;">VTM-02 🟢</div>
    
    </div>
    """
    
    st.markdown(puntos_html, unsafe_allow_html=True)
    
    st.info(
        "🚀 Fase 2 completada. Próximo paso: incidencias, próximos controles y dossier de inspección."
    )
