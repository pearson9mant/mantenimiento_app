import re
import unicodedata

from database.db import conectar
_COLUMNAS_INVENTARIO_ASEGURADAS = False


def _ph(conn):
    modulo = conn.__class__.__module__.lower()
    return "?" if "sqlite" in modulo else "%s"


def _add_columna_segura(cursor, tabla, columna, tipo):
    try:
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}")
    except Exception:
        try:
            cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
        except Exception:
            pass


# =====================================================
# NORMALIZACIÓN / DUPLICADOS
# =====================================================

PALABRAS_IGNORAR_MATERIAL = {
    "de", "del", "la", "el", "los", "las", "un", "una",
    "para", "por", "con", "sin", "y", "o"
}


def normalizar_texto_material(texto):
    texto = str(texto or "").strip().lower()

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))

    texto = texto.replace("á", "a")
    texto = texto.replace("é", "e")
    texto = texto.replace("í", "i")
    texto = texto.replace("ó", "o")
    texto = texto.replace("ú", "u")
    texto = texto.replace("ñ", "n")

    texto = re.sub(r"[^a-z0-9 ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def palabras_clave_material(texto):
    texto_norm = normalizar_texto_material(texto)

    palabras = [
        p for p in texto_norm.split()
        if p and p not in PALABRAS_IGNORAR_MATERIAL and len(p) >= 3
    ]

    return list(dict.fromkeys(palabras))


def buscar_material_duplicado_exacto(material, categoria="", unidad=""):
    asegurar_columnas_inventario()

    material_norm = normalizar_texto_material(material)
    categoria_norm = normalizar_texto_material(categoria)
    unidad_norm = normalizar_texto_material(unidad)

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, codigo, material, categoria, unidad, stock_actual, activo
        FROM inventario
        WHERE COALESCE(activo, 1) = 1
    """)

    filas = cursor.fetchall()
    conn.close()

    for fila in filas:
        id_mat, codigo, mat, cat, uni, stock, activo = fila

        if (
            normalizar_texto_material(mat) == material_norm
            and normalizar_texto_material(cat) == categoria_norm
            and normalizar_texto_material(uni) == unidad_norm
        ):
            return {
                "id": id_mat,
                "codigo": codigo,
                "material": mat,
                "categoria": cat,
                "unidad": uni,
                "stock_actual": stock,
            }

    return None


def buscar_materiales_parecidos(material, limite=8):
    asegurar_columnas_inventario()

    palabras_nuevo = set(palabras_clave_material(material))

    if not palabras_nuevo:
        return []

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, codigo, material, categoria, unidad, stock_actual
        FROM inventario
        WHERE COALESCE(activo, 1) = 1
        ORDER BY material ASC
    """)

    filas = cursor.fetchall()
    conn.close()

    parecidos = []

    for fila in filas:
        id_mat, codigo, mat, cat, uni, stock = fila

        palabras_existente = set(palabras_clave_material(mat))

        if not palabras_existente:
            continue

        coincidencias = palabras_nuevo.intersection(palabras_existente)

        if coincidencias:
            puntuacion = len(coincidencias)

            mat_norm = normalizar_texto_material(mat)
            nuevo_norm = normalizar_texto_material(material)

            for p in palabras_nuevo:
                if p in mat_norm:
                    puntuacion += 1

            for p in palabras_existente:
                if p in nuevo_norm:
                    puntuacion += 1

            parecidos.append({
                "id": id_mat,
                "codigo": codigo,
                "material": mat,
                "categoria": cat,
                "unidad": uni,
                "stock_actual": stock,
                "coincidencias": ", ".join(sorted(coincidencias)),
                "puntuacion": puntuacion,
            })

    return sorted(parecidos, key=lambda x: x["puntuacion"], reverse=True)[:limite]


def comprobar_material_antes_crear(material, categoria="", unidad=""):
    exacto = buscar_material_duplicado_exacto(material, categoria, unidad)
    parecidos = buscar_materiales_parecidos(material)

    return exacto, parecidos


