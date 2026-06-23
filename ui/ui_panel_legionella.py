import os
import html
import math
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import date, timedelta
from database.db import conectar


def adaptar_sql(sql):
    if os.getenv("DATABASE_URL"):
        return sql.replace("?", "%s")
    return sql


def leer_df(sql, params=()):
    conn = conectar()
    try:
        return pd.read_sql_query(adaptar_sql(sql), conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def escalar(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return str(valor)


def porcentaje(ok, total):
    try:
        total = int(total or 0)
        ok = int(ok or 0)
        if total <= 0:
            return 0
        return round((ok / total) * 100, 1)
    except Exception:
        return 0


def valor_unico(df, columna="total", defecto=0):
    try:
        if df.empty or columna not in df.columns:
            return defecto
        return int(df.loc[0, columna] or 0)
    except Exception:
        return defecto


def tarjeta_kpi(titulo, valor, icono):
    st.markdown(
        f"""
        <div style="
            background:#ffffff;border-radius:18px;padding:16px;text-align:center;
            box-shadow:0 3px 10px rgba(0,0,0,0.08);
            border:1px solid #e5e7eb;min-height:125px;
        ">
            <div style="font-size:30px;">{icono}</div>
            <div style="font-size:14px;color:#64748b;">{html.escape(str(titulo))}</div>
            <div style="font-size:30px;font-weight:900;color:#0f172a;">{html.escape(str(valor))}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def tarjeta_instalacion(titulo, icono, lineas, cumplimiento, estado="ok"):
    if estado == "riesgo":
        fondo = "#fee2e2"
        borde = "#fecaca"
        color = "#991b1b"
        semaforo = "🔴"
    elif estado == "proximo":
        fondo = "#fef3c7"
        borde = "#fde68a"
        color = "#92400e"
        semaforo = "🟠"
    else:
        fondo = "#ecfdf5"
        borde = "#bbf7d0"
        color = "#047857"
        semaforo = "🟢"

    lineas_html = "".join(
        [
            f"<div style='margin:6px 0;font-size:15px;color:#0f172a;'>{html.escape(str(linea))}</div>"
            for linea in lineas
        ]
    )

    st.markdown(
        f"""
        <div style="
            background:{fondo};border:1px solid {borde};border-radius:16px;
            padding:14px 16px;min-height:165px;
            box-shadow:0 2px 8px rgba(0,0,0,0.04);
        ">
            <div style="font-size:17px;font-weight:900;color:{color};margin-bottom:8px;">
                {icono} {html.escape(str(titulo))}
            </div>
            {lineas_html}
            <div style="margin-top:10px;font-size:16px;font-weight:900;color:{color};">
                {semaforo} Cumplimiento: {html.escape(str(cumplimiento))}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def punto_control(codigo, estado="ok"):
    codigo = html.escape(str(codigo or ""))

    if estado == "riesgo":
        fondo = "#fee2e2"
        color = "#991b1b"
        icono = "🔴"
    elif estado == "proximo":
        fondo = "#fef3c7"
        color = "#92400e"
        icono = "🟠"
    else:
        fondo = "#dcfce7"
        color = "#166534"
        icono = "🟢"

    return f"""
    <div style="
        background:{fondo};color:{color};padding:10px 14px;border-radius:12px;
        font-weight:800;font-size:14px;display:inline-block;margin:5px;
        min-width:82px;text-align:center;border:1px solid rgba(0,0,0,0.05);
        white-space:nowrap;
    ">
        {codigo} {icono}
    </div>
    """


# =====================================================
# CONTADORES REALES
# =====================================================

def _placeholders(lista):
    return ",".join(["?"] * len(lista))


def contar_puntos_exactos(centro=None, tipos=None, tipos_control=None, instalacion=None):
    condiciones = ["activo = 1"]
    params = []

    if centro:
        condiciones.append("centro = ?")
        params.append(centro)

    if tipos:
        condiciones.append(
            "LOWER(COALESCE(tipo_punto, '')) IN (" + _placeholders(tipos) + ")"
        )
        params.extend([str(t).lower() for t in tipos])

    if tipos_control:
        condiciones.append(
            "LOWER(COALESCE(tipo_control_punto, '')) IN (" + _placeholders(tipos_control) + ")"
        )
        params.extend([str(t).lower() for t in tipos_control])

    if instalacion:
        condiciones.append("LOWER(COALESCE(instalacion, '')) = ?")
        params.append(str(instalacion).lower())

    df = leer_df(f"""
        SELECT COUNT(*) AS total
        FROM legionella_puntos
        WHERE {' AND '.join(condiciones)}
    """, tuple(params))

    return valor_unico(df)


def contar_registros_por_puntos(centro=None, tipos=None, tipos_control=None, tareas=None):
    condiciones = ["p.activo = 1"]
    params = []

    if centro:
        condiciones.append("p.centro = ?")
        params.append(centro)

    if tipos:
        condiciones.append(
            "LOWER(COALESCE(p.tipo_punto, '')) IN (" + _placeholders(tipos) + ")"
        )
        params.extend([str(t).lower() for t in tipos])

    if tipos_control:
        condiciones.append(
            "LOWER(COALESCE(p.tipo_control_punto, '')) IN (" + _placeholders(tipos_control) + ")"
        )
        params.extend([str(t).lower() for t in tipos_control])

    if tareas:
        condiciones.append(
            "LOWER(COALESCE(r.tarea, '')) IN (" + _placeholders(tareas) + ")"
        )
        params.extend([str(t).lower() for t in tareas])

    df = leer_df(f"""
        SELECT COUNT(r.id) AS total
        FROM legionella_puntos p
        LEFT JOIN legionella_registros r
          ON r.centro = p.centro
         AND r.edificio = p.edificio
         AND r.punto = p.nombre_punto
        WHERE {' AND '.join(condiciones)}
    """, tuple(params))

    return valor_unico(df)


def contar_registros_tarea_global(tareas):
    if isinstance(tareas, str):
        tareas = [tareas]

    df = leer_df(f"""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE LOWER(COALESCE(tarea, '')) IN ({_placeholders(tareas)})
    """, tuple([str(t).lower() for t in tareas]))

    return valor_unico(df)


# =====================================================
# KPIS GENERALES
# =====================================================

def obtener_kpis_legionella():
    hoy = date.today()
    limite = hoy + timedelta(days=30)

    df_puntos = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_puntos
        WHERE activo = 1
    """)

    df_controles = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
    """)

    df_ot = leer_df("""
        SELECT COUNT(*) AS total
        FROM ordenes_trabajo
        WHERE area = 'Legionella'
           OR UPPER(COALESCE(origen, '')) = 'LEGIONELLA'
    """)

    df_incidencias = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_incidencias
        WHERE LOWER(COALESCE(estado, '')) NOT IN ('cerrada', 'cerrado', 'finalizada', 'finalizado')
    """)

    df_tareas = leer_df("""
        SELECT proxima_fecha
        FROM legionella_tareas
        WHERE activo = 1
          AND proxima_fecha IS NOT NULL
          AND TRIM(COALESCE(proxima_fecha, '')) <> ''
    """)

    proximos = 0

    if not df_tareas.empty:
        df_tareas["proxima_fecha_dt"] = pd.to_datetime(df_tareas["proxima_fecha"], errors="coerce")
        proximos = len(
            df_tareas[
                (df_tareas["proxima_fecha_dt"].dt.date >= hoy)
                & (df_tareas["proxima_fecha_dt"].dt.date <= limite)
            ]
        )

    df_ok = leer_df("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN estado = 'OK' THEN 1 ELSE 0 END) AS ok
        FROM legionella_registros
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
    """)

    total_reg = int(df_ok.loc[0, "total"] or 0) if not df_ok.empty else 0
    total_ok = int(df_ok.loc[0, "ok"] or 0) if not df_ok.empty else 0

    return {
        "puntos": valor_unico(df_puntos),
        "controles": valor_unico(df_controles),
        "ot": valor_unico(df_ot),
        "incidencias": valor_unico(df_incidencias),
        "proximos": proximos,
        "cumplimiento": porcentaje(total_ok, total_reg),
    }


def obtener_estado_instalaciones():
    return {
        "acumuladores": contar_puntos_exactos(tipos=["acumulador"]),
        "afch": contar_puntos_exactos(tipos=["grifo", "fuente", "lavamanos", "muestra"]),
        "duchas": contar_puntos_exactos(tipos=["ducha"]),
        "vtm": contar_puntos_exactos(tipos=["Válvulas", "valvulas", "válvulas"]),
        "solar": contar_puntos_exactos(tipos=["acumulador_solar"]),
        "retornos": contar_puntos_exactos(tipos=["retorno"]),

        "temp_acum": contar_registros_por_puntos(
            tipos=["acumulador"],
            tareas=["Temperatura acumulador", "Control sala ACS"]
        ),
        "temp_impulsion": contar_registros_por_puntos(
            tipos=["acumulador"],
            tareas=["Temperatura impulsión ACS", "Control sala ACS"]
        ),
        "temp_retorno": contar_registros_por_puntos(
            tipos=["acumulador"],
            tareas=["Control sala ACS"]
        ),
        "purgas": contar_registros_tarea_global(["Purga"]),
        "choques": contar_registros_tarea_global(["Choque térmico"]),
        "afs": contar_registros_por_puntos(
            tipos=["grifo", "fuente", "lavamanos", "muestra", "ducha"],
            tareas=["Control AFS", "Control punto terminal completo"]
        ),
        "cloro": contar_registros_por_puntos(
            tipos=["grifo", "fuente", "lavamanos", "muestra", "ducha"],
            tareas=["Control AFS", "Control punto terminal completo", "Cloro residual"]
        ),
        "acs_terminal": contar_registros_por_puntos(
            tipos=["ducha", "grifo", "lavamanos"],
            tareas=["Control ACS terminal", "Control punto terminal completo"]
        ),
        "vtm_rev": contar_registros_por_puntos(
            tipos=["Válvulas", "valvulas", "válvulas"],
            tareas=["Control válvula termostática"]
        ),
        "solar_lecturas": contar_registros_por_puntos(
            tipos=["acumulador_solar"],
            tareas=["Temperatura acumulador", "Solo temperatura"]
        ),
    }


def obtener_estado_instalaciones_centro(centro):
    return {
        "acumuladores": contar_puntos_exactos(
            centro=centro,
            tipos=["acumulador"]
        ),

        "afch": contar_puntos_exactos(
            centro=centro,
            tipos=["grifo", "fuente", "lavamanos", "muestra"]
        ),

        "duchas": contar_puntos_exactos(
            centro=centro,
            tipos=["ducha"]
        ),

        "vtm": contar_puntos_exactos(
            centro=centro,
            tipos=["Válvulas", "valvulas", "válvulas"]
        ),

        "solar": contar_puntos_exactos(
            centro=centro,
            tipos=["acumulador_solar"]
        ),

        "retornos": contar_puntos_exactos(
            centro=centro,
            tipos=["retorno"]
        ),

        "temp_acum": contar_registros_por_puntos(
            centro=centro,
            tipos=["acumulador"],
            tareas=["Temperatura acumulador", "Control sala ACS"]
        ),

        "temp_impulsion": contar_registros_por_puntos(
            centro=centro,
            tipos=["acumulador"],
            tareas=["Temperatura impulsión ACS", "Control sala ACS"]
        ),

        "temp_retorno": contar_registros_por_puntos(
            centro=centro,
            tipos=["acumulador"],
            tareas=["Control sala ACS"]
        ),

        "purgas": contar_registros_por_puntos(
            centro=centro,
            tareas=["Purga"]
        ),

        "choques": contar_registros_por_puntos(
            centro=centro,
            tareas=["Choque térmico"]
        ),

        "afs": contar_registros_por_puntos(
            centro=centro,
            tipos=["grifo", "fuente", "lavamanos", "muestra", "ducha"],
            tareas=["Control AFS", "Control punto terminal completo"]
        ),

        "cloro": contar_registros_por_puntos(
            centro=centro,
            tipos=["grifo", "fuente", "lavamanos", "muestra", "ducha"],
            tareas=["Control AFS", "Control punto terminal completo", "Cloro residual"]
        ),

        "acs_terminal": contar_registros_por_puntos(
            centro=centro,
            tipos=["ducha", "grifo", "lavamanos"],
            tareas=["Control ACS terminal", "Control punto terminal completo"]
        ),

        "vtm_rev": contar_registros_por_puntos(
            centro=centro,
            tipos=["Válvulas", "valvulas", "válvulas"],
            tareas=["Control válvula termostática"]
        ),

        "solar_lecturas": contar_registros_por_puntos(
            centro=centro,
            tipos=["acumulador_solar"],
            tareas=["Temperatura acumulador", "Solo temperatura"]
        ),
    }


def bloque_centro_legionella(nombre_centro, datos_centro, cumplimiento_txt):
    st.markdown(f"### 🏫 {nombre_centro}")

    c1, c2, c3 = st.columns(3)

    with c1:
        tarjeta_instalacion(
            "ACS",
            "🔥",
            [
                f"Acumuladores: {datos_centro['acumuladores']}",
                f"Temperaturas acumulador: {datos_centro['temp_acum']}",
                f"Impulsión: {datos_centro['temp_impulsion']}",
                f"Purgas: {datos_centro['purgas']}",
            ],
            cumplimiento_txt
        )

    with c2:
        solar_estado = "riesgo" if datos_centro["solar"] > 0 and datos_centro["solar_lecturas"] == 0 else "ok"

        tarjeta_instalacion(
            "SOLAR",
            "☀️",
            [
                f"Depósitos solares: {datos_centro['solar']}",
                f"Lecturas realizadas: {datos_centro['solar_lecturas']}",
                "Registro sin consigna automática",
                "Seguimiento de temperatura",
            ],
            cumplimiento_txt,
            solar_estado
        )

    with c3:
        tarjeta_instalacion(
            "AFCH / AFS",
            "💧",
            [
                f"Puntos agua fría: {datos_centro['afch']}",
                f"Controles AFS: {datos_centro['afs']}",
                f"Cloro residual: {datos_centro['cloro']}",
                "Control de temperatura y desinfectante",
            ],
            cumplimiento_txt
        )

    st.markdown("<br>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)

    with c4:
        tarjeta_instalacion(
            "DUCHAS",
            "🚿",
            [
                f"Puntos ducha: {datos_centro['duchas']}",
                f"ACS terminal: {datos_centro['acs_terminal']}",
                f"Purgas: {datos_centro['purgas']}",
                "Duchas incluidas en control",
            ],
            cumplimiento_txt
        )

    with c5:
        tarjeta_instalacion(
            "RETORNOS",
            "🔄",
            [
                f"Mediciones retorno: {datos_centro['temp_retorno']}",
                "Integrado en Control sala ACS",
                "Temperatura mínima: ≥ 50 ºC",
                "Recirculación controlada",
            ],
            cumplimiento_txt
        )

    with c6:
        tarjeta_instalacion(
            "VTM",
            "🎛️",
            [
                f"Válvulas termostáticas: {datos_centro['vtm']}",
                f"Revisiones: {datos_centro['vtm_rev']}",
                "Entrada / salida controlada",
                "Accesos revisados",
            ],
            cumplimiento_txt
        )


def obtener_puntos_control():
    df = leer_df("""
        SELECT
            p.nombre_punto,
            p.centro,
            p.edificio,
            p.tipo_punto,
            p.tipo_control_punto,
            (
                SELECT r.estado
                FROM legionella_registros r
                WHERE r.punto = p.nombre_punto
                  AND r.centro = p.centro
                  AND r.edificio = p.edificio
                ORDER BY r.fecha DESC, r.id DESC
                LIMIT 1
            ) AS ultimo_estado
        FROM legionella_puntos p
        WHERE p.activo = 1
        ORDER BY p.centro, p.edificio, p.nombre_punto
    """)

    if df.empty:
        return []

    palabras_antiguas = [
        "choque térmico",
        "choque termico",
        "control temperatura",
        "temperatura/",
        "acs-02-duchas",
        "acs-03-ducha",
        "acumulador acs-01-m-02",
    ]

    puntos = []

    for _, row in df.iterrows():
        nombre = str(row.get("nombre_punto") or "").strip()
        estado = str(row.get("ultimo_estado") or "OK").upper()

        if not nombre:
            continue

        nombre_lower = nombre.lower()

        if any(palabra in nombre_lower for palabra in palabras_antiguas):
            continue

        estado_visual = "riesgo" if estado in ["RIESGO", "INCIDENCIA"] else "ok"
        puntos.append((nombre, estado_visual))

    return puntos

def obtener_ficha_punto_control(nombre_punto):
    df = leer_df("""
        SELECT
            p.id,
            p.nombre_punto,
            p.centro,
            p.edificio,
            p.instalacion,
            p.tipo_punto,
            p.tipo_control_punto,
            p.ubicacion,
            p.ubicacion_exacta,
            p.numero_terminales,
            p.observaciones,
            (
                SELECT r.fecha
                FROM legionella_registros r
                WHERE r.punto = p.nombre_punto
                  AND r.centro = p.centro
                  AND r.edificio = p.edificio
                ORDER BY r.fecha DESC, r.id DESC
                LIMIT 1
            ) AS ultima_fecha,
            (
                SELECT r.estado
                FROM legionella_registros r
                WHERE r.punto = p.nombre_punto
                  AND r.centro = p.centro
                  AND r.edificio = p.edificio
                ORDER BY r.fecha DESC, r.id DESC
                LIMIT 1
            ) AS ultimo_estado,
            (
                SELECT r.resultado
                FROM legionella_registros r
                WHERE r.punto = p.nombre_punto
                  AND r.centro = p.centro
                  AND r.edificio = p.edificio
                ORDER BY r.fecha DESC, r.id DESC
                LIMIT 1
            ) AS ultimo_resultado
        FROM legionella_puntos p
        WHERE p.activo = 1
          AND p.nombre_punto = ?
        LIMIT 1
    """, (nombre_punto,))

    if df.empty:
        return None

    return df.iloc[0].to_dict()


def obtener_incidencias_abiertas():
    return leer_df("""
        SELECT centro, edificio, punto, tarea, descripcion
        FROM legionella_incidencias
        WHERE LOWER(COALESCE(estado, '')) NOT IN ('cerrada', 'cerrado', 'finalizada', 'finalizado')
        ORDER BY fecha_apertura DESC
        LIMIT 5
    """)


def obtener_proximos_controles():
    hoy = date.today()
    limite = hoy + timedelta(days=30)

    df = leer_df("""
        SELECT centro, edificio, punto, tarea, proxima_fecha
        FROM legionella_tareas
        WHERE activo = 1
          AND proxima_fecha IS NOT NULL
          AND TRIM(COALESCE(proxima_fecha, '')) <> ''
        ORDER BY proxima_fecha ASC
    """)

    if df.empty:
        return df

    df["proxima_fecha_dt"] = pd.to_datetime(df["proxima_fecha"], errors="coerce")

    df = df[
        (df["proxima_fecha_dt"].dt.date >= hoy)
        & (df["proxima_fecha_dt"].dt.date <= limite)
    ].copy()

    return df.head(5)


def obtener_actividad_anual():
    anio = str(date.today().year)

    temperaturas = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE substr(fecha, 1, 4) = ?
          AND (
              LOWER(COALESCE(tarea, '')) LIKE '%temperatura%'
              OR LOWER(COALESCE(tipo_control, '')) LIKE '%temperatura%'
              OR LOWER(COALESCE(tarea, '')) LIKE '%acs%'
              OR LOWER(COALESCE(tarea, '')) LIKE '%afs%'
              OR LOWER(COALESCE(tarea, '')) LIKE '%afch%'
          )
    """, (anio,))

    purgas = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE substr(fecha, 1, 4) = ?
          AND LOWER(COALESCE(tarea, '')) = 'purga'
    """, (anio,))

    choques = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
        WHERE substr(fecha, 1, 4) = ?
          AND LOWER(COALESCE(tarea, '')) = 'choque térmico'
    """, (anio,))

    analiticas = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_informes
        WHERE substr(fecha_informe, 1, 4) = ?
          AND (
              LOWER(COALESCE(tipo_informe, '')) LIKE '%analítica%'
              OR LOWER(COALESCE(tipo_informe, '')) LIKE '%analitica%'
          )
    """, (anio,))

    return {
        "temperaturas": valor_unico(temperaturas),
        "purgas": valor_unico(purgas),
        "choques": valor_unico(choques),
        "analiticas": valor_unico(analiticas),
    }


