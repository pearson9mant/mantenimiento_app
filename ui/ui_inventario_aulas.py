import streamlit as st
from pathlib import Path

from database.db import conectar, _sql
from modules.ubicaciones import CENTROS, obtener_edificios, obtener_espacios
from modules.catalogo_aulas import (
    obtener_elementos_catalogo_aulas,
    obtener_catalogo_aulas,
)

from modules.inventario_aulas import (
    crear_tabla_inventario_aulas,
    guardar_inventario_aula,
    obtener_inventario_aulas
)


ELEMENTOS_RAPIDOS_AULA = obtener_elementos_catalogo_aulas()


TIPOS_ESPACIO_INVENTARIO = [
    "Aula",
    "WC / baño",
    "Cocina",
    "Despacho",
    "Sala técnica",
    "Pasillo / zona común",
    "Otro",
]


CATEGORIAS_POR_TIPO_ESPACIO = {
    "Aula": [
        "Mobiliario",
        "Electricidad",
        "Informática",
        "Carpintería",
        "Climatización",
        "Seguridad",
        "Otros",
    ],
    "WC / baño": [
        "Fontanería",
        "Complementos WC",
        "Electricidad",
        "Carpintería",
        "Seguridad",
        "Otros",
    ],
    "Cocina": [
        "Cocina",
        "Fontanería",
        "Electricidad",
        "Climatización",
        "Seguridad",
        "Carpintería",
        "Otros",
    ],
    "Despacho": [
        "Mobiliario",
        "Electricidad",
        "Informática",
        "Carpintería",
        "Climatización",
        "Seguridad",
        "Otros",
    ],
    "Sala técnica": [
        "Electricidad",
        "Climatización",
        "ACS / Legionella",
        "Fontanería",
        "Seguridad",
        "Otros",
    ],
    "Pasillo / zona común": [
        "Electricidad",
        "Carpintería",
        "Construcción",
        "Seguridad",
        "Climatización",
        "Otros",
    ],
    "Otro": [],
}


PLANTILLAS_INVENTARIO = {
    "Aula": [
        ("Mesa alumno", 25),
        ("Silla alumno", 25),
        ("Mesa profesor", 1),
        ("Silla profesor", 1),
        ("Armario", 1),
        ("Pizarra", 1),
        ("Pantalla interactiva", 1),
        ("Proyector", 0),
        ("Aire acondicionado", 0),
        ("Radiador", 0),
        ("Enchufe", 6),
        ("Interruptor", 1),
        ("Iluminación", 1),
        ("Ventana", 2),
        ("Persiana", 2),
        ("Puerta", 1),
        ("Luz emergencia", 0),
        ("Detector humo", 0),
    ],
    "WC / baño": [
        ("WC", 2),
        ("Fluxor", 2),
        ("Lavabo", 2),
        ("Grifo", 2),
        ("Espejo", 2),
        ("Dispensador de jabón", 2),
        ("Portarrollos", 2),
        ("Secamanos", 1),
        ("Llave de paso", 1),
        ("Iluminación", 1),
        ("Puerta", 1),
    ],
    "Cocina": [
        ("Fregadero", 1),
        ("Grifo", 1),
        ("Lavavajillas", 1),
        ("Campana extractora", 1),
        ("Horno", 1),
        ("Cocina industrial", 1),
        ("Nevera", 1),
        ("Congelador", 1),
        ("Iluminación", 1),
        ("Enchufe", 4),
        ("Extintor", 1),
    ],
    "Despacho": [
        ("Mesa profesor", 1),
        ("Silla profesor", 1),
        ("Armario", 1),
        ("Estantería", 1),
        ("Ordenador", 1),
        ("Monitor", 1),
        ("Enchufe", 4),
        ("Iluminación", 1),
        ("Aire acondicionado", 0),
        ("Radiador", 0),
        ("Ventana", 1),
        ("Puerta", 1),
    ],
    "Sala técnica": [
        ("Cuadro eléctrico", 1),
        ("Iluminación", 1),
        ("Enchufe", 1),
        ("Extintor", 1),
        ("Detector humo", 1),
        ("Bomba", 0),
        ("Bomba recirculación", 0),
        ("Acumulador ACS", 0),
        ("Depósito", 0),
        ("Válvula", 0),
    ],
    "Pasillo / zona común": [
        ("Iluminación", 1),
        ("Luz emergencia", 1),
        ("Detector humo", 1),
        ("Extintor", 0),
        ("Puerta cortafuegos", 0),
        ("Enchufe", 1),
    ],
    "Otro": [],
}


