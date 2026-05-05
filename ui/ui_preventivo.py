import streamlit as st
from database.db import conectar
from modules.preventivo import generar_ots_preventivo_si_toca


def pantalla_preventivo():
    st.subheader("🔧 Mantenimiento preventivo")

    tab1, tab2 = st.tabs(["➕ Crear tarea", "📋 Tareas"])

    # =====================================================
    # CREAR TAREA
    # =====================================================
    with tab1:
        with st.form("form_preventivo"):
            centro = st.text_input("Centro", value="Pearson 22")
            edificio = st.text_input("Edificio", value="Edif. Infantil/Primaria")
            espacio = st.text_input("Espacio", value="General")

            area = st.selectbox(
                "Área",
                ["Electricidad", "Fontanería", "Climatización", "Otros"]
            )

            tarea = st.text_input("Tarea preventiva")

            frecuencia = st.selectbox(
                "Frecuencia",
                ["Semanal", "Mensual", "Trimestral", "Semestral", "Anual"]
            )

            operario = st.text_input("Operario")

            observaciones = st.text_area("Observaciones")

            crear = st.form_submit_button("✅ Crear tarea preventiva")

            if crear:
                if not tarea:
                    st.warning("La tarea es obligatoria")
                else:
                    conn = conectar()
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO preventivo_tareas
                        (
                            centro, edificio, espacio, area,
                            tarea, frecuencia,
                            ultima_fecha, proxima_fecha,
                            operario, activo, observaciones
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        centro,
                        edificio,
                        espacio,
                        area,
                        tarea,
                        frecuencia,
                        "",
                        "",
                        operario,
                        1,
                        observaciones
                    ))

                    conn.commit()
                    conn.close()

                    st.success("Tarea preventiva creada")
                    st.rerun()

    # =====================================================
    # LISTA DE TAREAS
    # =====================================================
    with tab2:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, centro, edificio, espacio, area, tarea,
                   frecuencia, proxima_fecha, operario, activo
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
                    tarea, frecuencia, proxima_fecha, operario, activo
                ) = t

                estado = "🟢 Activa" if activo else "🔴 Inactiva"

                with st.expander(f"{tarea} | {frecuencia} | {estado}"):

                    st.markdown(
                        f"""
                        🏢 {centro} · {edificio} · {espacio}  
                        🔧 Área: {area}  
                        👷 Operario: {operario or '-'}  
                        📅 Próxima: {proxima_fecha or '-'}
                        """
                    )

                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button("🔄 Activar/Desactivar", key=f"act_{id_tarea}"):
                            conn = conectar()
                            cursor = conn.cursor()

                            nuevo_estado = 0 if activo else 1

                            cursor.execute("""
                                UPDATE preventivo_tareas
                                SET activo = ?
                                WHERE id = ?
                            """, (nuevo_estado, id_tarea))

                            conn.commit()
                            conn.close()
                            st.rerun()

                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_{id_tarea}"):
                            conn = conectar()
                            cursor = conn.cursor()

                            cursor.execute("""
                                DELETE FROM preventivo_tareas
                                WHERE id = ?
                            """, (id_tarea,))

                            conn.commit()
                            conn.close()
                            st.warning("Tarea eliminada")
                            st.rerun()

        st.markdown("---")

        # =====================================================
        # GENERAR OT AUTOMÁTICAS
        # =====================================================
        st.markdown("### ⚙️ Generación automática")

        if st.button("🔄 Generar OTs preventivas", use_container_width=True):
            n = generar_ots_preventivo_si_toca()

            if n > 0:
                st.success(f"Se han generado {n} órdenes preventivas")
            else:
                st.info("No hay preventivos pendientes")
