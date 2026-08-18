from datetime import datetime

from database.db import conectar, _sql
from modules.ordenes import guardar_foto_ot
from modules.inventario import (
    obtener_material_por_codigo,
    registrar_movimiento_inventario,
)


ESTADOS_PEDIDO = [
    "Pendiente",
    "Preparado",
    "Entregado",
    "Sin stock",
    "Cancelado",
]

_ESTRUCTURA_PEDIDOS_ASEGURADA = False


def _log_pedidos_warning(contexto, error):
    try:
        print(
            f"[PEDIDOS MATERIAL WARNING] {contexto}: "
            f"{type(error).__name__}: {error}"
        )
    except Exception:
        pass


def _es_postgres_conn(conn):
    modulo = conn.__class__.__module__.lower()
    return "psycopg2" in modulo or "postgres" in modulo


def _id_sql(conn):
    if _es_postgres_conn(conn):
        return "SERIAL PRIMARY KEY"
    return "INTEGER PRIMARY KEY AUTOINCREMENT"


def _column_exists(cur, tabla, columna):
    try:
        if _es_postgres_conn(cur.connection):
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                  AND column_name = %s
                """,
                (tabla, columna),
            )
            return cur.fetchone() is not None

        cur.execute(f"PRAGMA table_info({tabla})")
        return columna in [
            fila[1]
            for fila in cur.fetchall()
        ]

    except Exception as e:
        _log_pedidos_warning(
            f"Comprobando columna {tabla}.{columna}",
            e,
        )
        return False


def _add_column(cur, tabla, columna, tipo):
    if _column_exists(
        cur,
        tabla,
        columna,
    ):
        return True

    try:
        cur.execute(
            f"""
            ALTER TABLE {tabla}
            ADD COLUMN {columna} {tipo}
            """
        )
        return True

    except Exception as e:
        _log_pedidos_warning(
            f"Añadiendo columna {tabla}.{columna}",
            e,
        )

        try:
            cur.connection.rollback()
        except Exception:
            pass

        return False


def crear_tabla_pedidos_material():
    """
    Asegura la estructura una sola vez por proceso.

    Mantiene:
    - cabecera histórica pedidos_material;
    - líneas múltiples pedidos_material_lineas;
    - compatibilidad con pedidos antiguos.
    """
    global _ESTRUCTURA_PEDIDOS_ASEGURADA

    if _ESTRUCTURA_PEDIDOS_ASEGURADA:
        return

    conn = conectar()
    cur = conn.cursor()
    id_sql = _id_sql(conn)

    try:
        cur.execute(_sql(f"""
            CREATE TABLE IF NOT EXISTS pedidos_material (
                id {id_sql},
                numero_pedido TEXT,
                fecha TEXT,
                operario TEXT,
                centro TEXT,
                edificio TEXT,
                prioridad TEXT,
                estado TEXT,
                observaciones TEXT,
                link_material TEXT,
                foto TEXT,
                fecha_preparado TEXT,
                fecha_entrega TEXT
            )
        """))

        conn.commit()

        columnas_cabecera = [
            ("numero_pedido", "TEXT"),
            ("fecha", "TEXT"),
            ("operario", "TEXT"),
            ("centro", "TEXT"),
            ("edificio", "TEXT"),
            ("material", "TEXT"),
            ("cantidad", "REAL"),
            ("prioridad", "TEXT"),
            ("estado", "TEXT"),
            ("observaciones", "TEXT"),
            ("link_material", "TEXT"),
            ("foto", "TEXT"),
            ("fecha_preparado", "TEXT"),
            ("fecha_entrega", "TEXT"),
        ]

        for columna, tipo in columnas_cabecera:
            _add_column(
                cur,
                "pedidos_material",
                columna,
                tipo,
            )

        cur.execute(_sql(f"""
            CREATE TABLE IF NOT EXISTS pedidos_material_lineas (
                id {id_sql},
                pedido_id INTEGER,
                codigo_material TEXT,
                material TEXT,
                cantidad REAL,
                estado TEXT,
                observaciones TEXT,
                link_material TEXT,
                fecha_preparado TEXT,
                fecha_entrega TEXT,
                inventario_descontado INTEGER DEFAULT 0
            )
        """))

        conn.commit()

        columnas_lineas = [
            ("pedido_id", "INTEGER"),
            ("codigo_material", "TEXT"),
            ("material", "TEXT"),
            ("cantidad", "REAL"),
            ("estado", "TEXT"),
            ("observaciones", "TEXT"),
            ("link_material", "TEXT"),
            ("fecha_preparado", "TEXT"),
            ("fecha_entrega", "TEXT"),
            (
                "inventario_descontado",
                "INTEGER DEFAULT 0",
            ),
        ]

        for columna, tipo in columnas_lineas:
            _add_column(
                cur,
                "pedidos_material_lineas",
                columna,
                tipo,
            )

        # Índices del flujo diario.
        indices = [
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_pedidos_operario "
                "ON pedidos_material(operario)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_pedidos_estado "
                "ON pedidos_material(estado)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_pedidos_fecha "
                "ON pedidos_material(fecha)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_ped_lineas_pedido "
                "ON pedidos_material_lineas(pedido_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_ped_lineas_codigo "
                "ON pedidos_material_lineas(codigo_material)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS "
                "idx_ped_lineas_estado "
                "ON pedidos_material_lineas(estado)"
            ),
        ]

        for sql_indice in indices:
            try:
                cur.execute(sql_indice)
            except Exception as e:
                _log_pedidos_warning(
                    f"Creando índice: {sql_indice}",
                    e,
                )

        conn.commit()
        _ESTRUCTURA_PEDIDOS_ASEGURADA = True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    migrar_pedidos_antiguos_a_lineas()


def formatear_numero_pedido(id_pedido):
    return f"PED-MAT-{int(id_pedido):04d}"


def migrar_pedidos_antiguos_a_lineas():
    """
    Migra pedidos antiguos de una sola línea sin borrar datos.
    """
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                id,
                material,
                cantidad,
                estado,
                observaciones,
                link_material
            FROM pedidos_material
            WHERE material IS NOT NULL
              AND material <> ''
        """))

        pedidos = cur.fetchall()

        for p in pedidos:
            pedido_id = p[0]
            material = p[1]
            cantidad = p[2]
            estado = p[3] or "Pendiente"
            observaciones = p[4] or ""
            link_material = p[5] or ""

            cur.execute(_sql("""
                SELECT COUNT(*)
                FROM pedidos_material_lineas
                WHERE pedido_id = ?
            """), (
                pedido_id,
            ))

            existe = int(
                cur.fetchone()[0] or 0
            )

            if existe == 0:
                cur.execute(_sql("""
                    INSERT INTO pedidos_material_lineas
                    (
                        pedido_id,
                        material,
                        cantidad,
                        estado,
                        observaciones,
                        link_material
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """), (
                    pedido_id,
                    material,
                    cantidad,
                    estado,
                    observaciones,
                    link_material,
                ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        _log_pedidos_warning(
            "Migrando pedidos antiguos",
            e,
        )

    finally:
        conn.close()


def crear_pedido_material_multiple(
    operario,
    centro,
    edificio="",
    prioridad="Media",
    observaciones="",
    lineas=None,
    foto="postgres_fotos",
):
    """
    Crea una cabecera con varias líneas.

    Cada línea puede ser:
    - material catalogado: codigo_material con valor;
    - material de compra: codigo_material vacío.
    """
    crear_tabla_pedidos_material()

    lineas = lineas or []

    lineas_validas = []

    for linea in lineas:
        material = str(
            linea.get(
                "material",
                "",
            )
            or ""
        ).strip()

        if not material:
            continue

        try:
            cantidad = float(
                linea.get(
                    "cantidad",
                    1,
                )
                or 1
            )
        except Exception:
            cantidad = 1.0

        if cantidad <= 0:
            continue

        lineas_validas.append({
            "codigo_material": str(
                linea.get(
                    "codigo_material",
                    "",
                )
                or ""
            ).strip(),
            "material": material,
            "cantidad": cantidad,
            "observaciones": str(
                linea.get(
                    "observaciones",
                    "",
                )
                or ""
            ).strip(),
            "link_material": str(
                linea.get(
                    "link_material",
                    "",
                )
                or ""
            ).strip(),
        })

    if not lineas_validas:
        return None

    conn = conectar()
    cur = conn.cursor()
    fecha = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )

    try:
        if _es_postgres_conn(conn):
            cur.execute(_sql("""
                INSERT INTO pedidos_material
                (
                    fecha,
                    operario,
                    centro,
                    edificio,
                    prioridad,
                    estado,
                    observaciones,
                    foto
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """), (
                fecha,
                operario,
                centro,
                edificio,
                prioridad,
                "Pendiente",
                observaciones,
                foto,
            ))

            fila = cur.fetchone()
            id_pedido = (
                fila[0]
                if fila
                else None
            )

        else:
            cur.execute(_sql("""
                INSERT INTO pedidos_material
                (
                    fecha,
                    operario,
                    centro,
                    edificio,
                    prioridad,
                    estado,
                    observaciones,
                    foto
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """), (
                fecha,
                operario,
                centro,
                edificio,
                prioridad,
                "Pendiente",
                observaciones,
                foto,
            ))

            id_pedido = cur.lastrowid

        if not id_pedido:
            conn.rollback()
            return None

        numero_pedido = formatear_numero_pedido(
            id_pedido
        )

        cur.execute(_sql("""
            UPDATE pedidos_material
            SET numero_pedido = ?
            WHERE id = ?
        """), (
            numero_pedido,
            id_pedido,
        ))

        for linea in lineas_validas:
            cur.execute(_sql("""
                INSERT INTO pedidos_material_lineas
                (
                    pedido_id,
                    codigo_material,
                    material,
                    cantidad,
                    estado,
                    observaciones,
                    link_material,
                    inventario_descontado
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """), (
                id_pedido,
                linea["codigo_material"],
                linea["material"],
                linea["cantidad"],
                "Pendiente",
                linea["observaciones"],
                linea["link_material"],
            ))

        conn.commit()
        return id_pedido

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def crear_pedido_material(
    operario,
    centro,
    material,
    cantidad,
    prioridad,
    observaciones="",
    link_material="",
    foto="postgres_fotos",
    estado=None,
    creado_por=None,
):
    """
    Compatibilidad con llamadas antiguas.

    Los parámetros estado y creado_por se aceptan para no romper
    interfaces históricas. El flujo nuevo siempre nace Pendiente.
    """
    observaciones_finales = str(
        observaciones or ""
    ).strip()

    if creado_por:
        texto_creado = (
            f"Creado por: {creado_por}"
        )

        if observaciones_finales:
            observaciones_finales += (
                f" | {texto_creado}"
            )
        else:
            observaciones_finales = (
                texto_creado
            )

    return crear_pedido_material_multiple(
        operario=operario,
        centro=centro,
        edificio="",
        prioridad=prioridad,
        observaciones=observaciones_finales,
        foto=foto,
        lineas=[
            {
                "codigo_material": "",
                "material": material,
                "cantidad": cantidad,
                "observaciones": observaciones,
                "link_material": link_material,
            }
        ],
    )


def obtener_numero_pedido(id_pedido):
    if not id_pedido:
        return ""

    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT numero_pedido
            FROM pedidos_material
            WHERE id = ?
        """), (
            id_pedido,
        ))

        fila = cur.fetchone()

        if fila and fila[0]:
            return fila[0]

        return formatear_numero_pedido(
            id_pedido
        )

    finally:
        conn.close()


def guardar_fotos_pedido_material(
    id_pedido,
    fotos,
):
    if not id_pedido or not fotos:
        return 0

    numero_pedido = obtener_numero_pedido(
        id_pedido
    )

    if not numero_pedido:
        return 0

    guardadas = 0

    for i, foto in enumerate(
        list(fotos)[:5],
        start=1,
    ):
        try:
            tamaño = getattr(
                foto,
                "size",
                0,
            )

            if tamaño and tamaño > 5 * 1024 * 1024:
                continue

            foto_bytes = foto.read()

            if len(foto_bytes) > 5 * 1024 * 1024:
                continue

            nombre_original = str(
                getattr(
                    foto,
                    "name",
                    f"foto_{i}.jpg",
                )
                or f"foto_{i}.jpg"
            )

            nombre_foto = (
                f"{numero_pedido}_"
                f"{i}_"
                f"{nombre_original}"
            )

            guardar_foto_ot(
                numero_ot=numero_pedido,
                nombre_foto=nombre_foto,
                foto_data=foto_bytes,
            )

            guardadas += 1

        except Exception as e:
            _log_pedidos_warning(
                f"Guardando foto de {numero_pedido}",
                e,
            )

    return guardadas


def obtener_lineas_pedido(id_pedido):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                id,
                pedido_id,
                codigo_material,
                material,
                cantidad,
                estado,
                observaciones,
                link_material,
                fecha_preparado,
                fecha_entrega,
                inventario_descontado
            FROM pedidos_material_lineas
            WHERE pedido_id = ?
            ORDER BY id ASC
        """), (
            id_pedido,
        ))

        return cur.fetchall()

    finally:
        conn.close()


