from datetime import datetime

from database.db import conectar, _sql
from modules.ordenes import (
    crear_orden,
    obtener_siguiente_numero_ot,
    vincular_origen_ot,
    guardar_foto_ot,
)

try:
    from modules.inventario_aulas import (
        guardar_o_actualizar_espacio,
        obtener_inventario_por_espacio,
    )
except Exception:
    guardar_o_actualizar_espacio = None
    obtener_inventario_por_espacio = None


ESTADOS_REVISION_AULA = [
    "Correcto",
    "Ajustado",
    "Revisar",
    "Avería",
]


_ESTRUCTURA_PREVENTIVO_AULAS_ASEGURADA = False


def hoy_str():
    return datetime.now().strftime("%Y-%m-%d")


def normalizar_texto(texto):
    texto = str(texto or "").strip().lower()

    cambios = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }

    for a, b in cambios.items():
        texto = texto.replace(a, b)

    return texto


def area_por_elemento_aula(elemento):
    elemento_txt = normalizar_texto(elemento)

    if any(x in elemento_txt for x in [
        "luz", "ilumin", "enchufe", "interruptor", "canaleta",
        "cable", "toma corriente", "emergencia", "diferencial",
        "magnetotermico", "cuadro electrico",
    ]):
        return "Electricidad"

    if any(x in elemento_txt for x in [
        "proyector", "pantalla", "hdmi", "altavoz", "ordenador",
        "pc", "monitor", "informat", "red", "switch", "wifi",
        "mando", "pizarra digital",
    ]):
        return "Informática"

    if any(x in elemento_txt for x in [
        "puerta", "maneta", "cerradura", "cierrapuertas",
        "ventana", "persiana", "carpinter", "bisagra",
    ]):
        return "Carpintería"

    if any(x in elemento_txt for x in [
        "grifo", "lavabo", "agua", "desague", "cisterna",
        "wc", "inodoro", "fregadero", "fontaner",
    ]):
        return "Fontanería"

    if any(x in elemento_txt for x in [
        "split", "aire", "clima", "climatizacion", "radiador",
        "termostato", "condensado", "filtro",
    ]):
        return "Climatización"

    if any(x in elemento_txt for x in [
        "mesa", "silla", "pizarra", "papelera", "estanteria",
        "armario", "mueble", "corcho", "mobiliario",
    ]):
        return "Equipamiento"

    return "Equipamiento"


# =====================================================
# ESTRUCTURA
# =====================================================

def _asegurar_columna(cur, conn, tabla, columna, tipo_sql):
    try:
        cur.execute(_sql(f"""
            ALTER TABLE {tabla}
            ADD COLUMN {columna} {tipo_sql}
        """))
        conn.commit()
    except Exception:
        conn.rollback()


def crear_tablas_preventivo_aulas():
    """
    Mantiene las tablas antiguas y añade únicamente las columnas necesarias
    para el nuevo Preventivo de Aulas.

    No borra ni renombra datos existentes.

    La estructura se comprueba una sola vez por proceso Streamlit para
    evitar ALTER TABLE repetidos en cada rerun de una OT.
    """
    global _ESTRUCTURA_PREVENTIVO_AULAS_ASEGURADA

    if _ESTRUCTURA_PREVENTIVO_AULAS_ASEGURADA:
        return

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS preventivo_aulas (
            id SERIAL PRIMARY KEY,
            fecha TEXT,
            centro TEXT,
            edificio TEXT,
            espacio TEXT,
            operario TEXT,
            estado TEXT,
            observaciones TEXT,
            numero_ot_preventiva TEXT
        )
    """))

    cur.execute(_sql("""
        CREATE TABLE IF NOT EXISTS preventivo_aulas_items (
            id SERIAL PRIMARY KEY,
            revision_id INTEGER,
            elemento TEXT,
            estado TEXT,
            observaciones TEXT,
            foto TEXT,
            crear_correctivo INTEGER DEFAULT 0,
            numero_ot_correctiva TEXT
        )
    """))

    conn.commit()

    _asegurar_columna(cur, conn, "preventivo_aulas", "planta", "TEXT")
    _asegurar_columna(
        cur,
        conn,
        "preventivo_aulas",
        "revision_general_completada",
        "INTEGER DEFAULT 0",
    )
    _asegurar_columna(
        cur,
        conn,
        "preventivo_aulas",
        "incidencias_revision",
        "TEXT DEFAULT ''",
    )
    _asegurar_columna(
        cur,
        conn,
        "preventivo_aulas",
        "flujo_revision_general",
        "INTEGER DEFAULT 0",
    )
    _asegurar_columna(
        cur,
        conn,
        "preventivo_aulas",
        "inventario_inicial_requerido",
        "INTEGER DEFAULT 0",
    )
    _asegurar_columna(
        cur,
        conn,
        "preventivo_aulas",
        "inventario_inicial_completado",
        "INTEGER DEFAULT 0",
    )

    for columna, tipo in [
        ("categoria", "TEXT DEFAULT ''"),
        ("tipo_linea", "TEXT DEFAULT ''"),
        ("pide_cantidad", "INTEGER DEFAULT 0"),
        ("cantidad_total", "INTEGER DEFAULT 0"),
        ("cantidad_correcta", "INTEGER DEFAULT 0"),
        ("cantidad_afectada", "INTEGER DEFAULT 0"),
        ("modelo_id", "INTEGER DEFAULT 0"),
    ]:
        _asegurar_columna(
            cur,
            conn,
            "preventivo_aulas_items",
            columna,
            tipo,
        )

    # Transición segura: las revisiones abiertas ya vinculadas a PREV
    # pasan al flujo nuevo. Los históricos cerrados no se tocan.
    try:
        cur.execute(_sql("""
            UPDATE preventivo_aulas
            SET flujo_revision_general = 1
            WHERE LOWER(COALESCE(estado, '')) <> 'cerrada'
              AND TRIM(COALESCE(numero_ot_preventiva, '')) <> ''
        """))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

    conn.close()
    _ESTRUCTURA_PREVENTIVO_AULAS_ASEGURADA = True


# =====================================================
# MODELO CONFIGURADO
# =====================================================

def obtener_modelo_aula_activo():
    """
    Lee directamente el catálogo que se administra desde Configuración
    (preventivo_aula_modelos).

    Así Configuración sigue siendo la fuente maestra y este módulo
    solo consume el modelo.
    """
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                id,
                categoria,
                elemento,
                tipo_linea,
                COALESCE(pide_cantidad, 0),
                COALESCE(cantidad_defecto, 0),
                COALESCE(orden, 0)
            FROM preventivo_aula_modelos
            WHERE activo = 1
            ORDER BY
                COALESCE(orden, 0) ASC,
                categoria ASC,
                elemento ASC
        """)
        return cur.fetchall()

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []

    finally:
        conn.close()


