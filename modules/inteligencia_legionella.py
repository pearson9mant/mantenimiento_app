from datetime import date
import pandas as pd

from database.db import conectar, _sql


ESTADOS_CIERRE = ["cerrada", "cerrado", "finalizada", "finalizado"]


def leer_df_legionella(sql, params=()):
    conn = conectar()
    try:
        return pd.read_sql_query(_sql(sql), conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def _estado_color(score, vencidas, incidencias, riesgos):
    if incidencias > 0 or vencidas > 0 or riesgos > 0:
        return "rojo", "Atención sanitaria"
    if score < 85:
        return "amarillo", "Seguimiento preventivo"
    return "verde", "Correcto"


def _recomendacion(color, vencidas, incidencias, proximas, riesgos):
    if incidencias > 0:
        return "Prioridad máxima: cerrar incidencias Legionella abiertas."
    if vencidas > 0:
        return "Realizar controles vencidos y generar OT si procede."
    if riesgos > 0:
        return "Revisar controles con resultado RIESGO o INCIDENCIA."
    if proximas > 0:
        return "Programar los controles próximos antes de su vencimiento."
    return "Mantener la planificación preventiva."


def _leer_datos(centro=None):
    params = []
    filtro = ""

    if centro:
        filtro = "WHERE centro = ?"
        params.append(centro)

    puntos = leer_df_legionella(f"""
        SELECT *
        FROM legionella_puntos
        {filtro}
    """, tuple(params))

    tareas = leer_df_legionella(f"""
        SELECT *
        FROM legionella_tareas
        {filtro}
    """, tuple(params))

    incidencias = leer_df_legionella(f"""
        SELECT *
        FROM legionella_incidencias
        {filtro}
    """, tuple(params))

    registros = leer_df_legionella(f"""
        SELECT *
        FROM legionella_registros
        {filtro}
        ORDER BY fecha DESC
    """, tuple(params))

    informes = leer_df_legionella(f"""
        SELECT *
        FROM legionella_informes
        {filtro}
    """, tuple(params))

    return puntos, tareas, incidencias, registros, informes


def diagnosticar_legionella_global(centro=None):
    puntos, tareas, incidencias, registros, informes = _leer_datos(centro)

    hoy = pd.Timestamp(date.today())

    puntos_total = len(puntos) if not puntos.empty else 0
    puntos_activos = 0

    if not puntos.empty and "activo" in puntos.columns:
        puntos_activos = len(puntos[puntos["activo"].fillna(0).astype(int) == 1])

    tareas_activas_df = pd.DataFrame()

    if not tareas.empty and "activo" in tareas.columns:
        tareas_activas_df = tareas[tareas["activo"].fillna(0).astype(int) == 1].copy()

    tareas_activas = len(tareas_activas_df)

    vencidas = 0
    proximas = 0

    if not tareas_activas_df.empty and "proxima_fecha" in tareas_activas_df.columns:
        tareas_activas_df["proxima_fecha_dt"] = pd.to_datetime(
            tareas_activas_df["proxima_fecha"],
            errors="coerce"
        )

        vencidas = len(tareas_activas_df[tareas_activas_df["proxima_fecha_dt"] <= hoy])

        proximas = len(
            tareas_activas_df[
                (tareas_activas_df["proxima_fecha_dt"] > hoy)
                & (tareas_activas_df["proxima_fecha_dt"] <= hoy + pd.Timedelta(days=15))
            ]
        )

    incidencias_abiertas = 0

    if not incidencias.empty and "estado" in incidencias.columns:
        estado_inc = incidencias["estado"].fillna("").astype(str).str.lower()
        incidencias_abiertas = len(incidencias[~estado_inc.isin(ESTADOS_CIERRE)])

    riesgos_registro = 0

    if not registros.empty and "estado" in registros.columns:
        riesgos_registro = len(
            registros[
                registros["estado"]
                .fillna("")
                .astype(str)
                .str.upper()
                .isin(["RIESGO", "INCIDENCIA"])
            ]
        )

    informes_total = len(informes) if not informes.empty else 0

    score = 100
    score -= incidencias_abiertas * 18
    score -= vencidas * 10
    score -= proximas * 3
    score -= min(riesgos_registro, 6) * 6
    score = max(0, min(100, score))

    color, estado = _estado_color(score, vencidas, incidencias_abiertas, riesgos_registro)

    recomendacion = _recomendacion(
        color=color,
        vencidas=vencidas,
        incidencias=incidencias_abiertas,
        proximas=proximas,
        riesgos=riesgos_registro
    )

    diagnostico = []

    diagnostico.append(f"{puntos_activos} punto(s) activo(s) de control.")
    diagnostico.append(f"{tareas_activas} control(es) planificado(s).")

    if vencidas > 0:
        diagnostico.append(f"{vencidas} control(es) vencido(s).")

    if proximas > 0:
        diagnostico.append(f"{proximas} control(es) próximo(s) a vencer.")

    if incidencias_abiertas > 0:
        diagnostico.append(f"{incidencias_abiertas} incidencia(s) abierta(s).")

    if riesgos_registro > 0:
        diagnostico.append(f"{riesgos_registro} registro(s) con riesgo o incidencia.")

    if informes_total > 0:
        diagnostico.append(f"{informes_total} informe(s) externo(s) archivado(s).")

    if not diagnostico:
        diagnostico.append("Sin datos suficientes para valorar la instalación.")

    return {
        "centro": centro or "Todos",
        "estado": estado,
        "color": color,
        "score": score,
        "puntos_total": puntos_total,
        "puntos_activos": puntos_activos,
        "tareas_activas": tareas_activas,
        "controles_vencidos": vencidas,
        "controles_proximos": proximas,
        "incidencias_abiertas": incidencias_abiertas,
        "riesgos_registro": riesgos_registro,
        "informes_total": informes_total,
        "diagnostico": diagnostico,
        "recomendacion": recomendacion,
    }


def obtener_prioridades_legionella(centro=None, limite=5):
    puntos, tareas, incidencias, registros, informes = _leer_datos(centro)
    prioridades = []

    if not incidencias.empty:
        estado = incidencias["estado"].fillna("").astype(str).str.lower()
        abiertas = incidencias[~estado.isin(ESTADOS_CIERRE)].copy()

        for _, row in abiertas.head(limite).iterrows():
            prioridades.append({
                "nivel": "rojo",
                "tipo": "Incidencia abierta",
                "centro": row.get("centro", ""),
                "edificio": row.get("edificio", ""),
                "punto": row.get("punto", ""),
                "descripcion": row.get("descripcion", ""),
                "accion": "Resolver incidencia Legionella.",
            })

    if len(prioridades) >= limite:
        return prioridades[:limite]

    if not tareas.empty and "proxima_fecha" in tareas.columns:
        hoy = pd.Timestamp(date.today())
        tareas_tmp = tareas.copy()
        tareas_tmp["proxima_fecha_dt"] = pd.to_datetime(tareas_tmp["proxima_fecha"], errors="coerce")

        vencidas = tareas_tmp[
            (tareas_tmp["activo"].fillna(0).astype(int) == 1)
            & (tareas_tmp["proxima_fecha_dt"] <= hoy)
        ].sort_values("proxima_fecha_dt")

        for _, row in vencidas.head(limite - len(prioridades)).iterrows():
            prioridades.append({
                "nivel": "rojo",
                "tipo": "Control vencido",
                "centro": row.get("centro", ""),
                "edificio": row.get("edificio", ""),
                "punto": row.get("punto", ""),
                "descripcion": f"{row.get('tarea', '')} vencido desde {row.get('proxima_fecha', '')}",
                "accion": "Realizar control y registrar resultado.",
            })

    return prioridades[:limite]

# ======================================================
# MOTOR DE CRITICIDAD LEGIONELLA
# ======================================================

def evaluar_nivel_criticidad(score):
    score = int(score or 0)

    if score >= 81:
        return "Crítico", "rojo"
    if score >= 61:
        return "Alto", "rojo"
    if score >= 41:
        return "Vigilancia", "amarillo"
    if score >= 21:
        return "Bueno", "verde"

    return "Excelente", "verde"


def _peso_tipo_punto(tipo_punto, nombre_punto="", tarea=""):
    texto = f"{tipo_punto} {nombre_punto} {tarea}".lower()

    if "acumulador" in texto and "solar" not in texto:
        return 25, "Punto crítico: acumulador ACS."

    if "retorno" in texto:
        return 20, "Punto crítico: retorno ACS."

    if "solar" in texto:
        return 18, "Punto sensible: acumulador solar."

    if "ducha" in texto:
        return 15, "Punto sensible: ducha."

    if "grifo" in texto or "terminal" in texto:
        return 10, "Punto terminal de control."

    if "muestra" in texto:
        return 8, "Punto de muestra."

    return 5, "Punto de control general."


def _peso_resultado_registro(registro):
    if not registro:
        return 0, ""

    estado = str(registro.get("estado") or "").upper()
    resultado = str(registro.get("resultado") or "")

    if estado == "RIESGO":
        return 35, f"Último registro en RIESGO: {resultado}"

    if estado == "INCIDENCIA":
        return 25, f"Último registro con incidencia: {resultado}"

    return 0, "Último registro correcto."


def _peso_incidencia(incidencia):
    if not incidencia:
        return 0, ""

    estado = str(incidencia.get("estado") or "").lower()

    if estado not in ESTADOS_CIERRE:
        return 30, "Existe incidencia Legionella abierta."

    return 0, ""


def _accion_por_contexto(punto, registro=None, incidencia=None):
    texto = (
        f"{punto.get('tipo_punto', '')} "
        f"{punto.get('nombre_punto', '')} "
        f"{punto.get('tipo_control_punto', '')} "
        f"{registro.get('resultado', '') if registro else ''}"
    ).lower()

    if incidencia:
        return "Resolver la incidencia abierta y registrar cierre técnico."

    if "retorno" in texto:
        return "Comprobar bomba de recirculación, purga de aire y temperatura de retorno."

    if "acumulador" in texto and "solar" not in texto:
        return "Comprobar consigna, producción ACS y recuperación térmica."

    if "solar" in texto:
        return "Revisar acumulador solar y confirmar temperatura real de acumulación."

    if "cloro" in texto:
        return "Repetir medición de cloro y comprobar dosificación / renovación de agua."

    if "afs" in texto or "agua fría" in texto:
        return "Comprobar temperatura AFCH, uso del punto y posible mezcla con ACS."

    if "ducha" in texto or "grifo" in texto:
        return "Realizar purga, revisar aireador y repetir control terminal."

    return "Mantener seguimiento preventivo según planificación."


def calcular_criticidad_punto(punto, ultimo_registro=None, incidencia=None):
    """
    Calcula la criticidad sanitaria de un punto Legionella.
    No modifica datos. Solo interpreta.
    """

    score = 0
    motivos = []

    peso, motivo = _peso_tipo_punto(
        punto.get("tipo_punto", ""),
        punto.get("nombre_punto", ""),
        punto.get("tipo_control_punto", "")
    )
    score += peso
    motivos.append(motivo)

    peso, motivo = _peso_resultado_registro(ultimo_registro)
    score += peso
    if motivo:
        motivos.append(motivo)

    peso, motivo = _peso_incidencia(incidencia)
    score += peso
    if motivo:
        motivos.append(motivo)

    score = max(0, min(100, score))

    nivel, color = evaluar_nivel_criticidad(score)

    return {
        "score": score,
        "nivel": nivel,
        "color": color,
        "motivos": motivos,
        "accion": _accion_por_contexto(punto, ultimo_registro, incidencia),
    }


def obtener_criticidad_puntos_legionella(centro=None, limite=20):
    puntos, tareas, incidencias, registros, informes = _leer_datos(centro)

    if puntos.empty:
        return []

    resultados = []

    for _, punto_row in puntos.iterrows():
        punto = punto_row.to_dict()
        nombre_punto = str(punto.get("nombre_punto") or "")

        ultimo_registro = None
        incidencia = None

        if not registros.empty and "punto" in registros.columns:
            df_reg = registros[
                registros["punto"].fillna("").astype(str) == nombre_punto
            ]

            if not df_reg.empty:
                ultimo_registro = df_reg.iloc[0].to_dict()

        if not incidencias.empty and "punto" in incidencias.columns:
            df_inc = incidencias[
                incidencias["punto"].fillna("").astype(str) == nombre_punto
            ]

            if not df_inc.empty:
                estados = df_inc["estado"].fillna("").astype(str).str.lower()
                abiertas = df_inc[~estados.isin(ESTADOS_CIERRE)]

                if not abiertas.empty:
                    incidencia = abiertas.iloc[0].to_dict()

        critica = calcular_criticidad_punto(
            punto=punto,
            ultimo_registro=ultimo_registro,
            incidencia=incidencia
        )

        resultados.append({
            "centro": punto.get("centro", ""),
            "edificio": punto.get("edificio", ""),
            "instalacion": punto.get("instalacion", ""),
            "punto": nombre_punto,
            "tipo_punto": punto.get("tipo_punto", ""),
            "score": critica["score"],
            "nivel": critica["nivel"],
            "color": critica["color"],
            "motivos": critica["motivos"],
            "accion": critica["accion"],
        })

    resultados = sorted(
        resultados,
        key=lambda x: x["score"],
        reverse=True
    )

    return resultados[:limite]

# ======================================================
# MOTOR DE ESTABILIDAD LEGIONELLA
# ======================================================

def evaluar_estabilidad_punto(nombre_punto, registros):
    """
    Evalúa si un punto Legionella es estable según sus últimos registros.
    Solo interpreta datos. No modifica nada.
    """

    if registros is None or registros.empty:
        return {
            "score": 50,
            "estado": "Sin histórico suficiente",
            "color": "amarillo",
            "mensaje": "No hay suficientes registros para valorar la estabilidad.",
            "motivos": ["Histórico insuficiente."],
        }

    df = registros.copy()

    if "punto" in df.columns:
        df = df[df["punto"].fillna("").astype(str) == str(nombre_punto)]

    if df.empty or len(df) < 3:
        return {
            "score": 55,
            "estado": "Histórico corto",
            "color": "amarillo",
            "mensaje": "El punto tiene pocos controles registrados. Conviene seguir acumulando histórico.",
            "motivos": ["Menos de 3 registros disponibles."],
        }

    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.sort_values("fecha_dt", ascending=False).head(8)

    riesgos = 0

    if "estado" in df.columns:
        riesgos = len(
            df[
                df["estado"]
                .fillna("")
                .astype(str)
                .str.upper()
                .isin(["RIESGO", "INCIDENCIA"])
            ]
        )

    valores = []

    for col in ["valor", "valor_2", "valor_3"]:
        if col in df.columns:
            serie = pd.to_numeric(df[col], errors="coerce").dropna()
            if not serie.empty:
                valores.extend(serie.tolist())

    variacion = 0

    if valores:
        try:
            variacion = max(valores) - min(valores)
        except Exception:
            variacion = 0

    score = 100
    score -= riesgos * 20

    if variacion > 15:
        score -= 25
    elif variacion > 8:
        score -= 15
    elif variacion > 4:
        score -= 8

    score = max(0, min(100, int(score)))

    motivos = []

    if riesgos > 0:
        motivos.append(f"{riesgos} registro(s) con riesgo o incidencia.")

    if variacion > 0:
        motivos.append(f"Variación observada aproximada: {round(variacion, 2)}.")

    if score >= 90:
        return {
            "score": score,
            "estado": "Muy estable",
            "color": "verde",
            "mensaje": "El punto mantiene un comportamiento muy estable.",
            "motivos": motivos or ["Sin desviaciones relevantes."],
        }

    if score >= 70:
        return {
            "score": score,
            "estado": "Estable",
            "color": "verde",
            "mensaje": "El punto presenta estabilidad aceptable.",
            "motivos": motivos or ["Sin incidencias relevantes."],
        }

    if score >= 50:
        return {
            "score": score,
            "estado": "Vigilancia",
            "color": "amarillo",
            "mensaje": "El punto requiere seguimiento preventivo.",
            "motivos": motivos or ["Se recomienda revisar próximos registros."],
        }

    return {
        "score": score,
        "estado": "Inestable",
        "color": "rojo",
        "mensaje": "El punto presenta señales de inestabilidad sanitaria o técnica.",
        "motivos": motivos or ["Revisar punto y controles asociados."],
    }


def obtener_estabilidad_puntos_legionella(centro=None, limite=20):
    puntos, tareas, incidencias, registros, informes = _leer_datos(centro)

    if puntos.empty:
        return []

    resultados = []

    for _, punto_row in puntos.iterrows():
        punto = punto_row.to_dict()
        nombre_punto = str(punto.get("nombre_punto") or "")

        estabilidad = evaluar_estabilidad_punto(
            nombre_punto=nombre_punto,
            registros=registros
        )

        resultados.append({
            "centro": punto.get("centro", ""),
            "edificio": punto.get("edificio", ""),
            "instalacion": punto.get("instalacion", ""),
            "punto": nombre_punto,
            "score": estabilidad["score"],
            "estado": estabilidad["estado"],
            "color": estabilidad["color"],
            "mensaje": estabilidad["mensaje"],
            "motivos": estabilidad["motivos"],
        })

    resultados = sorted(
        resultados,
        key=lambda x: x["score"]
    )

    return resultados[:limite]

# ======================================================
# MOTOR DE TEMPERATURAS LEGIONELLA
# ======================================================

def _evaluar_valor_temperatura(tarea, valor, valor_2=None, valor_3=None):
    tarea_txt = str(tarea or "").lower()

    try:
        v1 = float(valor)
    except Exception:
        v1 = None

    try:
        v2 = float(valor_2)
    except Exception:
        v2 = None

    try:
        v3 = float(valor_3)
    except Exception:
        v3 = None

    problemas = []

    if "sala acs" in tarea_txt:
        if v1 is not None and v1 < 60:
            problemas.append("Acumulador ACS inferior a 60 ºC.")
        if v2 is not None and v2 < 50:
            problemas.append("Impulsión ACS inferior a 50 ºC.")
        if v3 is not None and v3 < 50:
            problemas.append("Retorno ACS inferior a 50 ºC.")

    elif "acumulador" in tarea_txt and v1 is not None:
        if v1 < 60:
            problemas.append("Acumulador ACS inferior a 60 ºC.")

    elif "retorno" in tarea_txt and v1 is not None:
        if v1 < 50:
            problemas.append("Retorno ACS inferior a 50 ºC.")

    elif "impulsión" in tarea_txt and v1 is not None:
        if v1 < 50:
            problemas.append("Impulsión ACS inferior a 50 ºC.")

    elif "acs terminal" in tarea_txt and v1 is not None:
        if v1 < 50:
            problemas.append("ACS terminal inferior a 50 ºC.")

    elif "afs" in tarea_txt and v1 is not None:
        if v1 > 25:
            problemas.append("AFCH superior a 25 ºC.")

    elif "punto terminal completo" in tarea_txt:
        if v1 is not None and v1 > 25:
            problemas.append("AFCH superior a 25 ºC.")
        if v3 is not None and v3 < 50:
            problemas.append("ACS terminal inferior a 50 ºC.")

    return problemas


def evaluar_temperaturas_legionella(centro=None):
    """
    Evalúa el comportamiento térmico de la instalación.
    Solo interpreta registros. No modifica datos.
    """

    puntos, tareas, incidencias, registros, informes = _leer_datos(centro)

    if registros.empty:
        return {
            "score": 50,
            "estado": "Sin datos térmicos",
            "color": "amarillo",
            "fuera_rango": 0,
            "controles_revisados": 0,
            "mensaje": "No hay registros suficientes para valorar temperaturas.",
            "motivos": ["Todavía no existe histórico térmico suficiente."],
        }

    df = registros.copy()

    if "fecha" in df.columns:
        df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
        df = df.sort_values("fecha_dt", ascending=False).head(60)

    fuera_rango = 0
    controles_revisados = 0
    motivos = []

    for _, row in df.iterrows():
        tarea = row.get("tarea", "")
        valor = row.get("valor", None)
        valor_2 = row.get("valor_2", None)
        valor_3 = row.get("valor_3", None)

        problemas = _evaluar_valor_temperatura(
            tarea=tarea,
            valor=valor,
            valor_2=valor_2,
            valor_3=valor_3
        )

        controles_revisados += 1

        if problemas:
            fuera_rango += len(problemas)
            punto = row.get("punto", "")
            for problema in problemas:
                motivos.append(f"{punto}: {problema}")

    score = 100
    score -= fuera_rango * 12
    score = max(0, min(100, score))

    if fuera_rango == 0:
        return {
            "score": score,
            "estado": "Temperaturas correctas",
            "color": "verde",
            "fuera_rango": fuera_rango,
            "controles_revisados": controles_revisados,
            "mensaje": "Los últimos controles térmicos están dentro de los valores esperados.",
            "motivos": ["Sin desviaciones térmicas relevantes."],
        }

    if fuera_rango <= 2:
        return {
            "score": score,
            "estado": "Vigilancia térmica",
            "color": "amarillo",
            "fuera_rango": fuera_rango,
            "controles_revisados": controles_revisados,
            "mensaje": "Se han detectado algunas desviaciones térmicas que conviene revisar.",
            "motivos": motivos[:6],
        }

    return {
        "score": score,
        "estado": "Riesgo térmico",
        "color": "rojo",
        "fuera_rango": fuera_rango,
        "controles_revisados": controles_revisados,
        "mensaje": "Existen varias temperaturas fuera de rango en controles recientes.",
        "motivos": motivos[:8],
    }

# ======================================================
# MOTOR DE PLANIFICACIÓN LEGIONELLA
# ======================================================

def evaluar_planificacion_legionella(centro=None):
    """
    Evalúa si la planificación Legionella está controlada.
    Solo interpreta tareas. No modifica datos.
    """

    puntos, tareas, incidencias, registros, informes = _leer_datos(centro)

    if tareas.empty:
        return {
            "score": 40,
            "estado": "Sin planificación",
            "color": "rojo",
            "total": 0,
            "activas": 0,
            "vencidas": 0,
            "proximas": 0,
            "sin_fecha": 0,
            "mensaje": "No existe planificación activa de Legionella.",
            "motivos": ["Crear planificación automática desde puntos."],
        }

    df = tareas.copy()

    if "activo" in df.columns:
        df_activas = df[df["activo"].fillna(0).astype(int) == 1].copy()
    else:
        df_activas = df.copy()

    total = len(df)
    activas = len(df_activas)

    if df_activas.empty:
        return {
            "score": 45,
            "estado": "Planificación inactiva",
            "color": "rojo",
            "total": total,
            "activas": 0,
            "vencidas": 0,
            "proximas": 0,
            "sin_fecha": 0,
            "mensaje": "Existen tareas, pero ninguna está activa.",
            "motivos": ["Activar las tareas necesarias o revisar configuración."],
        }

    hoy = pd.Timestamp(date.today())

    df_activas["proxima_fecha_dt"] = pd.to_datetime(
        df_activas.get("proxima_fecha", ""),
        errors="coerce"
    )

    sin_fecha = len(df_activas[df_activas["proxima_fecha_dt"].isna()])
    vencidas = len(df_activas[df_activas["proxima_fecha_dt"] <= hoy])
    proximas = len(
        df_activas[
            (df_activas["proxima_fecha_dt"] > hoy)
            & (df_activas["proxima_fecha_dt"] <= hoy + pd.Timedelta(days=15))
        ]
    )

    score = 100
    score -= vencidas * 12
    score -= proximas * 4
    score -= sin_fecha * 8
    score = max(0, min(100, int(score)))

    motivos = []

    if vencidas > 0:
        motivos.append(f"{vencidas} control(es) vencido(s).")

    if proximas > 0:
        motivos.append(f"{proximas} control(es) próximo(s) a vencer.")

    if sin_fecha > 0:
        motivos.append(f"{sin_fecha} tarea(s) sin próxima fecha.")

    if score >= 90:
        estado = "Planificación excelente"
        color = "verde"
        mensaje = "La planificación preventiva está controlada."
        motivos = motivos or ["Todos los controles activos están en fecha."]
    elif score >= 70:
        estado = "Planificación en seguimiento"
        color = "amarillo"
        mensaje = "La planificación está razonablemente controlada, con controles próximos o pequeños ajustes pendientes."
    else:
        estado = "Planificación crítica"
        color = "rojo"
        mensaje = "Existen controles vencidos o tareas sin fecha que requieren revisión."

    return {
        "score": score,
        "estado": estado,
        "color": color,
        "total": total,
        "activas": activas,
        "vencidas": vencidas,
        "proximas": proximas,
        "sin_fecha": sin_fecha,
        "mensaje": mensaje,
        "motivos": motivos,
    }
