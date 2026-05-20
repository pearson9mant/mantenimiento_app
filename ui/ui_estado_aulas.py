import streamlit as st
import pandas as pd
from datetime import date, datetime

from modules.ubicaciones import CENTROS, obtener_edificios, obtener_espacios
from modules.estado_aulas import (
    obtener_estado_aula,
    guardar_estado_aula,
    obtener_historial_estado_aula,
    obtener_ordenes_abiertas_aula,
    obtener_historico_ordenes_aula,
)
from ui.ui_plan_verano import crear_trabajo_verano


ESTADOS = ["OK", "Bueno", "Regular", "Mal", "Pendiente", "No aplica"]


def calcular_anios_sin_pintar(fecha_txt):
    try:
        if not fecha_txt:
            return ""
        fecha = datetime.strptime(str(fecha_txt), "%Y-%m-%d").date()
        hoy = date.today()
        return round((hoy - fecha).days / 365, 1)
    except Exception:
        return ""


def ui_estado_aulas():
    st.title("🏫 Estado de aulas")
    st.caption("Control visual y técnico del estado de cada aula o espacio.")

    centro = st.selectbox("Centro", CENTROS, key="estado_aulas_centro")

    edificios = obtener_edificios(centro)
    edificio = st.selectbox("Edificio", edificios, key="estado_aulas_edificio")

    espacios = obtener_espacios(edificio, centro)

    if not espacios:
        st.warning("No hay aulas o espacios configurados para este edificio.")
        return

    aula = st.selectbox("Aula / espacio", espacios, key="estado_aulas_aula")

    estado_actual = obtener_estado_aula(centro, edificio, aula)

    st.divider()

    st.subheader(f"Ficha del aula: {aula}")

    if estado_actual:
        fecha_ultima_pintura = estado_actual[6]
        anios = calcular_anios_sin_pintar(fecha_ultima_pintura)

        col1, col2, col3 = st.columns(3)
        col1.metric("Estado general", estado_actual[4] or "Sin dato")
        col2.metric("Pintura", estado_actual[5] or "Sin dato")
        col3.metric("Años sin pintar", anios if anios != "" else "Sin dato")

        st.info(f"Última revisión: {estado_actual[14] or 'Sin dato'} · Revisado por: {estado_actual[15] or 'Sin dato'}")
    else:
        st.warning("Esta aula todavía no tiene ficha registrada.")

    st.divider()

    st.subheader("Registrar nueva revisión")

    with st.form("form_estado_aula"):
        col1, col2 = st.columns(2)

        with col1:
            estado_general = st.selectbox("Estado general", ESTADOS)
            estado_pintura = st.selectbox("Estado pintura", ESTADOS)
            fecha_ultima_pintura = st.date_input("Fecha última pintura", value=date.today())
            estado_electricidad = st.selectbox("Electricidad", ESTADOS)

        with col2:
            estado_iluminacion = st.selectbox("Iluminación", ESTADOS)
            estado_climatizacion = st.selectbox("Climatización", ESTADOS)
            estado_fontaneria = st.selectbox("Fontanería", ESTADOS)
            estado_mobiliario = st.selectbox("Mobiliario", ESTADOS)

        observaciones = st.text_area("Observaciones")
        revisado_por = st.text_input("Revisado por", value=str(st.session_state.get("usuario", "")))

        foto = ""
        archivo_foto = st.file_uploader("Foto del aula", type=["jpg", "jpeg", "png"])

        guardar = st.form_submit_button("💾 Guardar revisión")

        if guardar:
            guardar_estado_aula(
                centro,
                edificio,
                aula,
                estado_general,
                estado_pintura,
                fecha_ultima_pintura,
                estado_electricidad,
                estado_iluminacion,
                estado_climatizacion,
                estado_fontaneria,
                estado_mobiliario,
                observaciones,
                foto,
                revisado_por,
            )

            st.success("Estado del aula guardado correctamente.")
            st.rerun()

    st.divider()

    st.subheader("Órdenes abiertas en esta aula")

    df_abiertas = obtener_ordenes_abiertas_aula(centro, edificio, aula)

    if df_abiertas.empty:
        st.success("No hay órdenes abiertas para esta aula.")
    else:
        st.dataframe(df_abiertas, use_container_width=True, hide_index=True)

    st.subheader("Histórico de actuaciones")
    df_historico = obtener_historico_ordenes_aula(centro, edificio, aula)

    if df_historico.empty:
        st.info("No hay actuaciones finalizadas registradas para esta aula.")
    else:
        st.dataframe(df_historico, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("☀️ Planificación verano")

    col_verano1, col_verano2 = st.columns(2)

    with col_verano1:
        tipo_tarea_verano = st.selectbox(
            "Tipo actuación verano",
            [
                "Pintura",
                "Electricidad",
                "Climatización",
                "Iluminación",
                "Mobiliario",
                "Fontanería",
                "General"
            ],
            key="tipo_tarea_verano_aula"
        )

    with col_verano2:
        prioridad_verano = st.selectbox(
            "Prioridad",
            ["Baja", "Media", "Alta", "Urgente"],
            index=2,
            key="prioridad_verano_aula"
        )

    descripcion_verano = st.text_area(
        "Descripción actuación verano",
        value=f"{tipo_tarea_verano} aula {aula}",
        key="descripcion_verano_aula"
    )

    if st.button(
        "➕ Crear tarea verano",
        use_container_width=True,
        key="crear_tarea_verano_desde_aula"
    ):
        crear_trabajo_verano({
            "titulo": f"{tipo_tarea_verano} · {aula}",
            "descripcion": descripcion_verano,
            "centro": centro,
            "edificio": edificio,
            "zona": aula,
            "responsable": "",
            "empresa_externa": "",
            "fecha_inicio": date.today(),
            "fecha_fin": date.today(),
            "prioridad": prioridad_verano,
            "estado": "Planificado",
            "observaciones": f"Creado automáticamente desde Estado aulas ({aula})",
            "creado_por": st.session_state.get("usuario", "")
        })

        st.success(
            f"✅ Trabajo de verano creado correctamente:\n\n"
            f"{descripcion_verano}"
        )

    st.divider()

    st.subheader("Histórico de revisiones del aula")
    df_revisiones = obtener_historial_estado_aula(centro, edificio, aula)

    if df_revisiones.empty:
        st.info("No hay revisiones anteriores.")
    else:
        st.dataframe(df_revisiones, use_container_width=True, hide_index=True)