def _inventario_actual_por_elemento(centro, edificio, espacio):
    """
    Devuelve el inventario vivo actual del espacio indexado por nombre
    normalizado de elemento.
    """
    resultado = {}

    if obtener_inventario_por_espacio is None:
        return resultado

    try:
        inventario = obtener_inventario_por_espacio(
            centro,
            edificio,
            espacio,
        ) or []
    except Exception:
        return resultado

    for fila in inventario:
        try:
            elemento = str(fila[5] or "").strip()
            cantidad = int(float(fila[6] or 0))
            estado = str(fila[7] or "").strip()
            foto = str(fila[13] or "").strip()
        except Exception:
            continue

        clave = normalizar_texto(elemento)

        if not clave:
            continue

        # Si por compatibilidad antigua hubiera duplicados, conserva el último
        # registro recibido para ese nombre.
        resultado[clave] = {
            "elemento": elemento,
            "cantidad": max(0, cantidad),
            "estado": estado,
            "foto": foto,
        }

    return resultado


# =====================================================
# OT PREVENTIVA
# =====================================================

def crear_ot_preventiva_revision_aula(
    revision_id,
    centro,
    edificio,
    planta,
    espacio,
    operario,
    observaciones="",
):
    """
    Crea una única OT preventiva asociada a la revisión de aula.
    Usa crear_orden(), por lo que conserva el circuito normal de
    Operario, Colegio Vivo y avisos del sistema.
    """
    revision_id = int(revision_id)

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT COALESCE(numero_ot_preventiva, '')
            FROM preventivo_aulas
            WHERE id = ?
        """), (revision_id,))
        fila = cur.fetchone()
    finally:
        conn.close()

    if not fila:
        return ""

    numero_existente = str(fila[0] or "").strip()

    if numero_existente:
        return numero_existente

    numero = obtener_siguiente_numero_ot(
        centro,
        "PREV",
    )

    descripcion = (
        f"[PREVENTIVO AULA] Revisión preventiva · {espacio}"
    )

    observaciones_ot = f"""
Revisión preventiva de aula.

