from database.db import conectar, _sql


PLANTAS_BASE = {
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


# =====================================================
# NORMALIZACIÓN
# =====================================================

def normalizar_texto(texto):
    return str(texto or "").strip()


def normalizar_comparacion(texto):
    return (
        str(texto or "")
        .lower()
        .replace("edif.", "")
        .replace("edificio", "")
        .replace(" ", "")
        .replace("·", "")
        .replace("/", "")
        .replace("-", "")
        .strip()
    )


# =====================================================
# PLANTAS
# =====================================================

def crear_tabla_plantas_config():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS plantas_config (
            id SERIAL PRIMARY KEY,
            centro TEXT,
            edificio TEXT,
            planta TEXT,
            visible INTEGER DEFAULT 1
        )
    """))

    conn.commit()

    for centro, edificios in PLANTAS_BASE.items():
        for edificio, plantas in edificios.items():
            for planta in plantas:
                cur.execute(_sql("""
                    SELECT COUNT(*)
                    FROM plantas_config
                    WHERE centro = ? AND edificio = ? AND planta = ?
                """), (centro, edificio, planta))

                if int(cur.fetchone()[0] or 0) == 0:
                    cur.execute(_sql("""
                        INSERT INTO plantas_config
                        (centro, edificio, planta, visible)
                        VALUES (?, ?, ?, 1)
                    """), (centro, edificio, planta))

    conn.commit()
    conn.close()


def obtener_plantas_config():
    crear_tabla_plantas_config()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, centro, edificio, planta, visible
        FROM plantas_config
        ORDER BY centro, edificio, planta
    """))

    datos = cur.fetchall()
    conn.close()
    return datos


def actualizar_visible_planta(id_planta, visible):
    crear_tabla_plantas_config()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        UPDATE plantas_config
        SET visible = ?
        WHERE id = ?
    """), (visible, id_planta))

    conn.commit()
    conn.close()


def planta_visible(centro, edificio, planta):
    crear_tabla_plantas_config()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT visible
        FROM plantas_config
        WHERE centro = ? AND edificio = ? AND planta = ?
        LIMIT 1
    """), (centro, edificio, planta))

    fila = cur.fetchone()
    conn.close()

    if not fila:
        return True

    return int(fila[0] or 0) == 1


# =====================================================
# TABLA ESPACIOS
# =====================================================

def crear_tabla_espacios():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS espacios (
            id SERIAL PRIMARY KEY,
            centro TEXT,
            edificio TEXT,
            planta TEXT,
            espacio TEXT,
            tipo TEXT,
            activo INTEGER DEFAULT 1
        )
    """))

    for columna, tipo in [
        ("centro", "TEXT"),
        ("edificio", "TEXT"),
        ("planta", "TEXT"),
        ("espacio", "TEXT"),
        ("tipo", "TEXT"),
        ("activo", "INTEGER DEFAULT 1"),
        ("codigo", "TEXT"),
    ]:
        try:
            cur.execute(_sql(f"""
                ALTER TABLE espacios
                ADD COLUMN IF NOT EXISTS {columna} {tipo}
            """))
        except Exception:
            pass

    conn.commit()
    conn.close()


def limpiar_plantas_guardadas_como_espacios():
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            DELETE FROM espacios
            WHERE espacio = planta
              AND tipo = 'Planta'
        """))
        conn.commit()
    except Exception:
        conn.rollback()

    conn.close()


# =====================================================
# CÓDIGO INTERNO ESPACIO
# =====================================================

def generar_codigo_espacio(id_espacio):
    try:
        return f"ESP-{int(id_espacio):06d}"
    except Exception:
        return ""


