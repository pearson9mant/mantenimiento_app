import streamlit as st
import pandas as pd

from ui.ui_graficos_gerencia import pantalla_demo_graficos_gerencia
from ui.ui_cuadros_electricos import pantalla_cuadros_electricos

from database.db import conectar, _sql, _es_postgres
from modules.colegio import obtener_estado_espacio, icono_estado_espacio
from ui.ui_arbol_colegio import mostrar_arbol_colegio

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
    icono_tipo_espacio,
    obtener_plantas_config,
    obtener_plantas_config_ubicacion,
    crear_planta_configurable,
    actualizar_visible_planta,
    qr_habilitado_espacio,
    habilitar_qr_todos_espacios_activos,
    PLANTAS_BASE,
)

from modules.ordenes import (
    obtener_propuestas_reclasificacion_areas,
    aplicar_reclasificacion_areas,
)
from modules.areas import AREAS_OT
from modules.accesos_gerencia import obtener_resumen_accesos_gerencia


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
# MODELO CONFIGURABLE · PREVENTIVO DE AULAS
# =====================================================

CATEGORIAS_MODELO_AULA = [
    "Mobiliario",
    "Electricidad",
    "Iluminación",
    "Climatización",
    "Informática / Audiovisual",
    "Carpintería / Cerramientos",
    "General",
]


TIPOS_LINEA_MODELO_AULA = [
    "Elemento inventariable",
    "Comprobación técnica",
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


def actualizar_modelo_checklist(
    id_modelo,
    categoria,
    tarea_clave,
    item,
):
    """
    Edita un modelo existente sin borrar su estado activo/desactivado.
    """
    categoria = str(categoria or "").strip()
    tarea_clave = str(tarea_clave or "").strip().lower()
    item = str(item or "").strip()

    if not categoria:
        return False, "Indica una categoría."

    if not tarea_clave:
        return False, "Indica una palabra clave."

    if not item:
        return False, "Indica el punto del checklist."

    asegurar_tabla_checklist_modelos()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT COUNT(*)
            FROM preventivo_checklist_modelos
            WHERE id <> ?
              AND LOWER(categoria) = LOWER(?)
              AND LOWER(tarea_clave) = LOWER(?)
              AND LOWER(item) = LOWER(?)
        """), (
            int(id_modelo),
            categoria,
            tarea_clave,
            item,
        ))

        if int(cursor.fetchone()[0] or 0) > 0:
            return False, "Ya existe otro punto igual para esa tarea."

        cursor.execute(_sql("""
            UPDATE preventivo_checklist_modelos
            SET categoria = ?,
                tarea_clave = ?,
                item = ?
            WHERE id = ?
        """), (
            categoria,
            tarea_clave,
            item,
            int(id_modelo),
        ))

        conn.commit()
        return True, "Modelo actualizado correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo actualizar el modelo: {e}"

    finally:
        conn.close()


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

        # Una única visita preventiva al baño debe revisar también
        # la iluminación visible del espacio.
        ("Iluminación", "baño", "Comprobar encendido de todas las luminarias"),
        ("Iluminación", "baño", "Revisar luces fundidas o parpadeos"),
        ("Iluminación", "baño", "Revisar pantallas y difusores"),
        ("Iluminación", "baño", "Comprobar interruptores o sensores de presencia"),
        ("Iluminación", "baño", "Comprobar luz de emergencia si existe"),

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
        "Aquí puedes crear y editar modelos de checklist. "
        "WC, baño y aseo utilizan la misma familia en el motor preventivo."
    )

    if st.button(
        "🌱 Cargar / completar modelos por defecto",
        use_container_width=True,
        key="cfg_check_sembrar_defecto",
    ):
        creados = sembrar_modelos_checklist_por_defecto()

        if creados:
            st.success(
                f"Se han añadido {creados} puntos que faltaban."
            )
        else:
            st.info(
                "Los modelos por defecto ya estaban cargados."
            )

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
        placeholder="Ejemplo: Comprobar sensor de presencia",
        key="cfg_check_item"
    )

    if st.button(
        "➕ Crear punto de checklist",
        use_container_width=True,
        key="cfg_check_crear",
    ):
        ok, mensaje = crear_modelo_checklist(
            categoria,
            tarea_clave,
            item,
        )

        if ok:
            st.success(mensaje)
            st.rerun()
        else:
            st.warning(mensaje)

    st.markdown("---")
    st.markdown("#### 📋 Modelos existentes")

    filtro_clave = st.text_input(
        "🔎 Buscar modelo",
        placeholder="Ejemplo: baño, iluminación, split...",
        key="cfg_check_buscar_modelo",
    )

    modelos = obtener_modelos_checklist()

    if filtro_clave:
        buscar = str(filtro_clave).strip().lower()

        modelos = [
            modelo
            for modelo in modelos
            if buscar in " ".join(
                str(valor or "").lower()
                for valor in modelo[1:4]
            )
        ]

    if not modelos:
        st.info("No hay modelos de checklist que mostrar.")
        return

    st.caption(
        f"{len(modelos)} modelo(s) mostrado(s). "
        "Los cambios afectan a futuros checklists; no modifican OT ya creadas."
    )

    for id_modelo, categoria_actual, tarea_clave_actual, item_actual, activo in modelos:
        icono = "✅" if activo else "⛔"
        titulo = (
            f"{icono} {categoria_actual} · "
            f"{tarea_clave_actual} · {item_actual}"
        )

        with st.expander(titulo, expanded=False):
            nueva_categoria = st.selectbox(
                "Categoría",
                CATEGORIAS_CHECKLIST_PREVENTIVO,
                index=(
                    CATEGORIAS_CHECKLIST_PREVENTIVO.index(categoria_actual)
                    if categoria_actual in CATEGORIAS_CHECKLIST_PREVENTIVO
                    else len(CATEGORIAS_CHECKLIST_PREVENTIVO) - 1
                ),
                key=f"editar_check_categoria_{id_modelo}",
            )

            nueva_clave = st.text_input(
                "Palabra clave",
                value=str(tarea_clave_actual or ""),
                key=f"editar_check_clave_{id_modelo}",
            )

            nuevo_item = st.text_area(
                "Punto del checklist",
                value=str(item_actual or ""),
                key=f"editar_check_item_{id_modelo}",
                height=90,
            )

            st.caption(
                f"Estado actual: {'Activo' if activo else 'Desactivado'}"
            )

            c1, c2 = st.columns(2)

            with c1:
                if st.button(
                    "💾 Guardar cambios",
                    key=f"guardar_check_modelo_{id_modelo}",
                    use_container_width=True,
                ):
                    ok, mensaje = actualizar_modelo_checklist(
                        id_modelo=id_modelo,
                        categoria=nueva_categoria,
                        tarea_clave=nueva_clave,
                        item=nuevo_item,
                    )

                    if ok:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.warning(mensaje)

            with c2:
                if activo:
                    texto_estado = "⛔ Desactivar"
                    nuevo_estado = 0
                else:
                    texto_estado = "✅ Activar"
                    nuevo_estado = 1

                if st.button(
                    texto_estado,
                    key=f"estado_check_modelo_{id_modelo}",
                    use_container_width=True,
                ):
                    activar_desactivar_modelo_checklist(
                        id_modelo,
                        nuevo_estado,
                    )
                    st.rerun()

            st.markdown("---")

            confirmar = st.checkbox(
                "Confirmar borrado definitivo",
                key=f"confirmar_borrar_check_modelo_{id_modelo}",
            )

            if st.button(
                "🗑️ Borrar modelo",
                key=f"borrar_check_modelo_{id_modelo}",
                use_container_width=True,
            ):
                if confirmar:
                    borrar_modelo_checklist(id_modelo)
                    st.warning("Modelo eliminado.")
                    st.rerun()
                else:
                    st.error(
                        "Marca la confirmación antes de borrar."
                    )



# =====================================================
# MODELO PREVENTIVO DE AULAS
# =====================================================

def asegurar_tabla_modelo_preventivo_aula():
    """
    Catálogo configurable que define qué se revisará dentro de un aula.

    No guarda todavía resultados de una revisión.
    Solo define el MODELO:
    - elementos inventariables con cantidad;
    - comprobaciones técnicas sin cantidad.

    Es independiente del checklist preventivo antiguo para no alterar
    los preventivos de cuadros, baños, splits, etc. que ya funcionan.
    """
    conn = conectar()
    cursor = conn.cursor()

    if _es_postgres():
        id_sql = "SERIAL PRIMARY KEY"
    else:
        id_sql = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS preventivo_aula_modelos (
            id {id_sql},
            categoria TEXT,
            elemento TEXT,
            tipo_linea TEXT,
            pide_cantidad INTEGER DEFAULT 1,
            cantidad_defecto INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            orden INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()



def asegurar_tabla_modelo_preventivo_aula_espacio():
    """
    Configuración específica por espacio.

    No duplica el catálogo general: solo guarda qué elementos del modelo
    general están activos o inactivos en un espacio concreto.
    """
    asegurar_tabla_modelo_preventivo_aula()

    conn = conectar()
    cursor = conn.cursor()

    if _es_postgres():
        id_sql = "SERIAL PRIMARY KEY"
    else:
        id_sql = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS preventivo_aula_modelo_espacios (
            id {id_sql},
            centro TEXT,
            edificio TEXT,
            planta TEXT,
            espacio TEXT,
            modelo_id INTEGER,
            activo INTEGER DEFAULT 1
        )
    """)

    conn.commit()

    # Índice único lógico por espacio + modelo.
    try:
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_prev_aula_modelo_espacio_unico
            ON preventivo_aula_modelo_espacios
            (centro, edificio, planta, espacio, modelo_id)
        """)
        conn.commit()
    except Exception:
        conn.rollback()

    conn.close()


def obtener_configuracion_modelo_aula_espacio(
    centro,
    edificio,
    planta,
    espacio,
):
    """
    Devuelve un diccionario {modelo_id: activo} para un espacio concreto.
    """
    asegurar_tabla_modelo_preventivo_aula_espacio()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(_sql("""
        SELECT modelo_id, activo
        FROM preventivo_aula_modelo_espacios
        WHERE centro = ?
          AND edificio = ?
          AND COALESCE(planta, '') = ?
          AND espacio = ?
    """), (
        centro,
        edificio,
        planta or "",
        espacio,
    ))

    datos = {
        int(modelo_id): int(activo or 0)
        for modelo_id, activo in cursor.fetchall()
    }

    conn.close()
    return datos


def guardar_estado_modelo_aula_espacio(
    centro,
    edificio,
    planta,
    espacio,
    modelo_id,
    activo,
):
    """
    Activa o desactiva un elemento del modelo general para un espacio.
    """
    asegurar_tabla_modelo_preventivo_aula_espacio()

    conn = conectar()
    cursor = conn.cursor()

    try:
        # Intento UPDATE primero.
        cursor.execute(_sql("""
            UPDATE preventivo_aula_modelo_espacios
            SET activo = ?
            WHERE centro = ?
              AND edificio = ?
              AND COALESCE(planta, '') = ?
              AND espacio = ?
              AND modelo_id = ?
        """), (
            1 if activo else 0,
            centro,
            edificio,
            planta or "",
            espacio,
            int(modelo_id),
        ))

        if cursor.rowcount == 0:
            cursor.execute(_sql("""
                INSERT INTO preventivo_aula_modelo_espacios
                (
                    centro,
                    edificio,
                    planta,
                    espacio,
                    modelo_id,
                    activo
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """), (
                centro,
                edificio,
                planta or "",
                espacio,
                int(modelo_id),
                1 if activo else 0,
            ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def copiar_modelo_general_a_espacio(
    centro,
    edificio,
    planta,
    espacio,
):
    """
    Inicializa la configuración del espacio copiando el estado activo actual
    del modelo general. No cambia el catálogo general.
    """
    modelos = obtener_modelos_preventivo_aula(
        solo_activos=False
    )

    if not modelos:
        return 0

    guardados = 0

    for (
        modelo_id,
        categoria,
        elemento,
        tipo_linea,
        pide_cantidad,
        cantidad_defecto,
        activo,
        orden,
    ) in modelos:
        if guardar_estado_modelo_aula_espacio(
            centro=centro,
            edificio=edificio,
            planta=planta,
            espacio=espacio,
            modelo_id=modelo_id,
            activo=bool(activo),
        ):
            guardados += 1

    return guardados


def restablecer_modelo_espacio_a_general(
    centro,
    edificio,
    planta,
    espacio,
):
    """
    Elimina la personalización del espacio.
    La siguiente revisión vuelve a usar el modelo general activo.
    """
    asegurar_tabla_modelo_preventivo_aula_espacio()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            DELETE FROM preventivo_aula_modelo_espacios
            WHERE centro = ?
              AND edificio = ?
              AND COALESCE(planta, '') = ?
              AND espacio = ?
        """), (
            centro,
            edificio,
            planta or "",
            espacio,
        ))

        afectados = cursor.rowcount
        conn.commit()
        return int(afectados or 0)

    except Exception:
        conn.rollback()
        return 0

    finally:
        conn.close()


