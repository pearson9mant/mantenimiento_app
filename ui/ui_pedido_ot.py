import re
import unicodedata

import streamlit as st

from modules.inventario import obtener_materiales_para_select
from modules.ordenes import actualizar_estado
from modules.pedidos_material import (
    crear_pedido_material_multiple,
    obtener_numero_pedido,
    guardar_fotos_pedido_material,
)
from modules.pedidos_ot import (
    vincular_pedido_a_ot,
    obtener_pedidos_de_ot,
    obtener_ot_de_pedido,
)


def _normalizar(texto):
    texto = str(texto or "").lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    texto = re.sub(r"[^a-z0-9 ]+", " ", texto)
    return " ".join(texto.split())


def _catalogo_inventario():
    try:
        filas = obtener_materiales_para_select()
    except Exception:
        return []

    resultado = []

    for fila in filas or []:
        if len(fila) < 4:
            continue

        codigo = str(fila[0] or "").strip()
        material = str(fila[1] or "").strip()

        try:
            stock = float(fila[2] or 0)
        except Exception:
            stock = 0.0

        unidad = str(fila[3] or "").strip()

        if not material:
            continue

        resultado.append({
            "codigo": codigo,
            "material": material,
            "stock": stock,
            "unidad": unidad,
            "_buscar": _normalizar(
                f"{codigo} {material}"
            ),
        })

    return resultado


def _buscar_catalogo(
    catalogo,
    texto,
    limite=6,
):
    consulta = _normalizar(texto)

    if len(consulta) < 2:
        return []

    palabras = consulta.split()
    candidatos = []

    for item in catalogo:
        objetivo = item["_buscar"]

        if not all(
            palabra in objetivo
            for palabra in palabras
        ):
            continue

        material_norm = _normalizar(
            item["material"]
        )

        puntuacion = 0

        if material_norm.startswith(consulta):
            puntuacion += 100

        if consulta in material_norm:
            puntuacion += 50

        puntuacion += sum(
            10
            for palabra in palabras
            if material_norm.startswith(palabra)
        )

        candidatos.append(
            (puntuacion, item)
        )

    candidatos.sort(
        key=lambda x: (
            -x[0],
            x[1]["material"].lower(),
        )
    )

    return [
        item
        for _, item in candidatos[:limite]
    ]


def _base_key(id_orden):
    return f"pedido_ot_completo_{int(id_orden)}"


def _nueva_linea(id_orden):
    base = _base_key(id_orden)
    seq_key = f"{base}_seq"

    secuencia = int(
        st.session_state.get(
            seq_key,
            0,
        )
        or 0
    ) + 1

    st.session_state[seq_key] = secuencia

    return {
        "uid": secuencia,
        "busqueda": "",
        "codigo_material": "",
        "material": "",
        "cantidad": 1.0,
        "observaciones": "",
        "link_material": "",
        "es_compra": False,
        "categoria": "",
        "precio_unitario": None,
    }


def _lineas_key(id_orden):
    return f"{_base_key(id_orden)}_lineas"


def _obtener_lineas_ui(id_orden):
    clave = _lineas_key(id_orden)

    if clave not in st.session_state:
        st.session_state[clave] = [
            _nueva_linea(id_orden)
        ]

    return st.session_state[clave]


def _limpiar_formulario(id_orden):
    base = _base_key(id_orden)

    for clave in list(
        st.session_state.keys()
    ):
        if str(clave).startswith(base):
            st.session_state.pop(
                clave,
                None,
            )


