import re
import unicodedata
from difflib import SequenceMatcher

from database.db import conectar
_COLUMNAS_INVENTARIO_ASEGURADAS = False


def _ph(conn):
    modulo = conn.__class__.__module__.lower()
    return "?" if "sqlite" in modulo else "%s"


def _log_inventario_warning(contexto, error):
    """
    Registra avisos internos del inventario en los logs.
    No interrumpe el funcionamiento de la aplicación.
    """
    try:
        print(
            f"[INVENTARIO WARNING] {contexto}: "
            f"{type(error).__name__}: {error}"
        )
    except Exception:
        pass


def _add_columna_segura(cursor, tabla, columna, tipo):
    try:
        cursor.execute(
            f"ALTER TABLE {tabla} "
            f"ADD COLUMN IF NOT EXISTS {columna} {tipo}"
        )
        return True

    except Exception:
        try:
            cursor.execute(
                f"ALTER TABLE {tabla} "
                f"ADD COLUMN {columna} {tipo}"
            )
            return True

        except Exception as e:
            _log_inventario_warning(
                f"Añadiendo columna {tabla}.{columna}",
                e
            )
            return False


# =====================================================
# NORMALIZACIÓN / DUPLICADOS
# =====================================================

PALABRAS_IGNORAR_MATERIAL = {
    "de", "del", "la", "el", "los", "las", "un", "una",
    "para", "por", "con", "sin", "y", "o"
}


CATEGORIAS_INVENTARIO_INTELIGENTE = [
    "Electricidad",
    "Iluminación",
    "Fontanería",
    "Climatización",
    "Cerrajería",
    "Mobiliario",
    "Equipamiento",
    "Ferretería",
    "Albañilería",
    "Pintura",
    "Limpieza",
    "Jardinería",
    "Seguridad",
    "Legionella",
    "Otros",
]


def categorias_inventario_disponibles():
    return list(CATEGORIAS_INVENTARIO_INTELIGENTE)