Revisión ID: {revision_id}
Centro: {centro or "-"}
Edificio: {edificio or "-"}
Planta: {planta or "-"}
Aula / espacio: {espacio or "-"}
Operario: {operario or "-"}
Observaciones iniciales: {observaciones or "-"}
""".strip()

    datos_orden = (
        numero,
        descripcion,
        "Abierta",
        centro,
        edificio,
        espacio,
        "Preventivo",
        "Media",
        operario,
        "PREVENTIVO",
        "Mantenimiento preventivo",
        hoy_str(),
        "",
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
        observaciones_ot,
        planta or "",
    )

    numero_creado = crear_orden(
        datos_orden
    ) or numero

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE preventivo_aulas
            SET numero_ot_preventiva = ?
            WHERE id = ?
        """), (
            numero_creado,
            revision_id,
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    try:
        vincular_origen_ot(
            numero_ot=numero_creado,
            origen_tabla="preventivo_aulas",
            origen_id=revision_id,
        )
    except Exception:
        pass

    return numero_creado


# =====================================================
# CREACIÓN DE REVISIÓN DESDE MODELO
# =====================================================

def crear_revision_aula(
    centro,
    edificio,
    espacio,
    operario,
    observaciones="",
    numero_ot_preventiva="",
    planta="",
):
    """
    Crea una revisión utilizando el modelo activo de Configuración.

    Elemento inventariable:
    - precarga la cantidad del inventario vivo si ya existe;
    - en la primera revisión usa la cantidad sugerida del modelo;
    - guarda cantidad total, correcta y afectada.

    Comprobación técnica:
    - no utiliza cantidades.
    """
    crear_tablas_preventivo_aulas()

    modelo = obtener_modelo_aula_activo()

    if not modelo:
        raise ValueError(
            "El Modelo aulas está vacío. "
            "Ve a Configuración > Modelo aulas y carga o activa elementos."
        )

    inventario_actual = _inventario_actual_por_elemento(
        centro,
        edificio,
        espacio,
    )

    numero_ot_preventiva = str(
        numero_ot_preventiva or ""
    ).strip()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            INSERT INTO preventivo_aulas
            (
                fecha,
                centro,
                edificio,
                espacio,
                operario,
                estado,
                observaciones,
                numero_ot_preventiva,
                planta,
                flujo_revision_general,
                inventario_inicial_requerido,
                inventario_inicial_completado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """), (
            hoy_str(),
            centro,
            edificio,
            espacio,
            operario,
            "Abierta",
            observaciones,
            numero_ot_preventiva,
            planta,
            1,
            0 if inventario_actual else 1,
            1 if inventario_actual else 0,
        ))

        revision_id = cur.fetchone()[0]

        for (
            modelo_id,
            categoria,
            elemento,
            tipo_linea,
            pide_cantidad,
            cantidad_defecto,
            orden,
        ) in modelo:
            tipo_linea = str(tipo_linea or "").strip()
            es_inventariable = (
                tipo_linea == "Elemento inventariable"
            )

            cantidad_base = 0

            if es_inventariable:
                previo = inventario_actual.get(
                    normalizar_texto(elemento)
                )

                if previo is not None:
                    cantidad_base = int(
                        previo.get("cantidad", 0) or 0
                    )
                else:
                    try:
                        cantidad_base = max(
                            0,
                            int(cantidad_defecto or 0),
                        )
                    except Exception:
                        cantidad_base = 0

            cur.execute(_sql("""
                INSERT INTO preventivo_aulas_items
                (
                    revision_id,
                    elemento,
                    estado,
                    observaciones,
                    foto,
                    crear_correctivo,
                    numero_ot_correctiva,
                    categoria,
                    tipo_linea,
                    pide_cantidad,
                    cantidad_total,
                    cantidad_correcta,
                    cantidad_afectada,
                    modelo_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), (
                revision_id,
                elemento,
                "Correcto",
                "",
                "",
                0,
                "",
                categoria,
                tipo_linea,
                1 if (es_inventariable and bool(pide_cantidad)) else 0,
                cantidad_base if es_inventariable else 0,
                cantidad_base if es_inventariable else 0,
                0,
                int(modelo_id or 0),
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    if not numero_ot_preventiva:
        crear_ot_preventiva_revision_aula(
            revision_id=revision_id,
            centro=centro,
            edificio=edificio,
            planta=planta,
            espacio=espacio,
            operario=operario,
            observaciones=observaciones,
        )

    return revision_id


# =====================================================
# CONSULTAS
# =====================================================

def obtener_revisiones_aulas(limite=100):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, fecha, centro, edificio, espacio, operario,
               estado, observaciones, numero_ot_preventiva,
               COALESCE(planta, '')
        FROM preventivo_aulas
        ORDER BY id DESC
        LIMIT ?
    """), (limite,))

    datos = cur.fetchall()
    conn.close()

    return datos


def obtener_revision_aula(revision_id):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT id, fecha, centro, edificio, espacio, operario,
               estado, observaciones, numero_ot_preventiva,
               COALESCE(planta, '')
        FROM preventivo_aulas
        WHERE id = ?
    """), (revision_id,))

    dato = cur.fetchone()
    conn.close()

    return dato


def obtener_items_revision_aula(revision_id):
    """
    Devuelve la estructura nueva.

    Posiciones:
    0 id
    1 revision_id
    2 elemento
    3 estado
    4 observaciones
    5 foto
    6 crear_correctivo
    7 numero_ot_correctiva
    8 categoria
    9 tipo_linea
    10 pide_cantidad
    11 cantidad_total
    12 cantidad_correcta
    13 cantidad_afectada
    14 modelo_id
    """
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT
            id,
            revision_id,
            elemento,
            estado,
            observaciones,
            foto,
            crear_correctivo,
            numero_ot_correctiva,
            COALESCE(categoria, ''),
            COALESCE(tipo_linea, ''),
            COALESCE(pide_cantidad, 0),
            COALESCE(cantidad_total, 0),
            COALESCE(cantidad_correcta, 0),
            COALESCE(cantidad_afectada, 0),
            COALESCE(modelo_id, 0)
        FROM preventivo_aulas_items
        WHERE revision_id = ?
        ORDER BY id ASC
    """), (revision_id,))

    datos = cur.fetchall()
    conn.close()

    return datos


# =====================================================
# GUARDADO + INVENTARIO VIVO
# =====================================================

def actualizar_item_revision_aula(
    item_id,
    estado,
    observaciones="",
    foto="",
    crear_correctivo=0,
    cantidad_total=0,
    cantidad_correcta=0,
    cantidad_afectada=0,
):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        UPDATE preventivo_aulas_items
        SET estado = ?,
            observaciones = ?,
            foto = ?,
            crear_correctivo = ?,
            cantidad_total = ?,
            cantidad_correcta = ?,
            cantidad_afectada = ?
        WHERE id = ?
    """), (
        estado,
        observaciones,
        foto,
        1 if crear_correctivo else 0,
        max(0, int(cantidad_total or 0)),
        max(0, int(cantidad_correcta or 0)),
        max(0, int(cantidad_afectada or 0)),
        item_id,
    ))

    conn.commit()
    conn.close()

    return True


