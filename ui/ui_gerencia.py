import streamlit as st
import pandas as pd
from database.db import conectar

from config_gerencia import (
    TIPOS_SOLICITANTE,
    ESTADOS_HECHAS,
    ESTADOS_EN_PROCESO,
    ESTADOS_FALTAN,
    MOSTRAR_MESES,
    MOSTRAR_CENTROS,
    MOSTRAR_INVENTARIO,
    STOCK_BAJO,
)

try:
    from modules.inventario_aulas import obtener_inventario_aulas
except Exception:
    obtener_inventario_aulas = None


def leer_tabla(nombre_tabla):
    conn = conectar()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {nombre_tabla}", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


def clasificar_estado(estado):
    estado = str(estado).strip()

    if estado in ESTADOS_HECHAS:
        return "Hechas"

    if estado in ESTADOS_EN_PROCESO:
        return "En proceso"

    if estado in ESTADOS_FALTAN:
        return "Faltan"

    return "Faltan"


def clasificar_solicitante(row):
    solicitante = str(row.get("solicitante", "")).strip()
    origen = str(row.get("origen", "")).strip()

    texto = f"{solicitante} {origen}".lower()

    for tipo, nombres in TIPOS_SOLICITANTE.items():
        for nombre in nombres:
            if nombre.lower() in texto:
                return tipo

    if "profesor" in texto or "forms" in texto or "outlook" in texto:
        return "Profesores"

    if "incidencia profesor" in texto or "profesores" in texto:
        return "Profesores"

    if solicitante:
        return "Profesores"

    return "Sin clasificar"


