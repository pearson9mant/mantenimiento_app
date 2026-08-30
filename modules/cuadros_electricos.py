from datetime import datetime

from database.db import conectar, _sql, _es_postgres


def _ahora_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def asegurar_tablas_cuadros_electricos():
    conn = conectar()
    cur = conn.cursor()

    if _es_postgres():
        id_sql = "SERIAL PRIMARY KEY"
    else:
        id_sql = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cuadros_electricos (
            id {id_sql},
            codigo TEXT,
            nombre TEXT,
            centro TEXT,
            edificio TEXT,
            planta TEXT,
            espacio TEXT,
            fabricante TEXT,
            modelo TEXT,
            observaciones TEXT,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
        )
    """)

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cuadros_electricos_mecanismos (
            id {id_sql},
            cuadro_id INTEGER,
            mecanismo TEXT,
            caracteristicas TEXT,
            cantidad INTEGER DEFAULT 1,
            circuito TEXT,
            fabricante TEXT,
            modelo TEXT,
            observaciones TEXT,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT,
            identificador TEXT
        )
    """)

    conn.commit()

    # Migración aditiva: cuadros ya creados antes de incorporar
    # la identificación individual Q1, Q2, ID1, etc.
    try:
        cur.execute("""
            ALTER TABLE cuadros_electricos_mecanismos
            ADD COLUMN identificador TEXT
        """)
        conn.commit()
    except Exception:
        conn.rollback()

    try:
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_cuadros_electricos_codigo
            ON cuadros_electricos (codigo)
        """)
        conn.commit()
    except Exception:
        conn.rollback()

    try:
        cur.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_cuadros_mecanismos_cuadro
            ON cuadros_electricos_mecanismos (cuadro_id, activo)
        """)
        conn.commit()
    except Exception:
        conn.rollback()

    conn.close()


def crear_cuadro_electrico(
    codigo,
    nombre,
    centro,
    edificio,
    planta,
    espacio,
    fabricante="",
    modelo="",
    observaciones="",
):
    asegurar_tablas_cuadros_electricos()

    codigo = str(codigo or "").strip()
    nombre = str(nombre or "").strip()

    if not codigo:
        return False, "Indica una referencia o código del cuadro."

    if not nombre:
        return False, "Indica el nombre del cuadro."

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT COUNT(*)
            FROM cuadros_electricos
            WHERE LOWER(TRIM(codigo)) = LOWER(TRIM(?))
        """), (codigo,))

        if int(cur.fetchone()[0] or 0) > 0:
            return False, "Ya existe un cuadro con esa referencia."

        ahora = _ahora_str()

        cur.execute(_sql("""
            INSERT INTO cuadros_electricos
            (
                codigo,
                nombre,
                centro,
                edificio,
                planta,
                espacio,
                fabricante,
                modelo,
                observaciones,
                activo,
                fecha_creacion,
                fecha_actualizacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """), (
            codigo,
            nombre,
            centro,
            edificio,
            planta,
            espacio,
            fabricante,
            modelo,
            observaciones,
            ahora,
            ahora,
        ))

        conn.commit()
        return True, f"Cuadro creado: {codigo} · {nombre}"

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo crear el cuadro: {e}"

    finally:
        conn.close()


def obtener_cuadros_electricos(solo_activos=True):
    asegurar_tablas_cuadros_electricos()

    conn = conectar()
    cur = conn.cursor()

    sql = """
        SELECT
            id,
            codigo,
            nombre,
            centro,
            edificio,
            planta,
            espacio,
            fabricante,
            modelo,
            observaciones,
            activo,
            fecha_creacion,
            fecha_actualizacion
        FROM cuadros_electricos
    """

    if solo_activos:
        sql += " WHERE activo = 1"

    sql += """
        ORDER BY
            centro,
            edificio,
            planta,
            espacio,
            codigo
    """

    cur.execute(sql)
    datos = cur.fetchall()
    conn.close()
    return datos


def actualizar_cuadro_electrico(
    id_cuadro,
    codigo,
    nombre,
    centro,
    edificio,
    planta,
    espacio,
    fabricante="",
    modelo="",
    observaciones="",
):
    asegurar_tablas_cuadros_electricos()

    codigo = str(codigo or "").strip()
    nombre = str(nombre or "").strip()

    if not codigo:
        return False, "Indica una referencia o código."

    if not nombre:
        return False, "Indica el nombre del cuadro."

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT COUNT(*)
            FROM cuadros_electricos
            WHERE id <> ?
              AND LOWER(TRIM(codigo)) = LOWER(TRIM(?))
        """), (
            int(id_cuadro),
            codigo,
        ))

        if int(cur.fetchone()[0] or 0) > 0:
            return False, "Ya existe otro cuadro con esa referencia."

        cur.execute(_sql("""
            UPDATE cuadros_electricos
            SET codigo = ?,
                nombre = ?,
                centro = ?,
                edificio = ?,
                planta = ?,
                espacio = ?,
                fabricante = ?,
                modelo = ?,
                observaciones = ?,
                fecha_actualizacion = ?
            WHERE id = ?
        """), (
            codigo,
            nombre,
            centro,
            edificio,
            planta,
            espacio,
            fabricante,
            modelo,
            observaciones,
            _ahora_str(),
            int(id_cuadro),
        ))

        conn.commit()
        return True, "Cuadro actualizado correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo actualizar el cuadro: {e}"

    finally:
        conn.close()


