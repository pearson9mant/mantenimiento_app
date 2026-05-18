import os
import streamlit as st
import pandas as pd
from datetime import date, datetime
from pathlib import Path

from database.db import conectar


def adaptar_sql(sql):
    if os.getenv("DATABASE_URL"):
        return sql.replace("?", "%s")
    return sql


def ejecutar(sql, params=()):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(adaptar_sql(sql), params)
        conn.commit()
        st.cache_data.clear()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@st.cache_data(ttl=30)
def leer_df(sql, params=()):
    conn = conectar()
    try:
        df = pd.read_sql_query(adaptar_sql(sql), conn, params=params)
    finally:
        conn.close()
    return df


CENTROS = ["Pearson 22", "Pearson 9"]

TIPOS_SERVICIO = [
    "Legionella",
    "Climatización",
    "Electricidad",
    "Fontanería",
    "PCI / Contra incendios",
    "Ascensores",
    "Puertas automáticas",
    "Obra / Reforma",
    "Jardinería",
    "Otro",
]

ESTADOS_EXTERNAS = [
    "Avisado",
    "Pendiente presupuesto",
    "Pendiente aprobación",
    "Aprobado",
    "En ejecución",
    "Finalizado",
    "Cancelado",
]


def asegurar_tabla_empresas_externas():
    if os.getenv("DATABASE_URL"):
        ejecutar("""
            CREATE TABLE IF NOT EXISTS empresas_externas (
                id SERIAL PRIMARY KEY,
                fecha_registro TEXT,
                empresa TEXT,
                servicio TEXT,
                contacto TEXT,
                telefono TEXT,
                email TEXT,
                centro TEXT,
                edificio TEXT,
                espacio TEXT,
                descripcion TEXT,
                estado TEXT,
                prioridad TEXT,
                fecha_aviso TEXT,
                fecha_prevista TEXT,
                fecha_realizacion TEXT,
                presupuesto REAL DEFAULT 0,
                coste_final REAL DEFAULT 0,
                pdf TEXT,
                observaciones TEXT
            )
        """)
    else:
        ejecutar("""
            CREATE TABLE IF NOT EXISTS empresas_externas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_registro TEXT,
                empresa TEXT,
                servicio TEXT,
                contacto TEXT,
                telefono TEXT,
                email TEXT,
                centro TEXT,
                edificio TEXT,
                espacio TEXT,
                descripcion TEXT,
                estado TEXT,
                prioridad TEXT,
                fecha_aviso TEXT,
                fecha_prevista TEXT,
                fecha_realizacion TEXT,
                presupuesto REAL DEFAULT 0,
                coste_final REAL DEFAULT 0,
                pdf TEXT,
                observaciones TEXT
            )
        """)