# =====================================================
# COLUMNAS
# =====================================================

def asegurar_columnas_inventario():
    global _COLUMNAS_INVENTARIO_ASEGURADAS

    if _COLUMNAS_INVENTARIO_ASEGURADAS:
        return

    conn = conectar()
    cursor = conn.cursor()

    try:
        _add_columna_segura(cursor, "inventario", "foto", "TEXT")
        _add_columna_segura(cursor, "inventario", "foto_nombre", "TEXT")

        if "sqlite" in conn.__class__.__module__.lower():
            _add_columna_segura(cursor, "inventario", "foto_data", "BLOB")
        else:
            _add_columna_segura(cursor, "inventario", "foto_data", "BYTEA")

        _add_columna_segura(cursor, "inventario", "activo", "INTEGER DEFAULT 1")
        _add_columna_segura(cursor, "inventario", "material_normalizado", "TEXT")

        _add_columna_segura(cursor, "inventario", "precio_unitario", "REAL DEFAULT 0")
        _add_columna_segura(cursor, "inventario", "coste_total", "REAL DEFAULT 0")
        _add_columna_segura(cursor, "inventario", "fecha_compra", "TEXT")
        _add_columna_segura(cursor, "inventario", "referencia_factura", "TEXT")
        _add_columna_segura(cursor, "inventario", "observaciones_coste", "TEXT")

        # Datos ampliados de OT en historial de inventario
        _add_columna_segura(cursor, "movimientos_inventario", "descripcion_ot", "TEXT")
        _add_columna_segura(cursor, "movimientos_inventario", "centro_ot", "TEXT")
        _add_columna_segura(cursor, "movimientos_inventario", "edificio_ot", "TEXT")
        _add_columna_segura(cursor, "movimientos_inventario", "espacio_ot", "TEXT")
        _add_columna_segura(cursor, "movimientos_inventario", "area_ot", "TEXT")
        _add_columna_segura(cursor, "movimientos_inventario", "prioridad_ot", "TEXT")
        _add_columna_segura(cursor, "movimientos_inventario", "estado_ot", "TEXT")
        _add_columna_segura(cursor, "movimientos_inventario", "fecha_creacion_ot", "TEXT")
        _add_columna_segura(cursor, "movimientos_inventario", "origen_ot", "TEXT")

        cursor.execute("UPDATE inventario SET activo = 1 WHERE activo IS NULL")
        cursor.execute("UPDATE inventario SET precio_unitario = 0 WHERE precio_unitario IS NULL")
        cursor.execute("UPDATE inventario SET coste_total = 0 WHERE coste_total IS NULL")

        conn.commit()

    except Exception:
        conn.rollback()

    finally:
        conn.close()

    _COLUMNAS_INVENTARIO_ASEGURADAS = True)


def actualizar_materiales_normalizados():
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    try:
        cursor.execute("""
            SELECT id, material
            FROM inventario
        """)

        filas = cursor.fetchall()

        for id_mat, material in filas:
            material_norm = normalizar_texto_material(material)

            cursor.execute(f"""
                UPDATE inventario
                SET material_normalizado = {p}
                WHERE id = {p}
            """, (material_norm, id_mat))

        conn.commit()

    except Exception:
        conn.rollback()

    finally:
        conn.close()


# =====================================================
# CÓDIGO MATERIAL
# =====================================================

def generar_codigo_material(material, categoria):
    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    texto_material = "".join(c for c in material.upper() if c.isalnum() or c == " ")
    partes = [x for x in texto_material.split() if x]
    base_material = "".join(x[:2] for x in partes[:2])[:4]

    if len(base_material) < 4:
        base_material = (base_material + "XXXX")[:4]

    base_categoria = "".join(c for c in categoria.upper() if c.isalpha())[:3]

    if len(base_categoria) < 3:
        base_categoria = (base_categoria + "XXX")[:3]

    prefijo = f"{base_categoria}-{base_material}"

    cursor.execute(
        f"SELECT codigo FROM inventario WHERE codigo LIKE {p}",
        (f"{prefijo}-%",)
    )

    existentes = [fila[0] for fila in cursor.fetchall()]
    conn.close()

    numeros = []

    for cod in existentes:
        try:
            numeros.append(int(cod.split("-")[-1]))
        except Exception:
            pass

    siguiente = max(numeros) + 1 if numeros else 1
    return f"{prefijo}-{siguiente:03d}"


