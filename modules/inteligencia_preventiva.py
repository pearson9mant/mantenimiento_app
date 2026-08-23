from datetime import date, datetime, timedelta

import pandas as pd

from database.db import conectar, _sql


# =========================================================
# CONFIGURACIÓN DE LA INTELIGENCIA
# =========================================================

DIAS_ANALISIS_DEFECTO = 180

AREAS_SENSIBLES = {
    "fontaneria",
    "fontanería",
    "electricidad",
    "climatizacion",
    "climatización",
    "acs",
    "seguridad",
}

ORIGENES_NO_CORRECTIVOS = {
    "PREVENTIVO",
    "LEGIONELLA",
    "VERANO",
}

ESTADOS_CERRADOS = {
    "finalizada",
    "finalizado",
    "cerrada",
    "cerrado",
    "cancelada",
    "cancelado",
    "cerrado definitivo",
}


# =========================================================
# TIEMPOS ORIENTATIVOS DE PREVENTIVO
# =========================================================
# Sirven para dimensionar carga de trabajo. No sustituyen
# una medición real de tiempos ni una obligación normativa.

TIEMPOS_BASE_PREVENTIVO_MIN = {
    "cisterna / fluxor": 20,
    "grifo": 15,
    "fuga de agua": 25,
    "desagüe / atasco": 25,
    "tubería / racor": 30,
    "enchufe / toma": 20,
    "interruptor / pulsador": 15,
    "cuadro / protección": 30,
    "cableado": 30,
    "filtros": 25,
    "condensados / desagüe": 30,
    "temperatura / rendimiento": 25,
    "unidad interior": 30,
    "unidad exterior": 40,
    "luminaria / lámpara": 15,
    "emergencia": 20,
    "puerta / maneta": 20,
    "ventana / persiana": 25,
    "mesa / silla": 15,
    "pizarra": 15,
    "pantalla / proyector": 20,
    "ordenador": 20,
    "red / conectividad": 25,
    "audio": 20,
    "acumulador": 35,
    "retorno / recirculación": 35,
    "temperatura": 20,
    "válvula": 25,
    "puerta de emergencia": 30,
    "cierre / acceso": 20,
    "señalización": 15,
    "riego": 30,
    "árbol / rama": 30,
}

TIEMPO_BASE_AREA_MIN = {
    "fontaneria": 25,
    "electricidad": 25,
    "climatizacion": 30,
    "iluminacion": 20,
    "equipamiento": 20,
    "informatica": 25,
    "acs": 30,
    "seguridad": 25,
    "jardineria": 30,
}


# =========================================================
# PATRONES DE AVERÍA
# =========================================================
#
# La inteligencia no considera suficiente que dos incidencias
# pertenezcan al mismo área. Intenta identificar qué elemento
# o tipo de fallo se repite dentro de cada espacio.
#
# El sistema es deliberadamente conservador:
# si no encuentra un patrón repetido con suficiente evidencia,
# no recomienda crear un preventivo nuevo.

