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

    .cv-annex {
        border:1px solid #dbe3ef;
        border-radius:16px;
        padding:10px 10px 8px;
        background:#fff;
        box-shadow:0 5px 16px rgba(15,23,42,.06);
        margin-top:10px;
        margin-bottom:8px;
    }

    .cv-annex-title {
        background:linear-gradient(180deg,#173a6e,#0e284d);
        color:#fff;
        border:3px solid #d9caa7;
        border-radius:10px 10px 0 0;
        text-align:center;
        padding:8px 10px;
        font-size:13px;
        font-weight:950;
        letter-spacing:.25px;
        margin-bottom:6px;
    }

    .cv-panel {
        border:1px solid #dbe3ef;border-radius:18px;padding:14px 16px;background:#fff;
        box-shadow:0 8px 22px rgba(15,23,42,.07);
    }
    .cv-panel-title {font-size:21px;font-weight:900;color:#0f172a;margin-bottom:2px}
    .cv-panel-subtitle {font-size:13px;color:#64748b;font-weight:650;margin-bottom:10px}
    .cv-priority {
        border:1px solid #fecaca;background:#fff7f7;border-radius:14px;padding:11px 13px;
        margin-top:6px;
    }
    .cv-priority-title {font-size:16px;font-weight:900;color:#991b1b}
    .cv-priority-text {font-size:13px;color:#334155;margin-top:3px}
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
        .cv-annex-title{font-size:12px;padding:7px 8px}
    }

    @media (max-width: 760px) {
        .st-key-gerencia_anexo_p9 div[data-testid="stHorizontalBlock"]{
            flex-wrap:wrap !important;
            gap:4px !important;
        }

        .st-key-gerencia_anexo_p9 div[data-testid="stHorizontalBlock"] > div{
            flex:1 1 calc(50% - 4px) !important;
            min-width:calc(50% - 4px) !important;
            max-width:calc(50% - 4px) !important;
        }

        .st-key-gerencia_anexo_p9 div[data-testid="stButton"] > button{
            min-height:52px !important;
            white-space:normal !important;
            text-align:center !important;
            justify-content:center !important;
            line-height:1.15 !important;
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


def mostrar_anexo_servicios_cv(df, centro="Pearson 9"):
    """
    Dibuja el Anexo Servicios de Pearson 9 como una franja independiente,
    no como un cuarto edificio.

    Mantiene la misma selección y el mismo panel de detalle que el resto
    del Colegio Vivo.
    """
    zonas = EDIFICIOS_GERENCIA["Pearson 9"]["Anexo Servicios"]

    seleccionado_edificio = st.session_state.get("gerencia_cv_edificio")
    seleccionado_planta = st.session_state.get("gerencia_cv_planta")
    seleccionado_centro = st.session_state.get("gerencia_cv_centro")

    st.markdown(
        "<div class='cv-annex'>"
        "<div class='cv-annex-title'>"
        "ANEXO SERVICIOS · PLANTA ÚNICA"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    with st.container(key="gerencia_anexo_p9"):
        columnas = st.columns(
            len(zonas),
            gap="small",
        )

        iconos_zona = {
            "Taller": "🔧",
            "Vestuarios chicas": "🚿",
            "Sala calderas": "🔥",
            "Vestuarios chicos": "🚿",
        }

        for columna, zona in zip(columnas, zonas):
            icono_estado, cantidad, _ = _estado_planta(
                df,
                centro,
                "Anexo Servicios",
                zona,
            )

            sufijo = f"\n{cantidad}" if cantidad else "\nOK"

            seleccionada = (
                centro == seleccionado_centro
                and seleccionado_edificio == "Anexo Servicios"
                and seleccionado_planta == zona
            )

            prefijo = "▸ " if seleccionada else ""
            icono_zona = iconos_zona.get(zona, "📍")

            with columna:
                st.button(
                    f"{prefijo}{icono_estado} {icono_zona} {zona}{sufijo}",
                    key=f"cv_{centro}_anexo_{zona}",
                    use_container_width=True,
                    on_click=_seleccionar_planta_cv,
                    args=(
                        centro,
                        "Anexo Servicios",
                        zona,
                    ),
                    type="primary" if seleccionada else "secondary",
                )


def mostrar_mapa_centro_cv(df, centro):
    """
    Renderiza la estructura física del centro.

    Pearson 9:
    - A/B/C como edificios.
    - Anexo Servicios como franja independiente.

    Pearson 22 mantiene exactamente su representación actual.
    """
    edificios = EDIFICIOS_GERENCIA[centro]

    if centro == "Pearson 9":
        for edificio in [
            "Edificio A",
            "Edificio B",
            "Edificio C",
        ]:
            mostrar_edificio_cv(
                df,
                centro,
                edificio,
                edificios[edificio],
            )

        mostrar_anexo_servicios_cv(
            df,
            centro="Pearson 9",
        )
        return

    for edificio, plantas in edificios.items():
        mostrar_edificio_cv(
            df,
            centro,
            edificio,
            plantas,
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
        st.markdown("#### Actuación prioritaria")
        if activas.empty:
            st.success("No hay actuaciones pendientes.")
        else:
            candidatos = urgentes if not urgentes.empty else activas
            candidatos = candidatos.sort_values(["fecha_dt"], ascending=True, na_position="last")
            fila = candidatos.iloc[0]
            st.markdown(
                f"<div class='cv-priority'><div class='cv-priority-title'>"
                f"{fila.get('descripcion','') or 'Actuación pendiente'}</div>"
                f"<div class='cv-priority-text'>📍 {fila.get('espacio','') or planta}<br>"
                f"{fila.get('prioridad','') or 'Prioridad pendiente de valorar'} · "
                f"{fila.get('numero_ot','') or ''}</div></div>",
                unsafe_allow_html=True,
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
        columnas = ["numero_ot", "descripcion", "area", "prioridad", "estado"]
        vista = activas.sort_values("fecha_dt", ascending=True, na_position="last").head(6)[columnas].copy()
        vista.columns = ["OT", "Descripción", "Área", "Prioridad", "Estado"]
        st.dataframe(vista, use_container_width=True, hide_index=True, height=238)


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

            mostrar_mapa_centro_cv(
                df,
                centro_objetivo,
            )

        with derecha:
            with st.container(border=True):
                mostrar_panel_planta_cv(df)

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
            st.markdown(
                f"**{centro}**"
            )

            mostrar_mapa_centro_cv(
                df,
                centro,
            )

    with derecha:
        with st.container(border=True):
            mostrar_panel_planta_cv(df)

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