# =====================================================
# CREAR MATERIAL
# =====================================================

def crear_material_inventario(
    codigo,
    material,
    categoria,
    unidad,
    stock_actual,
    stock_minimo,
    centro,
    edificio,
    ubicacion,
    proveedor,
    observaciones,
    foto="",
    foto_nombre="",
    foto_data=None,
    precio_unitario=0,
    coste_total=0,
    fecha_compra="",
    referencia_factura="",
    observaciones_coste=""
):
    asegurar_columnas_inventario()

    material = str(material or "").strip()
    categoria = str(categoria or "").strip()
    unidad = str(unidad or "").strip()

    duplicado = buscar_material_duplicado_exacto(material, categoria, unidad)

    if duplicado:
        return False, (
            f"Este material ya existe: "
            f"{duplicado['material']} | Código: {duplicado['codigo']} | "
            f"Stock actual: {duplicado['stock_actual']}"
        )

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    try:
        material_normalizado = normalizar_texto_material(material)

        cursor.execute(f"""
            INSERT INTO inventario
            (
                codigo,
                material,
                categoria,
                unidad,
                stock_actual,
                stock_minimo,
                centro,
                edificio,
                ubicacion,
                proveedor,
                observaciones,
                foto,
                foto_nombre,
                foto_data,
                activo,
                material_normalizado,
                precio_unitario,
                coste_total,
                fecha_compra,
                referencia_factura,
                observaciones_coste
            )
            VALUES (
                {p}, {p}, {p}, {p}, {p}, {p}, {p},
                {p}, {p}, {p}, {p}, {p}, {p}, {p},
                {p}, {p}, {p}, {p}, {p}, {p}, {p}
            )
        """, (
            codigo,
            material,
            categoria,
            unidad,
            float(stock_actual),
            float(stock_minimo),
            centro,
            edificio,
            str(ubicacion or "").strip(),
            str(proveedor or "").strip(),
            str(observaciones or "").strip(),
            foto,
            foto_nombre,
            foto_data,
            1,
            material_normalizado,
            float(precio_unitario or 0),
            float(coste_total or 0),
            str(fecha_compra or "").strip(),
            str(referencia_factura or "").strip(),
            str(observaciones_coste or "").strip()
        ))

        conn.commit()
        return True, "Material creado correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"Error al crear material: {e}"

    finally:
        conn.close()


# =====================================================
# OBTENER MATERIALES
# =====================================================

def obtener_materiales_inventario(
    filtro_texto="",
    filtro_categoria="Todas",
    filtro_centro="Todos",
    filtro_edificio="Todos",
    incluir_inactivos=False
):
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    sql = """
        SELECT id, codigo, material, categoria, unidad, stock_actual, stock_minimo,
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta,
               foto, foto_nombre, foto_data, activo,
               precio_unitario, coste_total, fecha_compra,
               referencia_factura, observaciones_coste
        FROM inventario
        WHERE 1=1
    """

    params = []

    if not incluir_inactivos:
        sql += " AND COALESCE(activo, 1) = 1"

    if filtro_texto.strip():
        sql += f" AND (codigo LIKE {p} OR material LIKE {p} OR ubicacion LIKE {p} OR proveedor LIKE {p})"
        txt = f"%{filtro_texto.strip()}%"
        params.extend([txt, txt, txt, txt])

    if filtro_categoria != "Todas":
        sql += f" AND categoria = {p}"
        params.append(filtro_categoria)

    if filtro_centro != "Todos":
        sql += f" AND centro = {p}"
        params.append(filtro_centro)

    if filtro_edificio != "Todos":
        sql += f" AND edificio = {p}"
        params.append(filtro_edificio)

    sql += " ORDER BY material ASC"

    cursor.execute(sql, params)
    datos = cursor.fetchall()
    conn.close()

    return datos


