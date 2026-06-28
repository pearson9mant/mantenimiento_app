import streamlit as st

from database.db import conectar, _sql, _es_postgres

from modules.ubicaciones import (
    CENTROS,
    obtener_edificios,
    obtener_espacios,
    obtener_ubicaciones_personalizadas,
    crear_espacio_personalizado,
    activar_desactivar_espacio,
    borrar_espacio_personalizado
)

from modules.espacios import (
    crear_tabla_espacios,
    crear_espacio,
    obtener_espacios as obtener_espacios_catalogo,
    desactivar_espacio,
    actualizar_espacio,
    obtener_arbol_espacios,
    PLANTAS_BASE,
)


TIPOS_PUNTO_LEGIONELLA = [
    "acumulador",
    "acumulador_solar",
    "retorno",
    "grifo",
    "ducha",
    "deposito",
    "otro"
]


INSTALACIONES_LEGIONELLA = [
    "ACS",
    "AFCH",
    "Solar",
    "Otro"
]


CATEGORIAS_CHECKLIST_PREVENTIVO = [
    "Electricidad",
    "Iluminación",
    "Fontanería",
    "Climatización / Split",
    "Otros"
]


# =====================================================
# LEGIONELLA
# =====================================================

def obtener_puntos_legionella():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, centro, edificio, instalacion, tipo_punto,
                   nombre_punto, ubicacion, activo, observaciones
            FROM legionella_puntos
            ORDER BY centro, edificio, instalacion, nombre_punto
        """)
        datos = cursor.fetchall()
    except Exception:
        datos = []

    conn.close()
    return datos


def crear_punto_legionella(centro, edificio, instalacion, tipo_punto, nombre_punto, ubicacion, observaciones):
    nombre_punto = str(nombre_punto or "").strip()
    instalacion = str(instalacion or "").strip()

    if not centro or not edificio:
        return False, "Centro o edificio inválido."

    if not nombre_punto or nombre_punto.lower() in ["none", "null"]:
        return False, "Debes indicar un nombre de punto válido."

    if not instalacion or instalacion.lower() in ["none", "null"]:
        return False, "Debes indicar una instalación válida."

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT COUNT(*) FROM legionella_puntos
        WHERE centro = ? AND edificio = ? AND nombre_punto = ?
    """), (centro, edificio, nombre_punto))

    if cursor.fetchone()[0] > 0:
        conn.close()
        return False, "Ese punto ya existe."

    cursor.execute(_sql("""
        INSERT INTO legionella_puntos
        (centro, edificio, instalacion, tipo_punto, nombre_punto, ubicacion, activo, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    """), (
        centro,
        edificio,
        instalacion,
        tipo_punto,
        nombre_punto,
        ubicacion,
        observaciones
    ))

    conn.commit()
    conn.close()

    return True, f"Punto creado: {nombre_punto}"


def limpiar_puntos_legionella_invalidos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE legionella_puntos
        SET activo = 0
        WHERE nombre_punto IS NULL
           OR nombre_punto = ''
           OR LOWER(nombre_punto) = 'none'
    """)

    afectados = cursor.rowcount

    conn.commit()
    conn.close()

    return afectados


def activar_desactivar_punto_legionella(id_punto, activo):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE legionella_puntos
        SET activo = ?
        WHERE id = ?
    """), (activo, id_punto))

    conn.commit()
    conn.close()

    return True


# =====================================================
# CHECKLIST PREVENTIVO CONFIGURABLE
# =====================================================

