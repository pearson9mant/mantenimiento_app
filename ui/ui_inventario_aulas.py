import streamlit as st
from pathlib import Path

from database.db import conectar, _sql
from modules.ubicaciones import CENTROS, obtener_edificios, obtener_espacios

from modules.inventario_aulas import (
    crear_tabla_inventario_aulas,
    guardar_inventario_aula,
    obtener_inventario_aulas
)


ELEMENTOS_RAPIDOS_AULA = [
    "Silla",
    "Mesa alumno",
    "Mesa profesor",
    "Armario",
    "Pizarra",
    "Proyector",
    "Pantalla eléctrica",
    "Estantería",
    "Perchero",
    "Papelera",
    "Altavoz",
    "Monitor",
    "Ordenador",
    "Router / Switch",
    "Cortina",
    "Persiana",
    "Otro"
]


def centro_por_operario():
    operario = str(st.session_state.get("operario_activo", "")).strip()

    if operario == "Luis Lozano":
        return "Pearson 9"

    if operario == "J.A. Almeda":
        return "Pearson 22"

    return ""


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


def existe_registro_aula(centro, edificio, espacio, elemento):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            SELECT id
            FROM inventario_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
              AND elemento = ?
            ORDER BY id DESC
            LIMIT 1
        """), (
            centro,
            edificio,
            espacio,
            elemento
        ))

        fila = cursor.fetchone()
        return fila[0] if fila else None

    except Exception:
        return None

    finally:
        conn.close()


def actualizar_inventario_aula(
    id_reg,
    cantidad,
    estado,
    ancho,
    alto,
    fondo,
    unidad,
    observaciones,
    foto,
    operario
):
    from datetime import datetime

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            UPDATE inventario_aulas
            SET fecha_revision = ?,
                cantidad = ?,
                estado = ?,
                ancho = ?,
                alto = ?,
                fondo = ?,
                unidad = ?,
                observaciones = ?,
                foto = ?,
                operario = ?
            WHERE id = ?
        """), (
            datetime.now().strftime("%Y-%m-%d"),
            cantidad,
            estado,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario,
            id_reg
        ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        st.error(f"Error actualizando inventario: {e}")
        return False

    finally:
        conn.close()


def guardar_o_actualizar_aula(
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
    operario
):
    id_existente = existe_registro_aula(centro, edificio, espacio, elemento)

    if id_existente:
        return actualizar_inventario_aula(
            id_existente,
            cantidad,
            estado,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario
        )

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
        foto=foto,
        operario=operario
    )

    return True


def guardar_foto_aula(foto_subida, centro, edificio, espacio, elemento):
    if foto_subida is None:
        return ""

    carpeta = Path("data/fotos_aulas")
    carpeta.mkdir(parents=True, exist_ok=True)

    nombre_foto = f"{centro}_{edificio}_{espacio}_{elemento}_{foto_subida.name}"
    nombre_foto = (
        nombre_foto
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )

    ruta_foto = str(carpeta / nombre_foto)

    with open(ruta_foto, "wb") as f:
        f.write(foto_subida.getbuffer())

    return ruta_foto


