import streamlit as st
from datetime import date, timedelta
from pathlib import Path

from config import CENTROS, EDIFICIOS, AREAS, OPERARIOS, ESPACIOS
from database.db import conectar, _sql
from modules.preventivo import generar_ots_preventivo_si_toca
from modules.espacios import (
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)
from ui.preventivo_aulas import pantalla_preventivo_aulas
from modules.inteligencia_preventivos import construir_panel_preventivo


TAREAS_PREVENTIVAS_POR_AREA = {
    "Electricidad": [
        "Revisar cuadro eléctrico",
        "Revisar magnetotérmicos",
        "Revisar diferenciales",
        "Revisar enchufes",
        "Revisar interruptores",
        "Revisar iluminación",
        "Revisar luces de emergencia",
        "Revisar canaletas y cableado visible",
        "Otra",
    ],

    "Fontanería": [
        "Revisar baños",
        "Revisar grifos",
        "Revisar cisternas",
        "Revisar fluxores",
        "Revisar desagües",
        "Revisar fugas visibles",
        "Revisar fregaderos",
        "Otra",
    ],

    "Climatización": [
        "Revisar split aire acondicionado",
        "Limpiar filtros de climatización",
        "Revisar desagüe de condensados",
        "Comprobar funcionamiento frío/calor",
        "Revisar unidad exterior",
        "Revisar soportes y vibraciones",
        "Otra",
    ],

    "Iluminación": [
        "Revisar iluminación",
        "Revisar luminarias",
        "Revisar luces de emergencia",
        "Revisar interruptores y pulsadores",
        "Otra",
    ],

    "Equipamiento": [
        "Revisar mesas y sillas",
        "Revisar mobiliario",
        "Revisar puertas y manetas",
        "Revisar ventanas y persianas",
        "Revisar pizarras",
        "Otra",
    ],

    "Informática": [
        "Revisar pantalla / proyector",
        "Revisar conexiones HDMI",
        "Revisar ordenador",
        "Revisar red y conectividad",
        "Revisar altavoces",
        "Otra",
    ],

    "ACS": [
        "Revisar acumulador ACS",
        "Revisar retorno ACS",
        "Revisar bomba de recirculación",
        "Revisar válvulas",
        "Revisar aislamiento",
        "Otra",
    ],

    "Jardinería": [
        "Revisar sistema de riego",
        "Revisar programador de riego",
        "Revisar árboles y ramas",
        "Revisar zonas verdes",
        "Otra",
    ],

    "Seguridad": [
        "Revisar puertas de emergencia",
        "Revisar señalización",
        "Revisar cierres y accesos",
        "Revisar elementos de protección",
        "Otra",
    ],

    "General": [
        "Revisión visual general",
        "Comprobación de funcionamiento",
        "Limpieza preventiva",
        "Lubricación",
        "Ajuste",
        "Otra",
    ],
}


def asegurar_columnas_preventivo():
    conn = conectar()
    cursor = conn.cursor()

    columnas = {
        "foto": "TEXT",
        "tipo": "TEXT DEFAULT 'Preventivo'",
        "prioridad": "TEXT DEFAULT 'Media'",
        "duracion_prevista": "TEXT",
        "material_necesario": "TEXT",
        "empresa_externa": "TEXT",
        "fecha_limite": "TEXT",
        "planta": "TEXT"
    }

    try:
        for columna, tipo in columnas.items():
            try:
                cursor.execute(f"""
                    ALTER TABLE preventivo_tareas
                    ADD COLUMN IF NOT EXISTS {columna} {tipo}
                """)
            except Exception:
                try:
                    cursor.execute(f"""
                        ALTER TABLE preventivo_tareas
                        ADD COLUMN {columna} {tipo}
                    """)
                except Exception:
                    pass

        conn.commit()

    except Exception:
        conn.rollback()

    finally:
        conn.close()


def ejecutar_preventivos_automaticos():
    """
    Comprueba automáticamente las planificaciones preventivas.
    La protección contra duplicados está en generar_ots_preventivo_si_toca().
    """
    try:
        n = generar_ots_preventivo_si_toca()

        if n > 0:
            st.toast(
                f"🔧 Se han generado {n} OTs preventivas automáticamente"
            )

    except Exception as e:
        st.warning(
            f"No se pudieron generar preventivos automáticos: {e}"
        )


