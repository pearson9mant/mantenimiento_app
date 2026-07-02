from database.db import conectar, _sql


CATALOGO_BASE_AULAS = [
    # Mobiliario
    ("Mobiliario", "Silla alumno", "Equipamiento"),
    ("Mobiliario", "Silla profesor", "Equipamiento"),
    ("Mobiliario", "Mesa alumno", "Equipamiento"),
    ("Mobiliario", "Mesa profesor", "Equipamiento"),
    ("Mobiliario", "Armario", "Equipamiento"),
    ("Mobiliario", "Estantería", "Equipamiento"),
    ("Mobiliario", "Papelera", "Equipamiento"),
    ("Mobiliario", "Perchero", "Equipamiento"),

    # Electricidad
    ("Electricidad", "Iluminación", "Electricidad"),
    ("Electricidad", "Luminaria LED", "Electricidad"),
    ("Electricidad", "Tubo LED", "Electricidad"),
    ("Electricidad", "Panel LED", "Electricidad"),
    ("Electricidad", "Interruptor", "Electricidad"),
    ("Electricidad", "Conmutador", "Electricidad"),
    ("Electricidad", "Pulsador", "Electricidad"),
    ("Electricidad", "Enchufe", "Electricidad"),
    ("Electricidad", "Canaleta", "Electricidad"),
    ("Electricidad", "Cuadro eléctrico", "Electricidad"),
    ("Electricidad", "Magnetotérmico", "Electricidad"),
    ("Electricidad", "Diferencial", "Electricidad"),

    # Informática / audiovisual
    ("Informática", "Ordenador", "Informática"),
    ("Informática", "Monitor", "Informática"),
    ("Informática", "Proyector", "Informática"),
    ("Informática", "Pantalla eléctrica", "Informática"),
    ("Informática", "Pantalla interactiva", "Informática"),
    ("Informática", "Altavoces", "Informática"),
    ("Informática", "Router / Switch", "Informática"),
    ("Informática", "Punto de red", "Informática"),

    # Carpintería
    ("Carpintería", "Puerta", "Carpintería"),
    ("Carpintería", "Puerta cortafuegos", "Carpintería"),
    ("Carpintería", "Maneta", "Carpintería"),
    ("Carpintería", "Cerradura", "Carpintería"),
    ("Carpintería", "Bombín", "Carpintería"),
    ("Carpintería", "Cierrapuertas", "Carpintería"),
    ("Carpintería", "Bisagra", "Carpintería"),
    ("Carpintería", "Ventana", "Carpintería"),
    ("Carpintería", "Persiana", "Carpintería"),
    ("Carpintería", "Cortina", "Carpintería"),
    ("Carpintería", "Cristal", "Carpintería"),

    # Construcción
    ("Construcción", "Pared", "Construcción"),
    ("Construcción", "Techo", "Construcción"),
    ("Construcción", "Suelo", "Construcción"),
    ("Construcción", "Rodapié", "Construcción"),
    ("Construcción", "Escalera", "Construcción"),
    ("Construcción", "Barandilla", "Construcción"),

    # Climatización
    ("Climatización", "Radiador", "Climatización"),
    ("Climatización", "Split", "Climatización"),
    ("Climatización", "Fan-coil", "Climatización"),
    ("Climatización", "Termostato", "Climatización"),
    ("Climatización", "Rejilla ventilación", "Climatización"),

    # Fontanería / WC
    ("Fontanería", "Lavabo", "Fontanería"),
    ("Fontanería", "Grifo", "Fontanería"),
    ("Fontanería", "Grifo mezclador de bañera", "Fontanería"),
    ("Fontanería", "Desagüe", "Fontanería"),
    ("Fontanería", "Sifón", "Fontanería"),
    ("Fontanería", "WC", "Fontanería"),
    ("Fontanería", "Inodoro", "Fontanería"),
    ("Fontanería", "Urinario", "Fontanería"),
    ("Fontanería", "Ducha", "Fontanería"),
    ("Fontanería", "Plato de ducha", "Fontanería"),
    ("Fontanería", "Bañera", "Fontanería"),
    ("Fontanería", "Mampara", "Fontanería"),
    ("Fontanería", "Fluxor", "Fontanería"),
    ("Fontanería", "Llave de paso", "Fontanería"),

    # Complementos WC
    ("Complementos WC", "Espejo", "Equipamiento"),
    ("Complementos WC", "Dispensador de jabón", "Equipamiento"),
    ("Complementos WC", "Secamanos", "Electricidad"),
    ("Complementos WC", "Portarrollos", "Equipamiento"),
    ("Complementos WC", "Escobillero", "Equipamiento"),

    # Seguridad / PCI
    ("Seguridad", "Extintor", "Seguridad"),
    ("Seguridad", "BIE", "Seguridad"),
    ("Seguridad", "Luz emergencia", "Electricidad"),
    ("Seguridad", "Detector humo", "Seguridad"),
    ("Seguridad", "Pulsador alarma", "Seguridad"),
    ("Seguridad", "Señalización", "Seguridad"),

    # Cocina
    ("Cocina", "Fregadero", "Fontanería"),
    ("Cocina", "Lavavajillas", "Equipamiento"),
    ("Cocina", "Campana extractora", "Climatización"),
    ("Cocina", "Horno", "Equipamiento"),
    ("Cocina", "Cocina industrial", "Equipamiento"),
    ("Cocina", "Nevera", "Equipamiento"),
    ("Cocina", "Congelador", "Equipamiento"),

    # ACS / Legionella
    ("ACS / Legionella", "Acumulador ACS", "ACS"),
    ("ACS / Legionella", "Depósito", "ACS"),
    ("ACS / Legionella", "Bomba", "ACS"),
    ("ACS / Legionella", "Bomba recirculación", "ACS"),
    ("ACS / Legionella", "Válvula", "Fontanería"),
    ("ACS / Legionella", "Válvula mezcladora", "ACS"),
    ("ACS / Legionella", "Válvula termostática", "ACS"),
    ("ACS / Legionella", "Intercambiador", "ACS"),
    ("ACS / Legionella", "Grupo de presión", "Fontanería"),

    # Otros
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
