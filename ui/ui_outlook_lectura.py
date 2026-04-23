import streamlit as st
import pandas as pd
from modules.outlook import obtener_incidencias_outlook

def pantalla_outlook_lectura():
    st.subheader("📥 Incidencias Outlook")

    incidencias = obtener_incidencias_outlook()

    st.caption(f"Incidencias registradas: {len(incidencias)}")

    if not incidencias:
        st.info("No hay incidencias importadas todavía.")
        return

    datos = []
    for fila in incidencias:
        id_inc, fecha, asunto, remitente, centro, edificio, espacio, prioridad, solicitante, procesado = fila

        datos.append({
            "FECHA": fecha,
            "INCIDENCIA": asunto,
            "REMITENTE": remitente,
            "CENTRO": centro,
            "EDIFICIO": edificio,
            "ESPACIO": espacio,
            "PRIORIDAD": prioridad,
            "SOLICITANTE": solicitante,
            "PROCESADO": "Sí" if procesado else "No"
        })

    df = pd.DataFrame(datos)
    st.dataframe(df, use_container_width=True)