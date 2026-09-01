import streamlit as st


def _base(tipo_control, unidad, valor=None, valor_2=None, valor_3=None, observaciones_extra="", valido=True, errores=None):
    return {
        "tipo_control": tipo_control,
        "unidad": unidad,
        "valor": valor,
        "valor_2": valor_2,
        "valor_3": valor_3,
        "observaciones_extra": observaciones_extra,
        "valido": valido,
        "errores": errores or [],
    }


def mostrar_control_sala_acs(id_orden):
    st.info("Control conjunto de sala ACS: acumulador, impulsión y retorno.")

    valor = st.number_input("Temperatura acumulador ºC", 0.0, 100.0, 60.0, 0.1, key=f"leg_acum_{id_orden}")
    valor_2 = st.number_input("Temperatura impulsión ACS ºC", 0.0, 100.0, 50.0, 0.1, key=f"leg_impulsion_{id_orden}")
    valor_3 = st.number_input("Temperatura retorno ACS ºC", 0.0, 100.0, 50.0, 0.1, key=f"leg_retorno_{id_orden}")

    obs = f"Control sala ACS: Acumulador: {valor} ºC | Impulsión: {valor_2} ºC | Retorno: {valor_3} ºC"

    return _base("Control sala ACS", "ºC", valor, valor_2, valor_3, obs)


def mostrar_temperatura_simple(id_orden, tarea):
    unidad = "ºC"

    etiquetas = {
        "Temperatura acumulador": ("Temperatura acumulador ºC", 60.0),
        "Temperatura retorno": ("Temperatura retorno ºC", 50.0),
        "Temperatura punto terminal": ("Temperatura punto terminal ºC", 45.0),
        "Temperatura impulsión ACS": ("Temperatura impulsión ACS ºC", 50.0),
    }

    etiqueta, defecto = etiquetas.get(tarea, ("Temperatura ºC", 50.0))

    valor = st.number_input(
        etiqueta,
        min_value=0.0,
        max_value=100.0,
        value=defecto,
        step=0.1,
        key=f"leg_temp_simple_{id_orden}_{tarea}"
    )

    return _base(tarea, unidad, valor)


def mostrar_cloro_residual(id_orden):
    valor = st.number_input(
        "Cloro residual libre mg/L",
        min_value=0.0,
        max_value=5.0,
        value=0.5,
        step=0.01,
        key=f"leg_cloro_{id_orden}"
    )

    return _base("Cloro residual", "mg/L", valor)


def mostrar_control_afs(id_orden, terminales):
    valor = st.number_input("Temperatura AFS ºC", 0.0, 50.0, 18.0, 0.1, key=f"leg_temp_afs_{id_orden}")
    valor_2 = st.number_input("Cloro residual libre mg/L", 0.0, 5.0, 0.5, 0.01, key=f"leg_cloro_afs_{id_orden}")

    purga = st.checkbox("Purga realizada", key=f"leg_purga_afs_{id_orden}")
    aireador = st.checkbox("Aireador limpio/desinfectado", key=f"leg_aireador_afs_{id_orden}")
    revision = st.checkbox("Revisión visual correcta", key=f"leg_revision_afs_{id_orden}")

    terminales_revisados = st.number_input(
        "Terminales revisados",
        min_value=0,
        max_value=terminales,
        value=terminales,
        step=1,
        key=f"terminales_rev_afs_{id_orden}"
    )

    if terminales_revisados < terminales:
        st.warning(f"Solo se han revisado {terminales_revisados} de {terminales} terminales.")

    obs = (
        "Checklist AFS: "
        + ("Purga realizada: Sí" if purga else "Purga realizada: No")
        + " | "
        + ("Aireador limpio/desinfectado: Sí" if aireador else "Aireador limpio/desinfectado: No")
        + " | "
        + ("Revisión visual correcta: Sí" if revision else "Revisión visual correcta: No")
        + f" | Terminales revisados: {terminales_revisados}/{terminales}"
    )

    return _base("Control AFS", "ºC / mg/L", valor, valor_2, None, obs)