def asegurar_tabla_checklist_modelos():
    conn = conectar()
    cursor = conn.cursor()

    if _es_postgres():
        id_sql = "SERIAL PRIMARY KEY"
    else:
        id_sql = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS preventivo_checklist_modelos (
            id {id_sql},
            categoria TEXT,
            tarea_clave TEXT,
            item TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()


def crear_modelo_checklist(categoria, tarea_clave, item):
    categoria = str(categoria or "").strip()
    tarea_clave = str(tarea_clave or "").strip().lower()
    item = str(item or "").strip()

    if not categoria:
        return False, "Indica una categoría."

    if not tarea_clave:
        return False, "Indica una tarea clave."

    if not item:
        return False, "Indica el punto del checklist."

    asegurar_tabla_checklist_modelos()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT COUNT(*)
        FROM preventivo_checklist_modelos
        WHERE LOWER(categoria) = LOWER(?)
          AND LOWER(tarea_clave) = LOWER(?)
          AND LOWER(item) = LOWER(?)
    """), (categoria, tarea_clave, item))

    if cursor.fetchone()[0] > 0:
        conn.close()
        return False, "Ese punto ya existe para esa tarea."

    cursor.execute(_sql("""
        INSERT INTO preventivo_checklist_modelos
        (categoria, tarea_clave, item, activo)
        VALUES (?, ?, ?, 1)
    """), (categoria, tarea_clave, item))

    conn.commit()
    conn.close()

    return True, "Punto de checklist creado correctamente."


def obtener_modelos_checklist():
    asegurar_tabla_checklist_modelos()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, categoria, tarea_clave, item, activo
        FROM preventivo_checklist_modelos
        ORDER BY categoria, tarea_clave, id
    """)

    datos = cursor.fetchall()
    conn.close()
    return datos


def activar_desactivar_modelo_checklist(id_modelo, activo):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        UPDATE preventivo_checklist_modelos
        SET activo = ?
        WHERE id = ?
    """), (activo, id_modelo))

    conn.commit()
    conn.close()


def borrar_modelo_checklist(id_modelo):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        DELETE FROM preventivo_checklist_modelos
        WHERE id = ?
    """), (id_modelo,))

    conn.commit()
    conn.close()


def sembrar_modelos_checklist_por_defecto():
    modelos = [
        ("Electricidad", "cuadro", "Revisión visual del cuadro eléctrico"),
        ("Electricidad", "cuadro", "Comprobación de magnetotérmicos"),
        ("Electricidad", "cuadro", "Comprobación de diferenciales con botón TEST"),
        ("Electricidad", "cuadro", "Revisión de calentamientos, olores o ruidos"),
        ("Electricidad", "cuadro", "Apriete visual de bornes si procede"),
        ("Electricidad", "cuadro", "Limpieza interior de polvo si procede"),
        ("Electricidad", "cuadro", "Comprobación de tapas y señalización"),

        ("Electricidad", "enchufe", "Revisar enchufes sueltos"),
        ("Electricidad", "enchufe", "Comprobar tapas y mecanismos"),
        ("Electricidad", "enchufe", "Revisar calentamientos o marcas"),
        ("Electricidad", "enchufe", "Comprobar fijación a pared"),

        ("Iluminación", "iluminacion", "Comprobar encendido correcto"),
        ("Iluminación", "iluminacion", "Revisar lámparas o tubos fundidos"),
        ("Iluminación", "iluminacion", "Revisar pantallas o difusores"),
        ("Iluminación", "iluminacion", "Comprobar interruptores o pulsadores"),

        ("Iluminación", "emergencia", "Comprobar encendido de emergencia"),
        ("Iluminación", "emergencia", "Revisar pilotos de carga"),
        ("Iluminación", "emergencia", "Comprobar señalización de evacuación"),
        ("Iluminación", "emergencia", "Anotar luminarias defectuosas"),

        ("Fontanería", "baño", "Comprobar fugas visibles"),
        ("Fontanería", "baño", "Revisar grifos y pulsadores"),
        ("Fontanería", "baño", "Revisar cisternas o fluxores"),
        ("Fontanería", "baño", "Comprobar desagües"),
        ("Fontanería", "baño", "Comprobar malos olores"),

        ("Fontanería", "grifo", "Comprobar fugas"),
        ("Fontanería", "grifo", "Comprobar cierre correcto"),
        ("Fontanería", "grifo", "Comprobar presión de agua"),
        ("Fontanería", "grifo", "Revisar fijación y estado general"),

        ("Climatización / Split", "split", "Revisión visual de unidad interior"),
        ("Climatización / Split", "split", "Limpieza de filtros"),
        ("Climatización / Split", "split", "Comprobación de desagüe de condensados"),
        ("Climatización / Split", "split", "Comprobación de mando y encendido"),
        ("Climatización / Split", "split", "Comprobación de frío/calor"),
        ("Climatización / Split", "split", "Revisión de ruidos o vibraciones"),
        ("Climatización / Split", "split", "Revisión visual de unidad exterior"),
        ("Climatización / Split", "split", "Comprobación de soportes y fijaciones"),
        ("Climatización / Split", "split", "Comprobación de suciedad en batería exterior"),
        ("Climatización / Split", "split", "Anotar incidencias detectadas"),
    ]

    creados = 0

    for categoria, tarea_clave, item in modelos:
        ok, _ = crear_modelo_checklist(categoria, tarea_clave, item)
        if ok:
            creados += 1

    return creados