def asegurar_codigos_espacios():
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id
            FROM espacios
            WHERE codigo IS NULL OR codigo = ''
            ORDER BY id
        """))

        filas = cur.fetchall()

        for fila in filas:
            id_espacio = fila[0]
            codigo = generar_codigo_espacio(id_espacio)

            if codigo:
                cur.execute(_sql("""
                    UPDATE espacios
                    SET codigo = ?
                    WHERE id = ?
                """), (codigo, id_espacio))

        conn.commit()

    except Exception:
        conn.rollback()

    conn.close()


# =====================================================
# CRUD ESPACIOS
# =====================================================

def obtener_espacios(activos=True):
    crear_tabla_espacios()
    limpiar_plantas_guardadas_como_espacios()
    asegurar_codigos_espacios()

    conn = conectar()
    cur = conn.cursor()

    if activos:
        cur.execute(_sql("""
            SELECT id, centro, edificio, planta, espacio, tipo, activo
            FROM espacios
            WHERE activo = 1
            ORDER BY centro, edificio, planta, espacio
        """))
    else:
        cur.execute(_sql("""
            SELECT id, centro, edificio, planta, espacio, tipo, activo
            FROM espacios
            ORDER BY centro, edificio, planta, espacio
        """))

    datos = cur.fetchall()
    conn.close()
    return datos


def crear_espacio(centro, edificio, planta, espacio, tipo="Espacio"):
    crear_tabla_espacios()

    centro = normalizar_texto(centro)
    edificio = normalizar_texto(edificio)
    planta = normalizar_texto(planta)
    espacio = normalizar_texto(espacio)
    tipo = normalizar_texto(tipo) or "Espacio"

    if not centro or not edificio or not planta or not espacio:
        return False

    if espacio == planta:
        return False

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id
        FROM espacios
        WHERE centro = ?
          AND edificio = ?
          AND planta = ?
          AND espacio = ?
        LIMIT 1
    """), (
        centro,
        edificio,
        planta,
        espacio
    ))

    fila = cur.fetchone()

    if not fila:
        cur.execute(_sql("""
            INSERT INTO espacios (
                centro,
                edificio,
                planta,
                espacio,
                tipo,
                activo
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """), (
            centro,
            edificio,
            planta,
            espacio,
            tipo,
            1
        ))

        try:
            nuevo_id = cur.lastrowid
        except Exception:
            nuevo_id = None

        if nuevo_id:
            codigo = generar_codigo_espacio(nuevo_id)
            cur.execute(_sql("""
                UPDATE espacios
                SET codigo = ?
                WHERE id = ?
            """), (codigo, nuevo_id))

    else:
        id_espacio = fila[0]

        cur.execute(_sql("""
            UPDATE espacios
            SET tipo = ?,
                activo = 1
            WHERE id = ?
        """), (
            tipo,
            id_espacio
        ))

    conn.commit()
    conn.close()

    asegurar_codigos_espacios()
    return True


def actualizar_espacio(id_espacio, centro, edificio, planta, espacio, tipo):
    crear_tabla_espacios()

    centro = normalizar_texto(centro)
    edificio = normalizar_texto(edificio)
    planta = normalizar_texto(planta)
    espacio = normalizar_texto(espacio)
    tipo = normalizar_texto(tipo) or "Espacio"

    if not id_espacio or not centro or not edificio or not planta or not espacio:
        return False

    if espacio == planta:
        return False

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE espacios
            SET centro = ?,
                edificio = ?,
                planta = ?,
                espacio = ?,
                tipo = ?
            WHERE id = ?
        """), (
            centro,
            edificio,
            planta,
            espacio,
            tipo,
            id_espacio
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def desactivar_espacio(id_espacio):
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        UPDATE espacios
        SET activo = 0
        WHERE id = ?
    """), (id_espacio,))

    conn.commit()
    conn.close()
    return True


# =====================================================
# ÁRBOL
# =====================================================