PATRONES_POR_AREA = {
    "fontaneria": {
        "cisterna / fluxor": [
            "cisterna", "fluxor", "presto", "descarga", "pulsador wc",
        ],
        "grifo": [
            "grifo", "monomando", "aireador", "caño",
        ],
        "fuga de agua": [
            "fuga", "pierde agua", "pérdida de agua", "gotea", "goteo",
            "escape de agua",
        ],
        "desagüe / atasco": [
            "desague", "desagüe", "atasco", "atascado", "embozado",
            "sumidero", "sifon", "sifón",
        ],
        "tubería / racor": [
            "tuberia", "tubería", "racor", "latiguillo", "manguito",
            "llave de paso", "valvula", "válvula",
        ],
    },

    "electricidad": {
        "enchufe / toma": [
            "enchufe", "toma", "base electrica", "base eléctrica",
        ],
        "interruptor / pulsador": [
            "interruptor", "pulsador",
        ],
        "cuadro / protección": [
            "magnetotermico", "magnetotérmico", "diferencial",
            "cuadro electrico", "cuadro eléctrico", "salta el automatico",
            "salta el automático",
        ],
        "cableado": [
            "cable", "cableado", "conexion", "conexión",
        ],
    },

    "climatizacion": {
        "filtros": [
            "filtro", "filtros",
        ],
        "condensados / desagüe": [
            "condensado", "condensados", "desague", "desagüe",
            "gotea", "goteo",
        ],
        "temperatura / rendimiento": [
            "no enfria", "no enfría", "no calienta", "temperatura",
            "frio", "frío", "calor",
        ],
        "unidad interior": [
            "split", "unidad interior", "ventilador",
        ],
        "unidad exterior": [
            "unidad exterior", "compresor", "condensadora",
        ],
    },

    "iluminacion": {
        "luminaria / lámpara": [
            "luminaria", "lampara", "lámpara", "fluorescente",
            "bombilla", "led", "tubo",
        ],
        "emergencia": [
            "emergencia", "luz emergencia", "luz de emergencia",
        ],
        "interruptor / pulsador": [
            "interruptor", "pulsador",
        ],
    },

    "equipamiento": {
        "puerta / maneta": [
            "puerta", "maneta", "cerradura", "bisagra", "pomo",
        ],
        "ventana / persiana": [
            "ventana", "persiana", "estor",
        ],
        "mesa / silla": [
            "mesa", "silla", "pata", "tablero",
        ],
        "pizarra": [
            "pizarra",
        ],
    },

    "informatica": {
        "pantalla / proyector": [
            "pantalla", "proyector", "proyector", "hdmi",
        ],
        "ordenador": [
            "ordenador", "pc", "equipo informatico", "equipo informático",
        ],
        "red / conectividad": [
            "red", "wifi", "internet", "conexion", "conexión",
        ],
        "audio": [
            "altavoz", "altavoces", "audio", "sonido",
        ],
    },

    "acs": {
        "acumulador": [
            "acumulador", "deposito", "depósito",
        ],
        "retorno / recirculación": [
            "retorno", "recirculacion", "recirculación", "bomba retorno",
            "bomba de retorno",
        ],
        "temperatura": [
            "temperatura", "no llega", "agua fria", "agua fría",
        ],
        "válvula": [
            "valvula", "válvula",
        ],
    },

    "seguridad": {
        "puerta de emergencia": [
            "puerta emergencia", "puerta de emergencia", "antipanico",
            "antipánico",
        ],
        "cierre / acceso": [
            "cerradura", "cierre", "acceso", "llave",
        ],
        "señalización": [
            "senalizacion", "señalización", "senal", "señal",
        ],
    },

    "jardineria": {
        "riego": [
            "riego", "aspersor", "gotero", "programador",
        ],
        "árbol / rama": [
            "arbol", "árbol", "rama", "ramas",
        ],
    },
}


def _sin_acentos(texto):
    return (
        str(texto or "")
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
    )


def _texto_incidencia(fila):
    """
    Une los campos textuales disponibles de una OT sin depender
    de que todas las tablas tengan exactamente las mismas columnas.
    """
    campos = [
        "descripcion",
        "titulo",
        "incidencia",
        "observaciones",
        "observaciones_cierre",
        "detalle",
        "comentarios",
    ]

    partes = []

    for campo in campos:
        if campo in fila.index:
            valor = str(fila.get(campo, "") or "").strip()
            if valor:
                partes.append(valor)

    return " ".join(partes)


def _detectar_patron_individual(area, texto):
    """
    Devuelve el patrón técnico más probable de una incidencia.
    Si no hay evidencia suficiente devuelve cadena vacía.
    """
    area_clave = _normalizar_clave(area)
    texto_norm = _sin_acentos(texto)

    catalogo = PATRONES_POR_AREA.get(area_clave, {})

    mejor_patron = ""
    mejor_puntuacion = 0

    for patron, palabras in catalogo.items():
        puntuacion = 0

        for palabra in palabras:
            palabra_norm = _sin_acentos(palabra)

            if palabra_norm and palabra_norm in texto_norm:
                # Las expresiones compuestas pesan algo más.
                puntuacion += 2 if " " in palabra_norm else 1

        if puntuacion > mejor_puntuacion:
            mejor_patron = patron
            mejor_puntuacion = puntuacion

    if mejor_puntuacion <= 0:
        return ""

    return mejor_patron


def _analizar_patron_grupo(grupo, area):
    """
    Busca si dentro del grupo existe un tipo de avería realmente repetido.

    Criterio conservador:
    - al menos 2 incidencias del mismo patrón;
    - y ese patrón debe representar al menos el 50% del grupo.
    """
    patrones = []

    for _, fila in grupo.iterrows():
        texto = _texto_incidencia(fila)
        patron = _detectar_patron_individual(area, texto)

        if patron:
            patrones.append(patron)

    if not patrones:
        return {
            "patron": "",
            "repeticiones": 0,
            "confianza": "Sin patrón claro",
            "porcentaje": 0,
        }

    conteo = {}

    for patron in patrones:
        conteo[patron] = conteo.get(patron, 0) + 1

    patron_dominante = max(
        conteo,
        key=lambda p: conteo[p],
    )

    repeticiones = conteo[patron_dominante]
    total_grupo = len(grupo)

    porcentaje = round(
        (repeticiones / total_grupo) * 100
    ) if total_grupo else 0

    if repeticiones < 2 or porcentaje < 50:
        return {
            "patron": "",
            "repeticiones": repeticiones,
            "confianza": "Baja",
            "porcentaje": porcentaje,
        }

    if porcentaje >= 80 and repeticiones >= 3:
        confianza = "Alta"
    elif porcentaje >= 60:
        confianza = "Media"
    else:
        confianza = "Moderada"

    return {
        "patron": patron_dominante,
        "repeticiones": repeticiones,
        "confianza": confianza,
        "porcentaje": porcentaje,
    }


