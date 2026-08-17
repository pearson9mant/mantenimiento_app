from datetime import date
from difflib import SequenceMatcher
import pandas as pd

from database.db import conectar, _sql
from modules.inteligencia_preventivos import construir_panel_preventivo
from modules.inteligencia_legionella import construir_panel_sanitario_legionella


def _normalizar_ubicacion_corazon(valor):
    return (
        str(valor or "")
        .strip()
        .lower()
        .replace("edif.", "")
        .replace("edificio", "")
        .replace("infantil / primaria", "infantilprimaria")
        .replace("infantil/primaria", "infantilprimaria")
        .replace("·", "")
        .replace("/", "")
        .replace("\\", "")
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )


def _normalizar_espacio_corazon(valor):
    texto = _normalizar_ubicacion_corazon(valor)

    texto = (
        texto
        .replace("niñas", "chicas")
        .replace("ninas", "chicas")
        .replace("niños", "chicos")
        .replace("ninos", "chicos")
        .replace("profesores", "profes")
    )

    return texto


def cargar_indice_plantas_espacios(centro=None):
    """
    Lee una sola vez la tabla real `espacios` y construye un índice:

        (centro, edificio, espacio) -> planta

    Solo usa espacios activos y no modifica la base de datos.
    """
    params = []
    filtro = " WHERE activo = 1"

    if centro:
        filtro += " AND centro = ?"
        params.append(centro)

    df = leer_df_corazon(
        f"""
        SELECT centro, edificio, planta, espacio
        FROM espacios
        {filtro}
        """,
        tuple(params),
    )

    indice_exacto = {}
    indice_por_centro_espacio = {}
    filas_catalogo = []

    if df.empty:
        return {
            "exacto": indice_exacto,
            "centro_espacio": indice_por_centro_espacio,
            "filas": filas_catalogo,
        }

    for _, fila in df.iterrows():
        centro_txt = str(fila.get("centro") or "").strip()
        edificio_txt = str(fila.get("edificio") or "").strip()
        planta_txt = str(fila.get("planta") or "").strip()
        espacio_txt = str(fila.get("espacio") or "").strip()

        if not centro_txt or not planta_txt or not espacio_txt:
            continue

        if planta_txt.lower() in [
            "nan",
            "none",
            "null",
            "-",
            "sin planta",
        ]:
            continue

        clave_exacta = (
            _normalizar_ubicacion_corazon(centro_txt),
            _normalizar_ubicacion_corazon(edificio_txt),
            _normalizar_espacio_corazon(espacio_txt),
        )

        indice_exacto[clave_exacta] = planta_txt

        clave_reducida = (
            _normalizar_ubicacion_corazon(centro_txt),
            _normalizar_espacio_corazon(espacio_txt),
        )

        indice_por_centro_espacio.setdefault(
            clave_reducida,
            set(),
        ).add(planta_txt)

        filas_catalogo.append({
            "centro": centro_txt,
            "edificio": edificio_txt,
            "planta": planta_txt,
            "espacio": espacio_txt,
            "centro_norm": _normalizar_ubicacion_corazon(centro_txt),
            "edificio_norm": _normalizar_ubicacion_corazon(edificio_txt),
            "espacio_norm": _normalizar_espacio_corazon(espacio_txt),
        })

    return {
        "exacto": indice_exacto,
        "centro_espacio": indice_por_centro_espacio,
        "filas": filas_catalogo,
    }


def resolver_planta_corazon(
    centro,
    edificio,
    espacio,
    planta_actual,
    indice_plantas,
):
    """
    Respeta la planta existente. Si falta, busca en la tabla `espacios`.
    """
    planta_txt = str(planta_actual or "").strip()

    if planta_txt and planta_txt.lower() not in [
        "nan",
        "none",
        "null",
        "-",
        "sin planta",
    ]:
        return planta_txt

    centro_norm = _normalizar_ubicacion_corazon(centro)
    edificio_norm = _normalizar_ubicacion_corazon(edificio)
    espacio_norm = _normalizar_espacio_corazon(espacio)

    if not centro_norm or not espacio_norm:
        return "Sin planta"

    clave_exacta = (
        centro_norm,
        edificio_norm,
        espacio_norm,
    )

    planta = indice_plantas.get(
        "exacto",
        {},
    ).get(clave_exacta)

    if planta:
        return planta

    clave_reducida = (
        centro_norm,
        espacio_norm,
    )

    candidatas = indice_plantas.get(
        "centro_espacio",
        {},
    ).get(clave_reducida, set())

    if len(candidatas) == 1:
        return next(iter(candidatas))

    return "Sin planta"


ESTADOS_CIERRE = [
    "finalizada",
    "finalizado",
    "cerrada",
    "cerrado",
    "cancelada",
    "cancelado",
    "cerrado definitivo",
]


