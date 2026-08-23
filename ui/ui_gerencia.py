import streamlit as st
import pandas as pd
from datetime import datetime, date
import unicodedata

from database.db import conectar


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
    .gerencia-ejecutivo-simple {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 18px 20px;
        margin: 14px 0 18px 0;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
    }
    .gerencia-ejecutivo-title {
        font-size: 22px;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .gerencia-ejecutivo-subtitle {
        font-size: 13px;
        font-weight: 650;
        color: #64748b;
        margin-bottom: 12px;
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


@st.cache_data(ttl=60, show_spinner=False)
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


@st.cache_data(ttl=60, show_spinner=False)
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


@st.cache_data(ttl=60, show_spinner=False)
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
    diagnostico = _diagnostico_ejecutivo_centro(
        df,
        centro,
    )

    mensajes = {
        "rojo": "Existen factores que requieren atención prioritaria.",
        "amarillo": "Hay actuaciones o tendencias que conviene seguir.",
        "verde": "La situación general está bajo control.",
    }

    return (
        diagnostico["color"],
        diagnostico["indice"],
        mensajes.get(
            diagnostico["color"],
            diagnostico["mensaje"],
        ),
    )


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
    """
    Resumen compacto para las vistas antiguas de Gerencia.
    La lectura ejecutiva completa se concentra en Diagnóstico de Gerencia.
    """
    diagnostico = _mostrar_diagnostico_gerencia(
        df,
        centro,
    )

    riesgos = obtener_riesgos_criticos(
        df,
        centro,
    )

    if not riesgos.empty:
        with st.expander(
            f"🔴 Riesgos críticos ({len(riesgos)})",
            expanded=False,
        ):
            for _, row in riesgos.iterrows():
                st.markdown(
                    f"**{row.get('espacio', '-') or '-'}** · "
                    f"`{row.get('numero_ot', '-') or '-'}`"
                )
                st.caption(
                    row.get("descripcion", "") or ""
                )

    st.caption(
        "Gerencia interpreta la situación. "
        "La prioridad diaria de ejecución la determina el ❤️ Corazón."
    )




def _cerradas_mes_actual_gerencia(df, centro):
    datos = _datos_centro_ejecutivo(df, centro)

    if datos.empty:
        return pd.DataFrame()

    cerradas = datos[es_cerrada(datos)].copy()

    if cerradas.empty:
        return cerradas

    fecha_ref = cerradas["fecha_cierre_dt"].copy()
    fecha_ref = fecha_ref.where(
        fecha_ref.notna(),
        cerradas["fecha_dt"],
    )

    hoy = pd.Timestamp.today()

    return cerradas[
        fecha_ref.notna()
        & (fecha_ref.dt.month == hoy.month)
        & (fecha_ref.dt.year == hoy.year)
    ].copy()


def _resumen_simple_gerencia(df, centro):
    diagnostico = _diagnostico_ejecutivo_centro(df, centro)

    cerradas_mes = _cerradas_mes_actual_gerencia(
        df,
        centro,
    )

    abiertas = int(diagnostico.get("abiertas", 0) or 0)
    criticas = int(diagnostico.get("criticas", 0) or 0)
    material = int(diagnostico.get("material", 0) or 0)

    reincidencias = diagnostico.get("reincidencias")
    n_reincidencias = (
        len(reincidencias)
        if reincidencias is not None
        and not reincidencias.empty
        else 0
    )

    cerradas = len(cerradas_mes)

    if diagnostico.get("color") == "rojo":
        estado = "Requiere atención"
        icono = "🔴"
        mensaje = (
            "Hay asuntos que Mantenimiento está siguiendo "
            "con prioridad."
        )
    elif diagnostico.get("color") == "amarillo":
        estado = "En seguimiento"
        icono = "🟡"
        mensaje = (
            "Mantenimiento está gestionando la actividad "
            "y mantiene algunos puntos en seguimiento."
        )
    else:
        estado = "Situación controlada"
        icono = "🟢"
        mensaje = (
            "Mantenimiento está gestionando la actividad "
            "ordinaria sin incidencias relevantes para Gerencia."
        )

    situaciones = []

    if criticas > 0:
        situaciones.append(
            f"{criticas} actuación"
            f"{' prioritaria' if criticas == 1 else 'es prioritarias'} "
            "en seguimiento por Mantenimiento."
        )

    if material > 0:
        situaciones.append(
            f"{material} actuación"
            f"{' está' if material == 1 else 'es están'} "
            "pendiente de material."
        )

    if n_reincidencias > 0:
        situaciones.append(
            f"{n_reincidencias} espacio"
            f"{' presenta' if n_reincidencias == 1 else 's presentan'} "
            "incidencias repetidas y se mantiene seguimiento."
        )

    if not situaciones:
        situaciones.append(
            "No hay ningún asunto relevante que Gerencia "
            "necesite conocer en este momento."
        )

    return {
        "estado": estado,
        "icono": icono,
        "mensaje": mensaje,
        "abiertas": abiertas,
        "criticas": criticas,
        "material": material,
        "reincidencias": n_reincidencias,
        "cerradas_mes": cerradas,
        "situaciones": situaciones[:3],
    }


def mostrar_cabecera_simple_gerencia(df, centro):
    """
    Cabecera ejecutiva compacta para Gerencia.

    Arriba:
    - estado sencillo;
    - carga actual;
    - gráfico compacto de incidencias vs preventivos.

    El objetivo es que Gerencia pueda ver con el tiempo si el
    mantenimiento preventivo se acompaña de una reducción de averías.
    """
    resumen = _resumen_simple_gerencia(df, centro)
    diagnostico = _diagnostico_ejecutivo_centro(df, centro)

    st.markdown("## 🏫 Estado del mantenimiento")

    cabecera = (
        f"**{resumen['icono']} {resumen['estado']}**  \n"
        f"{resumen['mensaje']}  \n"
        "**No hay propuestas pendientes de aprobación registradas.**"
    )

    if resumen["icono"] == "🔴":
        st.error(cabecera)
    elif resumen["icono"] == "🟡":
        st.warning(cabecera)
    else:
        st.success(cabecera)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Abiertas", resumen["abiertas"])
    c2.metric("Prioritarias", resumen["criticas"])
    c3.metric("Pendiente material", resumen["material"])
    c4.metric("Espacios reincidentes", resumen["reincidencias"])

    st.markdown("### 🛡️ Efecto del mantenimiento preventivo")

    incidencias_mes = int(
        diagnostico.get("incidencias_mes", 0) or 0
    )

    _, preventivos_mes, _ = _salud_preventivo_correctivo(
        df,
        centro,
    )

    st.caption(
        f"Este mes · {incidencias_mes} incidencias · "
        f"{preventivos_mes} preventivos realizados"
    )

    evolucion = obtener_evolucion_mensual(df, centro)

    con_datos = evolucion[
        (evolucion["Preventivos realizados"] > 0)
        | (evolucion["Incidencias creadas"] > 0)
    ].copy()

    if con_datos.empty:
        grafico = (
            evolucion
            .head(6)
            .set_index("mes")[
                [
                    "Incidencias creadas",
                    "Preventivos realizados",
                ]
            ]
        )
    else:
        ultimo_indice = int(con_datos.index.max())
        primer_indice = max(0, ultimo_indice - 5)

        grafico = (
            evolucion
            .loc[primer_indice:ultimo_indice]
            .set_index("mes")[
                [
                    "Incidencias creadas",
                    "Preventivos realizados",
                ]
            ]
        )

    st.line_chart(
        grafico,
        use_container_width=True,
        height=240,
    )

    if con_datos.empty:
        st.info(
            "Efecto del preventivo: pendiente de histórico. "
            "La comparación empezará a ser útil cuando se ejecuten "
            "los preventivos del curso."
        )

    elif len(con_datos) == 1:
        st.info(
            "Todavía hay un solo mes con datos. "
            "La tendencia será más fiable cuando existan varios "
            "meses consecutivos."
        )

    else:
        actual = con_datos.iloc[-1]
        anterior = con_datos.iloc[-2]

        inc_actual = int(actual["Incidencias creadas"])
        inc_anterior = int(anterior["Incidencias creadas"])
        prev_actual = int(actual["Preventivos realizados"])
        prev_anterior = int(anterior["Preventivos realizados"])

        if prev_actual >= prev_anterior and inc_actual < inc_anterior:
            reduccion = (
                round(
                    ((inc_anterior - inc_actual) / inc_anterior) * 100
                )
                if inc_anterior > 0
                else 0
            )

            st.success(
                "Tendencia favorable: el mantenimiento preventivo "
                "se mantiene o aumenta mientras las incidencias "
                f"disminuyen un {reduccion}% respecto al mes anterior."
            )

        elif prev_actual > prev_anterior and inc_actual >= inc_anterior:
            st.warning(
                "Todavía no se observa una reducción clara de incidencias "
                "aunque ha aumentado la actividad preventiva. "
                "Conviene seguir acumulando histórico."
            )

        elif inc_actual < inc_anterior:
            st.success(
                "Las incidencias están disminuyendo respecto al mes anterior. "
                "Se seguirá observando su relación con el preventivo."
            )

        else:
            st.info(
                "Aún no hay una tendencia suficiente para atribuir "
                "cambios en las incidencias al mantenimiento preventivo."
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




def _periodos_ejecutivos():
    actual = pd.Timestamp.today().to_period("M")
    return actual, actual - 1


def _datos_centro_ejecutivo(df, centro):
    if df.empty:
        return df.copy()
    return df[df["centro"].fillna("").astype(str).str.strip() == centro].copy()


def _incidencias_periodo(df, centro, periodo):
    datos = _datos_centro_ejecutivo(df, centro)
    if datos.empty:
        return datos
    datos = datos[_es_incidencia_df(datos) & datos["fecha_dt"].notna()].copy()
    if datos.empty:
        return datos
    return datos[datos["fecha_dt"].dt.to_period("M") == periodo].copy()


def _salud_preventivo_correctivo(df, centro):
    actual, _ = _periodos_ejecutivos()
    datos = _datos_centro_ejecutivo(df, centro)
    if datos.empty:
        return 0, 0, 0
    datos = datos[datos["fecha_dt"].notna()].copy()
    datos = datos[datos["fecha_dt"].dt.to_period("M") == actual].copy()
    if datos.empty:
        return 0, 0, 0
    preventivos = int(_es_preventivo_df(datos).sum())
    correctivos = int(_es_incidencia_df(datos).sum())
    total = preventivos + correctivos
    return (round(preventivos / total * 100) if total else 0), preventivos, correctivos


def _resolucion_media(df, centro, dias=90):
    datos = _datos_centro_ejecutivo(df, centro)
    if datos.empty:
        return None, 0
    datos = datos[es_cerrada(datos) & datos["fecha_dt"].notna() & datos["fecha_cierre_dt"].notna()].copy()
    limite = pd.Timestamp.today() - pd.Timedelta(days=dias)
    datos = datos[datos["fecha_cierre_dt"] >= limite].copy()
    if datos.empty:
        return None, 0
    horas = (datos["fecha_cierre_dt"] - datos["fecha_dt"]).dt.total_seconds() / 3600
    horas = horas[(horas >= 0) & (horas <= 24 * 365)]
    return (float(horas.mean()), len(horas)) if not horas.empty else (None, 0)


def _texto_resolucion(horas):
    if horas is None:
        return "Sin datos"
    if horas < 24:
        return f"{horas:.1f} h".replace(".", ",")
    return f"{horas / 24:.1f} días".replace(".", ",")


def _reincidencias_ejecutivas(df, centro, dias=90):
    """
    Detecta espacios con 2 o más incidencias en el periodo indicado.

    Devuelve información suficiente para que Gerencia pueda empezar a
    seguir reincidencias desde ahora sin convertirlo todavía en un módulo
    complejo de causa raíz.
    """
    datos = _datos_centro_ejecutivo(df, centro)

    if datos.empty:
        return pd.DataFrame()

    limite = pd.Timestamp.today() - pd.Timedelta(days=dias)

    datos = datos[
        datos["fecha_dt"].notna()
        & (datos["fecha_dt"] >= limite)
    ].copy()

    datos = datos[
        _es_incidencia_df(datos)
    ].copy()

    if datos.empty:
        return pd.DataFrame()

    datos["espacio_limpio"] = (
        datos["espacio"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    datos = datos[
        ~datos["espacio_limpio"]
        .str.lower()
        .isin(["", "general", "-"])
    ].copy()

    if datos.empty:
        return pd.DataFrame()

    datos["area_limpia"] = (
        datos["area"]
        .fillna("Sin área")
        .replace("", "Sin área")
        .astype(str)
        .str.strip()
    )

    datos["descripcion_limpia"] = (
        datos["descripcion"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    datos["edificio"] = (
        datos["edificio"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    datos["planta"] = (
        datos["planta"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    agrupadas = []

    for (
        edificio,
        planta,
        espacio,
    ), grupo in datos.groupby(
        [
            "edificio",
            "planta",
            "espacio_limpio",
        ],
        dropna=False,
    ):
        total = len(grupo)

        if total < 2:
            continue

        grupo = grupo.sort_values(
            "fecha_dt",
            ascending=False,
        )

        ultima = grupo.iloc[0]

        areas = sorted({
            str(area).strip()
            for area in grupo["area_limpia"].tolist()
            if str(area).strip()
        })

        agrupadas.append({
            "edificio": edificio,
            "planta": planta,
            "espacio_limpio": espacio,
            "incidencias": int(total),
            "areas": ", ".join(areas),
            "ultima_fecha": ultima.get("fecha_dt"),
            "ultima_ot": str(
                ultima.get("numero_ot")
                or ""
            ).strip(),
            "ultima_descripcion": str(
                ultima.get("descripcion_limpia")
                or ""
            ).strip(),
        })

    if not agrupadas:
        return pd.DataFrame()

    resumen = pd.DataFrame(
        agrupadas
    )

    return resumen.sort_values(
        [
            "incidencias",
            "ultima_fecha",
            "espacio_limpio",
        ],
        ascending=[
            False,
            False,
            True,
        ],
    ).reset_index(drop=True)



def _area_crecimiento(df, centro):
    actual, anterior = _periodos_ejecutivos()
    a = _incidencias_periodo(df, centro, actual)
    b = _incidencias_periodo(df, centro, anterior)
    ca = a["area"].fillna("Sin área").replace("", "Sin área").value_counts() if not a.empty else pd.Series(dtype="int64")
    cb = b["area"].fillna("Sin área").replace("", "Sin área").value_counts() if not b.empty else pd.Series(dtype="int64")
    mejor = (None, 0, 0, 0)
    for area in set(ca.index).union(set(cb.index)):
        va, vb = int(ca.get(area, 0)), int(cb.get(area, 0))
        if va - vb > mejor[1]:
            mejor = (str(area), va - vb, va, vb)
    return mejor


def _preventivos_cerrados(df, centro):
    datos = _datos_centro_ejecutivo(df, centro)
    if datos.empty:
        return None, 0, 0
    p = datos[_es_preventivo_df(datos)].copy()
    if p.empty:
        return None, 0, 0
    total = len(p); cerrados = len(p[es_cerrada(p)])
    return round(cerrados / total * 100), cerrados, total



def _diagnostico_ejecutivo_centro(df, centro):
    """
    Diagnóstico ejecutivo único de Gerencia.

    Usa únicamente datos ya disponibles en este módulo:
    carga activa, riesgos críticos, material pendiente,
    tendencia mensual, reincidencias, resolución y preventivo.

    El índice se redondea a bloques de 5 puntos para no transmitir
    una falsa precisión.
    """
    datos_centro = _datos_centro_ejecutivo(df, centro)

    if datos_centro.empty:
        return {
            "color": "verde",
            "indice": 100,
            "estado": "Sin carga registrada",
            "mensaje": "No hay actuaciones registradas para este centro.",
            "abiertas": 0,
            "material": 0,
            "criticas": 0,
            "incidencias_mes": 0,
            "incidencias_mes_anterior": 0,
            "diferencia": 0,
            "tendencia": "estable",
            "reincidencias": pd.DataFrame(),
            "resolucion_horas": None,
            "resolucion_muestra": 0,
            "cumpl_preventivo": None,
            "preventivos_cerrados": 0,
            "preventivos_total": 0,
            "area_crecimiento": (None, 0, 0, 0),
            "puntos_alerta": [],
            "puntos_favorables": [],
        }

    abiertas_df = obtener_df_tarjeta(df, centro, "abiertas")
    material_df = obtener_df_tarjeta(df, centro, "material")
    criticas_df = obtener_riesgos_criticos(df, centro)

    actual, anterior = _periodos_ejecutivos()
    ia = len(_incidencias_periodo(df, centro, actual))
    ib = len(_incidencias_periodo(df, centro, anterior))
    diferencia = ia - ib

    reinc = _reincidencias_ejecutivas(df, centro)
    horas, n_res = _resolucion_media(df, centro)
    cumpl, cerrados_prev, total_prev = _preventivos_cerrados(df, centro)
    area_crecimiento = _area_crecimiento(df, centro)

    abiertas = len(abiertas_df)
    material = len(material_df)
    criticas = len(criticas_df)

    # -------------------------------------------------
    # ÍNDICE EJECUTIVO · 0-100
    # -------------------------------------------------
    # Filosofía:
    # - Gerencia interpreta la situación, no suma castigos OT por OT.
    # - Una misma actuación puede ser abierta + crítica + pendiente material;
    #   por eso usamos BLOQUES de riesgo con techo y no penalizaciones lineales.
    # - La tendencia puede compensar parcialmente la carga acumulada.
    # - Los valores muy bajos quedan reservados para escenarios realmente graves.
    indice = 100.0

    # 1) CARGA ACTIVA · máximo -15
    if abiertas >= 30:
        indice -= 15
    elif abiertas >= 20:
        indice -= 12
    elif abiertas >= 10:
        indice -= 8
    elif abiertas >= 5:
        indice -= 5
    elif abiertas > 0:
        indice -= 2

    # 2) RIESGO ACTUAL · máximo -20
    # No multiplicamos por cada crítica: evitamos hundir el índice
    # cuando varias pertenecen a la misma carga operativa.
    if criticas >= 10:
        indice -= 20
    elif criticas >= 6:
        indice -= 16
    elif criticas >= 3:
        indice -= 11
    elif criticas >= 1:
        indice -= 6

    # 3) BLOQUEOS POR MATERIAL · máximo -10
    if material >= 10:
        indice -= 10
    elif material >= 5:
        indice -= 7
    elif material >= 2:
        indice -= 4
    elif material == 1:
        indice -= 2

    # 4) REINCIDENCIA · máximo -10
    n_reinc = len(reinc)
    if n_reinc >= 10:
        indice -= 10
    elif n_reinc >= 5:
        indice -= 7
    elif n_reinc >= 2:
        indice -= 4
    elif n_reinc == 1:
        indice -= 2

    # 5) TENDENCIA MENSUAL · puede recuperar hasta +12
    if diferencia > 0:
        tendencia = "desfavorable"
        if ib > 0:
            subida_pct = ((ia - ib) / ib) * 100
            if subida_pct >= 100:
                indice -= 10
            elif subida_pct >= 50:
                indice -= 7
            elif subida_pct >= 20:
                indice -= 4
            else:
                indice -= 2
        else:
            indice -= min(8, ia * 2)
    elif diferencia < 0:
        tendencia = "favorable"
        if ib > 0:
            bajada_pct = ((ib - ia) / ib) * 100
            if bajada_pct >= 75:
                indice += 12
            elif bajada_pct >= 50:
                indice += 9
            elif bajada_pct >= 20:
                indice += 6
            else:
                indice += 3
    else:
        tendencia = "estable"

    # 6) RESOLUCIÓN · máximo -6
    if horas is not None:
        if horas > 24 * 10:
            indice -= 6
        elif horas > 24 * 7:
            indice -= 4
        elif horas > 72:
            indice -= 2

    # 7) PREVENTIVO · máximo -6 / refuerzo +3
    if cumpl is not None:
        if cumpl < 50:
            indice -= 6
        elif cumpl < 70:
            indice -= 3
        elif cumpl >= 90:
            indice += 3

    indice = max(0, min(100, indice))
    indice = int(round(indice / 5.0) * 5)

    # El color combina índice y existencia de riesgo real.
    # Tener críticas no convierte automáticamente una situación favorable
    # en "rojo"; sí obliga, como mínimo, a seguimiento.
    if indice < 45 or (criticas >= 10 and tendencia == "desfavorable"):
        color = "rojo"
        estado = "Requiere atención"
    elif indice < 80 or criticas > 0 or material > 0:
        color = "amarillo"
        estado = "Requiere seguimiento"
    else:
        color = "verde"
        estado = "Bajo control"

    puntos_alerta = []
    puntos_favorables = []

    if criticas:
        puntos_alerta.append(
            f"{criticas} actuación"
            f"{' crítica' if criticas == 1 else 'es críticas'} abierta"
            f"{'' if criticas == 1 else 's'}."
        )

    if material:
        puntos_alerta.append(
            f"{material} actuación"
            f"{' bloqueada' if material == 1 else 'es bloqueadas'} "
            "por material."
        )

    if not reinc.empty:
        puntos_alerta.append(
            f"{len(reinc)} espacio"
            f"{' reincidente' if len(reinc) == 1 else 's reincidentes'} "
            "en 90 días."
        )

    if diferencia > 0:
        puntos_alerta.append(
            f"Las incidencias suben de {ib} a {ia} este mes."
        )
    elif diferencia < 0:
        puntos_favorables.append(
            f"Las incidencias bajan de {ib} a {ia} este mes."
        )
    else:
        puntos_favorables.append(
            f"Las incidencias se mantienen en {ia} respecto al mes anterior."
        )

    if cumpl is not None:
        if cumpl >= 90:
            puntos_favorables.append(
                f"Preventivo cerrado: {cumpl}%."
            )
        elif cumpl < 70:
            puntos_alerta.append(
                f"Preventivo cerrado: {cumpl}%."
            )

    if horas is not None:
        if horas <= 72:
            puntos_favorables.append(
                f"Resolución media reciente: {_texto_resolucion(horas)}."
            )
        elif horas > 24 * 7:
            puntos_alerta.append(
                f"Resolución media elevada: {_texto_resolucion(horas)}."
            )

    mensaje = (
        f"Situación operativa: {estado.lower()}. "
        f"Tendencia: {tendencia}."
    )

    return {
        "color": color,
        "indice": indice,
        "estado": estado,
        "mensaje": mensaje,
        "abiertas": abiertas,
        "material": material,
        "criticas": criticas,
        "incidencias_mes": ia,
        "incidencias_mes_anterior": ib,
        "diferencia": diferencia,
        "tendencia": tendencia,
        "reincidencias": reinc,
        "resolucion_horas": horas,
        "resolucion_muestra": n_res,
        "cumpl_preventivo": cumpl,
        "preventivos_cerrados": cerrados_prev,
        "preventivos_total": total_prev,
        "area_crecimiento": area_crecimiento,
        "puntos_alerta": puntos_alerta,
        "puntos_favorables": puntos_favorables,
    }


def _mostrar_diagnostico_gerencia(df, centro):
    diagnostico = _diagnostico_ejecutivo_centro(df, centro)

    st.markdown("### 🧭 Diagnóstico de Gerencia")

    cabecera = (
        f"**{diagnostico['estado']} · "
        f"Índice operativo {diagnostico['indice']}%**\n\n"
        f"{diagnostico['mensaje']}"
    )

    if diagnostico["color"] == "rojo":
        st.error(cabecera)
    elif diagnostico["color"] == "amarillo":
        st.warning(cabecera)
    else:
        st.success(cabecera)

    alertas = diagnostico.get("puntos_alerta", [])
    favorables = diagnostico.get("puntos_favorables", [])

    if alertas:
        for linea in alertas[:3]:
            st.markdown(f"⚠️ {linea}")

    if favorables:
        for linea in favorables[:2]:
            st.caption(f"✓ {linea}")

    area, cambio, va, vb = diagnostico.get(
        "area_crecimiento",
        (None, 0, 0, 0),
    )

    if area and cambio > 0:
        st.caption(
            f"📈 Área a vigilar: {area} · "
            f"{vb} → {va} incidencias."
        )

    return diagnostico


def mostrar_capa_ejecutiva_gerencia(df, centro):
    diagnostico = _mostrar_diagnostico_gerencia(
        df,
        centro,
    )

    ia = diagnostico["incidencias_mes"]
    ib = diagnostico["incidencias_mes_anterior"]

    if ib > 0:
        variacion = ((ia - ib) / ib) * 100
        delta = f"{variacion:+.0f}% vs mes anterior"
    elif ia > 0:
        delta = f"+{ia} vs mes anterior"
    else:
        delta = "Sin variación"

    pct_prev, n_prev, n_corr = _salud_preventivo_correctivo(
        df,
        centro,
    )

    horas = diagnostico["resolucion_horas"]
    n_res = diagnostico["resolucion_muestra"]
    reinc = diagnostico["reincidencias"]
    cumpl = diagnostico["cumpl_preventivo"]
    cerrados_prev = diagnostico["preventivos_cerrados"]
    total_prev = diagnostico["preventivos_total"]

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "⚠️ Incidencias este mes",
        ia,
        delta=delta,
        delta_color="inverse",
        help=f"Mes anterior: {ib}",
    )

    k2.metric(
        "🛡️ Preventivo / correctivo",
        f"{pct_prev}% preventivo",
        help=f"Este mes: {n_prev} preventivos y {n_corr} correctivos.",
    )

    k3.metric(
        "⏱️ Resolución media",
        _texto_resolucion(horas),
        help=f"{n_res} OTs cerradas analizadas en los últimos 90 días.",
    )

    k4.metric(
        "🔁 Espacios reincidentes",
        len(reinc),
        help="2 o más incidencias en el mismo espacio durante los últimos 90 días.",
    )

    with st.expander(
        "📊 Ver detalle de salud del mantenimiento",
        expanded=False,
    ):
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### Preventivo")

            if cumpl is None:
                st.info(
                    "Todavía no hay preventivos registrados "
                    "para calcular el indicador."
                )
            else:
                st.metric(
                    "Preventivos cerrados",
                    f"{cumpl}%",
                    help=(
                        f"{cerrados_prev} cerrados de "
                        f"{total_prev} registrados."
                    ),
                )

                st.caption(
                    "Mide preventivos cerrados/registrados. "
                    "No se presenta como «en plazo» porque este módulo "
                    "no dispone aquí de la fecha límite planificada."
                )

        with c2:
            st.markdown("#### Reincidencias")

            if reinc.empty:
                st.success(
                    "Sin espacios reincidentes en los últimos 90 días."
                )
            else:
                vista = reinc.head(10).copy()

                vista["Última incidencia"] = pd.to_datetime(
                    vista["ultima_fecha"],
                    errors="coerce",
                ).dt.strftime("%d/%m/%Y")

                vista = vista.rename(
                    columns={
                        "edificio": "Edificio",
                        "planta": "Planta",
                        "espacio_limpio": "Espacio",
                        "incidencias": "Incidencias",
                        "areas": "Áreas",
                    }
                )

                st.dataframe(
                    vista[
                        [
                            "Edificio",
                            "Planta",
                            "Espacio",
                            "Incidencias",
                            "Áreas",
                            "Última incidencia",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(
                    "Reincidencia = 2 o más incidencias en el mismo "
                    "edificio + planta + espacio durante 90 días."
                )

        area, cambio, va, vb = diagnostico.get(
            "area_crecimiento",
            (None, 0, 0, 0),
        )

        if area and cambio > 0:
            st.warning(
                f"📈 **Área a vigilar: {area}.** "
                f"Pasa de {vb} a {va} incidencias respecto al mes anterior."
            )

        if not reinc.empty:
            primera = reinc.iloc[0]

            with st.container(border=True):
                st.markdown(
                    "#### 🔁 Reincidencia a observar"
                )

                st.markdown(
                    f"**{primera.get('espacio_limpio', '-')}** · "
                    f"{primera.get('incidencias', 0)} incidencias"
                )

                ubicacion_reinc = " · ".join(
                    [
                        str(valor).strip()
                        for valor in [
                            primera.get("edificio"),
                            primera.get("planta"),
                        ]
                        if str(valor or "").strip()
                    ]
                )

                if ubicacion_reinc:
                    st.caption(
                        f"📍 {ubicacion_reinc}"
                    )

                if primera.get("areas"):
                    st.write(
                        f"**Áreas implicadas:** {primera.get('areas')}"
                    )

                ultima_fecha = pd.to_datetime(
                    primera.get("ultima_fecha"),
                    errors="coerce",
                )

                if pd.notna(ultima_fecha):
                    st.write(
                        f"**Última incidencia:** "
                        f"{ultima_fecha.strftime('%d/%m/%Y')}"
                    )

                if primera.get("ultima_ot"):
                    st.write(
                        f"**Última OT:** {primera.get('ultima_ot')}"
                    )

                if primera.get("ultima_descripcion"):
                    st.caption(
                        primera.get("ultima_descripcion")
                    )

                st.info(
                    "Gerencia la señala para seguimiento. "
                    "La causa raíz se incorporará cuando exista "
                    "suficiente histórico fiable."
                )

        st.caption(
            "Gerencia interpreta tendencias y salud del mantenimiento. "
            "La prioridad diaria de ejecución continúa correspondiendo "
            "al ❤️ Corazón."
        )



def mostrar_menu_centro(df, centro):
    st.markdown(f"<div class='gerencia-section-title'>🏫 {centro}</div>", unsafe_allow_html=True)

    if st.button("⬅️ Volver a centros", use_container_width=True, key="volver_centros_gerencia"):
        volver_a_centros()

    mostrar_resumen_ejecutivo(df, centro)

    # Indicadores ejecutivos sin repetir el diagnóstico principal.
    diagnostico_ya_mostrado = True

    if diagnostico_ya_mostrado:
        ia = len(_incidencias_periodo(df, centro, _periodos_ejecutivos()[0]))
        ib = len(_incidencias_periodo(df, centro, _periodos_ejecutivos()[1]))
        pct_prev, n_prev, n_corr = _salud_preventivo_correctivo(df, centro)
        horas, n_res = _resolucion_media(df, centro)
        reinc = _reincidencias_ejecutivas(df, centro)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric(
            "⚠️ Incidencias este mes",
            ia,
            delta=(f"{((ia-ib)/ib)*100:+.0f}% vs mes anterior" if ib else (f"+{ia} vs mes anterior" if ia else "Sin variación")),
            delta_color="inverse",
        )
        k2.metric(
            "🛡️ Preventivo / correctivo",
            f"{pct_prev}% preventivo",
            help=f"Este mes: {n_prev} preventivos y {n_corr} correctivos.",
        )
        k3.metric(
            "⏱️ Resolución media",
            _texto_resolucion(horas),
            help=f"{n_res} OTs cerradas analizadas en los últimos 90 días.",
        )
        k4.metric(
            "🔁 Espacios reincidentes",
            len(reinc),
        )

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

    st.metric(
        "💰 Total inventario",
        euros(datos["valor_total"].sum())
    )

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

        with st.expander(
            f"📦 {codigo} · {material} · Stock: {stock}",
            expanded=False
        ):
            st.markdown(
                f"### {material}"
            )

            st.caption(
                f"🏷️ {categoria or '-'} · "
                f"📍 {ubicacion or '-'}"
            )

            st.markdown(
                f"**Precio unitario:** {euros(precio)}"
            )

            st.markdown(
                f"**Valor inventario:** {euros(valor)}"
            )

            if fecha_compra:
                st.caption(
                    f"📅 {fecha_compra}"
                )

            # =====================================================
            # FOTO INVENTARIO BAJO DEMANDA
            # =====================================================
            clave_foto_inv = (
                "gerencia_foto_inventario_abierta"
            )

            foto_abierta = st.session_state.get(
                clave_foto_inv
            )

            if foto_abierta == id_material:

                if st.button(
                    "🙈 Ocultar foto",
                    key=f"cerrar_foto_gerencia_{id_material}",
                    use_container_width=True,
                ):
                    st.session_state.pop(
                        clave_foto_inv,
                        None,
                    )
                    st.rerun()

                try:
                    foto_data = (
                        obtener_foto_inventario_por_id(
                            id_material
                        )
                    )

                    if foto_data:
                        try:
                            st.image(
                                bytes(foto_data),
                                width=220
                            )
                        except Exception:
                            st.caption(
                                "Foto no disponible."
                            )

                    elif foto:
                        try:
                            st.image(
                                foto,
                                width=220
                            )
                        except Exception:
                            st.caption(
                                "Foto no disponible."
                            )

                    else:
                        st.info(
                            "Este material no tiene foto."
                        )

                except Exception as e:
                    st.caption(
                        f"No se pudo cargar la foto: {e}"
                    )

            else:

                if st.button(
                    "📷 Ver foto",
                    key=f"abrir_foto_gerencia_{id_material}",
                    use_container_width=True,
                ):
                    st.session_state[
                        clave_foto_inv
                    ] = id_material

                    st.rerun()

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
        "Edificio A": ["Planta 2", "Planta 1"],
        "Edificio B": ["Planta 2", "Planta 1"],
        "Edificio C": ["Planta 2", "Planta 1"],
        # El anexo no pertenece a A/B/C y físicamente es una sola planta.
        "Anexo Servicios": [
            "Taller",
            "Vestuarios chicas",
            "Sala calderas",
            "Vestuarios chicos",
        ],
    },
}


ALIAS_EDIFICIOS_GERENCIA = {
    "Infantil / Primaria": ["infantil primaria", "infantil/primaria", "edif infantil primaria", "edificio infantil primaria"],
    "Llar": ["llar", "anexo", "edif llar", "edificio llar"],
    "Edificio A": ["edificio a", "edif a", "bloque a"],
    "Edificio B": ["edificio b", "edif b", "bloque b"],
    "Edificio C": ["edificio c", "edif c", "bloque c"],
    "Anexo Servicios": [
        "anexo servicios",
        "anexo",
        "taller",
        "vestuarios chicas",
        "vestuario chicas",
        "vestuarios chicos",
        "vestuario chicos",
        "sala calderas",
        "sala de calderas",
        "sala tecnica",
        "sala técnica",
    ],
}


def aplicar_estilo_colegio_vivo():
    st.markdown("""
    <style>
    .cv-hero {
        display:flex; align-items:center; justify-content:space-between;
        gap:16px; padding:14px 18px; margin:0 0 12px 0;
        background:linear-gradient(135deg,#0f172a 0%,#1d4ed8 100%);
        border-radius:18px; color:white;
        box-shadow:0 8px 24px rgba(15,23,42,.14);
    }
    .cv-title {font-size:27px;font-weight:900;line-height:1.05}
    .cv-subtitle {font-size:13px;font-weight:600;opacity:.9;margin-top:4px}
    .cv-status {padding:9px 14px;border-radius:14px;background:rgba(255,255,255,.14);font-weight:800}
    .cv-section {font-size:17px;font-weight:900;color:#0f172a;margin:2px 0 8px}
    .cv-building {
        border:1px solid #e2e8f0;border-radius:16px;padding:10px 10px 8px;
        background:#fff;box-shadow:0 5px 16px rgba(15,23,42,.06);margin-bottom:8px;
    }
    .cv-building-title {font-size:14px;font-weight:900;color:#1e3a8a;margin-bottom:6px}

    /* =====================================================
       MAPA VISUAL · MISMO LENGUAJE QUE OPERARIO
       ===================================================== */
    .cv-map-campus-title{
        width:100%;
        margin:2px auto 7px;
        text-align:center;
        color:#0f172a;
        font-size:18px;
        line-height:1;
        font-weight:950;
        letter-spacing:.35px;
        text-transform:uppercase;
    }

    .cv-map-roof{
        height:37px;
        position:relative;
        margin:0 4px -1px;
        background:#172b47;
        clip-path:polygon(50% 0,100% 78%,100% 100%,0 100%,0 78%);
    }

    .cv-map-roof:after{
        content:"";
        position:absolute;
        left:50%;
        top:11px;
        transform:translateX(-50%);
        width:11px;
        height:11px;
        border:3px solid #f4e6bd;
        border-radius:50%;
        background:#27496f;
    }

    .cv-map-building-name{
        height:39px;
        display:flex;
        align-items:center;
        justify-content:center;
        overflow:hidden;
        padding:0 2px;
        background:linear-gradient(180deg,#173a6e,#0e284d);
        color:#fff;
        font-size:12px;
        line-height:1;
        font-weight:950;
        white-space:nowrap;
        text-align:center;
        border-left:4px solid #d9caa7;
        border-right:4px solid #d9caa7;
        border-top:3px solid #e8dab5;
        border-bottom:3px solid #caba93;
    }

    .cv-map-ground{
        height:33px;
        position:relative;
        background:linear-gradient(#d4c29b,#bd9f72);
        border:4px solid #ded1ad;
        border-top:3px solid #b89e72;
    }

    .cv-map-door{
        position:absolute;
        left:50%;
        bottom:0;
        transform:translateX(-50%);
        width:19px;
        height:26px;
        background:linear-gradient(90deg,#16345b 48%,#0c2442 50%);
        border:2px solid #10233c;
        border-bottom:0;
        border-radius:2px 2px 0 0;
    }

    .cv-map-base{
        height:6px;
        background:#354154;
        border-bottom:2px solid #1f2937;
        border-radius:0 0 3px 3px;
    }

    .cv-map-annex-wrap{
        width:100%;
        margin:8px auto 4px;
    }

    .cv-map-annex-title{
        background:linear-gradient(180deg,#173a6e,#0e284d);
        color:#fff;
        border:3px solid #d9caa7;
        padding:7px 9px;
        text-align:center;
        font-size:12px;
        font-weight:950;
        letter-spacing:.25px;
    }

    /* Solo los botones de los edificios del mapa */
    .st-key-gerencia_mapa_edificios_p9
    div[data-testid="stButton"] > button,
    .st-key-gerencia_mapa_edificios_p22
    div[data-testid="stButton"] > button{
        min-height:43px !important;
        height:43px !important;
        padding:0 6px !important;
        margin:0 !important;
        border-radius:0 !important;
        border:1px solid rgba(80,70,50,.24) !important;
        color:#102033 !important;
        font-size:11px !important;
        line-height:1 !important;
        font-weight:900 !important;
        text-align:center !important;
        justify-content:center !important;
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.30) !important;
    }

    .st-key-gerencia_mapa_edificios_p9
    div[data-testid="stButton"] > button[kind="primary"],
    .st-key-gerencia_mapa_edificios_p22
    div[data-testid="stButton"] > button[kind="primary"]{
        background:linear-gradient(135deg,#173a6e,#2459a7) !important;
        color:#fff !important;
        border:2px solid #f0d58a !important;
    }

    .st-key-gerencia_anexo_p9
    div[data-testid="stButton"] > button{
        min-height:47px !important;
        height:47px !important;
        padding:4px 5px !important;
        border-radius:0 !important;
        font-size:10px !important;
        line-height:1.12 !important;
        font-weight:900 !important;
        white-space:normal !important;
        text-align:center !important;
        justify-content:center !important;
    }

    .cv-panel {
        border:1px solid #dbe3ef;border-radius:18px;padding:14px 16px;background:#fff;
        box-shadow:0 8px 22px rgba(15,23,42,.07);
    }
    .cv-panel-title {font-size:21px;font-weight:900;color:#0f172a;margin-bottom:2px}
    .cv-panel-subtitle {font-size:13px;color:#64748b;font-weight:650;margin-bottom:10px}
    .cv-kpi {
        border:1px solid #e2e8f0;border-radius:14px;padding:10px 12px;background:#f8fafc;
        min-height:82px;
    }
    .cv-kpi-label {font-size:12px;color:#64748b;font-weight:700}
    .cv-kpi-value {font-size:25px;color:#0f172a;font-weight:900;line-height:1.15;margin-top:4px}
    .cv-footer-card {border:1px solid #e2e8f0;border-radius:15px;padding:10px 12px;background:#fff;min-height:82px}
    .cv-footer-label {font-size:12px;font-weight:800;color:#475569}
    .cv-footer-value {font-size:20px;font-weight:900;color:#0f172a;margin-top:5px}
    div[data-testid="stButton"] > button {
        min-height:42px !important; height:auto !important; border-radius:11px !important;
        padding:7px 8px !important; font-size:13px !important; line-height:1.15 !important;
        white-space:pre-line !important; box-shadow:none !important;
    }
    div[data-testid="stMetric"] {background:#f8fafc;border:1px solid #e2e8f0;border-radius:13px;padding:8px 10px}
    div[data-testid="stDataFrame"] {border-radius:12px;overflow:hidden}
    .block-container {padding-top:1rem;padding-bottom:1rem;max-width:1700px}
    @media (max-width: 900px) {
        .cv-hero {display:block}.cv-status{margin-top:10px}.cv-title{font-size:23px}
    }

    @media (max-width: 760px) {
        .cv-map-campus-title{font-size:15px;margin-bottom:5px}

        .cv-map-roof{
            height:27px;
            margin:0 2px -1px;
        }

        .cv-map-roof:after{
            top:8px;
            width:8px;
            height:8px;
            border-width:2px;
        }

        .cv-map-building-name{
            height:30px;
            font-size:9px;
            border-left-width:2px;
            border-right-width:2px;
            border-top-width:2px;
            border-bottom-width:2px;
        }

        .st-key-gerencia_mapa_edificios_p9
        div[data-testid="stHorizontalBlock"],
        .st-key-gerencia_mapa_edificios_p22
        div[data-testid="stHorizontalBlock"]{
            flex-wrap:nowrap !important;
            gap:4px !important;
        }

        .st-key-gerencia_mapa_edificios_p9
        div[data-testid="stHorizontalBlock"] > div,
        .st-key-gerencia_mapa_edificios_p22
        div[data-testid="stHorizontalBlock"] > div{
            min-width:0 !important;
            flex:1 1 0 !important;
        }

        .st-key-gerencia_mapa_edificios_p9
        div[data-testid="stButton"] > button,
        .st-key-gerencia_mapa_edificios_p22
        div[data-testid="stButton"] > button{
            min-height:39px !important;
            height:39px !important;
            padding:0 3px !important;
            font-size:9px !important;
        }

        .cv-map-ground{
            height:23px;
            border-width:2px;
            border-top-width:2px;
        }

        .cv-map-door{
            width:13px;
            height:18px;
            border-width:1px;
        }

        .cv-map-base{
            height:4px;
        }

        .cv-map-annex-title{
            font-size:11px;
            padding:6px 5px;
        }

        .st-key-gerencia_anexo_p9
        div[data-testid="stHorizontalBlock"]{
            flex-wrap:wrap !important;
            gap:4px !important;
        }

        .st-key-gerencia_anexo_p9
        div[data-testid="stHorizontalBlock"] > div{
            flex:1 1 calc(50% - 4px) !important;
            min-width:calc(50% - 4px) !important;
            max-width:calc(50% - 4px) !important;
        }

        .st-key-gerencia_anexo_p9
        div[data-testid="stButton"] > button{
            min-height:50px !important;
            height:50px !important;
            font-size:10px !important;
        }
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


ZONAS_ANEXO_GERENCIA = {
    "Taller": [
        "taller",
    ],
    "Vestuarios chicas": [
        "vestuarios chicas",
        "vestuario chicas",
        "duchas femeninas",
        "duchas femenina",
        "duchas chicas",
    ],
    "Sala calderas": [
        "sala calderas",
        "sala de calderas",
        "sala tecnica",
        "sala técnica",
    ],
    "Vestuarios chicos": [
        "vestuarios chicos",
        "vestuario chicos",
        "duchas masculinas",
        "duchas masculina",
        "duchas chicos",
    ],
}


def _coincide_zona_anexo_gerencia(espacio, zona):
    texto = normalizar_busqueda(espacio)
    if not texto:
        return False

    aliases = ZONAS_ANEXO_GERENCIA.get(zona, [zona])

    for alias in aliases:
        alias_n = normalizar_busqueda(alias)
        if texto == alias_n or alias_n in texto:
            return True

    return False


def filtrar_por_ubicacion_gerencia(df, centro, edificio, planta):
    if df.empty:
        return df.copy()

    datos = df[
        df["centro"].fillna("").astype(str).str.strip() == centro
    ].copy()

    if datos.empty:
        return datos

    # -------------------------------------------------
    # ANEXO SERVICIOS · PEARSON 9
    # -------------------------------------------------
    # Taller, Vestuarios chicas, Sala calderas y Vestuarios chicos
    # son espacios de una única planta y no pertenecen a A/B/C.
    if centro == "Pearson 9" and edificio == "Anexo Servicios":
        espacio_texto = datos["espacio"].fillna("").astype(str)

        mascara = espacio_texto.apply(
            lambda valor: _coincide_zona_anexo_gerencia(
                valor,
                planta,
            )
        )

        # Compatibilidad con órdenes antiguas donde la ubicación
        # pudiera haber quedado en descripción o edificio.
        if not mascara.any():
            apoyo = (
                datos["espacio"].fillna("").astype(str)
                + " "
                + datos["edificio"].fillna("").astype(str)
                + " "
                + datos["descripcion"].fillna("").astype(str)
            )

            mascara = apoyo.apply(
                lambda valor: _coincide_zona_anexo_gerencia(
                    valor,
                    planta,
                )
            )

        return datos[mascara].copy()

    # -------------------------------------------------
    # EDIFICIOS NORMALES
    # -------------------------------------------------
    datos = datos[
        datos["edificio"].fillna("").astype(str).apply(
            lambda x: _coincide_edificio(
                x,
                edificio,
            )
        )
    ].copy()

    if datos.empty:
        return datos

    planta_obj = _normalizar_planta(planta)

    datos["_planta_norm"] = (
        datos["planta"]
        .fillna("")
        .astype(str)
        .apply(_normalizar_planta)
    )

    # Compatibilidad con órdenes antiguas sin planta:
    # intentar localizarla en espacio/descripcion.
    vacias = datos["_planta_norm"].eq("")

    if vacias.any():
        apoyo = (
            datos.loc[vacias, "espacio"].fillna("").astype(str)
            + " "
            + datos.loc[vacias, "descripcion"].fillna("").astype(str)
        ).apply(_normalizar_planta)

        datos.loc[vacias, "_planta_norm"] = apoyo

    return datos[
        datos["_planta_norm"] == planta_obj
    ].copy()


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


def _seleccion_mas_relevante(df, centro_objetivo=None):
    if centro_objetivo in EDIFICIOS_GERENCIA:
        centros = {
            centro_objetivo: EDIFICIOS_GERENCIA[centro_objetivo]
        }
    else:
        centros = EDIFICIOS_GERENCIA

    mejor = None
    mejor_peso = -1

    for centro, edificios in centros.items():
        for edificio, plantas in edificios.items():
            for planta in plantas:
                _, cantidad, nivel = _estado_planta(
                    df,
                    centro,
                    edificio,
                    planta,
                )

                peso = nivel * 1000 + cantidad

                if peso > mejor_peso:
                    mejor = (
                        centro,
                        edificio,
                        planta,
                    )
                    mejor_peso = peso

    if mejor is None:
        if centro_objetivo == "Pearson 9":
            return (
                "Pearson 9",
                "Edificio A",
                "Planta 2",
            )

        return (
            "Pearson 22",
            "Infantil / Primaria",
            "Planta 2",
        )

    return mejor


def _iniciar_seleccion_colegio_vivo(
    df,
    centro_objetivo=None,
):
    centro_actual = st.session_state.get(
        "gerencia_cv_centro"
    )
    edificio_actual = st.session_state.get(
        "gerencia_cv_edificio"
    )
    planta_actual = st.session_state.get(
        "gerencia_cv_planta"
    )

    necesita_inicializar = (
        not edificio_actual
        or not planta_actual
    )

    if (
        centro_objetivo in EDIFICIOS_GERENCIA
        and centro_actual != centro_objetivo
    ):
        necesita_inicializar = True

    if necesita_inicializar:
        centro, edificio, planta = _seleccion_mas_relevante(
            df,
            centro_objetivo=centro_objetivo,
        )

        st.session_state[
            "gerencia_cv_centro"
        ] = centro

        st.session_state[
            "gerencia_cv_edificio"
        ] = edificio

        st.session_state[
            "gerencia_cv_planta"
        ] = planta


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
    st.markdown(f"<div class='cv-building'><div class='cv-building-title'>{edificio}</div>", unsafe_allow_html=True)
    columnas = st.columns(len(plantas))
    seleccionado_edificio = st.session_state.get("gerencia_cv_edificio")
    seleccionado_planta = st.session_state.get("gerencia_cv_planta")
    seleccionado_centro = st.session_state.get("gerencia_cv_centro")
    for col, planta in zip(columnas, plantas):
        icono, cantidad, _ = _estado_planta(df, centro, edificio, planta)
        if edificio == "Anexo Servicios":
            etiqueta_planta = planta
        else:
            etiqueta_planta = planta.replace("Planta ", "P")

        sufijo = f"\n{cantidad}" if cantidad else "\nOK"
        seleccionada = centro == seleccionado_centro and edificio == seleccionado_edificio and planta == seleccionado_planta
        prefijo = "▸ " if seleccionada else ""
        with col:
            st.button(
                f"{prefijo}{icono} {etiqueta_planta}{sufijo}",
                key=f"cv_{centro}_{edificio}_{planta}",
                use_container_width=True,
                on_click=_seleccionar_planta_cv,
                args=(centro, edificio, planta),
                type="primary" if seleccionada else "secondary",
            )
    st.markdown("</div>", unsafe_allow_html=True)


def _pintar_edificio_visual_gerencia(
    df,
    centro,
    edificio,
    plantas,
):
    """
    Representación visual tipo Colegio Vivo de Operario.
    Solo cambia el dibujo; datos y selección siguen usando
    la lógica actual de Gerencia.
    """
    st.markdown(
        (
            '<div class="cv-map-roof"></div>'
            '<div class="cv-map-building-name">'
            f'{edificio.upper()}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    seleccionado_centro = st.session_state.get("gerencia_cv_centro")
    seleccionado_edificio = st.session_state.get("gerencia_cv_edificio")
    seleccionado_planta = st.session_state.get("gerencia_cv_planta")

    for planta in plantas:
        icono, cantidad, _ = _estado_planta(
            df,
            centro,
            edificio,
            planta,
        )

        etiqueta = (
            "T"
            if planta == "Terrado"
            else planta.replace("Planta ", "P")
        )

        contador = "✓" if cantidad == 0 else f"({cantidad})"

        seleccionada = (
            centro == seleccionado_centro
            and edificio == seleccionado_edificio
            and planta == seleccionado_planta
        )

        st.button(
            f"{icono} {etiqueta} {contador}",
            key=f"cv_visual_{centro}_{edificio}_{planta}",
            use_container_width=True,
            on_click=_seleccionar_planta_cv,
            args=(centro, edificio, planta),
            type="primary" if seleccionada else "secondary",
        )

    st.markdown(
        (
            '<div class="cv-map-ground">'
            '<div class="cv-map-door"></div>'
            '</div>'
            '<div class="cv-map-base"></div>'
        ),
        unsafe_allow_html=True,
    )


def _pintar_anexo_visual_gerencia(df):
    zonas = EDIFICIOS_GERENCIA[
        "Pearson 9"
    ]["Anexo Servicios"]

    st.markdown(
        (
            '<div class="cv-map-annex-wrap">'
            '<div class="cv-map-annex-title">'
            'ANEXO SERVICIOS · PLANTA ÚNICA'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    iconos_zona = {
        "Taller": "🔧",
        "Vestuarios chicas": "🚿",
        "Sala calderas": "🔥",
        "Vestuarios chicos": "🚿",
    }

    seleccionado_centro = st.session_state.get("gerencia_cv_centro")
    seleccionado_edificio = st.session_state.get("gerencia_cv_edificio")
    seleccionado_planta = st.session_state.get("gerencia_cv_planta")

    with st.container(key="gerencia_anexo_p9"):
        columnas = st.columns(
            len(zonas),
            gap="small",
        )

        for columna, zona in zip(
            columnas,
            zonas,
        ):
            icono_estado, cantidad, _ = _estado_planta(
                df,
                "Pearson 9",
                "Anexo Servicios",
                zona,
            )

            contador = "✓" if cantidad == 0 else f"({cantidad})"
            icono_zona = iconos_zona.get(zona, "📍")

            seleccionada = (
                seleccionado_centro == "Pearson 9"
                and seleccionado_edificio == "Anexo Servicios"
                and seleccionado_planta == zona
            )

            with columna:
                st.button(
                    f"{icono_estado} {icono_zona} {zona} {contador}",
                    key=f"cv_visual_p9_anexo_{zona}",
                    use_container_width=True,
                    on_click=_seleccionar_planta_cv,
                    args=(
                        "Pearson 9",
                        "Anexo Servicios",
                        zona,
                    ),
                    type="primary" if seleccionada else "secondary",
                )


def mostrar_mapa_visual_centro_gerencia(
    df,
    centro,
):
    """
    Mapa visual compacto para Gerencia.

    Pearson 22:
      Infantil/Primaria + Llar, como edificios reales.

    Pearson 9:
      A + B + C en una fila y Anexo Servicios debajo.
    """
    st.markdown(
        f'<div class="cv-map-campus-title">{centro}</div>',
        unsafe_allow_html=True,
    )

    clave_mapa = (
        "gerencia_mapa_edificios_p9"
        if centro == "Pearson 9"
        else "gerencia_mapa_edificios_p22"
    )

    with st.container(key=clave_mapa):
        if centro == "Pearson 9":
            columnas = st.columns(
                3,
                gap="small",
            )

            for columna, edificio in zip(
                columnas,
                [
                    "Edificio A",
                    "Edificio B",
                    "Edificio C",
                ],
            ):
                with columna:
                    _pintar_edificio_visual_gerencia(
                        df,
                        centro,
                        edificio,
                        EDIFICIOS_GERENCIA[
                            centro
                        ][edificio],
                    )

            _pintar_anexo_visual_gerencia(df)
            return

        # Pearson 22
        columnas = st.columns(
            [1.15, 1],
            gap="small",
        )

        with columnas[0]:
            _pintar_edificio_visual_gerencia(
                df,
                "Pearson 22",
                "Infantil / Primaria",
                EDIFICIOS_GERENCIA[
                    "Pearson 22"
                ]["Infantil / Primaria"],
            )

        with columnas[1]:
            _pintar_edificio_visual_gerencia(
                df,
                "Pearson 22",
                "Llar",
                EDIFICIOS_GERENCIA[
                    "Pearson 22"
                ]["Llar"],
            )


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

    areas = (
        activas["area"]
        .fillna("Sin área")
        .replace("", "Sin área")
        .value_counts()
        .head(5)
    )

    maximo = max(int(areas.max()), 1)

    for area, cantidad in areas.items():
        cantidad = int(cantidad)
        progreso = cantidad / maximo

        c1, c2 = st.columns([1.25, 3.75])

        with c1:
            st.markdown(f"**{area}**")

        with c2:
            st.progress(
                progreso,
                text=str(cantidad),
            )


def mostrar_panel_planta_cv(df):
    centro = st.session_state["gerencia_cv_centro"]
    edificio = st.session_state["gerencia_cv_edificio"]
    planta = st.session_state["gerencia_cv_planta"]
    datos = filtrar_por_ubicacion_gerencia(df, centro, edificio, planta)
    activas = _activas_gerencia(datos)
    urgentes = _urgentes_gerencia(activas)
    en_curso = activas[activas["estado"].isin(["En curso", "En ejecución"])] if not activas.empty else activas
    cerradas_mes = _cerradas_mes_planta(datos)

    texto_contexto = (
        "Situación operativa de la zona seleccionada"
        if edificio == "Anexo Servicios"
        else "Situación operativa de la planta seleccionada"
    )

    st.markdown(
        f"<div class='cv-panel-title'>📍 {centro} · {edificio} · {planta}</div>"
        f"<div class='cv-panel-subtitle'>{texto_contexto}</div>",
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
        st.markdown("#### Actuación que requiere más atención")

        if activas.empty:
            st.success("No hay actuaciones pendientes.")

        else:
            candidatos = (
                urgentes
                if not urgentes.empty
                else activas
            )

            candidatos = candidatos.sort_values(
                ["fecha_dt"],
                ascending=True,
                na_position="last",
            )

            fila = candidatos.iloc[0]

            descripcion_prioritaria = str(
                fila.get("descripcion", "")
                or "Actuación pendiente"
            ).strip()

            espacio_prioritario = str(
                fila.get("espacio", "")
                or planta
            ).strip()

            prioridad_prioritaria = str(
                fila.get("prioridad", "")
                or "Prioridad pendiente de valorar"
            ).strip()

            numero_ot_prioritaria = str(
                fila.get("numero_ot", "")
                or ""
            ).strip()

            with st.container(border=True):
                st.markdown(
                    f"**{descripcion_prioritaria}**"
                )

                st.caption(
                    f"📍 {espacio_prioritario}"
                )

                st.markdown(
                    f"**{prioridad_prioritaria}**"
                    + (
                        f" · `{numero_ot_prioritaria}`"
                        if numero_ot_prioritaria
                        else ""
                    )
                )

            st.caption(
                "Esta referencia es para seguimiento de Gerencia. "
                "La prioridad operativa la determina el ❤️ Corazón."
            )

    if edificio == "Anexo Servicios":
        st.markdown("#### Incidencias de esta zona")
    else:
        st.markdown("#### Incidencias de esta planta")

    if activas.empty:
        if edificio == "Anexo Servicios":
            st.success("Zona sin incidencias activas.")
        else:
            st.success("Planta sin incidencias activas.")
    else:
        columnas = [
            "numero_ot",
            "descripcion",
            "area",
            "prioridad",
            "estado",
        ]
        
        vista = (
            activas
            .sort_values(
                "fecha_dt",
                ascending=False,
                na_position="last",
            )[columnas]
            .copy()
        )
        
        vista.columns = [
            "OT",
            "Descripción",
            "Área",
            "Prioridad",
            "Estado",
        ]
        
        st.dataframe(
            vista,
            use_container_width=True,
            hide_index=True,
            height=238,
        )


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


def mostrar_colegio_vivo_gerencia(
    df,
    centro_objetivo=None,
):
    centro_objetivo = str(
        centro_objetivo or ""
    ).strip()

    if centro_objetivo not in EDIFICIOS_GERENCIA:
        centro_objetivo = None

    _iniciar_seleccion_colegio_vivo(
        df,
        centro_objetivo=centro_objetivo,
    )

    # =================================================
    # PERFIL GERENCIA · UN SOLO CENTRO
    # =================================================
    if centro_objetivo:
        icono_centro, estado_centro, total_centro = (
            _estado_centro_cv(
                df,
                centro_objetivo,
            )
        )

        st.markdown(
            f"<div class='cv-hero'><div>"
            f"<div class='cv-title'>🏫 {centro_objetivo}</div>"
            f"<div class='cv-subtitle'>"
            f"Gerencia · Colegio vivo · Estado operativo del centro"
            f"</div></div>"
            f"<div class='cv-status'>"
            f"{icono_centro} {estado_centro}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        st.info(
            f"{icono_centro} **{centro_objetivo} · "
            f"{estado_centro}** · "
            f"{total_centro} actuaciones activas"
        )

        mostrar_cabecera_simple_gerencia(
            df,
            centro_objetivo,
        )

        izquierda, derecha = st.columns(
            [1.08, 1.35],
            gap="large",
        )

        with izquierda:
            st.markdown(
                "<div class='cv-section'>"
                "Mapa operativo del centro"
                "</div>",
                unsafe_allow_html=True,
            )

            st.caption(
                "Pulsa una planta o zona para ver sus datos. "
                "El color refleja el riesgo, no solo la cantidad."
            )

            mostrar_mapa_visual_centro_gerencia(
                df,
                centro_objetivo,
            )

        with derecha:
            with st.container(border=True):
                mostrar_panel_planta_cv(df)

        mostrar_capa_ejecutiva_gerencia(df, centro_objetivo)

        mostrar_resumen_inferior_cv(df)

        with st.expander(
            "📈 Evolución, inventario y detalle ejecutivo",
            expanded=False,
        ):
            mostrar_evolucion_mantenimiento(
                df,
                centro_objetivo,
            )

            total_inv = total_inventario_centro(
                centro_objetivo
            )
            total_usado = total_utilizado_centro(
                centro_objetivo,
                df,
            )

            c1, c2 = st.columns(2)
            c1.metric(
                "Valor de inventario",
                euros(total_inv),
            )
            c2.metric(
                "Material utilizado",
                euros(total_usado),
            )

        return

    # =================================================
    # ADMINISTRACIÓN · VISTA GLOBAL DE LOS DOS CENTROS
    # =================================================
    e22, estado22, total22 = _estado_centro_cv(
        df,
        "Pearson 22",
    )
    e9, estado9, total9 = _estado_centro_cv(
        df,
        "Pearson 9",
    )

    estado_global = "El colegio está bajo control"
    icono_global = "🟢"

    if "🔴" in [e22, e9]:
        estado_global = (
            "Hay una zona que requiere atención prioritaria"
        )
        icono_global = "🔴"

    elif "🟡" in [e22, e9]:
        estado_global = (
            "El colegio requiere seguimiento operativo"
        )
        icono_global = "🟡"

    st.markdown(
        f"<div class='cv-hero'><div>"
        f"<div class='cv-title'>🏫 Colegio vivo</div>"
        f"<div class='cv-subtitle'>"
        f"Gerencia · Estado real de Pearson 22 y Pearson 9"
        f"</div></div>"
        f"<div class='cv-status'>"
        f"{icono_global} {estado_global}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    s1, s2 = st.columns(2)

    with s1:
        st.info(
            f"{e22} **Pearson 22 · {estado22}** · "
            f"{total22} actuaciones activas"
        )

    with s2:
        st.info(
            f"{e9} **Pearson 9 · {estado9}** · "
            f"{total9} actuaciones activas"
        )

    izquierda, derecha = st.columns(
        [1.08, 1.35],
        gap="large",
    )

    with izquierda:
        st.markdown(
            "<div class='cv-section'>"
            "Mapa operativo del colegio"
            "</div>",
            unsafe_allow_html=True,
        )

        st.caption(
            "Pulsa una planta o zona para ver sus datos. "
            "El color refleja el riesgo, no solo la cantidad."
        )

        for centro in EDIFICIOS_GERENCIA:
            mostrar_mapa_visual_centro_gerencia(
                df,
                centro,
            )

    with derecha:
        with st.container(border=True):
            mostrar_panel_planta_cv(df)

    centro_ejecutivo = st.session_state["gerencia_cv_centro"]
    st.caption(f"Visión ejecutiva del centro seleccionado · {centro_ejecutivo}")
    mostrar_capa_ejecutiva_gerencia(df, centro_ejecutivo)

    mostrar_resumen_inferior_cv(df)

    with st.expander(
        "📈 Evolución, inventario y detalle ejecutivo",
        expanded=False,
    ):
        centro = st.session_state[
            "gerencia_cv_centro"
        ]

        mostrar_evolucion_mantenimiento(
            df,
            centro,
        )

        total_inv = total_inventario_centro(
            centro
        )
        total_usado = total_utilizado_centro(
            centro,
            df,
        )

        c1, c2 = st.columns(2)
        c1.metric(
            "Valor de inventario",
            euros(total_inv),
        )
        c2.metric(
            "Material utilizado",
            euros(total_usado),
        )


def pantalla_gerencia():
    aplicar_estilo_gerencia()
    aplicar_estilo_colegio_vivo()
    iniciar_estado_gerencia()

    df = preparar_ordenes()

    if df.empty:
        st.warning(
            "No hay órdenes para mostrar todavía."
        )

        df = pd.DataFrame(
            columns=[
                "numero_ot",
                "fecha_creacion",
                "fecha_cierre",
                "centro",
                "edificio",
                "planta",
                "espacio",
                "descripcion",
                "estado",
                "operario",
                "solicitante",
                "origen",
                "area",
                "prioridad",
                "origen_tabla",
                "fecha_dt",
                "fecha_cierre_dt",
            ]
        )

    detalle_actual = st.session_state.get(
        "gerencia_detalle"
    )

    if detalle_actual:
        mostrar_detalle(df)
        return

    perfil_actual = str(
        st.session_state.get("perfil")
        or ""
    ).strip().lower()

    centro_objetivo = None

    if perfil_actual == "gerencia":
        centro_objetivo = st.session_state.get(
            "gerencia_cv_centro"
        )

    mostrar_colegio_vivo_gerencia(
        df,
        centro_objetivo=centro_objetivo,
    )
