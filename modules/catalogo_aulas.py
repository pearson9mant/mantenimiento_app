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

    # Iluminación
    ("Iluminación", "Iluminación", "Electricidad"),
    ("Iluminación", "Downlight", "Electricidad"),
    ("Iluminación", "Ojo de buey", "Electricidad"),
    ("Iluminación", "Plafón", "Electricidad"),
    ("Iluminación", "Luminaria LED", "Electricidad"),
    ("Iluminación", "Tubo LED", "Electricidad"),
    ("Iluminación", "Panel LED", "Electricidad"),
    ("Iluminación", "Pantalla fluorescente", "Electricidad"),
    ("Iluminación", "Luminaria estanca", "Electricidad"),
    ("Iluminación", "Luminaria exterior", "Electricidad"),
    ("Iluminación", "Proyector / Foco", "Electricidad"),

    # Electricidad
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
    ("Carpintería", "Puerta de madera", "Carpintería"),
    ("Carpintería", "Puerta de aluminio", "Carpintería"),
    ("Carpintería", "Puerta cortafuegos", "Carpintería"),
    ("Carpintería", "Ventana", "Carpintería"),
    ("Carpintería", "Persiana", "Carpintería"),
    ("Carpintería", "Cortina", "Carpintería"),
    ("Carpintería", "Cristal", "Carpintería"),

    # Cerrajería
    ("Cerrajería", "Maneta", "Cerrajería"),
    ("Cerrajería", "Cerradura", "Cerrajería"),
    ("Cerrajería", "Bombín", "Cerrajería"),
    ("Cerrajería", "Cierrapuertas", "Cerrajería"),
    ("Cerrajería", "Bisagra", "Cerrajería"),
    ("Cerrajería", "Cerrojo", "Cerrajería"),
    ("Cerrajería", "Candado", "Cerrajería"),

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
    ("Climatización", "Aire acondicionado", "Climatización"),
    ("Climatización", "Unidad interior A/A", "Climatización"),
    ("Climatización", "Unidad exterior A/A", "Climatización"),
    ("Climatización", "Mando aire acondicionado", "Climatización"),

    # Fontanería / WC
    ("Fontanería", "Lavabo", "Fontanería"),
    ("Fontanería", "Grifo", "Fontanería"),
    ("Fontanería", "Grifo temporizado", "Fontanería"),
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
    ("Fontanería", "Cisterna", "Fontanería"),
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

    # Equipamiento
    ("Equipamiento", "Pizarra", "Equipamiento"),
    ("Equipamiento", "Pantalla", "Equipamiento"),
    ("Equipamiento", "Reloj", "Equipamiento"),
    ("Equipamiento", "Tablón de anuncios", "Equipamiento"),
    ("Equipamiento", "Dispensador", "Equipamiento"),

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

    # Exterior / Jardinería
    ("Exterior / Jardinería", "Banco exterior", "Equipamiento"),
    ("Exterior / Jardinería", "Papelera exterior", "Equipamiento"),
    ("Exterior / Jardinería", "Fuente", "Fontanería"),
    ("Exterior / Jardinería", "Jardinera", "Jardinería"),
    ("Exterior / Jardinería", "Riego", "Jardinería"),
    ("Exterior / Jardinería", "Aspersor", "Jardinería"),
    ("Exterior / Jardinería", "Sumidero", "Fontanería"),
    ("Exterior / Jardinería", "Rejilla desagüe", "Fontanería"),
    ("Exterior / Jardinería", "Foco exterior", "Electricidad"),

    # Otros
    ("Otros", "Otro", "Equipamiento"),
]


# Elementos antiguos que ya pueden existir en la base de datos.
# Se reclasifican de forma idempotente para no dejar duplicados
# en las categorías anteriores al actualizar el catálogo.
RECLASIFICACION_CATEGORIAS = {
    "Iluminación": "Iluminación",
    "Luminaria LED": "Iluminación",
    "Tubo LED": "Iluminación",
    "Panel LED": "Iluminación",
    "Maneta": "Cerrajería",
    "Cerradura": "Cerrajería",
    "Bombín": "Cerrajería",
    "Cierrapuertas": "Cerrajería",
    "Bisagra": "Cerrajería",
}


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

    # Primero recolocamos los elementos antiguos si ya existían.
    for elemento, categoria_nueva in RECLASIFICACION_CATEGORIAS.items():
        cur.execute(_sql("""
            UPDATE catalogo_aulas
            SET categoria = ?
            WHERE elemento = ?
              AND categoria <> ?
        """), (
            categoria_nueva,
            elemento,
            categoria_nueva,
        ))

    # Después añadimos solo lo que todavía no exista.
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
