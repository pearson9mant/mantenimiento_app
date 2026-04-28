import streamlit as st
import pandas as pd

from modules.ordenes import obtener_ordenes, obtener_historico
from modules.outlook import importar_y_crear_ots_automaticamente
from database.db import conectar


def leer_df_seguro(sql):
    try:
        conn = conectar()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def pantalla_panel():
    st.subheader("📊 Panel general")

    ordenes = obtener_ordenes()
    historico = obtener_historico()

    abiertas = len([o for o in ordenes if o[3] == "Abierta"])
    en_curso = len([o for o in ordenes if o[3] == "En curso"])
    pendiente_material = len([o for o in ordenes if o[3] == "Pendiente material"])
    finalizadas = len(historico)

    ot_legionella = len([
        o for o in ordenes
        if len(o) > 11 and (o[11] or "").strip().upper() == "LEGIONELLA"
    ])

    ot_profesores = len([
        o for o in ordenes
        if len(o) > 11 and (o[11] or "").strip().upper() in ["OUTLOOK", "APP"]
    ])

    st.markdown("### Estado de órdenes")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🔴 Abiertas", abiertas)
    c2.metric("🟡 En curso", en_curso)
    c3.metric("📦 Pend. material", pendiente_material)
    c4.metric("✅ Finalizadas", finalizadas)
    c5.metric("💧 Legionella", ot_legionella)

    st.markdown("---")

    st.markdown("### 💧 Estado Legionella")

    df_leg = leer_df_seguro("""
        SELECT estado, centro, edificio, punto, tarea, fecha
        FROM legionella_registros
        ORDER BY fecha DESC
    """)

    df_inc = leer_df_seguro("""
        SELECT estado, centro, edificio, punto, tarea, fecha_apertura
        FROM legionella_incidencias
        ORDER BY fecha_apertura DESC
    """)

    if df_leg.empty:
        st.info("Todavía no hay controles de Legionella registrados.")
    else:
        total_controles = len(df_leg)
        controles_ok = len(df_leg[df_leg["estado"] == "OK"])
        controles_riesgo = len(df_leg[df_leg["estado"] == "RIESGO"])
        controles_incidencia = len(df_leg[df_leg["estado"] == "INCIDENCIA"])

        cumplimiento = round((controles_ok / total_controles) * 100, 1) if total_controles else 0

        l1, l2, l3, l4 = st.columns(4)
        l1.metric("Controles", total_controles)
        l2.metric("Correctos", controles_ok)
        l3.metric("Riesgo", controles_riesgo)
        l4.metric("Cumplimiento", f"{cumplimiento}%")

        if controles_riesgo > 0 or controles_incidencia > 0:
            st.warning("Hay controles de Legionella con riesgo o incidencia. Revisar pestaña Legionella.")
        else:
            st.success("Legionella sin incidencias en los registros actuales.")

    if not df_inc.empty:
        abiertas_leg = len(df_inc[df_inc["estado"] == "Abierta"])
        cerradas_leg = len(df_inc[df_inc["estado"] == "Cerrada"])

        i1, i2 = st.columns(2)
        i1.metric("🚨 Incidencias abiertas", abiertas_leg)
        i2.metric("✅ Incidencias cerradas", cerradas_leg)

    st.markdown("---")

    st.markdown("### 📩 Incidencias profesores / Outlook")

    p1, p2 = st.columns(2)
    p1.metric("OT profesores/app", ot_profesores)

    with p2:
        if st.button("🔄 Importar incidencias y crear OT", use_container_width=True):
            try:
                ok, mensaje = importar_y_crear_ots_automaticamente()

                if ok:
                    st.success(mensaje)
                else:
                    st.error(mensaje)

            except Exception:
                st.warning("Outlook no disponible en este entorno.")

    st.markdown("---")

    st.markdown("### Últimas órdenes activas")

    if not ordenes:
        st.info("No hay órdenes activas.")
    else:
        ultimas = ordenes[:5]

        for o in ultimas:
            try:
                numero_ot = o[1]
                descripcion = o[2]
                estado = o[3]
                centro = o[5]
                edificio = o[6]
                area = o[8]
                operario = o[10]
                origen = o[11] if len(o) > 11 else ""

                st.markdown(
                    f"**{numero_ot}** · {area or '-'} · {estado}  \n"
                    f"{descripcion}  \n"
                    f"🏢 {centro or '-'} · {edificio or '-'} · 👷 {operario or '-'} · Origen: {origen or '-'}"
                )
                st.markdown("---")
            except Exception:
                pass