def _resumen_lineas_por_pedido(ids_pedido):
    """
    Carga todas las líneas de los pedidos visibles en una sola consulta.
    Evita una consulta adicional por cada pedido.
    """
    ids = [
        int(x)
        for x in ids_pedido
        if x is not None
    ]

    if not ids:
        return {}

    conn = conectar()
    cur = conn.cursor()

    try:
        marcadores = ",".join(
            ["?"] * len(ids)
        )

        cur.execute(
            _sql(f"""
                SELECT
                    pedido_id,
                    material,
                    cantidad
                FROM pedidos_material_lineas
                WHERE pedido_id IN ({marcadores})
                ORDER BY pedido_id, id ASC
            """),
            tuple(ids),
        )

        mapa = {}

        for pedido_id, material, cantidad in cur.fetchall():
            mapa.setdefault(
                pedido_id,
                [],
            ).append(
                f"{material} x {cantidad}"
            )

        return {
            pedido_id: " | ".join(items)
            for pedido_id, items in mapa.items()
        }

    finally:
        conn.close()


def obtener_resumen_materiales_pedido(
    id_pedido,
):
    lineas = obtener_lineas_pedido(
        id_pedido
    )

    materiales = []

    for linea in lineas:
        materiales.append(
            f"{linea[3]} x {linea[4]}"
        )

    return " | ".join(
        materiales
    )


