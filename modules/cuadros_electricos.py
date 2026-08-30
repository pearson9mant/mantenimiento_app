from datetime import datetime
import json
import re

from database.db import conectar, _sql, _es_postgres
from modules.ordenes import (
    crear_orden,
    guardar_foto_ot,
    obtener_siguiente_numero_ot,
)


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


    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cuadros_electricos_revisiones (
            id {id_sql},
            numero_ot TEXT,
            cuadro_id INTEGER,
            fecha TEXT,
            operario TEXT,
            comprobaciones TEXT,
            observaciones TEXT,
            completada INTEGER DEFAULT 0,
            incidencias TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
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

    try:
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_cuadros_revision_numero_ot
            ON cuadros_electricos_revisiones (numero_ot)
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



# ============================================================
# PREVENTIVO DE CUADROS ELÉCTRICOS
# ============================================================

COMPROBACIONES_PREVENTIVO_CUADRO = [
    "Accesibilidad y ausencia de obstáculos",
    "Puerta, cierre y envolvente en buen estado",
    "Limpieza general y ausencia de suciedad anormal",
    "Identificación y señalización legibles",
    "Tapas, protecciones y obturadores correctamente colocados",
    "Sin signos visibles de calentamiento, decoloración u olor anormal",
    "Sin mecanismos, cables o bornes con deterioro visible",
]


def _normalizar_cuadro_txt(valor):
    import unicodedata

    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)

    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )


def es_tarea_preventivo_cuadro(area, tarea):
    area_txt = _normalizar_cuadro_txt(area)
    tarea_txt = _normalizar_cuadro_txt(tarea)

    return (
        area_txt == "electricidad"
        and (
            "revisar cuadro electrico" in tarea_txt
            or "preventivo cuadro" in tarea_txt
        )
    )


def resolver_cuadro_preventivo(
    centro,
    edificio,
    planta,
    espacio,
    tarea="",
):
    """
    Resuelve el cuadro de una planificación.

    Prioridad:
    1) referencia incluida entre corchetes en la tarea:
       Revisar cuadro eléctrico [QG-P5]
    2) referencia citada literalmente en el texto de la tarea;
    3) si solo existe un cuadro activo en esa ubicación, lo utiliza.

    Si hay varios y no se identifica uno de forma inequívoca, devuelve None.
    """
    cuadros = obtener_cuadros_electricos(
        solo_activos=True
    )

    tarea_txt = str(tarea or "").strip()
    tarea_norm = _normalizar_cuadro_txt(
        tarea_txt
    )

    coincidencias_ubicacion = []

    for fila in cuadros:
        (
            id_cuadro,
            codigo,
            nombre,
            centro_f,
            edificio_f,
            planta_f,
            espacio_f,
            fabricante,
            modelo,
            observaciones,
            activo,
            fecha_creacion,
            fecha_actualizacion,
        ) = fila

        if (
            str(centro_f or "").strip() == str(centro or "").strip()
            and str(edificio_f or "").strip() == str(edificio or "").strip()
            and str(planta_f or "").strip() == str(planta or "").strip()
            and str(espacio_f or "").strip() == str(espacio or "").strip()
        ):
            coincidencias_ubicacion.append(
                fila
            )

    if not coincidencias_ubicacion:
        return None

    codigo_corchetes = ""

    match = re.search(
        r"\[([^\]]+)\]",
        tarea_txt,
    )

    if match:
        codigo_corchetes = str(
            match.group(1) or ""
        ).strip()

    if codigo_corchetes:
        codigo_norm = _normalizar_cuadro_txt(
            codigo_corchetes
        )

        for fila in coincidencias_ubicacion:
            if _normalizar_cuadro_txt(
                fila[1]
            ) == codigo_norm:
                return fila

    for fila in coincidencias_ubicacion:
        codigo_norm = _normalizar_cuadro_txt(
            fila[1]
        )

        if (
            codigo_norm
            and codigo_norm in tarea_norm
        ):
            return fila

    if len(coincidencias_ubicacion) == 1:
        return coincidencias_ubicacion[0]

    return None


