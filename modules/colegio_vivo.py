import re
import unicodedata
from collections import defaultdict

from database.db import conectar, _sql


# =========================================================
# CONFIGURACIÓN
# =========================================================

MAPA_OPERARIO_CENTRO = {
    "J.A. Almeda": "Pearson 22",
    "Luis Lozano": "Pearson 9",
    "Abel Vasquez": None,
}


ESTADOS_CERRADOS = {
    "finalizada",
    "finalizado",
    "cerrada",
    "cerrado",
    "cancelada",
    "cancelado",
    "anulada",
    "anulado",
}


ESTADOS_BLOQUEADOS = {
    "pendiente material",
    "esperando material",
    "pendiente proveedor",
    "pendiente presupuesto",
    "pendiente empresa",
}


ESTADOS_EN_CURSO = {
    "en curso",
    "en ejecucion",
    "ejecutando",
}


# Estructura real que queremos representar.
EDIFICIOS = {
    "Pearson 22": {
        "Infantil / Primaria": [
            "Terrado",
            "Planta 5",
            "Planta 4",
            "Planta 3",
            "Planta 2",
            "Planta 1",
        ],
        "Llar": [
            "Terrado",
            "Planta 2",
            "Planta 1",
            "Planta 0",
        ],
    },
    "Pearson 9": {
        "Edificio A": [
            "Terrado",
            "Planta 2",
            "Planta 1",
            "Planta 0",
        ],
        "Edificio B": [
            "Terrado",
            "Planta 2",
            "Planta 1",
            "Planta 0",
        ],
        "Edificio C": [
            "Terrado",
            "Planta 2",
            "Planta 1",
            "Planta 0",
        ],
    },
}


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

    for caracter in [
        "/",
        "\\",
        "-",
        "_",
        ".",
        ",",
        ";",
        ":",
        "º",
        "ª",
        "(",
        ")",
    ]:
        texto = texto.replace(caracter, " ")

    return " ".join(texto.split())


def _normalizar_estado(valor):
    return _normalizar_texto(valor)


def _normalizar_prioridad(valor):
    return _normalizar_texto(valor)


def _normalizar_centro(valor):
    texto = _normalizar_texto(valor)

    alias_p22 = {
        "pearson 22",
        "pearson22",
        "p22",
        "pearson numero 22",
    }

    alias_p9 = {
        "pearson 9",
        "pearson9",
        "p9",
        "pearson numero 9",
    }

    if texto in alias_p22 or "pearson 22" in texto:
        return "Pearson 22"

    if texto in alias_p9 or "pearson 9" in texto:
        return "Pearson 9"

    return str(valor or "").strip()


def _texto_ubicacion_ot(ot):
    return " ".join(
        str(ot.get(campo) or "")
        for campo in [
            "centro",
            "edificio",
            "planta",
            "espacio",
            "descripcion",
            "solicitante",
            "observaciones",
            "observaciones_estado",
        ]
    )


