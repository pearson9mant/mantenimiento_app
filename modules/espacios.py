from database.db import conectar, _sql


_ESTRUCTURA_ESPACIOS_ASEGURADA = False
_ESTRUCTURA_PLANTAS_ASEGURADA = False



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
    """
    Asegura la estructura de plantas una sola vez por proceso.
    Evita repetir CREATE + sembrado en cada lectura del catálogo.
    """
    global _ESTRUCTURA_PLANTAS_ASEGURADA

    if _ESTRUCTURA_PLANTAS_ASEGURADA:
        return

    conn = conectar()
    cur = conn.cursor()

    try:
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
                        WHERE centro = ?
                          AND edificio = ?
                          AND planta = ?
                    """), (
                        centro,
                        edificio,
                        planta,
                    ))

                    if int(cur.fetchone()[0] or 0) == 0:
                        cur.execute(_sql("""
                            INSERT INTO plantas_config
                            (centro, edificio, planta, visible)
                            VALUES (?, ?, ?, 1)
                        """), (
                            centro,
                            edificio,
                            planta,
                        ))

        conn.commit()
        _ESTRUCTURA_PLANTAS_ASEGURADA = True

    except Exception:
        conn.rollback()
        raise

    finally:
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


def crear_planta_configurable(centro, edificio, planta, visible=1):
    """
    Crea una nueva planta o zona en plantas_config.

    No modifica PLANTAS_BASE y no duplica registros existentes.
    Si ya existe pero estaba oculta, puede volver a activarse.
    """
    crear_tabla_plantas_config()

    centro = normalizar_texto(centro)
    edificio = normalizar_texto(edificio)
    planta = normalizar_texto(planta)

    if not centro or not edificio or not planta:
        return False, "Centro, edificio y nombre de planta son obligatorios."

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id, visible
            FROM plantas_config
            WHERE LOWER(COALESCE(centro, '')) = LOWER(?)
              AND LOWER(COALESCE(edificio, '')) = LOWER(?)
              AND LOWER(COALESCE(planta, '')) = LOWER(?)
            LIMIT 1
        """), (
            centro,
            edificio,
            planta,
        ))

        fila = cur.fetchone()

        if fila:
            id_planta, visible_actual = fila

            if int(visible or 0) == 1 and int(visible_actual or 0) == 0:
                cur.execute(_sql("""
                    UPDATE plantas_config
                    SET visible = 1
                    WHERE id = ?
                """), (id_planta,))

                conn.commit()
                return True, "La planta ya existía y se ha vuelto a mostrar."

            return False, "Esa planta o zona ya existe en este edificio."

        cur.execute(_sql("""
            INSERT INTO plantas_config
            (centro, edificio, planta, visible)
            VALUES (?, ?, ?, ?)
        """), (
            centro,
            edificio,
            planta,
            1 if visible else 0,
        ))

        conn.commit()
        return True, f"Planta creada: {planta}"

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo crear la planta: {e}"

    finally:
        conn.close()


def obtener_plantas_config_ubicacion(
    centro,
    edificio,
    solo_visibles=False,
):
    """
    Devuelve plantas configuradas para una ubicación concreta.
    Consulta solo las filas necesarias.
    """
    crear_tabla_plantas_config()

    conn = conectar()
    cur = conn.cursor()

    try:
        if solo_visibles:
            cur.execute(_sql("""
                SELECT planta
                FROM plantas_config
                WHERE centro = ?
                  AND edificio = ?
                  AND visible = 1
                  AND planta IS NOT NULL
                  AND planta <> ''
                ORDER BY id
            """), (
                centro,
                edificio,
            ))
        else:
            cur.execute(_sql("""
                SELECT planta
                FROM plantas_config
                WHERE centro = ?
                  AND edificio = ?
                  AND planta IS NOT NULL
                  AND planta <> ''
                ORDER BY id
            """), (
                centro,
                edificio,
            ))

        resultado = []

        for fila in cur.fetchall():
            planta_txt = normalizar_texto(fila[0])

            if planta_txt and planta_txt not in resultado:
                resultado.append(planta_txt)

        return resultado

    finally:
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
    """
    Asegura la estructura de espacios una sola vez por proceso.
    """
    global _ESTRUCTURA_ESPACIOS_ASEGURADA

    if _ESTRUCTURA_ESPACIOS_ASEGURADA:
        return

    conn = conectar()
    cur = conn.cursor()

    try:
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
            ("qr_habilitado", "INTEGER DEFAULT 1"),
        ]:
            try:
                cur.execute(_sql(f"""
                    ALTER TABLE espacios
                    ADD COLUMN IF NOT EXISTS {columna} {tipo}
                """))
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        conn.commit()
        _ESTRUCTURA_ESPACIOS_ASEGURADA = True

    except Exception:
        conn.rollback()
        raise

    finally:
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