def _mostrar_selector_material(
    id_orden,
    linea,
    catalogo,
):
    base = _base_key(id_orden)
    uid = linea["uid"]

    codigo_actual = str(
        linea.get(
            "codigo_material",
            "",
        )
        or ""
    ).strip()

    if codigo_actual:
        item_actual = next(
            (
                item
                for item in catalogo
                if item["codigo"] == codigo_actual
            ),
            None,
        )

        material = (
            item_actual["material"]
            if item_actual
            else linea.get("material", "")
        )

        stock = (
            item_actual["stock"]
            if item_actual
            else 0
        )

        unidad = (
            item_actual["unidad"]
            if item_actual
            else ""
        )

        st.success(
            f"📦 **{material}** · "
            f"Stock: {stock:g} {unidad} · "
            f"Código: {codigo_actual}"
        )

        if st.button(
            "🔄 Cambiar material",
            key=f"{base}_cambiar_{uid}",
        ):
            linea["codigo_material"] = ""
            linea["material"] = ""
            linea["busqueda"] = ""
            linea["es_compra"] = False
            st.rerun()

        return

    if linea.get("es_compra", False):
        material_compra = st.text_input(
            "Material a comprar",
            value=str(
                linea.get("material", "")
                or ""
            ),
            key=f"{base}_compra_{uid}",
        )

        linea["material"] = material_compra

        st.caption(
            "🛒 Material no catalogado / compra."
        )

        categorias_compra = [
            "Electricidad",
            "Iluminación",
            "Fontanería",
            "Climatización",
            "Ferretería",
            "Pintura",
            "Limpieza",
            "Cerrajería",
            "Informática",
            "Seguridad",
            "ACS",
            "Equipamiento",
            "Jardinería",
            "Otros",
        ]

        categoria_actual = str(
            linea.get("categoria", "") or ""
        ).strip()
        opciones_categoria = ["Selecciona categoría"] + categorias_compra
        indice_categoria = (
            opciones_categoria.index(categoria_actual)
            if categoria_actual in opciones_categoria
            else 0
        )

        categoria_compra = st.selectbox(
            "Categoría",
            opciones_categoria,
            index=indice_categoria,
            key=f"{base}_categoria_{uid}",
        )
        linea["categoria"] = (
            ""
            if categoria_compra == "Selecciona categoría"
            else categoria_compra
        )

        precio_actual = linea.get("precio_unitario")
        precio_compra = st.number_input(
            "Precio unitario (€) · opcional",
            min_value=0.0,
            step=0.01,
            value=float(precio_actual or 0.0),
            key=f"{base}_precio_{uid}",
            help="Si todavía no conoces el precio, déjalo en 0,00 €.",
        )
        linea["precio_unitario"] = (
            float(precio_compra)
            if float(precio_compra) > 0
            else None
        )

        if st.button(
            "🔎 Volver a buscar en inventario",
            key=f"{base}_volver_{uid}",
        ):
            linea["es_compra"] = False
            linea["material"] = ""
            linea["busqueda"] = ""
            st.rerun()

        return

    consulta = st.text_input(
        "🔎 Busca material",
        value=str(
            linea.get("busqueda", "")
            or ""
        ),
        placeholder=(
            "Empieza a escribir: racor, "
            "silicona, tubo..."
        ),
        key=f"{base}_buscar_{uid}",
    )

    linea["busqueda"] = consulta

    if len(_normalizar(consulta)) < 2:
        st.caption(
            "Escribe al menos 2 letras "
            "para buscar en inventario."
        )
        return

    resultados = _buscar_catalogo(
        catalogo,
        consulta,
    )

    if resultados:
        st.caption(
            "Coincidencias en inventario:"
        )

        for item in resultados:
            stock = item["stock"]
            unidad = item["unidad"]

            if stock <= 0:
                icono = "🔴"
            elif stock <= 2:
                icono = "🟠"
            else:
                icono = "✅"

            if st.button(
                (
                    f"{icono} {item['material']} · "
                    f"Stock {stock:g} {unidad}"
                ),
                key=(
                    f"{base}_resultado_"
                    f"{uid}_{item['codigo']}"
                ),
                use_container_width=True,
            ):
                linea[
                    "codigo_material"
                ] = item["codigo"]

                linea[
                    "material"
                ] = item["material"]

                linea[
                    "es_compra"
                ] = False

                st.rerun()

    else:
        st.info(
            "No encuentro coincidencias "
            "en el inventario."
        )

    if st.button(
        (
            "🛒 Solicitar "
            f"«{consulta.strip()}» como compra"
        ),
        key=f"{base}_solicitar_compra_{uid}",
        use_container_width=True,
        disabled=not bool(
            consulta.strip()
        ),
    ):
        linea["codigo_material"] = ""
        linea["material"] = consulta.strip()
        linea["es_compra"] = True
        st.rerun()


