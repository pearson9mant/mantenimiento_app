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
    if intervalo_medio is None:
        return "Mensual"

    # La revisión debe adelantarse respecto al fallo medio.
    objetivo = max(
        7,
        round(intervalo_medio * 0.70),
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
            "grupos_analizados": 0,
            "recomendaciones": [],
        }

    preventivos = _cargar_preventivos(
        centro
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

        accion = ""
        motivo = ""
        frecuencia_actual = ""
        preventivo_id = None
        tarea_preventiva = ""

        # =============================================
        # NO EXISTE PREVENTIVO
        # =============================================
        if preventivo is None:

            accion = "Crear preventivo"

            motivo = (
                f"Se han registrado {cantidad} incidencias "
                f"en {dias} días en el mismo espacio y área."
            )

        # =============================================
        # YA EXISTE PREVENTIVO
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
                and dias_actuales
                > dias_sugeridos
            ):

                accion = (
                    "Revisar frecuencia"
                )

                motivo = (
                    f"Ya existe preventivo, pero las averías "
                    f"se repiten aproximadamente cada "
                    f"{intervalo_medio} días."
                )

            else:

                accion = (
                    "Vigilar preventivo existente"
                )

                motivo = (
                    f"Existe preventivo activo, pero se han "
                    f"registrado {cantidad} correctivos en "
                    f"{dias} días."
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

    return {
        "centro": centro,
        "dias": dias,
        "desde": str(desde),
        "total_correctivos": len(df),
        "grupos_analizados": len(
            agrupado
        ),
        "recomendaciones": recomendaciones,
    }
