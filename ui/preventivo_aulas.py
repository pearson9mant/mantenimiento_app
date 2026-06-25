import streamlit as st
from pathlib import Path

from config import CENTROS, EDIFICIOS, OPERARIOS
from modules.ubicaciones import obtener_espacios
from modules.preventivo_aulas import (
    crear_tablas_preventivo_aulas,
    crear_revision_aula,
    obtener_revisiones_aulas,
    obtener_revision_aula,
    obtener_items_revision_aula,
    actualizar_item_revision_aula,
    cerrar_revision_aula,
    crear_correctivos_desde_revision,
    resumen_revision_aula,
    ESTADOS_REVISION_AULA,
)


def limpiar_nombre_archivo(texto):
    texto = str(texto or "")
    caracteres_malos = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for c in caracteres_malos:
        texto = texto.replace(c, "_")
    return texto.replace(" ", "_")


def guardar_foto_revision_aula(foto, revision_id, item_id, elemento):
    if foto is None:
        return ""

    carpeta = Path("uploads/preventivo_aulas")
    carpeta.mkdir(parents=True, exist_ok=True)

    extension = foto.name.split(".")[-1].lower()
    nombre = limpiar_nombre_archivo(
        f"revision_{revision_id}_item_{item_id}_{elemento}.{extension}"
    )

    ruta = carpeta / nombre

    with open(ruta, "wb") as f:
        f.write(foto.getvalue())

    return str(ruta)


def operario_por_centro(centro):
    if centro == "Pearson 9":
        return "Luis Lozano"
    if centro == "Pearson 22":
        return "J.A. Almeda"
    return OPERARIOS[0] if OPERARIOS else ""