# Palabras con peso. Las palabras que identifican el TIPO de objeto
# tienen más peso que palabras de composición como hierro, acero o plástico.
_REGLAS_CATEGORIA_MATERIAL = {
    "Iluminación": {
        "downlight": 18,
        "foco": 14,
        "lampara": 14,
        "bombilla": 14,
        "led": 10,
        "fluorescente": 16,
        "driver": 15,
    },
    "Electricidad": {
        "interruptor": 18,
        "enchufe": 18,
        "base enchufe": 20,
        "magnetotermico": 20,
        "diferencial": 20,
        "contactor": 18,
        "rele": 16,
        "cable": 12,
        "manguera electrica": 16,
        "regleta": 14,
        "fuente alimentacion": 16,
        "transformador": 18,
        "sensor movimiento": 15,
    },
    "Fontanería": {
        "grifo": 20,
        "sifon": 20,
        "latiguillo": 20,
        "racor": 18,
        "tuberia": 18,
        "tubo agua": 18,
        "manguito": 16,
        "codo": 12,
        "te fontaneria": 16,
        "valvula": 13,
        "llave paso": 20,
        "fluxor": 20,
        "cisterna": 18,
        "desague": 18,
        "sumidero": 18,
        "junta grifo": 18,
        "aireador": 16,
    },
    "Climatización": {
        "aire acondicionado": 24,
        "split": 20,
        "fancoil": 20,
        "fan coil": 20,
        "termostato": 16,
        "filtro aire": 18,
        "conducto": 14,
        "rejilla climatizacion": 18,
        "compresor": 16,
        "gas refrigerante": 20,
        "bomba condensados": 20,
    },
    "Cerrajería": {
        "cerradura": 25,
        "bombin": 24,
        "cilindro cerradura": 25,
        "cerrojo": 24,
        "candado": 22,
        "bisagra": 20,
        "manilla": 20,
        "pomo": 16,
        "picaporte": 22,
        "pasador": 18,
        "muelle puerta": 18,
        "cierrapuertas": 22,
        "llave cerradura": 22,
    },
    "Mobiliario": {
        "mesa": 25,
        "silla": 25,
        "pupitre": 25,
        "armario": 24,
        "estanteria": 24,
        "taquilla": 22,
        "mueble": 22,
        "cajonera": 22,
        "banco": 16,
        "perchero": 20,
        "pizarra": 18,
        "papelera": 15,
        "taburete": 20,
    },
    "Equipamiento": {
        "pantalla proyeccion": 25,
        "pantalla de proyeccion": 25,
        "pantalla proyeccion motorizada": 28,
        "proyector": 24,
        "motor pantalla": 14,
        "equipamiento": 18,
    },
    "Ferretería": {
        "tornillo": 24,
        "tuerca": 24,
        "arandela": 24,
        "taco": 22,
        "broca": 22,
        "remache": 22,
        "brida": 18,
        "silicona": 18,
        "sellador": 18,
        "adhesivo": 14,
        "cinta americana": 18,
        "cinta aislante": 16,
        "abrazadera": 18,
        "muelle": 10,
        "cadena": 12,
    },
    "Albañilería": {
        "mortero": 24,
        "cemento": 24,
        "yeso": 22,
        "ladrillo": 22,
        "bloque hormigon": 22,
        "hormigon": 20,
        "rachola": 22,
        "baldosa": 22,
        "azulejo": 22,
        "masilla pared": 18,
        "lechada": 18,
        "arena": 12,
    },
    "Pintura": {
        "pintura": 25,
        "esmalte": 22,
        "imprimacion": 22,
        "rodillo": 20,
        "brocha": 20,
        "pincel": 18,
        "disolvente": 18,
        "aguarras": 18,
        "barniz": 20,
        "cubeta pintura": 16,
    },
    "Limpieza": {
        "detergente": 22,
        "desengrasante": 22,
        "lejia": 22,
        "limpiador": 18,
        "fregona": 20,
        "escoba": 20,
        "recogedor": 18,
        "bayeta": 18,
        "guante limpieza": 18,
        "bolsa basura": 20,
    },
    "Jardinería": {
        "manguera riego": 22,
        "aspersor": 22,
        "gotero": 20,
        "abono": 20,
        "tierra vegetal": 20,
        "pala jardin": 18,
        "tijera podar": 20,
        "semilla": 18,
        "maceta": 16,
    },
    "Seguridad": {
        "extintor": 25,
        "senal emergencia": 22,
        "señal emergencia": 22,
        "detector humo": 24,
        "pulsador alarma": 22,
        "sirena": 20,
        "botiquin": 20,
        "baliza": 16,
        "cinta balizamiento": 18,
    },
    "Legionella": {
        "reactivo dpd": 25,
        "dpd": 22,
        "fotometro": 22,
        "medidor cloro": 24,
        "cloro residual": 22,
        "termometro legionella": 25,
        "bote muestra": 18,
        "frasco muestra": 18,
    },
}


