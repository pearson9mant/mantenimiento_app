import pandas as pd
import streamlit as st

from database.db import conectar, _sql


COLUMNAS_EVENTO = [
    "fecha", "tipo", "icono", "centro", "edificio", "planta", "espacio",
    "actuacion", "operario", "resultado", "numero_ot", "origen",
    "detalle", "fuente", "id_fuente",
]


def _leer_df_seguro(sql, params=()):
    conn = conectar()
    try:
        return pd.read_sql_query(_sql(sql), conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def _texto(valor):
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except Exception:
        pass
    return str(valor).strip()


def _evento_base(**kwargs):
    evento = {col: "" for col in COLUMNAS_EVENTO}
    evento.update(kwargs)
    return evento


def _clasificar_ot(numero_ot, origen, area, descripcion, tipo_orden=""):
    numero = _texto(numero_ot).upper()
    origen_txt = _texto(origen).upper()
    area_txt = _texto(area).lower()
    tipo_orden_txt = _texto(tipo_orden).lower()

    if numero.startswith("PREV-") or (origen_txt == "PREVENTIVO" and not numero.startswith("INC-")):
        return "Preventivo", "📅"
    if numero.startswith("LEG-") or origen_txt == "LEGIONELLA" or area_txt == "legionella":
        return "OT Legionella", "💧"
    if tipo_orden_txt == "externa" or origen_txt in ["EXTERNA", "EXT", "EMPRESA"]:
        return "Empresa externa", "🏢"
    if origen_txt == "VERANO":
        return "Plan verano", "☀️"
    if numero.startswith("INC-"):
        return "Correctivo / incidencia", "🛠️"
    if origen_txt in ["APP", "OUTLOOK", "PROFESORES", "QR"]:
        return "Incidencia", "📱"
    return "Orden de trabajo", "🛠️"


def _eventos_ordenes_finalizadas():
    df = _leer_df_seguro("""
        SELECT id, numero_ot, descripcion, fecha_creacion, fecha_cierre,
               centro, edificio, COALESCE(planta, '') AS planta, espacio,
               area, prioridad, operario, origen,
               COALESCE(tipo_orden, '') AS tipo_orden,
               COALESCE(observaciones_cierre, '') AS observaciones_cierre,
               COALESCE(observaciones_estado, '') AS observaciones_estado
        FROM historico_ordenes
        ORDER BY fecha_cierre DESC, id DESC
    """)

    eventos = []
    for _, row in df.iterrows():
        tipo, icono = _clasificar_ot(
            row.get("numero_ot"), row.get("origen"), row.get("area"),
            row.get("descripcion"), row.get("tipo_orden")
        )
        fecha = row.get("fecha_cierre") if _texto(row.get("fecha_cierre")) else row.get("fecha_creacion")
        detalle = []
        if _texto(row.get("descripcion")):
            detalle.append(_texto(row.get("descripcion")))
        if _texto(row.get("observaciones_cierre")):
            detalle.append("Cierre: " + _texto(row.get("observaciones_cierre")))
        if _texto(row.get("observaciones_estado")):
            detalle.append("Estado: " + _texto(row.get("observaciones_estado")))

        eventos.append(_evento_base(
            fecha=fecha,
            tipo=tipo,
            icono=icono,
            centro=_texto(row.get("centro")),
            edificio=_texto(row.get("edificio")),
            planta=_texto(row.get("planta")),
            espacio=_texto(row.get("espacio")),
            actuacion=_texto(row.get("descripcion")) or _texto(row.get("numero_ot")),
            operario=_texto(row.get("operario")),
            resultado="Finalizada",
            numero_ot=_texto(row.get("numero_ot")),
            origen=_texto(row.get("origen")),
            detalle="\n".join(detalle),
            fuente="historico_ordenes",
            id_fuente=_texto(row.get("id")),
        ))
    return eventos


def _eventos_legionella():
    df = _leer_df_seguro("""
        SELECT id, fecha, centro, edificio, COALESCE(planta, '') AS planta,
               punto, tarea, tipo_control, estado, resultado, operario,
               observaciones, unidad, valor, valor_2, valor_3, valor_4
        FROM legionella_registros
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY fecha DESC, id DESC
    """)

    eventos = []
    for _, row in df.iterrows():
        detalle = []
        if _texto(row.get("resultado")):
            detalle.append(_texto(row.get("resultado")))
        valores = []
        for nombre, col in [("Valor", "valor"), ("Valor 2", "valor_2"), ("Valor 3", "valor_3"), ("Valor 4", "valor_4")]:
            if _texto(row.get(col)):
                valores.append(f"{nombre}: {_texto(row.get(col))}")
        if valores:
            if _texto(row.get("unidad")):
                valores.append("Unidad: " + _texto(row.get("unidad")))
            detalle.append(" · ".join(valores))
        if _texto(row.get("observaciones")):
            detalle.append(_texto(row.get("observaciones")))

        eventos.append(_evento_base(
            fecha=row.get("fecha"),
            tipo="Control Legionella",
            icono="💧",
            centro=_texto(row.get("centro")),
            edificio=_texto(row.get("edificio")),
            planta=_texto(row.get("planta")),
            espacio=_texto(row.get("punto")),
            actuacion=_texto(row.get("tarea")),
            operario=_texto(row.get("operario")),
            resultado=_texto(row.get("estado")) or _texto(row.get("resultado")),
            numero_ot="",
            origen="LEGIONELLA",
            detalle="\n".join(detalle),
            fuente="legionella_registros",
            id_fuente=_texto(row.get("id")),
        ))
    return eventos


def _eventos_inventario():
    df = _leer_df_seguro("""
        SELECT id, codigo_material, material, tipo_movimiento, cantidad,
               motivo, numero_ot, operario, fecha_movimiento
        FROM movimientos_inventario
        ORDER BY fecha_movimiento DESC, id DESC
    """)

    eventos = []
    for _, row in df.iterrows():
        material = _texto(row.get("material")) or _texto(row.get("codigo_material"))
        tipo_mov = _texto(row.get("tipo_movimiento"))
        detalle = []
        if _texto(row.get("cantidad")):
            detalle.append("Cantidad: " + _texto(row.get("cantidad")))
        if _texto(row.get("motivo")):
            detalle.append("Motivo: " + _texto(row.get("motivo")))
        if _texto(row.get("numero_ot")):
            detalle.append("OT: " + _texto(row.get("numero_ot")))

        eventos.append(_evento_base(
            fecha=row.get("fecha_movimiento"),
            tipo="Inventario",
            icono="📦",
            actuacion=f"{tipo_mov} · {material}".strip(" ·"),
            operario=_texto(row.get("operario")),
            resultado=tipo_mov,
            numero_ot=_texto(row.get("numero_ot")),
            origen="INVENTARIO",
            detalle=" · ".join(detalle),
            fuente="movimientos_inventario",
            id_fuente=_texto(row.get("id")),
        ))
    return eventos


def _eventos_informes_legionella():
    df = _leer_df_seguro("""
        SELECT id, tipo_informe, empresa, centro, edificio, instalacion,
               punto, fecha_actuacion, fecha_informe, resultado,
               numero_informe, observaciones
        FROM legionella_informes
        ORDER BY fecha_informe DESC, id DESC
    """)

    eventos = []
    for _, row in df.iterrows():
        fecha = row.get("fecha_informe") if _texto(row.get("fecha_informe")) else row.get("fecha_actuacion")
        detalle = []
        if _texto(row.get("empresa")):
            detalle.append("Empresa: " + _texto(row.get("empresa")))
        if _texto(row.get("numero_informe")):
            detalle.append("Informe: " + _texto(row.get("numero_informe")))
        if _texto(row.get("observaciones")):
            detalle.append(_texto(row.get("observaciones")))

        eventos.append(_evento_base(
            fecha=fecha,
            tipo="Informe Legionella",
            icono="📄",
            centro=_texto(row.get("centro")),
            edificio=_texto(row.get("edificio")),
            espacio=_texto(row.get("punto")),
            actuacion=_texto(row.get("tipo_informe")),
            operario=_texto(row.get("empresa")),
            resultado=_texto(row.get("resultado")),
            origen="LEGIONELLA",
            detalle=" · ".join(detalle),
            fuente="legionella_informes",
            id_fuente=_texto(row.get("id")),
        ))
    return eventos


@st.cache_data(ttl=30, show_spinner=False)
def obtener_historico_general():
    eventos = []
    eventos.extend(_eventos_ordenes_finalizadas())
    eventos.extend(_eventos_legionella())
    eventos.extend(_eventos_inventario())
    eventos.extend(_eventos_informes_legionella())

    if not eventos:
        return pd.DataFrame(columns=COLUMNAS_EVENTO + ["fecha_dt"])

    df = pd.DataFrame(eventos)
    for col in COLUMNAS_EVENTO:
        if col not in df.columns:
            df[col] = ""

    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df.sort_values(
        ["fecha_dt", "tipo"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)


def _opciones_no_vacias(df, columna):
    if df.empty or columna not in df.columns:
        return []
    return sorted({_texto(v) for v in df[columna].tolist() if _texto(v)})


def _formatear_fecha(valor):
    fecha = pd.to_datetime(valor, errors="coerce")
    if pd.isna(fecha):
        return _texto(valor)
    if fecha.hour == 0 and fecha.minute == 0 and fecha.second == 0:
        return fecha.strftime("%d/%m/%Y")
    return fecha.strftime("%d/%m/%Y %H:%M")


def _ubicacion_evento(row):
    return " · ".join(
        p for p in [
            _texto(row.get("centro")),
            _texto(row.get("edificio")),
            _texto(row.get("planta")),
            _texto(row.get("espacio")),
        ] if p
    )


def pantalla_historico_general():
    st.markdown("## 📚 Histórico General")

    st.info(
        "Vista cronológica de toda la actividad registrada. "
        "Es de solo lectura: cada dato permanece en su módulo original."
    )

    df = obtener_historico_general()

    if df.empty:
        st.info("Todavía no hay actividad histórica para mostrar.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Registros", len(df))
    c2.metric("🛠️ OT finalizadas", len(df[df["fuente"] == "historico_ordenes"]))
    c3.metric("💧 Controles Legionella", len(df[df["tipo"] == "Control Legionella"]))
    c4.metric("📦 Movimientos material", len(df[df["tipo"] == "Inventario"]))

    st.markdown("### 🔎 Buscar y filtrar")

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        tipo_f = st.selectbox("Tipo", ["Todos"] + _opciones_no_vacias(df, "tipo"), key="hist_general_tipo")
    with f2:
        centro_f = st.selectbox("Centro", ["Todos"] + _opciones_no_vacias(df, "centro"), key="hist_general_centro")
    with f3:
        operario_f = st.selectbox("Operario / empresa", ["Todos"] + _opciones_no_vacias(df, "operario"), key="hist_general_operario")
    with f4:
        origen_f = st.selectbox("Origen", ["Todos"] + _opciones_no_vacias(df, "origen"), key="hist_general_origen")

    buscar = st.text_input(
        "Buscar",
        placeholder="OT, aula, acumulador, purga, material, operario...",
        key="hist_general_buscar",
    ).strip().lower()

    df_f = df.copy()

    if tipo_f != "Todos":
        df_f = df_f[df_f["tipo"] == tipo_f]
    if centro_f != "Todos":
        df_f = df_f[df_f["centro"] == centro_f]
    if operario_f != "Todos":
        df_f = df_f[df_f["operario"] == operario_f]
    if origen_f != "Todos":
        df_f = df_f[df_f["origen"] == origen_f]

    if buscar:
        cols = [
            "tipo", "centro", "edificio", "planta", "espacio",
            "actuacion", "operario", "resultado", "numero_ot",
            "origen", "detalle",
        ]
        texto = df_f[cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
        df_f = df_f[texto.str.contains(buscar, regex=False)]

    st.caption(f"Registros encontrados: {len(df_f)} de {len(df)}")

    if df_f.empty:
        st.info("No hay resultados con estos filtros.")
        return

    vista = df_f.copy()
    vista["Fecha"] = vista["fecha"].apply(_formatear_fecha)
    vista["Tipo"] = (vista["icono"].fillna("") + " " + vista["tipo"].fillna("")).str.strip()
    vista["Ubicación"] = vista.apply(_ubicacion_evento, axis=1)
    vista["Actuación"] = vista["actuacion"].fillna("")
    vista["Operario"] = vista["operario"].fillna("")
    vista["Resultado"] = vista["resultado"].fillna("")
    vista["OT"] = vista["numero_ot"].fillna("")

    st.markdown("### 🕒 Cronología")
    st.dataframe(
        vista[["Fecha", "Tipo", "Ubicación", "Actuación", "Operario", "Resultado", "OT"]],
        use_container_width=True,
        hide_index=True,
        height=480,
    )

    with st.expander("🔍 Ver detalle de los últimos registros filtrados", expanded=False):
        for _, row in df_f.head(50).iterrows():
            titulo = (
                f"{_texto(row.get('icono'))} "
                f"{_formatear_fecha(row.get('fecha'))} · "
                f"{_texto(row.get('actuacion')) or _texto(row.get('tipo'))}"
            ).strip()

            with st.container(border=True):
                st.markdown(f"**{titulo}**")

                ubicacion = _ubicacion_evento(row)
                if ubicacion:
                    st.caption(f"📍 {ubicacion}")

                datos = []
                if _texto(row.get("numero_ot")):
                    datos.append("OT: " + _texto(row.get("numero_ot")))
                if _texto(row.get("operario")):
                    datos.append("Operario: " + _texto(row.get("operario")))
                if _texto(row.get("resultado")):
                    datos.append("Resultado: " + _texto(row.get("resultado")))
                if datos:
                    st.write(" · ".join(datos))

                if _texto(row.get("detalle")):
                    st.caption(_texto(row.get("detalle")))

                st.caption("Fuente: " + _texto(row.get("fuente")))

    exportar = vista[["Fecha", "Tipo", "Ubicación", "Actuación", "Operario", "Resultado", "OT"]].copy()
    csv = exportar.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "⬇️ Descargar histórico general CSV",
        data=csv,
        file_name="historico_general_mantenimiento.csv",
        mime="text/csv",
        use_container_width=True,
        key="descargar_historico_general_csv",
    )

    st.caption(
        "Histórico General no borra, edita ni sustituye los históricos especializados."
    )
