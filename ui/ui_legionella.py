import os
import streamlit as st
import pandas as pd
from datetime import date, datetime
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from database.db import conectar


OPERARIOS = ["J.A. Almeda", "Abel Vasquez", "Luis Lozano", "Otro"]

CENTROS = {
    "Pearson 22": {
        "Edif. Infantil/Primaria": [
            ("ACS", "Acumulador ACS 800L", "acumulador", "Cuarto técnico"),
            ("ACS", "Retorno ACS", "retorno", "Cuarto técnico"),
            ("AFCH", "Grifo representativo", "grifo", "Edificio Infantil/Primaria"),
        ],
        "Edif. Llar (Anexo)": [
            ("ACS", "Depósito ACS 1000L", "acumulador", "Sala técnica"),
            ("Solar", "Depósito solar 1", "acumulador_solar", "Sala técnica"),
            ("Solar", "Depósito solar 2", "acumulador_solar", "Sala técnica"),
            ("ACS", "Duchas", "ducha", "Vestuario"),
            ("AFCH", "Grifo representativo", "grifo", "Llar"),
        ],
    },
    "Pearson 9": {
        "Edif. A": [
            ("ACS", "Acumulador ACS", "acumulador", "Cuarto técnico"),
            ("ACS", "Retorno ACS", "retorno", "Cuarto técnico"),
            ("AFCH", "Grifo representativo", "grifo", "Edif. A"),
        ],
        "Edif. B": [
            ("AFCH", "Grifo representativo", "grifo", "Edif. B"),
        ],
        "Edif. C": [
            ("ACS", "Acumulador ACS", "acumulador", "Cuarto técnico"),
            ("AFCH", "Grifo representativo", "grifo", "Edif. C"),
        ],
    },
}

def adaptar_sql(sql):
    if os.getenv("DATABASE_URL"):
        return sql.replace("?", "%s")
    return sql


def ejecutar(sql, params=()):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(adaptar_sql(sql), params)
    conn.commit()
    conn.close()


def leer_df(sql, params=()):
    conn = conectar()
    df = pd.read_sql_query(adaptar_sql(sql), conn, params=params)
    conn.close()
    return df