def limpiar_nombre_archivo(texto):
    texto = str(texto or "")
    caracteres_malos = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for c in caracteres_malos:
        texto = texto.replace(c, "_")
    return texto.replace(" ", "_")


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


def existe_preventivo_duplicado(centro, edificio, espacio, area, tarea, frecuencia):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT COUNT(*)
        FROM preventivo_tareas
        WHERE centro = ?
          AND edificio = ?
          AND espacio = ?
          AND area = ?
          AND tarea = ?
          AND frecuencia = ?
          AND activo = 1
    """), (
        centro,
        edificio,
        espacio,
        area,
        tarea,
        frecuencia
    ))

    total = cursor.fetchone()[0]

    conn.close()
    return total > 0

def actualizar_planificacion_preventivo(
    tarea_id,
    frecuencia,
    proxima_fecha,
    operario,
    activo
):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE preventivo_tareas
            SET frecuencia = ?,
                proxima_fecha = ?,
                operario = ?,
                activo = ?
            WHERE id = ?
        """), (
            frecuencia,
            proxima_fecha,
            operario,
            1 if activo else 0,
            int(tarea_id)
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def mostrar_panel_inteligente_preventivo():
    st.markdown("## 🛠 Centro de Control Preventivo")

    centro_panel = st.selectbox(
        "Centro preventivo",
        ["Todos"] + CENTROS,
        key="preventivo_panel_centro"
    )

    centro_motor = None if centro_panel == "Todos" else centro_panel

    panel = construir_panel_preventivo(centro_motor)

    resumen = panel["resumen"]
    semaforo = panel.get("semaforo", [])
    prioridad_hoy = panel["prioridad_hoy"]
    prioridades = panel["prioridades"]
    areas = panel["areas"]
    recomendacion_inteligente = panel["recomendacion_inteligente"]

    color = resumen.get("color", "verde")
    score = resumen.get("score", 0)

    if color == "rojo":
        st.error(f"🔴 Estado preventivo · {score}% · {resumen.get('estado', '')}")
    elif color == "amarillo":
        st.warning(f"🟠 Estado preventivo · {score}% · {resumen.get('estado', '')}")
    else:
        st.success(f"🟢 Estado preventivo · {score}% · {resumen.get('estado', '')}")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", resumen.get("total", 0))
    c2.metric("Abiertos", resumen.get("abiertas", 0))
    c3.metric("Finalizados", resumen.get("finalizadas", 0))
    c4.metric("Vencidos", resumen.get("vencidas", 0))
    c5.metric("Próximos", resumen.get("proximas", 0))

    with st.container(border=True):
        st.markdown("### 🧠 Diagnóstico preventivo")

        for linea in resumen.get("diagnostico", []):
            st.markdown(f"• {linea}")

        if color == "rojo":
            st.error(f"🎯 {resumen.get('recomendacion', '')}")
        elif color == "amarillo":
            st.warning(f"🎯 {resumen.get('recomendacion', '')}")
        else:
            st.success(f"🎯 {resumen.get('recomendacion', '')}")

    st.markdown("### 🚦 Semáforo preventivo")

    cols = st.columns(len(semaforo))

    for col, item in zip(cols, semaforo):
        with col:
            if item.get("color") == "rojo":
                st.error(f"{item.get('icono')} **{item.get('nombre')}**\n\n{item.get('estado')}")
            elif item.get("color") == "amarillo":
                st.warning(f"{item.get('icono')} **{item.get('nombre')}**\n\n{item.get('estado')}")
            else:
                st.success(f"{item.get('icono')} **{item.get('nombre')}**\n\n{item.get('estado')}")

            st.caption(item.get("mensaje", ""))

    st.markdown("### 🎯 Si hoy solo hicieras una cosa...")

    with st.container(border=True):
        if prioridad_hoy:
            st.markdown(f"#### ⭐ {prioridad_hoy.get('numero_ot', '')}")
            st.markdown(f"### {prioridad_hoy.get('titulo', '')}")

            st.caption(
                f"{prioridad_hoy.get('centro', '')} · "
                f"{prioridad_hoy.get('edificio', '')} · "
                f"{prioridad_hoy.get('espacio', '')}"
            )

            st.markdown(f"**Área:** {prioridad_hoy.get('area', '-')}")
            st.markdown(f"**Fecha programada:** {prioridad_hoy.get('fecha_programada', '-')}")
            st.info(prioridad_hoy.get("accion", "Realizar preventivo."))

            st.markdown("#### 🧠 ¿Por qué recomienda esta actuación?")
            
            st.markdown(
                f"**Motivo:** {recomendacion_inteligente.get('motivo', '')}"
            )
            
            st.markdown(
                f"**Riesgo si no se actúa:** {recomendacion_inteligente.get('riesgo', '')}"
            )
            
            st.markdown(
                f"**Beneficio esperado:** {recomendacion_inteligente.get('beneficio', '')}"
            )
            
        else:
            st.success("No hay preventivos prioritarios pendientes.")

    st.markdown("## 📊 Salud del mantenimiento")

    if not areas:
        st.info("Todavía no hay información suficiente.")
    else:
        cols = st.columns(3)
    
        for i, area in enumerate(areas):
            with cols[i % 3]:
                color_area = area.get("color", "verde")
    
                if color_area == "rojo":
                    caja = st.container(border=True)
                elif color_area == "amarillo":
                    caja = st.container(border=True)
                else:
                    caja = st.container(border=True)
    
                with caja:
                    st.markdown(f"### {area.get('icono', '🟢')} {area.get('area', '-')}")
                    st.metric("Salud", f"{area.get('score', 0)}%")
                    st.markdown(f"**Estado:** {area.get('estado', '-')}")
                    st.markdown(f"📋 **Total:** {area.get('total', 0)}")
                    st.markdown(f"🔧 **Abiertos:** {area.get('abiertas', 0)}")
                    st.markdown(f"⏰ **Vencidos:** {area.get('vencidas', 0)}")
    
                    if color_area == "verde":
                        st.success("Área estable. Mantener seguimiento habitual.")
                    elif color_area == "amarillo":
                        st.warning("Conviene reducir preventivos abiertos.")
                    else:
                        st.error("Área prioritaria. Revisar cuanto antes.")

    with st.expander("📋 Prioridades preventivas", expanded=False):
        if not prioridades:
            st.success("No hay preventivos pendientes.")
        else:
            for i, p in enumerate(prioridades, start=1):
                st.markdown(
                    f"**{i}. {p.get('numero_ot', '')}** · "
                    f"{p.get('centro', '')} · {p.get('espacio', '')}"
                )
                st.caption(p.get("descripcion", ""))
                st.info(p.get("accion", ""))

    st.markdown("---")

def obtener_historico_preventivos():
    """
    Recupera las OT preventivas finalizadas y las enlaza con su
    planificación original para obtener planta, tarea y frecuencia.
    """
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT
            h.id,
            h.numero_ot,
            h.descripcion,
            h.fecha_creacion,
            h.fecha_cierre,
            h.centro,
            h.edificio,
            COALESCE(pr.planta, ''),
            h.espacio,
            h.area,
            h.operario,
            h.observaciones_cierre,
            COALESCE(pr.tarea, ''),
            COALESCE(pr.frecuencia, '')
        FROM historico_ordenes h
        LEFT JOIN preventivo_registros pr
            ON pr.numero_ot = h.numero_ot
        WHERE UPPER(COALESCE(h.origen, '')) = 'PREVENTIVO'
           OR UPPER(COALESCE(h.descripcion, '')) LIKE '[PREVENTIVO]%'
        ORDER BY h.id DESC
    """))

    datos = cursor.fetchall()
    conn.close()

    return datos


def obtener_checklist_historico_preventivo(numero_ot):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT
                item,
                hecho,
                fecha_hecho,
                operario,
                COALESCE(estado_revision, ''),
                COALESCE(observaciones_revision, ''),
                COALESCE(numero_ot_correctiva, '')
            FROM preventivo_checklist
            WHERE numero_ot = ?
            ORDER BY id ASC
        """), (numero_ot,))

        datos = cursor.fetchall()

    except Exception:
        conn.rollback()

        # Compatibilidad con checklists antiguos
        cursor.execute(_sql("""
            SELECT
                item,
                hecho,
                fecha_hecho,
                operario,
                '',
                COALESCE(observaciones, ''),
                ''
            FROM preventivo_checklist
            WHERE numero_ot = ?
            ORDER BY id ASC
        """), (numero_ot,))

        datos = cursor.fetchall()

    conn.close()
    return datos


