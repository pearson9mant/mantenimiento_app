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


def mostrar_revision_visual(id_orden):
    correcto = st.radio(
        "Resultado revisión visual",
        ["Correcto", "Deficiente"],
        horizontal=True,
        key=f"leg_revision_{id_orden}"
    )

    valor = 1 if correcto == "Correcto" else 0
    return _base("Revisión visual", "OK/KO", valor)


def mostrar_purga(id_orden):
    purga = st.radio(
        "Purga realizada",
        ["Sí", "No"],
        horizontal=True,
        key=f"leg_purga_{id_orden}"
    )

    valor = 1 if purga == "Sí" else 0
    return _base("Purga", "Sí/No", valor)


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