# =========================================================
# UTILIDADES
# =========================================================

def _normalizar(valor):
    return str(valor or "").strip().lower()


def _normalizar_clave(valor):
    return (
        _normalizar(valor)
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace(".", "")
        .replace("/", "")
        .replace("\\", "")
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )


def _leer_df(sql, params=()):
    conn = conectar()

    try:
        return pd.read_sql_query(
            _sql(sql),
            conn,
            params=params,
        )

    except Exception:
        return pd.DataFrame()

    finally:
        conn.close()


def _primera_columna(df, candidatos):
    for columna in candidatos:
        if columna in df.columns:
            return columna

    return None


def _convertir_fecha(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    if not texto or texto.lower() in {
        "none",
        "nan",
        "nat",
        "-",
    }:
        return None

    try:
        fecha = pd.to_datetime(
            texto,
            errors="coerce",
            dayfirst=True,
        )

        if pd.isna(fecha):
            return None

        return fecha.to_pydatetime().date()

    except Exception:
        return None


def _obtener_fecha_fila(fila):
    candidatos = [
        "fecha_cierre",
        "fecha_realizacion",
        "fecha",
        "fecha_creacion",
        "fecha_origen",
    ]

    for campo in candidatos:
        if campo in fila.index:
            fecha = _convertir_fecha(fila.get(campo))

            if fecha:
                return fecha

    return None


def _frecuencia_a_dias(frecuencia):
    texto = _normalizar(frecuencia)

    if not texto:
        return 0

    if "semanal" in texto:
        return 7

    if "quincenal" in texto:
        return 15

    if "mensual" in texto:
        return 30

    if "bimestral" in texto:
        return 60

    if "trimestral" in texto:
        return 90

    if "semestral" in texto:
        return 180

    if "anual" in texto:
        return 365

    try:
        return int(float(texto))

    except Exception:
        return 0


def _dias_a_frecuencia(dias):
    try:
        dias = int(dias)
    except Exception:
        dias = 30

    if dias <= 10:
        return "Semanal"

    if dias <= 22:
        return "Quincenal"

    if dias <= 45:
        return "Mensual"

    if dias <= 75:
        return "Bimestral"

    if dias <= 120:
        return "Trimestral"

    if dias <= 240:
        return "Semestral"

    return "Anual"



def _dias_frecuencia_recomendada(intervalo_medio):
    """
    Adelanta la revisión aproximadamente un 30% respecto
    al intervalo medio observado entre fallos.
    """
    if intervalo_medio is None:
        return 30

    try:
        intervalo = int(intervalo_medio)
    except Exception:
        return 30

    return max(7, round(intervalo * 0.70))


def _estimar_tiempo_preventivo_min(
    patron,
    area,
    repeticiones,
    cantidad,
):
    """
    Estimación prudente del tiempo de una revisión preventiva.
    """
    patron_txt = str(patron or "").strip()
    area_clave = _normalizar_clave(area)

    minutos = TIEMPOS_BASE_PREVENTIVO_MIN.get(
        patron_txt,
        TIEMPO_BASE_AREA_MIN.get(area_clave, 20),
    )

    try:
        repeticiones = int(repeticiones or 0)
    except Exception:
        repeticiones = 0

    try:
        cantidad = int(cantidad or 0)
    except Exception:
        cantidad = 0

    if repeticiones >= 5:
        minutos += 10
    elif repeticiones >= 3:
        minutos += 5

    if cantidad >= 8:
        minutos += 5

    return max(10, min(60, int(minutos)))


def _calcular_carga_preventiva_anual(
    dias_frecuencia,
    minutos_revision,
):
    try:
        dias = max(1, int(dias_frecuencia))
    except Exception:
        dias = 30

    try:
        minutos = max(1, int(minutos_revision))
    except Exception:
        minutos = 20

    revisiones_anuales = max(1, round(365 / dias))
    horas_anuales = round(
        (revisiones_anuales * minutos) / 60,
        1,
    )

    return revisiones_anuales, horas_anuales


def _evaluar_cobertura_preventiva(
    patron_detectado,
    preventivo,
):
    if not patron_detectado:
        return "Sin patrón"

    if preventivo is None:
        return "Sin preventivo"

    return "Con preventivo"


# =========================================================
# DATOS
# =========================================================

def _cargar_historico_correctivo(centro, desde):
    df = _leer_df(
        """
        SELECT *
        FROM historico_ordenes
        WHERE centro = ?
        """,
        (centro,),
    )

    if df.empty:
        return df

    registros = []

    for _, fila in df.iterrows():

        origen = str(
            fila.get("origen", "") or ""
        ).strip().upper()

        area = _normalizar(
            fila.get("area", "")
        )

        descripcion = _normalizar(
            fila.get("descripcion", "")
        )

        estado = _normalizar(
            fila.get("estado", "")
        )

        # ---------------------------------------------
        # No usamos preventivos como avería correctiva
        # ---------------------------------------------
        if origen in ORIGENES_NO_CORRECTIVOS:
            continue

        if "preventivo" in descripcion:
            continue

        if "legionella" in descripcion:
            continue

        if "legionella" in area:
            continue

        if "cancelad" in estado:
            continue

        fecha = _obtener_fecha_fila(fila)

        if not fecha:
            continue

        if fecha < desde:
            continue

        registro = fila.to_dict()
        registro["_fecha_inteligencia"] = fecha
        registro["_origen_dato"] = "historico"

        registros.append(registro)

    if not registros:
        return pd.DataFrame()

    return pd.DataFrame(registros)


def _cargar_correctivos_abiertos(centro, desde):
    df = _leer_df(
        """
        SELECT *
        FROM ordenes_trabajo
        WHERE centro = ?
        """,
        (centro,),
    )

    if df.empty:
        return df

    registros = []

    for _, fila in df.iterrows():

        estado = _normalizar(
            fila.get("estado", "")
        )

        if estado in ESTADOS_CERRADOS:
            continue

        origen = str(
            fila.get("origen", "") or ""
        ).strip().upper()

        area = _normalizar(
            fila.get("area", "")
        )

        descripcion = _normalizar(
            fila.get("descripcion", "")
        )

        if origen in ORIGENES_NO_CORRECTIVOS:
            continue

        if "preventivo" in descripcion:
            continue

        if "legionella" in descripcion:
            continue

        if "legionella" in area:
            continue

        fecha = _obtener_fecha_fila(fila)

        if fecha and fecha < desde:
            continue

        if not fecha:
            fecha = date.today()

        registro = fila.to_dict()
        registro["_fecha_inteligencia"] = fecha
        registro["_origen_dato"] = "abierta"

        registros.append(registro)

    if not registros:
        return pd.DataFrame()

    return pd.DataFrame(registros)


def _cargar_preventivos_periodo(centro, desde):
    """
    Lee actuaciones preventivas del periodo sin modificar nada.

    Combina:
    - preventivos ya archivados en historico_ordenes;
    - preventivos todavía abiertos en ordenes_trabajo.

    El objetivo es medir actividad preventiva real del mismo periodo
    usado para analizar incidencias correctivas.
    """
    registros = []

    for tabla, origen_dato in [
        ("historico_ordenes", "historico"),
        ("ordenes_trabajo", "abierta"),
    ]:
        df = _leer_df(
            f"""
            SELECT *
            FROM {tabla}
            WHERE centro = ?
              AND UPPER(COALESCE(origen, '')) = 'PREVENTIVO'
            """,
            (centro,),
        )

        if df.empty:
            continue

        for _, fila in df.iterrows():
            estado = _normalizar(
                fila.get("estado", "")
            )

            if "cancelad" in estado:
                continue

            fecha = _obtener_fecha_fila(
                fila
            )

            if not fecha:
                continue

            if fecha < desde:
                continue

            registro = fila.to_dict()
            registro["_fecha_inteligencia"] = fecha
            registro["_origen_dato"] = origen_dato

            registros.append(
                registro
            )

    if not registros:
        return pd.DataFrame()

    return pd.DataFrame(
        registros
    )


def _construir_balance_areas(
    correctivos,
    preventivos_periodo,
    preventivos_activos,
):
    """
    Compara actividad correctiva y preventiva por área.

    Importante:
    - El balance NO crea por sí mismo una recomendación.
    - Tener mucha correctiva no significa que exista un patrón técnico.
    - La creación de preventivos sigue dependiendo del motor de patrones.
    """
    areas = set()

    def _areas_df(df):
        if df is None or df.empty or "area" not in df.columns:
            return set()

        return {
            str(valor or "").strip()
            for valor in df["area"].tolist()
            if str(valor or "").strip()
        }

    areas |= _areas_df(
        correctivos
    )
    areas |= _areas_df(
        preventivos_periodo
    )
    areas |= _areas_df(
        preventivos_activos
    )

    resultado = []

    for area in sorted(
        areas,
        key=lambda x: _normalizar_clave(x),
    ):
        area_clave = _normalizar_clave(
            area
        )

        def _contar(df):
            if (
                df is None
                or df.empty
                or "area" not in df.columns
            ):
                return 0

            return int(
                sum(
                    1
                    for valor in df["area"].tolist()
                    if _normalizar_clave(valor)
                    == area_clave
                )
            )

        correctivos_n = _contar(
            correctivos
        )

        preventivos_n = _contar(
            preventivos_periodo
        )

        activos_n = _contar(
            preventivos_activos
        )

        if correctivos_n == 0 and preventivos_n > 0:
            estado = "Preventivo domina"
            color = "verde"
            lectura = (
                "Hay actividad preventiva y no aparecen correctivos "
                "en el periodo analizado."
            )

        elif correctivos_n == 0 and preventivos_n == 0:
            estado = "Sin actividad"
            color = "gris"
            lectura = (
                "No hay actividad suficiente para valorar esta área."
            )

        elif preventivos_n == 0:
            estado = "Correctivo sin cobertura"
            color = "rojo" if correctivos_n >= 3 else "amarillo"
            lectura = (
                "Hay correctivos pero no constan actuaciones preventivas "
                "en el mismo periodo. Esto no implica por sí solo que haya "
                "que crear un preventivo: debe existir patrón técnico."
            )

        else:
            ratio = correctivos_n / preventivos_n

            if ratio <= 1:
                estado = "Equilibrado"
                color = "verde"
                lectura = (
                    "La actividad preventiva iguala o supera a la correctiva."
                )

            elif ratio <= 2:
                estado = "Vigilar"
                color = "amarillo"
                lectura = (
                    "La correctiva supera moderadamente a la preventiva. "
                    "Conviene observar si hay patrones repetidos."
                )

            else:
                estado = "Correctivo domina"
                color = "rojo"
                lectura = (
                    "La correctiva supera claramente a la preventiva. "
                    "Priorizar el análisis de patrones antes de aumentar tareas."
                )

        ratio_cp = (
            round(
                correctivos_n / preventivos_n,
                2,
            )
            if preventivos_n > 0
            else None
        )

        resultado.append(
            {
                "area": area,
                "correctivos": correctivos_n,
                "preventivos_periodo": preventivos_n,
                "preventivos_activos": activos_n,
                "ratio_correctivo_preventivo": ratio_cp,
                "estado": estado,
                "color": color,
                "lectura": lectura,
            }
        )

    resultado.sort(
        key=lambda x: (
            -x["correctivos"],
            x["area"],
        )
    )

    return resultado



def _cargar_preventivos(centro):
    return _leer_df(
        """
        SELECT *
        FROM preventivo_tareas
        WHERE centro = ?
          AND activo = 1
        """,
        (centro,),
    )


def _cargar_plantas(centro):
    df = _leer_df(
        """
        SELECT centro, edificio, planta, espacio
        FROM espacios
        WHERE centro = ?
          AND activo = 1
        """,
        (centro,),
    )

    mapa = {}

    if df.empty:
        return mapa

    for _, fila in df.iterrows():

        edificio = _normalizar_clave(
            fila.get("edificio", "")
        )

        espacio = _normalizar_clave(
            fila.get("espacio", "")
        )

        planta = str(
            fila.get("planta", "") or ""
        ).strip()

        if edificio and espacio:
            mapa[(edificio, espacio)] = planta

    return mapa


# =========================================================
# COMPARACIÓN CON PREVENTIVOS EXISTENTES
# =========================================================

def _buscar_preventivo_existente(
    preventivos,
    edificio,
    espacio,
    area,
):
    if preventivos.empty:
        return None

    edificio_clave = _normalizar_clave(edificio)
    espacio_clave = _normalizar_clave(espacio)
    area_clave = _normalizar_clave(area)

    candidatos = []

    for _, fila in preventivos.iterrows():

        mismo_edificio = (
            _normalizar_clave(
                fila.get("edificio", "")
            )
            == edificio_clave
        )

        mismo_espacio = (
            _normalizar_clave(
                fila.get("espacio", "")
            )
            == espacio_clave
        )

        misma_area = (
            _normalizar_clave(
                fila.get("area", "")
            )
            == area_clave
        )

        if mismo_edificio and mismo_espacio and misma_area:
            candidatos.append(
                fila.to_dict()
            )

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: _frecuencia_a_dias(
            x.get("frecuencia", "")
        )
        or 9999
    )

    return candidatos[0]


