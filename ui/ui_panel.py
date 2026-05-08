import streamlit as st
import pandas as pd
import math
import wave
from io import BytesIO

from modules.ordenes import obtener_ordenes, obtener_historico
from modules.preventivo import generar_ots_preventivo_si_toca
from database.db import conectar
from modules.telegram_alertas import enviar_telegram


def leer_df_seguro(sql):
    try:
        conn = conectar()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# =====================================================
# ALERTA SONORA / AUTO REFRESCO
# =====================================================

def activar_auto_refresco_panel(segundos=30):
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(
            interval=segundos * 1000,
            key="auto_refresco_panel_general"
        )
    except Exception:
        st.caption(
            "🔄 Auto-refresco no instalado. Si quieres activarlo: "
            "pip install streamlit-autorefresh"
        )


def crear_sonido_alerta():
    sample_rate = 44100
    duracion = 0.55
    frecuencia = 880
    volumen = 0.45

    buffer = BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for i in range(int(sample_rate * duracion)):
            valor = int(
                32767
                * volumen
                * math.sin(2 * math.pi * frecuencia * i / sample_rate)
            )
            wav.writeframesraw(valor.to_bytes(2, byteorder="little", signed=True))

    buffer.seek(0)
    return buffer.getvalue()


def reproducir_alerta_sonora():
    sonido = crear_sonido_alerta()

    try:
        st.audio(sonido, format="audio/wav", autoplay=True)
    except TypeError:
        st.audio(sonido, format="audio/wav")


def obtener_numero_ot(o):
    return str(valor_ot(o, 1, "numero_ot", "") or "").strip()


def obtener_origen_ot(o):
    return str(valor_ot(o, 11, "origen", "") or "").strip().upper()


def detectar_ordenes_nuevas(ordenes):
    actuales = set()

    for o in ordenes:
        numero_ot = obtener_numero_ot(o)
        if numero_ot:
            actuales.add(numero_ot)

    if "panel_ots_vistas" not in st.session_state:
        st.session_state["panel_ots_vistas"] = actuales
        return []

    anteriores = st.session_state["panel_ots_vistas"]
    nuevas = sorted(list(actuales - anteriores))

    st.session_state["panel_ots_vistas"] = actuales

    return nuevas


def mostrar_alerta_nuevas_ordenes(ordenes):
    nuevas = detectar_ordenes_nuevas(ordenes)

    if not nuevas:
        return

    st.error(f"🔔 Han entrado {len(nuevas)} orden(es) nueva(s): {', '.join(nuevas)}")
    reproducir_alerta_sonora()


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
    activar_auto_refresco_panel(segundos=30)

    st.subheader("📊 Panel general")
    if st.button("📲 Probar Telegram"):
        ok = enviar_telegram("✅ Telegram conectado correctamente a Mantenimiento Loreto")

    if ok:
        st.success("Mensaje enviado")
    else:
        st.error("Error enviando Telegram")

    ordenes = obtener_ordenes()
    historico = obtener_historico()

    mostrar_alerta_nuevas_ordenes(ordenes)

    st.markdown("### 🔧 Preventivos")

    if st.button("🔄 Generar preventivos que tocan", use_container_width=True):
        n = generar_ots_preventivo_si_toca()
        if n > 0:
            st.success(f"Se han generado {n} órdenes preventivas.")
        else:
            st.info("No hay preventivos pendientes para generar.")
        st.rerun()

    st.markdown("---")

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

    abiertas = len([o for o in ordenes if valor_ot(o, 3, "estado") == "Abierta"])
    en_curso = len([o for o in ordenes if valor_ot(o, 3, "estado") == "En curso"])
    pendiente_material = len([o for o in ordenes if valor_ot(o, 3, "estado") == "Pendiente material"])
    finalizadas = len(historico)

    ot_legionella = len([
        o for o in ordenes
        if obtener_origen_ot(o) == "LEGIONELLA"
    ])

    ot_profesores = len([
        o for o in ordenes
        if obtener_origen_ot(o) in ["OUTLOOK", "APP"]
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
        if obtener_origen_ot(o) in ["OUTLOOK", "APP"]
    ]

    ultimas_profes = ultimas_profes[:5]

    if not ultimas_profes:
        st.info("No hay OTs recientes de profesores/app.")
    else:
        for o in ultimas_profes:
            try:
                numero_ot = valor_ot(o, 1, "numero_ot")
                descripcion = valor_ot(o, 2, "descripcion")
                estado = valor_ot(o, 3, "estado")
                fecha = valor_ot(o, 4, "fecha_creacion")
                centro = valor_ot(o, 5, "centro")
                edificio = valor_ot(o, 6, "edificio")
                espacio = valor_ot(o, 7, "espacio")
                area = valor_ot(o, 8, "area")
                prioridad = valor_ot(o, 9, "prioridad")
                operario = valor_ot(o, 10, "operario")
                origen = valor_ot(o, 11, "origen")

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
                numero_ot = valor_ot(o, 1, "numero_ot")
                descripcion = valor_ot(o, 2, "descripcion")
                estado = valor_ot(o, 3, "estado")
                centro = valor_ot(o, 5, "centro")
                edificio = valor_ot(o, 6, "edificio")
                area = valor_ot(o, 8, "area")
                operario = valor_ot(o, 10, "operario")
                origen = valor_ot(o, 11, "origen")

                st.markdown(
                    f"**{numero_ot}** · {area or '-'} · {estado}  \n"
                    f"{descripcion}  \n"
                    f"🏢 {centro or '-'} · {edificio or '-'} · 👷 {operario or '-'} · Origen: {origen or '-'}"
                )
                st.markdown("---")
            except Exception:
                pass