def leer_df_corazon(sql, params=()):
    conn = conectar()
    try:
        return pd.read_sql_query(_sql(sql), conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def normalizar(valor):
    return str(valor or "").strip().lower()


def normalizar_edificio(edificio):
    e = str(edificio or "").strip()

    if not e or e.lower() in ["nan", "none", "-", "sin edificio"]:
        return "Sin edificio"

    e_low = e.lower()
    e_low = e_low.replace(".", "")
    e_low = e_low.replace("edif", "")
    e_low = e_low.replace("edificio", "")
    e_low = e_low.replace(" ", "")
    e_low = e_low.replace("-", "")
    e_low = e_low.replace("_", "")

    if "infantil" in e_low or "primaria" in e_low:
        return "Edif. Infantil/Primaria"

    if "llar" in e_low:
        return "Edif. Llar (Anexo)"

    if e_low in ["a", "edifa"]:
        return "Edif. A"

    if e_low in ["b", "edifb"]:
        return "Edif. B"

    if e_low in ["c", "edifc"]:
        return "Edif. C"

    return e

# =====================================================
# HISTORIAL Y RECURRENCIA DEL ESPACIO
# =====================================================

def _texto_valido_corazon(valor):
    texto = str(valor or "").strip()
    return bool(
        texto
        and texto.lower() not in [
            "nan", "none", "null", "-", "sin espacio", "sin edificio"
        ]
    )


def _resultado_historial_vacio():
    return {
        "total": 0,
        "activas": 0,
        "historicas": 0,
        "misma_area": 0,
        "areas": {},
        "ultimas": [],
        "nivel_recurrencia": "Sin datos",
        "mensaje_recurrencia": (
            "No hay suficiente información para analizar este espacio."
        ),
        "es_recurrente": False,
    }


def _fecha_registro_corazon(fila):
    return (
        fila.get("fecha")
        or fila.get("fecha_creacion")
        or fila.get("fecha_alta")
        or ""
    )


def _clave_espacio_corazon(centro, edificio, espacio):
    centro_txt = str(centro or "").strip()
    edificio_txt = normalizar_edificio(edificio)
    espacio_txt = normalizar(espacio)

    if not centro_txt:
        return None
    if edificio_txt == "Sin edificio":
        return None
    if not _texto_valido_corazon(espacio):
        return None

    return centro_txt, edificio_txt, espacio_txt


def _crear_registro_corazon(fila, tipo):
    return {
        "tipo": tipo,
        "numero_ot": str(fila.get("numero_ot") or "").strip(),
        "fecha": _fecha_registro_corazon(fila),
        "area": str(fila.get("area") or "Otros"),
        "descripcion": str(fila.get("descripcion") or ""),
        "estado": str(fila.get("estado") or ""),
        "origen": str(fila.get("origen") or ""),
    }


def construir_indice_historial_corazon(df_activas, df_historico):
    """
    Construye una sola vez un índice:
    (centro, edificio normalizado, espacio normalizado) -> actuaciones.
    """
    indice = {}

    if df_activas is not None and not df_activas.empty:
        for _, fila in df_activas.iterrows():
            if normalizar(fila.get("estado")) in ESTADOS_CIERRE:
                continue

            clave = _clave_espacio_corazon(
                fila.get("centro"),
                fila.get("edificio"),
                fila.get("espacio"),
            )
            if clave is None:
                continue

            indice.setdefault(clave, []).append(
                _crear_registro_corazon(fila, "Activa")
            )

    if df_historico is not None and not df_historico.empty:
        for _, fila in df_historico.iterrows():
            clave = _clave_espacio_corazon(
                fila.get("centro"),
                fila.get("edificio"),
                fila.get("espacio"),
            )
            if clave is None:
                continue

            indice.setdefault(clave, []).append(
                _crear_registro_corazon(fila, "Histórico")
            )

    for registros in indice.values():
        for registro in registros:
            registro["_fecha_orden"] = pd.to_datetime(
                registro.get("fecha"),
                errors="coerce",
                dayfirst=True,
            )

        registros.sort(
            key=lambda item: (
                pd.notna(item.get("_fecha_orden")),
                item.get("_fecha_orden")
                if pd.notna(item.get("_fecha_orden"))
                else pd.Timestamp.min,
            ),
            reverse=True,
        )

    return indice


def cargar_indice_historial_corazon(centro=None):
    """
    Lee ordenes_trabajo e historico_ordenes una sola vez.
    """
    filtro = ""
    params = ()

    if centro:
        filtro = " WHERE centro = ?"
        params = (centro,)

    columnas = """
        numero_ot, fecha, fecha_creacion, fecha_alta,
        centro, edificio, espacio, area, descripcion,
        estado, origen
    """

    df_activas = leer_df_corazon(
        f"""
        SELECT {columnas}
        FROM ordenes_trabajo
        {filtro}
        """,
        params,
    )

    df_historico = leer_df_corazon(
        f"""
        SELECT {columnas}
        FROM historico_ordenes
        {filtro}
        """,
        params,
    )

    return construir_indice_historial_corazon(
        df_activas,
        df_historico,
    )


def _analizar_registros_espacio(
    registros,
    area=None,
    numero_ot_actual=None,
):
    resultado_vacio = _resultado_historial_vacio()
    area_objetivo = normalizar(area)
    numero_actual = str(numero_ot_actual or "").strip()

    registros_filtrados = [
        registro
        for registro in registros
        if not (
            numero_actual
            and str(registro.get("numero_ot") or "").strip() == numero_actual
        )
    ]

    if not registros_filtrados:
        resultado_vacio["nivel_recurrencia"] = "Sin recurrencia"
        resultado_vacio["mensaje_recurrencia"] = (
            "No constan actuaciones anteriores en este espacio."
        )
        return resultado_vacio

    total = len(registros_filtrados)
    activas = sum(
        1 for r in registros_filtrados if r.get("tipo") == "Activa"
    )
    historicas = sum(
        1 for r in registros_filtrados if r.get("tipo") == "Histórico"
    )

    areas = {}
    for registro in registros_filtrados:
        nombre_area = str(registro.get("area") or "Otros").strip()
        areas[nombre_area] = areas.get(nombre_area, 0) + 1

    misma_area = 0
    if area_objetivo:
        misma_area = sum(
            1
            for registro in registros_filtrados
            if normalizar(registro.get("area")) == area_objetivo
        )

    es_recurrente = False

    if total >= 10 or misma_area >= 6:
        nivel = "Muy alta"
        es_recurrente = True
        mensaje = f"Este espacio acumula {total} actuaciones anteriores"

        if misma_area:
            mensaje += (
                f", de las cuales {misma_area} pertenecen "
                f"al área de {area or 'mantenimiento'}."
            )
        else:
            mensaje += "."

        mensaje += (
            " Conviene valorar una revisión completa del espacio."
        )

    elif total >= 6 or misma_area >= 4:
        nivel = "Alta"
        es_recurrente = True
        mensaje = (
            f"Se observa una recurrencia alta: "
            f"{total} actuaciones anteriores"
        )

        if misma_area:
            mensaje += f" y {misma_area} del mismo área."
        else:
            mensaje += "."

    elif total >= 3 or misma_area >= 2:
        nivel = "Media"
        mensaje = f"Este espacio tiene {total} actuaciones anteriores"

        if misma_area:
            mensaje += (
                f", con {misma_area} relacionadas con "
                f"{area or 'esta área'}."
            )
        else:
            mensaje += "."

    else:
        nivel = "Baja"
        mensaje = (
            f"Solo consta {total} actuación anterior en este espacio."
            if total == 1
            else f"Constan {total} actuaciones anteriores en este espacio."
        )

    ultimas = []
    for registro in registros_filtrados[:5]:
        ultimas.append({
            "tipo": registro.get("tipo"),
            "numero_ot": registro.get("numero_ot"),
            "fecha": registro.get("fecha"),
            "area": registro.get("area"),
            "descripcion": registro.get("descripcion"),
            "estado": registro.get("estado"),
            "origen": registro.get("origen"),
        })

    return {
        "total": total,
        "activas": activas,
        "historicas": historicas,
        "misma_area": misma_area,
        "areas": areas,
        "ultimas": ultimas,
        "nivel_recurrencia": nivel,
        "mensaje_recurrencia": mensaje,
        "es_recurrente": es_recurrente,
    }


def obtener_historial_espacio_corazon(
    centro,
    edificio,
    espacio,
    area=None,
    numero_ot_actual=None,
    indice_historial=None,
):
    """
    Usa el índice en memoria cuando se proporciona.
    Mantiene compatibilidad si se llama sin índice.
    """
    clave = _clave_espacio_corazon(centro, edificio, espacio)

    if clave is None:
        return _resultado_historial_vacio()

    if indice_historial is None:
        indice_historial = cargar_indice_historial_corazon(
            str(centro or "").strip() or None
        )

    return _analizar_registros_espacio(
        registros=indice_historial.get(clave, []),
        area=area,
        numero_ot_actual=numero_ot_actual,
    )


def diagnosticar_planta_corazon(
    centro,
    edificio,
    espacio,
    planta_resuelta,
    indice_plantas,
):
    """
    Explica por qué no se pudo resolver la planta y propone
    coincidencias cercanas del catálogo real de espacios.
    """
    if normalizar_planta(planta_resuelta) != "Sin planta":
        return {
            "estado": "resuelta",
            "motivo": "",
            "sugerencias": [],
        }

    centro_norm = _normalizar_ubicacion_corazon(centro)
    edificio_norm = _normalizar_ubicacion_corazon(edificio)
    espacio_norm = _normalizar_espacio_corazon(espacio)

    if not espacio_norm:
        return {
            "estado": "sin_espacio",
            "motivo": "La OT no tiene espacio informado.",
            "sugerencias": [],
        }

    clave_reducida = (
        centro_norm,
        espacio_norm,
    )

    candidatas = indice_plantas.get(
        "centro_espacio",
        {},
    ).get(clave_reducida, set())

    if len(candidatas) > 1:
        return {
            "estado": "duplicado",
            "motivo": (
                "El mismo nombre de espacio aparece en varias plantas "
                "del centro."
            ),
            "sugerencias": sorted(candidatas),
        }

    sugerencias = []

    for fila in indice_plantas.get("filas", []):
        if fila.get("centro_norm") != centro_norm:
            continue

        puntuacion = SequenceMatcher(
            None,
            espacio_norm,
            fila.get("espacio_norm", ""),
        ).ratio()

        if fila.get("edificio_norm") == edificio_norm:
            puntuacion += 0.15

        if puntuacion >= 0.55:
            sugerencias.append({
                "puntuacion": puntuacion,
                "espacio": fila.get("espacio", ""),
                "edificio": fila.get("edificio", ""),
                "planta": fila.get("planta", ""),
            })

    sugerencias.sort(
        key=lambda item: item.get("puntuacion", 0),
        reverse=True,
    )

    sugerencias_limpias = []
    vistos = set()

    for sugerencia in sugerencias:
        clave = (
            sugerencia.get("espacio"),
            sugerencia.get("edificio"),
            sugerencia.get("planta"),
        )

        if clave in vistos:
            continue

        vistos.add(clave)
        sugerencias_limpias.append({
            "espacio": sugerencia.get("espacio", ""),
            "edificio": sugerencia.get("edificio", ""),
            "planta": sugerencia.get("planta", ""),
        })

        if len(sugerencias_limpias) >= 3:
            break

    if sugerencias_limpias:
        motivo = (
            "El nombre del espacio de la OT no coincide exactamente "
            "con el catálogo."
        )
    else:
        motivo = (
            "El espacio no está registrado en la tabla de espacios "
            "o no tiene una coincidencia reconocible."
        )

    return {
        "estado": "no_encontrada",
        "motivo": motivo,
        "sugerencias": sugerencias_limpias,
    }


def obtener_ordenes_abiertas_corazon(centro=None, operario=None):
    params = []
    filtro = ""

    if centro:
        filtro += " AND centro = ?"
        params.append(centro)

    if operario:
        filtro += " AND operario = ?"
        params.append(operario)

    df = leer_df_corazon(f"""
        SELECT *
        FROM ordenes_trabajo
        WHERE 1=1
        {filtro}
    """, tuple(params))

    if df.empty:
        return df

    estados = df["estado"].fillna("").astype(str).str.strip().str.lower()
    return df[~estados.isin(ESTADOS_CIERRE)].copy()


def calcular_tipo_prioridad(row):
    area = str(row.get("area", "") or "").lower()
    origen = str(row.get("origen", "") or "").lower()
    descripcion = str(row.get("descripcion", "") or "").lower()
    prioridad = str(row.get("prioridad", "") or "").lower()
    numero_ot = str(row.get("numero_ot", "") or "").strip().upper()

    if "legionella" in area or "legionella" in origen or "legionella" in descripcion:
        return "Sanitaria"

    if "urgente" in prioridad:
        return "Urgente"

    if "alta" in prioridad:
        return "Alta"

    # Una preventiva real se identifica por su numeración PREV.
    # Una INC nacida desde preventivo conserva el origen para trazabilidad,
    # pero sigue siendo una incidencia correctiva.
    if numero_ot.startswith("PREV-"):
        return "Preventiva"

    return "Incidencia"


# =====================================================
# DECISIÓN OPERATIVA DEL CORAZÓN
# =====================================================

# Personas cuya solicitud debe recibir un refuerzo operativo.
# Se puede ampliar sin tocar el algoritmo.
SOLICITANTES_DIRECCION_CORAZON = {
    "noemi",
    "noemí",
}

# Áreas que, a igualdad de prioridad, deben subir por impacto.
PESO_IMPACTO_AREA_CORAZON = {
    "agua": 12,
    "fontaneria": 12,
    "fontanería": 12,
    "electricidad": 10,
    "electrico": 10,
    "eléctrico": 10,
    "climatizacion": 8,
    "climatización": 8,
    "acs": 12,
    "legionella": 20,
}


def _peso_impacto_operativo_corazon(row):
    area = normalizar(row.get("area"))
    descripcion = normalizar(row.get("descripcion"))

    texto = f"{area} {descripcion}"

    mejor_peso = 0
    motivo = ""

    reglas = [
        (["legionella"], 20, "Riesgo sanitario."),
        (["fuga", "agua", "inund", "fontan"], 12, "Posible afectación por agua."),
        (["electr", "enchufe", "tension", "tensión", "cuadro"], 10, "Posible afectación eléctrica."),
        (["clima", "aire acondicionado", "calefaccion", "calefacción"], 8, "Afecta a climatización o confort."),
    ]

    for palabras, peso, texto_motivo in reglas:
        if any(palabra in texto for palabra in palabras) and peso > mejor_peso:
            mejor_peso = peso
            motivo = texto_motivo

    return mejor_peso, motivo


def _es_solicitud_direccion_corazon(row):
    solicitante = normalizar(row.get("solicitante"))

    if not solicitante:
        return False

    return any(
        nombre in solicitante
        for nombre in SOLICITANTES_DIRECCION_CORAZON
    )



def puntuar_orden(row):
    """
    Puntuación base del Corazón.

    Orden de decisión:
    1. Riesgo sanitario / urgencia explícita.
    2. Prioridad alta.
    3. Impacto operativo: agua, electricidad, climatización.
    4. Solicitud directa de dirección.
    5. Antigüedad.

    La concentración por planta se añade después, cuando todas las OT
    ya tienen la planta resuelta.
    """
    score = 0
    motivos = []
    dias = None

    area = normalizar(row.get("area"))
    origen = normalizar(row.get("origen"))
    prioridad = normalizar(row.get("prioridad"))
    descripcion = normalizar(row.get("descripcion"))
    numero_ot = normalizar(row.get("numero_ot"))

    es_preventiva_real = numero_ot.startswith("prev-")
    es_correctiva_desde_preventivo = (
        numero_ot.startswith("inc-")
        and origen == "preventivo"
    )

    # -------------------------------------------------
    # 1. PRIORIDAD PRINCIPAL
    # -------------------------------------------------
    if "legionella" in area or "legionella" in origen or "legionella" in descripcion:
        score += 95
        motivos.append("Riesgo sanitario / Legionella.")

    elif "urgente" in prioridad:
        score += 90
        motivos.append("Prioridad urgente.")

    elif "alta" in prioridad:
        score += 75
        motivos.append("Prioridad alta.")

    elif es_preventiva_real:
        score += 60
        motivos.append("Actuación preventiva pendiente.")

    elif es_correctiva_desde_preventivo:
        score += 55
        motivos.append(
            "Avería detectada durante mantenimiento preventivo."
        )

    elif origen in ["app", "outlook", "profesores", "externa"]:
        score += 55
        motivos.append("Incidencia o actuación externa abierta.")

    else:
        score += 40
        motivos.append("Orden abierta pendiente de gestión.")

    # -------------------------------------------------
    # 2. IMPACTO OPERATIVO
    # -------------------------------------------------
    peso_impacto, motivo_impacto = _peso_impacto_operativo_corazon(row)

    if peso_impacto:
        score += peso_impacto
        if motivo_impacto and motivo_impacto not in motivos:
            motivos.append(motivo_impacto)

    # -------------------------------------------------
    # 3. SOLICITUD DIRECTA DE DIRECCIÓN
    # No gana a una urgencia real, pero rompe empates y sube la OT.
    # -------------------------------------------------
    if _es_solicitud_direccion_corazon(row):
        score += 12
        motivos.append("Solicitud directa de dirección.")

    # -------------------------------------------------
    # 4. ANTIGÜEDAD
    # -------------------------------------------------
    fecha_txt = (
        row.get("fecha")
        or row.get("fecha_creacion")
        or row.get("fecha_alta")
        or ""
    )

    try:
        fecha_ot = pd.to_datetime(fecha_txt, errors="coerce")

        if pd.notna(fecha_ot):
            dias = (pd.Timestamp(date.today()) - fecha_ot).days

            if dias >= 90:
                score += 25
                motivos.append(f"Abierta desde hace {dias} días.")
            elif dias >= 60:
                score += 18
                motivos.append(f"Pendiente desde hace {dias} días.")
            elif dias >= 30:
                score += 12
                motivos.append(f"Más de un mes abierta ({dias} días).")
            elif dias >= 15:
                score += 6
                motivos.append(f"{dias} días sin resolver.")

    except Exception:
        pass

    score = min(score, 100)

    return score, motivos, dias




def _bonus_continuidad_ubicacion_corazon(
    prioridad_item,
    ubicacion_preferida=None,
):
    """
    Favorece continuar cerca de donde ya está el operario.

    Es un bonus pequeño: nunca debe imponerse a una urgencia,
    una sanitaria o una prioridad claramente superior.
    """
    if not ubicacion_preferida:
        return 0, ""

    centro_actual = _normalizar_ubicacion_corazon(
        ubicacion_preferida.get("centro")
    )
    edificio_actual = _normalizar_ubicacion_corazon(
        ubicacion_preferida.get("edificio")
    )
    planta_actual = normalizar_planta(
        ubicacion_preferida.get("planta")
    )

    centro_ot = _normalizar_ubicacion_corazon(
        prioridad_item.get("centro")
    )
    edificio_ot = _normalizar_ubicacion_corazon(
        prioridad_item.get("edificio")
    )
    planta_ot = normalizar_planta(
        prioridad_item.get("planta")
    )

    if (
        centro_actual
        and centro_ot == centro_actual
        and edificio_actual
        and edificio_ot == edificio_actual
        and planta_actual != "Sin planta"
        and planta_ot == planta_actual
    ):
        return 7, "Aprovecha que ya estás trabajando en esta planta."

    if (
        centro_actual
        and centro_ot == centro_actual
        and edificio_actual
        and edificio_ot == edificio_actual
    ):
        return 3, "Aprovecha que ya estás en este edificio."

    return 0, ""



def evaluar_ejecutabilidad_corazon(item):
    """
    Determina si una OT puede ejecutarse ahora.
    No cambia estados ni toma decisiones por el operario.
    """
    estado = normalizar(item.get("estado"))

    if estado in ESTADOS_BLOQUEADOS_CORAZON:
        motivos = {
            "pendiente material": "Está pendiente de material.",
            "pendiente proveedor": "Está pendiente de proveedor.",
            "pendiente presupuesto": "Está pendiente de presupuesto.",
            "avisado": "Está avisada y pendiente de siguiente actuación.",
        }

        return {
            "ejecutable": False,
            "bloqueada": True,
            "motivo_bloqueo": motivos.get(
                estado,
                "La OT está temporalmente bloqueada.",
            ),
        }

    if estado in ESTADOS_CIERRE:
        return {
            "ejecutable": False,
            "bloqueada": True,
            "motivo_bloqueo": "La OT ya está cerrada.",
        }

    return {
        "ejecutable": True,
        "bloqueada": False,
        "motivo_bloqueo": "",
    }


def clasificar_capa_decision_corazon(item):
    """
    Traduce la prioridad técnica a una capa operativa.

    CRITICO / HAZLO_AHORA / SIGUIENTE / APROVECHA /
    PUEDE_ESPERAR / EN_ESPERA.
    """
    ejecucion = evaluar_ejecutabilidad_corazon(item)

    if not ejecucion["ejecutable"]:
        return {
            "codigo": "EN_ESPERA",
            "etiqueta": "⏳ EN ESPERA",
            "mensaje": ejecucion["motivo_bloqueo"],
            **ejecucion,
        }

    score = int(item.get("score", 0) or 0)
    tipo = str(item.get("tipo_prioridad") or "").strip()
    prioridad = normalizar(item.get("prioridad"))
    bonus_ubicacion = int(item.get("bonus_ubicacion", 0) or 0)

    if tipo == "Sanitaria" or prioridad == "urgente" or score >= 90:
        return {
            "codigo": "CRITICO",
            "etiqueta": "🚨 CRÍTICO",
            "mensaje": "Puede interrumpir la ruta normal por riesgo o prioridad.",
            **ejecucion,
        }

    if score >= 70 or prioridad == "alta":
        return {
            "codigo": "HAZLO_AHORA",
            "etiqueta": "❤️ HAZLO AHORA",
            "mensaje": "Es una de las actuaciones ejecutables más importantes.",
            **ejecucion,
        }

    if bonus_ubicacion > 0:
        return {
            "codigo": "APROVECHA",
            "etiqueta": "📍 APROVECHA",
            "mensaje": "No es crítica, pero conviene resolverla por proximidad.",
            **ejecucion,
        }

    if score >= 55:
        return {
            "codigo": "SIGUIENTE",
            "etiqueta": "➡️ SIGUIENTE",
            "mensaje": "Conviene mantenerla entre las próximas actuaciones.",
            **ejecucion,
        }

    return {
        "codigo": "PUEDE_ESPERAR",
        "etiqueta": "🟢 PUEDE ESPERAR",
        "mensaje": "Puede permanecer en cola mientras haya actuaciones de mayor impacto.",
        **ejecucion,
    }


def construir_prioridades_globales(
    centro=None,
    operario=None,
    limite=100,
    df_ordenes_abiertas=None,
    ubicacion_preferida=None,
):
    """
    Mantiene el mismo comportamiento, pero evita consultar el historial
    dos veces por cada OT.
    """
    if df_ordenes_abiertas is None:
        df = obtener_ordenes_abiertas_corazon(centro, operario)
    else:
        df = df_ordenes_abiertas

    if df.empty:
        return []

    indice_historial = cargar_indice_historial_corazon(centro)
    indice_plantas = cargar_indice_plantas_espacios(centro)
    cache_plantas = {}
    prioridades = []

    for _, row in df.iterrows():
        score, motivos, dias_abierta = puntuar_orden(row)

        edificio_original = row.get("edificio", "")
        edificio_normalizado = normalizar_edificio(
            edificio_original
        )

        centro_ot = row.get("centro", "")
        espacio_ot = row.get("espacio", "")
        planta_original = row.get("planta", "")

        clave_planta = (
            str(centro_ot or "").strip(),
            str(edificio_original or "").strip(),
            str(espacio_ot or "").strip(),
            str(planta_original or "").strip(),
        )

        if clave_planta in cache_plantas:
            planta_resuelta = cache_plantas[clave_planta]
        else:
            try:
                planta_resuelta = resolver_planta_corazon(
                    centro=centro_ot,
                    edificio=edificio_original,
                    espacio=espacio_ot,
                    planta_actual=planta_original,
                    indice_plantas=indice_plantas,
                )
            except Exception:
                planta_resuelta = (
                    str(planta_original or "").strip()
                    or "Sin planta"
                )

            cache_plantas[clave_planta] = planta_resuelta

        diagnostico_planta = diagnosticar_planta_corazon(
            centro=centro_ot,
            edificio=edificio_original,
            espacio=espacio_ot,
            planta_resuelta=planta_resuelta,
            indice_plantas=indice_plantas,
        )

        historial_espacio = obtener_historial_espacio_corazon(
            centro=row.get("centro", ""),
            edificio=row.get("edificio", ""),
            espacio=row.get("espacio", ""),
            area=row.get("area", ""),
            numero_ot_actual=row.get("numero_ot", ""),
            indice_historial=indice_historial,
        )

        total_historial = historial_espacio.get("total", 0)
        misma_area = historial_espacio.get("misma_area", 0)

        if historial_espacio.get("es_recurrente"):
            incremento_recurrencia = min(
                15,
                5 + misma_area
            )

            score = min(
                100,
                score + incremento_recurrencia
            )

            motivos.append(
                historial_espacio.get(
                    "mensaje_recurrencia",
                    "El espacio presenta averías recurrentes."
                )
            )

        elif total_historial >= 3:
            score = min(100, score + 3)

            motivos.append(
                f"El espacio acumula "
                f"{total_historial} actuaciones anteriores."
            )

        prioridades.append({
            "score": score,
            "tipo_prioridad": calcular_tipo_prioridad(row),
            "numero_ot": row.get("numero_ot", ""),
            "titulo": row.get("descripcion", ""),
            "centro": row.get("centro", ""),
            "edificio": edificio_normalizado,
            "edificio_original": edificio_original,
            "planta": planta_resuelta,
            "planta_original": planta_original,
            "diagnostico_planta": diagnostico_planta,
            "espacio": espacio_ot,
            "area": row.get("area", ""),
            "origen": row.get("origen", ""),
            "prioridad": row.get("prioridad", ""),
            "operario": row.get("operario", ""),
            "estado": row.get("estado", ""),
            "dias_abierta": dias_abierta,
            "accion": "Atender esta actuación antes que el resto.",
            "motivo": "El sistema la considera prioritaria por origen, área, prioridad y riesgo operativo.",
            "motivos": motivos,
            "historial_espacio": historial_espacio,
            "recurrencia": historial_espacio.get(
                "nivel_recurrencia",
                "Sin datos"
            ),
            "actuaciones_espacio": historial_espacio.get(
                "total",
                0
            ),
            "actuaciones_misma_area": historial_espacio.get(
                "misma_area",
                0
            ),
        })

    # =================================================
    # BONUS DE CONCENTRACIÓN POR PLANTA
    # =================================================
    # A igualdad razonable de riesgo, el Corazón favorece terminar
    # varias actuaciones cercanas y evita desplazamientos innecesarios.
    concentracion = {}

    for prioridad_item in prioridades:
        clave_zona = (
            prioridad_item.get("centro", "") or "",
            prioridad_item.get("edificio", "") or "",
            prioridad_item.get("planta", "") or "",
        )

        if clave_zona[2] and clave_zona[2] != "Sin planta":
            concentracion[clave_zona] = (
                concentracion.get(clave_zona, 0) + 1
            )

    for prioridad_item in prioridades:
        clave_zona = (
            prioridad_item.get("centro", "") or "",
            prioridad_item.get("edificio", "") or "",
            prioridad_item.get("planta", "") or "",
        )

        cantidad_zona = concentracion.get(clave_zona, 0)

        if cantidad_zona >= 5:
            bonus_zona = 8
        elif cantidad_zona >= 3:
            bonus_zona = 5
        elif cantidad_zona == 2:
            bonus_zona = 2
        else:
            bonus_zona = 0

        if bonus_zona:
            prioridad_item["score"] = min(
                100,
                int(prioridad_item.get("score", 0) or 0) + bonus_zona,
            )

            prioridad_item.setdefault(
                "motivos",
                [],
            ).append(
                f"Hay {cantidad_zona} actuaciones ejecutables en esta planta."
            )

            prioridad_item["concentracion_planta"] = cantidad_zona
        else:
            prioridad_item["concentracion_planta"] = cantidad_zona

    # =================================================
    # CONTINUIDAD DE UBICACIÓN
    # =================================================
    # Si el operario ya está en una planta, intentamos resolver otra OT
    # cercana siempre que no exista algo claramente más importante.
    for prioridad_item in prioridades:
        bonus_ubicacion, motivo_ubicacion = (
            _bonus_continuidad_ubicacion_corazon(
                prioridad_item,
                ubicacion_preferida=ubicacion_preferida,
            )
        )

        if bonus_ubicacion:
            prioridad_item["score"] = min(
                100,
                int(prioridad_item.get("score", 0) or 0)
                + bonus_ubicacion,
            )
            prioridad_item["bonus_ubicacion"] = bonus_ubicacion

            if motivo_ubicacion:
                prioridad_item.setdefault(
                    "motivos",
                    [],
                ).append(motivo_ubicacion)
        else:
            prioridad_item["bonus_ubicacion"] = 0

    prioridades.sort(
        key=lambda x: (
            x.get("score", 0),
            1 if normalizar(x.get("prioridad")) == "urgente" else 0,
            x.get("concentracion_planta", 0),
            x.get("dias_abierta") or 0,
        ),
        reverse=True,
    )

    # FASE 1 · CAPA OPERATIVA
    for indice, prioridad_item in enumerate(prioridades):
        capa = clasificar_capa_decision_corazon(prioridad_item)

        if (
            indice == 0
            and capa.get("ejecutable")
            and capa.get("codigo") not in ["CRITICO", "EN_ESPERA"]
        ):
            capa["codigo"] = "HAZLO_AHORA"
            capa["etiqueta"] = "❤️ HAZLO AHORA"
            capa["mensaje"] = "Es la mejor actuación ejecutable según el Corazón."

        prioridad_item["capa_decision_corazon"] = capa
        prioridad_item["ejecutable_corazon"] = bool(capa.get("ejecutable"))
        prioridad_item["bloqueada_corazon"] = bool(capa.get("bloqueada"))
        prioridad_item["motivo_bloqueo_corazon"] = str(
            capa.get("motivo_bloqueo") or ""
        )

    return prioridades[:limite]


def normalizar_planta(planta):
    planta_txt = str(planta or "").strip()

    if not planta_txt or planta_txt.lower() in [
        "nan",
        "none",
        "null",
        "-",
        "sin planta",
    ]:
        return "Sin planta"

    return planta_txt


def construir_grupos_inteligentes(prioridades):
    """
    Agrupa las actuaciones por:
    centro -> edificio -> planta.

    No modifica puntuaciones ni prioridades. Solo organiza la ruta
    según la forma real de trabajo del operario.
    """
    grupos = {}

    for p in prioridades:
        centro = p.get("centro", "") or "Sin centro"
        edificio = normalizar_edificio(
            p.get("edificio", "")
        )
        planta = normalizar_planta(
            p.get("planta", "")
        )

        clave = (
            centro,
            edificio,
            planta,
        )

        grupos.setdefault(clave, []).append(p)

    resultado = []

    for (centro, edificio, planta), lista in grupos.items():
        score = max(
            x.get("score", 0)
            for x in lista
        )

        trabajos_ordenados = sorted(
            lista,
            key=lambda x: x.get("score", 0),
            reverse=True,
        )

        resultado.append({
            "centro": centro,
            "edificio": edificio,
            "planta": planta,
            "cantidad": len(trabajos_ordenados),
            "score": score,
            "trabajos": trabajos_ordenados,
            "primera_ot": (
                trabajos_ordenados[0]
                if trabajos_ordenados
                else None
            ),
        })

    resultado.sort(
        key=lambda x: (
            x["score"],
            x["cantidad"],
        ),
        reverse=True,
    )

    return resultado


def construir_ruta_inteligente(grupos, limite=10):
    """
    Construye una ruta por planta.

    Cada tramo representa una única planta dentro de un edificio.
    """
    ruta = []

    for g in grupos[:limite]:
        trabajos = g.get("trabajos", [])

        tipos = {}

        for t in trabajos:
            tipo = t.get(
                "tipo_prioridad",
                "Otros"
            )

            tipos[tipo] = (
                tipos.get(tipo, 0) + 1
            )

        centro = (
            g.get("centro", "")
            or "Sin centro"
        )

        edificio = (
            g.get("edificio", "")
            or "Sin edificio"
        )

        planta = (
            g.get("planta", "")
            or "Sin planta"
        )

        cantidad = g.get(
            "cantidad",
            0
        )

        primera_ot = g.get(
            "primera_ot"
        )

        if planta == "Sin planta":
            mensaje = (
                f"Hay {cantidad} actuaciones sin planta informada "
                f"en {edificio}. Conviene completar este dato para "
                "optimizar correctamente la ruta."
            )
        else:
            mensaje = (
                f"Conviene comenzar por {planta} de {edificio}. "
                f"Esta zona reúne {cantidad} actuaciones y una "
                f"prioridad máxima de {g.get('score', 0)}/100."
            )

        ruta.append({
            "centro": centro,
            "edificio": edificio,
            "planta": planta,
            "cantidad": cantidad,
            "score": g.get("score", 0),
            "tipos": tipos,
            "trabajos": trabajos,
            "primera_ot": primera_ot,
            "numero_ot_recomendada": (
                primera_ot.get("numero_ot", "")
                if primera_ot
                else ""
            ),
            "titulo_ot_recomendada": (
                primera_ot.get("titulo", "")
                if primera_ot
                else ""
            ),
            "mensaje": mensaje,
        })

    return ruta


def construir_carga_por_edificio(prioridades):
    edificios = {}

    for p in prioridades:
        centro = p.get("centro", "") or "Sin centro"
        edificio = normalizar_edificio(p.get("edificio", "")) or "Sin edificio"
        clave = (centro, edificio)

        if clave not in edificios:
            edificios[clave] = {
                "centro": centro,
                "edificio": edificio,
                "total": 0,
                "score_max": 0,
                "sanitarias": 0,
                "preventivas": 0,
                "incidencias": 0,
                "urgentes": 0,
            }

        edificios[clave]["total"] += 1
        edificios[clave]["score_max"] = max(
            edificios[clave]["score_max"],
            p.get("score", 0)
        )

        tipo = p.get("tipo_prioridad", "")

        if tipo == "Sanitaria":
            edificios[clave]["sanitarias"] += 1
        elif tipo == "Preventiva":
            edificios[clave]["preventivas"] += 1
        elif tipo in ["Urgente", "Alta"]:
            edificios[clave]["urgentes"] += 1
        else:
            edificios[clave]["incidencias"] += 1

    resultado = list(edificios.values())

    for e in resultado:
        score = 100
        score -= e["total"] * 3
        score -= e["sanitarias"] * 8
        score -= e["urgentes"] * 6
        score = max(0, min(100, score))

        e["salud"] = score

        if score >= 85:
            e["estado"] = "Controlado"
            e["color"] = "verde"
        elif score >= 60:
            e["estado"] = "Seguimiento"
            e["color"] = "amarillo"
        else:
            e["estado"] = "Carga alta"
            e["color"] = "rojo"

    resultado.sort(key=lambda x: (x["salud"], -x["total"]))
    return resultado


def detectar_datos_incompletos(prioridades):
    avisos = []

    for p in prioridades:
        edificio = normalizar_edificio(p.get("edificio", ""))
        espacio = str(p.get("espacio", "") or "").strip()
        planta = normalizar_planta(p.get("planta", ""))

        if edificio == "Sin edificio":
            avisos.append({
                "numero_ot": p.get("numero_ot", ""),
                "titulo": p.get("titulo", ""),
                "centro": p.get("centro", ""),
                "edificio": p.get("edificio_original", ""),
                "espacio": espacio,
                "campo": "edificio",
                "mensaje": "Esta OT no tiene edificio informado.",
                "sugerencias": [],
            })

        if not espacio or espacio.lower() in ["nan", "none", "-"]:
            avisos.append({
                "numero_ot": p.get("numero_ot", ""),
                "titulo": p.get("titulo", ""),
                "centro": p.get("centro", ""),
                "edificio": p.get("edificio_original", ""),
                "espacio": espacio,
                "campo": "espacio",
                "mensaje": "Esta OT no tiene espacio informado.",
                "sugerencias": [],
            })

        if planta == "Sin planta":
            diagnostico = p.get("diagnostico_planta", {}) or {}

            avisos.append({
                "numero_ot": p.get("numero_ot", ""),
                "titulo": p.get("titulo", ""),
                "centro": p.get("centro", ""),
                "edificio": p.get("edificio_original", ""),
                "espacio": espacio,
                "campo": "planta",
                "mensaje": diagnostico.get(
                    "motivo",
                    "No se ha podido determinar la planta de esta OT."
                ),
                "estado_diagnostico": diagnostico.get(
                    "estado",
                    "no_encontrada"
                ),
                "sugerencias": diagnostico.get(
                    "sugerencias",
                    []
                ),
            })

    return avisos



def diagnosticar_corazon_sistema(centro=None, operario=None):
    df = obtener_ordenes_abiertas_corazon(centro, operario)

    abiertas = len(df) if not df.empty else 0
    incidencias = 0
    preventivos = 0
    legionella = 0
    urgentes = 0

    if not df.empty:
        origen = df["origen"].fillna("").astype(str).str.upper()
        area = df["area"].fillna("").astype(str).str.lower()
        prioridad = df["prioridad"].fillna("").astype(str).str.lower()
        descripcion = df["descripcion"].fillna("").astype(str).str.lower()

        preventivos = len(df[origen == "PREVENTIVO"])

        legionella = len(df[
            (origen == "LEGIONELLA")
            | (area == "legionella")
            | (descripcion.str.contains("legionella", na=False))
        ])

        incidencias = len(df[
            origen.isin(["APP", "OUTLOOK", "PROFESORES", "EXTERNA"])
        ])

        urgentes = len(df[
            prioridad.str.contains("urgente|alta", case=False, na=False)
        ])

    try:
        preventivo = construir_panel_preventivo(centro)
        score_preventivo = preventivo.get("resumen", {}).get("score", 100)
    except Exception:
        preventivo = {}
        score_preventivo = 100

    try:
        legionella_panel = construir_panel_sanitario_legionella(centro)
        score_legionella = legionella_panel.get("resumen", {}).get("score", 100)
    except Exception:
        legionella_panel = {}
        score_legionella = 100

    score_operativo = 100
    score_operativo -= abiertas * 2
    score_operativo -= urgentes * 8
    score_operativo -= legionella * 8
    score_operativo -= preventivos * 2
    score_operativo = max(0, min(100, score_operativo))

    score_global = round(
        (score_operativo + score_preventivo + score_legionella) / 3
    )

    if score_global < 60:
        color = "rojo"
        estado = "Atención prioritaria"
        mensaje = "El colegio requiere actuar sobre trabajos críticos antes de considerar la situación estable."
    elif score_global < 85:
        color = "amarillo"
        estado = "Seguimiento operativo"
        mensaje = "El colegio está operativo, pero conviene reducir carga pendiente y cerrar actuaciones prioritarias."
    else:
        color = "verde"
        estado = "Colegio bajo control"
        mensaje = "La situación general es estable. Mantener ritmo de cierre y seguimiento."

    prioridades = construir_prioridades_globales(
        centro=centro,
        operario=operario,
        limite=100,
        df_ordenes_abiertas=df,
    )
    grupos = construir_grupos_inteligentes(prioridades)
    ruta = construir_ruta_inteligente(grupos)
    carga_edificios = construir_carga_por_edificio(prioridades)
    datos_incompletos = detectar_datos_incompletos(prioridades)

    prioridad_hoy = prioridades[0] if prioridades else None

    return {
        "fecha": str(date.today()),
        "centro": centro or "Todos",
        "operario": operario or "Todos",
        "score_global": score_global,
        "score_operativo": score_operativo,
        "score_preventivo": score_preventivo,
        "score_legionella": score_legionella,
        "color": color,
        "estado": estado,
        "mensaje": mensaje,
        "kpis": {
            "abiertas": abiertas,
            "incidencias": incidencias,
            "preventivos": preventivos,
            "legionella": legionella,
            "urgentes": urgentes,
        },
        "prioridad_hoy": prioridad_hoy,
        "prioridades": prioridades,
        "preventivo": preventivo,
        "legionella": legionella_panel,
        "grupos": grupos,
        "ruta": ruta,
        "carga_edificios": carga_edificios,
        "datos_incompletos": datos_incompletos,
    }

# =====================================================
# MISIÓN ACTUAL · CORAZÓN 4.0
# =====================================================

ESTADOS_BLOQUEADOS_CORAZON = {
    "pendiente material",
    "pendiente proveedor",
    "pendiente presupuesto",
    "avisado",
}

ESTADOS_EJECUTABLES_CORAZON = {
    "abierta",
    "en pausa",
    "en curso",
    "en ejecución",
}


def _fila_corazon_a_dict(row):
    """Convierte una fila pandas en un diccionario limpio y serializable."""
    if row is None:
        return None

    datos = row.to_dict() if hasattr(row, "to_dict") else dict(row)

    for clave, valor in list(datos.items()):
        try:
            if pd.isna(valor):
                datos[clave] = None
        except Exception:
            pass

    return datos


def obtener_ot_en_curso_corazon(operario, centro=None):
    """Devuelve la única OT en curso del operario, si existe."""
    operario_txt = str(operario or "").strip()

    if not operario_txt:
        return None

    params = [operario_txt]
    filtro_centro = ""

    if centro:
        filtro_centro = " AND centro = ?"
        params.append(centro)

    df = leer_df_corazon(f"""
        SELECT *
        FROM ordenes_trabajo
        WHERE operario = ?
          AND LOWER(TRIM(COALESCE(estado, ''))) = 'en curso'
          {filtro_centro}
        ORDER BY id DESC
        LIMIT 1
    """, tuple(params))

    if df.empty:
        return None

    return _fila_corazon_a_dict(df.iloc[0])


def obtener_ordenes_bloqueadas_corazon(operario=None, centro=None):
    """Devuelve las OT que esperan material, proveedor, aviso o presupuesto."""
    df = obtener_ordenes_abiertas_corazon(centro=centro, operario=operario)

    if df.empty or "estado" not in df.columns:
        return []

    estados = df["estado"].fillna("").astype(str).str.strip().str.lower()
    bloqueadas = df[estados.isin(ESTADOS_BLOQUEADOS_CORAZON)].copy()

    return [
        _fila_corazon_a_dict(fila)
        for _, fila in bloqueadas.iterrows()
    ]


def obtener_mision_actual(operario, centro=None, ubicacion_preferida=None):
    """
    Responde a la pregunta principal del Corazón:
    ¿qué debe hacer ahora este operario?

    1. Si ya tiene una OT En curso, la mantiene.
    2. Si no, descarta bloqueadas y selecciona la mejor OT ejecutable.
    3. No cambia estados por sí sola; la pantalla confirma con Empezar.
    """
    operario_txt = str(operario or "").strip()

    if not operario_txt:
        return {
            "estado_corazon": "sin_operario",
            "mision": None,
            "mensaje": "No hay operario seleccionado.",
            "bloqueadas": 0,
        }

    en_curso = obtener_ot_en_curso_corazon(
        operario=operario_txt,
        centro=centro,
    )

    if en_curso:
        en_curso["decision_humana_corazon"] = {
            "nivel": "continuar",
            "etiqueta": "🔵 CONTINÚA LO QUE ESTÁS HACIENDO",
            "mensaje": "Ya tienes esta OT en curso.",
        }

        return {
            "estado_corazon": "continuar",
            "mision": en_curso,
            "mensaje": "Continúa con la OT que ya está en curso.",
            "bloqueadas": len(
                obtener_ordenes_bloqueadas_corazon(
                    operario=operario_txt,
                    centro=centro,
                )
            ),
        }

    df = obtener_ordenes_abiertas_corazon(
        centro=centro,
        operario=operario_txt,
    )

    if df.empty:
        return {
            "estado_corazon": "sin_mision",
            "mision": None,
            "mensaje": "No hay órdenes activas para este operario.",
            "bloqueadas": 0,
        }

    estados = df["estado"].fillna("").astype(str).str.strip().str.lower()
    bloqueadas = int(estados.isin(ESTADOS_BLOQUEADOS_CORAZON).sum())
    ejecutables = df[estados.isin(ESTADOS_EJECUTABLES_CORAZON)].copy()

    if ejecutables.empty:
        return {
            "estado_corazon": "todo_bloqueado",
            "mision": None,
            "mensaje": "Todas las órdenes activas están bloqueadas o esperando.",
            "bloqueadas": bloqueadas,
        }

    prioridades = construir_prioridades_globales(
        centro=centro,
        operario=operario_txt,
        limite=1,
        df_ordenes_abiertas=ejecutables,
        ubicacion_preferida=ubicacion_preferida,
    )

    if not prioridades:
        return {
            "estado_corazon": "sin_mision",
            "mision": None,
            "mensaje": "El Corazón no ha encontrado una misión ejecutable.",
            "bloqueadas": bloqueadas,
        }

    prioridad = prioridades[0]
    numero_ot = str(prioridad.get("numero_ot") or "").strip()
    fila_mision = ejecutables[
        ejecutables["numero_ot"].fillna("").astype(str).str.strip() == numero_ot
    ]

    mision = (
        _fila_corazon_a_dict(fila_mision.iloc[0])
        if not fila_mision.empty
        else dict(prioridad)
    )

    mision["score_corazon"] = prioridad.get("score")
    mision["motivos_corazon"] = prioridad.get("motivos", [])
    mision["recurrencia_corazon"] = prioridad.get("recurrencia")
    mision["planta_resuelta_corazon"] = prioridad.get("planta")

    # FASE 1: información interna adicional.
    # La interfaz actual puede seguir ignorándola sin cambiar de aspecto.
    mision["capa_decision_corazon"] = prioridad.get(
        "capa_decision_corazon",
        clasificar_capa_decision_corazon(prioridad),
    )
    mision["ejecutable_corazon"] = prioridad.get(
        "ejecutable_corazon",
        True,
    )
    mision["bloqueada_corazon"] = prioridad.get(
        "bloqueada_corazon",
        False,
    )
    mision["motivo_bloqueo_corazon"] = prioridad.get(
        "motivo_bloqueo_corazon",
        "",
    )

    # Se conserva la lectura humana existente para no alterar
    # la página del operario.
    mision["decision_humana_corazon"] = clasificar_decision_corazon(
        mision
    )

    return {
        "estado_corazon": "propuesta",
        "mision": mision,
        "mensaje": "Esta es la siguiente misión recomendada por el Corazón.",
        "bloqueadas": bloqueadas,
    }


# =====================================================
# MEMORIA DEL CORAZÓN · ANTECEDENTE SIMILAR
# =====================================================

_PALABRAS_VACIAS_CORAZON = {
    "de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
    "y", "o", "en", "con", "por", "para", "que", "se", "no", "al", "a",
    "esta", "este", "esto", "esa", "ese", "muy", "mas", "más",
}


def _normalizar_texto_averia_corazon(valor):
    texto = normalizar(valor)

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)

    limpio = []
    for caracter in texto:
        limpio.append(
            caracter
            if caracter.isalnum() or caracter.isspace()
            else " "
        )

    palabras = [
        palabra
        for palabra in "".join(limpio).split()
        if palabra not in _PALABRAS_VACIAS_CORAZON
        and len(palabra) >= 2
    ]

    return " ".join(palabras)