def crear_revision_preventiva_cuadro(
    numero_ot,
    cuadro_id,
    operario="",
    observaciones="",
):
    asegurar_tablas_cuadros_electricos()

    numero_ot = str(
        numero_ot or ""
    ).strip()

    if not numero_ot:
        return False

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id
            FROM cuadros_electricos_revisiones
            WHERE numero_ot = ?
            LIMIT 1
        """), (
            numero_ot,
        ))

        existente = cur.fetchone()

        if existente:
            return True

        ahora = _ahora_str()

        comprobaciones = json.dumps(
            {
                punto: ""
                for punto in COMPROBACIONES_PREVENTIVO_CUADRO
            },
            ensure_ascii=False,
        )

        cur.execute(_sql("""
            INSERT INTO cuadros_electricos_revisiones
            (
                numero_ot,
                cuadro_id,
                fecha,
                operario,
                comprobaciones,
                observaciones,
                completada,
                incidencias,
                fecha_creacion,
                fecha_actualizacion
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        """), (
            numero_ot,
            int(cuadro_id),
            datetime.now().strftime("%Y-%m-%d"),
            operario,
            comprobaciones,
            observaciones,
            "[]",
            ahora,
            ahora,
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def obtener_revision_preventiva_cuadro(numero_ot):
    asegurar_tablas_cuadros_electricos()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                r.id,
                r.numero_ot,
                r.cuadro_id,
                r.fecha,
                r.operario,
                r.comprobaciones,
                r.observaciones,
                r.completada,
                r.incidencias,
                c.codigo,
                c.nombre,
                c.centro,
                c.edificio,
                c.planta,
                c.espacio
            FROM cuadros_electricos_revisiones r
            JOIN cuadros_electricos c
              ON c.id = r.cuadro_id
            WHERE r.numero_ot = ?
            LIMIT 1
        """), (
            numero_ot,
        ))

        fila = cur.fetchone()

        if not fila:
            return None

        (
            revision_id,
            numero_ot_f,
            cuadro_id,
            fecha,
            operario,
            comprobaciones_json,
            observaciones,
            completada,
            incidencias_json,
            codigo,
            nombre,
            centro,
            edificio,
            planta,
            espacio,
        ) = fila

        try:
            comprobaciones_raw = json.loads(
                comprobaciones_json or "{}"
            )
        except Exception:
            comprobaciones_raw = {}

        comprobaciones = {}

        for punto in COMPROBACIONES_PREVENTIVO_CUADRO:
            valor = comprobaciones_raw.get(
                punto,
                "",
            )

            if valor is True:
                valor = "correcto"
            elif valor is False:
                valor = ""
            else:
                valor = str(
                    valor or ""
                ).strip().lower()

            if valor not in [
                "",
                "correcto",
                "anomalia",
                "no_aplica",
            ]:
                valor = ""

            comprobaciones[punto] = valor

        try:
            incidencias = json.loads(
                incidencias_json or "[]"
            )
        except Exception:
            incidencias = []

        return {
            "id": int(revision_id),
            "numero_ot": numero_ot_f,
            "cuadro_id": int(cuadro_id),
            "fecha": fecha,
            "operario": operario,
            "comprobaciones": comprobaciones,
            "observaciones": observaciones or "",
            "completada": bool(completada),
            "incidencias": list(incidencias or []),
            "codigo": codigo or "",
            "nombre": nombre or "",
            "centro": centro or "",
            "edificio": edificio or "",
            "planta": planta or "",
            "espacio": espacio or "",
        }

    finally:
        conn.close()