def crear_modelo_preventivo_aula(
    categoria,
    elemento,
    tipo_linea,
    pide_cantidad=True,
    cantidad_defecto=0,
):
    categoria = str(categoria or "").strip()
    elemento = str(elemento or "").strip()
    tipo_linea = str(tipo_linea or "").strip()

    if not categoria:
        return False, "Indica una categoría."

    if not elemento:
        return False, "Indica el elemento o comprobación."

    if tipo_linea not in TIPOS_LINEA_MODELO_AULA:
        return False, "Tipo de línea no válido."

    if tipo_linea == "Comprobación técnica":
        pide_cantidad = False
        cantidad_defecto = 0

    try:
        cantidad_defecto = max(
            0,
            int(cantidad_defecto or 0),
        )
    except Exception:
        cantidad_defecto = 0

    asegurar_tabla_modelo_preventivo_aula()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT COUNT(*)
            FROM preventivo_aula_modelos
            WHERE LOWER(TRIM(categoria)) = LOWER(TRIM(?))
              AND LOWER(TRIM(elemento)) = LOWER(TRIM(?))
        """), (
            categoria,
            elemento,
        ))

        if int(cursor.fetchone()[0] or 0) > 0:
            return False, "Ese elemento ya existe en el modelo de aula."

        cursor.execute("""
            SELECT COALESCE(MAX(orden), 0)
            FROM preventivo_aula_modelos
        """)

        siguiente_orden = int(
            cursor.fetchone()[0] or 0
        ) + 10

        cursor.execute(_sql("""
            INSERT INTO preventivo_aula_modelos
            (
                categoria,
                elemento,
                tipo_linea,
                pide_cantidad,
                cantidad_defecto,
                activo,
                orden
            )
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """), (
            categoria,
            elemento,
            tipo_linea,
            1 if pide_cantidad else 0,
            cantidad_defecto,
            siguiente_orden,
        ))

        conn.commit()
        return True, "Elemento añadido al modelo de aula."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo crear el elemento: {e}"

    finally:
        conn.close()


def obtener_modelos_preventivo_aula(
    solo_activos=False,
):
    asegurar_tabla_modelo_preventivo_aula()

    conn = conectar()
    cursor = conn.cursor()

    sql = """
        SELECT
            id,
            categoria,
            elemento,
            tipo_linea,
            pide_cantidad,
            cantidad_defecto,
            activo,
            orden
        FROM preventivo_aula_modelos
    """

    if solo_activos:
        sql += " WHERE activo = 1"

    sql += """
        ORDER BY
            orden ASC,
            categoria ASC,
            elemento ASC
    """

    cursor.execute(sql)
    datos = cursor.fetchall()

    conn.close()
    return datos


def actualizar_modelo_preventivo_aula(
    id_modelo,
    categoria,
    elemento,
    tipo_linea,
    pide_cantidad,
    cantidad_defecto,
):
    categoria = str(categoria or "").strip()
    elemento = str(elemento or "").strip()
    tipo_linea = str(tipo_linea or "").strip()

    if not categoria:
        return False, "Indica una categoría."

    if not elemento:
        return False, "Indica el elemento o comprobación."

    if tipo_linea not in TIPOS_LINEA_MODELO_AULA:
        return False, "Tipo de línea no válido."

    if tipo_linea == "Comprobación técnica":
        pide_cantidad = False
        cantidad_defecto = 0

    try:
        cantidad_defecto = max(
            0,
            int(cantidad_defecto or 0),
        )
    except Exception:
        cantidad_defecto = 0

    asegurar_tabla_modelo_preventivo_aula()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT COUNT(*)
            FROM preventivo_aula_modelos
            WHERE id <> ?
              AND LOWER(TRIM(categoria)) = LOWER(TRIM(?))
              AND LOWER(TRIM(elemento)) = LOWER(TRIM(?))
        """), (
            int(id_modelo),
            categoria,
            elemento,
        ))

        if int(cursor.fetchone()[0] or 0) > 0:
            return False, "Ya existe otro elemento igual."

        cursor.execute(_sql("""
            UPDATE preventivo_aula_modelos
            SET categoria = ?,
                elemento = ?,
                tipo_linea = ?,
                pide_cantidad = ?,
                cantidad_defecto = ?
            WHERE id = ?
        """), (
            categoria,
            elemento,
            tipo_linea,
            1 if pide_cantidad else 0,
            cantidad_defecto,
            int(id_modelo),
        ))

        conn.commit()
        return True, "Modelo actualizado correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo actualizar: {e}"

    finally:
        conn.close()