def sugerir_categoria_material(material, observaciones=""):
    """
    Sugiere una categoría sin imponerla.

    Devuelve:
        {
            "categoria": "Mobiliario",
            "confianza": 92,
            "motivos": ["mesa"],
            "puntuaciones": {...}
        }

    Filosofía:
    - pesa más el tipo de objeto que su material/composición;
    - 'mesa patas hierro' => Mobiliario, no Cerrajería;
    - 'cerradura taquilla' => Cerrajería, aunque aparezca 'taquilla';
    - si no hay evidencia suficiente => Otros.
    """
    texto = normalizar_texto_material(
        f"{material or ''} {observaciones or ''}"
    )

    if not texto:
        return {
            "categoria": "Otros",
            "confianza": 0,
            "motivos": [],
            "puntuaciones": {},
        }

    puntuaciones = {}
    motivos_por_categoria = {}

    for categoria, reglas in _REGLAS_CATEGORIA_MATERIAL.items():
        puntos = 0
        motivos = []

        for termino, peso in reglas.items():
            termino_norm = normalizar_texto_material(termino)

            if termino_norm and termino_norm in texto:
                puntos += int(peso)
                motivos.append(termino)

        if puntos > 0:
            puntuaciones[categoria] = puntos
            motivos_por_categoria[categoria] = motivos

    if not puntuaciones:
        return {
            "categoria": "Otros",
            "confianza": 20,
            "motivos": [],
            "puntuaciones": {},
        }

    ordenadas = sorted(
        puntuaciones.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    categoria_ganadora, puntos_ganador = ordenadas[0]
    segundo = ordenadas[1][1] if len(ordenadas) > 1 else 0

    # Confianza orientativa: combina fuerza y distancia al segundo.
    margen = max(puntos_ganador - segundo, 0)
    confianza = min(
        99,
        55 + min(puntos_ganador, 30) + min(margen, 14)
    )

    return {
        "categoria": categoria_ganadora,
        "confianza": int(confianza),
        "motivos": motivos_por_categoria.get(categoria_ganadora, []),
        "puntuaciones": puntuaciones,
    }


def prefijo_codigo_categoria(categoria):
    categoria_norm = normalizar_texto_material(categoria)

    equivalencias = {
        "electricidad": "ELECTRICIDAD",
        "iluminacion": "ILUMINACION",
        "fontaneria": "FONTANERIA",
        "climatizacion": "CLIMATIZACION",
        "cerrajeria": "CERRAJERIA",
        "mobiliario": "MOBILIARIO",
        "equipamiento": "EQUIPAMIENTO",
        "ferreteria": "FERRETERIA",
        "albanileria": "ALBANILERIA",
        "pintura": "PINTURA",
        "limpieza": "LIMPIEZA",
        "jardineria": "JARDINERIA",
        "seguridad": "SEGURIDAD",
        "legionella": "LEGIONELLA",
        "otros": "OTROS",
        "otro": "OTROS",
    }

    if categoria_norm in equivalencias:
        return equivalencias[categoria_norm]

    limpio = re.sub(
        r"[^A-Z0-9]+",
        "_",
        categoria_norm.upper(),
    ).strip("_")

    return limpio or "OTROS"


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



def terminos_busqueda_material(texto):
    """Normaliza la consulta y expande alias habituales del colegio."""
    texto_norm = normalizar_texto_material(texto)
    if not texto_norm:
        return []

    alias = {
        "p22": ["pearson", "22"],
        "p9": ["pearson", "9"],
    }

    terminos = []
    for termino in texto_norm.split():
        terminos.extend(alias.get(termino, [termino]))

    return list(dict.fromkeys(t for t in terminos if t))


def _texto_busqueda_fila_inventario(fila):
    """Une y normaliza todos los campos útiles para buscar."""
    indices = [1, 2, 3, 4, 7, 8, 9, 10, 11, 19, 20, 21]
    valores = []
    for indice in indices:
        try:
            valores.append(str(fila[indice] or ""))
        except Exception:
            pass
    return normalizar_texto_material(" ".join(valores))


def _termino_coincide_busqueda(termino, texto_fila):
    """Substring, prefijo y pequeño error tipográfico."""
    termino = normalizar_texto_material(termino)
    texto_fila = normalizar_texto_material(texto_fila)
    if not termino:
        return True

    if termino in texto_fila:
        return True

    tokens = [t for t in texto_fila.split() if t]

    for token in tokens:
        if len(termino) >= 2 and token.startswith(termino):
            return True

    if len(termino) >= 4:
        for token in tokens:
            if len(token) < 4 or token[0] != termino[0]:
                continue
            ratio = SequenceMatcher(None, termino, token).ratio()
            umbral = 0.78 if len(termino) >= 6 else 0.82
            if ratio >= umbral:
                return True

    return False


def _filtrar_filas_inventario_por_texto(filas, filtro_texto):
    """
    Todas las palabras deben coincidir, pero pueden estar repartidas entre
    material, código, categoría, centro, edificio, ubicación, proveedor y notas.
    """
    terminos = terminos_busqueda_material(filtro_texto)
    if not terminos:
        return list(filas)

    resultado = []
    for fila in filas:
        texto_fila = _texto_busqueda_fila_inventario(fila)
        if all(_termino_coincide_busqueda(t, texto_fila) for t in terminos):
            resultado.append(fila)
    return resultado


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

        # Índices de uso frecuente del módulo.
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_inv_material_norm "
            "ON inventario(material_normalizado)",
            "CREATE INDEX IF NOT EXISTS idx_inv_centro_categoria "
            "ON inventario(centro, categoria)",
            "CREATE INDEX IF NOT EXISTS idx_mov_inv_codigo_material "
            "ON movimientos_inventario(codigo_material)",
            "CREATE INDEX IF NOT EXISTS idx_mov_inv_numero_ot "
            "ON movimientos_inventario(numero_ot)",
        ]

        for sql_indice in indices:
            try:
                cursor.execute(sql_indice)
            except Exception as e:
                _log_inventario_warning(
                    f"Creando índice: {sql_indice}",
                    e
                )

        conn.commit()

    except Exception as e:
        conn.rollback()
        _log_inventario_warning(
            "Asegurando estructura de inventario",
            e
        )
        return

    finally:
        conn.close()

    _COLUMNAS_INVENTARIO_ASEGURADAS = True


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
    """
    Nuevos códigos legibles y estables por categoría.

    Ejemplos:
        ELECTRICIDAD-001
        CERRAJERIA-001
        MOBILIARIO-001

    No modifica códigos históricos existentes.
    """
    asegurar_columnas_inventario()

    prefijo = prefijo_codigo_categoria(categoria)

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    try:
        cursor.execute(
            f"""
            SELECT codigo
            FROM inventario
            WHERE UPPER(COALESCE(codigo, '')) LIKE {p}
            """,
            (f"{prefijo}-%",)
        )
        existentes = [
            str(fila[0] or "").strip().upper()
            for fila in cursor.fetchall()
        ]
    finally:
        conn.close()

    numeros = []

    for codigo in existentes:
        try:
            numeros.append(int(codigo.rsplit("-", 1)[-1]))
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
# ALTA AUTOMÁTICA DESDE PEDIDOS DE MATERIAL
# =====================================================