# =========================================================
# ANÁLISIS
# =========================================================

def _calcular_intervalo_medio(fechas):
    fechas_validas = sorted(
        {
            f for f in fechas
            if f is not None
        }
    )

    if len(fechas_validas) < 2:
        return None

    intervalos = []

    for anterior, siguiente in zip(
        fechas_validas,
        fechas_validas[1:],
    ):
        dias = (
            siguiente - anterior
        ).days

        if dias >= 0:
            intervalos.append(dias)

    if not intervalos:
        return None

    return round(
        sum(intervalos) / len(intervalos)
    )


def _descripcion_representativa(grupo):
    if "descripcion" not in grupo.columns:
        return ""

    textos = []

    for valor in grupo["descripcion"].tolist():
        texto = str(valor or "").strip()

        if texto:
            textos.append(texto)

    if not textos:
        return ""

    return textos[-1]


def _hay_prioridad_alta(grupo):
    if "prioridad" not in grupo.columns:
        return False

    for prioridad in grupo["prioridad"].tolist():
        texto = _normalizar(prioridad)

        if (
            "urgente" in texto
            or "alta" in texto
        ):
            return True

    return False


def _calcular_score(
    cantidad,
    area,
    ultima_fecha,
    prioridad_alta,
    intervalo_medio,
):
    score = 0

    # Recurrencia
    score += min(
        50,
        cantidad * 12,
    )

    # Área crítica
    if _normalizar(area) in AREAS_SENSIBLES:
        score += 20

    # Prioridad
    if prioridad_alta:
        score += 15

    # Recencia
    if ultima_fecha:
        dias_desde_ultima = (
            date.today() - ultima_fecha
        ).days

        if dias_desde_ultima <= 15:
            score += 15

        elif dias_desde_ultima <= 30:
            score += 10

        elif dias_desde_ultima <= 60:
            score += 5

    # Fallos muy próximos entre sí
    if intervalo_medio is not None:

        if intervalo_medio <= 30:
            score += 15

        elif intervalo_medio <= 60:
            score += 10

        elif intervalo_medio <= 90:
            score += 5

    return min(
        100,
        score,
    )


