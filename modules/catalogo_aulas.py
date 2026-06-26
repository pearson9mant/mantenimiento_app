from database.db import conectar, _sql


CATALOGO_BASE_AULAS = [
    ("Mobiliario", "Silla alumno", "Equipamiento"),
    ("Mobiliario", "Silla profesor", "Equipamiento"),
    ("Mobiliario", "Mesa alumno", "Equipamiento"),
    ("Mobiliario", "Mesa profesor", "Equipamiento"),
    ("Mobiliario", "Armario", "Equipamiento"),
    ("Mobiliario", "Estantería", "Equipamiento"),
    ("Mobiliario", "Papelera", "Equipamiento"),

    ("Electricidad", "Iluminación", "Electricidad"),
    ("Electricidad", "Luminaria LED", "Electricidad"),
    ("Electricidad", "Interruptor", "Electricidad"),
    ("Electricidad", "Enchufe", "Electricidad"),
    ("Electricidad", "Canaleta", "Electricidad"),

    ("Informática", "Ordenador", "Informática"),
    ("Informática", "Monitor", "Informática"),
    ("Informática", "Proyector", "Informática"),
    ("Informática", "Pantalla eléctrica", "Informática"),
    ("Informática", "Pantalla interactiva", "Informática"),
    ("Informática", "Altavoces", "Informática"),
    ("Informática", "Router / Switch", "Informática"),
    ("Informática", "Punto de red", "Informática"),

    ("Carpintería", "Puerta", "Carpintería"),
    ("Carpintería", "Maneta", "Carpintería"),
    ("Carpintería", "Cerradura", "Carpintería"),
    ("Carpintería", "Cierrapuertas", "Carpintería"),
    ("Carpintería", "Ventana", "Carpintería"),
    ("Carpintería", "Persiana", "Carpintería"),
    ("Carpintería", "Cortina", "Carpintería"),

    ("Climatización", "Radiador", "Climatización"),
    ("Climatización", "Split", "Climatización"),
    ("Climatización", "Termostato", "Climatización"),

    ("Fontanería", "Lavabo", "Fontanería"),
    ("Fontanería", "Grifo", "Fontanería"),
    ("Fontanería", "Desagüe", "Fontanería"),
    ("Fontanería", "WC", "Fontanería"),

    ("Seguridad", "Extintor", "Seguridad"),
    ("Seguridad", "Luz emergencia", "Electricidad"),
    ("Seguridad", "Detector humo", "Seguridad"),

    ("Otros", "Otro", "Equipamiento"),
]


def crear_tabla_catalogo_aulas():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS catalogo_aulas (
            id SERIAL PRIMARY KEY,
            categoria TEXT,
            elemento TEXT,
            area TEXT,
            activo INTEGER DEFAULT 1
        )
    """))

    conn.commit()
    conn.close()


def sembrar_catalogo_aulas():
    crear_tabla_catalogo_aulas()

    conn = conectar()
    cur = conn.cursor()

    for categoria, elemento, area in CATALOGO_BASE_AULAS:
        cur.execute(_sql("""
            SELECT COUNT(*)
            FROM catalogo_aulas
            WHERE categoria = ?
              AND elemento = ?
        """), (
            categoria,
            elemento
        ))

        existe = cur.fetchone()[0]

        if not existe:
            cur.execute(_sql("""
                INSERT INTO catalogo_aulas
                (categoria, elemento, area, activo)
                VALUES (?, ?, ?, ?)
            """), (
                categoria,
                elemento,
                area,
                1
            ))

    conn.commit()
    conn.close()


def obtener_catalogo_aulas(activos=True):
    sembrar_catalogo_aulas()

    conn = conectar()
    cur = conn.cursor()

    if activos:
        cur.execute(_sql("""
            SELECT id, categoria, elemento, area, activo
            FROM catalogo_aulas
            WHERE activo = 1
            ORDER BY categoria, elemento
        """))
    else:
        cur.execute(_sql("""
            SELECT id, categoria, elemento, area, activo
            FROM catalogo_aulas
            ORDER BY categoria, elemento
        """))

    datos = cur.fetchall()
    conn.close()
    return datos


def obtener_elementos_catalogo_aulas():
    datos = obtener_catalogo_aulas(True)
    elementos = [str(d[2]) for d in datos if d[2]]

    if "Otro" not in elementos:
        elementos.append("Otro")

    return elementos


def obtener_area_por_elemento_catalogo(elemento):
    sembrar_catalogo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT area
        FROM catalogo_aulas
        WHERE elemento = ?
          AND activo = 1
        LIMIT 1
    """), (elemento,))

    fila = cur.fetchone()
    conn.close()

    if fila:
        return str(fila[0] or "Equipamiento")

    return "Equipamiento"


def crear_elemento_catalogo_aula(categoria, elemento, area):
    crear_tabla_catalogo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        INSERT INTO catalogo_aulas
        (categoria, elemento, area, activo)
        VALUES (?, ?, ?, ?)
    """), (
        categoria,
        elemento,
        area,
        1
    ))

    conn.commit()
    conn.close()
    return True