def sincronizar_item_inventario_vivo(
    revision_id,
    item_id,
):
    """
    Copia un elemento inventariable revisado al inventario vivo.

    No suma cantidades: actualiza el registro existente del espacio.
    """
    if guardar_o_actualizar_espacio is None:
        return False

    revision = obtener_revision_aula(revision_id)

    if not revision:
        return False

    (
        _id,
        fecha,
        centro,
        edificio,
        espacio,
        operario,
        estado_revision,
        observaciones_revision,
        numero_ot_preventiva,
        planta,
    ) = revision

    items = obtener_items_revision_aula(revision_id)

    item = next(
        (
            fila
            for fila in items
            if int(fila[0]) == int(item_id)
        ),
        None,
    )

    if item is None:
        return False

    tipo_linea = str(item[9] or "").strip()

    if tipo_linea != "Elemento inventariable":
        return True

    elemento = str(item[2] or "").strip()
    estado = str(item[3] or "Correcto").strip()
    observaciones = str(item[4] or "").strip()
    foto = str(item[5] or "").strip()
    cantidad_total = max(0, int(item[11] or 0))
    cantidad_afectada = max(0, int(item[13] or 0))

    return bool(
        guardar_o_actualizar_espacio(
            centro=centro,
            edificio=edificio,
            espacio=espacio,
            elemento=elemento,
            cantidad=cantidad_total,
            estado=estado,
            ancho=0,
            alto=0,
            fondo=0,
            unidad="ud",
            observaciones=observaciones,
            foto=foto,
            operario=operario,
            cantidad_afectada=cantidad_afectada,
        )
    )


def guardar_item_revision_y_sincronizar(
    revision_id,
    item_id,
    estado,
    observaciones="",
    foto="",
    crear_correctivo=0,
    cantidad_total=0,
    cantidad_correcta=0,
    cantidad_afectada=0,
):
    """
    Guarda una línea y, si es inventariable, actualiza el censo vivo.
    """
    ok = actualizar_item_revision_aula(
        item_id=item_id,
        estado=estado,
        observaciones=observaciones,
        foto=foto,
        crear_correctivo=crear_correctivo,
        cantidad_total=cantidad_total,
        cantidad_correcta=cantidad_correcta,
        cantidad_afectada=cantidad_afectada,
    )

    if not ok:
        return False

    return sincronizar_item_inventario_vivo(
        revision_id=revision_id,
        item_id=item_id,
    )



# =====================================================
# REVISIÓN GENERAL + INCIDENCIAS NORMALES
# =====================================================

def _limpiar_nombre_foto_incidencia(texto):
    texto = str(texto or "")
    for caracter in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]:
        texto = texto.replace(caracter, "_")
    return texto.replace(" ", "_")


