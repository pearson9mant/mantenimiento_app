import streamlit as st
import pandas as pd
from datetime import date, timedelta
from html import escape

from database.db import conectar, _sql
from config import CENTROS, OPERARIOS


ESTADOS_VERANO = [
    "Planificado",
    "Pendiente material",
    "Avisado",
    "En ejecución",
    "Finalizado",
    "Retrasado"
]

PRIORIDADES_VERANO = ["Baja", "Media", "Alta", "Urgente"]

MESES_VERANO = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12
}

COLORES_OPERARIOS = {
    "J.A. Almeda": "#2563eb",
    "Luis Lozano": "#7c3aed",
    "Abel Vasquez": "#ea580c",
    "Empresa externa": "#16a34a",
    "Otro": "#64748b",
    "Sin operarios": "#94a3b8"
}


# =====================================================
# BASE DE DATOS
# =====================================================

def es_postgres():
    try:
        from database.db import _es_postgres
        return _es_postgres()
    except Exception:
        return False


def asegurar_tabla_plan_verano():
    conn = conectar()
    cursor = conn.cursor()

    if es_postgres():
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plan_verano (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                descripcion TEXT,
                centro TEXT,
                edificio TEXT,
                zona TEXT,
                responsable TEXT,
                empresa_externa TEXT,
                fecha_inicio TEXT,
                fecha_fin TEXT,
                prioridad TEXT,
                estado TEXT,
                observaciones TEXT,
                creado_por TEXT,
                fecha_creacion TEXT
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plan_verano (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT,
                descripcion TEXT,
                centro TEXT,
                edificio TEXT,
                zona TEXT,
                responsable TEXT,
                empresa_externa TEXT,
                fecha_inicio TEXT,
                fecha_fin TEXT,
                prioridad TEXT,
                estado TEXT,
                observaciones TEXT,
                creado_por TEXT,
                fecha_creacion TEXT
            )
        """)

    conn.commit()
    conn.close()


def crear_trabajo_verano(datos):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        INSERT INTO plan_verano (
            titulo, descripcion, centro, edificio, zona,
            responsable, empresa_externa, fecha_inicio, fecha_fin,
            prioridad, estado, observaciones, creado_por, fecha_creacion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """), (
        datos["titulo"],
        datos["descripcion"],
        datos["centro"],
        datos["edificio"],
        datos["zona"],
        datos["responsable"],
        datos["empresa_externa"],
        str(datos["fecha_inicio"]),
        str(datos["fecha_fin"]),
        datos["prioridad"],
        datos["estado"],
        datos["observaciones"],
        datos["creado_por"],
        str(date.today())
    ))

    conn.commit()
    conn.close()


def obtener_plan_verano():
    conn = conectar()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM plan_verano ORDER BY fecha_inicio ASC",
            conn
        )
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


def actualizar_trabajo_verano(id_trabajo, fecha_inicio, fecha_fin, estado):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE plan_verano
        SET fecha_inicio = ?, fecha_fin = ?, estado = ?
        WHERE id = ?
    """), (
        str(fecha_inicio),
        str(fecha_fin),
        estado,
        id_trabajo
    ))

    conn.commit()
    conn.close()


def borrar_trabajo_verano(id_trabajo):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        DELETE FROM plan_verano
        WHERE id = ?
    """), (id_trabajo,))

    conn.commit()
    conn.close()


# =====================================================
# UTILIDADES
# =====================================================

def lista_centros():
    if isinstance(CENTROS, dict):
        return list(CENTROS.keys())
    return CENTROS


def lista_operarios_plan():
    base = list(OPERARIOS)
    extra = ["Empresa externa", "Otro"]

    resultado = []
    for op in base + extra:
        if op not in resultado:
            resultado.append(op)

    return resultado


def texto_seguro(valor):
    if pd.isna(valor):
        return ""
    return str(valor)


