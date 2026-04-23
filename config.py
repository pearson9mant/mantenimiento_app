from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "data" / "mantenimiento.db"

CLAVE_ADMIN = "1234"

CENTROS = ["Pearson 22", "Pearson 9"]

EDIFICIOS = {
    "Pearson 22": ["Edif. Infantil/Primaria", "Edif. Llar (Anexo)"],
    "Pearson 9": ["Edif. A", "Edif. B", "Edif. C"]
}

OPERARIOS = [
    "J.A. Almeda",
    "Luis Lozano",
    "Abel Vasquez",
    "Otro"
]

AREAS = [
    "Electricidad",
    "Iluminación",
    "Fontanería",
    "Climatización",
    "Legionella",
    "Mantenimiento general",
    "Albañilería",
    "Pintura",
    "Cerrajería",
    "Limpieza",
    "Jardinería",
    "Seguridad",
    "Otros"
]

ESTADOS = [
    "Abierta",
    "En curso",
    "Pendiente material",
    "Finalizada"
]

PRIORIDADES = [
    "Baja",
    "Media",
    "Alta"
]

CATEGORIAS_INVENTARIO = [
    "Electricidad",
    "Fontanería",
    "Climatización",
    "Legionella",
    "Albañilería",
    "Pintura",
    "Cerrajería",
    "Limpieza",
    "Ferretería",
    "Jardinería",
    "Seguridad",
    "Otros"
]

UNIDADES_INVENTARIO = [
    "ud",
    "caja",
    "metro",
    "rollo",
    "litro",
    "kg",
    "juego",
    "botella",
    "pack"
]

TIPOS_MOVIMIENTO = [
    "Entrada",
    "Salida",
    "Ajuste"
]

ESPACIOS = {

    "Edif. Llar (Anexo)": [
        "General",
        "I1A", "I1B", "I1C",
        "I2A", "I2B", "I2C",
        "Sala polivalente",
        "Vestuario chicas",
        "Vestuario chicos",
        "Pasillos",
        "Aseos",
        "Comunes",
        "Otro"
    ],

    "Edif. Infantil/Primaria": [
        "General",
        "I3A", "I3B", "I3C",
        "I4A", "I4B", "I4C",
        "I5A", "I5B", "I5C",
        "1A", "1B", "1C",
        "2A", "2B", "2C",
        "3A", "3B", "3C",
        "4A", "4B", "4C",
        "5A", "5B", "5C",
        "6A", "6B", "6C",
        "Teatro",
        "Patio fútbol",
        "Patio cuadrado",
        "Patio patines",
        "Recepción",
        "Secretaría",
        "Dirección",
        "Pasillos",
        "Aseos",
        "Comunes",
        "Otro"
    ],

    "Edif. A": [
        "General",
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillos",
        "Aseos",
        "Despachos",
        "Sala profesores",
        "Escaleras",
        "Comunes",
        "Otro"
    ],

    "Edif. B": [
        "General",
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillos",
        "Aseos",
        "Despachos",
        "Sala profesores",
        "Escaleras",
        "Comunes",
        "Otro"
    ],

    "Edif. C": [
        "General",
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",
        "Pasillos",
        "Aseos",
        "Despachos",
        "Sala profesores",
        "Escaleras",
        "Comunes",
        "Otro"
    ]
}

ASIGNACION_OPERARIO_POR_CENTRO = {
    "Pearson 9": "Luis Lozano",
    "Pearson 22": "J.A. Almeda"
}

OPERARIOS_CON_ALTA_MATERIAL = ["Abel Vasquez"]