def obtener_estado_revision_general_aula(revision_id):
    """
    Estado del nuevo Preventivo de aulas.
    """
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                COALESCE(revision_general_completada, 0),
                COALESCE(incidencias_revision, ''),
                COALESCE(flujo_revision_general, 0),
                COALESCE(inventario_inicial_requerido, 0),
                COALESCE(inventario_inicial_completado, 0)
            FROM preventivo_aulas
            WHERE id = ?
            LIMIT 1
        """), (int(revision_id),))

        fila = cur.fetchone()

        if not fila:
            return {
                "completada": False,
                "incidencias": [],
                "flujo_nuevo": False,
                "inventario_inicial_requerido": False,
                "inventario_inicial_completado": False,
            }

        incidencias = [
            x.strip()
            for x in str(fila[1] or "").split("|")
            if x.strip()
        ]

        return {
            "completada": bool(int(fila[0] or 0)),
            "incidencias": incidencias,
            "flujo_nuevo": bool(int(fila[2] or 0)),
            "inventario_inicial_requerido": bool(int(fila[3] or 0)),
            "inventario_inicial_completado": bool(int(fila[4] or 0)),
        }

    finally:
        conn.close()


def marcar_inventario_inicial_aula_completado(revision_id):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE preventivo_aulas
            SET inventario_inicial_completado = 1
            WHERE id = ?
        """), (int(revision_id),))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def registrar_incidencia_revision_aula(revision_id, numero_ot):
    revision_id = int(revision_id)
    numero_ot = str(numero_ot or "").strip()

    if not numero_ot:
        return False

    estado = obtener_estado_revision_general_aula(revision_id)
    incidencias = list(estado.get("incidencias", []) or [])

    if numero_ot not in incidencias:
        incidencias.append(numero_ot)

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE preventivo_aulas
            SET incidencias_revision = ?
            WHERE id = ?
        """), ("|".join(incidencias), revision_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def marcar_revision_general_aula_completada(revision_id, completada=True):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE preventivo_aulas
            SET revision_general_completada = ?
            WHERE id = ?
        """), (
            1 if completada else 0,
            int(revision_id),
        ))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def crear_incidencia_desde_revision_aula(
    revision_id,
    descripcion,
    fotos=None,
):
    revision = obtener_revision_aula(revision_id)

    if not revision:
        return False, "No se ha encontrado la revisión de aula.", ""

    (
        _id,
        fecha,
        centro,
        edificio,
        espacio,
        operario,
        estado_revision,
        observaciones_revision,
        numero_ot_preventiva,
        planta,
    ) = revision

    descripcion_limpia = str(descripcion or "").strip()

    if not descripcion_limpia:
        return False, "Describe brevemente la anomalía detectada.", ""

    fotos = list(fotos or [])

    if len(fotos) > 5:
        return False, "Puedes añadir un máximo de 5 fotografías.", ""

    fotos_validas = []

    for foto in fotos:
        try:
            tamano = int(getattr(foto, "size", 0) or 0)
        except Exception:
            tamano = 0

        if tamano > 5 * 1024 * 1024:
            return (
                False,
                f"La fotografía {getattr(foto, 'name', 'seleccionada')} supera 5 MB.",
                "",
            )

        fotos_validas.append(
            (
                str(getattr(foto, "name", "foto.jpg") or "foto.jpg"),
                foto.getvalue(),
            )
        )

    numero_ot = obtener_siguiente_numero_ot(
        centro,
        "INC",
    )

    fecha_origen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    observaciones_origen = (
        "Incidencia detectada durante una revisión preventiva de aula.\n"
        f"Revisión ID: {revision_id}\n"
        f"OT preventiva origen: {numero_ot_preventiva or '-'}\n"
        f"Planta: {planta or '-'}"
    )

    datos_orden = (
        numero_ot,
        descripcion_limpia,
        "Abierta",
        centro,
        edificio,
        espacio,
        "Otros",
        "Media",
        operario,
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
        planta or "",
    )

    try:
        numero_creado = crear_orden(datos_orden) or numero_ot
    except Exception as error:
        return False, f"No se ha podido crear la incidencia: {error}", ""

    error_fotos = ""

    if fotos_validas:
        try:
            for indice, (nombre_original, contenido) in enumerate(
                fotos_validas,
                start=1,
            ):
                nombre_foto = _limpiar_nombre_foto_incidencia(
                    f"{numero_creado}_{indice}_{nombre_original}"
                )

                guardar_foto_ot(
                    numero_ot=numero_creado,
                    nombre_foto=nombre_foto,
                    foto_data=contenido,
                )
        except Exception as error:
            error_fotos = str(error)

    registrar_incidencia_revision_aula(
        revision_id,
        numero_creado,
    )

    if error_fotos:
        mensaje = (
            f"Incidencia {numero_creado} creada, pero alguna fotografía "
            "no se pudo guardar."
        )
    else:
        mensaje = f"Incidencia {numero_creado} creada correctamente."

    return True, mensaje, numero_creado


