import html
from urllib.parse import quote

import pandas as pd
import streamlit as st

from ui.ui_gerencia import (
    ESTADOS_CERRADOS,
    es_cerrada,
    evaluar_estado_centro,
    filtrar_inventario_por_centro,
    preparar_inventario,
    preparar_ordenes,
)

EDIFICIOS = {
    "Pearson 22": {
        "Infantil / Primaria": ["Terrado", "Planta 5", "Planta 4", "Planta 3", "Planta 2", "Planta 1"],
        "Llar": ["Terrado", "Planta 2", "Planta 1", "Planta 0"],
    },
    "Pearson 9": {
        "Edificio A": ["Terrado", "Planta 2", "Planta 1", "Planta 0"],
        "Edificio B": ["Terrado", "Planta 2", "Planta 1", "Planta 0"],
        "Edificio C": ["Terrado", "Planta 2", "Planta 1", "Planta 0"],
    },
}

ALIAS_EDIFICIOS = {
    "Infantil / Primaria": ["infantil primaria", "infantil/primaria", "edif infantil primaria", "edificio infantil primaria"],
    "Llar": ["llar", "anexo", "edif llar", "edificio llar"],
    "Edificio A": ["edificio a", "edif a", "bloque a"],
    "Edificio B": ["edificio b", "edif b", "bloque b"],
    "Edificio C": ["edificio c", "edif c", "bloque c"],
}


def _norm(texto):
    return " ".join(str(texto or "").lower().replace("/", " ").replace("-", " ").split())


def _norm_planta(valor):
    texto = _norm(valor)
    if "terrado" in texto or "cubierta" in texto:
        return "terrado"
    for numero in range(10):
        if texto in {str(numero), f"p{numero}", f"p {numero}", f"planta {numero}"}:
            return f"planta {numero}"
        if f"planta {numero}" in texto or f"p {numero}" in texto:
            return f"planta {numero}"
    return texto


def _coincide_edificio(valor, edificio):
    texto = _norm(valor)
    return any(_norm(alias) in texto or texto in _norm(alias) for alias in ALIAS_EDIFICIOS.get(edificio, [edificio]))


def _filtrar_ubicacion(df, centro, edificio, planta):
    if df.empty:
        return df.copy()
    datos = df[df["centro"].fillna("").astype(str).str.strip().eq(centro)].copy()
    if datos.empty:
        return datos
    datos = datos[datos["edificio"].fillna("").astype(str).apply(lambda v: _coincide_edificio(v, edificio))].copy()
    if datos.empty:
        return datos
    objetivo = _norm_planta(planta)
    datos["_planta"] = datos["planta"].fillna("").astype(str).apply(_norm_planta)
    vacias = datos["_planta"].eq("")
    if vacias.any():
        apoyo = (
            datos.loc[vacias, "espacio"].fillna("").astype(str)
            + " "
            + datos.loc[vacias, "descripcion"].fillna("").astype(str)
        ).apply(_norm_planta)
        datos.loc[vacias, "_planta"] = apoyo
    return datos[datos["_planta"].eq(objetivo)].copy()


def _activas(datos):
    if datos.empty:
        return datos
    return datos[(datos["origen_tabla"].eq("activas")) & (~datos["estado"].isin(ESTADOS_CERRADOS))].copy()


def _urgentes(datos):
    if datos.empty:
        return datos
    texto = (
        datos["prioridad"].fillna("").astype(str)
        + " " + datos["area"].fillna("").astype(str)
        + " " + datos["descripcion"].fillna("").astype(str)
    ).str.lower()
    return datos[texto.str.contains("urgente|alta|fuga|gas|incendio|cuadro electr|legionella|acs|riesgo", na=False)].copy()


def _estado_planta(df, centro, edificio, planta):
    activas = _activas(_filtrar_ubicacion(df, centro, edificio, planta))
    urgentes = _urgentes(activas)
    cantidad = len(activas)
    if len(urgentes):
        return "critica", cantidad
    if cantidad >= 3:
        return "atencion", cantidad
    if cantidad:
        return "seguimiento", cantidad
    return "correcta", 0


