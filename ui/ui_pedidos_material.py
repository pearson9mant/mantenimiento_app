import re
import unicodedata

import streamlit as st

from config import CENTROS

from modules.pedidos_material import (
    crear_pedido_material_multiple,
    obtener_pedidos_material,
    obtener_lineas_pedido,
    obtener_datos_recepcion_linea,
    registrar_recepcion_linea_pedido,
    cambiar_estado_pedido,
    cambiar_estado_linea_pedido,
    guardar_fotos_pedido_material,
    borrar_pedido_material,
    ESTADOS_PEDIDO,
)

from modules.ordenes import obtener_fotos_ot
from modules.inventario import (
    obtener_materiales_para_select,
    categorias_inventario_disponibles,
)


PRIORIDADES = [
    "Baja",
    "Media",
    "Alta",
    "Urgente",
]


def categorias_pedido_material():
    categorias = categorias_inventario_disponibles()

    if "Iluminación" not in categorias:
        categorias.insert(
            1,
            "Iluminación",
        )

    return categorias


def usuario_actual():
    return str(
        st.session_state.get("operario_activo")
        or st.session_state.get("usuario")
        or st.session_state.get("nombre")
        or ""
    ).strip()


def es_abel():
    return "abel" in usuario_actual().lower()


def es_admin():
    perfil = str(
        st.session_state.get("perfil")
        or st.session_state.get("rol")
        or ""
    ).strip().lower()

    return perfil in [
        "admin",
        "administrador",
        "administracion",
        "administración",
    ]


def referencia_pedido(id_pedido):
    return f"PED-MAT-{int(id_pedido):04d}"


def _normalizar(texto):
    texto = str(
        texto or ""
    ).lower().strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )

    texto = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        texto,
    )

    return " ".join(
        texto.split()
    )


def _nueva_linea():
    secuencia = int(
        st.session_state.get(
            "pedido_material_linea_seq",
            0,
        )
    ) + 1

    st.session_state[
        "pedido_material_linea_seq"
    ] = secuencia

    return {
        "uid": secuencia,
        "busqueda": "",
        "codigo_material": "",
        "material": "",
        "cantidad": 1.0,
        "observaciones": "",
        "link_material": "",
        "categoria": "",
        "precio_unitario": "",
        "es_compra": False,
    }


def inicializar_lineas_pedido():
    if "pedido_material_lineas_ui" not in st.session_state:
        st.session_state[
            "pedido_material_lineas_ui"
        ] = [
            _nueva_linea()
        ]

    # Compatibilidad con session_state antiguo.
    lineas = st.session_state[
        "pedido_material_lineas_ui"
    ]

    for linea in lineas:
        if "uid" not in linea:
            linea["uid"] = _nueva_linea()["uid"]

        linea.setdefault(
            "busqueda",
            linea.get(
                "material",
                "",
            ),
        )
        linea.setdefault(
            "codigo_material",
            "",
        )
        linea.setdefault(
            "categoria",
            "",
        )
        linea.setdefault(
            "precio_unitario",
            "",
        )
        linea.setdefault(
            "es_compra",
            False,
        )


def añadir_linea_pedido():
    inicializar_lineas_pedido()

    st.session_state[
        "pedido_material_lineas_ui"
    ].append(
        _nueva_linea()
    )


def eliminar_linea_pedido(uid):
    inicializar_lineas_pedido()

    lineas = st.session_state[
        "pedido_material_lineas_ui"
    ]

    if len(lineas) <= 1:
        return

    st.session_state[
        "pedido_material_lineas_ui"
    ] = [
        linea
        for linea in lineas
        if linea.get("uid") != uid
    ]


def limpiar_lineas_pedido():
    st.session_state[
        "pedido_material_lineas_ui"
    ] = [
        _nueva_linea()
    ]

    st.session_state.pop(
        "pedido_fotos_abierto",
        None,
    )


def leer_pedido(p):
    if len(p) >= 14:
        return {
            "id_pedido": p[0],
            "numero_pedido": p[1],
            "fecha": p[2],
            "operario": p[3],
            "centro": p[4],
            "material": p[5],
            "cantidad": p[6],
            "prioridad": p[7],
            "estado": p[8],
            "observaciones": p[9],
            "link_material": p[10] or "",
        }

    return {
        "id_pedido": p[0],
        "numero_pedido": referencia_pedido(
            p[0]
        ),
        "fecha": p[1],
        "operario": p[2],
        "centro": p[3],
        "material": p[4],
        "cantidad": p[5],
        "prioridad": p[6],
        "estado": p[7],
        "observaciones": p[8],
        "link_material": "",
    }