def guardar_inventario_inicial_revision_aula(
    revision_id,
    cantidades_totales,
):
    """
    Primer censo del aula. Solo se introduce la cantidad instalada.
    Los siguientes preventivos reutilizan el inventario vivo.
    """
    items = obtener_items_revision_aula(revision_id)
    mapa = {int(item[0]): item for item in items}

    for item_id, cantidad in cantidades_totales.items():
        item_id = int(item_id)
        item = mapa.get(item_id)

        if item is None:
            continue

        if str(item[9] or "").strip() != "Elemento inventariable":
            continue

        total = max(0, int(cantidad or 0))

        guardar_item_revision_y_sincronizar(
            revision_id=revision_id,
            item_id=item_id,
            estado="Correcto",
            observaciones=str(item[4] or ""),
            foto=str(item[5] or ""),
            crear_correctivo=0,
            cantidad_total=total,
            cantidad_correcta=total,
            cantidad_afectada=0,
        )

    marcar_inventario_inicial_aula_completado(revision_id)
    return True


def guardar_inventario_revision_aula(
    revision_id,
    cantidades,
):
    items = obtener_items_revision_aula(revision_id)

    mapa = {
        int(item[0]): item
        for item in items
    }

    for item_id, valores in cantidades.items():
        item_id = int(item_id)
        item = mapa.get(item_id)

        if item is None:
            continue

        if str(item[9] or "").strip() != "Elemento inventariable":
            continue

        total, correctas, afectadas = valores
        total = max(0, int(total or 0))
        correctas = max(0, int(correctas or 0))
        afectadas = max(0, int(afectadas or 0))

        if correctas + afectadas != total:
            raise ValueError(
                f"{item[2]}: Total ({total}) debe ser igual a "
                f"Correctas ({correctas}) + Con incidencia ({afectadas})."
            )

        estado = "Avería" if afectadas > 0 else "Correcto"

        guardar_item_revision_y_sincronizar(
            revision_id=revision_id,
            item_id=item_id,
            estado=estado,
            observaciones=str(item[4] or ""),
            foto=str(item[5] or ""),
            crear_correctivo=0,
            cantidad_total=total,
            cantidad_correcta=correctas,
            cantidad_afectada=afectadas,
        )

    return True


# =====================================================
# CIERRE / CORRECTIVOS
# =====================================================

def cerrar_revision_aula(revision_id, observaciones=""):
    crear_tablas_preventivo_aulas()

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        UPDATE preventivo_aulas
        SET estado = ?,
            observaciones = ?
        WHERE id = ?
    """), (
        "Cerrada",
        observaciones,
        revision_id,
    ))

    conn.commit()
    conn.close()

    return True


def obtener_items_con_averia(revision_id):
    crear_tablas_preventivo_aulas()

    return [
        fila
        for fila in obtener_items_revision_aula(revision_id)
        if str(fila[3] or "") == "Avería"
    ]


def obtener_items_a_revisar(revision_id):
    crear_tablas_preventivo_aulas()

    return [
        fila
        for fila in obtener_items_revision_aula(revision_id)
        if str(fila[3] or "") == "Revisar"
    ]


def crear_correctivos_desde_revision(revision_id):
    crear_tablas_preventivo_aulas()

    revision = obtener_revision_aula(revision_id)

    if not revision:
        return 0

    (
        _id,
        fecha,
        centro,
        edificio,
        espacio,
        operario,
        estado_revision,
        observaciones_revision,
        numero_ot_preventiva,
        planta,
    ) = revision

    conn = conectar()
    cur = conn.cursor()

    cur.execute(_sql("""
        SELECT
            id,
            elemento,
            observaciones,
            foto,
            numero_ot_correctiva,
            COALESCE(cantidad_afectada, 0)
        FROM preventivo_aulas_items
        WHERE revision_id = ?
          AND estado = ?
          AND crear_correctivo = 1
    """), (
        revision_id,
        "Avería",
    ))

    items = cur.fetchall()

    creadas = 0

    for item in items:
        (
            item_id,
            elemento,
            observaciones_item,
            foto,
            numero_ot_correctiva,
            cantidad_afectada,
        ) = item

        if numero_ot_correctiva:
            continue

        numero = obtener_siguiente_numero_ot(
            centro,
            "CORR",
        )

        area = area_por_elemento_aula(
            elemento
        )

        descripcion = (
            f"[CORRECTIVO AULA] "
            f"{elemento} - {espacio}"
        )

        afectadas_txt = ""
        if int(cantidad_afectada or 0) > 0:
            afectadas_txt = (
                f"\nCantidad afectada: "
                f"{int(cantidad_afectada)}"
            )

        observaciones_ot = f"""
Correctivo generado desde revisión preventiva de aula.

