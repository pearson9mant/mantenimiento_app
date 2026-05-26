import streamlit as st

from config import CENTROS
from modules.pedidos_material import (
    crear_pedido_material,
    obtener_pedidos_material,
    cambiar_estado_pedido,
    ESTADOS_PEDIDO
)


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
        st.session_state.get("usuario")
        or st.session_state.get("operario_activo")
        or st.session_state.get("nombre")
        or ""
    ).strip()


def es_abel():
    usuario = usuario_actual().lower()
    return "abel" in usuario


def ui_pedidos_material():
    st.title("📦 Pedidos de material")

    usuario = usuario_actual()

    if not usuario:
        st.warning("No se ha detectado el operario actual.")
        return

    if es_abel():
        ui_pedidos_abel()
    else:
        ui_pedidos_operario(usuario)


def ui_pedidos_operario(operario):
    st.subheader("➕ Nuevo pedido")

    with st.form("form_pedido_material"):
        centro = st.selectbox("Centro", list(CENTROS.keys()) if isinstance(CENTROS, dict) else CENTROS)
        material = st.text_input("Material solicitado")
        cantidad = st.number_input("Cantidad", min_value=1.0, step=1.0)
        prioridad = st.selectbox("Prioridad", PRIORIDADES, index=1)
        observaciones = st.text_area("Observaciones")

        enviar = st.form_submit_button("📨 Enviar pedido")

        if enviar:
            if not material.strip():
                st.warning("Indica el material solicitado.")
            else:
                crear_pedido_material(
                    operario=operario,
                    centro=centro,
                    material=material,
                    cantidad=cantidad,
                    prioridad=prioridad,
                    observaciones=observaciones
                )
                st.success("Pedido enviado a almacén.")

    st.divider()
    st.subheader("🕓 Mis pedidos")

    pedidos = obtener_pedidos_material(operario=operario)

    if not pedidos:
        st.info("No tienes pedidos registrados.")
        return

    for p in pedidos:
        id_pedido = p[0]
        fecha = p[1]
        operario = p[2]
        centro = p[3]
        material = p[4]
        cantidad = p[5]
        prioridad = p[6]
        estado = p[7]
        observaciones = p[8]

        icono = {
            "Pendiente": "🟡",
            "Preparado": "🔵",
            "Entregado": "🟢",
            "Sin stock": "🔴",
            "Cancelado": "⚫"
        }.get(estado, "⚪")

        with st.expander(f"{icono} {material} · {cantidad} uds · {estado}"):
            st.write(f"**Fecha:** {fecha}")
            st.write(f"**Centro:** {centro}")
            st.write(f"**Prioridad:** {prioridad}")
            st.write(f"**Observaciones:** {observaciones or '-'}")


def ui_pedidos_abel():
    st.subheader("📥 Pedidos recibidos")

    filtro = st.selectbox(
        "Filtro",
        ["Pendientes / activos", "Todos"]
    )

    solo_pendientes = filtro == "Pendientes / activos"

    pedidos = obtener_pedidos_material(
        operario=None,
        solo_pendientes=solo_pendientes
    )

    if not pedidos:
        st.info("No hay pedidos de material.")
        return

    for p in pedidos:
        id_pedido = p[0]
        fecha = p[1]
        operario = p[2]
        centro = p[3]
        material = p[4]
        cantidad = p[5]
        prioridad = p[6]
        estado = p[7]
        observaciones = p[8]

        icono = {
            "Pendiente": "🟡",
            "Preparado": "🔵",
            "Entregado": "🟢",
            "Sin stock": "🔴",
            "Cancelado": "⚫"
        }.get(estado, "⚪")

        with st.expander(f"{icono} {material} · {cantidad} uds · {operario} · {estado}"):
            st.write(f"**Fecha:** {fecha}")
            st.write(f"**Operario:** {operario}")
            st.write(f"**Centro:** {centro}")
            st.write(f"**Prioridad:** {prioridad}")
            st.write(f"**Observaciones:** {observaciones or '-'}")

            nuevo_estado = st.selectbox(
                "Estado del pedido",
                ESTADOS_PEDIDO,
                index=ESTADOS_PEDIDO.index(estado) if estado in ESTADOS_PEDIDO else 0,
                key=f"estado_pedido_{id_pedido}"
            )

            if st.button("💾 Guardar estado", key=f"guardar_estado_pedido_{id_pedido}"):
                cambiar_estado_pedido(id_pedido, nuevo_estado)
                st.success("Estado actualizado.")
                st.rerun()
