import html
from urllib.parse import urlencode

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
    if not texto:
        return False
    return any(
        _norm(alias) in texto or texto in _norm(alias)
        for alias in ALIAS_EDIFICIOS.get(edificio, [edificio])
    )


def _filtrar_ubicacion(df, centro, edificio, planta):
    if df.empty:
        return df.copy()

    datos = df[df["centro"].fillna("").astype(str).str.strip().eq(centro)].copy()
    if datos.empty:
        return datos

    datos = datos[
        datos["edificio"].fillna("").astype(str).apply(
            lambda valor: _coincide_edificio(valor, edificio)
        )
    ].copy()
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
    return datos[
        datos["origen_tabla"].eq("activas")
        & (~datos["estado"].isin(ESTADOS_CERRADOS))
    ].copy()


def _urgentes(datos):
    if datos.empty:
        return datos
    texto = (
        datos["prioridad"].fillna("").astype(str)
        + " "
        + datos["area"].fillna("").astype(str)
        + " "
        + datos["descripcion"].fillna("").astype(str)
    ).str.lower()
    return datos[
        texto.str.contains(
            "urgente|alta|fuga|gas|incendio|cuadro electr|legionella|acs|riesgo",
            na=False,
        )
    ].copy()


def _estado_planta(df, centro, edificio, planta):
    activas = _activas(_filtrar_ubicacion(df, centro, edificio, planta))
    cantidad = len(activas)
    if len(_urgentes(activas)):
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
    fecha = cerradas["fecha_cierre_dt"].where(
        cerradas["fecha_cierre_dt"].notna(), cerradas["fecha_dt"]
    )
    hoy = pd.Timestamp.today()
    return cerradas[(fecha.dt.month == hoy.month) & (fecha.dt.year == hoy.year)].copy()


def _limpiar_descripcion(texto):
    texto = str(texto or "").strip()
    texto = texto.replace("[CORRECTIVA DESDE INVENTARIO]", "").strip()
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    lineas = [linea for linea in lineas if not linea.lower().startswith("ot origen:")]
    return " ".join(lineas) or "Actuación pendiente"


def _query_detalle(centro, edificio, planta):
    return "?" + urlencode(
        {
            "gerencia_v3": "detalle",
            "cv_centro": centro,
            "cv_edificio": edificio,
            "cv_planta": planta,
        }
    )