def obtener_pedidos_material(
    operario=None,
    solo_pendientes=False,
    limite=300,
):
    crear_tabla_pedidos_material()

    try:
        limite = int(limite)
    except Exception:
        limite = 300

    limite = max(
        1,
        min(
            limite,
            1000,
        ),
    )

    conn = conectar()
    cur = conn.cursor()

    query = """
        SELECT
            id,
            numero_pedido,
            fecha,
            operario,
            centro,
            prioridad,
            estado,
            observaciones,
            link_material,
            foto,
            fecha_preparado,
            fecha_entrega,
            edificio
        FROM pedidos_material
        WHERE 1=1
    """

    params = []

    if operario:
        query += " AND operario = ?"
        params.append(
            operario
        )

    if solo_pendientes:
        query += (
            " AND estado IN "
            "('Pendiente', 'Preparado', 'Sin stock')"
        )

    query += " ORDER BY id DESC LIMIT ?"
    params.append(
        limite
    )

    try:
        cur.execute(
            _sql(query),
            tuple(params),
        )

        pedidos = cur.fetchall()

    finally:
        conn.close()

    resumenes = _resumen_lineas_por_pedido(
        [
            p[0]
            for p in pedidos
        ]
    )

    resultado = []

    for p in pedidos:
        resultado.append((
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            resumenes.get(
                p[0],
                "",
            ),
            "",
            p[5],
            p[6],
            p[7],
            p[8],
            p[9],
            p[10],
            p[11],
        ))

    return resultado