def obtener_o_crear_material_para_pedido(
    material,
    categoria,
    centro="",
    edificio="",
    precio_unitario=None,
    unidad="ud",
    numero_pedido="",
):
    """
    Deja preparado en Inventario un material que se va a comprar.

    - Si ya existe exactamente, reutiliza su código y conserva el stock.
    - Si no existe, crea la ficha con stock 0.
    - El precio es opcional y no bloquea el alta.
    - No registra una entrada de stock: eso ocurre al recibir físicamente.
    """
    material = str(material or "").strip()
    categoria = str(categoria or "").strip()
    centro = str(centro or "").strip()
    edificio = str(edificio or "").strip()
    unidad = str(unidad or "ud").strip() or "ud"

    if not material:
        return False, "", "Falta el nombre del material."

    if not categoria:
        return False, "", "Falta la categoría del material."

    precio = 0.0
    if precio_unitario not in (None, ""):
        try:
            precio = float(precio_unitario)
        except Exception:
            return False, "", "El precio unitario no es válido."
        if precio < 0:
            return False, "", "El precio unitario no puede ser negativo."

    duplicado = buscar_material_duplicado_exacto(
        material,
        categoria,
        unidad,
    )

    if duplicado:
        codigo = str(duplicado.get("codigo") or "").strip()
        if precio > 0 and codigo:
            conn = conectar()
            cursor = conn.cursor()
            p = _ph(conn)
            try:
                cursor.execute(f"""
                    UPDATE inventario
                    SET precio_unitario = {p}
                    WHERE codigo = {p}
                """, (precio, codigo))
                conn.commit()
            except Exception:
                conn.rollback()
            finally:
                conn.close()

        return True, codigo, "Material ya existente en Inventario."

    codigo = generar_codigo_material(material, categoria)

    observacion = "Alta automática desde pedido de material"
    if numero_pedido:
        observacion += f" {numero_pedido}"

    ok, mensaje = crear_material_inventario(
        codigo=codigo,
        material=material,
        categoria=categoria,
        unidad=unidad,
        stock_actual=0,
        stock_minimo=0,
        centro=centro,
        edificio=edificio,
        ubicacion="",
        proveedor="",
        observaciones=observacion,
        precio_unitario=precio,
        coste_total=0,
    )

    if ok:
        return True, codigo, "Material creado en Inventario con stock 0."

    # Protección ante una creación simultánea o un duplicado detectado
    # entre la comprobación y el INSERT.
    duplicado = buscar_material_duplicado_exacto(
        material,
        categoria,
        unidad,
    )
    if duplicado:
        return (
            True,
            str(duplicado.get("codigo") or "").strip(),
            "Material ya existente en Inventario.",
        )

    return False, "", mensaje


