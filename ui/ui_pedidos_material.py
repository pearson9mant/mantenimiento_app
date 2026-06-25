import streamlit as st

from config import CENTROS

from modules.pedidos_material import (
    crear_pedido_material_multiple,
    obtener_pedidos_material,
    obtener_lineas_pedido,
    cambiar_estado_pedido,
    cambiar_estado_linea_pedido,
    guardar_fotos_pedido_material,
    borrar_pedido_material,
    ESTADOS_PEDIDO
)

from modules.ordenes import obtener_fotos_ot


OPERARIOS = [
    "J.A. Almeda",
    "Luis Lozano",
    "Abel Vasquez"
]


PRIORIDADES = [
    "Baja",
    "Media",
    "Alta",
    "Urgente"
]


def usuario_actual():
    return str(
        st.session_state.get("operario_activo")
        or st.session_state.get("usuario")
        or st.session_state.get("nombre")
        or ""
    ).strip()


def es_abel():
    usuario = usuario_actual().lower()
    return "abel" in usuario


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
        "administración"
    ]


def referencia_pedido(id_pedido):
    return f"PED-MAT-{int(id_pedido):04d}"


def inicializar_lineas_pedido():
    if "pedido_material_lineas_ui" not in st.session_state:
        st.session_state["pedido_material_lineas_ui"] = [
            {
                "material": "",
                "cantidad": 1.0,
                "observaciones": "",
                "link_material": ""
            }
        ]


def añadir_linea_pedido():
    inicializar_lineas_pedido()

    st.session_state["pedido_material_lineas_ui"].append(
        {
            "material": "",
            "cantidad": 1.0,
            "observaciones": "",
            "link_material": ""
        }
    )


def eliminar_linea_pedido(indice):
    inicializar_lineas_pedido()

    lineas = st.session_state["pedido_material_lineas_ui"]

    if len(lineas) > 1:
        lineas.pop(indice)

    st.session_state["pedido_material_lineas_ui"] = lineas


def limpiar_lineas_pedido():
    st.session_state["pedido_material_lineas_ui"] = [
        {
            "material": "",
            "cantidad": 1.0,
            "observaciones": "",
            "link_material": ""
        }
    ]


def leer_pedido(p):
    """
    Compatible con el formato devuelto por obtener_pedidos_material().
    """

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
        "numero_pedido": referencia_pedido(p[0]),
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
        "Cancelado": "⚫"
    }.get(estado, "⚪")


def mostrar_fotos_pedido(id_pedido):
    try:
        numero_pedido = referencia_pedido(id_pedido)
        fotos = obtener_fotos_ot(numero_pedido)

        if fotos:
            st.markdown("### 📷 Fotos")

            for nombre_foto, foto_data in fotos:
                st.image(
                    bytes(foto_data),
                    caption=nombre_foto,
                    width=250
                )

    except Exception as e:
        st.caption(f"Error fotos: {e}")


def mostrar_link_material(link_material):
    link_material = str(link_material or "").strip()

    if not link_material:
        return

    if link_material.startswith("http://") or link_material.startswith("https://"):
        st.link_button("🔗 Abrir enlace material", link_material)
    else:
        st.info(f"🔗 Enlace / referencia: {link_material}")


def mostrar_lineas_pedido(id_pedido, modo_abel=False):
    try:
        lineas = obtener_lineas_pedido(id_pedido)
    except Exception as e:
        st.error(f"No se pudieron cargar las líneas del pedido: {e}")
        return

    if not lineas:
        st.info("Este pedido no tiene líneas de material.")
        return

    st.markdown("### 📋 Materiales solicitados")

    for linea in lineas:
        id_linea = linea[0]
        material = linea[3]
        cantidad = linea[4]
        estado = linea[5] or "Pendiente"
        observaciones = linea[6] or ""
        link_material = linea[7] or ""

        icono = icono_estado(estado)

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{icono} {material}**")
                st.caption(f"Estado: {estado}")

                if observaciones:
                    st.write(f"**Obs.:** {observaciones}")

                mostrar_link_material(link_material)

            with col2:
                st.metric("Cantidad", cantidad)

            if modo_abel:
                nuevo_estado_linea = st.selectbox(
                    "Estado línea",
                    ESTADOS_PEDIDO,
                    index=ESTADOS_PEDIDO.index(estado)
                    if estado in ESTADOS_PEDIDO else 0,
                    key=f"estado_linea_pedido_{id_linea}"
                )

                if st.button(
                    "💾 Guardar línea",
                    key=f"guardar_linea_pedido_{id_linea}"
                ):
                    cambiar_estado_linea_pedido(
                        id_linea,
                        nuevo_estado_linea
                    )

                    st.success("Línea actualizada.")
                    st.rerun()


