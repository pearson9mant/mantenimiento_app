from datetime import date
import pandas as pd

from database.db import conectar, _sql
from modules.inteligencia_preventivos import construir_panel_preventivo
from modules.inteligencia_legionella import construir_panel_sanitario_legionella


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

    if "legionella" in area or "legionella" in origen or "legionella" in descripcion:
        return "Sanitaria"

    if "urgente" in prioridad:
        return "Urgente"

    if "alta" in prioridad:
        return "Alta"

    if str(row.get("origen", "") or "").upper() == "PREVENTIVO":
        return "Preventiva"

    return "Incidencia"


def puntuar_orden(row):
    score = 0
    motivos = []

    area = normalizar(row.get("area"))
    origen = normalizar(row.get("origen"))
    prioridad = normalizar(row.get("prioridad"))
    descripcion = normalizar(row.get("descripcion"))

    if "legionella" in area or "legionella" in origen or "legionella" in descripcion:
        score += 95
        motivos.append("Riesgo sanitario / Legionella.")

    elif "urgente" in prioridad:
        score += 90
        motivos.append("Prioridad urgente.")

    elif "alta" in prioridad:
        score += 75
        motivos.append("Prioridad alta.")

    elif origen == "preventivo":
        score += 60
        motivos.append("Actuación preventiva pendiente.")

    elif origen in ["app", "outlook", "profesores", "externa"]:
        score += 55
        motivos.append("Incidencia o actuación externa abierta.")

    else:
        score += 40
        motivos.append("Orden abierta pendiente de gestión.")

    if "fuga" in descripcion or "agua" in descripcion or "perdida" in descripcion:
        score += 10
        motivos.append("Posible afectación por agua.")

    if "eléctr" in descripcion or "electric" in descripcion:
        score += 8
        motivos.append("Posible riesgo eléctrico.")

    if "clima" in descripcion or "aire" in descripcion:
        score += 6
        motivos.append("Afecta a climatización o confort.")

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

    return score, motivos, dias if 'dias' in locals() else None


def construir_prioridades_globales(
    centro=None,
    operario=None,
    limite=100,
    df_ordenes_abiertas=None,
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
    prioridades = []

    for _, row in df.iterrows():
        score, motivos, dias_abierta = puntuar_orden(row)

        edificio_normalizado = normalizar_edificio(
            row.get("edificio", "")
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
            "edificio_original": row.get("edificio", ""),
            "planta": row.get("planta", ""),
            "espacio": row.get("espacio", ""),
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

    prioridades.sort(key=lambda x: x["score"], reverse=True)
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

        if edificio == "Sin edificio":
            avisos.append({
                "numero_ot": p.get("numero_ot", ""),
                "titulo": p.get("titulo", ""),
                "centro": p.get("centro", ""),
                "campo": "edificio",
                "mensaje": "Esta OT no tiene edificio informado.",
            })

        if not espacio or espacio.lower() in ["nan", "none", "-"]:
            avisos.append({
                "numero_ot": p.get("numero_ot", ""),
                "titulo": p.get("titulo", ""),
                "centro": p.get("centro", ""),
                "campo": "espacio",
                "mensaje": "Esta OT no tiene espacio informado.",
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