def obtener_arbol_espacios():
    crear_tabla_espacios()
    limpiar_plantas_guardadas_como_espacios()
    asegurar_codigos_espacios()

    arbol = {}

    for centro, edificios in PLANTAS_BASE.items():
        arbol[centro] = {}

        for edificio, plantas in edificios.items():
            arbol[centro][edificio] = {}

            for planta in plantas:
                if planta_visible(centro, edificio, planta):
                    arbol[centro][edificio][planta] = []

    datos = obtener_espacios(True)

    for fila in datos:
        id_espacio, centro, edificio, planta, espacio, tipo, activo = fila

        centro = normalizar_texto(centro)
        edificio = normalizar_texto(edificio)
        planta = normalizar_texto(planta)
        espacio = normalizar_texto(espacio)
        tipo = normalizar_texto(tipo)

        if not centro or not edificio or not planta or not espacio:
            continue

        if not planta_visible(centro, edificio, planta):
            continue

        arbol.setdefault(centro, {})
        arbol[centro].setdefault(edificio, {})
        arbol[centro][edificio].setdefault(planta, [])

        item = {
            "id": id_espacio,
            "espacio": espacio,
            "tipo": tipo,
            "activo": activo,
        }

        existe = any(
            normalizar_comparacion(e.get("espacio", "")) == normalizar_comparacion(espacio)
            for e in arbol[centro][edificio][planta]
        )

        if not existe:
            arbol[centro][edificio][planta].append(item)

    for centro in arbol:
        for edificio in arbol[centro]:
            for planta in arbol[centro][edificio]:
                arbol[centro][edificio][planta] = ordenar_items_espacios(
                    arbol[centro][edificio][planta]
                )

    return arbol


# =====================================================
# SELECTS CENTRALIZADOS
# =====================================================

def obtener_centros_espacios():
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT DISTINCT centro
        FROM espacios
        WHERE activo = 1
          AND centro IS NOT NULL
          AND centro <> ''
        ORDER BY centro
    """))

    datos = [fila[0] for fila in cur.fetchall()]
    conn.close()
    return datos


def obtener_edificios_espacios(centro):
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT DISTINCT edificio
        FROM espacios
        WHERE activo = 1
          AND centro = ?
          AND edificio IS NOT NULL
          AND edificio <> ''
        ORDER BY edificio
    """), (centro,))

    datos = [fila[0] for fila in cur.fetchall()]
    conn.close()
    return datos


def obtener_plantas_espacios(centro, edificio):
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT DISTINCT planta
        FROM espacios
        WHERE activo = 1
          AND centro = ?
          AND edificio = ?
          AND planta IS NOT NULL
          AND planta <> ''
        ORDER BY planta
    """), (centro, edificio))

    datos = [fila[0] for fila in cur.fetchall()]
    conn.close()
    return datos


def obtener_espacios_por_planta(centro, edificio, planta):
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT espacio, tipo
        FROM espacios
        WHERE activo = 1
          AND centro = ?
          AND edificio = ?
          AND planta = ?
          AND espacio IS NOT NULL
          AND espacio <> ''
        ORDER BY espacio
    """), (centro, edificio, planta))

    datos = cur.fetchall()
    conn.close()
    return datos


def obtener_tipos_espacios():
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT DISTINCT tipo
        FROM espacios
        WHERE activo = 1
          AND tipo IS NOT NULL
          AND tipo <> ''
        ORDER BY tipo
    """))

    datos = [fila[0] for fila in cur.fetchall()]
    conn.close()
    return datos


# =====================================================
# BÚSQUEDAS
# =====================================================

def obtener_espacio_por_id(id_espacio):
    crear_tabla_espacios()
    asegurar_codigos_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, codigo, centro, edificio, planta, espacio, tipo, activo
        FROM espacios
        WHERE id = ?
        LIMIT 1
    """), (id_espacio,))

    fila = cur.fetchone()
    conn.close()
    return fila


def obtener_id_espacio(centro, edificio, planta, espacio):
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id
        FROM espacios
        WHERE activo = 1
          AND centro = ?
          AND edificio = ?
          AND planta = ?
          AND espacio = ?
        LIMIT 1
    """), (
        centro,
        edificio,
        planta,
        espacio
    ))

    fila = cur.fetchone()
    conn.close()
    return fila[0] if fila else None


def obtener_codigo_espacio(centro, edificio, planta, espacio):
    crear_tabla_espacios()
    asegurar_codigos_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT codigo
        FROM espacios
        WHERE activo = 1
          AND centro = ?
          AND edificio = ?
          AND planta = ?
          AND espacio = ?
        LIMIT 1
    """), (
        centro,
        edificio,
        planta,
        espacio
    ))

    fila = cur.fetchone()
    conn.close()
    return str(fila[0] or "") if fila else ""


