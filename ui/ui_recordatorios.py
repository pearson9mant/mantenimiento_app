import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from database.db import conectar, _sql


PRIORIDADES_RECORDATORIO = ["Baja", "Media", "Alta", "Urgente"]
ESTADOS_RECORDATORIO = ["Pendiente", "Realizado"]


def asegurar_tabla_recordatorios():
    conn = conectar()
    cursor = conn.cursor()

    try:
        if "postgres" in conn.__class__.__module__.lower():
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recordatorios (
                    id SERIAL PRIMARY KEY,
                    titulo TEXT,
                    descripcion TEXT,
                    fecha_recordatorio TEXT,
                    prioridad TEXT,
                    estado TEXT DEFAULT 'Pendiente',
                    creado_por TEXT,
                    fecha_creacion TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recordatorios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    descripcion TEXT,
                    fecha_recordatorio TEXT,
                    prioridad TEXT,
                    estado TEXT DEFAULT 'Pendiente',
                    creado_por TEXT,
                    fecha_creacion TEXT
                )
            """)

        conn.commit()

    except Exception:
        conn.rollback()

    finally:
        conn.close()


def crear_recordatorio(titulo, descripcion, fecha_recordatorio, prioridad, creado_por):
    asegurar_tabla_recordatorios()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            INSERT INTO recordatorios
            (
                titulo,
                descripcion,
                fecha_recordatorio,
                prioridad,
                estado,
                creado_por,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, 'Pendiente', ?, ?)
        """), (
            titulo,
            descripcion,
            fecha_recordatorio,
            prioridad,
            creado_por,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        return True, "Recordatorio creado correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"Error creando recordatorio: {e}"

    finally:
        conn.close()


def obtener_recordatorios(incluir_realizados=False):
    asegurar_tabla_recordatorios()

    conn = conectar()

    try:
        if incluir_realizados:
            df = pd.read_sql_query(_sql("""
                SELECT *
                FROM recordatorios
                ORDER BY fecha_recordatorio ASC, id DESC
            """), conn)
        else:
            df = pd.read_sql_query(_sql("""
                SELECT *
                FROM recordatorios
                WHERE estado = 'Pendiente'
                ORDER BY fecha_recordatorio ASC, id DESC
            """), conn)

    except Exception:
        df = pd.DataFrame()

    finally:
        conn.close()

    return df

def obtener_resumen_recordatorios():
    df = obtener_recordatorios(incluir_realizados=False)

    if df.empty:
        return {
            "vencidos": 0,
            "hoy": 0,
            "mañana": 0
        }

    hoy = date.today()

    vencidos = 0
    hoy_count = 0
    mañana = 0

    for _, row in df.iterrows():

        try:
            fecha = pd.to_datetime(
                row["fecha_recordatorio"]
            ).date()

        except Exception:
            continue

        if fecha < hoy:
            vencidos += 1

        elif fecha == hoy:
            hoy_count += 1

        elif fecha == hoy + timedelta(days=1):
            mañana += 1

    return {
        "vencidos": vencidos,
        "hoy": hoy_count,
        "mañana": mañana
    }


def marcar_recordatorio_realizado(recordatorio_id):
    asegurar_tabla_recordatorios()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE recordatorios
            SET estado = 'Realizado'
            WHERE id = ?
        """), (int(recordatorio_id),))

        conn.commit()
        return True, "Recordatorio marcado como realizado."

    except Exception as e:
        conn.rollback()
        return False, f"Error actualizando recordatorio: {e}"

    finally:
        conn.close()


def borrar_recordatorio(recordatorio_id):
    asegurar_tabla_recordatorios()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            DELETE FROM recordatorios
            WHERE id = ?
        """), (int(recordatorio_id),))

        conn.commit()
        return True, "Recordatorio eliminado."

    except Exception as e:
        conn.rollback()
        return False, f"Error eliminando recordatorio: {e}"

    finally:
        conn.close()


def icono_prioridad(prioridad):
    prioridad = str(prioridad or "").lower()

    if prioridad == "urgente":
        return "🔴"
    if prioridad == "alta":
        return "🟠"
    if prioridad == "media":
        return "🟡"
    return "🟢"


