from collections import defaultdict

from modules.ordenes import obtener_ordenes_operario


ESTADOS_EJECUTABLES = {
    "Abierta",
    "En curso",
    "Avisado",
}


def color_planta(total, urgentes):

    if urgentes > 0:
        return "🔴"

    if total > 0:
        return "🟠"

    return "🟢"


def obtener_colegio_vivo(operario):

    ordenes = obtener_ordenes_operario(operario)

    colegio = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(list)
        )
    )

    for ot in ordenes:

        estado = str(ot.get("estado", "")).strip()

        if estado not in ESTADOS_EJECUTABLES:
            continue

        centro = ot.get("centro") or "Centro"

        edificio = ot.get("edificio") or "General"

        planta = ot.get("planta") or "Sin planta"

        colegio[centro][edificio][planta].append(ot)

    resultado = []

    for centro, edificios in colegio.items():

        bloque = {
            "centro": centro,
            "edificios": []
        }

        for edificio, plantas in edificios.items():

            datos_edificio = {
                "nombre": edificio,
                "plantas": []
            }

            for planta, ots in sorted(plantas.items(), reverse=True):

                urgentes = sum(
                    1
                    for ot in ots
                    if str(ot.get("prioridad", "")).lower() == "urgente"
                )

                datos_edificio["plantas"].append(
                    {
                        "nombre": planta,
                        "total": len(ots),
                        "urgentes": urgentes,
                        "color": color_planta(
                            len(ots),
                            urgentes,
                        ),
                        "ordenes": ots,
                    }
                )

            bloque["edificios"].append(datos_edificio)

        resultado.append(bloque)

    return resultado