def buscar_espacio(centro="", edificio="", planta="", espacio=""):
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    sql = """
        SELECT id, codigo, centro, edificio, planta, espacio, tipo, activo
        FROM espacios
        WHERE activo = 1
    """

    params = []

    if centro:
        sql += " AND centro = ?"
        params.append(centro)

    if edificio:
        sql += " AND edificio = ?"
        params.append(edificio)

    if planta:
        sql += " AND planta = ?"
        params.append(planta)

    if espacio:
        sql += " AND espacio = ?"
        params.append(espacio)

    sql += " ORDER BY centro, edificio, planta, espacio"

    cur.execute(_sql(sql), params)

    datos = cur.fetchall()
    conn.close()
    return datos


def obtener_tipo_espacio(centro, edificio, planta, espacio):
    filas = buscar_espacio(
        centro=centro,
        edificio=edificio,
        planta=planta,
        espacio=espacio
    )

    if filas:
        return str(filas[0][6] or "")

    return ""


# =====================================================
# COMPARADORES
# =====================================================

def coincide_centro(a, b):
    return normalizar_comparacion(a) == normalizar_comparacion(b)


def coincide_edificio(a, b):
    return normalizar_comparacion(a) == normalizar_comparacion(b)


def coincide_espacio(a, b):
    a_norm = normalizar_comparacion(a)
    b_norm = normalizar_comparacion(b)

    if not a_norm or not b_norm:
        return False

    if a_norm == b_norm:
        return True

    return False


def coincide_ubicacion(centro1, edificio1, espacio1, centro2, edificio2, espacio2):
    return (
        coincide_centro(centro1, centro2)
        and coincide_edificio(edificio1, edificio2)
        and coincide_espacio(espacio1, espacio2)
    )


# =====================================================
# ICONOS / ORDEN
# =====================================================

def icono_tipo_espacio(tipo):
    tipo = str(tipo or "").strip().lower()

    if "aula" in tipo:
        return "🏫"

    if tipo in ["wc", "aseo", "baño", "lavabo"]:
        return "🚻"

    if "biblioteca" in tipo:
        return "📚"

    if "cocina" in tipo:
        return "🍳"

    if "comedor" in tipo:
        return "🍽️"

    if "despacho" in tipo:
        return "🏢"

    if "sala técnica" in tipo or "sala tecnica" in tipo:
        return "⚙️"

    if "pasillo" in tipo:
        return "🚶"

    if "patio" in tipo:
        return "🌳"

    if "terrado" in tipo or "cubierta" in tipo:
        return "🏗️"

    if "almacén" in tipo or "almacen" in tipo:
        return "📦"

    if "laboratorio" in tipo:
        return "🧪"

    if "gimnasio" in tipo:
        return "🏃"

    if "plástica" in tipo or "plastica" in tipo:
        return "🎨"

    return "📍"


def prioridad_tipo_espacio(tipo):
    tipo = str(tipo or "").strip().lower()

    if "aula" in tipo:
        return 1
    if "biblioteca" in tipo:
        return 2
    if "laboratorio" in tipo:
        return 3
    if "wc" in tipo or "aseo" in tipo or "baño" in tipo:
        return 4
    if "cocina" in tipo or "comedor" in tipo:
        return 5
    if "despacho" in tipo:
        return 6
    if "sala técnica" in tipo or "sala tecnica" in tipo:
        return 7
    if "almacén" in tipo or "almacen" in tipo:
        return 8
    if "pasillo" in tipo:
        return 9
    if "patio" in tipo:
        return 10
    if "terrado" in tipo or "cubierta" in tipo:
        return 11

    return 99


def ordenar_items_espacios(items):
    return sorted(
        items,
        key=lambda x: (
            prioridad_tipo_espacio(x.get("tipo", "")),
            str(x.get("espacio", "")).lower()
        )
    )
