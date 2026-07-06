import streamlit as st
from datetime import date, timedelta
from pathlib import Path

from config import CENTROS, EDIFICIOS, AREAS, OPERARIOS, ESPACIOS
from database.db import conectar, _sql
from modules.preventivo import generar_ots_preventivo_si_toca
from modules.ubicaciones import obtener_espacios
from ui.preventivo_aulas import pantalla_preventivo_aulas
from modules.inteligencia_preventivos import construir_panel_preventivo


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
    "Revisar o lipiar placas solares",
    "Otra",
]


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
        "fecha_limite": "TEXT"
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
    Ejecuta la generación automática de OTs preventivas al entrar en la pantalla.
    Solo se ejecuta una vez por sesión para no repetir procesos en cada rerun.
    """
    if st.session_state.get("preventivos_auto_ejecutados"):
        return

    try:
        n = generar_ots_preventivo_si_toca()
        st.session_state["preventivos_auto_ejecutados"] = True

        if n > 0:
            st.toast(f"🔧 Se han generado {n} OTs preventivas automáticamente")

    except Exception as e:
        st.session_state["preventivos_auto_ejecutados"] = True
        st.warning(f"No se pudieron generar preventivos automáticos: {e}")


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
    semaforo = panel["semaforo"]
    prioridad_hoy = panel["prioridad_hoy"]
    prioridades = panel["prioridades"]
    areas = panel["areas"]

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
            st.caption(prioridad_hoy.get("motivo", ""))
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
    
                fondo = {
                    "verde": "#ecfdf5",
                    "amarillo": "#fffbeb",
                    "rojo": "#fef2f2",
                }.get(color_area, "#ecfdf5")
    
                borde = {
                    "verde": "#bbf7d0",
                    "amarillo": "#fde68a",
                    "rojo": "#fecaca",
                }.get(color_area, "#bbf7d0")
    
                if color_area == "verde":
                    valoracion = "Área estable. Mantener seguimiento habitual."
                elif color_area == "amarillo":
                    valoracion = "Conviene reducir preventivos abiertos para mantener la instalación estable."
                else:
                    valoracion = "Área prioritaria. Revisar actuaciones pendientes cuanto antes."
    
                st.markdown(
                    f"""
                    <div style="
                        background:{fondo};
                        border:1px solid {borde};
                        border-radius:18px;
                        padding:20px;
                        min-height:230px;
                        margin-bottom:16px;
                    ">
                        <h3>{area.get("icono", "🟢")} {area.get("area", "-")}</h3>
    
                        <h1>{area.get("score", 0)}%</h1>
    
                        <h4>{area.get("estado", "-")}</h4>
    
                        <hr>
    
                        <p>📋 <b>Total:</b> {area.get("total", 0)}</p>
                        <p>🔧 <b>Abiertos:</b> {area.get("abiertas", 0)}</p>
                        <p>⏰ <b>Vencidos:</b> {area.get("vencidas", 0)}</p>
    
                        <hr>
    
                        <p><b>Valoración:</b><br>{valoracion}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

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


def pantalla_preventivo():
    asegurar_columnas_preventivo()
    ejecutar_preventivos_automaticos()

    st.subheader("🔧 Mantenimiento preventivo")
    
    mostrar_panel_inteligente_preventivo()

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Crear tarea",
            "📋 Tareas",
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

        espacios_disponibles = obtener_espacios(edificio, centro)

        espacio_sel = st.selectbox(
            "Espacio",
            espacios_disponibles,
            key=f"prev_espacio_{centro}_{edificio}"
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

        with st.form("form_preventivo", clear_on_submit=True):
            area = st.selectbox("Área", AREAS, key="prev_area")

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
                TAREAS_PREVENTIVAS,
                key="prev_tarea_select"
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
                                centro, edificio, espacio, area,
                                tarea, frecuencia,
                                ultima_fecha, proxima_fecha,
                                operario, activo, observaciones, foto,
                                tipo, prioridad, duracion_prevista,
                                material_necesario, empresa_externa, fecha_limite
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            SELECT id, centro, edificio, espacio, area, tarea,
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
                    id_tarea, centro, edificio, espacio, area,
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
                        🏢 {centro} · {edificio} · {espacio}  
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
        pantalla_preventivo_aulas()
