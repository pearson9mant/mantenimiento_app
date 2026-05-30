import streamlit as st
from pathlib import Path

from modules.inventario import (
    generar_codigo_material,
    crear_material_inventario,
    obtener_materiales_inventario,
    registrar_movimiento_inventario,
    obtener_movimientos_por_material,
    desactivar_material,
    activar_material,
    comprobar_material_antes_crear,
)

from modules.ubicaciones import CENTROS, obtener_edificios, obtener_espacios
from modules.alertas_empresas import obtener_alertas_empresas_externas


def rol_actual():
    return str(
        st.session_state.get("rol")
        or st.session_state.get("tipo_usuario")
        or st.session_state.get("perfil")
        or st.session_state.get("modo")
        or ""
    ).strip().lower()


def puede_borrar_inventario():
    return rol_actual() in ["admin", "administracion", "administración"]


def limpiar_nombre_archivo(texto):
    texto = str(texto)
    caracteres_malos = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for c in caracteres_malos:
        texto = texto.replace(c, "_")
    return texto.replace(" ", "_")


def limpiar_formulario_crear_material():
    claves = [
        "crear_material_nombre",
        "crear_categoria_material",
        "crear_material_unidad",
        "crear_material_stock_actual",
        "crear_material_stock_minimo",
        "crear_material_precio_unitario",
        "crear_material_fecha_compra",
        "crear_material_referencia_factura",
        "crear_material_observaciones_coste",
        "inv_mat_centro",
        "inv_mat_edificio",
        "inv_mat_ubicacion",
        "crear_material_proveedor",
        "crear_material_observaciones",
        "foto_material_mantenimiento"
    ]

    for clave in claves:
        if clave in st.session_state:
            del st.session_state[clave]

    st.session_state["inventario_material_creado_ok"] = True
    st.session_state["inventario_abrir_crear_material"] = True


def mostrar_historial_material(codigo):
    movimientos = obtener_movimientos_por_material(codigo)

    if not movimientos:
        st.info("Sin movimientos.")
        return

    total_entradas = sum(float(mov[1]) for mov in movimientos if mov[0] == "Entrada")
    total_salidas = sum(float(mov[1]) for mov in movimientos if mov[0] == "Salida")
    total_con_ot = len([mov for mov in movimientos if mov[3]])

    h1, h2, h3 = st.columns(3)
    h1.metric("Entradas", total_entradas)
    h2.metric("Salidas", total_salidas)
    h3.metric("Con OT", total_con_ot)

    filtro_historial = st.selectbox(
        "Filtrar historial",
        ["Todos", "Entradas", "Salidas", "Con OT"],
        key=f"filtro_historial_{codigo}"
    )

    movimientos_filtrados = movimientos

    if filtro_historial == "Entradas":
        movimientos_filtrados = [mov for mov in movimientos if mov[0] == "Entrada"]

    elif filtro_historial == "Salidas":
        movimientos_filtrados = [mov for mov in movimientos if mov[0] == "Salida"]

    elif filtro_historial == "Con OT":
        movimientos_filtrados = [mov for mov in movimientos if mov[3]]

    for mov in movimientos_filtrados[:30]:
        tipo = mov[0]
        cantidad = mov[1]
        motivo = mov[2]
        ot = mov[3]
        operario_mov = mov[4]
        fecha = mov[5]

        descripcion_ot = mov[6] if len(mov) > 6 else ""
        centro_ot = mov[7] if len(mov) > 7 else ""
        edificio_ot = mov[8] if len(mov) > 8 else ""
        espacio_ot = mov[9] if len(mov) > 9 else ""
        area_ot = mov[10] if len(mov) > 10 else ""
        prioridad_ot = mov[11] if len(mov) > 11 else ""
        estado_ot = mov[12] if len(mov) > 12 else ""
        fecha_creacion_ot = mov[13] if len(mov) > 13 else ""
        origen_ot = mov[14] if len(mov) > 14 else ""

        if tipo == "Entrada":
            st.success(
                f"""
➕ Entrada · {cantidad}

📅 {fecha}  
👷 {operario_mov or '-'}

📝 {motivo or '-'}
"""
            )

        else:
            if ot:
                html_ot = f"""
<div style="
    background:#f8fafc;
    border-radius:14px;
    padding:14px;
    margin-bottom:12px;
    border-left:5px solid #f59e0b;
">

<div style="font-size:18px;font-weight:800;color:#0f172a;">
🛠 {ot}
</div>

<div style="margin-top:8px;font-size:15px;">
📦 Salida: <b>{cantidad}</b>
</div>

<div style="margin-top:8px;font-size:14px;line-height:1.6;color:#334155;">
📍 <b>{centro_ot or '-'}</b> · {edificio_ot or '-'} · {espacio_ot or '-'}<br>
🧰 Área: {area_ot or '-'}<br>
⚡ Prioridad: <b>{prioridad_ot or '-'}</b><br>
📌 Estado OT: <b>{estado_ot or '-'}</b><br>
👷 Operario: {operario_mov or '-'}<br>
🕓 Movimiento: {fecha or '-'}<br>
🗂 Origen: {origen_ot or '-'}<br>
</div>

<div style="
    margin-top:10px;
    background:#ffffff;
    border-radius:10px;
    padding:10px;
    border:1px solid #e2e8f0;
">

<div style="font-size:14px;font-weight:700;margin-bottom:4px;">
📝 Descripción OT
</div>

<div style="font-size:14px;color:#111827;">
{descripcion_ot or '-'}
</div>

</div>

<div style="
    margin-top:10px;
    font-size:13px;
    color:#64748b;
">
📅 Fecha creación OT: {fecha_creacion_ot or '-'}
</div>

</div>
"""
                st.markdown(html_ot, unsafe_allow_html=True)

            else:
                st.error(
                    f"""
➖ Salida manual · {cantidad}

📅 {fecha}  
👷 {operario_mov or '-'}

📝 {motivo or '-'}
"""
                )


