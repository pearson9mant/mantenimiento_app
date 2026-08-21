import streamlit as st
import pandas as pd
from datetime import date

from database.db import conectar, _sql
from ui.ui_historico_general import pantalla_historico_general


def _leer_df(sql, params=None):
    conn = conectar()

    try:
        if params:
            return pd.read_sql_query(sql, conn, params=params)
        return pd.read_sql_query(sql, conn)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()



def _rol_actual():
    return str(
        st.session_state.get("rol")
        or st.session_state.get("tipo_usuario")
        or st.session_state.get("perfil")
        or ""
    ).strip().lower()


def _puede_borrar_historicos():
    return _rol_actual() in [
        "admin", "administrador", "administracion", "administración"
    ]


def _borrar_ids_tabla(tabla, ids):
    tablas_permitidas = {
        "historico_ordenes",
        "legionella_registros",
        "legionella_informes",
    }

    if tabla not in tablas_permitidas:
        return False, 0, "Tabla no permitida."

    ids = [int(v) for v in ids if str(v).strip()]

    if not ids:
        return False, 0, "No hay registros seleccionados."

    conn = conectar()
    cur = conn.cursor()

    try:
        borrados = 0

        for id_registro in ids:
            cur.execute(
                _sql(f"DELETE FROM {tabla} WHERE id = ?"),
                (id_registro,),
            )
            borrados += max(int(cur.rowcount or 0), 0)

        conn.commit()
        st.cache_data.clear()
        return True, borrados, ""

    except Exception as e:
        conn.rollback()
        return False, 0, str(e)

    finally:
        conn.close()


def _borrar_historico_ot_ids(ids, limpiar_preventivo=False):
    """
    Borra históricos seleccionados.

    Si limpiar_preventivo=True borra además SOLO datos de ejecución
    ligados a esa OT preventiva. No toca preventivo_tareas ni planificación.
    """
    ids = [int(v) for v in ids if str(v).strip()]

    if not ids:
        return False, 0, "No hay registros seleccionados."

    conn = conectar()
    cur = conn.cursor()

    try:
        borrados = 0

        for id_registro in ids:
            cur.execute(
                _sql("""
                    SELECT numero_ot
                    FROM historico_ordenes
                    WHERE id = ?
                """),
                (id_registro,),
            )

            fila = cur.fetchone()
            numero_ot = str(fila[0] or "").strip() if fila else ""

            if numero_ot:
                try:
                    cur.execute(
                        _sql("DELETE FROM ordenes_fotos WHERE numero_ot = ?"),
                        (numero_ot,),
                    )
                except Exception:
                    pass

                if limpiar_preventivo:
                    for tabla in ["preventivo_checklist", "preventivo_registros"]:
                        try:
                            cur.execute(
                                _sql(f"DELETE FROM {tabla} WHERE numero_ot = ?"),
                                (numero_ot,),
                            )
                        except Exception:
                            pass

            cur.execute(
                _sql("DELETE FROM historico_ordenes WHERE id = ?"),
                (id_registro,),
            )
            borrados += max(int(cur.rowcount or 0), 0)

        conn.commit()
        st.cache_data.clear()
        return True, borrados, ""

    except Exception as e:
        conn.rollback()
        return False, 0, str(e)

    finally:
        conn.close()


def _editor_seleccion_borrado(df, columnas_mostrar, key, etiqueta="registros"):
    if df.empty:
        return []

    # Reset de índice para que la selección coincida exactamente con la fila.
    base = df.reset_index(drop=True).copy()
    base.insert(0, "Seleccionar", False)

    columnas = ["Seleccionar"] + [
        c for c in columnas_mostrar
        if c in base.columns
    ]

    editado = st.data_editor(
        base[columnas],
        use_container_width=True,
        hide_index=True,
        disabled=[c for c in columnas if c != "Seleccionar"],
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn(
                "✓",
                help=f"Marca los {etiqueta} que quieras borrar.",
                default=False,
            )
        },
        key=key,
    )

    marcados = editado[editado["Seleccionar"] == True]

    ids = []
    for i in marcados.index.tolist():
        try:
            ids.append(int(base.loc[i, "id"]))
        except Exception:
            pass

    return ids