def recalcular_estado_pedido(
    id_pedido,
):
    lineas = obtener_lineas_pedido(
        id_pedido
    )

    if not lineas:
        return

    estados = [
        str(
            linea[5]
            or "Pendiente"
        )
        for linea in lineas
    ]

    if all(
        estado == "Entregado"
        for estado in estados
    ):
        nuevo_estado = "Entregado"

    elif all(
        estado == "Cancelado"
        for estado in estados
    ):
        nuevo_estado = "Cancelado"

    elif any(
        estado == "Preparado"
        for estado in estados
    ):
        nuevo_estado = "Preparado"

    elif any(
        estado == "Sin stock"
        for estado in estados
    ):
        nuevo_estado = "Sin stock"

    else:
        nuevo_estado = "Pendiente"

    conn = conectar()
    cur = conn.cursor()

    try:
        ahora = datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        if nuevo_estado == "Preparado":
            cur.execute(_sql("""
                UPDATE pedidos_material
                SET estado = ?,
                    fecha_preparado =
                        COALESCE(NULLIF(fecha_preparado, ''), ?)
                WHERE id = ?
            """), (
                nuevo_estado,
                ahora,
                id_pedido,
            ))

        elif nuevo_estado == "Entregado":
            cur.execute(_sql("""
                UPDATE pedidos_material
                SET estado = ?,
                    fecha_entrega =
                        COALESCE(NULLIF(fecha_entrega, ''), ?)
                WHERE id = ?
            """), (
                nuevo_estado,
                ahora,
                id_pedido,
            ))

        else:
            cur.execute(_sql("""
                UPDATE pedidos_material
                SET estado = ?
                WHERE id = ?
            """), (
                nuevo_estado,
                id_pedido,
            ))

        conn.commit()

    finally:
        conn.close()


