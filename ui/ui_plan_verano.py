import streamlit as st
import pandas as pd
from datetime import date, timedelta

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
    "Julio": 7,
    "Agosto": 8
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


def color_trabajo(centro, prioridad, estado):
    centro = str(centro or "")
    prioridad = str(prioridad or "")
    estado = str(estado or "")

    if estado == "Finalizado":
        return "#dcfce7", "#166534"

    if estado == "Retrasado":
        return "#fee2e2", "#991b1b"

    if prioridad in ["Alta", "Urgente"]:
        return "#ffedd5", "#9a3412"

    if "22" in centro:
        return "#e0f2fe", "#075985"

    if "9" in centro:
        return "#ede9fe", "#5b21b6"

    return "#f1f5f9", "#334155"


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
        semanas.append([actual + timedelta(days=i) for i in range(5)])
        actual += timedelta(days=7)

    return semanas


def trabajo_activo_en_dia(fila, dia):
    inicio = fila["fecha_inicio_dt"].date()
    fin = fila["fecha_fin_dt"].date()
    return inicio <= dia <= fin


def texto_seguro(valor):
    if pd.isna(valor):
        return ""
    return str(valor)


# =====================================================
# PANTALLA PRINCIPAL
# =====================================================

def pantalla_plan_verano():
    asegurar_tabla_plan_verano()

    st.markdown("## ☀️ Planificación trabajos de verano")
    st.caption("Calendario visual compartido para Administración y Gerencia.")

    # =====================================================
    # CREAR TRABAJO
    # =====================================================

    with st.expander("➕ Crear nuevo trabajo", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            titulo = st.text_input("Título del trabajo")
            descripcion = st.text_area("Descripción")
            centro = st.selectbox("Centro", lista_centros())
            edificio = st.text_input("Edificio")
            zona = st.text_input("Zona / aula / sala")

        with col2:
            responsable = st.selectbox(
                "Responsable",
                OPERARIOS + ["Empresa externa", "Otro"]
            )
            empresa_externa = st.text_input("Empresa externa")
            fecha_inicio = st.date_input("Fecha inicio", value=date.today())
            fecha_fin = st.date_input("Fecha fin", value=date.today())
            prioridad = st.selectbox("Prioridad", PRIORIDADES_VERANO, index=1)
            estado = st.selectbox("Estado", ESTADOS_VERANO)

        observaciones = st.text_area("Observaciones")

        if st.button("💾 Guardar trabajo", use_container_width=True):
            if not titulo.strip():
                st.warning("Falta el título.")
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

    # =====================================================
    # FILTROS
    # =====================================================

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
        mes_nombre = st.selectbox("Mes", ["Julio", "Agosto"])

    with colf3:
        filtro_centro = st.selectbox(
            "Centro",
            ["Todos"] + sorted(df["centro"].dropna().unique().tolist())
        )

    with colf4:
        responsables = sorted(df["responsable"].fillna("Sin responsable").unique().tolist())
        filtro_responsable = st.selectbox(
            "Responsable",
            ["Todos"] + responsables
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

    if filtro_responsable != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["responsable"].fillna("Sin responsable") == filtro_responsable
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

    # =====================================================
    # RESUMEN SUPERIOR
    # =====================================================

    total = len(df_filtrado)
    en_ejecucion = len(df_filtrado[df_filtrado["estado"] == "En ejecución"])
    retrasados = len(df_filtrado[df_filtrado["estado"] == "Retrasado"])
    finalizados = len(df_filtrado[df_filtrado["estado"] == "Finalizado"])

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Trabajos", total)
    m2.metric("En ejecución", en_ejecucion)
    m3.metric("Retrasados", retrasados)
    m4.metric("Finalizados", finalizados)

    # =====================================================
    # ESTILOS CALENDARIO
    # =====================================================

    st.markdown("""
    <style>
    .cal-verano-titulo {
        font-size: 22px;
        font-weight: 900;
        color: #0f172a;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    .cal-dia {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 10px;
        min-height: 300px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
    }

    .cal-dia-fuera {
        opacity: 0.35;
    }

    .cal-dia-header {
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 8px;
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 6px;
    }

    .bloque-responsable {
        font-size: 12px;
        font-weight: 900;
        color: #0f172a;
        margin-top: 8px;
        margin-bottom: 5px;
        border-bottom: 1px dashed #cbd5e1;
        padding-bottom: 3px;
    }

    .cal-trabajo {
        border-radius: 12px;
        padding: 8px 9px;
        margin-bottom: 7px;
        font-size: 12px;
        font-weight: 800;
        line-height: 1.35;
    }

    .cal-detalle {
        font-size: 11px;
        font-weight: 600;
        opacity: 0.90;
        margin-top: 3px;
    }

    .sin-trabajos {
        color:#94a3b8;
        font-size:12px;
        margin-top:8px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"### 📅 Calendario {mes_nombre} {año}")

    semanas = semanas_del_mes(int(año), mes_numero)
    dias_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    for num_semana, semana in enumerate(semanas, start=1):
        st.markdown(
            f"<div class='cal-verano-titulo'>Semana {num_semana}</div>",
            unsafe_allow_html=True
        )

        columnas = st.columns(5)

        for i, dia in enumerate(semana):
            trabajos_dia = df_filtrado[
                df_filtrado.apply(lambda fila: trabajo_activo_en_dia(fila, dia), axis=1)
            ].copy()

            clase_fuera = "cal-dia-fuera" if dia.month != mes_numero else ""

            with columnas[i]:
                st.markdown(
                    f"""
                    <div class="cal-dia {clase_fuera}">
                        <div class="cal-dia-header">
                            {dias_nombre[i]}<br>{dia.strftime("%d/%m")}
                        </div>
                    """,
                    unsafe_allow_html=True
                )

                if trabajos_dia.empty:
                    st.markdown(
                        "<div class='sin-trabajos'>Sin trabajos</div>",
                        unsafe_allow_html=True
                    )

                else:
                    trabajos_dia["responsable_visible"] = trabajos_dia["responsable"].fillna("Sin responsable")
                    responsables_dia = trabajos_dia["responsable_visible"].unique().tolist()

                    for responsable_dia in responsables_dia:
                        trabajos_resp = trabajos_dia[
                            trabajos_dia["responsable_visible"] == responsable_dia
                        ]

                        st.markdown(
                            f"""
                            <div class="bloque-responsable">
                                👷 {responsable_dia}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        for _, fila in trabajos_resp.iterrows():
                            bg, color = color_trabajo(
                                fila.get("centro", ""),
                                fila.get("prioridad", ""),
                                fila.get("estado", "")
                            )

                            titulo = texto_seguro(fila.get("titulo", ""))
                            centro = texto_seguro(fila.get("centro", ""))
                            edificio = texto_seguro(fila.get("edificio", ""))
                            zona = texto_seguro(fila.get("zona", ""))
                            estado = texto_seguro(fila.get("estado", ""))
                            prioridad = texto_seguro(fila.get("prioridad", ""))
                            empresa = texto_seguro(fila.get("empresa_externa", ""))

                            fechas = (
                                f"{fila['fecha_inicio_dt'].strftime('%d/%m')}"
                                f" → "
                                f"{fila['fecha_fin_dt'].strftime('%d/%m')}"
                            )

                            extra_empresa = ""
                            if empresa:
                                extra_empresa = f"<br>🏢 {empresa}"

                            st.markdown(
                                f"""
                                <div class="cal-trabajo" style="background:{bg}; color:{color};">
                                    {titulo}
                                    <div class="cal-detalle">
                                        {centro}<br>
                                        {edificio} · {zona}<br>
                                        📅 {fechas}<br>
                                        {estado} · {prioridad}
                                        {extra_empresa}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================
    # EDICIÓN RÁPIDA
    # =====================================================

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
            st.write(f"**Responsable:** {texto_seguro(fila.get('responsable', ''))}")
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