def icono_estado(estado):
    return {
        "Pendiente": "🟡",
        "Preparado": "🔵",
        "Entregado": "🟢",
        "Sin stock": "🔴",
        "Cancelado": "⚫",
    }.get(
        estado,
        "⚪",
    )


def _catalogo_inventario():
    try:
        filas = obtener_materiales_para_select()
    except Exception:
        return []

    resultado = []

    for fila in filas:
        if len(fila) < 4:
            continue

        codigo = str(
            fila[0]
            or ""
        ).strip()

        material = str(
            fila[1]
            or ""
        ).strip()

        try:
            stock = float(
                fila[2]
                or 0
            )
        except Exception:
            stock = 0.0

        unidad = str(
            fila[3]
            or ""
        ).strip()

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
    consulta = _normalizar(
        texto
    )

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

        if material_norm.startswith(
            consulta
        ):
            puntuacion += 100

        if consulta in material_norm:
            puntuacion += 50

        puntuacion += sum(
            10
            for palabra in palabras
            if material_norm.startswith(
                palabra
            )
        )

        puntuacion += (
            max(
                0,
                20 - len(
                    material_norm
                ),
            )
            / 100
        )

        candidatos.append(
            (
                puntuacion,
                item,
            )
        )

    candidatos.sort(
        key=lambda x: (
            -x[0],
            x[1]["material"].lower(),
        )
    )

    return [
        item
        for _, item in candidatos[
            :limite
        ]
    ]


def _mapa_catalogo(
    catalogo,
):
    return {
        item["codigo"]: item
        for item in catalogo
        if item["codigo"]
    }


def mostrar_fotos_pedido(
    id_pedido,
    contexto="general",
):
    numero_pedido = referencia_pedido(
        id_pedido
    )

    contexto = str(
        contexto or "general"
    ).strip().lower()

    clave = (
        f"pedido_fotos_abierto_{contexto}"
    )

    abierto = st.session_state.get(
        clave
    )

    if abierto == numero_pedido:

        if st.button(
            "🙈 Ocultar fotos",
            key=(
                f"ocultar_fotos_pedido_"
                f"{contexto}_{id_pedido}"
            ),
        ):
            st.session_state.pop(
                clave,
                None,
            )
            st.rerun()

        try:
            fotos = obtener_fotos_ot(
                numero_pedido
            )

            if not fotos:
                st.info(
                    "Este pedido no tiene fotos."
                )
                return

            st.markdown(
                "### 📷 Fotos"
            )

            columnas = st.columns(3)

            for i, (
                nombre_foto,
                foto_data,
            ) in enumerate(
                fotos
            ):
                with columnas[
                    i % 3
                ]:
                    try:
                        st.image(
                            bytes(
                                foto_data
                            ),
                            caption=nombre_foto,
                            use_container_width=True,
                        )
                    except Exception:
                        st.caption(
                            "Foto no disponible."
                        )

        except Exception as e:
            st.caption(
                f"Error cargando fotos: {e}"
            )

    else:

        if st.button(
            "📷 Ver fotos",
            key=(
                f"ver_fotos_pedido_"
                f"{contexto}_{id_pedido}"
            ),
        ):
            st.session_state[
                clave
            ] = numero_pedido

            st.rerun()


def mostrar_link_material(
    link_material,
):
    link_material = str(
        link_material or ""
    ).strip()

    if not link_material:
        return

    if (
        link_material.startswith(
            "http://"
        )
        or link_material.startswith(
            "https://"
        )
    ):
        st.link_button(
            "🔗 Abrir enlace material",
            link_material,
        )

    else:
        st.info(
            f"🔗 Enlace / referencia: "
            f"{link_material}"
        )