def mostrar_pedido_material_desde_ot(
    id_orden,
    numero_ot,
    descripcion_ot,
    centro,
    edificio,
    planta,
    espacio,
    operario,
    prioridad="Media",
):
    """
    Pedido completo de material desde una OT.

    Mantiene el pedido normal:
    - búsqueda en inventario;
    - compra / no catalogado;
    - varias líneas;
    - cantidad;
    - observaciones;
    - enlace / referencia;
    - fotos.

    Y añade:
    - vínculo real con la OT;
    - ubicación heredada;
    - paso de la OT a Pendiente material.
    """
    numero_ot = str(
        numero_ot or ""
    ).strip()

    if not numero_ot:
        return

    base = _base_key(id_orden)

    try:
        pedidos = obtener_pedidos_de_ot(
            numero_ot,
            solo_activos=False,
        )
    except Exception:
        pedidos = []

    if pedidos:
        st.markdown(
            "### 📦 Pedidos vinculados a esta OT"
        )

        for (
            _id_pedido,
            numero_pedido,
            estado,
            fecha,
            _prioridad,
        ) in pedidos:
            st.caption(
                f"{numero_pedido or '-'} · "
                f"{estado or '-'} · "
                f"{fecha or '-'}"
            )

    clave_abrir = f"{base}_abierto"

    if not st.session_state.get(
        clave_abrir,
        False,
    ):
        if st.button(
            "📦 Solicitar material para esta OT",
            key=f"{base}_abrir",
            use_container_width=True,
        ):
            st.session_state[
                clave_abrir
            ] = True

            _obtener_lineas_ui(id_orden)
            st.rerun()

        return

    with st.container(border=True):
        st.markdown(
            f"### 📦 Solicitud de material · {numero_ot}"
        )

        st.caption(
            "Mismo pedido que en Pedidos de material, "
            "pero vinculado automáticamente a esta OT."
        )

        ubicacion = " · ".join(
            parte
            for parte in [
                str(centro or "").strip(),
                str(edificio or "").strip(),
                str(planta or "").strip(),
                str(espacio or "").strip(),
            ]
            if parte
        )

        st.info(
            f"🔗 **OT:** {numero_ot}\n\n"
            f"📍 {ubicacion or '-'}\n\n"
            f"🛠️ {descripcion_ot or '-'}"
        )

        fotos_pedido = st.file_uploader(
            "📷 Fotos del material o referencia",
            type=[
                "jpg",
                "jpeg",
                "png",
            ],
            accept_multiple_files=True,
            key=f"{base}_fotos",
            help=(
                "Máximo 5 fotos y 5 MB por foto."
            ),
        )

        fotos_validas = True

        if fotos_pedido:
            if len(fotos_pedido) > 5:
                st.error(
                    "Puedes adjuntar como máximo 5 fotos."
                )
                fotos_validas = False

            for foto in fotos_pedido[:5]:
                if (
                    getattr(foto, "size", 0)
                    > 5 * 1024 * 1024
                ):
                    st.error(
                        f"{foto.name}: supera 5 MB."
                    )
                    fotos_validas = False

            if fotos_validas:
                st.markdown(
                    "#### 👀 Vista previa"
                )

                cols = st.columns(
                    min(
                        3,
                        len(fotos_pedido),
                    )
                )

                for i, foto in enumerate(
                    fotos_pedido
                ):
                    with cols[
                        i % len(cols)
                    ]:
                        st.image(
                            foto,
                            caption=foto.name,
                            use_container_width=True,
                        )

        prioridades = [
            "Baja",
            "Media",
            "Alta",
            "Urgente",
        ]

        prioridad_actual = str(
            prioridad or "Media"
        ).strip()

        if prioridad_actual not in prioridades:
            prioridad_actual = "Media"

        prioridad_pedido = st.selectbox(
            "Prioridad",
            prioridades,
            index=prioridades.index(
                prioridad_actual
            ),
            key=f"{base}_prioridad",
        )

        observaciones_generales = st.text_area(
            "Observaciones generales del pedido",
            key=f"{base}_observaciones_generales",
        )

        catalogo = _catalogo_inventario()

        st.markdown(
            "### 📋 Materiales"
        )

        lineas = _obtener_lineas_ui(
            id_orden
        )

        for numero, linea in enumerate(
            list(lineas),
            start=1,
        ):
            uid = linea["uid"]

            with st.container(
                border=True
            ):
                st.markdown(
                    f"**Material {numero}**"
                )

                _mostrar_selector_material(
                    id_orden,
                    linea,
                    catalogo,
                )

                cantidad = st.number_input(
                    "Cantidad",
                    min_value=1.0,
                    step=1.0,
                    value=float(
                        linea.get(
                            "cantidad",
                            1.0,
                        )
                        or 1.0
                    ),
                    key=f"{base}_cantidad_{uid}",
                )

                obs_linea = st.text_input(
                    "Observaciones de esta línea",
                    value=str(
                        linea.get(
                            "observaciones",
                            "",
                        )
                        or ""
                    ),
                    key=f"{base}_obs_{uid}",
                )

                link_linea = st.text_input(
                    "🔗 Enlace / referencia",
                    value=str(
                        linea.get(
                            "link_material",
                            "",
                        )
                        or ""
                    ),
                    placeholder=(
                        "Proveedor, web o referencia..."
                    ),
                    key=f"{base}_link_{uid}",
                )

                linea["cantidad"] = cantidad
                linea["observaciones"] = obs_linea
                linea["link_material"] = link_linea

                if len(lineas) > 1:
                    if st.button(
                        "🗑️ Eliminar este material",
                        key=f"{base}_eliminar_{uid}",
                    ):
                        st.session_state[
                            _lineas_key(id_orden)
                        ] = [
                            item
                            for item in lineas
                            if item.get("uid") != uid
                        ]
                        st.rerun()

        col1, col2 = st.columns(
            [1, 2]
        )

        with col1:
            if st.button(
                "➕ Añadir otro material",
                key=f"{base}_añadir",
                use_container_width=True,
            ):
                st.session_state[
                    _lineas_key(id_orden)
                ].append(
                    _nueva_linea(id_orden)
                )
                st.rerun()

        with col2:
            enviar = st.button(
                "📨 Enviar pedido a Abel",
                key=f"{base}_enviar",
                type="primary",
                use_container_width=True,
            )

        if enviar:
            lineas_validas = []

            for linea in st.session_state[
                _lineas_key(id_orden)
            ]:
                material = str(
                    linea.get(
                        "material",
                        "",
                    )
                    or ""
                ).strip()

                if not material:
                    continue

                lineas_validas.append({
                    "codigo_material": str(
                        linea.get(
                            "codigo_material",
                            "",
                        )
                        or ""
                    ).strip(),
                    "material": material,
                    "cantidad": float(
                        linea.get(
                            "cantidad",
                            1,
                        )
                        or 1
                    ),
                    "observaciones": linea.get(
                        "observaciones",
                        "",
                    ),
                    "link_material": linea.get(
                        "link_material",
                        "",
                    ),
                    "categoria": str(
                        linea.get("categoria", "") or ""
                    ).strip(),
                    "precio_unitario": linea.get(
                        "precio_unitario"
                    ),
                })

            compras_sin_categoria = [
                linea
                for linea in st.session_state[_lineas_key(id_orden)]
                if str(linea.get("material", "") or "").strip()
                and linea.get("es_compra", False)
                and not str(linea.get("categoria", "") or "").strip()
            ]

            if not lineas_validas:
                st.warning(
                    "Añade al menos un material al pedido."
                )

            elif compras_sin_categoria:
                st.warning(
                    "Selecciona la categoría del material a comprar "
                    "para poder crear su código de inventario."
                )

            elif not fotos_validas:
                st.error(
                    "Corrige las fotos antes de enviar el pedido."
                )

            else:
                observaciones_pedido = (
                    f"Material para OT {numero_ot}"
                )

                if ubicacion:
                    observaciones_pedido += (
                        f" · {ubicacion}"
                    )

                if str(
                    observaciones_generales or ""
                ).strip():
                    observaciones_pedido += (
                        " · "
                        + str(
                            observaciones_generales
                        ).strip()
                    )

                try:
                    id_pedido = crear_pedido_material_multiple(
                        operario=operario,
                        centro=centro,
                        edificio=edificio,
                        prioridad=prioridad_pedido,
                        observaciones=observaciones_pedido,
                        lineas=lineas_validas,
                        foto="postgres_fotos",
                    )

                except Exception as error:
                    st.error(
                        f"No se pudo crear el pedido: {error}"
                    )

                else:
                    if not id_pedido:
                        st.error(
                            "No se pudo crear el pedido."
                        )

                    else:
                        if fotos_pedido:
                            guardar_fotos_pedido_material(
                                id_pedido,
                                fotos_pedido,
                            )

                        vincular_pedido_a_ot(
                            pedido_id=id_pedido,
                            id_orden=id_orden,
                            numero_ot=numero_ot,
                            centro=centro,
                            edificio=edificio,
                            planta=planta,
                            espacio=espacio,
                            descripcion_ot=descripcion_ot,
                        )

                        numero_pedido = obtener_numero_pedido(
                            id_pedido
                        )

                        actualizar_estado(
                            id_orden,
                            "Pendiente material",
                            (
                                "Material solicitado en "
                                f"{numero_pedido}."
                            ),
                        )

                        st.session_state[
                            "recalcular_corazon"
                        ] = True

                        _limpiar_formulario(
                            id_orden
                        )

                        st.success(
                            f"Pedido {numero_pedido} "
                            "enviado a Abel y vinculado a la OT."
                        )

                        st.rerun()

        if st.button(
            "❌ Cerrar sin enviar",
            key=f"{base}_cerrar",
            use_container_width=True,
        ):
            _limpiar_formulario(
                id_orden
            )
            st.rerun()


def mostrar_contexto_ot_pedido(
    id_pedido,
    contexto=None,
):
    """
    Bloque informativo para Abel y para el operario.
    Si el pedido no nació desde una OT, no muestra nada.
    """
    if contexto is None:
        contexto = obtener_ot_de_pedido(
            id_pedido
        )

    if not contexto:
        return

    st.markdown(
        "### 🔗 Orden de trabajo vinculada"
    )

    st.info(
        f"**{contexto['numero_ot']}** · "
        f"{contexto['descripcion_ot'] or '-'}"
    )

    ubicacion = " · ".join(
        parte
        for parte in [
            contexto["centro"],
            contexto["edificio"],
            contexto["planta"],
            contexto["espacio"],
        ]
        if str(parte or "").strip()
    )

    if ubicacion:
        st.caption(
            f"📍 {ubicacion}"
        )