def crear_espacio(
    centro,
    edificio,
    planta,
    espacio,
    tipo="Espacio",
    qr_habilitado=1,
):
    crear_tabla_espacios()

    centro = normalizar_texto(centro)
    edificio = normalizar_texto(edificio)
    planta = normalizar_texto(planta)
    espacio = normalizar_texto(espacio)
    tipo = normalizar_texto(tipo) or "Espacio"
    qr_habilitado = 1 if qr_habilitado else 0

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
                activo,
                qr_habilitado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (
            centro,
            edificio,
            planta,
            espacio,
            tipo,
            1,
            qr_habilitado
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
                activo = 1,
                qr_habilitado = ?
            WHERE id = ?
        """), (
            tipo,
            qr_habilitado,
            id_espacio
        ))

    conn.commit()
    conn.close()

    asegurar_codigos_espacios()
    return True


def actualizar_espacio(
    id_espacio,
    centro,
    edificio,
    planta,
    espacio,
    tipo,
    qr_habilitado=None,
):
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
        if qr_habilitado is None:
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
        else:
            qr_habilitado = 1 if qr_habilitado else 0

            cur.execute(_sql("""
                UPDATE espacios
                SET centro = ?,
                    edificio = ?,
                    planta = ?,
                    espacio = ?,
                    tipo = ?,
                    qr_habilitado = ?
                WHERE id = ?
            """), (
                centro,
                edificio,
                planta,
                espacio,
                tipo,
                qr_habilitado,
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

    # Añadir plantas creadas desde Configuración aunque aún no tengan espacios.
    for _id, centro_cfg, edificio_cfg, planta_cfg, visible_cfg in obtener_plantas_config():
        if not bool(visible_cfg):
            continue

        centro_cfg = normalizar_texto(centro_cfg)
        edificio_cfg = normalizar_texto(edificio_cfg)
        planta_cfg = normalizar_texto(planta_cfg)

        if not centro_cfg or not edificio_cfg or not planta_cfg:
            continue

        arbol.setdefault(centro_cfg, {})
        arbol[centro_cfg].setdefault(edificio_cfg, {})
        arbol[centro_cfg][edificio_cfg].setdefault(
            planta_cfg,
            [],
        )

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

    try:
        cur.execute(_sql("""
            SELECT DISTINCT edificio
            FROM espacios
            WHERE activo = 1
              AND centro = ?
              AND edificio IS NOT NULL
              AND edificio <> ''
            ORDER BY edificio
        """), (centro,))

        datos = [
            fila[0]
            for fila in cur.fetchall()
            if fila and fila[0]
        ]

    finally:
        conn.close()

    # Conserva edificios base aunque todavía no tengan espacios creados.
    for edificio_base in PLANTAS_BASE.get(centro, {}).keys():
        if edificio_base not in datos:
            datos.append(edificio_base)

    return datos



def obtener_plantas_espacios(centro, edificio):
    """
    Devuelve plantas/zonas visibles con una lectura ligera.

    No abre una conexión por cada planta y no recorre toda la tabla
    de espacios en Python.
    """
    crear_tabla_espacios()
    crear_tabla_plantas_config()

    plantas = []

    # Leer de una vez toda la configuración de esta ubicación.
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT planta, visible
            FROM plantas_config
            WHERE centro = ?
              AND edificio = ?
            ORDER BY id
        """), (
            centro,
            edificio,
        ))

        config = {
            normalizar_texto(planta_db): bool(visible)
            for planta_db, visible in cur.fetchall()
            if normalizar_texto(planta_db)
        }

        # Base histórica, respetando la visibilidad leída arriba.
        for planta_base in PLANTAS_BASE.get(
            centro,
            {},
        ).get(
            edificio,
            [],
        ):
            if config.get(planta_base, True) and planta_base not in plantas:
                plantas.append(planta_base)

        # Plantas configuradas nuevas.
        for planta_cfg, visible_cfg in config.items():
            if visible_cfg and planta_cfg not in plantas:
                plantas.append(planta_cfg)

        # Espacios activos de esta ubicación, filtrados ya en SQL.
        cur.execute(_sql("""
            SELECT DISTINCT planta
            FROM espacios
            WHERE activo = 1
              AND centro = ?
              AND edificio = ?
              AND planta IS NOT NULL
              AND planta <> ''
            ORDER BY planta
        """), (
            centro,
            edificio,
        ))

        for fila in cur.fetchall():
            planta_txt = normalizar_texto(
                fila[0] if fila else ""
            )

            if not planta_txt:
                continue

            if not config.get(planta_txt, True):
                continue

            if planta_txt not in plantas:
                plantas.append(planta_txt)

        return plantas

    finally:
        conn.close()