def activar_desactivar_cuadro(id_cuadro, activo):
    asegurar_tablas_cuadros_electricos()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE cuadros_electricos
            SET activo = ?,
                fecha_actualizacion = ?
            WHERE id = ?
        """), (
            1 if activo else 0,
            _ahora_str(),
            int(id_cuadro),
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def obtener_mecanismos_cuadro(id_cuadro, solo_activos=True):
    asegurar_tablas_cuadros_electricos()

    conn = conectar()
    cur = conn.cursor()

    sql = """
        SELECT
            id,
            cuadro_id,
            mecanismo,
            caracteristicas,
            cantidad,
            circuito,
            fabricante,
            modelo,
            observaciones,
            activo,
            fecha_creacion,
            fecha_actualizacion,
            identificador
        FROM cuadros_electricos_mecanismos
        WHERE cuadro_id = ?
    """

    params = [int(id_cuadro)]

    if solo_activos:
        sql += " AND activo = 1"

    sql += """
        ORDER BY
            mecanismo,
            caracteristicas,
            circuito,
            id
    """

    cur.execute(_sql(sql), tuple(params))
    datos = cur.fetchall()
    conn.close()
    return datos


def crear_mecanismo_cuadro(
    cuadro_id,
    mecanismo,
    caracteristicas="",
    cantidad=1,
    circuito="",
    fabricante="",
    modelo="",
    observaciones="",
    identificador="",
):
    asegurar_tablas_cuadros_electricos()

    mecanismo = str(mecanismo or "").strip()
    caracteristicas = str(caracteristicas or "").strip()
    circuito = str(circuito or "").strip()
    identificador = str(identificador or "").strip()

    if not mecanismo:
        return False, "Indica el mecanismo."

    try:
        cantidad = int(cantidad or 0)
    except Exception:
        cantidad = 0

    if cantidad <= 0:
        return False, "La cantidad debe ser mayor que 0."

    conn = conectar()
    cur = conn.cursor()

    try:
        if identificador:
            cur.execute(_sql("""
                SELECT COUNT(*)
                FROM cuadros_electricos_mecanismos
                WHERE cuadro_id = ?
                  AND activo = 1
                  AND LOWER(TRIM(COALESCE(identificador, ''))) =
                      LOWER(TRIM(?))
            """), (
                int(cuadro_id),
                identificador,
            ))

            if int(cur.fetchone()[0] or 0) > 0:
                return False, (
                    f"Ya existe el identificador {identificador} "
                    "en este cuadro."
                )

        cur.execute(_sql("""
            SELECT COUNT(*)
            FROM cuadros_electricos_mecanismos
            WHERE cuadro_id = ?
              AND activo = 1
              AND LOWER(TRIM(mecanismo)) = LOWER(TRIM(?))
              AND LOWER(TRIM(COALESCE(caracteristicas, ''))) =
                  LOWER(TRIM(COALESCE(?, '')))
              AND LOWER(TRIM(COALESCE(circuito, ''))) =
                  LOWER(TRIM(COALESCE(?, '')))
        """), (
            int(cuadro_id),
            mecanismo,
            caracteristicas,
            circuito,
        ))

        if int(cur.fetchone()[0] or 0) > 0:
            return False, (
                "Ya existe un mecanismo igual con esas características "
                "y ese circuito."
            )

        ahora = _ahora_str()

        cur.execute(_sql("""
            INSERT INTO cuadros_electricos_mecanismos
            (
                cuadro_id,
                mecanismo,
                caracteristicas,
                cantidad,
                circuito,
                fabricante,
                modelo,
                observaciones,
                activo,
                fecha_creacion,
                fecha_actualizacion,
                identificador
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """), (
            int(cuadro_id),
            mecanismo,
            caracteristicas,
            cantidad,
            circuito,
            fabricante,
            modelo,
            observaciones,
            ahora,
            ahora,
            identificador,
        ))

        conn.commit()
        return True, "Mecanismo añadido al inventario del cuadro."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo añadir el mecanismo: {e}"

    finally:
        conn.close()


def actualizar_mecanismo_cuadro(
    id_mecanismo,
    mecanismo,
    caracteristicas,
    cantidad,
    circuito,
    fabricante="",
    modelo="",
    observaciones="",
    identificador="",
):
    asegurar_tablas_cuadros_electricos()

    mecanismo = str(mecanismo or "").strip()
    identificador = str(identificador or "").strip()

    if not mecanismo:
        return False, "Indica el mecanismo."

    try:
        cantidad = int(cantidad or 0)
    except Exception:
        cantidad = 0

    if cantidad <= 0:
        return False, "La cantidad debe ser mayor que 0."

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT cuadro_id
            FROM cuadros_electricos_mecanismos
            WHERE id = ?
        """), (
            int(id_mecanismo),
        ))

        fila_cuadro = cur.fetchone()

        if not fila_cuadro:
            return False, "No se encuentra el mecanismo."

        cuadro_id = int(fila_cuadro[0])

        if identificador:
            cur.execute(_sql("""
                SELECT COUNT(*)
                FROM cuadros_electricos_mecanismos
                WHERE cuadro_id = ?
                  AND id <> ?
                  AND activo = 1
                  AND LOWER(TRIM(COALESCE(identificador, ''))) =
                      LOWER(TRIM(?))
            """), (
                cuadro_id,
                int(id_mecanismo),
                identificador,
            ))

            if int(cur.fetchone()[0] or 0) > 0:
                return False, (
                    f"Ya existe el identificador {identificador} "
                    "en este cuadro."
                )

        cur.execute(_sql("""
            UPDATE cuadros_electricos_mecanismos
            SET mecanismo = ?,
                caracteristicas = ?,
                cantidad = ?,
                circuito = ?,
                fabricante = ?,
                modelo = ?,
                observaciones = ?,
                fecha_actualizacion = ?,
                identificador = ?
            WHERE id = ?
        """), (
            mecanismo,
            caracteristicas,
            cantidad,
            circuito,
            fabricante,
            modelo,
            observaciones,
            _ahora_str(),
            identificador,
            int(id_mecanismo),
        ))

        conn.commit()
        return True, "Mecanismo actualizado."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo actualizar el mecanismo: {e}"

    finally:
        conn.close()


def eliminar_mecanismo_cuadro(id_mecanismo):
    asegurar_tablas_cuadros_electricos()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE cuadros_electricos_mecanismos
            SET activo = 0,
                fecha_actualizacion = ?
            WHERE id = ?
        """), (
            _ahora_str(),
            int(id_mecanismo),
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()