def preparar_ordenes():
    ordenes = leer_tabla("ordenes_trabajo")
    historico = leer_tabla("historico_ordenes")

    if ordenes.empty and historico.empty:
        return pd.DataFrame()

    if not historico.empty:
        historico["estado"] = "Finalizada"

    df = pd.concat([ordenes, historico], ignore_index=True)

    columnas_defecto = {
        "fecha_creacion": "",
        "fecha_cierre": "",
        "estado": "Abierta",
        "centro": "Sin centro",
        "edificio": "",
        "espacio": "",
        "descripcion": "",
        "operario": "Sin asignar",
        "solicitante": "",
        "origen": "",
        "numero_ot": "",
    }

    for col, valor in columnas_defecto.items():
        if col not in df.columns:
            df[col] = valor

    df["grupo_estado"] = df["estado"].apply(clasificar_estado)
    df["tipo_solicitante"] = df.apply(clasificar_solicitante, axis=1)

    df["fecha_dt"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["fecha_cierre_dt"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")

    df["mes"] = df["fecha_dt"].dt.strftime("%Y-%m").fillna("Sin fecha")

    df["dias_resolucion"] = (
        df["fecha_cierre_dt"] - df["fecha_dt"]
    ).dt.days

    return df


def calcular_metricas(df):
    total = len(df)
    hechas = len(df[df["grupo_estado"] == "Hechas"])
    proceso = len(df[df["grupo_estado"] == "En proceso"])
    faltan = len(df[df["grupo_estado"] == "Faltan"])
    rendimiento = round((hechas / total) * 100, 1) if total else 0

    tiempo = df["dias_resolucion"].dropna() if "dias_resolucion" in df.columns else pd.Series(dtype=float)
    tiempo_medio = round(tiempo.mean(), 1) if not tiempo.empty else 0

    return total, hechas, proceso, faltan, rendimiento, tiempo_medio


def mostrar_estado_general(df):
    total, hechas, proceso, faltan, rendimiento, tiempo_medio = calcular_metricas(df)

    st.markdown("### 🚦 Estado general")

    if total == 0:
        st.info("No hay datos suficientes para valorar el estado general.")
        return

    if faltan >= 15:
        st.error(f"🔴 Atención: hay {faltan} órdenes pendientes. Conviene priorizar cierres.")
    elif faltan >= 6:
        st.warning(f"🟠 Hay {faltan} órdenes pendientes. Situación controlada, pero a vigilar.")
    else:
        st.success(f"🟢 Mantenimiento controlado. Pendientes actuales: {faltan}.")

    if rendimiento < 50:
        st.warning(f"Rendimiento bajo: {rendimiento}%.")
    elif rendimiento >= 75:
        st.success(f"Buen rendimiento: {rendimiento}%.")
    else:
        st.info(f"Rendimiento actual: {rendimiento}%.")


def mostrar_metricas(df):
    total, hechas, proceso, faltan, rendimiento, tiempo_medio = calcular_metricas(df)

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Total OTs", total)
    c2.metric("Hechas", hechas)
    c3.metric("En proceso", proceso)
    c4.metric("Faltan", faltan)
    c5.metric("Rendimiento", f"{rendimiento}%")
    c6.metric("Media cierre", f"{tiempo_medio} días")


def mostrar_legionella():
    registros = leer_tabla("legionella_registros")
    incidencias = leer_tabla("legionella_incidencias")

    if registros.empty and incidencias.empty:
        return

    st.markdown("### 💧 Legionella")

    total = len(registros)
    ok = 0
    riesgos = 0
    incidencias_abiertas = 0

    if not registros.empty and "estado" in registros.columns:
        ok = len(registros[registros["estado"].astype(str).str.upper() == "OK"])
        riesgos = len(registros[registros["estado"].astype(str).str.upper().isin(["RIESGO", "INCIDENCIA"])])

    if not incidencias.empty and "estado" in incidencias.columns:
        incidencias_abiertas = len(
            incidencias[
                incidencias["estado"].astype(str).str.lower().isin(["abierta", "pendiente"])
            ]
        )

    cumplimiento = round((ok / total) * 100, 1) if total else 0

    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Controles", total)
    l2.metric("Correctos", ok)
    l3.metric("Riesgos/incidencias", riesgos)
    l4.metric("Cumplimiento", f"{cumplimiento}%")

    if incidencias_abiertas > 0:
        st.error(f"🔴 Hay {incidencias_abiertas} incidencias de Legionella abiertas.")
    elif riesgos > 0:
        st.warning("🟠 Hay registros de Legionella con riesgo/incidencia en el histórico.")
    else:
        st.success("🟢 Legionella sin incidencias abiertas.")

    with st.expander("💧 Detalle Legionella", expanded=False):
        if not registros.empty:
            columnas = [
                "fecha",
                "centro",
                "edificio",
                "punto",
                "tarea",
                "valor",
                "unidad",
                "estado",
                "resultado",
                "operario",
            ]
            columnas = [c for c in columnas if c in registros.columns]
            st.dataframe(registros[columnas], use_container_width=True, hide_index=True)

        if not incidencias.empty:
            st.markdown("#### Incidencias")
            st.dataframe(incidencias, use_container_width=True, hide_index=True)


def mostrar_tabla_resumen(df, columnas):
    if df.empty:
        st.info("No hay datos para mostrar.")
        return

    tabla = (
        df.groupby(columnas + ["grupo_estado"])
        .size()
        .reset_index(name="cantidad")
    )

    pivot = tabla.pivot_table(
        index=columnas,
        columns="grupo_estado",
        values="cantidad",
        fill_value=0
    ).reset_index()

    for col in ["Hechas", "En proceso", "Faltan"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot["Total"] = pivot["Hechas"] + pivot["En proceso"] + pivot["Faltan"]
    pivot["Rendimiento %"] = pivot.apply(
        lambda r: round((r["Hechas"] / r["Total"]) * 100, 1) if r["Total"] else 0,
        axis=1
    )

    columnas_orden = columnas + ["Hechas", "En proceso", "Faltan", "Total", "Rendimiento %"]
    pivot = pivot[columnas_orden]

    st.dataframe(pivot, use_container_width=True, hide_index=True)


def mostrar_rendimiento_operarios(df):
    if df.empty:
        st.info("No hay datos para mostrar.")
        return

    if "operario" not in df.columns:
        st.info("No hay columna de operario.")
        return

    tabla = (
        df.groupby("operario")
        .agg(
            Total=("grupo_estado", "count"),
            Hechas=("grupo_estado", lambda x: (x == "Hechas").sum()),
            En_proceso=("grupo_estado", lambda x: (x == "En proceso").sum()),
            Faltan=("grupo_estado", lambda x: (x == "Faltan").sum()),
            Media_cierre_dias=("dias_resolucion", "mean"),
        )
        .reset_index()
    )

    tabla["Rendimiento %"] = tabla.apply(
        lambda r: round((r["Hechas"] / r["Total"]) * 100, 1) if r["Total"] else 0,
        axis=1
    )

    tabla["Media_cierre_dias"] = tabla["Media_cierre_dias"].fillna(0).round(1)

    tabla = tabla.rename(columns={
        "operario": "Operario",
        "En_proceso": "En proceso",
        "Media_cierre_dias": "Media cierre días",
    })

    tabla = tabla.sort_values(["Faltan", "Total"], ascending=[False, False])

    st.dataframe(
        tabla[
            [
                "Operario",
                "Total",
                "Hechas",
                "En proceso",
                "Faltan",
                "Rendimiento %",
                "Media cierre días",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


def mostrar_inventario():
    inventario = leer_tabla("inventario")

    if inventario.empty:
        st.info("No hay inventario registrado.")
        return

    st.markdown("### 📦 Inventario")

    if "activo" in inventario.columns:
        inventario = inventario[inventario["activo"].fillna(1).astype(int) == 1]

    if "stock" not in inventario.columns:
        inventario["stock"] = 0

    inventario["stock"] = pd.to_numeric(inventario["stock"], errors="coerce").fillna(0)

    bajo_stock = inventario[inventario["stock"] <= STOCK_BAJO]

    c1, c2, c3 = st.columns(3)

    c1.metric("Materiales activos", len(inventario))
    c2.metric("Stock bajo", len(bajo_stock))

    if "coste_total" in inventario.columns:
        inventario["coste_total"] = pd.to_numeric(
            inventario["coste_total"],
            errors="coerce"
        ).fillna(0)

        coste_total = inventario["coste_total"].sum()
        c3.metric("Valor inventario", f"{coste_total:,.2f} €")
    else:
        c3.metric("Valor inventario", "Sin datos")

    if len(bajo_stock) > 0:
        st.warning(f"⚠️ Hay {len(bajo_stock)} materiales con stock bajo.")
    else:
        st.success("🟢 Stock general correcto.")

    with st.expander("📉 Materiales con stock bajo", expanded=False):
        if bajo_stock.empty:
            st.success("No hay materiales con stock bajo.")
        else:
            columnas = [
                "codigo",
                "material",
                "categoria",
                "stock",
                "ubicacion",
            ]
            columnas = [c for c in columnas if c in bajo_stock.columns]
            st.dataframe(bajo_stock[columnas], use_container_width=True, hide_index=True)

    with st.expander("📦 Inventario completo", expanded=False):
        columnas = [
            "codigo",
            "material",
            "categoria",
            "stock",
            "precio_unitario",
            "coste_total",
            "ubicacion",
        ]
        columnas = [c for c in columnas if c in inventario.columns]
        st.dataframe(inventario[columnas], use_container_width=True, hide_index=True)


def cargar_inventario_aulas_df():
    columnas = [
        "id",
        "fecha_revision",
        "centro",
        "edificio",
        "espacio",
        "elemento",
        "cantidad",
        "estado",
        "ancho",
        "alto",
        "fondo",
        "unidad",
        "observaciones",
        "foto",
        "operario",
        "fecha_creacion",
    ]

    if obtener_inventario_aulas is not None:
        try:
            datos = obtener_inventario_aulas()
            if datos:
                return pd.DataFrame(datos, columns=columnas)
        except Exception:
            pass

    aulas = leer_tabla("inventario_aulas")

    if aulas.empty:
        aulas = leer_tabla("aulas_inventario")

    return aulas


def mostrar_inventario_aulas():
    aulas = cargar_inventario_aulas_df()

    if aulas.empty:
        st.info("No hay inventario de aulas registrado.")
        return

    st.markdown("### 🏫 Inventario de aulas")

    columnas_base = [
        "fecha_revision",
        "centro",
        "edificio",
        "espacio",
        "elemento",
        "cantidad",
        "estado",
        "ancho",
        "alto",
        "fondo",
        "unidad",
        "observaciones",
        "operario",
        "fecha_creacion",
    ]

    total_registros = len(aulas)

    estados_malos = [
        "mal",
        "malo",
        "averiado",
        "averiada",
        "revisar",
        "pendiente",
        "deteriorado",
        "deteriorada",
        "roto",
        "rota",
        "regular",
    ]

    elementos_revisar = 0

    if "estado" in aulas.columns:
        elementos_revisar = len(
            aulas[
                aulas["estado"]
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(estados_malos)
            ]
        )

    a1, a2 = st.columns(2)
    a1.metric("Registros aulas", total_registros)
    a2.metric("Elementos a revisar", elementos_revisar)

    if elementos_revisar > 0:
        st.warning(f"⚠️ Hay {elementos_revisar} elementos de aula a revisar.")
    else:
        st.success("🟢 Inventario de aulas sin elementos críticos.")

    with st.expander("⚠️ Elementos de aula a revisar", expanded=False):
        if "estado" not in aulas.columns:
            st.info("No hay columna de estado en inventario de aulas.")
        else:
            revisar = aulas[
                aulas["estado"]
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(estados_malos)
            ]

            if revisar.empty:
                st.success("No hay elementos de aula pendientes de revisar.")
            else:
                columnas_revisar = [c for c in columnas_base if c in revisar.columns]
                st.dataframe(
                    revisar[columnas_revisar] if columnas_revisar else revisar,
                    use_container_width=True,
                    hide_index=True
                )

    with st.expander("🏫 Inventario de aulas completo", expanded=False):
        columnas = [c for c in columnas_base if c in aulas.columns]
        st.dataframe(
            aulas[columnas] if columnas else aulas,
            use_container_width=True,
            hide_index=True
        )


def pantalla_gerencia():
    st.subheader("📊 Gerencia Pro")

    df = preparar_ordenes()

    if df.empty:
        st.warning("No hay órdenes para analizar.")

        mostrar_legionella()

        if MOSTRAR_INVENTARIO:
            st.markdown("---")
            mostrar_inventario()

            st.markdown("---")
            mostrar_inventario_aulas()

        return

    st.markdown("### 🔎 Filtros")

    col1, col2 = st.columns(2)

    centros = ["Todos"] + sorted(df["centro"].dropna().astype(str).unique().tolist())
    centro_sel = col1.selectbox("Centro", centros)

    meses = ["Todos"] + sorted(df["mes"].dropna().astype(str).unique().tolist(), reverse=True)
    mes_sel = col2.selectbox("Mes", meses)

    if centro_sel != "Todos":
        df = df[df["centro"] == centro_sel]

    if mes_sel != "Todos":
        df = df[df["mes"] == mes_sel]

    st.markdown("---")

    mostrar_metricas(df)

    st.markdown("---")

    mostrar_estado_general(df)

    st.markdown("---")

    mostrar_legionella()

    st.markdown("---")

    with st.expander("📌 Órdenes por tipo de solicitante", expanded=False):
        mostrar_tabla_resumen(df, ["tipo_solicitante"])

    with st.expander("👷 Órdenes por operario", expanded=False):
        mostrar_tabla_resumen(df, ["operario"])

    with st.expander("📈 Rendimiento real por operario", expanded=False):
        mostrar_rendimiento_operarios(df)

    if MOSTRAR_CENTROS:
        with st.expander("🏫 Órdenes por centro", expanded=False):
            mostrar_tabla_resumen(df, ["centro"])

    if MOSTRAR_MESES:
        with st.expander("📅 Órdenes por mes", expanded=False):
            mostrar_tabla_resumen(df, ["mes"])

    with st.expander("📋 Detalle de órdenes", expanded=False):
        columnas = [
            "numero_ot",
            "fecha",
            "fecha_cierre",
            "centro",
            "edificio",
            "espacio",
            "descripcion",
            "estado",
            "grupo_estado",
            "operario",
            "solicitante",
            "tipo_solicitante",
            "origen",
            "dias_resolucion",
        ]

        columnas = [c for c in columnas if c in df.columns]

        st.dataframe(
            df[columnas],
            use_container_width=True,
            hide_index=True
        )

    if MOSTRAR_INVENTARIO:
        st.markdown("---")
        mostrar_inventario()

        st.markdown("---")
        mostrar_inventario_aulas()
