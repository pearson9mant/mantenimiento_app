import streamlit as st
import pandas as pd
from datetime import datetime, date
import unicodedata
import re

from database.db import conectar
from ui.ui_arbol_colegio import mostrar_arbol_gerencia


CENTROS_GERENCIA = ["Pearson 9", "Pearson 22"]

ESTADOS_CERRADOS = ["Finalizada", "Finalizado", "Cerrada", "Cerrado"]
ESTADOS_MATERIAL = ["Pendiente material", "Esperando material"]

FECHA_INICIO_EVOLUCION = date(2026, 9, 1)
FECHA_FIN_EVOLUCION = date(2027, 8, 31)

MESES_CURSO_2026_2027 = [
    ("2026-09", "Sep 26"),
    ("2026-10", "Oct 26"),
    ("2026-11", "Nov 26"),
    ("2026-12", "Dic 26"),
    ("2027-01", "Ene 27"),
    ("2027-02", "Feb 27"),
    ("2027-03", "Mar 27"),
    ("2027-04", "Abr 27"),
    ("2027-05", "May 27"),
    ("2027-06", "Jun 27"),
    ("2027-07", "Jul 27"),
    ("2027-08", "Ago 27"),
]


def aplicar_estilo_gerencia():
    st.markdown("""
    <style>
    .gerencia-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
        color: white;
        border-radius: 24px;
        padding: 24px 28px;
        margin-bottom: 22px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.18);
    }
    .gerencia-title { font-size: 30px; font-weight: 900; margin-bottom: 4px; }
    .gerencia-subtitle { font-size: 16px; font-weight: 600; opacity: 0.92; }
    .gerencia-section-title {
        font-size: 24px; font-weight: 900; color: #0f172a;
        margin-top: 20px; margin-bottom: 12px;
    }
    .gerencia-card-info {
        background: #f8fafc; border: 1px solid #e5e7eb;
        border-radius: 18px; padding: 14px 16px;
        margin-bottom: 14px; color: #334155; font-weight: 700;
    }
    .gerencia-evolucion-box {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
        border: 1px solid #dbeafe;
        border-radius: 22px;
        padding: 18px 20px;
        margin: 14px 0 18px 0;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }
    .gerencia-evolucion-title {
        font-size: 22px;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .gerencia-evolucion-subtitle {
        color: #475569;
        font-size: 14px;
        font-weight: 600;
    }
    div.stButton > button {
        min-height: 86px; border-radius: 20px; border: 1px solid #e5e7eb;
        background: #ffffff; box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
        font-size: 17px; font-weight: 900; color: #0f172a; white-space: pre-line;
    }
    div.stButton > button:hover {
        border: 1px solid #2563eb; background: #eff6ff; color: #1d4ed8;
    }
    @media (max-width: 768px) {
        .gerencia-title { font-size: 24px; }
        .gerencia-subtitle { font-size: 14px; }
        .gerencia-hero { padding: 20px 18px; border-radius: 20px; }
        div.stButton > button { min-height: 74px; font-size: 15px; }
    }
    </style>
    """, unsafe_allow_html=True)


def iniciar_estado_gerencia():
    if "gerencia_centro" not in st.session_state:
        st.session_state["gerencia_centro"] = None
    if "gerencia_detalle" not in st.session_state:
        st.session_state["gerencia_detalle"] = None


def volver_a_centros():
    st.session_state["gerencia_centro"] = None
    st.session_state["gerencia_detalle"] = None
    st.rerun()


def volver_a_menu_centro():
    st.session_state["gerencia_detalle"] = None
    st.rerun()


@st.cache_data(ttl=60)
def leer_tabla(nombre_tabla):
    conn = conectar()

    try:
        if nombre_tabla == "inventario":
            df = pd.read_sql_query("""
                SELECT
                    id, codigo, material, categoria, unidad,
                    stock_actual, stock_minimo, centro, edificio, ubicacion,
                    proveedor, observaciones, fecha_alta, foto, foto_nombre,
                    activo, precio_unitario, coste_total, fecha_compra,
                    referencia_factura, observaciones_coste
                FROM inventario
            """, conn)
        else:
            df = pd.read_sql_query(f"SELECT * FROM {nombre_tabla}", conn)

    except Exception:
        df = pd.DataFrame()

    finally:
        conn.close()

    return df


def obtener_foto_inventario_por_id(id_material):
    if id_material is None or str(id_material).strip() == "":
        return None

    conn = conectar()
    cursor = conn.cursor()

    try:
        marcador = "?" if "sqlite" in conn.__class__.__module__.lower() else "%s"

        cursor.execute(
            f"""
            SELECT foto_data
            FROM inventario
            WHERE id = {marcador}
            """,
            (int(id_material),)
        )

        fila = cursor.fetchone()
        return fila[0] if fila else None

    except Exception:
        return None

    finally:
        conn.close()


def leer_primera_tabla_existente(posibles_tablas):
    for tabla in posibles_tablas:
        df = leer_tabla(tabla)
        if not df.empty:
            return df, tabla
    return pd.DataFrame(), ""


