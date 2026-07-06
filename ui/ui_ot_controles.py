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
