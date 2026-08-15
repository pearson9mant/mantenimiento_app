from io import BytesIO
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    PageBreak,
    Image,
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
            if str(row.get("tipo_control", "") or "").strip() == "Control ACS terminal mezclado":
                return f"ACS terminal mezclado: {row.get('valor', '')} ºC"
            return f"ACS terminal: {row.get('valor', '')} ºC"

        if tarea == "Control punto terminal completo":
            return (
                f"AFS: {row.get('valor', '')} ºC / "
                f"Cloro: {row.get('valor_2', '')} mg/L / "
                f"ACS: {row.get('valor_3', '')} ºC"
            )

        if tarea == "Control sala ACS":
            valor_3 = row.get("valor_3", None)

            if pd.notna(valor_3):
                return (
                    f"Acum.: {row.get('valor', '')} ºC / "
                    f"Imp.: {row.get('valor_2', '')} ºC / "
                    f"Ret.: {valor_3} ºC"
                )

            return (
                f"Acum.: {row.get('valor', '')} ºC / "
                f"Imp.: {row.get('valor_2', '')} ºC / "
                "Sin retorno principal"
            )

        if tarea == "Revisión trimestral acumulador ACS":
            try:
                correcto = int(float(row.get("valor", 0) or 0)) == 1
            except Exception:
                correcto = False
            return "Revisión acumulador: Correcta" if correcto else "Revisión acumulador: Con deficiencias"

        if tarea == "Purga":
            try:
                realizada = int(float(row.get("valor", 0) or 0)) == 1
            except Exception:
                realizada = False
            return "Purga: Realizada" if realizada else "Purga: No realizada"

        if tarea == "Control válvula termostática":
            return (
                f"Entrada ACS: {row.get('valor', '')} ºC / "
                f"Salida mezclada: {row.get('valor_2', '')} ºC"
            )

        if tarea == "Control circuito duchas mezclado":
            return (
                f"VMT-01: {row.get('valor', '')} ºC / "
                f"RT-01: {row.get('valor_2', '')} ºC / "
                f"VMT-02: {row.get('valor_3', '')} ºC / "
                f"RT-02: {row.get('valor_4', '')} ºC"
            )

        if tarea == "Control depósitos solares":
            return (
                f"Solar 1: {row.get('valor', '')} ºC / "
                f"Solar 2: {row.get('valor_2', '')} ºC / "
                f"Diferencia: {row.get('valor_3', '')} ºC"
            )

        if tarea == "Choque térmico":
            return (
                f"Acumulador: {row.get('valor', '')} ºC / "
                f"Tiempo ≥70 ºC: {row.get('valor_2', '')} min / "
                f"Terminal mínimo: {row.get('valor_3', '')} ºC"
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
        SELECT fecha, centro, edificio, instalacion, punto, tarea, tipo_control,
               valor, valor_2, valor_3, valor_4,
               unidad, estado, resultado, operario, observaciones
        FROM legionella_registros
        WHERE SUBSTR(fecha, 1, 10) BETWEEN ? AND ?
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
        WHERE SUBSTR(fecha_apertura, 1, 10) BETWEEN ? AND ?
          AND centro = ?
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND punto IS NOT NULL
          AND tarea IS NOT NULL
        ORDER BY fecha_apertura DESC
    """, (fecha_inicio_txt, fecha_fin_txt, centro_filtro))

    df_puntos = leer_df("""
        SELECT centro, edificio, instalacion, tipo_punto, tipo_control_punto,
               nombre_punto, ubicacion, ubicacion_exacta, numero_terminales, activo,
               plano_nombre, plano_data
        FROM legionella_puntos
        WHERE centro = ?
          AND centro IS NOT NULL
          AND edificio IS NOT NULL
          AND nombre_punto IS NOT NULL
        ORDER BY centro, edificio, instalacion, nombre_punto
    """, (centro_filtro,))

    # ---------------------------------------------------------
    # PLANOS DEL CENTRO
    # ---------------------------------------------------------
    # La aplicación ya dispone de un plano general por centro en
    # assets/planos_legionella. Esos son los planos principales del libro.
    # Después añadimos, si existen, planos específicos guardados en puntos.
    planos_pdf_unicos = []
    huellas_planos = set()

    import hashlib

    planos_generales_legionella = {
        "Pearson 22": {
            "ruta": Path("assets/planos_legionella/Puntos_control_legionela.pdf"),
            "nombre": "Puntos_control_legionela.pdf",
            "edificio": "Plano general Pearson 22",
            "punto": "Puntos AFS, ACS, acumuladores, duchas y muestras",
        },
        "Pearson 9": {
            "ruta": Path(
                "assets/planos_legionella/"
                "Puntos_control_legionela_Pearson_9_v2.pdf"
            ),
            "nombre": "Puntos_control_legionela_Pearson_9_v2.pdf",
            "edificio": "Plano general Pearson 9",
            "punto": "Puntos AFS, ACS, acumuladores, duchas y muestras",
        },
    }

    plano_general = planos_generales_legionella.get(str(centro_filtro).strip())

    if plano_general:
        ruta_plano_general = plano_general["ruta"]

        if ruta_plano_general.exists():
            try:
                plano_bytes = ruta_plano_general.read_bytes()
                huella = hashlib.sha256(plano_bytes).hexdigest()

                huellas_planos.add(huella)

                planos_pdf_unicos.append({
                    "nombre": plano_general["nombre"],
                    "edificio": plano_general["edificio"],
                    "punto": plano_general["punto"],
                    "data": plano_bytes,
                    "origen": "Plano general del centro",
                })
            except Exception as e:
                print(
                    f"[INFORME LEGIONELLA] No se pudo leer el plano general "
                    f"de {centro_filtro}: {type(e).__name__}: {e}"
                )

    # Planos específicos almacenados en legionella_puntos.
    if not df_puntos.empty and "plano_data" in df_puntos.columns:
        for _, row_plano in df_puntos.iterrows():
            plano_data = row_plano.get("plano_data")

            if plano_data is None or plano_data == b"":
                continue

            try:
                plano_bytes = bytes(plano_data)
            except Exception:
                continue

            huella = hashlib.sha256(plano_bytes).hexdigest()

            if huella in huellas_planos:
                continue

            huellas_planos.add(huella)

            planos_pdf_unicos.append({
                "nombre": str(
                    row_plano.get("plano_nombre")
                    or f"Plano {row_plano.get('edificio', '')}"
                ).strip(),
                "edificio": str(row_plano.get("edificio") or "").strip(),
                "punto": str(row_plano.get("nombre_punto") or "").strip(),
                "data": plano_bytes,
                "origen": "Plano específico asociado a punto",
            })

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
              AND SUBSTR(
                    COALESCE(
                        NULLIF(fecha_actuacion, ''),
                        fecha_informe
                    ),
                    1,
                    10
                  ) BETWEEN ? AND ?
            ORDER BY
                COALESCE(
                    NULLIF(fecha_actuacion, ''),
                    fecha_informe
                ) DESC,
                id DESC
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

    # ---------------------------------------------------------
    # MATRIZ NORMATIVA
    # Base estatal vigente:
    # - RD 487/2022, de 21 de junio
    # - RD 614/2024, de 2 de julio (modificación)
    # - RD 3/2023, de 10 de enero, para calidad de agua de consumo
    # ---------------------------------------------------------

    NORMATIVA_LEGIONELLA = {
        "Control sala ACS": (
            "RD 487/2022 · Anexo IV · B.2 / "
            "Anexo III · I.A.7.c-f"
        ),
        "Temperatura acumulador": (
            "RD 487/2022 · Anexo IV · B.2 / "
            "Anexo III · I.A.7.c"
        ),
        "Temperatura acumulador ACS": (
            "RD 487/2022 · Anexo IV · B.2 / "
            "Anexo III · I.A.7.c"
        ),
        "Temperatura impulsión ACS": (
            "RD 487/2022 · Anexo III · I.A.7.f"
        ),
        "Temperatura retorno": (
            "RD 487/2022 · Anexo IV · B.2 / "
            "Anexo III · I.A.7.f"
        ),
        "Temperatura retorno ACS": (
            "RD 487/2022 · Anexo IV · B.2 / "
            "Anexo III · I.A.7.f"
        ),
        "Temperatura punto terminal": (
            "RD 487/2022 · Anexo IV · B.1-B.2"
        ),
        "Temperatura ACS terminal": (
            "RD 487/2022 · Anexo IV · B.1-B.2"
        ),
        "Control ACS terminal": (
            "RD 487/2022 · Anexo IV · B.1-B.2"
        ),
        "Control ACS terminal mezclado": (
            "Control técnico PPCL · terminal posterior a mezcla / "
            "RD 487/2022 · Anexo III · I.A.7.f"
        ),
        "Control AFS": (
            "RD 487/2022 · Anexo IV · B.1 y B.3 / "
            "RD 3/2023 · Anexo I.C · Tabla 3"
        ),
        "Cloro residual": (
            "RD 487/2022 · Anexo IV · B.3 / "
            "RD 3/2023 · Anexo I.C · Tabla 3, nota 8"
        ),
        "Control punto terminal completo": (
            "RD 487/2022 · Anexo IV · B.1-B.3 / "
            "RD 3/2023 · Anexo I.C"
        ),
        "Purga": (
            "RD 487/2022 · Anexo IV · B.2"
        ),
        "Ruta semanal purgas P9": (
            "RD 487/2022 · Anexo IV · B.1.3"
        ),
        "Revisión trimestral acumulador ACS": (
            "RD 487/2022 · Anexo IV · B.2 · "
            "redacción RD 614/2024, art. único.10"
        ),
        "Revisión visual": (
            "RD 487/2022 · Anexo IV · B.1"
        ),
        "Limpieza y desinfección acumulador": (
            "RD 487/2022 · Anexo IV · B.4 / Anexo X"
        ),
        "Limpieza y desinfección depósito AFCH": (
            "RD 487/2022 · Anexo IV · B.3-B.4 / Anexo X"
        ),
        "Puesta en servicio acumulador ACS": (
            "RD 487/2022 · Anexo III · I.A.7 / "
            "Anexo IV · B.2"
        ),
        "Choque térmico": (
            "RD 487/2022 · Anexo III · I.A.7.f / "
            "Anexo IV · B.4"
        ),
        "Control depósitos solares": (
            "RD 487/2022 · Anexo III · I.A.7.d"
        ),
        "Control válvula termostática": (
            "Control técnico PPCL · relacionado con "
            "RD 487/2022 · Anexo III · I.A.7.f"
        ),
        "Control circuito duchas mezclado": (
            "Control técnico PPCL · relacionado con "
            "RD 487/2022 · Anexo III · I.A.7.f"
        ),
        "Analítica laboratorio": (
            "RD 487/2022 · Anexos V, VI, VII y VIII"
        ),
        "Revisión externa": (
            "RD 487/2022 · PPCL/PSL · Anexo IV"
        ),
        "Certificado": (
            "RD 487/2022 · Anexo X, cuando corresponda"
        ),
        "Desinfección": (
            "RD 487/2022 · Anexo IV · B.4 / Anexo X"
        ),
    }

    def referencia_normativa(tarea, tipo_control=None):
        tarea_txt = str(tarea or "").strip()
        tipo_txt = str(tipo_control or "").strip()

        if tipo_txt in NORMATIVA_LEGIONELLA:
            return NORMATIVA_LEGIONELLA[tipo_txt]

        if tarea_txt in NORMATIVA_LEGIONELLA:
            return NORMATIVA_LEGIONELLA[tarea_txt]

        tarea_lower = tarea_txt.lower()

        for nombre, referencia in NORMATIVA_LEGIONELLA.items():
            if nombre.lower() in tarea_lower:
                return referencia

        return "Control definido en el PPCL de la instalación"

    def referencia_normativa_punto(row):
        instalacion = str(row.get("instalacion", "") or "").strip().lower()
        tipo_punto = str(row.get("tipo_punto", "") or "").strip().lower()
        tipo_control = str(row.get("tipo_control_punto", "") or "").strip().lower()

        if "solar" in instalacion or "solar" in tipo_punto or "solar" in tipo_control:
            return "RD 487/2022 · Anexo III · I.A.7.d"

        if "acumulador" in tipo_punto or "acumulador" in tipo_control:
            return (
                "RD 487/2022 · Anexo III · I.A.7 / "
                "Anexo IV · B.2"
            )

        if "retorno" in tipo_punto or "retorno" in tipo_control:
            return (
                "RD 487/2022 · Anexo III · I.A.7.f / "
                "Anexo IV · B.2"
            )

        if instalacion in ["afch", "afs"] or "afs" in tipo_control:
            return (
                "RD 487/2022 · Anexo III · I.A.6 / "
                "Anexo IV · B.1 y B.3"
            )

        if tipo_punto in ["grifo", "ducha", "lavamanos", "fuente"]:
            return "RD 487/2022 · Anexo IV · B.1-B.3"

        if "válvula" in tipo_control or "valvula" in tipo_control:
            return (
                "Control técnico PPCL · relacionado con "
                "RD 487/2022 · Anexo III · I.A.7.f"
            )

        return "RD 487/2022 · PPCL/PSL de la instalación"

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

    # Resumen técnico por familias reales de la instalación.
    # El objetivo es que los números sean comprensibles para mantenimiento,
    # gerencia e inspección, evitando mezclar puntos físicos con tareas.

    puntos_afs = contar_puntos(instalacion="AFCH") + contar_puntos(instalacion="AFS")
    puntos_ducha = contar_puntos(tipo_punto="ducha")
    puntos_vtm = contar_puntos(tipo_control="válvula")

    acumuladores_acs = 0
    depositos_solares = 0
    retornos_principales_acs_fisicos = 0
    terminales_ducha = 0

    if not df_puntos.empty:
        inst = df_puntos["instalacion"].astype(str).str.strip().str.lower()
        tipo = df_puntos["tipo_punto"].astype(str).str.strip().str.lower()
        nombre = df_puntos["nombre_punto"].astype(str).str.strip().str.lower()
        control = df_puntos["tipo_control_punto"].astype(str).str.strip().str.lower()

        es_solar = (
            inst.str.contains("solar", na=False)
            | tipo.str.contains("solar", na=False)
            | control.str.contains("solar", na=False)
        )

        es_acs = inst.str.contains("acs", na=False)
        es_acumulador = (
            tipo.str.contains("acumulador", na=False)
            | nombre.str.contains("acumulador", na=False)
            | nombre.str.contains("depósito acs", na=False)
            | nombre.str.contains("deposito acs", na=False)
        )

        acumuladores_acs = int(
            (es_acs & es_acumulador & ~es_solar).sum()
        )

        # Contar equipos solares físicos, no solo filas lógicas.
        # Un único punto puede representar varios depósitos que se revisan juntos.
        df_solar_fisico = df_puntos[es_solar].copy()

        depositos_solares = 0

        for _, solar_row in df_solar_fisico.iterrows():
            try:
                unidades_solares = int(
                    float(solar_row.get("numero_terminales", 0) or 0)
                )
            except Exception:
                unidades_solares = 0

            # Si el punto declara varias unidades físicas, las contamos.
            # Si no las declara, el propio punto representa al menos un depósito.
            depositos_solares += unidades_solares if unidades_solares > 0 else 1

        es_retorno = (
            tipo.str.contains("retorno", na=False)
            | nombre.str.contains("retorno", na=False)
        )

        es_retorno_mezclado = (
            nombre.str.contains("mezcl", na=False)
            | control.str.contains("mezcl", na=False)
        )

        retornos_principales_acs_fisicos = int(
            (es_acs & es_retorno & ~es_retorno_mezclado).sum()
        )

        try:
            terminales_ducha = int(
                df_puntos[
                    df_puntos["tipo_punto"]
                    .astype(str)
                    .str.lower()
                    .str.contains("ducha", na=False)
                ]["numero_terminales"]
                .fillna(0)
                .astype(int)
                .sum()
            )
        except Exception:
            terminales_ducha = 0

    controles_sala_acs = contar_tareas("Control sala ACS")
    controles_afs = contar_tareas("Control AFS")
    controles_terminales_completos = contar_tareas("Control punto terminal completo")
    controles_terminales_acs = contar_tareas("Control ACS terminal")
    controles_vtm = contar_tareas("Control válvula termostática")
    controles_circuito_mezclado = contar_tareas("Control circuito duchas mezclado")

    # En la app, el retorno principal puede quedar integrado en Control sala ACS.
    # Para evitar el "0" engañoso, el resumen informa de cuántos circuitos de sala
    # ACS incluyen retorno principal.
    retornos_principales_integrados = min(
        controles_sala_acs,
        acumuladores_acs
    )

    if retornos_principales_acs_fisicos > 0:
        retornos_principales_mostrados = retornos_principales_acs_fisicos
    else:
        retornos_principales_mostrados = retornos_principales_integrados

    revisiones_trimestrales_acs = 0
    revisiones_trimestrales_solares = 0
    purgas_acumulador = 0

    if not df_plan.empty:
        tarea_plan = df_plan["tarea"].astype(str).str.strip().str.lower()
        punto_plan = df_plan["punto"].astype(str).str.strip().str.lower()
        instalacion_plan = df_plan["instalacion"].astype(str).str.strip().str.lower()

        es_revision_trimestral = (
            tarea_plan == "revisión trimestral acumulador acs"
        )

        es_solar_plan = (
            instalacion_plan.str.contains("solar", na=False)
            | punto_plan.str.contains("solar", na=False)
        )

        revisiones_trimestrales_solares = int(
            (es_revision_trimestral & es_solar_plan).sum()
        )

        revisiones_trimestrales_acs = int(
            (es_revision_trimestral & ~es_solar_plan).sum()
        )

        purgas_acumulador = int(
            (
                (tarea_plan == "purga")
                & (
                    punto_plan.str.contains("acumulador", na=False)
                    | punto_plan.str.contains("depósito acs", na=False)
                    | punto_plan.str.contains("deposito acs", na=False)
                )
            ).sum()
        )

    # Cobertura documental real del periodo.
    tareas_previstas_periodo = 0
    tareas_con_registro_periodo = 0
    cobertura_periodo = 0.0

    if not df_plan.empty:
        tareas_previstas_periodo = len(df_plan)

        if not df.empty:
            claves_plan = set(
                (
                    str(r["edificio"]).strip(),
                    str(r["punto"]).strip(),
                    str(r["tarea"]).strip(),
                )
                for _, r in df_plan.iterrows()
            )

            claves_reg = set(
                (
                    str(r["edificio"]).strip(),
                    str(r["punto"]).strip(),
                    str(r["tarea"]).strip(),
                )
                for _, r in df.iterrows()
            )

            tareas_con_registro_periodo = len(
                claves_plan.intersection(claves_reg)
            )

        if tareas_previstas_periodo > 0:
            cobertura_periodo = round(
                (tareas_con_registro_periodo / tareas_previstas_periodo) * 100,
                1
            )

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
                ["Acumuladores ACS finales", str(acumuladores_acs)],
                [
                    "Retornos principales ACS controlados",
                    str(retornos_principales_mostrados)
                ],
                [
                    "Controles sala ACS planificados",
                    f"{controles_sala_acs} · frecuencia diaria"
                    if controles_sala_acs
                    else "0"
                ],
                [
                    "Revisiones de acumuladores",
                    f"{revisiones_trimestrales_acs} · frecuencia trimestral"
                    if revisiones_trimestrales_acs
                    else "0"
                ],
                [
                    "Purgas de fondo de acumulador",
                    f"{purgas_acumulador} · frecuencia semanal"
                    if purgas_acumulador
                    else "0"
                ],
            ]
        )
    )

    contenido.append(
        Paragraph(
            "Nota técnica ACS: el retorno principal se registra dentro del "
            "Control sala ACS cuando la instalación dispone de él. Los circuitos "
            "posteriores a válvulas mezcladoras no se contabilizan como retornos "
            "principales ACS.",
            estilo_texto_portada
        )
    )
    contenido.append(Spacer(1, 8))

    contenido.append(
        crear_bloque_estado(
            "AGUA FRÍA (AFCH / AFS)",
            [
                ["Puntos de control AFS/AFCH", str(puntos_afs)],
                [
                    "Controles AFS planificados",
                    f"{controles_afs} · temperatura + desinfectante"
                    if controles_afs
                    else "0"
                ],
            ]
        )
    )

    contenido.append(
        crear_bloque_estado(
            "INSTALACIÓN SOLAR",
            [
                ["Depósitos / acumuladores solares físicos", str(depositos_solares)],
                [
                    "Revisión trimestral conjunta planificada",
                    str(revisiones_trimestrales_solares)
                ],
            ]
        )
    )

    if depositos_solares > 1 and revisiones_trimestrales_solares == 1:
        contenido.append(
            Paragraph(
                "Nota técnica solar: la revisión trimestral se registra como una única "
                "actuación porque comprende conjuntamente los depósitos solares de la "
                "instalación. El número de equipos físicos y el número de tareas "
                "planificadas se muestran por separado.",
                estilo_texto_portada
            )
        )
        contenido.append(Spacer(1, 8))

    contenido.append(
        crear_bloque_estado(
            "PUNTOS TERMINALES",
            [
                ["Puntos tipo ducha", str(puntos_ducha)],
                ["Duchas / terminales asociados", str(terminales_ducha)],
                [
                    "Controles ACS terminal planificados",
                    str(controles_terminales_acs)
                ],
                [
                    "Controles completos AFS + ACS",
                    str(controles_terminales_completos)
                ],
            ]
        )
    )

    contenido.append(
        crear_bloque_estado(
            "VÁLVULAS TERMOSTÁTICAS / MEZCLA",
            [
                ["Válvulas termostáticas registradas", str(puntos_vtm)],
                [
                    "Controles de válvula planificados",
                    f"{controles_vtm} · frecuencia mensual"
                    if controles_vtm
                    else "0"
                ],
            ]
        )
    )

    contenido.append(
        crear_bloque_estado(
            "RESULTADO DEL PERIODO",
            [
                ["Registros realizados", str(total)],
                ["Registros correctos", str(ok)],
                ["Registros con riesgo / incidencia", str(no_ok)],
                ["Incidencias abiertas", str(incidencias_abiertas)],
                ["Incidencias cerradas", str(incidencias_cerradas)],
                ["Resultado de registros ejecutados", f"{cumplimiento}%"],
                [
                    "Cobertura de tareas activas en el periodo",
                    f"{tareas_con_registro_periodo}/{tareas_previstas_periodo} · {cobertura_periodo}%"
                    if tareas_previstas_periodo
                    else "Sin planificación activa"
                ],
            ]
        )
    )

    contenido.append(Spacer(1, 8))

    contenido.append(
        Paragraph(
            "1.1.1 Lectura técnica de la instalación",
            styles["Heading3"]
        )
    )
    contenido.append(Spacer(1, 4))

    arquitectura_txt = (
        f"El centro dispone de {acumuladores_acs} acumulador(es) ACS final(es), "
        f"{retornos_principales_mostrados} retorno(s) principal(es) controlado(s), "
        f"{terminales_ducha} terminal(es) de ducha asociados y "
        f"{puntos_vtm} válvula(s) termostática(s) registradas. "
        "El retorno principal se integra en el control de sala ACS cuando existe. "
        "Las válvulas termostáticas y los circuitos posteriores a mezcla se controlan "
        "como elementos técnicos específicos y no se contabilizan como retornos "
        "principales ACS."
    )

    contenido.append(
        Table(
            [[Paragraph(arquitectura_txt, estilo_texto_portada)]],
            colWidths=[470],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6F8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C4CE")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ])
        )
    )
    contenido.append(Spacer(1, 12))

    if total == 0:
        estado_operativo = "SIN DATOS SUFICIENTES"
        texto_estado = (
            "Existe planificación preventiva, pero no constan registros ejecutados "
            "en el periodo seleccionado. No procede calificar el estado operativo "
            "como favorable hasta disponer de evidencias de ejecución."
        )
    elif incidencias_abiertas > 0 or no_ok > 0:
        estado_operativo = "EN SEGUIMIENTO"
        texto_estado = (
            f"Se han registrado {total} controles en el periodo. "
            f"Constan {no_ok} resultado(s) con riesgo/incidencia y "
            f"{incidencias_abiertas} incidencia(s) abierta(s). "
            "Debe mantenerse el seguimiento hasta verificar el cierre efectivo "
            "de las acciones correctoras."
        )
    elif tareas_previstas_periodo and cobertura_periodo < 100:
        estado_operativo = "CONTROL PARCIAL"
        texto_estado = (
            f"Los {total} registros ejecutados son correctos, pero la cobertura "
            f"documental de tareas activas en el periodo es del {cobertura_periodo}%. "
            "El estado se considera controlado parcialmente hasta completar la "
            "evidencia de ejecución prevista."
        )
    else:
        estado_operativo = "FAVORABLE"
        texto_estado = (
            f"Durante el periodo se han registrado {total} controles y todos "
            "los resultados disponibles son correctos. No constan incidencias "
            "abiertas y la cobertura documental de las tareas activas es completa."
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
    elif estado_operativo == "EN SEGUIMIENTO":
        color_estado_fondo = colors.HexColor("#FDECEC")
        color_estado_borde = colors.HexColor("#B91C1C")
        color_estado_texto = colors.HexColor("#991B1B")
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
        ["Control", "Frecuencia normativa", "Criterio correcto", "Referencia normativa"],

        [
            "Control sala ACS",
            "Diaria",
            "Acumulador ≥60 ºC; retorno ≥50 ºC cuando exista. "
            "La impulsión se controla como parámetro operativo del PPCL.",
            referencia_normativa("Control sala ACS"),
        ],
        [
            "Temperatura acumulador ACS",
            "Diaria",
            "Acumulador final ≥60 ºC",
            referencia_normativa("Temperatura acumulador ACS"),
        ],
        [
            "Temperatura retorno ACS",
            "Diaria, cuando exista",
            "Retorno ≥50 ºC",
            referencia_normativa("Temperatura retorno ACS"),
        ],
        [
            "Temperatura ACS terminal",
            "Mensual · muestra rotatoria",
            "≥50 ºC en los puntos representativos de ACS",
            referencia_normativa("Temperatura ACS terminal"),
        ],
        [
            "Revisión puntos terminales",
            "Mensual · muestra rotatoria",
            "Todos los terminales revisados al menos una vez al año",
            "RD 487/2022 · Anexo IV · B.1.2",
        ],
        [
            "Puntos de poco uso",
            "Semanal",
            "Abrir grifos/duchas y dejar correr el agua unos minutos",
            "RD 487/2022 · Anexo IV · B.1.3",
        ],
        [
            "Purga fondo acumulador",
            "Semanal",
            "Purga del fondo del acumulador realizada",
            referencia_normativa("Purga"),
        ],
        [
            "Drenaje de tuberías ACS",
            "Mensual",
            "Eliminación de sedimentos mediante válvulas de drenaje",
            "RD 487/2022 · Anexo IV · B.2",
        ],
        [
            "Revisión trimestral acumulador ACS",
            "Trimestral",
            "Estado de mantenimiento correcto; no exige apertura/vaciado obligatorio",
            referencia_normativa("Revisión trimestral acumulador ACS"),
        ],
        [
            "Control AFS / AFCH",
            "Según programa PPCL; controles representativos de temperatura y desinfectante",
            "Temperatura preferentemente ≤25 ºC. Cloro libre residual: "
            "valor paramétrico 1,0 mg/L; recomendación general ≥0,2 mg/L.",
            referencia_normativa("Control AFS"),
        ],
        [
            "Cloro residual libre",
            "Según programa de control del agua y PPCL",
            "Máx. paramétrico 1,0 mg/L; recomendación general ≥0,2 mg/L",
            referencia_normativa("Cloro residual"),
        ],
        [
            "Control punto terminal completo",
            "Según PPCL y periodicidades de cada parámetro",
            "AFS + desinfectante + ACS terminal",
            referencia_normativa("Control punto terminal completo"),
        ],
        [
            "Depósitos solares",
            "Según PPCL",
            "Si no aseguran >60 ºC de forma continua, debe alcanzarse 60 ºC "
            "en acumulador final antes de distribución",
            referencia_normativa("Control depósitos solares"),
        ],
        [
            "Limpieza y desinfección sistema agua sanitaria",
            "Al menos anual y cuando proceda",
            "Procedimiento documentado y certificado",
            "RD 487/2022 · Anexo IV · B.4 / Anexo X",
        ],
        [
            "Choque térmico",
            "Cuando proceda según PPCL / actuación correctora",
            "Tratamiento térmico documentado; instalación capaz de alcanzar 70 ºC",
            referencia_normativa("Choque térmico"),
        ],
        [
            "Control válvula termostática",
            "Según PPCL",
            "Control técnico interno de funcionamiento y seguridad",
            referencia_normativa("Control válvula termostática"),
        ],
        [
            "Circuito mezclado duchas",
            "Según PPCL",
            "Control técnico de salida mezclada y retorno posterior a mezcla",
            referencia_normativa("Control circuito duchas mezclado"),
        ],
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
        Paragraph("CRITERIO", estilo_tabla_cabecera),
        Paragraph("REFERENCIA NORMATIVA", estilo_tabla_cabecera),
    ])

    for fila in programa[1:]:
        programa_formateado.append([
            Paragraph(limpiar_pdf(fila[0]), estilo_tabla_celda),
            Paragraph(limpiar_pdf(fila[1]), estilo_tabla_celda),
            Paragraph(limpiar_pdf(fila[2]), estilo_tabla_celda),
            Paragraph(limpiar_pdf(fila[3]), estilo_tabla_celda),
        ])

    tabla_programa = Table(
        programa_formateado,
        colWidths=[105, 95, 145, 155],
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
                "Marco normativo de referencia: Real Decreto 487/2022, de 21 de junio, "
                "en su redacción vigente tras el Real Decreto 614/2024, de 2 de julio. "
                "Para parámetros de calidad del agua de consumo se incorpora, cuando procede, "
                "el Real Decreto 3/2023, de 10 de enero. En Cataluña, ASPCAT identifica además "
                "el Decret 352/2004, de 27 de julio, como normativa relacionada. Las frecuencias y "
                "criterios técnicos de cada control se trazan a la normativa estatal vigente. "
                "Los controles identificados como «Control técnico PPCL» son medidas internas "
                "del plan y no una denominación literal del Real Decreto.",
                estilo_estado_texto
            ),
            Spacer(1, 7),
        ])
    )

    contenido.append(tabla_programa)
    contenido.append(Spacer(1, 18))

    contenido.append(
        Paragraph(
            "3. Inventario de puntos físicos de control",
            styles["Heading2"]
        )
    )
    contenido.append(Spacer(1, 6))

    estilo_inventario_cabecera = styles["Normal"].clone("InventarioCabecera")
    estilo_inventario_cabecera.fontName = "Helvetica-Bold"
    estilo_inventario_cabecera.fontSize = 6.5
    estilo_inventario_cabecera.leading = 8
    estilo_inventario_cabecera.textColor = colors.white
    estilo_inventario_cabecera.alignment = 1

    estilo_inventario_celda = styles["Normal"].clone("InventarioCelda")
    estilo_inventario_celda.fontName = "Helvetica"
    estilo_inventario_celda.fontSize = 6.2
    estilo_inventario_celda.leading = 7.8
    estilo_inventario_celda.textColor = colors.HexColor("#273444")

    estilo_inventario_edificio = styles["Normal"].clone("InventarioEdificio")
    estilo_inventario_edificio.fontName = "Helvetica-Bold"
    estilo_inventario_edificio.fontSize = 7.5
    estilo_inventario_edificio.leading = 9
    estilo_inventario_edificio.textColor = colors.HexColor("#17324D")

    # ---------------------------------------------------------
    # PLANOS Y LOCALIZACIÓN
    # ---------------------------------------------------------
    contenido.append(PageBreak())
    contenido.append(
        Paragraph(
            "2. PLANOS Y LOCALIZACIÓN DE LA INSTALACIÓN",
            styles["Heading1"]
        )
    )
    contenido.append(Spacer(1, 8))

    if planos_pdf_unicos:
        contenido.append(
            Paragraph(
                "Se muestra primero el plano general de puntos de control del centro. "
                "A continuación se incorporan, si existen, planos específicos asociados "
                "a puntos concretos. Los documentos duplicados se incluyen una sola vez. "
                "Los PDF originales se incorporan también al final del libro como anexo documental.",
                estilo_texto_portada
            )
        )
        contenido.append(Spacer(1, 10))

        planos_renderizados = 0

        try:
            import fitz  # PyMuPDF

            for indice_plano, plano in enumerate(planos_pdf_unicos, start=1):
                contenido.append(
                    Paragraph(
                        f"Plano {indice_plano}: {limpiar_pdf(plano['nombre'])}",
                        styles["Heading2"]
                    )
                )

                datos_identificacion_plano = [
                    [
                        Paragraph("<b>Edificio / zona</b>", estilo_texto_portada),
                        Paragraph(limpiar_pdf(plano["edificio"]), estilo_texto_portada),
                    ],
                    [
                        Paragraph("<b>Punto de referencia</b>", estilo_texto_portada),
                        Paragraph(limpiar_pdf(plano["punto"]), estilo_texto_portada),
                    ],
                    [
                        Paragraph("<b>Origen</b>", estilo_texto_portada),
                        Paragraph(
                            limpiar_pdf(plano.get("origen", "")),
                            estilo_texto_portada
                        ),
                    ],
                ]

                tabla_identificacion_plano = Table(
                    datos_identificacion_plano,
                    colWidths=[120, 350]
                )
                tabla_identificacion_plano.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF4")),
                    ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C4CE")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))

                contenido.append(tabla_identificacion_plano)
                contenido.append(Spacer(1, 8))

                try:
                    documento_plano = fitz.open(
                        stream=plano["data"],
                        filetype="pdf"
                    )

                    for numero_pagina in range(len(documento_plano)):
                        pagina = documento_plano.load_page(numero_pagina)

                        # Render a buena calidad para que el plano sea legible.
                        pix = pagina.get_pixmap(
                            matrix=fitz.Matrix(1.7, 1.7),
                            alpha=False
                        )

                        png_bytes = pix.tobytes("png")
                        imagen = Image(BytesIO(png_bytes))

                        # Ajustar manteniendo proporción dentro de una página A4.
                        max_ancho = 500
                        max_alto = 680

                        escala = min(
                            max_ancho / float(imagen.imageWidth),
                            max_alto / float(imagen.imageHeight),
                            1.0
                        )

                        imagen.drawWidth = imagen.imageWidth * escala
                        imagen.drawHeight = imagen.imageHeight * escala

                        if numero_pagina > 0:
                            contenido.append(PageBreak())

                        contenido.append(
                            Paragraph(
                                f"Página {numero_pagina + 1} de {len(documento_plano)}",
                                estilo_texto_portada
                            )
                        )
                        contenido.append(Spacer(1, 4))
                        contenido.append(imagen)
                        contenido.append(Spacer(1, 10))

                        planos_renderizados += 1

                    documento_plano.close()

                except Exception as e:
                    contenido.append(
                        Paragraph(
                            "No ha sido posible visualizar este plano dentro del libro. "
                            "El archivo original se mantiene para su incorporación como anexo PDF.",
                            estilo_texto_portada
                        )
                    )

                if indice_plano < len(planos_pdf_unicos):
                    contenido.append(PageBreak())

        except Exception:
            contenido.append(
                Paragraph(
                    "Los planos están registrados en la base de datos, pero este entorno "
                    "no dispone del renderizador PDF necesario para mostrarlos dentro del libro. "
                    "Los originales se intentarán incorporar como anexo al final.",
                    estilo_texto_portada
                )
            )

        if planos_renderizados == 0:
            contenido.append(Spacer(1, 8))
            contenido.append(
                Paragraph(
                    "Aviso: no se ha generado ninguna previsualización de plano.",
                    estilo_texto_portada
                )
            )

    else:
        contenido.append(
            Paragraph(
                "No constan planos PDF asociados a los puntos de control de este centro.",
                estilo_texto_portada
            )
        )

    contenido.append(Spacer(1, 14))

    if df_puntos.empty:
        contenido.append(
            Table(
                [[
                    Paragraph(
                        "No constan puntos de control registrados.",
                        estilo_inventario_celda
                    )
                ]],
                colWidths=[500],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D0D9")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ])
            )
        )

    else:
        df_puntos_informe = df_puntos.head(140).copy()

        edificios_inventario = (
            df_puntos_informe["edificio"]
            .fillna("Sin edificio")
            .astype(str)
            .unique()
            .tolist()
        )

        for edificio_actual in edificios_inventario:

            df_edificio = df_puntos_informe[
                df_puntos_informe["edificio"]
                .fillna("Sin edificio")
                .astype(str)
                == edificio_actual
            ]

            contenido.append(
                KeepTogether([
                    Paragraph(
                        limpiar_pdf(edificio_actual),
                        estilo_inventario_edificio
                    ),
                    Spacer(1, 5),
                ])
            )

            tabla_puntos = [[
                Paragraph("INST.", estilo_inventario_cabecera),
                Paragraph("PUNTO", estilo_inventario_cabecera),
                Paragraph("TIPO", estilo_inventario_cabecera),
                Paragraph("CONTROL", estilo_inventario_cabecera),
                Paragraph("TERM.", estilo_inventario_cabecera),
                Paragraph("UBICACIÓN", estilo_inventario_cabecera),
                Paragraph("REF. NORMATIVA", estilo_inventario_cabecera),
            ]]

            for _, row in df_edificio.iterrows():
                ubicacion = (
                    row.get("ubicacion_exacta")
                    or row.get("ubicacion")
                    or ""
                )

                tabla_puntos.append([
                    Paragraph(
                        limpiar_pdf(row.get("instalacion", ""), 12),
                        estilo_inventario_celda
                    ),
                    Paragraph(
                        limpiar_pdf(row.get("nombre_punto", ""), 45),
                        estilo_inventario_celda
                    ),
                    Paragraph(
                        limpiar_pdf(row.get("tipo_punto", ""), 24),
                        estilo_inventario_celda
                    ),
                    Paragraph(
                        limpiar_pdf(row.get("tipo_control_punto", ""), 30),
                        estilo_inventario_celda
                    ),
                    Paragraph(
                        limpiar_pdf(row.get("numero_terminales", ""), 6),
                        estilo_inventario_celda
                    ),
                    Paragraph(
                        limpiar_pdf(ubicacion, 45),
                        estilo_inventario_celda
                    ),
                    Paragraph(
                        limpiar_pdf(referencia_normativa_punto(row), 120),
                        estilo_inventario_celda
                    ),
                ])

            tabla_p = Table(
                tabla_puntos,
                colWidths=[38, 92, 58, 72, 30, 92, 118],
                repeatRows=1,
            )

            estilos_inventario = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C7D0D9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (4, 1), (4, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]

            for indice in range(1, len(tabla_puntos)):
                if indice % 2 == 0:
                    estilos_inventario.append(
                        (
                            "BACKGROUND",
                            (0, indice),
                            (-1, indice),
                            colors.HexColor("#F4F7F9")
                        )
                    )

            tabla_p.setStyle(TableStyle(estilos_inventario))

            contenido.append(tabla_p)
            contenido.append(Spacer(1, 12))

    contenido.append(Spacer(1, 6))

    # ---------------------------------------------------------
    # 4. ANÁLISIS TÉCNICO DEL PERIODO
    # ---------------------------------------------------------

    contenido.append(Paragraph("4. Análisis técnico del periodo", styles["Heading2"]))
    contenido.append(Spacer(1, 6))

    if total == 0:
        diagnostico_periodo = (
            "No constan controles registrados durante el periodo seleccionado. "
            "La ausencia de incidencias no puede interpretarse como conformidad: "
            "sin registros no existe evidencia suficiente de ejecución. "
            "Debe verificarse la planificación activa y completar los controles previstos."
        )
        color_diagnostico_fondo = colors.HexColor("#FFF4E5")
        color_diagnostico_borde = colors.HexColor("#D97706")
        titulo_diagnostico = "PERIODO SIN REGISTROS"
    elif no_ok == 0 and incidencias_abiertas == 0:
        diagnostico_periodo = (
            f"Durante el periodo se han registrado {total} controles, todos ellos clasificados como correctos. "
            "No constan incidencias abiertas asociadas a los controles revisados. "
            "La evolución operativa del periodo se considera favorable."
        )
        color_diagnostico_fondo = colors.HexColor("#E8F5E9")
        color_diagnostico_borde = colors.HexColor("#2E7D32")
        titulo_diagnostico = "EVOLUCIÓN FAVORABLE"
    else:
        diagnostico_periodo = (
            f"Durante el periodo se han registrado {total} controles, de los cuales {ok} son correctos "
            f"y {no_ok} requieren revisión o seguimiento. Permanecen {incidencias_abiertas} incidencia(s) abierta(s). "
            "Debe mantenerse el seguimiento hasta verificar el cierre efectivo de las acciones correctoras."
        )
        color_diagnostico_fondo = colors.HexColor("#FFF4E5")
        color_diagnostico_borde = colors.HexColor("#D97706")
        titulo_diagnostico = "PERIODO EN SEGUIMIENTO"

    tabla_diagnostico = Table(
        [[Paragraph(f"<b>{titulo_diagnostico}</b>", estilo_estado_texto)],
         [Paragraph(diagnostico_periodo, estilo_estado_texto)]],
        colWidths=[500]
    )
    tabla_diagnostico.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_diagnostico_fondo),
        ("BOX", (0, 0), (-1, -1), 0.8, color_diagnostico_borde),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, color_diagnostico_borde),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    contenido.append(tabla_diagnostico)
    contenido.append(Spacer(1, 18))

    # ---------------------------------------------------------
    # ESTILOS COMUNES PARA TABLAS OPERATIVAS
    # ---------------------------------------------------------

    estilo_operativo_cabecera = styles["Normal"].clone("OperativoCabecera")
    estilo_operativo_cabecera.fontName = "Helvetica-Bold"
    estilo_operativo_cabecera.fontSize = 6.4
    estilo_operativo_cabecera.leading = 7.6
    estilo_operativo_cabecera.textColor = colors.white
    estilo_operativo_cabecera.alignment = 1

    estilo_operativo_celda = styles["Normal"].clone("OperativoCelda")
    estilo_operativo_celda.fontName = "Helvetica"
    estilo_operativo_celda.fontSize = 6.1
    estilo_operativo_celda.leading = 7.5
    estilo_operativo_celda.textColor = colors.HexColor("#273444")

    estilo_operativo_celda_centro = estilo_operativo_celda.clone("OperativoCeldaCentro")
    estilo_operativo_celda_centro.alignment = 1

    def construir_tabla_operativa(cabeceras, filas, anchos, centrar_columnas=None):
        datos = [[Paragraph(limpiar_pdf(c), estilo_operativo_cabecera) for c in cabeceras]]

        for fila in filas:
            datos.append([
                Paragraph(
                    limpiar_pdf(valor),
                    estilo_operativo_celda_centro if centrar_columnas and indice in centrar_columnas
                    else estilo_operativo_celda
                )
                for indice, valor in enumerate(fila)
            ])

        tabla = Table(datos, colWidths=anchos, repeatRows=1)

        comandos = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C7D0D9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]

        for indice in range(1, len(datos)):
            if indice % 2 == 0:
                comandos.append(
                    ("BACKGROUND", (0, indice), (-1, indice), colors.HexColor("#F4F7F9"))
                )

        tabla.setStyle(TableStyle(comandos))
        return tabla

    def bloque_sin_datos(texto):
        return Table(
            [[Paragraph(texto, estilo_operativo_celda)]],
            colWidths=[500],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D0D9")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ])
        )

    contenido.append(PageBreak())

    # ---------------------------------------------------------
    # 5. PLANIFICACIÓN ACTIVA
    # ---------------------------------------------------------

    contenido.append(Paragraph("5. Planificación preventiva activa", styles["Heading2"]))
    contenido.append(Spacer(1, 6))

    if df_plan.empty:
        contenido.append(bloque_sin_datos("No consta planificación activa registrada."))
    else:
        filas_plan = []
        for _, row in df_plan.head(120).iterrows():
            consigna = ""
            if int(row.get("controla_consigna") or 0) == 1:
                consigna = f"≥ {row.get('consigna_minima', '')}"

            filas_plan.append([
                limpiar_pdf(row.get("edificio", ""), 28),
                limpiar_pdf(row.get("punto", ""), 40),
                limpiar_pdf(row.get("tarea", ""), 42),
                limpiar_pdf(row.get("frecuencia", ""), 20),
                limpiar_pdf(row.get("proxima_fecha", ""), 16),
                limpiar_pdf(row.get("operario", ""), 24),
                limpiar_pdf(consigna, 12),
                limpiar_pdf(
                    referencia_normativa(row.get("tarea", "")),
                    120
                ),
            ])

        contenido.append(construir_tabla_operativa(
            [
                "EDIFICIO", "PUNTO", "TAREA", "FRECUENCIA",
                "PRÓXIMA", "OPERARIO", "CONSIGNA", "REF. NORMATIVA"
            ],
            filas_plan,
            [50, 68, 78, 48, 48, 58, 35, 115],
            centrar_columnas={3, 4, 6}
        ))

    contenido.append(Spacer(1, 18))

    # ---------------------------------------------------------
    # 6. CONTROLES REALIZADOS
    # ---------------------------------------------------------

    contenido.append(Paragraph("6. Registro de controles realizados", styles["Heading2"]))
    contenido.append(Spacer(1, 6))

    if df.empty:
        contenido.append(bloque_sin_datos(
            "No constan controles registrados en el periodo seleccionado."
        ))
    else:
        filas_controles = []
        for _, row in df.head(150).iterrows():
            filas_controles.append([
                limpiar_pdf(str(row.get("fecha", ""))[:10]),
                limpiar_pdf(row.get("edificio", ""), 24),
                limpiar_pdf(row.get("punto", ""), 36),
                limpiar_pdf(row.get("tarea", ""), 38),
                limpiar_pdf(texto_valores(row), 62),
                limpiar_pdf(row.get("estado", ""), 14),
                limpiar_pdf(row.get("operario", ""), 22),
                limpiar_pdf(
                    referencia_normativa(
                        row.get("tarea", ""),
                        row.get("tipo_control", "")
                    ),
                    125
                ),
            ])

        tabla_controles = construir_tabla_operativa(
            [
                "FECHA", "EDIFICIO", "PUNTO", "TAREA",
                "VALORES", "ESTADO", "OPERARIO", "REF. NORMATIVA"
            ],
            filas_controles,
            [40, 48, 60, 67, 90, 36, 44, 115],
            centrar_columnas={0, 5}
        )

        # Colorear visualmente las celdas de estado.
        estilos_estado_controles = []
        for indice_fila, (_, row) in enumerate(df.head(150).iterrows(), start=1):
            estado_txt = str(row.get("estado", "")).strip().lower()
            if estado_txt == "ok":
                estilos_estado_controles.extend([
                    ("BACKGROUND", (5, indice_fila), (5, indice_fila), colors.HexColor("#E8F5E9")),
                    ("TEXTCOLOR", (5, indice_fila), (5, indice_fila), colors.HexColor("#1B5E20")),
                ])
            elif estado_txt:
                estilos_estado_controles.extend([
                    ("BACKGROUND", (5, indice_fila), (5, indice_fila), colors.HexColor("#FFF4E5")),
                    ("TEXTCOLOR", (5, indice_fila), (5, indice_fila), colors.HexColor("#92400E")),
                ])

        tabla_controles.setStyle(TableStyle(estilos_estado_controles))
        contenido.append(tabla_controles)

    contenido.append(Spacer(1, 18))

    # ---------------------------------------------------------
    # 6.1 CONTROLES CRÍTICOS
    # ---------------------------------------------------------

    contenido.append(Paragraph("6.1 Controles críticos del periodo", styles["Heading2"]))
    contenido.append(Spacer(1, 6))

    if df.empty:
        contenido.append(bloque_sin_datos("No constan controles críticos registrados."))
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
                "Revisión trimestral acumulador ACS",
                "Control circuito duchas mezclado",
            ])
        ].copy()

        if df_crit.empty:
            contenido.append(bloque_sin_datos("No constan controles críticos registrados."))
        else:
            filas_criticos = []
            for _, row in df_crit.head(40).iterrows():
                filas_criticos.append([
                    limpiar_pdf(str(row.get("fecha", ""))[:10]),
                    limpiar_pdf(row.get("punto", ""), 38),
                    limpiar_pdf(row.get("tarea", ""), 38),
                    limpiar_pdf(texto_valores(row), 60),
                    limpiar_pdf(row.get("estado", ""), 14),
                    limpiar_pdf(row.get("resultado", ""), 65),
                    limpiar_pdf(
                        referencia_normativa(
                            row.get("tarea", ""),
                            row.get("tipo_control", "")
                        ),
                        120
                    ),
                ])

            tabla_criticos = construir_tabla_operativa(
                [
                    "FECHA", "PUNTO", "CONTROL", "VALORES",
                    "ESTADO", "RESULTADO", "REF. NORMATIVA"
                ],
                filas_criticos,
                [40, 65, 70, 82, 38, 85, 120],
                centrar_columnas={0, 4}
            )

            estilos_criticos = []
            for indice_fila, (_, row) in enumerate(df_crit.head(40).iterrows(), start=1):
                estado_txt = str(row.get("estado", "")).strip().lower()
                if estado_txt == "ok":
                    estilos_criticos.extend([
                        ("BACKGROUND", (4, indice_fila), (4, indice_fila), colors.HexColor("#E8F5E9")),
                        ("TEXTCOLOR", (4, indice_fila), (4, indice_fila), colors.HexColor("#1B5E20")),
                    ])
                elif estado_txt:
                    estilos_criticos.extend([
                        ("BACKGROUND", (4, indice_fila), (4, indice_fila), colors.HexColor("#FDECEC")),
                        ("TEXTCOLOR", (4, indice_fila), (4, indice_fila), colors.HexColor("#9B1C1C")),
                    ])

            tabla_criticos.setStyle(TableStyle(estilos_criticos))
            contenido.append(tabla_criticos)

    contenido.append(Spacer(1, 18))

    # ---------------------------------------------------------
    # 7. INCIDENCIAS Y ACCIONES CORRECTORAS
    # ---------------------------------------------------------

    contenido.append(Paragraph("7. Incidencias y acciones correctoras", styles["Heading2"]))
    contenido.append(Spacer(1, 6))

    if df_inc.empty:
        contenido.append(bloque_sin_datos(
            "No constan incidencias registradas en el periodo."
        ))
    else:
        filas_incidencias = []
        for _, row in df_inc.head(80).iterrows():
            descripcion = str(row.get("descripcion", "") or "")
            cierre = str(row.get("observaciones_cierre", "") or "")
            if cierre:
                descripcion = f"{descripcion} | Cierre: {cierre}"

            filas_incidencias.append([
                limpiar_pdf(str(row.get("fecha_apertura", ""))[:10]),
                limpiar_pdf(row.get("edificio", ""), 26),
                limpiar_pdf(row.get("punto", ""), 34),
                limpiar_pdf(row.get("tarea", ""), 34),
                limpiar_pdf(row.get("estado", ""), 18),
                limpiar_pdf(descripcion, 100),
                limpiar_pdf(
                    referencia_normativa(row.get("tarea", "")),
                    120
                ),
            ])

        tabla_incidencias = construir_tabla_operativa(
            [
                "FECHA", "EDIFICIO", "PUNTO", "TAREA",
                "ESTADO", "DESCRIPCIÓN / CIERRE", "REF. NORMATIVA"
            ],
            filas_incidencias,
            [40, 48, 58, 60, 42, 140, 112],
            centrar_columnas={0, 4}
        )

        estilos_incidencias = []
        for indice_fila, (_, row) in enumerate(df_inc.head(80).iterrows(), start=1):
            estado_txt = str(row.get("estado", "")).strip().lower()
            cerrada = estado_txt in ["cerrada", "cerrado", "finalizada", "finalizado"]
            if cerrada:
                estilos_incidencias.extend([
                    ("BACKGROUND", (4, indice_fila), (4, indice_fila), colors.HexColor("#E8F5E9")),
                    ("TEXTCOLOR", (4, indice_fila), (4, indice_fila), colors.HexColor("#1B5E20")),
                ])
            else:
                estilos_incidencias.extend([
                    ("BACKGROUND", (4, indice_fila), (4, indice_fila), colors.HexColor("#FDECEC")),
                    ("TEXTCOLOR", (4, indice_fila), (4, indice_fila), colors.HexColor("#9B1C1C")),
                ])

        tabla_incidencias.setStyle(TableStyle(estilos_incidencias))
        contenido.append(tabla_incidencias)

    contenido.append(Spacer(1, 18))

    # ---------------------------------------------------------
    # 8. INFORMES EXTERNOS
    # ---------------------------------------------------------

    contenido.append(Paragraph("8. Informes externos, analíticas y certificados", styles["Heading2"]))
    contenido.append(Spacer(1, 6))

    if df_inf.empty:
        contenido.append(bloque_sin_datos(
            "No constan informes externos registrados en el periodo."
        ))
    else:
        filas_informes = []
        for _, row in df_inf.head(80).iterrows():
            filas_informes.append([
                limpiar_pdf(str(row.get("fecha_informe", ""))[:10]),
                limpiar_pdf(row.get("tipo_informe", ""), 30),
                limpiar_pdf(row.get("empresa", ""), 26),
                limpiar_pdf(row.get("instalacion", ""), 16),
                limpiar_pdf(row.get("punto", ""), 34),
                limpiar_pdf(row.get("resultado", ""), 24),
                limpiar_pdf(row.get("numero_informe", ""), 24),
                limpiar_pdf(
                    referencia_normativa(row.get("tipo_informe", "")),
                    120
                ),
            ])

        contenido.append(construir_tabla_operativa(
            [
                "FECHA", "TIPO", "EMPRESA", "INST.", "PUNTO",
                "RESULTADO", "N.º INFORME", "REF. NORMATIVA"
            ],
            filas_informes,
            [40, 68, 55, 35, 65, 52, 55, 130],
            centrar_columnas={0, 3, 5}
        ))

    contenido.append(Spacer(1, 20))

    # ---------------------------------------------------------
    # 9. CONCLUSIÓN Y TRAZABILIDAD
    # ---------------------------------------------------------

    contenido.append(Paragraph("9. Conclusión técnica y trazabilidad", styles["Heading2"]))
    contenido.append(Spacer(1, 6))

    if total == 0:
        conclusion_tecnica = (
            "No existen registros suficientes en el periodo para emitir una conclusión "
            "operacional. La planificación preventiva permanece activa, pero debe "
            "documentarse la ejecución de los controles previstos."
        )
    elif incidencias_abiertas > 0 or no_ok > 0:
        conclusion_tecnica = (
            "Los registros disponibles muestran controles que requieren seguimiento y/o "
            "incidencias pendientes. La valoración definitiva queda condicionada al cierre "
            "documentado de las acciones correctoras y a la verificación posterior de los "
            "parámetros afectados."
        )
    elif tareas_previstas_periodo and cobertura_periodo < 100:
        conclusion_tecnica = (
            f"Los controles registrados son correctos, pero la cobertura documental de "
            f"las tareas activas en el periodo es del {cobertura_periodo}%. "
            "La instalación se considera controlada parcialmente hasta completar la "
            "evidencia prevista."
        )
    else:
        conclusion_tecnica = (
            "Los registros disponibles reflejan una situación operativa favorable: "
            "los controles ejecutados cumplen los criterios establecidos, no constan "
            "incidencias abiertas y la cobertura documental del periodo es completa."
        )

    tabla_conclusion = Table(
        [[Paragraph("<b>CONCLUSIÓN DEL PERIODO</b>", estilo_estado_texto)],
         [Paragraph(conclusion_tecnica, estilo_estado_texto)]],
        colWidths=[500]
    )
    tabla_conclusion.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF3F7")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#7B91A6")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.HexColor("#7B91A6")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    contenido.append(tabla_conclusion)
    contenido.append(Spacer(1, 12))

    contenido.append(Paragraph(
        "El presente libro se genera con los datos registrados en la aplicación de mantenimiento: "
        "puntos físicos de control, planificación activa, controles de temperatura, cloro residual, "
        "purgas, revisiones, incidencias, acciones correctoras e informes externos. Cada actuación se "
        "acompaña de su referencia normativa o, cuando se trata de un control técnico específico creado "
        "por el centro, de su identificación como medida interna del PPCL. El marco estatal de referencia "
        "es el RD 487/2022 en su redacción vigente tras el RD 614/2024; para parámetros de calidad del agua "
        "de consumo se incorpora el RD 3/2023 cuando procede y, en Cataluña, se identifica también el "
        "Decret 352/2004 como normativa relacionada. El retorno ACS se considera únicamente cuando "
        "existe como circuito principal de retorno. Los circuitos posteriores a válvulas mezcladoras "
        "se documentan dentro del control técnico correspondiente y no se contabilizan como retornos "
        "principales ACS. La documentación original adjunta permanece archivada en el sistema.",
        estilo_estado_texto
    ))

    contenido.append(Spacer(1, 28))

    tabla_firma = Table(
        [
            [Paragraph("<b>Firma / Responsable</b>", estilo_estado_texto),
             Paragraph("<b>Fecha</b>", estilo_estado_texto)],
            ["", ""],
        ],
        colWidths=[330, 170],
        rowHeights=[24, 58]
    )
    tabla_firma.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9CA3AF")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D0D9")),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    contenido.append(tabla_firma)

    doc.build(contenido)

    pdf_final = buffer.getvalue()

    # Incorporar físicamente los planos PDF al final del libro.
    # Se usa import opcional para no romper la generación si la librería
    # no estuviera disponible en algún entorno.
    if planos_pdf_unicos:
        try:
            from pypdf import PdfReader, PdfWriter

            writer = PdfWriter()

            informe_reader = PdfReader(BytesIO(pdf_final))
            for pagina in informe_reader.pages:
                writer.add_page(pagina)

            planos_añadidos = 0

            for plano in planos_pdf_unicos:
                try:
                    plano_reader = PdfReader(BytesIO(plano["data"]))

                    for pagina in plano_reader.pages:
                        writer.add_page(pagina)

                    planos_añadidos += 1
                except Exception:
                    continue

            if planos_añadidos > 0:
                buffer_final = BytesIO()
                writer.write(buffer_final)
                pdf_final = buffer_final.getvalue()

        except Exception:
            pass

    st.download_button(
        f"📘 Descargar libro inspección {centro_filtro}",
        data=pdf_final,
        file_name=f"libro_inspeccion_legionella_{centro_filtro.replace(' ', '_')}_{fecha_inicio_txt}_a_{fecha_fin_txt}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