Aula/Espacio: {espacio}
Planta: {planta or "-"}
Elemento: {elemento}{afectadas_txt}
Área asignada automáticamente: {area}
Observación: {observaciones_item or "-"}
Fecha revisión: {fecha or hoy_str()}
OT preventiva origen: {numero_ot_preventiva or "-"}
""".strip()

        datos_orden = (
            numero,
            descripcion,
            "Abierta",
            centro,
            edificio,
            espacio,
            area,
            "Media",
            operario,
            "PREVENTIVO_AULA",
            "Mantenimiento preventivo",
            hoy_str(),
            foto or "",
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
            observaciones_ot,
            planta or "",
        )

        numero_creado = crear_orden(
            datos_orden
        ) or numero

        cur.execute(_sql("""
            UPDATE preventivo_aulas_items
            SET numero_ot_correctiva = ?
            WHERE id = ?
        """), (
            numero_creado,
            item_id,
        ))

        creadas += 1

    conn.commit()
    conn.close()

    return creadas


def obtener_estado_ot(numero_ot):
    if not numero_ot:
        return ""

    posibles_columnas = [
        "numero_ot",
        "numero",
        "codigo",
    ]

    for columna in posibles_columnas:
        conn = conectar()
        cur = conn.cursor()

        try:
            cur.execute(_sql(f"""
                SELECT estado
                FROM ordenes_trabajo
                WHERE {columna} = ?
                LIMIT 1
            """), (numero_ot,))

            fila = cur.fetchone()

            if fila:
                conn.close()
                return str(fila[0] or "")

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

        finally:
            try:
                conn.close()
            except Exception:
                pass

        conn = conectar()
        cur = conn.cursor()

        try:
            cur.execute(_sql(f"""
                SELECT estado
                FROM historico_ordenes
                WHERE {columna} = ?
                LIMIT 1
            """), (numero_ot,))

            fila = cur.fetchone()

            if fila:
                conn.close()
                return str(fila[0] or "")

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

        finally:
            try:
                conn.close()
            except Exception:
                pass

    return ""


def ot_correctiva_cerrada(numero_ot):
    estado = obtener_estado_ot(
        numero_ot
    ).lower()

    return estado in [
        "finalizada",
        "finalizado",
        "cerrado",
        "cerrada",
        "cancelada",
        "cancelado",
    ]




def obtener_contexto_revision_aula_por_ot(numero_ot):
    """
    Carga de una sola vez todo lo necesario para dibujar el preventivo
    de aula del operario.

    Evita abrir varias conexiones consecutivas a la base de datos para:
    - localizar la revisión;
    - cargar sus elementos;
    - leer el estado del nuevo flujo.

    Devuelve:
        (revision, items, estado_general)
    """
    crear_tablas_preventivo_aulas()

    numero_ot = str(numero_ot or "").strip()

    if not numero_ot:
        return None, [], {
            "completada": False,
            "incidencias": [],
            "flujo_nuevo": False,
            "inventario_inicial_requerido": False,
            "inventario_inicial_completado": False,
        }

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                id,
                fecha,
                centro,
                edificio,
                espacio,
                operario,
                estado,
                observaciones,
                numero_ot_preventiva,
                COALESCE(planta, '')
            FROM preventivo_aulas
            WHERE numero_ot_preventiva = ?
            ORDER BY id DESC
            LIMIT 1
        """), (numero_ot,))

        revision = cur.fetchone()

        if not revision:
            return None, [], {
                "completada": False,
                "incidencias": [],
                "flujo_nuevo": False,
                "inventario_inicial_requerido": False,
                "inventario_inicial_completado": False,
            }

        revision_id = int(revision[0])

        cur.execute(_sql("""
            SELECT
                id,
                revision_id,
                elemento,
                estado,
                observaciones,
                foto,
                crear_correctivo,
                numero_ot_correctiva,
                COALESCE(categoria, ''),
                COALESCE(tipo_linea, ''),
                COALESCE(pide_cantidad, 0),
                COALESCE(cantidad_total, 0),
                COALESCE(cantidad_correcta, 0),
                COALESCE(cantidad_afectada, 0),
                COALESCE(modelo_id, 0)
            FROM preventivo_aulas_items
            WHERE revision_id = ?
            ORDER BY id ASC
        """), (revision_id,))

        items = cur.fetchall()

        cur.execute(_sql("""
            SELECT
                COALESCE(revision_general_completada, 0),
                COALESCE(incidencias_revision, ''),
                COALESCE(flujo_revision_general, 0),
                COALESCE(inventario_inicial_requerido, 0),
                COALESCE(inventario_inicial_completado, 0)
            FROM preventivo_aulas
            WHERE id = ?
        """), (revision_id,))

        fila_estado = cur.fetchone()

        if fila_estado:
            (
                completada,
                incidencias_txt,
                flujo_nuevo,
                inventario_requerido,
                inventario_completado,
            ) = fila_estado
        else:
            completada = 0
            incidencias_txt = ""
            flujo_nuevo = 0
            inventario_requerido = 0
            inventario_completado = 0

        incidencias = [
            valor.strip()
            for valor in str(incidencias_txt or "").split("|")
            if valor.strip()
        ]

        estado_general = {
            "completada": bool(completada),
            "incidencias": incidencias,
            "flujo_nuevo": bool(flujo_nuevo),
            "inventario_inicial_requerido": bool(inventario_requerido),
            "inventario_inicial_completado": bool(inventario_completado),
        }

        return revision, items, estado_general

    finally:
        conn.close()


