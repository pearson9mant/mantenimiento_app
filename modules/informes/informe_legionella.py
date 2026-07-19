from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from database.db import conectar, _sql

def leer_df(query, params=()):
    conn = conectar()

    try:
        return pd.read_sql_query(
            _sql(query),
            conn,
            params=params
        )
    finally:
        conn.close()


def generar_informe_legionella(fecha_inicio, fecha_fin, centro_filtro):
    
    fecha_inicio_txt = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_txt = fecha_fin.strftime("%Y-%m-%d")

    def limpiar_pdf(texto, max_len=None):
        texto = "" if pd.isna(texto) else str(texto)
        texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if max_len:
            texto = texto[:max_len]
        return texto

    def texto_valores(row):
        tarea = str(row.get("tarea", ""))

        if tarea == "Control AFS":
            return f"AFS: {row.get('valor', '')} ºC / Cloro: {row.get('valor_2', '')} mg/L"

        if tarea == "Control ACS terminal":
            return f"ACS terminal: {row.get('valor', '')} ºC"

        if tarea == "Control punto terminal completo":
            return (
                f"AFS: {row.get('valor', '')} ºC / "
                f"Cloro: {row.get('valor_2', '')} mg/L / "
                f"ACS: {row.get('valor_3', '')} ºC"
            )

        if tarea == "Control sala ACS":
            return (
                f"Acum.: {row.get('valor', '')} ºC / "
                f"Imp.: {row.get('valor_2', '')} ºC / "
                f"Ret.: {row.get('valor_3', '')} ºC"
            )

        if tarea == "Control válvula termostática":
            return (
                f"Entrada ACS: {row.get('valor', '')} ºC / "
                f"Salida mezclada: {row.get('valor_2', '')} ºC"
            )

        unidad = "" if pd.isna(row.get("unidad", "")) else str(row.get("unidad", ""))
        valor = "" if pd.isna(row.get("valor", "")) else str(row.get("valor", ""))
        return f"{valor} {unidad}".strip()

    def contar_puntos(tipo_punto=None, instalacion=None, tipo_control=None):
        if df_puntos.empty:
            return 0

        df_tmp = df_puntos.copy()

        if tipo_punto:
            df_tmp = df_tmp[
                df_tmp["tipo_punto"].astype(str).str.lower().str.contains(
                    str(tipo_punto).lower(),
                    na=False
                )
            ]

        if instalacion:
            df_tmp = df_tmp[
                df_tmp["instalacion"].astype(str).str.lower().str.contains(
                    str(instalacion).lower(),
                    na=False
                )
            ]

        if tipo_control:
            df_tmp = df_tmp[
                df_tmp["tipo_control_punto"].astype(str).str.lower().str.contains(
                    str(tipo_control).lower(),
                    na=False
                )
            ]

        return len(df_tmp)

    def contar_tareas(texto):
        if df_plan.empty:
            return 0

        return len(
            df_plan[
                df_plan["tarea"].astype(str).str.lower().str.contains(
                    str(texto).lower(),
                    na=False
                )
            ]
        )

    def contar_registros(texto):
        if df.empty:
            return 0

        return len(
            df[
                df["tarea"].astype(str).str.lower().str.contains(
                    str(texto).lower(),
                    na=False
                )
            ]
        )

    df = leer_df("""
        SELECT fecha, centro, edificio, instalacion, punto, tarea, valor, valor_2, valor_3,
               unidad, estado, resultado, operario, observaciones
        FROM legionella_registros
        WHERE date(fecha) BETWEEN ? AND ?
          AND centro = ?
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY fecha DESC, id DESC
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
        SELECT centro, edificio, instalacion, tipo_punto, tipo_control_punto,
               nombre_punto, ubicacion, ubicacion_exacta, numero_terminales, activo
        FROM legionella_puntos
        WHERE centro = ?
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND nombre_punto IS NOT NULL
        ORDER BY centro, edificio, instalacion, nombre_punto
    """, (centro_filtro,))

    df_plan = leer_df("""
        SELECT centro, edificio, instalacion, punto, tarea, frecuencia, frecuencia_dias,
               proxima_fecha, operario, activo, generar_ot, consigna_minima, controla_consigna
        FROM legionella_tareas
        WHERE centro = ?
          AND activo = 1
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY centro, edificio, punto, tarea
    """, (centro_filtro,))

    try:
        df_inf = leer_df("""
            SELECT tipo_informe, empresa, centro, edificio, instalacion, punto,
                   fecha_actuacion, fecha_informe, resultado, numero_informe,
                   proxima_fecha, observaciones
            FROM legionella_informes
            WHERE centro = ?
              AND date(fecha_informe) BETWEEN ? AND ?
            ORDER BY fecha_informe DESC, id DESC
        """, (centro_filtro, fecha_inicio_txt, fecha_fin_txt))
    except Exception:
        df_inf = pd.DataFrame()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    contenido = []

    total = len(df)
    ok = len(df[df["estado"] == "OK"]) if not df.empty and "estado" in df.columns else 0
    no_ok = total - ok
    cumplimiento = round((ok / total) * 100, 2) if total else 0
    fecha_informe = datetime.now().strftime("%d/%m/%Y %H:%M")

    incidencias_abiertas = 0
    incidencias_cerradas = 0

    if not df_inc.empty:
        incidencias_abiertas = len(
            df_inc[
                ~df_inc["estado"].astype(str).str.lower().isin(
                    ["cerrada", "cerrado", "finalizada", "finalizado"]
                )
            ]
        )
        incidencias_cerradas = len(df_inc) - incidencias_abiertas

    puntos_acs = contar_puntos(instalacion="ACS")
    puntos_afs = contar_puntos(instalacion="AFCH") + contar_puntos(instalacion="AFS")
    depositos_solares = contar_puntos(instalacion="Solar")
    puntos_ducha = contar_puntos(tipo_punto="ducha")
    puntos_vtm = contar_puntos(tipo_control="válvula")
    terminales_ducha = 0

    if not df_puntos.empty and "numero_terminales" in df_puntos.columns:
        try:
            terminales_ducha = int(
                df_puntos[
                    df_puntos["tipo_punto"].astype(str).str.lower().str.contains("ducha", na=False)
                ]["numero_terminales"].fillna(0).astype(int).sum()
            )
        except Exception:
            terminales_ducha = 0

    controles_sala_acs = contar_tareas("Control sala ACS")
    controles_afs = contar_tareas("Control AFS")
    controles_terminales = contar_tareas("Control punto terminal completo")
    controles_vtm = contar_tareas("Control válvula termostática")

    # ---------------------------------------------------------
    # PORTADA PROFESIONAL
    # ---------------------------------------------------------
    
    estilo_marca = styles["Normal"].clone("MarcaPortada")
    estilo_marca.fontName = "Helvetica-Bold"
    estilo_marca.fontSize = 11
    estilo_marca.leading = 14
    estilo_marca.textColor = colors.HexColor("#16324F")
    estilo_marca.alignment = 1
    
    estilo_titulo_portada = styles["Title"].clone("TituloPortada")
    estilo_titulo_portada.fontName = "Helvetica-Bold"
    estilo_titulo_portada.fontSize = 23
    estilo_titulo_portada.leading = 27
    estilo_titulo_portada.textColor = colors.HexColor("#16324F")
    estilo_titulo_portada.alignment = 1
    estilo_titulo_portada.spaceAfter = 8
    
    estilo_subtitulo_portada = styles["Normal"].clone("SubtituloPortada")
    estilo_subtitulo_portada.fontName = "Helvetica"
    estilo_subtitulo_portada.fontSize = 10
    estilo_subtitulo_portada.leading = 14
    estilo_subtitulo_portada.textColor = colors.HexColor("#4B5563")
    estilo_subtitulo_portada.alignment = 1
    
    estilo_texto_portada = styles["Normal"].clone("TextoPortada")
    estilo_texto_portada.fontName = "Helvetica"
    estilo_texto_portada.fontSize = 9
    estilo_texto_portada.leading = 13
    estilo_texto_portada.textColor = colors.HexColor("#374151")
    
    contenido.append(Spacer(1, 18))
    
    contenido.append(
        Table(
            [["LORETO ABAT OLIBA · SERVICIO DE MANTENIMIENTO"]],
            colWidths=[500],
            rowHeights=[32],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#16324F")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#16324F")),
            ])
        )
    )
    
    contenido.append(Spacer(1, 38))
    
    contenido.append(
        Paragraph(
            "LIBRO DE INSPECCIÓN Y<br/>CONTROL DE LEGIONELLA",
            estilo_titulo_portada
        )
    )
    
    contenido.append(Spacer(1, 10))
    
    contenido.append(
        Paragraph(
            "Programa de vigilancia, control y mantenimiento higiénico-sanitario",
            estilo_subtitulo_portada
        )
    )
    
    contenido.append(Spacer(1, 30))
    
    datos_portada = [
        [
            Paragraph("<b>Centro</b>", estilo_texto_portada),
            Paragraph(limpiar_pdf(centro_filtro), estilo_texto_portada),
        ],
        [
            Paragraph("<b>Titular</b>", estilo_texto_portada),
            Paragraph("Loreto Abat Oliba", estilo_texto_portada),
        ],
        [
            Paragraph("<b>Instalaciones</b>", estilo_texto_portada),
            Paragraph(
                "ACS · AFCH · Solar · puntos terminales · acumuladores · VTM",
                estilo_texto_portada
            ),
        ],
        [
            Paragraph("<b>Periodo revisado</b>", estilo_texto_portada),
            Paragraph(
                f"{fecha_inicio.strftime('%d/%m/%Y')} a {fecha_fin.strftime('%d/%m/%Y')}",
                estilo_texto_portada
            ),
        ],
        [
            Paragraph("<b>Fecha de emisión</b>", estilo_texto_portada),
            Paragraph(fecha_informe, estilo_texto_portada),
        ],
        [
            Paragraph("<b>Responsable</b>", estilo_texto_portada),
            Paragraph(
                "Servicio de Mantenimiento Loreto Abat Oliba",
                estilo_texto_portada
            ),
        ],
    ]
    
    tabla_portada = Table(
        datos_portada,
        colWidths=[145, 355],
        rowHeights=[30, 30, 42, 30, 30, 38]
    )
    
    tabla_portada.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF4")),
        ("BACKGROUND", (1, 0), (1, -1), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2937")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#9CA3AF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    
    contenido.append(tabla_portada)
    
    contenido.append(Spacer(1, 28))
    
    contenido.append(
        Table(
            [[
                Paragraph(
                    "Documento generado automáticamente desde el Sistema Integral de "
                    "Mantenimiento. Incluye el inventario de puntos físicos, la planificación "
                    "preventiva, los controles operacionales, las incidencias, las acciones "
                    "correctoras y los informes externos asociados al control de Legionella.",
                    estilo_texto_portada
                )
            ]],
            colWidths=[500],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6F8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C4CE")),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ])
        )
    )
    
    contenido.append(Spacer(1, 28))

    # ---------------------------------------------------------
    # RESUMEN EJECUTIVO
    # ---------------------------------------------------------
    
    estilo_kpi_titulo = styles["Normal"].clone("KpiTitulo")
    estilo_kpi_titulo.fontName = "Helvetica-Bold"
    estilo_kpi_titulo.fontSize = 8
    estilo_kpi_titulo.leading = 10
    estilo_kpi_titulo.textColor = colors.HexColor("#4B5563")
    estilo_kpi_titulo.alignment = 1
    
    estilo_kpi_valor = styles["Normal"].clone("KpiValor")
    estilo_kpi_valor.fontName = "Helvetica-Bold"
    estilo_kpi_valor.fontSize = 18
    estilo_kpi_valor.leading = 20
    estilo_kpi_valor.textColor = colors.HexColor("#16324F")
    estilo_kpi_valor.alignment = 1
    
    contenido.append(Paragraph("1. Resumen ejecutivo", styles["Heading2"]))
    contenido.append(Spacer(1, 8))
    
    kpis = [
        [
            Paragraph("CONTROLES", estilo_kpi_titulo),
            Paragraph("CORRECTOS", estilo_kpi_titulo),
            Paragraph("INCIDENCIAS", estilo_kpi_titulo),
            Paragraph("CUMPLIMIENTO", estilo_kpi_titulo),
        ],
        [
            Paragraph(str(total), estilo_kpi_valor),
            Paragraph(str(ok), estilo_kpi_valor),
            Paragraph(str(no_ok), estilo_kpi_valor),
            Paragraph(f"{cumplimiento}%", estilo_kpi_valor),
        ],
    ]
    
    tabla_kpis = Table(
        kpis,
        colWidths=[125, 125, 125, 125],
        rowHeights=[24, 42]
    )
    
    tabla_kpis.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8C4CE")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    
    contenido.append(tabla_kpis)
    contenido.append(Spacer(1, 18))
    
    contenido.append(Paragraph("1.1 Estado actual de la instalación", styles["Heading2"]))
    contenido.append(Spacer(1,8))
    
    def crear_bloque_estado(titulo, filas):
        datos = [[titulo, ""]] + filas

        tabla = Table(
            datos,
            colWidths=[300, 170],
        )

        tabla.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),

            ("GRID", (0, 1), (-1, -1), 0.35, colors.HexColor("#D0D0D0")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),

            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))

        return KeepTogether([
            tabla,
            Spacer(1, 10),
        ])


    contenido.append(
        crear_bloque_estado(
            "SISTEMA ACS",
            [
                ["Puntos de control", str(puntos_acs)],
                ["Controles planificados", str(controles_sala_acs)],
            ]
        )
    )

    contenido.append(
        crear_bloque_estado(
            "AGUA FRÍA (AFCH / AFS)",
            [
                ["Puntos de control", str(puntos_afs)],
                ["Controles planificados", str(controles_afs)],
            ]
        )
    )

    contenido.append(
        crear_bloque_estado(
            "INSTALACIÓN SOLAR",
            [
                ["Depósitos solares", str(depositos_solares)],
            ]
        )
    )

    contenido.append(
        crear_bloque_estado(
            "PUNTOS TERMINALES",
            [
                ["Duchas", str(puntos_ducha)],
                ["Terminales", str(terminales_ducha)],
                ["Controles completos", str(controles_terminales)],
            ]
        )
    )

    contenido.append(
        crear_bloque_estado(
            "VÁLVULAS TERMOSTÁTICAS",
            [
                ["Instaladas", str(puntos_vtm)],
                ["Controles planificados", str(controles_vtm)],
            ]
        )
    )

    contenido.append(
        crear_bloque_estado(
            "RESULTADO DEL PERIODO",
            [
                ["Controles realizados", str(total)],
                ["Incidencias abiertas", str(incidencias_abiertas)],
                ["Incidencias cerradas", str(incidencias_cerradas)],
                ["Cumplimiento", f"{cumplimiento}%"],
            ]
        )
    )

    contenido.append(Spacer(1, 8))

    if incidencias_abiertas == 0:
        estado_operativo = "FAVORABLE"
        texto_estado = (
            "La instalación dispone de puntos físicos identificados y planificación preventiva activa. "
            "No constan incidencias abiertas en el periodo seleccionado. "
            "El estado operativo general se considera FAVORABLE según los registros disponibles."
        )
    else:
        estado_operativo = "EN SEGUIMIENTO"
        texto_estado = (
            f"La instalación dispone de puntos físicos identificados y planificación preventiva activa. "
            f"Constan {incidencias_abiertas} incidencia(s) abierta(s) en el periodo seleccionado. "
            "El estado operativo general queda EN SEGUIMIENTO hasta el cierre de las acciones correctoras."
        )

    contenido.append(
        Paragraph(
            "1.2 Evaluación operativa",
            styles["Heading2"]
        )
    )
    contenido.append(Spacer(1, 6))

    if estado_operativo == "FAVORABLE":
        color_estado_fondo = colors.HexColor("#E8F5E9")
        color_estado_borde = colors.HexColor("#2E7D32")
        color_estado_texto = colors.HexColor("#1B5E20")
    else:
        color_estado_fondo = colors.HexColor("#FFF4E5")
        color_estado_borde = colors.HexColor("#D97706")
        color_estado_texto = colors.HexColor("#92400E")

    estilo_estado_titulo = styles["Normal"].clone("EstadoTitulo")
    estilo_estado_titulo.fontName = "Helvetica-Bold"
    estilo_estado_titulo.fontSize = 11
    estilo_estado_titulo.leading = 14
    estilo_estado_titulo.textColor = color_estado_texto

    estilo_estado_texto = styles["Normal"].clone("EstadoTexto")
    estilo_estado_texto.fontName = "Helvetica"
    estilo_estado_texto.fontSize = 8.5
    estilo_estado_texto.leading = 12
    estilo_estado_texto.textColor = colors.HexColor("#374151")

    tabla_evaluacion = Table(
        [
            [
                Paragraph(
                    f"ESTADO GENERAL: {estado_operativo}",
                    estilo_estado_titulo
                )
            ],
            [
                Paragraph(
                    texto_estado,
                    estilo_estado_texto
                )
            ],
        ],
        colWidths=[470]
    )

    tabla_evaluacion.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_estado_fondo),
        ("BOX", (0, 0), (-1, -1), 1, color_estado_borde),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, color_estado_borde),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    contenido.append(
        KeepTogether([
            tabla_evaluacion,
            Spacer(1, 16),
        ])
    )

    contenido.append(Paragraph("2. Programa de mantenimiento y criterios de control", styles["Heading2"]))

    programa = [
        ["Control", "Frecuencia", "Criterio correcto"],
        ["Control sala ACS", "Según planificación", "Acumulador ≥ 60 ºC / Impulsión ≥ 50 ºC / Retorno ≥ 50 ºC"],
        ["Temperatura acumulador ACS", "Según planificación", "≥ 60 ºC"],
        ["Temperatura impulsión ACS", "Según planificación", "≥ 50 ºC"],
        ["Temperatura retorno ACS", "Integrado en Control sala ACS", "≥ 50 ºC"],
        ["Temperatura ACS terminal", "Según planificación", "≥ 50 ºC"],
        ["Temperatura AFCH", "Según planificación", "Preferentemente ≤ 25 ºC"],
        ["Cloro residual libre", "Según planificación", "0,2 - 1,0 mg/L"],
        ["Control punto terminal completo", "Según planificación", "AFCH + cloro + ACS terminal"],
        ["Depósitos solares", "Según planificación", "Registro de temperatura sin consigna automática"],
        ["Purga / revisión visual", "Según planificación", "Realizada / correcta"],
        ["Limpieza y desinfección acumulador", "Anual",
         "Limpieza, desinfección y revisión interior del acumulador ACS"],
        ["Limpieza y desinfección depósito AFCH", "Anual",
         "Según certificado empresa mantenedora"],
        ["Control válvula termostática", "Según planificación", "Entrada ≥ 60 ºC / salida 38-50 ºC"],
    ]

    estilo_tabla_cabecera = styles["Normal"].clone("TablaCabecera")
    estilo_tabla_cabecera.fontName = "Helvetica-Bold"
    estilo_tabla_cabecera.fontSize = 7.5
    estilo_tabla_cabecera.leading = 9
    estilo_tabla_cabecera.textColor = colors.white
    estilo_tabla_cabecera.alignment = 1

    estilo_tabla_celda = styles["Normal"].clone("TablaCelda")
    estilo_tabla_celda.fontName = "Helvetica"
    estilo_tabla_celda.fontSize = 7
    estilo_tabla_celda.leading = 9
    estilo_tabla_celda.textColor = colors.HexColor("#273444")

    programa_formateado = []

    programa_formateado.append([
        Paragraph("CONTROL", estilo_tabla_cabecera),
        Paragraph("FRECUENCIA", estilo_tabla_cabecera),
        Paragraph("CRITERIO CORRECTO", estilo_tabla_cabecera),
    ])

    for fila in programa[1:]:
        programa_formateado.append([
            Paragraph(limpiar_pdf(fila[0]), estilo_tabla_celda),
            Paragraph(limpiar_pdf(fila[1]), estilo_tabla_celda),
            Paragraph(limpiar_pdf(fila[2]), estilo_tabla_celda),
        ])

    tabla_programa = Table(
        programa_formateado,
        colWidths=[155, 120, 225],
        repeatRows=1,
    )

    estilos_programa = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C7D0D9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for indice in range(1, len(programa_formateado)):
        if indice % 2 == 0:
            estilos_programa.append(
                ("BACKGROUND", (0, indice), (-1, indice), colors.HexColor("#F4F7F9"))
            )

    tabla_programa.setStyle(TableStyle(estilos_programa))

    contenido.append(
        KeepTogether([
            Paragraph(
                "Criterios aplicados según la planificación activa de mantenimiento y control.",
                estilo_estado_texto
            ),
            Spacer(1, 7),
        ])
    )

    contenido.append(tabla_programa)
    contenido.append(Spacer(1, 18))

    contenido.append(Paragraph("3. Inventario de puntos físicos de control", styles["Heading2"]))

    if df_puntos.empty:
        contenido.append(Paragraph("No constan puntos de control registrados.", styles["Normal"]))
    else:
        tabla_puntos = [["Edificio", "Inst.", "Punto", "Tipo punto", "Tipo control", "Terminales", "Ubicación"]]

        for _, row in df_puntos.head(140).iterrows():
            ubicacion = row.get("ubicacion_exacta") or row.get("ubicacion") or ""
            tabla_puntos.append([
                limpiar_pdf(row.get("edificio", ""), 19),
                limpiar_pdf(row.get("instalacion", ""), 8),
                limpiar_pdf(row.get("nombre_punto", ""), 26),
                limpiar_pdf(row.get("tipo_punto", ""), 16),
                limpiar_pdf(row.get("tipo_control_punto", ""), 18),
                limpiar_pdf(row.get("numero_terminales", ""), 5),
                limpiar_pdf(ubicacion, 26),
            ])

        tabla_p = Table(tabla_puntos, colWidths=[72, 35, 105, 68, 78, 42, 100])
        tabla_p.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 5.8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        contenido.append(tabla_p)

    contenido.append(Spacer(1, 16))

    contenido.append(Paragraph("4. Resumen del periodo", styles["Heading2"]))

    resumen = [
        ["Total controles", "Correctos", "Incidencias / Riesgos", "Cumplimiento"],
        [str(total), str(ok), str(no_ok), f"{cumplimiento}%"]
    ]

    tabla_resumen = Table(resumen, colWidths=[125, 125, 140, 110])
    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    contenido.append(tabla_resumen)
    contenido.append(Spacer(1, 16))

    contenido.append(Paragraph("5. Planificación activa", styles["Heading2"]))

    if df_plan.empty:
        contenido.append(Paragraph("No consta planificación activa registrada.", styles["Normal"]))
    else:
        tabla_plan = [["Edificio", "Punto", "Tarea", "Frecuencia", "Próxima", "Operario", "Consigna"]]

        for _, row in df_plan.head(120).iterrows():
            consigna = ""
            if int(row.get("controla_consigna") or 0) == 1:
                consigna = f"≥ {row.get('consigna_minima', '')}"

            tabla_plan.append([
                limpiar_pdf(row.get("edificio", ""), 20),
                limpiar_pdf(row.get("punto", ""), 28),
                limpiar_pdf(row.get("tarea", ""), 30),
                limpiar_pdf(row.get("frecuencia", ""), 14),
                limpiar_pdf(row.get("proxima_fecha", ""), 12),
                limpiar_pdf(row.get("operario", ""), 18),
                limpiar_pdf(consigna, 10),
            ])

        tabla_pl = Table(tabla_plan, colWidths=[75, 105, 115, 60, 55, 65, 40])
        tabla_pl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        contenido.append(tabla_pl)

    contenido.append(Spacer(1, 16))

    contenido.append(Paragraph("6. Registro de controles realizados", styles["Heading2"]))

    if df.empty:
        contenido.append(Paragraph("No constan controles registrados en el periodo seleccionado.", styles["Normal"]))
    else:
        tabla_data = [["Fecha", "Edificio", "Punto", "Tarea", "Valores registrados", "Estado", "Operario"]]

        for _, row in df.head(150).iterrows():
            tabla_data.append([
                limpiar_pdf(str(row["fecha"])[:10]),
                limpiar_pdf(row["edificio"], 18),
                limpiar_pdf(row["punto"], 24),
                limpiar_pdf(row["tarea"], 26),
                limpiar_pdf(texto_valores(row), 45),
                limpiar_pdf(row["estado"], 12),
                limpiar_pdf(row["operario"], 16),
            ])

        tabla = Table(tabla_data, colWidths=[50, 70, 95, 100, 140, 50, 65])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        contenido.append(tabla)

    contenido.append(Spacer(1, 16))

    contenido.append(Paragraph("6.1 Últimos controles críticos", styles["Heading2"]))

    if df.empty:
        contenido.append(Paragraph("No constan controles críticos registrados.", styles["Normal"]))
    else:
        df_crit = df[
            df["tarea"].astype(str).isin([
                "Control sala ACS",
                "Control AFS",
                "Control ACS terminal",
                "Control punto terminal completo",
                "Control válvula termostática",
                "Temperatura acumulador",
                "Temperatura retorno",
                "Temperatura impulsión ACS",
            ])
        ].copy()

        if df_crit.empty:
            contenido.append(Paragraph("No constan controles críticos registrados.", styles["Normal"]))
        else:
            tabla_crit = [["Fecha", "Punto", "Control", "Valores", "Estado", "Resultado"]]

            for _, row in df_crit.head(40).iterrows():
                tabla_crit.append([
                    limpiar_pdf(str(row["fecha"])[:10]),
                    limpiar_pdf(row["punto"], 28),
                    limpiar_pdf(row["tarea"], 28),
                    limpiar_pdf(texto_valores(row), 45),
                    limpiar_pdf(row["estado"], 10),
                    limpiar_pdf(row["resultado"], 45),
                ])

            tabla_c = Table(tabla_crit, colWidths=[50, 95, 100, 135, 45, 145])
            tabla_c.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 5.8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            contenido.append(tabla_c)

    contenido.append(Spacer(1, 16))

    contenido.append(Paragraph("7. Incidencias y acciones correctoras", styles["Heading2"]))

    if df_inc.empty:
        contenido.append(Paragraph("No constan incidencias registradas en el periodo.", styles["Normal"]))
    else:
        tabla_inc = [["Fecha", "Edificio", "Punto", "Tarea", "Estado", "Descripción / cierre"]]

        for _, row in df_inc.head(80).iterrows():
            desc = row.get("descripcion", "")
            cierre = row.get("observaciones_cierre", "")
            if cierre:
                desc = f"{desc} | Cierre: {cierre}"

            tabla_inc.append([
                limpiar_pdf(str(row["fecha_apertura"])[:10]),
                limpiar_pdf(row["edificio"], 18),
                limpiar_pdf(row["punto"], 24),
                limpiar_pdf(row["tarea"], 24),
                limpiar_pdf(row["estado"], 14),
                limpiar_pdf(desc, 65),
            ])

        tabla_i = Table(tabla_inc, colWidths=[50, 70, 95, 95, 50, 210])
        tabla_i.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        contenido.append(tabla_i)

    contenido.append(Spacer(1, 16))

    contenido.append(Paragraph("8. Informes externos, analíticas y certificados", styles["Heading2"]))

    if df_inf.empty:
        contenido.append(Paragraph("No constan informes externos registrados en el periodo.", styles["Normal"]))
    else:
        tabla_inf = [["Fecha", "Tipo", "Empresa", "Inst.", "Punto", "Resultado", "Nº informe"]]

        for _, row in df_inf.head(80).iterrows():
            tabla_inf.append([
                limpiar_pdf(str(row.get("fecha_informe", ""))[:10]),
                limpiar_pdf(row.get("tipo_informe", ""), 22),
                limpiar_pdf(row.get("empresa", ""), 18),
                limpiar_pdf(row.get("instalacion", ""), 10),
                limpiar_pdf(row.get("punto", ""), 24),
                limpiar_pdf(row.get("resultado", ""), 16),
                limpiar_pdf(row.get("numero_informe", ""), 18),
            ])

        tabla_e = Table(tabla_inf, colWidths=[50, 105, 85, 45, 105, 75, 75])
        tabla_e.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        contenido.append(tabla_e)

    contenido.append(Spacer(1, 20))

    contenido.append(Paragraph("9. Observaciones y trazabilidad", styles["Heading2"]))
    contenido.append(Paragraph(
        "El presente libro se genera con los datos registrados en la aplicación de mantenimiento: "
        "puntos físicos de control, planificación activa, controles de temperatura, cloro residual, "
        "purgas, revisiones visuales, incidencias, acciones correctoras e informes externos. "
        "El retorno ACS se considera integrado dentro del control de sala ACS cuando así esté configurado "
        "en la planificación. La documentación original adjunta permanece archivada en el sistema.",
        styles["Normal"]
    ))

    contenido.append(Spacer(1, 28))
    contenido.append(Paragraph("<b>Firma / Responsable:</b> ________________________________", styles["Normal"]))
    contenido.append(Spacer(1, 10))
    contenido.append(Paragraph("<b>Fecha:</b> ________________________________", styles["Normal"]))

    doc.build(contenido)

    st.download_button(
        f"📘 Descargar libro inspección {centro_filtro}",
        data=buffer.getvalue(),
        file_name=f"libro_inspeccion_legionella_{centro_filtro.replace(' ', '_')}_{fecha_inicio_txt}_a_{fecha_fin_txt}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
