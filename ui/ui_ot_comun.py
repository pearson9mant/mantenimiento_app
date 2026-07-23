import streamlit as st

from database.db import conectar, _sql
from modules.ordenes import (
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    obtener_fotos_ot,
)
from modules.espacios import (
    obtener_centros_espacios,
    obtener_edificios_espacios,
    obtener_plantas_espacios,
    obtener_espacios_por_planta,
)


def perfil_actual():
    return str(
        st.session_state.get("perfil")
        or st.session_state.get("rol")
        or st.session_state.get("tipo_usuario")
        or st.session_state.get("modo")
        or ""
    ).strip().lower()


def puede_editar_ubicacion_ot():
    return perfil_actual() in [
        "admin",
        "administrador",
        "administracion",
        "administración",
    ]


def obtener_ot_por_id(id_orden):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id, numero_ot, descripcion, estado, fecha_creacion,
                   centro, edificio, planta, espacio, area, prioridad,
                   operario, origen, solicitante, fecha_origen, foto
            FROM ordenes_trabajo
            WHERE id = ?
        """), (id_orden,))

        fila = cur.fetchone()
    except Exception:
        fila = None

    conn.close()
    return fila


def actualizar_ubicacion_ot(
    id_orden,
    centro,
    edificio,
    planta,
    espacio,
):
    centro = str(centro or "").strip()
    edificio = str(edificio or "").strip()
    planta = str(planta or "").strip()
    espacio = str(espacio or "").strip()

    if not id_orden:
        return False, "No se ha podido identificar la OT."

    if not centro:
        return False, "Selecciona el centro."

    if not edificio:
        return False, "Selecciona el edificio."

    if not planta:
        return False, "Selecciona la planta."

    if not espacio:
        return False, "Selecciona el espacio."

    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            UPDATE ordenes_trabajo
            SET centro = ?,
                edificio = ?,
                planta = ?,
                espacio = ?
            WHERE id = ?
        """), (
            centro,
            edificio,
            planta,
            espacio,
            id_orden,
        ))

        conn.commit()
        return True, "Ubicación actualizada correctamente."

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo actualizar la ubicación: {e}"

    finally:
        conn.close()


def _indice_seguro(opciones, valor_actual):
    if not opciones:
        return 0

    valor_actual = str(valor_actual or "").strip()

    if valor_actual in opciones:
        return opciones.index(valor_actual)

    return 0


def mostrar_editor_ubicacion_ot(
    id_ot,
    centro_actual,
    edificio_actual,
    planta_actual,
    espacio_actual,
    prefijo,
):
    if not puede_editar_ubicacion_ot():
        return

    with st.expander(
        "✏️ Corregir ubicación",
        expanded=False,
    ):
        st.caption(
            "Este cambio modifica únicamente la ubicación de la OT. "
            "No altera el estado, las observaciones, las fotos ni los materiales."
        )

        centros = obtener_centros_espacios()

        if not centros:
            st.warning(
                "No hay centros registrados en el catálogo de espacios."
            )
            return

        centro_sel = st.selectbox(
            "Centro",
            centros,
            index=_indice_seguro(
                centros,
                centro_actual,
            ),
            key=f"{prefijo}_editar_ubicacion_centro_{id_ot}",
        )

        edificios = obtener_edificios_espacios(
            centro_sel
        )

        if not edificios:
            st.warning(
                "No hay edificios registrados para este centro."
            )
            return

        edificio_sel = st.selectbox(
            "Edificio",
            edificios,
            index=_indice_seguro(
                edificios,
                edificio_actual,
            ),
            key=f"{prefijo}_editar_ubicacion_edificio_{id_ot}",
        )

        plantas = obtener_plantas_espacios(
            centro_sel,
            edificio_sel,
        )

        if not plantas:
            st.warning(
                "No hay plantas registradas para este edificio."
            )
            return

        planta_sel = st.selectbox(
            "Planta",
            plantas,
            index=_indice_seguro(
                plantas,
                planta_actual,
            ),
            key=f"{prefijo}_editar_ubicacion_planta_{id_ot}",
        )

        espacios = obtener_espacios_por_planta(
            centro_sel,
            edificio_sel,
            planta_sel,
        )

        nombres_espacios = [
            str(fila[0] or "").strip()
            for fila in espacios
            if fila and str(fila[0] or "").strip()
        ]

        if espacio_actual:
            espacio_actual_txt = str(
                espacio_actual or ""
            ).strip()

            if (
                espacio_actual_txt
                and espacio_actual_txt not in nombres_espacios
            ):
                nombres_espacios = [
                    espacio_actual_txt
                ] + nombres_espacios

        if not nombres_espacios:
            st.warning(
                "No hay espacios registrados para esta planta."
            )
            return

        espacio_sel = st.selectbox(
            "Espacio",
            nombres_espacios,
            index=_indice_seguro(
                nombres_espacios,
                espacio_actual,
            ),
            key=f"{prefijo}_editar_ubicacion_espacio_{id_ot}",
        )

        st.caption(
            f"📍 Nueva ubicación: "
            f"{centro_sel} · {edificio_sel} · "
            f"{planta_sel} · {espacio_sel}"
        )

        confirmar = st.checkbox(
            "Confirmo el cambio de ubicación",
            key=f"{prefijo}_confirmar_ubicacion_{id_ot}",
        )

        if st.button(
            "💾 Guardar ubicación",
            key=f"{prefijo}_guardar_ubicacion_{id_ot}",
            use_container_width=True,
            type="primary",
        ):
            if not confirmar:
                st.error(
                    "Marca primero la confirmación."
                )
                return

            ok, mensaje = actualizar_ubicacion_ot(
                id_orden=id_ot,
                centro=centro_sel,
                edificio=edificio_sel,
                planta=planta_sel,
                espacio=espacio_sel,
            )

            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)


