from database.db import conectar, _sql


CENTROS = ["Pearson 22", "Pearson 9"]


# =====================================================
# EDIFICIOS
# =====================================================

EDIFICIOS_POR_CENTRO = {
    "Pearson 22": [
        "Edif. Infantil/Primaria",
        "Edif. Llar (Anexo)"
    ],
    "Pearson 9": [
        "Edif. A",
        "Edif. B",
        "Edif. C"
    ]
}


# =====================================================
# ESPACIOS BASE
# =====================================================

ESPACIOS_POR_EDIFICIO = {

    # =================================================
    # PEARSON 22
    # =================================================

    "Edif. Infantil/Primaria": [
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

        "Calderas",

        "Otro"
    ],

    "Edif. Llar (Anexo)": [
        "I1A", "I1B", "I1C",
        "I2A", "I2B", "I2C",

        "Sala polivalente",
        "Sala profesores",
        "Pasillo",
        "Patio",
        "WC",

        "Calderas",

        "Otro"
    ],

    # =================================================
    # PEARSON 9
    # =================================================

    "Edif. A": [
        "ESO 1A", "ESO 1B", "ESO 1C",
        "ESO 2A", "ESO 2B", "ESO 2C",
        "ESO 3A", "ESO 3B", "ESO 3C",

        "Capilla",
        "Cocina",
        "Comedor",
        "Laboratorio",
        "Secretaria",
        "Pasillo",
        "WC",

        "Calderas",

        "Otro"
    ],

    "Edif. B": [
        "General",
        "Laboratorio",
        "Aula informática",
        "Pasillo",
        "WC",

        "Calderas",

        "Otro"
    ],

    "Edif. C": [
        "ESO 4A", "ESO 4B", "ESO 4C",
        "Bach 1A", "Bach 1B", "Bach 1C",
        "Bach 2A", "Bach 2B", "Bach 2C",

        "Pasillo",
        "WC",

        "Calderas",

        "Otro"
    ]
}


# =====================================================
# ASEGURAR TABLA
# =====================================================

def asegurar_tabla_ubicaciones_personalizadas():
    conn = conectar()
    cursor = conn.cursor()

    modulo = conn.__class__.__module__.lower()
    es_postgres = "psycopg2" in modulo or "psycopg" in modulo

    if es_postgres:
        id_sql = "SERIAL PRIMARY KEY"
    else:
        id_sql = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS ubicaciones_personalizadas (
            id {id_sql},
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()


# =====================================================
# CENTROS / EDIFICIOS / ESPACIOS
# =====================================================

def obtener_centros():
    return CENTROS


def obtener_edificios(centro):
    return EDIFICIOS_POR_CENTRO.get(centro, [])


def obtener_espacios_base(edificio):
    return ESPACIOS_POR_EDIFICIO.get(edificio, ["Otro"])


# =====================================================
# ESPACIOS PERSONALIZADOS
# =====================================================

def obtener_espacios_personalizados(edificio, centro=None):
    asegurar_tabla_ubicaciones_personalizadas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        if centro:
            cursor.execute(_sql("""
                SELECT espacio
                FROM ubicaciones_personalizadas
                WHERE centro = ?
                  AND edificio = ?
                  AND activo = 1
                ORDER BY espacio
            """), (centro, edificio))
        else:
            cursor.execute(_sql("""
                SELECT espacio
                FROM ubicaciones_personalizadas
                WHERE edificio = ?
                  AND activo = 1
                ORDER BY espacio
            """), (edificio,))

        datos = [fila[0] for fila in cursor.fetchall()]

    except Exception:
        datos = []

    conn.close()
    return datos


# =====================================================
# ESPACIOS COMPLETOS
# =====================================================

def obtener_espacios(edificio, centro=None):
    base = obtener_espacios_base(edificio)
    personalizados = obtener_espacios_personalizados(edificio, centro)

    combinados = []

    for espacio in base + personalizados:
        espacio = str(espacio or "").strip()

        if espacio and espacio not in combinados:
            combinados.append(espacio)

    if "Otro" in combinados:
        combinados.remove("Otro")
        combinados.append("Otro")

    return combinados or ["Otro"]


# =====================================================
# CREAR ESPACIO PERSONALIZADO
# =====================================================

def crear_espacio_personalizado(centro, edificio, espacio):
    asegurar_tabla_ubicaciones_personalizadas()

    centro = str(centro or "").strip()
    edificio = str(edificio or "").strip()
    espacio = str(espacio or "").strip()

    if not centro or not edificio or not espacio:
        return False, "Faltan datos."

    if espacio.lower() == "otro":
        return False, "No hace falta crear 'Otro'. Ya existe."

    existentes = [e.lower() for e in obtener_espacios(edificio, centro)]

    if espacio.lower() in existentes:
        return False, "Ese espacio ya existe."

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        INSERT INTO ubicaciones_personalizadas
        (centro, edificio, espacio, activo)
        VALUES (?, ?, ?, 1)
    """), (centro, edificio, espacio))

    conn.commit()
    conn.close()

    return True, f"Espacio creado: {espacio}"


# =====================================================
# OBTENER UBICACIONES PERSONALIZADAS
# =====================================================

def obtener_ubicaciones_personalizadas():
    asegurar_tabla_ubicaciones_personalizadas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, centro, edificio, espacio, activo
            FROM ubicaciones_personalizadas
            ORDER BY centro, edificio, espacio
        """)

        datos = cursor.fetchall()

    except Exception:
        datos = []

    conn.close()
    return datos


# =====================================================
# ACTIVAR / DESACTIVAR
# =====================================================

def activar_desactivar_espacio(id_ubicacion, activo):
    asegurar_tabla_ubicaciones_personalizadas()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE ubicaciones_personalizadas
        SET activo = ?
        WHERE id = ?
    """), (activo, id_ubicacion))

    conn.commit()
    conn.close()

    return True


# =====================================================
# BORRAR ESPACIO
# =====================================================

def borrar_espacio_personalizado(id_ubicacion):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        DELETE FROM ubicaciones_personalizadas
        WHERE id = ?
    """), (id_ubicacion,))

    conn.commit()
    conn.close()

    return True
