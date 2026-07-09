import streamlit as st


def mostrar_procedimiento_choque_termico(id_orden, terminales):
    tipo_control = "Choque térmico"
    unidad = "ºC"

    st.markdown("### 🔥 Procedimiento de choque térmico")

    aviso_realizado = st.checkbox(
        "Dirección / usuarios avisados",
        key=f"choque_aviso_{id_orden}"
    )

    instalacion_controlada = st.checkbox(
        "Instalación controlada durante la actuación",
        key=f"choque_controlada_{id_orden}"
    )

    valor = st.number_input(
        "Temperatura máxima acumulador ºC",
        min_value=0.0,
        max_value=100.0,
        value=70.0,
        step=0.1,
        key=f"choque_temp_acum_{id_orden}"
    )

    valor_2 = st.number_input(
        "Temperatura máxima terminal ºC",
        min_value=0.0,
        max_value=100.0,
        value=65.0,
        step=0.1,
        key=f"choque_temp_terminal_{id_orden}"
    )

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

    sin_incidencias = st.checkbox(
        "Sin incidencias visibles",
        key=f"choque_sin_incidencias_{id_orden}"
    )

    checklist = [
        "Aviso realizado: Sí" if aviso_realizado else "Aviso realizado: No",
        "Instalación controlada: Sí" if instalacion_controlada else "Instalación controlada: No",
        f"Temperatura acumulador: {valor} ºC",
        f"Temperatura terminal: {valor_2} ºC",
        f"Tiempo mantenimiento: {tiempo} min",
        f"Terminales purgados: {terminales_purgados}/{terminales}",
        "Sin incidencias visibles: Sí" if sin_incidencias else "Sin incidencias visibles: No",
    ]

    valido = True
    errores = []

    if not aviso_realizado:
        valido = False
        errores.append("Falta confirmar aviso a dirección / usuarios.")

    if not instalacion_controlada:
        valido = False
        errores.append("Falta confirmar instalación controlada.")

    if valor < 70:
        valido = False
        errores.append("El acumulador no alcanza 70 ºC.")

    if terminales_purgados < terminales:
        valido = False
        errores.append("Faltan terminales por purgar.")

    return {
        "tipo_control": tipo_control,
        "unidad": unidad,
        "valor": valor,
        "valor_2": valor_2,
        "valor_3": None,
        "valido": valido,
        "errores": errores,
        "observaciones_extra": "Procedimiento choque térmico: " + " | ".join(checklist),
    }