def mostrar_control_acs_terminal(id_orden, terminales):
    valor = st.number_input("Temperatura ACS terminal ºC", 0.0, 100.0, 50.0, 0.1, key=f"leg_temp_acs_{id_orden}")

    purga = st.checkbox("Purga realizada", key=f"leg_purga_acs_{id_orden}")
    aireador = st.checkbox("Aireador limpio/desinfectado", key=f"leg_aireador_acs_{id_orden}")
    revision = st.checkbox("Revisión visual correcta", key=f"leg_revision_acs_{id_orden}")

    terminales_revisados = st.number_input(
        "Terminales revisados",
        min_value=0,
        max_value=terminales,
        value=terminales,
        step=1,
        key=f"terminales_rev_acs_{id_orden}"
    )

    if terminales_revisados < terminales:
        st.warning(f"Solo se han revisado {terminales_revisados} de {terminales} terminales.")

    obs = (
        "Checklist ACS terminal: "
        + ("Purga realizada: Sí" if purga else "Purga realizada: No")
        + " | "
        + ("Aireador limpio/desinfectado: Sí" if aireador else "Aireador limpio/desinfectado: No")
        + " | "
        + ("Revisión visual correcta: Sí" if revision else "Revisión visual correcta: No")
        + f" | Terminales revisados: {terminales_revisados}/{terminales}"
    )

    return _base("Control ACS terminal", "ºC", valor, None, None, obs)


def mostrar_control_depositos_solares(id_orden):
    st.markdown("#### ☀️ Control conjunto de depósitos solares")
    st.caption(
        "Este control registra únicamente las temperaturas de los depósitos solares. "
        "La purga de fondo se realiza y registra en su tarea semanal independiente."
    )

    col1, col2 = st.columns(2)

    with col1:
        temperatura_1 = st.number_input(
            "Temperatura depósito solar 1 ºC",
            min_value=0.0,
            max_value=100.0,
            value=45.0,
            step=0.1,
            key=f"leg_solar_temp_1_{id_orden}"
        )

    with col2:
        temperatura_2 = st.number_input(
            "Temperatura depósito solar 2 ºC",
            min_value=0.0,
            max_value=100.0,
            value=45.0,
            step=0.1,
            key=f"leg_solar_temp_2_{id_orden}"
        )

    diferencia = abs(float(temperatura_1) - float(temperatura_2))

    st.metric(
        "Diferencia entre depósitos",
        f"{diferencia:.1f} ºC"
    )

    if diferencia <= 5:
        estado_diferencia = "Normal"
        st.success("🟢 Diferencia térmica normal")
    elif diferencia <= 10:
        estado_diferencia = "Revisar"
        st.warning("🟡 Diferencia térmica a revisar")
    else:
        estado_diferencia = "Elevada"
        st.error("🔴 Diferencia térmica elevada")

    datos_observaciones = [
        f"Temperatura depósito solar 1: {temperatura_1:.1f} ºC",
        f"Temperatura depósito solar 2: {temperatura_2:.1f} ºC",
        f"Diferencia térmica: {diferencia:.1f} ºC",
        f"Valoración diferencia: {estado_diferencia}",
        "Purga de fondo: controlada en tarea semanal independiente",
    ]

    return {
        "tipo_control": "Control depósitos solares",
        "unidad": "ºC",
        "valor": float(temperatura_1),
        "valor_2": float(temperatura_2),
        "valor_3": float(diferencia),
        "valido": True,
        "errores": [],
        "observaciones_extra": (
            "Control depósitos solares: "
            + " | ".join(datos_observaciones)
        ),
    }