def pantalla_preventivo_aulas():
    crear_tablas_preventivo_aulas()

    st.subheader("🏫 Preventivo de aulas")

    tab1, tab2 = st.tabs(["➕ Nueva revisión", "📋 Revisiones"])

    with tab1:
        centro = st.selectbox("Centro", CENTROS, key="prev_aula_centro")

        edificios_disponibles = EDIFICIOS.get(centro, [])
        edificio = st.selectbox(
            "Edificio",
            edificios_disponibles,
            key=f"prev_aula_edificio_{centro}"
        )

        espacios_disponibles = obtener_espacios(edificio, centro)

        espacio_sel = st.selectbox(
            "Aula / espacio",
            espacios_disponibles,
            key=f"prev_aula_espacio_{centro}_{edificio}"
        )

        if espacio_sel == "Otro":
            espacio = st.text_input("Especificar aula / espacio", key="prev_aula_espacio_otro")
        else:
            espacio = espacio_sel

        operario_auto = operario_por_centro(centro)

        if operario_auto in OPERARIOS:
            indice_operario = OPERARIOS.index(operario_auto)
        else:
            indice_operario = 0

        operario_sel = st.selectbox(
            "Operario",
            OPERARIOS,
            index=indice_operario,
            key=f"prev_aula_operario_{centro}"
        )

        if operario_sel == "Otro":
            operario = st.text_input("Nombre operario", key="prev_aula_operario_otro")
        else:
            operario = operario_sel

        observaciones = st.text_area(
            "Observaciones iniciales",
            key="prev_aula_obs_iniciales"
        )

        if st.button("✅ Crear revisión de aula", use_container_width=True):
            if not str(espacio).strip():
                st.warning("Indica un aula o espacio.")
            elif not str(operario).strip():
                st.warning("Indica un operario.")
            else:
                revision_id = crear_revision_aula(
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    operario=operario,
                    observaciones=observaciones,
                )

                st.session_state["revision_aula_activa"] = revision_id
                st.success("Revisión de aula creada correctamente")
                st.rerun()

    with tab2:
        revisiones = obtener_revisiones_aulas(100)

        if not revisiones:
            st.info("No hay revisiones de aula.")
        else:
            for rev in revisiones:
                (
                    revision_id,
                    fecha,
                    centro,
                    edificio,
                    espacio,
                    operario,
                    estado,
                    observaciones,
                    numero_ot_preventiva,
                ) = rev

                resumen = resumen_revision_aula(revision_id)

                titulo = (
                    f"{fecha or '-'} | {centro} · {edificio} · {espacio} | "
                    f"{estado} | Averías: {resumen['averias']} | Revisar: {resumen['revisar']}"
                )

                with st.expander(titulo):
                    st.markdown(
                        f"""
                        🏢 **Centro:** {centro}  
                        🏫 **Edificio:** {edificio}  
                        🚪 **Aula / espacio:** {espacio}  
                        👷 **Operario:** {operario or '-'}  
                        📌 **Estado:** {estado or '-'}  
                        🧾 **OT preventiva origen:** {numero_ot_preventiva or '-'}
                        """
                    )

                    if observaciones:
                        st.markdown("**Observaciones iniciales:**")
                        st.write(observaciones)

                    items = obtener_items_revision_aula(revision_id)

                    st.markdown("### Revisión de elementos")

                    for item in items:
                        (
                            item_id,
                            _revision_id,
                            elemento,
                            estado_item,
                            obs_item,
                            foto,
                            crear_correctivo,
                            numero_ot_correctiva,
                        ) = item

                        st.markdown("---")
                        st.markdown(f"#### {elemento}")

                        col1, col2 = st.columns([2, 1])

                        with col1:
                            estado_nuevo = st.radio(
                                "Estado",
                                ESTADOS_REVISION_AULA,
                                index=ESTADOS_REVISION_AULA.index(estado_item)
                                if estado_item in ESTADOS_REVISION_AULA
                                else 0,
                                horizontal=True,
                                key=f"estado_aula_item_{item_id}",
                            )

                            obs_nueva = st.text_area(
                                "Observaciones",
                                value=obs_item or "",
                                key=f"obs_aula_item_{item_id}",
                            )

                            crear_corr_nuevo = False

                            if estado_nuevo == "Avería":
                                crear_corr_nuevo = st.checkbox(
                                    "Crear OT correctiva al cerrar/guardar",
                                    value=True if not numero_ot_correctiva else False,
                                    disabled=True if numero_ot_correctiva else False,
                                    key=f"crear_corr_aula_item_{item_id}",
                                )

                                if numero_ot_correctiva:
                                    st.success(f"OT correctiva creada: {numero_ot_correctiva}")

                            elif estado_nuevo == "Revisar":
                                st.info("Quedará registrado como pendiente de revisar, sin crear correctivo automático.")

                        with col2:
                            if foto:
                                try:
                                    st.image(foto, caption="Foto", use_container_width=True)
                                except Exception:
                                    st.caption("Foto no disponible.")

                            foto_nueva = st.file_uploader(
                                "Foto",
                                type=["jpg", "jpeg", "png"],
                                key=f"foto_aula_item_{item_id}",
                            )

                        if st.button("💾 Guardar elemento", key=f"guardar_aula_item_{item_id}"):
                            ruta_foto = foto or ""

                            if foto_nueva is not None:
                                if foto_nueva.size > 5 * 1024 * 1024:
                                    st.error("La foto supera 5 MB.")
                                    return

                                try:
                                    ruta_foto = guardar_foto_revision_aula(
                                        foto_nueva,
                                        revision_id,
                                        item_id,
                                        elemento,
                                    )
                                except Exception as e:
                                    st.error(f"Error guardando foto: {e}")
                                    return

                            actualizar_item_revision_aula(
                                item_id=item_id,
                                estado=estado_nuevo,
                                observaciones=obs_nueva,
                                foto=ruta_foto,
                                crear_correctivo=crear_corr_nuevo,
                            )

                            st.success("Elemento guardado")
                            st.rerun()

                    st.markdown("---")
                    st.markdown("### Cierre de revisión")

                    resumen = resumen_revision_aula(revision_id)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Correctos", resumen["correctos"])
                    c2.metric("Revisar", resumen["revisar"])
                    c3.metric("Averías", resumen["averias"])

                    observaciones_cierre = st.text_area(
                        "Observaciones de cierre",
                        value=observaciones or "",
                        key=f"obs_cierre_revision_aula_{revision_id}",
                    )

                    col_a, col_b = st.columns(2)

                    with col_a:
                        if st.button("🔧 Crear correctivos de averías", key=f"crear_corr_revision_{revision_id}"):
                            creadas = crear_correctivos_desde_revision(revision_id)

                            if creadas > 0:
                                st.success(f"Se han creado {creadas} OTs correctivas.")
                            else:
                                st.info("No hay averías pendientes de generar OT.")

                            st.rerun()

                    with col_b:
                        if st.button("✅ Cerrar revisión", key=f"cerrar_revision_aula_{revision_id}"):
                            cerrar_revision_aula(
                                revision_id=revision_id,
                                observaciones=observaciones_cierre,
                            )
                            st.success("Revisión cerrada")
                            st.rerun()
