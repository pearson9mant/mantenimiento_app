import html
import unicodedata
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
    texto = str(texto or "").lower().strip()
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    for caracter in ["/", "-", "_", ".", ",", ";", ":"]:
        texto = texto.replace(caracter, " ")
    return " ".join(texto.split())


ALIAS_CENTROS = {
    "Pearson 22": ["pearson 22", "pearson22", "p22", "pearson nº 22", "pearson numero 22"],
    "Pearson 9": ["pearson 9", "pearson9", "p9", "pearson nº 9", "pearson numero 9"],
}


def _coincide_centro(valor, centro):
    texto = _norm(valor)
    if not texto:
        return False

    alias = ALIAS_CENTROS.get(centro, [centro])
    return any(
        _norm(nombre) == texto
        or _norm(nombre) in texto
        or texto in _norm(nombre)
        for nombre in alias
    )


def _norm_planta(valor):
    texto = _norm(valor)

    if not texto:
        return ""

    if any(palabra in texto for palabra in ["terrado", "cubierta", "azotea", "tejado"]):
        return "terrado"

    equivalencias = {
        "baja": 0,
        "pb": 0,
        "principal": 0,
        "cero": 0,
        "primera": 1,
        "primero": 1,
        "segunda": 2,
        "segundo": 2,
        "tercera": 3,
        "tercero": 3,
        "cuarta": 4,
        "cuarto": 4,
        "quinta": 5,
        "quinto": 5,
    }

    palabras = texto.split()

    for numero in range(10):
        patrones = {
            str(numero),
            f"p{numero}",
            f"p {numero}",
            f"planta {numero}",
            f"piso {numero}",
            f"nivel {numero}",
        }

        if texto in patrones:
            return f"planta {numero}"

        if any(patron in texto for patron in patrones if len(patron) > 1):
            return f"planta {numero}"

    for palabra, numero in equivalencias.items():
        if palabra in palabras or f"planta {palabra}" in texto:
            return f"planta {numero}"

    return ""


def _coincide_edificio(valor, edificio):
    texto = _norm(valor)

    if not texto:
        return False

    alias_ampliados = {
        "Infantil / Primaria": [
            "infantil primaria",
            "infantil",
            "primaria",
            "edificio infantil",
            "edificio primaria",
            "edif infantil",
            "edif primaria",
            "principal",
        ],
        "Llar": [
            "llar",
            "llar infants",
            "llar d infants",
            "guarderia",
            "anexo",
            "edificio llar",
            "edif llar",
        ],
        "Edificio A": [
            "edificio a",
            "edif a",
            "bloque a",
            "pabellon a",
            "modulo a",
        ],
        "Edificio B": [
            "edificio b",
            "edif b",
            "bloque b",
            "pabellon b",
            "modulo b",
        ],
        "Edificio C": [
            "edificio c",
            "edif c",
            "bloque c",
            "pabellon c",
            "modulo c",
        ],
    }

    alias = alias_ampliados.get(
        edificio,
        ALIAS_EDIFICIOS.get(edificio, [edificio]),
    )

    return any(
        _norm(nombre) == texto
        or _norm(nombre) in texto
        or texto in _norm(nombre)
        for nombre in alias
    )


def _texto_ubicacion_fila(fila):
    campos = [
        "centro",
        "edificio",
        "planta",
        "espacio",
        "descripcion",
        "solicitante",
        "observaciones",
    ]

    return " ".join(
        str(fila.get(campo, "") or "")
        for campo in campos
        if campo in fila.index
    )


def _inferir_edificio_fila(fila, centro, edificio):
    texto = _norm(_texto_ubicacion_fila(fila))

    if _coincide_edificio(texto, edificio):
        return True

    edificio_guardado = _norm(fila.get("edificio", ""))

    # Compatibilidad con órdenes antiguas de Pearson 22:
    # si no indican edificio y no contienen Llar, pertenecen al edificio principal.
    if centro == "Pearson 22" and not edificio_guardado:
        contiene_llar = any(
            palabra in texto
            for palabra in ["llar", "guarderia", "anexo"]
        )

        if edificio == "Llar":
            return contiene_llar

        if edificio == "Infantil / Primaria":
            return not contiene_llar

    return False