def obtener_codigos_materiales():
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT codigo, material
        FROM inventario
        WHERE COALESCE(activo, 1) = 1
        ORDER BY material ASC
    """)

    datos = cursor.fetchall()
    conn.close()

    return datos


# =====================================================
# MOVIMIENTOS
# =====================================================

def obtener_datos_ot_para_inventario(cursor, conn, numero_ot):
    datos_ot = {
        "descripcion_ot": "",
        "centro_ot": "",
        "edificio_ot": "",
        "espacio_ot": "",
        "area_ot": "",
        "prioridad_ot": "",
        "estado_ot": "",
        "fecha_creacion_ot": "",
        "origen_ot": "",
    }

    numero_ot = str(numero_ot or "").strip()

    if not numero_ot:
        return datos_ot

    p = _ph(conn)

    consultas = [
        """
        SELECT descripcion, centro, edificio, espacio, area, prioridad, estado, fecha_creacion, origen
        FROM ordenes_trabajo
        WHERE numero_ot = {p}
        """,
        """
        SELECT descripcion, centro, edificio, espacio, area, prioridad, estado, fecha_creacion, origen
        FROM historico_ordenes
        WHERE numero_ot = {p}
        """
    ]

    for consulta in consultas:
        try:
            cursor.execute(consulta.format(p=p), (numero_ot,))
            fila = cursor.fetchone()

            if fila:
                datos_ot["descripcion_ot"] = fila[0] or ""
                datos_ot["centro_ot"] = fila[1] or ""
                datos_ot["edificio_ot"] = fila[2] or ""
                datos_ot["espacio_ot"] = fila[3] or ""
                datos_ot["area_ot"] = fila[4] or ""
                datos_ot["prioridad_ot"] = fila[5] or ""
                datos_ot["estado_ot"] = fila[6] or ""
                datos_ot["fecha_creacion_ot"] = str(fila[7] or "")
                datos_ot["origen_ot"] = fila[8] or ""
                return datos_ot
        except Exception:
            pass

    return datos_ot


def registrar_movimiento_inventario(
    codigo_material,
    tipo_movimiento,
    cantidad,
    motivo,
    numero_ot,
    operario
):
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    try:
        cursor.execute(f"""
            SELECT material, stock_actual
            FROM inventario
            WHERE codigo = {p}
        """, (codigo_material,))

        fila = cursor.fetchone()

        if not fila:
            conn.close()
            return False, "No existe el material."

        material, stock_actual = fila
        cantidad = float(cantidad)
        stock_actual = float(stock_actual)

        nuevo_stock = stock_actual

        if tipo_movimiento == "Entrada":
            nuevo_stock = stock_actual + cantidad

        elif tipo_movimiento == "Salida":
            if stock_actual < cantidad:
                conn.close()
                return False, f"Stock insuficiente. Disponible: {stock_actual}"

            nuevo_stock = stock_actual - cantidad

        elif tipo_movimiento == "Ajuste":
            nuevo_stock = cantidad

        datos_ot = obtener_datos_ot_para_inventario(cursor, conn, numero_ot)

        cursor.execute(f"""
            UPDATE inventario
            SET stock_actual = {p}
            WHERE codigo = {p}
        """, (nuevo_stock, codigo_material))

        cursor.execute(f"""
            INSERT INTO movimientos_inventario
            (
                codigo_material,
                material,
                tipo_movimiento,
                cantidad,
                motivo,
                numero_ot,
                operario,
                descripcion_ot,
                centro_ot,
                edificio_ot,
                espacio_ot,
                area_ot,
                prioridad_ot,
                estado_ot,
                fecha_creacion_ot,
                origen_ot
            )
            VALUES (
                {p}, {p}, {p}, {p}, {p}, {p}, {p},
                {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}
            )
        """, (
            codigo_material,
            material,
            tipo_movimiento,
            cantidad,
            str(motivo or "").strip(),
            str(numero_ot or "").strip(),
            str(operario or "").strip(),
            datos_ot["descripcion_ot"],
            datos_ot["centro_ot"],
            datos_ot["edificio_ot"],
            datos_ot["espacio_ot"],
            datos_ot["area_ot"],
            datos_ot["prioridad_ot"],
            datos_ot["estado_ot"],
            datos_ot["fecha_creacion_ot"],
            datos_ot["origen_ot"]
        ))

        conn.commit()
        return True, "Movimiento registrado correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"Error al registrar movimiento: {e}"

    finally:
        conn.close()


def obtener_movimientos_inventario():
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, codigo_material, material, tipo_movimiento, cantidad,
               motivo, numero_ot, operario, fecha_movimiento,
               descripcion_ot, centro_ot, edificio_ot, espacio_ot,
               area_ot, prioridad_ot, estado_ot, fecha_creacion_ot, origen_ot
        FROM movimientos_inventario
        ORDER BY fecha_movimiento DESC, id DESC
    """)

    datos = cursor.fetchall()
    conn.close()

    return datos