def estado_fecha(fecha_txt):
    try:
        fecha = pd.to_datetime(fecha_txt).date()
    except Exception:
        return "Sin fecha"

    hoy = date.today()

    if fecha < hoy:
        return "🔴 Vencido"
    if fecha == hoy:
        return "🔴 Hoy"
    if fecha == hoy + timedelta(days=1):
        return "🟠 Mañana"
    if fecha <= hoy + timedelta(days=7):
        return "🟡 Esta semana"

    return "🟢 Próximo"


def pantalla_recordatorios():
    asegurar_tabla_recordatorios()

    st.subheader("🔔 Recordatorios")

    tab1, tab2 = st.tabs(["➕ Crear recordatorio", "📋 Pendientes"])

    with tab1:
        st.markdown("### Nuevo recordatorio")

        titulo = st.text_input(
            "Título",
            placeholder="Ejemplo: Revisar bomba PCI"
        )

        descripcion = st.text_area(
            "Descripción",
            placeholder="Detalles del aviso o tarea pendiente"
        )

        fecha_recordatorio = st.date_input(
            "Fecha recordatorio",
            value=date.today()
        )

        prioridad = st.selectbox(
            "Prioridad",
            PRIORIDADES_RECORDATORIO,
            index=1
        )

        creado_por = st.session_state.get("usuario", "") or st.session_state.get("operario_activo", "") or "Administración"

        if st.button("💾 Guardar recordatorio", use_container_width=True):
            if not titulo.strip():
                st.warning("Indica un título.")
            else:
                ok, mensaje = crear_recordatorio(
                    titulo=titulo.strip(),
                    descripcion=descripcion.strip(),
                    fecha_recordatorio=fecha_recordatorio.strftime("%Y-%m-%d"),
                    prioridad=prioridad,
                    creado_por=creado_por
                )

                if ok:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.error(mensaje)

    with tab2:
        incluir_realizados = st.checkbox(
            "Mostrar realizados",
            value=False
        )

        df = obtener_recordatorios(incluir_realizados=incluir_realizados)

        if df.empty:
            st.info("No hay recordatorios pendientes.")
            return

        pendientes = len(df[df["estado"] == "Pendiente"]) if "estado" in df.columns else len(df)
        vencidos = 0

        for _, row in df.iterrows():
            if estado_fecha(row.get("fecha_recordatorio")) in ["🔴 Vencido", "🔴 Hoy"]:
                if row.get("estado") == "Pendiente":
                    vencidos += 1

        c1, c2 = st.columns(2)
        c1.metric("Pendientes", pendientes)
        c2.metric("Vencidos / hoy", vencidos)

        st.markdown("### Listado")

        for _, row in df.iterrows():
            recordatorio_id = row.get("id")
            titulo = row.get("titulo", "")
            descripcion = row.get("descripcion", "")
            fecha = row.get("fecha_recordatorio", "")
            prioridad = row.get("prioridad", "Media")
            estado = row.get("estado", "Pendiente")
            creado_por = row.get("creado_por", "")

            icono = icono_prioridad(prioridad)
            estado_f = estado_fecha(fecha)

            titulo_expander = f"{icono} {estado_f} · {fecha} · {titulo} · {estado}"

            with st.expander(titulo_expander, expanded=False):
                st.markdown(f"### {titulo}")
                st.markdown(f"**Fecha:** {fecha}")
                st.markdown(f"**Prioridad:** {prioridad}")
                st.markdown(f"**Estado:** {estado}")
                st.caption(f"Creado por: {creado_por or '-'}")

                if descripcion:
                    st.info(descripcion)

                col1, col2 = st.columns(2)

                with col1:
                    if estado == "Pendiente":
                        if st.button("✅ Marcar realizado", key=f"realizado_recordatorio_{recordatorio_id}", use_container_width=True):
                            ok, mensaje = marcar_recordatorio_realizado(recordatorio_id)
                            if ok:
                                st.success(mensaje)
                                st.rerun()
                            else:
                                st.error(mensaje)

                with col2:
                    confirmar = st.checkbox(
                        "Confirmar borrar",
                        key=f"confirmar_borrar_recordatorio_{recordatorio_id}"
                    )

                    if confirmar:
                        if st.button("🗑️ Borrar", key=f"borrar_recordatorio_{recordatorio_id}", use_container_width=True):
                            ok, mensaje = borrar_recordatorio(recordatorio_id)
                            if ok:
                                st.warning(mensaje)
                                st.rerun()
                            else:
                                st.error(mensaje)
