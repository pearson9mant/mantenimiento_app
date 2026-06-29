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
    """
    Elimina registros incorrectos tipo:
    planta='Planta 1' y espacio='Planta 1'
    porque una planta no debe ser un espacio.
    """
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


def obtener_espacios(activos=True):
    crear_tabla_espacios()
    limpiar_plantas_guardadas_como_espacios()

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


def obtener_arbol_espacios():
    crear_tabla_espacios()
    limpiar_plantas_guardadas_como_espacios()

    arbol = {}

    # Primero creamos centros / edificios / plantas aunque estén vacías
    for centro, edificios in PLANTAS_BASE.items():
        arbol[centro] = {}

        for edificio, plantas in edificios.items():
            arbol[centro][edificio] = {}

            for planta in plantas:
                if planta_visible(centro, edificio, planta):
                    arbol[centro][edificio][planta] = []

    # Después metemos espacios reales
    datos = obtener_espacios(True)

    for fila in datos:
        id_espacio, centro, edificio, planta, espacio, tipo, activo = fila

        centro = str(centro or "").strip()
        edificio = str(edificio or "").strip()
        planta = str(planta or "").strip()
        espacio = str(espacio or "").strip()
        tipo = str(tipo or "").strip()

        if not centro or not edificio or not planta or not espacio:
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

        existe = False

        for existente in arbol[centro][edificio][planta]:
            if existente.get("espacio") == espacio:
                existe = True
                break

        if not existe:
            arbol[centro][edificio][planta].append(item)

    for centro in arbol:
        for edificio in arbol[centro]:
            for planta in arbol[centro][edificio]:
                arbol[centro][edificio][planta] = ordenar_items_espacios(
                    arbol[centro][edificio][planta]
                )

    return arbol


def crear_espacio(centro, edificio, planta, espacio, tipo="Espacio"):
    crear_tabla_espacios()

    centro = str(centro or "").strip()
    edificio = str(edificio or "").strip()
    planta = str(planta or "").strip()
    espacio = str(espacio or "").strip()
    tipo = str(tipo or "Espacio").strip()

    if not centro or not edificio or not planta or not espacio:
        return False

    if espacio == planta:
        return False

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT COUNT(*)
        FROM espacios
        WHERE centro = ?
          AND edificio = ?
          AND planta = ?
          AND espacio = ?
    """), (
        centro,
        edificio,
        planta,
        espacio
    ))

    existe = int(cur.fetchone()[0] or 0)

    if existe == 0:
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
    else:
        cur.execute(_sql("""
            UPDATE espacios
            SET tipo = ?,
                activo = 1
            WHERE centro = ?
              AND edificio = ?
              AND planta = ?
              AND espacio = ?
        """), (
            tipo,
            centro,
            edificio,
            planta,
            espacio
        ))

    conn.commit()
    conn.close()
    return True


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

def actualizar_espacio(id_espacio, centro, edificio, planta, espacio, tipo):
    crear_tabla_espacios()

    centro = str(centro or "").strip()
    edificio = str(edificio or "").strip()
    planta = str(planta or "").strip()
    espacio = str(espacio or "").strip()
    tipo = str(tipo or "Espacio").strip()

    if not id_espacio or not centro or not edificio or not planta or not espacio:
        return False

    if espacio == planta:
        return False

    conn = conectar()
    cur = conn.cursor()

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

    conn.commit()
    conn.close()
    return True