def obtener_operarios_de_texto(texto):
    texto = texto_seguro(texto).strip()

    if not texto:
        return ["Sin operarios"]

    partes = [p.strip() for p in texto.split(",") if p.strip()]
    return partes if partes else ["Sin operarios"]


def color_operario(nombre):
    return COLORES_OPERARIOS.get(nombre, "#0f766e")


def color_fondo_estado(estado):
    estado = str(estado or "")

    if estado == "Finalizado":
        return "#f0fdf4"

    if estado == "Retrasado":
        return "#fef2f2"

    if estado == "En ejecución":
        return "#eff6ff"

    if estado == "Pendiente material":
        return "#fffbeb"

    return "#ffffff"


def color_borde_estado(estado):
    estado = str(estado or "")

    if estado == "Finalizado":
        return "#22c55e"

    if estado == "Retrasado":
        return "#ef4444"

    if estado == "En ejecución":
        return "#2563eb"

    if estado == "Pendiente material":
        return "#f59e0b"

    return "#e5e7eb"


def lunes_de_semana(fecha):
    return fecha - timedelta(days=fecha.weekday())


def semanas_del_mes(año, mes):
    primer_dia = date(año, mes, 1)

    if mes == 12:
        ultimo_dia = date(año + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(año, mes + 1, 1) - timedelta(days=1)

    inicio = lunes_de_semana(primer_dia)
    semanas = []

    actual = inicio
    while actual <= ultimo_dia:
        semanas.append([actual + timedelta(days=i) for i in range(7)])
        actual += timedelta(days=7)

    return semanas


def trabajo_activo_en_dia(fila, dia):
    inicio = fila["fecha_inicio_dt"].date()
    fin = fila["fecha_fin_dt"].date()
    return inicio <= dia <= fin


def nombres_operarios_compacto(operarios):
    if not operarios:
        return "Sin operarios"

    if len(operarios) <= 2:
        return " · ".join(operarios)

    return " · ".join(operarios[:2]) + f" +{len(operarios) - 2}"


def barra_colores_operarios(operarios):
    if not operarios:
        operarios = ["Sin operarios"]

    ancho = 100 / len(operarios)
    bloques = ""

    for op in operarios:
        bloques += (
            f"<div style='width:{ancho}%;"
            f"height:9px;"
            f"background:{color_operario(op)};'></div>"
        )

    return (
        "<div style='display:flex;width:100%;overflow:hidden;"
        "border-radius:12px 12px 0 0;margin:-8px -8px 8px -8px;'>"
        f"{bloques}"
        "</div>"
    )


def tarjeta_trabajo_html(fila):
    titulo = escape(texto_seguro(fila.get("titulo", "")))
    centro = escape(texto_seguro(fila.get("centro", "")))
    edificio = escape(texto_seguro(fila.get("edificio", "")))
    zona = escape(texto_seguro(fila.get("zona", "")))
    estado = escape(texto_seguro(fila.get("estado", "")))
    prioridad = escape(texto_seguro(fila.get("prioridad", "")))
    empresa = escape(texto_seguro(fila.get("empresa_externa", "")))
    responsable = texto_seguro(fila.get("responsable", ""))

    operarios = obtener_operarios_de_texto(responsable)

    fechas = (
        f"{fila['fecha_inicio_dt'].strftime('%d/%m')}"
        f" → "
        f"{fila['fecha_fin_dt'].strftime('%d/%m')}"
    )

    empresa_html = ""
    if empresa:
        empresa_html = f"<div class='pv-detalle'>🏢 {empresa}</div>"

    return f"""
    <div class="pv-tarea"
         style="background:{color_fondo_estado(estado)};
                border-color:{color_borde_estado(estado)};">
        {barra_colores_operarios(operarios)}
        <div class="pv-titulo">{titulo}</div>
        <div class="pv-detalle">👥 {escape(nombres_operarios_compacto(operarios))}</div>
        <div class="pv-detalle">📍 {centro}</div>
        <div class="pv-detalle">{edificio} · {zona}</div>
        <div class="pv-detalle">📅 {fechas}</div>
        <div class="pv-estado">{estado} · {prioridad}</div>
        {empresa_html}
    </div>
    """


def pintar_estilos_plan_verano():
    st.markdown("""
    <style>
    .pv-card-dia {
        background:#ffffff;
        border:1px solid #e5e7eb;
        border-radius:16px;
        min-height:230px;
        padding:9px;
        box-shadow:0 4px 12px rgba(15, 23, 42, 0.06);
        margin-bottom:12px;
    }

    .pv-card-dia-fuera {
        background:#f8fafc;
        opacity:0.45;
    }

    .pv-cabecera-dia {
        background:#0f172a;
        color:#ffffff;
        border-radius:14px;
        padding:8px;
        text-align:center;
        font-size:13px;
        font-weight:950;
        margin-bottom:8px;
    }

    .pv-dia-header {
        font-size:13px;
        font-weight:950;
        color:#0f172a;
        border-bottom:1px solid #e5e7eb;
        padding-bottom:6px;
        margin-bottom:8px;
    }

    .pv-dia-num {
        font-size:20px;
        font-weight:950;
    }

    .pv-tarea {
        border:2px solid #e5e7eb;
        border-radius:15px;
        padding:8px;
        margin-bottom:9px;
        box-shadow:0 3px 8px rgba(15, 23, 42, 0.08);
        overflow:hidden;
    }

    .pv-titulo {
        font-size:12px;
        font-weight:950;
        color:#0f172a;
        line-height:1.2;
        margin-bottom:5px;
        text-transform:uppercase;
    }

    .pv-detalle {
        font-size:10.5px;
        color:#334155;
        font-weight:700;
        line-height:1.25;
        margin-top:2px;
    }

    .pv-estado {
        display:inline-block;
        margin-top:5px;
        padding:3px 7px;
        border-radius:999px;
        background:#e2e8f0;
        color:#334155;
        font-size:10px;
        font-weight:900;
    }

    .pv-sin-trabajos {
        color:#94a3b8;
        font-size:12px;
        font-weight:700;
        margin-top:8px;
    }

    .pv-mes-titulo {
        font-size:24px;
        font-weight:950;
        color:#0f172a;
        margin-top:18px;
        margin-bottom:12px;
    }

    .pv-leyenda-box {
        display:flex;
        align-items:center;
        gap:7px;
        background:#ffffff;
        border:1px solid #e5e7eb;
        border-radius:999px;
        padding:6px 10px;
        font-size:12px;
        font-weight:800;
        color:#334155;
        margin-bottom:6px;
    }

    .pv-punto {
        width:12px;
        height:12px;
        border-radius:999px;
        display:inline-block;
    }
    </style>
    """, unsafe_allow_html=True)


def pintar_leyenda():
    ops = lista_operarios_plan()
    cols = st.columns(len(ops))

    for i, op in enumerate(ops):
        with cols[i]:
            st.markdown(
                f"""
                <div class="pv-leyenda-box">
                    <span class="pv-punto" style="background:{color_operario(op)};"></span>
                    {escape(op)}
                </div>
                """,
                unsafe_allow_html=True
            )

# =====================================================
# PANTALLA PRINCIPAL
# =====================================================

# =====================================================
# FORMULARIOS
# =====================================================

def formulario_nuevo_trabajo(prefijo_clave="plan", finalizado=False):
    """
    Formulario común para:
    - crear trabajos planificados;
    - registrar directamente trabajos ya realizados.
    """

    titulo_expander = (
        "➕ Registrar trabajo realizado"
        if finalizado
        else "➕ Crear nuevo trabajo"
    )

    with st.expander(titulo_expander, expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            titulo = st.text_input(
                "Título del trabajo",
                key=f"{prefijo_clave}_titulo"
            )
            descripcion = st.text_area(
                "Descripción",
                key=f"{prefijo_clave}_descripcion"
            )
            centro = st.selectbox(
                "Centro",
                lista_centros(),
                key=f"{prefijo_clave}_centro"
            )
            edificio = st.text_input(
                "Edificio",
                key=f"{prefijo_clave}_edificio"
            )
            zona = st.text_input(
                "Zona / aula / sala",
                key=f"{prefijo_clave}_zona"
            )

        with col2:
            operarios_seleccionados = st.multiselect(
                "Operarios asignados",
                lista_operarios_plan(),
                max_selections=4,
                help="Puedes seleccionar hasta 4 operarios o responsables para la misma faena.",
                key=f"{prefijo_clave}_operarios"
            )

            responsable = ", ".join(operarios_seleccionados)

            empresa_externa = st.text_input(
                "Empresa externa",
                key=f"{prefijo_clave}_empresa"
            )

            if finalizado:
                fecha_inicio = st.date_input(
                    "Fecha de inicio",
                    value=date.today(),
                    key=f"{prefijo_clave}_fecha_inicio"
                )
                fecha_fin = st.date_input(
                    "Fecha de finalización",
                    value=date.today(),
                    key=f"{prefijo_clave}_fecha_fin"
                )
                prioridad = st.selectbox(
                    "Prioridad",
                    PRIORIDADES_VERANO,
                    index=1,
                    key=f"{prefijo_clave}_prioridad"
                )
                estado = "Finalizado"
                st.success("Estado: Finalizado")
            else:
                fecha_inicio = st.date_input(
                    "Fecha inicio",
                    value=date.today(),
                    key=f"{prefijo_clave}_fecha_inicio"
                )
                fecha_fin = st.date_input(
                    "Fecha fin",
                    value=date.today(),
                    key=f"{prefijo_clave}_fecha_fin"
                )
                prioridad = st.selectbox(
                    "Prioridad",
                    PRIORIDADES_VERANO,
                    index=1,
                    key=f"{prefijo_clave}_prioridad"
                )
                estado = st.selectbox(
                    "Estado",
                    ESTADOS_VERANO,
                    key=f"{prefijo_clave}_estado"
                )

        observaciones = st.text_area(
            "Observaciones",
            key=f"{prefijo_clave}_observaciones"
        )

        texto_boton = (
            "✅ Guardar trabajo realizado"
            if finalizado
            else "💾 Guardar trabajo"
        )

        if st.button(
            texto_boton,
            use_container_width=True,
            key=f"{prefijo_clave}_guardar"
        ):
            if not titulo.strip():
                st.warning("Falta el título.")
            elif not operarios_seleccionados:
                st.warning("Selecciona al menos un operario o responsable.")
            elif fecha_fin < fecha_inicio:
                st.warning("La fecha final no puede ser anterior a la fecha inicial.")
            else:
                crear_trabajo_verano({
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "centro": centro,
                    "edificio": edificio,
                    "zona": zona,
                    "responsable": responsable,
                    "empresa_externa": empresa_externa,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "prioridad": prioridad,
                    "estado": estado,
                    "observaciones": observaciones,
                    "creado_por": st.session_state.get("usuario", "")
                })

                if finalizado:
                    st.success("Trabajo realizado guardado correctamente.")
                else:
                    st.success("Trabajo creado correctamente.")

                st.rerun()


# =====================================================
# PREPARACIÓN DE DATOS
# =====================================================

def preparar_dataframe_plan(df):
    if df.empty:
        return df

    df = df.copy()
    df["fecha_inicio_dt"] = pd.to_datetime(
        df["fecha_inicio"],
        errors="coerce"
    )
    df["fecha_fin_dt"] = pd.to_datetime(
        df["fecha_fin"],
        errors="coerce"
    )

    return df.dropna(
        subset=["fecha_inicio_dt", "fecha_fin_dt"]
    )


# =====================================================
# PESTAÑA PLANIFICACIÓN
# =====================================================

def mostrar_planificacion_verano(df):
    formulario_nuevo_trabajo(
        prefijo_clave="plan_nuevo",
        finalizado=False
    )

    if df.empty:
        st.info("Todavía no hay trabajos de verano planificados.")
        return

    st.markdown("### 🔎 Filtros")

    colf1, colf2, colf3, colf4 = st.columns(4)

    with colf1:
        año = st.number_input(
            "Año",
            min_value=2025,
            max_value=2035,
            value=date.today().year,
            step=1,
            key="plan_filtro_ano"
        )

    with colf2:
        mes_nombre = st.selectbox(
            "Mes",
            list(MESES_VERANO.keys()),
            index=max(0, min(11, date.today().month - 1)),
            key="plan_filtro_mes"
        )

    with colf3:
        filtro_centro = st.selectbox(
            "Centro",
            ["Todos"] + sorted(
                df["centro"].dropna().astype(str).unique().tolist()
            ),
            key="plan_filtro_centro"
        )

    with colf4:
        filtro_operario = st.selectbox(
            "Operario",
            ["Todos"] + lista_operarios_plan(),
            key="plan_filtro_operario"
        )

    colf5, colf6, colf7 = st.columns(3)

    with colf5:
        filtro_estado = st.selectbox(
            "Estado",
            ["Todos"] + ESTADOS_VERANO,
            key="plan_filtro_estado"
        )

    with colf6:
        filtro_prioridad = st.selectbox(
            "Prioridad",
            ["Todas"] + PRIORIDADES_VERANO,
            key="plan_filtro_prioridad"
        )

    with colf7:
        ver_finalizados = st.checkbox(
            "Mostrar finalizados",
            value=True,
            key="plan_ver_finalizados"
        )

    mes_numero = MESES_VERANO[mes_nombre]
    df_filtrado = df.copy()

    if filtro_centro != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["centro"] == filtro_centro
        ]

    if filtro_operario != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["responsable"].fillna("").str.contains(
                filtro_operario,
                case=False,
                na=False,
                regex=False
            )
        ]

    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["estado"] == filtro_estado
        ]

    if filtro_prioridad != "Todas":
        df_filtrado = df_filtrado[
            df_filtrado["prioridad"] == filtro_prioridad
        ]

    if not ver_finalizados:
        df_filtrado = df_filtrado[
            df_filtrado["estado"] != "Finalizado"
        ]

    inicio_mes = date(int(año), mes_numero, 1)

    if mes_numero == 12:
        fin_mes = date(int(año) + 1, 1, 1) - timedelta(days=1)
    else:
        fin_mes = date(int(año), mes_numero + 1, 1) - timedelta(days=1)

    df_filtrado = df_filtrado[
        (df_filtrado["fecha_inicio_dt"].dt.date <= fin_mes) &
        (df_filtrado["fecha_fin_dt"].dt.date >= inicio_mes)
    ]

    if df_filtrado.empty:
        st.warning("No hay trabajos planificados para ese filtro.")
        return

    total = len(df_filtrado)
    en_ejecucion = len(
        df_filtrado[df_filtrado["estado"] == "En ejecución"]
    )
    retrasados = len(
        df_filtrado[df_filtrado["estado"] == "Retrasado"]
    )
    finalizados = len(
        df_filtrado[df_filtrado["estado"] == "Finalizado"]
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Trabajos", total)
    m2.metric("En ejecución", en_ejecucion)
    m3.metric("Retrasados", retrasados)
    m4.metric("Finalizados", finalizados)

    pintar_leyenda()

    st.markdown(
        f"<div class='pv-mes-titulo'>"
        f"📅 Calendario completo · {mes_nombre} {año}"
        f"</div>",
        unsafe_allow_html=True
    )

    dias_nombre = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo"
    ]

    cabeceras = st.columns(7)

    for i, nombre in enumerate(dias_nombre):
        with cabeceras[i]:
            st.markdown(
                f"<div class='pv-cabecera-dia'>{nombre}</div>",
                unsafe_allow_html=True
            )

    semanas = semanas_del_mes(int(año), mes_numero)

    for semana in semanas:
        columnas = st.columns(7)

        for i, dia in enumerate(semana):
            trabajos_dia = df_filtrado[
                df_filtrado.apply(
                    lambda fila: trabajo_activo_en_dia(fila, dia),
                    axis=1
                )
            ].copy()

            clase_fuera = (
                "pv-card-dia-fuera"
                if dia.month != mes_numero
                else ""
            )

            with columnas[i]:
                html_dia = f"""
                <div class="pv-card-dia {clase_fuera}">
                    <div class="pv-dia-header">
                        <span class="pv-dia-num">{dia.day}</span><br>
                        {dias_nombre[dia.weekday()]}
                    </div>
                """

                if trabajos_dia.empty:
                    html_dia += (
                        "<div class='pv-sin-trabajos'>"
                        "Sin trabajos"
                        "</div>"
                    )
                else:
                    for _, fila in trabajos_dia.iterrows():
                        html_dia += tarjeta_trabajo_html(fila)

                html_dia += "</div>"

                st.markdown(
                    html_dia,
                    unsafe_allow_html=True
                )

    st.markdown("---")
    st.markdown("### ✏️ Modificar trabajos")

    for _, fila in df_filtrado.iterrows():
        id_trabajo = int(fila["id"])
        titulo = texto_seguro(fila.get("titulo", ""))
        centro = texto_seguro(fila.get("centro", ""))

        with st.expander(f"☀️ {titulo} · {centro}"):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                nueva_fecha_inicio = st.date_input(
                    "Inicio",
                    value=fila["fecha_inicio_dt"].date(),
                    key=f"edit_inicio_{id_trabajo}"
                )

            with col2:
                nueva_fecha_fin = st.date_input(
                    "Fin",
                    value=fila["fecha_fin_dt"].date(),
                    key=f"edit_fin_{id_trabajo}"
                )

            with col3:
                estado_actual = texto_seguro(
                    fila.get("estado", "")
                )

                nuevo_estado = st.selectbox(
                    "Estado",
                    ESTADOS_VERANO,
                    index=(
                        ESTADOS_VERANO.index(estado_actual)
                        if estado_actual in ESTADOS_VERANO
                        else 0
                    ),
                    key=f"edit_estado_{id_trabajo}"
                )

            with col4:
                st.write("")
                st.write("")

                if st.button(
                    "💾 Actualizar",
                    key=f"guardar_edit_{id_trabajo}"
                ):
                    if nueva_fecha_fin < nueva_fecha_inicio:
                        st.warning(
                            "La fecha fin no puede ser anterior."
                        )
                    else:
                        actualizar_trabajo_verano(
                            id_trabajo,
                            nueva_fecha_inicio,
                            nueva_fecha_fin,
                            nuevo_estado
                        )
                        st.success("Trabajo actualizado.")
                        st.rerun()

            st.write(
                f"**Descripción:** "
                f"{texto_seguro(fila.get('descripcion', ''))}"
            )
            st.write(
                f"**Operarios:** "
                f"{texto_seguro(fila.get('responsable', ''))}"
            )
            st.write(
                f"**Empresa:** "
                f"{texto_seguro(fila.get('empresa_externa', ''))}"
            )
            st.write(
                f"**Observaciones:** "
                f"{texto_seguro(fila.get('observaciones', ''))}"
            )

            confirmar = st.checkbox(
                "Confirmar eliminación",
                key=f"confirmar_borrar_{id_trabajo}"
            )

            if confirmar:
                if st.button(
                    "🗑️ Eliminar trabajo",
                    key=f"borrar_{id_trabajo}"
                ):
                    borrar_trabajo_verano(id_trabajo)
                    st.warning("Trabajo eliminado.")
                    st.rerun()


