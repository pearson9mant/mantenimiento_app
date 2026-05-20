import streamlit as st
import pandas as pd
from datetime import date, timedelta
from html import escape

from database.db import conectar, _sql
from config import CENTROS, OPERARIOS
from ui.ui_plan_verano import crear_trabajo_verano


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

def pantalla_plan_verano():
    asegurar_tabla_plan_verano()
    pintar_estilos_plan_verano()

    st.markdown("## ☀️ Planificación trabajos de verano")
    st.caption("Calendario mensual visual compartido para Administración y Gerencia.")

    with st.expander("➕ Crear nuevo trabajo", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            titulo = st.text_input("Título del trabajo")
            descripcion = st.text_area("Descripción")
            centro = st.selectbox("Centro", lista_centros())
            edificio = st.text_input("Edificio")
            zona = st.text_input("Zona / aula / sala")

        with col2:
            operarios_seleccionados = st.multiselect(
                "Operarios asignados",
                lista_operarios_plan(),
                max_selections=4,
                help="Puedes seleccionar hasta 4 operarios o responsables para la misma faena."
            )

            responsable = ", ".join(operarios_seleccionados)

            empresa_externa = st.text_input("Empresa externa")
            fecha_inicio = st.date_input("Fecha inicio", value=date.today())
            fecha_fin = st.date_input("Fecha fin", value=date.today())
            prioridad = st.selectbox("Prioridad", PRIORIDADES_VERANO, index=1)
            estado = st.selectbox("Estado", ESTADOS_VERANO)

        observaciones = st.text_area("Observaciones")

        if st.button("💾 Guardar trabajo", use_container_width=True):
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
                st.success("Trabajo creado correctamente.")
                st.rerun()

    df = obtener_plan_verano()

    if df.empty:
        st.info("Todavía no hay trabajos de verano planificados.")
        return

    df["fecha_inicio_dt"] = pd.to_datetime(df["fecha_inicio"], errors="coerce")
    df["fecha_fin_dt"] = pd.to_datetime(df["fecha_fin"], errors="coerce")
    df = df.dropna(subset=["fecha_inicio_dt", "fecha_fin_dt"])

    if df.empty:
        st.info("No hay trabajos con fechas válidas.")
        return

    st.markdown("### 🔎 Filtros")

    colf1, colf2, colf3, colf4 = st.columns(4)

    with colf1:
        año = st.number_input(
            "Año",
            min_value=2025,
            max_value=2035,
            value=date.today().year,
            step=1
        )

    with colf2:
        mes_nombre = st.selectbox(
            "Mes",
            list(MESES_VERANO.keys()),
            index=5
        )

    with colf3:
        filtro_centro = st.selectbox(
            "Centro",
            ["Todos"] + sorted(df["centro"].dropna().unique().tolist())
        )

    with colf4:
        filtro_operario = st.selectbox(
            "Operario",
            ["Todos"] + lista_operarios_plan()
        )

    colf5, colf6, colf7 = st.columns(3)

    with colf5:
        filtro_estado = st.selectbox(
            "Estado",
            ["Todos"] + ESTADOS_VERANO
        )

    with colf6:
        filtro_prioridad = st.selectbox(
            "Prioridad",
            ["Todas"] + PRIORIDADES_VERANO
        )

    with colf7:
        ver_finalizados = st.checkbox("Mostrar finalizados", value=True)

    mes_numero = MESES_VERANO[mes_nombre]

    df_filtrado = df.copy()

    if filtro_centro != "Todos":
        df_filtrado = df_filtrado[df_filtrado["centro"] == filtro_centro]

    if filtro_operario != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["responsable"].fillna("").str.contains(
                filtro_operario,
                case=False,
                na=False
            )
        ]

    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_estado]

    if filtro_prioridad != "Todas":
        df_filtrado = df_filtrado[df_filtrado["prioridad"] == filtro_prioridad]

    if not ver_finalizados:
        df_filtrado = df_filtrado[df_filtrado["estado"] != "Finalizado"]

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
    en_ejecucion = len(df_filtrado[df_filtrado["estado"] == "En ejecución"])
    retrasados = len(df_filtrado[df_filtrado["estado"] == "Retrasado"])
    finalizados = len(df_filtrado[df_filtrado["estado"] == "Finalizado"])

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Trabajos", total)
    m2.metric("En ejecución", en_ejecucion)
    m3.metric("Retrasados", retrasados)
    m4.metric("Finalizados", finalizados)

    pintar_leyenda()

    st.markdown(
        f"<div class='pv-mes-titulo'>📅 Calendario completo · {mes_nombre} {año}</div>",
        unsafe_allow_html=True
    )

    dias_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

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
                df_filtrado.apply(lambda fila: trabajo_activo_en_dia(fila, dia), axis=1)
            ].copy()

            clase_fuera = "pv-card-dia-fuera" if dia.month != mes_numero else ""

            with columnas[i]:
                html_dia = f"""
                <div class="pv-card-dia {clase_fuera}">
                    <div class="pv-dia-header">
                        <span class="pv-dia-num">{dia.day}</span><br>
                        {dias_nombre[dia.weekday()]}
                    </div>
                """

                if trabajos_dia.empty:
                    html_dia += "<div class='pv-sin-trabajos'>Sin trabajos</div>"
                else:
                    for _, fila in trabajos_dia.iterrows():
                        html_dia += tarjeta_trabajo_html(fila)

                html_dia += "</div>"

                st.markdown(html_dia, unsafe_allow_html=True)

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
                estado_actual = texto_seguro(fila.get("estado", ""))
                nuevo_estado = st.selectbox(
                    "Estado",
                    ESTADOS_VERANO,
                    index=ESTADOS_VERANO.index(estado_actual) if estado_actual in ESTADOS_VERANO else 0,
                    key=f"edit_estado_{id_trabajo}"
                )

            with col4:
                st.write("")
                st.write("")
                if st.button("💾 Actualizar", key=f"guardar_edit_{id_trabajo}"):
                    if nueva_fecha_fin < nueva_fecha_inicio:
                        st.warning("La fecha fin no puede ser anterior.")
                    else:
                        actualizar_trabajo_verano(
                            id_trabajo,
                            nueva_fecha_inicio,
                            nueva_fecha_fin,
                            nuevo_estado
                        )
                        st.success("Trabajo actualizado.")
                        st.rerun()

            st.write(f"**Descripción:** {texto_seguro(fila.get('descripcion', ''))}")
            st.write(f"**Operarios:** {texto_seguro(fila.get('responsable', ''))}")
            st.write(f"**Empresa:** {texto_seguro(fila.get('empresa_externa', ''))}")
            st.write(f"**Observaciones:** {texto_seguro(fila.get('observaciones', ''))}")

            confirmar = st.checkbox(
                "Confirmar eliminación",
                key=f"confirmar_borrar_{id_trabajo}"
            )

            if confirmar:
                if st.button("🗑️ Eliminar trabajo", key=f"borrar_{id_trabajo}"):
                    borrar_trabajo_verano(id_trabajo)
                    st.warning("Trabajo eliminado.")
                    st.rerun()
