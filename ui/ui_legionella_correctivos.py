import streamlit as st

from modules.legionella_correctivos_datos import (
    obtener_correctivo_especializado,
    guardar_correctivo_especializado,
    borrar_correctivo_especializado,
)
from modules.procedimientos_correctivos_legionella import (
    identificar_tipo_correctivo,
    validar_correctivo_especializado,
)

from ui.ui_legionella import (
    obtener_checklist_correctivo_legionella,
    guardar_checklist_correctivo_legionella,
    borrar_checklist_correctivo_legionella,
)


def _valor(datos, clave, defecto=False):
    return bool((datos or {}).get(clave, defecto))


def _guardar_especializado(numero_ot, tipo, datos, completo):
    guardar_correctivo_especializado(numero_ot, tipo, datos, completo)
    st.success("Checklist correctivo guardado.")
    st.rerun()


def _pie_guardar_reset(numero_ot, tipo, datos, completo):
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            f"💾 Guardar checklist {numero_ot}",
            key=f"guardar_correctivo_{tipo}_{numero_ot}",
            use_container_width=True,
        ):
            _guardar_especializado(numero_ot, tipo, datos, completo)
    with c2:
        if st.button(
            f"🗑️ Reiniciar checklist {numero_ot}",
            key=f"reset_correctivo_{tipo}_{numero_ot}",
            use_container_width=True,
        ):
            borrar_correctivo_especializado(numero_ot, tipo)
            st.warning("Checklist reiniciado.")
            st.rerun()

    if completo:
        st.success("Correctivo completado. Ya puedes finalizar la OT.")
    else:
        st.warning("Guarda y completa los puntos obligatorios antes de finalizar.")
    return completo


