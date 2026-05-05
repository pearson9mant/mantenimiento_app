import streamlit as st

from datetime import datetime, timedelta
from database.db import conectar, _sql
from modules.ordenes import crear_orden, obtener_siguiente_numero_ot


def calcular_proxima_fecha(fecha_base, frecuencia):
    if not fecha_base:
        fecha_base = date.today()

    frecuencia = str(frecuencia or "").lower()

    if "semanal" in frecuencia:
        return fecha_base + timedelta(days=7)

    if "mensual" in frecuencia:
        return fecha_base + timedelta(days=30)

    if "trimestral" in frecuencia:
        return fecha_base + timedelta(days=90)

    if "semestral" in frecuencia:
        return fecha_base + timedelta(days=180)

    if "anual" in frecuencia:
        return fecha_base + timedelta(days=365)

    return fecha_base + timedelta(days=30)


def pantalla_preventivo():
    st.subheader("🔧 Mantenimiento preventivo")

    tab1, tab2 = st.tabs(["➕ Crear tarea", "📋 Tareas"])

    with tab1:
        with st.form("form_preventivo"):
            centro = st.text_input("Centro", value="Pearson 22")
            edificio = st.text_input("Edificio", value="Edif. Infantil/Primaria")
            espacio = st.text_input("Espacio", value="General")

            area = st.selectbox(
                "Área",
                ["Electricidad", "Fontanería", "Climatización", "Albañilería", "Pintura", "Cerrajería", "Otros"]
            )

            tarea = st.text_input("Tarea preventiva")

            frecuencia = st.selectbox(
                "Frecuencia",
                ["Semanal", "Mensual", "Trimestral", "Semestral", "Anual"]
            )

            ultima_fecha = st.date_input("Última revisión / fecha base", value=date.today())

            proxima_fecha = calcular_proxima_fecha(ultima_fecha, frecuencia)

            st.info(f"📅 Próxima fecha calculada automáticamente: {proxima_fecha}")

            operario = st.text_input("Operario", value="J.A. Almeda")
            observaciones = st.text_area("Observaciones")

            crear = st.form_submit_button("✅ Crear tarea preventiva")

            if crear:
                if not tarea.strip():
                    st.warning("La tarea es obligatoria")
                else:
                    conn = conectar()
                    cursor = conn.cursor()

                    cursor.execute(_sql("""
                        INSERT INTO preventivo_tareas
                        (
                            centro, edificio, espacio, area,
                            tarea, frecuencia,
                            ultima_fecha, proxima_fecha,
                            operario, activo, observaciones
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """), (
                        centro,
                        edificio,
                        espacio,
                        area,
                        tarea,
                        frecuencia,
                        str(ultima_fecha),
                        str(proxima_fecha),
                        operario,
                        1,
                        observaciones
                    ))

                    conn.commit()
                    conn.close()

                    st.success("Tarea preventiva creada correctamente")
                    st.rerun()

    with tab2:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, centro, edificio, espacio, area, tarea,
                   frecuencia, ultima_fecha, proxima_fecha, operario, activo
            FROM preventivo_tareas
            ORDER BY id DESC
        """)

        tareas = cursor.fetchall()
        conn.close()

        if not tareas:
            st.info("No hay tareas preventivas")
        else:
            for t in tareas:
                (
                    id_tarea, centro, edificio, espacio, area,
                    tarea, frecuencia, ultima_fecha, proxima_fecha, operario, activo
                ) = t

                estado = "🟢 Activa" if activo else "🔴 Inactiva"

                with st.expander(f"{tarea} | {frecuencia} | Próxima: {proxima_fecha or '-'} | {estado}"):
                    st.markdown(
                        f"""
                        🏢 {centro} · {edificio} · {espacio}  
                        🔧 Área: {area}  
                        👷 Operario: {operario or '-'}  
                        📅 Última revisión: {ultima_fecha or '-'}  
                        📅 Próxima revisión: **{proxima_fecha or '-'}**
                        """
                    )

                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button("🔄 Activar/Desactivar", key=f"act_{id_tarea}"):
                            conn = conectar()
                            cursor = conn.cursor()

                            nuevo_estado = 0 if activo else 1

                            cursor.execute(_sql("""
                                UPDATE preventivo_tareas
                                SET activo = ?
                                WHERE id = ?
                            """), (nuevo_estado, id_tarea))

                            conn.commit()
                            conn.close()
                            st.rerun()

                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_{id_tarea}"):
                            conn = conectar()
                            cursor = conn.cursor()

                            cursor.execute(_sql("""
                                DELETE FROM preventivo_tareas
                                WHERE id = ?
                            """), (id_tarea,))

                            conn.commit()
                            conn.close()
                            st.warning("Tarea eliminada")
                            st.rerun()

        st.markdown("---")

        st.markdown("### ⚙️ Generación automática")

        if st.button("🔄 Generar OTs preventivas que tocan", use_container_width=True):
            n = generar_ots_preventivo_si_toca()

            if n > 0:
                st.success(f"Se han generado {n} órdenes preventivas")
            else:
                st.info("No hay preventivos pendientes")
