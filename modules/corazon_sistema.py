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
            "nan",
            "none",
            "null",
            "-",
            "sin espacio",
            "sin edificio",
        ]
    )


def obtener_historial_espacio_corazon(
    centro,
    edificio,
    espacio,
    area=None,
    numero_ot_actual=None,
):
    """
    Obtiene actuaciones activas e históricas del mismo espacio.

    La comparación se realiza por:
    - centro
    - edificio normalizado
    - espacio normalizado

    La OT que se está evaluando se excluye del recuento.
    """

    centro_txt = str(centro or "").strip()
    edificio_objetivo = normalizar_edificio(edificio)
    espacio_objetivo = normalizar(espacio)
    area_objetivo = normalizar(area)
    numero_actual = str(numero_ot_actual or "").strip()

    resultado_vacio = {
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

    if not centro_txt:
        return resultado_vacio

    if edificio_objetivo == "Sin edificio":
        return resultado_vacio

    if not _texto_valido_corazon(espacio):
        return resultado_vacio

    registros = []

    # -------------------------------------------------
    # ÓRDENES ACTIVAS
    # -------------------------------------------------

    df_activas = leer_df_corazon(
        """
        SELECT numero_ot, fecha, fecha_creacion, fecha_alta,
               centro, edificio, espacio, area, descripcion,
               estado, origen
        FROM ordenes_trabajo
        WHERE centro = ?
        """,
        (centro_txt,),
    )

    if not df_activas.empty:
        for _, fila in df_activas.iterrows():
            numero_ot = str(fila.get("numero_ot") or "").strip()

            if numero_actual and numero_ot == numero_actual:
                continue

            edificio_fila = normalizar_edificio(
                fila.get("edificio")
            )

            espacio_fila = normalizar(
                fila.get("espacio")
            )

            if edificio_fila != edificio_objetivo:
                continue

            if espacio_fila != espacio_objetivo:
                continue

            estado = normalizar(fila.get("estado"))

            if estado in ESTADOS_CIERRE:
                continue

            fecha_registro = (
                fila.get("fecha")
                or fila.get("fecha_creacion")
                or fila.get("fecha_alta")
                or ""
            )

            registros.append({
                "tipo": "Activa",
                "numero_ot": numero_ot,
                "fecha": fecha_registro,
                "area": str(fila.get("area") or "Otros"),
                "descripcion": str(
                    fila.get("descripcion") or ""
                ),
                "estado": str(fila.get("estado") or ""),
                "origen": str(fila.get("origen") or ""),
            })

    # -------------------------------------------------
    # HISTÓRICO
    # -------------------------------------------------

    df_historico = leer_df_corazon(
        """
        SELECT numero_ot, fecha, fecha_creacion, fecha_alta,
               centro, edificio, espacio, area, descripcion,
               estado, origen
        FROM historico_ordenes
        WHERE centro = ?
        """,
        (centro_txt,),
    )

    if not df_historico.empty:
        for _, fila in df_historico.iterrows():
            numero_ot = str(fila.get("numero_ot") or "").strip()

            if numero_actual and numero_ot == numero_actual:
                continue

            edificio_fila = normalizar_edificio(
                fila.get("edificio")
            )

            espacio_fila = normalizar(
                fila.get("espacio")
            )

            if edificio_fila != edificio_objetivo:
                continue

            if espacio_fila != espacio_objetivo:
                continue

            fecha_registro = (
                fila.get("fecha")
                or fila.get("fecha_creacion")
                or fila.get("fecha_alta")
                or ""
            )

            registros.append({
                "tipo": "Histórico",
                "numero_ot": numero_ot,
                "fecha": fecha_registro,
                "area": str(fila.get("area") or "Otros"),
                "descripcion": str(
                    fila.get("descripcion") or ""
                ),
                "estado": str(fila.get("estado") or ""),
                "origen": str(fila.get("origen") or ""),
            })

    if not registros:
        resultado_vacio["nivel_recurrencia"] = "Sin recurrencia"
        resultado_vacio["mensaje_recurrencia"] = (
            "No constan actuaciones anteriores en este espacio."
        )
        return resultado_vacio

    # -------------------------------------------------
    # PREPARAR FECHAS Y ORDENAR
    # -------------------------------------------------

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

    # -------------------------------------------------
    # RECUENTOS
    # -------------------------------------------------

    total = len(registros)

    activas = sum(
        1 for registro in registros
        if registro.get("tipo") == "Activa"
    )

    historicas = sum(
        1 for registro in registros
        if registro.get("tipo") == "Histórico"
    )

    areas = {}

    for registro in registros:
        nombre_area = str(
            registro.get("area") or "Otros"
        ).strip()

        areas[nombre_area] = areas.get(nombre_area, 0) + 1

    misma_area = 0

    if area_objetivo:
        misma_area = sum(
            1
            for registro in registros
            if normalizar(registro.get("area")) == area_objetivo
        )

    # -------------------------------------------------
    # NIVEL DE RECURRENCIA
    # -------------------------------------------------

    es_recurrente = False

    if total >= 10 or misma_area >= 6:
        nivel = "Muy alta"
        es_recurrente = True

        mensaje = (
            f"Este espacio acumula {total} actuaciones anteriores"
        )

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
            mensaje += (
                f" y {misma_area} del mismo área."
            )
        else:
            mensaje += "."

    elif total >= 3 or misma_area >= 2:
        nivel = "Media"

        mensaje = (
            f"Este espacio tiene {total} actuaciones anteriores"
        )

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
            f"Solo consta {total} actuación anterior "
            "en este espacio."
            if total == 1
            else f"Constan {total} actuaciones anteriores "
                 "en este espacio."
        )

    # Quitamos el campo interno usado para ordenar
    ultimas = []

    for registro in registros[:5]:
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


def construir_prioridades_globales(centro=None, operario=None, limite=100):
    df = obtener_ordenes_abiertas_corazon(centro, operario)

    if df.empty:
        return []

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


def construir_grupos_inteligentes(prioridades):
    grupos = {}

    for p in prioridades:
        clave = (
            p.get("centro", "") or "Sin centro",
            normalizar_edificio(p.get("edificio", "")),
        )

        grupos.setdefault(clave, []).append(p)

    resultado = []

    for (centro, edificio), lista in grupos.items():
        score = max(x.get("score", 0) for x in lista)

        resultado.append({
            "centro": centro,
            "edificio": edificio,
            "cantidad": len(lista),
            "score": score,
            "trabajos": lista,
        })

    resultado.sort(
        key=lambda x: (x["score"], x["cantidad"]),
        reverse=True
    )

    return resultado


def construir_ruta_inteligente(grupos, limite=5):
    ruta = []

    for g in grupos[:limite]:
        trabajos = g.get("trabajos", [])

        tipos = {}
        for t in trabajos:
            tipo = t.get("tipo_prioridad", "Otros")
            tipos[tipo] = tipos.get(tipo, 0) + 1

        edificio = g.get("edificio", "") or "Sin edificio"

        ruta.append({
            "centro": g.get("centro", ""),
            "edificio": edificio,
            "cantidad": g.get("cantidad", 0),
            "score": g.get("score", 0),
            "tipos": tipos,
            "trabajos": trabajos,
            "mensaje": (
                f"Concentrar trabajos en {edificio} permite resolver "
                f"{g.get('cantidad', 0)} actuaciones en una misma zona."
            )
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

    prioridades = construir_prioridades_globales(centro, operario, limite=100)
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