def _normalizar_edificio(valor, centro, ot=None):
    texto = _normalizar_texto(valor)

    if ot:
        texto_apoyo = _normalizar_texto(
            f"{texto} {_texto_ubicacion_ot(ot)}"
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
            "infantil/primaria",
            "edificio infantil",
            "edificio primaria",
            "edif infantil",
            "edif primaria",
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

    # Compatibilidad con registros antiguos.
    if centro == "Pearson 22":
        return "Infantil / Primaria"

    if centro == "Pearson 9":
        return "Edificio A"

    return str(valor or "General").strip()


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

    patrones = [
        r"\bplanta\s*([0-9])\b",
        r"\bpiso\s*([0-9])\b",
        r"\bnivel\s*([0-9])\b",
        r"\bp\s*([0-9])\b",
        r"\b([0-9])\s*planta\b",
    ]

    for patron in patrones:
        coincidencia = re.search(patron, texto)

        if coincidencia:
            return f"Planta {int(coincidencia.group(1))}"

    if texto.isdigit():
        numero = int(texto)

        if 0 <= numero <= 9:
            return f"Planta {numero}"

    palabras = texto.split()

    for palabra, numero in equivalencias.items():
        if palabra in palabras:
            return f"Planta {numero}"

    return ""


# =========================================================
# LECTURA DIRECTA Y SEGURA DE ÓRDENES
# =========================================================

def _obtener_ordenes_colegio_vivo(operario):
    """
    Lee directamente ordenes_trabajo con SELECT *.

    Ventajas:
    - Si existe la columna planta, la obtiene.
    - Si todavía no existe, no provoca error.
    - No modifica obtener_ordenes_operario().
    - Convierte siempre las filas a diccionarios.
    """
    centro_asignado = MAPA_OPERARIO_CENTRO.get(operario)

    conn = conectar()
    cursor = conn.cursor()

    try:
        if centro_asignado:
            cursor.execute(
                _sql("""
                    SELECT *
                    FROM ordenes_trabajo
                    WHERE centro = ?
                    ORDER BY id DESC
                """),
                (centro_asignado,),
            )
        else:
            cursor.execute("""
                SELECT *
                FROM ordenes_trabajo
                ORDER BY id DESC
            """)

        filas = cursor.fetchall()

        columnas = [
            descripcion[0]
            for descripcion in cursor.description
        ]

        return [
            dict(zip(columnas, fila))
            for fila in filas
        ]

    finally:
        conn.close()


# =========================================================
# UBICACIÓN
# =========================================================

def _obtener_planta(ot):
    """
    Mismo principio que Gerencia:

    1. Planta real, si existe.
    2. Espacio.
    3. Edificio.
    4. Descripción.
    5. Observaciones.
    """
    candidatos = [
        ot.get("planta"),
        ot.get("espacio"),
        ot.get("edificio"),
        ot.get("descripcion"),
        ot.get("observaciones"),
        ot.get("observaciones_estado"),
    ]

    for candidato in candidatos:
        planta = _normalizar_planta(candidato)

        if planta:
            return planta

    return ""


def _planta_respaldo(centro, edificio):
    """
    Evita que las OT antiguas desaparezcan.

    Se colocan provisionalmente igual que en Gerencia.
    """
    if centro == "Pearson 22":
        if edificio == "Llar":
            return "Planta 0"

        return "Planta 1"

    if centro == "Pearson 9":
        return "Planta 0"

    return "Sin planta"


def _obtener_planta_con_respaldo(ot, centro, edificio):
    planta = _obtener_planta(ot)

    if planta:
        return planta, False

    return _planta_respaldo(centro, edificio), True


# =========================================================
# ESTADOS
# =========================================================

def _es_cerrada(estado):
    return estado in ESTADOS_CERRADOS


def _es_bloqueada(estado):
    return estado in ESTADOS_BLOQUEADOS


def _es_ejecutable(estado):
    return (
        not _es_cerrada(estado)
        and not _es_bloqueada(estado)
    )


def _es_en_curso(estado):
    return estado in ESTADOS_EN_CURSO


# =========================================================
# DUPLICADOS
# =========================================================

def _clave_ot(ot):
    numero_ot = str(
        ot.get("numero_ot") or ""
    ).strip()

    if numero_ot:
        return f"ot::{numero_ot}"

    identificador = str(
        ot.get("id") or ""
    ).strip()

    if identificador:
        return f"id::{identificador}"

    return "fila::" + "||".join(
        str(ot.get(campo) or "").strip()
        for campo in [
            "fecha_creacion",
            "centro",
            "edificio",
            "planta",
            "espacio",
            "descripcion",
        ]
    )


def _eliminar_duplicados(ordenes):
    resultado = []
    vistas = set()

    for ot in ordenes:
        clave = _clave_ot(ot)

        if clave in vistas:
            continue

        vistas.add(clave)
        resultado.append(ot)

    return resultado


def _orden_planta(nombre):
    texto = _normalizar_texto(nombre)

    if texto == "terrado":
        return 100

    coincidencia = re.search(r"\d+", texto)

    if coincidencia:
        return int(coincidencia.group())

    return -100


# =========================================================
# FUNCIÓN PÚBLICA
# =========================================================

def obtener_colegio_vivo(operario):
    filas = _obtener_ordenes_colegio_vivo(operario)

    colegio = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(list)
        )
    )

    for ot in filas:
        estado = _normalizar_estado(
            ot.get("estado")
        )

        # Solo desaparecen las verdaderamente cerradas.
        if _es_cerrada(estado):
            continue

        centro = _normalizar_centro(
            ot.get("centro")
        )

        edificio = _normalizar_edificio(
            ot.get("edificio"),
            centro,
            ot,
        )

        planta, sin_ubicar = _obtener_planta_con_respaldo(
            ot,
            centro,
            edificio,
        )

        ot["_estado_normalizado"] = estado
        ot["_centro_normalizado"] = centro
        ot["_edificio_normalizado"] = edificio
        ot["_planta_normalizada"] = planta

        ot["_sin_ubicar"] = sin_ubicar
        ot["_bloqueada"] = _es_bloqueada(estado)
        ot["_ejecutable"] = _es_ejecutable(estado)
        ot["_en_curso"] = _es_en_curso(estado)

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
                ordenes = _eliminar_duplicados(ordenes)

                ordenes_ejecutables = [
                    ot
                    for ot in ordenes
                    if ot.get("_ejecutable", False)
                ]

                ordenes_bloqueadas = [
                    ot
                    for ot in ordenes
                    if ot.get("_bloqueada", False)
                ]

                ordenes_en_curso = [
                    ot
                    for ot in ordenes
                    if ot.get("_en_curso", False)
                ]

                ordenes_sin_ubicar = [
                    ot
                    for ot in ordenes
                    if ot.get("_sin_ubicar", False)
                ]

                urgentes = sum(
                    1
                    for ot in ordenes_ejecutables
                    if _normalizar_prioridad(
                        ot.get("prioridad")
                    ) == "urgente"
                )

                altas = sum(
                    1
                    for ot in ordenes_ejecutables
                    if _normalizar_prioridad(
                        ot.get("prioridad")
                    ) == "alta"
                )

                bloque_edificio["plantas"].append(
                    {
                        "nombre": planta,

                        "total": len(ordenes),
                        "ejecutables": len(ordenes_ejecutables),
                        "bloqueadas": len(ordenes_bloqueadas),
                        "en_curso": len(ordenes_en_curso),
                        "sin_ubicar": len(ordenes_sin_ubicar),

                        "urgentes": urgentes,
                        "altas": altas,

                        "ordenes": ordenes,
                        "ordenes_ejecutables": ordenes_ejecutables,
                        "ordenes_bloqueadas": ordenes_bloqueadas,
                        "ordenes_en_curso": ordenes_en_curso,
                        "ordenes_sin_ubicar": ordenes_sin_ubicar,
                    }
                )

            bloque_centro["edificios"].append(
                bloque_edificio
            )

        resultado.append(bloque_centro)

    return resultado
