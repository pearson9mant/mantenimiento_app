import streamlit as st

from modules.inventario import obtener_materiales_para_select
from modules.ordenes import actualizar_estado
from modules.pedidos_material import (
    crear_pedido_material_multiple,
    obtener_numero_pedido,
)
from modules.pedidos_ot import (
    vincular_pedido_a_ot,
    obtener_pedidos_de_ot,
    obtener_ot_de_pedido,
)


def _normalizar_materiales(filas):
    resultado = []

    for fila in filas or []:
        try:
            codigo = str(fila[0] or "").strip()
            material = str(fila[1] or "").strip()
            stock = float(fila[2] or 0)
            unidad = str(fila[3] or "").strip()
        except Exception:
            continue

        if material:
            resultado.append({
                "codigo": codigo,
                "material": material,
                "stock": stock,
                "unidad": unidad,
            })

    resultado.sort(
        key=lambda item: (
            0 if item["stock"] > 0 else 1,
            item["material"].lower(),
        )
    )

    return resultado


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
    Solicitud de material nacida desde una OT.

    - hereda OT y ubicación;
    - crea un PED-MAT normal;
    - lo vincula en una tabla independiente;
    - pasa la OT a Pendiente material al enviar;
    - no altera los pedidos generales existentes.
    """
    numero_ot = str(numero_ot or "").strip()

    if not numero_ot:
        return

    pedidos = obtener_pedidos_de_ot(
        numero_ot,
        solo_activos=False,
    )

    if pedidos:
        st.markdown("### 📦 Pedidos vinculados a esta OT")

        for (
            _id_pedido,
            numero_pedido,
            estado,
            fecha,
            _prioridad,
        ) in pedidos:
            st.caption(
                f"{numero_pedido or '-'} · "
                f"{estado or '-'} · {fecha or '-'}"
            )

    clave_abrir = f"pedido_ot_abrir_{id_orden}"

    if not st.session_state.get(
        clave_abrir,
        False,
    ):
        if st.button(
            "📦 Solicitar material para esta OT",
            key=f"pedido_ot_boton_{id_orden}",
            use_container_width=True,
        ):
            st.session_state[clave_abrir] = True
            st.rerun()

        return

    with st.container(border=True):
        st.markdown(
            f"### 📦 Solicitud de material · {numero_ot}"
        )

        st.caption(
            "El pedido quedará vinculado a esta OT y Abel verá "
            "la avería y su ubicación."
        )

        st.info(
            "📍 "
            + " · ".join(
                parte
                for parte in [
                    str(centro or "").strip(),
                    str(edificio or "").strip(),
                    str(planta or "").strip(),
                    str(espacio or "").strip(),
                ]
                if parte
            )
        )

        try:
            catalogo = _normalizar_materiales(
                obtener_materiales_para_select()
            )
        except Exception:
            catalogo = []

        tipo = st.radio(
            "Tipo de material",
            [
                "📦 Inventario",
                "🛒 Compra / no catalogado",
            ],
            horizontal=True,
            key=f"pedido_ot_tipo_{id_orden}",
        )

        codigo_material = ""
        material = ""

        if tipo == "📦 Inventario":
            if not catalogo:
                st.warning(
                    "No hay materiales disponibles en Inventario."
                )
            else:
                opciones = [
                    item["codigo"]
                    for item in catalogo
                ]

                mapa = {
                    item["codigo"]: item
                    for item in catalogo
                }

                codigo_material = st.selectbox(
                    "Material",
                    opciones,
                    format_func=lambda codigo: (
                        f"{mapa[codigo]['material']} · "
                        f"Stock {mapa[codigo]['stock']:g} "
                        f"{mapa[codigo]['unidad']}"
                    ),
                    key=f"pedido_ot_material_{id_orden}",
                )

                material = mapa[
                    codigo_material
                ]["material"]

        else:
            material = st.text_input(
                "Material a solicitar",
                placeholder=(
                    "Ej.: secador de manos, "
                    "mecanismo específico, recambio..."
                ),
                key=f"pedido_ot_compra_{id_orden}",
            )

        cantidad = st.number_input(
            "Cantidad",
            min_value=1.0,
            step=1.0,
            value=1.0,
            key=f"pedido_ot_cantidad_{id_orden}",
        )

        observaciones = st.text_area(
            "Observaciones del pedido",
            placeholder=(
                "Modelo, medidas, referencia o cualquier dato "
                "que ayude a preparar el material."
            ),
            key=f"pedido_ot_obs_{id_orden}",
        )

        c1, c2 = st.columns(2)

        with c1:
            if st.button(
                "📨 Enviar pedido a Abel",
                key=f"pedido_ot_enviar_{id_orden}",
                use_container_width=True,
                type="primary",
            ):
                material_limpio = str(
                    material or ""
                ).strip()

                if not material_limpio:
                    st.warning(
                        "Indica el material que necesitas."
                    )
                else:
                    id_pedido = crear_pedido_material_multiple(
                        operario=operario,
                        centro=centro,
                        edificio=edificio,
                        prioridad=prioridad or "Media",
                        observaciones=(
                            f"Material para OT {numero_ot}"
                            + (
                                f" · {observaciones.strip()}"
                                if str(observaciones or "").strip()
                                else ""
                            )
                        ),
                        lineas=[
                            {
                                "codigo_material": codigo_material,
                                "material": material_limpio,
                                "cantidad": cantidad,
                                "observaciones": observaciones,
                                "link_material": "",
                            }
                        ],
                        foto="postgres_fotos",
                    )

                    if not id_pedido:
                        st.error(
                            "No se ha podido crear el pedido."
                        )
                    else:
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

                        actualizar_estado(
                            id_orden,
                            "Pendiente material",
                            (
                                "Material solicitado en "
                                f"{obtener_numero_pedido(id_pedido)}."
                            ),
                        )

                        st.session_state[
                            "recalcular_corazon"
                        ] = True

                        st.session_state[
                            clave_abrir
                        ] = False

                        st.success(
                            "Pedido enviado y vinculado a la OT."
                        )
                        st.rerun()

        with c2:
            if st.button(
                "Cancelar",
                key=f"pedido_ot_cancelar_{id_orden}",
                use_container_width=True,
            ):
                st.session_state[
                    clave_abrir
                ] = False
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

    st.markdown("### 🔗 Orden de trabajo vinculada")

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