def mostrar_lineas_pedido(
    id_pedido,
    modo_abel=False,
    mapa_catalogo=None,
):
    try:
        lineas = obtener_lineas_pedido(
            id_pedido
        )
    except Exception as e:
        st.error(
            f"No se pudieron cargar las líneas del pedido: {e}"
        )
        return

    if not lineas:
        st.info(
            "Este pedido no tiene líneas de material."
        )
        return

    mapa_catalogo = mapa_catalogo or {}

    st.markdown(
        "### 📋 Materiales solicitados"
    )

    for linea in lineas:
        id_linea = linea[0]
        codigo_material = str(
            linea[2]
            or ""
        ).strip()

        material = linea[3]
        cantidad = linea[4]
        estado = linea[5] or "Pendiente"
        observaciones = linea[6] or ""
        link_material = linea[7] or ""

        descontado = bool(
            linea[10]
            if len(linea) > 10
            else 0
        )

        datos_recepcion = None

        try:
            datos_recepcion = obtener_datos_recepcion_linea(
                id_linea
            )
        except Exception:
            datos_recepcion = None

        es_compra = bool(
            int(
                (datos_recepcion or {}).get(
                    "es_compra",
                    0,
                )
                or 0
            )
        )

        icono = icono_estado(
            estado
        )

        with st.container(
            border=True
        ):
            col1, col2 = st.columns(
                [3, 1]
            )

            with col1:
                st.markdown(
                    f"**{icono} {material}**"
                )

                if codigo_material:
                    st.caption(
                        f"📦 Inventario · "
                        f"Código: {codigo_material}"
                    )

                    actual = mapa_catalogo.get(
                        codigo_material
                    )

                    if actual:
                        stock = actual["stock"]
                        unidad = actual["unidad"]

                        if es_compra:
                            st.caption(
                                f"🛒 Compra · Stock recibido: "
                                f"{stock:g} {unidad}"
                            )
                        elif stock <= 0:
                            st.error(
                                f"Stock actual: "
                                f"{stock:g} {unidad}"
                            )
                        elif stock < float(
                            cantidad or 0
                        ):
                            st.warning(
                                f"Stock actual: "
                                f"{stock:g} {unidad} · "
                                f"insuficiente para entregar "
                                f"{cantidad:g}"
                            )
                        else:
                            st.caption(
                                f"Stock actual: "
                                f"{stock:g} {unidad}"
                            )

                    if descontado and not es_compra:
                        st.caption(
                            "✅ Salida de inventario registrada."
                        )

                else:
                    st.caption(
                        "🛒 Material no catalogado / compra"
                    )

                st.caption(
                    f"Estado: {estado}"
                )

                if observaciones:
                    st.write(
                        f"**Obs.:** {observaciones}"
                    )

                mostrar_link_material(
                    link_material
                )

            with col2:
                st.metric(
                    "Cantidad",
                    cantidad,
                )

            if (
                (not modo_abel or es_admin())
                and es_compra
                and datos_recepcion
                and codigo_material
            ):
                cantidad_pedida = float(
                    datos_recepcion.get(
                        "cantidad",
                        0,
                    )
                    or 0
                )
                cantidad_recibida = float(
                    datos_recepcion.get(
                        "cantidad_recibida",
                        0,
                    )
                    or 0
                )
                pendiente = max(
                    cantidad_pedida - cantidad_recibida,
                    0,
                )

                st.caption(
                    f"Recibido: {cantidad_recibida:g} de "
                    f"{cantidad_pedida:g} · "
                    f"Pendiente: {pendiente:g}"
                )

                precio_guardado = float(
                    datos_recepcion.get(
                        "precio_unitario",
                        0,
                    )
                    or 0
                )

                if precio_guardado > 0:
                    st.caption(
                        f"💶 Precio unitario actual: "
                        f"{precio_guardado:.2f} €"
                    )
                else:
                    st.caption(
                        "💶 Precio todavía no informado."
                    )

                if pendiente > 0:
                    cantidad_ahora = st.number_input(
                        "Cantidad recibida ahora",
                        min_value=0.0,
                        max_value=float(
                            pendiente
                        ),
                        value=0.0,
                        step=1.0,
                        key=(
                            f"cantidad_recepcion_"
                            f"{id_linea}"
                        ),
                    )

                    precio_recepcion = st.number_input(
                        "Precio unitario (€) · opcional",
                        min_value=0.0,
                        value=float(
                            precio_guardado
                            if precio_guardado > 0
                            else 0.0
                        ),
                        step=0.01,
                        format="%.2f",
                        key=(
                            f"precio_recepcion_"
                            f"{id_linea}"
                        ),
                        help=(
                            "Si conoces ahora el precio real, indícalo. "
                            "Si no, déjalo en 0,00 € y podrás añadirlo "
                            "más adelante desde Inventario."
                        ),
                    )

                    if st.button(
                        "📦 Registrar recepción",
                        key=(
                            f"registrar_recepcion_"
                            f"{id_linea}"
                        ),
                        use_container_width=True,
                    ):
                        if cantidad_ahora <= 0:
                            st.warning(
                                "Indica la cantidad que has recibido."
                            )
                        else:
                            precio_para_guardar = (
                                float(precio_recepcion)
                                if float(precio_recepcion) > 0
                                else None
                            )

                            ok, mensaje = (
                                registrar_recepcion_linea_pedido(
                                    id_linea,
                                    cantidad_ahora,
                                    precio_unitario=precio_para_guardar,
                                )
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
                else:
                    st.success(
                        "✅ Material recibido completamente."
                    )

            if modo_abel:
                nuevo_estado_linea = st.selectbox(
                    "Estado línea",
                    ESTADOS_PEDIDO,
                    index=(
                        ESTADOS_PEDIDO.index(
                            estado
                        )
                        if estado in ESTADOS_PEDIDO
                        else 0
                    ),
                    key=(
                        f"estado_linea_pedido_"
                        f"{id_linea}"
                    ),
                )

                if st.button(
                    "💾 Guardar línea",
                    key=(
                        f"guardar_linea_pedido_"
                        f"{id_linea}"
                    ),
                    use_container_width=True,
                ):
                    resultado = (
                        cambiar_estado_linea_pedido(
                            id_linea,
                            nuevo_estado_linea,
                        )
                    )

                    if isinstance(
                        resultado,
                        tuple,
                    ):
                        ok, mensaje = resultado
                    else:
                        ok = bool(
                            resultado
                        )
                        mensaje = (
                            "Línea actualizada."
                            if ok
                            else "No se pudo actualizar."
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


def ui_pedidos_material():
    st.title(
        "📦 Pedidos de material"
    )

    usuario = usuario_actual()

    if not usuario:
        st.warning(
            "No se ha detectado el usuario actual."
        )
        return

    if es_admin():
        tab1, tab2 = st.tabs([
            "➕ Nuevo pedido",
            "📥 Pedidos recibidos",
        ])

        with tab1:
            ui_pedidos_operario(
                usuario
            )

        with tab2:
            ui_pedidos_abel()

    elif es_abel():
        ui_pedidos_abel()

    else:
        ui_pedidos_operario(
            usuario
        )


def _mostrar_selector_material(
    linea,
    catalogo,
):
    uid = linea["uid"]

    codigo_actual = str(
        linea.get(
            "codigo_material",
            "",
        )
        or ""
    ).strip()

    if codigo_actual:
        seleccionado = next(
            (
                item
                for item in catalogo
                if item["codigo"] == codigo_actual
            ),
            None,
        )

        material = (
            seleccionado["material"]
            if seleccionado
            else linea.get(
                "material",
                "",
            )
        )

        stock = (
            seleccionado["stock"]
            if seleccionado
            else 0
        )

        unidad = (
            seleccionado["unidad"]
            if seleccionado
            else ""
        )

        st.success(
            f"📦 **{material}** · "
            f"Stock: {stock:g} {unidad} · "
            f"Código: {codigo_actual}"
        )

        if st.button(
            "🔄 Cambiar material",
            key=f"cambiar_material_{uid}",
        ):
            linea[
                "codigo_material"
            ] = ""
            linea[
                "material"
            ] = ""
            linea[
                "busqueda"
            ] = ""
            linea[
                "es_compra"
            ] = False

            st.session_state.pop(
                f"buscar_material_{uid}",
                None,
            )

            st.rerun()

        return

    if linea.get(
        "es_compra",
        False,
    ):
        material_compra = st.text_input(
            "Material a comprar",
            value=str(
                linea.get(
                    "material",
                    "",
                )
                or ""
            ),
            key=f"material_compra_{uid}",
        )

        linea[
            "material"
        ] = material_compra

        categorias = categorias_pedido_material()
        categoria_actual = str(
            linea.get(
                "categoria",
                "",
            )
            or ""
        ).strip()

        opciones_categoria = [
            "— Selecciona categoría —",
            *categorias,
        ]

        indice_categoria = (
            opciones_categoria.index(
                categoria_actual
            )
            if categoria_actual in opciones_categoria
            else 0
        )

        categoria_sel = st.selectbox(
            "Categoría",
            opciones_categoria,
            index=indice_categoria,
            key=f"categoria_compra_{uid}",
        )

        linea[
            "categoria"
        ] = (
            ""
            if categoria_sel == "— Selecciona categoría —"
            else categoria_sel
        )

        precio_unitario = st.text_input(
            "Precio unitario (€) · opcional",
            value=str(
                linea.get(
                    "precio_unitario",
                    "",
                )
                or ""
            ),
            placeholder="Ej.: 4,80",
            key=f"precio_compra_{uid}",
        )

        linea[
            "precio_unitario"
        ] = precio_unitario

        st.caption(
            "🛒 Al enviar el pedido, este material quedará creado "
            "en Inventario con stock 0 y su código de categoría."
        )

        if st.button(
            "🔎 Volver a buscar en inventario",
            key=f"volver_buscar_{uid}",
        ):
            linea[
                "es_compra"
            ] = False
            linea[
                "material"
            ] = ""
            linea[
                "busqueda"
            ] = ""
            linea[
                "categoria"
            ] = ""
            linea[
                "precio_unitario"
            ] = ""

            st.session_state.pop(
                f"material_compra_{uid}",
                None,
            )

            st.rerun()

        return

    consulta = st.text_input(
        "🔎 Busca material",
        value=str(
            linea.get(
                "busqueda",
                "",
            )
            or ""
        ),
        placeholder=(
            "Empieza a escribir: racor, silicona, tubo..."
        ),
        key=f"buscar_material_{uid}",
    )

    linea[
        "busqueda"
    ] = consulta

    resultados = _buscar_catalogo(
        catalogo,
        consulta,
    )

    if len(_normalizar(consulta)) < 2:
        st.caption(
            "Escribe al menos 2 letras para buscar."
        )
        return

    if resultados:
        st.caption(
            "Coincidencias en inventario:"
        )

        for item in resultados:
            stock = item["stock"]
            unidad = item["unidad"]

            if stock <= 0:
                estado_stock = "🔴"
            elif stock <= 2:
                estado_stock = "🟠"
            else:
                estado_stock = "✅"

            if st.button(
                (
                    f"{estado_stock} "
                    f"{item['material']} · "
                    f"Stock {stock:g} {unidad}"
                ),
                key=(
                    f"resultado_material_"
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
                linea[
                    "categoria"
                ] = ""
                linea[
                    "precio_unitario"
                ] = ""

                st.rerun()

    else:
        st.info(
            "No encuentro coincidencias en el inventario."
        )

    if st.button(
        f"🛒 Solicitar «{consulta.strip()}» como compra",
        key=f"solicitar_compra_{uid}",
        use_container_width=True,
        disabled=not bool(
            consulta.strip()
        ),
    ):
        linea[
            "codigo_material"
        ] = ""
        linea[
            "material"
        ] = consulta.strip()
        linea[
            "es_compra"
        ] = True

        st.rerun()


def ui_pedidos_operario(
    operario,
):
    st.subheader(
        "➕ Nuevo pedido"
    )

    st.caption(
        "Busca primero en el inventario. "
        "Si no aparece, puedes solicitarlo como compra."
    )

    inicializar_lineas_pedido()

    catalogo = _catalogo_inventario()

    fotos_pedido = st.file_uploader(
        "📷 Fotos del material o referencia",
        type=[
            "jpg",
            "jpeg",
            "png",
        ],
        accept_multiple_files=True,
        key="fotos_pedido_material",
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
            if foto.size > 5 * 1024 * 1024:
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

    centro = st.selectbox(
        "Centro",
        (
            list(
                CENTROS.keys()
            )
            if isinstance(
                CENTROS,
                dict,
            )
            else CENTROS
        ),
        key="pedido_material_centro",
    )

    prioridad = st.selectbox(
        "Prioridad",
        PRIORIDADES,
        index=1,
        key="pedido_material_prioridad",
    )

    observaciones_generales = st.text_area(
        "Observaciones generales del pedido",
        key=(
            "pedido_material_"
            "observaciones_generales"
        ),
    )

    st.markdown(
        "### 📋 Materiales"
    )

    lineas = st.session_state[
        "pedido_material_lineas_ui"
    ]

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
                key=f"pedido_material_cantidad_{uid}",
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
                key=f"pedido_material_obs_{uid}",
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
                key=f"pedido_material_link_{uid}",
            )

            linea[
                "cantidad"
            ] = cantidad
            linea[
                "observaciones"
            ] = obs_linea
            linea[
                "link_material"
            ] = link_linea

            if len(lineas) > 1:
                if st.button(
                    "🗑️ Eliminar este material",
                    key=f"eliminar_linea_{uid}",
                ):
                    eliminar_linea_pedido(
                        uid
                    )
                    st.rerun()

    col1, col2 = st.columns(
        [1, 2]
    )

    with col1:
        if st.button(
            "➕ Añadir otro material",
            use_container_width=True,
        ):
            añadir_linea_pedido()
            st.rerun()

    with col2:
        enviar = st.button(
            "📨 Enviar pedido",
            type="primary",
            use_container_width=True,
        )

    if enviar:
        lineas_validas = []

        for linea in st.session_state[
            "pedido_material_lineas_ui"
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

            es_compra = bool(
                linea.get(
                    "es_compra",
                    False,
                )
            )

            categoria = str(
                linea.get(
                    "categoria",
                    "",
                )
                or ""
            ).strip()

            if es_compra and not categoria:
                st.warning(
                    f"Selecciona la categoría de «{material}»."
                )
                return

            precio_texto = str(
                linea.get(
                    "precio_unitario",
                    "",
                )
                or ""
            ).strip()

            precio_unitario = None

            if precio_texto:
                try:
                    precio_unitario = float(
                        precio_texto.replace(
                            ",",
                            ".",
                        )
                    )
                except Exception:
                    st.warning(
                        f"El precio de «{material}» no es válido."
                    )
                    return

                if precio_unitario < 0:
                    st.warning(
                        f"El precio de «{material}» no puede ser negativo."
                    )
                    return

            lineas_validas.append({
                "codigo_material": str(
                    linea.get(
                        "codigo_material",
                        "",
                    )
                    or ""
                ).strip(),
                "material": material,
                "categoria": categoria,
                "precio_unitario": precio_unitario,
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
            })

        if not lineas_validas:
            st.warning(
                "Añade al menos un material al pedido."
            )
            return

        if not fotos_validas:
            st.error(
                "Corrige las fotos antes de enviar el pedido."
            )
            return

        try:
            id_pedido = crear_pedido_material_multiple(
                operario=operario,
                centro=centro,
                edificio="",
                prioridad=prioridad,
                observaciones=observaciones_generales,
                lineas=lineas_validas,
                foto="postgres_fotos",
            )

        except Exception as e:
            st.error(
                f"No se pudo crear el pedido: {e}"
            )
            return

        if not id_pedido:
            st.error(
                "No se pudo crear el pedido."
            )
            return

        if fotos_pedido:
            guardar_fotos_pedido_material(
                id_pedido,
                fotos_pedido,
            )

        limpiar_lineas_pedido()

        st.success(
            "Pedido enviado a almacén."
        )
        st.rerun()

    st.divider()

    st.subheader(
        "🕓 Mis pedidos"
    )

    pedidos = obtener_pedidos_material(
        operario=operario,
        limite=150,
    )

    if not pedidos:
        st.info(
            "No tienes pedidos registrados."
        )
        return

    mapa_catalogo = _mapa_catalogo(
        catalogo
    )

    for p in pedidos:
        datos = leer_pedido(
            p
        )

        id_pedido = datos[
            "id_pedido"
        ]
        numero_pedido = (
            datos["numero_pedido"]
            or referencia_pedido(
                id_pedido
            )
        )
        fecha = datos["fecha"]
        centro = datos["centro"]
        material = datos["material"]
        prioridad = datos["prioridad"]
        estado = datos["estado"]
        observaciones = datos[
            "observaciones"
        ]

        icono = icono_estado(
            estado
        )

        titulo = (
            f"{icono} {numero_pedido} · "
            f"{material or 'Pedido material'} · "
            f"{estado}"
        )

        with st.expander(
            titulo
        ):
            st.write(
                f"**Fecha:** {fecha}"
            )
            st.write(
                f"**Centro:** {centro}"
            )
            st.write(
                f"**Prioridad:** {prioridad}"
            )
            st.write(
                f"**Estado general:** {estado}"
            )
            st.write(
                f"**Observaciones:** "
                f"{observaciones or '-'}"
            )

            mostrar_lineas_pedido(
                id_pedido,
                modo_abel=False,
                mapa_catalogo=mapa_catalogo,
            )

            mostrar_fotos_pedido(
                id_pedido,
                contexto="operario",
            )


def ui_pedidos_abel():
    st.subheader(
        "📥 Pedidos recibidos"
    )

    catalogo = _catalogo_inventario()
    mapa_catalogo = _mapa_catalogo(
        catalogo
    )

    filtro = st.selectbox(
        "Filtro",
        [
            "Pendientes / activos",
            "Todos",
        ],
        key="filtro_pedidos_abel",
    )

    solo_pendientes = (
        filtro == "Pendientes / activos"
    )

    pedidos = obtener_pedidos_material(
        operario=None,
        solo_pendientes=solo_pendientes,
        limite=300,
    )

    if not pedidos:
        st.info(
            "No hay pedidos de material."
        )
        return

    for p in pedidos:
        datos = leer_pedido(
            p
        )

        id_pedido = datos[
            "id_pedido"
        ]
        numero_pedido = (
            datos["numero_pedido"]
            or referencia_pedido(
                id_pedido
            )
        )
        fecha = datos["fecha"]
        operario = datos["operario"]
        centro = datos["centro"]
        material = datos["material"]
        prioridad = datos["prioridad"]
        estado = datos["estado"]
        observaciones = datos[
            "observaciones"
        ]

        icono = icono_estado(
            estado
        )

        titulo = (
            f"{icono} {numero_pedido} · "
            f"{material or 'Pedido material'} · "
            f"{operario} · {estado}"
        )

        with st.expander(
            titulo
        ):
            st.write(
                f"**Fecha:** {fecha}"
            )
            st.write(
                f"**Operario:** {operario}"
            )
            st.write(
                f"**Centro:** {centro}"
            )
            st.write(
                f"**Prioridad:** {prioridad}"
            )
            st.write(
                f"**Estado general:** {estado}"
            )
            st.write(
                f"**Observaciones:** "
                f"{observaciones or '-'}"
            )

            mostrar_lineas_pedido(
                id_pedido,
                modo_abel=True,
                mapa_catalogo=mapa_catalogo,
            )

            mostrar_fotos_pedido(
                id_pedido,
                contexto="abel",
            )

            st.divider()

            st.markdown(
                "### Cambiar estado de todo el pedido"
            )

            nuevo_estado = st.selectbox(
                "Estado general del pedido",
                ESTADOS_PEDIDO,
                index=(
                    ESTADOS_PEDIDO.index(
                        estado
                    )
                    if estado in ESTADOS_PEDIDO
                    else 0
                ),
                key=f"estado_pedido_{id_pedido}",
            )

            if nuevo_estado == "Entregado":
                st.caption(
                    "Al entregar, los materiales catalogados "
                    "se descontarán del inventario una sola vez."
                )

            if st.button(
                "💾 Guardar estado general",
                key=f"guardar_estado_pedido_{id_pedido}",
                use_container_width=True,
            ):
                resultado = cambiar_estado_pedido(
                    id_pedido,
                    nuevo_estado,
                )

                if isinstance(
                    resultado,
                    tuple,
                ):
                    ok, mensaje = resultado
                else:
                    ok = True
                    mensaje = (
                        "Estado general actualizado."
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

            st.divider()

            confirmar_borrado = st.checkbox(
                "Confirmar borrado",
                key=(
                    f"confirmar_borrado_pedido_"
                    f"{id_pedido}"
                ),
            )

            if st.button(
                "🗑️ Borrar pedido",
                key=f"borrar_pedido_{id_pedido}",
            ):
                if confirmar_borrado:
                    borrar_pedido_material(
                        id_pedido
                    )

                    st.warning(
                        "Pedido eliminado."
                    )
                    st.rerun()

                else:
                    st.error(
                        "Debes confirmar el borrado."
                    )