def obtener_espacios_por_planta(centro, edificio, planta):
    """
    Devuelve solo los espacios de la ubicación solicitada.
    """
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    try:
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
        """), (
            centro,
            edificio,
            planta,
        ))

        datos = []
        vistos = set()

        for espacio_db, tipo_db in cur.fetchall():
            espacio_txt = normalizar_texto(espacio_db)
            tipo_txt = normalizar_texto(tipo_db)

            clave = normalizar_comparacion(
                espacio_txt
            )

            if not espacio_txt or clave in vistos:
                continue

            vistos.add(clave)
            datos.append(
                (
                    espacio_txt,
                    tipo_txt,
                )
            )

        return datos

    finally:
        conn.close()



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
# QR DE ESPACIOS
# =====================================================

def actualizar_qr_habilitado_espacio(id_espacio, habilitado):
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE espacios
            SET qr_habilitado = ?
            WHERE id = ?
        """), (
            1 if habilitado else 0,
            id_espacio,
        ))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def habilitar_qr_todos_espacios_activos():
    """
    Activa QR en todos los espacios activos que todavía no lo tengan.
    """
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE espacios
            SET qr_habilitado = 1
            WHERE activo = 1
              AND COALESCE(qr_habilitado, 0) <> 1
        """))

        afectados = int(cur.rowcount or 0)
        conn.commit()
        return True, afectados

    except Exception:
        conn.rollback()
        return False, 0

    finally:
        conn.close()


def qr_habilitado_espacio(id_espacio):
    crear_tabla_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT qr_habilitado
        FROM espacios
        WHERE id = ?
        LIMIT 1
    """), (id_espacio,))

    fila = cur.fetchone()
    conn.close()

    return bool(fila and int(fila[0] or 0) == 1)


def obtener_espacios_para_qr():
    crear_tabla_espacios()
    asegurar_codigos_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT
            codigo,
            centro,
            edificio,
            planta,
            espacio,
            tipo
        FROM espacios
        WHERE activo = 1
          AND qr_habilitado = 1
          AND codigo IS NOT NULL
          AND codigo <> ''
        ORDER BY centro, edificio, planta, espacio
    """))

    datos = cur.fetchall()
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

def obtener_aulas_para_qr():
    """
    Alias de compatibilidad.
    Ahora devuelve todos los espacios con QR habilitado,
    no solo los de tipo Aula.
    """
    return obtener_espacios_para_qr()


def obtener_espacio_por_codigo(codigo):
    crear_tabla_espacios()
    asegurar_codigos_espacios()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, codigo, centro, edificio, planta, espacio, tipo, activo
        FROM espacios
        WHERE codigo = ?
        LIMIT 1
    """), (codigo,))

    fila = cur.fetchone()

    conn.close()
    return fila


def buscar_espacios_texto(texto, limite=30):
    crear_tabla_espacios()
    asegurar_codigos_espacios()

    texto = str(texto or "").strip().lower()

    if not texto:
        return []

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT
            id,
            codigo,
            centro,
            edificio,
            planta,
            espacio,
            tipo
        FROM espacios
        WHERE activo = 1
        ORDER BY espacio, centro, edificio, planta
    """))

    filas = cur.fetchall()
    conn.close()

    resultados = []

    for fila in filas:
        (
            id_espacio,
            codigo,
            centro,
            edificio,
            planta,
            espacio,
            tipo,
        ) = fila

        codigo_txt = str(codigo or "").strip()
        centro_txt = str(centro or "").strip()
        edificio_txt = str(edificio or "").strip()
        planta_txt = str(planta or "").strip()
        espacio_txt = str(espacio or "").strip()
        tipo_txt = str(tipo or "").strip()

        texto_busqueda = " ".join([
            codigo_txt,
            centro_txt,
            edificio_txt,
            planta_txt,
            espacio_txt,
            tipo_txt,
        ]).lower()

        if texto not in texto_busqueda:
            continue

        resultados.append({
            "id": id_espacio,
            "codigo": codigo_txt,
            "centro": centro_txt,
            "edificio": edificio_txt,
            "planta": planta_txt,
            "espacio": espacio_txt,
            "tipo": tipo_txt,
            "etiqueta": (
                f"{espacio_txt} · "
                f"{centro_txt} · "
                f"{edificio_txt} · "
                f"{planta_txt}"
            ),
        })

        if len(resultados) >= limite:
            break

    return resultados


