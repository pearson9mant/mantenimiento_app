import re
import unicodedata
import streamlit as st

from database.db import conectar, _sql
from config import CENTROS

from modules.pedidos_material import (
    crear_pedido_material_multiple,
    obtener_pedidos_material,
    obtener_lineas_pedido,
    archivar_pedido_material,
    obtener_datos_recepcion_linea,
    registrar_recepcion_linea_pedido,
    guardar_fotos_pedido_material,
)

from modules.ordenes import obtener_fotos_ot
from modules.pedidos_ot import obtener_ot_de_pedido
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


def _guardar_precio_linea_abel(id_linea, precio_unitario):
    """Guarda solo el precio de una línea. No registra recepción ni mueve stock."""
    try:
        precio = float(precio_unitario or 0)
    except Exception:
        return False, "El precio no es válido."

    if precio <= 0:
        return False, "Indica un precio mayor que 0,00 €."

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            _sql("""
                UPDATE pedidos_material_lineas
                SET precio_unitario = ?
                WHERE id = ?
            """),
            (precio, int(id_linea)),
        )
        conn.commit()
        return True, "Precio guardado."
    except Exception as e:
        conn.rollback()
        return False, f"No se pudo guardar el precio: {e}"
    finally:
        conn.close()


def _aprobaciones_gerencia_por_pedido(ids_pedido):
    """Lee las aprobaciones visibles de Abel en una sola consulta."""
    ids = [int(x) for x in ids_pedido if x is not None]
    if not ids:
        return {}

    conn = conectar()
    cur = conn.cursor()
    try:
        modulo = conn.__class__.__module__.lower()
        marcador = "?" if "sqlite" in modulo else "%s"
        marcas = ", ".join([marcador] * len(ids))
        try:
            cur.execute(
                f"""
                SELECT id, aprobacion_gerencia
                FROM pedidos_material
                WHERE id IN ({marcas})
                """,
                tuple(ids),
            )
            return {int(f[0]): str(f[1] or "").strip() for f in cur.fetchall()}
        except Exception:
            conn.rollback()
            return {}
    finally:
        conn.close()


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
                modo_abel
                and datos_recepcion
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
                precio_guardado = float(
                    datos_recepcion.get(
                        "precio_unitario",
                        0,
                    )
                    or 0
                )

                st.caption(
                    f"📦 Recibido por el operario: "
                    f"{cantidad_recibida:g} de {cantidad_pedida:g} · "
                    f"Pendiente: {pendiente:g}"
                )

                if precio_guardado > 0:
                    st.caption(
                        f"💶 Precio unitario: "
                        f"{precio_guardado:.2f} €"
                    )
                else:
                    st.warning("💶 Pendiente de precio")

                precio_abel = st.number_input(
                    "Precio unitario (€)",
                    min_value=0.0,
                    value=float(precio_guardado if precio_guardado > 0 else 0.0),
                    step=0.01,
                    format="%.2f",
                    key=f"precio_abel_{id_linea}",
                )

                if st.button(
                    "💾 Guardar precio",
                    key=f"guardar_precio_abel_{id_linea}",
                    use_container_width=True,
                ):
                    ok_precio, mensaje_precio = _guardar_precio_linea_abel(
                        id_linea,
                        precio_abel,
                    )
                    if ok_precio:
                        st.success(mensaje_precio)
                        st.rerun()
                    else:
                        st.error(mensaje_precio)

            if (
                not modo_abel
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




def _borrar_pedido_seguro(id_pedido):
    """Borra un pedido y su vínculo con OT, pero nunca borra la OT."""
    conn = conectar()
    cur = conn.cursor()

    try:
        cur.execute(
            _sql("DELETE FROM pedidos_material_ot WHERE pedido_id = ?"),
            (int(id_pedido),),
        )
        cur.execute(
            _sql("DELETE FROM pedidos_material_lineas WHERE pedido_id = ?"),
            (int(id_pedido),),
        )
        cur.execute(
            _sql("DELETE FROM pedidos_material WHERE id = ?"),
            (int(id_pedido),),
        )
        conn.commit()
        return True, "Pedido eliminado."
    except Exception as e:
        conn.rollback()
        return False, f"No se pudo eliminar el pedido: {e}"
    finally:
        conn.close()

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

            if estado not in ["Entregado", "Archivado"]:
                with st.expander("🗑️ Eliminar pedido"):
                    st.warning(
                        "El pedido se eliminará definitivamente. "
                        "Si está vinculado a una OT, la OT NO se eliminará."
                    )
                    confirmar = st.checkbox(
                        f"Confirmo que quiero eliminar {numero_pedido}",
                        key=f"confirmar_borrar_pedido_{id_pedido}",
                    )
                    if st.button(
                        "🗑️ Eliminar definitivamente",
                        disabled=not confirmar,
                        key=f"borrar_pedido_{id_pedido}",
                    ):
                        ok, mensaje = _borrar_pedido_seguro(id_pedido)
                        if ok:
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.error(mensaje)



def _situacion_pedidos_abel(ids_pedido):
    """Lee precios y aprobación de varios pedidos en una sola consulta."""
    ids = []
    for valor in ids_pedido or []:
        try:
            ids.append(int(valor))
        except Exception:
            continue

    if not ids:
        return {}

    conn = conectar()
    cur = conn.cursor()
    modulo = conn.__class__.__module__.lower()
    marcador = "?" if "sqlite" in modulo else "%s"
    marcas = ", ".join([marcador] * len(ids))

    try:
        try:
            cur.execute(
                f"""
                SELECT
                    p.id,
                    COALESCE(p.aprobacion_gerencia, ''),
                    COUNT(l.id),
                    SUM(CASE
                        WHEN COALESCE(l.precio_unitario, 0) > 0 THEN 0
                        ELSE 1
                    END)
                FROM pedidos_material p
                LEFT JOIN pedidos_material_lineas l ON l.pedido_id = p.id
                WHERE p.id IN ({marcas})
                GROUP BY p.id, p.aprobacion_gerencia
                """,
                tuple(ids),
            )
            return {
                int(pid): {
                    "aprobado": str(apr or "") == "Aprobado",
                    "total_lineas": int(total or 0),
                    "sin_precio": int(sin_precio or 0),
                }
                for pid, apr, total, sin_precio in cur.fetchall()
            }
        except Exception:
            conn.rollback()
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT
                    pedido_id,
                    COUNT(id),
                    SUM(CASE
                        WHEN COALESCE(precio_unitario, 0) > 0 THEN 0
                        ELSE 1
                    END)
                FROM pedidos_material_lineas
                WHERE pedido_id IN ({marcas})
                GROUP BY pedido_id
                """,
                tuple(ids),
            )
            return {
                int(pid): {
                    "aprobado": False,
                    "total_lineas": int(total or 0),
                    "sin_precio": int(sin_precio or 0),
                }
                for pid, total, sin_precio in cur.fetchall()
            }
    finally:
        conn.close()

def ui_pedidos_abel():
    st.subheader(
        "📥 Solicitudes de material"
    )

    st.caption(
        "Nuevo flujo: completa únicamente los precios que falten. "
        "Cuando todos estén informados, Gerencia puede aprobar el pedido. "
        "Los pedidos no se borran: pasan de fase y quedan en histórico."
    )

    catalogo = _catalogo_inventario()
    mapa_catalogo = _mapa_catalogo(
        catalogo
    )

    filtro = st.selectbox(
        "Mostrar",
        [
            "Por completar precio",
            "Esperando Gerencia",
            "Aprobados para comprar",
            "Histórico",
        ],
        key="filtro_pedidos_abel",
    )

    pedidos_todos = obtener_pedidos_material(
        operario=None,
        solo_pendientes=False,
        limite=300,
    )

    situacion = _situacion_pedidos_abel(
        [leer_pedido(p).get("id_pedido") for p in pedidos_todos]
    )

    pedidos = []
    for p in pedidos_todos:
        d = leer_pedido(p)
        pedido_id = int(d.get("id_pedido") or 0)
        estado_pedido = str(d.get("estado") or "").strip()
        activo = estado_pedido in ["Pendiente", "Preparado", "Sin stock"]
        s = situacion.get(
            pedido_id,
            {"aprobado": False, "total_lineas": 0, "sin_precio": 0},
        )
        precios_completos = (
            int(s.get("total_lineas") or 0) > 0
            and int(s.get("sin_precio") or 0) == 0
        )
        aprobado = bool(s.get("aprobado"))

        if filtro == "Por completar precio":
            mostrar = activo and not aprobado and not precios_completos
        elif filtro == "Esperando Gerencia":
            mostrar = activo and not aprobado and precios_completos
        elif filtro == "Aprobados para comprar":
            mostrar = activo and aprobado
        else:
            mostrar = not activo

        if mostrar:
            pedidos.append(p)

    if not pedidos:
        st.info(
            "No hay solicitudes de material."
        )
        return

    aprobaciones_gerencia = _aprobaciones_gerencia_por_pedido(
        [leer_pedido(p).get("id_pedido") for p in pedidos]
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
        operario = datos["operario"]
        centro = datos["centro"]
        material = datos["material"]
        prioridad = datos["prioridad"]
        estado = datos["estado"]
        observaciones = datos[
            "observaciones"
        ]

        try:
            contexto_ot = obtener_ot_de_pedido(
                id_pedido
            )
        except Exception:
            contexto_ot = None

        descripcion_ot = ""
        numero_ot = ""
        ubicacion_ot = ""

        if contexto_ot:
            descripcion_ot = str(
                contexto_ot.get("descripcion_ot") or ""
            ).strip()
            numero_ot = str(
                contexto_ot.get("numero_ot") or ""
            ).strip()
            ubicacion_ot = " · ".join(
                str(contexto_ot.get(campo) or "").strip()
                for campo in [
                    "centro",
                    "edificio",
                    "planta",
                    "espacio",
                ]
                if str(
                    contexto_ot.get(campo) or ""
                ).strip()
            )

        es_ampliacion = (
            "AMPLIACIÓN DEL PEDIDO"
            in str(observaciones or "").upper()
        )

        asunto_pedido = (
            descripcion_ot
            or material
            or "Pedido material"
        )

        marca_ampliacion = (
            " · ➕ AMPLIACIÓN"
            if es_ampliacion
            else ""
        )

        titulo = (
            f"📦 {numero_pedido} · "
            f"{asunto_pedido}"
            f"{marca_ampliacion} · "
            f"{operario}"
        )

        with st.expander(
            titulo
        ):
            if contexto_ot:
                st.info(
                    f"🔗 **OT:** {numero_ot or '-'}\n\n"
                    f"🛠️ **Trabajo:** {descripcion_ot or '-'}\n\n"
                    f"📍 **Ubicación:** {ubicacion_ot or '-'}"
                )

            col_a, col_b = st.columns(2)

            with col_a:
                st.write(
                    f"**Fecha:** {fecha}"
                )
                st.write(
                    f"**Solicita:** {operario}"
                )
                st.write(
                    f"**Centro:** {centro}"
                )

            with col_b:
                st.write(
                    f"**Prioridad:** {prioridad}"
                )
                st.write(
                    f"**Situación del pedido:** {estado}"
                )
                if aprobaciones_gerencia.get(int(id_pedido)) == "Aprobado":
                    st.success("✅ Aprobado por Gerencia · puede comprarse")
                else:
                    st.caption("🟡 Pendiente de aprobación de Gerencia")

            if observaciones:
                st.write(
                    f"**Observaciones:** {observaciones}"
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

            st.caption(
                "ℹ️ Solo información. Si el material llega, "
                "el operario registra la recepción desde la OT."
            )

            if estado not in [
                "Entregado",
                "Cancelado",
                "Archivado",
            ]:
                situacion_pedido = situacion.get(
                    int(id_pedido),
                    {"aprobado": False, "total_lineas": 0, "sin_precio": 0},
                )
                if situacion_pedido.get("aprobado"):
                    st.success(
                        "✅ Aprobado por Gerencia · pendiente de compra/recepción."
                    )
                elif int(situacion_pedido.get("sin_precio") or 0) > 0:
                    st.info(
                        "💶 Completa los precios que falten. "
                        "Después pasará a Esperando Gerencia."
                    )
                else:
                    st.info(
                        "🟡 Precios completos · esperando aprobación de Gerencia."
                    )

