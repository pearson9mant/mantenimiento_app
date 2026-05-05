import streamlit as st
from datetime import date, timedelta

from config import CENTROS, EDIFICIOS, AREAS, OPERARIOS, ESPACIOS
from database.db import conectar, _sql
from modules.preventivo import generar_ots_preventivo_si_toca


TAREAS_PREVENTIVAS = [
    "",
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


def limpiar_formulario_preventivo():
    claves = [
        "prev_centro",
        "prev_edificio",
        "prev_espacio",
        "prev_area",
        "prev_tarea_select",
        "prev_tarea_otra",
        "prev_frecuencia",
        "prev_ultima_fecha",
        "prev_operario",
        "prev_observaciones",
    ]

    for c in claves:
        if c in st.session_state:
            del st.session_state[c]


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

        with st.form("form_preventivo", clear_on_submit=True):

            centro = st.selectbox("Centro", [""] + CENTROS, key="prev_centro")

            edificios_disponibles = EDIFICIOS.get(centro, []) if centro else []
            edificio = st.selectbox("Edificio", [""] + edificios_disponibles, key="prev_edificio")

            espacios_disponibles = ESPACIOS.get(edificio, ["General", "Otro"]) if edificio else []
            espacio_sel = st.selectbox("Espacio", [""] + espacios_disponibles, key="prev_espacio")

            if espacio_sel == "Otro":
                espacio = st.text_input("Especificar espacio")
            else:
                espacio = espacio_sel

            area = st.selectbox("Área", [""] + AREAS, key="prev_area")

            tarea_sel = st.selectbox("Tarea preventiva", TAREAS_PREVENTIVAS, key="prev_tarea_select")

            if tarea_sel == "Otra":
                tarea = st.text_input("Especificar tarea preventiva", key="prev_tarea_otra")
            else:
                tarea = tarea_sel

            frecuencia = st.selectbox(
                "Frecuencia",
                ["", "Semanal", "Mensual", "Trimestral", "Semestral", "Anual"],
                key="prev_frecuencia"
            )

            ultima_fecha = st.date_input(
                "Última revisión / fecha base",
                value=date.today(),
                key="prev_ultima_fecha"
            )

            proxima_fecha = calcular_proxima_fecha(ultima_fecha, frecuencia)

            st.info(f"📅 Próxima fecha: {proxima_fecha}")

            operario_auto = operario_por_centro(centro)

            operario = st.selectbox(
                "Operario",
                [""] + OPERARIOS,
                index=0,
                key="prev_operario"
            )

            observaciones = st.text_area("Observaciones", key="prev_observaciones")

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

                    limpiar_formulario_preventivo()

                    st.success("Tarea preventiva creada correctamente")
                    st.rerun()

    # -------------------------------
    # RESTO SIN TOCAR
    # -------------------------------