def mostrar_control_terminal_completo(id_orden, terminales):
    valor = st.number_input("Temperatura AFS ºC", 0.0, 50.0, 18.0, 0.1, key=f"leg_temp_afs_completo_{id_orden}")
    valor_2 = st.number_input("Cloro residual libre mg/L", 0.0, 5.0, 0.5, 0.01, key=f"leg_cloro_completo_{id_orden}")
    valor_3 = st.number_input("Temperatura ACS terminal ºC", 0.0, 100.0, 50.0, 0.1, key=f"leg_temp_acs_completo_{id_orden}")

    purga = st.checkbox("Purga realizada", key=f"leg_purga_completo_{id_orden}")
    aireador = st.checkbox("Aireador limpio/desinfectado", key=f"leg_aireador_completo_{id_orden}")
    revision = st.checkbox("Revisión visual correcta", key=f"leg_revision_completo_{id_orden}")

    terminales_revisados = st.number_input(
        "Terminales revisados",
        min_value=0,
        max_value=terminales,
        value=terminales,
        step=1,
        key=f"terminales_rev_completo_{id_orden}"
    )

    if terminales_revisados < terminales:
        st.warning(f"Solo se han revisado {terminales_revisados} de {terminales} terminales.")

    obs = (
        "Checklist punto terminal completo: "
        + ("Purga realizada: Sí" if purga else "Purga realizada: No")
        + " | "
        + ("Aireador limpio/desinfectado: Sí" if aireador else "Aireador limpio/desinfectado: No")
        + " | "
        + ("Revisión visual correcta: Sí" if revision else "Revisión visual correcta: No")
        + f" | Terminales revisados: {terminales_revisados}/{terminales}"
    )

    return _base("Control punto terminal completo", "Control completo", valor, valor_2, valor_3, obs)



def mostrar_ruta_semanal_purgas_p9(id_orden):
    """
    Una sola OT semanal para AFS-04 y AFS-08.
    Solo es válida cuando ambos puntos han sido purgados.
    """
    st.markdown("### 🚰 Ruta semanal · puntos de poco uso")
    st.caption(
        "Completa los dos puntos. El resultado quedará registrado "
        "individualmente en AFS-04 y AFS-08."
    )

    with st.container(border=True):
        st.markdown("#### AFS-04 · Grifo comedor alumnos")
        purga_afs04 = st.checkbox(
            "Purga AFS-04 realizada",
            key=f"ruta_p9_afs04_purga_{id_orden}"
        )
        agua_afs04 = st.checkbox(
            "Agua transparente / sin anomalías",
            value=True,
            key=f"ruta_p9_afs04_agua_{id_orden}"
        )

    with st.container(border=True):
        st.markdown("#### AFS-08 · Grifo taller")
        purga_afs08 = st.checkbox(
            "Purga AFS-08 realizada",
            key=f"ruta_p9_afs08_purga_{id_orden}"
        )
        agua_afs08 = st.checkbox(
            "Agua transparente / sin anomalías",
            value=True,
            key=f"ruta_p9_afs08_agua_{id_orden}"
        )

    observaciones = st.text_area(
        "Observaciones de la ruta",
        key=f"ruta_p9_observaciones_{id_orden}"
    )

    completada = (
        purga_afs04
        and agua_afs04
        and purga_afs08
        and agua_afs08
    )

    errores = []

    if not purga_afs04:
        errores.append("Falta realizar la purga de AFS-04.")

    if not agua_afs04:
        errores.append("AFS-04 presenta agua no transparente o anomalía.")

    if not purga_afs08:
        errores.append("Falta realizar la purga de AFS-08.")

    if not agua_afs08:
        errores.append("AFS-08 presenta agua no transparente o anomalía.")

    observaciones_extra = (
        "Ruta semanal purgas P9: "
        f"AFS-04 purga={'Sí' if purga_afs04 else 'No'}, "
        f"agua correcta={'Sí' if agua_afs04 else 'No'} | "
        f"AFS-08 purga={'Sí' if purga_afs08 else 'No'}, "
        f"agua correcta={'Sí' if agua_afs08 else 'No'}"
    )

    if observaciones:
        observaciones_extra += f" | {observaciones}"

    return _base(
        "Ruta semanal purgas P9",
        "Sí/No",
        1 if completada else 0,
        1 if purga_afs04 and agua_afs04 else 0,
        1 if purga_afs08 and agua_afs08 else 0,
        observaciones_extra,
        valido=completada,
        errores=errores,
    )