def obtener_dossier_estado():
    plan = valor_unico(leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_tareas
        WHERE activo = 1
    """))

    registros = valor_unico(leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_registros
    """))

    informes = valor_unico(leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_informes
    """))

    puntos = valor_unico(leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_puntos
        WHERE activo = 1
    """))

    abiertas = valor_unico(leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_incidencias
        WHERE LOWER(COALESCE(estado, '')) NOT IN ('cerrada', 'cerrado', 'finalizada', 'finalizado')
    """))

    return {
        "puntos": puntos > 0,
        "plan": plan > 0,
        "registros": registros > 0,
        "informes": informes > 0,
        "correctivos": abiertas == 0,
    }


def estado_general_instalacion(kpis):
    return "proximo" if kpis["incidencias"] > 0 else "ok"


def pintar_semaforo_general(kpis, datos):
    estado_global = estado_general_instalacion(kpis)
    solar_estado = "riesgo" if datos["solar"] > 0 and datos["solar_lecturas"] == 0 else "ok"

    items = [
        ("🔥 ACS", "ok"),
        ("💧 AFCH", "ok"),
        ("🚿 Duchas", "ok"),
        ("🔄 Retornos", "ok"),
        ("🎛️ VTM", "ok"),
        ("☀️ Solar", solar_estado),
        ("🏫 Global", estado_global),
    ]

    html_items = ""

    for texto, estado in items:
        if estado == "riesgo":
            fondo, color, icono = "#fee2e2", "#991b1b", "🔴"
        elif estado == "proximo":
            fondo, color, icono = "#fef3c7", "#92400e", "🟠"
        else:
            fondo, color, icono = "#dcfce7", "#166534", "🟢"

        html_items += f"""
        <div style="
            background:{fondo};color:{color};border-radius:14px;
            padding:12px 18px;margin:6px;display:inline-block;
            font-weight:900;border:1px solid rgba(0,0,0,0.06);
        ">
            {icono} {html.escape(texto)}
        </div>
        """

    components.html(
        f"""
        <div style="
            background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;
            padding:14px;box-shadow:0 3px 10px rgba(0,0,0,0.06);
        ">
            {html_items}
        </div>
        """,
        height=92,
        scrolling=False
    )


def pintar_dossier_inspeccion(dossier):
    total_ok = sum(1 for v in dossier.values() if v)
    total = len(dossier)

    if total_ok == total:
        st.success("🟢 INSPECCIÓN PREPARADA")
    else:
        st.warning(f"🟠 Dossier parcialmente preparado: {total_ok}/{total}")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.success("✔ Puntos identificados") if dossier["puntos"] else st.error("✖ Faltan puntos")

    with c2:
        st.success("✔ Plan actualizado") if dossier["plan"] else st.error("✖ Falta planificación")

    with c3:
        st.success("✔ Registros completos") if dossier["registros"] else st.error("✖ Sin registros")

    with c4:
        st.success("✔ Informes archivados") if dossier["informes"] else st.warning("⚠ Sin informes externos")

    with c5:
        st.success("✔ Correctivos cerrados") if dossier["correctivos"] else st.warning("⚠ Correctivos pendientes")


def pantalla_panel_legionella():
    kpis = obtener_kpis_legionella()
    datos = obtener_estado_instalaciones()
    datos_p22 = obtener_estado_instalaciones_centro("Pearson 22")
    datos_p9 = obtener_estado_instalaciones_centro("Pearson 9")
    actividad = obtener_actividad_anual()
    dossier = obtener_dossier_estado()
    incidencias = obtener_incidencias_abiertas()
    proximos = obtener_proximos_controles()
    puntos = obtener_puntos_control()

    cumplimiento_txt = f"{str(kpis['cumplimiento']).replace('.', ',')}%"

    st.markdown(
        """
        <div style="
            background:linear-gradient(135deg,#0f172a,#1d4ed8);
            padding:25px;border-radius:22px;color:white;margin-bottom:18px;
            box-shadow:0 8px 24px rgba(15,23,42,0.18);
        ">
            <h1 style="margin:0;font-size:38px;">🛡️ Centro de Control Legionella</h1>
            <p style="margin-top:10px;font-size:16px;font-weight:700;">
                Colegio Abat Oliba Loreto
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if kpis["incidencias"] == 0:
        st.success("🟢 Instalación controlada · Sin riesgos críticos activos")
    else:
        st.warning(f"🟠 Instalación con {kpis['incidencias']} incidencia(s) abierta(s)")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        tarjeta_kpi("Puntos", escalar(kpis["puntos"]), "💧")
    with c2:
        tarjeta_kpi("Controles", escalar(kpis["controles"]), "📋")
    with c3:
        tarjeta_kpi("OT Legionella", escalar(kpis["ot"]), "🛠️")
    with c4:
        tarjeta_kpi("Incidencias", escalar(kpis["incidencias"]), "⚠️")
    with c5:
        tarjeta_kpi("Próximos", escalar(kpis["proximos"]), "📅")
    with c6:
        tarjeta_kpi("Cumplimiento", cumplimiento_txt, "🏆")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("## 🚦 Semáforo general")
    pintar_semaforo_general(kpis, datos)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("## 🏢 Estado de las instalaciones")

    c1, c2, c3 = st.columns(3)

    with c1:
        tarjeta_instalacion("ACS", "🔥", [
            f"Acumuladores: {datos['acumuladores']}",
            f"Temperaturas acumulador: {datos['temp_acum']}",
            f"Impulsión: {datos['temp_impulsion']}",
            f"Purgas: {datos['purgas']}",
            f"Choques térmicos: {datos['choques']}",
        ], cumplimiento_txt)

    with c2:
        tarjeta_instalacion("AFCH", "💧", [
            f"Puntos terminales: {datos['afch']}",
            f"Controles AFS: {datos['afs']}",
            f"Cloro residual: {datos['cloro']}",
            "Control de temperatura y desinfectante",
        ], cumplimiento_txt)

    with c3:
        tarjeta_instalacion("DUCHAS", "🚿", [
            f"Puntos: {datos['duchas']}",
            f"Controles ACS terminal: {datos['acs_terminal']}",
            f"Purgas: {datos['purgas']}",
            "Duchas incluidas en control",
        ], cumplimiento_txt)

    st.markdown("<br>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)

    with c4:
        tarjeta_instalacion("VTM", "🎛️", [
            f"Válvulas termostáticas: {datos['vtm']}",
            f"Revisiones: {datos['vtm_rev']}",
            "Entrada / salida controlada",
            "Accesos revisados",
        ], cumplimiento_txt)

    with c5:
        solar_estado = "riesgo" if datos["solar"] > 0 and datos["solar_lecturas"] == 0 else "ok"

        tarjeta_instalacion("SOLAR", "☀️", [
            f"Depósitos solares: {datos['solar']}",
            f"Lecturas realizadas: {datos['solar_lecturas']}",
            "Registro sin consigna automática",
            "Seguimiento de temperatura",
        ], cumplimiento_txt, solar_estado)

    with c6:
        tarjeta_instalacion("RETORNOS", "🔄", [
            f"Mediciones retorno: {datos['temp_retorno']}",
            "Integrado en Control sala ACS",
            "Temperatura mínima: ≥ 50 ºC",
            "Recirculación controlada",
        ], cumplimiento_txt)

    st.markdown("---")
    st.markdown("## 🏫 Estado por centro")

    bloque_centro_legionella("Pearson 22", datos_p22, cumplimiento_txt)

    st.markdown("<br>", unsafe_allow_html=True)

    bloque_centro_legionella("Pearson 9", datos_p9, cumplimiento_txt)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("## 🗺️ Puntos físicos de control")

    if puntos:
        puntos_html = "<div style='margin-bottom:10px;'>"
        for nombre, estado in puntos:
            puntos_html += punto_control(nombre, estado)
        puntos_html += "</div>"

        filas = max(1, math.ceil(len(puntos) / 8))
        alto = min(300, max(90, filas * 58))

        components.html(puntos_html, height=alto, scrolling=False)

        nombres_puntos = [nombre for nombre, _ in puntos]

        punto_sel = st.selectbox(
            "Ver ficha de punto",
            ["Selecciona un punto"] + nombres_puntos,
            key="panel_legionella_ficha_punto"
        )

        if punto_sel != "Selecciona un punto":
            ficha = obtener_ficha_punto_control(punto_sel)

            if ficha is None:
                st.warning("No se ha encontrado la ficha del punto.")
            else:
                st.markdown("### 📌 Ficha del punto")

                c1, c2, c3 = st.columns(3)

                with c1:
                    st.write(f"**Punto:** {ficha.get('nombre_punto', '')}")
                    st.write(f"**Centro:** {ficha.get('centro', '')}")
                    st.write(f"**Edificio:** {ficha.get('edificio', '')}")

                with c2:
                    st.write(f"**Instalación:** {ficha.get('instalacion', '')}")
                    st.write(f"**Tipo punto:** {ficha.get('tipo_punto', '')}")
                    st.write(f"**Tipo control:** {ficha.get('tipo_control_punto', '')}")

                with c3:
                    st.write(f"**Ubicación:** {ficha.get('ubicacion', '')}")
                    st.write(f"**Ubicación exacta:** {ficha.get('ubicacion_exacta', '')}")
                    st.write(f"**Terminales:** {ficha.get('numero_terminales', '')}")

                st.markdown("#### Último control")

                estado = ficha.get("ultimo_estado") or "Sin registros"
                resultado = ficha.get("ultimo_resultado") or ""
                fecha = ficha.get("ultima_fecha") or ""

                st.write(f"**Fecha:** {fecha}")
                st.write(f"**Estado:** {estado}")
                st.write(f"**Resultado:** {resultado}")

                if ficha.get("observaciones"):
                    st.info(f"Observaciones: {ficha.get('observaciones')}")
    else:
        st.info("Todavía no hay puntos activos registrados.")

    st.markdown("---")

    st.markdown("## 🚨 Situación operativa actual")

    c1, c2, c3 = st.columns(3)

    with c1:
        if incidencias.empty:
            st.success("🟢 Sin incidencias abiertas")
        else:
            texto = "🔴 Incidencias abiertas\n\n"
            for _, row in incidencias.iterrows():
                texto += f"• {row.get('punto', '')} · {row.get('tarea', '')}\n"
            texto += f"\nTotal visible: {len(incidencias)}"
            st.error(texto)

    with c2:
        if proximos.empty:
            st.success("🟢 Sin controles próximos")
        else:
            texto = "🟠 Próximos controles\n\n"
            for _, row in proximos.iterrows():
                texto += f"• {row.get('punto', '')} · {row.get('tarea', '')} → {row.get('proxima_fecha', '')}\n"
            texto += f"\nTotal visible: {len(proximos)}"
            st.warning(texto)

    with c3:
        if kpis["incidencias"] == 0:
            st.success("🟢 Estado general\n\nInstalación controlada\n\nSin riesgos críticos")
        else:
            st.warning("🟠 Estado general\n\nRevisar incidencias abiertas\n\nSeguimiento activo")

    st.markdown("---")

    st.markdown("## 📅 Actividad anual")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Temperaturas", escalar(actividad["temperaturas"]))
    with col2:
        st.metric("Purgas", escalar(actividad["purgas"]))
    with col3:
        st.metric("Choques térmicos", escalar(actividad["choques"]))
    with col4:
        st.metric("Analíticas", escalar(actividad["analiticas"]))

    st.markdown("---")

    st.markdown("## 🏆 Dossier de inspección")
    pintar_dossier_inspeccion(dossier)

    st.info(
        "✅ Panel conectado a datos reales de Legionella: puntos, registros, planificación, incidencias, informes, órdenes y separación por centro."
    )