def guardar_comprobaciones_revision_cuadro(
    numero_ot,
    comprobaciones,
    observaciones="",
):
    asegurar_tablas_cuadros_electricos()

    mapa = {}

    for punto in COMPROBACIONES_PREVENTIVO_CUADRO:
        valor = str(
            comprobaciones.get(
                punto,
                "",
            )
            or ""
        ).strip().lower()

        if valor not in [
            "",
            "correcto",
            "anomalia",
            "no_aplica",
        ]:
            valor = ""

        mapa[punto] = valor

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE cuadros_electricos_revisiones
            SET comprobaciones = ?,
                observaciones = ?,
                fecha_actualizacion = ?
            WHERE numero_ot = ?
        """), (
            json.dumps(
                mapa,
                ensure_ascii=False,
            ),
            str(observaciones or "").strip(),
            _ahora_str(),
            numero_ot,
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def comprobaciones_revision_cuadro_completas(numero_ot):
    revision = obtener_revision_preventiva_cuadro(
        numero_ot
    )

    if not revision:
        return False

    comprobaciones = revision.get(
        "comprobaciones",
        {},
    )

    return all(
        str(
            comprobaciones.get(
                punto,
                "",
            )
            or ""
        ).strip().lower()
        in [
            "correcto",
            "anomalia",
            "no_aplica",
        ]
        for punto in COMPROBACIONES_PREVENTIVO_CUADRO
    )


def obtener_puntos_anomalia_revision_cuadro(numero_ot):
    revision = obtener_revision_preventiva_cuadro(
        numero_ot
    )

    if not revision:
        return []

    comprobaciones = revision.get(
        "comprobaciones",
        {},
    )

    return [
        punto
        for punto in COMPROBACIONES_PREVENTIVO_CUADRO
        if str(
            comprobaciones.get(
                punto,
                "",
            )
            or ""
        ).strip().lower() == "anomalia"
    ]


def marcar_revision_cuadro_completada(
    numero_ot,
    completada=True,
):
    if (
        completada
        and not comprobaciones_revision_cuadro_completas(
            numero_ot
        )
    ):
        return False

    if completada:
        revision = obtener_revision_preventiva_cuadro(
            numero_ot
        )

        if not revision:
            return False

        anomalias = obtener_puntos_anomalia_revision_cuadro(
            numero_ot
        )

        incidencias = list(
            revision.get(
                "incidencias",
                [],
            )
            or []
        )

        if anomalias and not incidencias:
            return False

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE cuadros_electricos_revisiones
            SET completada = ?,
                fecha_actualizacion = ?
            WHERE numero_ot = ?
        """), (
            1 if completada else 0,
            _ahora_str(),
            numero_ot,
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def revision_cuadro_lista_para_cerrar(numero_ot):
    revision = obtener_revision_preventiva_cuadro(
        numero_ot
    )

    return bool(
        revision
        and revision.get("completada")
        and comprobaciones_revision_cuadro_completas(
            numero_ot
        )
    )


def _limpiar_nombre_foto_cuadro(texto):
    texto = str(texto or "")

    for caracter in [
        "/",
        "\\",
        ":",
        "*",
        "?",
        '"',
        "<",
        ">",
        "|",
    ]:
        texto = texto.replace(
            caracter,
            "_",
        )

    return texto.replace(
        " ",
        "_",
    )


def registrar_incidencia_revision_cuadro(
    numero_ot_preventiva,
    numero_inc,
):
    revision = obtener_revision_preventiva_cuadro(
        numero_ot_preventiva
    )

    if not revision:
        return False

    incidencias = list(
        revision.get(
            "incidencias",
            [],
        )
        or []
    )

    if numero_inc not in incidencias:
        incidencias.append(
            numero_inc
        )

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE cuadros_electricos_revisiones
            SET incidencias = ?,
                fecha_actualizacion = ?
            WHERE numero_ot = ?
        """), (
            json.dumps(
                incidencias,
                ensure_ascii=False,
            ),
            _ahora_str(),
            numero_ot_preventiva,
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def crear_incidencia_desde_revision_cuadro(
    numero_ot_preventiva,
    descripcion,
    fotos=None,
):
    revision = obtener_revision_preventiva_cuadro(
        numero_ot_preventiva
    )

    if not revision:
        return (
            False,
            "No se encuentra la revisión preventiva del cuadro.",
            "",
        )

    descripcion_limpia = str(
        descripcion or ""
    ).strip()

    if not descripcion_limpia:
        return (
            False,
            "Describe brevemente la anomalía detectada.",
            "",
        )

    fotos = list(
        fotos or []
    )

    if len(fotos) > 5:
        return (
            False,
            "Puedes añadir un máximo de 5 fotografías.",
            "",
        )

    fotos_validas = []

    for foto in fotos:
        tamano = int(
            getattr(
                foto,
                "size",
                0,
            )
            or 0
        )

        if tamano > 5 * 1024 * 1024:
            return (
                False,
                (
                    f"La fotografía "
                    f"{getattr(foto, 'name', 'seleccionada')} "
                    "supera 5 MB."
                ),
                "",
            )

        fotos_validas.append(
            (
                str(
                    getattr(
                        foto,
                        "name",
                        "foto.jpg",
                    )
                    or "foto.jpg"
                ),
                foto.getvalue(),
            )
        )

    numero_inc = obtener_siguiente_numero_ot(
        revision["centro"],
        "INC",
    )

    fecha_origen = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    observaciones_origen = (
        "Incidencia detectada durante preventivo de cuadro eléctrico.\n"
        f"Cuadro: {revision['codigo']} · {revision['nombre']}\n"
        f"OT preventiva origen: {numero_ot_preventiva}\n"
        f"Ubicación: {revision['planta']} · {revision['espacio']}"
    )

    datos_orden = (
        numero_inc,
        descripcion_limpia,
        "Abierta",
        revision["centro"],
        revision["edificio"],
        revision["espacio"],
        "Electricidad",
        "Media",
        revision["operario"],
        "PREVENTIVO",
        "Mantenimiento preventivo",
        fecha_origen,
        "postgres_fotos" if fotos_validas else "",
        "Operarios",
        "Interna",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        0,
        0,
        observaciones_origen,
        revision["planta"],
    )

    try:
        numero_creado = crear_orden(
            datos_orden
        ) or numero_inc
    except Exception as error:
        return (
            False,
            f"No se ha podido crear la incidencia: {error}",
            "",
        )

    error_fotos = ""

    if fotos_validas:
        try:
            for indice, (
                nombre_original,
                contenido,
            ) in enumerate(
                fotos_validas,
                start=1,
            ):
                nombre_foto = _limpiar_nombre_foto_cuadro(
                    f"{numero_creado}_{indice}_{nombre_original}"
                )

                guardar_foto_ot(
                    numero_ot=numero_creado,
                    nombre_foto=nombre_foto,
                    foto_data=contenido,
                )

        except Exception as error:
            error_fotos = str(
                error
            )

    registrar_incidencia_revision_cuadro(
        numero_ot_preventiva,
        numero_creado,
    )

    if error_fotos:
        mensaje = (
            f"Incidencia {numero_creado} creada, "
            "pero alguna fotografía no se pudo guardar."
        )
    else:
        mensaje = (
            f"Incidencia {numero_creado} creada correctamente."
        )

    return (
        True,
        mensaje,
        numero_creado,
    )
