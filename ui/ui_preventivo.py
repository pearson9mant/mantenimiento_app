import streamlit as st
from datetime import date, timedelta
from pathlib import Path

from config import CENTROS, AREAS, OPERARIOS
from database.db import conectar, _sql
from modules.preventivo import (
    generar_ots_preventivo_si_toca,
    frecuencia_a_dias,
)
from modules.espacios import (
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)
from ui.preventivo_aulas import pantalla_preventivo_aulas
from modules.inteligencia_preventivos import construir_panel_preventivo
from modules.cuadros_electricos import obtener_cuadros_electricos
from ui.ui_inteligencia_preventiva import (
    pantalla_inteligencia_preventiva,
)


_ESTRUCTURA_PREVENTIVO_ASEGURADA = False
_GENERACION_PREVENTIVO_COMPROBADA = False


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

    "Mantenimiento general aulas": [
        "Preventivo aulas",
        "Otra",
    ],

    "Mantenimiento general": [
        "Revisión visual general",
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
    global _ESTRUCTURA_PREVENTIVO_ASEGURADA

    if _ESTRUCTURA_PREVENTIVO_ASEGURADA:
        return

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

    _ESTRUCTURA_PREVENTIVO_ASEGURADA = True


def ejecutar_preventivos_automaticos():
    """Comprueba preventivos automáticos una sola vez por proceso."""
    global _GENERACION_PREVENTIVO_COMPROBADA

    if _GENERACION_PREVENTIVO_COMPROBADA:
        return

    try:
        n = generar_ots_preventivo_si_toca()
        _GENERACION_PREVENTIVO_COMPROBADA = True

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


def operario_por_centro(centro):
    if centro == "Pearson 9":
        return "Luis Lozano"
    if centro == "Pearson 22":
        return "J.A. Almeda"
    return OPERARIOS[0] if OPERARIOS else ""


def obtener_areas_preventivo():
    """
    Áreas disponibles únicamente dentro del módulo Preventivo.

    Se añade 'Mantenimiento general aulas' sin modificar config.AREAS,
    por lo que no afecta a incidencias, inventario, OT ni otros módulos.
    """
    areas = list(AREAS)

    area_aulas = "Mantenimiento general aulas"
    area_general = "Mantenimiento general"

    if area_aulas not in areas:
        areas.append(area_aulas)

    if area_general not in areas:
        areas.append(area_general)

    return areas


def existe_preventivo_duplicado(
    centro,
    edificio,
    planta,
    espacio,
    area,
    tarea,
    frecuencia
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT COUNT(*)
        FROM preventivo_tareas
        WHERE centro = ?
          AND edificio = ?
          AND COALESCE(planta, '') = ?
          AND espacio = ?
          AND area = ?
          AND tarea = ?
          AND frecuencia = ?
          AND activo = 1
    """), (
        centro,
        edificio,
        str(planta or ""),
        espacio,
        area,
        tarea,
        frecuencia
    ))

    total = cursor.fetchone()[0]
    conn.close()

    return total > 0


def crear_tarea_preventiva_planificada(
    centro,
    edificio,
    planta,
    espacio,
    area,
    tarea,
    frecuencia,
    proxima_fecha,
    operario,
    observaciones="",
    foto="",
    tipo="Preventivo",
    prioridad="Media",
    duracion_prevista="",
    material_necesario="",
    empresa_externa="",
    fecha_limite="",
):
    """
    Crea una tarea en preventivo_tareas sin generar directamente una OT.

    La OT la generará generar_ots_preventivo_si_toca() cuando corresponda,
    por lo que Preventivo de aulas usa exactamente el mismo circuito de
    Planificación que el resto de preventivos.
    """
    asegurar_columnas_preventivo()

    conn = conectar()
    cursor = conn.cursor()

    try:
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (
            centro,
            edificio,
            str(planta or ""),
            espacio,
            area,
            tarea,
            str(int(frecuencia_a_dias(frecuencia))),
            "",
            str(proxima_fecha),
            operario,
            1,
            observaciones,
            foto,
            tipo or "Preventivo",
            prioridad or "Media",
            duracion_prevista,
            material_necesario,
            empresa_externa,
            str(fecha_limite or proxima_fecha),
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def actualizar_planificacion_preventivo(
    tarea_id,
    frecuencia,
    proxima_fecha,
    operario,
    activo,
    area=None,
    tarea=None,
):
    """
    Actualiza la planificación preventiva.

    Compatibilidad:
    - Mantiene los parámetros históricos.
    - Área y tarea son opcionales para no romper llamadas antiguas.
    - No modifica centro, edificio, planta, espacio ni el ID.
    """
    conn = conectar()
    cursor = conn.cursor()

    try:
        if area is None and tarea is None:
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
        else:
            cursor.execute(_sql("""
                UPDATE preventivo_tareas
                SET area = ?,
                    tarea = ?,
                    frecuencia = ?,
                    proxima_fecha = ?,
                    operario = ?,
                    activo = ?
                WHERE id = ?
            """), (
                str(area or "").strip(),
                str(tarea or "").strip(),
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

    st.markdown("### ⚠️ Preventivo que requiere más atención")

    with st.container(border=True):
        if prioridad_hoy:
            st.markdown(
                f"#### 🔧 {prioridad_hoy.get('numero_ot', '')}"
            )

            st.markdown(
                f"### {prioridad_hoy.get('titulo', '')}"
            )

            st.caption(
                f"{prioridad_hoy.get('centro', '')} · "
                f"{prioridad_hoy.get('edificio', '')} · "
                f"{prioridad_hoy.get('espacio', '')}"
            )

            st.markdown(
                f"**Área:** "
                f"{prioridad_hoy.get('area', '-')}"
            )

            st.markdown(
                f"**Fecha programada:** "
                f"{prioridad_hoy.get('fecha_programada', '-')}"
            )

            st.info(
                "Este preventivo es el que requiere mayor atención "
                "dentro de la planificación preventiva."
            )

            st.markdown(
                "#### 🧠 Estado de esta actuación"
            )

            st.markdown(
                f"**Motivo:** "
                f"{recomendacion_inteligente.get('motivo', '')}"
            )

            st.markdown(
                f"**Riesgo de retrasarlo:** "
                f"{recomendacion_inteligente.get('riesgo', '')}"
            )

            st.markdown(
                f"**Beneficio de atenderlo:** "
                f"{recomendacion_inteligente.get('beneficio', '')}"
            )

            st.caption(
                "ℹ️ Este bloque analiza únicamente la planificación "
                "preventiva. La prioridad diaria de trabajo la determina "
                "el ❤️ Corazón."
            )

        else:
            st.success(
                "No hay preventivos pendientes que requieran "
                "atención especial."
            )

            st.caption(
                "La planificación preventiva se encuentra controlada. "
                "La prioridad diaria continúa siendo responsabilidad "
                "del ❤️ Corazón."
            )

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
            COALESCE(
                NULLIF(h.planta, ''),
                pr.planta,
                ''
            ),
            h.espacio,
            h.area,
            h.operario,
            h.observaciones_cierre,
            COALESCE(pr.tarea, ''),
            COALESCE(pr.frecuencia, '')
        FROM historico_ordenes h
        LEFT JOIN preventivo_registros pr
            ON pr.numero_ot = h.numero_ot
        WHERE (
                UPPER(COALESCE(h.numero_ot, '')) LIKE 'PREV-%'
                OR UPPER(COALESCE(h.descripcion, '')) LIKE '[PREVENTIVO]%'
              )
          AND UPPER(COALESCE(h.numero_ot, '')) NOT LIKE 'INC-%'
        ORDER BY h.id DESC
    """))

    datos = cursor.fetchall()
    conn.close()

    return datos


