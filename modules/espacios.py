from database.db import conectar, _sql


ESPACIOS_BASE = [
    # Pearson 22 - Infantil / Primaria
    ("Pearson 22", "Infantil / Primaria", "Terrado", "Terrado Infantil / Primaria", "Terrado"),
    ("Pearson 22", "Infantil / Primaria", "Planta 5", "Planta 5", "Planta"),
    ("Pearson 22", "Infantil / Primaria", "Planta 4", "Planta 4", "Planta"),
    ("Pearson 22", "Infantil / Primaria", "Planta 3", "Planta 3", "Planta"),
    ("Pearson 22", "Infantil / Primaria", "Planta 2", "Planta 2", "Planta"),
    ("Pearson 22", "Infantil / Primaria", "Planta 1", "Planta 1", "Planta"),

    # Pearson 22 - Llar
    ("Pearson 22", "Llar", "Terrado", "Terrado Llar", "Terrado"),
    ("Pearson 22", "Llar", "Planta 2", "Planta 2", "Planta"),
    ("Pearson 22", "Llar", "Planta 1", "Planta 1", "Planta"),
    ("Pearson 22", "Llar", "Planta 0", "Planta 0", "Planta"),

    # Pearson 9
    ("Pearson 9", "Edificio A", "Terrado", "Terrado Edificio A", "Terrado"),
    ("Pearson 9", "Edificio A", "Planta 2", "Planta 2", "Planta"),
    ("Pearson 9", "Edificio A", "Planta 1", "Planta 1", "Planta"),
    ("Pearson 9", "Edificio A", "Planta 0", "Planta 0", "Planta"),

    ("Pearson 9", "Edificio B", "Terrado", "Terrado Edificio B", "Terrado"),
    ("Pearson 9", "Edificio B", "Planta 2", "Planta 2", "Planta"),
    ("Pearson 9", "Edificio B", "Planta 1", "Planta 1", "Planta"),
    ("Pearson 9", "Edificio B", "Planta 0", "Planta 0", "Planta"),

    ("Pearson 9", "Edificio C", "Terrado", "Terrado Edificio C", "Terrado"),
    ("Pearson 9", "Edificio C", "Planta 2", "Planta 2", "Planta"),
    ("Pearson 9", "Edificio C", "Planta 1", "Planta 1", "Planta"),
    ("Pearson 9", "Edificio C", "Planta 0", "Planta 0", "Planta"),
]


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


def sembrar_espacios_base():
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    for centro, edificio, planta, espacio, tipo in ESPACIOS_BASE:
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

    conn.commit()
    conn.close()


def obtener_espacios(activos=True):
    sembrar_espacios_base()

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
    datos = obtener_espacios(True)

    arbol = {}

    for fila in datos:
        _id, centro, edificio, planta, espacio, tipo, activo = fila

        centro = str(centro or "").strip()
        edificio = str(edificio or "").strip()
        planta = str(planta or "").strip()
        espacio = str(espacio or "").strip()

        if not centro or not edificio or not planta or not espacio:
            continue

        arbol.setdefault(centro, {})
        arbol[centro].setdefault(edificio, {})
        arbol[centro][edificio].setdefault(planta, [])

        if espacio not in arbol[centro][edificio][planta]:
            arbol[centro][edificio][planta].append(espacio)

    for centro in arbol:
        for edificio in arbol[centro]:
            for planta in arbol[centro][edificio]:
                arbol[centro][edificio][planta] = sorted(arbol[centro][edificio][planta])

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
