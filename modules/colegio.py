import streamlit as st
from database.db import conectar, _sql
from modules.ubicaciones import obtener_centros_espacios

# =====================================================
# MAPA BASE DEL COLEGIO
# =====================================================

COLEGIO_BASE = {
    "Pearson 22": {
        "Infantil / Primaria": {
            "Terrado": [],
            "Planta 5": [],
            "Planta 4": [],
            "Planta 3": [],
            "Planta 2": [],
            "Planta 1": [],
        },
        "Llar": {
            "Terrado": [],
            "Planta 2": [],
            "Planta 1": [],
            "Planta 0": [],
        },
    },
    "Pearson 9": {
        "Edificio A": {
            "Terrado": [],
            "Planta 0": [],
            "Planta 1": [],
            "Planta 2": [],
        },
        "Edificio B": {
            "Terrado": [],
            "Planta 0": [],
            "Planta 1": [],
            "Planta 2": [],
        },
        "Edificio C": {
            "Terrado": [],
            "Planta 0": [],
            "Planta 1": [],
            "Planta 2": [],
        },
    },
}


# =====================================================
# NORMALIZADORES
# =====================================================

def normalizar_texto(texto):
    return str(texto or "").strip()


def _normalizar_comparacion(texto):
    """
    Normaliza textos para comparar centro/edificio/espacio aunque vengan
    escritos de forma ligeramente distinta.

    Ejemplo:
    'Edif. Infantil/Primaria' == 'Infantil / Primaria'
    """
    return (
        str(texto or "")
        .lower()
        .replace("edif.", "")
        .replace("edificio", "")
        .replace(" ", "")
        .replace("·", "")
        .strip()
    )


# =====================================================
# ÁRBOL BASE ANTIGUO / COMPATIBILIDAD
# =====================================================

def detectar_planta_desde_espacio(espacio):
    texto = normalizar_texto(espacio).lower()

    if "terrado" in texto or "cubierta" in texto:
        return "Terrado"
    if "planta 5" in texto or "p5" in texto:
        return "Planta 5"
    if "planta 4" in texto or "p4" in texto:
        return "Planta 4"
    if "planta 3" in texto or "p3" in texto:
        return "Planta 3"
    if "planta 2" in texto or "p2" in texto:
        return "Planta 2"
    if "planta 1" in texto or "p1" in texto:
        return "Planta 1"
    if "planta 0" in texto or "p0" in texto:
        return "Planta 0"

    return "Sin planta"


def obtener_espacios_desde_bd():
    espacios = []

    conn = conectar()
    cur = conn.cursor()

    consultas = [
        """
        SELECT DISTINCT centro, edificio, espacio
        FROM ordenes_trabajo
        WHERE espacio IS NOT NULL AND espacio <> ''
        """,
        """
        SELECT DISTINCT centro, edificio, espacio
        FROM historico_ordenes
        WHERE espacio IS NOT NULL AND espacio <> ''
        """,
        """
        SELECT DISTINCT centro, edificio, espacio
        FROM inventario_aulas
        WHERE espacio IS NOT NULL AND espacio <> ''
        """,
        """
        SELECT DISTINCT centro, edificio, espacio
        FROM preventivo_aulas
        WHERE espacio IS NOT NULL AND espacio <> ''
        """,
    ]

    for sql in consultas:
        try:
            cur.execute(_sql(sql))
            for centro, edificio, espacio in cur.fetchall():
                centro = normalizar_texto(centro)
                edificio = normalizar_texto(edificio)
                espacio = normalizar_texto(espacio)

                if centro and espacio:
                    espacios.append((centro, edificio, espacio))
        except Exception:
            pass

    conn.close()
    return espacios