def _tipo_espacio_sugerido(espacio):
    texto = str(espacio or "").strip().lower()

    if any(x in texto for x in ["wc", "baño", "aseo", "vestuario"]):
        return "WC / baño"

    if "cocina" in texto:
        return "Cocina"

    if any(
        x in texto
        for x in [
            "sala técnica",
            "sala tecnica",
            "caldera",
            "acs",
            "depósito",
            "deposito",
            "cuadro",
        ]
    ):
        return "Sala técnica"

    if any(x in texto for x in ["despacho", "secretaría", "secretaria"]):
        return "Despacho"

    if any(x in texto for x in ["pasillo", "hall", "entrada", "recepción", "recepcion"]):
        return "Pasillo / zona común"

    # En esta pantalla el caso normal es un aula.
    return "Aula"


def _catalogo_agrupado():
    catalogo = {}

    try:
        filas = obtener_catalogo_aulas(True)
    except Exception:
        filas = []

    for fila in filas:
        try:
            _id, categoria, elemento, area, activo = fila
        except Exception:
            continue

        categoria = str(categoria or "Otros").strip()
        elemento = str(elemento or "").strip()

        if not elemento:
            continue

        catalogo.setdefault(categoria, [])

        if elemento not in catalogo[categoria]:
            catalogo[categoria].append(elemento)

    for categoria in catalogo:
        catalogo[categoria] = sorted(catalogo[categoria])

    return catalogo


def _categorias_para_tipo(tipo_espacio, catalogo):
    permitidas = CATEGORIAS_POR_TIPO_ESPACIO.get(
        tipo_espacio,
        []
    )

    if not permitidas:
        return sorted(catalogo.keys())

    resultado = [
        categoria
        for categoria in permitidas
        if categoria in catalogo
    ]

    if "Otros" in catalogo and "Otros" not in resultado:
        resultado.append("Otros")

    return resultado


def _guardar_registros_inventario(
    registros,
    centro,
    edificio,
    espacio,
    operario
):
    guardados = 0

    for registro in registros:
        elemento = str(
            registro.get("elemento", "")
        ).strip()

        try:
            cantidad = int(
                registro.get("cantidad", 0) or 0
            )
        except Exception:
            cantidad = 0

        if not elemento or cantidad <= 0:
            continue

        estado = str(
            registro.get("estado", "Correcto")
            or "Correcto"
        ).strip()

        observaciones = str(
            registro.get("observaciones", "")
            or ""
        ).strip()

        foto_subida = registro.get(
            "foto_subida"
        )

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

    return guardados



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