def activar_desactivar_modelo_preventivo_aula(
    id_modelo,
    activo,
):
    asegurar_tabla_modelo_preventivo_aula()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE preventivo_aula_modelos
            SET activo = ?
            WHERE id = ?
        """), (
            1 if activo else 0,
            int(id_modelo),
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def borrar_modelo_preventivo_aula(
    id_modelo,
):
    """
    Borrado físico disponible únicamente desde Configuración.
    Para el uso normal es preferible desactivar, preservando el modelo.
    """
    asegurar_tabla_modelo_preventivo_aula()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            DELETE FROM preventivo_aula_modelos
            WHERE id = ?
        """), (
            int(id_modelo),
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def sembrar_modelo_preventivo_aula():
    """
    Modelo inicial.

    No impone cantidades reales del colegio.
    Las cantidades por defecto solo sirven como ayuda en la primera
    revisión y podrán modificarse desde Configuración.
    """
    modelos = [
        # -------------------------------------------------
        # MOBILIARIO / CENSO
        # -------------------------------------------------
        (
            "Mobiliario",
            "Silla alumno",
            "Elemento inventariable",
            True,
            25,
        ),
        (
            "Mobiliario",
            "Mesa alumno",
            "Elemento inventariable",
            True,
            25,
        ),
        (
            "Mobiliario",
            "Mesa profesor",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Mobiliario",
            "Silla profesor",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Mobiliario",
            "Armario",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Mobiliario",
            "Pizarra tradicional",
            "Elemento inventariable",
            True,
            1,
        ),

        # -------------------------------------------------
        # INFORMÁTICA / AUDIOVISUAL
        # -------------------------------------------------
        (
            "Informática / Audiovisual",
            "Pizarra digital",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Informática / Audiovisual",
            "Proyector",
            "Elemento inventariable",
            True,
            0,
        ),
        (
            "Informática / Audiovisual",
            "Pantalla de proyección manual",
            "Elemento inventariable",
            True,
            0,
        ),
        (
            "Informática / Audiovisual",
            "Pantalla de proyección eléctrica",
            "Elemento inventariable",
            True,
            0,
        ),

        # -------------------------------------------------
        # ELECTRICIDAD DEL AULA
        # Los cuadros generales de planta quedan fuera.
        # -------------------------------------------------
        (
            "Electricidad",
            "Cuadro eléctrico del aula",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Electricidad",
            "Diferencial del aula",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Electricidad",
            "Magnetotérmico 16A enchufes",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Electricidad",
            "Magnetotérmico 10A iluminación",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Electricidad",
            "Enchufes",
            "Elemento inventariable",
            True,
            6,
        ),
        (
            "Electricidad",
            "Prueba visual del cuadro eléctrico del aula",
            "Comprobación técnica",
            False,
            0,
        ),
        (
            "Electricidad",
            "Prueba del diferencial",
            "Comprobación técnica",
            False,
            0,
        ),

        # -------------------------------------------------
        # ILUMINACIÓN
        # -------------------------------------------------
        (
            "Iluminación",
            "Luminarias",
            "Elemento inventariable",
            True,
            0,
        ),
        (
            "Iluminación",
            "Interruptores / pulsadores",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Iluminación",
            "Luz de emergencia",
            "Elemento inventariable",
            True,
            0,
        ),
        (
            "Iluminación",
            "Comprobar encendido general",
            "Comprobación técnica",
            False,
            0,
        ),

        # -------------------------------------------------
        # CLIMATIZACIÓN
        # -------------------------------------------------
        (
            "Climatización",
            "Aire acondicionado",
            "Elemento inventariable",
            True,
            0,
        ),
        (
            "Climatización",
            "Limpieza / estado de filtros",
            "Comprobación técnica",
            False,
            0,
        ),
        (
            "Climatización",
            "Desagüe de condensados",
            "Comprobación técnica",
            False,
            0,
        ),
        (
            "Climatización",
            "Funcionamiento frío / calor",
            "Comprobación técnica",
            False,
            0,
        ),
        (
            "Climatización",
            "Ruidos o vibraciones anómalas",
            "Comprobación técnica",
            False,
            0,
        ),

        # -------------------------------------------------
        # CERRAMIENTOS
        # -------------------------------------------------
        (
            "Carpintería / Cerramientos",
            "Puerta",
            "Elemento inventariable",
            True,
            1,
        ),
        (
            "Carpintería / Cerramientos",
            "Ventanas",
            "Elemento inventariable",
            True,
            0,
        ),
        (
            "Carpintería / Cerramientos",
            "Persianas",
            "Elemento inventariable",
            True,
            0,
        ),

        # -------------------------------------------------
        # GENERAL
        # -------------------------------------------------
        (
            "General",
            "Estado de pintura",
            "Comprobación técnica",
            False,
            0,
        ),
        (
            "General",
            "Estado general del aula",
            "Comprobación técnica",
            False,
            0,
        ),
    ]

    creados = 0

    for (
        categoria,
        elemento,
        tipo_linea,
        pide_cantidad,
        cantidad_defecto,
    ) in modelos:

        ok, _ = crear_modelo_preventivo_aula(
            categoria=categoria,
            elemento=elemento,
            tipo_linea=tipo_linea,
            pide_cantidad=pide_cantidad,
            cantidad_defecto=cantidad_defecto,
        )

        if ok:
            creados += 1

    return creados


def pantalla_modelo_preventivo_aula_config():
    asegurar_tabla_modelo_preventivo_aula()
    asegurar_tabla_modelo_preventivo_aula_espacio()

    st.markdown("### 🧩 Modelo base de aulas")

    modo_modelo_aulas = st.radio(
        "Configuración del modelo",
        [
            "📋 Modelo general",
            "🏫 Por aula / espacio",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="cfg_modelo_aula_modo",
    )

    if modo_modelo_aulas == "🏫 Por aula / espacio":
        pantalla_modelo_preventivo_aula_por_espacio()
        return

    st.info(
        "Aquí defines el MODELO BASE: qué elementos pueden formar parte "
        "del inventario inicial de un aula. No es el inventario real de "
        "cada espacio. Las cantidades reales se guardan en Inventario espacios."
    )

    st.caption(
        "Las líneas antiguas de «Comprobación técnica» se conservan por "
        "compatibilidad, pero el nuevo Preventivo de aulas trabaja con "
        "inventario vivo + revisión general + incidencias INC."
    )

    if st.button(
        "🌱 Cargar / completar modelo inicial de aula",
        key="cfg_modelo_aula_sembrar",
        use_container_width=True,
    ):
        creados = sembrar_modelo_preventivo_aula()

        if creados > 0:
            st.success(
                f"Modelo de aula completado. "
                f"Se han añadido {creados} elementos que faltaban."
            )
        else:
            st.info(
                "El modelo inicial ya estaba cargado."
            )

        st.rerun()

    modelos = obtener_modelos_preventivo_aula()

    total_activos = sum(
        1
        for fila in modelos
        if bool(fila[6])
    )

    total_inventariables = sum(
        1
        for fila in modelos
        if bool(fila[6])
        and str(fila[3]) == "Elemento inventariable"
    )

    total_comprobaciones = sum(
        1
        for fila in modelos
        if bool(fila[6])
        and str(fila[3]) == "Comprobación técnica"
    )

    m1, m2, m3 = st.columns(3)

    m1.metric(
        "Activos",
        total_activos,
    )

    m2.metric(
        "📦 Inventariables",
        total_inventariables,
    )

    m3.metric(
        "🔧 Comprobaciones",
        total_comprobaciones,
    )

    st.markdown("---")
    st.markdown("#### ➕ Añadir elemento o comprobación")

    c1, c2 = st.columns(2)

    with c1:
        categoria = st.selectbox(
            "Categoría",
            CATEGORIAS_MODELO_AULA,
            key="cfg_modelo_aula_categoria",
        )

    with c2:
        tipo_linea = st.selectbox(
            "Tipo",
            TIPOS_LINEA_MODELO_AULA,
            key="cfg_modelo_aula_tipo",
        )

    elemento = st.text_input(
        "Elemento / comprobación",
        placeholder=(
            "Ejemplo: Purificador de aire, Altavoces, "
            "Comprobar cierre de ventanas..."
        ),
        key="cfg_modelo_aula_elemento",
    )

    es_inventariable = (
        tipo_linea == "Elemento inventariable"
    )

    c3, c4 = st.columns(2)

    with c3:
        pide_cantidad = st.checkbox(
            "Registrar cantidad",
            value=es_inventariable,
            disabled=not es_inventariable,
            key="cfg_modelo_aula_pide_cantidad",
        )

    with c4:
        cantidad_defecto = st.number_input(
            "Cantidad sugerida inicial",
            min_value=0,
            step=1,
            value=0,
            disabled=not es_inventariable,
            key="cfg_modelo_aula_cantidad_defecto",
            help=(
                "Solo sirve como ayuda para el primer censo. "
                "Después manda el inventario vivo de cada espacio."
            ),
        )

    if st.button(
        "➕ Añadir al modelo de aula",
        key="cfg_modelo_aula_crear",
        use_container_width=True,
    ):
        ok, mensaje = crear_modelo_preventivo_aula(
            categoria=categoria,
            elemento=elemento,
            tipo_linea=tipo_linea,
            pide_cantidad=pide_cantidad,
            cantidad_defecto=cantidad_defecto,
        )

        if ok:
            st.success(mensaje)
            st.rerun()
        else:
            st.warning(mensaje)

    st.markdown("---")
    st.markdown("#### 📋 Modelo actual")

    filtro_categoria = st.selectbox(
        "Filtrar categoría",
        ["Todas"] + CATEGORIAS_MODELO_AULA,
        key="cfg_modelo_aula_filtro_categoria",
    )

    buscar = st.text_input(
        "🔎 Buscar",
        placeholder="Ejemplo: aire, silla, diferencial, persiana...",
        key="cfg_modelo_aula_buscar",
    ).strip().lower()

    modelos_filtrados = []

    for fila in modelos:
        (
            id_modelo,
            categoria_actual,
            elemento_actual,
            tipo_actual,
            pide_cantidad_actual,
            cantidad_defecto_actual,
            activo,
            orden,
        ) = fila

        if (
            filtro_categoria != "Todas"
            and categoria_actual != filtro_categoria
        ):
            continue

        if buscar:
            texto = (
                f"{categoria_actual} "
                f"{elemento_actual} "
                f"{tipo_actual}"
            ).lower()

            if buscar not in texto:
                continue

        modelos_filtrados.append(fila)

    if not modelos_filtrados:
        st.info(
            "No hay elementos del modelo con estos filtros."
        )
        return

    st.caption(
        f"{len(modelos_filtrados)} elemento(s) mostrado(s). "
        "Desactivar es preferible a borrar cuando ya se ha usado un elemento."
    )

    for fila in modelos_filtrados:
        (
            id_modelo,
            categoria_actual,
            elemento_actual,
            tipo_actual,
            pide_cantidad_actual,
            cantidad_defecto_actual,
            activo,
            orden,
        ) = fila

        icono_estado = "✅" if activo else "⛔"

        if tipo_actual == "Elemento inventariable":
            icono_tipo = "📦"
            detalle = (
                f"Cantidad sugerida: "
                f"{int(cantidad_defecto_actual or 0)}"
            )
        else:
            icono_tipo = "🔧"
            detalle = "Sin cantidad"

        titulo = (
            f"{icono_estado} {icono_tipo} "
            f"{categoria_actual} · {elemento_actual}"
        )

        with st.expander(
            titulo,
            expanded=False,
        ):
            st.caption(
                f"{tipo_actual} · {detalle}"
            )

            nueva_categoria = st.selectbox(
                "Categoría",
                CATEGORIAS_MODELO_AULA,
                index=(
                    CATEGORIAS_MODELO_AULA.index(
                        categoria_actual
                    )
                    if categoria_actual in CATEGORIAS_MODELO_AULA
                    else len(CATEGORIAS_MODELO_AULA) - 1
                ),
                key=f"cfg_modelo_aula_edit_cat_{id_modelo}",
            )

            nuevo_elemento = st.text_input(
                "Elemento / comprobación",
                value=str(
                    elemento_actual or ""
                ),
                key=f"cfg_modelo_aula_edit_elemento_{id_modelo}",
            )

            nuevo_tipo = st.selectbox(
                "Tipo",
                TIPOS_LINEA_MODELO_AULA,
                index=(
                    TIPOS_LINEA_MODELO_AULA.index(
                        tipo_actual
                    )
                    if tipo_actual in TIPOS_LINEA_MODELO_AULA
                    else 0
                ),
                key=f"cfg_modelo_aula_edit_tipo_{id_modelo}",
            )

            inventariable_editado = (
                nuevo_tipo == "Elemento inventariable"
            )

            ec1, ec2 = st.columns(2)

            with ec1:
                nuevo_pide_cantidad = st.checkbox(
                    "Registrar cantidad",
                    value=bool(
                        pide_cantidad_actual
                    ) if inventariable_editado else False,
                    disabled=not inventariable_editado,
                    key=(
                        f"cfg_modelo_aula_edit_pide_"
                        f"{id_modelo}"
                    ),
                )

            with ec2:
                nueva_cantidad_defecto = st.number_input(
                    "Cantidad sugerida inicial",
                    min_value=0,
                    step=1,
                    value=(
                        int(cantidad_defecto_actual or 0)
                        if inventariable_editado
                        else 0
                    ),
                    disabled=not inventariable_editado,
                    key=(
                        f"cfg_modelo_aula_edit_cantidad_"
                        f"{id_modelo}"
                    ),
                )

            bc1, bc2 = st.columns(2)

            with bc1:
                if st.button(
                    "💾 Guardar cambios",
                    key=(
                        f"cfg_modelo_aula_guardar_"
                        f"{id_modelo}"
                    ),
                    use_container_width=True,
                ):
                    ok, mensaje = actualizar_modelo_preventivo_aula(
                        id_modelo=id_modelo,
                        categoria=nueva_categoria,
                        elemento=nuevo_elemento,
                        tipo_linea=nuevo_tipo,
                        pide_cantidad=nuevo_pide_cantidad,
                        cantidad_defecto=nueva_cantidad_defecto,
                    )

                    if ok:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.warning(mensaje)

            with bc2:
                if activo:
                    texto_estado = "⛔ Desactivar"
                    nuevo_estado = 0
                else:
                    texto_estado = "✅ Activar"
                    nuevo_estado = 1

                if st.button(
                    texto_estado,
                    key=(
                        f"cfg_modelo_aula_estado_"
                        f"{id_modelo}"
                    ),
                    use_container_width=True,
                ):
                    if activar_desactivar_modelo_preventivo_aula(
                        id_modelo,
                        nuevo_estado,
                    ):
                        st.rerun()

            st.markdown("---")

            confirmar_borrado = st.checkbox(
                "Confirmo borrado definitivo",
                key=(
                    f"cfg_modelo_aula_confirmar_borrar_"
                    f"{id_modelo}"
                ),
            )

            if st.button(
                "🗑️ Borrar definitivamente",
                key=(
                    f"cfg_modelo_aula_borrar_"
                    f"{id_modelo}"
                ),
                use_container_width=True,
            ):
                if not confirmar_borrado:
                    st.error(
                        "Marca primero la confirmación."
                    )
                elif borrar_modelo_preventivo_aula(
                    id_modelo
                ):
                    st.warning(
                        "Elemento eliminado del modelo."
                    )
                    st.rerun()
                else:
                    st.error(
                        "No se pudo borrar el elemento."
                    )



def pantalla_modelo_preventivo_aula_por_espacio():
    """
    Personaliza el modelo general para un espacio concreto.

    El catálogo maestro sigue estando en 'Modelo general'.
    Aquí solo se decide qué elementos se aplican a cada espacio.
    """
    asegurar_tabla_modelo_preventivo_aula()
    asegurar_tabla_modelo_preventivo_aula_espacio()

    st.markdown("### 🏫 Modelo específico por aula / espacio")

    st.info(
        "Aquí decides qué elementos del MODELO BASE se proponen para un "
        "espacio concreto. Esto no modifica directamente su inventario vivo. "
        "Para cantidades reales, altas o bajas usa Inventario espacios."
    )

    centro = st.selectbox(
        "Centro",
        list(PLANTAS_BASE.keys()),
        key="cfg_modelo_espacio_centro",
    )

    edificios = list(
        PLANTAS_BASE.get(
            centro,
            {},
        ).keys()
    )

    if not edificios:
        st.warning("No hay edificios configurados para este centro.")
        return

    edificio = st.selectbox(
        "Edificio",
        edificios,
        key="cfg_modelo_espacio_edificio",
    )

    plantas = obtener_plantas_catalogo_config(
        centro,
        edificio,
    )

    if not plantas:
        st.warning("No hay plantas configuradas para este edificio.")
        return

    planta = st.selectbox(
        "Planta",
        plantas,
        key="cfg_modelo_espacio_planta",
    )

    espacios_catalogo = obtener_espacios_catalogo(
        activos=True
    )

    espacios = []

    for (
        id_espacio,
        centro_f,
        edificio_f,
        planta_f,
        espacio_f,
        tipo_f,
        activo_f,
    ) in espacios_catalogo:
        if (
            str(centro_f) == str(centro)
            and str(edificio_f) == str(edificio)
            and str(planta_f) == str(planta)
        ):
            nombre = str(espacio_f or "").strip()

            if nombre and nombre not in espacios:
                espacios.append(nombre)

    if not espacios:
        st.warning("No hay espacios registrados en esta planta.")
        return

    espacio = st.selectbox(
        "Aula / espacio",
        espacios,
        key="cfg_modelo_espacio_espacio",
    )

    modelos = obtener_modelos_preventivo_aula(
        solo_activos=False
    )

    if not modelos:
        st.info("No hay elementos en el modelo general.")
        return

    config_actual = obtener_configuracion_modelo_aula_espacio(
        centro=centro,
        edificio=edificio,
        planta=planta,
        espacio=espacio,
    )

    tiene_config_especifica = bool(
        config_actual
    )

    st.caption(
        f"📍 {centro} · {edificio} · {planta} · {espacio}"
    )

    if not tiene_config_especifica:
        st.info(
            "Este espacio todavía usa directamente el modelo general activo."
        )

        if st.button(
            "📋 Crear configuración específica desde el modelo general",
            key="cfg_modelo_espacio_copiar_general",
            use_container_width=True,
            type="primary",
        ):
            cantidad = copiar_modelo_general_a_espacio(
                centro=centro,
                edificio=edificio,
                planta=planta,
                espacio=espacio,
            )

            if cantidad > 0:
                st.success(
                    f"Configuración creada con {cantidad} elementos."
                )
                st.rerun()
            else:
                st.warning(
                    "No se pudo crear la configuración específica."
                )

        return

    c1, c2, c3 = st.columns(3)

    activos_espacio = sum(
        1
        for (
            modelo_id,
            categoria,
            elemento,
            tipo_linea,
            pide_cantidad,
            cantidad_defecto,
            activo_general,
            orden,
        ) in modelos
        if bool(config_actual.get(
            int(modelo_id),
            int(activo_general or 0),
        ))
    )

    total_inventariables = sum(
        1
        for (
            modelo_id,
            categoria,
            elemento,
            tipo_linea,
            pide_cantidad,
            cantidad_defecto,
            activo_general,
            orden,
        ) in modelos
        if (
            str(tipo_linea) == "Elemento inventariable"
            and bool(config_actual.get(
                int(modelo_id),
                int(activo_general or 0),
            ))
        )
    )

    total_comprobaciones = sum(
        1
        for (
            modelo_id,
            categoria,
            elemento,
            tipo_linea,
            pide_cantidad,
            cantidad_defecto,
            activo_general,
            orden,
        ) in modelos
        if (
            str(tipo_linea) == "Comprobación técnica"
            and bool(config_actual.get(
                int(modelo_id),
                int(activo_general or 0),
            ))
        )
    )

    c1.metric("Activos en este espacio", activos_espacio)
    c2.metric("📦 Inventariables", total_inventariables)
    c3.metric("🔧 Comprobaciones", total_comprobaciones)

    st.markdown("---")

    filtro_categoria = st.selectbox(
        "Filtrar categoría",
        ["Todas"] + CATEGORIAS_MODELO_AULA,
        key="cfg_modelo_espacio_filtro_categoria",
    )

    buscar = st.text_input(
        "🔎 Buscar elemento",
        placeholder="Ejemplo: proyector, pantalla, pizarra, aire...",
        key="cfg_modelo_espacio_buscar",
    ).strip().lower()

    for (
        modelo_id,
        categoria,
        elemento,
        tipo_linea,
        pide_cantidad,
        cantidad_defecto,
        activo_general,
        orden,
    ) in modelos:

        if (
            filtro_categoria != "Todas"
            and categoria != filtro_categoria
        ):
            continue

        if buscar:
            texto = (
                f"{categoria} {elemento} {tipo_linea}"
            ).lower()

            if buscar not in texto:
                continue

        estado_espacio = bool(
            config_actual.get(
                int(modelo_id),
                int(activo_general or 0),
            )
        )

        icono_tipo = (
            "📦"
            if str(tipo_linea) == "Elemento inventariable"
            else "🔧"
        )

        with st.container(border=True):
            col_txt, col_estado = st.columns(
                [4, 1],
                vertical_alignment="center",
            )

            with col_txt:
                st.markdown(
                    f"**{icono_tipo} {elemento}**"
                )
                st.caption(
                    f"{categoria} · {tipo_linea}"
                )

            with col_estado:
                nuevo_estado = st.toggle(
                    "Activo",
                    value=estado_espacio,
                    key=(
                        f"cfg_modelo_espacio_toggle_"
                        f"{centro}_{edificio}_{planta}_{espacio}_{modelo_id}"
                    ),
                )

            if nuevo_estado != estado_espacio:
                if guardar_estado_modelo_aula_espacio(
                    centro=centro,
                    edificio=edificio,
                    planta=planta,
                    espacio=espacio,
                    modelo_id=modelo_id,
                    activo=nuevo_estado,
                ):
                    st.rerun()

    st.markdown("---")

    confirmar_reset = st.checkbox(
        "Confirmo que quiero quitar la personalización de este espacio",
        key="cfg_modelo_espacio_confirmar_reset",
    )

    if st.button(
        "↩️ Volver a usar el modelo general",
        key="cfg_modelo_espacio_reset",
        use_container_width=True,
    ):
        if not confirmar_reset:
            st.warning(
                "Marca primero la confirmación."
            )
        else:
            restablecer_modelo_espacio_a_general(
                centro=centro,
                edificio=edificio,
                planta=planta,
                espacio=espacio,
            )

            st.success(
                "El espacio vuelve a usar el modelo general activo."
            )
            st.rerun()


# =====================================================
# RECLASIFICACIÓN DE ÁREAS DE OT ANTIGUAS
# =====================================================

def mostrar_reclasificacion_areas_ot():
    st.markdown("### 🧠 Reclasificar áreas de OT antiguas")

    st.info(
        "El sistema propone un área para cada orden. "
        "Puedes revisarla, cambiarla o desmarcarla antes de modificar "
        "la base de datos."
    )

    # -------------------------------------------------
    # ANALIZAR
    # -------------------------------------------------

    if st.button(
        "🔎 Analizar OT antiguas",
        key="cfg_analizar_areas_ot",
        use_container_width=True
    ):
        try:
            propuestas = obtener_propuestas_reclasificacion_areas()

            st.session_state["cfg_propuestas_areas_ot"] = propuestas
            st.session_state.pop(
                "cfg_propuestas_finales_areas_ot",
                None
            )
            st.session_state["cfg_confirmar_reclasificacion"] = False

            if propuestas:
                st.success(
                    f"Se han encontrado {len(propuestas)} órdenes "
                    "que pueden reclasificarse."
                )
            else:
                st.success(
                    "No se han encontrado órdenes pendientes "
                    "de reclasificar."
                )

        except Exception as e:
            st.error(
                f"No se pudo realizar el análisis: {e}"
            )

    propuestas = st.session_state.get(
        "cfg_propuestas_areas_ot",
        []
    )

    if not propuestas:
        st.caption(
            "Pulsa el botón de análisis para revisar las órdenes antiguas."
        )
        return

    # -------------------------------------------------
    # MÉTRICAS GENERALES
    # -------------------------------------------------

    ordenes_activas = sum(
        1
        for propuesta in propuestas
        if propuesta.get("tabla") == "ordenes_trabajo"
    )

    ordenes_historicas = sum(
        1
        for propuesta in propuestas
        if propuesta.get("tabla") == "historico_ordenes"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Cambios propuestos",
            len(propuestas)
        )

    with c2:
        st.metric(
            "OT activas",
            ordenes_activas
        )

    with c3:
        st.metric(
            "Histórico",
            ordenes_historicas
        )

    st.markdown("---")

    # -------------------------------------------------
    # FILTROS
    # -------------------------------------------------

    st.markdown("#### 🔍 Filtrar propuestas")

    areas_encontradas = sorted({
        str(propuesta.get("area_propuesta") or "Otros")
        for propuesta in propuestas
    })

    col_filtro1, col_filtro2 = st.columns(2)

    with col_filtro1:
        filtro_area = st.selectbox(
            "Área propuesta",
            ["Todas"] + areas_encontradas,
            key="cfg_filtro_area_reclasificacion"
        )

    with col_filtro2:
        filtro_tipo = st.selectbox(
            "Tipo de orden",
            [
                "Todas",
                "OT activas",
                "Histórico",
            ],
            key="cfg_filtro_tipo_reclasificacion"
        )

    texto_busqueda = st.text_input(
        "Buscar por número o descripción",
        placeholder="Ejemplo: lavabo, puerta, enchufe, OT-0025...",
        key="cfg_buscar_reclasificacion"
    )

    texto_busqueda_normalizado = texto_busqueda.strip().lower()

    propuestas_filtradas = []

    for propuesta in propuestas:
        area_propuesta = str(
            propuesta.get("area_propuesta") or "Otros"
        )

        tabla = propuesta.get("tabla", "")

        numero_ot = str(
            propuesta.get("numero_ot") or ""
        )

        descripcion = str(
            propuesta.get("descripcion") or ""
        )

        if (
            filtro_area != "Todas"
            and area_propuesta != filtro_area
        ):
            continue

        if (
            filtro_tipo == "OT activas"
            and tabla != "ordenes_trabajo"
        ):
            continue

        if (
            filtro_tipo == "Histórico"
            and tabla != "historico_ordenes"
        ):
            continue

        if texto_busqueda_normalizado:
            texto_completo = (
                f"{numero_ot} {descripcion}"
            ).lower()

            if texto_busqueda_normalizado not in texto_completo:
                continue

        propuestas_filtradas.append(propuesta)

    st.caption(
        f"Mostrando {len(propuestas_filtradas)} de "
        f"{len(propuestas)} propuestas."
    )

    # -------------------------------------------------
    # CREAR TABLA EDITABLE
    # -------------------------------------------------

    filas_editor = []

    for propuesta in propuestas_filtradas:
        filas_editor.append({
            "Aplicar": True,
            "ID interno": propuesta.get("id"),
            "Tabla": propuesta.get("tabla"),
            "Nº OT": propuesta.get("numero_ot") or "",
            "Descripción": propuesta.get("descripcion") or "",
            "Origen": propuesta.get("origen") or "",
            "Área actual": propuesta.get("area_actual") or "Otros",
            "Área final": propuesta.get("area_propuesta") or "Otros",
        })

    dataframe_editor = pd.DataFrame(filas_editor)

    if dataframe_editor.empty:
        st.warning(
            "No hay propuestas que coincidan con los filtros."
        )
        return

    st.markdown("#### ✏️ Revisar y corregir")

    st.caption(
        "Desmarca «Aplicar» para excluir una orden. "
        "Puedes cambiar «Área final» mediante el desplegable."
    )

    dataframe_editado = st.data_editor(
        dataframe_editor,
        key="cfg_editor_reclasificacion_areas",
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=[
            "ID interno",
            "Tabla",
            "Nº OT",
            "Descripción",
            "Origen",
            "Área actual",
        ],
        column_config={
            "Aplicar": st.column_config.CheckboxColumn(
                "Aplicar",
                help="Desmarca esta casilla para no actualizar la orden.",
                default=True,
                width="small",
            ),
            "ID interno": st.column_config.NumberColumn(
                "ID interno",
                width="small",
            ),
            "Tabla": st.column_config.TextColumn(
                "Registro",
                width="small",
            ),
            "Nº OT": st.column_config.TextColumn(
                "Nº OT",
                width="medium",
            ),
            "Descripción": st.column_config.TextColumn(
                "Descripción",
                width="large",
            ),
            "Origen": st.column_config.TextColumn(
                "Origen",
                width="small",
            ),
            "Área actual": st.column_config.TextColumn(
                "Área actual",
                width="medium",
            ),
            "Área final": st.column_config.SelectboxColumn(
                "Área final",
                options=AREAS_OT,
                required=True,
                width="medium",
            ),
        }
    )

    # -------------------------------------------------
    # RESUMEN DEL CONTENIDO EDITADO
    # -------------------------------------------------

    seleccionadas = dataframe_editado[
        dataframe_editado["Aplicar"] == True
    ].copy()

    st.markdown("---")
    st.markdown("#### 📊 Resumen definitivo")

    if seleccionadas.empty:
        st.warning(
            "No hay ninguna orden marcada para aplicar."
        )
    else:
        resumen_final = (
            seleccionadas["Área final"]
            .value_counts()
            .to_dict()
        )

        columnas = st.columns(3)

        for indice, (area, cantidad) in enumerate(
            resumen_final.items()
        ):
            with columnas[indice % 3]:
                st.metric(
                    str(area),
                    int(cantidad)
                )

        st.metric(
            "Total seleccionado",
            len(seleccionadas)
        )

    # -------------------------------------------------
    # PREPARAR CAMBIOS
    # -------------------------------------------------

    if not st.session_state.get(
        "cfg_confirmar_reclasificacion",
        False
    ):
        if st.button(
            "✅ Preparar aplicación de cambios",
            key="cfg_preparar_reclasificacion",
            use_container_width=True,
            disabled=seleccionadas.empty
        ):
            propuestas_finales = []

            for _, fila in seleccionadas.iterrows():
                propuestas_finales.append({
                    "tabla": fila["Tabla"],
                    "id": int(fila["ID interno"]),
                    "numero_ot": fila["Nº OT"],
                    "descripcion": fila["Descripción"],
                    "origen": fila["Origen"],
                    "area_actual": fila["Área actual"],
                    "area_propuesta": fila["Área final"],
                })

            st.session_state[
                "cfg_propuestas_finales_areas_ot"
            ] = propuestas_finales

            st.session_state[
                "cfg_confirmar_reclasificacion"
            ] = True

            st.rerun()

        return

    # -------------------------------------------------
    # CONFIRMACIÓN FINAL
    # -------------------------------------------------

    propuestas_finales = st.session_state.get(
        "cfg_propuestas_finales_areas_ot",
        []
    )

    if not propuestas_finales:
        st.warning(
            "No hay propuestas preparadas para aplicar."
        )
        return

    st.warning(
        f"Se van a actualizar hasta "
        f"{len(propuestas_finales)} órdenes."
    )

    confirmar_checkbox = st.checkbox(
        "Confirmo que he revisado las áreas y quiero aplicar los cambios",
        key="cfg_checkbox_confirmar_reclasificacion"
    )

    texto_confirmacion = st.text_input(
        "Para confirmar escribe: RECLASIFICAR",
        key="cfg_texto_confirmar_reclasificacion"
    )

    texto_valido = (
        texto_confirmacion.strip().upper()
        == "RECLASIFICAR"
    )

    col_aplicar, col_cancelar = st.columns(2)

    with col_aplicar:
        if st.button(
            "🧠 Aplicar cambios definitivos",
            key="cfg_aplicar_reclasificacion",
            use_container_width=True
        ):
            if not confirmar_checkbox:
                st.error(
                    "Marca primero la casilla de confirmación."
                )

            elif not texto_valido:
                st.error(
                    "Debes escribir RECLASIFICAR para continuar."
                )

            else:
                try:
                    resultado = aplicar_reclasificacion_areas(
                        propuestas_finales
                    )

                    errores = resultado.get("errores", [])

                    if errores:
                        for error in errores:
                            st.error(error)

                    else:
                        actualizadas = resultado.get(
                            "actualizadas",
                            0
                        )

                        omitidas = resultado.get(
                            "omitidas",
                            0
                        )

                        por_area = resultado.get(
                            "por_area",
                            {}
                        )

                        st.success(
                            f"Reclasificación terminada. "
                            f"Se han actualizado "
                            f"{actualizadas} órdenes."
                        )

                        if omitidas:
                            st.info(
                                f"Se han omitido {omitidas} órdenes "
                                "porque ya habían cambiado o no "
                                "cumplían las condiciones."
                            )

                        if por_area:
                            st.markdown(
                                "#### Resultado aplicado"
                            )

                            for area, cantidad in sorted(
                                por_area.items(),
                                key=lambda elemento: elemento[1],
                                reverse=True
                            ):
                                st.write(
                                    f"✅ **{area}:** {cantidad}"
                                )

                        st.session_state.pop(
                            "cfg_propuestas_areas_ot",
                            None
                        )

                        st.session_state.pop(
                            "cfg_propuestas_finales_areas_ot",
                            None
                        )

                        st.session_state.pop(
                            "cfg_confirmar_reclasificacion",
                            None
                        )

                        st.session_state.pop(
                            "cfg_checkbox_confirmar_reclasificacion",
                            None
                        )

                        st.session_state.pop(
                            "cfg_texto_confirmar_reclasificacion",
                            None
                        )

                        st.session_state.pop(
                            "cfg_editor_reclasificacion_areas",
                            None
                        )

                except Exception as e:
                    st.error(
                        f"No se pudieron aplicar los cambios: {e}"
                    )

    with col_cancelar:
        if st.button(
            "❌ Volver a la revisión",
            key="cfg_cancelar_reclasificacion",
            use_container_width=True
        ):
            st.session_state[
                "cfg_confirmar_reclasificacion"
            ] = False

            st.session_state.pop(
                "cfg_propuestas_finales_areas_ot",
                None
            )

            st.session_state.pop(
                "cfg_checkbox_confirmar_reclasificacion",
                None
            )

            st.session_state.pop(
                "cfg_texto_confirmar_reclasificacion",
                None
            )

            st.rerun()


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

def mostrar_arbol_colegio():
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
                                for item_espacio in espacios:
                                    nombre_espacio = item_espacio.get("espacio", "")
                                    tipo_espacio = item_espacio.get("tipo", "")

                                    icono_tipo = icono_tipo_espacio(tipo_espacio)

                                    estado_espacio = obtener_estado_espacio(
                                        centro=centro,
                                        edificio=edificio,
                                        espacio=nombre_espacio
                                    )

                                    icono_estado = icono_estado_espacio(estado_espacio)

                                    with st.expander(
                                        f"{icono_estado} {icono_tipo} {nombre_espacio}",
                                        expanded=False
                                    ):
                                        from ui.ui_colegio import ficha_espacio_basica

                                        ficha_espacio_basica(
                                            centro=centro,
                                            edificio=edificio,
                                            planta=planta,
                                            espacio=nombre_espacio
                                        )


# =====================================================
# CONFIGURACIÓN ESPACIOS
# =====================================================

ZONAS_ESPECIALES_P22 = [
    "Exterior",
    "Sala técnica / Instalaciones",
]


def obtener_plantas_catalogo_config(centro, edificio):
    """
    Plantas disponibles para Crear/Editar espacios.

    Incluye:
    - plantas base;
    - plantas creadas desde Configuración;
    - zonas especiales de Pearson 22.
    """
    plantas = []

    for planta in PLANTAS_BASE.get(
        centro,
        {},
    ).get(
        edificio,
        [],
    ):
        if planta not in plantas:
            plantas.append(planta)

    for planta in obtener_plantas_config_ubicacion(
        centro,
        edificio,
        solo_visibles=True,
    ):
        if planta not in plantas:
            plantas.append(planta)

    if centro == "Pearson 22":
        for zona in ZONAS_ESPECIALES_P22:
            if zona not in plantas:
                plantas.append(zona)

    return plantas


def pantalla_configuracion_espacios():
    crear_tabla_espacios()

    st.markdown("### 🏫 Catálogo de espacios del colegio")

    seccion_espacios = st.radio(
        "Sección de espacios",
        [
            "➕ Crear",
            "📚 Catálogo",
            "📍 Plantas",
            "🌳 Árbol del colegio",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="cfg_espacios_seccion",
    )

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
        "Exterior",
        "Terrado",
        "Sala técnica / Instalaciones",
        "Almacén",
        "Laboratorio",
        "Gimnasio",
        "Otro",
    ]

    if seccion_espacios == "➕ Crear":
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

        plantas = obtener_plantas_catalogo_config(
            centro,
            edificio,
        )

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

        qr_habilitado = st.checkbox(
            "📱 Habilitar QR para este espacio",
            value=True,
            key="cfg_catalogo_qr_habilitado",
            help=(
                "Los espacios nuevos nacen con QR habilitado. "
                "Desmárcalo solo si este espacio concreto no debe tener formulario QR."
            ),
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
                    tipo=tipo,
                    qr_habilitado=qr_habilitado,
                )

                if ok:
                    st.success("Espacio guardado correctamente.")
                    st.rerun()
                else:
                    st.error("No se pudo guardar el espacio.")

    elif seccion_espacios == "📚 Catálogo":
        st.markdown("#### 📚 Espacios registrados")

        with st.expander(
            "📱 Corregir QR de espacios antiguos",
            expanded=False,
        ):
            st.caption(
                "Úsalo una sola vez para espacios creados antes del nuevo criterio, "
                "por ejemplo Cocina, Despachos, WC o salas."
            )

            confirmar_qr_todos = st.checkbox(
                "Confirmo habilitar QR en todos los espacios activos",
                key="cfg_confirmar_qr_todos_espacios",
            )

            if st.button(
                "📱 Habilitar QR en todos los espacios activos",
                key="cfg_habilitar_qr_todos_espacios",
                use_container_width=True,
            ):
                if not confirmar_qr_todos:
                    st.warning("Marca primero la confirmación.")
                else:
                    ok_qr, afectados_qr = habilitar_qr_todos_espacios_activos()

                    if ok_qr:
                        if afectados_qr > 0:
                            st.success(
                                f"QR habilitado en {afectados_qr} espacios antiguos."
                            )
                        else:
                            st.info(
                                "Todos los espacios activos ya tenían QR habilitado."
                            )
                        st.rerun()
                    else:
                        st.error(
                            "No se pudo actualizar el estado QR de los espacios."
                        )

        espacios = obtener_espacios_catalogo(activos=True)

        if not espacios:
            st.info("Todavía no hay espacios registrados.")
        else:
            for id_espacio, centro, edificio, planta, espacio, tipo, activo in espacios:
                with st.expander(
                    f"🏫 {centro} · {edificio} · {planta} · {espacio} · {tipo}",
                    expanded=False
                ):

                    nuevo_centro = st.selectbox(
                        "Centro",
                        list(PLANTAS_BASE.keys()),
                        index=list(PLANTAS_BASE.keys()).index(centro)
                        if centro in PLANTAS_BASE else 0,
                        key=f"edit_esp_centro_{id_espacio}"
                    )

                    nuevos_edificios = list(PLANTAS_BASE.get(nuevo_centro, {}).keys())

                    nuevo_edificio = st.selectbox(
                        "Edificio",
                        nuevos_edificios,
                        index=nuevos_edificios.index(edificio)
                        if edificio in nuevos_edificios else 0,
                        key=f"edit_esp_edificio_{id_espacio}"
                    )

                    nuevas_plantas = obtener_plantas_catalogo_config(
                        nuevo_centro,
                        nuevo_edificio,
                    )

                    if (
                        planta
                        and planta not in nuevas_plantas
                    ):
                        nuevas_plantas.append(planta)

                    nueva_planta = st.selectbox(
                        "Planta",
                        nuevas_plantas,
                        index=nuevas_plantas.index(planta)
                        if planta in nuevas_plantas else 0,
                        key=f"edit_esp_planta_{id_espacio}"
                    )

                    nuevo_tipo = st.selectbox(
                        "Tipo",
                        tipos_espacio,
                        index=tipos_espacio.index(tipo)
                        if tipo in tipos_espacio else tipos_espacio.index("Otro"),
                        key=f"edit_esp_tipo_{id_espacio}"
                    )

                    nuevo_espacio = st.text_input(
                        "Nombre del espacio",
                        value=str(espacio or ""),
                        key=f"edit_esp_nombre_{id_espacio}"
                    )

                    nuevo_qr_habilitado = st.checkbox(
                        "📱 QR habilitado",
                        value=qr_habilitado_espacio(id_espacio),
                        key=f"edit_esp_qr_{id_espacio}",
                        help=(
                            "Permite generar y utilizar una placa QR "
                            "para este espacio."
                        ),
                    )

                    if st.button(
                        "💾 Guardar cambios",
                        key=f"guardar_cambios_espacio_{id_espacio}",
                        use_container_width=True
                    ):
                        ok = actualizar_espacio(
                            id_espacio=id_espacio,
                            centro=nuevo_centro,
                            edificio=nuevo_edificio,
                            planta=nueva_planta,
                            espacio=nuevo_espacio,
                            tipo=nuevo_tipo,
                            qr_habilitado=nuevo_qr_habilitado,
                        )

                        if ok:
                            st.success("Espacio actualizado correctamente.")
                            st.rerun()
                        else:
                            st.error("No se pudo actualizar el espacio.")

                    st.markdown("---")

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

    elif seccion_espacios == "📍 Plantas":
        st.markdown("#### ➕ Crear nueva planta / zona")

        st.caption(
            "La nueva planta quedará disponible para crear espacios "
            "y para los módulos que utilizan el catálogo central."
        )

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            centro_nueva_planta = st.selectbox(
                "Centro",
                list(PLANTAS_BASE.keys()),
                key="cfg_nueva_planta_centro",
            )

        edificios_nueva_planta = list(
            PLANTAS_BASE.get(
                centro_nueva_planta,
                {},
            ).keys()
        )

        with col_p2:
            edificio_nueva_planta = st.selectbox(
                "Edificio",
                edificios_nueva_planta,
                key="cfg_nueva_planta_edificio",
            )

        nombre_nueva_planta = st.text_input(
            "Nombre de la planta / zona",
            placeholder=(
                "Ejemplo: Planta 6, Sótano, Semisótano, Exterior..."
            ),
            key="cfg_nueva_planta_nombre",
        )

        nueva_planta_visible = st.checkbox(
            "Visible desde el momento de crearla",
            value=True,
            key="cfg_nueva_planta_visible",
        )

        if st.button(
            "💾 Crear planta / zona",
            key="cfg_crear_nueva_planta",
            use_container_width=True,
        ):
            ok, mensaje = crear_planta_configurable(
                centro=centro_nueva_planta,
                edificio=edificio_nueva_planta,
                planta=nombre_nueva_planta,
                visible=1 if nueva_planta_visible else 0,
            )

            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.warning(mensaje)

        st.markdown("---")
        st.markdown("#### 📍 Plantas configuradas")

        plantas = obtener_plantas_config()

        if not plantas:
            st.info("No hay plantas configuradas.")
        else:
            for id_planta, centro, edificio, planta, visible in plantas:
                col1, col2 = st.columns([4, 1])

                with col1:
                    estado = "✅ Visible" if visible else "❌ Oculta"
                    st.markdown(
                        f"**{centro}** · {edificio} · "
                        f"{planta} · {estado}"
                    )

                with col2:
                    if visible:
                        if st.button(
                            "Ocultar",
                            key=f"ocultar_planta_{id_planta}",
                            use_container_width=True
                        ):
                            actualizar_visible_planta(
                                id_planta,
                                0,
                            )
                            st.rerun()
                    else:
                        if st.button(
                            "Mostrar",
                            key=f"mostrar_planta_{id_planta}",
                            use_container_width=True
                        ):
                            actualizar_visible_planta(
                                id_planta,
                                1,
                            )
                            st.rerun()

    elif seccion_espacios == "🌳 Árbol del colegio":
        mostrar_arbol_colegio()




# =====================================================
# USO GERENCIA
# =====================================================

def pantalla_uso_gerencia():
    st.markdown("### 👁️ Uso Gerencia")
    st.caption(
        "Registro interno de entradas reales del perfil Gerencia. "
        "Los rerun de Streamlit y las visitas desde Administración no suman."
    )

    try:
        resumen = obtener_resumen_accesos_gerencia()
    except Exception as e:
        st.error(f"No se pudo consultar el uso de Gerencia: {e}")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Entradas hoy", int(resumen.get("hoy", 0)))
    c2.metric("Entradas este mes", int(resumen.get("mes", 0)))
    c3.metric("Entradas totales", int(resumen.get("total", 0)))

    registros = resumen.get("registros", [])

    if not registros:
        st.info("Todavía no se ha registrado ninguna entrada de Gerencia.")
        return

    st.markdown("#### Últimas entradas")
    st.dataframe(
        pd.DataFrame(registros).head(100),
        use_container_width=True,
        hide_index=True,
    )


# =====================================================
# PANTALLA CONFIGURACIÓN
# =====================================================

def pantalla_configuracion():
    """
    Configuración con carga bajo demanda.

    A diferencia de st.tabs(), solo ejecuta la sección seleccionada.
    Esto evita cargar a la vez Catálogo, Árbol, Legionella, Checklist,
    Inteligencia y Borrados en cada rerun.
    """
    st.subheader("⚙️ Configuración")

    seccion = st.radio(
        "Sección de configuración",
        [
            "🏫 Espacios",
            "💧 Legionella",
            "✅ Checklist preventivo",
            "🧩 Modelo aulas",
            "⚡ Cuadros eléctricos",
            "🧠 Inteligencia",
            "👁️ Uso Gerencia",
            "📊 Gráficos",
            "🧹 Borrados",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="cfg_seccion_principal",
    )

    if seccion == "🏫 Espacios":
        pantalla_configuracion_espacios()
        return

    if seccion == "✅ Checklist preventivo":
        pantalla_checklist_preventivo_config()
        return

    if seccion == "🧩 Modelo aulas":
        pantalla_modelo_preventivo_aula_config()
        return

    if seccion == "⚡ Cuadros eléctricos":
        pantalla_cuadros_electricos()
        return

    if seccion == "🧠 Inteligencia":
        mostrar_reclasificacion_areas_ot()
        return

    if seccion == "👁️ Uso Gerencia":
        pantalla_uso_gerencia()
        return

    if seccion == "📊 Gráficos":
        pantalla_demo_graficos_gerencia()
        return

    if seccion == "🧹 Borrados":
        pantalla_borrados_inicio()
        return

    # =================================================
    # LEGIONELLA
    # =================================================
    st.markdown("### 💧 Configuración Legionella")

    if st.button(
        "🧹 Limpiar puntos inválidos (None)",
        use_container_width=True,
        key="cfg_leg_limpiar_invalidos",
    ):
        afectados = limpiar_puntos_legionella_invalidos()
        st.success(
            f"{afectados} puntos limpiados/desactivados."
        )
        st.rerun()

    seccion_legionella = st.radio(
        "Gestión Legionella",
        [
            "➕ Añadir punto",
            "📋 Puntos existentes",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="cfg_leg_seccion",
    )

    if seccion_legionella == "➕ Añadir punto":
        st.markdown("#### Añadir punto de control")

        centro_leg = st.selectbox(
            "Centro",
            CENTROS,
            key="cfg_leg_centro",
        )

        edificios_leg = obtener_edificios(
            centro_leg
        )

        edificio_leg = st.selectbox(
            "Edificio",
            edificios_leg,
            key="cfg_leg_edificio",
        )

        instalacion = st.selectbox(
            "Instalación",
            INSTALACIONES_LEGIONELLA,
            key="cfg_leg_instalacion",
        )

        if instalacion == "Otro":
            instalacion = st.text_input(
                "Especificar instalación",
                key="cfg_leg_instalacion_otro",
            )

        tipo_punto = st.selectbox(
            "Tipo de punto",
            TIPOS_PUNTO_LEGIONELLA,
            key="cfg_leg_tipo_punto",
        )

        nombre_punto = st.text_input(
            "Nombre del punto",
            placeholder=(
                "Ejemplo: Acumulador ACS 800L, "
                "Retorno ACS, Ducha vestuario..."
            ),
            key="cfg_leg_nombre_punto",
        )

        ubicacion = st.text_input(
            "Ubicación",
            placeholder=(
                "Ejemplo: Cuarto técnico, vestuario, "
                "sala calderas..."
            ),
            key="cfg_leg_ubicacion",
        )

        observaciones = st.text_area(
            "Observaciones",
            key="cfg_leg_observaciones",
        )

        if st.button(
            "➕ Crear punto Legionella",
            use_container_width=True,
            key="cfg_leg_crear_punto",
        ):
            ok, mensaje = crear_punto_legionella(
                centro=centro_leg,
                edificio=edificio_leg,
                instalacion=instalacion,
                tipo_punto=tipo_punto,
                nombre_punto=nombre_punto,
                ubicacion=ubicacion,
                observaciones=observaciones,
            )

            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.warning(mensaje)

        return

    # =================================================
    # PUNTOS EXISTENTES
    # =================================================
    st.markdown("#### Puntos de control existentes")

    puntos = obtener_puntos_legionella()

    if not puntos:
        st.info(
            "No hay puntos de Legionella creados."
        )
        return

    for (
        id_punto,
        centro,
        edificio,
        instalacion,
        tipo_punto,
        nombre_punto,
        ubicacion,
        activo,
        observaciones,
    ) in puntos:

        icono = "✅" if activo else "⛔"

        titulo = (
            f"{icono} {centro} · {edificio} · "
            f"{nombre_punto}"
        )

        with st.expander(
            titulo,
            expanded=False,
        ):
            st.markdown(
                f"**Centro:** {centro}"
            )
            st.markdown(
                f"**Edificio:** {edificio}"
            )
            st.markdown(
                f"**Instalación:** {instalacion}"
            )
            st.markdown(
                f"**Tipo punto:** {tipo_punto}"
            )
            st.markdown(
                f"**Nombre:** {nombre_punto}"
            )
            st.markdown(
                f"**Ubicación:** {ubicacion or '-'}"
            )
            st.markdown(
                f"**Estado:** "
                f"{'Activo' if activo else 'Desactivado'}"
            )

            if observaciones:
                st.info(
                    observaciones
                )

            if activo:
                texto_boton = (
                    f"⛔ Desactivar punto {id_punto}"
                )
                nuevo_estado = 0
            else:
                texto_boton = (
                    f"✅ Activar punto {id_punto}"
                )
                nuevo_estado = 1

            if st.button(
                texto_boton,
                key=f"estado_leg_{id_punto}",
                use_container_width=True,
            ):
                activar_desactivar_punto_legionella(
                    id_punto,
                    nuevo_estado,
                )
                st.rerun()




        