def mostrar_historico_preventivo():
    st.markdown("### 📚 Histórico de mantenimiento preventivo")

    ot_abierta = st.session_state.get(
        "historico_preventivo_ot_abierta"
    )

    historico = obtener_historico_preventivos()

    if not historico:
        st.info("Todavía no hay preventivos finalizados.")
        return

    # ==================================================
    # DETALLE DE UNA SOLA REVISIÓN
    # ==================================================
    if ot_abierta:
        fila = next(
            (
                h for h in historico
                if str(h[1]) == str(ot_abierta)
            ),
            None
        )

        if fila is None:
            st.session_state.pop(
                "historico_preventivo_ot_abierta",
                None
            )
            st.rerun()

        (
            id_historico,
            numero_ot,
            descripcion,
            fecha_creacion,
            fecha_cierre,
            centro,
            edificio,
            planta,
            espacio,
            area,
            operario,
            observaciones_cierre,
            tarea,
            frecuencia,
        ) = fila

        if st.button(
            "⬅ Volver al histórico preventivo",
            key="volver_historico_preventivo",
            use_container_width=True
        ):
            st.session_state.pop(
                "historico_preventivo_ot_abierta",
                None
            )
            st.rerun()

        st.markdown(f"## {numero_ot}")

        st.markdown(
            f"""
**Tarea:** {tarea or descripcion or "-"}  
🏢 **Centro:** {centro or "-"}  
🏫 **Edificio:** {edificio or "-"}  
🧱 **Planta:** {planta or "-"}  
📍 **Espacio:** {espacio or "-"}  
🔧 **Área:** {area or "-"}  
🔁 **Frecuencia:** {frecuencia or "-"}  
👷 **Operario:** {operario or "-"}  
📅 **Fecha de cierre:** {fecha_cierre or "-"}
"""
        )

        if observaciones_cierre:
            st.markdown("#### Observaciones de cierre")
            st.info(str(observaciones_cierre))

        checks = obtener_checklist_historico_preventivo(
            numero_ot
        )

        st.markdown("### ✅ Checklist realizado")

        if not checks:
            st.info(
                "Esta OT no tiene checklist guardado o pertenece "
                "al sistema preventivo anterior."
            )
            return

        correctos = 0
        revisar = 0
        averias = 0

        for check in checks:
            (
                item,
                hecho,
                fecha_hecho,
                operario_check,
                estado_revision,
                observaciones_revision,
                numero_ot_correctiva,
            ) = check

            estado = str(estado_revision or "").strip()

            if not estado and bool(hecho):
                estado = "Correcto"

            if estado == "Correcto":
                icono = "✅"
                correctos += 1
            elif estado == "Revisar":
                icono = "🟡"
                revisar += 1
            elif estado == "Avería":
                icono = "🔴"
                averias += 1
            else:
                icono = "⚪"

            with st.container(border=True):
                st.markdown(f"**{icono} {item}**")
                st.caption(
                    f"Estado: {estado or 'Sin estado'} · "
                    f"Fecha: {fecha_hecho or '-'} · "
                    f"Operario: {operario_check or operario or '-'}"
                )

                if observaciones_revision:
                    st.write(observaciones_revision)

                if numero_ot_correctiva:
                    st.warning(
                        f"🔧 Correctiva vinculada: "
                        f"{numero_ot_correctiva}"
                    )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Puntos", len(checks))
        c2.metric("✅ Correctos", correctos)
        c3.metric("🟡 Revisar", revisar)
        c4.metric("🔴 Averías", averias)

        return

    # ==================================================
    # LISTADO LIGERO
    # ==================================================
    centros = sorted({
        str(fila[5])
        for fila in historico
        if fila[5]
    })

    areas = sorted({
        str(fila[9])
        for fila in historico
        if fila[9]
    })

    col1, col2 = st.columns(2)

    with col1:
        centro_filtro = st.selectbox(
            "Centro",
            ["Todos"] + centros,
            key="hist_prev_centro"
        )

    with col2:
        area_filtro = st.selectbox(
            "Área",
            ["Todas"] + areas,
            key="hist_prev_area"
        )

    buscar = st.text_input(
        "Buscar por OT, tarea, espacio u operario",
        key="hist_prev_buscar"
    ).strip().lower()

    filtrado = []

    for fila in historico:
        numero_ot = str(fila[1] or "")
        descripcion = str(fila[2] or "")
        centro = str(fila[5] or "")
        planta = str(fila[7] or "")
        espacio = str(fila[8] or "")
        area = str(fila[9] or "")
        operario = str(fila[10] or "")
        tarea = str(fila[12] or "")

        if centro_filtro != "Todos" and centro != centro_filtro:
            continue

        if area_filtro != "Todas" and area != area_filtro:
            continue

        texto_busqueda = " ".join([
            numero_ot,
            descripcion,
            centro,
            planta,
            espacio,
            area,
            operario,
            tarea,
        ]).lower()

        if buscar and buscar not in texto_busqueda:
            continue

        filtrado.append(fila)

    st.caption(
        f"Preventivos encontrados: {len(filtrado)}"
    )

    if not filtrado:
        st.info("No hay resultados con estos filtros.")
        return

    for fila in filtrado[:100]:
        (
            id_historico,
            numero_ot,
            descripcion,
            fecha_creacion,
            fecha_cierre,
            centro,
            edificio,
            planta,
            espacio,
            area,
            operario,
            observaciones_cierre,
            tarea,
            frecuencia,
        ) = fila

        with st.container(border=True):
            st.markdown(
                f"### ✅ {numero_ot} · {tarea or descripcion}"
            )

            st.caption(
                f"📅 {fecha_cierre or '-'} · "
                f"🏢 {centro or '-'} · "
                f"{edificio or '-'} · "
                f"{planta or '-'} · "
                f"{espacio or '-'}"
            )

            st.markdown(
                f"**Área:** {area or '-'} · "
                f"**Frecuencia:** {frecuencia or '-'} · "
                f"**Operario:** {operario or '-'}"
            )

            if st.button(
                "🔎 Ver revisión y checklist",
                key=f"abrir_hist_prev_{id_historico}",
                use_container_width=True
            ):
                st.session_state[
                    "historico_preventivo_ot_abierta"
                ] = numero_ot
                st.rerun()