def pantalla_checklist_preventivo_config():
    st.markdown("### ✅ Checklist preventivo configurable")

    st.info(
        "Aquí puedes crear modelos de checklist. "
        "Cuando una tarea preventiva contenga la palabra clave, se cargarán estos puntos automáticamente."
    )

    if st.button("🌱 Cargar modelos por defecto", use_container_width=True):
        creados = sembrar_modelos_checklist_por_defecto()
        st.success(f"Modelos creados: {creados}")
        st.rerun()

    st.markdown("---")

    st.markdown("#### ➕ Añadir punto de checklist")

    categoria = st.selectbox(
        "Categoría",
        CATEGORIAS_CHECKLIST_PREVENTIVO,
        key="cfg_check_categoria"
    )

    tarea_clave = st.text_input(
        "Palabra clave de la tarea",
        placeholder="Ejemplo: cuadro, enchufe, emergencia, baño, split...",
        key="cfg_check_tarea_clave"
    )

    item = st.text_input(
        "Punto del checklist",
        placeholder="Ejemplo: Comprobación de diferenciales con botón TEST",
        key="cfg_check_item"
    )

    if st.button("➕ Crear punto de checklist", use_container_width=True):
        ok, mensaje = crear_modelo_checklist(categoria, tarea_clave, item)

        if ok:
            st.success(mensaje)
            st.rerun()
        else:
            st.warning(mensaje)

    st.markdown("---")

    st.markdown("#### 📋 Modelos existentes")

    modelos = obtener_modelos_checklist()

    if not modelos:
        st.info("Todavía no hay modelos de checklist.")
    else:
        for id_modelo, categoria, tarea_clave, item, activo in modelos:
            icono = "✅" if activo else "⛔"
            titulo = f"{icono} {categoria} · {tarea_clave} · {item}"

            with st.expander(titulo, expanded=False):
                st.markdown(f"**Categoría:** {categoria}")
                st.markdown(f"**Palabra clave:** {tarea_clave}")
                st.markdown(f"**Punto:** {item}")
                st.markdown(f"**Estado:** {'Activo' if activo else 'Desactivado'}")

                c1, c2 = st.columns(2)

                with c1:
                    if activo:
                        if st.button(
                            f"⛔ Desactivar {id_modelo}",
                            key=f"desactivar_check_modelo_{id_modelo}",
                            use_container_width=True
                        ):
                            activar_desactivar_modelo_checklist(id_modelo, 0)
                            st.rerun()
                    else:
                        if st.button(
                            f"✅ Activar {id_modelo}",
                            key=f"activar_check_modelo_{id_modelo}",
                            use_container_width=True
                        ):
                            activar_desactivar_modelo_checklist(id_modelo, 1)
                            st.rerun()

                with c2:
                    confirmar = st.checkbox(
                        "Confirmar borrado",
                        key=f"confirmar_borrar_check_modelo_{id_modelo}"
                    )

                    if st.button(
                        f"🗑️ Borrar {id_modelo}",
                        key=f"borrar_check_modelo_{id_modelo}",
                        use_container_width=True
                    ):
                        if confirmar:
                            borrar_modelo_checklist(id_modelo)
                            st.warning("Modelo eliminado.")
                            st.rerun()
                        else:
                            st.error("Marca la confirmación antes de borrar.")


# =====================================================
# BORRADOS CONTROLADOS
# =====================================================

def borrar_historico_ordenes():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM historico_ordenes")
        conn.commit()
        return True, "Histórico de órdenes eliminado correctamente."
    except Exception as e:
        conn.rollback()
        return False, f"Error al borrar histórico de órdenes: {e}"
    finally:
        conn.close()


def borrar_ordenes_activas():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM ordenes_trabajo")
        conn.commit()
        return True, "Órdenes activas eliminadas correctamente."
    except Exception as e:
        conn.rollback()
        return False, f"Error al borrar órdenes activas: {e}"
    finally:
        conn.close()


