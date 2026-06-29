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


def normalizar_texto(texto):
    return str(texto or "").strip()


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


def obtener_estado_espacio(centro, edificio, espacio):
    """
    Devuelve:
    rojo     -> tiene OT activa / correctivo pendiente
    amarillo -> tiene elementos a revisar
    verde    -> sin avisos
    """

    conn = conectar()
    cur = conn.cursor()

    # 1. Órdenes abiertas en ese espacio
    try:
        cur.execute(_sql("""
            SELECT COUNT(*)
            FROM ordenes_trabajo
            WHERE TRIM(LOWER(centro)) = TRIM(LOWER(?))
              AND TRIM(LOWER(edificio)) = TRIM(LOWER(?))
              AND TRIM(LOWER(espacio)) = TRIM(LOWER(?))
              AND TRIM(LOWER(COALESCE(estado, ''))) NOT IN (
                    'finalizada',
                    'cerrado',
                    'cerrada',
                    'cancelada'
              )
        """), (centro, edificio, espacio))

        if int(cur.fetchone()[0] or 0) > 0:
            conn.close()
            return "rojo"

    except Exception:
        pass

    # 2. Revisiones con elementos a revisar
    try:
        cur.execute(_sql("""
            SELECT COUNT(*)
            FROM preventivo_aulas_items i
            INNER JOIN preventivo_aulas r ON i.revision_id = r.id
            WHERE TRIM(LOWER(r.centro)) = TRIM(LOWER(?))
              AND TRIM(LOWER(r.edificio)) = TRIM(LOWER(?))
              AND TRIM(LOWER(r.espacio)) = TRIM(LOWER(?))
              AND i.estado = 'Revisar'
        """), (centro, edificio, espacio))

        if int(cur.fetchone()[0] or 0) > 0:
            conn.close()
            return "amarillo"

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
