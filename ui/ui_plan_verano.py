import streamlit as st
import pandas as pd
from datetime import date

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


def asegurar_tabla_plan_verano():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
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
    """))

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
        df = pd.read_sql_query("SELECT * FROM plan_verano ORDER BY fecha_inicio ASC", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


def actualizar_estado_verano(id_trabajo, nuevo_estado):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE plan_verano
        SET estado = ?
        WHERE id = ?
    """), (nuevo_estado, id_trabajo))

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


def pantalla_plan_verano():
    asegurar_tabla_plan_verano()

    st.markdown("## ☀️ Planificación trabajos de verano")
    st.caption("Vista tipo tarjetas para planificar obras, mantenimientos y trabajos de julio/agosto.")

    with st.expander("➕ Crear nuevo trabajo de verano", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            titulo = st.text_input("Título del trabajo")
            descripcion = st.text_area("Descripción")
            centro = st.selectbox("Centro", list(CENTROS.keys()) if isinstance(CENTROS, dict) else CENTROS)
            edificio = st.text_input("Edificio / zona principal")
            zona = st.text_input("Zona concreta / aula / sala")

        with col2:
            responsable = st.selectbox("Responsable", OPERARIOS + ["Empresa externa", "Otro"])
            empresa_externa = st.text_input("Empresa externa")
            fecha_inicio = st.date_input("Fecha inicio", value=date.today())
            fecha_fin = st.date_input("Fecha fin", value=date.today())
            prioridad = st.selectbox("Prioridad", PRIORIDADES_VERANO, index=1)
            estado = st.selectbox("Estado", ESTADOS_VERANO)

        observaciones = st.text_area("Observaciones")

        if st.button("💾 Guardar trabajo de verano", use_container_width=True):
            if not titulo.strip():
                st.warning("Falta el título del trabajo.")
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
                st.success("Trabajo de verano creado correctamente.")
                st.rerun()

    df = obtener_plan_verano()

    if df.empty:
        st.info("Todavía no hay trabajos de verano planificados.")
        return

    df["fecha_inicio_dt"] = pd.to_datetime(df["fecha_inicio"], errors="coerce")
    df["fecha_fin_dt"] = pd.to_datetime(df["fecha_fin"], errors="coerce")

    st.markdown("### 🔎 Filtros")

    colf1, colf2, colf3, colf4 = st.columns(4)

    with colf1:
        filtro_centro = st.selectbox(
            "Centro",
            ["Todos"] + sorted(df["centro"].dropna().unique().tolist())
        )

    with colf2:
        filtro_estado = st.selectbox(
            "Estado",
            ["Todos"] + ESTADOS_VERANO
        )

    with colf3:
        filtro_prioridad = st.selectbox(
            "Prioridad",
            ["Todas"] + PRIORIDADES_VERANO
        )

    with colf4:
        filtro_mes = st.selectbox(
            "Mes",
            ["Todos", "Julio", "Agosto"]
        )

    df_filtrado = df.copy()

    if filtro_centro != "Todos":
        df_filtrado = df_filtrado[df_filtrado["centro"] == filtro_centro]

    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_estado]

    if filtro_prioridad != "Todas":
        df_filtrado = df_filtrado[df_filtrado["prioridad"] == filtro_prioridad]

    if filtro_mes == "Julio":
        df_filtrado = df_filtrado[df_filtrado["fecha_inicio_dt"].dt.month == 7]

    if filtro_mes == "Agosto":
        df_filtrado = df_filtrado[df_filtrado["fecha_inicio_dt"].dt.month == 8]

    if df_filtrado.empty:
        st.warning("No hay trabajos con esos filtros.")
        return

    st.markdown("""
    <style>
    .tarjeta-verano {
        background: #ffffff;
        border-radius: 20px;
        padding: 18px;
        margin-bottom: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08);
    }

    .tarjeta-verano h3 {
        margin-top: 0;
        margin-bottom: 6px;
        color: #0f172a;
    }

    .etiqueta-verano {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        background: #e0f2fe;
        color: #075985;
        font-size: 12px;
        font-weight: 700;
        margin-right: 6px;
    }

    .prioridad-alta {
        background: #fee2e2;
        color: #991b1b;
    }

    .prioridad-media {
        background: #fef3c7;
        color: #92400e;
    }

    .prioridad-baja {
        background: #dcfce7;
        color: #166534;
    }

    .info-verano {
        color: #334155;
        font-size: 14px;
        line-height: 1.7;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📅 Trabajos planificados")

    for _, fila in df_filtrado.iterrows():
        id_trabajo = int(fila["id"])
        titulo = fila.get("titulo", "")
        descripcion = fila.get("descripcion", "")
        centro = fila.get("centro", "")
        edificio = fila.get("edificio", "")
        zona = fila.get("zona", "")
        responsable = fila.get("responsable", "")
        empresa = fila.get("empresa_externa", "")
        prioridad = fila.get("prioridad", "")
        estado = fila.get("estado", "")
        observaciones = fila.get("observaciones", "")

        fecha_inicio = fila.get("fecha_inicio", "")
        fecha_fin = fila.get("fecha_fin", "")

        clase_prioridad = "prioridad-baja"
        if prioridad in ["Alta", "Urgente"]:
            clase_prioridad = "prioridad-alta"
        elif prioridad == "Media":
            clase_prioridad = "prioridad-media"

        st.markdown(f"""
        <div class="tarjeta-verano">
            <h3>☀️ {titulo}</h3>
            <span class="etiqueta-verano">{estado}</span>
            <span class="etiqueta-verano {clase_prioridad}">{prioridad}</span>

            <div class="info-verano">
                <b>📍 Centro:</b> {centro}<br>
                <b>🏫 Edificio/Zona:</b> {edificio} · {zona}<br>
                <b>👷 Responsable:</b> {responsable}<br>
                <b>🏢 Empresa:</b> {empresa}<br>
                <b>📅 Fechas:</b> {fecha_inicio} → {fecha_fin}<br>
                <b>📝 Descripción:</b> {descripcion}<br>
                <b>💬 Observaciones:</b> {observaciones}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            nuevo_estado = st.selectbox(
                "Cambiar estado",
                ESTADOS_VERANO,
                index=ESTADOS_VERANO.index(estado) if estado in ESTADOS_VERANO else 0,
                key=f"estado_verano_{id_trabajo}"
            )

            if st.button("Actualizar estado", key=f"btn_estado_verano_{id_trabajo}"):
                actualizar_estado_verano(id_trabajo, nuevo_estado)
                st.success("Estado actualizado.")
                st.rerun()

        with col2:
            confirmar = st.checkbox(
                "Borrar",
                key=f"confirmar_borrar_verano_{id_trabajo}"
            )

            if confirmar:
                if st.button("🗑️ Eliminar", key=f"borrar_verano_{id_trabajo}"):
                    borrar_trabajo_verano(id_trabajo)
                    st.warning("Trabajo eliminado.")
                    st.rerun()
