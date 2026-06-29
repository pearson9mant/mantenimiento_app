import streamlit as st

from database.db import conectar, _sql
from modules.ordenes import (
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    obtener_fotos_ot,
)


def obtener_ot_por_id(id_orden):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT id, numero_ot, descripcion, estado, fecha_creacion,
                   centro, edificio, espacio, area, prioridad,
                   operario, origen, solicitante, fecha_origen, foto
            FROM ordenes_trabajo
            WHERE id = ?
        """), (id_orden,))

        fila = cur.fetchone()
    except Exception:
        fila = None

    conn.close()
    return fila


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
    st.caption(f"🏢 {centro or '-'} · {edificio or '-'} · {espacio or '-'}")
    st.caption(f"👷 Operario: {operario or '-'}")
    st.caption(f"📌 Origen: {origen or '-'}")

    if solicitante:
        st.caption(f"Solicitante: {solicitante}")

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
        if st.button("▶️ En curso", key=f"{prefijo}_curso_{id_ot}", use_container_width=True):
            actualizar_estado(id_ot, "En curso", observacion_estado)
            st.rerun()

    with c2:
        if st.button("📦 Material", key=f"{prefijo}_material_{id_ot}", use_container_width=True):
            actualizar_estado(id_ot, "Pendiente material", observacion_estado)
            st.rerun()

    with c3:
        if st.button("✔️ Finalizar", key=f"{prefijo}_finalizar_{id_ot}", use_container_width=True):
            st.session_state[f"{prefijo}_confirmar_fin_{id_ot}"] = True
            st.rerun()

    if st.session_state.get(f"{prefijo}_confirmar_fin_{id_ot}", False):
        st.warning(f"¿Seguro que quieres finalizar {numero_ot}?")

        f1, f2 = st.columns(2)

        with f1:
            if st.button("Sí, finalizar", key=f"{prefijo}_si_fin_{id_ot}", use_container_width=True):
                actualizar_observaciones_estado(id_ot, observacion_estado)
                finalizar_orden(id_ot, observacion_estado)
                st.session_state[f"{prefijo}_confirmar_fin_{id_ot}"] = False
                st.success(f"{numero_ot} finalizada correctamente.")
                st.rerun()

        with f2:
            if st.button("Cancelar", key=f"{prefijo}_no_fin_{id_ot}", use_container_width=True):
                st.session_state[f"{prefijo}_confirmar_fin_{id_ot}"] = False
                st.rerun()
