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
        "Sala calderas": [
            ("ACS", "Acumulador ACS Principal", "acumulador", "Cuarto calderas"),
            ("ACS", "Retorno ACS Principal", "retorno", "Cuarto calderas"),
        ],
        "Edif. A": [
            ("AFCH", "Grifo representativo", "grifo", "Edif. A"),
        ],
        "Edif. B": [
            ("AFCH", "Grifo representativo", "grifo", "Edif. B"),
        ],
        "Edif. C": [
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
    try:
        cur.execute(adaptar_sql(sql), params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def leer_df(sql, params=()):
    conn = conectar()
    try:
        df = pd.read_sql_query(adaptar_sql(sql), conn, params=params)
    finally:
        conn.close()
    return df
def asegurar_columnas_planificacion_legionella():
    columnas = [
        ("punto_id", "INTEGER"),
        ("tarea", "TEXT"),
        ("tipo_control", "TEXT"),
        ("frecuencia", "TEXT"),
        ("valor_minimo", "REAL"),
        ("valor_maximo", "REAL"),
        ("unidad", "TEXT"),
        ("ultima_fecha", "TEXT"),
        ("proxima_fecha", "TEXT"),
        ("activo", "INTEGER DEFAULT 1"),
        ("observaciones", "TEXT"),
        ("centro", "TEXT"),
        ("edificio", "TEXT"),
        ("instalacion", "TEXT"),
        ("punto", "TEXT"),
        ("operario", "TEXT"),
        ("frecuencia_dias", "INTEGER DEFAULT 30"),
        ("fecha_inicio", "TEXT"),
        ("generar_ot", "INTEGER DEFAULT 1"),
    ]

    for columna, tipo in columnas:
        try:
            ejecutar(f"ALTER TABLE legionella_tareas ADD COLUMN {columna} {tipo}")
        except Exception:
            pass


def limpiar_registros_invalidos_legionella():
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(adaptar_sql("""
            DELETE FROM legionella_registros
            WHERE centro IS NULL
               OR edificio IS NULL
               OR punto IS NULL
               OR tarea IS NULL
               OR TRIM(COALESCE(centro, '')) = ''
               OR TRIM(COALESCE(edificio, '')) = ''
               OR TRIM(COALESCE(punto, '')) = ''
               OR TRIM(COALESCE(tarea, '')) = ''
        """))

        registros_borrados = cur.rowcount

        cur.execute(adaptar_sql("""
            DELETE FROM legionella_incidencias
            WHERE centro IS NULL
               OR edificio IS NULL
               OR punto IS NULL
               OR tarea IS NULL
               OR TRIM(COALESCE(centro, '')) = ''
               OR TRIM(COALESCE(edificio, '')) = ''
               OR TRIM(COALESCE(punto, '')) = ''
               OR TRIM(COALESCE(tarea, '')) = ''
        """))

        incidencias_borradas = cur.rowcount

        conn.commit()
        return registros_borrados, incidencias_borradas

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def sembrar_puntos_si_vacio():
    conn = conectar()
    cur = conn.cursor()
    creados = 0

    try:
        for centro, edificios in CENTROS.items():
            for edificio, puntos in edificios.items():
                for instalacion, nombre, tipo, ubicacion in puntos:
                    cur.execute(
                        adaptar_sql("""
                        SELECT COUNT(*)
                        FROM legionella_puntos
                        WHERE centro = ?
                          AND edificio = ?
                          AND instalacion = ?
                          AND nombre_punto = ?
                        """),
                        (centro, edificio, instalacion, nombre),
                    )

                    existe = cur.fetchone()[0]

                    if existe == 0:
                        cur.execute(
                            adaptar_sql("""
                            INSERT INTO legionella_puntos
                            (centro, edificio, instalacion, tipo_punto, nombre_punto, ubicacion, activo, observaciones)
                            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                            """),
                            (
                                centro,
                                edificio,
                                instalacion,
                                tipo,
                                nombre,
                                ubicacion,
                                "Alta inicial automática",
                            ),
                        )
                        creados += 1

        conn.commit()
        return creados

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def evaluar_resultado(tipo_control, valor, valor_2=None):
    try:
        valor = float(valor)
    except Exception:
        return "INCIDENCIA", "Valor no válido o vacío"

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

    try:
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
    finally:
        conn.close()

    return total > 0


def crear_ot_legionella(centro, edificio, punto, tarea, operario=None):
    if not centro or not edificio or not punto or not tarea:
        return False

    descripcion = f"Control Legionella - {tarea} - {punto}"

    if existe_ot_legionella_abierta(centro, edificio, descripcion):
        return False

    numero_ot = obtener_siguiente_numero_ot()
    operario_final = operario or operario_por_centro(centro)

    ejecutar(
        """
        INSERT INTO ordenes_trabajo
        (numero_ot, descripcion, estado, centro, edificio, espacio, area, prioridad, operario, origen, tipo_solicitante)
        VALUES (?, ?, 'Abierta', ?, ?, ?, 'Legionella', 'Alta', ?, 'Legionella', 'Operarios')
        """,
        (
            numero_ot,
            descripcion,
            centro,
            edificio,
            punto,
            operario_final,
        ),
    )

    return True


def dias_frecuencia(tarea):
    if tarea in [
        "Temperatura acumulador",
        "Temperatura impulsión ACS",
        "Temperatura retorno",
        "Cloro residual"
    ]:
        return 7

    if tarea in ["Purga", "Revisión visual", "Temperatura punto terminal"]:
        return 30

    return 30


def tareas_por_tipo_punto(tipo_punto):
    tareas = ["Revisión visual", "Purga"]

    if tipo_punto in ["acumulador", "acumulador_solar"]:
        tareas.insert(0, "Temperatura acumulador")
        tareas.insert(1, "Temperatura impulsión ACS")

    if tipo_punto == "retorno":
        tareas.insert(0, "Temperatura retorno")

    if tipo_punto in ["grifo", "ducha"]:
        tareas.insert(0, "Cloro residual")
        tareas.insert(1, "Temperatura punto terminal")

    return tareas


def unidad_por_tarea(tarea):
    if tarea in ["Temperatura acumulador", "Temperatura retorno", "Temperatura punto terminal"]:
        return "ºC"

    if tarea == "Cloro residual":
        return "mg/L"

    if tarea == "Revisión visual":
        return "OK/KO"

    if tarea == "Purga":
        return "Sí/No"

    return ""


def existe_plan_legionella(punto_id, tarea):
    df = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_tareas
        WHERE punto_id = ?
          AND tarea = ?
          AND activo = 1
    """, (punto_id, tarea))

    return int(df.loc[0, "total"]) > 0


def sembrar_planificacion_legionella(fecha_inicio):
    puntos_df = leer_df("""
        SELECT *
        FROM legionella_puntos
        WHERE activo = 1
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND nombre_punto IS NOT NULL
        ORDER BY centro, edificio, instalacion, nombre_punto
    """)

    if puntos_df.empty:
        return 0

    creadas = 0

    for _, punto in puntos_df.iterrows():
        punto_id = int(punto["id"])
        centro = punto["centro"]
        edificio = punto["edificio"]
        instalacion = punto["instalacion"]
        nombre_punto = punto["nombre_punto"]
        tipo_punto = punto["tipo_punto"]
        operario = operario_por_centro(centro)

        for tarea in tareas_por_tipo_punto(tipo_punto):
            if existe_plan_legionella(punto_id, tarea):
                continue

            frecuencia = dias_frecuencia(tarea)
            unidad = unidad_por_tarea(tarea)

            ejecutar("""
                INSERT INTO legionella_tareas
                (punto_id, centro, edificio, instalacion, punto, tarea, tipo_control,
                 frecuencia, frecuencia_dias, unidad, fecha_inicio, ultima_fecha,
                 proxima_fecha, operario, activo, generar_ot, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 1, 1, ?)
            """, (
                punto_id,
                centro,
                edificio,
                instalacion,
                nombre_punto,
                tarea,
                tarea,
                f"{frecuencia} días",
                frecuencia,
                unidad,
                fecha_inicio,
                fecha_inicio,
                operario,
                "Planificación inicial automática"
            ))

            creadas += 1

    return creadas


def obtener_planificacion_legionella():
    return leer_df("""
        SELECT id, centro, edificio, instalacion, punto, tarea, tipo_control,
               frecuencia_dias, proxima_fecha, operario, activo, generar_ot
        FROM legionella_tareas
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY centro, edificio, punto, tarea
    """)


def actualizar_plan_legionella(tarea_id, frecuencia_dias, proxima_fecha, operario, generar_ot, activo):
    ejecutar("""
        UPDATE legionella_tareas
        SET frecuencia_dias = ?,
            frecuencia = ?,
            proxima_fecha = ?,
            operario = ?,
            generar_ot = ?,
            activo = ?
        WHERE id = ?
    """, (
        int(frecuencia_dias),
        f"{int(frecuencia_dias)} días",
        proxima_fecha,
        operario,
        1 if generar_ot else 0,
        1 if activo else 0,
        int(tarea_id)
    ))

def borrar_plan_legionella(tarea_id):
    ejecutar("""
        DELETE FROM legionella_tareas
        WHERE id = ?
    """, (int(tarea_id),))

def crear_punto_legionella(centro, edificio, instalacion, tipo_punto, nombre_punto, ubicacion, observaciones):
    ejecutar("""
        INSERT INTO legionella_puntos
        (centro, edificio, instalacion, tipo_punto, nombre_punto, ubicacion, activo, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        centro,
        edificio,
        instalacion,
        tipo_punto,
        nombre_punto,
        ubicacion,
        observaciones
    ))


def actualizar_estado_punto_legionella(punto_id, activo):
    ejecutar("""
        UPDATE legionella_puntos
        SET activo = ?
        WHERE id = ?
    """, (
        1 if activo else 0,
        int(punto_id)
    ))


def obtener_puntos_legionella_admin():
    return leer_df("""
        SELECT id, centro, edificio, instalacion, tipo_punto,
               nombre_punto, ubicacion, activo, observaciones
        FROM legionella_puntos
        ORDER BY centro, edificio, instalacion, nombre_punto
    """)


def calcular_estado_control(proxima_fecha):
    hoy = pd.Timestamp(date.today())

    if proxima_fecha <= hoy:
        return "🔴 TOCA"

    if proxima_fecha <= hoy + pd.Timedelta(days=30):
        return "🟠 PRÓXIMO"

    return "🟢 OK"


def generar_ots_legionella_planificadas():
    df = leer_df("""
        SELECT id, centro, edificio, punto, tarea, frecuencia_dias, proxima_fecha, operario
        FROM legionella_tareas
        WHERE activo = 1
          AND generar_ot = 1
          AND proxima_fecha IS NOT NULL
          AND date(proxima_fecha) <= date('now')
    """)

    if df.empty:
        return 0, "No hay controles planificados que toquen hoy."

    creadas = 0
    ya_existia = 0

    for _, fila in df.iterrows():
        creada = crear_ot_legionella(
            fila["centro"],
            fila["edificio"],
            fila["punto"],
            fila["tarea"],
            fila["operario"],
        )

        if creada:
            creadas += 1

            proxima = pd.to_datetime(fila["proxima_fecha"]) + pd.Timedelta(
                days=int(fila["frecuencia_dias"] or 30)
            )

            ejecutar("""
                UPDATE legionella_tareas
                SET proxima_fecha = ?
                WHERE id = ?
            """, (
                proxima.strftime("%Y-%m-%d"),
                int(fila["id"])
            ))
        else:
            ya_existia += 1

    if creadas > 0:
        return creadas, f"Se han creado {creadas} OT de Legionella planificadas."

    if ya_existia > 0:
        return 0, "Ya existen OT abiertas para esos controles."

    return 0, "No se ha creado ninguna OT."


def generar_ots_legionella_si_toca():
    df_plan = leer_df("""
        SELECT COUNT(*) AS total
        FROM legionella_tareas
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
          AND activo = 1
    """)

    try:
        total_plan = int(df_plan.loc[0, "total"])
    except Exception:
        total_plan = 0

    if total_plan > 0:
        return generar_ots_legionella_planificadas()

    df = leer_df("""
        SELECT fecha, centro, edificio, punto, tarea, resultado
        FROM legionella_registros
        WHERE centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
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

    if creadas > 0:
        mensaje = f"Se han creado {creadas} órdenes automáticamente"
    elif ya_existia > 0:
        mensaje = "Ya existen órdenes abiertas de Legionella"
    else:
        mensaje = "No toca todavía (controles en fecha o próximos)"

    return creadas, mensaje


def registrar_control(fecha_registro, punto, tarea, tipo_control, valor, valor_2, unidad, operario, observaciones):
    centro = punto.get("centro")
    edificio = punto.get("edificio")
    instalacion = punto.get("instalacion") or ""
    punto_id = punto.get("id")
    punto_nombre = punto.get("nombre_punto")

    if not centro or not edificio or not punto_nombre:
        return "ERROR", "Punto incompleto. No se ha guardado el registro."

    if not tarea or not tipo_control:
        return "ERROR", "Tarea o tipo de control vacío. No se ha guardado el registro."

    if valor is None:
        return "ERROR", "Valor no válido. No se ha guardado el registro."

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
            centro,
            edificio,
            instalacion,
            punto_id,
            None,
            punto_nombre,
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

    try:
        df_plan = leer_df("""
            SELECT id, frecuencia_dias
            FROM legionella_tareas
            WHERE centro = ?
              AND edificio = ?
              AND punto = ?
              AND tarea = ?
              AND activo = 1
            ORDER BY id DESC
            LIMIT 1
        """, (centro, edificio, punto_nombre, tarea))

        if not df_plan.empty:
            frecuencia = int(df_plan.iloc[0]["frecuencia_dias"] or dias_frecuencia(tarea))
            proxima = pd.to_datetime(fecha_registro) + pd.Timedelta(days=frecuencia)

            ejecutar("""
                UPDATE legionella_tareas
                SET ultima_fecha = ?,
                    proxima_fecha = ?
                WHERE id = ?
            """, (
                fecha_registro,
                proxima.strftime("%Y-%m-%d"),
                int(df_plan.iloc[0]["id"])
            ))
    except Exception:
        pass

    if estado in ["RIESGO", "INCIDENCIA"]:
        if centro and edificio and punto_nombre and tarea:
            ejecutar(
                """
                INSERT INTO legionella_incidencias
                (centro, edificio, punto, tarea, descripcion, estado, prioridad, operario)
                VALUES (?, ?, ?, ?, ?, 'Abierta', 'Alta', ?)
                """,
                (
                    centro,
                    edificio,
                    punto_nombre,
                    tarea,
                    resultado + (" | " + observaciones if observaciones else ""),
                    operario,
                ),
            )

            crear_ot_legionella(
                centro,
                edificio,
                punto_nombre,
                tarea,
                operario,
            )

    return estado, resultado


def generar_informe_legionella(fecha_inicio, fecha_fin, centro_filtro):
    fecha_inicio_txt = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_txt = fecha_fin.strftime("%Y-%m-%d")

    def limpiar_pdf(texto, max_len=None):
        texto = "" if pd.isna(texto) else str(texto)
        texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if max_len:
            texto = texto[:max_len]
        return texto

    df = leer_df("""
        SELECT fecha, centro, edificio, instalacion, punto, tarea, valor, valor_2,
               unidad, estado, resultado, operario, observaciones
        FROM legionella_registros
        WHERE date(fecha) BETWEEN ? AND ?
          AND centro = ?
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY fecha DESC
    """, (fecha_inicio_txt, fecha_fin_txt, centro_filtro))

    df_inc = leer_df("""
        SELECT fecha_apertura, centro, edificio, punto, tarea, descripcion,
               estado, prioridad, operario, fecha_cierre, observaciones_cierre
        FROM legionella_incidencias
        WHERE date(fecha_apertura) BETWEEN ? AND ?
          AND centro = ?
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY fecha_apertura DESC
    """, (fecha_inicio_txt, fecha_fin_txt, centro_filtro))

    df_puntos = leer_df("""
        SELECT centro, edificio, instalacion, tipo_punto, nombre_punto, ubicacion, activo
        FROM legionella_puntos
        WHERE centro = ?
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND nombre_punto IS NOT NULL
        ORDER BY centro, edificio, instalacion, nombre_punto
    """, (centro_filtro,))

    df_plan = leer_df("""
        SELECT centro, edificio, instalacion, punto, tarea, frecuencia, frecuencia_dias,
               proxima_fecha, operario, activo
        FROM legionella_tareas
        WHERE centro = ?
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY centro, edificio, punto, tarea
    """, (centro_filtro,))

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
    ok = len(df[df["estado"] == "OK"]) if not df.empty and "estado" in df.columns else 0
    no_ok = total - ok
    cumplimiento = round((ok / total) * 100, 2) if total else 0

    fecha_informe = datetime.now().strftime("%d/%m/%Y %H:%M")

    contenido.append(Paragraph("LIBRO DE MANTENIMIENTO Y CONTROL DE LEGIONELLA", styles["Title"]))
    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph(f"<b>Centro:</b> {centro_filtro}", styles["Normal"]))
    contenido.append(Paragraph("<b>Centro titular:</b> Loreto Abat Oliba", styles["Normal"]))
    contenido.append(Paragraph("<b>Instalaciones:</b> ACS / AFCH / puntos terminales / acumuladores / retornos", styles["Normal"]))
    contenido.append(Paragraph(f"<b>Periodo revisado:</b> {fecha_inicio.strftime('%d/%m/%Y')} a {fecha_fin.strftime('%d/%m/%Y')}", styles["Normal"]))
    contenido.append(Paragraph(f"<b>Fecha de emisión:</b> {fecha_informe}", styles["Normal"]))
    contenido.append(Paragraph("<b>Responsable mantenimiento:</b> Departamento de Mantenimiento", styles["Normal"]))
    contenido.append(Spacer(1, 24))

    contenido.append(Paragraph(
        "Este documento recoge el registro de mantenimiento, planificación, controles realizados, "
        "resultados, incidencias y trazabilidad de las actuaciones de control de Legionella registradas "
        "en el sistema de mantenimiento.",
        styles["Normal"]
    ))

    contenido.append(Spacer(1, 22))

    contenido.append(Paragraph("Índice del libro", styles["Heading2"]))
    indice = [
        ["1", "Datos generales de la instalación"],
        ["2", "Programa de mantenimiento y controles"],
        ["3", "Puntos de control registrados"],
        ["4", "Resumen del periodo"],
        ["5", "Registro de controles realizados"],
        ["6", "Incidencias y acciones correctoras"],
        ["7", "Observaciones y trazabilidad"],
    ]

    tabla_indice = Table(indice, colWidths=[40, 430])
    tabla_indice.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    contenido.append(tabla_indice)
    contenido.append(Spacer(1, 20))

    contenido.append(Paragraph("1. Datos generales de la instalación", styles["Heading2"]))

    edificios_detectados = (
        " / ".join(sorted(df_puntos["edificio"].dropna().astype(str).unique().tolist()))
        if not df_puntos.empty
        else "No especificado"
    )

    datos_generales = [
        ["Centro", centro_filtro],
        ["Centro titular", "Loreto Abat Oliba"],
        ["Edificios", edificios_detectados],
        ["Tipo de instalación", "ACS / AFCH / Solar / puntos terminales"],
        ["Tipo de documento", "Libro de mantenimiento y control de Legionella"],
        ["Periodo", f"{fecha_inicio.strftime('%d/%m/%Y')} a {fecha_fin.strftime('%d/%m/%Y')}"],
        ["Fecha emisión", fecha_informe],
    ]

    tabla_datos = Table(datos_generales, colWidths=[140, 340])
    tabla_datos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
    ]))
    contenido.append(tabla_datos)
    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph("2. Programa de mantenimiento y controles", styles["Heading2"]))

    programa = [
        ["Control", "Frecuencia", "Valor / criterio correcto"],
        ["Temperatura acumulador", "Según planificación", "≥ 60 ºC"],
        ["Temperatura retorno", "Según planificación", "≥ 50 ºC"],
        ["Cloro residual", "Según planificación", "0,2 - 1,0 mg/L"],
        ["Temperatura punto terminal", "Según planificación", "Registro de temperatura"],
        ["Purga", "Según planificación", "Realizada"],
        ["Revisión visual", "Según planificación", "Correcta / sin anomalías"],
    ]

    tabla_programa = Table(programa, colWidths=[160, 130, 190])
    tabla_programa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    contenido.append(tabla_programa)
    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph("3. Puntos de control registrados", styles["Heading2"]))

    if df_puntos.empty:
        contenido.append(Paragraph("No constan puntos de control registrados.", styles["Normal"]))
    else:
        tabla_puntos = [["Centro", "Edificio", "Instalación", "Tipo", "Punto", "Ubicación"]]

        for _, row in df_puntos.head(80).iterrows():
            tabla_puntos.append([
                limpiar_pdf(row.get("centro", ""), 18),
                limpiar_pdf(row.get("edificio", ""), 22),
                limpiar_pdf(row.get("instalacion", ""), 16),
                limpiar_pdf(row.get("tipo_punto", ""), 16),
                limpiar_pdf(row.get("nombre_punto", ""), 28),
                limpiar_pdf(row.get("ubicacion", ""), 26),
            ])

        tabla_p = Table(tabla_puntos, colWidths=[60, 78, 65, 65, 120, 92])
        tabla_p.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        contenido.append(tabla_p)

    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph("4. Resumen del periodo", styles["Heading2"]))

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

    contenido.append(Paragraph("Planificación activa", styles["Heading3"]))

    if df_plan.empty:
        contenido.append(Paragraph("No consta planificación activa registrada.", styles["Normal"]))
    else:
        tabla_plan = [["Centro", "Edificio", "Punto", "Tarea", "Frecuencia", "Próxima", "Operario"]]

        for _, row in df_plan.head(70).iterrows():
            tabla_plan.append([
                limpiar_pdf(row.get("centro", ""), 18),
                limpiar_pdf(row.get("edificio", ""), 18),
                limpiar_pdf(row.get("punto", ""), 25),
                limpiar_pdf(row.get("tarea", ""), 25),
                limpiar_pdf(row.get("frecuencia", ""), 16),
                limpiar_pdf(row.get("proxima_fecha", ""), 12),
                limpiar_pdf(row.get("operario", ""), 20),
            ])

        tabla_pl = Table(tabla_plan, colWidths=[60, 65, 95, 95, 60, 55, 70])
        tabla_pl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        contenido.append(tabla_pl)

    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph("5. Registro de controles realizados", styles["Heading2"]))

    if df.empty:
        contenido.append(Paragraph("No constan controles registrados en el periodo seleccionado.", styles["Normal"]))
    else:
        tabla_data = [["Fecha", "Centro", "Edificio", "Punto", "Tarea", "Valor", "Estado"]]

        for _, row in df.head(100).iterrows():
            valor = "" if pd.isna(row["valor"]) else str(row["valor"])
            unidad = "" if pd.isna(row["unidad"]) else str(row["unidad"])

            tabla_data.append([
                limpiar_pdf(str(row["fecha"])[:10]),
                limpiar_pdf(row["centro"], 18),
                limpiar_pdf(row["edificio"], 20),
                limpiar_pdf(row["punto"], 26),
                limpiar_pdf(row["tarea"], 26),
                limpiar_pdf(f"{valor} {unidad}", 14),
                limpiar_pdf(row["estado"], 12)
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

    contenido.append(Paragraph("6. Incidencias y acciones correctoras", styles["Heading2"]))

    if df_inc.empty:
        contenido.append(Paragraph("No constan incidencias registradas en el periodo.", styles["Normal"]))
    else:
        tabla_inc = [["Fecha", "Centro", "Punto", "Tarea", "Estado", "Descripción"]]

        for _, row in df_inc.head(60).iterrows():
            tabla_inc.append([
                limpiar_pdf(str(row["fecha_apertura"])[:10]),
                limpiar_pdf(row["centro"], 18),
                limpiar_pdf(row["punto"], 24),
                limpiar_pdf(row["tarea"], 24),
                limpiar_pdf(row["estado"], 14),
                limpiar_pdf(row["descripcion"], 50),
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

    contenido.append(Paragraph("7. Observaciones y trazabilidad", styles["Heading2"]))
    contenido.append(Paragraph(
        "Libro generado automáticamente desde el sistema de mantenimiento. "
        "Los datos incluidos proceden de los registros introducidos en la aplicación: "
        "temperaturas, cloro residual, purgas, revisiones visuales, planificación, incidencias "
        "y acciones correctoras asociadas.",
        styles["Normal"]
    ))

    contenido.append(Spacer(1, 30))
    contenido.append(Paragraph("<b>Firma / Responsable:</b> ________________________________", styles["Normal"]))
    contenido.append(Spacer(1, 10))
    contenido.append(Paragraph("<b>Fecha:</b> ________________________________", styles["Normal"]))

    doc.build(contenido)

    st.download_button(
        f"📘 Descargar libro mantenimiento {centro_filtro}",
        data=buffer.getvalue(),
        file_name=f"libro_mantenimiento_legionella_{centro_filtro.replace(' ', '_')}_{fecha_inicio_txt}_a_{fecha_fin_txt}.pdf",
        mime="application/pdf"
    )
def crear_tarea_legionella_manual(
    centro,
    edificio,
    instalacion,
    punto,
    tarea,
    frecuencia_dias,
    unidad,
    operario,
    generar_ot
):
    ejecutar("""
        INSERT INTO legionella_tareas
        (centro, edificio, instalacion, punto, tarea, tipo_control,
         frecuencia, frecuencia_dias, unidad, fecha_inicio, ultima_fecha,
         proxima_fecha, operario, activo, generar_ot, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 1, ?, ?)
    """, (
        centro,
        edificio,
        instalacion,
        punto,
        tarea,
        tarea,
        f"{int(frecuencia_dias)} días",
        int(frecuencia_dias),
        unidad,
        date.today().strftime("%Y-%m-%d"),
        date.today().strftime("%Y-%m-%d"),
        operario,
        1 if generar_ot else 0,
        "Tarea creada manualmente"
    ))

def actualizar_punto_legionella(
    punto_id,
    centro,
    edificio,
    instalacion,
    tipo_punto,
    nombre_punto,
    ubicacion,
    observaciones,
    activo
):
    ejecutar("""
        UPDATE legionella_puntos
        SET centro = ?,
            edificio = ?,
            instalacion = ?,
            tipo_punto = ?,
            nombre_punto = ?,
            ubicacion = ?,
            observaciones = ?,
            activo = ?
        WHERE id = ?
    """, (
        centro,
        edificio,
        instalacion,
        tipo_punto,
        nombre_punto,
        ubicacion,
        observaciones,
        1 if activo else 0,
        int(punto_id)
    ))


def limpiar_puntos_duplicados_legionella():
    df = leer_df("""
        SELECT id, centro, edificio, instalacion, tipo_punto, nombre_punto, ubicacion
        FROM legionella_puntos
        ORDER BY id
    """)

    if df.empty:
        return 0

    df["clave"] = (
        df["centro"].astype(str).str.strip().str.lower() + "|" +
        df["edificio"].astype(str).str.strip().str.lower() + "|" +
        df["instalacion"].astype(str).str.strip().str.lower() + "|" +
        df["tipo_punto"].astype(str).str.strip().str.lower() + "|" +
        df["nombre_punto"].astype(str).str.strip().str.lower() + "|" +
        df["ubicacion"].astype(str).str.strip().str.lower()
    )

    duplicados = df[df.duplicated("clave", keep="first")]

    if duplicados.empty:
        return 0

    ids = duplicados["id"].tolist()

    for punto_id in ids:
        ejecutar("""
            DELETE FROM legionella_puntos
            WHERE id = ?
        """, (int(punto_id),))

    return len(ids)

def pantalla_legionella():
    asegurar_columnas_planificacion_legionella()

    puntos_creados = sembrar_puntos_si_vacio()

    if puntos_creados:
        st.success(f"Se han creado {puntos_creados} puntos automáticos de Legionella que faltaban.")

    ots_creadas, mensaje = generar_ots_legionella_si_toca()

    if ots_creadas > 0:
        st.success(mensaje)
    else:
        st.info(mensaje)

    st.subheader("💧 Legionella")

    with st.expander("🛡️ Mantenimiento de datos Legionella", expanded=False):
        st.caption("Limpia registros antiguos incompletos. No toca los registros correctos.")

        if st.button("🧹 Limpiar registros inválidos (None)", use_container_width=True):
            try:
                registros_borrados, incidencias_borradas = limpiar_registros_invalidos_legionella()
                st.success(
                    f"Limpieza finalizada. Registros eliminados: {registros_borrados}. "
                    f"Incidencias eliminadas: {incidencias_borradas}."
                )
                st.rerun()
            except Exception as e:
                st.error(f"Error al limpiar registros inválidos: {e}")

    st.caption("Control ACS / AFCH · temperaturas · cloro · purgas · incidencias · histórico")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "📋 Registrar control",
        "🗓️ Planificación",
        "⚙️ Puntos",
        "📅 Próximos / estado",
        "📚 Histórico",
        "🚨 Incidencias",
        "📄 Informe",
    ]
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

        tareas = tareas_por_tipo_punto(tipo_punto)

        tarea = st.selectbox("Tarea", tareas)

        if tarea == "Temperatura acumulador":
            tipo_control = "Temperatura acumulador"
            unidad = "ºC"
            valor = st.number_input("Temperatura acumulador ºC", min_value=0.0, max_value=100.0, value=60.0, step=0.1)
            valor_2 = None

        elif tarea == "Temperatura impulsión ACS":
            tipo_control = "Temperatura impulsión ACS"
            unidad = "ºC"
            valor = st.number_input("Temperatura impulsión ACS ºC", min_value=0.0, max_value=100.0, value=55.0, step=0.1)
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
            tipo_control = tarea
            unidad = "Realizado/No realizado"
            realizado = st.radio("Resultado", ["Realizado", "No realizado"], horizontal=True)
            valor = 1 if realizado == "Realizado" else 0
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
            elif estado == "ERROR":
                st.error(resultado)
            else:
                st.warning(f"Control guardado con incidencia: {resultado}")

    with tab2:
        st.markdown("### 🗓️ Planificación Legionella")

        st.info(
            "Desde aquí puedes preparar los controles para septiembre, cambiar frecuencias "
            "y generar órdenes automáticamente cuando toque."
        )

        fecha_inicio_plan = st.date_input(
            "Fecha inicial de planificación",
            value=date(2026, 9, 1),
            key="legionella_fecha_inicio_plan"
        )

        col_plan1, col_plan2 = st.columns(2)

        with col_plan1:
            if st.button("🧱 Crear planificación automática desde puntos", use_container_width=True):
                creadas = sembrar_planificacion_legionella(fecha_inicio_plan.strftime("%Y-%m-%d"))

                if creadas > 0:
                    st.success(f"Se han creado {creadas} controles planificados.")
                else:
                    st.info("No se han creado controles nuevos. Ya existían o faltan puntos.")

                st.rerun()

        with col_plan2:
            if st.button("⚙️ Generar OT que tocan hoy", use_container_width=True):
                creadas, mensaje = generar_ots_legionella_planificadas()

                if creadas > 0:
                    st.success(mensaje)
                else:
                    st.info(mensaje)

                st.rerun()

        df_plan = obtener_planificacion_legionella()

        if df_plan.empty:
            st.warning("Todavía no hay planificación de Legionella.")
        else:
            df_plan["proxima_fecha_dt"] = pd.to_datetime(df_plan["proxima_fecha"], errors="coerce")
            df_plan["estado_control"] = df_plan["proxima_fecha_dt"].apply(
                lambda x: calcular_estado_control(x) if pd.notna(x) else "Sin fecha"
            )

            total = len(df_plan)
            toca = len(df_plan[df_plan["estado_control"] == "🔴 TOCA"])
            proximo = len(df_plan[df_plan["estado_control"] == "🟠 PRÓXIMO"])
            ok = len(df_plan[df_plan["estado_control"] == "🟢 OK"])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Planificados", total)
            c2.metric("🔴 Toca", toca)
            c3.metric("🟠 Próximo", proximo)
            c4.metric("🟢 OK", ok)

            centro_f = st.selectbox(
                "Filtrar centro planificación",
                ["Todos"] + sorted(df_plan["centro"].dropna().unique().tolist()),
                key="filtro_plan_centro_leg"
            )

            df_filtrado = df_plan.copy()

            if centro_f != "Todos":
                df_filtrado = df_filtrado[df_filtrado["centro"] == centro_f]

            st.markdown("### Controles planificados")

            for _, row in df_filtrado.iterrows():
                estado = "Activo" if int(row["activo"] or 0) == 1 else "Inactivo"
                titulo = (
                    f"{row['estado_control']} · {row['centro']} · {row['edificio']} · "
                    f"{row['punto']} · {row['tarea']} · {row['proxima_fecha']} · {estado}"
                )

                with st.expander(titulo, expanded=False):
                    c1, c2 = st.columns(2)

                    with c1:
                        frecuencia = st.number_input(
                            "Frecuencia en días",
                            min_value=1,
                            max_value=365,
                            value=int(row["frecuencia_dias"] or 30),
                            step=1,
                            key=f"freq_leg_{row['id']}"
                        )

                        fecha_base = date.today()
                        if row["proxima_fecha"]:
                            try:
                                fecha_base = pd.to_datetime(row["proxima_fecha"]).date()
                            except Exception:
                                fecha_base = date.today()

                        proxima_fecha = st.date_input(
                            "Próxima fecha",
                            value=fecha_base,
                            key=f"prox_leg_{row['id']}"
                        )

                    with c2:
                        operario = st.selectbox(
                            "Operario",
                            OPERARIOS,
                            index=OPERARIOS.index(row["operario"]) if row["operario"] in OPERARIOS else 0,
                            key=f"operario_plan_leg_{row['id']}"
                        )

                        if operario == "Otro":
                            operario = st.text_input(
                                "Nombre operario",
                                value=str(row["operario"] or ""),
                                key=f"operario_otro_plan_leg_{row['id']}"
                            )

                        generar_ot = st.checkbox(
                            "Generar OT cuando toque",
                            value=bool(row["generar_ot"]),
                            key=f"generar_ot_leg_{row['id']}"
                        )

                        activo = st.checkbox(
                            "Activo",
                            value=bool(row["activo"]),
                            key=f"activo_leg_{row['id']}"
                        )

                    if st.button("💾 Guardar cambios", key=f"guardar_plan_leg_{row['id']}", use_container_width=True):
                        actualizar_plan_legionella(
                            row["id"],
                            frecuencia,
                            proxima_fecha.strftime("%Y-%m-%d"),
                            operario,
                            generar_ot,
                            activo
                        )

                        st.success("Planificación actualizada.")
                        st.rerun()

                    st.markdown("---")

                    if st.button(
                        "🗑️ Borrar planificación",
                        key=f"borrar_plan_leg_{row['id']}",
                        use_container_width=True
                    ):
                        borrar_plan_legionella(row["id"])

                        st.warning(
                            f"Planificación eliminada: "
                            f"{row['punto']} - {row['tarea']}"
                        )

                        st.rerun()

            st.markdown("### Vista rápida")

            df_mostrar = df_filtrado.copy()
            st.dataframe(
                df_mostrar[
                    [
                        "estado_control",
                        "centro",
                        "edificio",
                        "punto",
                        "tarea",
                        "frecuencia_dias",
                        "proxima_fecha",
                        "operario",
                        "activo",
                        "generar_ot",
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

    with tab3:
        st.markdown("### ⚙️ Gestión de puntos Legionella")

        st.info(
            "Desde aquí puedes crear, editar, activar/desactivar puntos, crear tareas manuales "
            "y limpiar duplicados."
        )

        with st.expander("➕ Crear nuevo punto", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                centro_nuevo = st.selectbox(
                    "Centro",
                    list(CENTROS.keys()),
                    key="nuevo_punto_centro"
                )

                edificios_disponibles = list(CENTROS.get(centro_nuevo, {}).keys())

                edificio_nuevo = st.selectbox(
                    "Edificio / zona",
                    edificios_disponibles + ["Otro"],
                    key="nuevo_punto_edificio"
                )

                if edificio_nuevo == "Otro":
                    edificio_nuevo = st.text_input(
                        "Nombre edificio / zona",
                        key="nuevo_punto_edificio_otro"
                    )

                instalacion_nueva = st.selectbox(
                    "Instalación",
                    ["ACS", "AFCH", "Solar", "Otro"],
                    key="nuevo_punto_instalacion"
                )

                if instalacion_nueva == "Otro":
                    instalacion_nueva = st.text_input(
                        "Nombre instalación",
                        key="nuevo_punto_instalacion_otro"
                    )

            with col2:
                tipo_punto_nuevo = st.selectbox(
                    "Tipo de punto",
                    [
                        "acumulador",
                        "acumulador_solar",
                        "retorno",
                        "grifo",
                        "ducha",
                        "deposito",
                        "otro",
                    ],
                    key="nuevo_punto_tipo"
                )

                nombre_punto_nuevo = st.text_input(
                    "Nombre del punto",
                    placeholder="Ejemplo: Acumulador ACS Principal",
                    key="nuevo_punto_nombre"
                )

                ubicacion_nueva = st.text_input(
                    "Ubicación",
                    placeholder="Ejemplo: Cuarto calderas",
                    key="nuevo_punto_ubicacion"
                )

            observaciones_nueva = st.text_area(
                "Observaciones",
                key="nuevo_punto_observaciones"
            )

            if st.button("💾 Crear punto Legionella", use_container_width=True):
                if not centro_nuevo or not edificio_nuevo or not instalacion_nueva or not tipo_punto_nuevo or not nombre_punto_nuevo:
                    st.error("Faltan datos obligatorios.")
                else:
                    crear_punto_legionella(
                        centro_nuevo,
                        edificio_nuevo,
                        instalacion_nueva,
                        tipo_punto_nuevo,
                        nombre_punto_nuevo,
                        ubicacion_nueva,
                        observaciones_nueva
                    )

                    st.success("Punto creado correctamente.")
                    st.rerun()

        with st.expander("➕ Crear control / tarea manual", expanded=False):
            puntos_tarea = obtener_puntos_legionella_admin()

            if puntos_tarea.empty:
                st.info("Primero debes crear algún punto.")
            else:
                centro_tarea = st.selectbox(
                    "Centro",
                    sorted(puntos_tarea["centro"].dropna().astype(str).unique().tolist()),
                    key="tarea_manual_centro"
                )

                df_centro = puntos_tarea[puntos_tarea["centro"] == centro_tarea]

                edificio_tarea = st.selectbox(
                    "Edificio / zona",
                    sorted(df_centro["edificio"].dropna().astype(str).unique().tolist()),
                    key="tarea_manual_edificio"
                )

                df_edificio = df_centro[df_centro["edificio"] == edificio_tarea]

                punto_tarea = st.selectbox(
                    "Punto",
                    sorted(df_edificio["nombre_punto"].dropna().astype(str).unique().tolist()),
                    key="tarea_manual_punto"
                )

                fila_punto = df_edificio[df_edificio["nombre_punto"] == punto_tarea].iloc[0]

                tarea_manual = st.text_input(
                    "Nombre del control / tarea",
                    value="Limpieza interior acumulador",
                    key="tarea_manual_nombre"
                )

                frecuencia_manual = st.number_input(
                    "Frecuencia en días",
                    min_value=1,
                    max_value=730,
                    value=365,
                    step=1,
                    key="tarea_manual_frecuencia"
                )

                unidad_manual = st.selectbox(
                    "Unidad",
                    ["Realizado/No realizado", "OK/KO", "ºC", "mg/L", "Otra"],
                    key="tarea_manual_unidad"
                )

                operario_manual = st.selectbox(
                    "Operario",
                    OPERARIOS,
                    index=OPERARIOS.index(operario_por_centro(centro_tarea))
                    if operario_por_centro(centro_tarea) in OPERARIOS else 0,
                    key="tarea_manual_operario"
                )

                generar_ot_manual = st.checkbox(
                    "Generar OT cuando toque",
                    value=True,
                    key="tarea_manual_generar_ot"
                )

                if st.button("💾 Crear control / tarea manual", use_container_width=True):
                    crear_tarea_legionella_manual(
                        centro_tarea,
                        edificio_tarea,
                        fila_punto["instalacion"],
                        punto_tarea,
                        tarea_manual,
                        frecuencia_manual,
                        unidad_manual,
                        operario_manual,
                        generar_ot_manual
                    )

                    st.success("Control / tarea manual creado correctamente.")
                    st.rerun()

        st.markdown("---")

        col_dup1, col_dup2 = st.columns(2)

        with col_dup1:
            if st.button("🧹 Limpiar puntos duplicados", use_container_width=True):
                eliminados = limpiar_puntos_duplicados_legionella()

                if eliminados > 0:
                    st.success(f"Se han eliminado {eliminados} puntos duplicados.")
                    st.rerun()
                else:
                    st.info("No se han encontrado puntos duplicados.")

        st.markdown("### Puntos existentes")

        puntos_admin = obtener_puntos_legionella_admin()

        if puntos_admin.empty:
            st.info("No hay puntos registrados.")
        else:
            centro_filtro_puntos = st.selectbox(
                "Filtrar centro",
                ["Todos"] + sorted(puntos_admin["centro"].dropna().astype(str).unique().tolist()),
                key="filtro_admin_puntos_leg"
            )

            df_puntos_admin = puntos_admin.copy()

            if centro_filtro_puntos != "Todos":
                df_puntos_admin = df_puntos_admin[df_puntos_admin["centro"] == centro_filtro_puntos]

            for _, row in df_puntos_admin.iterrows():
                estado_txt = "Activo" if int(row["activo"] or 0) == 1 else "Inactivo"

                titulo = (
                    f"{estado_txt} · {row['centro']} · {row['edificio']} · "
                    f"{row['instalacion']} · {row['nombre_punto']}"
                )

                with st.expander(titulo, expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        centro_edit = st.selectbox(
                            "Centro",
                            list(CENTROS.keys()),
                            index=list(CENTROS.keys()).index(row["centro"])
                            if row["centro"] in list(CENTROS.keys()) else 0,
                            key=f"edit_centro_punto_{row['id']}"
                        )

                        edificios_edit = list(CENTROS.get(centro_edit, {}).keys())

                        edificio_edit = st.selectbox(
                            "Edificio / zona",
                            edificios_edit + ["Otro"],
                            index=(edificios_edit + ["Otro"]).index(row["edificio"])
                            if row["edificio"] in edificios_edit + ["Otro"] else len(edificios_edit),
                            key=f"edit_edificio_punto_{row['id']}"
                        )

                        if edificio_edit == "Otro":
                            edificio_edit = st.text_input(
                                "Nombre edificio / zona",
                                value=str(row["edificio"] or ""),
                                key=f"edit_edificio_otro_punto_{row['id']}"
                            )

                        instalacion_edit = st.text_input(
                            "Instalación",
                            value=str(row["instalacion"] or ""),
                            key=f"edit_instalacion_punto_{row['id']}"
                        )

                        tipo_edit = st.selectbox(
                            "Tipo de punto",
                            [
                                "acumulador",
                                "acumulador_solar",
                                "retorno",
                                "grifo",
                                "ducha",
                                "deposito",
                                "otro",
                            ],
                            index=[
                                "acumulador",
                                "acumulador_solar",
                                "retorno",
                                "grifo",
                                "ducha",
                                "deposito",
                                "otro",
                            ].index(row["tipo_punto"]) if row["tipo_punto"] in [
                                "acumulador",
                                "acumulador_solar",
                                "retorno",
                                "grifo",
                                "ducha",
                                "deposito",
                                "otro",
                            ] else 0,
                            key=f"edit_tipo_punto_{row['id']}"
                        )

                    with col2:
                        nombre_edit = st.text_input(
                            "Nombre punto",
                            value=str(row["nombre_punto"] or ""),
                            key=f"edit_nombre_punto_{row['id']}"
                        )

                        ubicacion_edit = st.text_input(
                            "Ubicación",
                            value=str(row["ubicacion"] or ""),
                            key=f"edit_ubicacion_punto_{row['id']}"
                        )

                        observaciones_edit = st.text_area(
                            "Observaciones",
                            value=str(row["observaciones"] or ""),
                            key=f"edit_observaciones_punto_{row['id']}"
                        )

                        activo_edit = st.checkbox(
                            "Punto activo",
                            value=bool(row["activo"]),
                            key=f"edit_activo_punto_{row['id']}"
                        )

                    if st.button(
                        "💾 Guardar cambios del punto",
                        key=f"guardar_edicion_punto_{row['id']}",
                        use_container_width=True
                    ):
                        actualizar_punto_legionella(
                            row["id"],
                            centro_edit,
                            edificio_edit,
                            instalacion_edit,
                            tipo_edit,
                            nombre_edit,
                            ubicacion_edit,
                            observaciones_edit,
                            activo_edit
                        )

                        st.success("Punto actualizado correctamente.")
                        st.rerun()

            with st.expander("📋 Vista rápida de puntos", expanded=False):
                st.dataframe(
                    df_puntos_admin,
                    use_container_width=True,
                    hide_index=True
                )

    with tab4:
        st.markdown("### Próximos controles / estado")

        df_plan = obtener_planificacion_legionella()

        if not df_plan.empty:
            df_plan["proxima_fecha_dt"] = pd.to_datetime(df_plan["proxima_fecha"], errors="coerce")
            df_plan["estado_control"] = df_plan["proxima_fecha_dt"].apply(
                lambda x: calcular_estado_control(x) if pd.notna(x) else "Sin fecha"
            )

            total = len(df_plan)
            toca = len(df_plan[df_plan["estado_control"] == "🔴 TOCA"])
            proximo = len(df_plan[df_plan["estado_control"] == "🟠 PRÓXIMO"])
            ok = len(df_plan[df_plan["estado_control"] == "🟢 OK"])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Controles", total)
            c2.metric("🔴 Toca", toca)
            c3.metric("🟠 Próximo", proximo)
            c4.metric("🟢 OK", ok)

            st.dataframe(
                df_plan[
                    [
                        "estado_control",
                        "centro",
                        "edificio",
                        "punto",
                        "tarea",
                        "frecuencia_dias",
                        "proxima_fecha",
                        "operario",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:
            df = leer_df("""
                SELECT fecha, centro, edificio, instalacion, punto, tarea, estado, resultado, operario
                FROM legionella_registros
                WHERE centro IS NOT NULL
                  AND edificio IS NOT NULL
                  AND punto IS NOT NULL
                  AND tarea IS NOT NULL
                ORDER BY fecha DESC, id DESC
            """)

            if df.empty:
                st.info("Todavía no hay controles registrados ni planificación creada.")
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

    with tab5:
        st.markdown("### Histórico de controles")

        st.warning("Zona de pruebas: puedes borrar el histórico de controles de Legionella.")

        confirmar_borrado = st.checkbox(
            "Confirmo que quiero borrar el histórico de controles Legionella",
            key="confirmar_borrar_historico_legionella"
        )

        if st.button("🗑️ Borrar histórico de controles", use_container_width=True):
            if not confirmar_borrado:
                st.error("Marca primero la casilla de confirmación.")
            else:
                try:
                    ejecutar("DELETE FROM legionella_registros")
                    st.success("Histórico de controles eliminado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al borrar histórico: {e}")

        st.markdown("---")

        df = leer_df("""
            SELECT fecha, centro, edificio, instalacion, punto, tarea, tipo_control,
                   valor, valor_2, unidad, estado, resultado, operario, observaciones
            FROM legionella_registros
            WHERE centro IS NOT NULL
              AND edificio IS NOT NULL
              AND punto IS NOT NULL
              AND tarea IS NOT NULL
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

    with tab6:
        st.markdown("### Incidencias Legionella")

        df = leer_df("""
            SELECT id, fecha_apertura, centro, edificio, punto, tarea, descripcion,
                   estado, prioridad, operario, fecha_cierre, observaciones_cierre
            FROM legionella_incidencias
            WHERE centro IS NOT NULL
              AND edificio IS NOT NULL
              AND punto IS NOT NULL
              AND tarea IS NOT NULL
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

    with tab7:
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
            col_p9, col_p22 = st.columns(2)

            with col_p9:
                if st.button("📘 Generar libro Pearson 9", use_container_width=True):
                    generar_informe_legionella(
                        fecha_inicio,
                        fecha_fin,
                        "Pearson 9"
                    )

            with col_p22:
                if st.button("📘 Generar libro Pearson 22", use_container_width=True):
                    generar_informe_legionella(
                        fecha_inicio,
                        fecha_fin,
                        "Pearson 22"
                    )