def pantalla_preventivo():
    asegurar_columnas_preventivo()
    ejecutar_preventivos_automaticos()

    st.subheader("🔧 Mantenimiento preventivo")
    
    mostrar_panel_inteligente_preventivo()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "➕ Crear tarea",
            "📋 Tareas",
            "📅 Planificación",
            "📚 Histórico",
            "🏫 Preventivo aulas",
        ]
    )

    with tab1:
        centro = st.selectbox("Centro", CENTROS, key="prev_centro")

        edificios_disponibles = EDIFICIOS.get(centro, [])
        edificio = st.selectbox(
            "Edificio",
            edificios_disponibles,
            key=f"prev_edificio_{centro}"
        )

        plantas_disponibles = obtener_plantas_espacios(
            centro,
            edificio
        )
        
        if not plantas_disponibles:
            plantas_disponibles = ["Sin planta"]
        
        planta = st.selectbox(
            "Planta",
            plantas_disponibles,
            key=f"prev_planta_{centro}_{edificio}"
        )
        
        espacios_encontrados = obtener_espacios_por_planta(
            centro,
            edificio,
            planta
        )
        
        espacios_disponibles = [
            fila[0]
            for fila in espacios_encontrados
            if fila and fila[0]
        ]
        
        if not espacios_disponibles:
            espacios_disponibles = ["Otro"]
        
        espacio_sel = st.selectbox(
            "Espacio",
            espacios_disponibles,
            key=f"prev_espacio_{centro}_{edificio}_{planta}"
        )

        if espacio_sel == "Otro":
            espacio = st.text_input("Especificar espacio", key="prev_espacio_otro")
        else:
            espacio = espacio_sel

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

        area = st.selectbox(
            "Área",
            AREAS,
            key="prev_area"
        )
        
        tareas_disponibles = TAREAS_PREVENTIVAS_POR_AREA.get(
            area,
            TAREAS_PREVENTIVAS_POR_AREA["General"]
        )
        
        with st.form(
            key=f"form_preventivo_{area}",
            clear_on_submit=True
        ):
            tipo = st.selectbox(
                "Tipo de preventivo",
                ["Preventivo", "Normativo", "Inspección", "Limpieza", "Calibración", "Lubricación"],
                key="prev_tipo"
            )

            prioridad = st.selectbox(
                "Prioridad",
                ["Baja", "Media", "Alta"],
                index=1,
                key="prev_prioridad"
            )

            duracion_prevista = st.selectbox(
                "Duración prevista",
                ["15 min", "30 min", "45 min", "1 h", "2 h", "Más de 2 h"],
                key="prev_duracion"
            )

            material_necesario = st.text_area(
                "Material necesario",
                key="prev_material_necesario"
            )

            empresa_externa = st.text_input(
                "Empresa externa / mantenedor",
                key="prev_empresa_externa"
            )

            fecha_limite = st.date_input(
                "Fecha límite",
                value=proxima_fecha,
                key="prev_fecha_limite"
            )

            tarea_sel = st.selectbox(
                "Tarea preventiva",
                tareas_disponibles,
                key=f"prev_tarea_select_{area}"
            )

            if tarea_sel == "Otra":
                tarea = st.text_input("Especificar tarea preventiva", key="prev_tarea_otra")
            else:
                tarea = tarea_sel

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

            foto = st.file_uploader(
                "Foto preventiva (opcional)",
                type=["jpg", "jpeg", "png"],
                key="foto_preventivo"
            )

            foto_bytes = None
            foto_error = False

            if foto is not None:
                if foto.size > 5 * 1024 * 1024:
                    st.warning("La foto supera 5 MB. Sube una imagen más pequeña.")
                    foto_error = True
                else:
                    foto_bytes = foto.getvalue()
                    st.image(
                        foto_bytes,
                        caption="Foto preventiva",
                        use_container_width=True
                    )

            crear_de_todas_formas = st.checkbox(
                "Crear de todas formas si ya existe una preventiva igual",
                key="prev_crear_de_todas_formas"
            )

            crear = st.form_submit_button(
                "✅ Crear tarea preventiva",
                use_container_width=True
            )

            if crear:
                if foto_error:
                    st.error("No se puede guardar. La foto es demasiado grande.")
                    return

                if not str(tarea).strip():
                    st.warning("La tarea es obligatoria")
                elif not str(espacio).strip():
                    st.warning("Indica un espacio")
                elif not str(operario).strip():
                    st.warning("Indica un operario")
                else:
                    duplicado = existe_preventivo_duplicado(
                        centro,
                        edificio,
                        espacio,
                        area,
                        tarea,
                        frecuencia
                    )

                    if duplicado and not crear_de_todas_formas:
                        st.warning(
                            "⚠️ Ya existe una tarea preventiva igual activa en este mismo espacio. "
                            "Si realmente quieres duplicarla, marca la casilla de confirmación."
                        )
                    else:
                        ruta_foto = ""

                        if foto_bytes is not None:
                            try:
                                carpeta = Path("uploads/preventivo")
                                carpeta.mkdir(parents=True, exist_ok=True)

                                extension = foto.name.split(".")[-1].lower()
                                nombre_original = limpiar_nombre_archivo(foto.name)

                                nombre_foto = limpiar_nombre_archivo(
                                    f"{centro}_{edificio}_{espacio}_{tarea}_{nombre_original}"
                                )

                                if not nombre_foto.lower().endswith(f".{extension}"):
                                    nombre_foto = f"{nombre_foto}.{extension}"

                                ruta_foto = str(carpeta / nombre_foto)

                                with open(ruta_foto, "wb") as f:
                                    f.write(foto_bytes)

                            except Exception as e:
                                st.error(f"Error guardando foto: {e}")
                                return

                        conn = conectar()
                        cursor = conn.cursor()

                        cursor.execute(_sql("""
                            INSERT INTO preventivo_tareas
                            (
                                centro, edificio, planta, espacio, area,
                                tarea, frecuencia,
                                ultima_fecha, proxima_fecha,
                                operario, activo, observaciones, foto,
                                tipo, prioridad, duracion_prevista,
                                material_necesario, empresa_externa, fecha_limite
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?)
                        """), (
                            centro,
                            edificio,
                            planta,
                            espacio,
                            area,
                            tarea,
                            frecuencia,
                            str(ultima_fecha),
                            str(proxima_fecha),
                            operario,
                            1,
                            observaciones,
                            ruta_foto,
                            tipo,
                            prioridad,
                            duracion_prevista,
                            material_necesario,
                            empresa_externa,
                            str(fecha_limite)
                        ))

                        conn.commit()
                        conn.close()

                        st.success("Tarea preventiva creada correctamente")
                        st.rerun()

    with tab2:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, centro, edificio, planta, espacio, area, tarea,
                   frecuencia, ultima_fecha, proxima_fecha, operario, activo, foto,
                   tipo, prioridad, duracion_prevista, material_necesario,
                   empresa_externa, fecha_limite
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
                    id_tarea, centro, edificio, planta, espacio, area,
                    tarea, frecuencia, ultima_fecha, proxima_fecha, operario, activo, foto,
                    tipo, prioridad, duracion_prevista, material_necesario,
                    empresa_externa, fecha_limite
                ) = t

                estado = "🟢 Activa" if activo else "🔴 Inactiva"

                with st.expander(
                    f"{tarea} | {frecuencia} | Próxima: {proxima_fecha or '-'} | {estado}"
                ):
                    st.markdown(
                        f"""
                         🏢 {centro} · {edificio} · {planta} · {espacio} 
                        🔧 Área: {area}  
                        🧩 Tipo: {tipo or 'Preventivo'}  
                        🚦 Prioridad: {prioridad or 'Media'}  
                        ⏱️ Duración prevista: {duracion_prevista or '-'}  
                        👷 Operario: {operario or '-'}  
                        🏢 Empresa externa: {empresa_externa or '-'}  
                        📅 Última revisión: {ultima_fecha or '-'}  
                        📅 Próxima revisión: **{proxima_fecha or '-'}**  
                        📅 Fecha límite: **{fecha_limite or '-'}**
                        """
                    )

                    if material_necesario:
                        st.markdown("**📦 Material necesario:**")
                        st.write(material_necesario)

                    if foto:
                        try:
                            st.image(foto, caption="Foto preventiva", width=260)
                        except Exception:
                            st.caption("Foto preventiva no disponible.")

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

        st.info(
            "La generación preventiva se comprueba automáticamente al entrar en esta pantalla. "
            "Este botón queda como comprobación manual."
        )

        if st.button("🔄 Generar OTs preventivas que tocan", use_container_width=True):
            n = generar_ots_preventivo_si_toca()

            if n > 0:
                st.success(f"Se han generado {n} órdenes preventivas")
            else:
                st.info("No hay preventivos pendientes")

    with tab3:
        st.markdown("### 📅 Planificación preventiva")

        st.info(
            "Desde aquí puedes programar la próxima fecha, la frecuencia, "
            "el operario y activar o desactivar cada mantenimiento."
        )

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                centro,
                edificio,
                planta,
                espacio,
                area,
                tarea,
                frecuencia,
                proxima_fecha,
                operario,
                activo
            FROM preventivo_tareas
            ORDER BY centro, edificio, planta, espacio, tarea
        """)

        planificaciones = cursor.fetchall()
        conn.close()

        if not planificaciones:
            st.info("No hay tareas preventivas para planificar.")

        else:
            centros_plan = sorted({
                str(fila[1])
                for fila in planificaciones
                if fila[1]
            })

            centro_filtro_plan = st.selectbox(
                "Filtrar centro",
                ["Todos"] + centros_plan,
                key="filtro_plan_preventivo_centro"
            )

            planificaciones_filtradas = planificaciones

            if centro_filtro_plan != "Todos":
                planificaciones_filtradas = [
                    fila
                    for fila in planificaciones
                    if str(fila[1]) == centro_filtro_plan
                ]

            activas = len([
                fila for fila in planificaciones_filtradas
                if bool(fila[10])
            ])

            inactivas = len(planificaciones_filtradas) - activas

            hoy = date.today()

            vencidas = 0

            for fila in planificaciones_filtradas:
                try:
                    fecha_plan = date.fromisoformat(str(fila[8]))

                    if bool(fila[10]) and fecha_plan <= hoy:
                        vencidas += 1
                except Exception:
                    pass

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Planificadas", len(planificaciones_filtradas))
            c2.metric("Activas", activas)
            c3.metric("Inactivas", inactivas)
            c4.metric("Vencidas", vencidas)

            st.markdown("---")

            frecuencias_disponibles = [
                "Semanal",
                "Mensual",
                "Trimestral",
                "Semestral",
                "Anual",
            ]

            for fila in planificaciones_filtradas:
                (
                    tarea_id,
                    centro,
                    edificio,
                    planta,
                    espacio,
                    area,
                    tarea,
                    frecuencia,
                    proxima_fecha,
                    operario,
                    activo,
                ) = fila

                titulo = (
                    f"{centro} · {edificio} · {planta or '-'} · "
                    f"{espacio} · {tarea} · Próxima: {proxima_fecha or '-'}"
                )

                with st.expander(titulo, expanded=False):
                    st.caption(
                        f"🔧 Área: {area or '-'} · "
                        f"👷 Operario: {operario or '-'}"
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        frecuencia_actual = (
                            frecuencia
                            if frecuencia in frecuencias_disponibles
                            else "Mensual"
                        )

                        frecuencia_editada = st.selectbox(
                            "Frecuencia",
                            frecuencias_disponibles,
                            index=frecuencias_disponibles.index(
                                frecuencia_actual
                            ),
                            key=f"plan_prev_frecuencia_{tarea_id}"
                        )

                        try:
                            fecha_actual = date.fromisoformat(
                                str(proxima_fecha)
                            )
                        except Exception:
                            fecha_actual = date.today()

                        proxima_fecha_editada = st.date_input(
                            "Próxima fecha",
                            value=fecha_actual,
                            key=f"plan_prev_fecha_{tarea_id}"
                        )

                    with col2:
                        operario_actual = (
                            operario
                            if operario in OPERARIOS
                            else operario_por_centro(centro)
                        )

                        indice_operario = (
                            OPERARIOS.index(operario_actual)
                            if operario_actual in OPERARIOS
                            else 0
                        )

                        operario_editado = st.selectbox(
                            "Operario",
                            OPERARIOS,
                            index=indice_operario,
                            key=f"plan_prev_operario_{tarea_id}"
                        )

                        if operario_editado == "Otro":
                            operario_editado = st.text_input(
                                "Nombre operario",
                                value=str(operario or ""),
                                key=f"plan_prev_operario_otro_{tarea_id}"
                            )

                        activo_editado = st.checkbox(
                            "Planificación activa",
                            value=bool(activo),
                            key=f"plan_prev_activo_{tarea_id}"
                        )

                    if st.button(
                        "💾 Guardar planificación",
                        key=f"guardar_plan_prev_{tarea_id}",
                        use_container_width=True
                    ):
                        try:
                            actualizado = actualizar_planificacion_preventivo(
                                tarea_id=tarea_id,
                                frecuencia=frecuencia_editada,
                                proxima_fecha=proxima_fecha_editada.strftime(
                                    "%Y-%m-%d"
                                ),
                                operario=operario_editado,
                                activo=activo_editado
                            )

                            if actualizado:
                                generadas = generar_ots_preventivo_si_toca()
                            
                                if generadas > 0:
                                    st.success(
                                        f"Planificación guardada y {generadas} OT preventiva(s) "
                                        "generada(s) automáticamente."
                                    )
                                else:
                                    st.success(
                                        "Planificación actualizada correctamente."
                                    )
                            
                                st.rerun()

                        except Exception as e:
                            st.error(
                                f"No se ha podido actualizar: {e}"
                            )

            st.markdown("---")

            if st.button(
                "⚙️ Generar OTs preventivas que tocan hoy",
                key="generar_ots_desde_planificacion_preventiva",
                use_container_width=True
            ):
                try:
                    generadas = generar_ots_preventivo_si_toca()

                    if generadas > 0:
                        st.success(
                            f"Se han generado {generadas} OT preventivas."
                        )
                    else:
                        st.info(
                            "No hay preventivos pendientes de generar."
                        )

                    st.rerun()

                except Exception as e:
                    st.error(
                        f"No se han podido generar las OT: {e}"
                    )

    with tab4:
        mostrar_historico_preventivo()

    with tab5:
        pantalla_preventivo_aulas()