def _cerradas_mes(datos):
    if datos.empty:
        return datos
    cerradas = datos[es_cerrada(datos)].copy()
    if cerradas.empty:
        return cerradas
    fecha = cerradas["fecha_cierre_dt"].where(cerradas["fecha_cierre_dt"].notna(), cerradas["fecha_dt"])
    hoy = pd.Timestamp.today()
    return cerradas[(fecha.dt.month == hoy.month) & (fecha.dt.year == hoy.year)].copy()


def _limpiar_descripcion(texto):
    texto = str(texto or "").strip()
    if texto.startswith("[CORRECTIVA DESDE INVENTARIO]"):
        texto = texto.replace("[CORRECTIVA DESDE INVENTARIO]", "", 1).strip()
    partes = [p.strip() for p in texto.splitlines() if p.strip()]
    partes = [p for p in partes if not p.lower().startswith("ot origen:")]
    return " ".join(partes) or "Actuación pendiente"


def _css():
    st.markdown("""
    <style>
    .v2-wrap{max-width:1450px;margin:0 auto}
    .v2-hero{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-radius:18px;background:linear-gradient(135deg,#0f172a,#1d4ed8);color:#fff;margin-bottom:12px}
    .v2-title{font-size:26px;font-weight:900}.v2-sub{font-size:13px;opacity:.9;margin-top:3px}.v2-alert{font-weight:800;background:rgba(255,255,255,.14);padding:8px 12px;border-radius:12px}
    .v2-centro{font-size:18px;font-weight:900;color:#0f172a;margin:10px 0 6px}
    .v2-building{background:#e2e8f0;border:1px solid #cbd5e1;border-radius:14px 14px 8px 8px;padding:7px;box-shadow:0 8px 20px rgba(15,23,42,.08)}
    .v2-roof{height:10px;background:#334155;clip-path:polygon(8% 100%,20% 0,80% 0,92% 100%);margin:0 10px}
    .v2-building-name{text-align:center;background:#1e3a8a;color:#fff;padding:7px;font-weight:900;border-radius:8px 8px 3px 3px}
    a.v2-floor{display:flex;align-items:center;justify-content:space-between;text-decoration:none;color:#0f172a;padding:7px 10px;margin-top:3px;border:1px solid rgba(15,23,42,.10);font-weight:800;min-height:38px;transition:.12s}
    a.v2-floor:hover{filter:brightness(.97);transform:translateY(-1px)}
    .v2-floor.correcta{background:#dcfce7}.v2-floor.seguimiento{background:#fef3c7}.v2-floor.atencion{background:#ffedd5}.v2-floor.critica{background:#fee2e2}
    .v2-pill{min-width:27px;height:27px;border-radius:999px;background:rgba(255,255,255,.72);display:inline-flex;align-items:center;justify-content:center;font-size:12px}
    .v2-base{height:9px;background:#475569;border-radius:0 0 5px 5px;margin-top:4px}
    .v2-legend{text-align:center;font-size:13px;color:#475569;margin:10px 0 0}
    .v2-back{display:inline-block;text-decoration:none;background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:9px 14px;border-radius:11px;font-weight:850;margin-bottom:12px}
    .v2-detail-head{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:14px 16px;margin-bottom:10px}
    .v2-detail-title{font-size:23px;font-weight:900;color:#0f172a}.v2-detail-sub{color:#64748b;font-size:13px;margin-top:3px}
    .v2-kpi{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px}.v2-kpi-l{font-size:12px;color:#64748b;font-weight:750}.v2-kpi-v{font-size:27px;font-weight:900;color:#0f172a}
    .v2-priority{background:#fff7f7;border:1px solid #fecaca;border-radius:14px;padding:14px}.v2-priority h4{color:#991b1b;margin:0 0 6px;font-size:18px}.v2-priority p{margin:4px 0;color:#334155}
    .block-container{max-width:1700px!important;padding-top:.6rem!important}
    @media(max-width:900px){.v2-hero{display:block}.v2-alert{margin-top:8px}.v2-title{font-size:22px}}
    </style>
    """, unsafe_allow_html=True)