def preparar_ordenes():
    ordenes = leer_tabla("ordenes_trabajo")
    historico = leer_tabla("historico_ordenes")

    if not ordenes.empty:
        ordenes["origen_tabla"] = "activas"

    if not historico.empty:
        historico["origen_tabla"] = "historico"
        if "estado" not in historico.columns:
            historico["estado"] = "Finalizada"

    if ordenes.empty and historico.empty:
        return pd.DataFrame()

    df = pd.concat([ordenes, historico], ignore_index=True)

    columnas_defecto = {
        "numero_ot": "",
        "fecha_creacion": "",
        "fecha_cierre": "",
        "centro": "Sin centro",
        "edificio": "",
        "planta": "",
        "espacio": "",
        "descripcion": "",
        "estado": "Abierta",
        "operario": "",
        "solicitante": "",
        "origen": "",
        "area": "",
        "prioridad": "",
        "origen_tabla": "",
    }

    for col, valor in columnas_defecto.items():
        if col not in df.columns:
            df[col] = valor

    df["estado"] = df["estado"].fillna("").astype(str).str.strip()
    df["centro"] = df["centro"].fillna("").astype(str).str.strip()
    df["origen"] = df["origen"].fillna("").astype(str).str.strip()
    df["area"] = df["area"].fillna("").astype(str).str.strip()
    df["descripcion"] = df["descripcion"].fillna("").astype(str)

    df["fecha_dt"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["fecha_cierre_dt"] = pd.to_datetime(df["fecha_cierre"], errors="coerce")

    return df


def preparar_inventario():
    df = leer_tabla("inventario")

    if df.empty:
        return pd.DataFrame()

    columnas_defecto = {
        "codigo": "",
        "material": "",
        "nombre": "",
        "categoria": "",
        "stock": 0,
        "stock_actual": 0,
        "precio_unitario": 0,
        "coste_total": 0,
        "centro": "",
        "ubicacion": "",
        "activo": 1,
        "fecha_compra": "",
        "foto": "",
        "foto_nombre": "",
    }

    for col, valor in columnas_defecto.items():
        if col not in df.columns:
            df[col] = valor

    df["material_mostrar"] = df["material"].fillna("")
    df.loc[df["material_mostrar"].astype(str).str.strip() == "", "material_mostrar"] = df["nombre"]

    df["stock_num"] = pd.to_numeric(df["stock"], errors="coerce").fillna(0)

    if df["stock_num"].sum() == 0 and "stock_actual" in df.columns:
        df["stock_num"] = pd.to_numeric(df["stock_actual"], errors="coerce").fillna(0)

    df["precio_num"] = pd.to_numeric(df["precio_unitario"], errors="coerce").fillna(0)
    df["coste_total_num"] = pd.to_numeric(df["coste_total"], errors="coerce").fillna(0)

    df["valor_total"] = df["coste_total_num"]
    df.loc[df["valor_total"] == 0, "valor_total"] = df["stock_num"] * df["precio_num"]

    if "activo" in df.columns:
        df = df[
            (df["activo"].isna())
            | (df["activo"].astype(str).isin(["1", "True", "true", "Activo", "activo", ""]))
        ]

    return df


def preparar_movimientos_inventario():
    movimientos, tabla = leer_primera_tabla_existente([
        "movimientos_inventario",
        "inventario_movimientos",
        "movimientos_material",
        "historico_inventario"
    ])

    if movimientos.empty:
        return pd.DataFrame()

    columnas_defecto = {
        "fecha": "",
        "fecha_movimiento": "",
        "numero_ot": "",
        "ot": "",
        "orden_trabajo": "",
        "codigo_material": "",
        "material": "",
        "nombre_material": "",
        "tipo": "",
        "movimiento": "",
        "tipo_movimiento": "",
        "cantidad": 0,
        "precio_unitario": 0,
        "coste_total": 0,
        "coste": 0,
        "operario": "",
        "centro": "",
        "observaciones": "",
        "motivo": "",
    }

    for col, valor in columnas_defecto.items():
        if col not in movimientos.columns:
            movimientos[col] = valor

    movimientos["tabla_origen"] = tabla

    movimientos["fecha_mostrar"] = movimientos["fecha"].fillna("").astype(str)
    movimientos.loc[movimientos["fecha_mostrar"].str.strip() == "", "fecha_mostrar"] = movimientos["fecha_movimiento"].fillna("").astype(str)

    movimientos["numero_ot_mostrar"] = movimientos["numero_ot"].fillna("").astype(str)
    movimientos.loc[movimientos["numero_ot_mostrar"].str.strip() == "", "numero_ot_mostrar"] = movimientos["ot"].fillna("").astype(str)
    movimientos.loc[movimientos["numero_ot_mostrar"].str.strip() == "", "numero_ot_mostrar"] = movimientos["orden_trabajo"].fillna("").astype(str)

    movimientos["material_mostrar"] = movimientos["material"].fillna("").astype(str)
    movimientos.loc[movimientos["material_mostrar"].str.strip() == "", "material_mostrar"] = movimientos["nombre_material"].fillna("").astype(str)
    movimientos.loc[movimientos["material_mostrar"].str.strip() == "", "material_mostrar"] = movimientos["codigo_material"].fillna("").astype(str)

    movimientos["tipo_mostrar"] = movimientos["tipo"].fillna("").astype(str)
    movimientos.loc[movimientos["tipo_mostrar"].str.strip() == "", "tipo_mostrar"] = movimientos["movimiento"].fillna("").astype(str)
    movimientos.loc[movimientos["tipo_mostrar"].str.strip() == "", "tipo_mostrar"] = movimientos["tipo_movimiento"].fillna("").astype(str)

    movimientos["observaciones_mostrar"] = movimientos["observaciones"].fillna("").astype(str)
    movimientos.loc[movimientos["observaciones_mostrar"].str.strip() == "", "observaciones_mostrar"] = movimientos["motivo"].fillna("").astype(str)

    movimientos["cantidad_num"] = pd.to_numeric(movimientos["cantidad"], errors="coerce").fillna(0).astype(float)
    movimientos["precio_num"] = pd.to_numeric(movimientos["precio_unitario"], errors="coerce").fillna(0).astype(float)
    movimientos["coste_total_num"] = pd.to_numeric(movimientos["coste_total"], errors="coerce").fillna(0).astype(float)

    if movimientos["coste_total_num"].sum() == 0:
        movimientos["coste_total_num"] = pd.to_numeric(movimientos["coste"], errors="coerce").fillna(0).astype(float)

    inventario = preparar_inventario()

    if not inventario.empty:
        inv = inventario.copy()

        if "codigo" not in inv.columns:
            inv["codigo"] = ""

        inv["codigo"] = inv["codigo"].fillna("").astype(str)
        inv["material_mostrar"] = inv["material_mostrar"].fillna("").astype(str)
        inv["precio_num"] = pd.to_numeric(inv["precio_num"], errors="coerce").fillna(0).astype(float)

        mapa_codigo = inv[["codigo", "precio_num"]].drop_duplicates()
        mapa_codigo = mapa_codigo.rename(columns={"precio_num": "precio_inventario_codigo"})

        movimientos["codigo_material"] = movimientos["codigo_material"].fillna("").astype(str)

        movimientos = movimientos.merge(
            mapa_codigo,
            left_on="codigo_material",
            right_on="codigo",
            how="left"
        )

        movimientos["precio_inventario_codigo"] = pd.to_numeric(
            movimientos["precio_inventario_codigo"],
            errors="coerce"
        ).fillna(0).astype(float)

        movimientos.loc[movimientos["precio_num"] == 0, "precio_num"] = movimientos["precio_inventario_codigo"]

        movimientos = movimientos.drop(columns=["codigo"], errors="ignore")

        mapa_material = inv[["material_mostrar", "precio_num"]].drop_duplicates()
        mapa_material = mapa_material.rename(columns={"precio_num": "precio_inventario_material"})

        movimientos = movimientos.merge(mapa_material, on="material_mostrar", how="left")

        movimientos["precio_inventario_material"] = pd.to_numeric(
            movimientos["precio_inventario_material"],
            errors="coerce"
        ).fillna(0).astype(float)

        movimientos.loc[movimientos["precio_num"] == 0, "precio_num"] = movimientos["precio_inventario_material"]

    movimientos["cantidad_num"] = pd.to_numeric(movimientos["cantidad_num"], errors="coerce").fillna(0).astype(float)
    movimientos["precio_num"] = pd.to_numeric(movimientos["precio_num"], errors="coerce").fillna(0).astype(float)
    movimientos["coste_total_num"] = pd.to_numeric(movimientos["coste_total_num"], errors="coerce").fillna(0).astype(float)

    movimientos.loc[movimientos["coste_total_num"] == 0, "coste_total_num"] = (
        movimientos["cantidad_num"].abs() * movimientos["precio_num"]
    )

    texto_tipo = movimientos["tipo_mostrar"].fillna("").astype(str).str.lower()

    usados = movimientos[
        texto_tipo.str.contains("salida|uso|utilizado|consumo|retirada|descuento", na=False)
        | (movimientos["cantidad_num"] < 0)
    ].copy()

    return usados


def filtrar_inventario_por_centro(df, centro):
    if df.empty:
        return df

    if "centro" in df.columns and df["centro"].fillna("").astype(str).str.strip().any():
        return df[df["centro"].fillna("").astype(str).str.strip() == centro].copy()

    if "ubicacion" in df.columns:
        texto = df["ubicacion"].fillna("").astype(str).str.lower()

        if centro == "Pearson 9":
            return df[texto.str.contains("pearson 9|p9", na=False)].copy()

        if centro == "Pearson 22":
            return df[texto.str.contains("pearson 22|p22", na=False)].copy()

    return df.copy()


def filtrar_movimientos_por_centro(movimientos, ordenes, centro):
    if movimientos.empty:
        return movimientos

    if "centro" in movimientos.columns and movimientos["centro"].fillna("").astype(str).str.strip().any():
        return movimientos[movimientos["centro"].fillna("").astype(str).str.strip() == centro].copy()

    if ordenes.empty or "numero_ot" not in ordenes.columns:
        return movimientos.copy()

    mapa_ot = ordenes[["numero_ot", "centro"]].dropna().copy()
    mapa_ot["numero_ot"] = mapa_ot["numero_ot"].astype(str)
    mapa_ot["centro"] = mapa_ot["centro"].astype(str)

    datos = movimientos.copy()
    datos["numero_ot_mostrar"] = datos["numero_ot_mostrar"].astype(str)

    datos = datos.merge(
        mapa_ot,
        left_on="numero_ot_mostrar",
        right_on="numero_ot",
        how="left",
        suffixes=("", "_orden")
    )

    return datos[datos["centro_orden"] == centro].copy()


def total_inventario_centro(centro):
    inventario = preparar_inventario()
    datos = filtrar_inventario_por_centro(inventario, centro)
    return float(datos["valor_total"].sum()) if not datos.empty else 0.0


def total_utilizado_centro(centro, ordenes):
    movimientos = preparar_movimientos_inventario()
    datos = filtrar_movimientos_por_centro(movimientos, ordenes, centro)
    return float(datos["coste_total_num"].sum()) if not datos.empty else 0.0


def es_cerrada(df):
    return df["estado"].isin(ESTADOS_CERRADOS) | (df["origen_tabla"] == "historico")


def es_esperando_material(df):
    return df["estado"].isin(ESTADOS_MATERIAL)


def es_abierta(df):
    return (
        (df["origen_tabla"] == "activas")
        & (~df["estado"].isin(ESTADOS_CERRADOS))
        & (~df["estado"].isin(ESTADOS_MATERIAL))
    )


def es_en_curso(df):
    return df["estado"].isin(["En curso", "En ejecución"])


def es_pendiente_material(df):
    return df["estado"].isin(["Pendiente material", "Esperando material"])


def filtrar_realizadas_mes(df, origen_busqueda):
    if df.empty:
        return df

    hoy = datetime.today()
    datos = df[es_cerrada(df)].copy()

    if datos.empty:
        return datos

    fecha_ref = datos["fecha_cierre_dt"]

    if fecha_ref.isna().all():
        fecha_ref = datos["fecha_dt"]

    datos = datos[
        (fecha_ref.dt.month == hoy.month)
        & (fecha_ref.dt.year == hoy.year)
    ]

    texto = (
        datos["origen"].fillna("").astype(str)
        + " "
        + datos["area"].fillna("").astype(str)
        + " "
        + datos["descripcion"].fillna("").astype(str)
    ).str.lower()

    return datos[texto.str.contains(origen_busqueda, na=False)]


def obtener_df_tarjeta(df, centro, tipo):
    datos = df[df["centro"] == centro].copy()

    if tipo == "abiertas":
        return datos[es_abierta(datos)]

    if tipo == "en_curso":
        return datos[es_en_curso(datos)]

    if tipo == "material":
        return datos[es_pendiente_material(datos)]

    if tipo == "cerradas":
        return datos[es_cerrada(datos)]

    if tipo == "legionella_mes":
        return filtrar_realizadas_mes(datos, "legionella")

    if tipo == "preventivas_mes":
        return filtrar_realizadas_mes(datos, "preventivo")

    return pd.DataFrame()


def contar(df, centro, tipo):
    return len(obtener_df_tarjeta(df, centro, tipo))


def euros(valor):
    try:
        return f"{float(valor):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 €"


def normalizar_busqueda(texto):
    texto = str(texto or "").lower().strip()

    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )

    texto = texto.replace(".", " ")
    texto = texto.replace("-", " ")
    texto = texto.replace("_", " ")
    texto = texto.replace("/", " ")

    return " ".join(texto.split())