def _panel_confirmacion_borrado(ids, key, accion_borrado, texto_objeto="registros"):
    if not _puede_borrar_historicos():
        return

    cantidad = len(ids)

    if cantidad == 0:
        st.caption("Marca una o varias casillas para habilitar el borrado.")
        return

    st.warning(f"Has seleccionado **{cantidad} {texto_objeto}** para borrar.")

    confirmar = st.checkbox(
        f"Confirmo el borrado definitivo de {cantidad} {texto_objeto}",
        key=f"{key}_confirmar",
    )

    if st.button(
        f"🗑️ Borrar seleccionados ({cantidad})",
        key=f"{key}_boton",
        use_container_width=True,
        type="primary",
    ):
        if not confirmar:
            st.error("Marca primero la casilla de confirmación.")
            return

        ok, borrados, error = accion_borrado(ids)

        if ok:
            st.success(f"Se han eliminado {borrados} {texto_objeto}.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"No se pudo completar el borrado: {error}")


def _es_incidencia_historica(df):
    if df.empty:
        return pd.Series(False, index=df.index)

    numero = df["numero_ot"].fillna("").astype(str).str.upper()
    origen = df["origen"].fillna("").astype(str).str.upper()
    descripcion = df["descripcion"].fillna("").astype(str).str.upper()

    es_inc = (
        numero.str.startswith("INC-")
        | origen.isin(["APP", "QR", "PROFESORES", "OUTLOOK", "INCIDENCIA"])
    )

    excluida = (
        numero.str.startswith("PREV-")
        | numero.str.startswith("LEG-")
        | origen.isin(["PREVENTIVO", "LEGIONELLA", "VERANO"])
        | descripcion.str.startswith("[PREVENTIVO]")
    )

    return es_inc & (~excluida)


def _historico_incidencias():
    st.markdown("### 📱 Histórico de Incidencias")

    df = _leer_df("""
        SELECT
            id, numero_ot, descripcion, fecha_creacion, fecha_cierre,
            centro, edificio, espacio, area, prioridad, operario,
            origen, solicitante, observaciones_cierre
        FROM historico_ordenes
        ORDER BY fecha_cierre DESC, id DESC
    """)

    if df.empty:
        st.info("No hay incidencias finalizadas.")
        return

    df = df[_es_incidencia_historica(df)].copy()

    if df.empty:
        st.info("No hay incidencias finalizadas.")
        return

    df = _filtros_comunes(df, "hist_inc", "fecha_cierre")

    buscar = st.text_input(
        "Buscar incidencia",
        placeholder="OT, aula, descripción, área...",
        key="hist_inc_buscar",
    ).strip().lower()

    if buscar:
        texto = (
            df["numero_ot"].fillna("").astype(str) + " "
            + df["descripcion"].fillna("").astype(str) + " "
            + df["espacio"].fillna("").astype(str) + " "
            + df["edificio"].fillna("").astype(str) + " "
            + df["area"].fillna("").astype(str)
        ).str.lower()
        df = df[texto.str.contains(buscar, regex=False)]

    st.caption(f"Incidencias encontradas: {len(df)}")

    if df.empty:
        st.info("No hay resultados con estos filtros.")
        return

    columnas = [
        "fecha_cierre", "numero_ot", "centro", "edificio",
        "espacio", "area", "prioridad", "operario", "descripcion",
    ]

    if _puede_borrar_historicos():
        ids = _editor_seleccion_borrado(
            df, columnas, "editor_borrar_hist_inc", "incidencias"
        )
        _panel_confirmacion_borrado(
            ids,
            "borrar_hist_inc",
            lambda valores: _borrar_historico_ot_ids(valores, False),
            "incidencia(s)",
        )
    else:
        st.dataframe(df[columnas], use_container_width=True, hide_index=True)


def _fecha_segura(serie):
    return pd.to_datetime(serie, errors="coerce")


def _filtros_comunes(df, prefijo, columna_fecha="fecha_cierre"):
    if df.empty:
        return df

    filtrado = df.copy()

    if columna_fecha in filtrado.columns:
        filtrado["_fecha_filtro"] = _fecha_segura(
            filtrado[columna_fecha]
        )

        fechas_validas = filtrado["_fecha_filtro"].dropna()

        if not fechas_validas.empty:
            fecha_min = fechas_validas.min().date()
            fecha_max = fechas_validas.max().date()
        else:
            fecha_min = date.today()
            fecha_max = date.today()
    else:
        fecha_min = date.today()
        fecha_max = date.today()

    c1, c2, c3 = st.columns(3)

    with c1:
        desde = st.date_input(
            "Desde",
            value=fecha_min,
            key=f"{prefijo}_desde"
        )

    with c2:
        hasta = st.date_input(
            "Hasta",
            value=fecha_max,
            key=f"{prefijo}_hasta"
        )

    with c3:
        centros = ["Todos"]

        if "centro" in filtrado.columns:
            centros += sorted(
                filtrado["centro"]
                .dropna()
                .astype(str)
                .str.strip()
                .loc[lambda s: s != ""]
                .unique()
                .tolist()
            )

        centro = st.selectbox(
            "Centro",
            centros,
            key=f"{prefijo}_centro"
        )

    if columna_fecha in filtrado.columns:
        filtrado = filtrado[
            filtrado["_fecha_filtro"].notna()
            & (filtrado["_fecha_filtro"].dt.date >= desde)
            & (filtrado["_fecha_filtro"].dt.date <= hasta)
        ]

    if centro != "Todos" and "centro" in filtrado.columns:
        filtrado = filtrado[
            filtrado["centro"].astype(str) == centro
        ]

    return filtrado



def _historico_ot():
    st.markdown("### 🛠️ Histórico de OT")

    df = _leer_df("""
        SELECT
            id, numero_ot, descripcion, fecha_creacion, fecha_cierre,
            centro, edificio, espacio, area, prioridad, operario, origen,
            solicitante, observaciones_cierre
        FROM historico_ordenes
        ORDER BY fecha_cierre DESC, id DESC
    """)

    if df.empty:
        st.info("No hay órdenes finalizadas en el histórico.")
        return

    df = _filtros_comunes(df, "hist_ot", "fecha_cierre")

    c1, c2, c3 = st.columns(3)

    with c1:
        operarios = ["Todos"] + sorted(
            df["operario"].dropna().astype(str).str.strip()
            .loc[lambda s: s != ""].unique().tolist()
        )
        operario = st.selectbox("Operario", operarios, key="hist_ot_operario")

    with c2:
        areas = ["Todas"] + sorted(
            df["area"].dropna().astype(str).str.strip()
            .loc[lambda s: s != ""].unique().tolist()
        )
        area = st.selectbox("Área", areas, key="hist_ot_area")

    with c3:
        buscar = st.text_input(
            "Buscar",
            placeholder="OT, tarea, espacio, descripción...",
            key="hist_ot_buscar",
        ).strip().lower()

    if operario != "Todos":
        df = df[df["operario"].astype(str) == operario]

    if area != "Todas":
        df = df[df["area"].astype(str) == area]

    if buscar:
        texto = (
            df["numero_ot"].fillna("").astype(str) + " "
            + df["descripcion"].fillna("").astype(str) + " "
            + df["espacio"].fillna("").astype(str) + " "
            + df["edificio"].fillna("").astype(str) + " "
            + df["origen"].fillna("").astype(str)
        ).str.lower()
        df = df[texto.str.contains(buscar, regex=False)]

    st.caption(f"Resultados: {len(df)}")

    if df.empty:
        st.info("No hay resultados con estos filtros.")
        return

    columnas = [
        "fecha_cierre", "numero_ot", "centro", "edificio",
        "espacio", "area", "operario", "origen", "descripcion",
    ]

    if _puede_borrar_historicos():
        ids = _editor_seleccion_borrado(
            df, columnas, "editor_borrar_hist_ot", "OT"
        )
        _panel_confirmacion_borrado(
            ids,
            "borrar_hist_ot",
            lambda valores: _borrar_historico_ot_ids(valores, False),
            "OT",
        )
    else:
        st.dataframe(df[columnas], use_container_width=True, hide_index=True)


def _historico_legionella():
    st.markdown("### 💧 Histórico de Legionella")

    df = _leer_df("""
        SELECT
            id, fecha, centro, edificio, instalacion, punto, tarea,
            tipo_control, valor, valor_2, valor_3, unidad, estado,
            resultado, operario, observaciones
        FROM legionella_registros
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY fecha DESC, id DESC
    """)

    if df.empty:
        st.info("No hay controles de Legionella registrados.")
        return

    df = _filtros_comunes(df, "hist_leg", "fecha")

    c1, c2 = st.columns(2)
    with c1:
        estados = ["Todos"] + sorted(
            df["estado"].dropna().astype(str).str.strip()
            .loc[lambda s: s != ""].unique().tolist()
        )
        estado = st.selectbox("Estado", estados, key="hist_leg_estado")

    with c2:
        buscar = st.text_input(
            "Buscar punto o control",
            key="hist_leg_buscar",
        ).strip().lower()

    if estado != "Todos":
        df = df[df["estado"].astype(str) == estado]

    if buscar:
        texto = (
            df["punto"].fillna("").astype(str) + " "
            + df["tarea"].fillna("").astype(str) + " "
            + df["edificio"].fillna("").astype(str) + " "
            + df["resultado"].fillna("").astype(str)
        ).str.lower()
        df = df[texto.str.contains(buscar, regex=False)]

    st.caption(f"Controles encontrados: {len(df)}")

    columnas = [
        "fecha", "centro", "edificio", "punto", "tarea",
        "valor", "valor_2", "valor_3", "unidad",
        "estado", "resultado", "operario",
    ]

    if _puede_borrar_historicos():
        st.warning(
            "El borrado elimina únicamente el control registrado. "
            "No modifica puntos ni planificación de Legionella."
        )
        ids = _editor_seleccion_borrado(
            df, columnas, "editor_borrar_hist_leg", "controles"
        )
        _panel_confirmacion_borrado(
            ids,
            "borrar_hist_leg",
            lambda valores: _borrar_ids_tabla("legionella_registros", valores),
            "control(es)",
        )
    else:
        st.dataframe(df[columnas], use_container_width=True, hide_index=True)


def _historico_preventivos():
    st.markdown("### 🔧 Histórico de Preventivos")

    df = _leer_df("""
        SELECT
            h.id, h.numero_ot, h.descripcion, h.fecha_creacion, h.fecha_cierre,
            h.centro, h.edificio, COALESCE(pr.planta, '') AS planta,
            h.espacio, h.area, h.operario, h.observaciones_cierre,
            COALESCE(pr.tarea, '') AS tarea,
            COALESCE(pr.frecuencia, '') AS frecuencia
        FROM historico_ordenes h
        LEFT JOIN preventivo_registros pr
            ON pr.numero_ot = h.numero_ot
        WHERE UPPER(COALESCE(h.origen, '')) = 'PREVENTIVO'
           OR UPPER(COALESCE(h.descripcion, '')) LIKE '[PREVENTIVO]%'
        ORDER BY h.fecha_cierre DESC, h.id DESC
    """)

    if df.empty:
        st.info("No hay preventivos finalizados.")
        return

    df = _filtros_comunes(df, "hist_prev", "fecha_cierre")

    buscar = st.text_input(
        "Buscar preventivo",
        placeholder="Tarea, OT, planta o espacio...",
        key="hist_prev_buscar_global",
    ).strip().lower()

    if buscar:
        texto = (
            df["numero_ot"].fillna("").astype(str) + " "
            + df["tarea"].fillna("").astype(str) + " "
            + df["descripcion"].fillna("").astype(str) + " "
            + df["planta"].fillna("").astype(str) + " "
            + df["espacio"].fillna("").astype(str)
        ).str.lower()
        df = df[texto.str.contains(buscar, regex=False)]

    st.caption(f"Preventivos encontrados: {len(df)}")

    columnas = [
        "fecha_cierre", "numero_ot", "centro", "edificio",
        "planta", "espacio", "area", "tarea", "frecuencia", "operario",
    ]

    if _puede_borrar_historicos():
        st.warning(
            "Se borra la ejecución histórica y su checklist, "
            "pero NO la tarea preventiva ni su planificación."
        )
        ids = _editor_seleccion_borrado(
            df, columnas, "editor_borrar_hist_prev", "preventivos"
        )
        _panel_confirmacion_borrado(
            ids,
            "borrar_hist_prev",
            lambda valores: _borrar_historico_ot_ids(valores, True),
            "preventivo(s)",
        )
    else:
        st.dataframe(df[columnas], use_container_width=True, hide_index=True)


def _historico_informes_externos():
    st.markdown("### 📁 Informes externos de Legionella")

    df = _leer_df("""
        SELECT
            id, tipo_informe, empresa, centro, edificio, instalacion,
            punto, fecha_actuacion, fecha_informe, resultado,
            numero_informe, proxima_fecha, observaciones, pdf_nombre
        FROM legionella_informes
        ORDER BY fecha_actuacion DESC, id DESC
    """)

    if df.empty:
        st.info("No hay informes externos registrados.")
        return

    df = _filtros_comunes(df, "hist_inf_leg", "fecha_actuacion")
    st.caption(f"Informes encontrados: {len(df)}")

    columnas = [
        "fecha_actuacion", "tipo_informe", "empresa", "centro",
        "edificio", "instalacion", "punto", "resultado",
        "numero_informe", "proxima_fecha",
    ]

    if _puede_borrar_historicos():
        ids = _editor_seleccion_borrado(
            df, columnas, "editor_borrar_hist_inf", "informes"
        )
        _panel_confirmacion_borrado(
            ids,
            "borrar_hist_inf",
            lambda valores: _borrar_ids_tabla("legionella_informes", valores),
            "informe(s)",
        )
    else:
        st.dataframe(df[columnas], use_container_width=True, hide_index=True)


def pantalla_historicos():
    st.subheader("📚 Históricos")

    st.caption(
        "Archivo central de mantenimiento. "
        "Consulta y limpieza selectiva de registros históricos."
    )

    if _puede_borrar_historicos():
        st.info(
            "Administración: marca las casillas de los registros que quieras "
            "eliminar y confirma el borrado. Puedes seleccionar varios a la vez."
        )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "🌍 General",
            "📱 Incidencias",
            "🛠️ OT",
            "💧 Legionella",
            "🔧 Preventivos",
            "📁 Informes externos",
        ]
    )

    with tab1:
        pantalla_historico_general()
        st.caption(
            "El Histórico General es solo lectura. "
            "Para borrar, utiliza la pestaña de origen correspondiente."
        )

    with tab2:
        _historico_incidencias()

    with tab3:
        _historico_ot()

    with tab4:
        _historico_legionella()

    with tab5:
        _historico_preventivos()

    with tab6:
        _historico_informes_externos()