def _similitud_textos_corazon(texto_a, texto_b):
    a = _normalizar_texto_averia_corazon(texto_a)
    b = _normalizar_texto_averia_corazon(texto_b)

    if not a or not b:
        return 0.0

    ratio_secuencia = SequenceMatcher(None, a, b).ratio()

    tokens_a = set(a.split())
    tokens_b = set(b.split())

    union = tokens_a | tokens_b
    interseccion = tokens_a & tokens_b

    ratio_tokens = (
        len(interseccion) / len(union)
        if union
        else 0.0
    )

    return max(
        ratio_secuencia,
        (ratio_tokens * 0.75) + (ratio_secuencia * 0.25),
    )


def buscar_antecedente_similar_corazon(
    ot_actual,
    umbral=0.72,
):
    """
    Busca una OT histórica realmente parecida a la misión actual.

    Solo devuelve antecedentes:
    - del mismo centro y espacio;
    - con similitud textual suficiente;
    - con solución real registrada.
    """
    if not ot_actual:
        return None

    centro = str(
        ot_actual.get("centro")
        or ot_actual.get("_centro_vivo")
        or ""
    ).strip()

    edificio = str(
        ot_actual.get("edificio")
        or ot_actual.get("_edificio_vivo")
        or ""
    ).strip()

    espacio = str(
        ot_actual.get("espacio")
        or ot_actual.get("aula")
        or ot_actual.get("ubicacion")
        or ""
    ).strip()

    area = str(
        ot_actual.get("area")
        or ""
    ).strip()

    descripcion_actual = str(
        ot_actual.get("descripcion")
        or ot_actual.get("titulo")
        or ot_actual.get("incidencia")
        or ""
    ).strip()

    numero_actual = str(
        ot_actual.get("numero_ot")
        or ""
    ).strip()

    if not centro or not espacio or not descripcion_actual:
        return None

    df = leer_df_corazon(
        """
        SELECT
            numero_ot,
            descripcion,
            area,
            edificio,
            espacio,
            fecha_cierre,
            fecha_creacion,
            observaciones_cierre,
            trabajo_realizado
        FROM historico_ordenes
        WHERE centro = ?
          AND espacio = ?
        ORDER BY id DESC
        LIMIT 80
        """,
        (centro, espacio),
    )

    if df.empty:
        return None

    edificio_actual_norm = normalizar_edificio(edificio)
    area_actual_norm = normalizar(area)

    mejor = None

    for _, fila in df.iterrows():
        numero_anterior = str(
            fila.get("numero_ot") or ""
        ).strip()

        if numero_actual and numero_anterior == numero_actual:
            continue

        solucion = str(
            fila.get("observaciones_cierre")
            or fila.get("trabajo_realizado")
            or ""
        ).strip()

        if not solucion:
            continue

        descripcion_anterior = str(
            fila.get("descripcion")
            or ""
        ).strip()

        similitud_textual = _similitud_textos_corazon(
            descripcion_actual,
            descripcion_anterior,
        )

        if similitud_textual < 0.45:
            continue

        puntuacion = similitud_textual

        if normalizar_edificio(
            fila.get("edificio")
        ) == edificio_actual_norm:
            puntuacion += 0.08

        if (
            area_actual_norm
            and normalizar(fila.get("area")) == area_actual_norm
        ):
            puntuacion += 0.12

        puntuacion = min(1.0, puntuacion)

        if puntuacion < umbral:
            continue

        fecha = (
            fila.get("fecha_cierre")
            or fila.get("fecha_creacion")
            or ""
        )

        candidato = {
            "numero_ot": numero_anterior,
            "fecha": str(fecha or "").strip(),
            "descripcion": descripcion_anterior,
            "solucion": solucion,
            "area": str(fila.get("area") or "").strip(),
            "edificio": str(fila.get("edificio") or "").strip(),
            "espacio": str(fila.get("espacio") or "").strip(),
            "similitud": round(puntuacion * 100),
        }

        if (
            mejor is None
            or candidato["similitud"] > mejor["similitud"]
        ):
            mejor = candidato

    return mejor