def mostrar_revision_trimestral_acumulador_acs(id_orden):
    st.markdown("#### 🔧 Revisión trimestral acumulador ACS")
    st.caption(
        "Revisión del estado físico y de conservación del acumulador. "
        "La purga semanal se controla en una tarea independiente."
    )

    estado_general_ok = st.checkbox(
        "Estado exterior general correcto",
        key=f"rev_trim_estado_{id_orden}"
    )
    sin_fugas = st.checkbox(
        "Sin fugas visibles",
        key=f"rev_trim_fugas_{id_orden}"
    )
    sin_corrosion = st.checkbox(
        "Sin corrosión visible",
        key=f"rev_trim_corrosion_{id_orden}"
    )
    sin_incrustaciones = st.checkbox(
        "Sin incrustaciones o deterioro visible",
        key=f"rev_trim_incrustaciones_{id_orden}"
    )
    aislamiento_ok = st.checkbox(
        "Aislamiento exterior en buen estado",
        key=f"rev_trim_aislamiento_{id_orden}"
    )
    conexiones_ok = st.checkbox(
        "Conexiones, válvulas y elementos accesibles en buen estado",
        key=f"rev_trim_conexiones_{id_orden}"
    )

    revision_ok = all([
        estado_general_ok,
        sin_fugas,
        sin_corrosion,
        sin_incrustaciones,
        aislamiento_ok,
        conexiones_ok,
    ])

    if revision_ok:
        st.success("✅ Revisión visual del acumulador correcta")
    else:
        st.warning(
            "⚠️ La revisión quedará con incidencia mientras exista "
            "algún punto sin confirmar."
        )

    checklist = [
        "Estado exterior general: Correcto"
        if estado_general_ok
        else "Estado exterior general: Deficiencia",
        "Fugas visibles: No"
        if sin_fugas
        else "Fugas visibles: Sí / revisar",
        "Corrosión visible: No"
        if sin_corrosion
        else "Corrosión visible: Sí / revisar",
        "Incrustaciones/deterioro visible: No"
        if sin_incrustaciones
        else "Incrustaciones/deterioro visible: Sí / revisar",
        "Aislamiento exterior: Correcto"
        if aislamiento_ok
        else "Aislamiento exterior: Revisar",
        "Conexiones/válvulas accesibles: Correctas"
        if conexiones_ok
        else "Conexiones/válvulas accesibles: Revisar",
        "Purga semanal: controlada en tarea independiente",
    ]

    return _base(
        "Revisión trimestral acumulador ACS",
        "OK/KO",
        1 if revision_ok else 0,
        None,
        None,
        "Revisión trimestral acumulador ACS: " + " | ".join(checklist),
    )


def mostrar_revision_visual(id_orden):
    correcto = st.radio(
        "Resultado revisión visual",
        ["Correcto", "Deficiente"],
        horizontal=True,
        key=f"leg_revision_{id_orden}"
    )

    valor = 1 if correcto == "Correcto" else 0
    return _base("Revisión visual", "OK/KO", valor)


def mostrar_purga(id_orden, punto):
    st.markdown("### 🚰 Procedimiento de purga")

    tipo_punto = str(punto.get("tipo_punto", "") or "").lower()
    instalacion = str(punto.get("instalacion", "") or "").upper()

    es_acumulador = (
        "acs" in instalacion
        or tipo_punto in [
            "acumulador",
            "acumulador_solar",
            "deposito",
            "deposito_solar",
        ]
    )

    purga_realizada = st.checkbox(
        "☑ Purga de fondo realizada" if es_acumulador else "☑ Purga realizada",
        key=f"purga_realizada_{id_orden}"
    )

    agua_transparente = st.checkbox(
        "☑ Agua transparente / sin anomalías",
        value=True,
        key=f"purga_agua_{id_orden}"
    )

    valor = None
    unidad = ""

    # ------------------------------------------------
    # AFCH
    # ------------------------------------------------

    # En acumuladores/depósitos, la purga semanal de fondo no duplica
    # el control de temperatura, que se registra en su tarea específica.
    if not es_acumulador:
        unidad = "mg/L"

        valor = st.number_input(
            "🧪 Cloro residual",
            min_value=0.0,
            max_value=5.0,
            value=0.5,
            step=0.01,
            key=f"purga_cloro_{id_orden}"
        )

    observaciones = st.text_area(
        "📝 Observaciones",
        key=f"purga_obs_{id_orden}"
    )

    foto = st.file_uploader(
        "📷 Foto opcional",
        type=["jpg", "jpeg", "png"],
        key=f"purga_foto_{id_orden}"
    )

    errores = []

    if not purga_realizada:
        errores.append(
            "Debe confirmar que la purga de fondo se ha realizado."
            if es_acumulador
            else "Debe confirmar que la purga se ha realizado."
        )

    if not agua_transparente:
        errores.append("El agua presenta una anomalía. Indícala en observaciones.")

    observaciones_extra = (
        (
            f"Purga de fondo realizada: {'Sí' if purga_realizada else 'No'}"
            if es_acumulador
            else f"Purga realizada: {'Sí' if purga_realizada else 'No'}"
        )
        + " | "
        + f"Agua transparente / sin anomalías: {'Sí' if agua_transparente else 'No'}"
    )

    if observaciones:
        observaciones_extra += f" | {observaciones}"

    # La purga tiene dos datos distintos:
    # - valor: confirma si se ha realizado (1/0)
    # - valor_2: conserva el cloro cuando corresponde a una purga AFCH
    medicion = valor

    if unidad == "mg/L":
        observaciones_extra += (
            f" | Cloro residual: {float(medicion):.2f} mg/L"
        )

    return {
        "tipo_control": "Purga",
        "unidad": unidad,
        "valor": 1 if purga_realizada else 0,
        "valor_2": medicion,
        "valor_3": None,
        "foto": foto,
        "observaciones_extra": observaciones_extra,
        "valido": len(errores) == 0,
        "errores": errores,
    }



