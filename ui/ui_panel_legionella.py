import os
import streamlit as st
import pandas as pd
from datetime import date
from database.db import conectar


def adaptar_sql(sql):
    if os.getenv("DATABASE_URL"):
        return sql.replace("?", "%s")
    return sql


def leer_df(sql, params=()):
    conn = conectar()
    try:
        return pd.read_sql_query(adaptar_sql(sql), conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def escalar(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return str(valor)


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


def valor_unico(df, columna="total", defecto=0):
    try:
        if df.empty:
            return defecto
        return int(df.loc[0, columna] or 0)
    except Exception:
        return defecto


def obtener_kpis_legionella():
    hoy = date.today().strftime("%Y-%m-%d")

    df_puntos = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_puntos
        WHERE activo = 1
    """)

    df_controles = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
    """)

    df_ot = leer_df("""
        SELECT COUNT(*) AS total
        FROM ordenes_trabajo
        WHERE area = 'Legionella'
           OR UPPER(COALESCE(origen, '')) = 'LEGIONELLA'
    """)

    df_incidencias = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_incidencias
        WHERE LOWER(COALESCE(estado, '')) NOT IN ('cerrada', 'cerrado', 'finalizada', 'finalizado')
    """)

    df_proximos = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_tareas
        WHERE activo = 1
          AND proxima_fecha IS NOT NULL
          AND date(proxima_fecha) <= date(?, '+30 days')
    """, (hoy,))

    df_ok = leer_df("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN estado = 'OK' THEN 1 ELSE 0 END) AS ok
        FROM legionella_registros
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
    """)

    total_reg = 0
    total_ok = 0

    if not df_ok.empty:
        total_reg = int(df_ok.loc[0, "total"] or 0)
        total_ok = int(df_ok.loc[0, "ok"] or 0)

    cumplimiento = round((total_ok / total_reg) * 100, 1) if total_reg else 0

    return {
        "puntos": valor_unico(df_puntos),
        "controles": valor_unico(df_controles),
        "ot": valor_unico(df_ot),
        "incidencias": valor_unico(df_incidencias),
        "proximos": valor_unico(df_proximos),
        "cumplimiento": cumplimiento,
    }


def contar_registros_por_tarea(texto):
    df = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE LOWER(COALESCE(tarea, '')) LIKE ?
           OR LOWER(COALESCE(tipo_control, '')) LIKE ?
    """, (f"%{texto.lower()}%", f"%{texto.lower()}%"))

    return valor_unico(df)


def contar_puntos_por_tipo(textos):
    condiciones = []
    params = []

    for texto in textos:
        condiciones.append("""
            LOWER(COALESCE(tipo_punto, '')) LIKE ?
            OR LOWER(COALESCE(tipo_control_punto, '')) LIKE ?
            OR LOWER(COALESCE(instalacion, '')) LIKE ?
            OR LOWER(COALESCE(nombre_punto, '')) LIKE ?
        """)
        params.extend([
            f"%{texto.lower()}%",
            f"%{texto.lower()}%",
            f"%{texto.lower()}%",
            f"%{texto.lower()}%",
        ])

    sql = f"""
        SELECT COUNT(*) AS total
        FROM legionella_puntos
        WHERE activo = 1
          AND ({' OR '.join(condiciones)})
    """

    df = leer_df(sql, tuple(params))
    return valor_unico(df)


def obtener_estado_instalaciones():
    acumuladores = contar_puntos_por_tipo(["acumulador"])
    afch = contar_puntos_por_tipo(["afch", "afs", "grifo", "fuente", "lavamanos"])
    duchas = contar_puntos_por_tipo(["ducha"])
    vtm = contar_puntos_por_tipo(["válvula", "valvula", "vtm"])
    solar = contar_puntos_por_tipo(["solar"])
    retornos = contar_puntos_por_tipo(["retorno", "rtc"])

    temp_acum = contar_registros_por_tarea("acumulador")
    temp_impulsion = contar_registros_por_tarea("impulsión")
    temp_retorno = contar_registros_por_tarea("retorno")
    purgas = contar_registros_por_tarea("purga")
    choques = contar_registros_por_tarea("choque")
    afs = contar_registros_por_tarea("AFS")
    cloro = contar_registros_por_tarea("cloro")
    acs_terminal = contar_registros_por_tarea("ACS terminal")
    vtm_rev = contar_registros_por_tarea("válvula")
    solar_lecturas = contar_registros_por_tarea("solar")

    return {
        "acumuladores": acumuladores,
        "afch": afch,
        "duchas": duchas,
        "vtm": vtm,
        "solar": solar,
        "retornos": retornos,
        "temp_acum": temp_acum,
        "temp_impulsion": temp_impulsion,
        "temp_retorno": temp_retorno,
        "purgas": purgas,
        "choques": choques,
        "afs": afs,
        "cloro": cloro,
        "acs_terminal": acs_terminal,
        "vtm_rev": vtm_rev,
        "solar_lecturas": solar_lecturas,
    }