def ui_pedidos_material():
    st.title("📦 Pedidos de material")

    usuario = usuario_actual()

    if not usuario:
        st.warning("No se ha detectado el usuario actual.")
        return

    if es_admin():
        tab1, tab2 = st.tabs([
            "➕ Nuevo pedido",
            "📥 Pedidos recibidos"
        ])

        with tab1:
            ui_pedidos_operario(usuario)

        with tab2:
            ui_pedidos_abel()

    elif es_abel():
        ui_pedidos_abel()

    else:
        ui_pedidos_operario(usuario)


def ui_pedidos_operario(operario):
    st.subheader("➕ Nuevo pedido")

    inicializar_lineas_pedido()

    fotos_pedido = st.file_uploader(
        "📷 Fotos del material o referencia",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="fotos_pedido_material"
    )

    if fotos_pedido:
        st.markdown("#### 👀 Vista previa")

        for foto in fotos_pedido:
            st.image(
                foto,
                caption=foto.name,
                width=180
            )

    centro = st.selectbox(
        "Centro",
        list(CENTROS.keys()) if isinstance(CENTROS, dict) else CENTROS,
        key="pedido_material_centro"
    )

    prioridad = st.selectbox(
        "Prioridad",
        PRIORIDADES,
        index=1,
        key="pedido_material_prioridad"
    )

    observaciones_generales = st.text_area(
        "Observaciones generales del pedido",
        key="pedido_material_observaciones_generales"
    )

    st.markdown("### 📋 Materiales")

    lineas = st.session_state["pedido_material_lineas_ui"]

    for i, linea in enumerate(lineas):
        with st.container(border=True):
            st.markdown(f"**Material {i + 1}**")

            material = st.text_input(
                "Material solicitado",
                value=linea.get("material", ""),
                key=f"pedido_material_nombre_{i}"
            )

            cantidad = st.number_input(
                "Cantidad",
                min_value=1.0,
                step=1.0,
                value=float(linea.get("cantidad", 1.0) or 1.0),
                key=f"pedido_material_cantidad_{i}"
            )

            obs_linea = st.text_input(
                "Observaciones de esta línea",
                value=linea.get("observaciones", ""),
                key=f"pedido_material_obs_linea_{i}"
            )

            link_linea = st.text_input(
                "🔗 Enlace / referencia de este material",
                value=linea.get("link_material", ""),
                placeholder="Amazon, Leroy, proveedor, referencia...",
                key=f"pedido_material_link_linea_{i}"
            )

            st.session_state["pedido_material_lineas_ui"][i] = {
                "material": material,
                "cantidad": cantidad,
                "observaciones": obs_linea,
                "link_material": link_linea
            }

            if len(lineas) > 1:
                if st.button(
                    "🗑️ Eliminar este material",
                    key=f"eliminar_linea_pedido_material_{i}"
                ):
                    eliminar_linea_pedido(i)
                    st.rerun()

    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("➕ Añadir otro material"):
            añadir_linea_pedido()
            st.rerun()

    with col2:
        enviar = st.button("📨 Enviar pedido", type="primary")

    if enviar:
        lineas_validas = []

        for linea in st.session_state["pedido_material_lineas_ui"]:
            material = str(linea.get("material") or "").strip()

            if material:
                lineas_validas.append(
                    {
                        "codigo_material": "",
                        "material": material,
                        "cantidad": float(linea.get("cantidad") or 1),
                        "observaciones": linea.get("observaciones", ""),
                        "link_material": linea.get("link_material", "")
                    }
                )

        if not lineas_validas:
            st.warning("Añade al menos un material al pedido.")
            return

        id_pedido = crear_pedido_material_multiple(
            operario=operario,
            centro=centro,
            edificio="",
            prioridad=prioridad,
            observaciones=observaciones_generales,
            lineas=lineas_validas,
            foto="postgres_fotos"
        )

        if fotos_pedido and id_pedido:
            try:
                guardar_fotos_pedido_material(
                    id_pedido,
                    fotos_pedido
                )

            except Exception as e:
                st.error(f"Error guardando fotos: {e}")

        limpiar_lineas_pedido()

        st.success("Pedido enviado a almacén.")
        st.rerun()

    st.divider()

    st.subheader("🕓 Mis pedidos")

    pedidos = obtener_pedidos_material(
        operario=operario
    )

    if not pedidos:
        st.info("No tienes pedidos registrados.")
        return

    for p in pedidos:
        datos = leer_pedido(p)

        id_pedido = datos["id_pedido"]
        numero_pedido = datos["numero_pedido"] or referencia_pedido(id_pedido)
        fecha = datos["fecha"]
        centro = datos["centro"]
        material = datos["material"]
        prioridad = datos["prioridad"]
        estado = datos["estado"]
        observaciones = datos["observaciones"]

        icono = icono_estado(estado)

        titulo = f"{icono} {numero_pedido} · {material or 'Pedido material'} · {estado}"

        with st.expander(titulo):
            st.write(f"**Fecha:** {fecha}")
            st.write(f"**Centro:** {centro}")
            st.write(f"**Prioridad:** {prioridad}")
            st.write(f"**Estado general:** {estado}")
            st.write(f"**Observaciones:** {observaciones or '-'}")

            mostrar_lineas_pedido(id_pedido, modo_abel=False)
            mostrar_fotos_pedido(id_pedido)