def borrar_historico_preventivo(
    id_historico,
    numero_ot,
):
    """
    Elimina una ejecución preventiva finalizada del histórico.

    Borra la ejecución y sus datos asociados, pero conserva
    la tarea preventiva y su planificación futura.
    """
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(
            _sql("""
                DELETE FROM preventivo_checklist
                WHERE numero_ot = ?
            """),
            (numero_ot,),
        )

        cursor.execute(
            _sql("""
                DELETE FROM preventivo_registros
                WHERE numero_ot = ?
            """),
            (numero_ot,),
        )

        cursor.execute(
            _sql("""
                DELETE FROM historico_ordenes
                WHERE id = ?
                  AND numero_ot = ?
            """),
            (
                int(id_historico),
                numero_ot,
            ),
        )

        conn.commit()
        return True, "Histórico preventivo eliminado correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo borrar el histórico preventivo: {e}"

    finally:
        conn.close()


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
🔁 **Frecuencia:** {frecuencia_a_dias(frecuencia)} días  
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
        ajustados = 0
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

            elif estado == "Ajustado":
                icono = "🛠"
                ajustados += 1
                
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

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Puntos", len(checks))
        c2.metric("✅ Correctos", correctos)
        c3.metric("🛠 Ajustados", ajustados)
        c4.metric("🟡 Revisar", revisar)
        c5.metric("🔴 Averías", averias)

        st.markdown("---")

        with st.expander(
            "🗑️ Eliminar este histórico preventivo",
            expanded=False,
        ):
            st.warning(
                "Se eliminará esta ejecución finalizada y sus registros "
                "asociados. La tarea preventiva y su planificación futura "
                "se conservarán."
            )

            confirmar_borrado = st.checkbox(
                "Confirmo que quiero eliminar este histórico preventivo",
                key=f"confirmar_borrar_hist_prev_{id_historico}",
            )

            texto_confirmacion = st.text_input(
                "Para confirmar escribe BORRAR",
                key=f"texto_borrar_hist_prev_{id_historico}",
            )

            if st.button(
                "🗑️ Borrar histórico preventivo",
                key=f"borrar_hist_prev_{id_historico}",
                use_container_width=True,
            ):
                if not confirmar_borrado:
                    st.error(
                        "Marca primero la casilla de confirmación."
                    )
                elif texto_confirmacion.strip().upper() != "BORRAR":
                    st.error(
                        "Escribe BORRAR para confirmar."
                    )
                else:
                    ok, mensaje = borrar_historico_preventivo(
                        id_historico=id_historico,
                        numero_ot=numero_ot,
                    )

                    if ok:
                        st.session_state.pop(
                            "historico_preventivo_ot_abierta",
                            None,
                        )
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)

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
                f"**Frecuencia:** {frecuencia_a_dias(frecuencia)} días · "
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
    
    panel_cargado = bool(
        st.session_state.get(
            "preventivo_panel_inteligente_cargado",
            False,
        )
    )

    if not panel_cargado:
        st.caption(
            "El Centro de Control Preventivo se carga solo cuando lo necesitas."
        )
        if st.button(
            "🧠 Cargar Centro de Control Preventivo",
            key="cargar_panel_inteligente_preventivo",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["preventivo_panel_inteligente_cargado"] = True
            st.rerun()
    else:
        c_panel1, c_panel2 = st.columns([4, 1])
        with c_panel1:
            st.success("Centro de Control Preventivo cargado.")
        with c_panel2:
            if st.button(
                "⚡ Ocultar",
                key="ocultar_panel_inteligente_preventivo",
                use_container_width=True,
            ):
                st.session_state["preventivo_panel_inteligente_cargado"] = False
                st.rerun()

        mostrar_panel_inteligente_preventivo()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "➕ Crear tarea",
            "📋 Tareas",
            "📅 Planificación",
            "📚 Histórico",
            "🏫 Preventivo aulas",
            "🧠 Inteligencia preventiva",
        ]
    )

    with tab1:
        # =====================================================
        # UBICACIÓN · CATÁLOGO CENTRAL
        # =====================================================

        centros_catalogo = obtener_centros_espacios()

        if not centros_catalogo:
            centros_catalogo = list(CENTROS)

        centro = st.selectbox(
            "Centro",
            centros_catalogo,
            key="prev_centro",
        )

        edificios_disponibles = obtener_edificios_espacios(
            centro
        )

        if not edificios_disponibles:
            st.warning(
                "Este centro todavía no tiene edificios "
                "registrados en Configuración → Espacios."
            )
            return

        edificio = st.selectbox(
            "Edificio",
            edificios_disponibles,
            key=f"prev_edificio_{centro}",
        )

        plantas_disponibles = obtener_plantas_espacios(
            centro,
            edificio,
        )

        if not plantas_disponibles:
            st.warning(
                "Este edificio todavía no tiene plantas "
                "registradas en el catálogo."
            )
            return

        planta = st.selectbox(
            "Planta",
            plantas_disponibles,
            key=f"prev_planta_{centro}_{edificio}",
        )

        espacios_encontrados = obtener_espacios_por_planta(
            centro,
            edificio,
            planta,
        )

        espacios_disponibles = [
            fila[0]
            for fila in espacios_encontrados
            if fila and fila[0]
        ]

        if not espacios_disponibles:
            st.warning(
                "No hay espacios registrados en esta planta. "
                "Añádelos desde Configuración → Espacios."
            )
            return

        espacio = st.selectbox(
            "Espacio",
            espacios_disponibles,
            key=f"prev_espacio_{centro}_{edificio}_{planta}",
        )

        frecuencia_dias = st.number_input(
            "Frecuencia en días",
            min_value=1,
            max_value=3650,
            value=30,
            step=1,
            key="prev_frecuencia_dias"
        )

        proxima_fecha = st.date_input(
            "Próxima fecha",
            value=date.today(),
            key="prev_proxima_fecha"
        )

        # La última revisión es un dato histórico.
        # Una tarea nueva todavía no ha sido revisada.
        ultima_fecha = ""

        areas_preventivo = obtener_areas_preventivo()

        area = st.selectbox(
            "Área",
            areas_preventivo,
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

            cuadro_preventivo_valido = True

            if (
                area == "Electricidad"
                and tarea_sel == "Revisar cuadro eléctrico"
            ):
                cuadros_ubicacion = []

                try:
                    cuadros_activos = obtener_cuadros_electricos(
                        solo_activos=True
                    )
                except Exception:
                    cuadros_activos = []

                for fila_cuadro in cuadros_activos:
                    if (
                        str(fila_cuadro[3] or "").strip() == str(centro or "").strip()
                        and str(fila_cuadro[4] or "").strip() == str(edificio or "").strip()
                        and str(fila_cuadro[5] or "").strip() == str(planta or "").strip()
                        and str(fila_cuadro[6] or "").strip() == str(espacio or "").strip()
                    ):
                        cuadros_ubicacion.append(
                            fila_cuadro
                        )

                if not cuadros_ubicacion:
                    cuadro_preventivo_valido = False
                    st.warning(
                        "No hay ningún cuadro eléctrico activo registrado "
                        "en esta ubicación. Créalo primero en "
                        "Configuración → Cuadros eléctricos."
                    )

                else:
                    opciones_cuadro = [
                        str(fila[1] or "").strip()
                        for fila in cuadros_ubicacion
                    ]

                    codigo_cuadro = st.selectbox(
                        "Cuadro eléctrico",
                        opciones_cuadro,
                        format_func=lambda codigo: next(
                            (
                                f"{fila[1]} · {fila[2]}"
                                for fila in cuadros_ubicacion
                                if str(fila[1]) == str(codigo)
                            ),
                            codigo,
                        ),
                        key="prev_cuadro_electrico",
                    )

                    tarea = (
                        f"Revisar cuadro eléctrico "
                        f"[{codigo_cuadro}]"
                    )

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

                if not cuadro_preventivo_valido:
                    st.warning(
                        "Selecciona una ubicación con un cuadro eléctrico "
                        "registrado antes de crear este preventivo."
                    )
                elif not str(tarea).strip():
                    st.warning("La tarea es obligatoria")
                elif not str(espacio).strip():
                    st.warning("Indica un espacio")
                elif not str(operario).strip():
                    st.warning("Indica un operario")
                else:
                    duplicado = existe_preventivo_duplicado(
                        centro,
                        edificio,
                        planta,
                        espacio,
                        area,
                        tarea,
                        str(int(frecuencia_dias))
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

                        crear_tarea_preventiva_planificada(
                            centro=centro,
                            edificio=edificio,
                            planta=planta,
                            espacio=espacio,
                            area=area,
                            tarea=tarea,
                            frecuencia=str(int(frecuencia_dias)),
                            proxima_fecha=str(proxima_fecha),
                            operario=operario,
                            observaciones=observaciones,
                            foto=ruta_foto,
                            tipo=tipo,
                            prioridad=prioridad,
                            duracion_prevista=duracion_prevista,
                            material_necesario=material_necesario,
                            empresa_externa=empresa_externa,
                            fecha_limite=str(fecha_limite),
                        )

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
            tareas_por_pagina = 20
            total_paginas_tareas = max(
                1, (len(tareas) + tareas_por_pagina - 1) // tareas_por_pagina
            )
            pagina_tareas = st.number_input(
                "Página de tareas",
                min_value=1,
                max_value=total_paginas_tareas,
                value=1,
                step=1,
                key="pagina_tareas_preventivo",
            )
            inicio_tareas = (int(pagina_tareas) - 1) * tareas_por_pagina
            fin_tareas = inicio_tareas + tareas_por_pagina

            st.caption(
                f"Mostrando {inicio_tareas + 1}-"
                f"{min(fin_tareas, len(tareas))} de {len(tareas)} tareas"
            )

            for t in tareas[inicio_tareas:fin_tareas]:
                (
                    id_tarea, centro, edificio, planta, espacio, area,
                    tarea, frecuencia, ultima_fecha, proxima_fecha, operario, activo, foto,
                    tipo, prioridad, duracion_prevista, material_necesario,
                    empresa_externa, fecha_limite
                ) = t

                estado = "🟢 Activa" if activo else "🔴 Inactiva"

                with st.expander(
                    f"{tarea} | {frecuencia_a_dias(frecuencia)} días | Próxima: {proxima_fecha or '-'} | {estado}"
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
                        clave_foto = "preventivo_foto_tarea_abierta"

                        foto_abierta = st.session_state.get(
                            clave_foto
                        )

                        if foto_abierta == id_tarea:
                            if st.button(
                                "🙈 Ocultar foto",
                                key=f"ocultar_foto_prev_{id_tarea}",
                            ):
                                st.session_state.pop(
                                    clave_foto,
                                    None,
                                )
                                st.rerun()

                            try:
                                st.image(
                                    foto,
                                    caption="Foto preventiva",
                                    width=260,
                                )
                            except Exception:
                                st.caption(
                                    "Foto preventiva no disponible."
                                )
                        else:
                            if st.button(
                                "📷 Ver foto",
                                key=f"ver_foto_prev_{id_tarea}",
                            ):
                                st.session_state[
                                    clave_foto
                                ] = id_tarea
                                st.rerun()

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

            plan_por_pagina = 15
            total_paginas_plan = max(
                1,
                (len(planificaciones_filtradas) + plan_por_pagina - 1)
                // plan_por_pagina
            )
            pagina_plan = st.number_input(
                "Página de planificación",
                min_value=1,
                max_value=total_paginas_plan,
                value=1,
                step=1,
                key="pagina_planificacion_preventivo",
            )
            inicio_plan = (int(pagina_plan) - 1) * plan_por_pagina
            fin_plan = inicio_plan + plan_por_pagina

            st.caption(
                f"Mostrando {inicio_plan + 1}-"
                f"{min(fin_plan, len(planificaciones_filtradas))} "
                f"de {len(planificaciones_filtradas)} planificaciones"
            )

            for fila in planificaciones_filtradas[inicio_plan:fin_plan]:
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
                        f"🔧 Área actual: {area or '-'} · "
                        f"👷 Operario: {operario or '-'}"
                    )

                    st.markdown("#### ✏️ Datos de la planificación")

                    col_dato1, col_dato2 = st.columns(2)

                    with col_dato1:
                        areas_planificacion = obtener_areas_preventivo()

                        indice_area = (
                            areas_planificacion.index(area)
                            if area in areas_planificacion
                            else 0
                        )

                        area_editada = st.selectbox(
                            "Área",
                            areas_planificacion,
                            index=indice_area,
                            key=f"plan_prev_area_{tarea_id}"
                        )

                    with col_dato2:
                        tareas_area = TAREAS_PREVENTIVAS_POR_AREA.get(
                            area_editada,
                            TAREAS_PREVENTIVAS_POR_AREA["General"]
                        )

                        tarea_actual = str(tarea or "").strip()
                        opciones_tarea = list(tareas_area)

                        if tarea_actual and tarea_actual not in opciones_tarea:
                            opciones_tarea = [tarea_actual] + opciones_tarea

                        tarea_seleccionada = st.selectbox(
                            "Tarea preventiva",
                            opciones_tarea,
                            index=(
                                opciones_tarea.index(tarea_actual)
                                if tarea_actual in opciones_tarea
                                else 0
                            ),
                            key=f"plan_prev_tarea_{tarea_id}"
                        )

                        if tarea_seleccionada == "Otra":
                            tarea_editada = st.text_input(
                                "Especificar tarea preventiva",
                                value="",
                                key=f"plan_prev_tarea_otra_{tarea_id}"
                            ).strip()
                        else:
                            tarea_editada = tarea_seleccionada

                    col1, col2 = st.columns(2)

                    with col1:
                        frecuencia_actual_dias = frecuencia_a_dias(
                            frecuencia,
                            defecto=30
                        )

                        frecuencia_editada = st.number_input(
                            "Frecuencia en días",
                            min_value=1,
                            max_value=3650,
                            value=int(frecuencia_actual_dias),
                            step=1,
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
                            if not str(tarea_editada or "").strip():
                                st.warning(
                                    "La tarea preventiva no puede quedar vacía."
                                )
                                actualizado = False
                            else:
                                actualizado = actualizar_planificacion_preventivo(
                                    tarea_id=tarea_id,
                                    frecuencia=str(int(frecuencia_editada)),
                                    proxima_fecha=proxima_fecha_editada.strftime(
                                        "%Y-%m-%d"
                                    ),
                                    operario=operario_editado,
                                    activo=activo_editado,
                                    area=area_editada,
                                    tarea=str(tarea_editada).strip(),
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

    with tab6:
        pantalla_inteligencia_preventiva()