def pantalla_inventario():
    st.subheader("📦 Inventario mantenimiento")

    try:
        alertas = obtener_alertas_empresas_externas()

        if alertas["toca"] or alertas["proximo"]:
            st.markdown("### 🔔 Avisos empresas externas / Legionella")

            for item in alertas["toca"]:
                st.error(
                    f"🔴 TOCA gestionar: "
                    f"{item['tipo']} · "
                    f"{item['empresa']} · "
                    f"{item['centro']} · "
                    f"{item['fecha']}"
                )

            for item in alertas["proximo"]:
                st.warning(
                    f"🟠 Próximo: "
                    f"{item['tipo']} · "
                    f"{item['empresa']} · "
                    f"{item['centro']} · "
                    f"{item['fecha']}"
                )

    except Exception:
        pass

    operario = st.session_state.get("operario_activo", "")

    if operario == "Abel Vasquez":
        abrir_crear_material = st.session_state.pop("inventario_abrir_crear_material", False)

        with st.expander("➕ Crear material nuevo", expanded=abrir_crear_material):

            if st.session_state.pop("inventario_material_creado_ok", False):
                st.success("Material creado correctamente. Formulario limpio para crear otro.")

            material = st.text_input("Nombre material", key="crear_material_nombre")

            categoria = st.selectbox(
                "Categoría",
                ["Electricidad", "Fontanería", "Climatización", "Ferretería", "Pintura", "Limpieza", "Otros"],
                key="crear_categoria_material"
            )

            unidad = st.text_input("Unidad", value="uds", key="crear_material_unidad")

            exacto = None
            parecidos = []

            if material.strip():
                try:
                    exacto, parecidos = comprobar_material_antes_crear(
                        material,
                        categoria,
                        unidad
                    )
                except Exception:
                    exacto = None
                    parecidos = []

                if exacto:
                    st.error(
                        f"⚠️ Ya existe este material: "
                        f"{exacto['material']} | Código: {exacto['codigo']} | "
                        f"Stock: {exacto['stock_actual']}"
                    )

                elif parecidos:
                    st.warning("🔎 Materiales parecidos encontrados. Revisa antes de crear uno nuevo:")

                    for p in parecidos:
                        st.write(
                            f"- **{p['material']}** | "
                            f"Código: `{p['codigo']}` | "
                            f"Stock: {p['stock_actual']} | "
                            f"Coincide: {p.get('coincidencias', '-')}"
                        )

            stock_actual = st.number_input("Stock inicial", min_value=0.0, step=1.0, key="crear_material_stock_actual")
            stock_minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0, key="crear_material_stock_minimo")

            st.markdown("#### 💶 Coste del material")

            precio_unitario = st.number_input(
                "Precio unitario (€)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                key="crear_material_precio_unitario"
            )

            coste_total = float(stock_actual) * float(precio_unitario)
            st.info(f"Coste total inicial: {coste_total:.2f} €")

            fecha_compra = st.text_input(
                "Fecha compra / entrada",
                placeholder="Ejemplo: 30/04/2026",
                key="crear_material_fecha_compra"
            )

            referencia_factura = st.text_input(
                "Referencia factura / albarán",
                key="crear_material_referencia_factura"
            )

            observaciones_coste = st.text_area(
                "Observaciones coste",
                key="crear_material_observaciones_coste"
            )

            centro = st.selectbox("Centro", CENTROS, key="inv_mat_centro")
            edificios = obtener_edificios(centro)

            edificio = st.selectbox("Edificio", edificios, key="inv_mat_edificio")
            espacios = obtener_espacios(edificio)

            ubicacion = st.selectbox(
                "Aula / Espacio / Ubicación",
                espacios,
                key="inv_mat_ubicacion"
            )

            proveedor = st.text_input("Proveedor", key="crear_material_proveedor")
            observaciones = st.text_area("Observaciones", key="crear_material_observaciones")

            foto_subida = st.file_uploader(
                "Foto del material",
                type=["jpg", "jpeg", "png"],
                key="foto_material_mantenimiento"
            )

            ruta_foto = ""
            foto_nombre = ""
            foto_data = None

            if foto_subida is not None:
                if foto_subida.size > 5 * 1024 * 1024:
                    st.warning("La foto supera 5 MB. Mejor sube una imagen más pequeña.")
                else:
                    foto_nombre = limpiar_nombre_archivo(
                        f"{centro}_{edificio}_{ubicacion}_{material}_{foto_subida.name}"
                    )

                    foto_data = foto_subida.getvalue()

                    st.image(bytes(foto_data), width=250)
                    st.caption(f"📷 {foto_nombre}")

            if st.button("Crear material", use_container_width=True):
                if not material.strip():
                    st.warning("Indica el nombre del material.")

                elif exacto:
                    st.error("No se puede crear porque ya existe un material igual.")

                elif foto_subida is not None and foto_subida.size > 5 * 1024 * 1024:
                    st.error("No se puede guardar. La foto supera 5 MB.")

                else:
                    codigo = generar_codigo_material(material, categoria)

                    resultado = crear_material_inventario(
                        codigo=codigo,
                        material=material,
                        categoria=categoria,
                        unidad=unidad,
                        stock_actual=stock_actual,
                        stock_minimo=stock_minimo,
                        centro=centro,
                        edificio=edificio,
                        ubicacion=ubicacion,
                        proveedor=proveedor,
                        observaciones=observaciones,
                        foto=ruta_foto,
                        foto_nombre=foto_nombre,
                        foto_data=foto_data,
                        precio_unitario=precio_unitario,
                        coste_total=coste_total,
                        fecha_compra=fecha_compra,
                        referencia_factura=referencia_factura,
                        observaciones_coste=observaciones_coste
                    )

                    if isinstance(resultado, tuple):
                        ok, mensaje = resultado
                    else:
                        ok, mensaje = True, "Material creado correctamente"

                    if ok:
                        st.success(f"{mensaje}: {codigo}")
                        limpiar_formulario_crear_material()
                        st.rerun()
                    else:
                        st.error(mensaje)

    st.markdown("### 🔎 Buscar material")

    filtro_texto = st.text_input(
        "Buscar por código, material, ubicación o proveedor",
        key="filtro_texto_inventario"
    )

    f1, f2 = st.columns(2)

    with f1:
        filtro_centro = st.selectbox(
            "Centro",
            ["Todos"] + CENTROS,
            key="filtro_centro_inventario"
        )

    with f2:
        edificios_filtro = obtener_edificios(filtro_centro) if filtro_centro != "Todos" else []

        filtro_edificio = st.selectbox(
            "Edificio",
            ["Todos"] + edificios_filtro,
            key="filtro_edificio_inventario"
        )

    filtro_categoria = st.selectbox(
        "Categoría",
        ["Todas", "Electricidad", "Fontanería", "Climatización", "Ferretería", "Pintura", "Limpieza", "Otros"],
        key="filtro_categoria_inventario"
    )

    solo_stock_bajo = st.checkbox(
        "⚠️ Solo materiales con stock bajo",
        value=False,
        key="solo_stock_bajo_inventario"
    )

    ver_inactivos = False
    if puede_borrar_inventario():
        ver_inactivos = st.checkbox(
            "Mostrar materiales desactivados",
            key="ver_inactivos_inventario"
        )

    materiales = obtener_materiales_inventario(
        filtro_texto=filtro_texto,
        filtro_categoria=filtro_categoria,
        filtro_centro=filtro_centro,
        filtro_edificio=filtro_edificio,
        incluir_inactivos=ver_inactivos
    )

    if solo_stock_bajo:
        materiales = [
            m for m in materiales
            if float(m[5] or 0) <= float(m[6] or 0)
        ]

    if not materiales:
        st.info("No hay materiales con esos filtros.")
        return

    st.markdown(f"### 📋 Stock actual ({len(materiales)})")

    for m in materiales:
        columnas = [
            "id",
            "codigo",
            "material",
            "categoria",
            "unidad",
            "stock_actual",
            "stock_minimo",
            "centro",
            "edificio",
            "ubicacion",
            "proveedor",
            "observaciones",
            "fecha_alta",
            "foto",
            "foto_nombre",
            "foto_data",
            "activo",
            "precio_unitario",
            "coste_total",
            "fecha_compra",
            "referencia_factura",
            "observaciones_coste"
        ]

        material_dict = dict(zip(columnas, m))

        codigo = material_dict.get("codigo")
        material = material_dict.get("material")
        categoria = material_dict.get("categoria")
        unidad = material_dict.get("unidad")

        stock_actual = material_dict.get("stock_actual")
        stock_minimo = material_dict.get("stock_minimo")

        centro = material_dict.get("centro")
        edificio = material_dict.get("edificio")
        ubicacion = material_dict.get("ubicacion")

        proveedor = material_dict.get("proveedor")
        observaciones = material_dict.get("observaciones")

        foto = material_dict.get("foto")
        foto_nombre = material_dict.get("foto_nombre")
        foto_data = material_dict.get("foto_data")

        activo = material_dict.get("activo", 1)

        precio_unitario = material_dict.get("precio_unitario", 0)
        coste_total = material_dict.get("coste_total", 0)

        fecha_compra = material_dict.get("fecha_compra", "")
        referencia_factura = material_dict.get("referencia_factura", "")
        observaciones_coste = material_dict.get("observaciones_coste", "")

        try:
            precio_unitario = float(precio_unitario or 0)
        except Exception:
            precio_unitario = 0

        try:
            coste_total = float(coste_total or 0)
        except Exception:
            coste_total = 0

        try:
            stock_actual_num = float(stock_actual or 0)
            stock_minimo_num = float(stock_minimo or 0)
        except Exception:
            stock_actual_num = 0
            stock_minimo_num = 0

        if activo == 0:
            icono = "⛔"
        elif stock_actual_num <= stock_minimo_num:
            icono = "⚠️"
        else:
            icono = "✅"

        titulo = f"{icono} {codigo} | {material} | Stock: {stock_actual} {unidad}"

        with st.expander(titulo, expanded=False):

            if activo == 0:
                st.warning(f"⛔ Material desactivado: {material}")
            elif stock_actual_num <= stock_minimo_num:
                st.warning(f"⚠️ Stock bajo: {material} ({stock_actual} {unidad})")

            st.markdown(f"### **{codigo}** · {material}")
            st.markdown(f"**Categoría:** {categoria or '-'}")
            st.markdown(f"**Stock:** {stock_actual} {unidad} · **Mínimo:** {stock_minimo} {unidad}")
            st.markdown(f"**Precio unitario:** {precio_unitario:.2f} € · **Coste inicial:** {coste_total:.2f} €")
            st.caption(f"🏢 {centro or '-'} · {edificio or '-'} · {ubicacion or '-'}")

            if proveedor:
                st.caption(f"Proveedor: {proveedor}")

            if fecha_compra:
                st.caption(f"Fecha compra / entrada: {fecha_compra}")

            if referencia_factura:
                st.caption(f"Factura / albarán: {referencia_factura}")

            if observaciones:
                st.info(observaciones)

            if observaciones_coste:
                st.info(f"💶 {observaciones_coste}")

            if foto_data:
                try:
                    st.image(bytes(foto_data), width=220)
                    if foto_nombre:
                        st.caption(f"📷 {foto_nombre}")
                except Exception as e:
                    st.caption(f"Foto no disponible: {e}")

            elif foto:
                try:
                    st.image(foto, width=220)
                    if foto_nombre:
                        st.caption(f"📷 {foto_nombre}")
                except Exception:
                    st.caption("Foto no disponible.")
            # -------------------------
            # EDITAR MATERIAL - ABEL
            # -------------------------
            with st.expander("✏️ Editar material"):
            
                nuevo_material = st.text_input(
                    "Material",
                    value=str(material or ""),
                    key=f"abel_edit_material_{codigo}"
                )
            
                nueva_categoria = st.text_input(
                    "Categoría",
                    value=str(categoria or ""),
                    key=f"abel_edit_categoria_{codigo}"
                )
            
                nueva_ubicacion = st.text_input(
                    "Ubicación",
                    value=str(ubicacion or ""),
                    key=f"abel_edit_ubicacion_{codigo}"
                )
            
                nuevo_proveedor = st.text_input(
                    "Proveedor",
                    value=str(proveedor or ""),
                    key=f"abel_edit_proveedor_{codigo}"
                )
            
                nuevo_stock_minimo = st.number_input(
                    "Stock mínimo",
                    min_value=0.0,
                    value=float(stock_minimo or 0),
                    step=1.0,
                    key=f"abel_edit_stock_minimo_{codigo}"
                )
            
                nuevo_precio_unitario = st.number_input(
                    "Precio unitario €",
                    min_value=0.0,
                    value=float(precio_unitario or 0),
                    step=0.10,
                    key=f"abel_edit_precio_{codigo}"
                )
            
                nuevas_observaciones = st.text_area(
                    "Observaciones",
                    value=str(observaciones or ""),
                    key=f"abel_edit_obs_{codigo}"
                )
            
                nueva_foto = st.file_uploader(
                    "Cambiar foto",
                    type=["jpg", "jpeg", "png"],
                    key=f"abel_edit_foto_{codigo}"
                )
            
                col_guardar, col_cancelar = st.columns(2)
            
                with col_guardar:
                    if st.button("💾 Guardar cambios", key=f"abel_guardar_{codigo}"):
            
                        foto_nombre_nueva = None
                        foto_data_nueva = None
            
                        if nueva_foto is not None:
                            foto_nombre_nueva = nueva_foto.name
                            foto_data_nueva = nueva_foto.getvalue()
            
                        actualizar_material_abel(
                            codigo=codigo,
                            material=nuevo_material,
                            categoria=nueva_categoria,
                            ubicacion=nueva_ubicacion,
                            proveedor=nuevo_proveedor,
                            stock_minimo=nuevo_stock_minimo,
                            precio_unitario=nuevo_precio_unitario,
                            observaciones=nuevas_observaciones,
                            foto_nombre=foto_nombre_nueva,
                            foto_data=foto_data_nueva
                        )
            
                        st.success("Material actualizado correctamente.")
                        st.rerun()

            
            if puede_borrar_inventario():
                if activo == 1:
                    confirmar = st.checkbox(
                        f"Confirmo que quiero desactivar {codigo}",
                        key=f"confirmar_desactivar_{codigo}"
                    )

                    if confirmar:
                        if st.button(f"⛔ Desactivar {codigo}", key=f"desactivar_{codigo}", use_container_width=True):
                            ok, mensaje = desactivar_material(codigo)
                            if ok:
                                st.success(mensaje)
                                st.rerun()
                            else:
                                st.error(mensaje)
                else:
                    confirmar_activar = st.checkbox(
                        f"Confirmo que quiero reactivar {codigo}",
                        key=f"confirmar_activar_{codigo}"
                    )

                    if confirmar_activar:
                        if st.button(f"✅ Activar {codigo}", key=f"activar_{codigo}", use_container_width=True):
                            ok, mensaje = activar_material(codigo)
                            if ok:
                                st.success(mensaje)
                                st.rerun()
                            else:
                                st.error(mensaje)

            with st.expander(f"📊 Historial {codigo}"):
                mostrar_historial_material(codigo)

            if activo == 1:
                c1, c2 = st.columns(2)

                with c1:
                    entrada = st.number_input(
                        f"Entrada {codigo}",
                        min_value=0.0,
                        step=1.0,
                        key=f"entrada_{codigo}"
                    )

                    if st.button(f"➕ Añadir {codigo}", key=f"btn_entrada_{codigo}"):
                        if entrada > 0:
                            ok, mensaje = registrar_movimiento_inventario(
                                codigo_material=codigo,
                                tipo_movimiento="Entrada",
                                cantidad=entrada,
                                motivo="Entrada manual",
                                numero_ot="",
                                operario=operario
                            )

                            if ok:
                                st.success(mensaje)
                                st.rerun()
                            else:
                                st.error(mensaje)

                with c2:
                    salida = st.number_input(
                        f"Salida {codigo}",
                        min_value=0.0,
                        step=1.0,
                        key=f"salida_{codigo}"
                    )

                    if st.button(f"➖ Quitar {codigo}", key=f"btn_salida_{codigo}"):
                        if salida > 0:
                            ok, mensaje = registrar_movimiento_inventario(
                                codigo_material=codigo,
                                tipo_movimiento="Salida",
                                cantidad=salida,
                                motivo="Salida manual",
                                numero_ot="",
                                operario=operario
                            )

                            if ok:
                                st.success(mensaje)
                                st.rerun()
                            else:
                                st.error(mensaje)
            else:
                st.info("Material desactivado: no permite entradas ni salidas.")