def borrar_inventario_aula_completo(centro, edificio, espacio):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            DELETE FROM inventario_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
        """), (
            centro,
            edificio,
            espacio
        ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        st.error(f"Error al borrar inventario del aula: {e}")
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

    st.subheader("🏫 Inventario rápido de aulas y espacios")

    st.caption(
        "Inventario normalizado para alimentar el censo global "
        "de Activos del colegio."
    )

    operario = st.session_state.get(
        "operario_activo",
        ""
    )

    # Inventario global: desde esta pantalla se puede trabajar
    # con cualquiera de los centros del colegio.
    centro = st.selectbox(
        "Centro",
        CENTROS,
        key="inv_aula_centro"
    )

    edificios = obtener_edificios(
        centro
    )

    edificio = st.selectbox(
        "Edificio",
        edificios,
        key="inv_aula_edificio"
    )

    espacios = obtener_espacios(
        edificio,
        centro
    )

    espacio = st.selectbox(
        "Aula / espacio",
        espacios,
        key="inv_aula_espacio"
    )

    tipo_sugerido = _tipo_espacio_sugerido(
        espacio
    )

    tipo_espacio = st.selectbox(
        "Tipo de espacio",
        TIPOS_ESPACIO_INVENTARIO,
        index=TIPOS_ESPACIO_INVENTARIO.index(
            tipo_sugerido
        ),
        key=(
            f"inv_tipo_espacio_"
            f"{centro}_{edificio}_{espacio}"
        )
    )

    st.markdown("---")
    st.markdown("### 📦 Inventario del espacio")

    tab_plantilla, tab_manual, tab_copiar = st.tabs(
        [
            "⚡ Plantilla rápida",
            "✍️ Introducción manual",
            "📋 Copiar otro espacio",
        ]
    )

    # =====================================================
    # PLANTILLA RÁPIDA
    # =====================================================
    with tab_plantilla:
        plantilla = PLANTILLAS_INVENTARIO.get(
            tipo_espacio,
            []
        )

        if not plantilla:
            st.info(
                "Este tipo de espacio no tiene plantilla automática. "
                "Utiliza Introducción manual."
            )
        else:
            st.info(
                "Ajusta únicamente las cantidades reales. "
                "Los elementos con cantidad 0 no se guardarán."
            )

            registros_plantilla = []

            for i, (
                elemento,
                cantidad_base
            ) in enumerate(
                plantilla
            ):
                c1, c2, c3 = st.columns(
                    [3, 1, 2]
                )

                with c1:
                    st.markdown(
                        f"**{elemento}**"
                    )

                with c2:
                    cantidad = st.number_input(
                        "Cantidad",
                        min_value=0,
                        step=1,
                        value=int(
                            cantidad_base
                        ),
                        key=(
                            f"plantilla_cantidad_{centro}_"
                            f"{edificio}_{espacio}_{i}"
                        )
                    )

                with c3:
                    estado = st.selectbox(
                        "Estado",
                        [
                            "Correcto",
                            "Regular",
                            "Dañado",
                            "Falta",
                            "Retirar",
                        ],
                        key=(
                            f"plantilla_estado_{centro}_"
                            f"{edificio}_{espacio}_{i}"
                        )
                    )

                observaciones = st.text_input(
                    "Observaciones",
                    key=(
                        f"plantilla_obs_{centro}_"
                        f"{edificio}_{espacio}_{i}"
                    )
                )

                registros_plantilla.append(
                    {
                        "elemento": elemento,
                        "cantidad": cantidad,
                        "estado": estado,
                        "observaciones": observaciones,
                        "foto_subida": None,
                    }
                )

                st.markdown("---")

            if st.button(
                "💾 Guardar plantilla del espacio",
                use_container_width=True,
                key=(
                    f"guardar_plantilla_{centro}_"
                    f"{edificio}_{espacio}"
                )
            ):
                guardados = _guardar_registros_inventario(
                    registros=registros_plantilla,
                    centro=centro,
                    edificio=edificio,
                    espacio=espacio,
                    operario=operario
                )

                if guardados > 0:
                    st.success(
                        f"Inventario actualizado. "
                        f"Elementos guardados: {guardados}"
                    )
                    st.rerun()
                else:
                    st.warning(
                        "No hay elementos con cantidad "
                        "mayor que 0 para guardar."
                    )

    # =====================================================
    # INTRODUCCIÓN MANUAL
    # =====================================================
    with tab_manual:
        catalogo = _catalogo_agrupado()

        categorias = _categorias_para_tipo(
            tipo_espacio,
            catalogo
        )

        if not categorias:
            categorias = [
                "Otros"
            ]

        st.caption(
            "El catálogo se filtra según el tipo de espacio. "
            "Así evitamos ver equipos ACS dentro de un aula."
        )

        num_elementos = st.number_input(
            "Número de elementos a introducir",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
            key="inv_aula_num_elementos"
        )

        registros_a_guardar = []

        for i in range(
            int(num_elementos)
        ):
            st.markdown(
                f"#### Elemento {i + 1}"
            )

            c0, c1, c2, c3 = st.columns(
                [2, 3, 1, 2]
            )

            with c0:
                categoria = st.selectbox(
                    "Categoría",
                    categorias,
                    key=(
                        f"inv_rapido_categoria_{centro}_"
                        f"{edificio}_{espacio}_{i}"
                    )
                )

            with c1:
                opciones_elementos = list(
                    catalogo.get(
                        categoria,
                        []
                    )
                )

                if "Otro" not in opciones_elementos:
                    opciones_elementos.append(
                        "Otro"
                    )

                elemento = st.selectbox(
                    "Elemento",
                    opciones_elementos,
                    key=(
                        f"inv_rapido_elemento_{centro}_"
                        f"{edificio}_{espacio}_{i}"
                    )
                )

                if elemento == "Otro":
                    elemento = st.text_input(
                        "Especificar elemento",
                        placeholder=(
                            "Ejemplo: ventilador, reloj, "
                            "cámara, micrófono..."
                        ),
                        key=(
                            f"inv_rapido_elemento_otro_{centro}_"
                            f"{edificio}_{espacio}_{i}"
                        )
                    )

            with c2:
                cantidad = st.number_input(
                    "Cantidad",
                    min_value=0,
                    step=1,
                    key=(
                        f"inv_rapido_cantidad_{centro}_"
                        f"{edificio}_{espacio}_{i}"
                    )
                )

            with c3:
                estado = st.selectbox(
                    "Estado",
                    [
                        "Correcto",
                        "Regular",
                        "Dañado",
                        "Falta",
                        "Retirar",
                    ],
                    key=(
                        f"inv_rapido_estado_{centro}_"
                        f"{edificio}_{espacio}_{i}"
                    )
                )

            observaciones = st.text_input(
                "Observaciones",
                key=(
                    f"inv_rapido_obs_{centro}_"
                    f"{edificio}_{espacio}_{i}"
                )
            )

            foto_subida = st.file_uploader(
                "Foto",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                ],
                key=(
                    f"inv_rapido_foto_{centro}_"
                    f"{edificio}_{espacio}_{i}"
                )
            )

            if foto_subida is not None:
                st.image(
                    foto_subida,
                    caption="Foto seleccionada",
                    width=250
                )

            registros_a_guardar.append(
                {
                    "elemento": elemento,
                    "cantidad": cantidad,
                    "estado": estado,
                    "observaciones": observaciones,
                    "foto_subida": foto_subida,
                }
            )

            st.markdown("---")

        if st.button(
            "💾 Guardar elementos manuales",
            use_container_width=True,
            key=(
                f"guardar_manual_{centro}_"
                f"{edificio}_{espacio}"
            )
        ):
            guardados = _guardar_registros_inventario(
                registros=registros_a_guardar,
                centro=centro,
                edificio=edificio,
                espacio=espacio,
                operario=operario
            )

            if guardados > 0:
                st.success(
                    f"Inventario guardado. "
                    f"Elementos actualizados: {guardados}"
                )
                st.rerun()
            else:
                st.warning(
                    "No hay elementos con cantidad para guardar."
                )

    # =====================================================
    # COPIAR DESDE OTRO ESPACIO
    # =====================================================
    with tab_copiar:
        st.info(
            "Ideal para aulas parecidas: completa bien una primera "
            "aula, cópiala y después ajusta únicamente las diferencias."
        )

        centro_origen = st.selectbox(
            "Centro origen",
            CENTROS,
            index=(
                CENTROS.index(centro)
                if centro in CENTROS
                else 0
            ),
            key=(
                f"copiar_centro_origen_{centro}_"
                f"{edificio}_{espacio}"
            )
        )

        edificios_origen = obtener_edificios(
            centro_origen
        )

        edificio_origen = st.selectbox(
            "Edificio origen",
            edificios_origen,
            index=(
                edificios_origen.index(edificio)
                if edificio in edificios_origen
                else 0
            ),
            key=(
                f"copiar_edificio_origen_{centro}_"
                f"{edificio}_{espacio}"
            )
        )

        espacios_origen = obtener_espacios(
            edificio_origen,
            centro_origen
        )

        espacios_validos = [
            e for e in espacios_origen
            if not (
                centro_origen == centro
                and edificio_origen == edificio
                and str(e) == str(espacio)
            )
        ]

        if not espacios_validos:
            st.warning(
                "No hay otro espacio disponible para copiar."
            )
        else:
            espacio_origen = st.selectbox(
                "Espacio origen",
                espacios_validos,
                key=(
                    f"copiar_espacio_origen_{centro}_"
                    f"{edificio}_{espacio}"
                )
            )

            st.caption(
                f"Destino: {centro} · {edificio} · {espacio}"
            )

            confirmar_copia = st.checkbox(
                "Confirmo copiar el inventario",
                key=(
                    f"confirmar_copia_inv_{centro}_"
                    f"{edificio}_{espacio}"
                )
            )

            if st.button(
                "📋 Copiar inventario",
                use_container_width=True,
                key=(
                    f"btn_copiar_inv_{centro}_"
                    f"{edificio}_{espacio}"
                )
            ):
                if not confirmar_copia:
                    st.warning(
                        "Marca primero la confirmación."
                    )
                else:
                    ok, mensaje = copiar_inventario_entre_espacios(
                        centro_origen=centro_origen,
                        edificio_origen=edificio_origen,
                        espacio_origen=espacio_origen,
                        centro_destino=centro,
                        edificio_destino=edificio,
                        espacio_destino=espacio,
                        operario=operario
                    )

                    if ok:
                        st.success(
                            mensaje
                        )
                        st.rerun()
                    else:
                        st.error(
                            mensaje
                        )

    # =====================================================
    # ACCIONES
    # =====================================================
    st.markdown("---")

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "🔎 Pasar revisión preventiva de esta aula",
            use_container_width=True
        ):
            st.session_state[
                "seccion_actual"
            ] = "Preventivo aulas"

            st.session_state[
                "prev_aula_centro_preseleccionado"
            ] = centro

            st.session_state[
                "prev_aula_edificio_preseleccionado"
            ] = edificio

            st.session_state[
                "prev_aula_espacio_preseleccionado"
            ] = espacio

            st.rerun()

    with c2:
        if st.button(
            "🔄 Actualizar listado",
            use_container_width=True
        ):
            st.rerun()

    # =====================================================
    # INVENTARIO ACTUAL
    # =====================================================
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
        st.info(
            "Este espacio todavía no tiene inventario."
        )
        return

    total_unidades = sum(
        int(r[6] or 0)
        for r in registros_filtrados
    )

    st.markdown(
        f"### 🏫 {centro} | {edificio} | {espacio}"
    )

    st.caption(
        f"{len(registros_filtrados)} registros · "
        f"{total_unidades} unidades"
    )

    # Resumen compacto por estado
    total_correcto = sum(
        int(r[6] or 0)
        for r in registros_filtrados
        if str(r[7] or "") == "Correcto"
    )

    total_regular = sum(
        int(r[6] or 0)
        for r in registros_filtrados
        if str(r[7] or "") == "Regular"
    )

    total_problema = sum(
        int(r[6] or 0)
        for r in registros_filtrados
        if str(r[7] or "") in [
            "Dañado",
            "Falta",
            "Retirar",
        ]
    )

    m1, m2, m3 = st.columns(3)

    m1.metric(
        "🟢 Correcto",
        total_correcto
    )

    m2.metric(
        "🟡 Regular",
        total_regular
    )

    m3.metric(
        "🔴 Atención",
        total_problema
    )

    st.markdown("---")

    with st.expander(
        "🗑️ Zona de borrado del espacio",
        expanded=False
    ):
        confirmar_borrar_aula = st.checkbox(
            "Confirmo borrar todo el inventario de este espacio",
            key=(
                f"confirmar_borrar_aula_"
                f"{centro}_{edificio}_{espacio}"
            )
        )

        if st.button(
            "🗑️ Borrar inventario completo de este espacio",
            key=(
                f"borrar_aula_completa_"
                f"{centro}_{edificio}_{espacio}"
            ),
            use_container_width=True
        ):
            if not confirmar_borrar_aula:
                st.error(
                    "Marca primero la confirmación."
                )
            else:
                if borrar_inventario_aula_completo(
                    centro,
                    edificio,
                    espacio
                ):
                    st.warning(
                        "Inventario del espacio borrado correctamente."
                    )
                    st.rerun()

    st.markdown("---")

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

        if estado in [
            "Dañado",
            "Falta",
            "Retirar",
        ]:
            icono = "🔴"
        elif estado == "Regular":
            icono = "🟡"
        else:
            icono = "✅"

        with st.expander(
            f"{icono} {elemento} · "
            f"{cantidad} uds · {estado}",
            expanded=False
        ):
            st.markdown(
                f"**Elemento:** {elemento}"
            )

            st.markdown(
                f"**Cantidad:** {cantidad}"
            )

            st.markdown(
                f"**Estado:** {estado}"
            )

            st.caption(
                f"Revisado por {operario_reg or '-'} · "
                f"{fecha_revision or '-'}"
            )

            if observaciones:
                st.info(
                    observaciones
                )

            if foto:
                try:
                    st.image(
                        foto,
                        width=250
                    )
                except Exception:
                    st.caption(
                        "Foto no disponible."
                    )

            confirmar = st.checkbox(
                "Confirmo borrar este registro",
                key=(
                    f"confirmar_borrar_inv_aula_"
                    f"{id_reg}"
                )
            )

            if st.button(
                f"🗑️ Borrar {elemento}",
                key=(
                    f"borrar_inv_aula_"
                    f"{id_reg}"
                ),
                use_container_width=True
            ):
                if not confirmar:
                    st.error(
                        "Marca primero la confirmación."
                    )
                else:
                    if borrar_inventario_aula(
                        id_reg
                    ):
                        st.warning(
                            "Registro borrado correctamente."
                        )
                        st.rerun()


def copiar_inventario_entre_espacios(
    centro_origen,
    edificio_origen,
    espacio_origen,
    centro_destino,
    edificio_destino,
    espacio_destino,
    operario=""
):
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(_sql("""
            SELECT elemento, cantidad, estado, ancho, alto, fondo, unidad, observaciones
            FROM inventario_aulas
            WHERE centro = ?
              AND edificio = ?
              AND espacio = ?
        """), (
            centro_origen,
            edificio_origen,
            espacio_origen
        ))

        filas = cur.fetchall()

        if not filas:
            conn.close()
            return False, "El espacio origen no tiene inventario."

        copiados = 0
        omitidos = 0

        for fila in filas:
            elemento, cantidad, estado, ancho, alto, fondo, unidad, observaciones = fila

            cur.execute(_sql("""
                SELECT COUNT(*)
                FROM inventario_aulas
                WHERE centro = ?
                  AND edificio = ?
                  AND espacio = ?
                  AND LOWER(TRIM(elemento)) = LOWER(TRIM(?))
            """), (
                centro_destino,
                edificio_destino,
                espacio_destino,
                elemento
            ))

            existe = cur.fetchone()[0]

            if existe:
                omitidos += 1
                continue

            cur.execute(_sql("""
                INSERT INTO inventario_aulas
                (
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
                    numero_ot_correctiva,
                    fecha_correctivo
                )
                VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, '', '')
            """), (
                centro_destino,
                edificio_destino,
                espacio_destino,
                elemento,
                cantidad,
                estado,
                ancho or 0,
                alto or 0,
                fondo or 0,
                unidad or "cm",
                observaciones or "",
                operario or ""
            ))

            copiados += 1

        conn.commit()
        conn.close()

        return True, f"Inventario copiado. Elementos copiados: {copiados}. Omitidos por existir: {omitidos}."

    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error copiando inventario: {e}"