def pantalla_inventario_aulas():
    crear_tabla_inventario_aulas()

    st.subheader("🏫 Inventario rápido de aulas")

    operario = st.session_state.get("operario_activo", "")
    perfil = st.session_state.get("perfil", "")
    centro_fijo = centro_por_operario() if perfil != "admin" else ""

    if centro_fijo:
        st.info(f"Centro asignado: **{centro_fijo}**")
        centro = centro_fijo
    else:
        centro = st.selectbox("Centro", CENTROS, key="inv_aula_centro")

    edificios = obtener_edificios(centro)

    edificio = st.selectbox(
        "Edificio",
        edificios,
        key="inv_aula_edificio"
    )

    espacios = obtener_espacios(edificio)

    espacio = st.selectbox(
        "Aula / espacio",
        espacios,
        key="inv_aula_espacio"
    )

    st.markdown("---")
    st.markdown("### 📦 Inventario del aula")

    num_elementos = st.number_input(
        "Número de elementos a introducir",
        min_value=1,
        max_value=30,
        value=10,
        step=1,
        key="inv_aula_num_elementos"
    )

    with st.form("form_inventario_aula_rapido"):
        registros_a_guardar = []

        for i in range(int(num_elementos)):
            st.markdown(f"#### Elemento {i + 1}")

            c1, c2, c3 = st.columns([2, 1, 1])

            with c1:
                elemento = st.selectbox(
                    "Elemento",
                    ELEMENTOS_RAPIDOS_AULA,
                    key=f"inv_rapido_elemento_{i}"
                )

                if elemento == "Otro":
                    elemento = st.text_input(
                        "Especificar elemento",
                        key=f"inv_rapido_elemento_otro_{i}"
                    )

            with c2:
                cantidad = st.number_input(
                    "Cantidad",
                    min_value=0,
                    step=1,
                    key=f"inv_rapido_cantidad_{i}"
                )

            with c3:
                estado = st.selectbox(
                    "Estado",
                    ["Correcto", "Regular", "Dañado", "Falta", "Retirar"],
                    key=f"inv_rapido_estado_{i}"
                )

            observaciones = st.text_input(
                "Observaciones",
                key=f"inv_rapido_obs_{i}"
            )

            foto_subida = st.file_uploader(
                "Foto",
                type=["jpg", "jpeg", "png"],
                key=f"inv_rapido_foto_{i}"
            )

            registros_a_guardar.append(
                (elemento, cantidad, estado, observaciones, foto_subida)
            )

            st.markdown("---")

        guardar = st.form_submit_button(
            "💾 Guardar inventario del aula",
            use_container_width=True
        )

        if guardar:
            guardados = 0

            for elemento, cantidad, estado, observaciones, foto_subida in registros_a_guardar:
                elemento = str(elemento or "").strip()

                if not elemento or cantidad <= 0:
                    continue

                ruta_foto = guardar_foto_aula(
                    foto_subida,
                    centro,
                    edificio,
                    espacio,
                    elemento
                )

                ok = guardar_o_actualizar_aula(
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    elemento=elemento,
                    cantidad=cantidad,
                    estado=estado,
                    ancho=0,
                    alto=0,
                    fondo=0,
                    unidad="cm",
                    observaciones=observaciones,
                    foto=ruta_foto,
                    operario=operario
                )

                if ok:
                    guardados += 1

            if guardados > 0:
                st.success(f"Inventario guardado. Elementos actualizados: {guardados}")
                st.rerun()
            else:
                st.warning("No hay elementos con cantidad para guardar.")

    st.markdown("---")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("🔎 Pasar revisión preventiva de esta aula", use_container_width=True):
            st.session_state["seccion_actual"] = "Preventivo aulas"
            st.session_state["prev_aula_centro_preseleccionado"] = centro
            st.session_state["prev_aula_edificio_preseleccionado"] = edificio
            st.session_state["prev_aula_espacio_preseleccionado"] = espacio
            st.rerun()

    with c2:
        if st.button("🔄 Actualizar listado", use_container_width=True):
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Inventario actual")

    registros = obtener_inventario_aulas()

    registros_filtrados = [
        r for r in registros
        if str(r[2]) == str(centro)
        and str(r[3]) == str(edificio)
        and str(r[4]) == str(espacio)
    ]

    if not registros_filtrados:
        st.info("Esta aula todavía no tiene inventario.")
        return

    total_unidades = sum(int(r[6] or 0) for r in registros_filtrados)

    st.markdown(f"### 🏫 {centro} | {edificio} | {espacio}")
    st.caption(f"{len(registros_filtrados)} registros · {total_unidades} unidades")

    for r in registros_filtrados:
        (
            id_reg,
            fecha_revision,
            centro_r,
            edificio_r,
            espacio_r,
            elemento,
            cantidad,
            estado,
            ancho,
            alto,
            fondo,
            unidad,
            observaciones,
            foto,
            operario_reg,
            fecha_creacion
        ) = r

        if estado in ["Dañado", "Falta", "Retirar"]:
            icono = "🔴"
        elif estado == "Regular":
            icono = "🟡"
        else:
            icono = "✅"

        with st.expander(
            f"{icono} {elemento} · {cantidad} uds · {estado}",
            expanded=False
        ):
            st.markdown(f"**Elemento:** {elemento}")
            st.markdown(f"**Cantidad:** {cantidad}")
            st.markdown(f"**Estado:** {estado}")
            st.caption(f"Revisado por {operario_reg or '-'} · {fecha_revision or '-'}")

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