def mostrar_puesta_en_servicio_acumulador_acs(id_orden):
    st.markdown("### 💧 Puesta en servicio acumulador ACS")
    st.info(
        "Actuación extraordinaria tras vaciado, parada o intervención "
        "importante de la instalación."
    )

    deposito_llenado = st.checkbox(
        "☑ Acumulador / depósito completamente llenado",
        key=f"puesta_servicio_llenado_{id_orden}"
    )

    renovacion_agua = st.checkbox(
        "☑ Renovación completa de agua confirmada",
        key=f"puesta_servicio_renovacion_{id_orden}"
    )

    sin_fugas = st.checkbox(
        "☑ Sin fugas visibles",
        key=f"puesta_servicio_fugas_{id_orden}"
    )

    produccion_acs = st.checkbox(
        "☑ Producción ACS en servicio",
        key=f"puesta_servicio_produccion_{id_orden}"
    )

    valor = st.number_input(
        "🌡 Temperatura acumulador ºC",
        min_value=0.0,
        max_value=100.0,
        value=60.0,
        step=0.1,
        key=f"puesta_servicio_acum_{id_orden}"
    )

    valor_2 = st.number_input(
        "➡️ Temperatura impulsión ACS ºC",
        min_value=0.0,
        max_value=100.0,
        value=50.0,
        step=0.1,
        key=f"puesta_servicio_impulsion_{id_orden}"
    )

    valor_3 = st.number_input(
        "🔄 Temperatura retorno ACS ºC",
        min_value=0.0,
        max_value=100.0,
        value=50.0,
        step=0.1,
        key=f"puesta_servicio_retorno_{id_orden}"
    )

    errores = []

    if not deposito_llenado:
        errores.append("Falta confirmar el llenado completo del acumulador.")

    if not renovacion_agua:
        errores.append("Falta confirmar la renovación completa del agua.")

    if not sin_fugas:
        errores.append("Falta confirmar ausencia de fugas visibles.")

    if not produccion_acs:
        errores.append("Falta confirmar que la producción ACS está en servicio.")

    obs = (
        "Puesta en servicio acumulador ACS: "
        + ("Llenado completo: Sí" if deposito_llenado else "Llenado completo: No")
        + " | "
        + ("Renovación de agua: Sí" if renovacion_agua else "Renovación de agua: No")
        + " | "
        + ("Sin fugas: Sí" if sin_fugas else "Sin fugas: No")
        + " | "
        + ("Producción ACS en servicio: Sí" if produccion_acs else "Producción ACS en servicio: No")
        + f" | Temperatura acumulador: {valor:.1f} ºC"
        + f" | Impulsión ACS: {valor_2:.1f} ºC"
        + f" | Retorno ACS: {valor_3:.1f} ºC"
    )

    return _base(
        "Puesta en servicio acumulador ACS",
        "ºC",
        valor,
        valor_2,
        valor_3,
        obs,
        valido=len(errores) == 0,
        errores=errores,
    )