def actualizar_precio_material_desde_pedido(codigo, precio_unitario):
    """Actualiza el precio de un material cuando el dato está disponible."""
    codigo = str(codigo or "").strip()
    if not codigo or precio_unitario in (None, ""):
        return True

    try:
        precio = float(precio_unitario)
    except Exception:
        return False

    if precio < 0:
        return False

    asegurar_columnas_inventario()
    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)
    try:
        cursor.execute(f"""
            UPDATE inventario
            SET precio_unitario = {p}
            WHERE codigo = {p}
        """, (precio, codigo))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
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

    try:
        cursor.execute(sql, params)
        datos = cursor.fetchall()
    finally:
        conn.close()

    if filtro_texto.strip():
        datos = _filtrar_filas_inventario_por_texto(
            datos,
            filtro_texto,
        )

    return datos



def obtener_materiales_inventario_ligero(
    filtro_texto="",
    filtro_categoria="Todas",
    filtro_centro="Todos",
    filtro_edificio="Todos",
    incluir_inactivos=False
):
    """
    Listado ligero: misma búsqueda inteligente, sin descargar foto_data.
    """
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    sql = """
        SELECT id, codigo, material, categoria, unidad,
               stock_actual, stock_minimo,
               centro, edificio, ubicacion, proveedor,
               observaciones, fecha_alta,
               foto, foto_nombre,
               NULL AS foto_data,
               activo,
               precio_unitario, coste_total, fecha_compra,
               referencia_factura, observaciones_coste
        FROM inventario
        WHERE 1=1
    """

    params = []

    if not incluir_inactivos:
        sql += " AND COALESCE(activo, 1) = 1"

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

    try:
        cursor.execute(sql, params)
        datos = cursor.fetchall()
    finally:
        conn.close()

    if filtro_texto.strip():
        datos = _filtrar_filas_inventario_por_texto(
            datos,
            filtro_texto,
        )

    return datos



def obtener_foto_material(codigo):
    """
    Recupera la foto de un único material bajo demanda.

    Devuelve:
        {
            "foto": str,
            "foto_nombre": str,
            "foto_data": bytes | None
        }
    """
    asegurar_columnas_inventario()

    codigo = str(codigo or "").strip()

    if not codigo:
        return {
            "foto": "",
            "foto_nombre": "",
            "foto_data": None,
        }

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    try:
        cursor.execute(f"""
            SELECT foto, foto_nombre, foto_data
            FROM inventario
            WHERE codigo = {p}
        """, (codigo,))

        fila = cursor.fetchone()

        if not fila:
            return {
                "foto": "",
                "foto_nombre": "",
                "foto_data": None,
            }

        return {
            "foto": fila[0] or "",
            "foto_nombre": fila[1] or "",
            "foto_data": fila[2],
        }

    except Exception as e:
        _log_inventario_warning(
            f"Cargando foto del material {codigo}",
            e
        )

        return {
            "foto": "",
            "foto_nombre": "",
            "foto_data": None,
        }

    finally:
        conn.close()

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
        except Exception as e:
            _log_inventario_warning(
                f"Consultando datos de OT {numero_ot}",
                e
            )

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
# NORMALIZAR CÓDIGO MANUALMENTE
# =====================================================