def borrar_historico_legionella():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM legionella_registros")
        cursor.execute("DELETE FROM legionella_incidencias")
        conn.commit()
        return True, "Histórico de Legionella eliminado correctamente."
    except Exception as e:
        conn.rollback()
        return False, f"Error al borrar histórico de Legionella: {e}"
    finally:
        conn.close()


def resetear_contador_ot():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM contador_ot")
        conn.commit()
        return True, "Contador OT reiniciado correctamente."
    except Exception as e:
        conn.rollback()
        return False, f"Error al reiniciar contador OT: {e}"
    finally:
        conn.close()


def pantalla_borrados_inicio():
    st.markdown("### 🧹 Borrados para empezar")

    st.warning("Zona delicada. Estos botones borran datos reales. Usa siempre la confirmación antes de ejecutar.")

    st.markdown("---")

    st.markdown("#### 1️⃣ Borrar solo histórico de órdenes")
    st.caption("Elimina solo las órdenes finalizadas guardadas en histórico. No toca órdenes activas ni contador.")

    confirmar_historico = st.checkbox(
        "Confirmo que quiero borrar SOLO el histórico de órdenes",
        key="confirmar_borrar_solo_historico"
    )

    if st.button("🧹 Borrar histórico de órdenes", use_container_width=True):
        if not confirmar_historico:
            st.error("Marca la confirmación antes de borrar.")
        else:
            ok, mensaje = borrar_historico_ordenes()

            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)

    st.markdown("---")

    st.markdown("#### 2️⃣ Borrar órdenes activas + contador")
    st.caption("Elimina órdenes pendientes/abiertas/en curso y reinicia numeración OT. No toca histórico.")

    confirmar_ordenes = st.checkbox(
        "Confirmo que quiero borrar órdenes activas y reiniciar contador",
        key="confirmar_borrar_ordenes_contador"
    )

    if st.button("🧯 Borrar órdenes activas + reset contador", use_container_width=True):
        if not confirmar_ordenes:
            st.error("Marca la confirmación antes de borrar.")
        else:
            ok1, msg1 = borrar_ordenes_activas()
            ok2, msg2 = resetear_contador_ot()

            if ok1 and ok2:
                st.success("Órdenes activas eliminadas y contador OT reiniciado correctamente.")
                st.rerun()
            else:
                st.error(msg1)
                st.error(msg2)

    st.markdown("---")

    st.markdown("#### 3️⃣ Borrar histórico de Legionella")
    st.caption("Elimina registros e incidencias de Legionella. No toca los puntos de control creados.")

    confirmar_legionella = st.checkbox(
        "Confirmo que quiero borrar el histórico de Legionella",
        key="confirmar_borrar_historico_legionella"
    )

    if st.button("💧 Borrar histórico Legionella", use_container_width=True):
        if not confirmar_legionella:
            st.error("Marca la confirmación antes de borrar.")
        else:
            ok, mensaje = borrar_historico_legionella()

            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)

    st.markdown("---")

    st.markdown("#### 4️⃣ Reinicio total septiembre")
    st.error("Esto borra órdenes activas, histórico de órdenes, histórico de Legionella y contador OT. No borra puntos de Legionella.")

    confirmar_total = st.checkbox(
        "Confirmo REINICIO TOTAL para septiembre",
        key="confirmar_reinicio_total_septiembre"
    )

    texto_seguridad = st.text_input(
        "Para confirmar escribe: SEPTIEMBRE",
        key="texto_confirmacion_septiembre"
    )

    if st.button("🔥 Reinicio TOTAL septiembre + contador", use_container_width=True):
        if not confirmar_total:
            st.error("Marca la confirmación antes de hacer el reinicio total.")
        elif texto_seguridad.strip().upper() != "SEPTIEMBRE":
            st.error("Debes escribir SEPTIEMBRE para confirmar.")
        else:
            ok1, msg1 = borrar_ordenes_activas()
            ok2, msg2 = borrar_historico_ordenes()
            ok3, msg3 = resetear_contador_ot()
            ok4, msg4 = borrar_historico_legionella()

            if ok1 and ok2 and ok3 and ok4:
                st.success("Reinicio total de septiembre realizado correctamente.")
                st.rerun()
            else:
                st.error(msg1)
                st.error(msg2)
                st.error(msg3)
                st.error(msg4)


