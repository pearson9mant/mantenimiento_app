import streamlit as st
import pandas as pd
from datetime import datetime

from database.db import conectar


CENTROS_GERENCIA = ["Pearson 9", "Pearson 22"]

ESTADOS_CERRADOS = [
    "Finalizada",
    "Finalizado",
    "Cerrada",
    "Cerrado"
]

ESTADOS_MATERIAL = [
    "Pendiente material",
    "Esperando material"
]


# =====================================================
# ESTILO VISUAL GERENCIA SIMPLE
# =====================================================

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

    .gerencia-title {
        font-size: 30px;
        font-weight: 900;
        margin-bottom: 4px;
    }

    .gerencia-subtitle {
        font-size: 16px;
        font-weight: 600;
        opacity: 0.92;
    }

    .gerencia-section-title {
        font-size: 24px;
        font-weight: 900;
        color: #0f172a;
        margin-top: 20px;
        margin-bottom: 12px;
    }

    .gerencia-card-info {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 14px 16px;
        margin-bottom: 14px;
        color: #334155;
        font-weight: 700;
    }

    div.stButton > button {
        min-height: 86px;
        border-radius: 20px;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
        font-size: 17px;
        font-weight: 900;
        color: #0f172a;
        white-space: pre-line;
    }

    div.stButton > button:hover {
        border: 1px solid #2563eb;
        background: #eff6ff;
        color: #1d4ed8;
    }

    @media (max-width: 768px) {
        .gerencia-title {
            font-size: 24px;
        }

        .gerencia-subtitle {
            font-size: 14px;
        }

        .gerencia-hero {
            padding: 20px 18px;
            border-radius: 20px;
        }

        div.stButton > button {
            min-height: 74px;
            font-size: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# =====================================================
# ESTADO NAVEGACIÓN
# =====================================================

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


# =====================================================
# LECTURA DATOS
# =====================================================

@st.cache_data(ttl=60)
def leer_tabla(nombre_tabla):
    conn = conectar()

    try:
        df = pd.read_sql_query(f"SELECT * FROM {nombre_tabla}", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


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


# =====================================================
# INVENTARIO
# =====================================================

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
    movimientos.loc[
        movimientos["fecha_mostrar"].str.strip() == "",
        "fecha_mostrar"
    ] = movimientos["fecha_movimiento"].fillna("").astype(str)

    movimientos["numero_ot_mostrar"] = movimientos["numero_ot"].fillna("").astype(str)
    movimientos.loc[
        movimientos["numero_ot_mostrar"].str.strip() == "",
        "numero_ot_mostrar"
    ] = movimientos["ot"].fillna("").astype(str)

    movimientos.loc[
        movimientos["numero_ot_mostrar"].str.strip() == "",
        "numero_ot_mostrar"
    ] = movimientos["orden_trabajo"].fillna("").astype(str)

    movimientos["material_mostrar"] = movimientos["material"].fillna("").astype(str)

    movimientos.loc[
        movimientos["material_mostrar"].str.strip() == "",
        "material_mostrar"
    ] = movimientos["nombre_material"].fillna("").astype(str)

    movimientos.loc[
        movimientos["material_mostrar"].str.strip() == "",
        "material_mostrar"
    ] = movimientos["codigo_material"].fillna("").astype(str)

    movimientos["tipo_mostrar"] = movimientos["tipo"].fillna("").astype(str)

    movimientos.loc[
        movimientos["tipo_mostrar"].str.strip() == "",
        "tipo_mostrar"
    ] = movimientos["movimiento"].fillna("").astype(str)

    movimientos.loc[
        movimientos["tipo_mostrar"].str.strip() == "",
        "tipo_mostrar"
    ] = movimientos["tipo_movimiento"].fillna("").astype(str)

    movimientos["observaciones_mostrar"] = movimientos["observaciones"].fillna("").astype(str)

    movimientos.loc[
        movimientos["observaciones_mostrar"].str.strip() == "",
        "observaciones_mostrar"
    ] = movimientos["motivo"].fillna("").astype(str)

    # =====================================================
    # NUMÉRICOS SEGUROS FLOAT
    # =====================================================

    movimientos["cantidad_num"] = pd.to_numeric(
        movimientos["cantidad"],
        errors="coerce"
    ).fillna(0).astype(float)

    movimientos["precio_num"] = pd.to_numeric(
        movimientos["precio_unitario"],
        errors="coerce"
    ).fillna(0).astype(float)

    movimientos["coste_total_num"] = pd.to_numeric(
        movimientos["coste_total"],
        errors="coerce"
    ).fillna(0).astype(float)

    if movimientos["coste_total_num"].sum() == 0:
        movimientos["coste_total_num"] = pd.to_numeric(
            movimientos["coste"],
            errors="coerce"
        ).fillna(0).astype(float)

    # =====================================================
    # RECUPERAR PRECIOS DESDE INVENTARIO
    # =====================================================

    inventario = preparar_inventario()

    if not inventario.empty:
        inv = inventario.copy()

        if "codigo" not in inv.columns:
            inv["codigo"] = ""

        inv["codigo"] = inv["codigo"].fillna("").astype(str)

        inv["material_mostrar"] = (
            inv["material_mostrar"]
            .fillna("")
            .astype(str)
        )

        inv["precio_num"] = pd.to_numeric(
            inv["precio_num"],
            errors="coerce"
        ).fillna(0).astype(float)

        # =========================
        # MAPA POR CÓDIGO
        # =========================

        mapa_codigo = inv[
            ["codigo", "precio_num"]
        ].drop_duplicates()

        mapa_codigo = mapa_codigo.rename(columns={
            "precio_num": "precio_inventario_codigo"
        })

        movimientos["codigo_material"] = (
            movimientos["codigo_material"]
            .fillna("")
            .astype(str)
        )

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

        movimientos.loc[
            movimientos["precio_num"] == 0,
            "precio_num"
        ] = movimientos["precio_inventario_codigo"]

        movimientos = movimientos.drop(
            columns=["codigo"],
            errors="ignore"
        )

        # =========================
        # MAPA POR MATERIAL
        # =========================

        mapa_material = inv[
            ["material_mostrar", "precio_num"]
        ].drop_duplicates()

        mapa_material = mapa_material.rename(columns={
            "precio_num": "precio_inventario_material"
        })

        movimientos = movimientos.merge(
            mapa_material,
            on="material_mostrar",
            how="left"
        )

        movimientos["precio_inventario_material"] = pd.to_numeric(
            movimientos["precio_inventario_material"],
            errors="coerce"
        ).fillna(0).astype(float)

        movimientos.loc[
            movimientos["precio_num"] == 0,
            "precio_num"
        ] = movimientos["precio_inventario_material"]

    # =====================================================
    # ASEGURAR FLOATS ANTES DEL CÁLCULO
    # =====================================================

    movimientos["cantidad_num"] = pd.to_numeric(
        movimientos["cantidad_num"],
        errors="coerce"
    ).fillna(0).astype(float)

    movimientos["precio_num"] = pd.to_numeric(
        movimientos["precio_num"],
        errors="coerce"
    ).fillna(0).astype(float)

    movimientos["coste_total_num"] = pd.to_numeric(
        movimientos["coste_total_num"],
        errors="coerce"
    ).fillna(0).astype(float)

    # =====================================================
    # CALCULAR COSTE SI FALTA
    # =====================================================

    movimientos.loc[
        movimientos["coste_total_num"] == 0,
        "coste_total_num"
    ] = (
        movimientos["cantidad_num"].abs()
        * movimientos["precio_num"]
    )

    # =====================================================
    # FILTRAR SOLO SALIDAS / USOS
    # =====================================================

    texto_tipo = (
        movimientos["tipo_mostrar"]
        .fillna("")
        .astype(str)
        .str.lower()
    )

    usados = movimientos[
        texto_tipo.str.contains(
            "salida|uso|utilizado|consumo|retirada|descuento",
            na=False
        )
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


# =====================================================
# FILTROS Y CONTADORES
# =====================================================

def es_cerrada(df):
    return (
        df["estado"].isin(ESTADOS_CERRADOS)
        | (df["origen_tabla"] == "historico")
    )


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
    return df["estado"].isin([
        "Pendiente material",
        "Esperando material"
    ])


def filtrar_realizadas_mes(df, origen_busqueda):
    if df.empty:
        return df

    hoy = datetime.today()
    mes_actual = hoy.month
    año_actual = hoy.year

    datos = df[es_cerrada(df)].copy()

    if datos.empty:
        return datos

    fecha_ref = datos["fecha_cierre_dt"]

    if fecha_ref.isna().all():
        fecha_ref = datos["fecha_dt"]

    datos = datos[
        (fecha_ref.dt.month == mes_actual)
        & (fecha_ref.dt.year == año_actual)
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

    if tipo == "material":
        return datos[es_esperando_material(datos)]

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

def buscador_dataframe(df, key, placeholder="Buscar..."):
    if df.empty:
        return df

    busqueda = st.text_input(
        "🔎 Buscador",
        placeholder=placeholder,
        key=key
    )

    if not busqueda:
        return df

    texto = busqueda.strip().lower()

    datos = df.copy()

    # Buscar texto normal en todas las columnas
    texto_general = (
        datos.astype(str)
        .fillna("")
        .apply(lambda col: col.str.lower())
    )

    mascara_texto = texto_general.apply(
        lambda col: col.str.contains(texto, na=False)
    ).any(axis=1)

    # Buscar también por fechas en varios formatos
    mascara_fecha = pd.Series(False, index=datos.index)

    columnas_fecha = [
        col for col in datos.columns
        if "fecha" in str(col).lower()
    ]

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

        mascara_columna = formatos_fecha.fillna("").apply(
            lambda c: c.str.lower().str.contains(texto, na=False)
        ).any(axis=1)

        mascara_fecha = mascara_fecha | mascara_columna

    return datos[mascara_texto | mascara_fecha]


# =====================================================
# NAVEGACIÓN / BOTONES
# =====================================================

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


# =====================================================
# PANTALLAS
# =====================================================

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


def mostrar_menu_centro(df, centro):
    st.markdown(
        f"<div class='gerencia-section-title'>🏫 {centro}</div>",
        unsafe_allow_html=True
    )

    if st.button("⬅️ Volver a centros", use_container_width=True, key="volver_centros_gerencia"):
        volver_a_centros()

    st.markdown(
        "<div class='gerencia-card-info'>Pulsa una tarjeta para ver solo ese detalle.</div>",
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        boton_tarjeta(
            "Órdenes abiertas",
            contar(df, centro, "abiertas"),
            centro,
            "abiertas",
            "📂"
        )

    with c2:
        boton_tarjeta(
            "En curso",
            contar(df, centro, "en_curso"),
            centro,
            "en_curso",
            "🟡"
        )

    with c3:
        boton_tarjeta(
            "Pendiente material",
            contar(df, centro, "material"),
            centro,
            "material",
            "📦"
        )

    with c4:
        boton_tarjeta(
            "Órdenes cerradas",
            contar(df, centro, "cerradas"),
            centro,
            "cerradas",
            "✅"
        )

    c3, c4 = st.columns(2)

    with c3:
        boton_tarjeta(
            "Legionella este mes",
            contar(df, centro, "legionella_mes"),
            centro,
            "legionella_mes",
            "💧"
        )

    with c4:
        boton_tarjeta(
            "Preventivas este mes",
            contar(df, centro, "preventivas_mes"),
            centro,
            "preventivas_mes",
            "🛠️"
        )

    st.markdown("### 💶 Inventario")

    total_inv = total_inventario_centro(centro)
    total_usado = total_utilizado_centro(centro, df)

    c5, c6 = st.columns(2)

    with c5:
        boton_tarjeta_dinero(
            "Total inventario",
            total_inv,
            centro,
            "inventario_total",
            "💰"
        )

    with c6:
        boton_tarjeta_dinero(
            "Material utilizado",
            total_usado,
            centro,
            "inventario_utilizado",
            "📉"
        )


# =====================================================
# DETALLES
# =====================================================

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

    st.dataframe(
        datos[columnas],
        use_container_width=True,
        hide_index=True
    )


def mostrar_detalle_inventario_total(centro):
    inventario = preparar_inventario()
    datos = filtrar_inventario_por_centro(inventario, centro)

    if datos.empty:
        st.info("No hay inventario registrado para mostrar.")
        return

    columnas = [
        "codigo",
        "material_mostrar",
        "categoria",
        "stock_num",
        "precio_num",
        "valor_total",
        "ubicacion",
        "fecha_compra",
    ]

    columnas = [c for c in columnas if c in datos.columns]

    st.metric("💰 Total inventario", euros(datos["valor_total"].sum()))

    st.dataframe(
        datos[columnas],
        use_container_width=True,
        hide_index=True
    )


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

    st.dataframe(
        datos[columnas],
        use_container_width=True,
        hide_index=True
    )


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
# PANTALLA PRINCIPAL
# =====================================================

def pantalla_gerencia():
    aplicar_estilo_gerencia()
    iniciar_estado_gerencia()

    st.markdown("""
    <div class="gerencia-hero">
        <div class="gerencia-title">📊 Gerencia</div>
        <div class="gerencia-subtitle">
            Vista por centro: órdenes, Legionella, preventivas e inventario
        </div>
    </div>
    """, unsafe_allow_html=True)

    df = preparar_ordenes()

    if df.empty:
        st.warning("No hay órdenes para mostrar todavía.")
        df = pd.DataFrame()

    centro_actual = st.session_state.get("gerencia_centro")
    detalle_actual = st.session_state.get("gerencia_detalle")

    if not centro_actual:
        mostrar_selector_centros()
        return

    if detalle_actual:
        mostrar_detalle(df)
        return

    mostrar_menu_centro(df, centro_actual)
