import streamlit as st
from pathlib import Path
from collections import defaultdict

from database.db import conectar, _sql
from modules.ubicaciones import CENTROS, obtener_edificios, obtener_espacios

from modules.inventario_aulas import (
    crear_tabla_inventario_aulas,
    guardar_inventario_aula,
    obtener_inventario_aulas
)


def borrar_inventario_aula(id_reg):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(
            _sql("DELETE FROM inventario_aulas WHERE id = ?"),
            (int(id_reg),)
        )
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        st.error(f"Error al borrar registro: {e}")
        return False

    finally:
        conn.close()


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

        if elemento == "Otro":
            elemento = st.text_input(
                "Especificar elemento",
                placeholder="Ejemplo: ventilador, altavoz, cortina...",
                key="inv_aula_elemento_otro"
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
    st.markdown("### 🏫 Aulas inventariadas")

    registros = obtener_inventario_aulas()

    if not registros:
        st.info("Todavía no hay registros de inventario de aulas.")
        return

    filtro_centro = st.selectbox(
        "Filtrar centro",
        ["Todos"] + sorted(list(set([str(r[2]) for r in registros if r[2]]))),
        key="filtro_inv_aulas_centro"
    )

    registros_filtrados = registros

    if filtro_centro != "Todos":
        registros_filtrados = [
            r for r in registros_filtrados
            if str(r[2]) == filtro_centro
        ]

    aulas = defaultdict(list)

    for r in registros_filtrados:
        centro = r[2]
        edificio = r[3]
        espacio = r[4]

        clave_aula = f"{centro} | {edificio} | {espacio}"
        aulas[clave_aula].append(r)

    if not aulas:
        st.info("No hay aulas con ese filtro.")
        return

    for aula, elementos in aulas.items():

        total_elementos = sum(int(e[6] or 0) for e in elementos)

        estados = [e[7] for e in elementos]

        if any(e in ["Dañado", "Falta", "Retirar"] for e in estados):
            icono_aula = "🔴"
        elif any(e == "Regular" for e in estados):
            icono_aula = "🟡"
        else:
            icono_aula = "✅"

        titulo_aula = f"{icono_aula} {aula} · {len(elementos)} registros · {total_elementos} uds."

        with st.expander(titulo_aula, expanded=False):

            st.markdown(f"### 🏫 {aula}")

            resumen = defaultdict(int)

            for e in elementos:
                elemento = e[5]
                cantidad = int(e[6] or 0)
                resumen[elemento] += cantidad

            st.markdown("#### Resumen del aula")

            for elemento, cantidad in resumen.items():
                st.write(f"• **{cantidad} x {elemento}**")

            st.markdown("---")
            st.markdown("#### Detalle")

            for r in elementos:
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

                with st.expander(
                    f"{icono} {elemento} · Cantidad: {cantidad} · {estado}",
                    expanded=False
                ):

                    st.markdown(f"### {elemento}")
                    st.markdown(f"**Cantidad:** {cantidad} · **Estado:** {estado}")
                    st.markdown(f"📏 {ancho} x {alto} x {fondo} {unidad}")
                    st.markdown(f"🏢 {centro} · {edificio} · {espacio}")
                    st.caption(f"Revisado por {operario or '-'} · {fecha_revision}")

                    if observaciones:
                        st.info(observaciones)

                    if foto:
                        try:
                            st.image(foto, width=250)
                        except Exception:
                            st.caption("Foto no disponible.")

                    confirmar = st.checkbox(
                        "Confirmo borrar este registro",
                        key=f"confirmar_borrar_inv_aula_{id_reg}"
                    )

                    if st.button(
                        f"🗑️ Borrar {elemento}",
                        key=f"borrar_inv_aula_{id_reg}",
                        use_container_width=True
                    ):
                        if not confirmar:
                            st.error("Marca primero la confirmación.")
                        else:
                            if borrar_inventario_aula(id_reg):
                                st.warning("Registro borrado correctamente.")
                                st.rerun()