def _inferir_planta_fila(fila):
    planta_directa = _norm_planta(fila.get("planta", ""))

    if planta_directa:
        return planta_directa

    texto_apoyo = " ".join(
        str(fila.get(campo, "") or "")
        for campo in ["edificio", "espacio", "descripcion", "observaciones"]
        if campo in fila.index
    )

    return _norm_planta(texto_apoyo)


def _filtrar_ubicacion(df, centro, edificio, planta):
    if df.empty:
        return df.copy()

    datos = df.copy()

    # Centro tolerante: Pearson 22, Pearson22, P22, etc.
    datos = datos[
        datos["centro"]
        .fillna("")
        .astype(str)
        .apply(lambda valor: _coincide_centro(valor, centro))
    ].copy()

    if datos.empty:
        return datos

    # Edificio: consulta tanto el campo edificio como espacio y descripción.
    datos = datos[
        datos.apply(
            lambda fila: _inferir_edificio_fila(fila, centro, edificio),
            axis=1,
        )
    ].copy()

    if datos.empty:
        return datos

    objetivo = _norm_planta(planta)
    datos["_planta"] = datos.apply(_inferir_planta_fila, axis=1)

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



def _activas_centro_totales(df, centro):
    """Todas las órdenes activas del centro, sin exigir edificio ni planta."""
    if df.empty:
        return df.copy()

    datos = df[
        df["centro"]
        .fillna("")
        .astype(str)
        .apply(lambda valor: _coincide_centro(valor, centro))
    ].copy()

    return _activas(datos)


def _clave_fila_orden(fila):
    numero_ot = str(fila.get("numero_ot", "") or "").strip()
    if numero_ot:
        return f"ot::{numero_ot}"

    identificador = str(fila.get("id", "") or "").strip()
    if identificador:
        return f"id::{identificador}"

    return "fila::" + "||".join(
        str(fila.get(campo, "") or "").strip()
        for campo in [
            "fecha_creacion",
            "centro",
            "edificio",
            "planta",
            "espacio",
            "descripcion",
        ]
    )


def _indices_ubicados_centro(df, centro):
    """Claves de órdenes que ya han sido colocadas en alguna planta del plano."""
    claves = set()

    for edificio, plantas in EDIFICIOS[centro].items():
        for planta in plantas:
            datos = _activas(_filtrar_ubicacion(df, centro, edificio, planta))
            for _, fila in datos.iterrows():
                claves.add(_clave_fila_orden(fila))

    return claves


def _incidencias_sin_ubicar(df, centro):
    """Órdenes activas del centro que no coinciden con ninguna planta del dibujo."""
    todas = _activas_centro_totales(df, centro)

    if todas.empty:
        return todas

    ubicadas = _indices_ubicados_centro(df, centro)

    mascara = todas.apply(
        lambda fila: _clave_fila_orden(fila) not in ubicadas,
        axis=1,
    )

    return todas[mascara].copy()


def _planta_respaldo(centro, edificio):
    """
    Planta donde se muestran temporalmente incidencias antiguas sin planta.
    Evita que desaparezcan del cuadro, pero se identifican como 'sin ubicar'.
    """
    if centro == "Pearson 22":
        if edificio == "Llar":
            return "Planta 0"
        return "Planta 1"

    return "Planta 0"


def _sin_ubicar_asignadas_a_edificio(df, centro, edificio, planta):
    """
    Reparte únicamente órdenes sin ubicar:
    - respeta edificio cuando puede inferirse;
    - las que tampoco tienen edificio van al edificio principal del centro;
    - solo se añaden en la planta de respaldo.
    """
    if planta != _planta_respaldo(centro, edificio):
        return pd.DataFrame(columns=df.columns)

    sin_ubicar = _incidencias_sin_ubicar(df, centro)

    if sin_ubicar.empty:
        return sin_ubicar

    def pertenece(fila):
        texto = _norm(_texto_ubicacion_fila(fila))
        edificio_guardado = _norm(fila.get("edificio", ""))

        if _coincide_edificio(texto, edificio):
            return True

        if centro == "Pearson 22":
            contiene_llar = any(
                palabra in texto
                for palabra in ["llar", "guarderia", "anexo"]
            )

            if edificio == "Llar":
                return contiene_llar

            if edificio == "Infantil / Primaria":
                return not contiene_llar

        if centro == "Pearson 9" and not edificio_guardado:
            # Las antiguas sin bloque se muestran provisionalmente en Edificio A.
            return edificio == "Edificio A"

        return False

    return sin_ubicar[
        sin_ubicar.apply(pertenece, axis=1)
    ].copy()


