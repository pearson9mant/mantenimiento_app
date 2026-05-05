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


def operario_por_centro(centro):
    if centro == "Pearson 9":
        return "Luis Lozano"
    if centro == "Pearson 22":
        return "J.A. Almeda"
    return OPERARIOS[0] if OPERARIOS else ""


def pantalla_preventivo():
    st.subheader("🔧 Mantenimiento preventivo")

    tab1, tab2 = st.tabs(["➕ Crear tarea", "📋 Tareas"])

    with tab1:
        centro = st.selectbox("Centro", CENTROS, key="prev_centro")

        edificios_disponibles = EDIFICIOS.get(centro, [])
        edificio = st.selectbox("Edificio", edificios_disponibles, key=f"prev_edificio_{centro}")

        espacios_disponibles = ESPACIOS.get(edificio, ["General", "Otro"])
        espacio_sel = st.selectbox("Espacio", espacios_disponibles, key=f"prev_espacio_{centro}_{edificio}")

        if espacio_sel == "Otro":
            espacio = st.text_input("Especificar espacio", key="prev_espacio_otro")
        else:
            espacio = espacio_sel

        with st.form("form_preventivo", clear_on_submit=True):
            area = st.selectbox("Área", AREAS, key="prev_area")

            tarea_sel = st.selectbox(
                "Tarea preventiva",
                TAREAS_PREVENTIVAS,
                key="prev_tarea_select"
            )

            if tarea_sel == "Otra":
                tarea = st.text_input("Especificar tarea preventiva", key="prev_tarea_otra")
            else:
                tarea = tarea_sel

            frecuencia = st.selectbox(
                "Frecuencia",
                ["Semanal", "Mensual", "Trimestral", "Semestral", "Anual"],
                key="prev_frecuencia"
            )

            ultima_fecha = st.date_input(
                "Última revisión / fecha base",
                value=date.today(),
                key="prev_ultima_fecha"
            )

            proxima_fecha = calcular_proxima_fecha(ultima_fecha, frecuencia)

            st.info(f"📅 Próxima fecha calculada automáticamente: {proxima_fecha}")

            operario_auto = operario_por_centro(centro)

            if operario_auto in OPERARIOS:
                indice_operario = OPERARIOS.index(operario_auto)
            else:
                indice_operario = 0

            operario_sel = st.selectbox(
                "Operario",
                OPERARIOS,
                index=indice_operario,
                key=f"prev_operario_{centro}"
            )

            if operario_sel == "Otro":
                operario = st.text_input("Nombre operario", key="prev_operario_otro")
            else:
                operario = operario_sel

            observaciones = st.text_area("Observaciones", key="prev_observaciones")

            crear = st.form_submit_button("✅ Crear tarea preventiva", use_container_width=True)

            if crear:
                if not str(tarea).strip():
                    st.warning("La tarea es obligatoria")
                elif not str(espacio).strip():
                    st.warning("Indica un espacio")
                elif not str(operario).strip():
                    st.warning("Indica un operario")
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