def _href(centro, edificio, planta):
    return f"?gerencia_v2=detalle&cv_centro={quote(centro)}&cv_edificio={quote(edificio)}&cv_planta={quote(planta)}"


def _edificio_html(df, centro, edificio, plantas):
    pisos = []
    for planta in plantas:
        estado, cantidad = _estado_planta(df, centro, edificio, planta)
        nombre = "T" if planta == "Terrado" else planta.replace("Planta ", "P")
        indicador = "✓" if cantidad == 0 else str(cantidad)
        pisos.append(
            f'<a class="v2-floor {estado}" href="{_href(centro, edificio, planta)}">'
            f'<span>{html.escape(nombre)}</span><span class="v2-pill">{indicador}</span></a>'
        )
    return (
        '<div class="v2-building"><div class="v2-roof"></div>'
        f'<div class="v2-building-name">{html.escape(edificio)}</div>'
        + "".join(pisos)
        + '<div class="v2-base"></div></div>'
    )


def _estado_global(df):
    peor = 0
    texto = "El colegio está bajo control"
    for centro, edificios in EDIFICIOS.items():
        for edificio, plantas in edificios.items():
            for planta in plantas:
                estado, _ = _estado_planta(df, centro, edificio, planta)
                nivel = {"correcta": 0, "seguimiento": 1, "atencion": 2, "critica": 3}[estado]
                peor = max(peor, nivel)
    if peor == 3:
        texto = "Hay una zona que requiere atención prioritaria"
    elif peor:
        texto = "El colegio requiere seguimiento"
    return texto


def _mostrar_mapa(df):
    st.markdown(
        f'<div class="v2-hero"><div><div class="v2-title">🏫 Colegio vivo</div>'
        f'<div class="v2-sub">Pearson 22 y Pearson 9</div></div>'
        f'<div class="v2-alert">{html.escape(_estado_global(df))}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="v2-centro">Pearson 22</div>', unsafe_allow_html=True)
    p22a, p22b = st.columns([1.25, .85], gap="medium")
    with p22a:
        st.markdown(_edificio_html(df, "Pearson 22", "Infantil / Primaria", EDIFICIOS["Pearson 22"]["Infantil / Primaria"]), unsafe_allow_html=True)
    with p22b:
        st.markdown(_edificio_html(df, "Pearson 22", "Llar", EDIFICIOS["Pearson 22"]["Llar"]), unsafe_allow_html=True)

    st.markdown('<div class="v2-centro">Pearson 9</div>', unsafe_allow_html=True)
    cols = st.columns(3, gap="medium")
    for col, edificio in zip(cols, ["Edificio A", "Edificio B", "Edificio C"]):
        with col:
            st.markdown(_edificio_html(df, "Pearson 9", edificio, EDIFICIOS["Pearson 9"][edificio]), unsafe_allow_html=True)

    st.markdown('<div class="v2-legend">🟢 Correcto &nbsp;&nbsp; 🟡 Seguimiento &nbsp;&nbsp; 🟠 Atención &nbsp;&nbsp; 🔴 Prioridad</div>', unsafe_allow_html=True)


