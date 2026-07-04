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