def normalizar_codigo_material(codigo_actual, categoria):
    """
    Cambia manualmente un código antiguo al formato actual de su categoría.

    Actualiza en la misma transacción:
    - inventario.codigo
    - movimientos_inventario.codigo_material
    - pedidos_material_lineas.codigo_material, si existe

    No toca stock, cantidades, estados ni códigos de otros materiales.
    """
    asegurar_columnas_inventario()

    codigo_actual = str(codigo_actual or "").strip()
    categoria = str(categoria or "").strip()

    if not codigo_actual:
        return False, "", "Falta el código actual."

    if not categoria:
        return False, "", "Falta la categoría."

    prefijo = prefijo_codigo_categoria(categoria)

    # Si ya está en el formato vigente de esa categoría, no hacemos nada.
    if re.fullmatch(rf"{re.escape(prefijo)}-\d{{3}}", codigo_actual.upper()):
        return True, codigo_actual, "El código ya está normalizado."

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    try:
        cursor.execute(
            f"SELECT id FROM inventario WHERE codigo = {p}",
            (codigo_actual,)
        )
        if not cursor.fetchone():
            return False, "", "No existe el material que se quiere normalizar."

        cursor.execute(
            f"""
            SELECT codigo
            FROM inventario
            WHERE UPPER(COALESCE(codigo, '')) LIKE {p}
            """,
            (f"{prefijo}-%",)
        )
        existentes = [
            str(fila[0] or "").strip().upper()
            for fila in cursor.fetchall()
        ]

        numeros = []
        for codigo in existentes:
            try:
                numeros.append(int(codigo.rsplit("-", 1)[-1]))
            except Exception:
                pass

        siguiente = max(numeros) + 1 if numeros else 1
        nuevo_codigo = f"{prefijo}-{siguiente:03d}"

        cursor.execute(
            f"SELECT id FROM inventario WHERE codigo = {p}",
            (nuevo_codigo,)
        )
        if cursor.fetchone():
            return False, "", f"Ya existe el código {nuevo_codigo}."

        cursor.execute(
            f"UPDATE inventario SET codigo = {p} WHERE codigo = {p}",
            (nuevo_codigo, codigo_actual)
        )

        cursor.execute(
            f"""
            UPDATE movimientos_inventario
            SET codigo_material = {p}
            WHERE codigo_material = {p}
            """,
            (nuevo_codigo, codigo_actual)
        )

        # Los pedidos pueden conservar referencias al material. La tabla o la
        # columna pueden no existir en instalaciones antiguas; en ese caso no
        # bloqueamos la normalización del inventario.
        try:
            cursor.execute(
                f"""
                UPDATE pedidos_material_lineas
                SET codigo_material = {p}
                WHERE codigo_material = {p}
                """,
                (nuevo_codigo, codigo_actual)
            )
        except Exception as e:
            _log_inventario_warning(
                f"Actualizando código {codigo_actual} en pedidos_material_lineas",
                e
            )

        conn.commit()
        return True, nuevo_codigo, "Código normalizado correctamente."

    except Exception as e:
        conn.rollback()
        return False, "", f"Error al normalizar el código: {e}"

    finally:
        conn.close()


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


def actualizar_material_abel(
    codigo,
    material,
    categoria,
    ubicacion,
    proveedor,
    stock_minimo,
    precio_unitario,
    observaciones,
    foto_nombre=None,
    foto_data=None
):
    asegurar_columnas_inventario()

    conn = conectar()
    cursor = conn.cursor()
    p = _ph(conn)

    try:

        if foto_data is not None:

            cursor.execute(f"""
                UPDATE inventario
                SET
                    material = {p},
                    material_normalizado = {p},
                    categoria = {p},
                    ubicacion = {p},
                    proveedor = {p},
                    stock_minimo = {p},
                    precio_unitario = {p},
                    observaciones = {p},
                    foto_nombre = {p},
                    foto_data = {p}
                WHERE codigo = {p}
            """, (
                material,
                normalizar_texto_material(material),
                categoria,
                ubicacion,
                proveedor,
                float(stock_minimo or 0),
                float(precio_unitario or 0),
                observaciones,
                foto_nombre,
                foto_data,
                codigo
            ))

        else:

            cursor.execute(f"""
                UPDATE inventario
                SET
                    material = {p},
                    material_normalizado = {p},
                    categoria = {p},
                    ubicacion = {p},
                    proveedor = {p},
                    stock_minimo = {p},
                    precio_unitario = {p},
                    observaciones = {p}
                WHERE codigo = {p}
            """, (
                material,
                normalizar_texto_material(material),
                categoria,
                ubicacion,
                proveedor,
                float(stock_minimo or 0),
                float(precio_unitario or 0),
                observaciones,
                codigo
            ))

        conn.commit()
        return True, "Material actualizado correctamente."

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        conn.close()