def mostrar_procedimiento_choque_termico(id_orden, terminales):
    st.markdown("### 🔥 Procedimiento de choque térmico")

    aviso = st.checkbox("Dirección / usuarios avisados", key=f"choque_aviso_{id_orden}")
    controlada = st.checkbox("Instalación controlada durante la actuación", key=f"choque_controlada_{id_orden}")

    valor = st.number_input("Temperatura máxima acumulador ºC", 0.0, 100.0, 70.0, 0.1, key=f"choque_temp_acum_{id_orden}")
    valor_2 = st.number_input("Temperatura máxima terminal ºC", 0.0, 100.0, 65.0, 0.1, key=f"choque_temp_terminal_{id_orden}")

    tiempo = st.number_input(
        "Tiempo mantenido sobre consigna (min)",
        min_value=0,
        max_value=240,
        value=30,
        step=5,
        key=f"choque_tiempo_{id_orden}"
    )

    terminales_purgados = st.number_input(
        "Terminales purgados",
        min_value=0,
        max_value=terminales,
        value=terminales,
        step=1,
        key=f"choque_terminales_{id_orden}"
    )

    sin_incidencias = st.checkbox("Sin incidencias visibles", key=f"choque_sin_incidencias_{id_orden}")

    errores = []

    if not aviso:
        errores.append("Falta confirmar aviso a dirección / usuarios.")

    if not controlada:
        errores.append("Falta confirmar instalación controlada.")

    if valor < 70:
        errores.append("El acumulador no alcanza 70 ºC.")

    if terminales_purgados < terminales:
        errores.append("Faltan terminales por purgar.")

    obs = (
        "Procedimiento choque térmico: "
        + ("Aviso realizado: Sí" if aviso else "Aviso realizado: No")
        + " | "
        + ("Instalación controlada: Sí" if controlada else "Instalación controlada: No")
        + f" | Temperatura acumulador: {valor} ºC"
        + f" | Temperatura terminal: {valor_2} ºC"
        + f" | Tiempo mantenimiento: {tiempo} min"
        + f" | Terminales purgados: {terminales_purgados}/{terminales}"
        + " | "
        + ("Sin incidencias visibles: Sí" if sin_incidencias else "Sin incidencias visibles: No")
    )

    return _base(
        "Choque térmico",
        "ºC",
        valor,
        valor_2,
        None,
        obs,
        valido=len(errores) == 0,
        errores=errores
    )


def mostrar_limpieza_desinfeccion(id_orden, tarea):
    st.markdown("### 🧼 Limpieza y desinfección")

    realizada = st.checkbox("Limpieza realizada", key=f"limpieza_realizada_{id_orden}")
    desinfeccion = st.checkbox("Desinfección realizada", key=f"desinfeccion_realizada_{id_orden}")
    aclarado = st.checkbox("Aclarado / puesta en servicio correcta", key=f"limpieza_aclarado_{id_orden}")

    empresa = st.text_input("Empresa / técnico", key=f"limpieza_empresa_{id_orden}")

    errores = []

    if not realizada:
        errores.append("Falta confirmar limpieza realizada.")

    if not desinfeccion:
        errores.append("Falta confirmar desinfección realizada.")

    if not aclarado:
        errores.append("Falta confirmar aclarado / puesta en servicio.")

    obs = (
        f"Procedimiento {tarea}: "
        + ("Limpieza: Sí" if realizada else "Limpieza: No")
        + " | "
        + ("Desinfección: Sí" if desinfeccion else "Desinfección: No")
        + " | "
        + ("Aclarado / servicio: Sí" if aclarado else "Aclarado / servicio: No")
        + f" | Empresa/técnico: {empresa or '-'}"
    )

    valor = 1 if realizada and desinfeccion and aclarado else 0

    return _base(tarea, "Sí/No", valor, None, None, obs, valido=len(errores) == 0, errores=errores)


def mostrar_control_generico(id_orden, tarea):
    valor = st.number_input(
        "Valor del control",
        min_value=0.0,
        max_value=999.0,
        value=0.0,
        step=0.1,
        key=f"leg_valor_generico_{id_orden}"
    )

    return _base(tarea, "", valor)
