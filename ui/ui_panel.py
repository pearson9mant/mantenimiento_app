import streamlit as st
import pandas as pd

from modules.ordenes import obtener_ordenes, obtener_historico
from database.db import conectar


def leer_df_seguro(sql):
    try:
        conn = conectar()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# =====================================================
# KPIs SEGUROS - NO TOCAN LO QUE YA FUNCIONA
# =====================================================

def valor_ot(o, indice, clave="", defecto=""):
    try:
        if isinstance(o, dict):
            return o.get(clave, defecto)
        if len(o) > indice:
            return o[indice]
        return defecto
    except Exception:
        return defecto


def normalizar_estado(estado):
    estado = str(estado or "").strip().lower()

    if estado in ["finalizada", "finalizado", "cerrada", "cerrado"]:
        return "Hechas"

    if estado in ["en curso", "en proceso"]:
        return "En proceso"

    if estado in ["abierta", "pendiente", "pendiente material", "esperando material"]:
        return "Faltan"

    return "Faltan"


def calcular_kpis_panel(ordenes, historico):
    total_activas = len(ordenes)
    total_finalizadas = len(historico)
    total = total_activas + total_finalizadas

    hechas = total_finalizadas

    en_proceso = len([
        o for o in ordenes
        if normalizar_estado(valor_ot(o, 3, "estado")) == "En proceso"
    ])

    faltan = len([
        o for o in ordenes
        if normalizar_estado(valor_ot(o, 3, "estado")) == "Faltan"
    ])

    rendimiento = round((hechas / total) * 100, 1) if total else 0

    return {
        "total": total,
        "hechas": hechas,
        "en_proceso": en_proceso,
        "faltan": faltan,
        "rendimiento": rendimiento,
    }


def pantalla_panel():
    st.subheader("📊 Panel general")

    ordenes = obtener_ordenes()
    historico = obtener_historico()

    # -------------------------------
    # KPIs GENERALES NUEVOS
    # -------------------------------
    kpis = calcular_kpis_panel(ordenes, historico)

    st.markdown("### 📈 KPIs generales")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total OT", kpis["total"])
    k2.metric("✅ Hechas", kpis["hechas"])
    k3.metric("🔄 En proceso", kpis["en_proceso"])
    k4.metric("⏳ Faltan", kpis["faltan"])
    k5.metric("📈 Rendimiento", f'{kpis["rendimiento"]}%')

    st.markdown("---")

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

    # -------------------------------
    # ÚLTIMAS OTs DE PROFESORES / APP
    # -------------------------------
    st.markdown("### 📩 Últimas OTs creadas desde profesores/app")

    ultimas_profes = [
        o for o in ordenes
        if len(o) > 11 and (o[11] or "").strip().upper() in ["OUTLOOK", "APP"]
    ]

    ultimas_profes = ultimas_profes[:5]

    if not ultimas_profes:
        st.info("No hay OTs recientes de profesores/app.")
    else:
        for o in ultimas_profes:
            try:
                numero_ot = o[1]
                descripcion = o[2]
                estado = o[3]
                fecha = o[4]
                centro = o[5]
                edificio = o[6]
                espacio = o[7]
                area = o[8]
                prioridad = o[9]
                operario = o[10]
                origen = o[11] if len(o) > 11 else ""

                icono_estado = {
                    "Abierta": "🔴",
                    "En curso": "🟡",
                    "Pendiente material": "📦",
                    "Finalizada": "✅"
                }.get(estado, "⚪")

                st.markdown(
                    f"**{icono_estado} {numero_ot}** · {prioridad or '-'} · {estado}  \n"
                    f"{descripcion}  \n"
                    f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}  \n"
                    f"👷 {operario or '-'} · Origen: {origen or '-'} · {fecha or '-'}"
                )
                st.markdown("---")
            except Exception:
                pass

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

    st.markdown("### 📩 Incidencias profesores / app")
    st.metric("OT profesores/app", ot_profesores)

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
