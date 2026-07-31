import re
from collections import defaultdict

from modules.ordenes import obtener_ordenes_operario


ESTADOS_EJECUTABLES = {
    "Abierta",
    "En curso",
    "Avisado",
}


COLUMNAS_ORDEN_OPERARIO = [
    "id",
    "numero_ot",
    "descripcion",
    "estado",
    "fecha_creacion",
    "centro",
    "edificio",
    "espacio",
    "area",
    "prioridad",
    "operario",
    "origen",
    "solicitante",
    "fecha_origen",
    "foto",
    "tipo_solicitante",
    "tipo_orden",
    "empresa_externa",
    "contacto_empresa",
    "telefono_empresa",
    "email_empresa",
    "fecha_programada",
    "fecha_realizacion",
    "coste_estimado",
    "coste_final",
    "observaciones_estado",
]


def _convertir_ot_diccionario(ot):
    if isinstance(ot, dict):
        return ot

    if isinstance(ot, (tuple, list)):
        return dict(zip(COLUMNAS_ORDEN_OPERARIO, ot))

    return {}


def _obtener_planta(ot):
    planta = str(ot.get("planta") or "").strip()

    if planta:
        return planta

    espacio = str(ot.get("espacio") or "").strip()

    patrones = [
        r"\bplanta\s*(-?\d+)\b",
        r"\bp\s*(-?\d+)\b",
        r"\bterrado\b",
    ]

    for patron in patrones:
        coincidencia = re.search(patron, espacio, flags=re.IGNORECASE)

        if not coincidencia:
            continue

        if "terrado" in coincidencia.group(0).lower():
            return "Terrado"

        return f"P{coincidencia.group(1)}"

    return "Sin planta"


def _orden_planta(nombre):
    texto = str(nombre or "").strip().lower()

    if texto == "terrado":
        return 100

    coincidencia = re.search(r"-?\d+", texto)

    if coincidencia:
        return int(coincidencia.group())

    return -100


def color_planta(total, urgentes, altas):
    if urgentes > 0:
        return "🔴"

    if altas > 0:
        return "🟠"

    if total > 0:
        return "🟡"

    return "🟢"


def obtener_colegio_vivo(operario):
    filas = obtener_ordenes_operario(operario)

    colegio = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(list)
        )
    )

    for fila in filas:
        ot = _convertir_ot_diccionario(fila)

        if not ot:
            continue

        estado = str(ot.get("estado") or "").strip()

        if estado not in ESTADOS_EJECUTABLES:
            continue

        centro = str(ot.get("centro") or "Centro").strip()
        edificio = str(ot.get("edificio") or "General").strip()
        planta = _obtener_planta(ot)

        colegio[centro][edificio][planta].append(ot)

    resultado = []

    for centro, edificios in colegio.items():
        bloque_centro = {
            "centro": centro,
            "edificios": [],
        }

        for edificio, plantas in edificios.items():
            bloque_edificio = {
                "nombre": edificio,
                "plantas": [],
            }

            plantas_ordenadas = sorted(
                plantas.items(),
                key=lambda item: _orden_planta(item[0]),
                reverse=True,
            )

            for planta, ordenes in plantas_ordenadas:
                urgentes = sum(
                    1
                    for ot in ordenes
                    if str(ot.get("prioridad") or "").strip().lower()
                    == "urgente"
                )

                altas = sum(
                    1
                    for ot in ordenes
                    if str(ot.get("prioridad") or "").strip().lower()
                    == "alta"
                )

                bloque_edificio["plantas"].append(
                    {
                        "nombre": planta,
                        "total": len(ordenes),
                        "urgentes": urgentes,
                        "altas": altas,
                        "color": color_planta(
                            len(ordenes),
                            urgentes,
                            altas,
                        ),
                        "ordenes": ordenes,
                    }
                )

            bloque_centro["edificios"].append(bloque_edificio)

        resultado.append(bloque_centro)

    return resultado