def sembrar_puntos_si_vacio():
    df = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_puntos
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND nombre_punto IS NOT NULL
    """)

    if int(df.loc[0, "total"]) > 0:
        return

    conn = conectar()
    cur = conn.cursor()

    for centro, edificios in CENTROS.items():
        for edificio, puntos in edificios.items():
            for instalacion, nombre, tipo, ubicacion in puntos:
                cur.execute(
                    adaptar_sql("""
                    INSERT INTO legionella_puntos
                    (centro, edificio, instalacion, tipo_punto, nombre_punto, ubicacion, activo, observaciones)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """),
                    (centro, edificio, instalacion, tipo, nombre, ubicacion, "Alta inicial automática"),
                )

    conn.commit()
    conn.close()


def evaluar_resultado(tipo_control, valor, valor_2=None):
    if tipo_control == "Temperatura acumulador":
        if valor >= 60:
            return "OK", "Correcto"
        return "RIESGO", "Acumulador por debajo de 60 ºC"

    if tipo_control == "Temperatura retorno":
        if valor >= 50:
            return "OK", "Correcto"
        return "RIESGO", "Retorno por debajo de 50 ºC"

    if tipo_control == "Cloro residual":
        if 0.2 <= valor <= 1.0:
            return "OK", "Correcto"
        return "RIESGO", "Cloro fuera de rango 0,2 - 1,0 mg/L"

    if tipo_control == "Revisión visual":
        if valor == 1:
            return "OK", "Correcto"
        return "INCIDENCIA", "Revisión visual desfavorable"

    if tipo_control == "Purga":
        if valor == 1:
            return "OK", "Correcto"
        return "INCIDENCIA", "Purga no realizada"

    return "OK", "Registrado"


def operario_por_centro(centro):
    if centro == "Pearson 9":
        return "Luis Lozano"
    if centro == "Pearson 22":
        return "J.A. Almeda"
    return ""


def obtener_siguiente_numero_ot():
    conn = conectar()
    cur = conn.cursor()

    numeros = []

    for tabla in ["ordenes_trabajo", "historico_ordenes"]:
        try:
            cur.execute(f"SELECT numero_ot FROM {tabla} WHERE numero_ot IS NOT NULL")
            for fila in cur.fetchall():
                numero = str(fila[0])
                if numero.startswith("OT-"):
                    try:
                        numeros.append(int(numero.replace("OT-", "")))
                    except Exception:
                        pass
        except Exception:
            pass

    conn.close()

    siguiente = max(numeros) + 1 if numeros else 1
    return f"OT-{siguiente:05d}"


def existe_ot_legionella_abierta(centro, edificio, descripcion):
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        adaptar_sql("""
        SELECT COUNT(*)
        FROM ordenes_trabajo
        WHERE centro = ?
          AND edificio = ?
          AND area = 'Legionella'
          AND origen = 'Legionella'
          AND descripcion = ?
          AND LOWER(COALESCE(estado, '')) NOT IN ('finalizada', 'cerrada')
        """),
        (centro, edificio, descripcion),
    )

    total = cur.fetchone()[0]
    conn.close()

    return total > 0


def crear_ot_legionella(centro, edificio, punto, tarea):
    descripcion = f"Control Legionella - {tarea} - {punto}"

    if existe_ot_legionella_abierta(centro, edificio, descripcion):
        return False

    numero_ot = obtener_siguiente_numero_ot()
    operario = operario_por_centro(centro)

    ejecutar(
        """
        INSERT INTO ordenes_trabajo
        (numero_ot, descripcion, estado, centro, edificio, espacio, area, prioridad, operario, origen)
        VALUES (?, ?, 'Abierta', ?, ?, ?, 'Legionella', 'Alta', ?, 'Legionella')
        """,
        (
            numero_ot,
            descripcion,
            centro,
            edificio,
            punto,
            operario,
        ),
    )

    return True


def registrar_control(fecha_registro, punto, tarea, tipo_control, valor, valor_2, unidad, operario, observaciones):
    estado, resultado = evaluar_resultado(tipo_control, valor, valor_2)

    ejecutar(
        """
        INSERT INTO legionella_registros
        (fecha, centro, edificio, instalacion, punto_id, tarea_id, punto, tarea, tipo_control,
         valor, valor_2, unidad, estado, resultado, operario, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fecha_registro,
            punto["centro"],
            punto["edificio"],
            punto["instalacion"],
            punto["id"],
            None,
            punto["nombre_punto"],
            tarea,
            tipo_control,
            valor,
            valor_2,
            unidad,
            estado,
            resultado,
            operario,
            observaciones,
        ),
    )

    if estado in ["RIESGO", "INCIDENCIA"]:
        ejecutar(
            """
            INSERT INTO legionella_incidencias
            (centro, edificio, punto, tarea, descripcion, estado, prioridad, operario)
            VALUES (?, ?, ?, ?, ?, 'Abierta', 'Alta', ?)
            """,
            (
                punto["centro"],
                punto["edificio"],
                punto["nombre_punto"],
                tarea,
                resultado + (" | " + observaciones if observaciones else ""),
                operario,
            ),
        )

        crear_ot_legionella(
            punto["centro"],
            punto["edificio"],
            punto["nombre_punto"],
            tarea,
        )

    return estado, resultado


def dias_frecuencia(tarea):
    if tarea in ["Temperatura acumulador", "Temperatura retorno", "Cloro residual"]:
        return 7

    if tarea in ["Purga", "Revisión visual", "Temperatura punto terminal"]:
        return 30

    return 30


def calcular_estado_control(proxima_fecha):
    hoy = pd.Timestamp(date.today())

    if proxima_fecha <= hoy:
        return "🔴 TOCA"

    if proxima_fecha <= hoy + pd.Timedelta(days=30):
        return "🟠 PRÓXIMO"

    return "🟢 OK"


