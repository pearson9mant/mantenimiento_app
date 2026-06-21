import streamlit as st


def tarjeta_kpi(titulo, valor, icono):
    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border-radius:18px;
            padding:16px;
            text-align:center;
            box-shadow:0 3px 10px rgba(0,0,0,0.08);
            border:1px solid #e5e7eb;
            min-height:125px;
        ">
            <div style="font-size:30px;">{icono}</div>
            <div style="font-size:14px;color:#64748b;">{titulo}</div>
            <div style="font-size:30px;font-weight:900;color:#0f172a;">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def tarjeta_instalacion(titulo, icono, lineas, cumplimiento):
    lineas_html = "".join(
        [f"<div style='margin:6px 0;font-size:15px;color:#0f172a;'>{linea}</div>" for linea in lineas]
    )

    st.markdown(
        f"""
        <div style="
            background:#ecfdf5;
            border:1px solid #bbf7d0;
            border-radius:16px;
            padding:14px 16px;
            min-height:145px;
            box-shadow:0 2px 8px rgba(0,0,0,0.04);
        ">
            <div style="font-size:17px;font-weight:900;color:#047857;margin-bottom:8px;">
                {icono} {titulo}
            </div>
            {lineas_html}
            <div style="
                margin-top:10px;
                font-size:16px;
                font-weight:900;
                color:#047857;
            ">
                🟢 Cumplimiento: {cumplimiento}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def punto_control(codigo, estado="ok"):
    if estado == "riesgo":
        fondo = "#fee2e2"
        color = "#991b1b"
        icono = "🔴"
    elif estado == "proximo":
        fondo = "#fef3c7"
        color = "#92400e"
        icono = "🟠"
    else:
        fondo = "#dcfce7"
        color = "#166534"
        icono = "🟢"

    return f"""
    <div style="
        background:{fondo};
        color:{color};
        padding:10px 14px;
        border-radius:12px;
        font-weight:800;
        font-size:14px;
        display:inline-block;
        margin:5px;
        min-width:82px;
        text-align:center;
        border:1px solid rgba(0,0,0,0.05);
    ">
        {codigo} {icono}
    </div>
    """


def pantalla_panel_legionella():

    st.markdown(
        """
        <div style="
            background:linear-gradient(135deg,#0f172a,#1d4ed8);
            padding:25px;
            border-radius:22px;
            color:white;
            margin-bottom:18px;
            box-shadow:0 8px 24px rgba(15,23,42,0.18);
        ">
            <h1 style="margin:0;font-size:38px;">
                🛡️ Centro de Control Legionella
            </h1>
            <p style="margin-top:10px;font-size:16px;font-weight:700;">
                Colegio Abat Oliba Loreto
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.success("🟢 Instalación controlada · Sin riesgos críticos activos")

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

    st.markdown("## 🏢 Estado de las instalaciones")

    c1, c2, c3 = st.columns(3)

    with c1:
        tarjeta_instalacion(
            "ACS",
            "🔥",
            [
                "Acumuladores: 3",
                "🌡️ Temperaturas: 30",
                "🚰 Purgas: 12",
                "🔥 Choques térmicos: 2",
            ],
            "98%"
        )

    with c2:
        tarjeta_instalacion(
            "AFCH",
            "💧",
            [
                "Puntos terminales: 19",
                "🌡️ Temperaturas: 19",
                "🧪 Cloro residual: 19",
                "Último cloro: 0,62 mg/L",
            ],
            "99%"
        )

    with c3:
        tarjeta_instalacion(
            "DUCHAS",
            "🚿",
            [
                "Puntos: 8",
                "🚿 Controles realizados: 48",
                "🚰 Purgas: 24",
                "Uso bajo incluido en control",
            ],
            "97%"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)

    with c4:
        tarjeta_instalacion(
            "VTM",
            "🎛️",
            [
                "Válvulas termostáticas: 2",
                "🔍 Revisiones: 12",
                "🌡️ Entrada / salida controlada",
                "Accesos revisados",
            ],
            "100%"
        )

    with c5:
        tarjeta_instalacion(
            "SOLAR",
            "☀️",
            [
                "Depósitos solares: 2",
                "🌡️ Lecturas realizadas: 730",
                "Registro sin consigna automática",
                "Seguimiento de temperatura",
            ],
            "100%"
        )

    with c6:
        tarjeta_instalacion(
            "RETORNOS",
            "🔄",
            [
                "Puntos: 2",
                "🌡️ Mediciones: 365",
                "Temperatura mínima: ≥ 50 ºC",
                "Recirculación controlada",
            ],
            "100%"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("## 🗺️ Estado de los puntos de control")

    puntos_html = "<div style='margin-bottom:10px;'>"
    puntos_html += punto_control("ACS-01")
    puntos_html += punto_control("ACS-02")
    puntos_html += punto_control("RTC-01")
    puntos_html += punto_control("RTC-02")
    puntos_html += punto_control("PT-01")
    puntos_html += punto_control("PT-02")
    puntos_html += punto_control("PT-03")
    puntos_html += punto_control("PT-04", "riesgo")
    puntos_html += punto_control("PT-05")
    puntos_html += punto_control("PT-06")
    puntos_html += punto_control("PT-07", "proximo")
    puntos_html += punto_control("M01")
    puntos_html += punto_control("M02")
    puntos_html += punto_control("VTM-01")
    puntos_html += punto_control("VTM-02")
    puntos_html += "</div>"

    st.markdown(puntos_html, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("## 🚨 Situación operativa actual")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.error("""
🔴 Incidencias abiertas

• ACS-02 temperatura baja  
• PT-04 cloro fuera de rango  

Total: 2
""")

    with c2:
        st.warning("""
🟠 Próximos controles

• ACS-01 → mañana  
• RTC-01 → mañana  
• PT-07 → 3 días  

Total: 8
""")

    with c3:
        st.success("""
🟢 Estado general

Instalación controlada  

Sin riesgos críticos
""")

    st.markdown("---")

    st.markdown("## 📅 Actividad anual")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Temperaturas", "1.248")

    with col2:
        st.metric("Purgas", "312")

    with col3:
        st.metric("Choques térmicos", "8")

    with col4:
        st.metric("Analíticas", "12")

    st.markdown("---")

    st.markdown("## 🏆 Dossier de inspección")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.success("✔ Plan actualizado")

    with c2:
        st.success("✔ Registros completos")

    with c3:
        st.success("✔ Analíticas archivadas")

    with c4:
        st.success("✔ Correctivos cerrados")

    st.info(
        "🚀 Fase 3 completada. Siguiente paso: conectar estos datos a las tablas reales de Legionella."
    )
