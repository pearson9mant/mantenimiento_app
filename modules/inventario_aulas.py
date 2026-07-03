from datetime import datetime
from pathlib import Path

from database.db import conectar, _sql


# =====================================================
# INVENTARIO DE ESPACIOS
# Antes llamado inventario_aulas.
# Mantenemos nombre de tabla y funciones antiguas
# para no romper nada.
# =====================================================

ELEMENTOS_BASE_ESPACIO = [
    "Mesas",
    "Sillas",
    "Pantalla / proyector",
    "Pizarra",
    "Iluminación",
    "Enchufes visibles",
    "Puerta / maneta",
    "Ventanas / persianas",
    "Papeleras",
    "Estado general",
]


# Compatibilidad antigua
ELEMENTOS_BASE_AULA = ELEMENTOS_BASE_ESPACIO


def hoy():
    return datetime.now().strftime("%Y-%m-%d")


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def crear_tabla_inventario_aulas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        CREATE TABLE IF NOT EXISTS inventario_aulas (
            id SERIAL PRIMARY KEY,
            fecha_revision TEXT,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            elemento TEXT,
            cantidad INTEGER,
            estado TEXT,
            ancho REAL,
            alto REAL,
            fondo REAL,
            unidad TEXT,
            observaciones TEXT,
            foto TEXT,
            operario TEXT,
            fecha_creacion TEXT
        )
    """))

    for columna, tipo in [
        ("fecha_revision", "TEXT"),
        ("centro", "TEXT"),
        ("edificio", "TEXT"),
        ("espacio", "TEXT"),
        ("elemento", "TEXT"),
        ("cantidad", "INTEGER"),
        ("estado", "TEXT"),
        ("ancho", "REAL"),
        ("alto", "REAL"),
        ("fondo", "REAL"),
        ("unidad", "TEXT"),
        ("observaciones", "TEXT"),
        ("foto", "TEXT"),
        ("operario", "TEXT"),
        ("fecha_creacion", "TEXT"),
        ("numero_ot_correctiva", "TEXT"),
        ("fecha_correctivo", "TEXT"),
        ("fabricante", "TEXT"),
        ("modelo", "TEXT"),
        ("numero_serie", "TEXT"),
        ("fecha_instalacion", "TEXT"),
        ("proveedor", "TEXT"),
        ("vida_util_anios", "INTEGER DEFAULT 0"),
        ("coste_estimado", "REAL DEFAULT 0"),
        ("cantidad_afectada", "INTEGER DEFAULT 0"),
    ]:
        try:
            cursor.execute(_sql(f"""
                ALTER TABLE inventario_aulas
                ADD COLUMN IF NOT EXISTS {columna} {tipo}
            """))
        except Exception:
            pass

    conn.commit()
    conn.close()


def guardar_foto_espacio(foto_subida, centro, edificio, espacio, elemento):
    if foto_subida is None:
        return ""

    carpeta = Path("data/fotos_espacios")
    carpeta.mkdir(parents=True, exist_ok=True)

    nombre_foto = f"{centro}_{edificio}_{espacio}_{elemento}_{foto_subida.name}"
    nombre_foto = (
        nombre_foto
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )

    ruta_foto = str(carpeta / nombre_foto)

    with open(ruta_foto, "wb") as f:
        f.write(foto_subida.getbuffer())

    return ruta_foto


# Compatibilidad antigua
def guardar_foto_aula(foto_subida, centro, edificio, espacio, elemento):
    return guardar_foto_espacio(
        foto_subida=foto_subida,
        centro=centro,
        edificio=edificio,
        espacio=espacio,
        elemento=elemento
    )


def existe_registro_espacio(centro, edificio, espacio, elemento):
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT id
            FROM inventario_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
              AND elemento = ?
            ORDER BY id DESC
            LIMIT 1
        """), (
            centro,
            edificio,
            espacio,
            elemento
        ))

        fila = cursor.fetchone()
        return fila[0] if fila else None

    except Exception:
        return None

    finally:
        conn.close()


# Compatibilidad antigua
def existe_registro_aula(centro, edificio, espacio, elemento):
    return existe_registro_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio,
        elemento=elemento
    )