def generar_ots_legionella_si_toca():
    df = leer_df("""
        SELECT fecha, centro, edificio, punto, tarea, resultado
        FROM legionella_registros
        ORDER BY fecha DESC, id DESC
    """)

    if df.empty:
        return 0, "Sin registros todavía"

    df["fecha"] = pd.to_datetime(df["fecha"])

    df_ultimos = (
        df.sort_values("fecha", ascending=False)
        .drop_duplicates(subset=["centro", "edificio", "punto", "tarea"])
        .copy()
    )

    df_ultimos["frecuencia_dias"] = df_ultimos["tarea"].apply(dias_frecuencia)
    df_ultimos["proxima_fecha"] = (
        df_ultimos["fecha"] + pd.to_timedelta(df_ultimos["frecuencia_dias"], unit="D")
    )
    df_ultimos["estado_control"] = df_ultimos["proxima_fecha"].apply(calcular_estado_control)

    creadas = 0
    ya_existia = 0
    no_toca = 0

    for _, fila in df_ultimos.iterrows():

        if fila["estado_control"] == "🔴 TOCA":
            creada = crear_ot_legionella(
                fila["centro"],
                fila["edificio"],
                fila["punto"],
                fila["tarea"],
            )
            if creada:
                creadas += 1
            else:
                ya_existia += 1
        else:
            no_toca += 1

    # 🔽 MENSAJE INTELIGENTE
    if creadas > 0:
        mensaje = f"Se han creado {creadas} órdenes automáticamente"
    elif ya_existia > 0:
        mensaje = "Ya existen órdenes abiertas de Legionella"
    else:
        mensaje = "No toca todavía (controles en fecha o próximos)"

    return creadas, mensaje


