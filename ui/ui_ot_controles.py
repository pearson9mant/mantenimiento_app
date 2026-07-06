import streamlit as st
from datetime import date

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
    crear_checklist_preventivo,
)

from ui.ui_legionella import (
    registrar_control,
    leer_df,
    obtener_checklist_correctivo_legionella,
    guardar_checklist_correctivo_legionella,
    borrar_checklist_correctivo_legionella,
)
def extraer_datos_ot_legionella(descripcion, espacio):
    texto = str(descripcion or "").strip()
    partes = [p.strip() for p in texto.split(" - ")]

    tarea = ""
    punto = str(espacio or "").strip()

    if texto.upper().startswith("CORRECTIVO LEGIONELLA"):
        if len(partes) >= 2:
            tarea = partes[1].strip()
        if len(partes) >= 4:
            punto = partes[-1].strip()
        return tarea, punto

    if len(partes) >= 3:
        tarea = partes[1].strip()
        punto = partes[2].strip()
    elif len(partes) == 2:
        tarea = partes[1].strip()

    return tarea, punto
