from database.db import conectar


def _ph(conn):
    modulo = conn.__class__.__module__.lower()
    return "?" if "sqlite" in modulo else "%s"


def asegurar_columnas_inventario():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS foto TEXT")
        conn.commit()
    except Exception:
        conn.rollback()

    try:
        cursor.execute("ALTER TABLE inventario ADD COLUMN IF NOT EXISTS activo INTEGER DEFAULT 1")
        conn.commit()
    except Exception:
        conn.rollback()

    try:
        cursor.execute("UPDATE inventario SET activo = 1 WHERE activo IS NULL")
        conn.commit()
    except Exception:
        conn.rollback()

    conn.close()


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
    foto=""
):
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

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
            activo
        )
        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
    """, (
        codigo,
        material.strip(),
        categoria,
        unidad,
        float(stock_actual),
        float(stock_minimo),
        centro,
        edificio,
        ubicacion.strip(),
        proveedor.strip(),
        observaciones.strip(),
        foto,
        1
    ))

    conn.commit()
    conn.close()


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
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta, foto, activo
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


def registrar_movimiento_inventario(
    codigo_material,
    tipo_movimiento,
    cantidad,
    motivo,
    numero_ot,
    operario
):
    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

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
            operario
        )
        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})
    """, (
        codigo_material,
        material,
        tipo_movimiento,
        cantidad,
        motivo.strip(),
        numero_ot.strip(),
        operario.strip()
    ))

    conn.commit()
    conn.close()

    return True, "Movimiento registrado correctamente."


def obtener_movimientos_inventario():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, codigo_material, material, tipo_movimiento, cantidad,
               motivo, numero_ot, operario, fecha_movimiento
        FROM movimientos_inventario
        ORDER BY fecha_movimiento DESC, id DESC
    """)

    datos = cursor.fetchall()
    conn.close()

    return datos


def obtener_stock_bajo():
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, codigo, material, categoria, unidad, stock_actual, stock_minimo,
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta, foto, activo
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
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta, foto, activo
        FROM inventario
        WHERE codigo = {p}
    """, (codigo,))

    fila = cursor.fetchone()
    conn.close()

    return fila


def obtener_movimientos_por_material(codigo_material):
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
            fecha_movimiento
        FROM movimientos_inventario
        WHERE codigo_material = {p}
        ORDER BY fecha_movimiento DESC
    """, (codigo_material,))

    datos = cursor.fetchall()
    conn.close()

    return datos


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
    

