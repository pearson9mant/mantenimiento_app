import re
import unicodedata

import streamlit as st
from database.db import conectar, _sql

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


def _sin_acentos(texto):
    texto = str(texto or "")
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def _normalizar_comparacion(texto):
    texto = _sin_acentos(texto).lower()

    texto = texto.replace("edif.", "")
    texto = texto.replace("edificio", "")
    texto = texto.replace("infantil/primaria", "infantilprimaria")
    texto = texto.replace("infantil / primaria", "infantilprimaria")
    texto = texto.replace("·", "")
    texto = texto.replace("/", "")
    texto = texto.replace("\\", "")
    texto = texto.replace("-", "")
    texto = texto.replace("_", "")
    texto = texto.replace("ª", "a")
    texto = texto.replace("º", "o")
    texto = texto.replace("1a", "1")
    texto = texto.replace("2a", "2")
    texto = texto.replace("3a", "3")
    texto = texto.replace("4a", "4")
    texto = texto.replace("5a", "5")
    texto = texto.replace("planta", "p")
    texto = texto.replace(" ", "")

    return texto.strip()


def _normalizar_espacio_alias(texto):
    """
    Normalización prudente para espacios.
    No convierte 'WC' en 'WC chicas' para evitar falsos positivos.
    Sí corrige equivalencias claras:
    - P5A / I5A
    - WC niñas / WC chicas
    - WC niños / WC chicos
    """

    t = _normalizar_comparacion(texto)

    t = t.replace("ninas", "chicas")
    t = t.replace("ninos", "chicos")
    t = t.replace("profesores", "profes")

    # Antiguo formulario: P3A/P4A/P5A
    # Catálogo nuevo: I3A/I4A/I5A
    m = re.fullmatch(r"p([345])([abc])", t)
    if m:
        return f"i{m.group(1)}{m.group(2)}"

    return t


def _coincide_centro(a, b):
    return _normalizar_comparacion(a) == _normalizar_comparacion(b)


def _coincide_espacio(a, b):
    a_norm = _normalizar_espacio_alias(a)
    b_norm = _normalizar_espacio_alias(b)

    if not a_norm or not b_norm:
        return False

    if a_norm == b_norm:
        return True

    return False


# =====================================================
# CENTROS / ESPACIOS
# =====================================================

def obtener_centros_espacios():
    centros = []

    try:
        conn = conectar()
        cur = conn.cursor()

        cur.execute(_sql("""
            SELECT DISTINCT centro
            FROM colegio_espacios
            WHERE centro IS NOT NULL AND TRIM(centro) <> ''
            ORDER BY centro
        """))

        centros = [
            normalizar_texto(r[0])
            for r in cur.fetchall()
            if normalizar_texto(r[0])
        ]

        conn.close()

    except Exception:
        centros = []

    if centros:
        return centros

    return list(COLEGIO_BASE.keys())


def obtener_centros_visibles_usuario():
    perfil = str(st.session_state.get("perfil", "")).lower()
    operario = str(st.session_state.get("operario_activo", "")).strip()

    todos_centros = obtener_centros_espacios()

    if perfil in ["admin", "administracion", "administración", "inventario"]:
        return todos_centros

    if operario == "J.A. Almeda":
        return [c for c in todos_centros if c == "Pearson 22"]

    if operario == "Luis Lozano":
        return [c for c in todos_centros if c == "Pearson 9"]

    return todos_centros


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
        FROM colegio_espacios
        WHERE espacio IS NOT NULL AND espacio <> ''
        """,
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

        for centro_ot, edificio_ot, espacio_ot, estado_ot in cur.fetchall():
            if (
                _coincide_centro(centro_ot, centro)
                and _coincide_espacio(espacio_ot, espacio)
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


def obtener_ots_abiertas_por_centro():
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

    datos = {
        "__filas__": []
    }

    for centro, espacio, total in filas:
        centro_txt = normalizar_texto(centro)
        espacio_txt = normalizar_texto(espacio)
        total_int = int(total or 0)

        clave = (
            _normalizar_comparacion(centro_txt),
            _normalizar_espacio_alias(espacio_txt)
        )

        datos[clave] = datos.get(clave, 0) + total_int

        datos["__filas__"].append({
            "centro": centro_txt,
            "espacio": espacio_txt,
            "total": total_int,
        })

    return datos


def obtener_estado_espacio_rapido(centro, espacio, ots_abiertas):
    if contar_ots_espacio_rapido(centro, espacio, ots_abiertas) > 0:
        return "rojo"

    return "verde"


def contar_ots_espacio_rapido(centro, espacio, ots_abiertas):
    if not ots_abiertas:
        return 0

    clave = (
        _normalizar_comparacion(centro),
        _normalizar_espacio_alias(espacio)
    )

    total = int(ots_abiertas.get(clave, 0) or 0)

    if total > 0:
        return total

    for fila in ots_abiertas.get("__filas__", []):
        if (
            _coincide_centro(fila.get("centro"), centro)
            and _coincide_espacio(fila.get("espacio"), espacio)
        ):
            total += int(fila.get("total") or 0)

    return total