def _obtener_linea_para_estado(
    id_linea,
):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                pedido_id,
                codigo_material,
                material,
                cantidad,
                estado,
                inventario_descontado
            FROM pedidos_material_lineas
            WHERE id = ?
        """), (
            id_linea,
        ))

        return cur.fetchone()

    finally:
        conn.close()


def _descontar_inventario_linea(
    numero_pedido,
    codigo_material,
    cantidad,
    operario="",
):
    codigo_material = str(
        codigo_material or ""
    ).strip()

    if not codigo_material:
        return (
            True,
            "Material externo: no afecta al inventario.",
        )

    material = obtener_material_por_codigo(
        codigo_material
    )

    if not material:
        return (
            False,
            f"El material {codigo_material} ya no existe en inventario.",
        )

    stock_actual = float(
        material.get(
            "stock_actual",
            0,
        )
        or 0
    )

    cantidad = float(
        cantidad or 0
    )

    if stock_actual < cantidad:
        return (
            False,
            (
                f"Stock insuficiente de "
                f"{material.get('material', codigo_material)}. "
                f"Disponible: {stock_actual}."
            ),
        )

    return registrar_movimiento_inventario(
        codigo_material=codigo_material,
        tipo_movimiento="Salida",
        cantidad=cantidad,
        motivo=(
            f"Entrega pedido material "
            f"{numero_pedido}"
        ),
        numero_ot="",
        operario=operario,
    )


def cambiar_estado_linea_pedido(
    id_linea,
    nuevo_estado,
):
    crear_tabla_pedidos_material()

    if nuevo_estado not in ESTADOS_PEDIDO:
        return (
            False,
            "Estado de pedido no válido.",
        )

    linea = _obtener_linea_para_estado(
        id_linea
    )

    if not linea:
        return (
            False,
            "No se ha encontrado la línea del pedido.",
        )

    (
        pedido_id,
        codigo_material,
        material,
        cantidad,
        estado_anterior,
        inventario_descontado,
    ) = linea

    # Datos del pedido para trazabilidad.
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                numero_pedido,
                operario
            FROM pedidos_material
            WHERE id = ?
        """), (
            pedido_id,
        ))

        cabecera = cur.fetchone()

    finally:
        conn.close()

    numero_pedido = (
        cabecera[0]
        if cabecera and cabecera[0]
        else formatear_numero_pedido(
            pedido_id
        )
    )

    operario = (
        cabecera[1]
        if cabecera
        else ""
    )

    # Descuento físico solo una vez y solo al entregar.
    if (
        nuevo_estado == "Entregado"
        and str(codigo_material or "").strip()
        and not bool(inventario_descontado)
    ):
        ok_stock, mensaje_stock = (
            _descontar_inventario_linea(
                numero_pedido=numero_pedido,
                codigo_material=codigo_material,
                cantidad=cantidad,
                operario=operario,
            )
        )

        if not ok_stock:
            # La línea queda marcada Sin stock para que Abel la vea.
            conn = conectar()
            cur = conn.cursor()

            try:
                cur.execute(_sql("""
                    UPDATE pedidos_material_lineas
                    SET estado = 'Sin stock'
                    WHERE id = ?
                """), (
                    id_linea,
                ))

                conn.commit()

            finally:
                conn.close()

            recalcular_estado_pedido(
                pedido_id
            )

            return (
                False,
                mensaje_stock,
            )

        inventario_descontado = 1

    conn = conectar()
    cur = conn.cursor()

    try:
        ahora = datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        if nuevo_estado == "Preparado":
            cur.execute(_sql("""
                UPDATE pedidos_material_lineas
                SET estado = ?,
                    fecha_preparado =
                        COALESCE(NULLIF(fecha_preparado, ''), ?),
                    inventario_descontado = ?
                WHERE id = ?
            """), (
                nuevo_estado,
                ahora,
                int(
                    bool(
                        inventario_descontado
                    )
                ),
                id_linea,
            ))

        elif nuevo_estado == "Entregado":
            cur.execute(_sql("""
                UPDATE pedidos_material_lineas
                SET estado = ?,
                    fecha_entrega =
                        COALESCE(NULLIF(fecha_entrega, ''), ?),
                    inventario_descontado = ?
                WHERE id = ?
            """), (
                nuevo_estado,
                ahora,
                int(
                    bool(
                        inventario_descontado
                    )
                ),
                id_linea,
            ))

        else:
            cur.execute(_sql("""
                UPDATE pedidos_material_lineas
                SET estado = ?,
                    inventario_descontado = ?
                WHERE id = ?
            """), (
                nuevo_estado,
                int(
                    bool(
                        inventario_descontado
                    )
                ),
                id_linea,
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    recalcular_estado_pedido(
        pedido_id
    )

    return (
        True,
        (
            "Línea actualizada. "
            if nuevo_estado != "Entregado"
            else "Material entregado correctamente."
        ),
    )


def cambiar_estado_pedido(
    id_pedido,
    nuevo_estado,
):
    """
    Estado general del pedido.

    Para Entregado se procesa línea a línea porque las líneas
    catalogadas deben descontarse del inventario exactamente una vez.
    """
    crear_tabla_pedidos_material()

    if nuevo_estado not in ESTADOS_PEDIDO:
        return (
            False,
            "Estado de pedido no válido.",
        )

    if nuevo_estado == "Entregado":
        lineas = obtener_lineas_pedido(
            id_pedido
        )

        # Precomprobación de stock para evitar entregas parciales
        # por falta de existencias.
        necesidades = {}

        for linea in lineas:
            codigo = str(
                linea[2]
                or ""
            ).strip()

            descontado = bool(
                linea[10]
                if len(linea) > 10
                else 0
            )

            if (
                codigo
                and not descontado
            ):
                necesidades[codigo] = (
                    necesidades.get(
                        codigo,
                        0.0,
                    )
                    + float(
                        linea[4]
                        or 0
                    )
                )

        for codigo, cantidad in necesidades.items():
            material = obtener_material_por_codigo(
                codigo
            )

            if not material:
                return (
                    False,
                    (
                        f"No existe en inventario el material "
                        f"{codigo}."
                    ),
                )

            stock = float(
                material.get(
                    "stock_actual",
                    0,
                )
                or 0
            )

            if stock < cantidad:
                return (
                    False,
                    (
                        f"Stock insuficiente de "
                        f"{material.get('material', codigo)}. "
                        f"Necesario: {cantidad} · Disponible: {stock}."
                    ),
                )

        for linea in lineas:
            if str(
                linea[5]
                or ""
            ) == "Entregado":
                continue

            ok, mensaje = cambiar_estado_linea_pedido(
                linea[0],
                "Entregado",
            )

            if not ok:
                return (
                    False,
                    mensaje,
                )

        recalcular_estado_pedido(
            id_pedido
        )

        return (
            True,
            "Pedido entregado correctamente.",
        )

    conn = conectar()
    cur = conn.cursor()

    try:
        ahora = datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        if nuevo_estado == "Preparado":
            cur.execute(_sql("""
                UPDATE pedidos_material
                SET estado = ?,
                    fecha_preparado =
                        COALESCE(NULLIF(fecha_preparado, ''), ?)
                WHERE id = ?
            """), (
                nuevo_estado,
                ahora,
                id_pedido,
            ))

            cur.execute(_sql("""
                UPDATE pedidos_material_lineas
                SET estado = ?,
                    fecha_preparado =
                        COALESCE(NULLIF(fecha_preparado, ''), ?)
                WHERE pedido_id = ?
                  AND estado <> 'Entregado'
            """), (
                nuevo_estado,
                ahora,
                id_pedido,
            ))

        else:
            cur.execute(_sql("""
                UPDATE pedidos_material
                SET estado = ?
                WHERE id = ?
            """), (
                nuevo_estado,
                id_pedido,
            ))

            cur.execute(_sql("""
                UPDATE pedidos_material_lineas
                SET estado = ?
                WHERE pedido_id = ?
                  AND estado <> 'Entregado'
            """), (
                nuevo_estado,
                id_pedido,
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return (
        True,
        "Estado general actualizado.",
    )


def borrar_pedido_material(
    id_pedido,
):
    crear_tabla_pedidos_material()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            DELETE FROM pedidos_material_lineas
            WHERE pedido_id = ?
        """), (
            id_pedido,
        ))

        cur.execute(_sql("""
            DELETE FROM pedidos_material
            WHERE id = ?
        """), (
            id_pedido,
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