def ui_pedidos_abel():
    st.subheader("📥 Pedidos recibidos")

    filtro = st.selectbox(
        "Filtro",
        [
            "Pendientes / activos",
            "Todos"
        ]
    )

    solo_pendientes = (
        filtro == "Pendientes / activos"
    )

    pedidos = obtener_pedidos_material(
        operario=None,
        solo_pendientes=solo_pendientes
    )

    if not pedidos:
        st.info("No hay pedidos de material.")
        return

    for p in pedidos:
        datos = leer_pedido(p)

        id_pedido = datos["id_pedido"]
        numero_pedido = datos["numero_pedido"] or referencia_pedido(id_pedido)
        fecha = datos["fecha"]
        operario = datos["operario"]
        centro = datos["centro"]
        material = datos["material"]
        prioridad = datos["prioridad"]
        estado = datos["estado"]
        observaciones = datos["observaciones"]

        icono = icono_estado(estado)

        titulo = f"{icono} {numero_pedido} · {material or 'Pedido material'} · {operario} · {estado}"

        with st.expander(titulo):
            st.write(f"**Fecha:** {fecha}")
            st.write(f"**Operario:** {operario}")
            st.write(f"**Centro:** {centro}")
            st.write(f"**Prioridad:** {prioridad}")
            st.write(f"**Estado general:** {estado}")
            st.write(f"**Observaciones:** {observaciones or '-'}")

            mostrar_lineas_pedido(id_pedido, modo_abel=True)
            mostrar_fotos_pedido(id_pedido)

            st.divider()

            st.markdown("### Cambiar estado de todo el pedido")

            nuevo_estado = st.selectbox(
                "Estado general del pedido",
                ESTADOS_PEDIDO,
                index=ESTADOS_PEDIDO.index(estado)
                if estado in ESTADOS_PEDIDO else 0,
                key=f"estado_pedido_{id_pedido}"
            )

            if st.button(
                "💾 Guardar estado general",
                key=f"guardar_estado_pedido_{id_pedido}"
            ):
                cambiar_estado_pedido(
                    id_pedido,
                    nuevo_estado
                )

                st.success("Estado general actualizado.")
                st.rerun()

            st.divider()

            confirmar_borrado = st.checkbox(
                "Confirmar borrado",
                key=f"confirmar_borrado_pedido_{id_pedido}"
            )

            if st.button(
                "🗑️ Borrar pedido",
                key=f"borrar_pedido_{id_pedido}"
            ):
                if confirmar_borrado:
                    borrar_pedido_material(
                        id_pedido
                    )

                    st.warning("Pedido eliminado.")
                    st.rerun()

                else:
                    st.error("Debes confirmar el borrado.")

