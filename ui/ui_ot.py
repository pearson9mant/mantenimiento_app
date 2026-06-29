import streamlit as st
from pathlib import Path

from modules.ordenes import (
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    obtener_fotos_ot,
    crear_correctiva_desde_ot,
)

from modules.inventario import (
    obtener_material_por_codigo,
    registrar_movimiento_inventario,
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
    crear_checklist_preventivo,
)

from ui.ui_legionella import (
    obtener_checklist_correctivo_legionella,
    guardar_checklist_correctivo_legionella,
    borrar_checklist_correctivo_legionella,
)


def mostrar_tarjeta_ot(
    fila,
    materiales_select,
    operario_sel,
    modo="operario"
):
    pass