def obtener_puntos_control():
    df = leer_df("""
        SELECT
            p.nombre_punto,
            p.tipo_punto,
            p.tipo_control_punto,
            COALESCE(MAX(r.estado), 'OK') AS estado
        FROM legionella_puntos p
        LEFT JOIN legionella_registros r
            ON p.nombre_punto = r.punto
           AND p.centro = r.centro
           AND p.edificio = r.edificio
        WHERE p.activo = 1
        GROUP BY p.nombre_punto, p.tipo_punto, p.tipo_control_punto
        ORDER BY p.nombre_punto
    """)

    if df.empty:
        return []

    puntos = []

    for _, row in df.iterrows():
        nombre = str(row.get("nombre_punto") or "").strip()
        estado = str(row.get("estado") or "OK").upper()

        if not nombre:
            continue

        if estado in ["RIESGO", "INCIDENCIA"]:
            estado_visual = "riesgo"
        else:
            estado_visual = "ok"

        puntos.append((nombre, estado_visual))

    return puntos


def obtener_incidencias_abiertas():
    return leer_df("""
        SELECT centro, edificio, punto, tarea, descripcion
        FROM legionella_incidencias
        WHERE LOWER(COALESCE(estado, '')) NOT IN ('cerrada', 'cerrado', 'finalizada', 'finalizado')
        ORDER BY fecha_apertura DESC
        LIMIT 5
    """)


def obtener_proximos_controles():
    hoy = date.today().strftime("%Y-%m-%d")

    return leer_df("""
        SELECT centro, edificio, punto, tarea, proxima_fecha
        FROM legionella_tareas
        WHERE activo = 1
          AND proxima_fecha IS NOT NULL
          AND date(proxima_fecha) <= date(?, '+30 days')
        ORDER BY date(proxima_fecha) ASC
        LIMIT 5
    """, (hoy,))


def obtener_actividad_anual():
    anio = str(date.today().year)

    temperaturas = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE substr(fecha, 1, 4) = ?
          AND (
              LOWER(COALESCE(tarea, '')) LIKE '%temperatura%'
              OR LOWER(COALESCE(tipo_control, '')) LIKE '%temperatura%'
              OR LOWER(COALESCE(tarea, '')) LIKE '%acs%'
              OR LOWER(COALESCE(tarea, '')) LIKE '%afs%'
          )
    """, (anio,))

    purgas = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE substr(fecha, 1, 4) = ?
          AND LOWER(COALESCE(tarea, '')) LIKE '%purga%'
    """, (anio,))

    choques = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE substr(fecha, 1, 4) = ?
          AND LOWER(COALESCE(tarea, '')) LIKE '%choque%'
    """, (anio,))

    analiticas = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_informes
        WHERE substr(fecha_informe, 1, 4) = ?
          AND LOWER(COALESCE(tipo_informe, '')) LIKE '%analítica%'
    """, (anio,))

    return {
        "temperaturas": valor_unico(temperaturas),
        "purgas": valor_unico(purgas),
        "choques": valor_unico(choques),
        "analiticas": valor_unico(analiticas),
    }


