CENTROS = ["Pearson 22", "Pearson 9"]

EDIFICIOS_POR_CENTRO = {
    "Pearson 22": [
        "Infantil/Primaria",
        "Llar"
    ],
    "Pearson 9": [
        "Edif. A",
        "Edif. B",
        "Edif. C"
    ]
}

ESPACIOS_POR_EDIFICIO = {
    "Infantil/Primaria": [
        "I3A", "I3B", "I3C",
        "I4A", "I4B", "I4C",
        "I5A", "I5B", "I5C",
        "1A", "1B", "1C",
        "2A", "2B", "2C",
        "3A", "3B", "3C",
        "4A", "4B", "4C",
        "5A", "5B", "5C",
        "6A", "6B", "6C",
        "Secretaría",
        "Sala profesores",
        "Comedor",
        "Pasillo",
        "Patio",
        "WC",
        "Otro"
    ],
    "Llar": [
        "I1A", "I1B", "I1C",
        "I2A", "I2B", "I2C",
        "Sala polivalente",
        "Sala profesores",
        "Pasillo",
        "Patio",
        "WC",
        "Otro"
    ],
    "Edif. A": [
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillo",
        "WC",
        "Otro"
    ],
    "Edif. B": [
        "General",
        "Laboratorio",
        "Aula informática",
        "Pasillo",
        "WC",
        "Otro"
    ],
    "Edif. C": [
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillo",
        "WC",
        "Otro"
    ]
}


def obtener_edificios(centro):
    return EDIFICIOS_POR_CENTRO.get(centro, [])


def obtener_espacios(edificio):
    return ESPACIOS_POR_EDIFICIO.get(edificio, ["Otro"])
