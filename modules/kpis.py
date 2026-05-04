import pandas as pd
from datetime import datetime
from modules.ordenes import obtener_ordenes, obtener_historico


ESTADOS_HECHAS = ["finalizada", "finalizado", "cerrada", "cerrado"]
ESTADOS_EN_PROCESO = ["en curso", "en proceso"]
ESTADOS_FALTAN = ["abierta", "pendiente", "pendiente material", "esperando material"]


def _normalizar(texto):
    return str(texto or "").strip().lower()


def _estado_grupo(estado):
    e = _normalizar(estado)

    if e in ESTADOS_HECHAS:
        return "Hechas"
    if e in ESTADOS_EN_PROCESO:
        return "En proceso"
    if e in ESTADOS_FALTAN:
        return "Faltan"

    return "Faltan"


def _origen_grupo(origen, solicitante=""):
    o = _normalizar(origen)
    s = _normalizar(solicitante)

    operarios = ["juan", "j.a.", "almeda", "luis", "abel"]

    if "legion" in o:
        return "Legionella"

    if "prevent" in o:
        return "Preventivo"

    if "outlook" in o or "forms" in o or "profesor" in o:
        return "Profesores"

    if "gerencia" in o or "direccion" in o or "dirección" in o or "noemi" in s or "noemí" in s:
        return "Gerencia"

    if any(x in s for x in operarios):
        return "Operarios"

    return "Otros"


def _a_dataframe():
    ordenes = obtener_ordenes()
    historico = obtener_historico()

    filas = []

    for ot in ordenes:
        filas.append({
            "numero_ot": ot.get("numero_ot", ""),
            "descripcion": ot.get("descripcion", ""),
            "estado": ot.get("estado", ""),
            "estado_grupo": _estado_grupo(ot.get("estado", "")),
            "fecha": ot.get("fecha", ""),
            "fecha_cierre": "",
            "centro": ot.get("centro", ""),
            "edificio": ot.get("edificio", ""),
            "area": ot.get("area", ""),
            "prioridad": ot.get("prioridad", ""),
            "operario": ot.get("operario", ""),
            "origen": ot.get("origen", ""),
            "solicitante": ot.get("solicitante", ""),
            "tipo_origen": _origen_grupo(ot.get("origen", ""), ot.get("solicitante", "")),
        })

    for ot in historico:
        filas.append({
            "numero_ot": ot.get("numero_ot", ""),
            "descripcion": ot.get("descripcion", ""),
            "estado": "Finalizada",
            "estado_grupo": "Hechas",
            "fecha": ot.get("fecha", ""),
            "fecha_cierre": ot.get("fecha_cierre", ""),
            "centro": ot.get("centro", ""),
            "edificio": ot.get("edificio", ""),
            "area": ot.get("area", ""),
            "prioridad": ot.get("prioridad", ""),
            "operario": ot.get("operario", ""),
            "origen": ot.get("origen", ""),
            "solicitante": ot.get("solicitante", ""),
            "tipo_origen": _origen_grupo(ot.get("origen", ""), ot.get("solicitante", "")),
        })

    df = pd.DataFrame(filas)

    if df.empty:
        return pd.DataFrame(columns=[
            "numero_ot", "descripcion", "estado", "estado_grupo", "fecha",
            "fecha_cierre", "centro", "edificio", "area", "prioridad",
            "operario", "origen", "solicitante", "tipo_origen", "mes"
        ])

    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["fecha_cierre_dt"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")
    df["mes"] = df["fecha_dt"].dt.strftime("%Y-%m").fillna("Sin fecha")

    df["dias_resolucion"] = (
        df["fecha_cierre_dt"] - df["fecha_dt"]
    ).dt.days

    return df


def kpis_globales():
    df = _a_dataframe()

    total = len(df)
    hechas = len(df[df["estado_grupo"] == "Hechas"])
    en_proceso = len(df[df["estado_grupo"] == "En proceso"])
    faltan = len(df[df["estado_grupo"] == "Faltan"])

    rendimiento = round((hechas / total) * 100, 1) if total else 0

    tiempo_medio = df["dias_resolucion"].dropna()
    tiempo_medio = round(tiempo_medio.mean(), 1) if not tiempo_medio.empty else 0

    return {
        "total": total,
        "hechas": hechas,
        "en_proceso": en_proceso,
        "faltan": faltan,
        "rendimiento": rendimiento,
        "tiempo_medio": tiempo_medio,
    }


def kpis_por_operario():
    df = _a_dataframe()

    if df.empty:
        return pd.DataFrame()

    tabla = df.groupby("operario").agg(
        total=("numero_ot", "count"),
        hechas=("estado_grupo", lambda x: (x == "Hechas").sum()),
        en_proceso=("estado_grupo", lambda x: (x == "En proceso").sum()),
        faltan=("estado_grupo", lambda x: (x == "Faltan").sum()),
        tiempo_medio=("dias_resolucion", "mean"),
    ).reset_index()

    tabla["rendimiento_%"] = tabla.apply(
        lambda r: round((r["hechas"] / r["total"]) * 100, 1) if r["total"] else 0,
        axis=1
    )

    tabla["tiempo_medio"] = tabla["tiempo_medio"].fillna(0).round(1)

    return tabla.sort_values("operario")


def kpis_de_operario(nombre_operario):
    df = _a_dataframe()
    nombre = _normalizar(nombre_operario)

    df = df[df["operario"].apply(lambda x: _normalizar(x) == nombre)]

    total = len(df)
    hechas = len(df[df["estado_grupo"] == "Hechas"])
    en_proceso = len(df[df["estado_grupo"] == "En proceso"])
    faltan = len(df[df["estado_grupo"] == "Faltan"])

    rendimiento = round((hechas / total) * 100, 1) if total else 0

    return {
        "total": total,
        "hechas": hechas,
        "en_proceso": en_proceso,
        "faltan": faltan,
        "rendimiento": rendimiento,
    }


def kpis_por_origen():
    df = _a_dataframe()

    if df.empty:
        return pd.DataFrame()

    tabla = df.groupby("tipo_origen").agg(
        total=("numero_ot", "count"),
        hechas=("estado_grupo", lambda x: (x == "Hechas").sum()),
        en_proceso=("estado_grupo", lambda x: (x == "En proceso").sum()),
        faltan=("estado_grupo", lambda x: (x == "Faltan").sum()),
    ).reset_index()

    tabla["rendimiento_%"] = tabla.apply(
        lambda r: round((r["hechas"] / r["total"]) * 100, 1) if r["total"] else 0,
        axis=1
    )

    return tabla.sort_values("tipo_origen")


def kpis_por_mes():
    df = _a_dataframe()

    if df.empty:
        return pd.DataFrame()

    tabla = df.groupby("mes").agg(
        total=("numero_ot", "count"),
        hechas=("estado_grupo", lambda x: (x == "Hechas").sum()),
        en_proceso=("estado_grupo", lambda x: (x == "En proceso").sum()),
        faltan=("estado_grupo", lambda x: (x == "Faltan").sum()),
    ).reset_index()

    return tabla.sort_values("mes", ascending=False)


def kpis_por_centro():
    df = _a_dataframe()

    if df.empty:
        return pd.DataFrame()

    tabla = df.groupby("centro").agg(
        total=("numero_ot", "count"),
        hechas=("estado_grupo", lambda x: (x == "Hechas").sum()),
        en_proceso=("estado_grupo", lambda x: (x == "En proceso").sum()),
        faltan=("estado_grupo", lambda x: (x == "Faltan").sum()),
    ).reset_index()

    return tabla.sort_values("centro")