def mostrar_ficha_ot_comun(id_orden, prefijo="colegio"):
    fila = obtener_ot_por_id(id_orden)

    if not fila:
        st.error("No se ha encontrado la OT.")
        return

    (
        id_ot,
        numero_ot,
        descripcion,
        estado,
        fecha_creacion,
        centro,
        edificio,
        planta,
        espacio,
        area,
        prioridad,
        operario,
        origen,
        solicitante,
        fecha_origen,
        foto,
    ) = fila

    icono_estado = {
        "Abierta": "🔴",
        "En curso": "🟠",
        "Pendiente material": "📦",
        "Finalizada": "✅",
        "Cerrada": "✅",
    }.get(str(estado or ""), "⚪")

    st.markdown(f"### {icono_estado} {numero_ot or 'OT'}")
    st.markdown(f"**{prioridad or '-'}** · {area or '-'} · {estado or '-'}")
    st.markdown(descripcion or "")

    ubicacion = " · ".join(
        [
            str(valor).strip()
            for valor in [
                centro,
                edificio,
                planta,
                espacio,
            ]
            if str(valor or "").strip()
        ]
    )

    st.caption(
        f"🏢 {ubicacion or '-'}"
    )
    st.caption(f"👷 Operario: {operario or '-'}")
    st.caption(f"📌 Origen: {origen or '-'}")

    if solicitante:
        st.caption(f"Solicitante: {solicitante}")

    mostrar_editor_ubicacion_ot(
        id_ot=id_ot,
        centro_actual=centro,
        edificio_actual=edificio,
        planta_actual=planta,
        espacio_actual=espacio,
        prefijo=prefijo,
    )

    st.markdown("---")

    try:
        fotos_db = obtener_fotos_ot(numero_ot)

        if fotos_db:
            cols = st.columns(3)

            for i, (nombre_foto, foto_data) in enumerate(fotos_db):
                with cols[i % 3]:
                    st.image(
                        bytes(foto_data),
                        caption=f"Foto {i + 1}",
                        use_container_width=True
                    )
        elif foto:
            st.info("Esta OT tiene foto asociada.")
    except Exception:
        st.caption("No se pudieron cargar las fotos.")

    st.markdown("### 📝 Gestión de la OT")

    observacion_estado = st.text_area(
        "Observación del estado",
        key=f"{prefijo}_obs_estado_{id_ot}"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button(
            "▶️ En curso",
            key=f"{prefijo}_curso_{id_ot}",
            use_container_width=True,
        ):
            actualizar_estado(
                id_ot,
                "En curso",
                observacion_estado,
            )
            st.rerun()

    with c2:
        if st.button(
            "📦 Material",
            key=f"{prefijo}_material_{id_ot}",
            use_container_width=True,
        ):
            actualizar_estado(
                id_ot,
                "Pendiente material",
                observacion_estado,
            )
            st.rerun()

    with c3:
        if st.button(
            "✔️ Finalizar",
            key=f"{prefijo}_finalizar_{id_ot}",
            use_container_width=True,
        ):
            st.session_state[
                f"{prefijo}_confirmar_fin_{id_ot}"
            ] = True
            st.rerun()

    if st.session_state.get(
        f"{prefijo}_confirmar_fin_{id_ot}",
        False,
    ):
        st.warning(
            f"¿Seguro que quieres finalizar {numero_ot}?"
        )

        f1, f2 = st.columns(2)

        with f1:
            if st.button(
                "Sí, finalizar",
                key=f"{prefijo}_si_fin_{id_ot}",
                use_container_width=True,
            ):
                actualizar_observaciones_estado(
                    id_ot,
                    observacion_estado,
                )
                finalizar_orden(
                    id_ot,
                    observacion_estado,
                )
                st.session_state[
                    f"{prefijo}_confirmar_fin_{id_ot}"
                ] = False
                st.success(
                    f"{numero_ot} finalizada correctamente."
                )
                st.rerun()

        with f2:
            if st.button(
                "Cancelar",
                key=f"{prefijo}_no_fin_{id_ot}",
                use_container_width=True,
            ):
                st.session_state[
                    f"{prefijo}_confirmar_fin_{id_ot}"
                ] = False
                st.rerun()