def _mostrar_detalle(df, centro, edificio, planta):
    datos = _filtrar_ubicacion(df, centro, edificio, planta)
    activas = _activas(datos)
    urgentes = _urgentes(activas)
    en_curso = activas[activas["estado"].isin(["En curso", "En ejecución"])] if not activas.empty else activas
    cerradas_mes = _cerradas_mes(datos)

    st.markdown('<a class="v2-back" href="?gerencia_v2=mapa">← Volver al colegio</a>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="v2-detail-head"><div class="v2-detail-title">📍 {html.escape(centro)} · {html.escape(edificio)} · {html.escape(planta)}</div>'
        '<div class="v2-detail-sub">Situación operativa de la planta</div></div>', unsafe_allow_html=True)

    cols = st.columns(4)
    for col, label, value in zip(cols, ["Pendientes", "Urgentes / altas", "En curso", "Finalizadas mes"], [len(activas), len(urgentes), len(en_curso), len(cerradas_mes)]):
        with col:
            st.markdown(f'<div class="v2-kpi"><div class="v2-kpi-l">{label}</div><div class="v2-kpi-v">{value}</div></div>', unsafe_allow_html=True)

    a, b = st.columns([1, 1.1], gap="large")
    with a:
        st.markdown("### Por áreas")
        if activas.empty:
            st.success("Sin incidencias activas.")
        else:
            areas = activas["area"].fillna("Sin área").replace("", "Sin área").value_counts()
            st.bar_chart(areas, horizontal=True, height=230)
    with b:
        st.markdown("### Actuación prioritaria")
        if activas.empty:
            st.success("No hay actuaciones pendientes.")
        else:
            candidatos = urgentes if not urgentes.empty else activas
            fila = candidatos.sort_values("fecha_dt", ascending=True, na_position="last").iloc[0]
            descripcion = _limpiar_descripcion(fila.get("descripcion", ""))
            st.markdown(
                f'<div class="v2-priority"><h4>{html.escape(descripcion)}</h4>'
                f'<p>📍 {html.escape(str(fila.get("espacio", "") or planta))}</p>'
                f'<p>{html.escape(str(fila.get("prioridad", "") or "Sin prioridad"))} · {html.escape(str(fila.get("estado", "") or ""))}</p>'
                f'<p>{html.escape(str(fila.get("numero_ot", "") or ""))}</p></div>',
                unsafe_allow_html=True,
            )

    with st.expander(f"Ver {len(activas)} incidencias de esta planta", expanded=False):
        if activas.empty:
            st.info("No hay incidencias activas.")
        else:
            vista = activas.sort_values("fecha_dt", ascending=True, na_position="last").copy()
            vista["descripcion"] = vista["descripcion"].apply(_limpiar_descripcion)
            columnas = ["numero_ot", "descripcion", "area", "prioridad", "estado", "operario"]
            columnas = [c for c in columnas if c in vista.columns]
            st.dataframe(vista[columnas], use_container_width=True, hide_index=True)

    with st.expander("Indicadores del centro", expanded=False):
        _, porcentaje, mensaje = evaluar_estado_centro(df, centro)
        inventario = preparar_inventario()
        inv = filtrar_inventario_por_centro(inventario, centro)
        stock_bajo = 0
        if not inv.empty and "stock_minimo" in inv.columns:
            minimo = pd.to_numeric(inv["stock_minimo"], errors="coerce").fillna(0)
            stock_bajo = int((inv["stock_num"] <= minimo).sum())
        c1, c2 = st.columns(2)
        c1.metric("Estado del centro", f"{porcentaje}%")
        c2.metric("Alertas de stock", stock_bajo)
        st.caption(mensaje)


def pantalla_gerencia():
    _css()
    df = preparar_ordenes()
    if df.empty:
        df = pd.DataFrame(columns=[
            "numero_ot", "fecha_creacion", "fecha_cierre", "centro", "edificio", "planta",
            "espacio", "descripcion", "estado", "operario", "solicitante", "origen", "area",
            "prioridad", "origen_tabla", "fecha_dt", "fecha_cierre_dt"
        ])

    params = st.query_params
    vista = params.get("gerencia_v2", "mapa")
    centro = params.get("cv_centro", "")
    edificio = params.get("cv_edificio", "")
    planta = params.get("cv_planta", "")

    if vista == "detalle" and centro and edificio and planta:
        _mostrar_detalle(df, centro, edificio, planta)
    else:
        _mostrar_mapa(df)