def mostrar_correctivo_temperatura(num_ot, centro, edificio, espacio, desc):
    st.markdown("### 🌡️ Checklist correctivo de temperatura")
    checklist = obtener_checklist_correctivo_legionella(num_ot) or {}

    revisar_consigna = st.checkbox("Revisar consigna acumulador", value=bool(checklist.get("revisar_consigna", 0)), key=f"leg_consigna_op_{num_ot}")
    revisar_termostato = st.checkbox("Revisar termostato", value=bool(checklist.get("revisar_termostato", 0)), key=f"leg_termostato_op_{num_ot}")
    revisar_caldera = st.checkbox("Revisar caldera", value=bool(checklist.get("revisar_caldera", 0)), key=f"leg_caldera_op_{num_ot}")
    revisar_resistencia = st.checkbox("Revisar resistencia eléctrica", value=bool(checklist.get("revisar_resistencia", 0)), key=f"leg_resistencia_op_{num_ot}")
    revisar_recirculacion = st.checkbox("Revisar recirculación", value=bool(checklist.get("revisar_recirculacion", 0)), key=f"leg_recirculacion_op_{num_ot}")
    revisar_bomba = st.checkbox("Revisar bomba retorno", value=bool(checklist.get("revisar_bomba", 0)), key=f"leg_bomba_op_{num_ot}")
    purgar_aire = st.checkbox("Purgar aire circuito", value=bool(checklist.get("purgar_aire", 0)), key=f"leg_aire_op_{num_ot}")
    esperar_recuperacion = st.checkbox("Esperar recuperación térmica", value=bool(checklist.get("esperar_recuperacion", 0)), key=f"leg_recuperacion_op_{num_ot}")
    nueva_medicion = st.checkbox("Realizar nueva medición", value=bool(checklist.get("nueva_medicion", 0)), key=f"leg_medicion_op_{num_ot}")

    opciones_causa = ["", "Consigna incorrecta", "Termostato", "Caldera", "Resistencia", "Recirculación / bomba", "Aire en circuito", "Empresa externa pendiente", "Otra"]
    causa_guardada = str(checklist.get("causa_detectada", ""))
    causa_detectada = st.selectbox("Causa detectada", opciones_causa, index=opciones_causa.index(causa_guardada) if causa_guardada in opciones_causa else 0, key=f"leg_causa_op_{num_ot}")
    temperatura_final = st.number_input("Temperatura final ºC", min_value=0.0, max_value=100.0, value=float(checklist.get("temperatura_final", 0) or 0), step=0.1, key=f"leg_temp_op_{num_ot}")
    empresa_externa = st.text_input("Empresa externa / técnico", value=str(checklist.get("empresa_externa", "")), key=f"leg_empresa_op_{num_ot}")
    observaciones = st.text_area("Observaciones correctivo", value=str(checklist.get("observaciones", "")), key=f"leg_obs_op_{num_ot}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"💾 Guardar checklist {num_ot}", key=f"guardar_leg_op_{num_ot}", use_container_width=True):
            guardar_checklist_correctivo_legionella(num_ot, centro, edificio, espacio, desc, {
                "revisar_consigna": int(revisar_consigna), "revisar_termostato": int(revisar_termostato),
                "revisar_caldera": int(revisar_caldera), "revisar_resistencia": int(revisar_resistencia),
                "revisar_recirculacion": int(revisar_recirculacion), "revisar_bomba": int(revisar_bomba),
                "purgar_aire": int(purgar_aire), "esperar_recuperacion": int(esperar_recuperacion),
                "nueva_medicion": int(nueva_medicion), "causa_detectada": causa_detectada,
                "temperatura_final": temperatura_final, "empresa_externa": empresa_externa,
                "observaciones": observaciones,
            })
            st.success("Checklist Legionella guardado.")
            st.rerun()
    with c2:
        if st.button(f"🗑️ Reset checklist {num_ot}", key=f"reset_leg_op_{num_ot}", use_container_width=True):
            borrar_checklist_correctivo_legionella(num_ot)
            st.warning("Checklist reiniciado.")
            st.rerun()

    completo = bool(causa_detectada.strip()) and nueva_medicion and temperatura_final >= 50
    if completo:
        st.success("Correctivo de temperatura completado.")
    else:
        st.warning("Falta causa, nueva medición o temperatura final válida.")
    return completo


def mostrar_correctivo_purga(num_ot, desc):
    tipo = "purga"
    datos = obtener_correctivo_especializado(num_ot, tipo) or {}
    st.markdown("### 🚿 Checklist correctivo de purga")
    st.caption(f"Tarea detectada: {extraer_tarea_correctivo(desc) or 'Purga'}")

    acceso = st.checkbox("Comprobar acceso al punto", value=_valor(datos, "acceso"), key=f"purga_acceso_{num_ot}")
    valvula = st.checkbox("Comprobar funcionamiento de la válvula de purga", value=_valor(datos, "valvula"), key=f"purga_valvula_{num_ot}")
    realizada = st.checkbox("Realizar la purga", value=_valor(datos, "realizada"), key=f"purga_realizada_{num_ot}")
    salida = st.checkbox("Verificar salida continua de agua", value=_valor(datos, "salida_continua"), key=f"purga_salida_{num_ot}")
    sin_sedimentos = st.checkbox("Sin aire o sedimentos anormales", value=_valor(datos, "sin_sedimentos"), key=f"purga_sedimentos_{num_ot}")
    cierre = st.checkbox("Comprobar cierre correcto de la válvula", value=_valor(datos, "cierre"), key=f"purga_cierre_{num_ot}")
    sin_fugas = st.checkbox("Confirmar que no hay fugas", value=_valor(datos, "sin_fugas"), key=f"purga_fugas_{num_ot}")
    duracion = st.number_input("Duración aproximada de la purga (minutos)", min_value=0, max_value=120, value=int(datos.get("duracion", 0) or 0), step=1, key=f"purga_duracion_{num_ot}")
    resultado = st.selectbox("Resultado final", ["", "Correcto", "Pendiente reparación", "Pendiente empresa externa"], index=["", "Correcto", "Pendiente reparación", "Pendiente empresa externa"].index(datos.get("resultado", "")) if datos.get("resultado", "") in ["", "Correcto", "Pendiente reparación", "Pendiente empresa externa"] else 0, key=f"purga_resultado_{num_ot}")
    incidencia = st.text_area("Incidencia encontrada / actuación realizada", value=str(datos.get("incidencia", "")), key=f"purga_incidencia_{num_ot}")
    empresa = st.text_input("Empresa externa / técnico (si procede)", value=str(datos.get("empresa", "")), key=f"purga_empresa_{num_ot}")

    nuevos = {"acceso": acceso, "valvula": valvula, "realizada": realizada, "salida_continua": salida, "sin_sedimentos": sin_sedimentos, "cierre": cierre, "sin_fugas": sin_fugas, "duracion": duracion, "resultado": resultado, "incidencia": incidencia, "empresa": empresa}
    completo = validar_correctivo_especializado(tipo, nuevos)
    return _pie_guardar_reset(num_ot, tipo, nuevos, completo)


def _mostrar_correctivo_medicion(num_ot, tipo, titulo, unidad, minimo=0.0, maximo=100.0):
    datos = obtener_correctivo_especializado(num_ot, tipo) or {}
    st.markdown(f"### {titulo}")
    confirmar = st.checkbox("Confirmar medición inicial", value=_valor(datos, "confirmar"), key=f"{tipo}_confirmar_{num_ot}")
    revisar = st.checkbox("Revisar instalación y causa probable", value=_valor(datos, "revisar"), key=f"{tipo}_revisar_{num_ot}")
    actuar = st.checkbox("Realizar actuación correctora", value=_valor(datos, "actuar"), key=f"{tipo}_actuar_{num_ot}")
    repetir = st.checkbox("Repetir medición", value=_valor(datos, "repetir"), key=f"{tipo}_repetir_{num_ot}")
    valor_final = st.number_input(f"Valor final ({unidad})", min_value=minimo, max_value=maximo, value=float(datos.get("valor_final", 0) or 0), step=0.1, key=f"{tipo}_valor_{num_ot}")
    causa = st.text_input("Causa detectada", value=str(datos.get("causa", "")), key=f"{tipo}_causa_{num_ot}")
    observaciones = st.text_area("Actuación y observaciones", value=str(datos.get("observaciones", "")), key=f"{tipo}_obs_{num_ot}")
    nuevos = {"confirmar": confirmar, "revisar": revisar, "actuar": actuar, "repetir": repetir, "valor_final": valor_final, "causa": causa, "observaciones": observaciones}
    completo = validar_correctivo_especializado(tipo, nuevos)
    return _pie_guardar_reset(num_ot, tipo, nuevos, completo)


def mostrar_correctivo_bomba(num_ot):
    tipo = "bomba_recirculacion"
    datos = obtener_correctivo_especializado(num_ot, tipo) or {}
    st.markdown("### 🔄 Checklist correctivo de bomba / recirculación")
    campos = [
        ("alimentacion", "Comprobar alimentación eléctrica"), ("protecciones", "Revisar protecciones"),
        ("marcha", "Comprobar señal de marcha"), ("bomba", "Comprobar funcionamiento de la bomba"),
        ("valvulas", "Comprobar posición de válvulas"), ("aire", "Comprobar aire en circuito"),
        ("circulacion", "Verificar caudal o circulación"), ("retorno", "Comprobar temperatura de retorno"),
    ]
    valores = {clave: st.checkbox(etiqueta, value=_valor(datos, clave), key=f"bomba_{clave}_{num_ot}") for clave, etiqueta in campos}
    resultado = st.selectbox("Resultado final", ["", "Funcionando", "Pendiente reparación", "Pendiente empresa externa"], index=["", "Funcionando", "Pendiente reparación", "Pendiente empresa externa"].index(datos.get("resultado", "")) if datos.get("resultado", "") in ["", "Funcionando", "Pendiente reparación", "Pendiente empresa externa"] else 0, key=f"bomba_resultado_{num_ot}")
    causa = st.text_input("Causa detectada", value=str(datos.get("causa", "")), key=f"bomba_causa_{num_ot}")
    observaciones = st.text_area("Reparación / observaciones", value=str(datos.get("observaciones", "")), key=f"bomba_obs_{num_ot}")
    nuevos = {**valores, "resultado": resultado, "causa": causa, "observaciones": observaciones}
    completo = validar_correctivo_especializado(tipo, nuevos)
    return _pie_guardar_reset(num_ot, tipo, nuevos, completo)


def mostrar_correctivo_visual(num_ot):
    tipo = "visual_limpieza"
    datos = obtener_correctivo_especializado(num_ot, tipo) or {}
    st.markdown("### 🧼 Checklist correctivo visual / limpieza")
    defecto = st.checkbox("Identificar el defecto", value=_valor(datos, "defecto"), key=f"visual_defecto_{num_ot}")
    revisar = st.checkbox("Comprobar suciedad, incrustaciones o corrosión", value=_valor(datos, "revisar"), key=f"visual_revisar_{num_ot}")
    limpiar = st.checkbox("Limpiar el elemento", value=_valor(datos, "limpiar"), key=f"visual_limpiar_{num_ot}")
    desinfectar = st.checkbox("Desinfectar si procede", value=_valor(datos, "desinfectar"), key=f"visual_desinfectar_{num_ot}")
    juntas = st.checkbox("Revisar juntas, tapas y cierres", value=_valor(datos, "juntas"), key=f"visual_juntas_{num_ot}")
    sin_fugas = st.checkbox("Verificar ausencia de fugas", value=_valor(datos, "sin_fugas"), key=f"visual_fugas_{num_ot}")
    resultado = st.selectbox("Resultado final", ["", "Correcto", "Pendiente sustitución", "Pendiente empresa externa"], index=["", "Correcto", "Pendiente sustitución", "Pendiente empresa externa"].index(datos.get("resultado", "")) if datos.get("resultado", "") in ["", "Correcto", "Pendiente sustitución", "Pendiente empresa externa"] else 0, key=f"visual_resultado_{num_ot}")
    producto = st.text_input("Producto utilizado (si procede)", value=str(datos.get("producto", "")), key=f"visual_producto_{num_ot}")
    observaciones = st.text_area("Actuación / observaciones", value=str(datos.get("observaciones", "")), key=f"visual_obs_{num_ot}")
    nuevos = {"defecto": defecto, "revisar": revisar, "limpiar": limpiar, "desinfectar": desinfectar, "juntas": juntas, "sin_fugas": sin_fugas, "resultado": resultado, "producto": producto, "observaciones": observaciones}
    completo = validar_correctivo_especializado(tipo, nuevos)
    return _pie_guardar_reset(num_ot, tipo, nuevos, completo)


def mostrar_correctivo_generico(num_ot, desc):
    tipo = "generico"
    datos = obtener_correctivo_especializado(num_ot, tipo) or {}
    st.markdown("### 🛠️ Checklist correctivo Legionella")
    st.info("Tipo no reconocido automáticamente. Se aplica un checklist general seguro.")
    identificado = st.checkbox("Defecto identificado", value=_valor(datos, "identificado"), key=f"gen_identificado_{num_ot}")
    actuacion = st.checkbox("Actuación correctora realizada", value=_valor(datos, "actuacion"), key=f"gen_actuacion_{num_ot}")
    verificacion = st.checkbox("Verificación final realizada", value=_valor(datos, "verificacion"), key=f"gen_verificacion_{num_ot}")
    resultado = st.selectbox("Resultado final", ["", "Correcto", "Pendiente reparación", "Pendiente empresa externa"], index=["", "Correcto", "Pendiente reparación", "Pendiente empresa externa"].index(datos.get("resultado", "")) if datos.get("resultado", "") in ["", "Correcto", "Pendiente reparación", "Pendiente empresa externa"] else 0, key=f"gen_resultado_{num_ot}")
    causa = st.text_input("Causa detectada", value=str(datos.get("causa", "")), key=f"gen_causa_{num_ot}")
    observaciones = st.text_area("Actuación / observaciones", value=str(datos.get("observaciones", "")), key=f"gen_obs_{num_ot}")
    nuevos = {"identificado": identificado, "actuacion": actuacion, "verificacion": verificacion, "resultado": resultado, "causa": causa, "observaciones": observaciones, "descripcion": desc}
    completo = validar_correctivo_especializado(tipo, nuevos)
    return _pie_guardar_reset(num_ot, tipo, nuevos, completo)


def mostrar_checklist_correctivo_legionella(num_ot, centro, edificio, espacio, desc):
    tipo = identificar_tipo_correctivo(desc)
    if tipo == "temperatura":
        return mostrar_correctivo_temperatura(num_ot, centro, edificio, espacio, desc)
    if tipo == "purga":
        return mostrar_correctivo_purga(num_ot, desc)
    if tipo == "cloro":
        return _mostrar_correctivo_medicion(num_ot, "cloro", "🧪 Correctivo de cloro residual", "mg/L", 0.0, 5.0)
    if tipo == "afs_temperatura":
        return _mostrar_correctivo_medicion(num_ot, "afs_temperatura", "❄️ Correctivo de temperatura AFS", "ºC", 0.0, 50.0)
    if tipo == "bomba_recirculacion":
        return mostrar_correctivo_bomba(num_ot)
    if tipo == "visual_limpieza":
        return mostrar_correctivo_visual(num_ot)
    return mostrar_correctivo_generico(num_ot, desc)


def correctivo_legionella_completo(numero_ot, descripcion):
    tipo = identificar_tipo_correctivo(descripcion)
    if tipo == "temperatura":
        checklist = obtener_checklist_correctivo_legionella(numero_ot) or {}
        return bool(str(checklist.get("causa_detectada") or "").strip()) and bool(checklist.get("nueva_medicion", 0)) and float(checklist.get("temperatura_final", 0) or 0) >= 50

    datos = obtener_correctivo_especializado(numero_ot, tipo)
    return bool(datos and datos.get("_completado", False))