# =====================================================
# PESTAÑA TRABAJOS TERMINADOS
# =====================================================

def mostrar_trabajos_terminados(df):
    st.caption(
        "Aquí puedes registrar trabajos ya realizados y consultar "
        "todos los que tienen estado Finalizado."
    )

    formulario_nuevo_trabajo(
        prefijo_clave="terminado_nuevo",
        finalizado=True
    )

    if df.empty:
        st.info("Todavía no hay trabajos terminados.")
        return

    terminados = df[
        df["estado"].fillna("").astype(str).str.strip() == "Finalizado"
    ].copy()

    if terminados.empty:
        st.info("Todavía no hay trabajos con estado Finalizado.")
        return

    st.markdown("### 🔎 Buscar trabajos realizados")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        años_disponibles = sorted(
            terminados["fecha_fin_dt"]
            .dt.year
            .dropna()
            .astype(int)
            .unique()
            .tolist(),
            reverse=True
        )

        filtro_ano = st.selectbox(
            "Año",
            ["Todos"] + años_disponibles,
            key="terminados_filtro_ano"
        )

    with col2:
        filtro_centro = st.selectbox(
            "Centro",
            ["Todos"] + sorted(
                terminados["centro"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            ),
            key="terminados_filtro_centro"
        )

    with col3:
        filtro_operario = st.selectbox(
            "Operario",
            ["Todos"] + lista_operarios_plan(),
            key="terminados_filtro_operario"
        )

    with col4:
        buscar = st.text_input(
            "Buscar",
            placeholder="Título, zona, edificio...",
            key="terminados_buscar"
        )

    filtrados = terminados.copy()

    if filtro_ano != "Todos":
        filtrados = filtrados[
            filtrados["fecha_fin_dt"].dt.year == int(filtro_ano)
        ]

    if filtro_centro != "Todos":
        filtrados = filtrados[
            filtrados["centro"] == filtro_centro
        ]

    if filtro_operario != "Todos":
        filtrados = filtrados[
            filtrados["responsable"].fillna("").str.contains(
                filtro_operario,
                case=False,
                na=False,
                regex=False
            )
        ]

    texto_busqueda = str(buscar or "").strip()

    if texto_busqueda:
        mascara = (
            filtrados["titulo"].fillna("").str.contains(
                texto_busqueda,
                case=False,
                na=False,
                regex=False
            )
            |
            filtrados["descripcion"].fillna("").str.contains(
                texto_busqueda,
                case=False,
                na=False,
                regex=False
            )
            |
            filtrados["edificio"].fillna("").str.contains(
                texto_busqueda,
                case=False,
                na=False,
                regex=False
            )
            |
            filtrados["zona"].fillna("").str.contains(
                texto_busqueda,
                case=False,
                na=False,
                regex=False
            )
        )

        filtrados = filtrados[mascara]

    filtrados = filtrados.sort_values(
        by=["fecha_fin_dt", "id"],
        ascending=[False, False]
    )

    total_terminados = len(filtrados)
    centros = filtrados["centro"].nunique()
    operarios = (
        filtrados["responsable"]
        .fillna("")
        .replace("", pd.NA)
        .dropna()
        .nunique()
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Trabajos realizados", total_terminados)
    m2.metric("Centros", centros)
    m3.metric("Asignaciones", operarios)

    if filtrados.empty:
        st.warning("No hay trabajos terminados para esos filtros.")
        return

    st.markdown("### ✅ Histórico de trabajos realizados")

    for _, fila in filtrados.iterrows():
        id_trabajo = int(fila["id"])
        titulo = texto_seguro(fila.get("titulo", ""))
        centro = texto_seguro(fila.get("centro", ""))
        edificio = texto_seguro(fila.get("edificio", ""))
        zona = texto_seguro(fila.get("zona", ""))
        responsable = texto_seguro(fila.get("responsable", ""))
        prioridad = texto_seguro(fila.get("prioridad", ""))
        fecha_fin = fila["fecha_fin_dt"].strftime("%d/%m/%Y")

        encabezado = (
            f"✅ {fecha_fin} · {titulo} · {centro}"
        )

        with st.expander(encabezado):
            col_info1, col_info2, col_info3 = st.columns(3)

            with col_info1:
                st.write(f"**Centro:** {centro}")
                st.write(f"**Edificio:** {edificio}")
                st.write(f"**Zona:** {zona}")

            with col_info2:
                st.write(f"**Operarios:** {responsable}")
                st.write(f"**Prioridad:** {prioridad}")
                st.write(
                    f"**Empresa:** "
                    f"{texto_seguro(fila.get('empresa_externa', ''))}"
                )

            with col_info3:
                st.write(
                    f"**Inicio:** "
                    f"{fila['fecha_inicio_dt'].strftime('%d/%m/%Y')}"
                )
                st.write(f"**Finalización:** {fecha_fin}")
                st.write("**Estado:** Finalizado")

            descripcion = texto_seguro(
                fila.get("descripcion", "")
            )
            observaciones = texto_seguro(
                fila.get("observaciones", "")
            )

            if descripcion:
                st.write(f"**Descripción:** {descripcion}")

            if observaciones:
                st.write(f"**Observaciones:** {observaciones}")

            st.markdown("---")
            st.markdown("#### ✏️ Corregir o reabrir")

            col_edit1, col_edit2, col_edit3, col_edit4 = st.columns(4)

            with col_edit1:
                nueva_fecha_inicio = st.date_input(
                    "Inicio",
                    value=fila["fecha_inicio_dt"].date(),
                    key=f"terminado_inicio_{id_trabajo}"
                )

            with col_edit2:
                nueva_fecha_fin = st.date_input(
                    "Finalización",
                    value=fila["fecha_fin_dt"].date(),
                    key=f"terminado_fin_{id_trabajo}"
                )

            with col_edit3:
                nuevo_estado = st.selectbox(
                    "Estado",
                    ESTADOS_VERANO,
                    index=ESTADOS_VERANO.index("Finalizado"),
                    key=f"terminado_estado_{id_trabajo}",
                    help=(
                        "Puedes cambiarlo a otro estado para devolverlo "
                        "a la planificación."
                    )
                )

            with col_edit4:
                st.write("")
                st.write("")

                if st.button(
                    "💾 Guardar cambios",
                    key=f"terminado_guardar_{id_trabajo}"
                ):
                    if nueva_fecha_fin < nueva_fecha_inicio:
                        st.warning(
                            "La fecha final no puede ser anterior."
                        )
                    else:
                        actualizar_trabajo_verano(
                            id_trabajo,
                            nueva_fecha_inicio,
                            nueva_fecha_fin,
                            nuevo_estado
                        )
                        st.success("Trabajo actualizado.")
                        st.rerun()

            confirmar = st.checkbox(
                "Confirmar eliminación del histórico",
                key=f"terminado_confirmar_borrar_{id_trabajo}"
            )

            if confirmar:
                if st.button(
                    "🗑️ Eliminar trabajo",
                    key=f"terminado_borrar_{id_trabajo}"
                ):
                    borrar_trabajo_verano(id_trabajo)
                    st.warning("Trabajo eliminado.")
                    st.rerun()


# =====================================================
# PANTALLA PRINCIPAL
# =====================================================

def pantalla_plan_verano():
    asegurar_tabla_plan_verano()
    pintar_estilos_plan_verano()

    st.markdown("## ☀️ Planificación trabajos de verano")
    st.caption(
        "Calendario mensual visual compartido para Administración y Gerencia."
    )

    df = preparar_dataframe_plan(
        obtener_plan_verano()
    )

    tab_planificacion, tab_terminados = st.tabs([
        "📅 Planificación",
        "✅ Trabajos terminados"
    ])

    with tab_planificacion:
        mostrar_planificacion_verano(df)

    with tab_terminados:
        mostrar_trabajos_terminados(df)