# =====================================================
# LECTURA HUMANA DE LA DECISIÓN DEL CORAZÓN
# =====================================================

def clasificar_decision_corazon(mision):
    """
    Traduce la puntuación técnica a una recomendación comprensible
    para el operario, sin cambiar el orden ni la puntuación.

    No decide nada nuevo: solo explica la decisión ya tomada.
    """
    if not mision:
        return {
            "nivel": "sin_mision",
            "etiqueta": "",
            "mensaje": "",
        }

    score = int(
        mision.get("score_corazon")
        or mision.get("score")
        or 0
    )

    prioridad = normalizar(
        mision.get("prioridad")
    )

    area = normalizar(
        mision.get("area")
    )

    origen = normalizar(
        mision.get("origen")
    )

    descripcion = normalizar(
        mision.get("descripcion")
    )

    motivos = [
        str(motivo or "").strip()
        for motivo in (
            mision.get("motivos_corazon")
            or mision.get("motivos")
            or []
        )
        if str(motivo or "").strip()
    ]

    texto_global = " ".join(
        [area, origen, descripcion] + motivos
    ).lower()

    critica = (
        "urgente" in prioridad
        or "legionella" in texto_global
        or score >= 90
    )

    if critica:
        return {
            "nivel": "ahora",
            "etiqueta": "🔴 HAZLO AHORA",
            "mensaje": (
                "Esta actuación tiene prioridad suficiente "
                "para interrumpir la ruta normal."
            ),
        }

    continuidad = any(
        frase in texto_global
        for frase in [
            "ya estás trabajando en esta planta",
            "ya estas trabajando en esta planta",
            "ya estás en este edificio",
            "ya estas en este edificio",
            "actuaciones ejecutables en esta planta",
        ]
    )

    if continuidad and score < 90:
        return {
            "nivel": "aprovecha",
            "etiqueta": "🟡 APROVECHA QUE ESTÁS AQUÍ",
            "mensaje": (
                "No es una emergencia, pero resolverla ahora "
                "evita desplazamientos y mejora la jornada."
            ),
        }

    if score >= 70 or prioridad == "alta":
        return {
            "nivel": "ahora",
            "etiqueta": "🟠 CONVIENE HACERLA AHORA",
            "mensaje": (
                "Es una de las actuaciones más importantes "
                "que tienes disponibles."
            ),
        }

    return {
        "nivel": "puede_esperar",
        "etiqueta": "🟢 PUEDE ESPERAR",
        "mensaje": (
            "Puede mantenerse en cola mientras existan "
            "actuaciones de mayor impacto."
        ),
    }


def latido_corazon(
    operario,
    centro=None,
    ubicacion_preferida=None,
):
    """Alias estable para que las pantallas consulten el Corazón."""
    return obtener_mision_actual(
        operario=operario,
        centro=centro,
        ubicacion_preferida=ubicacion_preferida,
    )

