import streamlit as st
from datetime import date, timedelta

from config import CENTROS, EDIFICIOS, AREAS, OPERARIOS, ESPACIOS
from database.db import conectar, _sql
from modules.preventivo import generar_ots_preventivo_si_toca


TAREAS_PREVENTIVAS = [
    "Revisar cuadro eléctrico",
    "Revisar enchufes",
    "Revisar iluminación",
    "Revisar luces de emergencia",
    "Revisar baños",
    "Revisar grifos",
    "Revisar cisternas",
    "Revisar desagües",
    "Revisar split aire acondicionado",
    "Otra",
]


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


def obtener_reset_form():
    if "prev_reset_form" not in st.session_state:
        st.session_state["prev_reset_form"] = 0
    return st.session_state["prev_reset_form"]


def resetear_formulario_preventivo():
    st.session_state["prev_reset_form"] = st.session_state.get("prev_reset_form", 0) + 1


def pantalla_preventivo():
    st.subheader("🔧 Mantenimiento preventivo")

    tab1, tab2 = st.tabs(["➕ Crear tarea", "📋 Tareas"])

    with tab1:
        reset = obtener_reset_form()

        with st.form(f"form_preventivo_{reset}", clear_on_submit=True):

            centro_sel = st.selectbox(
                "Centro",
                ["Selecciona..."] + CENTROS,
                key=f"prev_centro_{reset}"
            )
            centro = "" if centro_sel == "Selecciona..." else centro_sel

            edificios_disponibles = EDIFICIOS.get(centro, []) if centro else []
            edificio_sel = st.selectbox(
                "Edificio",
                ["Selecciona..."] + edificios_disponibles,
                key=f"prev_edificio_{reset}"
            )
            edificio = "" if edificio_sel == "Selecciona..." else edificio_sel

            espacios_disponibles = ESPACIOS.get(edificio, ["General", "Otro"]) if edificio else []
            espacio_sel = st.selectbox(
                "Espacio",
                ["Selecciona..."] + espacios_disponibles,
                key=f"prev_espacio_{reset}"
            )

            if espacio_sel == "Selecciona...":
                espacio = ""
            elif espacio_sel == "Otro":
                espacio = st.text_input("Especificar espacio", key=f"prev_espacio_otro_{reset}")
            else:
                espacio = espacio_sel

            area_sel = st.selectbox(
                "Área",
                ["Selecciona..."] + AREAS,
                key=f"prev_area_{reset}"
            )
            area = "" if area_sel == "Selecciona..." else area_sel

            tarea_sel = st.selectbox(
                "Tarea preventiva",
                ["Selecciona..."] + TAREAS_PREVENTIVAS,
                key=f"prev_tarea_select_{reset}"
            )

            if tarea_sel == "Selecciona...":
                tarea = ""
            elif tarea_sel == "Otra":
                tarea = st.text_input("Especificar tarea preventiva", key=f"prev_tarea_otra_{reset}")
            else:
                tarea = tarea_sel

            frecuencia_sel = st.selectbox(
                "Frecuencia",
                ["Selecciona...", "Semanal", "Mensual", "Trimestral", "Semestral", "Anual"],
                key=f"prev_frecuencia_{reset}"
            )
            frecuencia = "" if frecuencia_sel == "Selecciona..." else frecuencia_sel

            ultima_fecha = st.date_input(
                "Última revisión / fecha base",
                value=date.today(),
                key=f"prev_ultima_fecha_{reset}"
            )

            proxima_fecha = calcular_proxima_fecha(ultima_fecha, frecuencia)

            st.info(f"📅 Próxima fecha: {proxima_fecha}")

            operario_sel = st.selectbox(
                "Operario",
                ["Selecciona..."] + OPERARIOS,
                key=f"prev_operario_{reset}"
            )
            operario = "" if operario_sel == "Selecciona..." else operario_sel

            observaciones = st.text_area("Observaciones", key=f"prev_observaciones_{reset}")

            crear = st.form_submit_button("✅ Crear tarea preventiva", use_container_width=True)

            if crear:
                if not centro:
                    st.warning("Selecciona centro")
                elif not edificio:
                    st.warning("Selecciona edificio")
                elif not espacio:
                    st.warning("Selecciona espacio")
                elif not area:
                    st.warning("Selecciona área")
                elif not tarea:
                    st.warning("Selecciona tarea")
                elif not frecuencia:
                    st.warning("Selecciona frecuencia")
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

                    resetear_formulario_preventivo()
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