# =====================================================
# CONFIGURACIÓN ESPACIOS
# =====================================================

def pantalla_configuracion_espacios():
    crear_tabla_espacios()

    st.markdown("### 🏫 Catálogo de espacios del colegio")

    sub1, sub2, sub3 = st.tabs([
        "➕ Crear",
        "📚 Catálogo",
        "🌳 Árbol del colegio"
    ])

    tipos_espacio = [
        "Aula",
        "WC",
        "Biblioteca",
        "Cocina",
        "Comedor",
        "Despacho",
        "Sala técnica",
        "Pasillo",
        "Patio",
        "Terrado",
        "Almacén",
        "Laboratorio",
        "Gimnasio",
        "Otro",
    ]

    with sub1:
        st.markdown("#### ➕ Crear nuevo espacio")

        centro = st.selectbox(
            "Centro",
            list(PLANTAS_BASE.keys()),
            key="cfg_catalogo_centro"
        )

        edificios = list(PLANTAS_BASE.get(centro, {}).keys())

        edificio = st.selectbox(
            "Edificio",
            edificios,
            key="cfg_catalogo_edificio"
        )

        plantas = PLANTAS_BASE.get(centro, {}).get(edificio, [])

        planta = st.selectbox(
            "Planta",
            plantas,
            key="cfg_catalogo_planta"
        )

        tipo = st.selectbox(
            "Tipo de espacio",
            tipos_espacio,
            key="cfg_catalogo_tipo"
        )

        if tipo == "Otro":
            tipo = st.text_input(
                "Especificar tipo",
                key="cfg_catalogo_tipo_otro"
            )

        espacio = st.text_input(
            "Nombre del espacio",
            placeholder="Ejemplo: Aula 6C, WC chicos, Biblioteca...",
            key="cfg_catalogo_espacio"
        )

        if st.button("💾 Guardar espacio", use_container_width=True):
            if not espacio:
                st.warning("Indica el nombre del espacio.")
            elif espacio == planta:
                st.error("La planta no puede guardarse como espacio.")
            else:
                ok = crear_espacio(
                    centro=centro,
                    edificio=edificio,
                    planta=planta,
                    espacio=espacio,
                    tipo=tipo
                )

                if ok:
                    st.success("Espacio guardado correctamente.")
                    st.rerun()
                else:
                    st.error("No se pudo guardar el espacio.")

    with sub2:
        st.markdown("#### 📚 Espacios registrados")

        espacios = obtener_espacios_catalogo(activos=True)

        if not espacios:
            st.info("Todavía no hay espacios registrados.")
        else:
            for id_espacio, centro, edificio, planta, espacio, tipo, activo in espacios:
                with st.expander(
                    f"🏫 {centro} · {edificio} · {planta} · {espacio} · {tipo}",
                    expanded=False
                ):
                    st.markdown(f"**Centro:** {centro}")
                    st.markdown(f"**Edificio:** {edificio}")
                    st.markdown(f"**Planta:** {planta}")
                    st.markdown(f"**Espacio:** {espacio}")
                    st.markdown(f"**Tipo:** {tipo}")

                    confirmar = st.checkbox(
                        "Confirmo desactivar este espacio",
                        key=f"confirmar_desactivar_catalogo_{id_espacio}"
                    )

                    if st.button(
                        "🗑️ Desactivar espacio",
                        key=f"desactivar_catalogo_{id_espacio}",
                        use_container_width=True
                    ):
                        if not confirmar:
                            st.error("Marca primero la confirmación.")
                        else:
                            desactivar_espacio(id_espacio)
                            st.warning("Espacio desactivado.")
                            st.rerun()

    with sub3:
        st.markdown("#### 🌳 Árbol del colegio")

        arbol = obtener_arbol_espacios()

        for centro, edificios in arbol.items():
            with st.expander(f"🏢 {centro}", expanded=True):
                for edificio, plantas in edificios.items():
                    with st.expander(f"🏫 {edificio}", expanded=False):
                        for planta, espacios in plantas.items():
                            with st.expander(f"📍 {planta}", expanded=False):
                                if not espacios:
                                    st.caption("Sin espacios registrados.")
                                else:
                                    for espacio in espacios:
                                        with st.expander(f"🏫 {espacio}", expanded=False):
                                            from ui.ui_colegio import ficha_espacio_basica
                                    
                                            ficha_espacio_basica(
                                                centro=centro,
                                                edificio=edificio,
                                                planta=planta,
                                                espacio=espacio
                                            )