def _css():
    st.markdown(
        """
        <style>
        .block-container{max-width:1680px!important;padding-top:.5rem!important;padding-bottom:.5rem!important}
        .rv-wrap{max-width:1500px;margin:0 auto}
        .rv-hero{display:flex;align-items:center;justify-content:space-between;gap:16px;background:linear-gradient(135deg,#07182f,#123b78);color:#fff;border-radius:18px;padding:13px 18px;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.16)}
        .rv-title{font-size:25px;font-weight:950;letter-spacing:-.3px}.rv-sub{font-size:13px;opacity:.86;margin-top:2px}.rv-alert{font-size:13px;font-weight:850;background:rgba(255,255,255,.12);border-radius:999px;padding:8px 13px}
        .rv-campus{font-size:18px;font-weight:950;color:#0f172a;text-align:center;margin:2px 0 8px;text-transform:uppercase;letter-spacing:.5px}
        .rv-buildings{display:flex;align-items:flex-end;justify-content:center;gap:34px;width:100%;margin:0 auto 12px}
        .rv-building{width:178px;flex:0 0 178px;filter:drop-shadow(0 9px 8px rgba(15,23,42,.11))}
        .rv-building.tall{width:205px;flex-basis:205px}
        .rv-roof{height:58px;position:relative;margin:0 10px -1px;background:#172b47;clip-path:polygon(50% 0,100% 78%,100% 100%,0 100%,0 78%)}
        .rv-roof:after{content:"";position:absolute;left:50%;top:18px;transform:translateX(-50%);width:19px;height:19px;border:3px solid #f4e6bd;border-radius:50%;background:#27496f}
        .rv-name{background:linear-gradient(180deg,#173a6e,#0e284d);color:#fff;text-align:center;font-size:13px;font-weight:950;padding:9px 5px;border-left:7px solid #d9caa7;border-right:7px solid #d9caa7;border-top:5px solid #e8dab5;border-bottom:5px solid #caba93}
        .rv-body{border-left:9px solid #ded1ad;border-right:9px solid #ded1ad;background:#efe7d2}
        a.rv-floor{display:grid;grid-template-columns:1fr 34px;align-items:center;min-height:52px;padding:0 8px 0 12px;text-decoration:none;color:#102033;font-size:13px;font-weight:900;border-bottom:2px solid rgba(80,70,50,.24);box-shadow:inset 0 0 0 1px rgba(255,255,255,.32);transition:transform .12s,filter .12s}
        a.rv-floor:hover{transform:scale(1.018);filter:saturate(1.08) brightness(.98);z-index:2;position:relative}
        .rv-floor.correcta{background:linear-gradient(90deg,#d9f7c9,#bfeaa7)}
        .rv-floor.seguimiento{background:linear-gradient(90deg,#fff1ad,#ffd763)}
        .rv-floor.atencion{background:linear-gradient(90deg,#ffd2aa,#ff9b54)}
        .rv-floor.critica{background:linear-gradient(90deg,#ffc2c2,#ff7f7f)}
        .rv-badge{width:29px;height:29px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.82);font-size:12px;font-weight:950;box-shadow:0 2px 6px rgba(15,23,42,.12)}
        .rv-ground{height:54px;position:relative;background:linear-gradient(#d4c29b,#bd9f72);border:9px solid #ded1ad;border-top:5px solid #b89e72}
        .rv-door{position:absolute;left:50%;bottom:0;transform:translateX(-50%);width:32px;height:42px;background:linear-gradient(90deg,#16345b 48%,#0c2442 50%);border:4px solid #10233c;border-bottom:0;border-radius:4px 4px 0 0}
        .rv-base{height:12px;background:#354154;border-radius:0 0 4px 4px;border-bottom:4px solid #1f2937}
        .rv-legend{display:flex;justify-content:center;gap:26px;align-items:center;color:#475569;font-size:13px;margin:8px 0 4px}.rv-dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px}
        .rv-separator{height:1px;background:#e2e8f0;margin:8px 0 10px}
        .rv-back{display:inline-block;text-decoration:none!important;color:#1d4ed8!important;background:#eff6ff;border:1px solid #bfdbfe;border-radius:11px;padding:9px 14px;font-weight:900;margin:0 0 10px}
        .rv-detail{border:1px solid #e2e8f0;border-radius:17px;background:#fff;padding:15px 17px}.rv-detail-title{font-size:23px;font-weight:950;color:#0f172a}.rv-detail-sub{font-size:13px;color:#64748b;margin-top:3px}
        .rv-kpi{border:1px solid #e2e8f0;border-radius:13px;background:#f8fafc;padding:11px}.rv-kpi-label{font-size:12px;color:#64748b;font-weight:750}.rv-kpi-value{font-size:28px;font-weight:950;color:#0f172a}
        .rv-priority{border:1px solid #fecaca;background:#fff7f7;border-radius:14px;padding:14px}.rv-priority-title{font-size:18px;font-weight:950;color:#991b1b}.rv-priority-meta{font-size:13px;color:#475569;margin-top:6px;line-height:1.65}
        @media(max-width:1100px){.rv-buildings{gap:18px}.rv-building{width:150px;flex-basis:150px}.rv-building.tall{width:170px;flex-basis:170px}}
        @media(max-width:760px){.rv-buildings{overflow-x:auto;justify-content:flex-start;padding-bottom:8px}.rv-hero{display:block}.rv-alert{display:inline-block;margin-top:8px}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _building_html(df, centro, edificio, plantas, tall=False):
    pisos = []
    for planta in plantas:
        estado, cantidad = _estado_planta(df, centro, edificio, planta)
        etiqueta = "TERRADO" if planta == "Terrado" else planta.replace("Planta ", "P")
        badge = "✓" if cantidad == 0 else str(cantidad)
        pisos.append(
            f'<a target="_self" class="rv-floor {estado}" href="{html.escape(_query_detalle(centro, edificio, planta), quote=True)}">'
            f'<span>{html.escape(etiqueta)}</span><span class="rv-badge">{badge}</span></a>'
        )

    clase = "rv-building tall" if tall else "rv-building"
    return (
        f'<div class="{clase}">'
        '<div class="rv-roof"></div>'
        f'<div class="rv-name">{html.escape(edificio.upper())}</div>'
        '<div class="rv-body">'
        + "".join(pisos)
        + '</div><div class="rv-ground"><div class="rv-door"></div></div><div class="rv-base"></div></div>'
    )


def _estado_global(df):
    peor = 0
    for centro, edificios in EDIFICIOS.items():
        for edificio, plantas in edificios.items():
            for planta in plantas:
                estado, _ = _estado_planta(df, centro, edificio, planta)
                peor = max(peor, {"correcta": 0, "seguimiento": 1, "atencion": 2, "critica": 3}[estado])
    if peor == 3:
        return "🔴 Hay una zona que requiere atención"
    if peor:
        return "🟡 El colegio requiere seguimiento"
    return "🟢 El colegio está bajo control"


def _mostrar_mapa(df):
    st.markdown(
        f'<div class="rv-hero"><div><div class="rv-title">🏢 COLEGIO VIVO</div>'
        '<div class="rv-sub">Estado real del colegio</div></div>'
        f'<div class="rv-alert">{html.escape(_estado_global(df))}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="rv-campus">Pearson 22</div>', unsafe_allow_html=True)
    p22 = (
        '<div class="rv-buildings">'
        + _building_html(df, "Pearson 22", "Infantil / Primaria", EDIFICIOS["Pearson 22"]["Infantil / Primaria"], tall=True)
        + _building_html(df, "Pearson 22", "Llar", EDIFICIOS["Pearson 22"]["Llar"])
        + '</div>'
    )
    st.markdown(p22, unsafe_allow_html=True)

    st.markdown('<div class="rv-separator"></div><div class="rv-campus">Pearson 9</div>', unsafe_allow_html=True)
    p9 = '<div class="rv-buildings">' + ''.join(
        _building_html(df, "Pearson 9", edificio, EDIFICIOS["Pearson 9"][edificio])
        for edificio in ["Edificio A", "Edificio B", "Edificio C"]
    ) + '</div>'
    st.markdown(p9, unsafe_allow_html=True)

    st.markdown(
        '<div class="rv-legend">'
        '<span><i class="rv-dot" style="background:#55c947"></i>Correcto</span>'
        '<span><i class="rv-dot" style="background:#f4c542"></i>Seguimiento</span>'
        '<span><i class="rv-dot" style="background:#f58a3b"></i>Atención</span>'
        '<span><i class="rv-dot" style="background:#e63946"></i>Prioridad</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _mostrar_detalle(df, centro, edificio, planta):
    datos = _filtrar_ubicacion(df, centro, edificio, planta)
    activas = _activas(datos)
    urgentes = _urgentes(activas)
    en_curso = activas[activas["estado"].isin(["En curso", "En ejecución"])] if not activas.empty else activas
    cerradas_mes = _cerradas_mes(datos)

    st.markdown('<a target="_self" class="rv-back" href="?gerencia_v3=mapa">← Volver al colegio</a>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="rv-detail"><div class="rv-detail-title">📍 {html.escape(centro)} · {html.escape(edificio)} · {html.escape(planta)}</div>'
        '<div class="rv-detail-sub">Situación operativa de la planta</div></div>',
        unsafe_allow_html=True,
    )

    columnas = st.columns(4)
    for columna, etiqueta, valor in zip(
        columnas,
        ["Pendientes", "Urgentes / altas", "En curso", "Finalizadas mes"],
        [len(activas), len(urgentes), len(en_curso), len(cerradas_mes)],
    ):
        with columna:
            st.markdown(
                f'<div class="rv-kpi"><div class="rv-kpi-label">{etiqueta}</div><div class="rv-kpi-value">{valor}</div></div>',
                unsafe_allow_html=True,
            )

    izquierda, derecha = st.columns([1, 1.15], gap="large")
    with izquierda:
        st.markdown("### Por áreas")
        if activas.empty:
            st.success("Sin incidencias activas.")
        else:
            areas = activas["area"].fillna("Sin área").replace("", "Sin área").value_counts()
            st.bar_chart(areas, horizontal=True, height=220)

    with derecha:
        st.markdown("### Actuación prioritaria")
        if activas.empty:
            st.success("No hay actuaciones pendientes.")
        else:
            candidatos = urgentes if not urgentes.empty else activas
            fila = candidatos.sort_values("fecha_dt", ascending=True, na_position="last").iloc[0]
            st.markdown(
                f'<div class="rv-priority"><div class="rv-priority-title">{html.escape(_limpiar_descripcion(fila.get("descripcion", "")))}</div>'
                f'<div class="rv-priority-meta">📍 {html.escape(str(fila.get("espacio", "") or planta))}<br>'
                f'{html.escape(str(fila.get("prioridad", "") or "Sin prioridad"))} · {html.escape(str(fila.get("estado", "") or ""))}<br>'
                f'{html.escape(str(fila.get("numero_ot", "") or ""))}</div></div>',
                unsafe_allow_html=True,
            )

    with st.expander(f"Ver {len(activas)} incidencias de esta planta", expanded=False):
        if activas.empty:
            st.info("No hay incidencias activas.")
        else:
            vista = activas.sort_values("fecha_dt", ascending=True, na_position="last").copy()
            vista["descripcion"] = vista["descripcion"].apply(_limpiar_descripcion)
            columnas_vista = ["numero_ot", "descripcion", "area", "prioridad", "estado", "operario"]
            columnas_vista = [columna for columna in columnas_vista if columna in vista.columns]
            st.dataframe(vista[columnas_vista], use_container_width=True, hide_index=True)

    with st.expander("Indicadores del centro", expanded=False):
        _, porcentaje, mensaje = evaluar_estado_centro(df, centro)
        inventario = preparar_inventario()
        inventario_centro = filtrar_inventario_por_centro(inventario, centro)
        stock_bajo = 0
        if not inventario_centro.empty and "stock_minimo" in inventario_centro.columns:
            minimo = pd.to_numeric(inventario_centro["stock_minimo"], errors="coerce").fillna(0)
            stock_bajo = int((inventario_centro["stock_num"] <= minimo).sum())
        c1, c2 = st.columns(2)
        c1.metric("Estado del centro", f"{porcentaje}%")
        c2.metric("Alertas de stock", stock_bajo)
        st.caption(mensaje)


def pantalla_gerencia():
    _css()
    df = preparar_ordenes()
    if df.empty:
        df = pd.DataFrame(
            columns=[
                "numero_ot", "fecha_creacion", "fecha_cierre", "centro", "edificio", "planta",
                "espacio", "descripcion", "estado", "operario", "solicitante", "origen", "area",
                "prioridad", "origen_tabla", "fecha_dt", "fecha_cierre_dt",
            ]
        )

    params = st.query_params
    vista = params.get("gerencia_v3", "mapa")
    centro = params.get("cv_centro", "")
    edificio = params.get("cv_edificio", "")
    planta = params.get("cv_planta", "")

    if vista == "detalle" and centro and edificio and planta:
        _mostrar_detalle(df, centro, edificio, planta)
    else:
        _mostrar_mapa(df)