def obtener_arbol_colegio():
    arbol = {}

    for centro, edificios in COLEGIO_BASE.items():
        arbol[centro] = {}

        for edificio, plantas in edificios.items():
            arbol[centro][edificio] = {}

            for planta in plantas.keys():
                arbol[centro][edificio][planta] = []

    espacios_bd = obtener_espacios_desde_bd()

    for centro, edificio, espacio in espacios_bd:
        if centro not in arbol:
            arbol[centro] = {}

        if not edificio:
            edificio = "Sin edificio"

        if edificio not in arbol[centro]:
            arbol[centro][edificio] = {}

        planta = detectar_planta_desde_espacio(espacio)

        if planta not in arbol[centro][edificio]:
            arbol[centro][edificio][planta] = []

        if espacio not in arbol[centro][edificio][planta]:
            arbol[centro][edificio][planta].append(espacio)

    for centro in arbol:
        for edificio in arbol[centro]:
            for planta in arbol[centro][edificio]:
                arbol[centro][edificio][planta] = sorted(
                    arbol[centro][edificio][planta]
                )

    return arbol


# =====================================================
# ESTADO DEL ESPACIO
# =====================================================

def obtener_estado_espacio(centro, edificio, espacio):
    """
    Devuelve:
    rojo     -> tiene OT activa / correctivo pendiente
    amarillo -> reservado para elementos a revisar
    verde    -> sin avisos
    """

    centro_obj = _normalizar_comparacion(centro)
    edificio_obj = _normalizar_comparacion(edificio)
    espacio_obj = _normalizar_comparacion(espacio)

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT centro, edificio, espacio, estado
            FROM ordenes_trabajo
            WHERE TRIM(LOWER(COALESCE(estado, ''))) NOT IN (
                'finalizada',
                'cerrado',
                'cerrada',
                'cancelada'
            )
        """))

        ordenes = cur.fetchall()

        for centro_ot, edificio_ot, espacio_ot, estado_ot in ordenes:
            if (
                _normalizar_comparacion(centro_ot) == centro_obj
                and _normalizar_comparacion(espacio_ot) == espacio_obj
            ):
                conn.close()
                return "rojo"

    except Exception:
        pass

    conn.close()
    return "verde"


def icono_estado_espacio(estado):
    if estado == "rojo":
        return "🔴"
    if estado == "amarillo":
        return "🟡"
    return "🟢"

def obtener_centros_visibles_usuario():
    perfil = str(st.session_state.get("perfil", "")).lower()
    operario = str(st.session_state.get("operario_activo", "")).strip()

    todos_centros = obtener_centros_espacios()

    if perfil in ["admin", "administracion", "administración"]:
        return todos_centros

    if perfil == "inventario":
        return todos_centros

    if operario == "J.A. Almeda":
        return [c for c in todos_centros if c == "Pearson 22"]

    if operario == "Luis Lozano":
        return [c for c in todos_centros if c == "Pearson 9"]

    return []

def obtener_ots_abiertas_por_centro():
    """
    Devuelve todas las OT abiertas agrupadas por centro + espacio.
    Se usa para pintar el árbol rápido sin consultar la BD por cada aula.
    """

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT centro, espacio, COUNT(*)
            FROM ordenes_trabajo
            WHERE TRIM(LOWER(COALESCE(estado, ''))) NOT IN (
                'finalizada',
                'cerrado',
                'cerrada',
                'cancelada'
            )
            GROUP BY centro, espacio
        """))

        filas = cur.fetchall()

    except Exception:
        filas = []

    conn.close()

    datos = {}

    for centro, espacio, total in filas:
        clave = (
            _normalizar_comparacion(centro),
            _normalizar_comparacion(espacio)
        )
        datos[clave] = int(total or 0)

    return datos


def obtener_estado_espacio_rapido(centro, espacio, ots_abiertas):
    clave = (
        _normalizar_comparacion(centro),
        _normalizar_comparacion(espacio)
    )

    if ots_abiertas.get(clave, 0) > 0:
        return "rojo"

    return "verde"


def contar_ots_espacio_rapido(centro, espacio, ots_abiertas):
    clave = (
        _normalizar_comparacion(centro),
        _normalizar_comparacion(espacio)
    )

    return int(ots_abiertas.get(clave, 0) or 0)