def generar_informe_legionella(fecha_inicio, fecha_fin):

    fecha_inicio_txt = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_txt = fecha_fin.strftime("%Y-%m-%d")

    df = leer_df("""
        SELECT fecha, centro, edificio, instalacion, punto, tarea, valor, valor_2,
               unidad, estado, resultado, operario, observaciones
        FROM legionella_registros
        WHERE date(fecha) BETWEEN ? AND ?
        ORDER BY fecha DESC
    """, (fecha_inicio_txt, fecha_fin_txt))

    df_inc = leer_df("""
        SELECT fecha_apertura, centro, edificio, punto, tarea, descripcion,
               estado, prioridad, operario, fecha_cierre, observaciones_cierre
        FROM legionella_incidencias
        WHERE date(fecha_apertura) BETWEEN ? AND ?
        ORDER BY fecha_apertura DESC
    """, (fecha_inicio_txt, fecha_fin_txt))

    if df.empty:
        st.warning("No hay datos para generar el informe en esas fechas.")
        return

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35
    )

    styles = getSampleStyleSheet()
    contenido = []

    total = len(df)
    ok = len(df[df["estado"] == "OK"])
    no_ok = total - ok
    cumplimiento = round((ok / total) * 100, 2) if total else 0

    fecha_informe = datetime.now().strftime("%d/%m/%Y %H:%M")

    contenido.append(Paragraph("INFORME DE CONTROL DE LEGIONELLA", styles["Title"]))
    contenido.append(Spacer(1, 12))

    contenido.append(Paragraph(f"<b>Fecha de emisión:</b> {fecha_informe}", styles["Normal"]))
    contenido.append(Paragraph(f"<b>Periodo revisado:</b> {fecha_inicio.strftime('%d/%m/%Y')} a {fecha_fin.strftime('%d/%m/%Y')}", styles["Normal"]))
    contenido.append(Paragraph("<b>Centro:</b> Pearson 9 / Pearson 22", styles["Normal"]))
    contenido.append(Paragraph("<b>Tipo de control:</b> ACS / AFCH / puntos terminales", styles["Normal"]))
    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph("1. Resumen general", styles["Heading2"]))

    resumen = [
        ["Total controles", "Correctos", "Incidencias/Riesgos", "Cumplimiento"],
        [str(total), str(ok), str(no_ok), f"{cumplimiento}%"]
    ]

    tabla_resumen = Table(resumen, colWidths=[110, 110, 130, 110])
    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))

    contenido.append(tabla_resumen)
    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph("2. Controles realizados", styles["Heading2"]))

    tabla_data = [["Fecha", "Centro", "Edificio", "Punto", "Tarea", "Valor", "Estado"]]

    for _, row in df.head(60).iterrows():
        valor = "" if pd.isna(row["valor"]) else str(row["valor"])
        unidad = "" if pd.isna(row["unidad"]) else str(row["unidad"])

        tabla_data.append([
            str(row["fecha"])[:10],
            str(row["centro"]),
            str(row["edificio"]),
            str(row["punto"])[:22],
            str(row["tarea"])[:24],
            f"{valor} {unidad}",
            str(row["estado"])
        ])

    tabla = Table(tabla_data, colWidths=[55, 65, 70, 100, 105, 55, 60])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    contenido.append(tabla)
    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph("3. Incidencias detectadas", styles["Heading2"]))

    if df_inc.empty:
        contenido.append(Paragraph("No constan incidencias registradas en el periodo.", styles["Normal"]))
    else:
        tabla_inc = [["Fecha", "Centro", "Punto", "Tarea", "Estado", "Descripción"]]

        for _, row in df_inc.head(40).iterrows():
            tabla_inc.append([
                str(row["fecha_apertura"])[:10],
                str(row["centro"]),
                str(row["punto"])[:22],
                str(row["tarea"])[:22],
                str(row["estado"]),
                str(row["descripcion"])[:45],
            ])

        tabla_i = Table(tabla_inc, colWidths=[55, 65, 100, 100, 55, 155])
        tabla_i.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        contenido.append(tabla_i)

    contenido.append(Spacer(1, 20))
    contenido.append(Paragraph("4. Observaciones", styles["Heading2"]))
    contenido.append(Paragraph(
        "Informe generado automáticamente desde el sistema de mantenimiento. "
        "Los controles registrados incluyen temperaturas, cloro residual, purgas, revisiones visuales "
        "e incidencias asociadas.",
        styles["Normal"]
    ))

    doc.build(contenido)

    st.download_button(
        "📄 Descargar informe inspección Legionella",
        data=buffer.getvalue(),
        file_name=f"informe_legionella_{fecha_inicio_txt}_a_{fecha_fin_txt}.pdf",
        mime="application/pdf"
    )


