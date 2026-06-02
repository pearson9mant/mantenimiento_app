import streamlit as st
from pathlib import Path
from modules.ubicaciones import CENTROS, obtener_edificios, obtener_espacios

from modules.inventario_aulas import (
    crear_tabla_inventario_aulas,
    guardar_inventario_aula,
    obtener_inventario_aulas
)


def pantalla_inventario_aulas():
    crear_tabla_inventario_aulas()

    st.subheader("🏫 Inventario aulas")

    operario = st.session_state.get("operario_activo", "")

    with st.expander("➕ Nuevo registro", expanded=False):

        centro = st.selectbox(
            "Centro",
            CENTROS,
            key="inv_aula_centro"
        )

        edificios = obtener_edificios(centro)

        edificio = st.selectbox(
            "Edificio",
            edificios,
            key="inv_aula_edificio"
        )

        espacios = obtener_espacios(edificio)

        espacio = st.selectbox(
            "Aula / Espacio",
            espacios,
            key="inv_aula_espacio"
        )

        elemento = st.selectbox(
            "Elemento",
            [
                "Silla",
                "Mesa alumno",
                "Mesa profesor",
                "Armario",
                "Pizarra",
                "Proyector",
                "Estantería",
                "Pantalla eléctrica",
                "Perchero",
                "Otro"
            ],
            key="inv_aula_elemento"
        )

        cantidad = st.number_input(
            "Cantidad",
            min_value=0,
            step=1,
            key="inv_aula_cantidad"
        )

        estado = st.selectbox(
            "Estado",
            ["Correcto", "Regular", "Dañado", "Falta", "Retirar"],
            key="inv_aula_estado"
        )

        st.markdown("### 📏 Medidas")

        m1, m2, m3, m4 = st.columns(4)

        with m1:
            ancho = st.number_input("Ancho", min_value=0.0, step=1.0, key="inv_aula_ancho")

        with m2:
            alto = st.number_input("Alto", min_value=0.0, step=1.0, key="inv_aula_alto")

        with m3:
            fondo = st.number_input("Fondo", min_value=0.0, step=1.0, key="inv_aula_fondo")

        with m4:
            unidad = st.selectbox("Unidad", ["cm", "m", "mm"], key="inv_aula_unidad")

        observaciones = st.text_area(
            "Observaciones",
            key="inv_aula_observaciones"
        )

        foto_subida = st.file_uploader(
            "Foto",
            type=["jpg", "jpeg", "png"],
            key="inv_aula_foto"
        )

        ruta_foto = ""

        if foto_subida is not None:
            carpeta = Path("data/fotos_aulas")
            carpeta.mkdir(parents=True, exist_ok=True)

            nombre_foto = f"{centro}_{edificio}_{espacio}_{elemento}_{foto_subida.name}".replace(" ", "_")
            ruta_foto = str(carpeta / nombre_foto)

            with open(ruta_foto, "wb") as f:
                f.write(foto_subida.getbuffer())

            st.image(ruta_foto, width=250)

        if st.button("💾 Guardar registro", use_container_width=True):
            if not edificio or not espacio or not elemento:
                st.warning("Rellena edificio, aula/espacio y elemento.")
            else:
                guardar_inventario_aula(
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    elemento=elemento,
                    cantidad=cantidad,
                    estado=estado,
                    ancho=ancho,
                    alto=alto,
                    fondo=fondo,
                    unidad=unidad,
                    observaciones=observaciones,
                    foto=ruta_foto,
                    operario=operario
                )

                st.success("Registro guardado correctamente.")
                st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Registros guardados")

    registros = obtener_inventario_aulas()

    if not registros:
        st.info("Todavía no hay registros de inventario de aulas.")
        return

    for r in registros[:50]:
        (
            id_reg,
            fecha_revision,
            centro,
            edificio,
            espacio,
            elemento,
            cantidad,
            estado,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario,
            fecha_creacion
        ) = r

        if estado in ["Dañado", "Falta", "Retirar"]:
            icono = "🔴"
        elif estado == "Regular":
            icono = "🟡"
        else:
            icono = "✅"

        titulo = f"{icono} {elemento} | {espacio} | Cantidad: {cantidad} | {estado}"

        with st.expander(titulo, expanded=False):
            st.markdown(f"### {elemento} · {espacio}")
            st.markdown(f"**Cantidad:** {cantidad} · **Estado:** {estado}")
            st.markdown(f"📏 {ancho} x {alto} x {fondo} {unidad}")
            st.markdown(f"🏢 {centro} · {edificio}")
            st.caption(f"Revisado por {operario or '-'} · {fecha_revision}")

            if observaciones:
                st.info(observaciones)

            if foto:
                try:
                    st.image(foto, width=250)
                except Exception:
                    st.caption("Foto no disponible.")