def _nivel_recomendacion(score):
    if score >= 80:
        return "Alta"

    if score >= 55:
        return "Media"

    return "Observación"


def _frecuencia_recomendada(intervalo_medio):
    objetivo = _dias_frecuencia_recomendada(
        intervalo_medio
    )

    return _dias_a_frecuencia(
        objetivo
    )


def analizar_inteligencia_preventiva(
    centro="Pearson 22",
    dias=DIAS_ANALISIS_DEFECTO,
):
    """
    Analiza correctivos históricos y abiertos.

    IMPORTANTE:
    - No crea preventivos.
    - No modifica frecuencias.
    - No modifica OTs.
    - Solo devuelve recomendaciones.
    """

    desde = (
        date.today()
        - timedelta(days=int(dias))
    )

    historico = _cargar_historico_correctivo(
        centro,
        desde,
    )

    abiertas = _cargar_correctivos_abiertos(
        centro,
        desde,
    )

    frames = [
        df
        for df in [
            historico,
            abiertas,
        ]
        if not df.empty
    ]

    if not frames:
        return {
            "centro": centro,
            "dias": dias,
            "desde": str(desde),
            "total_correctivos": 0,
            "preventivos_activos": 0,
            "patrones_confirmados": 0,
            "patrones_con_preventivo": 0,
            "patrones_sin_preventivo": 0,
            "total_preventivos_periodo": 0,
            "balance_areas": [],
            "grupos_analizados": 0,
            "recomendaciones": [],
        }

    df = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )

    for columna in [
        "edificio",
        "espacio",
        "area",
    ]:
        if columna not in df.columns:
            df[columna] = ""

        df[columna] = (
            df[columna]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # No analizamos ubicaciones sin mínimo contexto.
    df = df[
        (df["espacio"] != "")
        & (df["area"] != "")
    ].copy()

    if df.empty:
        return {
            "centro": centro,
            "dias": dias,
            "desde": str(desde),
            "total_correctivos": 0,
            "preventivos_activos": 0,
            "patrones_confirmados": 0,
            "patrones_con_preventivo": 0,
            "patrones_sin_preventivo": 0,
            "total_preventivos_periodo": 0,
            "balance_areas": [],
            "grupos_analizados": 0,
            "recomendaciones": [],
        }

    preventivos = _cargar_preventivos(
        centro
    )

    preventivos_periodo = (
        _cargar_preventivos_periodo(
            centro,
            desde,
        )
    )

    balance_areas = (
        _construir_balance_areas(
            correctivos=df,
            preventivos_periodo=preventivos_periodo,
            preventivos_activos=preventivos,
        )
    )

    mapa_plantas = _cargar_plantas(
        centro
    )

    recomendaciones = []

    agrupado = df.groupby(
        [
            "edificio",
            "espacio",
            "area",
        ],
        dropna=False,
    )

    for (
        edificio,
        espacio,
        area,
    ), grupo in agrupado:

        cantidad = len(grupo)

        area_norm = _normalizar(area)

        patron_info = _analizar_patron_grupo(
            grupo,
            area,
        )

        patron_detectado = patron_info.get(
            "patron",
            "",
        )

        repeticiones_patron = patron_info.get(
            "repeticiones",
            0,
        )

        confianza_patron = patron_info.get(
            "confianza",
            "Sin patrón claro",
        )

        porcentaje_patron = patron_info.get(
            "porcentaje",
            0,
        )

        # ---------------------------------------------
        # Umbral diferente según riesgo
        # ---------------------------------------------
        minimo = (
            2
            if area_norm in AREAS_SENSIBLES
            else 3
        )

        if cantidad < minimo:
            continue

        fechas = [
            f
            for f
            in grupo[
                "_fecha_inteligencia"
            ].tolist()
            if f
        ]

        if not fechas:
            continue

        fechas.sort()

        primera_fecha = fechas[0]
        ultima_fecha = fechas[-1]

        intervalo_medio = (
            _calcular_intervalo_medio(
                fechas
            )
        )

        prioridad_alta = (
            _hay_prioridad_alta(
                grupo
            )
        )

        score = _calcular_score(
            cantidad=cantidad,
            area=area,
            ultima_fecha=ultima_fecha,
            prioridad_alta=prioridad_alta,
            intervalo_medio=intervalo_medio,
        )

        preventivo = (
            _buscar_preventivo_existente(
                preventivos,
                edificio,
                espacio,
                area,
            )
        )

        frecuencia_sugerida = (
            _frecuencia_recomendada(
                intervalo_medio
            )
        )

        dias_frecuencia_sugerida = (
            _dias_frecuencia_recomendada(
                intervalo_medio
            )
        )

        tiempo_preventivo_min = (
            _estimar_tiempo_preventivo_min(
                patron=patron_detectado,
                area=area,
                repeticiones=repeticiones_patron,
                cantidad=cantidad,
            )
            if patron_detectado
            else 0
        )

        (
            revisiones_anuales_sugeridas,
            horas_preventivo_anuales,
        ) = (
            _calcular_carga_preventiva_anual(
                dias_frecuencia_sugerida,
                tiempo_preventivo_min,
            )
            if patron_detectado
            else (0, 0)
        )

        cobertura_preventiva = (
            _evaluar_cobertura_preventiva(
                patron_detectado,
                preventivo,
            )
        )

        accion = ""
        motivo = ""
        frecuencia_actual = ""
        preventivo_id = None
        tarea_preventiva = ""

        # =============================================
        # NO HAY PATRÓN TÉCNICO REPETIDO CLARO
        # =============================================
        if not patron_detectado:

            accion = "Seguir observando"

            motivo = (
                f"Hay {cantidad} incidencias en {dias} días en el mismo "
                f"espacio y área, pero sus descripciones no muestran todavía "
                f"un mismo tipo de avería repetido con suficiente claridad. "
                f"No conviene crear un preventivo solo por coincidencia de área."
            )

        # =============================================
        # HAY PATRÓN Y NO EXISTE PREVENTIVO
        # =============================================
        elif preventivo is None:

            accion = "Crear preventivo"

            motivo = (
                f"Patrón detectado: {patron_detectado}. "
                f"Se repite en {repeticiones_patron} de {cantidad} incidencias "
                f"({porcentaje_patron}% del grupo). "
                f"Confianza del patrón: {confianza_patron}. "
                f"Conviene valorar un preventivo específico sobre este elemento."
            )

        # =============================================
        # HAY PATRÓN Y YA EXISTE PREVENTIVO
        # =============================================
        else:

            preventivo_id = preventivo.get(
                "id"
            )

            tarea_preventiva = str(
                preventivo.get(
                    "tarea",
                    "",
                )
                or ""
            ).strip()

            frecuencia_actual = str(
                preventivo.get(
                    "frecuencia",
                    "",
                )
                or ""
            ).strip()

            dias_actuales = (
                _frecuencia_a_dias(
                    frecuencia_actual
                )
            )

            dias_sugeridos = (
                _frecuencia_a_dias(
                    frecuencia_sugerida
                )
            )

            if (
                intervalo_medio is not None
                and dias_actuales > 0
                and dias_sugeridos > 0
                and dias_actuales > dias_sugeridos
            ):

                accion = "Revisar frecuencia"

                motivo = (
                    f"Patrón detectado: {patron_detectado}. "
                    f"Se repite en {repeticiones_patron} de {cantidad} incidencias "
                    f"({porcentaje_patron}%). "
                    f"Ya existe preventivo, pero las averías se repiten "
                    f"aproximadamente cada {intervalo_medio} días. "
                    f"Conviene revisar si la frecuencia actual se adelanta "
                    f"lo suficiente al fallo."
                )

            else:

                accion = "Vigilar preventivo existente"

                motivo = (
                    f"Patrón detectado: {patron_detectado}. "
                    f"Se repite en {repeticiones_patron} de {cantidad} incidencias "
                    f"({porcentaje_patron}%). "
                    f"Existe preventivo activo; antes de crear otro conviene "
                    f"comprobar si su checklist cubre específicamente este elemento."
                )

        planta = mapa_plantas.get(
            (
                _normalizar_clave(
                    edificio
                ),
                _normalizar_clave(
                    espacio
                ),
            ),
            "",
        )

        abiertos_grupo = 0

        if "_origen_dato" in grupo.columns:
            abiertos_grupo = int(
                (
                    grupo[
                        "_origen_dato"
                    ]
                    == "abierta"
                ).sum()
            )

        recomendaciones.append({
            "score": score,
            "nivel": _nivel_recomendacion(
                score
            ),
            "centro": centro,
            "edificio": edificio,
            "planta": planta,
            "espacio": espacio,
            "area": area,
            "cantidad": cantidad,
            "abiertas": abiertos_grupo,
            "primera_fecha": str(
                primera_fecha
            ),
            "ultima_fecha": str(
                ultima_fecha
            ),
            "intervalo_medio": (
                intervalo_medio
            ),
            "prioridad_alta": (
                prioridad_alta
            ),
            "patron_detectado": (
                patron_detectado
            ),
            "repeticiones_patron": (
                repeticiones_patron
            ),
            "confianza_patron": (
                confianza_patron
            ),
            "porcentaje_patron": (
                porcentaje_patron
            ),
            "descripcion": (
                _descripcion_representativa(
                    grupo
                )
            ),
            "accion": accion,
            "motivo": motivo,
            "frecuencia_actual": (
                frecuencia_actual
            ),
            "frecuencia_sugerida": (
                frecuencia_sugerida
            ),
            "dias_frecuencia_sugerida": (
                dias_frecuencia_sugerida
                if patron_detectado
                else 0
            ),
            "tiempo_preventivo_min": (
                tiempo_preventivo_min
            ),
            "revisiones_anuales_sugeridas": (
                revisiones_anuales_sugeridas
            ),
            "horas_preventivo_anuales": (
                horas_preventivo_anuales
            ),
            "cobertura_preventiva": (
                cobertura_preventiva
            ),
            "preventivo_id": (
                preventivo_id
            ),
            "tarea_preventiva": (
                tarea_preventiva
            ),
        })

    recomendaciones.sort(
        key=lambda x: (
            -x["score"],
            -x["cantidad"],
            x["edificio"],
            x["espacio"],
        )
    )

    patrones_confirmados = [
        item
        for item in recomendaciones
        if str(
            item.get("patron_detectado") or ""
        ).strip()
    ]

    patrones_con_preventivo = [
        item
        for item in patrones_confirmados
        if item.get("cobertura_preventiva")
        == "Con preventivo"
    ]

    patrones_sin_preventivo = [
        item
        for item in patrones_confirmados
        if item.get("cobertura_preventiva")
        == "Sin preventivo"
    ]

    return {
        "centro": centro,
        "dias": dias,
        "desde": str(desde),
        "total_correctivos": len(df),
        "preventivos_activos": (
            len(preventivos)
            if preventivos is not None
            and not preventivos.empty
            else 0
        ),
        "patrones_confirmados": len(
            patrones_confirmados
        ),
        "patrones_con_preventivo": len(
            patrones_con_preventivo
        ),
        "patrones_sin_preventivo": len(
            patrones_sin_preventivo
        ),
        "total_preventivos_periodo": (
            len(preventivos_periodo)
            if preventivos_periodo is not None
            and not preventivos_periodo.empty
            else 0
        ),
        "balance_areas": balance_areas,
        "grupos_analizados": len(
            agrupado
        ),
        "recomendaciones": recomendaciones,
    }
