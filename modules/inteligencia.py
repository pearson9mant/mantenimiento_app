from modules.ficha_espacio import (
    obtener_actuaciones_espacio,
    obtener_inventario_espacio,
    obtener_preventivos_espacio,
)


def diagnosticar_espacio(centro, edificio, espacio):
    trabajos = obtener_actuaciones_espacio(centro, edificio, espacio)
    inventario = obtener_inventario_espacio(centro, edificio, espacio)
    preventivos = obtener_preventivos_espacio(centro, edificio, espacio)

    total_trabajos = len(trabajos)
    total_activos = len(inventario)
    total_preventivos = len(preventivos)

    activos_danados = 0
    correctivos = 0

    diagnostico = []
    recomendacion = ""

    primera_ot = ""
    primera_desc = ""

    if trabajos:
        try:
            primera_ot = str(trabajos[0][1] or "")
            primera_desc = str(trabajos[0][2] or "")
        except Exception:
            pass

        diagnostico.append(f"Existe {total_trabajos} trabajo pendiente en este espacio.")

    if total_activos == 0:
        diagnostico.append("El espacio todavía no tiene inventario registrado.")

    for item in inventario:
        try:
            elemento = str(item[2] or "Elemento")
            estado = str(item[4] or "")
            ot_correctiva = str(item[12] or "")
        except Exception:
            continue

        if estado in ["Dañado", "Falta", "Retirar"]:
            activos_danados += 1
            diagnostico.append(f"{elemento} está en estado {estado}.")

        if ot_correctiva:
            correctivos += 1
            diagnostico.append(f"Hay un correctivo pendiente asociado a la OT {ot_correctiva}.")

    if total_preventivos == 0:
        diagnostico.append("No existen preventivos asociados a este espacio.")

    if total_trabajos > 0:
        estado = "Requiere intervención"
        color = "rojo"
        recomendacion = (
            f"Abrir la OT {primera_ot}."
            if primera_ot
            else "Abrir Trabajos del espacio y revisar la OT pendiente."
        )

    elif activos_danados > 0 or correctivos > 0:
        estado = "Requiere intervención"
        color = "rojo"
        recomendacion = "Revisar los activos dañados y finalizar los correctivos pendientes."

    else:
        estado = "Excelente"
        color = "verde"
        recomendacion = "No es necesaria ninguna actuación inmediata."
        diagnostico = [
            "Sin trabajos pendientes.",
            "Sin activos dañados.",
            "Sin correctivos pendientes.",
        ]

    return {
        "estado": estado,
        "color": color,
        "diagnostico": diagnostico,
        "recomendacion": recomendacion,
        "trabajos": total_trabajos,
        "activos": total_activos,
        "preventivos": total_preventivos,
        "danados": activos_danados,
        "correctivos": correctivos,
        "primera_ot": primera_ot,
        "primera_desc": primera_desc,
    }

def diagnosticar_legionella_espacio(centro, edificio, espacio):
    """
    Diagnóstico inicial Legionella por espacio.
    De momento no rompe nada: si no encuentra datos, devuelve estado neutro.
    Más adelante conectaremos registros reales, puntos y controles.
    """

    return {
        "aplica": False,
        "estado": "No aplica",
        "color": "gris",
        "diagnostico": [],
        "recomendaciones": [],
        "pendientes": 0,
    }