def obtener_movimientos_por_material(codigo_material):
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    cursor.execute(f"""
        SELECT
            tipo_movimiento,
            cantidad,
            motivo,
            numero_ot,
            operario,
            fecha_movimiento,
            descripcion_ot,
            centro_ot,
            edificio_ot,
            espacio_ot,
            area_ot,
            prioridad_ot,
            estado_ot,
            fecha_creacion_ot,
            origen_ot
        FROM movimientos_inventario
        WHERE codigo_material = {p}
        ORDER BY fecha_movimiento DESC
    """, (codigo_material,))

    datos = cursor.fetchall()
    conn.close()

    return datos


# =====================================================
# STOCK / SELECTS
# =====================================================

def obtener_stock_bajo():
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, codigo, material, categoria, unidad, stock_actual, stock_minimo,
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta,
               foto, foto_nombre, foto_data, activo,
               precio_unitario, coste_total, fecha_compra,
               referencia_factura, observaciones_coste
        FROM inventario
        WHERE stock_actual <= stock_minimo
          AND COALESCE(activo, 1) = 1
        ORDER BY stock_actual ASC, material ASC
    """)

    datos = cursor.fetchall()
    conn.close()

    return datos


def obtener_materiales_para_select():
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT codigo, material, stock_actual, unidad
        FROM inventario
        WHERE COALESCE(activo, 1) = 1
        ORDER BY material ASC
    """)

    datos = cursor.fetchall()
    conn.close()

    return datos


def obtener_material_por_codigo(codigo):
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    cursor.execute(f"""
        SELECT id, codigo, material, categoria, unidad, stock_actual, stock_minimo,
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta,
               foto, foto_nombre, foto_data, activo,
               precio_unitario, coste_total, fecha_compra,
               referencia_factura, observaciones_coste
        FROM inventario
        WHERE codigo = {p}
    """, (codigo,))

    columnas = [desc[0] for desc in cursor.description]
    fila = cursor.fetchone()
    conn.close()

    if fila:
        return dict(zip(columnas, fila))

    return None


# =====================================================
# ACTIVAR / DESACTIVAR
# =====================================================

def desactivar_material(codigo):
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    cursor.execute(f"""
        UPDATE inventario
        SET activo = 0
        WHERE codigo = {p}
    """, (codigo,))

    conn.commit()
    conn.close()

    return True, "Material desactivado correctamente."


def activar_material(codigo):
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    cursor.execute(f"""
        UPDATE inventario
        SET activo = 1
        WHERE codigo = {p}
    """, (codigo,))

    conn.commit()
    conn.close()

    return True, "Material activado correctamente."