def pantalla_legionella():
    sembrar_puntos_si_vacio()
    ots_creadas = generar_ots_legionella_si_toca()

    ots_creadas, mensaje = generar_ots_legionella_si_toca()

    if ots_creadas > 0:
        st.success(mensaje)
    else:
        st.info(mensaje)

    st.subheader("💧 Legionella")
    st.caption("Control ACS / AFCH · temperaturas · cloro · purgas · incidencias · histórico")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📋 Registrar control", "📅 Próximos / estado", "📚 Histórico", "🚨 Incidencias", "📄 Informe"]
    )

    with tab1:
        st.markdown("### Nuevo control")

        centros = list(CENTROS.keys())
        centro = st.selectbox("Centro", centros)

        edificios = list(CENTROS[centro].keys())
        edificio = st.selectbox("Edificio", edificios)

        puntos_df = leer_df(
            """
            SELECT * FROM legionella_puntos
            WHERE centro = ? AND edificio = ? AND activo = 1
            ORDER BY instalacion, nombre_punto
            """,
            (centro, edificio),
        )

        if puntos_df.empty:
            st.warning("No hay puntos de control dados de alta.")
            return

        punto_nombre = st.selectbox("Punto de control", puntos_df["nombre_punto"].tolist())
        df_filtrado = puntos_df[puntos_df["nombre_punto"] == punto_nombre]

        if df_filtrado.empty:
            st.error("No se ha encontrado el punto de control. Revisa configuración.")
            return

        punto = df_filtrado.iloc[0].to_dict()

        tipo_punto = punto["tipo_punto"]

        tareas = ["Revisión visual", "Purga"]

        if tipo_punto in ["acumulador", "acumulador_solar"]:
            tareas.insert(0, "Temperatura acumulador")

        if tipo_punto == "retorno":
            tareas.insert(0, "Temperatura retorno")

        if tipo_punto in ["grifo", "ducha"]:
            tareas.insert(0, "Cloro residual")
            tareas.insert(1, "Temperatura punto terminal")

        tarea = st.selectbox("Tarea", tareas)

        if tarea == "Temperatura acumulador":
            tipo_control = "Temperatura acumulador"
            unidad = "ºC"
            valor = st.number_input("Temperatura acumulador ºC", min_value=0.0, max_value=100.0, value=60.0, step=0.1)
            valor_2 = None

        elif tarea == "Temperatura retorno":
            tipo_control = "Temperatura retorno"
            unidad = "ºC"
            valor = st.number_input("Temperatura retorno ºC", min_value=0.0, max_value=100.0, value=50.0, step=0.1)
            valor_2 = None

        elif tarea == "Temperatura punto terminal":
            tipo_control = "Temperatura punto terminal"
            unidad = "ºC"
            valor = st.number_input("Temperatura ºC", min_value=0.0, max_value=100.0, value=45.0, step=0.1)
            valor_2 = None

        elif tarea == "Cloro residual":
            tipo_control = "Cloro residual"
            unidad = "mg/L"
            valor = st.number_input("Cloro residual libre mg/L", min_value=0.0, max_value=5.0, value=0.5, step=0.01)
            valor_2 = None

        elif tarea == "Revisión visual":
            tipo_control = "Revisión visual"
            unidad = "OK/KO"
            correcto = st.radio("Resultado revisión visual", ["Correcto", "Deficiente"], horizontal=True)
            valor = 1 if correcto == "Correcto" else 0
            valor_2 = None

        else:
            tipo_control = "Purga"
            unidad = "Sí/No"
            purga = st.radio("Purga realizada", ["Sí", "No"], horizontal=True)
            valor = 1 if purga == "Sí" else 0
            valor_2 = None

        fecha_registro = st.date_input("Fecha del control", value=date.today())
        operario_auto = operario_por_centro(centro)

        if operario_auto in OPERARIOS:
            indice_operario = OPERARIOS.index(operario_auto)
        else:
            indice_operario = 0

        operario = st.selectbox(
            "Operario",
            OPERARIOS,
            index=indice_operario,
            key=f"legionella_operario_{centro}"
        )

        if operario == "Otro":
            operario = st.text_input("Nombre operario")

        observaciones = st.text_area("Observaciones")

        if st.button("Guardar control Legionella", type="primary"):
            estado, resultado = registrar_control(
                fecha_registro.strftime("%Y-%m-%d"),
                punto,
                tarea,
                tipo_control,
                valor,
                valor_2,
                unidad,
                operario,
                observaciones,
            )

            if estado == "OK":
                st.success(f"Control guardado correctamente: {resultado}")
            elif estado == "RIESGO":
                st.error(f"Control guardado con RIESGO: {resultado}")
            else:
                st.warning(f"Control guardado con incidencia: {resultado}")

    with tab2:
        st.markdown("### Próximos controles / estado")

        df = leer_df("""
            SELECT fecha, centro, edificio, instalacion, punto, tarea, estado, resultado, operario
            FROM legionella_registros
            ORDER BY fecha DESC, id DESC
        """)

        if df.empty:
            st.info("Todavía no hay controles registrados.")
        else:
            df["fecha"] = pd.to_datetime(df["fecha"])

            df_ultimos = (
                df.sort_values("fecha", ascending=False)
                .drop_duplicates(subset=["centro", "edificio", "punto", "tarea"])
                .copy()
            )

            df_ultimos["frecuencia_dias"] = df_ultimos["tarea"].apply(dias_frecuencia)
            df_ultimos["proxima_fecha"] = (
                df_ultimos["fecha"] + pd.to_timedelta(df_ultimos["frecuencia_dias"], unit="D")
            )
            df_ultimos["estado_control"] = df_ultimos["proxima_fecha"].apply(calcular_estado_control)

            total = len(df_ultimos)
            toca = len(df_ultimos[df_ultimos["estado_control"] == "🔴 TOCA"])
            proximo = len(df_ultimos[df_ultimos["estado_control"] == "🟠 PRÓXIMO"])
            ok = len(df_ultimos[df_ultimos["estado_control"] == "🟢 OK"])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Controles", total)
            c2.metric("🔴 Toca", toca)
            c3.metric("🟠 Próximo", proximo)
            c4.metric("🟢 OK", ok)

            st.markdown("### Detalle")

            df_ultimos["fecha"] = df_ultimos["fecha"].dt.strftime("%Y-%m-%d")
            df_ultimos["proxima_fecha"] = df_ultimos["proxima_fecha"].dt.strftime("%Y-%m-%d")

            st.dataframe(
                df_ultimos[
                    [
                        "estado_control",
                        "centro",
                        "edificio",
                        "punto",
                        "tarea",
                        "fecha",
                        "proxima_fecha",
                        "resultado",
                        "operario",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    with tab3:
        st.markdown("### Histórico de controles")

        df = leer_df("""
            SELECT fecha, centro, edificio, instalacion, punto, tarea, tipo_control,
                   valor, valor_2, unidad, estado, resultado, operario, observaciones
            FROM legionella_registros
            ORDER BY fecha DESC, id DESC
        """)

        if df.empty:
            st.info("No hay histórico todavía.")
        else:
            centro_f = st.selectbox("Filtrar centro", ["Todos"] + sorted(df["centro"].dropna().unique().tolist()))
            estado_f = st.selectbox("Filtrar estado", ["Todos"] + sorted(df["estado"].dropna().unique().tolist()))

            df_filtrado = df.copy()

            if centro_f != "Todos":
                df_filtrado = df_filtrado[df_filtrado["centro"] == centro_f]

            if estado_f != "Todos":
                df_filtrado = df_filtrado[df_filtrado["estado"] == estado_f]

            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

            csv = df_filtrado.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Descargar histórico CSV",
                data=csv,
                file_name="historico_legionella.csv",
                mime="text/csv",
            )

    with tab4:
        st.markdown("### Incidencias Legionella")

        df = leer_df("""
            SELECT id, fecha_apertura, centro, edificio, punto, tarea, descripcion,
                   estado, prioridad, operario, fecha_cierre, observaciones_cierre
            FROM legionella_incidencias
            ORDER BY fecha_apertura DESC, id DESC
        """)

        if df.empty:
            st.success("No hay incidencias de Legionella.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

            abiertas = df[df["estado"] == "Abierta"]

            if not abiertas.empty:
                st.markdown("### Cerrar incidencia")

                incidencia_id = st.selectbox(
                    "Incidencia abierta",
                    abiertas["id"].tolist()
                )

                obs_cierre = st.text_area("Observaciones de cierre")

                if st.button("Cerrar incidencia"):
                    ejecutar(
                        """
                        UPDATE legionella_incidencias
                        SET estado = 'Cerrada',
                            fecha_cierre = ?,
                            observaciones_cierre = ?
                        WHERE id = ?
                        """,
                        (
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            obs_cierre,
                            int(incidencia_id),
                        ),
                    )
                    st.success("Incidencia cerrada.")
                    st.rerun()

    with tab5:
        st.markdown("### Informe inspección Legionella")

        col1, col2 = st.columns(2)

        fecha_inicio = col1.date_input(
            "Fecha inicio",
            value=date.today().replace(day=1),
            key="legionella_informe_inicio"
        )

        fecha_fin = col2.date_input(
            "Fecha fin",
            value=date.today(),
            key="legionella_informe_fin"
        )

        if fecha_inicio > fecha_fin:
            st.error("La fecha de inicio no puede ser posterior a la fecha fin.")
        else:
            if st.button("📄 Generar informe inspección"):
                generar_informe_legionella(fecha_inicio, fecha_fin)