def _datos_planta_completos(df, centro, edificio, planta):
    """
    Datos colocados normalmente + incidencias antiguas sin ubicación exacta.
    Se eliminan duplicados por OT para no inflar los contadores.
    """
    normales = _filtrar_ubicacion(df, centro, edificio, planta)
    respaldo = _sin_ubicar_asignadas_a_edificio(
        df, centro, edificio, planta
    )

    if normales.empty and respaldo.empty:
        return normales.copy()

    datos = pd.concat([normales, respaldo], ignore_index=True)

    datos["_clave_orden"] = datos.apply(_clave_fila_orden, axis=1)
    datos = datos.drop_duplicates("_clave_orden", keep="first")

    return datos.drop(columns=["_clave_orden"], errors="ignore")


def _pendiente_material(datos):
    if datos.empty:
        return datos

    estados_material = {
        "pendiente material",
        "esperando material",
        "pendiente proveedor",
        "pendiente presupuesto",
    }

    estado_normalizado = (
        datos["estado"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return datos[estado_normalizado.isin(estados_material)].copy()

def _estado_planta(df, centro, edificio, planta):
    activas = _activas(_datos_planta_completos(df, centro, edificio, planta))
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

    # Algunas órdenes antiguas guardan las fechas como texto.
    # Convertimos siempre antes de usar el accesor .dt.
    fecha_cierre = pd.to_datetime(
        cerradas.get("fecha_cierre_dt"),
        errors="coerce",
        dayfirst=True,
    )

    fecha_creacion = pd.to_datetime(
        cerradas.get("fecha_dt"),
        errors="coerce",
        dayfirst=True,
    )

    fecha = fecha_cierre.where(
        fecha_cierre.notna(),
        fecha_creacion,
    )

    hoy = pd.Timestamp.today()

    mascara = (
        fecha.notna()
        & fecha.dt.month.eq(hoy.month)
        & fecha.dt.year.eq(hoy.year)
    )

    return cerradas[mascara].copy()


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


def _abrir_detalle(centro, edificio, planta):
    st.session_state["gerencia_v3_vista"] = "detalle"
    st.session_state["gerencia_v3_centro"] = centro
    st.session_state["gerencia_v3_edificio"] = edificio
    st.session_state["gerencia_v3_planta"] = planta


def _volver_mapa():
    st.session_state["gerencia_v3_vista"] = "mapa"
    st.session_state.pop("gerencia_v3_centro", None)
    st.session_state.pop("gerencia_v3_edificio", None)
    st.session_state.pop("gerencia_v3_planta", None)


def _clave_segura(*partes):
    texto = "_".join(_norm(p) for p in partes)
    return "".join(c if c.isalnum() else "_" for c in texto)


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
        .rv-exec-state{display:flex;align-items:center;justify-content:space-between;gap:16px;border-radius:16px;padding:14px 17px;margin:12px 0 14px;border:1px solid #dbe3ef;background:#f8fafc}
        .rv-exec-state.good{background:#f0fdf4;border-color:#bbf7d0}
        .rv-exec-state.watch{background:#fffbeb;border-color:#fde68a}
        .rv-exec-state.alert{background:#fff7ed;border-color:#fed7aa}
        .rv-exec-state.critical{background:#fef2f2;border-color:#fecaca}
        .rv-exec-label{font-size:12px;font-weight:850;color:#64748b;text-transform:uppercase;letter-spacing:.45px}
        .rv-exec-value{font-size:22px;font-weight:950;color:#0f172a;margin-top:2px}
        .rv-exec-note{font-size:13px;color:#475569;font-weight:650;text-align:right}
        .rv-summary{border:1px solid #dbe3ef;background:#fff;border-radius:15px;padding:14px 16px;min-height:220px}
        .rv-summary-title{font-size:17px;font-weight:950;color:#0f172a;margin-bottom:11px}
        .rv-summary-grid{display:grid;grid-template-columns:145px 1fr;gap:9px 12px;font-size:14px}
        .rv-summary-key{color:#64748b;font-weight:750}.rv-summary-value{color:#0f172a;font-weight:900}
        .rv-area-row{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #eef2f7;padding:10px 2px}
        .rv-area-row:last-child{border-bottom:0}.rv-area-name{font-size:14px;font-weight:850;color:#334155}
        .rv-area-count{min-width:30px;height:30px;border-radius:999px;background:#eff6ff;color:#1d4ed8;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:950}
        .rv-trend{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:7px 11px;font-size:13px;font-weight:900;margin-top:10px}
        .rv-trend.good{background:#dcfce7;color:#166534}.rv-trend.bad{background:#fee2e2;color:#991b1b}.rv-trend.flat{background:#e2e8f0;color:#334155}
        .rv-exec-list{margin:0;padding:0;list-style:none}.rv-exec-list li{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:9px 0;border-bottom:1px solid #eef2f7;font-size:14px}.rv-exec-list li:last-child{border-bottom:0}.rv-exec-list span{color:#475569;font-weight:750}.rv-exec-list strong{color:#0f172a;font-weight:950;text-align:right}
        @media(max-width:1100px){.rv-buildings{gap:18px}.rv-building{width:150px;flex-basis:150px}.rv-building.tall{width:170px;flex-basis:170px}}
        @media(max-width:760px){.rv-buildings{overflow-x:auto;justify-content:flex-start;padding-bottom:8px}.rv-hero{display:block}.rv-alert{display:inline-block;margin-top:8px}}
        
        div[data-testid="stButton"] > button{
            min-height:48px!important;
            border-radius:0!important;
            border:1px solid rgba(80,70,50,.25)!important;
            font-weight:900!important;
            text-align:left!important;
            justify-content:flex-start!important;
            background:#f8fafc!important;
            color:#102033!important;
            box-shadow:inset 0 0 0 1px rgba(255,255,255,.4)!important;
        }
        div[data-testid="stButton"] > button:hover{
            border-color:#2563eb!important;
            transform:translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_building_native(df, centro, edificio, plantas, tall=False):
    clase = "rv-building tall" if tall else "rv-building"
    st.markdown(
        f'<div class="{clase}" style="width:100%;filter:none">'
        '<div class="rv-roof"></div>'
        f'<div class="rv-name">{html.escape(edificio.upper())}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    for planta in plantas:
        estado, cantidad = _estado_planta(df, centro, edificio, planta)
        etiqueta = "TERRADO" if planta == "Terrado" else planta.replace("Planta ", "P")
        badge = "✓" if cantidad == 0 else str(cantidad)
        icono = {
            "correcta": "🟢",
            "seguimiento": "🟡",
            "atencion": "🟠",
            "critica": "🔴",
        }[estado]

        clave = _clave_segura("rv", centro, edificio, planta)
        st.button(
            f"{icono}  {etiqueta}                         {badge}",
            key=clave,
            use_container_width=True,
            on_click=_abrir_detalle,
            args=(centro, edificio, planta),
        )

    st.markdown(
        '<div class="rv-ground"><div class="rv-door"></div></div><div class="rv-base"></div>',
        unsafe_allow_html=True,
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
    margen_1, col_inf, col_llar, margen_2 = st.columns([1.5, 1.15, 1, 1.5], gap="large")
    with col_inf:
        _render_building_native(
            df, "Pearson 22", "Infantil / Primaria",
            EDIFICIOS["Pearson 22"]["Infantil / Primaria"], tall=True,
        )
    with col_llar:
        _render_building_native(df, "Pearson 22", "Llar", EDIFICIOS["Pearson 22"]["Llar"])

    st.markdown('<div class="rv-separator"></div><div class="rv-campus">Pearson 9</div>', unsafe_allow_html=True)
    margen_3, col_a, col_b, col_c, margen_4 = st.columns([1, 1, 1, 1, 1], gap="large")
    with col_a:
        _render_building_native(df, "Pearson 9", "Edificio A", EDIFICIOS["Pearson 9"]["Edificio A"])
    with col_b:
        _render_building_native(df, "Pearson 9", "Edificio B", EDIFICIOS["Pearson 9"]["Edificio B"])
    with col_c:
        _render_building_native(df, "Pearson 9", "Edificio C", EDIFICIOS["Pearson 9"]["Edificio C"])

    total_activo = 0
    total_ubicado = 0
    total_sin_ubicar = 0

    for centro in EDIFICIOS:
        activas_centro = _activas_centro_totales(df, centro)
        sin_ubicar = _incidencias_sin_ubicar(df, centro)

        total_activo += len(activas_centro)
        total_sin_ubicar += len(sin_ubicar)
        total_ubicado += max(0, len(activas_centro) - len(sin_ubicar))

    if total_sin_ubicar:
        st.warning(
            f"⚠️ Hay {total_sin_ubicar} incidencias activas antiguas sin edificio "
            f"o planta reconocible. Ya aparecen provisionalmente en el plano para "
            f"que no desaparezcan de los totales."
        )

        with st.expander(
            f"🔎 Revisar {total_sin_ubicar} incidencias sin ubicación exacta",
            expanded=False,
        ):
            for centro in EDIFICIOS:
                pendientes = _incidencias_sin_ubicar(df, centro)

                if pendientes.empty:
                    continue

                st.markdown(f"#### {centro}")

                columnas_revision = [
                    "numero_ot",
                    "fecha_creacion",
                    "edificio",
                    "planta",
                    "espacio",
                    "descripcion",
                    "estado",
                    "prioridad",
                ]
                columnas_revision = [
                    columna
                    for columna in columnas_revision
                    if columna in pendientes.columns
                ]

                st.dataframe(
                    pendientes[columnas_revision],
                    use_container_width=True,
                    hide_index=True,
                )

    st.caption(
        f"Control de lectura: {total_activo} incidencias activas · "
        f"{total_ubicado} ubicadas directamente · "
        f"{total_sin_ubicar} sin ubicación exacta."
    )

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
    datos = _datos_planta_completos(df, centro, edificio, planta)
    activas = _activas(datos)
    urgentes = _urgentes(activas)

    if not activas.empty:
        estado_normalizado = (
            activas["estado"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        en_curso = activas[
            estado_normalizado.isin(["en curso", "en ejecución", "en ejecucion"])
        ].copy()
    else:
        en_curso = activas

    pendiente_material = _pendiente_material(activas)
    cerradas_mes = _cerradas_mes(datos)

    # Estado ejecutivo de la planta.
    if len(urgentes) > 0:
        clase_estado = "critical"
        icono_estado = "🔴"
        texto_estado = "REQUIERE ATENCIÓN PRIORITARIA"
        nota_estado = "Se recomienda priorizar y realizar seguimiento inmediato."
    elif len(activas) >= 3:
        clase_estado = "alert"
        icono_estado = "🟠"
        texto_estado = "REQUIERE ATENCIÓN"
        nota_estado = "Conviene reforzar el seguimiento de esta planta."
    elif len(activas) > 0:
        clase_estado = "watch"
        icono_estado = "🟡"
        texto_estado = "EN SEGUIMIENTO"
        nota_estado = "La situación está controlada, con actuaciones pendientes de seguimiento."
    else:
        clase_estado = "good"
        icono_estado = "🟢"
        texto_estado = "BAJO CONTROL"
        nota_estado = "No hay incidencias activas en esta planta."

    st.button("← Volver al colegio", key="gerencia_v3_volver", on_click=_volver_mapa)

    st.markdown(
        f'<div class="rv-detail">'
        f'<div class="rv-detail-title">📍 {html.escape(centro)} · {html.escape(edificio)} · {html.escape(planta)}</div>'
        '<div class="rv-detail-sub">Resumen ejecutivo para Gerencia</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="rv-exec-state {clase_estado}">'
        f'<div><div class="rv-exec-label">Estado de la planta</div>'
        f'<div class="rv-exec-value">{icono_estado} {texto_estado}</div></div>'
        f'<div class="rv-exec-note">{html.escape(nota_estado)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    columnas = st.columns(5)
    for columna, etiqueta, valor in zip(
        columnas,
        [
            "Activas",
            "En curso",
            "Pendiente material",
            "Urgentes / altas",
            "Finalizadas mes",
        ],
        [
            len(activas),
            len(en_curso),
            len(pendiente_material),
            len(urgentes),
            len(cerradas_mes),
        ],
    ):
        with columna:
            st.markdown(
                f'<div class="rv-kpi">'
                f'<div class="rv-kpi-label">{etiqueta}</div>'
                f'<div class="rv-kpi-value">{valor}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Resumen de áreas.
    if activas.empty:
        areas = pd.Series(dtype="int64")
    else:
        areas = (
            activas["area"]
            .fillna("Sin área")
            .replace("", "Sin área")
            .value_counts()
        )

    # Responsable predominante.
    responsable = "Sin asignar"
    if not activas.empty and "operario" in activas.columns:
        operarios = (
            activas["operario"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        operarios = operarios[operarios.ne("")]
        if not operarios.empty:
            responsable = str(operarios.value_counts().index[0])

    # Datos ejecutivos globales de la planta.
    numero_areas = int(len(areas))

    # Responsable predominante ya calculado arriba.
    ot_mas_antigua = "—"
    antiguedad_dias = None

    if not activas.empty:
        ordenadas = activas.sort_values(
            "fecha_dt",
            ascending=True,
            na_position="last",
        )
        primera = ordenadas.iloc[0]
        ot_mas_antigua = str(primera.get("numero_ot", "") or "—")

        fecha_antigua = pd.to_datetime(
            primera.get("fecha_dt"),
            errors="coerce",
        )
        if pd.notna(fecha_antigua):
            antiguedad_dias = max(0, (pd.Timestamp.today().normalize() - fecha_antigua.normalize()).days)

    # Tendencia: incidencias creadas en los últimos 7 días frente a los 7 anteriores.
    fechas_creacion = pd.to_datetime(
        datos.get("fecha_dt"),
        errors="coerce",
    )
    hoy_normalizado = pd.Timestamp.today().normalize()
    inicio_actual = hoy_normalizado - pd.Timedelta(days=6)
    inicio_anterior = hoy_normalizado - pd.Timedelta(days=13)
    fin_anterior = hoy_normalizado - pd.Timedelta(days=7)

    nuevas_actual = int(
        ((fechas_creacion >= inicio_actual) & (fechas_creacion <= hoy_normalizado + pd.Timedelta(days=1))).sum()
    )
    nuevas_anterior = int(
        ((fechas_creacion >= inicio_anterior) & (fechas_creacion <= fin_anterior)).sum()
    )
    diferencia_tendencia = nuevas_actual - nuevas_anterior

    if diferencia_tendencia < 0:
        clase_tendencia = "good"
        icono_tendencia = "↘"
        texto_tendencia = f"{abs(diferencia_tendencia)} menos que la semana anterior"
    elif diferencia_tendencia > 0:
        clase_tendencia = "bad"
        icono_tendencia = "↗"
        texto_tendencia = f"{diferencia_tendencia} más que la semana anterior"
    else:
        clase_tendencia = "flat"
        icono_tendencia = "→"
        texto_tendencia = "Sin cambios respecto a la semana anterior"

    izquierda, derecha = st.columns([0.9, 1.1], gap="large")

    with izquierda:
        st.markdown("### Áreas afectadas")

        if areas.empty:
            st.success("No hay áreas afectadas.")
        else:
            filas_html = ""
            for area, cantidad in areas.head(6).items():
                filas_html += (
                    '<div class="rv-area-row">'
                    f'<div class="rv-area-name">{html.escape(str(area))}</div>'
                    f'<div class="rv-area-count">{int(cantidad)}</div>'
                    '</div>'
                )

            st.markdown(
                f'<div class="rv-summary">{filas_html}</div>',
                unsafe_allow_html=True,
            )

    with derecha:
        st.markdown("### Resumen ejecutivo")

        antiguedad_texto = (
            f"{antiguedad_dias} días abierta"
            if antiguedad_dias is not None
            else "Fecha no disponible"
        )

        st.markdown(
            '<div class="rv-summary">'
            '<div class="rv-summary-title">Visión global de la planta</div>'
            '<ul class="rv-exec-list">'
            f'<li><span>Incidencias activas</span><strong>{len(activas)}</strong></li>'
            f'<li><span>Atención prioritaria</span><strong>{len(urgentes)}</strong></li>'
            f'<li><span>Pendientes de material</span><strong>{len(pendiente_material)}</strong></li>'
            f'<li><span>Áreas afectadas</span><strong>{numero_areas}</strong></li>'
            f'<li><span>Responsable principal</span><strong>{html.escape(responsable)}</strong></li>'
            f'<li><span>OT más antigua</span><strong>{html.escape(ot_mas_antigua)} · {html.escape(antiguedad_texto)}</strong></li>'
            '</ul>'
            f'<div class="rv-trend {clase_tendencia}">{icono_tendencia} {html.escape(texto_tendencia)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with st.expander(
        f"Ver detalle de las {len(activas)} incidencias activas",
        expanded=False,
    ):
        if activas.empty:
            st.info("No hay incidencias activas.")
        else:
            vista = activas.sort_values(
                "fecha_dt",
                ascending=True,
                na_position="last",
            ).copy()

            vista["descripcion"] = vista["descripcion"].apply(
                _limpiar_descripcion
            )

            def _estado_visual(valor):
                estado = str(valor or "").strip()
                normalizado = estado.lower()

                if normalizado in ["en curso", "en ejecución", "en ejecucion"]:
                    return f"🛠️ {estado}"

                if normalizado in [
                    "pendiente material",
                    "esperando material",
                    "pendiente proveedor",
                    "pendiente presupuesto",
                ]:
                    return f"📦 {estado}"

                return f"📋 {estado}" if estado else "📋 Abierta"

            vista["estado"] = vista["estado"].apply(_estado_visual)

            columnas_vista = [
                "numero_ot",
                "espacio",
                "descripcion",
                "area",
                "prioridad",
                "estado",
                "operario",
            ]
            columnas_vista = [
                columna
                for columna in columnas_vista
                if columna in vista.columns
            ]

            nombres_columnas = {
                "numero_ot": "OT",
                "espacio": "Ubicación",
                "descripcion": "Descripción",
                "area": "Área",
                "prioridad": "Prioridad",
                "estado": "Estado",
                "operario": "Responsable",
            }

            vista = vista[columnas_vista].rename(
                columns=nombres_columnas
            )

            st.dataframe(
                vista,
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("Indicadores generales del centro", expanded=False):
        _, porcentaje, mensaje = evaluar_estado_centro(df, centro)
        inventario = preparar_inventario()
        inventario_centro = filtrar_inventario_por_centro(
            inventario,
            centro,
        )

        stock_bajo = 0
        if (
            not inventario_centro.empty
            and "stock_minimo" in inventario_centro.columns
        ):
            minimo = pd.to_numeric(
                inventario_centro["stock_minimo"],
                errors="coerce",
            ).fillna(0)

            stock_bajo = int(
                (inventario_centro["stock_num"] <= minimo).sum()
            )

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
                "prioridad", "observaciones", "origen_tabla", "fecha_dt", "fecha_cierre_dt",
            ]
        )

    vista = st.session_state.get("gerencia_v3_vista", "mapa")
    centro = st.session_state.get("gerencia_v3_centro", "")
    edificio = st.session_state.get("gerencia_v3_edificio", "")
    planta = st.session_state.get("gerencia_v3_planta", "")

    if vista == "detalle" and centro and edificio and planta:
        _mostrar_detalle(df, centro, edificio, planta)
    else:
        _mostrar_mapa(df)