def pantalla_empresas_externas():
    asegurar_tabla_empresas_externas()

    st.subheader("🏢 Empresas externas")
    st.caption("Control de avisos, presupuestos, actuaciones, costes y documentación externa.")

    df = leer_df("""
        SELECT *
        FROM empresas_externas
        ORDER BY fecha_registro DESC, id DESC
    """)

    total = len(df)
    pendientes = len(df[df["estado"].isin(["Avisado", "Pendiente presupuesto", "Pendiente aprobación", "Aprobado"])]) if not df.empty else 0
    ejecucion = len(df[df["estado"] == "En ejecución"]) if not df.empty else 0
    finalizados = len(df[df["estado"] == "Finalizado"]) if not df.empty else 0
    coste_total = float(df["coste_final"].fillna(0).sum()) if not df.empty and "coste_final" in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", total)
    c2.metric("Pendientes", pendientes)
    c3.metric("En ejecución", ejecucion)
    c4.metric("Coste final", f"{coste_total:,.2f} €")

    with st.expander("➕ Nueva intervención externa", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            empresa = st.text_input("Empresa externa", key="ext_empresa")
            servicio = st.selectbox("Tipo de servicio", TIPOS_SERVICIO, key="ext_servicio")
            contacto = st.text_input("Contacto", key="ext_contacto")
            telefono = st.text_input("Teléfono", key="ext_telefono")
            email = st.text_input("Email", key="ext_email")

        with col2:
            centro = st.selectbox("Centro", CENTROS, key="ext_centro")
            edificio = st.text_input("Edificio / zona", key="ext_edificio")
            espacio = st.text_input("Espacio / aula / instalación", key="ext_espacio")
            estado = st.selectbox("Estado", ESTADOS_EXTERNAS, key="ext_estado")
            prioridad = st.selectbox("Prioridad", ["Baja", "Media", "Alta", "Urgente"], index=1, key="ext_prioridad")

        descripcion = st.text_area("Descripción del trabajo", key="ext_descripcion")

        col3, col4, col5 = st.columns(3)

        with col3:
            fecha_aviso = st.date_input("Fecha aviso", value=date.today(), key="ext_fecha_aviso")

        with col4:
            fecha_prevista = st.date_input("Fecha prevista", value=date.today(), key="ext_fecha_prevista")

        with col5:
            fecha_realizacion = st.date_input("Fecha realización", value=date.today(), key="ext_fecha_realizacion")

        col6, col7 = st.columns(2)

        with col6:
            presupuesto = st.number_input("Presupuesto €", min_value=0.0, value=0.0, step=10.0, key="ext_presupuesto")

        with col7:
            coste_final = st.number_input("Coste final €", min_value=0.0, value=0.0, step=10.0, key="ext_coste_final")

        archivo_pdf = st.file_uploader(
            "Subir presupuesto / albarán / informe PDF",
            type=["pdf"],
            key="ext_pdf"
        )

        observaciones = st.text_area("Observaciones", key="ext_observaciones")

        if st.button("💾 Guardar intervención externa", use_container_width=True):
            if not empresa or not descripcion:
                st.error("Falta empresa o descripción.")
            else:
                ruta_pdf = ""

                if archivo_pdf is not None:
                    carpeta = Path("uploads/empresas_externas")
                    carpeta.mkdir(parents=True, exist_ok=True)

                    nombre_pdf = (
                        f"{empresa}_{servicio}_{centro}_{fecha_aviso}.pdf"
                        .replace(" ", "_")
                        .replace("/", "_")
                        .replace("\\", "_")
                        .replace(":", "_")
                    )

                    ruta_archivo = carpeta / nombre_pdf

                    with open(ruta_archivo, "wb") as f:
                        f.write(archivo_pdf.getbuffer())

                    ruta_pdf = str(ruta_archivo)

                ejecutar("""
                    INSERT INTO empresas_externas
                    (
                        fecha_registro,
                        empresa,
                        servicio,
                        contacto,
                        telefono,
                        email,
                        centro,
                        edificio,
                        espacio,
                        descripcion,
                        estado,
                        prioridad,
                        fecha_aviso,
                        fecha_prevista,
                        fecha_realizacion,
                        presupuesto,
                        coste_final,
                        pdf,
                        observaciones
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    empresa,
                    servicio,
                    contacto,
                    telefono,
                    email,
                    centro,
                    edificio,
                    espacio,
                    descripcion,
                    estado,
                    prioridad,
                    fecha_aviso.strftime("%Y-%m-%d"),
                    fecha_prevista.strftime("%Y-%m-%d"),
                    fecha_realizacion.strftime("%Y-%m-%d"),
                    float(presupuesto),
                    float(coste_final),
                    ruta_pdf,
                    observaciones
                ))

                st.success("Intervención externa guardada correctamente.")
                st.rerun()

    st.markdown("### 📚 Histórico empresas externas")

    df = leer_df("""
        SELECT *
        FROM empresas_externas
        ORDER BY fecha_registro DESC, id DESC
    """)

    if df.empty:
        st.info("Todavía no hay intervenciones externas registradas.")
        return

    f1, f2, f3 = st.columns(3)

    with f1:
        filtro_centro = st.selectbox(
            "Filtrar centro",
            ["Todos"] + sorted(df["centro"].dropna().astype(str).unique().tolist()),
            key="filtro_ext_centro"
        )

    with f2:
        filtro_empresa = st.selectbox(
            "Filtrar empresa",
            ["Todas"] + sorted(df["empresa"].dropna().astype(str).unique().tolist()),
            key="filtro_ext_empresa"
        )

    with f3:
        filtro_estado = st.selectbox(
            "Filtrar estado",
            ["Todos"] + sorted(df["estado"].dropna().astype(str).unique().tolist()),
            key="filtro_ext_estado"
        )

    df_filtrado = df.copy()

    if filtro_centro != "Todos":
        df_filtrado = df_filtrado[df_filtrado["centro"] == filtro_centro]

    if filtro_empresa != "Todas":
        df_filtrado = df_filtrado[df_filtrado["empresa"] == filtro_empresa]

    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_estado]

    st.dataframe(
        df_filtrado[
            [
                "id",
                "empresa",
                "servicio",
                "centro",
                "edificio",
                "espacio",
                "estado",
                "prioridad",
                "fecha_aviso",
                "fecha_prevista",
                "fecha_realizacion",
                "presupuesto",
                "coste_final",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### 🔍 Detalle / acciones")

    for _, row in df_filtrado.iterrows():
        titulo = (
            f"{row['empresa']} · {row['servicio']} · {row['centro']} · "
            f"{row['estado']} · {row['fecha_aviso']}"
        )

        with st.expander(titulo, expanded=False):
            col_a, col_b = st.columns(2)

            with col_a:
                nuevo_estado = st.selectbox(
                    "Estado",
                    ESTADOS_EXTERNAS,
                    index=ESTADOS_EXTERNAS.index(row["estado"]) if row["estado"] in ESTADOS_EXTERNAS else 0,
                    key=f"edit_ext_estado_{row['id']}"
                )

                nueva_fecha_prevista = st.date_input(
                    "Fecha prevista",
                    value=pd.to_datetime(row["fecha_prevista"]).date() if row["fecha_prevista"] else date.today(),
                    key=f"edit_ext_fecha_prevista_{row['id']}"
                )

                nueva_fecha_realizacion = st.date_input(
                    "Fecha realización",
                    value=pd.to_datetime(row["fecha_realizacion"]).date() if row["fecha_realizacion"] else date.today(),
                    key=f"edit_ext_fecha_realizacion_{row['id']}"
                )

            with col_b:
                nuevo_presupuesto = st.number_input(
                    "Presupuesto €",
                    min_value=0.0,
                    value=float(row["presupuesto"] or 0),
                    step=10.0,
                    key=f"edit_ext_presupuesto_{row['id']}"
                )

                nuevo_coste = st.number_input(
                    "Coste final €",
                    min_value=0.0,
                    value=float(row["coste_final"] or 0),
                    step=10.0,
                    key=f"edit_ext_coste_{row['id']}"
                )

                nuevas_obs = st.text_area(
                    "Observaciones",
                    value=str(row["observaciones"] or ""),
                    key=f"edit_ext_obs_{row['id']}"
                )

            if st.button("💾 Guardar cambios", key=f"guardar_ext_{row['id']}", use_container_width=True):
                ejecutar("""
                    UPDATE empresas_externas
                    SET estado = ?,
                        fecha_prevista = ?,
                        fecha_realizacion = ?,
                        presupuesto = ?,
                        coste_final = ?,
                        observaciones = ?
                    WHERE id = ?
                """, (
                    nuevo_estado,
                    nueva_fecha_prevista.strftime("%Y-%m-%d"),
                    nueva_fecha_realizacion.strftime("%Y-%m-%d"),
                    float(nuevo_presupuesto),
                    float(nuevo_coste),
                    nuevas_obs,
                    int(row["id"])
                ))

                st.success("Intervención actualizada.")
                st.rerun()

            col_pdf, col_del = st.columns([4, 1])

            with col_pdf:
                if row["pdf"] and Path(str(row["pdf"])).exists():
                    with open(row["pdf"], "rb") as f:
                        st.download_button(
                            "📎 Descargar PDF",
                            data=f.read(),
                            file_name=Path(row["pdf"]).name,
                            mime="application/pdf",
                            key=f"descargar_ext_pdf_{row['id']}"
                        )
                elif row["pdf"]:
                    st.warning("El registro tiene PDF, pero el archivo no se encuentra en Render.")
                else:
                    st.info("Sin PDF adjunto.")

            with col_del:
                confirmar = st.checkbox(
                    "Confirmar borrado",
                    key=f"confirmar_borrar_ext_{row['id']}"
                )

                if st.button("🗑️ Borrar", key=f"borrar_ext_{row['id']}"):
                    if not confirmar:
                        st.error("Marca confirmar borrado.")
                    else:
                        try:
                            if row["pdf"] and Path(str(row["pdf"])).exists():
                                Path(str(row["pdf"])).unlink()

                            ejecutar("""
                                DELETE FROM empresas_externas
                                WHERE id = ?
                            """, (int(row["id"]),))

                            st.success("Registro eliminado.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error al borrar: {e}")
