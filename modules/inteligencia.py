from modules.ficha_espacio import (
    obtener_actuaciones_espacio,
    obtener_inventario_espacio,
    obtener_preventivos_espacio,
)
from ui.ui_legionella import obtener_resumen_legionella_espacio


def diagnosticar_legionella_espacio(centro, edificio, espacio):
    """
    El motor inteligente pregunta al módulo de Legionella.
    Toda la lógica permanece dentro del módulo Legionella.
    """

    try:
        return obtener_resumen_legionella_espacio(
            centro,
            edificio,
            espacio
        )
    except Exception:
        return {
            "aplica": False,
            "estado": "No aplica",
            "color": "gris",
            "puntos": 0,
            "tareas": 0,
            "incidencias_abiertas": 0,
            "ultimo_control": "",
            "proximo_control": "",
            "diagnostico": [],
            "recomendaciones": [],
        }


def diagnosticar_espacio(centro, edificio, espacio):
    trabajos = obtener_actuaciones_espacio(centro, edificio, espacio)
    inventario = obtener_inventario_espacio(centro, edificio, espacio)
    preventivos = obtener_preventivos_espacio(centro, edificio, espacio)
    legionella = diagnosticar_legionella_espacio(centro, edificio, espacio)

    total_trabajos = len(trabajos)
    total_activos = len(inventario)
    total_preventivos = len(preventivos)

    activos_danados = 0
    correctivos = 0

    diagnostico = []
    recomendaciones = []

    primera_ot = ""
    primera_desc = ""

    if trabajos:
        try:
            primera_ot = str(trabajos[0][1] or "")
            primera_desc = str(trabajos[0][2] or "")
        except Exception:
            pass

        diagnostico.append(
            f"Existe {total_trabajos} trabajo pendiente en este espacio."
        )

    if total_activos == 0:
        diagnostico.append("El espacio todavía no tiene inventario registrado.")

    for item in inventario:
        try:
            elemento = str(item[2] or "Elemento")
            estado_item = str(item[4] or "")
            ot_correctiva = str(item[12] or "")
        except Exception:
            continue

        if estado_item in ["Dañado", "Falta", "Retirar"]:
            activos_danados += 1
            diagnostico.append(f"{elemento} está en estado {estado_item}.")

        if ot_correctiva:
            correctivos += 1
            diagnostico.append(
                f"Hay un correctivo pendiente asociado a la OT {ot_correctiva}."
            )

    if total_preventivos == 0:
        diagnostico.append("No existen preventivos asociados a este espacio.")

    if legionella.get("aplica"):
        for linea in legionella.get("diagnostico", []):
            diagnostico.append(linea)

        for linea in legionella.get("recomendaciones", []):
            if linea not in recomendaciones:
                recomendaciones.append(linea)

    if total_trabajos > 0:
        estado = "Requiere intervención"
        color = "rojo"

        if primera_ot:
            recomendaciones.append(f"Abrir la OT {primera_ot}.")
        else:
            recomendaciones.append(
                "Abrir Trabajos del espacio y revisar la OT pendiente."
            )

    elif activos_danados > 0 or correctivos > 0:
        estado = "Requiere intervención"
        color = "rojo"
        recomendaciones.append(
            "Revisar los activos dañados y finalizar los correctivos pendientes."
        )

    else:
        estado = "Excelente"
        color = "verde"
        diagnostico = [
            "Sin trabajos pendientes.",
            "Sin activos dañados.",
            "Sin correctivos pendientes.",
        ]
        recomendaciones = [
            "No es necesaria ninguna actuación inmediata."
        ]

    if legionella.get("aplica"):
        if legionella.get("color") == "rojo":
            estado = "Requiere intervención"
            color = "rojo"
        elif legionella.get("color") == "amarillo" and color != "rojo":
            estado = "Requiere revisión"
            color = "amarillo"

    if not recomendaciones:
        recomendaciones.append("No es necesaria ninguna actuación inmediata.")

    return {
        "estado": estado,
        "color": color,
        "diagnostico": diagnostico,
        "recomendacion": recomendaciones[0],
        "recomendaciones": recomendaciones,
        "trabajos": total_trabajos,
        "activos": total_activos,
        "preventivos": total_preventivos,
        "danados": activos_danados,
        "correctivos": correctivos,
        "primera_ot": primera_ot,
        "primera_desc": primera_desc,
        "legionella": legionella,
    }

def _preventivos_pendientes(preventivos):
    pendientes = []

    for p in preventivos:
        try:
            estado = str(p[3] or "").strip().lower()
        except Exception:
            estado = ""

        if estado not in [
            "finalizado", "finalizada",
            "cerrado", "cerrada",
            "completado", "completada",
            "ok",
        ]:
            pendientes.append(p)

    return pendientes


def _legionella_relevante(legionella):
    if not legionella:
        return False

    if not legionella.get("aplica"):
        return False

    if int(legionella.get("incidencias_abiertas") or 0) > 0:
        return True

    color = str(legionella.get("color") or "").lower()
    return color in ["rojo", "amarillo"]


def obtener_actividad_espacio(centro, edificio, planta, espacio):
    trabajos = obtener_actuaciones_espacio(centro, edificio, espacio)
    preventivos = obtener_preventivos_espacio(centro, edificio, espacio)
    preventivos_pend = _preventivos_pendientes(preventivos)

    info = diagnosticar_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio
    )

    legionella = info.get("legionella", {})
    tiene_legionella = _legionella_relevante(legionella)

    tiene_actividad = (
        len(trabajos) > 0
        or len(preventivos_pend) > 0
        or tiene_legionella
    )

    return {
        "centro": centro,
        "edificio": edificio,
        "planta": planta,
        "espacio": espacio,
        "actuaciones": trabajos,
        "preventivos": preventivos,
        "preventivos_pendientes": preventivos_pend,
        "legionella": legionella,
        "tiene_legionella": tiene_legionella,
        "tiene_actividad": tiene_actividad,
    }


def obtener_actividad_edificio(centro, edificio):
    from modules.espacios import obtener_plantas_espacios, obtener_espacios_por_planta

    actividad = []

    for planta in obtener_plantas_espacios(centro, edificio):
        for espacio, tipo in obtener_espacios_por_planta(centro, edificio, planta):
            item = obtener_actividad_espacio(
                centro=centro,
                edificio=edificio,
                planta=planta,
                espacio=espacio
            )

            if item["tiene_actividad"]:
                actividad.append(item)

    return actividad


def edificio_tiene_actividad(centro, edificio):
    return len(obtener_actividad_edificio(centro, edificio)) > 0


def centro_tiene_actividad(centro):
    from modules.espacios import obtener_edificios_espacios

    for edificio in obtener_edificios_espacios(centro):
        if edificio_tiene_actividad(centro, edificio):
            return True

    return False