def actualizar_inventario_espacio(
    id_reg,
    cantidad,
    estado,
    ancho,
    alto,
    fondo,
    unidad,
    observaciones,
    foto,
    operario,
    cantidad_afectada=0
):
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE inventario_aulas
            SET fecha_revision = ?,
                cantidad = ?,
                cantidad_afectada = ?,
                estado = ?,
                ancho = ?,
                alto = ?,
                fondo = ?,
                unidad = ?,
                observaciones = ?,
                foto = ?,
                operario = ?
            WHERE id = ?
        """), (
            hoy(),
            cantidad,
            cantidad_afectada,
            estado,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario,
            id_reg
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


# Compatibilidad antigua
def actualizar_inventario_aula(
    id_reg,
    cantidad,
    estado,
    ancho,
    alto,
    fondo,
    unidad,
    observaciones,
    foto,
    operario
):
    return actualizar_inventario_espacio(
        id_reg=id_reg,
        cantidad=cantidad,
        estado=estado,
        ancho=ancho,
        alto=alto,
        fondo=fondo,
        unidad=unidad,
        observaciones=observaciones,
        foto=foto,
        operario=operario
    )


def guardar_inventario_aula(
    centro,
    edificio,
    espacio,
    elemento,
    cantidad,
    estado,
    ancho,
    alto,
    fondo,
    unidad,
    observaciones,
    foto,
    operario,
    cantidad_afectada=0
):
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            INSERT INTO inventario_aulas (
                fecha_revision,
                centro,
                edificio,
                espacio,
                elemento,
                cantidad,
                cantidad_afectada,
                estado,
                ancho,
                alto,
                fondo,
                unidad,
                observaciones,
                foto,
                operario,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (
            hoy(),
            centro,
            edificio,
            espacio,
            elemento,
            cantidad,
            cantidad_afectada,
            estado,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario,
            ahora()
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def guardar_o_actualizar_espacio(
    centro,
    edificio,
    espacio,
    elemento,
    cantidad,
    estado,
    ancho,
    alto,
    fondo,
    unidad,
    observaciones,
    foto,
    operario,
    cantidad_afectada=0
):
    crear_tabla_inventario_aulas()

    elemento = str(elemento or "").strip()

    if not centro or not edificio or not espacio or not elemento:
        return False

    id_existente = existe_registro_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio,
        elemento=elemento
    )

    if id_existente:
        return actualizar_inventario_espacio(
            id_reg=id_existente,
            cantidad=cantidad,
            cantidad_afectada=cantidad_afectada,
            estado=estado,
            ancho=ancho,
            alto=alto,
            fondo=fondo,
            unidad=unidad,
            observaciones=observaciones,
            foto=foto,
            operario=operario
        )

    return guardar_inventario_aula(
        centro=centro,
        edificio=edificio,
        espacio=espacio,
        elemento=elemento,
        cantidad=cantidad,
        cantidad_afectada=cantidad_afectada,
        estado=estado,
        ancho=ancho,
        alto=alto,
        fondo=fondo,
        unidad=unidad,
        observaciones=observaciones,
        foto=foto,
        operario=operario
    )


# Compatibilidad antigua
def guardar_o_actualizar_aula(
    centro,
    edificio,
    espacio,
    elemento,
    cantidad,
    estado,
    ancho,
    alto,
    fondo,
    unidad,
    observaciones,
    foto,
    operario
):
    return guardar_o_actualizar_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio,
        elemento=elemento,
        cantidad=cantidad,
        estado=estado,
        ancho=ancho,
        alto=alto,
        fondo=fondo,
        unidad=unidad,
        observaciones=observaciones,
        foto=foto,
        operario=operario
    )


def obtener_inventario_aulas():
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT
            id,
            fecha_revision,
            centro,
            edificio,
            espacio,
            elemento,
            cantidad,
            estado,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario,
            fecha_creacion
        FROM inventario_aulas
        ORDER BY fecha_creacion DESC
    """))

    datos = cursor.fetchall()
    conn.close()
    return datos


def obtener_inventario_por_espacio(centro, edificio, espacio):
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT
            id,
            fecha_revision,
            centro,
            edificio,
            espacio,
            elemento,
            cantidad,
            estado,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario,
            fecha_creacion
        FROM inventario_aulas
        WHERE centro = ?
          AND edificio = ?
          AND espacio = ?
        ORDER BY elemento ASC, fecha_creacion DESC
    """), (
        centro,
        edificio,
        espacio
    ))

    datos = cursor.fetchall()
    conn.close()
    return datos


# Compatibilidad antigua
def obtener_inventario_por_aula(centro, edificio, espacio):
    return obtener_inventario_por_espacio(
        centro=centro,
        edificio=edificio,
        espacio=espacio
    )


def obtener_elementos_espacio_para_revision(centro, edificio, espacio):
    inventario = obtener_inventario_por_espacio(centro, edificio, espacio)

    if inventario:
        elementos = []

        for item in inventario:
            elemento = str(item[5] or "").strip()
            cantidad = item[6]

            if not elemento:
                continue

            try:
                cantidad_num = int(float(cantidad or 0))
            except Exception:
                cantidad_num = 0

            if cantidad_num > 1:
                texto = f"{elemento} ({cantidad_num})"
            else:
                texto = elemento

            if texto not in elementos:
                elementos.append(texto)

        if elementos:
            return elementos

    return ELEMENTOS_BASE_ESPACIO


# Compatibilidad antigua
def obtener_elementos_aula_para_revision(centro, edificio, espacio):
    return obtener_elementos_espacio_para_revision(
        centro=centro,
        edificio=edificio,
        espacio=espacio
    )


def eliminar_elemento_inventario_espacio(id_elemento):
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            DELETE FROM inventario_aulas
            WHERE id = ?
        """), (id_elemento,))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()