def obtener_revision_aula_por_ot(numero_ot):
    """
    Localiza la revisión integral asociada a una OT preventiva concreta.
    """
    crear_tablas_preventivo_aulas()

    numero_ot = str(numero_ot or "").strip()

    if not numero_ot:
        return None

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT
                id,
                fecha,
                centro,
                edificio,
                espacio,
                operario,
                estado,
                observaciones,
                numero_ot_preventiva,
                COALESCE(planta, '')
            FROM preventivo_aulas
            WHERE numero_ot_preventiva = ?
            ORDER BY id DESC
            LIMIT 1
        """), (numero_ot,))

        return cur.fetchone()

    finally:
        conn.close()


def revision_aula_lista_para_cerrar(numero_ot):
    """
    Cierre del Preventivo de aulas.

    Flujo nuevo:
    - primer censo, solo cuando todavía no existe inventario vivo;
    - revisión general terminada explícitamente;
    - las anomalías son INC independientes.

    El histórico antiguo conserva su regla previa.
    """
    revision = obtener_revision_aula_por_ot(numero_ot)

    if not revision:
        return False

    revision_id = revision[0]
    items = obtener_items_revision_aula(revision_id)

    if not items:
        return False

    estado_general = obtener_estado_revision_general_aula(revision_id)

    if estado_general.get("flujo_nuevo"):
        if (
            estado_general.get("inventario_inicial_requerido")
            and not estado_general.get("inventario_inicial_completado")
        ):
            return False

        return bool(estado_general.get("completada"))

    for item in items:
        tipo_linea = str(item[9] or "").strip()

        if tipo_linea == "Elemento inventariable":
            total = int(item[11] or 0)
            correctas = int(item[12] or 0)
            afectadas = int(item[13] or 0)

            if total < 0 or correctas < 0 or afectadas < 0:
                return False

            if correctas + afectadas != total:
                return False

        estado = str(item[3] or "").strip()
        observaciones = str(item[4] or "").strip()
        crear_correctivo = bool(item[6])
        numero_ot_correctiva = str(item[7] or "").strip()

        if estado not in ESTADOS_REVISION_AULA:
            return False

        if estado in ["Ajustado", "Revisar", "Avería"] and not observaciones:
            return False

        if (
            estado == "Avería"
            and crear_correctivo
            and not numero_ot_correctiva
        ):
            return False

    return True

def resumen_revision_aula(revision_id):
    items = obtener_items_revision_aula(
        revision_id
    )

    total = len(items)
    correctos = len([
        i for i in items
        if str(i[3]) == "Correcto"
    ])
    ajustados = len([
        i for i in items
        if str(i[3]) == "Ajustado"
    ])
    revisar = len([
        i for i in items
        if str(i[3]) == "Revisar"
    ])

    averias_detectadas = 0
    averias_pendientes = 0
    averias_resueltas = 0

    total_unidades = 0
    unidades_correctas = 0
    unidades_afectadas = 0

    for i in items:
        estado_item = str(i[3] or "")
        numero_ot_correctiva = str(
            i[7] or ""
        )

        if str(i[9] or "") == "Elemento inventariable":
            total_unidades += int(i[11] or 0)
            unidades_correctas += int(i[12] or 0)
            unidades_afectadas += int(i[13] or 0)

        if estado_item == "Avería":
            averias_detectadas += 1

            if (
                numero_ot_correctiva
                and ot_correctiva_cerrada(
                    numero_ot_correctiva
                )
            ):
                averias_resueltas += 1
            else:
                averias_pendientes += 1

    estado_general = obtener_estado_revision_general_aula(
        revision_id
    )
    incidencias_revision = list(
        estado_general.get("incidencias", []) or []
    )

    return {
        "total": total,
        "correctos": correctos,
        "ajustados": ajustados,
        "revisar": revisar,
        "averias": averias_detectadas,
        "averias_detectadas": averias_detectadas,
        "averias_pendientes": averias_pendientes,
        "averias_resueltas": averias_resueltas,
        "unidades_total": total_unidades,
        "unidades_correctas": unidades_correctas,
        "unidades_afectadas": unidades_afectadas,
        "revision_general_completada": bool(
            estado_general.get("completada")
        ),
        "incidencias_revision": incidencias_revision,
        "incidencias_revision_total": len(incidencias_revision),
    }