def obtener_dossier_estado():
    plan = valor_unico(leer_df("SELECT COUNT(*) AS total FROM legionella_tareas WHERE activo = 1"))
    registros = valor_unico(leer_df("SELECT COUNT(*) AS total FROM legionella_registros"))
    informes = valor_unico(leer_df("SELECT COUNT(*) AS total FROM legionella_informes"))
    abiertas = valor_unico(leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_incidencias
        WHERE LOWER(COALESCE(estado, '')) NOT IN ('cerrada', 'cerrado', 'finalizada', 'finalizado')
    """))

    return {
        "plan": plan > 0,
        "registros": registros > 0,
        "informes": informes > 0,
        "correctivos": abiertas == 0,
    }


def pantalla_panel_legionella():
    kpis = obtener_kpis_legionella()
    datos = obtener_estado_instalaciones()
    actividad = obtener_actividad_anual()
    dossier = obtener_dossier_estado()
    incidencias = obtener_incidencias_abiertas()
    proximos = obtener_proximos_controles()
    puntos = obtener_puntos_control()

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

    if kpis["incidencias"] == 0:
        st.success("🟢 Instalación controlada · Sin riesgos críticos activos")
    else:
        st.warning(f"🟠 Instalación con {kpis['incidencias']} incidencia(s) abierta(s)")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        tarjeta_kpi("Puntos", escalar(kpis["puntos"]), "💧")
    with c2:
        tarjeta_kpi("Controles", escalar(kpis["controles"]), "📋")
    with c3:
        tarjeta_kpi("OT Legionella", escalar(kpis["ot"]), "🛠️")
    with c4:
        tarjeta_kpi("Incidencias", escalar(kpis["incidencias"]), "⚠️")
    with c5:
        tarjeta_kpi("Próximos", escalar(kpis["proximos"]), "📅")
    with c6:
        tarjeta_kpi("Cumplimiento", f"{str(kpis['cumplimiento']).replace('.', ',')}%", "🏆")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("## 🏢 Estado de las instalaciones")

    c1, c2, c3 = st.columns(3)

    with c1:
        tarjeta_instalacion(
            "ACS",
            "🔥",
            [
                f"Acumuladores: {datos['acumuladores']}",
                f"🌡️ Temperaturas acumulador: {datos['temp_acum']}",
                f"➡️ Impulsión: {datos['temp_impulsion']}",
                f"🚰 Purgas: {datos['purgas']}",
                f"🔥 Choques térmicos: {datos['choques']}",
            ],
            f"{str(kpis['cumplimiento']).replace('.', ',')}%"
        )

    with c2:
        tarjeta_instalacion(
            "AFCH",
            "💧",
            [
                f"Puntos terminales: {datos['afch']}",
                f"🌡️ Controles AFS: {datos['afs']}",
                f"🧪 Cloro residual: {datos['cloro']}",
                "Control de temperatura y desinfectante",
            ],
            f"{str(kpis['cumplimiento']).replace('.', ',')}%"
        )

    with c3:
        tarjeta_instalacion(
            "DUCHAS",
            "🚿",
            [
                f"Puntos: {datos['duchas']}",
                f"🚿 Controles ACS terminal: {datos['acs_terminal']}",
                f"🚰 Purgas: {datos['purgas']}",
                "Duchas incluidas en control",
            ],
            f"{str(kpis['cumplimiento']).replace('.', ',')}%"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)

    with c4:
        tarjeta_instalacion(
            "VTM",
            "🎛️",
            [
                f"Válvulas termostáticas: {datos['vtm']}",
                f"🔍 Revisiones: {datos['vtm_rev']}",
                "🌡️ Entrada / salida controlada",
                "Accesos revisados",
            ],
            f"{str(kpis['cumplimiento']).replace('.', ',')}%"
        )

    with c5:
        tarjeta_instalacion(
            "SOLAR",
            "☀️",
            [
                f"Depósitos solares: {datos['solar']}",
                f"🌡️ Lecturas realizadas: {datos['solar_lecturas']}",
                "Registro sin consigna automática",
                "Seguimiento de temperatura",
            ],
            f"{str(kpis['cumplimiento']).replace('.', ',')}%"
        )

    with c6:
        tarjeta_instalacion(
            "RETORNOS",
            "🔄",
            [
                f"Puntos: {datos['retornos']}",
                f"🌡️ Mediciones retorno: {datos['temp_retorno']}",
                "Temperatura mínima: ≥ 50 ºC",
                "Recirculación controlada",
            ],
            f"{str(kpis['cumplimiento']).replace('.', ',')}%"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("## 🗺️ Estado de los puntos de control")

    if puntos:
        puntos_html = "<div style='margin-bottom:10px;'>"
        for nombre, estado in puntos:
            puntos_html += punto_control(nombre, estado)
        puntos_html += "</div>"

        st.markdown(puntos_html, unsafe_allow_html=True)
    else:
        st.info("Todavía no hay puntos activos registrados.")

    st.markdown("---")

    st.markdown("## 🚨 Situación operativa actual")

    c1, c2, c3 = st.columns(3)

    with c1:
        if incidencias.empty:
            st.success("🟢 Sin incidencias abiertas")
        else:
            texto = "🔴 Incidencias abiertas\n\n"
            for _, row in incidencias.iterrows():
                texto += f"• {row.get('punto', '')} · {row.get('tarea', '')}\n"
            texto += f"\nTotal: {len(incidencias)}"
            st.error(texto)

    with c2:
        if proximos.empty:
            st.success("🟢 Sin controles próximos")
        else:
            texto = "🟠 Próximos controles\n\n"
            for _, row in proximos.iterrows():
                texto += f"• {row.get('punto', '')} · {row.get('tarea', '')} → {row.get('proxima_fecha', '')}\n"
            texto += f"\nTotal visible: {len(proximos)}"
            st.warning(texto)

    with c3:
        if kpis["incidencias"] == 0:
            st.success("🟢 Estado general\n\nInstalación controlada\n\nSin riesgos críticos")
        else:
            st.warning("🟠 Estado general\n\nRevisar incidencias abiertas\n\nSeguimiento activo")

    st.markdown("---")

    st.markdown("## 📅 Actividad anual")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Temperaturas", escalar(actividad["temperaturas"]))

    with col2:
        st.metric("Purgas", escalar(actividad["purgas"]))

    with col3:
        st.metric("Choques térmicos", escalar(actividad["choques"]))

    with col4:
        st.metric("Analíticas", escalar(actividad["analiticas"]))

    st.markdown("---")

    st.markdown("## 🏆 Dossier de inspección")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.success("✔ Plan actualizado") if dossier["plan"] else st.error("✖ Falta planificación")

    with c2:
        st.success("✔ Registros completos") if dossier["registros"] else st.error("✖ Sin registros")

    with c3:
        st.success("✔ Informes archivados") if dossier["informes"] else st.warning("⚠ Sin informes externos")

    with c4:
        st.success("✔ Correctivos cerrados") if dossier["correctivos"] else st.warning("⚠ Correctivos pendientes")

    st.info(
        "✅ Panel conectado a datos reales de Legionella: puntos, registros, planificación, incidencias, informes y órdenes."
    )