def eliminar_inventario_espacio(centro, edificio, espacio):
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            DELETE
            FROM inventario_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
        """), (
            centro,
            edificio,
            espacio
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


# Compatibilidad antigua
def eliminar_elemento_inventario_aula(id_elemento):
    return eliminar_elemento_inventario_espacio(id_elemento)

def guardar_correctivo_inventario(
    id_elemento,
    numero_ot,
    fecha_correctivo=None
):
    """
    Guarda la OT correctiva asociada a un elemento del inventario.
    Así evitamos crear varias OT para el mismo problema.
    """

    crear_tabla_inventario_aulas()

    if not fecha_correctivo:
        fecha_correctivo = ahora()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE inventario_aulas
            SET numero_ot_correctiva = ?,
                fecha_correctivo = ?
            WHERE id = ?
        """), (
            numero_ot,
            fecha_correctivo,
            id_elemento
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()

def actualizar_datos_activo_espacio(
    id_elemento,
    fabricante="",
    modelo="",
    numero_serie="",
    fecha_instalacion="",
    proveedor="",
    vida_util_anios=0,
    coste_estimado=0
):
    crear_tabla_inventario_aulas()

    try:
        vida_util_anios = int(vida_util_anios or 0)
    except Exception:
        vida_util_anios = 0

    try:
        coste_estimado = float(coste_estimado or 0)
    except Exception:
        coste_estimado = 0

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE inventario_aulas
            SET fabricante = ?,
                modelo = ?,
                numero_serie = ?,
                fecha_instalacion = ?,
                proveedor = ?,
                vida_util_anios = ?,
                coste_estimado = ?
            WHERE id = ?
        """), (
            fabricante,
            modelo,
            numero_serie,
            fecha_instalacion,
            proveedor,
            vida_util_anios,
            coste_estimado,
            id_elemento
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()

def limpiar_correctivo_inventario(id_elemento):
    """
    Limpia la OT correctiva asociada a un elemento.
    Se usa cuando el correctivo ya está resuelto.
    """

    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE inventario_aulas
            SET numero_ot_correctiva = '',
                fecha_correctivo = ''
            WHERE id = ?
        """), (id_elemento,))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()

def cerrar_correctivo_inventario(id_elemento, estado_final="Correcto"):
    """
    Cierra el correctivo asociado al inventario y actualiza el estado del elemento.
    Se ejecuta automáticamente al finalizar la OT.
    """
    crear_tabla_inventario_aulas()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE inventario_aulas
            SET numero_ot_correctiva = '',
                fecha_correctivo = '',
                estado = ?,
                fecha_revision = ?
            WHERE id = ?
        """), (
            estado_final,
            hoy(),
            id_elemento
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()

def clonar_inventario_espacio(
    centro_origen,
    edificio_origen,
    espacio_origen,
    centro_destino,
    edificio_destino,
    espacio_destino,
    operario="",
    copiar_fotos=False
):
    from datetime import datetime

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT elemento, cantidad, estado, ancho, alto, fondo, unidad,
                   observaciones, foto
            FROM inventario_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
        """), (
            centro_origen,
            edificio_origen,
            espacio_origen
        ))

        filas = cur.fetchall()

        if not filas:
            conn.close()
            return False, "El espacio origen no tiene inventario."

        copiados = 0
        omitidos = 0

        for fila in filas:
            (
                elemento,
                cantidad,
                estado,
                ancho,
                alto,
                fondo,
                unidad,
                observaciones,
                foto
            ) = fila

            cur.execute(_sql("""
                SELECT COUNT(*)
                FROM inventario_aulas
                WHERE centro = ?
                  AND edificio = ?
                  AND espacio = ?
                  AND LOWER(TRIM(elemento)) = LOWER(TRIM(?))
            """), (
                centro_destino,
                edificio_destino,
                espacio_destino,
                elemento
            ))

            if cur.fetchone()[0] > 0:
                omitidos += 1
                continue

            foto_final = foto if copiar_fotos else ""

            cur.execute(_sql("""
                INSERT INTO inventario_aulas
                (
                    fecha_revision,
                    centro,
                    edificio,
                    espacio,
                    elemento,
                    cantidad,
                    estado,
                    ancho,
                    alto,
                    fondo,
                    unidad,
                    observaciones,
                    foto,
                    operario,
                    numero_ot_correctiva,
                    fecha_correctivo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '')
            """), (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                centro_destino,
                edificio_destino,
                espacio_destino,
                elemento,
                cantidad,
                estado,
                ancho or 0,
                alto or 0,
                fondo or 0,
                unidad or "cm",
                observaciones or "",
                foto_final,
                operario or ""
            ))

            copiados += 1

        conn.commit()
        conn.close()

        return True, (
            f"Espacio clonado correctamente. "
            f"Elementos copiados: {copiados}. "
            f"Omitidos porque ya existían: {omitidos}."
        )

    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error clonando inventario: {e}"
