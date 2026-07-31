import re
import unicodedata
from collections import defaultdict

from modules.ordenes import obtener_ordenes_operario


# =========================================================
# ESTADOS QUE EL OPERARIO PUEDE EJECUTAR
# =========================================================

ESTADOS_EJECUTABLES = {
    "abierta",
    "en curso",
    "en ejecucion",
    "avisado",
}


# Deben coincidir exactamente con el SELECT de
# obtener_ordenes_operario().
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


# =========================================================
# NORMALIZACIÓN
# =========================================================

def _normalizar_texto(valor):
    texto = str(valor or "").strip().lower()

    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )

    for caracter in ["/", "\\", "-", "_", ".", ",", ";", ":"]:
        texto = texto.replace(caracter, " ")

    return " ".join(texto.split())


def _convertir_ot_diccionario(ot):
    """
    obtener_ordenes_operario() devuelve tuplas.

    Este módulo las convierte internamente a diccionario sin
    modificar la función original ni afectar otras pantallas.
    """
    if isinstance(ot, dict):
        return dict(ot)

    if isinstance(ot, (tuple, list)):
        return dict(
            zip(
                COLUMNAS_ORDEN_OPERARIO,
                ot,
            )
        )

    return {}


def _normalizar_estado(valor):
    return _normalizar_texto(valor)


def _normalizar_prioridad(valor):
    return _normalizar_texto(valor)


# =========================================================
# CENTROS Y EDIFICIOS
# =========================================================

def _normalizar_centro(valor):
    texto = _normalizar_texto(valor)

    if (
        texto in {
            "pearson 22",
            "pearson22",
            "p22",
            "pearson numero 22",
        }
        or "pearson 22" in texto
    ):
        return "Pearson 22"

    if (
        texto in {
            "pearson 9",
            "pearson9",
            "p9",
            "pearson numero 9",
        }
        or "pearson 9" in texto
    ):
        return "Pearson 9"

    return str(valor or "Centro").strip()


def _normalizar_edificio(valor, centro, ot=None):
    texto = _normalizar_texto(valor)

    if ot:
        texto_apoyo = " ".join(
            [
                texto,
                _normalizar_texto(ot.get("espacio")),
                _normalizar_texto(ot.get("descripcion")),
            ]
        )
    else:
        texto_apoyo = texto

    if any(
        alias in texto_apoyo
        for alias in [
            "llar",
            "llar infants",
            "guarderia",
            "anexo",
            "edificio llar",
            "edif llar",
        ]
    ):
        return "Llar"

    if any(
        alias in texto_apoyo
        for alias in [
            "infantil primaria",
            "infantil",
            "primaria",
            "edificio infantil",
            "edificio primaria",
            "edif infantil",
            "edif primaria",
            "principal",
        ]
    ):
        return "Infantil / Primaria"

    if any(
        alias in texto_apoyo
        for alias in [
            "edificio a",
            "edif a",
            "bloque a",
            "pabellon a",
            "modulo a",
        ]
    ):
        return "Edificio A"

    if any(
        alias in texto_apoyo
        for alias in [
            "edificio b",
            "edif b",
            "bloque b",
            "pabellon b",
            "modulo b",
        ]
    ):
        return "Edificio B"

    if any(
        alias in texto_apoyo
        for alias in [
            "edificio c",
            "edif c",
            "bloque c",
            "pabellon c",
            "modulo c",
        ]
    ):
        return "Edificio C"

    # Compatibilidad con órdenes antiguas.
    if centro == "Pearson 22":
        return "Infantil / Primaria"

    if centro == "Pearson 9":
        return "Edificio A"

    return str(valor or "General").strip()


# =========================================================
# DETECCIÓN DE PLANTA
# =========================================================

def _normalizar_planta(valor):
    texto = _normalizar_texto(valor)

    if not texto:
        return ""

    if any(
        palabra in texto
        for palabra in [
            "terrado",
            "cubierta",
            "azotea",
            "tejado",
        ]
    ):
        return "Terrado"

    equivalencias = {
        "baja": 0,
        "pb": 0,
        "principal": 0,
        "cero": 0,
        "primera": 1,
        "primero": 1,
        "segunda": 2,
        "segundo": 2,
        "tercera": 3,
        "tercero": 3,
        "cuarta": 4,
        "cuarto": 4,
        "quinta": 5,
        "quinto": 5,
    }

    # Casos claros:
    # Planta 4, P4, P 4, Piso 4, Nivel 4.
    patrones = [
        r"\bplanta\s*([0-9])\b",
        r"\bpiso\s*([0-9])\b",
        r"\bnivel\s*([0-9])\b",
        r"\bp\s*([0-9])\b",
        r"\b([0-9])\s*(?:a|ª|o|º)\s*planta\b",
    ]

    for patron in patrones:
        coincidencia = re.search(
            patron,
            texto,
            flags=re.IGNORECASE,
        )

        if coincidencia:
            return f"Planta {int(coincidencia.group(1))}"

    palabras = texto.split()

    for palabra, numero in equivalencias.items():
        if palabra in palabras:
            return f"Planta {numero}"

    return ""


def _obtener_planta(ot):
    """
    Intenta encontrar la planta sin inventarla.

    Orden de confianza:
    1. Campo planta, si existiera en algún resultado futuro.
    2. Campo edificio.
    3. Campo espacio.
    4. Descripción.
    5. Observaciones de estado.
    """

    candidatos = [
        ot.get("planta"),
        ot.get("edificio"),
        ot.get("espacio"),
        ot.get("descripcion"),
        ot.get("observaciones_estado"),
    ]

    for candidato in candidatos:
        planta = _normalizar_planta(candidato)

        if planta:
            return planta

    return "Sin planta"


def _orden_planta(nombre):
    texto = _normalizar_texto(nombre)

    if texto == "terrado":
        return 100

    coincidencia = re.search(r"\d+", texto)

    if coincidencia:
        return int(coincidencia.group())

    return -100


# =========================================================
# ESTADO VISUAL
# =========================================================

def color_planta(total, urgentes, altas):
    if urgentes > 0:
        return "🔴"

    if altas > 0:
        return "🟠"

    if total > 0:
        return "🟡"

    return "🟢"


# =========================================================
# FUNCIÓN PÚBLICA
# =========================================================

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

        estado = _normalizar_estado(
            ot.get("estado")
        )

        if estado not in ESTADOS_EJECUTABLES:
            continue

        centro = _normalizar_centro(
            ot.get("centro")
        )

        edificio = _normalizar_edificio(
            ot.get("edificio"),
            centro,
            ot,
        )

        planta = _obtener_planta(ot)

        # Guardamos también los valores normalizados en la OT.
        # Así la misión y el edificio usan la misma ubicación.
        ot["_centro_normalizado"] = centro
        ot["_edificio_normalizado"] = edificio
        ot["_planta_normalizada"] = planta

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
                    if _normalizar_prioridad(
                        ot.get("prioridad")
                    ) == "urgente"
                )

                altas = sum(
                    1
                    for ot in ordenes
                    if _normalizar_prioridad(
                        ot.get("prioridad")
                    ) == "alta"
                )

                total = len(ordenes)

                bloque_edificio["plantas"].append(
                    {
                        "nombre": planta,
                        "total": total,
                        "urgentes": urgentes,
                        "altas": altas,
                        "color": color_planta(
                            total,
                            urgentes,
                            altas,
                        ),
                        "ordenes": ordenes,
                    }
                )

            bloque_centro["edificios"].append(
                bloque_edificio
            )

        resultado.append(bloque_centro)

    return resultado