def coincide_busqueda_flexible(busqueda, objetivo):
    busqueda = normalizar_busqueda(busqueda)
    objetivo = normalizar_busqueda(objetivo)

    if not busqueda:
        return True

    palabras = busqueda.split()

    return all(palabra in objetivo for palabra in palabras)


def buscador_dataframe(df, key, placeholder="Buscar..."):
    if df.empty:
        return df

    busqueda = st.text_input("🔎 Buscador", placeholder=placeholder, key=key)

    if not busqueda:
        return df

    datos = df.copy()
    texto_general = datos.astype(str).fillna("").agg(" ".join, axis=1)

    mascara_texto = texto_general.apply(
        lambda texto: coincide_busqueda_flexible(busqueda, texto)
    )

    mascara_fecha = pd.Series(False, index=datos.index)

    columnas_fecha = [col for col in datos.columns if "fecha" in str(col).lower()]

    for col in columnas_fecha:
        fechas = pd.to_datetime(datos[col], errors="coerce")

        formatos_fecha = pd.DataFrame({
            "fecha_iso": fechas.dt.strftime("%Y-%m-%d"),
            "fecha_es": fechas.dt.strftime("%d/%m/%Y"),
            "fecha_mes_iso": fechas.dt.strftime("%Y-%m"),
            "fecha_mes_es": fechas.dt.strftime("%m/%Y"),
            "fecha_dia_mes": fechas.dt.strftime("%d/%m"),
            "fecha_anio": fechas.dt.strftime("%Y"),
        })

        texto_fechas = formatos_fecha.fillna("").agg(" ".join, axis=1)

        mascara_columna = texto_fechas.apply(
            lambda texto: coincide_busqueda_flexible(busqueda, texto)
        )

        mascara_fecha = mascara_fecha | mascara_columna

    return datos[mascara_texto | mascara_fecha]


def seleccionar_centro(centro):
    st.session_state["gerencia_centro"] = centro
    st.session_state["gerencia_detalle"] = None
    st.rerun()


def seleccionar_detalle(centro, tipo, titulo):
    st.session_state["gerencia_detalle"] = {
        "centro": centro,
        "tipo": tipo,
        "titulo": titulo
    }
    st.rerun()


def boton_tarjeta(titulo, cantidad, centro, tipo, icono):
    texto = f"{icono} {cantidad}\n{titulo}"

    if st.button(texto, key=f"gerencia_{centro}_{tipo}", use_container_width=True):
        seleccionar_detalle(centro, tipo, titulo)


def boton_tarjeta_dinero(titulo, importe, centro, tipo, icono):
    texto = f"{icono} {euros(importe)}\n{titulo}"

    if st.button(texto, key=f"gerencia_{centro}_{tipo}", use_container_width=True):
        seleccionar_detalle(centro, tipo, titulo)


