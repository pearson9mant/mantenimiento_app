from database.db import conectar

def generar_codigo_material(material, categoria):
    texto_material = "".join(c for c in material.upper() if c.isalnum() or c == " ")
    partes = [p for p in texto_material.split() if p]
    base_material = "".join(p[:2] for p in partes[:2])[:4]
    if len(base_material) < 4:
        base_material = (base_material + "XXXX")[:4]

    base_categoria = "".join(c for c in categoria.upper() if c.isalpha())[:3]
    if len(base_categoria) < 3:
        base_categoria = (base_categoria + "XXX")[:3]

    prefijo = f"{base_categoria}-{base_material}"

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo FROM inventario WHERE codigo LIKE ?", (f"{prefijo}-%",))
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


def crear_material_inventario(codigo, material, categoria, unidad, stock_actual, stock_minimo,
                              centro, edificio, ubicacion, proveedor, observaciones):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO inventario
        (codigo, material, categoria, unidad, stock_actual, stock_minimo, centro, edificio, ubicacion, proveedor, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        observaciones.strip()
    ))

    conn.commit()
    conn.close()


def obtener_materiales_inventario(filtro_texto="", filtro_categoria="Todas", filtro_centro="Todos", filtro_edificio="Todos"):
    conn = conectar()
    cursor = conn.cursor()

    sql = """
        SELECT id, codigo, material, categoria, unidad, stock_actual, stock_minimo,
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta
        FROM inventario
        WHERE 1=1
    """
    params = []

    if filtro_texto.strip():
        sql += " AND (codigo LIKE ? OR material LIKE ? OR ubicacion LIKE ? OR proveedor LIKE ?)"
        txt = f"%{filtro_texto.strip()}%"
        params.extend([txt, txt, txt, txt])

    if filtro_categoria != "Todas":
        sql += " AND categoria = ?"
        params.append(filtro_categoria)

    if filtro_centro != "Todos":
        sql += " AND centro = ?"
        params.append(filtro_centro)

    if filtro_edificio != "Todos":
        sql += " AND edificio = ?"
        params.append(filtro_edificio)

    sql += " ORDER BY material ASC"

    cursor.execute(sql, params)
    datos = cursor.fetchall()
    conn.close()
    return datos


def obtener_codigos_materiales():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, material FROM inventario ORDER BY material ASC")
    datos = cursor.fetchall()
    conn.close()
    return datos


def registrar_movimiento_inventario(codigo_material, tipo_movimiento, cantidad, motivo, numero_ot, operario):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT material, stock_actual
        FROM inventario
        WHERE codigo = ?
    """, (codigo_material,))

    fila = cursor.fetchone()
    if not fila:
        conn.close()
        return False, "No existe el material."

    material, stock_actual = fila
    cantidad = float(cantidad)

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

    cursor.execute("""
        UPDATE inventario
        SET stock_actual = ?
        WHERE codigo = ?
    """, (nuevo_stock, codigo_material))

    cursor.execute("""
        INSERT INTO movimientos_inventario
        (codigo_material, material, tipo_movimiento, cantidad, motivo, numero_ot, operario)
        VALUES (?, ?, ?, ?, ?, ?, ?)
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
        SELECT id, codigo_material, material, tipo_movimiento, cantidad, motivo, numero_ot, operario, fecha_movimiento
        FROM movimientos_inventario
        ORDER BY fecha_movimiento DESC, id DESC
    """)

    datos = cursor.fetchall()
    conn.close()
    return datos


def obtener_stock_bajo():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, codigo, material, categoria, unidad, stock_actual, stock_minimo,
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta
        FROM inventario
        WHERE stock_actual <= stock_minimo
        ORDER BY stock_actual ASC, material ASC
    """)

    datos = cursor.fetchall()
    conn.close()
    return datos

def obtener_materiales_para_select():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT codigo, material, stock_actual, unidad
        FROM inventario
        ORDER BY material ASC
    """)

    datos = cursor.fetchall()
    conn.close()
    return datos


def obtener_material_por_codigo(codigo):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, codigo, material, categoria, unidad, stock_actual, stock_minimo,
               centro, edificio, ubicacion, proveedor, observaciones, fecha_alta
        FROM inventario
        WHERE codigo = ?
    """, (codigo,))

    fila = cursor.fetchone()
    conn.close()
    return fila