# =====================================================
# PANTALLA CONFIGURACIÓN
# =====================================================

def pantalla_configuracion():
    st.subheader("⚙️ Configuración")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏫 Espacios",
        "💧 Legionella",
        "✅ Checklist preventivo",
        "🧹 Borrados"
    ])

    with tab1:
        pantalla_configuracion_espacios()

    with tab2:
        st.markdown("### 💧 Configuración Legionella")

        if st.button("🧹 Limpiar puntos inválidos (None)", use_container_width=True):
            afectados = limpiar_puntos_legionella_invalidos()
            st.success(f"{afectados} puntos limpiados/desactivados.")
            st.rerun()

        sub1, sub2 = st.tabs(["➕ Añadir punto", "📋 Puntos existentes"])

        with sub1:
            st.markdown("#### Añadir punto de control")

            centro_leg = st.selectbox("Centro", CENTROS, key="cfg_leg_centro")
            edificios_leg = obtener_edificios(centro_leg)
            edificio_leg = st.selectbox("Edificio", edificios_leg, key="cfg_leg_edificio")

            instalacion = st.selectbox(
                "Instalación",
                INSTALACIONES_LEGIONELLA,
                key="cfg_leg_instalacion"
            )

            if instalacion == "Otro":
                instalacion = st.text_input("Especificar instalación", key="cfg_leg_instalacion_otro")

            tipo_punto = st.selectbox(
                "Tipo de punto",
                TIPOS_PUNTO_LEGIONELLA,
                key="cfg_leg_tipo_punto"
            )

            nombre_punto = st.text_input(
                "Nombre del punto",
                placeholder="Ejemplo: Acumulador ACS 800L, Retorno ACS, Ducha vestuario..."
            )

            ubicacion = st.text_input(
                "Ubicación",
                placeholder="Ejemplo: Cuarto técnico, vestuario, sala calderas..."
            )

            observaciones = st.text_area("Observaciones")

            if st.button("➕ Crear punto Legionella", use_container_width=True):
                ok, mensaje = crear_punto_legionella(
                    centro=centro_leg,
                    edificio=edificio_leg,
                    instalacion=instalacion,
                    tipo_punto=tipo_punto,
                    nombre_punto=nombre_punto,
                    ubicacion=ubicacion,
                    observaciones=observaciones
                )

                if ok:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.warning(mensaje)

        with sub2:
            st.markdown("#### Puntos de control existentes")

            puntos = obtener_puntos_legionella()

            if not puntos:
                st.info("No hay puntos de Legionella creados.")
            else:
                for (
                    id_punto,
                    centro,
                    edificio,
                    instalacion,
                    tipo_punto,
                    nombre_punto,
                    ubicacion,
                    activo,
                    observaciones
                ) in puntos:

                    icono = "✅" if activo else "⛔"
                    titulo = f"{icono} {centro} · {edificio} · {nombre_punto}"

                    with st.expander(titulo, expanded=False):
                        st.markdown(f"**Centro:** {centro}")
                        st.markdown(f"**Edificio:** {edificio}")
                        st.markdown(f"**Instalación:** {instalacion}")
                        st.markdown(f"**Tipo punto:** {tipo_punto}")
                        st.markdown(f"**Nombre:** {nombre_punto}")
                        st.markdown(f"**Ubicación:** {ubicacion or '-'}")
                        st.markdown(f"**Estado:** {'Activo' if activo else 'Desactivado'}")

                        if observaciones:
                            st.info(observaciones)

                        if activo:
                            if st.button(
                                f"⛔ Desactivar punto {id_punto}",
                                key=f"desactivar_leg_{id_punto}",
                                use_container_width=True
                            ):
                                activar_desactivar_punto_legionella(id_punto, 0)
                                st.rerun()
                        else:
                            if st.button(
                                f"✅ Activar punto {id_punto}",
                                key=f"activar_leg_{id_punto}",
                                use_container_width=True
                            ):
                                activar_desactivar_punto_legionella(id_punto, 1)
                                st.rerun()

    with tab3:
        pantalla_checklist_preventivo_config()

    with tab4:
        pantalla_borrados_inicio()