def mostrar_selector_centros():
    st.markdown(
        "<div class='gerencia-card-info'>Selecciona un centro para ver su resumen.</div>",
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("🏫 Pearson 9", use_container_width=True, key="btn_gerencia_p9"):
            seleccionar_centro("Pearson 9")

    with c2:
        if st.button("🏫 Pearson 22", use_container_width=True, key="btn_gerencia_p22"):
            seleccionar_centro("Pearson 22")

def evaluar_estado_centro(df, centro):
    abiertas = contar(df, centro, "abiertas")
    material = contar(df, centro, "material")
    legionella = contar(df, centro, "legionella_mes")
    preventivas = contar(df, centro, "preventivas_mes")

    if abiertas >= 20 or material >= 5:
        return "rojo", 55, "Existen incidencias que requieren atención prioritaria."

    if abiertas >= 8 or material > 0:
        return "amarillo", 76, "Hay actuaciones pendientes que conviene seguir."

    return "verde", 94, "Estado general correcto."


def obtener_riesgos_criticos(df, centro):
    if df.empty:
        return pd.DataFrame()

    datos = obtener_df_tarjeta(df, centro, "abiertas")

    if datos.empty:
        return datos

    texto = (
        datos["espacio"].fillna("").astype(str) + " " +
        datos["area"].fillna("").astype(str) + " " +
        datos["descripcion"].fillna("").astype(str) + " " +
        datos["prioridad"].fillna("").astype(str)
    ).str.lower()

    palabras_criticas = (
        "caldera|acs|legionella|cuadro eléctrico|electricidad|fuga|gas|"
        "frigorífica|congelador|cámara|alarma|incendio|extintor|bie|"
        "cristal roto|desprendido|riesgo|urgente"
    )

    return datos[
        texto.str.contains(palabras_criticas, na=False)
        | datos["prioridad"].fillna("").astype(str).str.lower().str.contains("urgente|alta", na=False)
    ].head(8)


def mostrar_resumen_ejecutivo(df, centro):
    color, porcentaje, mensaje = evaluar_estado_centro(df, centro)

    if color == "verde":
        st.success(f"🟢 Estado general del centro · {porcentaje}%\n\n{mensaje}")
    elif color == "amarillo":
        st.warning(f"🟠 Estado general del centro · {porcentaje}%\n\n{mensaje}")
    else:
        st.error(f"🔴 Estado general del centro · {porcentaje}%\n\n{mensaje}")

    riesgos = obtener_riesgos_criticos(df, centro)

    st.markdown("### 🔴 Riesgos críticos")

    if riesgos.empty:
        st.success("No hay riesgos críticos detectados.")
    else:
        for _, row in riesgos.iterrows():
            st.markdown(
                f"**{row.get('espacio', '-') or '-'}** · "
                f"`{row.get('numero_ot', '-') or '-'}`"
            )
            st.caption(row.get("descripcion", "") or "")

    st.markdown("### 🎯 Actuaciones recomendadas hoy")

    abiertas = obtener_df_tarjeta(df, centro, "abiertas").head(5)

    if abiertas.empty:
        st.success("No hay actuaciones pendientes prioritarias.")
    else:
        for i, (_, row) in enumerate(abiertas.iterrows(), start=1):
            st.markdown(
                f"{i}. **{row.get('espacio', '-') or '-'}** · "
                f"{row.get('descripcion', '-') or '-'}"
            )


def _serie_mensual_base():
    return pd.DataFrame({
        "periodo": [periodo for periodo, _ in MESES_CURSO_2026_2027],
        "mes": [etiqueta for _, etiqueta in MESES_CURSO_2026_2027],
    })


def _filtrar_curso_2026_2027(df, columna_fecha):
    if df.empty or columna_fecha not in df.columns:
        return pd.DataFrame()

    datos = df.copy()
    datos[columna_fecha] = pd.to_datetime(datos[columna_fecha], errors="coerce")

    inicio = pd.Timestamp(FECHA_INICIO_EVOLUCION)
    fin_exclusivo = pd.Timestamp(FECHA_FIN_EVOLUCION) + pd.Timedelta(days=1)

    return datos[
        (datos[columna_fecha] >= inicio)
        & (datos[columna_fecha] < fin_exclusivo)
    ].copy()


def _es_preventivo_df(df):
    texto = (
        df["origen"].fillna("").astype(str)
        + " "
        + df["descripcion"].fillna("").astype(str)
        + " "
        + df["area"].fillna("").astype(str)
    ).str.lower()

    return texto.str.contains("preventivo", na=False)


def _es_incidencia_df(df):
    texto = (
        df["origen"].fillna("").astype(str)
        + " "
        + df["descripcion"].fillna("").astype(str)
        + " "
        + df["area"].fillna("").astype(str)
    ).str.lower()

    excluidas = texto.str.contains("preventivo|legionella|verano", na=False)
    return ~excluidas


def obtener_evolucion_mensual(df, centro):
    base = _serie_mensual_base()

    if df.empty:
        base["Preventivos realizados"] = 0
        base["Incidencias creadas"] = 0
        return base

    datos = df[df["centro"] == centro].copy()

    preventivos = datos[es_cerrada(datos) & _es_preventivo_df(datos)].copy()
    preventivos = _filtrar_curso_2026_2027(preventivos, "fecha_cierre_dt")

    if not preventivos.empty:
        preventivos["periodo"] = preventivos["fecha_cierre_dt"].dt.to_period("M").astype(str)
        preventivos_mes = (
            preventivos.groupby("periodo")
            .size()
            .rename("Preventivos realizados")
            .reset_index()
        )
    else:
        preventivos_mes = pd.DataFrame(columns=["periodo", "Preventivos realizados"])

    incidencias = datos[_es_incidencia_df(datos)].copy()
    incidencias = _filtrar_curso_2026_2027(incidencias, "fecha_dt")

    if not incidencias.empty:
        incidencias["periodo"] = incidencias["fecha_dt"].dt.to_period("M").astype(str)
        incidencias_mes = (
            incidencias.groupby("periodo")
            .size()
            .rename("Incidencias creadas")
            .reset_index()
        )
    else:
        incidencias_mes = pd.DataFrame(columns=["periodo", "Incidencias creadas"])

    evolucion = base.merge(preventivos_mes, on="periodo", how="left").merge(
        incidencias_mes, on="periodo", how="left"
    )

    evolucion["Preventivos realizados"] = pd.to_numeric(
        evolucion["Preventivos realizados"], errors="coerce"
    ).fillna(0).astype(int)

    evolucion["Incidencias creadas"] = pd.to_numeric(
        evolucion["Incidencias creadas"], errors="coerce"
    ).fillna(0).astype(int)

    return evolucion


def calcular_indice_prevencion(evolucion):
    if evolucion.empty:
        return 0

    preventivos = int(evolucion["Preventivos realizados"].sum())
    incidencias = int(evolucion["Incidencias creadas"].sum())

    if preventivos == 0 and incidencias == 0:
        return 0

    valor = (preventivos / max(preventivos + incidencias, 1)) * 100
    return max(0, min(100, round(valor)))


def construir_conclusion_evolucion(evolucion):
    con_datos = evolucion[
        (evolucion["Preventivos realizados"] > 0)
        | (evolucion["Incidencias creadas"] > 0)
    ].copy()

    if con_datos.empty:
        return (
            "La evolución comenzará a registrarse en septiembre de 2026. "
            "A medida que avance el curso, este gráfico mostrará si el aumento "
            "del mantenimiento preventivo se acompaña de una reducción de incidencias."
        )

    if len(con_datos) == 1:
        fila = con_datos.iloc[-1]
        return (
            f"En {fila['mes']} se han realizado "
            f"{int(fila['Preventivos realizados'])} preventivos y se han registrado "
            f"{int(fila['Incidencias creadas'])} incidencias. La tendencia será más "
            "representativa cuando existan varios meses consecutivos."
        )

    actual = con_datos.iloc[-1]
    anterior = con_datos.iloc[-2]

    cambio_prev = int(actual["Preventivos realizados"] - anterior["Preventivos realizados"])
    cambio_inc = int(actual["Incidencias creadas"] - anterior["Incidencias creadas"])

    if cambio_prev > 0 and cambio_inc < 0:
        return (
            f"En {actual['mes']} aumentaron los preventivos en {cambio_prev} y las "
            f"incidencias disminuyeron en {abs(cambio_inc)} respecto al mes anterior. "
            "La evolución es favorable."
        )

    if cambio_prev < 0 and cambio_inc > 0:
        return (
            f"En {actual['mes']} descendieron los preventivos y aumentaron las "
            "incidencias. Conviene reforzar la planificación preventiva."
        )

    if cambio_inc < 0:
        return (
            f"En {actual['mes']} las incidencias disminuyeron en "
            f"{abs(cambio_inc)} respecto al mes anterior."
        )

    return (
        f"En {actual['mes']} se realizaron {int(actual['Preventivos realizados'])} "
        f"preventivos y se registraron {int(actual['Incidencias creadas'])} incidencias."
    )


def mostrar_evolucion_mantenimiento(df, centro):
    st.markdown("""
    <div class="gerencia-evolucion-box">
        <div class="gerencia-evolucion-title">📈 Evolución del mantenimiento</div>
        <div class="gerencia-evolucion-subtitle">
            Curso 2026/2027 · Preventivos realizados e incidencias creadas
        </div>
    </div>
    """, unsafe_allow_html=True)

    evolucion = obtener_evolucion_mensual(df, centro)

    total_preventivos = int(evolucion["Preventivos realizados"].sum())
    total_incidencias = int(evolucion["Incidencias creadas"].sum())
    indice = calcular_indice_prevencion(evolucion)

    meses_con_datos = evolucion[
        (evolucion["Preventivos realizados"] > 0)
        | (evolucion["Incidencias creadas"] > 0)
    ]

    if not meses_con_datos.empty:
        ultimo = meses_con_datos.iloc[-1]
        ultimo_mes = str(ultimo["mes"])
        prev_ultimo = int(ultimo["Preventivos realizados"])
        inc_ultimo = int(ultimo["Incidencias creadas"])
    else:
        ultimo_mes = "Sin datos todavía"
        prev_ultimo = 0
        inc_ultimo = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🛠️ Preventivos curso", total_preventivos)
    c2.metric("⚠️ Incidencias curso", total_incidencias)
    c3.metric("🛡️ Índice prevención", f"{indice}%")
    c4.metric(
        f"📅 {ultimo_mes}",
        f"{prev_ultimo} / {inc_ultimo}",
        help="Preventivos realizados / incidencias creadas"
    )

    grafico = evolucion.set_index("mes")[
        ["Preventivos realizados", "Incidencias creadas"]
    ]

    st.line_chart(grafico, use_container_width=True, height=360)

    st.caption(
        "El objetivo es observar si el aumento de preventivos realizados "
        "se acompaña de una disminución de las incidencias creadas."
    )

    conclusion = construir_conclusion_evolucion(evolucion)
    st.markdown("#### 💬 Lectura de la evolución")

    if total_preventivos == 0 and total_incidencias == 0:
        st.info(conclusion)
    elif len(meses_con_datos) >= 2:
        actual = meses_con_datos.iloc[-1]
        anterior = meses_con_datos.iloc[-2]
        favorable = (
            int(actual["Preventivos realizados"]) >= int(anterior["Preventivos realizados"])
            and int(actual["Incidencias creadas"]) <= int(anterior["Incidencias creadas"])
        )
        if favorable:
            st.success(conclusion)
        else:
            st.warning(conclusion)
    else:
        st.info(conclusion)



def mostrar_menu_centro(df, centro):
    st.markdown(f"<div class='gerencia-section-title'>🏫 {centro}</div>", unsafe_allow_html=True)

    if st.button("⬅️ Volver a centros", use_container_width=True, key="volver_centros_gerencia"):
        volver_a_centros()

    mostrar_resumen_ejecutivo(df, centro)

    mostrar_evolucion_mantenimiento(df, centro)

    with st.expander("📊 Indicadores de mantenimiento", expanded=False):
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            boton_tarjeta("Órdenes abiertas", contar(df, centro, "abiertas"), centro, "abiertas", "📂")

        with c2:
            boton_tarjeta("En curso", contar(df, centro, "en_curso"), centro, "en_curso", "🟡")

        with c3:
            boton_tarjeta("Pendiente material", contar(df, centro, "material"), centro, "material", "📦")

        with c4:
            boton_tarjeta("Órdenes cerradas", contar(df, centro, "cerradas"), centro, "cerradas", "✅")

        c5, c6 = st.columns(2)

        with c5:
            boton_tarjeta("Legionella este mes", contar(df, centro, "legionella_mes"), centro, "legionella_mes", "💧")

        with c6:
            boton_tarjeta("Preventivas este mes", contar(df, centro, "preventivas_mes"), centro, "preventivas_mes", "🛠️")

    with st.expander("🌳 Ver incidencias por centro", expanded=False):
        st.caption("Vista solo lectura para gerencia.")
        mostrar_arbol_gerencia()

    with st.expander("💶 Recursos e inventario", expanded=False):
        total_inv = total_inventario_centro(centro)
        total_usado = total_utilizado_centro(centro, df)

        c7, c8 = st.columns(2)

        with c7:
            boton_tarjeta_dinero("Total inventario", total_inv, centro, "inventario_total", "💰")

        with c8:
            boton_tarjeta_dinero("Material utilizado", total_usado, centro, "inventario_utilizado", "📉")


def mostrar_detalle_ordenes(df, centro, tipo, titulo):
    datos = obtener_df_tarjeta(df, centro, tipo)

    if datos.empty:
        st.info("No hay registros para mostrar.")
        return

    columnas = [
        "numero_ot",
        "fecha_creacion",
        "fecha_cierre",
        "centro",
        "edificio",
        "espacio",
        "descripcion",
        "estado",
        "operario",
        "solicitante",
        "origen",
        "area",
        "prioridad",
    ]

    columnas = [c for c in columnas if c in datos.columns]

    datos = buscador_dataframe(
        datos,
        key=f"buscador_gerencia_{centro}_{tipo}",
        placeholder="Buscar por OT, operario, aula, descripción, estado o fecha..."
    )

    st.dataframe(datos[columnas], use_container_width=True, hide_index=True)


def mostrar_detalle_inventario_total(centro):
    inventario = preparar_inventario()
    datos = filtrar_inventario_por_centro(inventario, centro)

    if datos.empty:
        st.info("No hay inventario registrado para mostrar.")
        return

    st.metric("💰 Total inventario", euros(datos["valor_total"].sum()))

    datos = buscador_dataframe(
        datos,
        key=f"buscador_inv_gerencia_{centro}",
        placeholder="Buscar material, código, ubicación o proveedor..."
    )

    for _, row in datos.iterrows():
        id_material = row.get("id", None)
        codigo = row.get("codigo", "")
        material = row.get("material_mostrar", "")
        categoria = row.get("categoria", "")
        stock = row.get("stock_num", 0)
        precio = row.get("precio_num", 0)
        valor = row.get("valor_total", 0)
        ubicacion = row.get("ubicacion", "")
        fecha_compra = row.get("fecha_compra", "")
        foto = row.get("foto", "")

        foto_data = obtener_foto_inventario_por_id(id_material)

        with st.expander(f"📦 {codigo} · {material} · Stock: {stock}", expanded=False):
            st.markdown(f"### {material}")

            st.caption(f"🏷️ {categoria or '-'} · 📍 {ubicacion or '-'}")
            st.markdown(f"**Precio unitario:** {euros(precio)}")
            st.markdown(f"**Valor inventario:** {euros(valor)}")

            if fecha_compra:
                st.caption(f"📅 {fecha_compra}")

            if foto_data:
                try:
                    st.image(bytes(foto_data), width=220)
                except Exception:
                    st.caption("Foto no disponible.")

            elif foto:
                try:
                    st.image(foto, width=220)
                except Exception:
                    st.caption("Foto no disponible.")


def mostrar_detalle_inventario_utilizado(centro, ordenes):
    movimientos = preparar_movimientos_inventario()
    datos = filtrar_movimientos_por_centro(movimientos, ordenes, centro)

    if datos.empty:
        st.info("No hay material utilizado registrado para mostrar.")
        return

    columnas = [
        "fecha_mostrar",
        "numero_ot_mostrar",
        "material_mostrar",
        "cantidad_num",
        "precio_num",
        "coste_total_num",
        "operario",
        "observaciones_mostrar",
    ]

    columnas = [c for c in columnas if c in datos.columns]

    st.metric("📉 Total material utilizado", euros(datos["coste_total_num"].sum()))

    st.dataframe(datos[columnas], use_container_width=True, hide_index=True)


def mostrar_detalle(df):
    detalle = st.session_state.get("gerencia_detalle")

    if not detalle:
        return

    centro = detalle.get("centro")
    tipo = detalle.get("tipo")
    titulo = detalle.get("titulo")

    st.markdown(
        f"<div class='gerencia-section-title'>📋 {titulo} · {centro}</div>",
        unsafe_allow_html=True
    )

    if st.button("⬅️ Volver al resumen del centro", use_container_width=True, key="volver_menu_centro_gerencia"):
        volver_a_menu_centro()

    if tipo == "inventario_total":
        mostrar_detalle_inventario_total(centro)
        return

    if tipo == "inventario_utilizado":
        mostrar_detalle_inventario_utilizado(centro, df)
        return

    mostrar_detalle_ordenes(df, centro, tipo, titulo)



# =====================================================
# COLEGIO VIVO · GERENCIA
# =====================================================

EDIFICIOS_GERENCIA = {
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


ALIAS_EDIFICIOS_GERENCIA = {
    "Infantil / Primaria": ["infantil primaria", "infantil/primaria", "edif infantil primaria", "edificio infantil primaria"],
    "Llar": ["llar", "anexo", "edif llar", "edificio llar"],
    "Edificio A": ["edificio a", "edif a", "bloque a"],
    "Edificio B": ["edificio b", "edif b", "bloque b"],
    "Edificio C": ["edificio c", "edif c", "bloque c"],
}


def aplicar_estilo_colegio_vivo():
    st.markdown("""
    <style>
    .cv-hero {
        display:flex; align-items:center; justify-content:space-between;
        gap:14px; padding:12px 16px; margin:0 0 10px 0;
        background:linear-gradient(135deg,#0f172a 0%,#1d4ed8 100%);
        border-radius:17px; color:white;
        box-shadow:0 7px 20px rgba(15,23,42,.13);
    }
    .cv-title {font-size:25px;font-weight:900;line-height:1.05}
    .cv-subtitle {font-size:12px;font-weight:600;opacity:.88;margin-top:3px}
    .cv-status {padding:8px 12px;border-radius:12px;background:rgba(255,255,255,.14);font-size:13px;font-weight:800}
    .cv-centro-title {font-size:14px;font-weight:900;color:#0f172a;margin:7px 0 5px}
    .cv-building {
        border:1px solid #dbe3ef;border-radius:15px;padding:8px;
        background:#f8fafc;box-shadow:0 4px 12px rgba(15,23,42,.05);
        margin-bottom:8px;
    }
    .cv-building-title {
        text-align:center;font-size:14px;font-weight:900;color:#1e3a8a;
        background:#fff;border:1px solid #e2e8f0;border-radius:10px;
        padding:6px 8px;margin-bottom:5px;
    }
    .cv-floor-note {font-size:11px;color:#64748b;text-align:center;margin-top:4px}
    .cv-panel-title {font-size:20px;font-weight:900;color:#0f172a;margin-bottom:1px}
    .cv-panel-subtitle {font-size:12px;color:#64748b;font-weight:650;margin-bottom:8px}
    .cv-priority {
        border:1px solid #fecaca;background:#fff7f7;border-radius:13px;
        padding:10px 12px;margin-top:4px;
    }
    .cv-priority-title {font-size:16px;font-weight:900;color:#991b1b}
    .cv-priority-text {font-size:12px;color:#334155;margin-top:3px}
    .cv-kpi {
        border:1px solid #e2e8f0;border-radius:12px;padding:8px 10px;background:#f8fafc;
        min-height:72px;
    }
    .cv-kpi-label {font-size:11px;color:#64748b;font-weight:700}
    .cv-kpi-value {font-size:23px;color:#0f172a;font-weight:900;line-height:1.1;margin-top:3px}
    .cv-footer-card {
        border:1px solid #e2e8f0;border-radius:13px;padding:9px 10px;background:#fff;min-height:70px
    }
    .cv-footer-label {font-size:11px;font-weight:800;color:#475569}
    .cv-footer-value {font-size:17px;font-weight:900;color:#0f172a;margin-top:4px;line-height:1.15}
    div[data-testid="stButton"] > button {
        height:auto !important; border-radius:9px !important;
        padding:6px 8px !important; font-size:12px !important; line-height:1.08 !important;
        white-space:pre-line !important; box-shadow:none !important;
    }
    .cv-building div[data-testid="stButton"] > button {
        min-height:38px !important; margin:0 !important;
        border-radius:7px !important; font-weight:800 !important;
    }
    div[data-testid="stMetric"] {
        background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:7px 9px
    }
    div[data-testid="stDataFrame"] {border-radius:12px;overflow:hidden}
    .block-container {padding-top:.65rem;padding-bottom:.75rem;max-width:1700px}
    @media (max-width: 900px) {
        .cv-hero {display:block}.cv-status{margin-top:8px}.cv-title{font-size:22px}
    }
    </style>
    """, unsafe_allow_html=True)

def _normalizar_planta(valor):
    texto = normalizar_busqueda(valor)
    if not texto:
        return ""
    if "terrado" in texto or "cubierta" in texto:
        return "terrado"
    for numero in range(0, 10):
        if texto in {str(numero), f"p {numero}", f"planta {numero}", f"p{numero}"}:
            return f"planta {numero}"
        if f"planta {numero}" in texto or f"p {numero}" in texto:
            return f"planta {numero}"
    return texto


def _coincide_edificio(valor, edificio):
    texto = normalizar_busqueda(valor)
    if not texto:
        return False
    alias = ALIAS_EDIFICIOS_GERENCIA.get(edificio, [edificio])
    return any(normalizar_busqueda(a) in texto or texto in normalizar_busqueda(a) for a in alias)


def filtrar_por_ubicacion_gerencia(df, centro, edificio, planta):
    if df.empty:
        return df.copy()
    datos = df[df["centro"].fillna("").astype(str).str.strip() == centro].copy()
    if datos.empty:
        return datos
    datos = datos[datos["edificio"].fillna("").astype(str).apply(lambda x: _coincide_edificio(x, edificio))].copy()
    if datos.empty:
        return datos
    planta_obj = _normalizar_planta(planta)
    datos["_planta_norm"] = datos["planta"].fillna("").astype(str).apply(_normalizar_planta)
    # Compatibilidad con órdenes antiguas sin planta: intentar localizarla en espacio/descripcion.
    vacias = datos["_planta_norm"].eq("")
    if vacias.any():
        apoyo = (
            datos.loc[vacias, "espacio"].fillna("").astype(str) + " " +
            datos.loc[vacias, "descripcion"].fillna("").astype(str)
        ).apply(_normalizar_planta)
        datos.loc[vacias, "_planta_norm"] = apoyo
    return datos[datos["_planta_norm"] == planta_obj].copy()


def _activas_gerencia(datos):
    if datos.empty:
        return datos
    return datos[(datos["origen_tabla"] == "activas") & (~datos["estado"].isin(ESTADOS_CERRADOS))].copy()


def _urgentes_gerencia(datos):
    if datos.empty:
        return datos
    texto = (
        datos["prioridad"].fillna("").astype(str) + " " +
        datos["area"].fillna("").astype(str) + " " +
        datos["descripcion"].fillna("").astype(str)
    ).str.lower()
    return datos[
        texto.str.contains("urgente|alta|fuga|gas|incendio|cuadro electr|legionella|acs|riesgo", na=False)
    ].copy()


def _estado_planta(df, centro, edificio, planta):
    datos = filtrar_por_ubicacion_gerencia(df, centro, edificio, planta)
    activas = _activas_gerencia(datos)
    urgentes = _urgentes_gerencia(activas)
    cantidad = len(activas)
    if len(urgentes) > 0:
        return "🔴", cantidad, 3
    if cantidad >= 3:
        return "🟠", cantidad, 2
    if cantidad > 0:
        return "🟡", cantidad, 1
    return "🟢", 0, 0


def _seleccion_mas_relevante(df):
    mejor = ("Pearson 22", "Infantil / Primaria", "Planta 2")
    mejor_peso = -1
    for centro, edificios in EDIFICIOS_GERENCIA.items():
        for edificio, plantas in edificios.items():
            for planta in plantas:
                _, cantidad, nivel = _estado_planta(df, centro, edificio, planta)
                peso = nivel * 1000 + cantidad
                if peso > mejor_peso:
                    mejor = (centro, edificio, planta)
                    mejor_peso = peso
    return mejor


def _iniciar_seleccion_colegio_vivo(df):
    claves = ["gerencia_cv_centro", "gerencia_cv_edificio", "gerencia_cv_planta"]
    if not all(st.session_state.get(k) for k in claves):
        centro, edificio, planta = _seleccion_mas_relevante(df)
        st.session_state["gerencia_cv_centro"] = centro
        st.session_state["gerencia_cv_edificio"] = edificio
        st.session_state["gerencia_cv_planta"] = planta


def _seleccionar_planta_cv(centro, edificio, planta):
    st.session_state["gerencia_cv_centro"] = centro
    st.session_state["gerencia_cv_edificio"] = edificio
    st.session_state["gerencia_cv_planta"] = planta


def _estado_centro_cv(df, centro):
    max_nivel = 0
    total = 0
    for edificio, plantas in EDIFICIOS_GERENCIA[centro].items():
        for planta in plantas:
            _, cantidad, nivel = _estado_planta(df, centro, edificio, planta)
            total += cantidad
            max_nivel = max(max_nivel, nivel)
    if max_nivel >= 3:
        return "🔴", "Atención prioritaria", total
    if max_nivel >= 1:
        return "🟡", "Seguimiento", total
    return "🟢", "Bajo control", total


def _tarjeta_html(label, value):
    st.markdown(
        f"<div class='cv-kpi'><div class='cv-kpi-label'>{label}</div>"
        f"<div class='cv-kpi-value'>{value}</div></div>",
        unsafe_allow_html=True,
    )


def mostrar_edificio_cv(df, centro, edificio, plantas):
    st.markdown(
        f"<div class='cv-building'><div class='cv-building-title'>{edificio}</div>",
        unsafe_allow_html=True,
    )

    seleccionado = (
        st.session_state.get("gerencia_cv_centro"),
        st.session_state.get("gerencia_cv_edificio"),
        st.session_state.get("gerencia_cv_planta"),
    )

    # Plantas apiladas: el conjunto se lee visualmente como un edificio.
    for planta in plantas:
        icono, cantidad, nivel = _estado_planta(df, centro, edificio, planta)
        etiqueta = planta.replace("Planta ", "P")
        es_seleccionada = (centro, edificio, planta) == seleccionado

        if cantidad:
            texto = f"{icono}  {etiqueta}   ·   {cantidad} activa" + ("s" if cantidad != 1 else "")
        else:
            texto = f"{icono}  {etiqueta}   ·   Sin incidencias"

        st.button(
            texto,
            key=f"cv_{centro}_{edificio}_{planta}",
            use_container_width=True,
            on_click=_seleccionar_planta_cv,
            args=(centro, edificio, planta),
            type="primary" if es_seleccionada else "secondary",
        )

    st.markdown("</div>", unsafe_allow_html=True)

def _cerradas_mes_planta(datos):
    if datos.empty:
        return datos
    cerradas = datos[es_cerrada(datos)].copy()
    if cerradas.empty:
        return cerradas
    fecha_ref = cerradas["fecha_cierre_dt"].copy()
    fecha_ref = fecha_ref.where(fecha_ref.notna(), cerradas["fecha_dt"])
    hoy = pd.Timestamp.today()
    return cerradas[(fecha_ref.dt.month == hoy.month) & (fecha_ref.dt.year == hoy.year)].copy()


def _mostrar_areas_cv(activas):
    if activas.empty:
        st.success("Sin incidencias activas en esta planta.")
        return
    areas = activas["area"].fillna("Sin área").replace("", "Sin área").value_counts().head(5)
    maximo = max(int(areas.max()), 1)
    for area, cantidad in areas.items():
        porcentaje = max(8, int((int(cantidad) / maximo) * 100))
        st.markdown(
            f"<div style='display:grid;grid-template-columns:110px 1fr 28px;gap:8px;align-items:center;margin:5px 0'>"
            f"<span style='font-size:12px;font-weight:700;color:#334155'>{area}</span>"
            f"<div style='height:8px;background:#e2e8f0;border-radius:999px;overflow:hidden'>"
            f"<div style='height:8px;width:{porcentaje}%;background:#3b82f6;border-radius:999px'></div></div>"
            f"<strong style='font-size:12px'>{int(cantidad)}</strong></div>",
            unsafe_allow_html=True,
        )


def _limpiar_descripcion_gerencia(descripcion):
    texto = str(descripcion or "").strip()
    texto = re.sub(r"^\s*\[CORRECTIVA DESDE INVENTARIO\]\s*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"^\s*OT\s+origen\s*:\s*[^\n.]+[.\s]*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto or "Actuación pendiente"


def mostrar_panel_planta_cv(df):
    centro = st.session_state["gerencia_cv_centro"]
    edificio = st.session_state["gerencia_cv_edificio"]
    planta = st.session_state["gerencia_cv_planta"]
    datos = filtrar_por_ubicacion_gerencia(df, centro, edificio, planta)
    activas = _activas_gerencia(datos)
    urgentes = _urgentes_gerencia(activas)
    en_curso = activas[activas["estado"].isin(["En curso", "En ejecución"])] if not activas.empty else activas
    cerradas_mes = _cerradas_mes_planta(datos)

    st.markdown(
        f"<div class='cv-panel-title'>📍 {centro} · {edificio} · {planta}</div>"
        f"<div class='cv-panel-subtitle'>Situación operativa de la planta seleccionada</div>",
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1: _tarjeta_html("Pendientes", len(activas))
    with k2: _tarjeta_html("Urgentes / altas", len(urgentes))
    with k3: _tarjeta_html("En curso", len(en_curso))
    with k4: _tarjeta_html("Finalizadas mes", len(cerradas_mes))

    c_areas, c_prioridad = st.columns([1.05, 1])
    with c_areas:
        st.markdown("#### Por áreas")
        _mostrar_areas_cv(activas)
    with c_prioridad:
        st.markdown("#### Actuación prioritaria")
        if activas.empty:
            st.success("No hay actuaciones pendientes.")
        else:
            candidatos = urgentes if not urgentes.empty else activas
            candidatos = candidatos.sort_values(["fecha_dt"], ascending=True, na_position="last")
            fila = candidatos.iloc[0]
            descripcion_limpia = _limpiar_descripcion_gerencia(
                fila.get("descripcion", "")
            )
            st.markdown(
                f"<div class='cv-priority'><div class='cv-priority-title'>"
                f"{descripcion_limpia}</div>"
                f"<div class='cv-priority-text'>📍 {fila.get('espacio','') or planta}<br>"
                f"{fila.get('prioridad','') or 'Prioridad pendiente de valorar'} · "
                f"{fila.get('estado','') or 'Pendiente'} · "
                f"{fila.get('numero_ot','') or ''}</div></div>",
                unsafe_allow_html=True,
            )

    if not activas.empty:
        with st.expander(
            f"Ver {len(activas)} incidencia" + ("s" if len(activas) != 1 else "") + " de esta planta",
            expanded=False,
        ):
            columnas = ["numero_ot", "descripcion", "area", "prioridad", "estado"]
            vista = activas.sort_values(
                "fecha_dt", ascending=True, na_position="last"
            ).head(10)[columnas].copy()
            vista["descripcion"] = vista["descripcion"].apply(_limpiar_descripcion_gerencia)
            vista.columns = ["OT", "Descripción", "Área", "Prioridad", "Estado"]
            st.dataframe(vista, use_container_width=True, hide_index=True, height=245)


def _cumplimiento_simple(df, centro, palabra):
    datos = df[df["centro"] == centro].copy()
    if datos.empty:
        return 100
    texto = (datos["origen"].fillna("").astype(str) + " " + datos["area"].fillna("").astype(str) + " " + datos["descripcion"].fillna("").astype(str)).str.lower()
    objetivo = datos[texto.str.contains(palabra, na=False)].copy()
    if objetivo.empty:
        return 100
    total = len(objetivo)
    cerradas = len(objetivo[es_cerrada(objetivo)])
    return round((cerradas / max(total, 1)) * 100)


def mostrar_resumen_inferior_cv(df):
    centro = st.session_state["gerencia_cv_centro"]
    color, porcentaje, mensaje = evaluar_estado_centro(df, centro)
    preventivo = _cumplimiento_simple(df, centro, "preventivo")
    legionella = _cumplimiento_simple(df, centro, "legionella")
    inventario = preparar_inventario()
    inv_centro = filtrar_inventario_por_centro(inventario, centro)
    stock_bajo = 0
    if not inv_centro.empty and "stock_minimo" in inv_centro.columns:
        minimo = pd.to_numeric(inv_centro["stock_minimo"], errors="coerce").fillna(0)
        stock_bajo = int((inv_centro["stock_num"] <= minimo).sum())

    cols = st.columns(4)
    valores = [
        ("Estado general", f"{porcentaje}% · {mensaje}"),
        ("Preventivo", f"{preventivo}% cumplido"),
        ("Legionella", f"{legionella}% cumplido"),
        ("Inventario", "Correcto" if stock_bajo == 0 else f"{stock_bajo} alertas"),
    ]
    for col, (label, value) in zip(cols, valores):
        with col:
            st.markdown(
                f"<div class='cv-footer-card'><div class='cv-footer-label'>{label}</div>"
                f"<div class='cv-footer-value'>{value}</div></div>",
                unsafe_allow_html=True,
            )


def mostrar_colegio_vivo_gerencia(df):
    _iniciar_seleccion_colegio_vivo(df)

    e22, estado22, total22 = _estado_centro_cv(df, "Pearson 22")
    e9, estado9, total9 = _estado_centro_cv(df, "Pearson 9")
    estado_global = "El colegio está bajo control"
    icono_global = "🟢"
    if "🔴" in [e22, e9]:
        estado_global = "Hay una zona que requiere atención prioritaria"
        icono_global = "🔴"
    elif "🟡" in [e22, e9]:
        estado_global = "El colegio requiere seguimiento operativo"
        icono_global = "🟡"

    st.markdown(
        f"<div class='cv-hero'><div><div class='cv-title'>🏫 Colegio vivo</div>"
        f"<div class='cv-subtitle'>Gerencia · Estado real de Pearson 22 y Pearson 9</div></div>"
        f"<div class='cv-status'>{icono_global} {estado_global}</div></div>",
        unsafe_allow_html=True,
    )

    s1, s2 = st.columns(2)
    with s1:
        st.info(f"{e22} **Pearson 22 · {estado22}** · {total22} actuaciones activas")
    with s2:
        st.info(f"{e9} **Pearson 9 · {estado9}** · {total9} actuaciones activas")

    izquierda, derecha = st.columns([1.25, 1], gap="medium")

    with izquierda:
        # Pearson 22: dos edificios, uno claramente más alto.
        st.markdown("<div class='cv-centro-title'>Pearson 22</div>", unsafe_allow_html=True)
        p22_grande, p22_llar = st.columns([1.45, 1], gap="small")
        with p22_grande:
            mostrar_edificio_cv(
                df, "Pearson 22", "Infantil / Primaria",
                EDIFICIOS_GERENCIA["Pearson 22"]["Infantil / Primaria"],
            )
        with p22_llar:
            mostrar_edificio_cv(
                df, "Pearson 22", "Llar",
                EDIFICIOS_GERENCIA["Pearson 22"]["Llar"],
            )

        # Pearson 9: tres edificios compactos en paralelo.
        st.markdown("<div class='cv-centro-title'>Pearson 9</div>", unsafe_allow_html=True)
        columnas_p9 = st.columns(3, gap="small")
        for col, (edificio, plantas) in zip(
            columnas_p9, EDIFICIOS_GERENCIA["Pearson 9"].items()
        ):
            with col:
                mostrar_edificio_cv(df, "Pearson 9", edificio, plantas)

    with derecha:
        with st.container(border=True):
            mostrar_panel_planta_cv(df)

    mostrar_resumen_inferior_cv(df)

    with st.expander("📈 Evolución, inventario y detalle ejecutivo", expanded=False):
        centro = st.session_state["gerencia_cv_centro"]
        mostrar_evolucion_mantenimiento(df, centro)
        total_inv = total_inventario_centro(centro)
        total_usado = total_utilizado_centro(centro, df)
        c1, c2 = st.columns(2)
        c1.metric("Valor de inventario", euros(total_inv))
        c2.metric("Material utilizado", euros(total_usado))


def pantalla_gerencia():
    aplicar_estilo_gerencia()
    aplicar_estilo_colegio_vivo()
    iniciar_estado_gerencia()

    df = preparar_ordenes()
    if df.empty:
        st.warning("No hay órdenes para mostrar todavía.")
        df = pd.DataFrame(columns=[
            "numero_ot", "fecha_creacion", "fecha_cierre", "centro", "edificio",
            "planta", "espacio", "descripcion", "estado", "operario", "solicitante",
            "origen", "area", "prioridad", "origen_tabla", "fecha_dt", "fecha_cierre_dt"
        ])

    detalle_actual = st.session_state.get("gerencia_detalle")
    if detalle_actual:
        mostrar_detalle(df)
        return

    mostrar_colegio_vivo_gerencia(df)
